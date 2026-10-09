r"""Coleta pg_stat_statements, exibe rankings e exporta arquivos locais.

Não modifica os dados das tabelas nem reseta estatísticas.

Execução manual na raiz do projeto:
    .\.venv\Scripts\python.exe -m src.collector --top 5
"""

import argparse
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import psycopg
from psycopg import sql
from psycopg.rows import dict_row

from src.database import get_connection
from src.config import PROJECT_ROOT
from src.exporter import export_results
from src.ranking import print_rankings


LEADING_COMMENTS = re.compile(r"\A(?:\s+|--[^\n]*(?:\n|$)|/\*.*?\*/)*", re.DOTALL)
SELECT_START = re.compile(r"^SELECT\b", re.IGNORECASE)
EXPERIMENT_RELATION = (
    r'"?public"?\s*\.\s*'
    r'"?(?:clientes|produtos|pedidos|itens_pedido|pagamentos)"?'
)
EXPERIMENT_TABLE = re.compile(
    r'\b(?:FROM|JOIN)\s+' + EXPERIMENT_RELATION + r'(?=\s|[;,)]|$)',
    re.IGNORECASE,
)
PREPARATION_QUERY = re.compile(
    r'SELECT\s+EXISTS\s*\(\s*SELECT\s+(?:1|\$\d+)\s+FROM\s+'
    + EXPERIMENT_RELATION
    + r'\s+LIMIT\s+(?:1|\$\d+)\s*\)\s*;?\s*',
    re.IGNORECASE,
)


def positive_integer(value: str) -> int:
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("O valor deve ser maior que zero.")
    return number


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--top", type=positive_integer, default=5, help="Posições em cada ranking.")
    parser.add_argument(
        "--all-selects", action="store_true",
        help="Inclui SELECTs administrativos do mesmo banco e usuário.",
    )
    parser.add_argument(
        "--format", choices=("csv", "json", "both"), default="both",
        help="Formato de exportação (padrão: both, CSV e JSON).",
    )
    parser.add_argument(
        "--output-dir", type=Path, default=PROJECT_ROOT / "results",
        help="Pasta dos resultados (padrão: results na raiz do projeto).",
    )
    parser.add_argument(
        "--no-export", action="store_true",
        help="Exibe os rankings sem criar ou substituir arquivos de resultados.",
    )
    return parser.parse_args()


def matches_scope(query: str | None, all_selects: bool) -> bool:
    """Filtra o formato de SQL do experimento; não é um analisador SQL geral."""
    if not query:
        return False
    statement = LEADING_COMMENTS.sub("", query, count=1)
    if not SELECT_START.match(statement):
        return False
    if all_selects:
        return True
    if PREPARATION_QUERY.fullmatch(statement):
        return False
    return EXPERIMENT_TABLE.search(statement) is not None


def inspect_extension(cursor: psycopg.Cursor) -> tuple[dict, set[str]]:
    cursor.execute(
        """
        SELECT e.extversion AS extension_version, n.nspname AS extension_schema
        FROM pg_extension e
        JOIN pg_namespace n ON n.oid = e.extnamespace
        WHERE e.extname = 'pg_stat_statements'
        """
    )
    extension = cursor.fetchone()
    if extension is None:
        raise ValueError("pg_stat_statements não está instalado neste banco. Conclua a Etapa 4.")

    cursor.execute(
        sql.SQL("SELECT * FROM {} LIMIT 0").format(
            sql.Identifier(extension["extension_schema"], "pg_stat_statements")
        )
    )
    columns = {column.name for column in cursor.description}
    required = {"queryid", "query", "calls", "total_exec_time", "mean_exec_time", "rows"}
    missing = required - columns
    if missing:
        raise ValueError(
            "A view não possui os campos exigidos: " + ", ".join(sorted(missing)) + ". "
            "O coletor usa as métricas de execução das versões modernas. "
            "Versões antigas com total_time/mean_time exigem adaptação e não são "
            "convertidas silenciosamente em tempo de execução."
        )
    return extension, columns


