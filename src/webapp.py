"""Interface local do TCC. Execute com python -m src.webapp --open."""

from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import socket
import sys
import uuid
from urllib.parse import urlsplit
from urllib.request import urlopen
import webbrowser

import psycopg
from pglast import prettify

from scripts.generate_workload import QUERY_FILE, load_queries
from src.analyzer import (
    collect_relation_metadata, explain_query, fetch_history, validate_select,
)
from src.collector import collect_metrics
from src.config import PROJECT_ROOT
from src.database import get_connection
from src.demo_queries import DEMO_QUERIES
from src.plan_analyzer import analyze_plan
from src.recommendations import recommend
from src.execution_logs import import_logs, list_queries, get_query, reports, save_experiment
from src.optimization import propose, missing_proposal_note
from src.benchmark import benchmark, RUN_LOCK
from src.log_capture import capture_workload
from src.statement_sync import (synchronize, list_statements, get_statement, query_shape, bind_parameters, performance_findings)

STATIC = PROJECT_ROOT / "web"
APP_ID = "tcc-sql-logs-interface"
DESCRIPTIONS = {
    "Q01": "Busca um cliente pelo seu identificador. É um exemplo de acesso pela chave primária.",
    "Q02": "Filtra produtos por categoria e preço e organiza os resultados.",
    "Q03": "Mostra os pedidos de um cliente, do mais recente ao mais antigo.",
    "Q04": "Retorna todas as colunas dos pedidos cancelados.",
    "Q05": "Busca os pedidos de 2026 e os dados de seus clientes. O filtro extrai o ano da data de cada pedido.",
    "Q06": "Cruza várias tabelas para resumir vendas por estado e categoria.",
    "Q07": "Agrupa os pedidos por mês dentro de um período.",
    "Q08": "Ordena os pedidos pelo valor para encontrar os maiores.",
    "Q09": "Procura um cliente por e-mail, convertendo a coluna para letras minúsculas com LOWER.",
    "Q10": "Usa uma subconsulta com a média dos valores para filtrar pedidos.",
    "Q11": "Conta pedidos por cliente usando uma subconsulta relacionada à consulta principal.",
    "Q12": "Lê todos os itens de pedido, sem aplicar um filtro.",
}


def presets() -> dict:
    return {
        "queries": DEMO_QUERIES,
        "comparisons": [
            dict(id="email", title="Busca por e-mail", original_id="Q09",
                 original=(PROJECT_ROOT / "sql/candidate_email_lower.sql").read_text(encoding="utf-8"),
                 alternative=(PROJECT_ROOT / "sql/candidate_email_direct.sql").read_text(encoding="utf-8"),
                 explanation="O original aplica LOWER ao e-mail. A alternativa compara diretamente com o e-mail e permite investigar o uso do índice já existente.",
                 condition="Neste conjunto sintético, todos os e-mails estão em minúsculas. Fora dessa condição, as duas consultas podem retornar resultados diferentes."),
            dict(id="date", title="Pedidos de 2026", original_id="Q05",
                 original=(PROJECT_ROOT / "sql/candidate_query.sql").read_text(encoding="utf-8"),
                 alternative=(PROJECT_ROOT / "sql/candidate_query_range.sql").read_text(encoding="utf-8"),
                 explanation="O original extrai o ano da data. A alternativa usa o intervalo de 1º de janeiro de 2026 até antes de 1º de janeiro de 2027.",
                 condition="As duas formas selecionam o mesmo ano neste banco. Como muitos pedidos são de 2026, uma varredura completa ainda pode ser uma escolha adequada."),
        ],
    }


