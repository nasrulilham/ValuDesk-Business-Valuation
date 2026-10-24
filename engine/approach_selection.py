"""Evidence-led method selection; never promotes hypothetical bridge prices into BUY/SELL.

Decision rules are deterministic, based on observed model outputs rather than
untraceable AI predictions. The prospective rating is gated by information cut-off
and unverified economic adjustments.
"""
from __future__ import annotations

from statistics import median


def select_approach(scenarios, forecast, relative, bridge, reconciliation, *,
                    historical_price, market_date, reference_bridge=None, historically_modified=False):
    fcff_positive = all(float(row.get('FCFF',0))>0 for row in forecast) and len(forecast)>=5
    earnings_positive = all(float(row.get('EBIT',0))>0 for row in forecast)
    pe = next((r for r in relative if r.get('method')=='P/E'), {})
    pb = next((r for r in relative if r.get('method')=='P/BV'), {})
    enough_peers = pe.get('n',0)>=2 and pb.get('n',0)>=2
    p,b=pe.get('fair_value'),pb.get('fair_value')
    dispersion = abs(b/p-1)*100 if p and b else None
    terminal_pct = float((scenarios.get('Base') or {}).get('terminal_share_pct') or 0)
    has_bridge = bridge.get('status') == 'ILLUSTRATIVE_ONLY'
    has_reference = bool(reference_bridge and reference_bridge.get('status') == 'REFERENCE_CASE_UNCONFIRMED')
    qualified = has_bridge and fcff_positive and earnings_positive and terminal_pct < 80
    if qualified:
        method='DCF — CONDITIONAL PRIMARY'
        rationale=('Five forecast years show positive FCFF and EBIT. The explicitly entered '
                   'equity bridge permits a conditional DCF per-share scenario; it remains unverified.')
    elif fcff_positive:
        method='DCF OPERATING EV — PRIMARY DIAGNOSTIC'
        rationale=('Five years of positive forecast FCFF support an operating-enterprise DCF. '
                   'Without a documented and accepted equity bridge it cannot be treated as an equity target.')
    else:
        method='RELATIVE SCREEN — PRIMARY DIAGNOSTIC' if enough_peers else 'INSUFFICIENT EVIDENCE'
        rationale=('Projected cash flows are not consistently positive; use only cautiously selected '
                   'profitability/book comparables, if two or more valid peers are available.')
    if dispersion is not None and dispersion > 30:
        rationale += f' Peer P/E versus P/BV midpoint divergence is {dispersion:.1f}%, so they should not be averaged blindly.'
    if terminal_pct>=65:
        rationale += f' Terminal value represents {terminal_pct:.1f}% of Base EV: terminal assumptions are material.'


    vals = (bridge.get('scenario_values') or {}) if has_bridge else ((reference_bridge or {}).get('scenario_values') or {})
    low = (vals.get('Bear') or {}).get('illustrative_per_share_idr')
    mid = (vals.get('Base') or {}).get('illustrative_per_share_idr')
    high = (vals.get('Bull') or {}).get('illustrative_per_share_idr')
    scenario_ok = all(v is not None and float(v)>0 for v in (low,mid,high)) and low<=mid<=high
    gap = (mid/historical_price-1)*100 if scenario_ok and historical_price>0 else None


    if gap is None:
        scenario_rating='HOLD'
        rating_basis='NO COMPLETE SCENARIO — HOLD IS A NEUTRAL PLACEHOLDER'
    else:
        scenario_rating='BUY' if gap>15 else ('SELL' if gap< -10 else 'HOLD')
        rating_basis='RETROSPECTIVE SCENARIO SCREEN ONLY — NOT INVESTMENT ADVICE'
    quote_predates_report = market_date < '2026-03-30'
    time_reason = ('The reference quote predates the publication of FY2025 audited statements in 2026; ' if quote_predates_report else
                   'The reference quote is a historical observation and its information availability must match the revised assumptions; ')
    return {
      'preferred_method':method,
      'method_reason':rationale,
      'secondary_methods':['P/E comparable', 'P/BV comparable'] if enough_peers else [],
      'rules':[
        {'rule':'Projected FCFF positive across five years','passed':fcff_positive},
        {'rule':'Projected EBIT positive across five years','passed':earnings_positive},
        {'rule':'At least two valid peers for P/E and P/BV','passed':enough_peers},
        {'rule':'Analyst reference bridge components available','passed':has_reference or has_bridge},
        {'rule':'Terminal share of EV below 80%','passed':terminal_pct<80},
      ],
      'central_estimate_idr_per_share':mid if scenario_ok else None,
      'range_low_idr_per_share':low if scenario_ok else None,
      'range_high_idr_per_share':high if scenario_ok else None,
      'range_status':'CONDITIONAL REFERENCE SCENARIO — NOT CERTIFIED' if scenario_ok else 'NOT AVAILABLE',
      'range_source':'USER_CONFIRMED' if has_bridge else ('BUNDLED_REFERENCE_UNCONFIRMED' if has_reference else 'UNAVAILABLE'),
      'user_confirmed_bridge':has_bridge,
      'historical_price_idr':historical_price,
      'market_date':market_date,
      'historical_gap_pct':gap,
      'decision_thresholds':{'buy_if_upside_above_pct':15,'sell_if_downside_below_pct':-10,'otherwise':'HOLD'},
      'rating':scenario_rating,
      'rating_basis':rating_basis,
      'rating_ready':False,
      'rating_reason':(time_reason +
          'cost of capital, FCFF normalization, cash, NCI and claims have unresolved economic verification. '
          'The +15%/-10% rule is a disclosed future decision policy, not automatically applied to historical comparisons.'),
      'information_cutoff':'RETROSPECTIVE 2026 RESEARCH USING HISTORICAL '+market_date+' QUOTE',
      'historical_inputs_modified':bool(historically_modified),
      'recommendation':('The historical scenario classifies as '+scenario_rating+' under the disclosed +15%/-10% thresholds. '
          'Use DCF as the conditional primary analytical range and P/E/P/BV as external checks. '
          'This classification is not an investment instruction or a current price target.')
    }
