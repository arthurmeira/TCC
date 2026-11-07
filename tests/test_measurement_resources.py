import unittest
from src.measurement_resources import resource_sample, summarize_resources


class ResourceTests(unittest.TestCase):
    def test_root_buffers_are_not_double_counted(self):
        doc={'Plan':{'Node Type':'Aggregate','Actual Rows':1,'Actual Loops':1,
                     'Shared Hit Blocks':12,'Plans':[{'Node Type':'Seq Scan',
                     'Actual Rows':5,'Actual Loops':3,'Shared Hit Blocks':12}]}}
        s=resource_sample(doc)
        self.assertEqual(s['shared_hits'],12)
        self.assertEqual(s['actual_output_rows'],1)
        self.assertEqual(s['nodes'][1]['rows_emitted'],15)

    def test_median_and_missing_values(self):
        samples=[resource_sample({'Plan':{'Node Type':'Seq Scan','Total Cost':v,'Plan Rows':1}}) for v in (10,40,20)]
        self.assertEqual(summarize_resources(samples)['medians']['estimated_cost'],20)
