"""Reescritas limitadas, justificadas pela estrutura SQL e pelos tipos do banco."""
from __future__ import annotations

from copy import deepcopy
from pglast import ast, parse_sql, prettify
from pglast.parser import ParseError
from pglast.stream import RawStream
from pglast.visitors import Visitor
from psycopg import sql

from src.analyzer import validate_select
from src.database import get_connection


def parse_select(query):
    query = validate_select(query)
    try:
        tree = parse_sql(query)
    except ParseError as exc:
        raise ValueError("O SQL está incompleto ou contém um erro de sintaxe.") from exc
    if len(tree) != 1 or not isinstance(tree[0].stmt, ast.SelectStmt):
        raise ValueError("Informe exatamente um SELECT.")
    return tree[0].stmt


class Safety(Visitor):
    """A reprodução de logs aceita SELECTs de tabelas, sem funções arbitrárias."""
    allowed = {"extract", "date_part", "lower", "upper", "date_trunc", "count", "sum", "avg",
               "min", "max", "abs", "round", "length", "char_length"}

    def visit_SelectStmt(self, ancestors, node):
        if node.intoClause or node.lockingClause:
            raise ValueError("O teste aceita SELECT e CTEs de leitura, sem INTO ou bloqueios.")

    def visit_FuncCall(self, ancestors, node):
        parts = [part.sval for part in node.funcname]
        if parts[-1] not in self.allowed or (len(parts) > 1 and parts[:-1] != ["pg_catalog"]):
            raise ValueError("Função fora do conjunto aceito para execução controlada: " + ".".join(parts))

    def visit_RangeVar(self, ancestors, node):
        if node.catalogname or node.schemaname not in {None, "public"}:
            raise ValueError("O teste está restrito às tabelas do esquema public.")

    def visit_ParamRef(self, ancestors, node):
        raise ValueError("O log contém parâmetros ($1 etc.). Informe um SQL com os valores antes de testar.")


def executable_select(query):
    statement = parse_select(query)
    Safety()(statement)
    return RawStream()(statement)


def missing_proposal_note(query, analysis):
    statement=parse_select(query)
    if analysis and statement.groupClause and not statement.whereClause:
        nodes=[]
        def walk(node):
            nodes.append(node)
            for child in node.get("Plans",[]):walk(child)
        walk(analysis["plan"]["Plan"])
        if any(n.get("Node Type") in {"Seq Scan","Parallel Seq Scan"} for n in nodes):
            parallel=any(n.get("Node Type") in {"Gather","Gather Merge"} for n in nodes)
            return dict(title="Sem alternativa automática",message=(
                "O plano atual lê a tabela para calcular os totais por grupo, sem filtro. "
                + ("A agregação já utiliza processamento paralelo. " if parallel else "")
                + "As regras atuais não geram uma reescrita para esse padrão; uma melhoria de tempo precisaria ser testada."))
    return dict(title="Sem alternativa automática",message="Não há uma regra de reescrita implementada para este padrão. As métricas e os alertas disponíveis continuam na análise.")


