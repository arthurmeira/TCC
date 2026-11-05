"""Regras: limites semânticos, índices equivalentes e abstenção."""
import unittest
from unittest.mock import patch
from sqlglot import parse_one
from src.recommendations import (
    parse_supported, year_rewrite, filter_order_index, recommend, covers,
)


def catalog(typ='timestamp'):
    return {'p': {'schema': 'public', 'table': 'pedidos',
                  'columns': {'id': 'int8', 'cliente_id': 'int8', 'data_pedido': typ},
                  'indexes': []}}


class RecommendationTests(unittest.TestCase):
    def test_year_rewrite_preserves_projection_join_and_other_predicates(self):
        q = parse_supported("SELECT p.id FROM public.pedidos p JOIN public.clientes c ON c.id=p.cliente_id WHERE EXTRACT(YEAR FROM p.data_pedido)=2026 AND p.cliente_id=42 ORDER BY p.id")
        r = year_rewrite(q, catalog())
        alternate = parse_one(r['sql'], read='postgres')
        self.assertEqual(q.expressions, alternate.expressions)
        self.assertEqual(q.args['joins'], alternate.args['joins'])
        self.assertEqual(q.args['order'], alternate.args['order'])
        self.assertIn('p.cliente_id = 42', r['sql'])
        self.assertIn('2027-01-01', r['sql'])
        self.assertIn('EXTRACT', q.sql())  # Entrada não foi modificada.

    def test_year_rewrite_rejects_unsupported_semantics(self):
        for condition in ["EXTRACT(YEAR FROM data_pedido)=0", "EXTRACT(YEAR FROM data_pedido)=9999",
                          "EXTRACT(YEAR FROM data_pedido)=2026.5", "EXTRACT(YEAR FROM data_pedido)=$1",
                          "EXTRACT(MONTH FROM data_pedido)=1", "EXTRACT(YEAR FROM data_pedido)='2026'",
                          "EXTRACT(YEAR FROM data_pedido)=2026 OR id=1"]:
            with self.subTest(condition=condition):
                q = parse_supported('SELECT * FROM public.pedidos p WHERE ' + condition)
                self.assertIsNone(year_rewrite(q, catalog()))
        q = parse_supported('SELECT * FROM public.pedidos p WHERE EXTRACT(YEAR FROM data_pedido)=2026')
        for typ in ['timestamptz', 'text', 'unsupported']:
            self.assertIsNone(year_rewrite(q, catalog(typ)))

    def test_date_and_reversed_equality(self):
        q = parse_supported('SELECT id FROM public.pedidos p WHERE 2024=EXTRACT(YEAR FROM data_pedido)')
        self.assertIn("AS DATE", year_rewrite(q, catalog('date'))['sql'])

    def test_literals_comments_and_ambiguous_columns_are_not_rewritten(self):
        q = parse_supported("SELECT 'EXTRACT(YEAR FROM data_pedido)=2026' FROM public.pedidos p /* EXTRACT(YEAR FROM data_pedido)=2026 */")
        self.assertIsNone(year_rewrite(q, catalog()))
        q = parse_supported('SELECT * FROM public.pedidos p JOIN public.pedidos other ON p.id=other.id WHERE EXTRACT(YEAR FROM data_pedido)=2026')
        data = catalog(); data['other'] = data['p'].copy()
        self.assertIsNone(year_rewrite(q, data))

    def test_subqueries_and_derived_tables_are_outside_initial_scope(self):
        for sql in ['SELECT * FROM (SELECT * FROM pedidos) p',
                    'SELECT (SELECT count(*) FROM pedidos) FROM clientes',
                    'SELECT * FROM pedidos p JOIN clientes c USING (id)',
                    'SELECT * FROM pedidos UNION SELECT * FROM pedidos']:
            self.assertIsNone(parse_supported(sql))

    def test_filter_order_proposes_index_with_correct_directions(self):
        q = parse_supported('SELECT id FROM public.pedidos p WHERE cliente_id=42 ORDER BY data_pedido DESC NULLS LAST, id')
        result, _ = filter_order_index(q, catalog(), {'Plan': {'Node Type': 'Sort'}})
        self.assertEqual(result['kind'], 'index')
        self.assertIn('"data_pedido" DESC NULLS LAST', result['sql'])
        self.assertIn('"id" ASC NULLS LAST', result['sql'])

    def test_existing_forward_and_backward_indexes_suppress_duplicate(self):
        eq = ['cliente_id']; order = [('data_pedido', True, True), ('id', False, False)]
        for reverse in [False, True]:
            keys = [dict(column='cliente_id', desc=False, nulls_first=False, default_ops=True, same_collation=True)]
            keys += [dict(column=col, desc=desc ^ reverse, nulls_first=nulls ^ reverse,
                          default_ops=True, same_collation=True) for col, desc, nulls in order]
            idx = dict(name='existing', keys=keys)
            self.assertTrue(covers(idx, eq, order))
            data = catalog(); data['p']['indexes'] = [idx]
            q = parse_supported('SELECT id FROM public.pedidos p WHERE cliente_id=42 ORDER BY data_pedido DESC, id')
            proposal, notes = filter_order_index(q, data, {'Plan': {'Node Type': 'Sort'}})
            self.assertIsNone(proposal)
            self.assertIn('existing', notes[0])
            idx['keys'][-1]['nulls_first'] = not idx['keys'][-1]['nulls_first']
            self.assertFalse(covers(idx, eq, order))

    def test_index_rule_abstains_for_alias_expressions_or_and_range(self):
        for query in [
            'SELECT -id AS id FROM pedidos p WHERE cliente_id=42 ORDER BY id',
            'SELECT id FROM pedidos p WHERE cliente_id=42 OR cliente_id=43 ORDER BY id',
            'SELECT id FROM pedidos p WHERE cliente_id>42 ORDER BY id',
            'SELECT id FROM pedidos p WHERE cliente_id=42 ORDER BY LOWER(id::text)',
        ]:
            self.assertIsNone(filter_order_index(parse_supported(query), catalog(), {'Plan': {'Node Type': 'Sort'}})[0])

    def test_empty_proposals_are_explicit_and_rules_do_not_execute_ddl(self):
        with patch('src.recommendations.read_catalog', return_value=catalog()):
            result = recommend(None, 'SELECT id FROM pedidos p', {'Plan': {'Node Type': 'Seq Scan'}})
        self.assertEqual(result['rewrite_status'], 'not_identified')
        self.assertEqual(result['proposals'], [])


if __name__ == '__main__':
    unittest.main()
