r"""Gera dados sintéticos e carrega tabelas vazias com COPY.

Execução manual na raiz do projeto:
    .\.venv\Scripts\python.exe -m scripts.populate_database
"""

import argparse
import random
import sys
from collections.abc import Iterable
from datetime import datetime, timedelta
from decimal import Decimal
from itertools import batched
from time import perf_counter

import psycopg
from psycopg import sql

from src.database import get_connection


COLUMNS = {
    "clientes": (
        "id", "nome", "email", "cidade", "estado", "data_cadastro", "ativo",
    ),
    "produtos": (
        "id", "nome", "categoria", "preco", "estoque", "ativo",
    ),
    "pedidos": ("id", "cliente_id", "data_pedido", "status", "valor_total"),
    "itens_pedido": (
        "id", "pedido_id", "produto_id", "quantidade", "valor_unitario",
    ),
    "pagamentos": (
        "id", "pedido_id", "data_pagamento", "forma_pagamento", "valor", "status",
    ),
}

CITIES = (
    ("São Paulo", "SP"), ("Rio de Janeiro", "RJ"),
    ("Belo Horizonte", "MG"), ("Curitiba", "PR"),
    ("Porto Alegre", "RS"), ("Salvador", "BA"),
    ("Recife", "PE"), ("Fortaleza", "CE"),
    ("Brasília", "DF"), ("Manaus", "AM"),
)

# Preços mínimos e máximos em centavos.
CATEGORIES = (
    ("Eletrônicos", 5000, 500000),
    ("Informática", 3000, 800000),
    ("Casa", 1000, 100000),
    ("Vestuário", 2000, 50000),
    ("Livros", 1500, 20000),
    ("Esportes", 2500, 150000),
)


def positive_integer(value: str) -> int:
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("O valor deve ser maior que zero.")
    return number


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--clientes", type=positive_integer, default=100_000)
    parser.add_argument("--produtos", type=positive_integer, default=50_000)
    parser.add_argument("--pedidos", type=positive_integer, default=1_000_000)
    parser.add_argument("--lote", type=positive_integer, default=10_000)
    parser.add_argument("--seed", type=int, default=2026)
    return parser.parse_args()


def money(cents: int) -> Decimal:
    """Converte centavos inteiros sem usar ponto flutuante."""
    return Decimal(cents) / Decimal(100)


def random_datetime(rng: random.Random, start: datetime, end: datetime) -> datetime:
    seconds = int((end - start).total_seconds())
    return start + timedelta(seconds=rng.randrange(seconds))


def popular_id(rng: random.Random, total: int, fraction: float, chance: float) -> int:
    """Concentra uma parcela dos sorteios no primeiro grupo de IDs."""
    popular_count = max(1, int(total * fraction))
    if popular_count == total or rng.random() < chance:
        return rng.randint(1, popular_count)
    return rng.randint(popular_count + 1, total)


def customer_rows(total: int, rng: random.Random) -> Iterable[tuple]:
    for customer_id in range(1, total + 1):
        city, state = rng.choices(
            CITIES, weights=(25, 15, 10, 8, 7, 8, 7, 7, 8, 5), k=1
        )[0]
        registered_at = random_datetime(
            rng, datetime(2022, 1, 1), datetime(2024, 1, 1)
        )
        yield (
            customer_id, f"Cliente {customer_id:06d}",
            f"cliente{customer_id}@example.com", city, state,
            registered_at, rng.random() < 0.95,
        )


def product_rows(total: int, rng: random.Random, prices: list[int]) -> Iterable[tuple]:
    for product_id in range(1, total + 1):
        category, minimum, maximum = rng.choice(CATEGORIES)
        price = rng.randint(minimum, maximum)
        prices[product_id] = price
        stock = 0 if rng.random() < 0.08 else rng.randint(1, 500)
        yield (
            product_id, f"Produto {product_id:05d}", category,
            money(price), stock, rng.random() < 0.97,
        )


def copy_rows(cursor: psycopg.Cursor, table: str, rows: Iterable[tuple]) -> None:
    statement = sql.SQL("COPY {} ({}) FROM STDIN").format(
        sql.Identifier("public", table),
        sql.SQL(", ").join(sql.Identifier(column) for column in COLUMNS[table]),
    )
    with cursor.copy(statement) as copy:
        for row in rows:
            copy.write_row(row)


def load_catalog(
    cursor: psycopg.Cursor, table: str, rows: Iterable[tuple], total: int, batch_size: int
) -> None:
    loaded = 0
    for batch in batched(rows, batch_size):
        copy_rows(cursor, table, batch)
        loaded += len(batch)
        print(f"{table}: {loaded:,}/{total:,} enviados", flush=True)


def payment_status(rng: random.Random, order_status: str) -> str:
    if order_status == "pendente":
        return rng.choices(("pendente", "recusado"), weights=(80, 20), k=1)[0]
    if order_status == "cancelado":
        return rng.choices(("estornado", "recusado"), weights=(60, 40), k=1)[0]
    return "aprovado"