def correlated_count_proposal(statement):
    """COUNT(*) correlacionado simples: agrega uma vez e preserva zeros via LEFT JOIN."""
    if (statement.withClause or statement.groupClause or statement.havingClause or statement.distinctClause
            or statement.larg or statement.rarg or len(statement.fromClause or ())!=1
            or not isinstance(statement.fromClause[0],ast.RangeVar)):
        return []
    outer=statement.fromClause[0]
    if outer.schemaname not in {None,"public"}:
        return []
    targets=[(i,t) for i,t in enumerate(statement.targetList or ()) if isinstance(t.val,ast.SubLink)]
    if len(targets)!=1:
        return []
    index,target=targets[0]
    if not target.name or target.val.subLinkType.name!="EXPR_SUBLINK":
        return []  # Não muda o nome implícito de uma coluna de resultado.
    sub=target.val.subselect
    if (not isinstance(sub,ast.SelectStmt) or sub.withClause or sub.groupClause or sub.havingClause
            or sub.distinctClause or sub.limitCount or sub.limitOffset or sub.sortClause or sub.larg or sub.rarg
            or len(sub.fromClause or ())!=1 or not isinstance(sub.fromClause[0],ast.RangeVar)
            or len(sub.targetList or ())!=1):
        return []
    child=sub.fromClause[0]; fn=sub.targetList[0].val
    if not child.inh:
        return []  # ONLY não é preservado pela construção da tabela agregada.
    if child.schemaname not in {None,"public"} or not isinstance(fn,ast.FuncCall):
        return []
    if [n.sval for n in fn.funcname] not in [["count"],["pg_catalog","count"]] or not fn.agg_star or fn.agg_filter or fn.over or fn.agg_distinct:
        return []
    predicate=sub.whereClause
    if not isinstance(predicate,ast.A_Expr) or [n.sval for n in predicate.name]!=["="]:
        return []
    def fields(node):
        return [n.sval for n in node.fields] if isinstance(node,ast.ColumnRef) and all(isinstance(n,ast.String) for n in node.fields) else []
    left,right=fields(predicate.lexpr),fields(predicate.rexpr)
    child_alias=child.alias.aliasname if child.alias else child.relname
    outer_alias=outer.alias.aliasname if outer.alias else outer.relname
    if child_alias==outer_alias:
        return []
    if len(left)==2 and len(right)==2 and left[0]==outer_alias and right[0]==child_alias:
        left,right=right,left
    if len(left)!=2 or len(right)!=2 or left[0]!=child_alias or right[0]!=outer_alias:
        return []
    class Check(Visitor):
        selects=0
        stars=False
        def visit_SelectStmt(self,ancestors,node):self.selects+=1
        def visit_ColumnRef(self,ancestors,node):
            if any(isinstance(f,ast.A_Star) for f in node.fields):self.stars=True
    check=Check();check(statement)
    if check.selects!=2 or check.stars:
        return []
    original=RawStream()(statement)
    def unique(base):
        name=base
        while name.lower() in original.lower():name+="_x"
        return name
    alias,key,count=unique("_tcc_counts"),unique("_tcc_key"),unique("_tcc_count")
    ident=lambda value:sql.Identifier(value).as_string()
    child_table=sql.Identifier(child.schemaname or "public",child.relname).as_string()
    outer_reference=sql.Identifier(right[0],right[1]).as_string()
    joined=parse_select(f"SELECT 1 FROM {RawStream()(outer)} LEFT JOIN (SELECT {ident(left[1])} AS {ident(key)}, count(*) AS {ident(count)} FROM {child_table} GROUP BY {ident(left[1])}) AS {ident(alias)} ON {ident(alias)}.{ident(key)}={outer_reference}")
    alternative=deepcopy(statement)
    alternative.fromClause=joined.fromClause
    alternative.targetList[index].val=parse_select(f"SELECT COALESCE({ident(alias)}.{ident(count)},0)").targetList[0].val
    return [dict(id="correlated-count",title="Substituir a contagem repetida por uma agregação com LEFT JOIN",
                 evidence="A subconsulta conta registros da mesma tabela para cada linha externa. A alternativa agrupa a tabela uma vez e associa as contagens.",
                 condition="COUNT(*) correlacionado por uma igualdade, sem filtros adicionais na subconsulta. LEFT JOIN e COALESCE preservam os registros sem correspondência e a contagem zero.",
                 original=prettify(original,comma_at_eoln=True),alternative=prettify(RawStream()(alternative),comma_at_eoln=True),
                 origin="Regra explícita sobre a árvore SQL",status="Proposta para teste")]


