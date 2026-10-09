"""Mede duas consultas equivalentes depois da análise preventiva."""

from __future__ import annotations

import argparse
import random
import sys
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Any

import psycopg

from src.analyzer import explain_query, fetch_history, load_select
from src.database import get_connection


@dataclass
class ClientMeasurement:
    calls: int = 0
    rows: int = 0
    total_ms: float = 0.0

    @property
    def mean_ms(self) -> float:
        return self.total_ms / self.calls if self.calls else 0.0


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Executa duas consultas equivalentes e compara deltas do "
            "pg_stat_statements."
        )
    )
    parser.add_argument("--original", type=Path, required=True)
    parser.add_argument("--alternative", type=Path, required=True)
    parser.add_argument(
        "--calls",
        type=int,
        default=100,
        help="Execuções de cada consulta (padrão: 100).",
    )
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--timeout-seconds", type=int, default=30)
    return parser.parse_args()


def identify_queries(
    original_query: str,
    alternative_query: str,
    timeout_seconds: int,
) -> tuple[int, int, dict[str, Any] | None, dict[str, Any] | None]:
    """Obtém Query IDs e métricas acumuladas antes do teste."""
    with get_connection() as connection:
        connection.read_only = True
        original_document = explain_query(
            connection, original_query, timeout_seconds
        )
        alternative_document = explain_query(
            connection, alternative_query, timeout_seconds
        )
        original_id = original_document.get("Query Identifier")
        alternative_id = alternative_document.get("Query Identifier")
        if original_id is None or alternative_id is None:
            raise ValueError("O PostgreSQL não retornou os Query IDs necessários.")
        original_history = fetch_history(connection, int(original_id))
        alternative_history = fetch_history(connection, int(alternative_id))

    return (
        int(original_id),
        int(alternative_id),
        original_history,
        alternative_history,
    )


def run_interleaved_workload(
    original_query: str,
    alternative_query: str,
    calls: int,
    seed: int,
    timeout_seconds: int,
) -> tuple[dict[str, ClientMeasurement], bool]:
    """Executa a mesma quantidade em ordem intercalada e aleatória."""
    schedule = ["original"] * calls + ["alternative"] * calls
    random.Random(seed).shuffle(schedule)
    queries = {
        "original": original_query,
        "alternative": alternative_query,
    }
    measurements = {
        "original": ClientMeasurement(),
        "alternative": ClientMeasurement(),
    }
    first_results: dict[str, list[tuple[Any, ...]]] = {}
    progress_interval = max(1, len(schedule) // 10)

    with get_connection() as connection:
        connection.read_only = True
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT set_config('statement_timeout', %s, true)",
                (f"{timeout_seconds}s",),
            )
            for position, label in enumerate(schedule, start=1):
                started_at = perf_counter()
                cursor.execute(queries[label])
                rows = cursor.fetchall()
                elapsed_ms = (perf_counter() - started_at) * 1000

                measurement = measurements[label]
                measurement.calls += 1
                measurement.rows += len(rows)
                measurement.total_ms += elapsed_ms
                first_results.setdefault(label, rows)

                if position % progress_interval == 0 or position == len(schedule):
                    print(f"Progresso: {position}/{len(schedule)} execuções")

    equivalent_results = (
        first_results.get("original") == first_results.get("alternative")
    )
    return measurements, equivalent_results


def collect_after(
    original_id: int,
    alternative_id: int,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """Obtém métricas acumuladas em uma nova transação."""
    with get_connection() as connection:
        connection.read_only = True
        return (
            fetch_history(connection, original_id),
            fetch_history(connection, alternative_id),
        )


def metrics_delta(
    before: dict[str, Any] | None,
    after: dict[str, Any] | None,
) -> dict[str, float]:
    before = before or {}
    after = after or {}
    calls = int(after.get("calls", 0)) - int(before.get("calls", 0))
    total_ms = float(after.get("total_exec_time", 0)) - float(
        before.get("total_exec_time", 0)
    )
    rows = int(after.get("rows", 0)) - int(before.get("rows", 0))
    return {
        "calls": calls,
        "total_ms": total_ms,
        "mean_ms": total_ms / calls if calls else 0.0,
        "rows": rows,
    }


def display_results(
    measurements: dict[str, ClientMeasurement],
    original_delta: dict[str, float],
    alternative_delta: dict[str, float],
    equivalent_results: bool,
) -> None:
    print("\n" + "=" * 72)
    print("VALIDAÇÃO CONTROLADA DA RECOMENDAÇÃO")
    print("=" * 72)
    print(
        "Primeiros resultados equivalentes: "
        + ("sim" if equivalent_results else "NÃO")
    )

    print("\nMétricas do servidor — deltas do pg_stat_statements:")
    for label, delta in (
        ("Original", original_delta),
        ("Alternativa", alternative_delta),
    ):
        print(
            f"- {label}: calls={int(delta['calls'])} | "
            f"rows={int(delta['rows'])} | total={delta['total_ms']:.2f} ms | "
            f"média={delta['mean_ms']:.4f} ms"
        )

    print("\nTempos observados pelo cliente Python:")
    for label, key in (("Original", "original"), ("Alternativa", "alternative")):
        item = measurements[key]
        print(
            f"- {label}: calls={item.calls} | rows={item.rows} | "
            f"total={item.total_ms:.2f} ms | média={item.mean_ms:.4f} ms"
        )

    if original_delta["mean_ms"] > 0:
        change = (
            (original_delta["mean_ms"] - alternative_delta["mean_ms"])
            / original_delta["mean_ms"]
            * 100
        )
        if change >= 0:
            print(f"\nRedução do tempo médio no servidor: {change:.2f}%")
        else:
            print(f"\nAumento do tempo médio no servidor: {abs(change):.2f}%")

    print(
        "As métricas representam somente esta rodada e podem variar por cache, "
        "concorrência e condições da máquina."
    )


def main() -> int:
    args = parse_arguments()
    if not 1 <= args.calls <= 10_000:
        print("Erro: --calls deve estar entre 1 e 10000.", file=sys.stderr)
        return 1
    if not 1 <= args.timeout_seconds <= 600:
        print("Erro: --timeout-seconds deve estar entre 1 e 600.", file=sys.stderr)
        return 1

    try:
        original_query = load_select(args.original)
        alternative_query = load_select(args.alternative)
        (
            original_id,
            alternative_id,
            original_before,
            alternative_before,
        ) = identify_queries(
            original_query,
            alternative_query,
            args.timeout_seconds,
        )

        print("As consultas serão executadas somente para validar a recomendação.")
        print(f"Execuções por consulta: {args.calls} | seed={args.seed}")
        measurements, equivalent_results = run_interleaved_workload(
            original_query,
            alternative_query,
            args.calls,
            args.seed,
            args.timeout_seconds,
        )
        original_after, alternative_after = collect_after(
            original_id, alternative_id
        )
        original_delta = metrics_delta(original_before, original_after)
        alternative_delta = metrics_delta(alternative_before, alternative_after)
        display_results(
            measurements,
            original_delta,
            alternative_delta,
            equivalent_results,
        )
    except (OSError, ValueError) as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1
    except psycopg.Error as exc:
        print(
            "Erro durante a validação controlada: "
            f"{exc.diag.message_primary or exc}",
            file=sys.stderr,
        )
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
