"""ValuDesk 2.8.1 — KLBF valuation platform, FY2025 financial audit data.

Only KLBF + the five named comparable issuers are supported.
Historical figures are sourced from the bundled audit trail, NEVER synthesized.
DCF produces a transparent operating enterprise-value scenario. Unverified equity
bridge items prevent an unsupported per-share DCF fair-value or BUY/SELL rating.
"""
from __future__ import annotations

import csv
import io
import json
import math
from dataclasses import asdict, replace
from copy import deepcopy
from datetime import date
from pathlib import Path
from statistics import median
from typing import Any

from starlette.applications import Starlette
from starlette.responses import FileResponse, JSONResponse, Response
from starlette.routing import Route, Mount
from starlette.staticfiles import StaticFiles
from engine.equity_bridge import build_reported_bridge, evaluate_bridge, preview_reference_bridge, BridgeInputError
from engine.analyst_case import analyst_scenario
from engine.excel_export import create_excel_model
from engine.reconciliation_engine import build_reconciliation
from engine.ev_ebitda_screen import build_candidates, peer_proxy_summary
from engine.data_updates import parse_historical, peer_inputs, HISTORICAL_DEFAULTS
from engine.approach_selection import select_approach
from engine.dcf_engine import ForecastAssumptions, project_cash_flows, operating_value, scenario_assumptions, ModelInputError

BASE = Path(__file__).resolve().parent
DATA = BASE / 'data'
QUALIFIED = json.loads((DATA / 'qualified_valuation.json').read_text(encoding='utf-8'))
AUDIT = json.loads((DATA / 'financial_audit.json').read_text(encoding='utf-8'))
REPORTED_BRIDGE = build_reported_bridge(AUDIT)

def read_csv(name):
    with (DATA / name).open('r',encoding='utf-8-sig',newline='') as f:
        return list(csv.DictReader(f))

PEER_ROWS = read_csv('peer_audit.csv')
PEER_CONTEXT = {x['ticker']:x for x in read_csv('peer_context.csv')}
INPUT_AUDIT = read_csv('input_audit.csv')
EV_EBITDA_CANDIDATES = build_candidates(PEER_ROWS)

NAMES = {
 'KLBF.JK': 'PT Kalbe Farma Tbk',
 'TSPC.JK': 'PT Tempo Scan Pacific Tbk',
 'SIDO.JK': 'PT Industri Jamu dan Farmasi Sido Muncul Tbk',
 'DVLA.JK': 'PT Darya-Varia Laboratoria Tbk',
 'MERK.JK': 'PT Merck Tbk',
 'SOHO.JK': 'PT Soho Global Health Tbk',
}
CORE_PEERS = ('TSPC.JK','SOHO.JK')
MARKET_DATE = '2025-12-30'
BASE_REVENUE = 35324.544
BASE_NCWC = 9425.203
BASE_INPUT = ForecastAssumptions(
 revenue_growth=.06, ebit_margin=4581.879/BASE_REVENUE,
 da_to_revenue=814.193/BASE_REVENUE, capex_to_revenue=831.765/BASE_REVENUE,
 ncwc_to_revenue=BASE_NCWC/BASE_REVENUE, tax_rate=.22,
 wacc=QUALIFIED['wacc']['wacc'],terminal_growth=.025,terminal_roic=.15
)
SHARES = 45.28652861
PARENT_NI = 3664.998
COMMON_EQUITY = 23312.457
PRICE_2025 = 1205.0


def num(v):
    try:
        f=float(v)
        return f if math.isfinite(f) else None
    except (TypeError,ValueError):
        return None


def coerce_pct(body,key,original,low,high):
    raw=body.get(key,original*100)
    n=num(raw)
    if n is None or not low <= n <= high:
        raise ValueError(f'{key} must be between {low} and {high} percent.')
    return n/100


