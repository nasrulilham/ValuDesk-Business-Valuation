"""KLBF FY2025 sourced enterprise-to-equity bridge.

Explicit FY2025 reported balances are not automatically fair-value estimates.
Unknown items stay unknown. A fully disclosed hypothetical scenario is deliberately
separate from certified equity fair value and any investment rating.
"""
from __future__ import annotations

from typing import Any
import math

class BridgeInputError(ValueError):
    pass

REPORT_FIELDS = {
    'Cash': ('cash_book_bn', 'Cash and cash equivalents', 'Cash reported, not necessarily excess'),
    'Debt including leases/finance payables': ('debt_book_bn', 'Interest-bearing debt and lease/finance payables', 'Book principal; not a market debt valuation'),
    'NCI book equity': ('nci_book_bn', 'Non-controlling interests', 'Book value; not proven economic market value'),
    'Acquisition payable': ('acquisition_payable_book_bn', 'Outstanding acquisition payable', 'Contractual balance; economic valuation unresolved'),
    'Outstanding shares': ('shares_bn', 'FY2025 outstanding shares', 'Period-end, excluding treasury shares'),
}

OPEN_ITEMS = (
    'Excess cash / cash not required for operations',
    'Economic value of NCI versus its book-value proxy',
    'Non-operating assets including investments, with no double count',
    'Other non-equity claims (pensions, payables, restricted items)',
    'Book-versus-economic treatment and acquisition-payable/financing classification',
)

def build_reported_bridge(audit: dict[str,Any]) -> dict[str, Any]:
    rows = [r for r in audit['input_audit'] if r.get('ticker') == 'KLBF.JK' and r.get('period') == '2025-12-31']
    result = {}
    for field, (key, label, qualification) in REPORT_FIELDS.items():
        found = next((r for r in rows if r['field'] == field), None)
        if not found or found.get('official') is None:
            raise BridgeInputError(f'Missing reported bridge input: {field}')
        value = float(found['official'])
        if not math.isfinite(value) or value < 0:
            raise BridgeInputError(f'Invalid reported input: {field}')
        result[key] = {
            'value_bn': value, 'field':field, 'label':label,
            'qualification':qualification, 'source':found['source'],
            'reported_status':found['status']
        }
    return {'anchor':'2025-12-31', 'unit':'IDR billions (shares: billion shares)',
            'reported':result, 'open_items':list(OPEN_ITEMS),
            'disclosure':'Reported cash, debt, book NCI and acquisition obligations are identifiable. This is not yet a complete economic equity bridge.'}


def _number_input(body:dict, field:str, *, maximum:float|None=None) -> float|None:
    raw=body.get(field)
    if raw is None or raw == '':
        return None
    if isinstance(raw,bool):
        raise BridgeInputError(field+' must be a numeric amount, not a checkbox.')
    try: value=float(raw)
    except (ValueError,TypeError) as err: raise BridgeInputError(field+' must be numeric.') from err
    if not math.isfinite(value) or value < 0 or (maximum is not None and value>maximum):
        raise BridgeInputError(field+' must be a finite non-negative amount'+(f' not exceeding {maximum:.3f}.' if maximum is not None else '.'))
    return value


