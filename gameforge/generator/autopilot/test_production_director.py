import unittest
from production_director import create_production_plan

class ProductionDirectorTests(unittest.TestCase):
    def test_plan_has_gates_and_no_sales_guarantee(self):
        spec={"title":"Test","campaign":{"target_hours":7},"platforms":["android","windows"],"performance":{"android_profile":"low"}}
        plan=create_production_plan(spec)
        self.assertEqual(len(plan["stages"]),6)
        self.assertFalse(plan["release_ready"])
        self.assertIn("No sales",plan["success_policy"])
    def test_unverified_market_claims_not_upgraded_to_verified(self):
        spec={"title":"Test","campaign":{"target_hours":6},"platforms":["android","windows"],"performance":{}}
        plan=create_production_plan(spec,[{"source":"example","date":"2026-01-01","claim":"players want X","verified":False}])
        self.assertFalse(plan["market_evidence"][0]["verified"])

if __name__=="__main__": unittest.main()
