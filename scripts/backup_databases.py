"""Backups portáveis e restauração protegida. Execute como módulo; veja --help."""
from __future__ import annotations

import argparse
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import uuid

import psycopg
from psycopg import sql
from src.config import PROJECT_ROOT, get_database_config

TABLES = ('clientes', 'produtos', 'pedidos', 'itens_pedido', 'pagamentos')


def sha256(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def write_json(path, value):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)


def binary(args, name):
    path = Path(args.pg_bin) / (name + ('.exe' if os.name == 'nt' else '')) if args.pg_bin else shutil.which(name)
    if not path or not Path(path).is_file():
        raise ValueError(f'{name} não encontrado. Informe --pg-bin com a pasta bin do PostgreSQL 18.')
    return str(path)


def run_pg(args, cfg, name, options):
    # A senha não integra argumentos, arquivos de relatório nem mensagens.
    env = os.environ.copy()
    env.update(PGHOST=cfg['host'], PGPORT=str(cfg['port']), PGUSER=cfg['user'],
               PGPASSWORD=cfg['password'], PGCONNECT_TIMEOUT=str(cfg['connect_timeout']))
    result = subprocess.run([binary(args, name), *options], env=env, capture_output=True)
    if result.returncode:
        error = result.stderr.decode('utf-8', errors='replace').replace(cfg['password'], '[oculto]')
        raise RuntimeError(f'{name} falhou ({result.returncode}): {error}')
    return result.stdout


def inventory(connection):
    """Compara todas as linhas via COPY binário ordenado, além de estruturas."""
    tables = {}
    with connection.cursor() as cur:
        for name in TABLES:
            cur.execute(sql.SQL('SELECT count(*) FROM public.{}').format(sql.Identifier(name)))
            count = cur.fetchone()[0]
            digest = hashlib.sha256()
            with cur.copy(sql.SQL('COPY (SELECT * FROM public.{} ORDER BY id) TO STDOUT (FORMAT BINARY)').format(sql.Identifier(name))) as copy:
                for chunk in copy:
                    digest.update(chunk)
            tables[name] = {'rows': count, 'copy_binary_sha256': digest.hexdigest()}
        cur.execute("SELECT indexname,indexdef FROM pg_indexes WHERE schemaname='public' ORDER BY indexname")
        indexes = cur.fetchall()
        cur.execute("""SELECT c.relname,k.conname,k.contype,pg_get_constraintdef(k.oid)
            FROM pg_constraint k JOIN pg_class c ON c.oid=k.conrelid
            JOIN pg_namespace n ON n.oid=c.relnamespace
            WHERE n.nspname='public' ORDER BY c.relname,k.conname""")
        constraints = cur.fetchall()
        cur.execute("""SELECT table_name,column_name,data_type,is_nullable,column_default,is_identity,identity_generation
            FROM information_schema.columns WHERE table_schema='public'
            AND table_name=ANY(%s) ORDER BY table_name,ordinal_position""", (list(TABLES),))
        columns = cur.fetchall()
        sequences = {}
        for name in TABLES:
            cur.execute('SELECT pg_get_serial_sequence(%s, %s)', ('public.' + name, 'id'))
            sequence = cur.fetchone()[0]
            if sequence:
                cur.execute(sql.SQL('SELECT last_value,is_called FROM {}').format(sql.Identifier(*sequence.split('.'))))
                sequences[sequence] = cur.fetchone()
        cur.execute('SELECT extname,extversion FROM pg_extension ORDER BY extname')
        extensions = cur.fetchall()
    return json.loads(json.dumps(dict(tables=tables, indexes=indexes, constraints=constraints,
                                      columns=columns, sequences=sequences, extensions=extensions)))