def market_universe(facts=None, rows=None, candidates=None):
    facts = facts or parse_historical(None)
    rows = PEER_ROWS if rows is None else rows
    candidates = EV_EBITDA_CANDIDATES if candidates is None else candidates
    companies=[]
    klbf_ctx=PEER_CONTEXT.get('KLBF.JK',{})
    companies.append({'ticker':'KLBF.JK','name':NAMES['KLBF.JK'],'role':'Selected valuation case',
                      'revenue_bn':facts.revenue_2025_bn,'market_price':facts.market_price_idr,'price_date':facts.market_date,
                      'sales_growth':((facts.revenue_2025_bn/facts.revenue_2024_bn-1)*100 if facts.modified else num(klbf_ctx.get('revenue_growth_provider_pct'))),
                      'pe':None,'pb':None,'status':'Partial audit — DCF equity bridge open'})
    for peer in rows:
        ticker=peer['Ticker']
        if ticker not in NAMES:continue
        ctx=PEER_CONTEXT.get(ticker,{})
        companies.append({
         'ticker':ticker,'name':NAMES[ticker],'role':'Core comparable' if ticker in CORE_PEERS else 'Sensitivity comparable',
         'revenue_bn':num(ctx.get('revenue_bn_provider')),
         'market_price':num(peer['Price']),'price_date':peer['Price date'],
         'sales_growth':num(ctx.get('revenue_growth_provider_pct')),
         'pe':num(peer['P/E']),'pb':num(peer['P/BV']),
         'ev_ebitda_proxy':candidates.get(ticker,{}).get('multiple_x'),
         'net_income_bn':num(peer['Parent NI (bn)']),'equity_bn':num(peer['Common equity (bn)']),
         'status':'Qualified peer; EV/EBITDA screening proxy only' if ticker != 'DVLA.JK' else 'Provider snapshot — report not certified',
         'source':peer['Source note'], 'caveat':peer['Comparability rationale'],
        })
    return companies


def peer_analysis(tickers, facts=None, rows=None, candidates=None):
    facts = facts or parse_historical(None)
    rows = PEER_ROWS if rows is None else rows
    candidates = EV_EBITDA_CANDIDATES if candidates is None else candidates
    selected=[p for p in rows if p['Ticker'] in tickers]
    results=[]
    for method,key,scalar in [('P/E','P/E',facts.parent_net_income_2025_bn/facts.shares_bn),('P/BV','P/BV',facts.common_equity_2025_bn/facts.shares_bn)]:
        valid=[num(p[key]) for p in selected]
        valid=sorted([x for x in valid if x is not None and x>0])
        if len(valid)<2:
            results.append({'method':method,'status':'Insufficient valid peers','n':len(valid),'median':None,'fair_value':None})
            continue
        def percentile(p):
            z=(len(valid)-1)*p/100; i=int(z); j=min(i+1,len(valid)-1)
            return valid[i]+(valid[j]-valid[i])*(z-i)
        results.append({'method':method,'status':'Indicative only','n':len(valid),'median':median(valid),
         'p25':percentile(25),'p75':percentile(75),'fair_value':median(valid)*scalar,
         'low':percentile(25)*scalar,'high':percentile(75)*scalar,
         'valid_tickers':[p['Ticker'] for p in selected if num(p[key]) is not None and num(p[key])>0]})
    results.append(peer_proxy_summary(tickers,candidates,facts.ebit_2025_bn,facts.da_2025_bn))
    return results


def assumptions(body):
    a=BASE_INPUT
    return replace(a,
       revenue_growth=coerce_pct(body,'revenue_growth',a.revenue_growth,-20,40),
       ebit_margin=coerce_pct(body,'ebit_margin',a.ebit_margin,0,45),
       da_to_revenue=coerce_pct(body,'da_to_revenue',a.da_to_revenue,0,15),
       capex_to_revenue=coerce_pct(body,'capex_to_revenue',a.capex_to_revenue,0,30),
       ncwc_to_revenue=coerce_pct(body,'ncwc_to_revenue',a.ncwc_to_revenue,0,75),
       tax_rate=coerce_pct(body,'tax_rate',a.tax_rate,0,50),
       wacc=coerce_pct(body,'wacc',a.wacc,2,30),
       terminal_growth=coerce_pct(body,'terminal_growth',a.terminal_growth,0,8),
       terminal_roic=coerce_pct(body,'terminal_roic',a.terminal_roic,1,70))


