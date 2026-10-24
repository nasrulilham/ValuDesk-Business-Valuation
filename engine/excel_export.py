"""Dynamic Excel export from an artifact-tool-authored formula workbook template.

Runtime uses only Python's standard library to populate documented inputs in an
existing, validated OOXML template. Formula cells are never replaced by values.
Excel will recalculate formula caches on opening the downloaded workbook.
"""
from __future__ import annotations

from io import BytesIO
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import math
import re
import xml.etree.ElementTree as ET

NS = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
TAG = lambda short: '{%s}%s' % (NS,short)
ET.register_namespace('x', NS)
ADDRESS = re.compile(r'^([A-Z]+)([1-9][0-9]*)$')
FIVE = ('TSPC.JK','SIDO.JK','DVLA.JK','MERK.JK','SOHO.JK')


def checked_number(x):
    if x is None or x == '': return None
    if isinstance(x, bool): raise ValueError('Boolean is not a financial number')
    n=float(x)
    if not math.isfinite(n):raise ValueError('Nonfinite values may not enter the workbook')
    return n


def put_cell(root, addr, value):
    """Only insert/replace raw-value OOXML cells. Never modify formulas."""
    match=ADDRESS.fullmatch(addr)
    if not match:raise ValueError('Invalid cell address: '+addr)
    row_num=int(match.group(2))
    sheet_data=root.find(TAG('sheetData'))
    if sheet_data is None:raise ValueError('Spreadsheet template missing sheetData')
    row=next((r for r in sheet_data.findall(TAG('row')) if int(r.get('r'))==row_num),None)
    if row is None:
        row=ET.Element(TAG('row'),{'r':str(row_num)})
        rows=sheet_data.findall(TAG('row'))
        next_row=next((r for r in rows if int(r.get('r'))>row_num),None)
        sheet_data.insert(list(sheet_data).index(next_row),row) if next_row is not None else sheet_data.append(row)
    cell=next((c for c in row.findall(TAG('c')) if c.get('r')==addr),None)
    if cell is None:
        cell=ET.Element(TAG('c'),{'r':addr})
        def colnum(s):
            n=0
            for ch in s:n=n*26+ord(ch)-64
            return n
        target=colnum(match.group(1));children=row.findall(TAG('c'))
        next_cell=next((c for c in children if colnum(ADDRESS.fullmatch(c.get('r')).group(1))>target),None)
        row.insert(list(row).index(next_cell),cell) if next_cell is not None else row.append(cell)
    if cell.find(TAG('f')) is not None:
        raise ValueError('Cannot overwrite formula: '+addr)
    for child in list(cell):
        if child.tag in (TAG('v'),TAG('is')):cell.remove(child)
    if value is None:
        cell.attrib.pop('t',None)
        return
    if isinstance(value,str):
        cell.set('t','inlineStr')
        is_el=ET.SubElement(cell,TAG('is'))
        txt=ET.SubElement(is_el,TAG('t'))
        txt.text=value[:1000]
        return
    number=checked_number(value)
    cell.set('t','n')
    ET.SubElement(cell,TAG('v')).text=format(number,'.16g')


def _cache_number(value):
    if value is None:
        return None
    try:
        v = float(value)
    except (ValueError, TypeError):
        return None
    return v if math.isfinite(v) else None


def _read_numeric_cell(root, addr):
    cell = root.find('.//%s[@r="%s"]' % (TAG('c'), addr))
    if cell is None:
        return None
    tag = cell.find(TAG('v'))
    return _cache_number(tag.text) if tag is not None else None


def _set_cached_formula(root, addr, value):
    cell = root.find('.//%s[@r="%s"]' % (TAG('c'), addr))
    if cell is None or cell.find(TAG('f')) is None:
        raise ValueError('Missing workbook formula at ' + addr)
    prev = cell.find(TAG('v'))
    if prev is not None:
        cell.remove(prev)
    n = _cache_number(value)
    if n is None:
        cell.set('t', 'str')
        ET.SubElement(cell, TAG('v')).text = ''
    else:
        cell.attrib.pop('t', None)
        ET.SubElement(cell, TAG('v')).text = format(n, '.17g')


def _excel_percentile(values, p):
    items = sorted(x for x in values if x is not None)
    if not items:
        return None
    fractional = (len(items) - 1) * p
    lo = int(fractional)
    hi = min(len(items) - 1, lo + 1)
    return items[lo] + (items[hi] - items[lo]) * (fractional - lo)


def _excel_median(values):
    return _excel_percentile(values, .5)


