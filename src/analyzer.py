"""CLI para análise preventiva de uma consulta SELECT com EXPLAIN estimado."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

import psycopg
from psycopg import sql

from src.database import get_connection
from src.plan_analyzer import analyze_plan, iter_plan_nodes, relation_key


EXPLAIN_PREFIX = (
    "EXPLAIN (ANALYZE FALSE, VERBOSE TRUE, COSTS TRUE, "
    "SETTINGS TRUE, SUMMARY TRUE, FORMAT JSON) "
)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Analisa o plano estimado de um SELECT sem executar a consulta."
        )
    )
    parser.add_argument(
        "--sql-file",
        type=Path,
        required=True,
        help="Arquivo UTF-8 que contém exatamente uma consulta SELECT.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=30,
        help="Limite para o planejamento no servidor (padrão: 30).",
    )
    parser.add_argument(
        "--no-history",
        action="store_true",
        help="Não procura o queryid no histórico do pg_stat_statements.",
    )
    return parser.parse_args()


def load_select(path: Path) -> str:
    """Lê e valida uma única instrução SELECT."""
    if not path.is_file():
        raise ValueError(f"Arquivo SQL não encontrado: {path}")

    query = path.read_text(encoding="utf-8-sig")
    normalized, semicolons = _normalize_sql(query)
    if not normalized.strip():
        raise ValueError("O arquivo SQL está vazio.")
    if len(semicolons) > 1:
        raise ValueError("O arquivo deve conter somente uma instrução SQL.")

    if semicolons:
        separator = semicolons[0]
        if normalized[separator + 1 :].strip():
            raise ValueError("Há conteúdo SQL depois do ponto e vírgula final.")
        query = query[:separator].rstrip()
        normalized = normalized[:separator]
    else:
        query = query.strip()

    if not re.match(r"^\s*SELECT\b", normalized, re.IGNORECASE):
        raise ValueError(
            "Nesta versão, o analisador aceita somente uma consulta iniciada por SELECT."
        )
    if re.search(r"\bINTO\b", normalized, re.IGNORECASE):
        raise ValueError("SELECT INTO não é aceito pelo analisador preventivo.")

    return query


def _normalize_sql(query: str) -> tuple[str, list[int]]:
    """Oculta comentários e identifica separadores fora de literais."""
    result = list(query)
    semicolons: list[int] = []
    index = 0
    state = "normal"
    block_depth = 0
    dollar_tag = ""

    while index < len(query):
        char = query[index]
        next_char = query[index + 1] if index + 1 < len(query) else ""

        if state == "normal":
            if char == "-" and next_char == "-":
                result[index] = result[index + 1] = " "
                state = "line_comment"
                index += 2
                continue
            if char == "/" and next_char == "*":
                result[index] = result[index + 1] = " "
                state = "block_comment"
                block_depth = 1
                index += 2
                continue
            if char == "'":
                state = "single_quote"
            elif char == '"':
                state = "double_quote"
            elif char == "$":
                match = re.match(r"\$(?:[A-Za-z_][A-Za-z0-9_]*)?\$", query[index:])
                if match:
                    dollar_tag = match.group(0)
                    state = "dollar_quote"
                    index += len(dollar_tag)
                    continue
            elif char == ";":
                semicolons.append(index)

        elif state == "line_comment":
            if char in "\r\n":
                state = "normal"
            else:
                result[index] = " "

        elif state == "block_comment":
            result[index] = " "
            if char == "/" and next_char == "*":
                result[index + 1] = " "
                block_depth += 1
                index += 2
                continue
            if char == "*" and next_char == "/":
                result[index + 1] = " "
                block_depth -= 1
                index += 2
                if block_depth == 0:
                    state = "normal"
                continue

        elif state == "single_quote":
            if char == "\\" and next_char:
                index += 2
                continue
            if char == "'":
                if next_char == "'":
                    index += 2
                    continue
                state = "normal"

        elif state == "double_quote":
            if char == '"':
                if next_char == '"':
                    index += 2
                    continue
                state = "normal"

        elif state == "dollar_quote" and query.startswith(dollar_tag, index):
            index += len(dollar_tag)
            state = "normal"
            continue

        index += 1

    if state in {"single_quote", "double_quote", "dollar_quote", "block_comment"}:
        raise ValueError("O arquivo SQL contém comentário ou literal não finalizado.")

    return "".join(result), semicolons


def explain_query(
    connection: psycopg.Connection,
    query: str,
    timeout_seconds: int,
) -> dict[str, Any]:
    """Solicita somente o plano estimado em JSON."""
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT set_config('statement_timeout', %s, true)",
            (f"{timeout_seconds}s",),
        )
        cursor.execute("SELECT set_config('lock_timeout', '5s', true)")
        cursor.execute("SELECT current_database()")
        database_name = cursor.fetchone()[0]
        if database_name != "tcc_sql_optimizer":
            raise ValueError(
                "O analisador deve ser usado somente no banco tcc_sql_optimizer."
            )

        cursor.execute(EXPLAIN_PREFIX + query)
        payload = cursor.fetchone()[0]

    if isinstance(payload, str):
        payload = json.loads(payload)
    if not isinstance(payload, list) or not payload or "Plan" not in payload[0]:
        raise ValueError("O PostgreSQL retornou um plano JSON em formato inesperado.")
    return payload[0]


def collect_relation_metadata(
    connection: psycopg.Connection,
    document: dict[str, Any],
) -> dict[tuple[str, str], dict[str, int]]:
    """Lê estimativas e tamanhos das relações citadas no plano."""
    relations = {
        key
        for node in iter_plan_nodes(document["Plan"])
        if (key := relation_key(node)) is not None
    }
    metadata: dict[tuple[str, str], dict[str, int]] = {}

    with connection.cursor() as cursor:
        for schema_name, relation_name in sorted(relations):
            cursor.execute(
                """
                SELECT
                    GREATEST(c.reltuples, 0)::bigint AS estimated_rows,
                    pg_total_relation_size(c.oid) AS size_bytes
                FROM pg_catalog.pg_class AS c
                JOIN pg_catalog.pg_namespace AS n ON n.oid = c.relnamespace
                WHERE n.nspname = %s
                  AND c.relname = %s;
                """,
                (schema_name, relation_name),
            )
            row = cursor.fetchone()
            if row:
                metadata[(schema_name, relation_name)] = {
                    "estimated_rows": int(row[0]),
                    "size_bytes": int(row[1]),
                }
    return metadata


def fetch_history(
    connection: psycopg.Connection,
    query_id: int | None,
) -> dict[str, Any] | None:
    """Procura métricas anteriores do mesmo queryid, quando disponíveis."""
    if query_id is None:
        return None

    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT n.nspname
            FROM pg_catalog.pg_extension AS e
            JOIN pg_catalog.pg_namespace AS n ON n.oid = e.extnamespace
            WHERE e.extname = 'pg_stat_statements';
            """
        )
        extension_row = cursor.fetchone()
        if not extension_row:
            return None

        statement = sql.SQL(
            """
            SELECT calls, total_exec_time, mean_exec_time, rows
            FROM {}.pg_stat_statements
            WHERE dbid = (
                SELECT oid FROM pg_catalog.pg_database
                WHERE datname = current_database()
            )
              AND userid = (
                SELECT usesysid FROM pg_catalog.pg_user
                WHERE usename = current_user
            )
              AND queryid = %s
              AND toplevel = true
            LIMIT 1;
            """
        ).format(sql.Identifier(extension_row[0]))
        cursor.execute(statement, (query_id,))
        row = cursor.fetchone()

    if not row:
        return None
    return {
        "calls": int(row[0]),
        "total_exec_time": float(row[1]),
        "mean_exec_time": float(row[2]),
        "rows": int(row[3]),
    }


