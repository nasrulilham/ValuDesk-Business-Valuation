"""End-to-end regression checks for historical edits, peer-only scope and Excel parity."""
import unittest
from io import BytesIO
from zipfile import ZipFile
from xml.etree import ElementTree as ET

from starlette.testclient import TestClient
from server import calculate, app,REPORTED_BRIDGE
from engine.analyst_case import analyst_scenario

BASE_NOTE='Analyst data update test only; source details would reference a dated official corporate filing.'

def source_update(**changes):
    return dict(source_note=BASE_NOTE,last_updated='2026-10-24',**changes)

def bridge_case():
    return dict(analyst_scenario(REPORTED_BRIDGE)['inputs'],basis_note='Analyst scenario illustration based on audited book values and stated provisional assumptions.',acknowledge_proxies=True,acknowledge_scope=True)

class IntegrationV27(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.client=TestClient(app)
    def test_sources_required_to_change_amounts(self):
        r=self.client.post('/api/calculate',json={'ticker':'KLBF.JK','historical_update':{'revenue_2025_bn':37000}})
        self.assertEqual(r.status_code,422)
        self.assertIn('source',r.json()['error'])
    def test_reject_implausible_units(self):
        r=self.client.post('/api/calculate',json={'ticker':'KLBF.JK','historical_update':source_update(revenue_2025_bn=-8)})
        self.assertEqual(r.status_code,422)
        self.assertIn('revenue',r.json()['error'])
    def test_default_remains_unchanged(self):
        original=calculate({'ticker':'KLBF.JK','equity_bridge':bridge_case()})
        self.assertAlmostEqual(original['scenarios']['Base']['ev_bn'],36444.02261792211)
        self.assertAlmostEqual(original['equity_bridge']['scenario_values']['Base']['illustrative_per_share_idr'],836.9305376511638)
        self.assertEqual(original['approach_selection']['rating_ready'],False)
        self.assertEqual(original['approach_selection']['central_estimate_idr_per_share'],original['equity_bridge']['scenario_values']['Base']['illustrative_per_share_idr'])
    def test_revenue_changes_dcf_and_chart(self):
        before=calculate({'ticker':'KLBF.JK'})
        after=calculate({'ticker':'KLBF.JK','historical_update':source_update(revenue_2025_bn=36000)})
        self.assertNotEqual(before['scenarios']['Base']['ev_bn'],after['scenarios']['Base']['ev_bn'])
        self.assertAlmostEqual(after['forecast'][0]['Revenue'],38160)
        self.assertEqual(after['historical_years'][-1]['revenue_bn'],36000)
    def test_share_and_profit_change_relative_and_bridge(self):
        before=calculate({'ticker':'KLBF.JK','equity_bridge':bridge_case()})
        after=calculate({'ticker':'KLBF.JK','historical_update':source_update(shares_bn=48,parent_net_income_2025_bn=4100),'equity_bridge':bridge_case()})
        self.assertNotEqual(before['relative'][0]['fair_value'],after['relative'][0]['fair_value'])
        self.assertNotEqual(before['equity_bridge']['scenario_values']['Base']['illustrative_per_share_idr'],after['equity_bridge']['scenario_values']['Base']['illustrative_per_share_idr'])
        self.assertEqual(after['reported_bridge']['reported']['shares_bn']['value_bn'],48)
    def test_fixed_peers_are_not_full_dcf(self):
        for ticker in ('TSPC.JK','SIDO.JK','DVLA.JK','MERK.JK','SOHO.JK'):
            result=calculate({'ticker':ticker})
            self.assertFalse(result['ready'])
            self.assertEqual(result['role'],'COMPARABLE ONLY')
            self.assertEqual(result['forecast'],[])
    def test_peer_quote_moves_all_multiples_without_manufacturing_eps(self):
        case={'DVLA.JK':{'price':1800,'price_date':'2026-10-24','source_note':BASE_NOTE,'last_updated':'2026-10-24'}}
        after=calculate({'ticker':'KLBF.JK','peers':['TSPC.JK','SOHO.JK','DVLA.JK'],'peer_updates':case})
        peer=next(x for x in after['market_universe'] if x['ticker']=='DVLA.JK')
        self.assertEqual(peer['market_price'],1800)
        self.assertGreater(peer['ev_ebitda_proxy'],5.76)
        other=calculate({'ticker':'DVLA.JK','peer_updates':case})
        self.assertEqual(other['market_universe'][3]['market_price'],1800)
        self.assertFalse(other['ready'])
    def test_excel_numeric_caches_follow_manual_data(self):
        r=self.client.post('/api/export/excel',json={'ticker':'KLBF.JK','equity_bridge':bridge_case(),'historical_update':source_update(revenue_2025_bn=36000,parent_net_income_2025_bn=4100,shares_bn=48)})
        self.assertEqual(r.status_code,200)
        ns={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
        with ZipFile(BytesIO(r.content)) as archive:
            root=ET.fromstring(archive.read('xl/worksheets/sheet2.xml'))
            def val(ref):
                c=root.find(f'.//s:c[@r="{ref}"]/s:v',ns)
                return float(c.text)
            self.assertEqual(val('B4'),36000)
            self.assertEqual(val('B6'),4100)
            self.assertEqual(val('B8'),48)
            scenario=ET.fromstring(archive.read('xl/worksheets/sheet6.xml'))
            ev=scenario.find('.//s:c[@r="B7"]/s:v',ns)
            self.assertIsNotNone(ev)
            self.assertGreater(float(ev.text),30000)
    def test_approach_gating_after_an_analyst_bridge(self):
        before=calculate({'ticker':'KLBF.JK'})['approach_selection']
        self.assertGreater(before['central_estimate_idr_per_share'],800)
        self.assertFalse(before['user_confirmed_bridge'])
        self.assertEqual(before['rating'],'SELL')
        self.assertEqual(before['range_source'],'BUNDLED_REFERENCE_UNCONFIRMED')
        after=calculate({'ticker':'KLBF.JK','equity_bridge':bridge_case()})['approach_selection']
        self.assertGreater(after['central_estimate_idr_per_share'],800)
        self.assertFalse(after['rating_ready'])
        self.assertTrue(after['user_confirmed_bridge'])
        self.assertEqual(after['range_source'],'USER_CONFIRMED')
        self.assertEqual(after['rating'],'SELL')
    def test_reference_not_a_fabricated_user_acknowledgment(self):
        default=calculate({'ticker':'KLBF.JK'})
        self.assertEqual(default['equity_bridge']['status'],'INCOMPLETE')
        self.assertFalse(default['reference_bridge']['user_submitted'])
        self.assertFalse(default['approach_selection']['rating_ready'])
        self.assertIn('RETROSPECTIVE',default['approach_selection']['rating_basis'])
        self.assertTrue(any(g['passed'] for g in default['approach_selection']['rules']
                            if 'reference bridge' in g['rule']))

    def test_reference_scenario_recalculates_on_growth_and_price_changes(self):
        previous=calculate({'ticker':'KLBF.JK'})
        moved=calculate({'ticker':'KLBF.JK','revenue_growth':8,
                           'historical_update':source_update(market_price_idr=640,market_date='2025-12-30')})
        self.assertNotEqual(previous['reference_bridge']['scenario_values']['Base']['illustrative_per_share_idr'],
                            moved['reference_bridge']['scenario_values']['Base']['illustrative_per_share_idr'])
        self.assertIn(moved['approach_selection']['rating'],('BUY','HOLD','SELL'))

    def test_default_excel_export_has_conditional_reference_and_numeric_formula_cache(self):
        r=self.client.post('/api/export/excel',json={'ticker':'KLBF.JK'})
        self.assertEqual(r.status_code,200)
        ns={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
        with ZipFile(BytesIO(r.content)) as archive:
            sheet=ET.fromstring(archive.read('xl/worksheets/sheet6.xml'))
            result=sheet.find('.//s:c[@r="I7"]/s:v',ns)
            self.assertIsNotNone(result)
            self.assertAlmostEqual(float(result.text),836.9305,places=2)
            inputs=ET.fromstring(archive.read('xl/worksheets/sheet2.xml'))
            flag=inputs.find('.//s:c[@r="B31"]/s:v',ns)
            self.assertEqual(int(flag.text),1)

    def test_client_routes_and_assets(self):
        for uri in ('/','/static/app_react.jsx','/static/classic_ui.css','/static/model_config.js'):
            response=self.client.get(uri)
            self.assertEqual(response.status_code,200,uri)
        boot=self.client.get('/api/bootstrap').json()
        self.assertIn('historical_defaults',boot)

if __name__=='__main__':unittest.main()
