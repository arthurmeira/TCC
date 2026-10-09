"""Regras heurísticas para análise preventiva de planos do PostgreSQL."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Iterator


LARGE_RELATION_ROWS = 50_000
LARGE_RESULT_ROWS = 100_000
LARGE_SORT_ROWS = 10_000
EXPENSIVE_NESTED_LOOP_PAIRS = 1_000_000
CARDINALITY_DIVERGENCE_RATIO = 10

FUNCTION_PATTERN = re.compile(
    r"\b(extract|lower|upper|date_trunc|substring|trim)\s*\(",
    re.IGNORECASE,
)
SELECT_ALL_PATTERN = re.compile(
    r"\bselect\s+(?:distinct\s+)?(?:[a-z_][\w$]*\.)?\*",
    re.IGNORECASE | re.DOTALL,
)


@dataclass(frozen=True)
class Finding:
    """Um indício encontrado no plano e sua recomendação de investigação."""

    severity: str
    title: str
    evidence: str
    recommendation: str
    points: int


@dataclass(frozen=True)
class PlanAssessment:
    """Resultado consolidado da análise por regras."""

    attention_level: str
    score: int
    findings: tuple[Finding, ...]


def iter_plan_nodes(plan: dict[str, Any]) -> Iterator[dict[str, Any]]:
    """Percorre recursivamente todos os nós de um plano JSON."""
    yield plan
    for child in plan.get("Plans", []):
        yield from iter_plan_nodes(child)


def relation_key(node: dict[str, Any]) -> tuple[str, str] | None:
    """Retorna (schema, relação) quando o nó referencia uma tabela."""
    relation_name = node.get("Relation Name")
    if not relation_name:
        return None
    return (node.get("Schema", "public"), relation_name)


def analyze_plan(
    query_sql: str,
    document: dict[str, Any],
    relation_metadata: dict[tuple[str, str], dict[str, int]],
    history: dict[str, Any] | None = None,
) -> PlanAssessment:
    """Aplica regras simples ao plano estimado, sem afirmar causalidade."""
    root_plan = document["Plan"]
    nodes = list(iter_plan_nodes(root_plan))
    findings: list[Finding] = []

    if SELECT_ALL_PATTERN.search(query_sql):
        findings.append(
            Finding(
                severity="baixa",
                title="Seleção ampla de colunas",
                evidence="A consulta contém SELECT *.",
                recommendation=(
                    "Liste somente as colunas necessárias quando o consumidor "
                    "não precisar do registro completo. Isso pode reduzir "
                    "transferência, memória e trabalho de serialização."
                ),
                points=1,
            )
        )

    for node in nodes:
        node_type = str(node.get("Node Type", ""))
        key = relation_key(node)
        metadata = relation_metadata.get(key, {}) if key else {}
        relation_rows = metadata.get("estimated_rows", 0)
        relation_label = ".".join(key) if key else "relação não identificada"
        filter_expression = str(node.get("Filter", ""))

        if (
            node_type in {"Seq Scan", "Parallel Seq Scan"}
            and filter_expression
            and relation_rows >= LARGE_RELATION_ROWS
        ):
            findings.append(
                Finding(
                    severity="alta",
                    title=f"Varredura sequencial em {relation_label}",
                    evidence=(
                        f"O plano prevê {node_type} com filtro em uma relação "
                        f"estimada em {relation_rows:,} linhas."
                    ),
                    recommendation=(
                        "Verifique a seletividade do filtro e os índices já "
                        "existentes. Um índice só deve ser proposto depois de "
                        "confirmar as colunas, a distribuição dos dados e o "
                        "efeito esperado sobre escritas."
                    ),
                    points=3,
                )
            )

        if filter_expression and FUNCTION_PATTERN.search(filter_expression):
            findings.append(
                Finding(
                    severity="média",
                    title=f"Função aplicada no filtro de {relation_label}",
                    evidence=f"Filtro estimado pelo plano: {filter_expression}",
                    recommendation=(
                        "Avalie uma forma equivalente que compare a coluna "
                        "diretamente, como um intervalo de datas. Se isso não "
                        "for possível, investigue um índice de expressão; "
                        "nenhuma dessas opções deve ser aplicada sem medição."
                    ),
                    points=2,
                )
            )

        if node_type in {"Sort", "Incremental Sort"}:
            plan_rows = int(node.get("Plan Rows", 0) or 0)
            if plan_rows >= LARGE_SORT_ROWS:
                sort_keys = ", ".join(node.get("Sort Key", [])) or "não informadas"
                findings.append(
                    Finding(
                        severity="média",
                        title="Ordenação de muitas linhas",
                        evidence=(
                            f"O nó {node_type} estima ordenar {plan_rows:,} "
                            f"linhas pelas chaves: {sort_keys}."
                        ),
                        recommendation=(
                            "Confirme se toda a ordenação e todo o resultado são "
                            "necessários. Depois, avalie filtros, paginação e a "
                            "possibilidade de um índice compatível com o ORDER BY."
                        ),
                        points=2,
                    )
                )

        if node_type == "Nested Loop":
            children = node.get("Plans", [])
            if len(children) >= 2:
                left_rows = int(children[0].get("Plan Rows", 0) or 0)
                right_rows = int(children[1].get("Plan Rows", 0) or 0)
                estimated_pairs = left_rows * right_rows
                if estimated_pairs >= EXPENSIVE_NESTED_LOOP_PAIRS:
                    findings.append(
                        Finding(
                            severity="média",
                            title="Nested Loop com combinação estimada elevada",
                            evidence=(
                                "Os dois primeiros ramos estimam até "
                                f"{estimated_pairs:,} combinações brutas."
                            ),
                            recommendation=(
                                "Revise as condições de junção, a seletividade e "
                                "os índices das chaves relacionadas. O Nested Loop "
                                "não é um problema por si só; o alerta depende do "
                                "volume efetivamente processado."
                            ),
                            points=2,
                        )
                    )

    estimated_output = int(root_plan.get("Plan Rows", 0) or 0)
    if estimated_output >= LARGE_RESULT_ROWS:
        findings.append(
            Finding(
                severity="alta",
                title="Resultado estimado volumoso",
                evidence=(
                    f"O nó principal estima retornar {estimated_output:,} linhas."
                ),
                recommendation=(
                    "Confirme se o consumidor precisa de todas as linhas. Filtros "
                    "mais seletivos, paginação ou agregação podem reduzir o custo "
                    "e o tráfego quando forem compatíveis com a regra de negócio."
                ),
                points=3,
            )
        )

    if history and history.get("calls", 0) > 0 and estimated_output > 0:
        historical_rows_per_call = history["rows"] / history["calls"]
        larger_value = max(historical_rows_per_call, estimated_output)
        smaller_value = min(historical_rows_per_call, estimated_output)
        divergence_ratio = larger_value / smaller_value if smaller_value else 0

        if divergence_ratio >= CARDINALITY_DIVERGENCE_RATIO:
            direction = (
                "subestima"
                if estimated_output < historical_rows_per_call
                else "superestima"
            )
            findings.append(
                Finding(
                    severity="alta",
                    title="Grande divergência na estimativa de linhas",
                    evidence=(
                        f"O plano estima {estimated_output:,} linhas, enquanto "
                        f"o histórico registra em média "
                        f"{historical_rows_per_call:,.0f} por execução. A "
                        f"estimativa {direction} o resultado em aproximadamente "
                        f"{divergence_ratio:.1f} vezes."
                    ),
                    recommendation=(
                        "Investigue a qualidade das estatísticas e a expressão "
                        "usada no filtro. Uma estimativa distante pode levar o "
                        "planejador a escolher operações inadequadas. Compare "
                        "posteriormente a forma atual com um predicado de intervalo "
                        "e atualize estatísticas somente em experimento controlado."
                    ),
                    points=3,
                )
            )

    subplans = [
        node
        for node in nodes
        if node.get("Parent Relationship") == "SubPlan"
        or node.get("Subplan Name")
    ]
    if subplans:
        findings.append(
            Finding(
                severity="média",
                title="Subplano identificado",
                evidence=f"O plano contém {len(subplans)} nó(s) associado(s) a subplano.",
                recommendation=(
                    "Verifique se a subconsulta depende de cada linha da consulta "
                    "externa. Quando houver correlação e grande volume, compare "
                    "posteriormente uma junção ou pré-agregação equivalente."
                ),
                points=2,
            )
        )

    findings = _deduplicate(findings)
    score = min(sum(item.points for item in findings), 10)
    if score >= 7:
        attention_level = "alto"
    elif score >= 3:
        attention_level = "médio"
    else:
        attention_level = "baixo"

    return PlanAssessment(
        attention_level=attention_level,
        score=score,
        findings=tuple(findings),
    )


def _deduplicate(findings: list[Finding]) -> list[Finding]:
    """Remove achados idênticos preservando a ordem das regras."""
    unique: list[Finding] = []
    seen: set[tuple[str, str]] = set()
    for finding in findings:
        key = (finding.title, finding.evidence)
        if key not in seen:
            seen.add(key)
            unique.append(finding)
    return unique
