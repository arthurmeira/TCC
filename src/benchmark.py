"""Medição repetida de planos reais e assinaturas de todos os resultados."""
from __future__ import annotations

import hashlib
import json
import random
import statistics
import threading
import uuid
import psycopg
from pglast import ast
from pglast.stream import RawStream
from datetime import datetime, timezone
from time import perf_counter

from src.database import get_connection
from src.execution_logs import save_experiment, log_origin
from src.optimization import executable_select, parse_select
from src.measurement_resources import resource_sample, summarize_resources

RUN_LOCK = threading.Lock()
MAX_ROWS = 3_000_000


def ordering_columns(query):
    """Resolve ORDER BY nas colunas projetadas; casos ambíguos ficam estritos."""
    statement = parse_select(query)
    targets = statement.targetList or ()
    if any(isinstance(t.val, ast.ColumnRef) and
           any(isinstance(f, ast.A_Star) for f in t.val.fields) for t in targets):
        return None
    indexes = []
    for sort in statement.sortClause or ():
        node = sort.node
        if isinstance(node, ast.A_Const) and isinstance(node.val, ast.Integer):
            matches = [node.val.ival - 1] if 1 <= node.val.ival <= len(targets) else []
        else:
            matches = []
            if isinstance(node, ast.ColumnRef) and len(node.fields) == 1 and isinstance(node.fields[0], ast.String):
                matches = [i for i, t in enumerate(targets) if t.name == node.fields[0].sval]
            if not matches:
                matches = [i for i, t in enumerate(targets) if RawStream()(t.val) == RawStream()(node)]
        if len(matches) != 1:
            return None
        indexes.append(matches[0])
    return indexes or None


def result_signature(connection, query, ordered):
    count, digest = 0, 0
    sequence = hashlib.sha256()
    indexes = ordering_columns(query) if ordered else None
    group_key, group_count, group_digest = None, 0, 0
    def finish_group():
        sequence.update(f"{group_count}:{group_digest:064x};".encode())
    with connection.cursor() as cursor:
        for row in cursor.stream(query, size=2000):
            count += 1
            if count > MAX_ROWS:
                raise ValueError("O resultado excedeu o limite de 3 milhões de linhas do teste.")
            encoded = json.dumps(row,default=str,ensure_ascii=False,separators=(",", ":")).encode()
            hashed = hashlib.sha256(encoded).digest()
            digest = (digest + int.from_bytes(hashed, "big")) % (1 << 256)
            if indexes is not None:
                key = tuple(row[i] for i in indexes)
                if group_count and key != group_key:
                    finish_group()
                    group_count, group_digest = 0, 0
                group_key = key
                group_count += 1
                group_digest = (group_digest + int.from_bytes(hashed, 'big')) % (1 << 256)
            else:
                sequence.update(hashed)
        columns = [(col.name, col.type_code) for col in cursor.description or ()]
    if group_count:
        finish_group()
    return dict(rows=count,columns=columns,signature=sequence.hexdigest() if ordered else f"{digest:064x}")


