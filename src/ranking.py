"""Ordenação e apresentação das métricas de execução coletadas."""


RANKINGS = (
    ("total_exec_time", "TOP CONSULTAS POR TEMPO TOTAL"),
    ("mean_exec_time", "TOP CONSULTAS POR TEMPO MÉDIO"),
    ("calls", "TOP CONSULTAS POR QUANTIDADE DE EXECUÇÕES"),
)


def rank_queries(metrics: list[dict], criterion: str, limit: int = 5) -> list[dict]:
    """Ordena numericamente em ordem decrescente, sem alterar a lista original."""
    if criterion not in {field for field, _ in RANKINGS}:
        raise ValueError(f"Critério de ranking desconhecido: {criterion}.")
    if limit <= 0:
        raise ValueError("A quantidade de posições deve ser maior que zero.")

    return sorted(
        metrics,
        key=lambda item: (-item[criterion], item["query_id"]),
    )[:limit]


def print_rankings(metrics: list[dict], limit: int = 5) -> None:
    """Exibe três rankings calculados sobre a mesma coleta."""
    for criterion, title in RANKINGS:
        print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")
        for position, item in enumerate(rank_queries(metrics, criterion, limit), start=1):
            print(f"\n{position}. Query ID: {item['query_id']}")
            print(f"Execuções: {item['calls']:,}")
            print(f"Tempo total: {item['total_exec_time']:.2f} ms")
            print(f"Tempo médio: {item['mean_exec_time']:.2f} ms")
            print(f"Linhas retornadas (acumuladas): {item['rows']:,}")
            print(f"Impact score: {item['impact_score']:.2f} ms")
            print(f"SQL:\n{item['query']}")