def execute_preset(preset_id):
    """Executa apenas um exemplo cadastrado, em transação de leitura."""
    if not isinstance(preset_id, str):
        raise ValueError('Selecione uma consulta cadastrada.')
    selected = next((q for q in presets()['queries'] if q['id'] == preset_id), None)
    if selected is None:
        raise ValueError('Consulta cadastrada não encontrada.')
    from src.optimization import executable_select
    query = executable_select(selected['sql'])
    if not RUN_LOCK.acquire(blocking=False):
        raise ValueError('Outro teste ou coleta está em andamento. Aguarde sua conclusão.')
    try:
        with get_connection() as connection:
            connection.read_only = True
            with connection.cursor() as cursor:
                cursor.execute("SET LOCAL statement_timeout='30s'")
                cursor.execute("SET LOCAL lock_timeout='3s'")
                cursor.execute('SET LOCAL search_path=pg_catalog,public')
                rows = sum(1 for _ in cursor.stream(query, size=2000))
        return {'id': selected['id'], 'title': selected['title'], 'rows': rows}
    finally:
        RUN_LOCK.release()


def analyze_query(query: str, *, generic=None, history_override=None) -> dict:
    query = validate_select(query)
    if generic is None:
        generic=bool(query_shape(query)[1].parameters)
    with get_connection() as connection:
        connection.read_only = True
        document = explain_query(connection, query, 30, generic=generic)
        metadata = collect_relation_metadata(connection, document)
        improvements = recommend(connection, query, document)
        query_id = document.get("Query Identifier")
        history = history_override if history_override is not None else fetch_history(connection, int(query_id)) if query_id is not None else None
    # Expõe também as regras já usadas pela investigação de consultas.
    if not generic and not any(p['kind'] == 'rewrite' for p in improvements['proposals']):
        for candidate in propose(query):
            improvements['proposals'].append(dict(
                kind='rewrite', title=candidate['title'], sql=candidate['alternative'],
                explanation=candidate['evidence'], evidence=candidate['origin'],
                conditions=candidate['condition'], status='Proposta para teste; ganho ainda não medido.'))
        if any(p['kind'] == 'rewrite' for p in improvements['proposals']):
            improvements['rewrite_status'] = 'available'
            improvements['notes'] = []
    assessment = analyze_plan(query, document, metadata, None if generic else history)
    plan = document["Plan"]
    # Identificadores bigint precisam ser texto no JavaScript para não perder dígitos.
    if query_id is not None:
        document["Query Identifier"] = str(query_id)
    return {
        "sql": query, "query_id": str(query_id) if query_id is not None else None,
        "root_node": plan.get("Node Type"), "estimated_rows": plan.get("Plan Rows", 0),
        "total_cost": plan.get("Total Cost", 0), "history": history,
        "score": assessment.score, "attention_level": assessment.attention_level,
        "findings": [asdict(f) for f in assessment.findings], "plan": document,
        "analyzed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "query_executed": False, "improvements": improvements, "plan_kind": "generic" if generic else "values",
    }


def project_recommendation(original, alternative):
    """Compara estimativas do planejador sem converter custo em milissegundos."""
    before,after=original["total_cost"],alternative["total_cost"]
    reduction=(before-after)/before*100 if before>0 else None
    def operations(plan):
        result=[]
        def walk(node):
            if node.get("Relation Name"):
                result.append({"table":node["Relation Name"],"operation":node["Node Type"]})
            for child in node.get("Plans",[]):walk(child)
        walk(plan["Plan"])
        return result
    def subplans(node):
        return int(bool(node.get("Subplan Name")))+sum(subplans(child) for child in node.get("Plans",[]))
    return dict(cost_before=before,cost_after=after,cost_reduction_pct=reduction,
                rows_before=original["estimated_rows"],rows_after=alternative["estimated_rows"],
                operations_before=operations(original["plan"]),operations_after=operations(alternative["plan"]),
                subplans_before=subplans(original["plan"]["Plan"]),subplans_after=subplans(alternative["plan"]["Plan"]),
                generic=original["plan_kind"]=="generic",expected_time_ms=None,
                time_note="O plano não prevê tempo em milissegundos. Medir ganho executa as duas versões para obter tempos reais.")


