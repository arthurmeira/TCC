import unittest
from src.query_triage import review_signal


class TriageTests(unittest.TestCase):
    def test_parameterized_filter_is_flagged(self):
        r=review_signal({'sql':'SELECT * FROM pedidos WHERE EXTRACT($1 FROM data_pedido)=$2'})
        self.assertTrue(r['needed'])
        self.assertIn('EXTRACT', r['reasons'][0])

    def test_literals_and_projection_do_not_trigger(self):
        for sql in ["SELECT 'lower(email)' FROM clientes", 'SELECT lower(email) FROM clientes',
                    'SELECT * FROM clientes WHERE id=$1']:
            self.assertFalse(review_signal({'sql':sql})['needed'])

    def test_metrics_and_inactive(self):
        self.assertTrue(review_signal({'mean_ms':501})['needed'])
        self.assertFalse(review_signal({'mean_ms':501,'active':False})['needed'])
        self.assertFalse(review_signal({'share':100,'total_ms':2,'calls':1})['needed'])
        self.assertTrue(review_signal({'share':25,'total_ms':2000,'calls':10})['needed'])

    def test_invalid_sql_does_not_break_list(self):
        self.assertFalse(review_signal({'sql':'SELECT ('})['needed'])