def _compute_formula_caches(sheets):
    """Populate Excel cached results in a fixed, formula-audited 9-sheet template.

    This recalculates only the existing model's known financial formulas.  No
    new financial assumptions or invented historical values are introduced.
    Microsoft Excel remains responsible for subsequent interactive recalcs.
    """
    inputs = sheets[2]
    iv = lambda addr: _read_numeric_cell(inputs, addr)
    revenue_base = iv('B4')
    ncwc_base = iv('B5')
    settings = {'growth': iv('B11'), 'margin': iv('B12'), 'da': iv('B13'),
                'capex': iv('B14'), 'ncwc': iv('B15'), 'tax': iv('B16'),
                'wacc': iv('B17'), 'g': iv('B18'), 'roic': iv('B19')}
    if revenue_base is None or ncwc_base is None or any(v is None for v in settings.values()):
        raise ValueError('Missing DCF inputs for formula cache calculation')

    cases = {
        'Bear': (3, -.03, -.015, .005, .02, .01, -.005),
        'Base': (4, 0, 0, 0, 0, 0, 0),
        'Bull': (5, .03, .015, -.003, -.02, -.01, .005),
    }
    results = {}
    for name, (snum, dg, dm, dc, dn, dw, dt) in cases.items():
        s = sheets[snum]
        growth = settings['growth'] + dg
        margin = settings['margin'] + dm
        da_rate = settings['da']
        capex = max(0, settings['capex'] + dc)
        ncwc_rate = settings['ncwc'] + dn
        tax = settings['tax']
        wacc = settings['wacc'] + dw
        terminal_g = settings['g'] + dt
        roic = settings['roic']
        assumptions = (growth, margin, da_rate, capex, ncwc_rate, wacc, terminal_g, roic, tax)
        for col in 'BCDEF':
            for row, number in zip(range(5, 14), assumptions):
                _set_cached_formula(s, f'{col}{row}', number)
        prior_revenue = revenue_base
        prior_ncwc = ncwc_base
        discounted_flows = []
        for year, col in enumerate('BCDEF', 1):
            rev = prior_revenue * (1 + growth)
            ebit = rev * margin
            nopat = ebit * (1 - tax)
            da = rev * da_rate
            capex_amount = -rev * capex
            ncwc = rev * ncwc_rate
            delta_ncwc = prior_ncwc - ncwc
            fcff = sum((nopat, da, capex_amount, delta_ncwc))
            pv_factor = 1 / ((1 + wacc) ** year)
            discounted = fcff * pv_factor
            values = (rev, ebit, nopat, da, capex_amount, ncwc, delta_ncwc,
                      fcff, pv_factor, discounted)
            for row, value in zip(range(15, 25), values):
                _set_cached_formula(s, f'{col}{row}', value)
            prior_revenue = rev
            prior_ncwc = ncwc
            discounted_flows.append(discounted)
        terminal_nopat = nopat * (1 + terminal_g)
        terminal_reinvestment = -terminal_nopat * terminal_g / roic if roic else None
        terminal_fcff = (terminal_nopat + terminal_reinvestment) if terminal_reinvestment is not None else None
        terminal = terminal_fcff / (wacc - terminal_g) if terminal_fcff is not None and wacc > terminal_g else None
        terminal_pv = terminal / ((1 + wacc) ** 5) if terminal is not None else None
        pv_fcff = sum(discounted_flows)
        ev = pv_fcff + terminal_pv if terminal_pv is not None else None
        terminal_percent = terminal_pv / ev if ev else None
        for row, number in ((27, terminal_nopat), (28, terminal_reinvestment),
                            (29, terminal_fcff), (30, terminal), (31, terminal_pv),
                            (32, pv_fcff), (33, ev), (34, terminal_percent)):
            _set_cached_formula(s, f'B{row}', number)
        results[name] = dict(ev=ev, pv_fcff=pv_fcff, terminal_pv=terminal_pv,
                             wacc=wacc, terminal_percent=terminal_percent)

    shares = iv('B8')
    has_bridge = iv('B31') == 1 and all(iv(f'B{i}') is not None for i in range(27, 31))
    adjustment = (iv('B27') + iv('B29') - iv('B22') - iv('B28') - iv('B24') - iv('B30')) if has_bridge else None
    s = sheets[6]
    for row, case in zip((6, 7, 8), ('Bear','Base','Bull')):
        result = results[case]
        eq = result['ev'] + adjustment if adjustment is not None and result['ev'] is not None else None
        per_share = eq / shares if shares and eq is not None else None
        for col, number in zip('BCDEFGHI', (
                result['ev'], result['pv_fcff'], result['terminal_pv'],
                result['wacc'], result['terminal_percent'], adjustment, eq, per_share)):
            _set_cached_formula(s, f'{col}{row}', number)
        result['share'] = per_share

    s = sheets[7]
    selected_values = {'pe': [], 'pb': [], 'ev': []}
    for row in range(8, 13):
        read = lambda col: _read_numeric_cell(s, f'{col}{row}')
        market, debt, nci, cash, ebitda = (read(c) for c in 'HIJKL')
        ev = market + debt + nci - cash if all(v is not None for v in (market, debt, nci, cash)) else None
        multiple = ev / ebitda if ebitda and ev is not None and ebitda > 0 else None
        selected = read('B') == 1
        pe = read('M') if selected else None
        pb = read('N') if selected else None
        selected_ev = multiple if selected else None
        for col, v in zip('OPQRS', (ev, multiple, pe, pb, selected_ev)):
            _set_cached_formula(s, f'{col}{row}', v)
        if pe is not None: selected_values['pe'].append(pe)
        if pb is not None: selected_values['pb'].append(pb)
        if selected_ev is not None: selected_values['ev'].append(selected_ev)

    s = sheets[8]
    eps = iv('B6') / shares if shares else None
    book_per_share = iv('B7') / shares if shares else None
    for row, key, scalar in ((5, 'pe', eps), (6, 'pb', book_per_share)):
        vals = selected_values[key]
        _set_cached_formula(s, f'B{row}', len(vals))
        for col, quant in (('C', .25), ('D', .5), ('E', .75)):
            num = _excel_percentile(vals, quant) * scalar if len(vals) >= 2 and scalar is not None else None
            _set_cached_formula(s, f'{col}{row}', num)
    for row, case in ((7, 'Bear'), (8, 'Base'), (9, 'Bull')):
        _set_cached_formula(s, f'D{row}', results[case]['share'])
    multiple = _excel_median(selected_values['ev']) if len(selected_values['ev']) >= 2 else None
    ebitda_klbf = iv('B25') + iv('B26')
    for cell, num in (('D11', multiple), ('D12', ebitda_klbf),
                      ('D13', multiple * ebitda_klbf if multiple is not None else None),
                      ('D14', results['Base']['ev'])):
        _set_cached_formula(s, cell, num)


