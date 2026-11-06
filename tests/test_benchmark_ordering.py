import unittest
from types import SimpleNamespace

from src.benchmark import result_signature, ordering_columns


class Cursor:
    description = [SimpleNamespace(name='id', type_code=23), SimpleNamespace(name='total', type_code=1700)]
    def __init__(self, rows): self.rows = rows
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def stream(self, *args, **kwargs): return iter(self.rows)


class Connection:
    def __init__(self, rows): self.rows = rows
    def cursor(self): return Cursor(self.rows)


class OrderingTests(unittest.TestCase):
    query = 'SELECT id, sum(valor) AS total FROM pedidos GROUP BY id ORDER BY total DESC'
    def signature(self, rows, query=None):
        return result_signature(Connection(rows), query or self.query, True)

    def test_ties_can_change_position(self):
        self.assertEqual(self.signature([(1, 10), (2, 10), (3, 5)]),
                         self.signature([(2, 10), (1, 10), (3, 5)]))

    def test_non_tied_order_and_data_changes_are_rejected(self):
        baseline = self.signature([(1, 10), (2, 10), (3, 5)])
        for rows in [[(3, 5), (1, 10), (2, 10)], [(1, 10), (1, 10), (3, 5)], [(1, 10), (2, 10)]]:
            self.assertNotEqual(baseline, self.signature(rows))

    def test_secondary_key_preserved(self):
        query = self.query + ', id'
        self.assertNotEqual(self.signature([(1, 10), (2, 10)], query),
                            self.signature([(2, 10), (1, 10)], query))

    def test_resolution_and_strict_fallback(self):
        self.assertEqual(ordering_columns(self.query), [1])
        self.assertEqual(ordering_columns('SELECT id, total FROM pedidos ORDER BY 2, 1'), [1, 0])
        self.assertIsNone(ordering_columns('SELECT * FROM pedidos ORDER BY total'))
        self.assertIsNone(ordering_columns('SELECT id FROM pedidos ORDER BY total'))
        self.assertNotEqual(self.signature([(1, 10), (2, 10)], 'SELECT * FROM pedidos ORDER BY total'),
                            self.signature([(2, 10), (1, 10)], 'SELECT * FROM pedidos ORDER BY total'))
