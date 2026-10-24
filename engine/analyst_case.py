"""Evidence-led FY2025 KLBF analyst scenario; NEVER a certified fair value.

Balance sheet amounts are from the FY2025 audited issuer statements. Every
interpretive bridge adjustment remains an analyst decision. The loader merely
prefills inputs; the user must affirm understanding and calculate explicitly.
"""
from __future__ import annotations
from typing import Any



EVIDENCE = {
    "current_financial_assets_bn": {"value": 154.143, "source": "KLBF FY2025 consolidated financial statements PDF p13, note 7 (mutual fund)"},
    "noncurrent_financial_assets_bn": {"value": 265.096, "source": "KLBF FY2025 consolidated financial statements PDF p13, note 11 (equity funds / bond investments)"},
    "investments_in_associates_bn": {"value": 265.444, "source": "KLBF FY2025 consolidated financial statements PDF p13, note 12"},
    "employee_benefit_liability_bn": {"value": 407.705, "source": "KLBF FY2025 consolidated financial statements PDF p14, note 36 (long-term employee benefit obligation)"},
    "revenue_bn": {"value": 35324.544, "source": "KLBF FY2025 consolidated financial statements PDF p16 (FY2025 revenue)"},
}


def analyst_scenario(reported_bridge:dict[str,Any], reserve_rate:float=0.02, revenue_bn:float|None=None) -> dict[str,Any]:
    """Populate a transparent *conditional* bridge, not actual economic values."""
    if not 0 <= reserve_rate <= 0.10:
        raise ValueError('Operating-cash reserve rate must be between 0% and 10% of revenue.')
    reported=reported_bridge['reported']
    cash=float(reported['cash_book_bn']['value_bn'])
    nci=float(reported['nci_book_bn']['value_bn'])
    revenue=float(EVIDENCE['revenue_bn']['value'] if revenue_bn is None else revenue_bn)
    reserve=revenue*reserve_rate
    excess=max(0.,cash-reserve)
    assets=sum(EVIDENCE[k]['value'] for k in (
        'current_financial_assets_bn','noncurrent_financial_assets_bn','investments_in_associates_bn'))
    pension=EVIDENCE['employee_benefit_liability_bn']['value']
    note=(
        'Conditional KLBF FY2025 analyst case (NOT audited economic value): '
        f'cash book Rp{cash:.3f}bn less {reserve_rate*100:g}% of FY2025 revenue '
        f'Rp{revenue:.3f}bn as a discretionary operating cash reserve = Rp{excess:.3f}bn assumed excess. '
        f'Nonoperating asset carrying-value proxy Rp{assets:.3f}bn includes FY2025 notes 7 (154.143), '
        '11 (265.096) and 12 (265.444); separately identify only if excluded from consolidated operating FCFF. '
        f'Book NCI Rp{nci:.3f}bn used as a proxy, not a proven economic minority claim. '
        f'Long-term employee-benefit liability Rp{pension:.3f}bn provisionally treated as another claim; '
        'check overlap with forecast payroll, pension assets and future FCFF cash costs. '
        'Book debt includes lease and finance payables; acquisition payable deducted separately, not also in NCWC. '
        'WACC, D&A, forecast FCFF and NCWC remain analyst assumptions. '
        'FY2025 statements were published in 2026, after 2025-12-30 market close. '
        'This is a retrospective teaching scenario, not a tradable fair-value recommendation.'
    )
    return {
      'status':'ANALYST_HYPOTHESIS_NOT_CERTIFIED',
      'reserve_rate_pct':reserve_rate*100,
      'operating_cash_reserve_bn':round(reserve,6),
      'inputs':{
        'excess_cash_bn':round(excess,6),
        'nci_economic_bn':round(nci,6),
        'nonoperating_assets_bn':round(assets,6),
        'other_claims_bn':round(pension,6),
        'basis_note':note,
      },
      'facts':EVIDENCE,
      'assumptions':[ 
         'Operating cash reserve of 2% of sales is an analyst heuristic, not an issuer disclosure.',
         'Investment carrying values approximate nonoperating economic values only if truly separate from operating FCFF.',
         'Book NCI and long-term employee liabilities may not equal economic claims.',
         'Other claims and restricted cash could exist; this is NOT a completeness certification.',
         'D&A, organic NCWC, sustainable WACC and terminal ROIC remain under review.'
      ],
      'eligible_for_final_recommendation':False,
    }