def calculate(body):
    ticker=str(body.get('ticker','KLBF.JK')).strip().upper()
    if ticker not in NAMES:raise ValueError('Only KLBF and its five defined peers are supported.')
    if ticker!='KLBF.JK':
        facts=parse_historical(body.get('historical_update'))
        peer_rows,candidates,_=peer_inputs(PEER_ROWS,EV_EBITDA_CANDIDATES,body.get('peer_updates'))
        return {'ticker':ticker,'ready':False,'role':'COMPARABLE ONLY',
                'message':'Peer financial and market multiples only. Full DCF, equity bridge and Excel forecast remain KLBF-specific.',
                'market_universe':market_universe(facts,peer_rows,candidates),'peer_candidates':candidates,
                'dcf_scenarios':[],'forecast':[],'relative':[],'fair_value':None,'rating':None}
    facts=parse_historical(body.get('historical_update'))
    peer_rows, candidates, peer_modified=peer_inputs(PEER_ROWS,EV_EBITDA_CANDIDATES,body.get('peer_updates'))
    a=assumptions(body)
    if a.terminal_growth>=a.wacc or a.terminal_growth>=a.terminal_roic:
        raise ValueError('Terminal growth must be below WACC and terminal ROIC.')
    scenarios={};base_forecast=None
    for case, settings in scenario_assumptions(a).items():
        if settings.terminal_growth >= settings.wacc or settings.terminal_growth >= settings.terminal_roic:
            raise ValueError(f'{case} scenario has terminal growth >= WACC or ROIC.')
        forecast=project_cash_flows(facts.revenue_2025_bn,facts.ncwc_2025_bn,2025,settings)
        res=operating_value(forecast,settings.wacc,settings.terminal_growth,settings.terminal_roic)
        scenarios[case]={'ev_bn':res['enterprise_value'],'pv_forecast_bn':res['pv_explicit_fcff'],
             'pv_terminal_bn':res['pv_terminal_value'],'terminal_share_pct':res['terminal_ev_share']*100,
             'wacc_pct':settings.wacc*100,'growth_pct':settings.revenue_growth*100}
        if case=='Base':base_forecast=forecast
    tickers=[x for x in body.get('peers',list(CORE_PEERS)) if x in NAMES and x!='KLBF.JK']
    relative=peer_analysis(tickers,facts,peer_rows,candidates)
    sensitivity=[]
    for adjw in (-.02,-.01,0,.01,.02):
        row=[]
        for adjg in (-.01,-.005,0,.005,.01):
            w=a.wacc+adjw;g=a.terminal_growth+adjg
            row.append(None if not (0<=g<min(w,a.terminal_roic)) else round(operating_value(base_forecast,w,g,a.terminal_roic)['enterprise_value'],1))
        sensitivity.append(row)
    reported=deepcopy(REPORTED_BRIDGE)
    if facts.shares_bn != SHARES:
        reported['reported']['shares_bn']['value_bn']=facts.shares_bn
        reported['reported']['shares_bn']['source']='Analyst historical input override: '+facts.source_note
    bridge=evaluate_bridge(reported,scenarios,body.get('equity_bridge'))
    analyst_reference=analyst_scenario(reported, revenue_bn=facts.revenue_2025_bn)
    reference_bridge=preview_reference_bridge(reported,scenarios,analyst_reference['inputs'])
    reconciliation=build_reconciliation(relative=relative, scenarios=scenarios, bridge=bridge,
      market_price=facts.market_price_idr, market_date=facts.market_date, shares_bn=facts.shares_bn)
    decision=select_approach(scenarios,base_forecast.to_dict('records'),relative,bridge,reconciliation,
         historical_price=facts.market_price_idr, market_date=facts.market_date,
         reference_bridge=reference_bridge, historically_modified=facts.modified or peer_modified)
    return {'ticker':ticker,'ready':True,'scenarios':scenarios,
       'forecast':[{k:(round(float(v),3) if isinstance(v,(float,int)) else v) for k,v in row.items()} for row in base_forecast.to_dict('records')],
       'relative':relative,'sensitivity_ev_bn':sensitivity,
       'assumptions':asdict(a),'rating':None,'fair_value':None,
       'reported_bridge':reported,'equity_bridge':bridge,'reference_bridge':reference_bridge,'reconciliation':reconciliation,'approach_selection':decision,
       'historical':asdict(facts), 'historical_years':[{'year':y,'revenue_bn':getattr(facts,f'revenue_{y}_bn')} for y in range(2022,2026)],
       'market_universe':market_universe(facts,peer_rows,candidates),
       'peer_inputs_modified':peer_modified,'peer_candidates':candidates,
       'equity_bridge_status':'NOT CERTIFIED: economic NCI, economic debt/payables and nonoperating assets/claims remain unresolved',
       'warning':'Illustrative retrospective operating EV only; FY2025 information was not public on 2025-12-31. Not a current BUY/SELL rating.',
       'peer_selection':tickers}


async def index(request):
    return FileResponse(BASE/'static'/'index.html')