def evaluate_bridge(reported:dict, cases:dict, submitted:dict|None) -> dict:
    """Evaluate explicitly sourced or assumed sensitivity ONLY; no certified output."""
    base={'status':'INCOMPLETE', 'certified':False, 'final_fair_value_per_share':None,
          'investment_rating':None, 'scenario_values':None,
          'missing':list(OPEN_ITEMS),
          'reason':'Known report balances do not establish economic equity value. Supply a complete, documented scenario to view illustrative equity sensitivity.'}
    if not submitted or not isinstance(submitted,dict):
        return base
    known=reported['reported']; cash=known['cash_book_bn']['value_bn']
    names=('excess_cash_bn','nci_economic_bn','nonoperating_assets_bn','other_claims_bn')
    amounts={k:_number_input(submitted,k,maximum=cash if k=='excess_cash_bn' else None) for k in names}
    missing=[k for k,v in amounts.items() if v is None]
    if missing:
        return {**base,'missing':missing,'reason':'Complete each missing component explicitly. Blank is unknown; do not silently treat it as zero.'}
    if submitted.get('acknowledge_proxies') is not True:
        return {**base,'missing':['acknowledge_proxies'],'reason':'Acknowledge the use of book debt and contractual payable as provisional economic-value proxies.'}
    if submitted.get('acknowledge_scope') is not True:
        return {**base,'missing':['acknowledge_scope'],'reason':'Confirm that excess cash, separate investments and claims have been classified without overlap or double counting.'}
    note=str(submitted.get('basis_note','')).strip()
    if len(note)<25:
        return {**base,'missing':['basis_note'],'reason':'Provide a source/rationale (at least 25 characters) for all explicit scenario assumptions, including any zero.'}
    shares=known['shares_bn']['value_bn']
    if shares<=0:raise BridgeInputError('Verified share count must be positive.')
    debt=known['debt_book_bn']['value_bn']; acquisition=known['acquisition_payable_book_bn']['value_bn']

    equity_adjustment=(amounts['excess_cash_bn'] + amounts['nonoperating_assets_bn'] -
                       debt - amounts['nci_economic_bn'] - acquisition - amounts['other_claims_bn'])
    scenario_values={}
    for name in ('Bear','Base','Bull'):
        if name not in cases:raise BridgeInputError('Missing DCF scenario '+name)
        ev=cases[name]['ev_bn']
        equity=ev+equity_adjustment
        scenario_values[name]={'operating_ev_bn':ev, 'equity_adjustment_bn':equity_adjustment,
                               'illustrative_equity_bn':equity,
                               'illustrative_per_share_idr':equity/shares,
                               'is_certified':False}
    return {**base,'status':'ILLUSTRATIVE_ONLY','missing':[],
       'reason':'Scenario uses explicit analyst assumptions and book/contractual proxies; this is not an audited economic equity value.',
       'scenario_values':scenario_values,'assumptions_used':amounts,
       'source_note':note, 'shares_bn':shares,
       'proxies_used':{'debt_book_bn':debt,'acquisition_payable_book_bn':acquisition}}


def preview_reference_bridge(reported:dict, cases:dict, analyst_inputs:dict) -> dict:
    """Price the bundled analyst reference case WITHOUT claiming user consent.

    This is a mathematical what-if with report-based carrying value proxies; it
    must never change a user-submitted bridge or certify an investment rating.
    """
    known=reported['reported']
    names=('excess_cash_bn','nci_economic_bn','nonoperating_assets_bn','other_claims_bn')
    amounts={k:_number_input(analyst_inputs,k,maximum=known['cash_book_bn']['value_bn'] if k=='excess_cash_bn' else None) for k in names}
    if any(v is None for v in amounts.values()):
        raise BridgeInputError('Reference analyst case has a missing economic component.')
    shares=known['shares_bn']['value_bn']
    if shares<=0:raise BridgeInputError('Reference share count must be positive.')
    delta=(amounts['excess_cash_bn']+amounts['nonoperating_assets_bn']
          -known['debt_book_bn']['value_bn']-amounts['nci_economic_bn']
          -known['acquisition_payable_book_bn']['value_bn']-amounts['other_claims_bn'])
    values={}
    for name in ('Bear','Base','Bull'):
        ev=cases[name]['ev_bn']
        equity=ev+delta
        values[name]={'operating_ev_bn':ev,'equity_adjustment_bn':delta,
                      'illustrative_equity_bn':equity,'illustrative_per_share_idr':equity/shares,
                      'is_certified':False}
    return {'status':'REFERENCE_CASE_UNCONFIRMED','scenario_values':values,
            'source':'Bundled FY2025 analyst reference; user has not confirmed these assumptions',
            'assumptions_used':amounts,'certified':False,'final_fair_value_per_share':None,
            'investment_rating':None,'user_submitted':False}
