"""Comparação preventiva entre dois planos estimados, sem executar os SELECTs."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import psycopg

from src.analyzer import (
    collect_relation_metadata,
    explain_query,
    fetch_history,
    load_select,
)
from src.database import get_connection
from src.plan_analyzer import analyze_plan, iter_plan_nodes


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compara dois planos estimados sem executar as consultas."
    )
    parser.add_argument("--original", type=Path, required=True)
    parser.add_argument("--alternative", type=Path, required=True)
    parser.add_argument("--timeout-seconds", type=int, default=30)
    return parser.parse_args()


def build_summary(
    path: Path,
    document: dict[str, Any],
    history: dict[str, Any] | None,
    score: int,
    attention_level: str,
) -> dict[str, Any]:
    root = document["Plan"]
    return {
        "path": path,
        "query_id": document.get("Query Identifier"),
        "root_node": root.get("Node Type", "não informado"),
        "node_count": sum(1 for _ in iter_plan_nodes(root)),
        "total_cost": float(root.get("Total Cost", 0) or 0),
        "estimated_rows": int(root.get("Plan Rows", 0) or 0),
        "planning_time": float(document.get("Planning Time", 0) or 0),
        "history": history,
        "score": score,
        "attention_level": attention_level,
    }


def display_comparison(
    original: dict[str, Any],
    alternative: dict[str, Any],
) -> None:
    print("=" * 72)
    print("COMPARAÇÃO PREVENTIVA DE PLANOS")
    print("=" * 72)
    print("Consultas executadas: não (dois EXPLAINs com ANALYZE FALSE)")
    print(f"Original:    {original['path']}")
    print(f"Alternativa: {alternative['path']}")

    rows = (
        ("Query ID", original["query_id"], alternative["query_id"]),
        ("Nó principal", original["root_node"], alternative["root_node"]),
        ("Nós no plano", original["node_count"], alternative["node_count"]),
        (
            "Custo estimado",
            f"{original['total_cost']:.2f}",
            f"{alternative['total_cost']:.2f}",
        ),
        (
            "Linhas estimadas",
            f"{original['estimated_rows']:,}",
            f"{alternative['estimated_rows']:,}",
        ),
        (
            "Planejamento",
            f"{original['planning_time']:.2f} ms",
            f"{alternative['planning_time']:.2f} ms",
        ),
        (
            "Atenção heurística",
            f"{original['attention_level'].upper()} ({original['score']}/10)",
            f"{alternative['attention_level'].upper()} ({alternative['score']}/10)",
        ),
    )

    label_width = max(len(row[0]) for row in rows)
    original_width = max(len(str(row[1])) for row in rows)
    print()
    print(
        "Métrica".ljust(label_width + 2)
        + "Original".ljust(original_width + 2)
        + "Alternativa"
    )
    print("-" * 72)
    for label, original_value, alternative_value in rows:
        print(
            str(label).ljust(label_width + 2)
            + str(original_value).ljust(original_width + 2)
            + str(alternative_value)
        )

    original_history = original.get("history")
    if original_history and original_history.get("calls", 0) > 0:
        historical_average = original_history["rows"] / original_history["calls"]
        original_error = _relative_error(
            original["estimated_rows"], historical_average
        )
        alternative_error = _relative_error(
            alternative["estimated_rows"], historical_average
        )
        print("\nReferência histórica da consulta original:")
        print(f"- Média observada: {historical_average:,.0f} linhas por execução")
        print(f"- Erro relativo da estimativa original: {original_error:.2f}%")
        print(f"- Erro relativo da estimativa alternativa: {alternative_error:.2f}%")
        print(
            "- A comparação da alternativa com essa referência pressupõe que "
            "as duas consultas sejam semanticamente equivalentes."
        )

    cost_change = _percentage_change(
        original["total_cost"], alternative["total_cost"]
    )
    row_change = _percentage_change(
        original["estimated_rows"], alternative["estimated_rows"]
    )
    print("\nVariações estimadas:")
    print(f"- Custo do planejador: {cost_change:+.2f}%")
    print(f"- Linhas reconhecidas pelo planejador: {row_change:+.2f}%")
    print(
        "- O custo é uma unidade interna, não tempo previsto. Um custo maior "
        "pode apenas refletir uma estimativa de cardinalidade mais realista."
    )
    print(
        "\nA comparação não comprova ganho de desempenho; ela organiza "
        "hipóteses para um teste controlado posterior."
    )


def _relative_error(estimated: float, reference: float) -> float:
    if reference == 0:
        return 0.0
    return abs(estimated - reference) / reference * 100


def _percentage_change(original: float, alternative: float) -> float:
    if original == 0:
        return 0.0
    return (alternative - original) / original * 100


def main() -> int:
    args = parse_arguments()
    if not 1 <= args.timeout_seconds <= 600:
        print("Erro: --timeout-seconds deve estar entre 1 e 600.", file=sys.stderr)
        return 1

    try:
        original_query = load_select(args.original)
        alternative_query = load_select(args.alternative)

        with get_connection() as connection:
            connection.read_only = True

            original_document = explain_query(
                connection, original_query, args.timeout_seconds
            )
            original_metadata = collect_relation_metadata(
                connection, original_document
            )
            original_query_id_value = original_document.get("Query Identifier")
            original_query_id = (
                int(original_query_id_value)
                if original_query_id_value is not None
                else None
            )
            original_history = fetch_history(connection, original_query_id)
            original_assessment = analyze_plan(
                original_query,
                original_document,
                original_metadata,
                original_history,
            )

            alternative_document = explain_query(
                connection, alternative_query, args.timeout_seconds
            )
            alternative_metadata = collect_relation_metadata(
                connection, alternative_document
            )
            alternative_query_id_value = alternative_document.get("Query Identifier")
            alternative_query_id = (
                int(alternative_query_id_value)
                if alternative_query_id_value is not None
                else None
            )
            alternative_history = fetch_history(connection, alternative_query_id)
            alternative_assessment = analyze_plan(
                alternative_query,
                alternative_document,
                alternative_metadata,
                alternative_history,
            )

        original_summary = build_summary(
            args.original,
            original_document,
            original_history,
            original_assessment.score,
            original_assessment.attention_level,
        )
        alternative_summary = build_summary(
            args.alternative,
            alternative_document,
            alternative_history,
            alternative_assessment.score,
            alternative_assessment.attention_level,
        )
        display_comparison(original_summary, alternative_summary)
    except (OSError, ValueError) as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1
    except psycopg.Error as exc:
        print(
            "Erro ao solicitar os planos estimados ao PostgreSQL: "
            f"{exc.diag.message_primary or exc}",
            file=sys.stderr,
        )
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
