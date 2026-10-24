"""Quick offline regression checks: run `python -m unittest tests.py`."""
import unittest
from starlette.testclient import TestClient
from server import app,calculate,market_universe,peer_analysis,QUALIFIED

class TestValuDesk(unittest.TestCase):
 def test_fixed_universe(self):
  self.assertEqual([x['ticker'] for x in market_universe()], ['KLBF.JK','TSPC.JK','SIDO.JK','DVLA.JK','MERK.JK','SOHO.JK'])
 def test_numeric_parity_audit(self):
  out=calculate({'ticker':'KLBF.JK','peers':['TSPC.JK','SOHO.JK']})
  for name in ('Bear','Base','Bull'):
   self.assertAlmostEqual(out['scenarios'][name]['ev_bn'],QUALIFIED['dcf_scenarios'][name]['enterprise_value'],places=4)
  self.assertAlmostEqual(out['relative'][0]['fair_value'],1541.7195187595992,places=4)
  self.assertAlmostEqual(out['relative'][1]['fair_value'],2092.53098507345,places=4)
 def test_no_unsupported_equity(self):
  out=calculate({'ticker':'KLBF.JK'})
  self.assertIsNone(out['fair_value']);self.assertIsNone(out['rating'])
 def test_peer_not_synthetic(self):
  out=calculate({'ticker':'TSPC.JK'});
  self.assertFalse(out['ready']);self.assertIsNone(out['fair_value']);self.assertEqual(out['forecast'],[])
 def test_sensitivity_change(self):
  base=calculate({'ticker':'KLBF.JK'})['scenarios']['Base']['ev_bn']
  alt=calculate({'ticker':'KLBF.JK','revenue_growth':8})['scenarios']['Base']['ev_bn']
  self.assertNotEqual(base,alt)
 def test_peer_change(self):
  base=peer_analysis(['TSPC.JK','SOHO.JK'])[0]['fair_value']
  alt=peer_analysis(['TSPC.JK','MERK.JK'])[0]['fair_value']
  self.assertNotEqual(base,alt)
 def test_invalid_growth(self):
  with self.assertRaises(ValueError): calculate({'ticker':'KLBF.JK','terminal_growth':50})
 def test_endpoints(self):
  c=TestClient(app)
  self.assertEqual(c.get('/api/health').status_code,200)
  self.assertEqual(len(c.get('/api/bootstrap').json()['companies']),6)
  self.assertEqual(c.post('/api/calculate',json={'ticker':'KLBF.JK'}).status_code,200)
  self.assertEqual(c.post('/api/calculate',json={'ticker':'KLBF.JK','terminal_growth':99}).status_code,422)
  r=c.post('/api/export',json={'ticker':'KLBF.JK'})
  self.assertEqual(r.status_code,200);self.assertIn('FY,Year,Revenue',r.text)

if __name__=='__main__':unittest.main()