async def bootstrap(request):
    return JSONResponse({'companies':market_universe(),
      'audit':{'period':'FY2025','review_date':'2026-10-23','market_date':MARKET_DATE,'market_price':PRICE_2025,
              'historical_revenue_bn':BASE_REVENUE,'operating_ebit_bn':4581.879,'net_income_parent_bn':PARENT_NI,
              'share_count_bn':SHARES,'common_equity_bn':COMMON_EQUITY,
              'last_years':[{'year':2022,'revenue_bn':28933.5},{'year':2023,'revenue_bn':30449.13},
                {'year':2024,'revenue_bn':32627.78},{'year':2025,'revenue_bn':35324.544}],
              'preliminary_ev_audit':{k:round(v['enterprise_value'],2) for k,v in QUALIFIED['dcf_scenarios'].items()},
              'status':'Preliminary / Not Rated'},
      'source_register':AUDIT['sources'],'input_audit':INPUT_AUDIT,
      'reported_bridge':REPORTED_BRIDGE,'analyst_case':analyst_scenario(REPORTED_BRIDGE),'ev_ebitda_candidates':EV_EBITDA_CANDIDATES,
      'historical_defaults':dict(HISTORICAL_DEFAULTS,market_date=MARKET_DATE,source_note='',last_updated=''),
      'default_peers':list(CORE_PEERS),'defaults':{k:round(v*100,4) for k,v in asdict(BASE_INPUT).items() if k!='terminal_roic'} | {'terminal_roic':15.0}})

async def api_calculate(request):
    try:
        body=await request.json()
        return JSONResponse(calculate(body))
    except (ValueError,BridgeInputError,ModelInputError,TypeError,KeyError) as e:
        return JSONResponse({'error':str(e)},status_code=422)

async def api_export(request):
    """Download transparent calculation table, no synthetic historical figures."""
    try:
        body=await request.json()
        result=calculate(body)
        if not result.get('ready'):
            return JSONResponse({'error':'No completed forecast to export for this ticker.'},status_code=422)
        out=io.StringIO()
        out.write('# ValuDesk 2.8.1 — Preliminary FY2025 KLBF research forecast\n')
        out.write('# Units: IDR billions; NCI/equity bridge unresolved; not a final fair-value rating\n')
        writer=csv.DictWriter(out,fieldnames=['FY','Year','Revenue','EBIT','NOPAT','D&A','CapEx','NCWC','Delta NCWC','FCFF'])
        writer.writeheader();writer.writerows(result['forecast'])
        return Response(out.getvalue().encode('utf-8-sig'),media_type='text/csv',
           headers={'Content-Disposition':'attachment; filename="ValuDesk_KLBF_DCF_preliminary.csv"'})
    except (ValueError,BridgeInputError,ModelInputError,TypeError,KeyError) as e:
        return JSONResponse({'error':str(e)},status_code=422)

async def api_export_excel(request):
    """Export a live, formula-based workbook with session assumptions and peer set."""
    try:
        body=await request.json()
        result=calculate(body)
        if not result.get('ready'):
            return JSONResponse({'error':'Excel financial model is available for KLBF only; no synthetic peer DCF.'},status_code=422)
        params=assumptions(body)
        binary=create_excel_model(DATA/'ValuDesk_Excel_Model_Template.xlsx',
            data=result, assumptions=params, bridge=(result['equity_bridge'] if result['equity_bridge']['status']=='ILLUSTRATIVE_ONLY' else result['reference_bridge']),
            peer_rows=peer_inputs(PEER_ROWS,EV_EBITDA_CANDIDATES,body.get('peer_updates'))[0],
            candidates=peer_inputs(PEER_ROWS,EV_EBITDA_CANDIDATES,body.get('peer_updates'))[1],
            peer_selection=result['peer_selection'], source_register=AUDIT['sources'],
            historical=parse_historical(body.get('historical_update')))
        return Response(binary,media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            headers={'Content-Disposition':'attachment; filename="ValuDesk_KLBF_FY2025_Financial_Model_Preliminary.xlsx"',
                     'Cache-Control':'no-store'})
    except (ValueError,BridgeInputError,ModelInputError,TypeError,KeyError) as e:
        return JSONResponse({'error':str(e)},status_code=422)

async def health(request):
    return JSONResponse({'status':'ok','app':'ValuDesk 2.8.1','supported_tickers':list(NAMES)})

app=Starlette(debug=False,routes=[Route('/',index),Route('/api/health',health),
  Route('/api/bootstrap',bootstrap),Route('/api/calculate',api_calculate,methods=['POST']),
  Route('/api/export',api_export,methods=['POST']),
  Route('/api/export/excel',api_export_excel,methods=['POST']),
  Mount('/static',app=StaticFiles(directory=str(BASE/'static')),name='static')])

if __name__=='__main__':
    import os
    import uvicorn
    uvicorn.run('server:app',host='127.0.0.1',port=int(os.getenv('VALUDESK_PORT','8000')),reload=False)