def collect_metrics(all_selects: bool = False) -> tuple[list[dict], dict]:
    """Lê as estatísticas uma vez e calcula o indicador provisório em Python."""
    with get_connection() as connection:
        connection.read_only = True
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT current_database() AS database_name,
                       current_user AS user_name,
                       current_setting('server_version') AS server_version,
                       current_setting('pg_stat_statements.track', true) AS track
                """
            )
            metadata = cursor.fetchone()
            if metadata["database_name"] != "tcc_sql_optimizer":
                raise ValueError("O coletor deve usar o banco tcc_sql_optimizer.")
            extension, columns = inspect_extension(cursor)
            metadata.update(extension)
            if metadata["track"] not in ("top", "all"):
                raise ValueError("O rastreamento pg_stat_statements não está ativo nesta sessão.")

            if "toplevel" in columns:
                top_level_filter = sql.SQL("AND s.toplevel = TRUE")
            elif metadata["track"] == "top":
                top_level_filter = sql.SQL("")
            else:
                raise ValueError("Esta versão exige pg_stat_statements.track = top para este coletor.")

            statement = sql.SQL(
                """
                SELECT s.queryid AS query_id, s.query, s.calls,
                       s.total_exec_time, s.mean_exec_time, s.rows
                FROM {} s
                WHERE s.dbid = (
                    SELECT oid FROM pg_database WHERE datname = current_database()
                )
                  AND s.userid = (
                    SELECT oid FROM pg_roles WHERE rolname = current_user
                )
                  AND s.calls > 0
                  {}
                ORDER BY s.queryid
                """
            ).format(
                sql.Identifier(extension["extension_schema"], "pg_stat_statements"),
                top_level_filter,
            )
            cursor.execute(statement)
            records = cursor.fetchall()

    collected_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    metrics = []
    for record in records:
        if record["query_id"] is None or not matches_scope(record["query"], all_selects):
            continue
        calls = int(record["calls"])
        mean_exec_time = float(record["mean_exec_time"])
        metrics.append({
            "query_id": int(record["query_id"]),
            "query": record["query"],
            "calls": calls,
            "total_exec_time": float(record["total_exec_time"]),
            "mean_exec_time": mean_exec_time,
            "rows": int(record["rows"]),
            "impact_score": mean_exec_time * calls,
            "collected_at": collected_at,
        })

    metadata.update({
        "collected_at": collected_at,
        "candidate_count": len(records),
        "excluded_count": len(records) - len(metrics),
        "scope": "todos os SELECTs" if all_selects else "SELECTs das tabelas experimentais",
    })
    return metrics, metadata


def main() -> int:
    args = parse_arguments()
    try:
        metrics, metadata = collect_metrics(args.all_selects)
    except ValueError as exc:
        print(f"Erro de configuração: {exc}", file=sys.stderr)
        return 1
    except psycopg.Error as exc:
        message = exc.diag.message_primary or "Falha de conexão ou comunicação com o PostgreSQL."
        print(f"Erro PostgreSQL [{exc.sqlstate or 'sem SQLSTATE'}]: {message}", file=sys.stderr)
        print("Confira a conexão e a configuração da extensão na Etapa 4.", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nColeta interrompida pelo usuário.", file=sys.stderr)
        return 130

    print(f"Banco: {metadata['database_name']} | Usuário: {metadata['user_name']}")
    print(
        f"PostgreSQL: {metadata['server_version']} | "
        f"pg_stat_statements: {metadata['extension_version']}"
    )
    print(f"Coletado em (UTC): {metadata['collected_at']}")
    print(f"Escopo: {metadata['scope']}")
    print(f"Consultas selecionadas: {len(metrics)} | Entradas excluídas: {metadata['excluded_count']}")
    print(f"Execuções acumuladas das consultas selecionadas: {sum(item['calls'] for item in metrics)}")

    if not metrics:
        print(
            "Nenhuma consulta corresponde ao filtro. Execute o workload após habilitar a extensão. "
            "Use o mesmo banco e usuário do workload."
        )
        print("Nenhum arquivo de resultados foi criado ou atualizado.")
        return 2

    print("Impact score provisório = tempo médio × chamadas; equivale aproximadamente ao tempo total.")
    print_rankings(metrics, args.top)
    if not args.no_export:
        try:
            paths = export_results(metrics, args.output_dir, args.format)
        except (OSError, ValueError) as exc:
            print(f"Erro ao exportar resultados: {exc}", file=sys.stderr)
            print(
                "A exportação não foi concluída. Confira permissões e feche arquivos abertos. "
                "Cada arquivo é substituído separadamente; confira collected_at nos dois formatos. "
                "Não é necessário repetir o workload ou resetar as estatísticas.",
                file=sys.stderr,
            )
            return 1
        except KeyboardInterrupt:
            print("\nExportação interrompida; confira os arquivos antes de utilizá-los.", file=sys.stderr)
            return 130
        print(f"\nExportação concluída: {len(metrics)} consultas em cada arquivo.")
        for path in paths:
            print(f"Arquivo salvo: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
