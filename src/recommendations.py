"""Recomendações explicáveis: duas regras conservadoras, sem executar DDL."""
from __future__ import annotations

import hashlib

import sqlglot
from sqlglot import exp
from sqlglot.errors import SqlglotError

from src.plan_analyzer import iter_plan_nodes


def ident(node):
    if not isinstance(node, exp.Identifier):
        return None
    return node.name if node.args.get("quoted") else node.name.lower()


def quoted(name):
    return '"' + name.replace('"', '""') + '"'


def parse_supported(query):
    """Uma SELECT, sem escopos aninhados nem fontes derivadas nesta versão."""
    tree = sqlglot.parse_one(query, read="postgres")
    if not isinstance(tree, exp.Select) or len(list(tree.find_all(exp.Select))) != 1:
        return None
    if tree.args.get("with_") or tree.find(exp.Subquery) or tree.find(exp.Into):
        return None
    source = tree.args.get("from_")
    sources = [source.this] if source else []
    for join in tree.args.get("joins", []):
        if join.args.get("using") or join.args.get("method"):
            return None
        sources.append(join.this)
    if not sources or any(not isinstance(t, exp.Table) or t.catalog for t in sources):
        return None
    for table in sources:
        if not isinstance(table.this, exp.Identifier):
            return None
        alias = table.args.get("alias")
        if alias and alias.args.get("columns"):
            return None
    return tree


def read_catalog(connection, tree):
    """Resolve nomes no search_path da mesma conexão que produziu o plano."""
    catalog = {}
    with connection.cursor() as cursor:
        for table in tree.find_all(exp.Table):
            name = ident(table.this)
            schema = ident(table.args.get("db"))
            alias = table.args.get("alias")
            binding = ident(alias.this) if alias else name
            reference = '.'.join(quoted(n) for n in (schema, name) if n)
            cursor.execute("""
                SELECT c.oid, n.nspname, c.relname
                FROM pg_catalog.pg_class c
                JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace
                WHERE c.oid=pg_catalog.to_regclass(%s) AND c.relkind='r'
            """, (reference,))
            relation = cursor.fetchone()
            if not relation or binding in catalog:
                return {}
            oid, actual_schema, actual_name = relation
            cursor.execute("""
                SELECT a.attname, t.typname, tn.nspname
                FROM pg_catalog.pg_attribute a
                JOIN pg_catalog.pg_type t ON t.oid=a.atttypid
                JOIN pg_catalog.pg_namespace tn ON tn.oid=t.typnamespace
                WHERE a.attrelid=%s AND a.attnum>0 AND NOT a.attisdropped
            """, (oid,))
            columns = {name: typ if ns == 'pg_catalog' else 'unsupported'
                       for name, typ, ns in cursor.fetchall()}
            cursor.execute("""
                SELECT ic.relname, json_agg(json_build_object(
                    'column', a.attname,
                    'desc', (i.indoption[k.pos-1] & 1) <> 0,
                    'nulls_first', (i.indoption[k.pos-1] & 2) <> 0,
                    'default_ops', op.opcdefault,
                    'same_collation', i.indcollation[k.pos-1] = a.attcollation
                ) ORDER BY k.pos)
                FROM pg_catalog.pg_index i
                JOIN pg_catalog.pg_class ic ON ic.oid=i.indexrelid
                JOIN pg_catalog.pg_am am ON am.oid=ic.relam
                CROSS JOIN LATERAL unnest(i.indkey) WITH ORDINALITY k(attnum,pos)
                LEFT JOIN pg_catalog.pg_attribute a
                  ON a.attrelid=i.indrelid AND a.attnum=k.attnum
                LEFT JOIN pg_catalog.pg_opclass op ON op.oid=i.indclass[k.pos-1]
                WHERE i.indrelid=%s AND i.indisvalid AND i.indisready
                  AND i.indpred IS NULL AND i.indexprs IS NULL
                  AND am.amname='btree' AND k.pos<=i.indnkeyatts
                GROUP BY ic.relname
            """, (oid,))
            indexes = [{"name": n, "keys": keys} for n, keys in cursor.fetchall()]
            catalog[binding] = dict(schema=actual_schema, table=actual_name,
                                    columns=columns, indexes=indexes)
    return catalog