def investigate_statement(payload):
    record = get_statement(payload.get("id", ""))
    _,shape = query_shape(record["sql"])
    materialized = None
    if "parameters" in payload:
        materialized = bind_parameters(record["sql"], payload["parameters"])
    elif not shape.parameters:
        materialized = record["sql"]
    query = materialized or record["sql"]
    historical = {key:record[key] for key in ("calls","rows","total_exec_time","mean_exec_time")}
    analysis,plan_error = None,None
    try:
        analysis = analyze_query(query,generic=materialized is None,history_override=historical)
    except (psycopg.Error,ValueError):
        plan_error = "O PostgreSQL não pôde planejar este SQL na conexão atual. As métricas históricas permanecem disponíveis. Informe os valores dos parâmetros e confira os tipos, permissões e o esquema da consulta."
    recommendations = []
    if analysis:
        try:
            recommendations = propose(query)
        except (psycopg.Error,ValueError):
            pass
    for recommendation in recommendations:
        recommendation["requires_parameters"]=bool(query_shape(recommendation["alternative"])[1].parameters)
        recommendation["projection"]=None
        try:
            alternative=analyze_query(recommendation["alternative"],generic=recommendation["requires_parameters"])
            recommendation["projection"]=project_recommendation(analysis,alternative)
        except (psycopg.Error,ValueError):
            recommendation["projection_error"]="Não foi possível estimar o plano da alternativa."
    additional = (analysis or {}).get('improvements', {}).get('proposals', [])
    has_rewrite = bool(recommendations) or any(p.get('kind') == 'rewrite' for p in additional)
    if payload.get('record_outcome') is True and materialized and not has_rewrite:
        status = 'plan_unavailable' if plan_error else 'no_proposal'
        verdict = 'Plano indisponível' if plan_error else 'Sem alternativa automática'
        save_experiment(dict(id=uuid.uuid4().hex, created_at=datetime.now(timezone.utc).isoformat(),
            query_id=record['id'], original_sql=query, alternative_sql=None, status=status,
            verdict=verdict, equivalent=None, reduction_pct=None, metrics={},
            reason=plan_error or 'As regras disponíveis não encontraram uma reescrita automática.',
            environment=dict(database=record.get('database_name'))))
    return dict(record=record,formatted_sql=prettify(query,comma_at_eoln=True,safety_belt=True),analysis=analysis,findings=performance_findings(record),recommendations=recommendations,
                recommendation_note=missing_proposal_note(query,analysis) if not recommendations else None,
                parameters=sorted(shape.parameters),materialized_sql=materialized,plan_error=plan_error,
                query_executed=False,source="pg_stat_statements",
                note="Estatísticas agregadas por banco, usuário e Query ID. O PostgreSQL não informa qual ferramenta executou cada chamada. O plano é estimado agora, na conexão do sistema; não é o plano histórico de uma execução.")


