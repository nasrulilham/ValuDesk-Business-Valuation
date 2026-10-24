"""Step 3: source-aware comparison of valuation methods, not a final price target.

Only like-for-like per-share estimates can share a chart. Operating enterprise
value is never compared directly with a share price. A Step 2 equity scenario,
when explicitly supplied, remains hypothetical. This module NEVER combines
methods into a final target or investment recommendation.
"""
from __future__ import annotations

import math

METHOD_LABELS = {
    'P/E': 'Earnings multiple (P/E)',
    'P/BV': 'Book-equity multiple (P/BV)',
}


def _number(value):
    if isinstance(value, bool):
        return None
    try:
        n = float(value)
        return n if math.isfinite(n) else None
    except (ValueError, TypeError):
        return None


def build_reconciliation(*, relative, scenarios, bridge, market_price, market_date, shares_bn):
    """Return method-specific per-share ranges and explicit audit/readiness gates."""
    price = _number(market_price)
    shares = _number(shares_bn)
    if price is None or price <= 0 or shares is None or shares <= 0:
        raise ValueError('Positive dated market price and share count are required.')

    methods = []
    by_method = {}
    for row in relative:
        name = row.get('method')
        if name not in METHOD_LABELS:
            continue
        n = row.get('n', 0)
        low, mid, high = (_number(row.get(k)) for k in ('low', 'fair_value', 'high'))
        eligible = (isinstance(n, int) and n >= 2 and all(x is not None and x > 0 for x in (low, mid, high)) and low <= mid <= high)
        entry = {
            'method': name, 'label': METHOD_LABELS[name], 'kind': 'RELATIVE',
            'quality': 'PRELIMINARY' if eligible else 'UNAVAILABLE',
            'n_peers': n, 'peer_tickers': row.get('valid_tickers', []),
            'low_idr_per_share': low if eligible else None,
            'mid_idr_per_share': mid if eligible else None,
            'high_idr_per_share': high if eligible else None,
            'versus_historical_price_pct': (mid / price - 1) * 100 if eligible else None,
            'qualification': 'P25–median–P75 of selected valid peers; descriptive quantiles, NOT statistical confidence limits or a certified price target.'
        }
        methods.append(entry)
        by_method[name] = entry

    illustrative = bool(isinstance(bridge, dict) and bridge.get('status') == 'ILLUSTRATIVE_ONLY')
    scenario_values = bridge.get('scenario_values', {}) if illustrative else {}
    if illustrative:
        vals = [_number((scenario_values.get(case) or {}).get('illustrative_per_share_idr')) for case in ('Bear', 'Base', 'Bull')]
        if all(v is not None and v > 0 for v in vals) and vals[0] <= vals[1] <= vals[2]:
            methods.append({
                'method': 'DCF Equity Scenario', 'label': 'DCF equity — hypothetical Step 2 bridge',
                'kind': 'ILLUSTRATIVE_DCF', 'quality': 'ILLUSTRATIVE_ONLY',
                'n_peers': None, 'peer_tickers': [],
                'low_idr_per_share': vals[0], 'mid_idr_per_share': vals[1],
                'high_idr_per_share': vals[2],
                'versus_historical_price_pct': (vals[1]/price-1)*100,
                'qualification': 'Only a conditional scenario: explicit equity-bridge assumptions are not certified economic market values.'
            })

    pe = by_method.get('P/E', {})
    pbv = by_method.get('P/BV', {})
    p = pe.get('mid_idr_per_share')
    b = pbv.get('mid_idr_per_share')
    spread = (b/p-1)*100 if p is not None and b is not None else None
    ev_base = _number((scenarios.get('Base') or {}).get('ev_bn'))
    ev_proxy = next((x for x in relative if x.get('method')=='EV/EBITDA'), {})
    cutoff_note = ('FY2025 audited information was published in 2026 after this reference close.'
                  if market_date < '2026-03-30' else
                  'Dated quote is a historical reference; updated financial information requires matching source availability and audit checks.')
    gates = [
        {'label': 'DCF operating enterprise value', 'status': 'PRELIMINARY' if ev_base is not None else 'UNAVAILABLE', 'why': 'FCFF model forecasts operating enterprise value; it cannot be plotted as Rp/share.'},
        {'label': 'Enterprise-to-equity bridge', 'status': 'ILLUSTRATIVE ONLY' if illustrative else 'UNVERIFIED', 'why': 'NCI economic value, excess cash, financing/other claims and acquisition payable treatment require economic verification.'},
        {'label': 'Relative valuation: P/E', 'status': 'PRELIMINARY' if p is not None else 'INSUFFICIENT PEERS', 'why': 'Peer earnings comparability, statement timing and accounting policy require analyst judgment.'},
        {'label': 'Relative valuation: P/BV', 'status': 'PRELIMINARY' if b is not None else 'INSUFFICIENT PEERS', 'why': 'Book equity is not interchangeable with earnings; balance sheet differences affect multiples.'},
        {'label': 'EV/EBITDA comparables', 'status': 'SCREENING ONLY' if ev_proxy.get('n',0)>=2 else 'INSUFFICIENT PEERS', 'why': 'Book-debt/NCI and full-cash simplified EV divided by unreconciled EBITDA candidates. Operating cash needs, lease definitions, nonoperating assets and other claims remain unverified; not a fair-value/share input.'},
        {'label': 'Information cutoff', 'status': 'RETROSPECTIVE ONLY', 'why': cutoff_note},
    ]
    return {
        'status': 'NOT_RATED', 'certified_fair_value_idr_per_share': None,
        'blended_target_idr_per_share': None, 'buy_sell_rating': None,
        'historical_reference': {'price_idr': price, 'date': market_date, 'is_current_price': False},
        'methods': methods, 'readiness_gates': gates,
        'method_divergence': {
            'pbv_to_pe_median_pct': spread,
            'can_reconcile_to_final': False,
            'reason': 'P/E capitalizes earnings while P/BV values book equity; different multiples and peer economics can produce materially different implied prices.' if spread is not None else 'A valid two-peer minimum is needed for both relative valuation methods.'
        },
        'operating_ev_bn': ev_base,
        'illustrative_bridge_visible': illustrative,
        'note': 'Method comparison is diagnostic only. No weighted/blended price or investment recommendation is produced. Hypothetical zeros must not be treated as verified balances.'
    }