def resolve(column, catalog):
    if not isinstance(column, exp.Column) or column.args.get("catalog"):
        return None
    name = ident(column.this)
    binding = ident(column.args.get("table"))
    candidates = [(b, r) for b, r in catalog.items()
                  if name in r['columns'] and (not binding or binding == b)]
    schema = ident(column.args.get("db"))
    if schema:
        candidates = [(b, r) for b, r in candidates if r['schema'] == schema]
    return (candidates[0][0], name) if len(candidates) == 1 else None


def conjuncts(node):
    if isinstance(node, exp.Paren):
        return conjuncts(node.this)
    if isinstance(node, exp.And):
        return conjuncts(node.this) + conjuncts(node.expression)
    return [node]


def year_rewrite(tree, catalog):
    alternative = tree.copy()
    where = alternative.args.get('where')
    if not where:
        return None
    changed = []
    for predicate in conjuncts(where.this):
        if not isinstance(predicate, exp.EQ):
            continue
        left, right = predicate.this, predicate.expression
        if isinstance(right, exp.Extract):
            left, right = right, left
        if not (isinstance(left, exp.Extract) and left.this.name.upper() == 'YEAR'
                and isinstance(right, exp.Literal) and not right.is_string
                and right.this.isdigit()):
            continue
        year = int(right.this)
        column = left.expression
        key = resolve(column, catalog)
        if not key or not 1 <= year <= 9998:
            continue
        typ = catalog[key[0]]['columns'][key[1]]
        if typ not in {'date', 'timestamp'}:
            continue
        sql_type = 'DATE' if typ == 'date' else 'TIMESTAMP'
        col_sql = column.sql(dialect='postgres')
        replacement = sqlglot.parse_one(
            f"({col_sql} >= {sql_type} '{year:04d}-01-01' AND "
            f"{col_sql} < {sql_type} '{year+1:04d}-01-01')", read='postgres')
        predicate.replace(replacement)
        changed.append(col_sql)
    if not changed:
        return None
    generated = alternative.sql(dialect='postgres', pretty=True)
    # Não aceita perda estrutural na serialização do dialeto suportado.
    if sqlglot.parse_one(generated, read='postgres') != alternative:
        return None
    return dict(rule_id='date_year_range', kind='rewrite',
                title='Substituir extração de ano por intervalo de datas',
                explanation='O filtro passa a comparar diretamente a coluna. Isso pode favorecer as estatísticas e o acesso por índice, quando vantajoso.',
                evidence='Filtro por ano em: ' + ', '.join(changed),
                conditions='Aplicável a DATE ou TIMESTAMP sem fuso, ano literal entre 1 e 9998 e igualdade no filtro. Preserva o intervalo do ano; o ganho depende dos dados e do plano.',
                sql=generated + ';', status='Proposta ainda não validada por execução')


def covers(index, equality, ordering):
    keys = index['keys']
    if len(keys) < len(equality) + len(ordering):
        return False
    used = keys[:len(equality) + len(ordering)]
    if any(not k.get('default_ops') or not k.get('same_collation') for k in used):
        return False
    if {k['column'] for k in keys[:len(equality)]} != set(equality):
        return False
    tail = keys[len(equality):len(equality)+len(ordering)]
    return any(all(k['column'] == col and bool(k['desc']) == (desc ^ reverse)
                   and bool(k['nulls_first']) == (nulls ^ reverse)
                   for k, (col, desc, nulls) in zip(tail, ordering))
               for reverse in (False, True))


