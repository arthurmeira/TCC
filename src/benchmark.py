"""Medição repetida de planos reais e assinaturas de todos os resultados."""
from __future__ import annotations

import hashlib
import json
import random
import statistics
import threading
import uuid
import psycopg
from datetime import datetime, timezone
from time import perf_counter

from src.database import get_connection
from src.execution_logs import save_experiment
from src.optimization import executable_select, parse_select

RUN_LOCK = threading.Lock()
MAX_ROWS = 3_000_000


def result_signature(connection, query, ordered):
    count, digest = 0, 0
    sequence = hashlib.sha256()
    with connection.cursor() as cursor:
        for row in cursor.stream(query, size=2000):
            count += 1
            if count > MAX_ROWS:
                raise ValueError("O resultado excedeu o limite de 3 milhões de linhas do teste.")
            encoded = json.dumps(row,default=str,ensure_ascii=False,separators=(",", ":")).encode()
            hashed = hashlib.sha256(encoded).digest()
            digest = (digest + int.from_bytes(hashed, "big")) % (1 << 256)
            sequence.update(hashed)
        columns = [(col.name, col.type_code) for col in cursor.description or ()]
    return dict(rows=count,columns=columns,signature=sequence.hexdigest() if ordered else f"{digest:064x}")


def benchmark(original, alternative, calls=10, query_id=None):
    if type(calls) is not int or not 3 <= calls <= 50:
        raise ValueError("Escolha de 3 a 50 repetições por versão.")
    original, alternative = executable_select(original), executable_select(alternative)
    if original == alternative:
        raise ValueError("As versões são iguais. Informe uma alteração para comparar.")
    if not RUN_LOCK.acquire(blocking=False):
        raise ValueError("Já existe um teste em andamento. Aguarde sua conclusão.")
    try:
        started = perf_counter()
        measurements = {"original": [], "alternative": []}
        plans, signatures = {}, {}
        queries = dict(original=original,alternative=alternative)
        with get_connection() as connection:
            connection.read_only = True
            connection.isolation_level = psycopg.IsolationLevel.REPEATABLE_READ
            with connection.cursor() as cursor:
                cursor.execute("SET LOCAL statement_timeout='30s'")
                cursor.execute("SET LOCAL lock_timeout='3s'")
                cursor.execute("SET LOCAL search_path=pg_catalog,public")
            for label, query in queries.items():
                signatures[label] = result_signature(connection,query,bool(parse_select(query).sortClause))
            equivalent = signatures["original"] == signatures["alternative"]
            if not equivalent:
                raise ValueError("As assinaturas dos resultados ou as colunas diferem. A alteração não foi validada; nenhum ganho será apresentado.")
            # Aquecimento explícito; não entra nos tempos publicados.
            schedule = ["original", "alternative"] + ["original"] * calls + ["alternative"] * calls
            tail = schedule[2:]; random.Random(2026).shuffle(tail); schedule[2:] = tail
            for position, label in enumerate(schedule):
                if perf_counter() - started > 180:
                    raise ValueError("O experimento excedeu 3 minutos. Reduza o número de repetições.")
                with connection.cursor() as cursor:
                    cursor.execute("EXPLAIN (ANALYZE TRUE, BUFFERS TRUE, TIMING FALSE, SUMMARY TRUE, FORMAT JSON) " + queries[label])
                    plan = cursor.fetchone()[0][0]
                plans[label] = plan
                if position >= 2:
                    measurements[label].append(float(plan["Execution Time"]))
        summary = {}
        for label, values in measurements.items():
            summary[label] = dict(calls=len(values),mean_ms=statistics.mean(values),median_ms=statistics.median(values),
                                  min_ms=min(values),max_ms=max(values),stdev_ms=statistics.stdev(values),samples_ms=values,
                                  rows=signatures[label]["rows"],root_node=plans[label]["Plan"]["Node Type"],plan=plans[label])
        before, after = summary["original"]["median_ms"],summary["alternative"]["median_ms"]
        reduction = (before-after)/before*100 if before > 0 else None
        verdict = "Tempo menor nesta rodada" if reduction is not None and reduction > 0 else "Tempo maior nesta rodada" if reduction is not None and reduction < 0 else "Sem redução nesta rodada"
        report = dict(id=uuid.uuid4().hex,created_at=datetime.now(timezone.utc).isoformat(),query_id=query_id,
                      original_sql=original,alternative_sql=alternative,metrics=summary,reduction_pct=reduction,verdict=verdict,
                      equivalent=True,result_check="SHA-256 por linha, contagem e colunas; multiconjunto para consultas sem ORDER BY, sequência quando há ORDER BY. Mesma fotografia transacional dos dados.",
                      signatures=signatures,method="EXPLAIN ANALYZE, BUFFERS, TIMING FALSE; 1 aquecimento por versão e repetições intercaladas, semente 2026. Tempos do servidor, incluindo instrumentação do EXPLAIN. Comparação descritiva da rodada, sem teste de significância.",
                      elapsed_seconds=perf_counter()-started)
        save_experiment(report)
        return report
    finally:
        RUN_LOCK.release()
