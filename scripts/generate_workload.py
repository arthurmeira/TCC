r"""Executa manualmente as consultas definidas em sql/queries.sql.

Prévia sem conexão:
    .\.venv\Scripts\python.exe -m scripts.generate_workload --preview
Uma execução por consulta:
    .\.venv\Scripts\python.exe -m scripts.generate_workload --smoke
Carga completa:
    .\.venv\Scripts\python.exe -m scripts.generate_workload
"""

import argparse
import random
import re
import sys
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter

import psycopg
from psycopg import sql

from src.database import get_connection


QUERY_FILE = Path(__file__).resolve().parent.parent / "sql" / "queries.sql"
HEADER = re.compile(
    r"^-- name: (Q\d{2}) \| calls: ([1-9]\d*) \| title: ([^\r\n]+)\r?$",
    re.MULTILINE,
)
TABLES = ("clientes", "produtos", "pedidos", "itens_pedido", "pagamentos")


@dataclass(frozen=True)
class Query:
    name: str
    calls: int
    title: str
    statement: str


@dataclass
class ExecutionTotals:
    calls: int = 0
    rows: int = 0
    client_ms: float = 0.0


def positive_integer(value: str) -> int:
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("O valor deve ser maior que zero.")
    return number


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preview", action="store_true", help="Lista a carga sem conectar ao banco.")
    parser.add_argument("--smoke", action="store_true", help="Executa cada consulta uma única vez.")
    parser.add_argument("--seed", type=int, default=2026, help="Semente da ordem de execução.")
    parser.add_argument(
        "--timeout-seconds", type=positive_integer, default=120,
        help="Limite de statement_timeout por consulta, em segundos (padrão: 120).",
    )
    return parser.parse_args()


def load_queries(path: Path) -> list[Query]:
    """Lê o formato controlado do projeto; não é um parser SQL genérico."""
    text = path.read_text(encoding="utf-8-sig")
    headers = list(HEADER.finditer(text))
    if not headers:
        raise ValueError("Nenhuma consulta encontrada em sql/queries.sql.")

    for line in text[:headers[0].start()].splitlines():
        if line.strip() and not line.lstrip().startswith("--"):
            raise ValueError("O início de queries.sql deve conter somente comentários.")

    queries = []
    names = set()
    for index, header in enumerate(headers):
        name, calls, title = header.groups()
        if name in names:
            raise ValueError(f"Identificador repetido: {name}.")
        names.add(name)
        end = headers[index + 1].start() if index + 1 < len(headers) else len(text)
        block = text[header.end():end]
        statement = "\n".join(
            line for line in block.splitlines()
            if not line.lstrip().startswith("--")
        ).strip()
        if not re.match(r"SELECT\b", statement, flags=re.IGNORECASE):
            raise ValueError(f"{name}: o bloco deve começar com SELECT.")
        if not statement.endswith(";") or statement.count(";") != 1:
            raise ValueError(f"{name}: use um único SELECT com um ponto e vírgula final.")
        queries.append(Query(name, int(calls), title.strip(), statement))

    return queries


def show_plan(queries: list[Query], smoke: bool, seed: int) -> None:
    print(f"Modo: {'uma execução por consulta' if smoke else 'carga completa'} | seed={seed}")
    for query in queries:
        count = 1 if smoke else query.calls
        print(f"{query.name}: {count:>3} execuções | {query.title}")
    total = sum(1 if smoke else query.calls for query in queries)
    print(f"Total: {len(queries)} consultas diferentes | {total} execuções", flush=True)


