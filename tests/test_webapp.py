"""Contrato HTTP local: validação, isolamento e erros, sem acessar PostgreSQL."""

import http.client
import json
import threading
import unittest
from unittest.mock import patch

import psycopg

from src.webapp import Handler, LocalServer


class QuietHandler(Handler):
    def log_message(self, *_args):
        pass


class WebappTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = LocalServer(("127.0.0.1", 0), QuietHandler)
        cls.port = cls.server.server_port
        cls.server.allowed_hosts = {f"127.0.0.1:{cls.port}", f"localhost:{cls.port}"}
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def request(self, path, payload=None, headers=None, raw=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        defaults = {"Content-Type": "application/json", "X-TCC-Client": "local"}
        defaults.update(headers or {})
        body = raw if raw is not None else json.dumps(payload) if payload is not None else None
        try:
            connection.request("POST" if body is not None else "GET", path, body, defaults)
            response = connection.getresponse()
            content = response.read()
            return response.status, content, dict(response.getheaders())
        finally:
            connection.close()

    def test_static_allowlist_does_not_expose_project_files(self):
        self.assertEqual(self.request("/")[0], 200)
        for path in ("/.env", "/.env.local", "/../.env", "/%2e%2e/.env", "/src/config.py"):
            with self.subTest(path=path):
                self.assertEqual(self.request(path)[0], 404)

    def test_report_sql_formatting_preserves_original_and_handles_invalid_sql(self):
        saved = [{"original_sql": "select id from public.clientes where id = 1", "alternative_sql": "SELECT ('"}]
        with patch("src.webapp.reports", return_value=saved):
            status, content, _ = self.request("/api/reports")
        result = json.loads(content)
        self.assertEqual(status, 200)
        self.assertEqual(result["reports"], saved)
        self.assertIn("\n", result["formatted_sql"][0]["original"])
        self.assertEqual(result["formatted_sql"][0]["alternative"], "SELECT ('")

    def test_only_one_server_can_listen_on_the_port(self):
        with self.assertRaises(OSError):
            duplicate = LocalServer(("127.0.0.1", self.port), QuietHandler)
            duplicate.server_close()

    def test_foreign_host_and_origin_are_rejected_before_analysis(self):
        with patch("src.webapp.analyze_query") as analyze:
            for headers in ({"Host": "example.org"}, {"Origin": "https://example.org"},
                            {"X-TCC-Client": ""}):
                with self.subTest(headers=headers):
                    self.assertEqual(self.request("/api/analyze", {"sql": "SELECT 1"}, headers)[0], 403)
            analyze.assert_not_called()

    def test_invalid_inputs_never_reach_database_analysis(self):
        inputs = [[], {}, {"sql": 1}, {"sql": ""}, {"sql": "DELETE FROM public.clientes"},
                  {"sql": "SELECT 1; SELECT 2"}, {"sql": "SELECT 1 INTO teste"},
                  {"sql": "SELECT 'literal incompleto"}, {"sql": "SELECT 1 /* incompleto"}]
        with patch("src.webapp.analyze_query") as analyze:
            for payload in inputs:
                with self.subTest(payload=payload):
                    self.assertEqual(self.request("/api/analyze", payload)[0], 400)
            self.assertEqual(self.request("/api/analyze", raw="{")[0], 400)
            self.assertEqual(self.request("/api/analyze", raw="x" * 65537)[0], 400)
            analyze.assert_not_called()

    def test_compare_validates_both_inputs_before_planning_either(self):
        with patch("src.webapp.analyze_query") as analyze:
            status, _, _ = self.request("/api/compare", {"original": "SELECT 1", "alternative": "DROP TABLE clientes"})
            self.assertEqual(status, 400)
            analyze.assert_not_called()

    def test_literal_semicolons_are_accepted_and_bigint_is_preserved(self):
        result = {"query_id": "6996977888698455443", "query_executed": False}
        sql = "/* exemplo */ SELECT ';' AS texto; -- comentário"
        with patch("src.webapp.analyze_query", return_value=result) as analyze:
            status, body, headers = self.request("/api/analyze", {"sql": sql})
            self.assertEqual(status, 200)
            self.assertEqual(json.loads(body), result)
            self.assertEqual(headers["Cache-Control"], "no-store")
            analyze.assert_called_once_with(sql)

    def test_database_errors_are_actionable_without_exposing_details(self):
        errors = [(psycopg.OperationalError("secret database password"), 503),
                  (psycopg.errors.SyntaxError("secret SQL"), 400),
                  (psycopg.errors.QueryCanceled("secret SQL"), 408)]
        for error, expected in errors:
            with self.subTest(error=type(error).__name__):
                with patch("src.webapp.analyze_query", side_effect=error):
                    status, body, _ = self.request("/api/analyze", {"sql": "SELECT 1"})
                    self.assertEqual(status, expected)
                    self.assertNotIn(b"secret", body)
                    self.assertTrue(json.loads(body)["error"])

    def test_sync_is_manual_and_requires_local_origin(self):
        with patch("src.webapp.synchronize",return_value={"new":5,"updated":0}) as sync:
            self.assertEqual(self.request("/api/statements/sync",{},headers={"Origin":"https://outside.example"})[0],403)
            sync.assert_not_called()
            status,body,_=self.request("/api/statements/sync",{})
            self.assertEqual(status,200)
            self.assertEqual(json.loads(body)["new"],5)
            sync.assert_called_once_with()

if __name__ == "__main__":
    unittest.main()