def filter_order_index(tree, catalog, document):
    if len(catalog) != 1 or tree.args.get('joins') or tree.args.get('group') or tree.args.get('distinct'):
        return None, []
    where, order = tree.args.get('where'), tree.args.get('order')
    if not where or not order:
        return None, []
    equality = []
    for predicate in conjuncts(where.this):
        if not isinstance(predicate, exp.EQ):
            return None, []
        col, value = predicate.this, predicate.expression
        if isinstance(value, exp.Column):
            col, value = value, col
        key = resolve(col, catalog)
        if not key or not isinstance(value, (exp.Literal, exp.Boolean)):
            return None, []
        if key[1] not in equality:
            equality.append(key[1])
    ordering = []
    for item in order.expressions:
        key = resolve(item.this, catalog)
        # ORDER BY de alias de projeção pode apontar para outra expressão.
        aliases = {ident(e.args.get('alias')) for e in tree.expressions if isinstance(e, exp.Alias)}
        if not key or (not item.this.table and key[1] in aliases):
            return None, []
        if key[1] not in equality:
            ordering.append((key[1], bool(item.args.get('desc')), bool(item.args.get('nulls_first'))))
    if not ordering or not equality or len(equality) + len(ordering) > 4:
        return None, []
    relation = next(iter(catalog.values()))
    for index in relation['indexes']:
        if covers(index, equality, ordering):
            return None, [f"O índice {index['name']} já é compatível com o filtro e a ordenação desta regra. Não foi sugerido outro equivalente."]
    if not any(n.get('Node Type') in {'Sort', 'Incremental Sort'} for n in iter_plan_nodes(document['Plan'])):
        return None, ['O plano já atende à ordenação sem uma etapa explícita de Sort; esta regra não propôs índice adicional.']
    keys = [quoted(col) for col in equality] + [
        f"{quoted(col)} {'DESC' if desc else 'ASC'} NULLS {'FIRST' if nulls else 'LAST'}"
        for col, desc, nulls in ordering]
    signature = repr((relation['schema'], relation['table'], equality, ordering))
    suffix = hashlib.sha256(signature.encode()).hexdigest()[:10]
    name = 'idx_tcc_filter_order_' + suffix
    ddl = f"CREATE INDEX {quoted(name)}\nON {quoted(relation['schema'])}.{quoted(relation['table'])} ({', '.join(keys)});"
    return dict(rule_id='filter_order_index', kind='index', title='Índice para filtro e ordenação',
                explanation='Um índice B-tree com as igualdades primeiro e a ordenação em seguida pode reduzir a busca e evitar uma ordenação separada. A consulta pode ser mantida.',
                evidence='O plano contém ordenação explícita; não foi encontrado índice B-tree completo compatível entre os índices válidos consultados.',
                conditions='Hipótese para teste: avaliar seletividade, frequência, espaço e custo nas escritas. Índices parciais ou de expressão existentes exigem avaliação adicional. O índice sugerido não foi criado.',
                sql=ddl, status='Pendente de criação e medição no ambiente experimental'), []


def recommend(connection, query, document):
    notes = []
    proposals = []
    try:
        tree = parse_supported(query)
        if tree is None:
            notes.append('A estrutura da consulta está fora do suporte das duas regras iniciais. A análise do plano continua disponível.')
        else:
            catalog = read_catalog(connection, tree)
            if not catalog:
                notes.append('Não foi possível resolver todas as tabelas comuns desta consulta. Nenhuma transformação foi proposta.')
            else:
                rewrite = year_rewrite(tree, catalog)
                if rewrite:
                    proposals.append(rewrite)
                index, index_notes = filter_order_index(tree, catalog, document)
                notes.extend(index_notes)
                if index:
                    proposals.append(index)
    except (SqlglotError, RecursionError):
        notes.append('O analisador de sintaxe não suporta esta consulta para recomendações. O plano do PostgreSQL permanece disponível.')
    return dict(proposals=proposals, notes=notes,
                rewrite_status='available' if any(p['kind'] == 'rewrite' for p in proposals) else 'not_identified',
                rules_evaluated=['date_year_range', 'filter_order_index'])
