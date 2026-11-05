"""Produz consultas no banco copiado e lê seus registros reais no log do servidor."""
import re
import time
import uuid

from scripts.generate_workload import load_queries, QUERY_FILE
from src.database import get_connection
from src.execution_logs import import_logs, MAX_BYTES
from src.optimization import executable_select
from src.benchmark import RUN_LOCK

CAPTURE_LOCK = RUN_LOCK


def capture_workload(calls=2):
    if type(calls) is not int or not 1 <= calls <= 5:
        raise ValueError("Use de 1 a 5 chamadas por exemplo.")
    if not CAPTURE_LOCK.acquire(blocking=False):
        raise ValueError("Uma coleta já está em andamento.")
    try:
        token = "tcc_logs_" + uuid.uuid4().hex
        with get_connection() as connection:
            connection.read_only = True
            with connection.cursor() as cursor:
                cursor.execute("SELECT current_database(), current_setting('logging_collector'), pg_current_logfile()")
                database, collector, first = cursor.fetchone()
                if database != "tcc_sql_optimizer_logs":
                    raise ValueError("A coleta só pode executar no banco copiado tcc_sql_optimizer_logs.")
                if collector != "on" or not first or not first.endswith('.log'):
                    raise ValueError("A coleta local requer logging_collector ligado e saída stderr em .log. Você também pode importar CSV/JSON do PostgreSQL.")
                cursor.execute("SELECT (pg_stat_file(%s)).size", (first,)); offset = cursor.fetchone()[0]
                cursor.execute("SET LOCAL statement_timeout='30s'")
                cursor.execute("SET LOCAL lock_timeout='3s'")
                cursor.execute("SET LOCAL search_path=pg_catalog,public")
                # Somente esta sessão: não altera postgresql.conf nem o banco original.
                cursor.execute("SET LOCAL lc_messages='C'")
                cursor.execute("SET LOCAL log_min_duration_statement=0")
            completed = 0
            for query in load_queries(QUERY_FILE):
                query_text = executable_select(query.statement)
                for _ in range(calls):
                    with connection.cursor() as cursor:
                        for row in cursor.stream(f"/* {token} */ {query_text}",size=2000):
                            pass
                    completed += 1
        # O processo coletor escreve de maneira assíncrona. Aguarda a última duração.
        text = ""
        for attempt in range(20):
            with get_connection() as connection:
                connection.read_only = True
                with connection.cursor() as cursor:
                    cursor.execute("SELECT pg_current_logfile()")
                    current = cursor.fetchone()[0]
                    paths = [(first,offset)] + ([(current,0)] if current != first else [])
                    text = ""
                    for path, start in paths:
                        cursor.execute("SELECT (pg_stat_file(%s)).size", (path,)); size = cursor.fetchone()[0]
                        if size-start > MAX_BYTES:
                            raise ValueError("O trecho do log excedeu 20 MB. Importe um recorte manualmente.")
                        cursor.execute("SELECT pg_read_file(%s,%s,%s)",(path,start,max(0,size-start)))
                        text += cursor.fetchone()[0]
            records = re.split(r"(?m)(?=^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2})",text)
            selected = [r for r in records if token in r and re.search(r"duration:.*(?:statement:|execute\s+[^:]+:)",r)]
            if len(selected) >= completed:
                break
            time.sleep(.25)
        if len(selected) != completed:
            raise ValueError(f"O servidor executou {completed} consultas, mas foram encontrados {len(selected)} registros completos. Confira o log do PostgreSQL antes de repetir.")
        result = import_logs("".join(selected),token+'.log',database_name=database)
        return {**result,"database":database,"executed":completed,"source":"Log real do servidor PostgreSQL; sessão identificada exclusivamente para esta coleta"}
    finally:
        CAPTURE_LOCK.release()
