import unittest

from src.optimization import propose, parse_select, missing_proposal_note
from src.webapp import project_recommendation


class ProposalTests(unittest.TestCase):
    def test_correlated_count_keeps_output_alias_outer_predicates_and_parameters(self):
        query="SELECT c.id,c.nome,(SELECT count(*) FROM public.pedidos p WHERE p.cliente_id=c.id) AS total FROM public.clientes c WHERE c.id BETWEEN $1 AND $2 ORDER BY c.id"
        suggestions=propose(query)
        self.assertEqual(len(suggestions),1)
        alternative=suggestions[0]['alternative']
        self.assertIn('LEFT JOIN',alternative)
        self.assertIn('COALESCE',alternative)
        self.assertIn(' AS total',alternative)
        self.assertIn('BETWEEN $1 AND $2',alternative)
        self.assertIn('ORDER BY c.id',alternative)
        self.assertEqual(len(parse_select(alternative).targetList),3)

    def test_count_with_extra_filter_or_boolean_sublink_is_not_rewritten(self):
        queries=[
            "SELECT c.id,(SELECT count(*) FROM pedidos p WHERE p.cliente_id=c.id AND p.status='pago') AS n FROM clientes c",
            "SELECT c.id,c.id IN (SELECT count(*) FROM pedidos p WHERE p.cliente_id=c.id) AS n FROM clientes c",
            "SELECT c.*,(SELECT count(*) FROM pedidos p WHERE p.cliente_id=c.id) AS n FROM clientes c",
        ]
        for query in queries:
            with self.subTest(query=query):self.assertEqual(propose(query),[])

    def test_projection_never_converts_cost_into_predicted_time(self):
        def analysis(cost,node):
            return dict(total_cost=cost,estimated_rows=1,plan_kind='generic',plan={'Plan':{'Node Type':node,'Relation Name':'clientes'}})
        result=project_recommendation(analysis(1000,'Seq Scan'),analysis(10,'Index Scan'))
        self.assertEqual(result['cost_reduction_pct'],99)
        self.assertIsNone(result['expected_time_ms'])
        self.assertTrue(result['generic'])

    def test_unfiltered_aggregate_explains_why_no_rewrite_was_generated(self):
        query="SELECT status,count(*) AS quantidade,sum(valor_total) AS total FROM public.pedidos GROUP BY status"
        self.assertEqual(propose(query),[])
        analysis={'plan':{'Plan':{'Node Type':'Gather Merge','Plans':[{'Node Type':'Aggregate','Plans':[{'Node Type':'Seq Scan','Relation Name':'pedidos'}]}]}}}
        note=missing_proposal_note(query,analysis)
        self.assertIn('sem filtro',note['message'])
        self.assertIn('paralelo',note['message'])


if __name__=='__main__':unittest.main()
