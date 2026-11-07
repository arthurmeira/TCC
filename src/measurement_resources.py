"""Métricas de linhas, blocos e estimativas extraídas do plano PostgreSQL."""
import statistics


def resource_sample(document):
    root = document['Plan']
    nodes = []

    def walk(node, path):
        loops = node.get('Actual Loops', 0)
        nodes.append(dict(path=path, operation=node['Node Type'], relation=node.get('Relation Name'),
                          rows_per_loop=node.get('Actual Rows'), loops=loops,
                          rows_emitted=node.get('Actual Rows', 0) * loops,
                          rows_removed_by_filter=node.get('Rows Removed by Filter', 0) * loops))
        for i, child in enumerate(node.get('Plans', [])):
            walk(child, f'{path}.{i}')

    walk(root, '0')
    return dict(shared_hits=root.get('Shared Hit Blocks', 0), shared_reads=root.get('Shared Read Blocks', 0),
                temp_reads=root.get('Temp Read Blocks', 0), temp_writes=root.get('Temp Written Blocks', 0),
                estimated_cost=root.get('Total Cost'), estimated_rows=root.get('Plan Rows'),
                actual_output_rows=root.get('Actual Rows', 0) * root.get('Actual Loops', 0), nodes=nodes)


def summarize_resources(samples):
    keys = ('shared_hits', 'shared_reads', 'temp_reads', 'temp_writes',
            'estimated_cost', 'estimated_rows', 'actual_output_rows')
    return dict(samples=samples, medians={k: statistics.median([s[k] for s in samples])
                if all(s[k] is not None for s in samples) else None for k in keys})