def prepare_session(connection: psycopg.Connection, timeout_seconds: int) -> None:
    """Configura apenas esta sessão e confere o banco e a presença dos dados."""
    connection.autocommit = True
    connection.prepare_threshold = None
    with connection.cursor() as cursor:
        cursor.execute("SET default_transaction_read_only = on")
        cursor.execute(
            "SELECT set_config('statement_timeout', %s, false)",
            (f"{timeout_seconds * 1000}ms",),
        )
        cursor.execute(
            "SELECT set_config('application_name', %s, false)",
            ("tcc_generate_workload",),
        )
        cursor.execute("SELECT current_database(), current_setting('transaction_read_only')")
        database_name, read_only = cursor.fetchone()
        if database_name != "tcc_sql_optimizer" or read_only != "on":
            raise ValueError("A sessão deve usar tcc_sql_optimizer em modo somente leitura.")

        for table in TABLES:
            cursor.execute(
                sql.SQL("SELECT EXISTS (SELECT 1 FROM {} LIMIT 1)").format(
                    sql.Identifier("public", table)
                )
            )
            if not cursor.fetchone()[0]:
                raise ValueError(f"A tabela public.{table} está vazia. Valide a carga de dados.")


def execute_query(connection: psycopg.Connection, query: Query) -> tuple[int, float]:
    """Consome todas as linhas sem manter o resultado completo em memória."""
    started = perf_counter()
    row_count = 0
    with connection.cursor() as cursor:
        with closing(cursor.stream(query.statement)) as records:
            for _ in records:
                row_count += 1
    return row_count, (perf_counter() - started) * 1000


def show_summary(queries: list[Query], totals: dict[str, ExecutionTotals]) -> None:
    print("\nResumo das execuções concluídas (tempos medidos pelo cliente Python):")
    for query in queries:
        item = totals[query.name]
        average_ms = item.client_ms / item.calls if item.calls else 0.0
        print(
            f"{query.name} | calls={item.calls} | rows={item.rows:,} | "
            f"total_cliente_ms={item.client_ms:.2f} | media_cliente_ms={average_ms:.2f}"
        )
    print("Esses tempos incluem transferência e consumo das linhas; não são métricas do pg_stat_statements.")


def run_workload(queries: list[Query], args: argparse.Namespace) -> None:
    schedule = [query for query in queries for _ in range(1 if args.smoke else query.calls)]
    random.Random(args.seed).shuffle(schedule)
    totals = {query.name: ExecutionTotals() for query in queries}
    started = perf_counter()
    try:
        with get_connection() as connection:
            prepare_session(connection, args.timeout_seconds)
            for position, query in enumerate(schedule, start=1):
                print(
                    f"[{position}/{len(schedule)}] {query.name}: {query.title} — executando...",
                    flush=True,
                )
                rows, elapsed_ms = execute_query(connection, query)
                totals[query.name].calls += 1
                totals[query.name].rows += rows
                totals[query.name].client_ms += elapsed_ms
                print(f"  OK | {rows:,} linhas | {elapsed_ms:.2f} ms no cliente", flush=True)
    finally:
        show_summary(queries, totals)

    print(f"\nWorkload concluído: {len(schedule)} execuções sem erro.")
    print(f"Tempo total do processo de carga: {perf_counter() - started:.1f} segundos")


def main() -> int:
    args = parse_arguments()
    try:
        queries = load_queries(QUERY_FILE)
        show_plan(queries, args.smoke, args.seed)
        if args.preview:
            print("Prévia concluída. Nenhuma conexão com o banco foi aberta.")
            return 0
        print(f"Limite no servidor: {args.timeout_seconds} segundos por consulta.", flush=True)
        run_workload(queries, args)
    except (OSError, ValueError) as exc:
        print(f"Erro de preparação: {exc}", file=sys.stderr)
        return 1
    except psycopg.Error as exc:
        message = exc.diag.message_primary or "Falha de conexão ou comunicação com o PostgreSQL."
        print(f"Erro PostgreSQL [{exc.sqlstate or 'sem SQLSTATE'}]: {message}", file=sys.stderr)
        print(
            "Workload interrompido. As execuções anteriores podem ter gerado estatísticas. "
            "Envie o erro antes de repetir o experimento.",
            file=sys.stderr,
        )
        return 1
    except KeyboardInterrupt:
        print("\nWorkload interrompido pelo usuário; a execução ficou incompleta.", file=sys.stderr)
        return 130
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
