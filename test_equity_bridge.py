"""Step 2 bridge regression checks; run python -m unittest discover -p 'test*.py'."""
import unittest
from starlette.testclient import TestClient
from engine.equity_bridge import BridgeInputError
from server import app, calculate, REPORTED_BRIDGE

NOTE='For sensitivity testing only: cash classified as operating, investment assets and other claims assumed zero; needs independent verification.'

def scenario(**updates):
    data={
        'excess_cash_bn':'123.5','nci_economic_bn':'1416.046','nonoperating_assets_bn':'0',
        'other_claims_bn':'0', 'basis_note':NOTE,
        'acknowledge_proxies':True,'acknowledge_scope':True,
    }
    data.update(updates)
    return data

class Step2Test(unittest.TestCase):
    def test_sourced_reported_and_provenance(self):
        r=REPORTED_BRIDGE['reported']
        self.assertAlmostEqual(r['cash_book_bn']['value_bn'],4331.44)
        self.assertAlmostEqual(r['debt_book_bn']['value_bn'],298.842)
        self.assertAlmostEqual(r['nci_book_bn']['value_bn'],1416.046)
        self.assertAlmostEqual(r['acquisition_payable_book_bn']['value_bn'],729.383)
        self.assertAlmostEqual(r['shares_bn']['value_bn'],45.28652861)
        self.assertIn('KLBF FY2025',r['acquisition_payable_book_bn']['source'])
    def test_default_cannot_fabricate_equity_value(self):
        a=calculate({'ticker':'KLBF.JK'})
        self.assertEqual(a['equity_bridge']['status'],'INCOMPLETE')
        self.assertIsNone(a['equity_bridge']['scenario_values'])
        self.assertIsNone(a['fair_value'])
        self.assertIsNone(a['rating'])
    def test_partial_unknown_is_not_zero(self):
        a=calculate({'ticker':'KLBF.JK','equity_bridge':scenario(other_claims_bn='')})['equity_bridge']
        self.assertEqual(a['status'],'INCOMPLETE');self.assertIn('other_claims_bn',a['missing'])
    def test_no_assumed_cash_is_excess(self):
        a=calculate({'ticker':'KLBF.JK','equity_bridge':scenario(excess_cash_bn='')})['equity_bridge']
        self.assertEqual(a['status'],'INCOMPLETE');self.assertIn('excess_cash_bn',a['missing'])
    def test_cash_cannot_exceed_reported_total(self):
        with self.assertRaises(BridgeInputError):
            calculate({'ticker':'KLBF.JK','equity_bridge':scenario(excess_cash_bn=4331.441)})
    def test_invalid_other_claims_cannot_be_negative(self):
        with self.assertRaises(BridgeInputError):
            calculate({'ticker':'KLBF.JK','equity_bridge':scenario(other_claims_bn=-1)})
    def test_confirmations_required(self):
        for k in ('acknowledge_scope','acknowledge_proxies'):
            a=calculate({'ticker':'KLBF.JK','equity_bridge':scenario(**{k:False})})['equity_bridge']
            self.assertEqual(a['status'],'INCOMPLETE');self.assertIn(k,a['missing'])
    def test_rationale_required_and_zero_is_explicit(self):
        a=calculate({'ticker':'KLBF.JK','equity_bridge':scenario(basis_note='none')})['equity_bridge']
        self.assertEqual(a['status'],'INCOMPLETE')
        a=calculate({'ticker':'KLBF.JK','equity_bridge':scenario()})['equity_bridge']
        self.assertEqual(a['status'],'ILLUSTRATIVE_ONLY')
        self.assertAlmostEqual(a['assumptions_used']['other_claims_bn'],0)
        self.assertFalse(a['certified']);self.assertIsNone(a['final_fair_value_per_share'])
    def test_bridge_equation_3_scenarios(self):
        a=calculate({'ticker':'KLBF.JK','equity_bridge':scenario()})
        debt=298.842;nci=1416.046;acq=729.383;shares=45.28652861
        for case in ('Bear','Base','Bull'):
            sc=a['equity_bridge']['scenario_values'][case]
            expected=a['scenarios'][case]['ev_bn']+123.5-debt-nci-acq
            self.assertAlmostEqual(sc['illustrative_equity_bn'],expected)
            self.assertAlmostEqual(sc['illustrative_per_share_idr'],expected/shares)
        self.assertIsNone(a['fair_value']);self.assertIsNone(a['rating'])
    def test_recalculate_scenario_after_growth(self):
        a=calculate({'ticker':'KLBF.JK','equity_bridge':scenario()})
        b=calculate({'ticker':'KLBF.JK','revenue_growth':8,'equity_bridge':scenario()})
        self.assertGreater(b['equity_bridge']['scenario_values']['Base']['illustrative_per_share_idr'],a['equity_bridge']['scenario_values']['Base']['illustrative_per_share_idr'])
    def test_http_api(self):
        c=TestClient(app)
        r=c.get('/api/bootstrap');self.assertIn('reported_bridge',r.json())
        r=c.post('/api/calculate',json={'ticker':'KLBF.JK','equity_bridge':scenario()});self.assertEqual(r.status_code,200)
        self.assertEqual(r.json()['equity_bridge']['status'],'ILLUSTRATIVE_ONLY')
        r=c.post('/api/calculate',json={'ticker':'KLBF.JK','equity_bridge':scenario(other_claims_bn=-1)})
        self.assertEqual(r.status_code,422)

if __name__=='__main__':unittest.main()
