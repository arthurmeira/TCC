import unittest
from unittest.mock import MagicMock, patch

from src.optimization import executable_select
from src.webapp import execute_preset, execute_read_query, presets


class ExecutePresetsTests(unittest.TestCase):
    def test_all_twelve_presets_are_accepted_selects(self):
        examples = presets()['queries']
        self.assertEqual(len(examples), 12)
        for example in examples:
            with self.subTest(id=example['id']):
                self.assertTrue(executable_select(example['sql']).startswith('SELECT'))

    def test_unknown_identifier_does_not_connect(self):
        with patch('src.webapp.get_connection') as connect:
            for identifier in ('DELETE FROM clientes', '', None, 'Q99'):
                with self.subTest(identifier=identifier), self.assertRaises(ValueError):
                    execute_preset(identifier)
            connect.assert_not_called()

    def test_executes_once_in_read_only_transaction(self):
        connection = MagicMock()
        cursor = connection.cursor.return_value.__enter__.return_value
        cursor.stream.return_value = iter([(1,), (2,)])
        with patch('src.webapp.get_connection') as connect:
            connect.return_value.__enter__.return_value = connection
            result = execute_preset('C01')
        self.assertTrue(connection.read_only)
        self.assertEqual(result['rows'], 2)
        self.assertEqual(cursor.stream.call_count, 1)

    def test_custom_query_uses_read_only_execution(self):
        connection = MagicMock()
        cursor = connection.cursor.return_value.__enter__.return_value
        cursor.stream.return_value = iter([(1,)])
        with patch('src.webapp.get_connection') as connect:
            connect.return_value.__enter__.return_value = connection
            result = execute_read_query('SELECT id FROM public.clientes')
        self.assertTrue(connection.read_only)
        self.assertEqual(result['rows'], 1)
        self.assertEqual(cursor.stream.call_count, 1)

    def test_custom_rejects_unsafe_sql_before_connecting(self):
        with patch('src.webapp.get_connection') as connect:
            for query in (None, '', 'DELETE FROM public.clientes', 'SELECT pg_sleep(1)', 'SELECT * FROM public.clientes FOR UPDATE'):
                with self.subTest(query=query), self.assertRaises(ValueError):
                    execute_read_query(query)
            connect.assert_not_called()
