"""关键风险回归：省份/单位/真实输入溯源/不转档级/不提前排名。"""
import sys, unittest, sqlite3
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import pipeline
class IntegrityTests(unittest.TestCase):
    def test_province_dictionary(self):
        p=pipeline.provinces();self.assertEqual(len(p),31)
        self.assertEqual(len({x['province_code'] for x in p}),31)
        self.assertEqual([sum(x['region_4']==r for x in p) for r in ['东部','中部','西部','东北']],[10,6,12,3])
    def test_month_and_year_are_distinct(self):
        self.assertEqual(pipeline.date_period('2024-05',{})[1],'2024-05-31')
        self.assertEqual(pipeline.date_period('2024',{'period_type':'year_end'})[0],'2024-12-31')
    def test_database_quality(self):
        pipeline.validate()
    def test_no_unapproved_ranking(self):
        self.assertFalse((ROOT/'data/processed/province_rankings.csv').exists())
        self.assertFalse((ROOT/'data/processed/province_scores.csv').exists())
if __name__=='__main__':unittest.main()