def benchmark(original, alternative, calls=10, query_id=None, *, selection_reason=None, source_event_id=None, rule=None):
    if type(calls) is not int or not 3 <= calls <= 50:
        raise ValueError("Escolha de 3 a 50 repetições por versão.")
    original, alternative = executable_select(original), executable_select(alternative)
    if original == alternative:
        raise ValueError("As versões são iguais. Informe uma alteração para comparar.")
    origin = dict(kind='manual_or_preset', note='SQL fornecido diretamente; sem vínculo comprovado com log.')
    if query_id:
        if not isinstance(query_id, str):
            raise ValueError('Identificador de consulta inválido.')
        if query_id.startswith('pg:'):
            origin = dict(kind='pg_stat_statements', statement_id=query_id,
                          note='Consulta selecionada nas estatísticas agregadas; não é um evento individual de log.')
        else:
            origin = log_origin(query_id, source_event_id, selection_reason, original)
    if not RUN_LOCK.acquire(blocking=False):
        raise ValueError("Já existe um teste em andamento. Aguarde sua conclusão.")
    try:
        started = perf_counter()
        measurements = {"original": [], "alternative": []}
        resources = {"original": [], "alternative": []}
        plans, signatures = {}, {}
        queries = dict(original=original,alternative=alternative)
        with get_connection() as connection:
            connection.read_only = True
            connection.isolation_level = psycopg.IsolationLevel.REPEATABLE_READ
            with connection.cursor() as cursor:
                cursor.execute("SET LOCAL statement_timeout='30s'")
                cursor.execute("SET LOCAL lock_timeout='3s'")
                cursor.execute("SET LOCAL search_path=pg_catalog,public")
                cursor.execute("SELECT current_database(), current_setting('server_version')")
                database_name, server_version = cursor.fetchone()
            for label, query in queries.items():
                signatures[label] = result_signature(connection,query,bool(parse_select(query).sortClause))
            equivalent = signatures["original"] == signatures["alternative"]
            if not equivalent:
                save_experiment(dict(id=uuid.uuid4().hex, created_at=datetime.now(timezone.utc).isoformat(),
                    query_id=query_id, original_sql=original, alternative_sql=alternative,
                    status='not_equivalent', verdict='Resultados diferentes', equivalent=False,
                    reduction_pct=None, metrics={}, signatures=signatures, rule=rule,
                    environment=dict(database=database_name, postgresql_version=server_version),
                    reason='As assinaturas ou colunas diferem; a comparação de desempenho não foi realizada.'))
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
                    resources[label].append(resource_sample(plan))
        summary = {}
        for label, values in measurements.items():
            summary[label] = dict(calls=len(values),mean_ms=statistics.mean(values),median_ms=statistics.median(values),
                                  min_ms=min(values),max_ms=max(values),stdev_ms=statistics.stdev(values),samples_ms=values,
                                  rows=signatures[label]["rows"],root_node=plans[label]["Plan"]["Node Type"],plan=plans[label],
                                  resources=summarize_resources(resources[label]))
        before, after = summary["original"]["median_ms"],summary["alternative"]["median_ms"]
        reduction = (before-after)/before*100 if before > 0 else None
        verdict = "Tempo menor nesta rodada" if reduction is not None and reduction > 0 else "Tempo maior nesta rodada" if reduction is not None and reduction < 0 else "Sem redução nesta rodada"
        report = dict(id=uuid.uuid4().hex,created_at=datetime.now(timezone.utc).isoformat(),query_id=query_id,
                      original_sql=original,alternative_sql=alternative,metrics=summary,reduction_pct=reduction,verdict=verdict,origin=origin,
                      equivalent=True,result_check="SHA-256 por linha, contagem e colunas; multiconjunto sem ORDER BY. Com ORDER BY projetado, sequência de grupos empatados, preservando duplicatas dentro de cada grupo; outros casos usam sequência estrita. Mesma fotografia transacional dos dados.",
                      signatures=signatures,method="EXPLAIN ANALYZE, BUFFERS, TIMING FALSE; 1 aquecimento por versão e repetições intercaladas, semente 2026. Tempos do servidor, incluindo instrumentação do EXPLAIN. Comparação descritiva da rodada, sem teste de significância.",
                      elapsed_seconds=perf_counter()-started,
                      rule=rule if isinstance(rule, str) and len(rule) <= 200 else None,
                      environment=dict(database=database_name, postgresql_version=server_version))
        report['resource_method'] = (
            'Blocos: contadores da raiz do plano de cada repetição, sem somar os filhos. '
            'Shared hits são acessos atendidos pelo cache do PostgreSQL; shared reads podem vir do cache do sistema operacional, não comprovam leituras físicas do disco. '
            'Linhas: saída da consulta e linhas por operação (Actual Rows × Actual Loops); não somar operações como linhas únicas. '
            'Métricas do plano exibem medianas das repetições medidas; amostras e operações de cada plano estão no JSON. '
            'Os tempos de execução do servidor são medidos separadamente e apresentados com mediana, média, mínimo e máximo.')
        save_experiment(report)
        return report
    finally:
        RUN_LOCK.release()