def display_report(
    sql_file: Path,
    document: dict[str, Any],
    relation_metadata: dict[tuple[str, str], dict[str, int]],
    history: dict[str, Any] | None,
    assessment: Any,
) -> None:
    root = document["Plan"]
    query_id = document.get("Query Identifier")
    node_count = sum(1 for _ in iter_plan_nodes(root))

    print("=" * 64)
    print("ANÁLISE PREVENTIVA DA CONSULTA")
    print("=" * 64)
    print(f"Arquivo: {sql_file}")
    print("Consulta executada: não (EXPLAIN com ANALYZE FALSE)")
    print(f"Query ID estimado: {query_id if query_id is not None else 'não informado'}")
    print(f"Nó principal: {root.get('Node Type', 'não informado')}")
    print(f"Quantidade de nós no plano: {node_count}")
    print(f"Custo total estimado: {float(root.get('Total Cost', 0)):.2f}")
    print(f"Linhas de saída estimadas: {int(root.get('Plan Rows', 0) or 0):,}")
    if "Planning Time" in document:
        print(f"Tempo de planejamento: {float(document['Planning Time']):.2f} ms")
    print("Observação: custo estimado usa unidades do planejador, não milissegundos.")

    if relation_metadata:
        print("\nRelações consideradas:")
        for key, metadata in sorted(relation_metadata.items()):
            print(
                f"- {key[0]}.{key[1]}: ~{metadata['estimated_rows']:,} linhas; "
                f"{_format_bytes(metadata['size_bytes'])}"
            )

    print("\nHistórico real no pg_stat_statements:")
    if history:
        print(
            f"- chamadas={history['calls']:,} | "
            f"total={history['total_exec_time']:.2f} ms | "
            f"média={history['mean_exec_time']:.2f} ms | "
            f"linhas={history['rows']:,}"
        )
    else:
        print("- Nenhuma entrada correspondente foi encontrada ou consultada.")

    print(
        f"\nNível de atenção heurístico: {assessment.attention_level.upper()} "
        f"({assessment.score}/10)"
    )
    if not assessment.findings:
        print("Nenhum padrão coberto pelas regras atuais foi identificado.")
        print("Isso não comprova que a consulta terá bom desempenho.")
        return

    for position, finding in enumerate(assessment.findings, start=1):
        print(f"\n{position}. [{finding.severity.upper()}] {finding.title}")
        print(f"   Evidência: {finding.evidence}")
        print(f"   Sugestão: {finding.recommendation}")

    print("\nAs sugestões são hipóteses para validação posterior, não otimizações automáticas.")


def _format_bytes(size_bytes: int) -> str:
    value = float(size_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024 or unit == "TB":
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} TB"


def main() -> int:
    args = parse_arguments()
    if not 1 <= args.timeout_seconds <= 600:
        print("Erro: --timeout-seconds deve estar entre 1 e 600.", file=sys.stderr)
        return 1

    try:
        query = load_select(args.sql_file)
        with get_connection() as connection:
            connection.read_only = True
            document = explain_query(connection, query, args.timeout_seconds)
            metadata = collect_relation_metadata(connection, document)
            query_id_value = document.get("Query Identifier")
            query_id = int(query_id_value) if query_id_value is not None else None
            history = None if args.no_history else fetch_history(connection, query_id)

        assessment = analyze_plan(query, document, metadata, history)
        display_report(
            args.sql_file,
            document,
            metadata,
            history,
            assessment,
        )
    except (OSError, ValueError) as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1
    except psycopg.Error as exc:
        print(
            "Erro ao solicitar o plano estimado ao PostgreSQL: "
            f"{exc.diag.message_primary or exc}",
            file=sys.stderr,
        )
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