def sqlite_info(path):
    with closing(sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True)) as db:
        integrity = db.execute('PRAGMA integrity_check').fetchall()
        if integrity != [('ok',)]:
            raise ValueError('SQLite não passou no integrity_check.')
        if db.execute('PRAGMA foreign_key_check').fetchall():
            raise ValueError('SQLite contém violação de chave estrangeira.')
        names = db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
        counts = {name: db.execute('SELECT count(*) FROM "' + name.replace('"', '""') + '"').fetchone()[0] for name, in names}
    return dict(integrity='ok', tables=counts)


def create(args, cfg):
    folder = Path(args.bundle).resolve()
    folder.mkdir(parents=True, exist_ok=False)
    print('Gerando backup em', folder, flush=True)
    with psycopg.connect(**cfg) as conn:
        conn.read_only = True
        conn.isolation_level = psycopg.IsolationLevel.REPEATABLE_READ
        with conn.cursor() as cur:
            cur.execute('SELECT pg_export_snapshot(),current_setting(\'server_version\')')
            snapshot, version = cur.fetchone()
            cur.execute("SELECT pg_encoding_to_char(encoding),datcollate,datctype FROM pg_database WHERE datname=current_database()")
            locale = cur.fetchone()
        before = inventory(conn)
        print('Inventário e assinaturas de todas as linhas obtidos.', flush=True)
        run_pg(args, cfg, 'pg_dump', ['--no-password', '--format=custom', '--no-owner', '--no-privileges',
            '--snapshot=' + snapshot, '--file=' + str(folder / 'postgresql.dump'), '--dbname=' + cfg['dbname']])
    toc = run_pg(args, cfg, 'pg_restore', ['--list', str(folder / 'postgresql.dump')])
    (folder / 'postgresql.toc.txt').write_bytes(toc)
    source = PROJECT_ROOT / 'results' / 'logs.sqlite3'
    if not source.is_file():
        raise ValueError('results/logs.sqlite3 não encontrado; pacote incompleto.')
    with closing(sqlite3.connect(source.resolve().as_uri() + '?mode=ro', uri=True)) as src:
        with closing(sqlite3.connect(folder / 'logs.sqlite3')) as dst:
            src.backup(dst)
    history = sqlite_info(folder / 'logs.sqlite3')
    for path in (PROJECT_ROOT / 'results').glob('rodada_*.json'):
        shutil.copy2(path, folder / path.name)
    logs = PROJECT_ROOT / 'results' / 'log_sources'
    if logs.is_dir():
        shutil.copytree(logs, folder / 'log_sources')
    manifest = dict(format_version=1, created_at=datetime.now(timezone.utc).isoformat(),
        database=cfg['dbname'], postgresql_version=version, source_locale=locale,
        postgres=before, sqlite=history,
        notes=['Dump lógico completo do banco, sem owners/ACLs e sem roles/senhas.',
               'Contadores ativos de pg_stat_statements não são transportados.',
               'SQLite consistente via Backup API; PostgreSQL via snapshot exportado.',
               'As duas cópias são consistentes individualmente, não uma transação distribuída.'],
        files={p.relative_to(folder).as_posix(): {'bytes': p.stat().st_size, 'sha256': sha256(p)}
               for p in sorted(folder.rglob('*')) if p.is_file()})
    write_json(folder / 'manifest.json', manifest)
    print('Backup criado; execute verify para testar a restauração completa.', flush=True)


def load_bundle(folder):
    manifest = json.loads((folder / 'manifest.json').read_text(encoding='utf-8'))
    if manifest['database'] != 'tcc_sql_optimizer_logs':
        raise ValueError('Nome de banco inesperado no manifesto.')
    for name, expected in manifest['files'].items():
        path = (folder / name).resolve()
        if not path.is_relative_to(folder) or not path.is_file() or sha256(path) != expected['sha256']:
            raise ValueError('Arquivo ausente ou SHA-256 diferente: ' + name)
    if sqlite_info(folder / 'logs.sqlite3') != manifest['sqlite']:
        raise ValueError('Inventário SQLite diferente do manifesto.')
    return manifest


