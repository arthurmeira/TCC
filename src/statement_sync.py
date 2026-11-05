"""Snapshots do pg_stat_statements. Contadores agregados nunca viram eventos de log."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import math
import threading
import uuid

from pglast import ast, parse_sql
from pglast.parser import ParseError
from pglast.stream import RawStream
from pglast.visitors import Visitor
from psycopg import sql
from psycopg.rows import dict_row

from src.collector import inspect_extension
from src.database import get_connection
from src.execution_logs import connect

SYNC_LOCK = threading.Lock()
COUNTERS = ("calls", "total_exec_time", "rows", "shared_blks_hit", "shared_blks_read",
            "shared_blks_dirtied", "shared_blks_written", "local_blks_hit", "local_blks_read",
            "temp_blks_read", "temp_blks_written", "shared_blk_read_time", "shared_blk_write_time",
            "temp_blk_read_time", "temp_blk_write_time")
OPTIONAL = (*COUNTERS[3:], "min_exec_time", "max_exec_time", "stddev_exec_time", "stats_since", "minmax_stats_since")


def init_store(db):
    db.executescript("""
        CREATE TABLE IF NOT EXISTS sync_runs (
          id TEXT PRIMARY KEY, captured_at TEXT NOT NULL, context TEXT NOT NULL, summary TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS observed_statements (
          id TEXT PRIMARY KEY, source_key TEXT NOT NULL, first_seen TEXT NOT NULL,
          last_seen TEXT NOT NULL, active INTEGER NOT NULL, record TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS statement_snapshots (
          run_id TEXT NOT NULL, statement_id TEXT NOT NULL, record TEXT NOT NULL,
          PRIMARY KEY(run_id, statement_id));
    """)


class QueryShape(Visitor):
    def __init__(self):
        super().__init__()
        self.relations = []
        self.parameters = set()
        self.writes = False
    def visit_RangeVar(self, ancestors, node):
        self.relations.append((node.schemaname, node.relname))
    def visit_ParamRef(self, ancestors, node):
        self.parameters.add(node.number)
    def visit_SelectStmt(self, ancestors, node):
        if node.intoClause:
            self.writes = True
    def visit(self, ancestors, node):
        if isinstance(node, (ast.InsertStmt, ast.UpdateStmt, ast.DeleteStmt, ast.MergeStmt)):
            self.writes = True


def query_shape(query):
    tree = parse_sql(query)
    if len(tree) != 1 or not isinstance(tree[0].stmt, ast.SelectStmt):
        raise ValueError("A observação aceita SELECTs, inclusive CTEs somente de leitura.")
    shape = QueryShape(); shape(tree)
    if shape.writes:
        raise ValueError("A consulta contém uma operação de alteração.")
    return tree, shape


def in_scope(query, user_relations):
    """Exclui metadados administrativos sem exigir public. no SQL do cliente."""
    try:
        _, shape = query_shape(query)
    except (ValueError, ParseError):
        return False
    return any((schema, name) in user_relations if schema else any(n == name for _, n in user_relations)
               for schema, name in shape.relations)


def read_postgres_snapshot():
    with get_connection() as connection:
        connection.read_only = True
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute("SET LOCAL statement_timeout='15s'")
            cursor.execute("""SELECT current_database() AS database_name, current_user AS collector_user,
                (SELECT oid::text FROM pg_database WHERE datname=current_database()) AS database_id,
                current_setting('server_version') AS server_version,
                current_setting('server_version_num') AS server_version_num,
                current_setting('pg_stat_statements.track',true) AS track,
                current_setting('track_io_timing') AS track_io_timing,
                pg_postmaster_start_time()::text AS server_started_at,
                (SELECT rolsuper FROM pg_roles WHERE rolname=current_user)
                  OR pg_has_role(current_user,'pg_read_all_stats','MEMBER') AS can_read_other_users""")
            context = dict(cursor.fetchone())
            if context["database_name"] != "tcc_sql_optimizer_logs":
                raise ValueError("Atualize as consultas no banco tcc_sql_optimizer_logs desta cópia.")
            extension, columns = inspect_extension(cursor)
            context.update(extension)
            if context["track"] not in {"top", "all"}:
                raise ValueError("O pg_stat_statements não está coletando execuções. Habilite o rastreamento no PostgreSQL.")
            info = sql.Identifier(extension["extension_schema"], "pg_stat_statements_info")
            cursor.execute(sql.SQL("SELECT stats_reset::text AS stats_reset,dealloc FROM {}").format(info))
            before = dict(cursor.fetchone()); context.update(before)
            # OID do banco + endereço/porta diferenciam fontes sem usar credenciais.
            context["source_key"] = hashlib.sha256(f"{connection.info.host}:{connection.info.port}/{context['database_id']}/{context['database_name']}/{int(context['server_version_num'])//10000}".encode()).hexdigest()
            cursor.execute("""SELECT n.nspname,c.relname FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
                WHERE n.nspname NOT IN ('pg_catalog','information_schema') AND n.nspname NOT LIKE 'pg_toast%'
                AND n.nspname NOT LIKE 'pg_temp_%' AND c.relkind IN ('r','p','v','m','f')
                AND NOT EXISTS (SELECT 1 FROM pg_depend d WHERE d.classid='pg_class'::regclass
                    AND d.objid=c.oid AND d.deptype='e')""")
            relations = {(r["nspname"], r["relname"]) for r in cursor.fetchall()}
            optional = [sql.SQL("s.{} AS {}").format(sql.Identifier(k),sql.Identifier(k))
                        if k in columns else sql.SQL("NULL AS {}").format(sql.Identifier(k)) for k in OPTIONAL]
            cursor.execute(sql.SQL("""SELECT s.dbid::text AS database_id,s.userid::text AS user_id,
                pg_get_userbyid(s.userid) AS user_name,s.queryid::text AS query_id,s.query AS sql,
                s.calls,s.total_exec_time,s.mean_exec_time,s.rows,{}
                FROM {} s WHERE s.dbid=(SELECT oid FROM pg_database WHERE datname=current_database())
                AND s.calls>0 AND s.toplevel=TRUE ORDER BY s.userid,s.queryid""").format(
                    sql.SQL(",").join(optional),sql.Identifier(extension["extension_schema"],"pg_stat_statements")))
            candidates = cursor.fetchall()
            records = []
            for record in candidates:
                if not record["query_id"] or not record["sql"] or not in_scope(record["sql"], relations):
                    continue
                record = dict(record)
                for k in ("stats_since", "minmax_stats_since"):
                    if record[k] is not None:
                        record[k] = record[k].isoformat()
                record["toplevel"] = True
                record["database_name"] = context["database_name"]
                records.append(record)
            cursor.execute(sql.SQL("SELECT stats_reset::text AS stats_reset,dealloc FROM {}").format(info))
            after = cursor.fetchone()
            if after["stats_reset"] != before["stats_reset"]:
                raise ValueError("As estatísticas foram reiniciadas durante a leitura. Clique em Atualizar consultas novamente.")
            context["dealloc"] = after["dealloc"]
            context["scope"] = "SELECTs de tabelas de usuário do banco conectado, de todos os usuários visíveis; somente nível superior"
            context["excluded"] = len(candidates)-len(records)
            context["captured_at"] = datetime.now(timezone.utc).isoformat()
    return records, context


def counter_delta(current, previous, *, reset=False, reappeared=False):
    reason = "initial" if previous is None else "reset" if reset else "reappeared" if reappeared else None
    if previous:
        if current.get("stats_since") != previous.get("stats_since"):
            reason = "reset"
        for key in COUNTERS:
            a,b = current.get(key),previous.get(key)
            if a is not None and b is not None and a < b-1e-7:
                reason = "reset"
    values = {key: (max(0,current[key]-previous[key]) if reason is None and current.get(key) is not None and previous.get(key) is not None else None) for key in COUNTERS}
    calls = values["calls"]
    values["mean_exec_time"] = values["total_exec_time"]/calls if calls and values["total_exec_time"] is not None else None
    return dict(valid=reason is None,reason=reason,**values)


def activity_dates(db):
    """Recupera a última mudança detectada dos snapshots anteriores à nova coluna JSON."""
    return {row[0]:row[1] for row in db.execute("""SELECT statement_id,MAX(json_extract(record,'$.last_seen'))
        FROM statement_snapshots WHERE json_extract(record,'$.status') IN ('new','updated','restarted')
        GROUP BY statement_id""")}


def synchronize(fetcher=None):
    if not SYNC_LOCK.acquire(blocking=False):
        raise ValueError("Já existe uma atualização de consultas em andamento.")
    try:
        records, context = (fetcher or read_postgres_snapshot)()
        with connect() as db:
            init_store(db)
            # BEGIN IMMEDIATE serializa snapshots também entre processos.
            db.execute("BEGIN IMMEDIATE")
            previous_run = db.execute("SELECT context FROM sync_runs WHERE json_extract(context,'$.source_key')=? ORDER BY captured_at DESC LIMIT 1",(context["source_key"],)).fetchone()
            previous_context = json.loads(previous_run[0]) if previous_run else None
            if previous_context and context["captured_at"] <= previous_context["captured_at"]:
                raise ValueError("Uma leitura mais recente já foi salva. Clique em Atualizar consultas novamente.")
            source_key = context["source_key"]
            reset = bool(previous_context and previous_context["source_key"] == source_key and previous_context["stats_reset"] != context["stats_reset"])
            run_id = uuid.uuid4().hex
            summary = dict(new=0,updated=0,unchanged=0,restarted=0,unavailable=0,delta_calls=0,
                           initial=previous_context is None,global_reset=reset,captured_at=context["captured_at"],run_id=run_id)
            previous_rows = {r["id"]:r for r in db.execute("SELECT * FROM observed_statements WHERE source_key=?",(source_key,))}
            legacy_activity = activity_dates(db) if any("last_activity" not in json.loads(r["record"]) for r in previous_rows.values()) else {}
            seen = set()
            for record in records:
                key = "pg:"+hashlib.sha256(f"{source_key}|{record['database_id']}|{record['user_id']}|{record['query_id']}|{record['toplevel']}".encode()).hexdigest()[:32]
                seen.add(key); old = previous_rows.get(key)
                previous = json.loads(old["record"]) if old else None
                delta = counter_delta(record,previous,reset=reset,reappeared=bool(old and not old["active"]))
                status = "new" if old is None else "restarted" if not delta["valid"] else "updated" if any((delta.get(k) or 0)>0 for k in COUNTERS) else "unchanged"
                summary[status] += 1
                summary["delta_calls"] += delta["calls"] or 0
                record = {**record,"id":key,"source":"pg_stat_statements","delta":delta,"status":status,
                          "active":True,"first_seen":old["first_seen"] if old else context["captured_at"],
                          "last_activity":context["captured_at"] if status!="unchanged" else previous.get("last_activity",legacy_activity.get(key,old["first_seen"])),
                          "last_seen":context["captured_at"],"snapshot_id":run_id,"context":context}
                body=json.dumps(record,ensure_ascii=False)
                db.execute("INSERT INTO observed_statements VALUES (?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET last_seen=excluded.last_seen,active=1,record=excluded.record",
                           (key,source_key,record["first_seen"],context["captured_at"],1,body))
                db.execute("INSERT INTO statement_snapshots VALUES (?,?,?)",(run_id,key,body))
            for key,old in previous_rows.items():
                if key not in seen:
                    db.execute("UPDATE observed_statements SET active=0 WHERE id=?",(key,))
                    summary["unavailable"] += 1
            db.execute("INSERT INTO sync_runs VALUES (?,?,?,?)",(run_id,context["captured_at"],json.dumps(context),json.dumps(summary)))
        return summary
    finally:
        SYNC_LOCK.release()


def list_statements():
    with connect() as db:
        init_store(db)
        last = db.execute("SELECT * FROM sync_runs ORDER BY captured_at DESC LIMIT 1").fetchone()
        context = json.loads(last["context"]) if last else None
        records = [dict(json.loads(r["record"]),active=bool(r["active"])) for r in db.execute("SELECT record,active FROM observed_statements WHERE source_key=?",(context["source_key"] if context else "",))]
        legacy_activity = activity_dates(db) if any("last_activity" not in r for r in records) else {}
        for record in records:
            record.setdefault("last_activity",legacy_activity.get(record["id"],record["first_seen"]))
    total = sum(r["total_exec_time"] for r in records if r["active"])
    for r in records:
        r.update(total_ms=r["total_exec_time"],mean_ms=r["mean_exec_time"],share=r["total_exec_time"]/total*100 if total and r["active"] else 0,variants=None)
    return dict(queries=records,calls=sum(r["calls"] for r in records if r["active"]),total_ms=total,
                latest=dict(context=json.loads(last["context"]),summary=json.loads(last["summary"])) if last else None)


def get_statement(key):
    for record in list_statements()["queries"]:
        if record["id"] == key:
            return record
    raise ValueError("Consulta não encontrada. Clique em Atualizar consultas para sincronizar.")


def bind_parameters(query, values):
    tree,shape=query_shape(query)
    if not isinstance(values,list) or len(values)!=(max(shape.parameters) if shape.parameters else 0):
        raise ValueError("Informe uma lista JSON com um valor por posição, de $1 até o último parâmetro.")
    if len(values)>100 or any(not isinstance(v,(str,int,float,bool,type(None))) or (isinstance(v,float) and not math.isfinite(v)) for v in values):
        raise ValueError("Use até 100 valores simples: texto, número, booleano ou null.")
    class Bind(Visitor):
        def visit_ParamRef(self, ancestors, node):
            literal=sql.Literal(values[node.number-1]).as_string()
            return parse_sql("SELECT "+literal)[0].stmt.targetList[0].val
    Bind()(tree)
    return RawStream()(tree)


def performance_findings(record):
    findings=[]
    def add(title,evidence,recommendation):
        findings.append(dict(title=title,evidence=evidence,recommendation=recommendation,severity="média",points=0))
    if record["mean_ms"]>=500:
        add("Tempo médio elevado",f"Média acumulada de {record['mean_ms']:.2f} ms em {record['calls']} chamadas.","Examine filtros, junções e o plano. Compare uma alternativa usando valores representativos.")
    if record["share"]>=20:
        add("Participação alta no tempo observado",f"Esta entrada corresponde a {record['share']:.1f}% do tempo acumulado das consultas atualmente visíveis.","Priorize esta consulta na investigação do consumo acumulado.")
    if record["calls"] and record["rows"]/record["calls"]>=100_000:
        add("Grande volume de linhas",f"Média de {record['rows']/record['calls']:.0f} linhas por chamada.","Verifique se filtros, projeção e paginação podem reduzir os dados retornados sem alterar o resultado necessário.")
    if (record.get("temp_blks_written") or 0)>0:
        add("Uso de arquivos temporários",f"{record['temp_blks_written']} blocos temporários escritos no período acumulado.","Investigue ordenações e agregações no plano; avalie índices e memória no ambiente de teste.")
    if (record.get("shared_blks_read") or 0)>=10_000:
        add("Volume de leitura de blocos",f"{record['shared_blks_read']} blocos compartilhados lidos. Isso não equivale necessariamente a acesso ao disco físico.","Examine seletividade e índices, distinguindo leitura de blocos e acertos em cache.")
    return findings