def overview() -> dict:
    metrics, metadata = collect_metrics()
    for record in metrics:
        record["query_id"] = str(record["query_id"])
    metrics.sort(key=lambda m: -m["total_exec_time"])
    with get_connection() as connection:
        connection.read_only = True
        with connection.cursor() as cursor:
            cursor.execute("SET LOCAL statement_timeout = '10s'")
            cursor.execute("""
                SELECT relname, GREATEST(reltuples, 0)::bigint
                FROM pg_class WHERE relnamespace = 'public'::regnamespace
                AND relname IN ('clientes','produtos','pedidos','itens_pedido','pagamentos')
                ORDER BY relname
            """)
            tables = [dict(name=name, estimated_rows=rows) for name, rows in cursor]
        # O histórico normaliza valores como $1. Relacionamos seus IDs aos
        # exemplos originais usando somente EXPLAIN, sem executar os SELECTs.
        examples = {}
        for query in load_queries(QUERY_FILE):
            document = explain_query(connection, validate_select(query.statement), 30)
            query_id = document.get("Query Identifier")
            if query_id is not None:
                examples[str(query_id)] = query
        for record in metrics:
            example = examples.get(record["query_id"])
            record["preset_id"] = example.name if example else None
            record["title"] = example.title if example else "Consulta fora dos exemplos"
    return {"metrics": metrics, "metadata": metadata, "tables": tables}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args) -> None:
        # Não registra corpo de requisições, SQL ou credenciais.
        super().log_message(format, *args)

    def valid_host(self) -> bool:
        return self.headers.get("Host") in self.server.allowed_hosts

    def send_body(self, body: bytes, content_type: str, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, payload: dict, status: int = 200) -> None:
        self.send_body(json.dumps(payload, ensure_ascii=False, allow_nan=False).encode(),
                       "application/json; charset=utf-8", status)

    def do_GET(self) -> None:
        if not self.valid_host():
            self.send_json({"error": "Acesso permitido apenas pelo endereço local."}, 403)
            return
        path = urlsplit(self.path).path
        try:
            if path == "/api/info":
                self.send_json({"app": APP_ID})
            elif path == "/api/presets":
                self.send_json(presets())
            elif path == "/api/statements":
                self.send_json(list_statements())
            elif path == "/api/logs":
                self.send_json(list_queries())
            elif path == "/api/reports":
                self.send_json({"reports": reports()})
            elif path == "/api/overview":
                self.send_json(overview())
            elif path in {"/", "/app.js", "/styles.css", "/favicon.svg"}:
                filename, mime = {
                    "/": ("index.html", "text/html; charset=utf-8"),
                    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
                    "/styles.css": ("styles.css", "text/css; charset=utf-8"),
                    "/favicon.svg": ("favicon.svg", "image/svg+xml"),
                }[path]
                self.send_body((STATIC / filename).read_bytes(), mime)
            else:
                self.send_json({"error": "Página não encontrada."}, 404)
        except Exception as exc:
            self.handle_error(exc)

    def do_POST(self) -> None:
        # Bloqueia chamadas de outros sites e requisições simples cross-origin.
        origin = self.headers.get("Origin")
        allowed_origins = {f"http://{host}" for host in self.server.allowed_hosts}
        if (not self.valid_host() or self.headers.get("X-TCC-Client") != "local"
                or (origin is not None and origin not in allowed_origins)):
            self.send_json({"error": "Abra a interface pelo endereço local."}, 403)
            return
        path = urlsplit(self.path).path
        if path not in {"/api/analyze", "/api/compare", "/api/logs/import", "/api/logs/capture", "/api/logs/investigate", "/api/benchmark", "/api/statements/sync", "/api/statements/investigate", "/api/presets/execute"}:
            self.send_json({"error": "Operação não encontrada."}, 404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            limit = 21 * 1024 * 1024 if path == "/api/logs/import" else 65_536
            if not 0 < length <= limit:
                raise ValueError("O arquivo excedeu o limite de importação." if path == "/api/logs/import" else "Informe uma consulta de até 64 KB.")
            if self.headers.get_content_type() != "application/json":
                raise ValueError("Formato de requisição inválido.")
            payload = json.loads(self.rfile.read(length))
            if not isinstance(payload, dict):
                raise ValueError("Formato de requisição inválido.")
            if path == '/api/presets/execute':
                self.send_json(execute_preset(payload.get('id')))
                return
            if path == "/api/statements/sync":
                self.send_json(synchronize())
                return
            if path == "/api/statements/investigate":
                self.send_json(investigate_statement(payload))
                return
            if path == "/api/logs/import":
                if not isinstance(payload.get("content"), str) or not isinstance(payload.get("filename"), str):
                    raise ValueError("Selecione um arquivo de log.")
                if payload.get('database_confirmed') is not True:
                    raise ValueError('Confirme que o arquivo corresponde ao banco tcc_sql_optimizer_logs.')
                self.send_json(import_logs(payload["content"], payload["filename"], database_name='tcc_sql_optimizer_logs'))
                return
            if path == "/api/logs/capture":
                self.send_json(capture_workload(payload.get("calls", 2)))
                return
            if path == "/api/logs/investigate":
                record = get_query(payload.get("id", ""))
                if record.get("database_name") not in {None,"tcc_sql_optimizer_logs"}:
                    raise ValueError("Este registro pertence a outro banco. A investigação desta cópia está configurada para tcc_sql_optimizer_logs.")
                self.send_json({"record": record, "analysis": analyze_query(record["sql"]), "recommendations": propose(record["sql"])})
                return
            if path == "/api/benchmark":
                if not all(isinstance(payload.get(k), str) for k in ("original", "alternative")):
                    raise ValueError("Preencha as duas consultas para executar o teste.")
                self.send_json(benchmark(payload["original"], payload["alternative"], payload.get("calls", 10), payload.get("query_id"),
                    selection_reason=payload.get('selection_reason'), source_event_id=payload.get('source_event_id'), rule=payload.get('rule')))
                return
            fields = ("sql",) if path == "/api/analyze" else ("original", "alternative")
            for field in fields:
                if not isinstance(payload.get(field), str):
                    raise ValueError("Preencha o SQL da consulta.")
                validate_select(payload[field])
            if path == "/api/analyze":
                self.send_json(analyze_query(payload["sql"]))
            else:
                self.send_json({"original": analyze_query(payload["original"]),
                                "alternative": analyze_query(payload["alternative"])})
        except Exception as exc:
            self.handle_error(exc)

    def handle_error(self, exc: Exception) -> None:
        if isinstance(exc, (ValueError, UnicodeError)):
            self.send_json({"error": str(exc)}, 400)
        elif isinstance(exc, psycopg.Error):
            if exc.sqlstate and exc.sqlstate.startswith("42"):
                message = "O PostgreSQL não reconheceu esse SQL. Confira os nomes das tabelas, colunas e a sintaxe."
                status = 400
            elif exc.sqlstate == "57014":
                message, status = "A análise atingiu o limite de tempo. Tente uma consulta mais simples.", 408
            else:
                message = "Não foi possível consultar o banco. Confira o serviço PostgreSQL, o arquivo .env e a extensão pg_stat_statements."
                status = 503
            self.send_json({"error": message}, status)
        else:
            print(f"Falha na interface: {type(exc).__name__}", file=sys.stderr)
            self.send_json({"error": "Não foi possível concluir a operação. Consulte o terminal da interface."}, 500)


class LocalServer(ThreadingHTTPServer):
    # No Windows, SO_REUSEADDR pode permitir dois servidores na mesma porta.
    allow_reuse_address = False
    allow_reuse_port = False

    def server_bind(self) -> None:
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8767)
    parser.add_argument("--open", action="store_true", help="Abre o navegador.")
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("A porta deve estar entre 1 e 65535.")
    address = f"http://127.0.0.1:{args.port}"
    try:
        server = LocalServer(("127.0.0.1", args.port), Handler)
    except OSError:
        try:
            with urlopen(address + "/api/info", timeout=2) as response:
                info = json.load(response)
                if info.get("app") == APP_ID:
                    print(f"A interface já está aberta em {address}")
                    if args.open:
                        webbrowser.open(address)
                    return 0
        except Exception:
            pass
        print(f"Porta {args.port} indisponível. Use --port para escolher outra.", file=sys.stderr)
        return 1
    server.allowed_hosts = {f"127.0.0.1:{args.port}", f"localhost:{args.port}"}
    print(f"Interface do TCC: {address}\nMantenha esta janela aberta. Ctrl+C encerra a interface.", flush=True)
    if args.open:
        webbrowser.open(address)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
