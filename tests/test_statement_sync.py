from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import psycopg

from src import execution_logs
from src.statement_sync import (synchronize, list_statements, get_statement, counter_delta,
                                bind_parameters, in_scope, query_shape)
from src.analyzer import validate_select


def record(calls=5, query_id="9223372036854775806", user_id="10", **extra):
    return dict(database_id="100",user_id=user_id,user_name="postgres",query_id=query_id,
                sql="SELECT id FROM clientes WHERE id=$1",calls=calls,total_exec_time=calls*2.,
                mean_exec_time=2.,rows=calls,shared_blks_hit=calls*3,shared_blks_read=calls,
                stats_since="2026-11-01T00:00:00+00:00",toplevel=True,database_name="tcc_sql_optimizer_logs",**extra)


def context(at,reset="same",source="cluster"):
    return dict(captured_at=f"2026-11-01T12:00:{at:02}+00:00",stats_reset=reset,source_key=source)


class StatementSyncTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.patch=patch.object(execution_logs,"STORE",Path(self.tmp.name)/"store.sqlite3")
        self.patch.start()

    def tearDown(self):
        self.patch.stop();self.tmp.cleanup()

    def sync(self,records,at,reset="same",source="cluster"):
        return synchronize(lambda:(deepcopy(records),context(at,reset,source)))

    def test_baseline_unchanged_and_exact_deltas_without_duplicates(self):
        self.assertEqual(self.sync([record()],0)["new"],1)
        first=list_statements()["queries"][0]
        self.assertFalse(first["delta"]["valid"])
        self.assertEqual(self.sync([record()],1)["unchanged"],1)
        changed=self.sync([record(8)],2)
        self.assertEqual(changed["new"],0);self.assertEqual(changed["updated"],1)
        self.assertEqual(changed["delta_calls"],3)
        queries=list_statements()["queries"]
        self.assertEqual(len(queries),1)
        self.assertEqual(queries[0]["id"],first["id"])
        self.assertEqual(queries[0]["delta"]["rows"],3)
        self.assertEqual(queries[0]["delta"]["total_exec_time"],6.)
        self.assertEqual(queries[0]["query_id"],"9223372036854775806")

    def test_different_users_are_not_merged(self):
        self.sync([record(),record(user_id="20")],0)
        self.assertEqual(len(list_statements()["queries"]),2)

    def test_recent_activity_changes_only_when_counters_change(self):
        self.sync([record()],0)
        self.sync([record()],1)
        item=list_statements()["queries"][0]
        self.assertEqual(item["last_activity"],context(0)["captured_at"])
        self.assertEqual(item["last_seen"],context(1)["captured_at"])
        self.sync([record(8)],2)
        self.sync([record(8)],3)
        self.assertEqual(list_statements()["queries"][0]["last_activity"],context(2)["captured_at"])

    def test_global_reset_partial_reset_and_counter_decrease(self):
        self.sync([record(10)],0)
        reset=self.sync([record(3)],1,reset="new-reset")
        self.assertTrue(reset["global_reset"])
        self.assertEqual(reset["restarted"],1)
        item=list_statements()["queries"][0]
        self.assertIsNone(item["delta"]["calls"])
        current=record(50);current["stats_since"]="2026-11-01T01:00:00+00:00"
        self.assertEqual(counter_delta(current,record(10))["reason"],"reset")
        self.assertEqual(counter_delta(record(1),record(10))["reason"],"reset")

    def test_missing_and_reappearing_entry_starts_new_baseline(self):
        self.sync([record()],0)
        self.assertEqual(self.sync([],1)["unavailable"],1)
        self.assertFalse(list_statements()["queries"][0]["active"])
        self.assertEqual(self.sync([record(20)],2)["restarted"],1)
        self.assertEqual(list_statements()["queries"][0]["delta"]["reason"],"reappeared")

    def test_stale_snapshot_cannot_overwrite_newer_metrics(self):
        self.sync([record(10)],2)
        with self.assertRaises(ValueError):self.sync([record(2)],1)
        self.assertEqual(list_statements()["queries"][0]["calls"],10)

    def test_failed_read_preserves_last_snapshot(self):
        self.sync([record()],0)
        def failure():raise ValueError("extension unavailable")
        with self.assertRaises(ValueError):synchronize(failure)
        self.assertEqual(list_statements()["queries"][0]["calls"],5)
        self.assertEqual(self.sync([record(6)],1)["updated"],1)

    def test_scope_handles_unqualified_names_ctes_and_ignores_metadata_and_strings(self):
        relations={("public","clientes"),("public","pedidos")}
        self.assertTrue(in_scope("SELECT * FROM clientes",relations))
        self.assertTrue(in_scope("WITH q AS (SELECT * FROM public.pedidos) SELECT count(*) FROM q",relations))
        self.assertFalse(in_scope("SELECT * FROM pg_catalog.pg_class",relations))
        self.assertFalse(in_scope("SELECT 'FROM clientes'",relations))
        self.assertFalse(in_scope("WITH q AS (DELETE FROM clientes RETURNING *) SELECT * FROM q",relations))

    def test_parameter_binding_preserves_strings_and_is_not_text_replacement(self):
        text=bind_parameters("SELECT '$1' AS literal FROM clientes WHERE email=$1 AND id=$2",["x'; DROP TABLE clientes; --",123])
        self.assertIn("'$1'",text)
        self.assertIn("x''; DROP TABLE clientes; --",text)
        self.assertEqual(query_shape(text)[1].parameters,set())
        validate_select(text)
        for values in [[],{},[1],[{},2]]:
            with self.subTest(values=values),self.assertRaises(ValueError):bind_parameters("SELECT $1,$2",values)

    def test_read_only_cte_supported_but_writes_rejected(self):
        validate_select("WITH c AS (SELECT id FROM clientes) SELECT * FROM c")
        with self.assertRaises(ValueError):validate_select("WITH c AS (UPDATE clientes SET ativo=false RETURNING *) SELECT * FROM c")

    def test_unavailable_plan_preserves_metrics_and_exportable_analysis(self):
        from src.webapp import investigate_statement
        item={**record(),"id":"pg:test","mean_ms":2.,"total_ms":10.,"share":10}
        with patch("src.webapp.get_statement",return_value=item),patch("src.webapp.analyze_query",side_effect=psycopg.errors.UndefinedFunction):
            result=investigate_statement({"id":"pg:test"})
        self.assertEqual(result["record"]["calls"],5)
        self.assertIsNone(result["analysis"])
        self.assertTrue(result["plan_error"])
        self.assertFalse(result["query_executed"])


if __name__=="__main__":unittest.main()