def propose(query: str) -> list[dict]:
    statement = parse_select(query)
    correlated=correlated_count_proposal(statement)
    if correlated:
        return correlated
    # Apenas um nível SELECT, com predicado isolado: não reescreve strings, comentários ou subconsultas.
    relations = {}
    class Relations(Visitor):
        selects = 0
        def visit_SelectStmt(self, ancestors, node):
            self.selects += 1
        def visit_RangeVar(self, ancestors, node):
            if node.schemaname not in {None, "public"}:
                return
            relations[node.alias.aliasname if node.alias else node.relname] = node.relname
    visitor = Relations(); visitor(statement)
    if visitor.selects != 1 or statement.withClause or statement.intoClause:
        return []
    predicate = statement.whereClause
    if not isinstance(predicate, ast.A_Expr) or [n.sval for n in predicate.name] != ["="]:
        return []
    fn, literal = predicate.lexpr, predicate.rexpr
    if not isinstance(fn, ast.FuncCall) or not isinstance(literal, (ast.A_Const,ast.ParamRef)):
        return []
    names = [n.sval for n in fn.funcname]
    if len(names) > 1 and names[:-1] != ["pg_catalog"]:
        return []
    function = names[-1]
    args = fn.args or ()
    column = args[-1] if args else None
    if not isinstance(column, ast.ColumnRef):
        return []
    fields = [n.sval for n in column.fields if isinstance(n, ast.String)]
    if len(fields) != len(column.fields) or len(fields) not in {1, 2}:
        return []
    table = relations.get(fields[0]) if len(fields) == 2 else next(iter(relations.values()), None) if len(relations) == 1 else None
    if not table:
        return []
    col = fields[-1]
    with get_connection() as connection:
        connection.read_only = True
        with connection.cursor() as cursor:
            cursor.execute("SET LOCAL statement_timeout='15s'")
            cursor.execute("SET LOCAL search_path=pg_catalog,public")
            cursor.execute("SELECT data_type FROM information_schema.columns WHERE table_schema='public' AND table_name=%s AND column_name=%s", (table,col))
            row = cursor.fetchone()
            if not row:
                return []
            datatype = row[0]
            reference = RawStream()(column)
            replacement, rule, title, evidence, condition = None, None, None, None, None
            if function == "extract" and len(args) == 2 and isinstance(args[0], ast.A_Const) and isinstance(args[0].val, ast.String) and args[0].val.sval.lower() == "year" and isinstance(literal,ast.A_Const) and isinstance(literal.val, ast.Integer) and datatype in {"date","timestamp without time zone"}:
                year = literal.val.ival
                if not 1 <= year <= 9998:
                    return []
                replacement = parse_select(f"SELECT 1 WHERE {reference} >= DATE '{year:04}-01-01' AND {reference} < DATE '{year+1:04}-01-01'").whereClause
                rule, title = "year-range", "Substituir a extração do ano por um intervalo"
                evidence = f"EXTRACT(YEAR) aplicado a {table}.{col}, do tipo {datatype}. O intervalo permite usar diretamente as estatísticas da coluna e índices compatíveis."
                condition = "Predicado de igualdade com ano literal; coluna DATE ou TIMESTAMP sem fuso. Mantém o ano e o tratamento de valores nulos."
            elif function == "lower" and len(args) == 1 and (isinstance(literal,ast.ParamRef) or isinstance(literal.val,ast.String)) and datatype in {"character varying", "text"}:
                # Testa a normalização pela mesma collation e LOWER do servidor.
                cursor.execute(sql.SQL("SELECT NOT EXISTS (SELECT 1 FROM public.{} WHERE {} IS DISTINCT FROM pg_catalog.lower({}))").format(sql.Identifier(table),sql.Identifier(col),sql.Identifier(col)))
                normalized = cursor.fetchone()[0]
                if not normalized:
                    return []
                replacement = deepcopy(predicate); replacement.lexpr = deepcopy(column)
                rule, title = "normalized-lower", "Comparar diretamente a coluna normalizada"
                evidence = f"O banco confirmou que todos os valores atuais de {table}.{col} já correspondem a LOWER({col}). Compare a coluna diretamente em vez de aplicar LOWER; isso permite investigar o uso do índice da coluna."
                condition = "Válido para os dados atuais verificados. A regra de armazenamento deve manter os valores normalizados; a validação compara novamente os resultados."
    if replacement is None:
        return []
    alternative = deepcopy(statement); alternative.whereClause = replacement
    return [dict(id=rule,title=title,evidence=evidence,condition=condition,
                 original=prettify(RawStream()(statement),comma_at_eoln=True),alternative=prettify(RawStream()(alternative),comma_at_eoln=True),
                 origin="Regra explícita sobre a árvore SQL + metadados do PostgreSQL",status="Proposta para teste")]