def restore_new(args, cfg, target):
    folder = Path(args.bundle).resolve()
    manifest = load_bundle(folder)
    admin_cfg = dict(cfg, dbname='postgres')
    with psycopg.connect(**admin_cfg, autocommit=True) as admin:
        with admin.cursor() as cur:
            cur.execute('SELECT 1 FROM pg_database WHERE datname=%s', (target,))
            if cur.fetchone():
                raise ValueError('Restauração recusada: o banco de destino já existe: ' + target)
            cur.execute(sql.SQL('CREATE DATABASE {} WITH TEMPLATE template0 ENCODING \'UTF8\'').format(sql.Identifier(target)))
    print('Banco novo criado:', target, flush=True)
    # Em caso de erro, o banco novo é preservado para diagnóstico, nunca recriado.
    run_pg(args, cfg, 'pg_restore', ['--no-password', '--exit-on-error', '--single-transaction',
        '--no-owner', '--no-privileges', '--dbname=' + target, str(folder / 'postgresql.dump')])
    with psycopg.connect(**dict(cfg, dbname=target)) as conn:
        conn.read_only = True
        actual = inventory(conn)
    if actual != manifest['postgres']:
        raise ValueError('Inventário restaurado divergiu (dados, estruturas, sequências ou versões das extensões). Banco novo preservado: ' + target)
    with psycopg.connect(**dict(cfg, dbname=target), autocommit=True) as conn:
        conn.execute('ANALYZE')
    return manifest


def verify(args, cfg):
    target = 'tcc_restore_check_' + uuid.uuid4().hex[:12]
    restore_new(args, cfg, target)
    # Remove exclusivamente o banco aleatório que esta execução criou e verificou.
    with psycopg.connect(**dict(cfg, dbname='postgres'), autocommit=True) as conn:
        conn.execute(sql.SQL('DROP DATABASE {}').format(sql.Identifier(target)))
    report = dict(verified_at=datetime.now(timezone.utc).isoformat(), status='passed',
        checks=['pg_restore real em banco novo', 'SHA-256 de todas as linhas via COPY binário ordenado',
                'contagens, índices, constraints, colunas, sequências e extensões',
                'SQLite integrity_check, foreign_key_check e contagens', 'SHA-256 dos arquivos'],
        temporary_database_removed=True)
    path = Path(args.bundle) / ('verification_' + uuid.uuid4().hex[:8] + '.json')
    write_json(path, report)
    print('Restauração integral verificada; banco temporário removido. Relatório:', path, flush=True)


def restore(args, cfg):
    results = PROJECT_ROOT / 'results'
    folder = Path(args.bundle).resolve()
    manifest = load_bundle(folder)
    names = [n for n in manifest['files'] if n == 'logs.sqlite3' or n.startswith('log_sources/') or n.startswith('rodada_')]
    if any((results / n).exists() for n in names) or any((results / n).exists() for n in ('logs.sqlite3-wal', 'logs.sqlite3-shm')):
        raise ValueError('Restauração recusada: já existem arquivos de histórico em results. Use um clone novo e encerre a aplicação.')
    restore_new(args, cfg, cfg['dbname'])
    for name in names:
        dst = results / name
        dst.parent.mkdir(parents=True, exist_ok=True)
        with (folder / name).open('rb') as src, dst.open('xb') as out:
            shutil.copyfileobj(src, out)
    print('PostgreSQL e histórico SQLite restaurados. Inicie python -m src.webapp --open.', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['create', 'verify', 'restore'])
    parser.add_argument('--bundle', required=True, help='Diretório do pacote (novo para create).')
    parser.add_argument('--pg-bin', help='Pasta de pg_dump e pg_restore; omitida se estão no PATH.')
    args = parser.parse_args()
    try:
        globals()[args.action](args, get_database_config())
    except Exception as exc:
        # Nunca exibe traceback nem configuração de conexão.
        password = os.environ.get('DB_PASSWORD', '')
        message = str(exc).replace(password, '[oculto]') if password else str(exc)
        print('Falha:', message)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
