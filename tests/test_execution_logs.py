import csv
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from src import execution_logs as logs
from src.optimization import executable_select, propose


class ExecutionLogsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.patch = patch.object(logs, "STORE", Path(self.tmp.name)/"logs.sqlite3")
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        self.tmp.cleanup()

    def test_multiline_and_literals_group_without_losing_individual_durations(self):
        content = ("2026-10-31 10:00:00 -03 LOG: duration: 4.5 ms statement: SELECT id\nFROM public.clientes WHERE id=1;\n"
                   "2026-10-31 10:00:01 -03 LOG: duration: 2.0 ms execute <unnamed>: SELECT id FROM public.clientes WHERE id=2;\n"
                   "2026-10-31 10:00:02 -03 LOG: duration: 0.4 ms parse <unnamed>: SELECT id FROM public.clientes WHERE id=2;\n")
        self.assertEqual(logs.import_logs(content,"sample.log")["accepted"],2)
        result=logs.list_queries()
        self.assertEqual(len(result["queries"]),1)
        self.assertEqual(result["calls"],2)
        self.assertEqual(result["total_ms"],6.5)
        self.assertEqual(result["queries"][0]["variants"],2)
        self.assertTrue(logs.import_logs(content,"renamed.log")["duplicate"])
        self.assertEqual(logs.list_queries()["calls"],2)
        source=next((Path(self.tmp.name)/"log_sources").iterdir())
        self.assertEqual(source.read_bytes(),content.encode("utf-8"))
        self.assertTrue(logs.import_logs(source.read_bytes().decode("utf-8"),source.name)["duplicate"])

    def test_native_json_and_csv_and_portuguese_execute(self):
        record={"timestamp":"2026-10-31 10:00:00-03", "dbname":"test", "message":"duração: 12.3 ms executar <unnamed>: SELECT 1"}
        logs.import_logs(json.dumps(record),"native.jsonl")
        row=[""]*26;row[0]="2026-10-31";row[2]="test";row[13]="duration: 8.2 ms statement: SELECT 2"
        data=io.StringIO();csv.writer(data).writerow(row)
        logs.import_logs(data.getvalue(),"native.csv")
        result=logs.list_queries()
        self.assertEqual(result["calls"],2)
        self.assertAlmostEqual(result["total_ms"],20.5)

    def test_empty_or_malformed_import_never_adds_partial_records(self):
        with self.assertRaises(ValueError): logs.import_logs('duration: 1 ms statement: DELETE FROM clientes',"empty.log")
        with self.assertRaises(ValueError): logs.import_logs('{invalid',"bad.json")
        self.assertEqual(logs.list_queries()["calls"],0)

    def test_identical_sql_from_different_databases_is_not_merged(self):
        records=[dict(dbname=name,message="duration: 2 ms statement: SELECT 1") for name in ("database_a","database_b")]
        logs.import_logs(json.dumps(records),"two-databases.json")
        self.assertEqual(len(logs.list_queries()["queries"]),2)

    def test_execution_rejects_side_effects_and_unbound_parameters(self):
        for query in ["SELECT pg_sleep(30)","SELECT public.custom_fn()", "SELECT * INTO other FROM public.clientes", "SELECT * FROM public.clientes FOR UPDATE", "SELECT * FROM public.clientes WHERE id=$1", "WITH q AS (DELETE FROM clientes RETURNING *) SELECT * FROM q"]:
            with self.subTest(query=query), self.assertRaises(ValueError): executable_select(query)
        self.assertIn("SELECT",executable_select("SELECT count(*) FROM public.clientes"))

    def test_no_rewrite_inside_literals_or_for_unsupported_boolean_expression(self):
        with patch("src.optimization.get_connection") as connection:
            self.assertEqual(propose("SELECT 'LOWER(email) = test' FROM public.clientes"),[])
            self.assertEqual(propose("SELECT * FROM public.clientes WHERE LOWER(email)='x' OR ativo=true"),[])
            connection.assert_not_called()


if __name__ == "__main__": unittest.main()
