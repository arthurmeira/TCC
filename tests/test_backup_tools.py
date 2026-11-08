"""Proteções dos utilitários; sem alterar PostgreSQL ou histórico real."""
import json
from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import MagicMock, patch
from types import SimpleNamespace

from scripts import backup_databases as backups
from scripts import reproduce_experiment as reproduction


class BackupToolTests(unittest.TestCase):
    def test_create_refuses_existing_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch.object(backups.psycopg, 'connect') as connect:
                with self.assertRaises(FileExistsError):
                    backups.create(SimpleNamespace(bundle=temp), {})
                connect.assert_not_called()

    def test_restore_refuses_existing_database_before_pg_restore(self):
        cursor = MagicMock()
        cursor.fetchone.return_value = (1,)
        connection = MagicMock()
        connection.cursor.return_value.__enter__.return_value = cursor
        with patch.object(backups, 'load_bundle', return_value={}), patch.object(backups, 'run_pg') as run:
            with patch.object(backups.psycopg, 'connect') as connect:
                connect.return_value.__enter__.return_value = connection
                with self.assertRaisesRegex(ValueError, 'já existe'):
                    backups.restore_new(SimpleNamespace(bundle='.'), {}, 'existing')
                run.assert_not_called()
                self.assertEqual(cursor.execute.call_count, 1)

    def test_restore_refuses_existing_sqlite_before_database_creation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'results').mkdir()
            existing = root / 'results' / 'logs.sqlite3'
            existing.write_bytes(b'keep original')
            with patch.object(backups, 'PROJECT_ROOT', root), patch.object(backups, 'load_bundle', return_value={'files': {'logs.sqlite3': {}}}), patch.object(backups, 'restore_new') as restore:
                with self.assertRaisesRegex(ValueError, 'histórico'):
                    backups.restore(SimpleNamespace(bundle=temp), {})
                restore.assert_not_called()
            self.assertEqual(existing.read_bytes(), b'keep original')

    def test_manifest_rejects_changed_file(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'data').write_bytes(b'changed')
            (root / 'manifest.json').write_text(json.dumps({'database': 'tcc_sql_optimizer_logs', 'files': {'data': {'sha256': 'wrong'}}}))
            with self.assertRaisesRegex(ValueError, 'SHA-256'):
                backups.load_bundle(root)

    def test_manifest_rejects_escape_from_bundle(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'manifest.json').write_text(json.dumps({'database': 'tcc_sql_optimizer_logs', 'files': {'../outside': {'sha256': 'wrong'}}}))
            with self.assertRaises(ValueError):
                backups.load_bundle(root)

    def test_sqlite_backup_is_complete_and_valid(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'store.sqlite3'
            with closing(sqlite3.connect(path)) as db:
                db.execute('CREATE TABLE experiments(id TEXT)')
                db.execute("INSERT INTO experiments VALUES ('sample')")
                db.commit()
            self.assertEqual(backups.sqlite_info(path), {'integrity': 'ok', 'tables': {'experiments': 1}})

    def test_new_experiment_never_overwrites_output(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'round.json'
            path.write_text('original')
            with self.assertRaises(FileExistsError):
                reproduction.run(path)
            self.assertEqual(path.read_text(), 'original')

    def test_failed_verification_does_not_drop_database(self):
        with patch.object(backups, 'restore_new', side_effect=ValueError('failed')), patch.object(backups.psycopg, 'connect') as connect:
            with self.assertRaises(ValueError):
                backups.verify(SimpleNamespace(bundle='.'), {})
            connect.assert_not_called()
