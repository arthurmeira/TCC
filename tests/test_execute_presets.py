import unittest
from unittest.mock import MagicMock, patch

from src.optimization import executable_select
from src.webapp import execute_preset, presets


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
