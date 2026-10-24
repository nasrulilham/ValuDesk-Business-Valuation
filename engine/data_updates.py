"""Validated, request-scoped manual overrides for KLBF and fixed healthcare comparables.

No live scraping, no server-wide mutable state. Every override must carry provenance.
Values never overwrite bundled audited data; restore defaults by omitting overrides.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from math import isfinite
from typing import Mapping


HISTORICAL_DEFAULTS = {
    'revenue_2022_bn': 28933.5,
    'revenue_2023_bn': 30449.13,
    'revenue_2024_bn': 32627.78,
    'revenue_2025_bn': 35324.544,
    'ebit_2025_bn': 4581.879,
    'parent_net_income_2025_bn': 3664.998,
    'common_equity_2025_bn': 23312.457,
    'shares_bn': 45.28652861,
    'ncwc_2025_bn': 9425.203,
    'da_2025_bn': 814.193,
    'capex_2025_bn': 831.765,
    'market_price_idr': 1205.0,
}

@dataclass(frozen=True)
class HistoricalInputs:
    revenue_2022_bn: float
    revenue_2023_bn: float
    revenue_2024_bn: float
    revenue_2025_bn: float
    ebit_2025_bn: float
    parent_net_income_2025_bn: float
    common_equity_2025_bn: float
    shares_bn: float
    ncwc_2025_bn: float
    da_2025_bn: float
    capex_2025_bn: float
    market_price_idr: float
    market_date: str
    source_note: str
    last_updated: str
    modified: bool


def _number(name, val, low=0, high=1e9):
    if isinstance(val, bool):
        raise ValueError(f'{name}: numeric input required')
    try:
        number = float(val)
    except (ValueError, TypeError):
        raise ValueError(f'{name}: numeric input required') from None
    if not isfinite(number) or not low <= number <= high:
        raise ValueError(f'{name}: must be finite and within [{low}, {high}]')
    return number


def _iso_date(value, label):
    if not isinstance(value, str):
        raise ValueError(f'{label}: YYYY-MM-DD is required')
    try:
        parsed = date.fromisoformat(value)
    except (ValueError, TypeError):
        raise ValueError(f'{label}: enter a valid YYYY-MM-DD date') from None
    if parsed.year < 2020 or parsed.year > 2100:
        raise ValueError(f'{label}: date outside the accepted study horizon')
    return value


def parse_historical(payload: Mapping | None, *, baseline_date='2025-12-30') -> HistoricalInputs:
    if payload in (None, {}):
        values = dict(HISTORICAL_DEFAULTS)
        return HistoricalInputs(**values, market_date=baseline_date, source_note='Bundled FY2025 audit snapshot', last_updated='Bundled audit', modified=False)
    if not isinstance(payload, dict):
        raise ValueError('historical_update must be an object')
    allowed = set(HISTORICAL_DEFAULTS) | {'market_date', 'source_note', 'last_updated'}
    if set(payload)-allowed:
        raise ValueError('Unsupported historical field(s): ' + ', '.join(sorted(set(payload)-allowed)))
    values = {key: _number(key, payload.get(key, default),
              0.000000001 if key.startswith('revenue_') or key in ('shares_bn','market_price_idr') else 0)
              for key, default in HISTORICAL_DEFAULTS.items()}
    if values['ebit_2025_bn'] > values['revenue_2025_bn']:
        raise ValueError('EBIT cannot exceed revenue: check units')
    if values['ncwc_2025_bn'] > values['revenue_2025_bn'] * 2:
        raise ValueError('Operating NCWC exceeds 200% of revenue: check units')
    date_value = _iso_date(payload.get('market_date', baseline_date), 'market_date')
    modified = (date_value != baseline_date or any(abs(values[k]-v) > max(1e-8,abs(v)*1e-10)
             for k, v in HISTORICAL_DEFAULTS.items()))
    note = str(payload.get('source_note','')).strip()
    updated = str(payload.get('last_updated','')).strip()
    if modified and (len(note) < 12 or not updated):
        raise ValueError('Updated historical data require a source / method note (12+ characters) and a last-updated date')
    if modified:
        _iso_date(updated, 'last_updated')
    return HistoricalInputs(**values, market_date=date_value,
                            source_note=note if modified else 'Bundled FY2025 audit snapshot',
                            last_updated=updated if modified else 'Bundled audit', modified=modified)


def peer_inputs(original_rows: list[dict], candidates: dict, payload: Mapping | None):
    """Returns cloned rows/candidates. A new price rebases P/E and P/BV on their originally supplied denominator."""
    rows = [dict(r) for r in original_rows]
    screen = {ticker: dict(value) for ticker, value in candidates.items()}
    if not payload:
        return rows, screen, False
    if not isinstance(payload, dict):
        raise ValueError('peer_updates must be keyed by known ticker')
    allowed = {r['Ticker'] for r in rows}
    if set(payload)-allowed:
        raise ValueError('Unknown comparable ticker in peer update')
    modified = False
    for row in rows:
        ticker = row['Ticker']
        update = payload.get(ticker)
        if not update:
            continue
        if not isinstance(update, dict) or set(update)-{'price', 'price_date','source_note', 'last_updated'}:
            raise ValueError(f'{ticker}: invalid peer update')
        new_price = _number(ticker+' price', update.get('price'), 0.00001, 1e8)
        original_price = _number(ticker+' existing price', row['Price'], .00001, 1e8)
        day = _iso_date(update.get('price_date',''), ticker+' price_date')
        note = str(update.get('source_note','')).strip()
        updated = str(update.get('last_updated','')).strip()
        if len(note)<12 or not updated:
            raise ValueError(f'{ticker}: source note (12+ chars) and last-updated date required')
        _iso_date(updated,ticker+' last_updated')
        scale = new_price/original_price
        row['Price'] = str(new_price)
        row['Price date'] = day
        for field in ('P/E', 'P/BV'):
            if row.get(field) not in ('', None):
                row[field] = str(float(row[field])*scale)
        row['Source note'] = f'Manual price override, {updated}: {note}; original P/E and P/BV denominators kept unchanged.'
        if ticker in screen and screen[ticker].get('market_cap_bn') is not None:
            candidate = screen[ticker]
            candidate['market_cap_bn'] = float(candidate['market_cap_bn'])*scale
            debt = candidate.get('debt_book_bn')
            nci = candidate.get('nci_book_bn')
            cash = candidate.get('cash_book_bn')
            ebitda = candidate.get('ebitda_candidate_bn')
            if all(x is not None for x in (debt,nci,cash,ebitda)) and float(ebitda)>0:
                candidate['simplified_ev_bn'] = candidate['market_cap_bn']+float(debt)+float(nci)-float(cash)
                candidate['multiple_x'] = candidate['simplified_ev_bn']/float(ebitda)
        modified = True
    return rows, screen, modified
