import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src import execution_logs as logs


class LogOriginTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = patch.object(logs, 'STORE', Path(self.tmp.name)/'logs.sqlite3')
        self.store.start()

    def tearDown(self):
        self.store.stop()
        self.tmp.cleanup()

    def ingest(self, name='test.json', database='tcc_sql_optimizer_logs'):
        return logs.import_logs(json.dumps([
            dict(dbname=database, timestamp='2026-11-06 10:00:00-03', message='duration: 10 ms statement: SELECT id FROM clientes WHERE id=1'),
            dict(dbname=database, timestamp='2026-11-06 10:01:00-03', message='duration: 600 ms statement: SELECT id FROM clientes WHERE id=2'),
        ]), name)

    def test_origin_tracks_slowest_event_and_file(self):
        batch=self.ingest()
        q=logs.list_queries()['queries'][0]
        self.assertEqual(q['calls'],2)
        self.assertEqual(q['selected_event']['duration_ms'],600)
        self.assertEqual(q['batches'][0]['source'],'test.json')
        origin=logs.log_origin(q['id'],q['selected_event']['id'],'Maior duração no lote',q['sql'])
        self.assertEqual(origin['content_sha256'],batch['id'])
        self.assertTrue(origin['original_matches_event'])
        self.assertEqual(origin['event']['sql'],'SELECT id FROM clientes WHERE id=2')
        self.assertEqual(origin['selection_reason'],'Maior duração no lote')

    def test_edit_is_not_claimed_as_exact_reproduction(self):
        self.ingest();q=logs.list_queries()['queries'][0]
        o=logs.log_origin(q['id'],q['selected_event']['id'],'Filtro revisado','SELECT id FROM clientes WHERE id=3')
        self.assertFalse(o['original_matches_event'])

    def test_wrong_event_missing_reason_foreign_database_rejected(self):
        self.ingest();q=logs.list_queries()['queries'][0]
        for event,reason in [('unknown','Teste'),(q['selected_event']['id'],''),(None,'Teste')]:
            with self.assertRaises(ValueError):logs.log_origin(q['id'],event,reason,q['sql'])
        self.ingest(database='another_database')
        q=next(q for q in logs.list_queries()['queries'] if q['database_name']=='another_database')
        with self.assertRaises(ValueError):logs.log_origin(q['id'],q['selected_event']['id'],'Teste',q['sql'])

    def test_multiple_batches_and_duplicate_import(self):
        self.ingest()
        self.assertTrue(self.ingest(name='renamed.json')['duplicate'])
        logs.import_logs(json.dumps(dict(dbname='tcc_sql_optimizer_logs',message='duration: 5 ms statement: SELECT id FROM clientes WHERE id=3')),'second.json')
        q=logs.list_queries()['queries'][0]
        self.assertEqual(q['calls'],3)
        self.assertEqual(len(q['batches']),2)
        self.assertEqual(q['selected_event']['duration_ms'],600)
