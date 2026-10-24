"""FY2025 EV/EBITDA *screening* only (not reported or certified EV).

Inputs are retained verbatim from the Step 37 FY2025 peer audit snapshot.
DVLA is now separately flagged as PROVIDER_CROSS_CHECKED after comparison of the
issuer's official *listing* for FY2025 with dated secondary financial disclosures.
We could not independently inspect the primary FY2025 PDF in this session; this
is deliberately not official-PDF or economic EV verification.

Never use full current liabilities as interest-bearing debt. The Indopremier
2025 DVLA screen labels 679.9bn 'S.T. Debt' and 190.5bn 'L.T. Debt', though
independent statement mappings identify these as total current liabilities
and pension/post-retirement liabilities, not necessarily financial debt.
"""
import math
from statistics import median

ELIGIBLE = {'TSPC.JK', 'SIDO.JK', 'DVLA.JK', 'MERK.JK', 'SOHO.JK'}
DVLA_CROSSCHECK = {
    'evidence_grade': 'PROVIDER_CROSS_CHECKED_NOT_PDF_VERIFIED',
    'status_message': 'Provider cross-check only; official FY2025 PDF listed by issuer but detailed notes were not independently read. Do not call this audited EV/EBITDA.',
    'cash_crosscheck_bn': 341.559,
    'interest_bearing_debt_crosscheck_bn': 0.20687,
    'nci_book_crosscheck_bn': 0.00111,
    'market_ebitda_candidate_bn': 257.5,
    'market_ebitda_report_date': '2026-03-25',
    'reported_market_multiple_x': 9.03,
    'source_urls': {
        'issuer_financial_reports': 'https://www.darya-varia.com/en/investors/financial-report',
        'provider_balance_sheet': 'https://stockanalysis.com/quote/idx/DVLA/financials/balance-sheet/',
        'fy2025_market_summary': 'https://ipotnews.com/ipotnews/newsDetail.php?group_news=RESEARCHNEWS&halaman=1&jdl=Financial_Statements_Full_Year_2025_of_DVLA&name=&news_id=486277&q=Financial+Statements&search=y_general&taging_subtype=COMPANYUPDATE',
    },
    'critical_discrepancy': 'One market source reports 9.03x using S.T. Debt ~679.9bn and L.T. Debt ~190.5bn, which match total current liabilities and pension obligations in another mapping. They must not be substituted for financial debt without explicit reconciliation.',
}

def finite(value):
    if isinstance(value, bool) or value in ('', None):
        return None
    try:
        x = float(value)
        return x if math.isfinite(x) else None
    except (ValueError, TypeError):
        return None

def build_candidates(peer_rows):
    """Build *incomplete* EV proxy, preserving distinct evidence grades."""
    candidates = {}
    for p in peer_rows:
        ticker = p.get('Ticker', '')
        market = finite(p.get('Market cap (bn)'))
        debt = finite(p.get('Debt (bn)'))
        nci = finite(p.get('NCI (bn)'))
        cash = finite(p.get('Cash (bn)'))
        ebitda = finite(p.get('EBITDA (bn)'))
        parts = {'market_cap_bn': market, 'debt_book_bn': debt,
                 'nci_book_bn': nci, 'cash_book_bn': cash,
                 'ebitda_candidate_bn': ebitda}
        complete = (ticker in ELIGIBLE and all(v is not None for v in parts.values())
                    and min(market, debt, nci, cash) >= 0 and market > 0 and ebitda > 0)
        proxy = market + debt + nci - cash if complete else None
        complete = complete and proxy is not None and proxy > 0
        record = {
            'ticker': ticker, **parts,
            'simplified_ev_bn': proxy if complete else None,
            'multiple_x': proxy / ebitda if complete else None,
            'status': 'SCREENING_PROXY' if complete else 'UNAVAILABLE',
            'evidence_grade': 'UNRECONCILED_AUDIT_CANDIDATE' if complete else 'UNAVAILABLE',
            'source_note': p.get('Source note', ''),
            'qualification': (
                'Unreconciled FY2025 EBITDA; book debt/NCI; FULL cash deducted; '
                'required operating cash, non-operating assets, other claims and lease definitions '
                'not reconciled. Not an audited EV/EBITDA.' if complete else
                'Unavailable until a consistently sourced EV/EBITDA can be computed.'
            ),
        }
        if ticker == 'DVLA.JK':
            record.update(DVLA_CROSSCHECK)
            record['status'] = 'PROVIDER_SCREEN_ONLY' if complete else 'UNAVAILABLE'
            record['market_ebitda_alternative_multiple_x'] = (
                proxy / DVLA_CROSSCHECK['market_ebitda_candidate_bn'] if complete else None
            )
            record['qualification'] = (
                'NOT PDF-VERIFIED. Saved provider EBITDA 261.493bn vs March 25 2026 market '
                'summary 257.5bn; 2025 market price in this model is dated Dec 30. '
                'Full cash is deducted; finance debt is not full current liabilities. '
                'Economic adjustments remain unresolved.'
            )
        candidates[ticker] = record
    return candidates

def peer_proxy_summary(tickers, candidates, klbf_ebit_bn=None, klbf_da_candidate_bn=None):
    vals = sorted([(t, candidates[t]['multiple_x']) for t in tickers
                   if t in candidates and candidates[t]['multiple_x'] is not None],
                  key=lambda x: x[1])
    numbers = [v for _, v in vals]
    base = {
        'method': 'EV/EBITDA', 'status': 'SCREENING ONLY — NOT CERTIFIED',
        'n': len(vals), 'valid_tickers': [t for t, _ in vals],
        'evidence_caveat': ('DVLA uses a cross-checked provider candidate; the source FY2025 '
                            'PDF has not been independently reconciled. All peers use incomplete '
                            'economic EV and unreconciled EBITDA candidates.'),
        'median': None, 'p25': None, 'p75': None,
        'fair_value': None, 'low': None, 'high': None, 'implied_ev_bn': None,
        'implied_ev_low_bn': None, 'implied_ev_high_bn': None,
        'implied_share_price_idr': None,
        'unit': 'IDR billions — enterprise value only',
        'assumptions': 'Book debt/NCI, gross cash; EBITDA candidates unvalidated; no economic EV bridge.',
    }
    if len(numbers) < 2:
        base['status'] = 'INSUFFICIENT SCREENING PEERS'
        return base
    def q(p):
        z = (len(numbers) - 1) * p / 100
        i = int(z)
        j = min(i + 1, len(numbers) - 1)
        return numbers[i] + (numbers[j] - numbers[i]) * (z - i)
    base.update({'median': median(numbers), 'p25': q(25), 'p75': q(75)})
    ebit = finite(klbf_ebit_bn)
    da = finite(klbf_da_candidate_bn)
    if ebit is not None and da is not None and ebit > 0 and da >= 0:
        ebitda = ebit + da
        base.update({
            'klbf_ebitda_candidate_bn': ebitda,
            'klbf_ebit_bn': ebit,
            'klbf_da_candidate_bn': da,
            'implied_ev_bn': base['median'] * ebitda,
            'implied_ev_low_bn': base['p25'] * ebitda,
            'implied_ev_high_bn': base['p75'] * ebitda,
        })
    return base