def create_excel_model(template_path:Path, *, data:dict, assumptions:dict,
                       bridge:dict, peer_rows:list, candidates:dict,
                       peer_selection:list, source_register:list, historical=None) -> bytes:
    """Return a workbook containing only source-backed input snapshots and Excel formulas."""
    if set(peer_selection)-set(FIVE):
        raise ValueError('Unsupported peer in Excel export')
    if not data.get('ready') or data.get('ticker')!='KLBF.JK':
        raise ValueError('KLBF approved scenario is required for workbook export.')
    updates={
      'Inputs':{
        'B4': historical.revenue_2025_bn if historical else 35324.544,
        'B5': historical.ncwc_2025_bn if historical else 9425.203,
        'B6': historical.parent_net_income_2025_bn if historical else 3664.998,
        'B7': historical.common_equity_2025_bn if historical else 23312.457,
        'B8': historical.shares_bn if historical else 45.28652861,
        'B9': historical.market_price_idr if historical else 1205.0,
        'B25': historical.ebit_2025_bn if historical else 4581.879,
        'B26': historical.da_2025_bn if historical else 814.193,
        'B11':assumptions.revenue_growth, 'B12':assumptions.ebit_margin,
        'B13':assumptions.da_to_revenue,'B14':assumptions.capex_to_revenue,
        'B15':assumptions.ncwc_to_revenue,'B16':assumptions.tax_rate,
        'B17':assumptions.wacc,'B18':assumptions.terminal_growth,'B19':assumptions.terminal_roic,
        'B31':1 if bridge.get('status') in ('ILLUSTRATIVE_ONLY','REFERENCE_CASE_UNCONFIRMED') else 0,
        'B32':bridge.get('source_note',bridge.get('source','NO COMPLETE ANALYST EQUITY SCENARIO')), 
        'B33':', '.join(t for t in FIVE if t in peer_selection),
      },'Peer Multiples':{},'Sources':{},'Guide':{}
    }
    reported=bridge.get('assumptions_used') if bridge.get('status') in ('ILLUSTRATIVE_ONLY','REFERENCE_CASE_UNCONFIRMED') else None
    mapped={'excess_cash_bn':'B27','nci_economic_bn':'B28','nonoperating_assets_bn':'B29','other_claims_bn':'B30'}
    for k,cell in mapped.items(): updates['Inputs'][cell]=reported.get(k) if reported else None
    for row,ticker in enumerate(FIVE,8):
        peer=next((x for x in peer_rows if x.get('Ticker')==ticker),None)
        if peer is None:raise ValueError('Peer data missing '+ticker)
        candidate=candidates.get(ticker,{})
        fields={
            'A':ticker,'B':1 if ticker in peer_selection else 0,'C':peer.get('Price date'),
            'D':peer.get('Price'),'E':peer.get('Parent NI (bn)'),
            'F':peer.get('Common equity (bn)'), 'G':peer.get('Shares (bn)'),
            'H':candidate.get('market_cap_bn'),'I':candidate.get('debt_book_bn'),
            'J':candidate.get('nci_book_bn'),'K':candidate.get('cash_book_bn'),
            'L':candidate.get('ebitda_candidate_bn'),'M':peer.get('P/E'),
            'N':peer.get('P/BV'),
            'T':('PROVIDER SCREEN — NOT PDF CERTIFIED' if ticker=='DVLA.JK' else
                 'SCREENING PROXY — book EV and EBITDA not fully reconciled')
        }
        for col,value in fields.items():
            if col in ('A','C','T'):normalized=value or ''
            else:normalized=checked_number(value)
            updates['Peer Multiples'][f'{col}{row}']=normalized

    for i,peer in enumerate(peer_rows):
        note=str(peer.get('Source note',''))
        if note.startswith('Manual price override'):
            updates['Sources'][f'A{23+i}']=peer.get('Ticker','')
            updates['Sources'][f'B{23+i}']='Peer price manual override'
            updates['Sources'][f'C{23+i}']=note[:190]
            updates['Sources'][f'D{23+i}']=peer.get('Price date','')
    for row,entry in enumerate(source_register[:15],5):
        fields={'A':entry.get('issuer'),'B':entry.get('period'),'C':entry.get('document'),
                'D':entry.get('publication_date') or 'Unverified',
                'E':entry.get('date_status'),'F':entry.get('url')}
        for col,v in fields.items():updates['Sources'][f'{col}{row}']=v or ''
    updates['Guide']['B3']='KLBF.JK / FY2025'
    if historical and historical.modified:
        updates['Guide']['B12'] = 'Historical input override (analyst supplied): '+historical.source_note[:180]
        updates['Guide']['B13'] = 'Last updated '+historical.last_updated+' | market quote '+historical.market_date
        updates['Sources']['A22'] = 'KLBF'
        updates['Sources']['B22'] = 'FY2025 / manual inputs'
        updates['Sources']['C22'] = historical.source_note[:180]
        updates['Sources']['D22'] = historical.last_updated
    updates['Guide']['C10']='Equity scenario: '+('BUNDLED REFERENCE — USER NOT CONFIRMED' if bridge.get('status')=='REFERENCE_CASE_UNCONFIRMED' else 'USER-CONFIRMED CONDITIONAL ASSUMPTIONS' if reported else 'NOT AVAILABLE')
    target_sheets={'Guide':1,'Inputs':2,'Peer Multiples':7,'Sources':9}
    parts={'xl/worksheets/sheet%d.xml'%target_sheets[name]:changes for name,changes in updates.items()}
    out=BytesIO()


    with ZipFile(template_path,'r') as zin:
        parts_by_filename = {info.filename:zin.read(info.filename) for info in zin.infolist()}
        original_infos = zin.infolist()
    sheet_roots = {}
    for i in range(1,10):
        name = 'xl/worksheets/sheet%d.xml' % i
        sheet_roots[i] = ET.fromstring(parts_by_filename[name])
    for sheet_name, changes in updates.items():
        sheet_index = target_sheets[sheet_name]
        for addr, value in changes.items():
            put_cell(sheet_roots[sheet_index], addr, value)
    _compute_formula_caches(sheet_roots)
    for i, root in sheet_roots.items():
        parts_by_filename['xl/worksheets/sheet%d.xml' % i] = ET.tostring(
            root, encoding='utf-8', xml_declaration=True)
    workbook_root=ET.fromstring(parts_by_filename['xl/workbook.xml'])
    calc=workbook_root.find(TAG('calcPr'))
    if calc is None:
        calc=ET.SubElement(workbook_root,TAG('calcPr'))
    calc.set('calcId','0')
    calc.set('calcMode','auto')
    calc.set('fullCalcOnLoad','1')
    calc.set('forceFullCalc','1')
    parts_by_filename['xl/workbook.xml']=ET.tostring(workbook_root,encoding='utf-8',xml_declaration=True)
    with ZipFile(out,'w',compression=ZIP_DEFLATED) as zout:
        for info in original_infos:
            zout.writestr(info, parts_by_filename[info.filename])
    return out.getvalue()
