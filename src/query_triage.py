"""Triagem explicável usando somente SQL registrado e métricas históricas."""
from pglast import ast, parse_sql
from pglast.parser import ParseError
from pglast.visitors import Visitor


def review_signal(record):
    if record.get('active') is False:
        return dict(needed=False, label='Fora do histórico atual', reasons=[], priority=0)
    reasons = []
    mean = record.get('mean_ms', 0)
    if mean >= 500:
        reasons.append(f'Tempo médio de {mean:.1f} ms, acima do limiar de triagem de 500 ms.')
    if record.get('share', 0) >= 20 and record.get('total_ms', 0) >= 1000 and record.get('calls', 0) >= 5:
        reasons.append('Pelo menos 20% do tempo acumulado, com 5 ou mais chamadas e pelo menos 1 segundo total.')
    if (record.get('temp_blks_written') or 0) > 0:
        reasons.append('Há escrita de blocos temporários nas execuções acumuladas.')
    if (record.get('shared_blks_read') or 0) >= 10000:
        reasons.append('Pelo menos 10.000 acessos de leitura de blocos acumulados; não equivale necessariamente a disco físico.')
    functions = set()
    class Functions(Visitor):
        def visit_FuncCall(self, ancestors, node):
            name = node.funcname[-1].sval
            if name in {'extract', 'lower'}:
                functions.add(name)
    try:
        tree = parse_sql(record.get('sql', ''))
        if len(tree) == 1 and isinstance(tree[0].stmt, ast.SelectStmt):
            statement = tree[0].stmt
            if statement.whereClause:
                Functions()(statement.whereClause)
    except (ParseError, RecursionError):
        pass
    if functions:
        reasons.append('Filtro com ' + ', '.join(sorted(n.upper() for n in functions)) +
                       ': possível padrão de reescrita; depende dos parâmetros, tipos e dados.')
    return dict(needed=bool(reasons), label='Revisão sugerida' if reasons else 'Sem sinal nesta triagem',
                reasons=reasons, priority=len(reasons),
                method='Triagem heurística, sem executar a consulta nem gerar uma proposta. Não garante ganho; ausência de sinal não comprova desempenho ótimo.')