def make_order_batch(
    first_id: int, stop_id: int, first_item_id: int,
    customer_count: int, prices: list[int], rng: random.Random,
) -> tuple[list, list, list]:
    orders, items, payments = [], [], []
    item_id = first_item_id

    for order_id in range(first_id, stop_id):
        customer_id = popular_id(rng, customer_count, 0.20, 0.80)
        year = rng.choices((2024, 2025, 2026), weights=(20, 30, 50), k=1)[0]
        end = datetime(2026, 9, 1) if year == 2026 else datetime(year + 1, 1, 1)
        ordered_at = random_datetime(rng, datetime(year, 1, 1), end)
        status = rng.choices(
            ("pendente", "pago", "enviado", "entregue", "cancelado"),
            weights=(12, 13, 20, 48, 7), k=1,
        )[0]
        total_cents = 0

        for _ in range(rng.randint(2, 3)):
            product_id = popular_id(rng, len(prices) - 1, 0.10, 0.70)
            quantity = rng.choices((1, 2, 3, 4, 5), weights=(60, 25, 10, 3, 2), k=1)[0]
            percentage = rng.choices((100, 95, 90, 85), weights=(65, 20, 10, 5), k=1)[0]
            unit_cents = (prices[product_id] * percentage + 50) // 100
            total_cents += quantity * unit_cents
            items.append((item_id, order_id, product_id, quantity, money(unit_cents)))
            item_id += 1

        total = money(total_cents)
        orders.append((order_id, customer_id, ordered_at, status, total))
        paid_status = payment_status(rng, status)
        paid_at = None
        if paid_status in ("aprovado", "estornado"):
            paid_at = ordered_at + timedelta(minutes=rng.randint(1, 2880))
        method = rng.choices(
            ("pix", "cartao_credito", "cartao_debito", "boleto"),
            weights=(45, 35, 10, 10), k=1,
        )[0]
        payments.append((order_id, order_id, paid_at, method, total, paid_status))

    return orders, items, payments


def require_empty_tables(cursor: psycopg.Cursor) -> None:
    cursor.execute("SELECT current_database()")
    if cursor.fetchone()[0] != "tcc_sql_optimizer":
        raise ValueError("A conexão deve apontar para tcc_sql_optimizer.")

    # Impede cargas simultâneas e outras escritas enquanto a transação estiver aberta.
    tables = sql.SQL(", ").join(sql.Identifier("public", table) for table in COLUMNS)
    cursor.execute(
        sql.SQL("LOCK TABLE {} IN SHARE ROW EXCLUSIVE MODE NOWAIT").format(tables)
    )
    for table in COLUMNS:
        cursor.execute(
            sql.SQL("SELECT EXISTS (SELECT 1 FROM {} LIMIT 1)").format(
                sql.Identifier("public", table)
            )
        )
        if cursor.fetchone()[0]:
            raise ValueError(
                f"A tabela public.{table} já contém dados. "
                "Carga cancelada sem apagar ou acrescentar registros."
            )


def populate(args: argparse.Namespace) -> dict[str, int]:
    rng = random.Random(args.seed)
    prices = [0] * (args.produtos + 1)
    counts = {
        "clientes": args.clientes, "produtos": args.produtos,
        "pedidos": args.pedidos, "itens_pedido": 0, "pagamentos": args.pedidos,
    }

    with get_connection() as connection:
        with connection.cursor() as cursor:
            require_empty_tables(cursor)
            print("Tabelas vazias. Iniciando carga; o COMMIT ocorrerá ao final.", flush=True)
            load_catalog(
                cursor, "clientes", customer_rows(args.clientes, rng),
                args.clientes, args.lote,
            )
            load_catalog(
                cursor, "produtos", product_rows(args.produtos, rng, prices),
                args.produtos, args.lote,
            )

            for first_id in range(1, args.pedidos + 1, args.lote):
                stop_id = min(first_id + args.lote, args.pedidos + 1)
                orders, items, payments = make_order_batch(
                    first_id, stop_id, counts["itens_pedido"] + 1,
                    args.clientes, prices, rng,
                )
                copy_rows(cursor, "pedidos", orders)
                copy_rows(cursor, "itens_pedido", items)
                copy_rows(cursor, "pagamentos", payments)
                counts["itens_pedido"] += len(items)
                loaded = stop_id - 1
                print(
                    f"pedidos: {loaded:,}/{args.pedidos:,} "
                    f"({100 * loaded / args.pedidos:.1f}%) | "
                    f"itens: {counts['itens_pedido']:,} | pagamentos: {loaded:,}",
                    flush=True,
                )

            print("Atualizando estatísticas das cinco tabelas (ANALYZE)...", flush=True)
            for table in COLUMNS:
                cursor.execute(
                    sql.SQL("ANALYZE {}").format(sql.Identifier("public", table))
                )

            for table, count in counts.items():
                cursor.execute(
                    "SELECT setval(pg_get_serial_sequence(%s, 'id'), %s, true)",
                    (f"public.{table}", count),
                )
            print("Confirmando a transação...", flush=True)

    return counts


def main() -> int:
    args = parse_arguments()
    started = perf_counter()
    print(f"Python: {sys.version.split()[0]} | Psycopg: {psycopg.__version__}", flush=True)
    print(
        f"Carga: {args.clientes:,} clientes, {args.produtos:,} produtos, "
        f"{args.pedidos:,} pedidos | lote={args.lote} | seed={args.seed}",
        flush=True,
    )
    try:
        counts = populate(args)
    except ValueError as exc:
        print(f"Erro de configuração ou preparação: {exc}", file=sys.stderr)
        return 1
    except psycopg.Error as exc:
        message = exc.diag.message_primary or "Falha de conexão ou comunicação com o PostgreSQL."
        print(f"Erro PostgreSQL [{exc.sqlstate or 'sem SQLSTATE'}]: {message}", file=sys.stderr)
        print("Carga não confirmada pelo programa. Envie o erro antes de repetir.", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nExecução interrompida. Confira o estado da carga antes de repetir.", file=sys.stderr)
        return 130

    print("\nCarga concluída e COMMIT confirmado.")
    for table, count in counts.items():
        print(f"{table}: {count:,}")
    print(f"Tempo total: {perf_counter() - started:.1f} segundos")
    print("Valide no DBeaver com sql/validate_population.sql.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
