"""Confere a rodada salva ou executa os 12 exemplos pelo benchmark atual."""
import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import statistics

from src.config import PROJECT_ROOT


def check_saved(path):
    data = json.loads(path.read_text(encoding='utf-8'))
    cases = data['cases']
    if [c['id'] for c in cases] != [f'C{i:02}' for i in range(1, 13)]:
        raise ValueError('Esperados C01 a C12, nesta ordem.')
    total = 0
    print('Caso | Original (ms) | Alternativa (ms) | Variação da média')
    for case in cases:
        if case.get('equivalent') is not True:
            raise ValueError('Caso sem correspondência validada: ' + case['id'])
        means = []
        for label in ('original', 'alternative'):
            metric = case['metrics'][label]
            samples = metric['samples_ms']
            if len(samples) != 10 or metric['calls'] != 10:
                raise ValueError('Esperadas dez amostras por versão.')
            mean = statistics.mean(samples)
            if not math.isclose(mean, metric['mean_ms'], rel_tol=1e-10):
                raise ValueError('Média inconsistente: ' + case['id'])
            means.append(mean)
            total += len(samples)
        before, after = means
        print(f"{case['id']} | {before:.4f} | {after:.4f} | {(after/before-1)*100:+.2f}%")
    print(f'{total} amostras conferidas. Sem conexão ao PostgreSQL e sem alterações no histórico.')


def run(output):
    from src.benchmark import benchmark
    from src.demo_queries import DEMO_QUERIES
    from src.optimization import propose
    output.parent.mkdir(parents=True, exist_ok=True)
    # Reserva exclusiva; se falhar, o arquivo parcial e os relatórios já salvos permanecem.
    with output.open('x', encoding='utf-8') as stream:
        data = dict(started_at=datetime.now(timezone.utc).isoformat(),
                    method='Nova rodada: 10 medições por versão; regras atuais; fonte exemplos locais.', cases=[])
        def persist():
            stream.seek(0)
            json.dump(data, stream, ensure_ascii=False, indent=2)
            stream.truncate()
            stream.flush()
        persist()
        for case in DEMO_QUERIES:
            proposals = propose(case['sql'])
            if len(proposals) != 1:
                raise ValueError('Esperada uma proposta para ' + case['id'])
            proposal = proposals[0]
            print('Medindo', case['id'], flush=True)
            report = benchmark(case['sql'], proposal['alternative'], calls=10, rule=proposal['id'])
            data['cases'].append(dict(id=case['id'], title=case['title'], sql=case['sql'],
                alternative_sql=proposal['alternative'], report_id=report['id'],
                equivalent=report['equivalent'], metrics=report['metrics'],
                reduction_pct=report['reduction_pct'], environment=report['environment']))
            persist()
        data['finished_at'] = datetime.now(timezone.utc).isoformat()
        persist()
    print('Nova rodada salva em', output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--check-saved', type=Path, help='Recalcula médias sem executar SQL.')
    mode.add_argument('--run', action='store_true', help='Executa SQL e acrescenta 12 avaliações ao SQLite.')
    parser.add_argument('--output', type=Path, help='Arquivo novo da rodada; nunca sobrescrito.')
    args = parser.parse_args()
    if args.check_saved:
        check_saved(args.check_saved)
    else:
        output = args.output or PROJECT_ROOT / 'results' / ('rodada_reproduzida_' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '.json')
        run(output)


if __name__ == '__main__':
    main()
