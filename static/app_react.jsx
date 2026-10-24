
const {useState,useEffect,useMemo}=React;
const fmt=(v,d=1)=>v===null||v===undefined||v===''||!Number.isFinite(Number(v))?'—':Number(v).toLocaleString('en-US',{maximumFractionDigits:d,minimumFractionDigits:d});
const pct=v=>v===null||v===undefined?'—':(v>=0?'+':'')+fmt(v,1)+'%';
const BN=v=>v===null||v===undefined?'—':'Rp '+fmt(v/1000,2)+' T';
const IDR=v=>v===null||v===undefined?'—':'Rp '+fmt(v,0);
const Line=({label,value,highlight})=><div className="flex justify-between items-center py-2 border-b border-slate-100 gap-4"><span className="hint">{label}</span><span className={'mono text-right font-semibold '+(highlight?'emphasis':'')}>{value}</span></div>;
const Kpi=({label,value,extra})=><div className="card p-4"><div className="lbl mb-2">{label}</div><div className="kpi mono">{value}</div><div className="text-xs hint mt-2">{extra}</div></div>;
const Panel=({title,subtitle,children,right})=><section className="card mb-4 overflow-hidden"><header className="px-4 py-3 border-b border-slate-200 flex items-center justify-between gap-3"><div><div className="font-extrabold text-sm">{title}</div>{subtitle&&<div className="text-xs hint mt-1">{subtitle}</div>}</div>{right}</header><div className="p-4">{children}</div></section>;
function EquityBridge({reported,result,bridge,setBridge,onCalculate,busy,analystCase}){
  if(!reported || !result?.ready)return null;
  const r=reported.reported || {}, outcome=result.equity_bridge||{};
  const update=(key,val)=>setBridge(p=>({...p,[key]:val,submitted:false}));
  const inputs=[
    ['excess_cash_bn','Excess cash eligible for addition','Not all cash is automatically excess; FY2025 cash book ceiling applies.'],
    ['nci_economic_bn','NCI economic-value assumption','Book NCI is prefilled only as a clearly disclosed proxy.'],
    ['nonoperating_assets_bn','Separate non-operating assets','Include only investments not already captured in operating FCFF.'],
    ['other_claims_bn','Other non-equity claims','Consider pension/financing and other claims, excluding liabilities deducted elsewhere.']
  ];
  const cell=(v)=>v===null||v===undefined?'—':fmt(v,3);
  const reportedRows=[
    ['cash_book_bn','Cash & cash equivalents','Source balance; NOT automatically excess cash'],
    ['debt_book_bn','Debt including leases and finance payables','Book principal, debt fair value unresolved'],
    ['nci_book_bn','NCI book equity','Not the economic value of minority shareholders'],
    ['acquisition_payable_book_bn','Acquisition payable','Recognize separately, not again in operating NCWC'],
    ['shares_bn','Shares outstanding','Billion shares, excluding treasury']
  ];
  return <Panel title="STEP 2 — Enterprise-to-Equity Bridge (KLBF)" subtitle="FY2025 audited report balances are separated from uncertain economic values; amounts in IDR billions">
    <div className="warning mb-4"><b>No automatic zero assumptions.</b> Data below come from the FY2025 audit. An operating EV is not an equity value. FY2025 accounts were published after the year-end, so this is a retrospective model, not a December 2025 tradable price target.</div>
    <div className="tablewrap"><table><thead><tr><th>Reported FY2025 item</th><th>Amount (bn)</th><th>Basis / qualification</th></tr></thead><tbody>{reportedRows.map(([key,label,caveat])=><tr key={key}><td><b>{label}</b></td><td className="mono">{cell(r[key]?.value_bn)}</td><td className="text-left text-xs whitespace-normal max-w-lg"><div>{caveat}</div><div className="hint mt-1">{r[key]?.source}</div></td></tr>)}</tbody></table></div>
    {analystCase&&<div className="mt-4 bg-slate-50 border border-slate-200 rounded p-4 text-sm">
      <div className="flex flex-wrap gap-3 justify-between items-center"><div><div className="font-extrabold">FY2025 analyst case — sourced balances + explicit assumptions</div><div className="hint text-xs mt-1">Operating cash reserve {fmt(analystCase.reserve_rate_pct,0)}% of revenue is a modeling convention, NOT a reported company balance.</div></div>
      <button className="btn-light" onClick={()=>{setBridge(p=>({...p,...Object.fromEntries(Object.entries(analystCase.inputs).map(([k,v])=>[k,String(v)])),acknowledge_proxies:false,acknowledge_scope:false,submitted:false}));}}>Load analyst reference case</button></div>
      <div className="grid grid-cols-2 xl:grid-cols-4 gap-3 mt-3 text-xs"><div><div className="hint">Assumed excess cash</div><b className="mono">{fmt(analystCase.inputs.excess_cash_bn,2)} bn</b></div><div><div className="hint">Investments (book)</div><b className="mono">{fmt(analystCase.inputs.nonoperating_assets_bn,2)} bn</b></div><div><div className="hint">NCI (book proxy)</div><b className="mono">{fmt(analystCase.inputs.nci_economic_bn,2)} bn</b></div><div><div className="hint">Other claim: benefits (book)</div><b className="mono">{fmt(analystCase.inputs.other_claims_bn,2)} bn</b></div></div>
      <p className="hint text-xs mt-3">The button fills the form, but does not automatically approve assumptions, tick confirmations, or calculate a final value. Read the text and revise each assumption before submitting.</p>
    </div>}
    <div className="mt-4 text-sm font-bold">Explicit equity sensitivity (optional)</div>
    <p className="text-xs hint mt-1 mb-3">Enter all four numbers, including an explicit zero where supportable, then provide one source/rationale. These inputs are analyst assumptions, not replacements for reported history.</p>
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">{inputs.map(([key,label,hint])=><label key={key} className="block"><div className="text-xs font-bold mb-1">{label} (Rp bn)</div><input type="number" className="input w-full" step="any" min="0" max={key==='excess_cash_bn'?r.cash_book_bn?.value_bn:undefined} value={bridge[key]??''} onChange={e=>update(key,e.target.value)} placeholder="Unknown — enter a sourced assumption"/><div className="text-xs hint mt-1">{hint}</div></label>)}</div>
    <label className="block mt-4 text-xs font-bold">Source / method / justification for all assumptions, including explicit zero</label><textarea className="input w-full mt-2" style={{minHeight:82}} value={bridge.basis_note??''} onChange={e=>update('basis_note',e.target.value)} placeholder="Explain sources, assumptions and why there is no double-counting; cite report notes or analyst rationale."/>
    <div className="mt-3 space-y-3 text-sm"><label className="flex gap-2 items-start"><input type="checkbox" checked={!!bridge.acknowledge_proxies} onChange={e=>update('acknowledge_proxies',e.target.checked)}/><span>I accept that book debt and the contractual acquisition payable are unverified economic-value proxies, and I have assessed NCI separately.</span></label><label className="flex gap-2 items-start"><input type="checkbox" checked={!!bridge.acknowledge_scope} onChange={e=>update('acknowledge_scope',e.target.checked)}/><span>I have classified excess cash, non-operating assets, acquisition obligations and other claims consistently without double counting.</span></label></div>
    <div className="flex flex-wrap gap-2 mt-4"><button className="btn" disabled={busy} onClick={onCalculate}>Calculate analyst equity scenario</button><button className="btn-light" onClick={()=>{setBridge({excess_cash_bn:'',nci_economic_bn:String(r.nci_book_bn?.value_bn||''),nonoperating_assets_bn:'',other_claims_bn:'',basis_note:'',acknowledge_proxies:false,acknowledge_scope:false,submitted:false});}}>Clear scenario</button></div>
    {bridge.submitted && outcome.status==='ILLUSTRATIVE_ONLY'&&<div className="mt-4"><div className="warning mb-3"><b>CONDITIONAL SCENARIO — NOT CERTIFIED.</b> The results use analyst assumptions, book-value proxies and preliminary DCF operating EV. They are not certified equity values or investment recommendations.</div><div className="tablewrap"><table><thead><tr><th>Case</th><th>Operating EV (bn)</th><th>Bridge adjustment (bn)</th><th>Indicative equity (bn)</th><th>Scenario Rp/share</th></tr></thead><tbody>{['Bear','Base','Bull'].map(name=>{const v=outcome.scenario_values?.[name]||{};return <tr key={name}><td><b>{name}</b></td><td className="mono">{cell(v.operating_ev_bn)}</td><td className="mono">{cell(v.equity_adjustment_bn)}</td><td className="mono">{cell(v.illustrative_equity_bn)}</td><td className="mono emphasis">{IDR(v.illustrative_per_share_idr)}</td></tr>})}</tbody></table></div><p className="text-xs hint mt-3">Formula: operating EV + analyst-assessed excess cash + separate non-operating assets − book-debt proxy − economic NCI assumption − acquisition payable proxy − other claims. Divided by FY2025 shares. Changing DCF assumptions and recalculating also updates this scenario.</p></div>}
    {bridge.submitted && outcome.status!=='ILLUSTRATIVE_ONLY' &&<div className="warning mt-4"><b>Not yet calculable:</b> {outcome.reason} {outcome.missing?.length?'Missing: '+outcome.missing.join(', '):''}</div>}
    <div className="text-xs hint mt-4 border-t border-slate-200 pt-3"><b>Remaining audit limitations:</b> {reported.open_items.join('; ')}. Final fair value and BUY/SELL remain disabled regardless of scenario completion.</div>
  </Panel>
}

function ReconciliationView({result,bridge,onOpenDcf,onOpenPeers}){
  const r=result?.reconciliation;
  if(!result?.ready || !r)return <><h1 className="title mb-3">Valuation Reconciliation</h1><div className="warning">No company-specific reconciliation is available. Open KLBF to see its audited research methods; other covered tickers have peer data only.</div></>;
  const reference=r.historical_reference;
  const decision=result?.approach_selection;


  const referenceLevels=[decision?.range_low_idr_per_share,decision?.central_estimate_idr_per_share,decision?.range_high_idr_per_share];
  const validReference=decision?.range_source==='BUNDLED_REFERENCE_UNCONFIRMED'&&referenceLevels.every(x=>Number.isFinite(x)&&x>0)&&referenceLevels[0]<=referenceLevels[1]&&referenceLevels[1]<=referenceLevels[2];
  const bundledReference=validReference?[{
    method:'DCF Analyst Reference',label:'DCF equity — analyst reference (unconfirmed)',
    kind:'REFERENCE_DCF',quality:'REFERENCE / UNCONFIRMED',n_peers:null,peer_tickers:[],
    low_idr_per_share:referenceLevels[0],mid_idr_per_share:referenceLevels[1],high_idr_per_share:referenceLevels[2],
    versus_historical_price_pct:decision.historical_gap_pct,
  }]:[];
  const methods=[...(r.methods||[]).filter(m=>m.kind!=='ILLUSTRATIVE_DCF'||bridge.submitted),...bundledReference];
  const visible=methods.filter(m=>m.mid_idr_per_share!==null && m.low_idr_per_share!==null && m.high_idr_per_share!==null);
  const rel=visible.filter(m=>m.kind==='RELATIVE');
  const pe=rel.find(m=>m.method==='P/E'),pb=rel.find(m=>m.method==='P/BV');
  const hasConditional=visible.some(m=>m.kind==='ILLUSTRATIVE_DCF'||m.kind==='REFERENCE_DCF');
  const scenarioReady=Number.isFinite(decision?.central_estimate_idr_per_share)&&decision.central_estimate_idr_per_share>0;
  const scenarioTag=scenarioReady?`SCENARIO ${decision.rating} · CONDITIONAL`:'SCENARIO UNAVAILABLE';
  const maxPrice=Math.max(reference.price_idr,...visible.map(m=>m.high_idr_per_share),1)*1.13;
  const xpos=x=>Math.max(0,Math.min(100,(x/maxPrice)*100));
  const gap=v=>Number.isFinite(v)?(v>=0?'+':'')+fmt(v,1)+'%':'—';
  const tone=status=>status==='BLOCKED'||status==='UNVERIFIED'||status==='INSUFFICIENT PEERS'?'#a76520':status==='PRELIMINARY'?'#2559cc':'#736182';
  return <>
    <div className="flex flex-wrap items-center justify-between gap-3 mb-4"><div><h1 className="title">STEP 3 — Valuation Reconciliation</h1><p className="hint">Compare like-for-like per-share ranges, understand method divergence, and document unresolved valuation gates.</p></div><span className="tag">{scenarioTag}</span></div>
    <div className="gridk mb-4"><Kpi label="DCF · Operating EV" value={BN(r.operating_ev_bn)} extra="Enterprise value only — not Rp/share"/><Kpi label="P/E · Indicative midpoint" value={pe?IDR(pe.mid_idr_per_share):'N/A'} extra={pe?`${pe.n_peers} selected valid peers`:'Insufficient peers'}/><Kpi label="P/BV · Indicative midpoint" value={pb?IDR(pb.mid_idr_per_share):'N/A'} extra={pb?`${pb.n_peers} selected valid peers`:'Insufficient peers'}/><Kpi label="Conditional DCF Base / Share" value={scenarioReady?IDR(decision.central_estimate_idr_per_share):'—'} extra={scenarioReady?(decision.user_confirmed_bridge?'Analyst-submitted scenario · unverified':'Bundled analyst reference · unconfirmed'):'No complete equity scenario'}/></div>
    <p className="text-xs hint mb-4">Historical reference: {IDR(reference.price_idr)} on {reference.date} · Retrospective FY2025 study. See Reports & Sources for the information-cutoff explanation.</p>
    <Panel title="Comparable Valuation Ranges — Rp per Share" subtitle="P25–median–P75 peer quantiles. The DCF equity range is shown only as a qualified analyst reference or explicitly submitted scenario." right={<button className="btn-light" onClick={onOpenPeers}>Select peers →</button>}>
      {visible.length===0?<div className="warning">No comparable per-share method has adequate inputs. Select at least two valid peers.</div>:<div className="space-y-6">
        {visible.map((m)=>{
          const color=(m.kind==='ILLUSTRATIVE_DCF'||m.kind==='REFERENCE_DCF')?'#8c62b9':m.method==='P/E'?'#285fea':'#00866d';
          return <div key={m.method}>
            <div className="flex justify-between items-center gap-4 flex-wrap mb-2"><div><b className="text-sm">{m.label}</b><div className="hint text-xs">{m.kind==='REFERENCE_DCF'?'Bundled reference · unconfirmed':m.kind==='ILLUSTRATIVE_DCF'?'Analyst-submitted conditional scenario':`${m.n_peers} valid peers · P25 to P75`}</div></div><div className="mono text-xs"><span className="hint">{IDR(m.low_idr_per_share)} — </span><b>{IDR(m.mid_idr_per_share)}</b><span className="hint"> — {IDR(m.high_idr_per_share)}</span></div></div>
            <div role="img" aria-label={`${m.label}: lower ${Math.round(m.low_idr_per_share)}, midpoint ${Math.round(m.mid_idr_per_share)}, upper ${Math.round(m.high_idr_per_share)} rupiah per share; historic reference ${reference.price_idr}`} className="relative h-9 rounded-sm border border-slate-200 bg-slate-50">
              <div style={{position:'absolute',left:xpos(m.low_idr_per_share)+'%',width:Math.max(.5,xpos(m.high_idr_per_share)-xpos(m.low_idr_per_share))+'%',top:'35%',height:'30%',background:color,opacity:.42,borderRadius:2}}/>
              <div style={{position:'absolute',left:xpos(m.mid_idr_per_share)+'%',height:'74%',top:'13%',width:3,background:color,transform:'translateX(-50%)'}}/>
              <div style={{position:'absolute',left:xpos(reference.price_idr)+'%',height:'100%',top:0,width:2,background:'#ee9c18',transform:'translateX(-50%)'}}/>
            </div>
          </div>;
        })}
        <div className="flex flex-wrap gap-5 justify-between text-xs hint border-t pt-3"><span><span style={{background:'#ee9c18',display:'inline-block',width:9,height:9,marginRight:6}}/> Historical reference {IDR(reference.price_idr)} ({reference.date})</span><span>Colored band: range · colored tick: midpoint · orange tick: historical quote</span></div>
      </div>}
      <p className="text-xs hint mt-3">Peer quantiles are descriptive summaries, not statistical confidence intervals; the chart does not represent current-price opportunity. Any purple DCF row is explicitly hypothetical.</p>
    </Panel>
    <Panel title="EV/EBITDA — Enterprise-Level Peer Screen (Not Rp/Share)" subtitle="Separate from the football field because operating enterprise value and equity share price are not interchangeable">
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <Kpi label="Screen median multiple" value={result.relative?.find(x=>x.method==='EV/EBITDA')?.median==null?'N/A':fmt(result.relative.find(x=>x.method==='EV/EBITDA').median,2)+'×'} extra="Unreconciled peer EBITDA / book-value EV proxies"/>
        <Kpi label="KLBF implied EV screen" value={BN(result.relative?.find(x=>x.method==='EV/EBITDA')?.implied_ev_bn)} extra="Enterprise value only; unverified D&A"/>
        <Kpi label="DCF Base operating EV" value={BN(r.operating_ev_bn)} extra="Different forecasting methodology"/>
      </div>
    </Panel>
    <Panel title="Method-by-Method Diagnostic" subtitle="Identical Rp/share units only. Percentage differences are hindsight calculations, not expected investment returns.">
      <div className="tablewrap"><table><thead><tr><th>Method</th><th>Evidence status</th><th>Low (Rp/sh)</th><th>Midpoint (Rp/sh)</th><th>High (Rp/sh)</th><th>Gap vs historic close*</th></tr></thead><tbody>{methods.map(m=><tr key={m.method}><td><b>{m.method}</b><div className="text-xs hint">{m.quality}</div></td><td className="text-left text-xs whitespace-normal max-w-sm">{m.kind==='RELATIVE'?`${m.n_peers} peers: ${(m.peer_tickers||[]).join(', ')}`:m.kind==='REFERENCE_DCF'?'Bundled analyst reference; NOT user confirmed':'User-submitted bridge scenario'}</td><td>{IDR(m.low_idr_per_share)}</td><td className="emphasis font-bold">{IDR(m.mid_idr_per_share)}</td><td>{IDR(m.high_idr_per_share)}</td><td>{gap(m.versus_historical_price_pct)}</td></tr>)}</tbody></table></div>
      <p className="hint text-xs mt-3">* Historical screening gap = indicative midpoint / Rp{fmt(reference.price_idr,0)} − 1. Verify the information cutoff for the displayed reference date; this is a hindsight arithmetic comparison.</p>
      <div className="mt-4 border-t border-slate-200 pt-3 text-sm"><b>P/BV versus P/E midpoint difference:</b> <span className="mono emphasis">{gap(r.method_divergence?.pbv_to_pe_median_pct)}</span><p className="hint text-xs mt-2">{r.method_divergence?.reason} This difference should be explained using profitability, ROE, capital intensity, accounting policies, and peer business economics—not averaged away automatically.</p></div>
    </Panel>
    <Panel title="Readiness & Methodology Gates" subtitle="Current data-quality decisions; the presence of a numerical output does not certify an investment target."><div className="tablewrap"><table><thead><tr><th>Requirement</th><th>Status</th><th>Reason / next work</th></tr></thead><tbody>{(r.readiness_gates||[]).map(g=><tr key={g.label}><td><b>{g.label}</b></td><td><b style={{color:tone(g.status)}}>{g.status}</b></td><td className="whitespace-normal text-left max-w-xl text-xs">{g.why}</td></tr>)}</tbody></table></div></Panel>
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4"><div className="card p-4"><div className="font-extrabold mb-2">What we can conclude</div><p className="text-sm hint">The preliminary P/E and P/BV methods give separate implied ranges. The five-year DCF offers operating enterprise-value scenarios. {hasConditional?(bridge.submitted?'The DCF equity row uses an analyst-submitted bridge; its economic assumptions remain unverified.':'The DCF equity row uses a bundled analyst reference, not yet confirmed by the user. It is not a certified benchmark.'):'No supported DCF per-share scenario is currently available.'}</p></div><div className="card p-4"><div className="font-extrabold mb-2">What we cannot conclude</div><p className="text-sm hint">A certified combined fair-value target or current investment recommendation is not supported. The retrospective BUY/HOLD/SELL scenario classification is not a tradable signal; economic adjustments and information-cutoff issues remain unresolved.</p><button className="btn-light mt-4" onClick={onOpenDcf}>Inspect Step 2 Equity Bridge →</button></div></div>
  </>;
}
function RevenueChart({years}){const w=700,h=210,pad=42;const values=years.map(x=>Number(x.revenue_bn)||0);const high=Math.max(...values)*1.13;const xy=years.map((r,i)=>[(pad+(w-2*pad)*(i/(years.length-1))),(h-pad-((values[i]/high)*(h-2*pad)))]);return <svg viewBox={`0 0 ${w} ${h}`} width="100%" role="img" aria-label="KLBF annual revenue FY2022 to FY2025"><defs><linearGradient id="bluefade" x1="0" y1="0" x2="0" y2="1"><stop stopColor="#2b67ed" stopOpacity=".2"/><stop offset="1" stopColor="#2b67ed" stopOpacity=".015"/></linearGradient></defs>{[0,.25,.5,.75,1].map(t=><g key={t}><line x1={pad} x2={w-pad} y1={h-pad-(h-2*pad)*t} y2={h-pad-(h-2*pad)*t} stroke="#e6edf5" strokeDasharray="3 4"/><text x={pad-8} y={h-pad-(h-2*pad)*t+4} textAnchor="end" className="chart-label">{(high*t/1000).toFixed(0)}T</text></g>)}<path d={'M '+xy.map(x=>x.join(',')).join(' L ')+' L '+xy[xy.length-1][0]+','+(h-pad)+' L '+pad+','+(h-pad)+' Z'} fill="url(#bluefade)"/><polyline points={xy.map(x=>x.join(',')).join(' ')} stroke="#285fea" strokeWidth="3" fill="none"/>{xy.map((p,i)=><g key={i}><circle cx={p[0]} cy={p[1]} r="4" fill="white" stroke="#285fea" strokeWidth="2"/><text x={p[0]} y={h-16} textAnchor="middle" className="chart-label">{years[i].year}</text></g>)}</svg>}


function HistoricalDataEditor({draft,setDraft,active,peerDraft,setPeerDraft,peerActive,onApply,onReset,onPeerApply,onPeerRemove,onSave,onLoad,companies,busy}){
  const fields=window.VD_CONFIG.historicalFields;
  const change=(key,value)=>setDraft(prev=>({...prev,[key]:value}));
  const [peerTicker,setPeerTicker]=React.useState('TSPC.JK');
  const currentPeer=companies.find(c=>c.ticker===peerTicker);
  const quote=peerDraft?.[peerTicker]||{};
  const peerChange=(key,value)=>setPeerDraft(prev=>({...prev,[peerTicker]:{...(prev[peerTicker]||{}),[key]:value}}));
  return <>
    <div className="flex justify-between items-start flex-wrap gap-3 mb-5"><div><h1 className="title mb-1">Data Studio · Historical Input Manager</h1><p className="hint">Update actual KLBF FY2022–FY2025 amounts or dated peer quotes. Every change carries its own source and date.</p></div><span className="context-pill">KLBF PRIMARY · 5 REFERENCE PEERS</span></div>
    <div className="alert-strip mb-4 text-sm"><b>Data governance:</b> amounts below are editable inputs, not AI estimates. Nothing in the bundled audit is overwritten. Click Apply & Recalculate to update valuation outputs and the next Excel export. Changes apply to the current browser session only; save a JSON copy for later reuse.</div>
    <Panel title="01 · KLBF historical records" subtitle="Editable from the audited FY2025 baseline · Rp billions, except shares and price"
      right={<div className="flex flex-wrap gap-2"><button className="btn-light" onClick={onReset}>Reset audited snapshot</button><button className="btn" disabled={busy} onClick={onApply}>Apply & Recalculate</button></div>}>
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {fields.map(([key,label])=><div className="data-field" key={key}><label htmlFor={'data-'+key}>{label}</label><input id={'data-'+key} className="input" type="number" min={key.includes('revenue_')||key==='shares_bn'||key==='market_price_idr'?0.000001:0} step="any" value={draft?.[key]??''} onChange={e=>change(key,e.target.value)}/></div>)}
        <div className="data-field"><label htmlFor="historical-market-date">Market quote date</label><input id="historical-market-date" className="input" type="date" value={draft?.market_date||'2025-12-30'} onChange={e=>change('market_date',e.target.value)}/></div>
        <div className="data-field"><label htmlFor="historical-updated">Last updated (manual changes)</label><input id="historical-updated" className="input" type="date" value={draft?.last_updated||''} onChange={e=>change('last_updated',e.target.value)}/></div>
      </div>
      <div className="data-field mt-4"><label htmlFor="historical-source">Source link, report page, or analyst verification rationale</label><textarea id="historical-source" className="input" rows="2" placeholder="Example: KLBF FY2025 audited financial statements, p. 16; analyst checked ..." value={draft?.source_note||''} onChange={e=>change('source_note',e.target.value)}/></div>
      <div className="label-note mt-3">Required only when data values or market date differ from bundled defaults. EBIT, NCWC and D&A must be interpreted consistently with the projection ratios on Model Assumptions. FY2025 statements reported in 2026 remain retrospective.</div>
      <div className="flex gap-3 items-center mt-3 flex-wrap"><span className="tag">Applied dataset: {active?.last_updated||'FY2025 bundled audit'}</span><button className="btn-light" onClick={onSave}>Save input snapshot (.json)</button><label className="btn-light cursor-pointer">Import saved snapshot <input type="file" accept="application/json,.json" hidden onChange={e=>{const f=e.target.files?.[0];if(f)onLoad(f);e.target.value='';}}/></label></div>
    </Panel>
    <Panel title="02 · Comparable market quotes" subtitle="Peer quotes are for P/E, P/BV and EV/EBITDA screening—not six independently modeled DCFs.">
      <div className="alert-strip mb-4 text-sm">A revised peer price rebases its P/E and P/BV against the original reported EPS and book value/share denominators. Its simplified screening EV also updates. For a new financial period, replace the underlying peer financial data in the audited dataset before interpreting the ratio as fully current.</div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="data-field"><label htmlFor="peer-security">Peer security</label><select id="peer-security" className="input" value={peerTicker} onChange={e=>setPeerTicker(e.target.value)}>{companies.filter(x=>x.ticker!=='KLBF.JK').map(x=><option key={x.ticker} value={x.ticker}>{x.ticker} — {x.name}</option>)}</select></div>
        <div className="data-field"><label htmlFor="peer-quote">Quote (Rp/share)</label><input id="peer-quote" className="input" type="number" step="any" min="0.000001" placeholder={String(currentPeer?.market_price||'')} value={quote.price??''} onChange={e=>peerChange('price',e.target.value)}/></div>
        <div className="data-field"><label htmlFor="peer-quote-date">Quote date</label><input id="peer-quote-date" className="input" type="date" value={quote.price_date||currentPeer?.price_date||'2025-12-30'} onChange={e=>peerChange('price_date',e.target.value)}/></div>
        <div className="data-field"><label htmlFor="peer-update-date">Last updated</label><input id="peer-update-date" className="input" type="date" value={quote.last_updated||''} onChange={e=>peerChange('last_updated',e.target.value)}/></div>
      </div>
      <div className="data-field mt-4"><label htmlFor="peer-source">Price source / justification</label><textarea id="peer-source" className="input" rows="2" placeholder="Dated official quote or reliable provider URL" value={quote.source_note||''} onChange={e=>peerChange('source_note',e.target.value)}/></div>
      <div className="flex items-center gap-3 mt-3 flex-wrap"><button className="btn" disabled={busy} onClick={()=>onPeerApply(peerTicker)}>Apply peer quote</button><button className="btn-light" onClick={()=>onPeerRemove(peerTicker)}>Restore this peer</button><span className="label-note">{Object.keys(peerActive||{}).length} peers currently overridden</span></div>
    </Panel>
    <Panel title="03 · After an update" subtitle="One workflow, reproducible inputs"><div className="grid grid-cols-1 md:grid-cols-3 gap-3">{[
      ['1. Validate','All updated numbers and dates pass server checks; missing source details are rejected.'],
      ['2. Recalculate','FCFF/DCF, relative multiples, bridge, reconciliation and decision criteria use updated data.'],
      ['3. Export','Download Excel from the DCF workspace and archive this JSON input snapshot alongside the sources.']
    ].map(([title,desc])=><div key={title} className="case-card"><strong>{title}</strong><p className="hint text-sm mt-2">{desc}</p></div>)}</div></Panel>
  </>;
}
function PeerOnlyView({company,onHome,onData,onRelative,universe}){
  if(!company)return null;
  return <>
    <div className="flex justify-between gap-3 flex-wrap items-center mb-4"><div><h1 className="title">{company.ticker} · Comparative Research</h1><p className="hint">{company.name}</p></div><span className="context-pill">PEER-ONLY COVERAGE</span></div>
    <div className="alert-strip mb-4"><b>This is not a DCF model for {company.ticker}.</b> ValuDesk provides a fully integrated DCF and equity bridge for KLBF only. This issuer supplies source-qualified market multiples and peer screening to evaluate KLBF; no peer-specific FCFF is invented.</div>
    <div className="gridk mb-4"><Kpi label="Market share price" value={IDR(company.market_price)} extra={company.price_date}/><Kpi label="P/E" value={company.pe==null?'—':fmt(company.pe,2)+'×'} extra="Historical comparable"/><Kpi label="P/BV" value={company.pb==null?'—':fmt(company.pb,2)+'×'} extra="Historical comparable"/><Kpi label="EV/EBITDA proxy" value={company.ev_ebitda_proxy==null?'—':fmt(company.ev_ebitda_proxy,2)+'×'} extra="Screening, not certified"/></div>
    <Panel title="Coverage scope" subtitle="Clear separation between operating valuation and comparables"><div className="case-card"><b>{company.status}</b><p className="hint text-sm mt-2">{company.caveat||'The company is part of the fixed Indonesian healthcare peer universe.'}</p></div><div className="flex flex-wrap gap-3 mt-4"><button className="btn" onClick={onHome}>Open KLBF full valuation →</button><button className="btn-light" onClick={onRelative}>Compare KLBF peers</button><button className="btn-light" onClick={onData}>Update peer quote</button></div></Panel>
  </>;
}
function ApproachSelectionView({decision,onOpenBridge,onOpenPeers,embedded=false}){
  if(!decision)return <div className="warning">No completed KLBF model. Select KLBF, then recalculate to see documented method selection.</div>;
  return <div>
    {!embedded&&<div className="mb-4"><h1 className="title">Valuation Approach & Decision Framework</h1><p className="hint">Explicit financial rules, methods, conditions, and limitations—not a fabricated investment signal.</p></div>}
    <div className="gridk mb-4"><Kpi label="Preferred analytical method" value={decision.preferred_method.replace(' — ',' · ')} extra="Rule-based, not a final rating"/><Kpi label="Conditional central estimate" value={IDR(decision.central_estimate_idr_per_share)} extra={decision.user_confirmed_bridge?'User-confirmed analyst case':'Bundled analyst reference · unconfirmed'}/><Kpi label="Conditional Bear–Bull band" value={decision.range_low_idr_per_share!=null?IDR(decision.range_low_idr_per_share)+' – '+IDR(decision.range_high_idr_per_share):'—'} extra="Reference / share · conditional, not certified"/><Kpi label="Decision status" value={decision.rating} extra="Retrospective scenario classification only"/></div>
    <Panel title="Why this valuation approach?" subtitle="Method-selection rules are recalculated whenever the financial data or assumptions change"><div className="alert-strip text-sm">{decision.method_reason}</div>
      <div className="tablewrap mt-3"><table><thead><tr><th>Decision criterion</th><th>Result</th></tr></thead><tbody>{decision.rules.map((item,i)=><tr key={i}><td>{item.rule}</td><td><span className={item.passed?'good':'status'}>{item.passed?'PASS':'NOT MET'}</span></td></tr>)}</tbody></table></div>
      <p className="hint text-xs mt-3">Peer methods: {(decision.secondary_methods||[]).join(' and ')||'Not enough comparable coverage'}. All peer valuation ranges remain unverified screening evidence.</p>
    </Panel>
    <Panel title="Conditional outcome, historical comparison and recommendation" subtitle="Historical scenario screen under disclosed thresholds; not an investment recommendation">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-3"><div className="case-card"><div className="lbl">Historical market reference</div><div className="kpi mono mt-2">{IDR(decision.historical_price_idr)}</div><div className="hint text-xs mt-2">{decision.market_date} · retrospective comparison</div></div><div className="case-card"><div className="lbl">Scenario gap vs historical reference</div><div className="kpi mono mt-2">{pct(decision.historical_gap_pct)}</div><div className="hint text-xs mt-2">Hindsight arithmetic only; NOT expected return or current upside</div></div></div>
      <p className="text-sm mb-2"><b>Scenario interpretation: </b>{decision.recommendation}</p><p className="text-xs hint">Evidence status: {decision.range_source==='USER_CONFIRMED'?'Submitted analyst inputs; economic proxies remain unverified':'Bundled analyst reference; not submitted or confirmed by the user'}. Certified investment rating: unavailable.</p>
      <p className="hint text-sm">{decision.rating_reason}</p>
      <div className="label-note mt-3">Scenario decision rule: BUY if gap exceeds +15%, SELL if gap is below −10%, otherwise HOLD. This classification compares a retrospective model against a 2025 quote using information published in 2026, not a tradable recommendation.</div>
      <div className="flex flex-wrap gap-2 mt-4"><button className="btn-light" onClick={onOpenBridge}>Inspect equity bridge →</button><button className="btn-light" onClick={onOpenPeers}>Inspect comparable selection →</button></div>
    </Panel>
  </div>;
}

function App(){const [bridge,setBridge]=useState({excess_cash_bn:'',nci_economic_bn:'',nonoperating_assets_bn:'',other_claims_bn:'',basis_note:'',acknowledge_proxies:false,acknowledge_scope:false,submitted:false}),[boot,setBoot]=useState(null),[page,setPage]=useState('dashboard'),[ticker,setTicker]=useState('KLBF.JK'),[peerTickers,setPeerTickers]=useState(['TSPC.JK','SOHO.JK']),[values,setValues]=useState(null),[result,setResult]=useState(null),[busy,setBusy]=useState(false),[error,setError]=useState(''),[tab,setTab]=useState('Base'),[historicalDraft,setHistoricalDraft]=useState(null),[historicalActive,setHistoricalActive]=useState(null),[peerDraft,setPeerDraft]=useState({}),[peerActive,setPeerActive]=useState({}),[dataMessage,setDataMessage]=useState('');
useEffect(()=>{fetch('/api/bootstrap').then(r=>r.json()).then(x=>{setBoot(x);setValues(x.defaults);setHistoricalDraft(x.historical_defaults);setBridge(p=>({...p,nci_economic_bn:String(x.reported_bridge?.reported?.nci_book_bn?.value_bn??'')}))}).catch(e=>setError('Cannot load local data: '+e.message))},[]);
const params=useMemo(()=>({...values,ticker,peers:peerTickers,...(historicalActive?{historical_update:historicalActive}:{}),...(Object.keys(peerActive).length?{peer_updates:peerActive}:{}),...(bridge.submitted?{equity_bridge:{...bridge}}:{})}),[values,ticker,peerTickers,bridge,historicalActive,peerActive]);
async function calculate(body=params){if(!body)return;setBusy(true);setError('');try{const r=await fetch('/api/calculate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});const x=await r.json();if(!r.ok)throw Error(x.error||'Calculation failed');setResult(x);return x}catch(e){setError(e.message);return null}finally{setBusy(false)}}
useEffect(()=>{if(values)calculate({...params,ticker})},[ticker,!!values]);
const universe=result?.market_universe||boot?.companies||[];
const co=universe.find(x=>x.ticker===ticker),isKLBF=ticker==='KLBF.JK',historical=boot?.audit,last=result?.historical_years||historical?.last_years||[];
const displayPrice=isKLBF?(result?.historical?.market_price_idr??historical?.market_price):co?.market_price;
const historicOverride=historicalActive||boot?.historical_defaults;
const menu=[['dashboard','◫','Executive Dashboard'],['financial','▤','Financial Analysis'],['data','▦','Historical Data Studio'],['valuation','◈','DCF Valuation'],['relative','≋','Relative Valuation'],['reconciliation','≐','Valuation Reconciliation'],['approach','◎','Valuation Decision'],['assumptions','☷','Model Assumptions'],['sources','◎','Reports & Sources']];
async function exportCsv(){if(!result?.ready)return;try{const r=await fetch('/api/export',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(params)});if(!r.ok)throw Error('Could not export');const blob=await r.blob();const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='ValuDesk_KLBF_Preliminary_FCFF.csv';a.click();URL.revokeObjectURL(a.href)}catch(e){setError(e.message)}}
async function exportExcel(){if(!result?.ready||ticker!=='KLBF.JK'){setError('Excel valuation model is available for KLBF only.');return;}try{setError('');const r=await fetch('/api/export/excel',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(params)});if(!r.ok){const j=await r.json();throw Error(j.error||'Excel export failed')}const blob=await r.blob();const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download='ValuDesk_KLBF_FY2025_Financial_Model_Preliminary.xlsx';document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),2000);}catch(e){setError(e.message)}}
function requestEquityBridge(){setBridge(p=>({...p,submitted:true}));calculate({...params,equity_bridge:{...bridge,submitted:true}})}
function changeVal(k,v){setValues(p=>({...p,[k]:v}))}
function chooseTicker(v){setTicker(v);setResult(null);setPage('dashboard')}
async function applyHistorical(){
  const next={...historicalDraft};

  const base=boot.historical_defaults;
  const rateMap={ebit_margin:'ebit_2025_bn',da_to_revenue:'da_2025_bn',capex_to_revenue:'capex_2025_bn',ncwc_to_revenue:'ncwc_2025_bn'};
  const revised={...values};
  for(const [key,f] of Object.entries(rateMap)){
    if(Math.abs(Number(values[key])-Number(boot.defaults[key]))<.00011){
      revised[key]=Number((100*Number(next[f])/Number(next.revenue_2025_bn)).toFixed(5));
    }
  }
  const r=await calculate({...params,...revised,ticker:'KLBF.JK',historical_update:next});
  if(r?.ready){setHistoricalActive(next);setValues(revised);setDataMessage('Validated: historical inputs and untouched historical-based forecast rates are active; Excel export will match.')} 
}
async function resetHistorical(){const next={...boot.historical_defaults};const r=await calculate({...params,ticker:'KLBF.JK',historical_update:next});
  if(r?.ready){setHistoricalDraft(next);setHistoricalActive(null);setDataMessage('Original bundled KLBF inputs restored.')}
}
async function applyPeer(t){const old=peerDraft[t]||{};const next={...peerActive,[t]:{...old,price_date:old.price_date||universe.find(x=>x.ticker===t)?.price_date}};
  const r=await calculate({...params,ticker:'KLBF.JK',peer_updates:next});if(r?.ready){setPeerActive(next);setDataMessage(t+' quote updated; comparable ratios recalculated.')}
}
async function removePeer(t){const next={...peerActive};delete next[t];const r=await calculate({...params,ticker:'KLBF.JK',peer_updates:next});
 if(r?.ready){setPeerActive(next);setPeerDraft(p=>{const copy={...p};delete copy[t];return copy});setDataMessage('Restored '+t+' market snapshot.')}
}
function saveInputs(){const payload={schema:'valudesk-2.7-inputs',historical:historicalActive||boot.historical_defaults,peers:peerActive,assumptions:values,notes:'Manually verified dates and source notes must accompany updates.'};
 const blob=new Blob([JSON.stringify(payload,null,2)],{type:'application/json'});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download='ValuDesk_Input_Snapshot.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
async function loadInputs(file){try{const payload=JSON.parse(await file.text());if(payload.schema!=='valudesk-2.7-inputs'||!payload.historical||!payload.assumptions||!payload.peers)throw Error('Invalid snapshot schema');
 const r=await calculate({...params,...payload.assumptions,ticker:'KLBF.JK',historical_update:payload.historical,peer_updates:payload.peers});
 if(r?.ready){setHistoricalDraft(payload.historical);setHistoricalActive(payload.historical);setPeerActive(payload.peers);setValues(payload.assumptions);setPeerDraft(payload.peers);setDataMessage('Saved input snapshot imported and recalculated.')}else throw Error('Server rejected saved inputs');
 }catch(e){setError('Snapshot import: '+e.message)}}
const ev=result?.scenarios||{},rel=result?.relative||[];


const bridgeIsUserConfirmed=Boolean(bridge.submitted && result?.equity_bridge?.status==='ILLUSTRATIVE_ONLY');
const displayBridge=bridgeIsUserConfirmed?result?.equity_bridge:result?.reference_bridge;
const bridgeScenarioValues=displayBridge?.scenario_values;
const bridgeBaseShare=bridgeScenarioValues?.Base?.illustrative_per_share_idr;
const hasShareEstimate=isKLBF && !!result?.ready
  && bridgeBaseShare!==null && bridgeBaseShare!==undefined
  && Number.isFinite(Number(bridgeBaseShare));
const displayShares=hasShareEstimate?bridgeScenarioValues:null;
const bridgeDescriptor=bridgeIsUserConfirmed?'User-confirmed analyst scenario · conditional':'Bundled analyst reference · not user-confirmed';
function Dashboard(){
  return <>
    <div className="flex items-center justify-between gap-2 flex-wrap mb-4">
      <div><h1 className="title">Executive Coverage & Valuation Overview</h1>
        <div className="hint">Focused Indonesian healthcare equity research · Historical FY2025 exercise</div>
      </div>
      <span className="tag">RETROSPECTIVE · NOT CERTIFIED</span>
    </div>
    <div className="gridk mb-4">
      <Kpi label="Coverage universe" value="6 issuers" extra="KLBF + 5 peer candidates"/>
      <Kpi label="Market close — selected" value={IDR(co?.market_price)} extra={'Historical quote · '+(co?.price_date||'—')}/>
      <Kpi label="KLBF base operating EV" value={isKLBF&&ev.Base?BN(ev.Base.ev_bn):'Not modeled'} extra="Operating enterprise value only"/>
      <Kpi
        label="DCF Base estimate / share"
        value={isKLBF?(displayShares?IDR(displayShares.Base.illustrative_per_share_idr):'—'):'Not modeled'}
        extra={displayShares?bridgeDescriptor+' · not certified':isKLBF?'Unable to compute reference equity scenario':'DCF equity modeling is available for KLBF only'}
      />
    </div>
    <div className="mb-4 flex justify-end"><button className="btn-light" onClick={()=>setPage('approach')}>Open evidence-led valuation decision →</button></div>
    {displayShares && <Panel
      title="DCF Equity Scenario — Analyst Estimate"
      subtitle={bridgeDescriptor+" · values per KLBF share"}
      right={<button className="btn-light text-xs" onClick={()=>setPage('valuation')}>Review assumptions →</button>}
    >
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {['Bear','Base','Bull'].map(name=><div key={name} className={'p-4 rounded border '+(name==='Base'?'bg-blue-50 border-blue-200':'bg-slate-50 border-slate-200')}>
          <div className="lbl">{name} · DCF Equity / Share</div>
          <div className="text-xl font-extrabold mono mt-2">{IDR(displayShares[name]?.illustrative_per_share_idr)}</div>
          <div className="hint text-xs mt-1">Conditional scenario, not a certified target</div>
        </div>)}
      </div>
    </Panel>}
    <div className="alert-strip mb-4"><b>Study scope:</b> This is a retrospective research illustration. FY2025 accounts published in 2026 cannot justify a point-in-time 2025 investment decision. Per-share reference scenarios use disclosed analyst proxies and are not current trading signals. User confirmation remains separate.</div>
    <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
      <Panel title="KLBF Historical Revenue" subtitle="Reported/provider financial history; IDR billions"><RevenueChart years={last}/></Panel>
      <Panel title="DCF Enterprise Value Scenarios" subtitle="Five-year FCFF · values are operating EV, not equity value">
        <div className="space-y-5">{['Bear','Base','Bull'].map(n=>{
          const v=ev[n]?.ev_bn;
          const max=Math.max(...Object.values(ev).map(x=>x?.ev_bn||0),1);
          return <div key={n}><div className="flex justify-between mb-2"><b className="text-sm">{n}</b><b className="mono">{BN(v)}</b></div><div className="bartrack"><div className="barfill" style={{width:((v||0)/max*100)+'%',background:n==='Bear'?'#d18b50':n==='Bull'?'#008b68':'#285fea'}}/></div></div>
        })}</div>
        <div className="mt-5 border-t pt-4 hint text-xs">FCFF, NCWC and terminal assumptions remain preliminary. NCI, acquisition payables and financing claims are not fully reconciled.</div>
      </Panel>
    </div>
    <Panel title="Relative Valuation Benchmark" subtitle="P/E and P/BV equity screens; EV/EBITDA enterprise-only proxy" right={<button className="btn-light text-xs" onClick={()=>setPage('relative')}>Review peers →</button>}>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">{rel.map(x=><div key={x.method} className="bg-slate-50 p-4 rounded border border-slate-200"><div className="lbl">{x.method}</div><div className="text-xl font-extrabold mono mt-2">{x.method==='EV/EBITDA'?(x.median==null?'N/A':fmt(x.median,2)+'×'):(x.fair_value===null?'N/A':IDR(x.fair_value))}</div><div className="hint text-xs mt-1">{x.status} {x.n?'· '+x.n+' valid peers':''}</div></div>)}</div>
    </Panel>
  </>
}
function Financial(){return <><h1 className="title mb-1">Financial Analysis</h1><p className="hint mb-4">Source-aware historical inputs. Missing figures are not replaced with fabricated data.</p><div className="gridk mb-4"><Kpi label="FY2025 Revenue" value={BN(isKLBF?(result?.historical?.revenue_2025_bn??co?.revenue_bn):co?.revenue_bn)} extra={co?.ticker}/><Kpi label="FY2025 Sales Growth" value={pct(co?.sales_growth)} extra="Provider / calculated"/><Kpi label="FY2025 Operating EBIT" value={isKLBF?BN(result?.historical?.ebit_2025_bn??historical?.operating_ebit_bn):'Not verified'} extra="KLBF sourced subtotal only"/><Kpi label="Parent Net Income" value={isKLBF?BN(result?.historical?.parent_net_income_2025_bn??historical?.net_income_parent_bn):BN(co?.net_income_bn)} extra="FY2025 accounting basis"/></div><Panel title="Revenue History — KLBF" subtitle="IDR billions; figures other than FY2025 should be treated as provider-derived historical context"><div className="tablewrap"><table><thead><tr><th>Financial year</th><th>Revenue (IDR bn)</th><th>Year-over-year growth</th><th>Data qualification</th></tr></thead><tbody>{last.map((x,i)=><tr key={x.year}><td><b>{x.year}</b></td><td className="mono">{fmt(x.revenue_bn,2)}</td><td>{i?pct((x.revenue_bn/last[i-1].revenue_bn-1)*100):'—'}</td><td>{result?.historical?.modified?'Manual update · source in Data Studio':(x.year===2025?'Verified KLBF FY2025':'Provider snapshot; verify with annual report')}</td></tr>)}</tbody></table></div></Panel><Panel title="Healthcare Universe — Financial Comparison" subtitle="Six fixed issuers. No general market ticker input required."><div className="tablewrap"><table><thead><tr><th>Company</th><th>Revenue FY2025 (bn)</th><th>Sales growth</th><th>Market close</th></tr></thead><tbody>{universe.map(c=><tr key={c.ticker}><td><button className="font-bold emphasis" onClick={()=>chooseTicker(c.ticker)}>{c.ticker}</button><div className="text-xs hint">{c.name}</div></td><td className="mono">{fmt(c.revenue_bn,2)}</td><td className="mono">{pct(c.sales_growth)}</td><td className="mono">{IDR(c.market_price)}</td></tr>)}</tbody></table></div></Panel></>}
function DCF(){return <><div className="flex justify-between items-center mb-4"><div><h1 className="title">DCF Valuation Workspace</h1><p className="hint">FCFF → Discounting → Enterprise Value; equity bridge requires additional validation</p></div><div className="flex flex-wrap gap-2"><button className="btn-light" onClick={exportExcel} disabled={busy||!result?.ready}>↓ Download Excel (.xlsx)</button><button className="btn" onClick={()=>calculate()} disabled={busy}>↻ {busy?'Calculating...':'Refresh Forecast'}</button></div></div>{!result?.ready?<div className="warning">{result?.message||'No approved DCF model available for this company.'} Select KLBF to view the case-study forecast.</div>:<><div className="gridk mb-4">{['Bear','Base','Bull'].map(n=><Kpi key={n} label={`${n} Operating EV`} value={BN(ev[n]?.ev_bn)} extra={`WACC ${fmt(ev[n]?.wacc_pct,2)}% · 5-year projection`}/>)}<Kpi
    label="DCF estimate / share · Base"
    value={displayShares?IDR(displayShares.Base.illustrative_per_share_idr):'—'}
    extra={displayShares
      ? bridgeDescriptor+' · not a certified target'
      : 'No valid reference scenario available'}
  /></div><Panel title="Explicit 5-Year FCFF Forecast" subtitle="2026–2030 forecast · IDR billions · calculated live from assumptions" right={<button onClick={exportCsv} className="btn-light">↓ Export CSV</button>}><div className="tablewrap"><table><thead><tr><th>Financial line (IDR bn)</th>{(result.forecast||[]).map(r=><th key={r.FY}>{r.FY}E</th>)}</tr></thead><tbody>{[['Revenue','Revenue'],['EBIT','Operating EBIT'],['NOPAT','NOPAT'],['D&A','(+) D&A'],['CapEx','(-) CapEx'],['Delta NCWC','(-/+) Δ NCWC'],['FCFF','Free Cash Flow to Firm']].map(([k,label])=><tr key={k} className={k==='FCFF'?'bg-blue-50 font-bold':''}><td>{label}</td>{result.forecast.map(x=><td key={x.FY} className="mono">{fmt(x[k],1)}</td>)}</tr>)}</tbody></table></div></Panel><div className="grid grid-cols-1 xl:grid-cols-2 gap-4"><Panel title="Enterprise Value Reconciliation" subtitle="Operating enterprise value before equity bridge adjustments"><Line label="Present value of forecast FCFF" value={BN(ev.Base?.pv_forecast_bn)}/><Line label="Present value of terminal value" value={BN(ev.Base?.pv_terminal_bn)}/><Line label="Operating enterprise value" value={BN(ev.Base?.ev_bn)} highlight/><Line label="Terminal EV share" value={fmt(ev.Base?.terminal_share_pct,1)+'%'}/><div className="warning mt-4">Full economic equity bridge remains UNCERTIFIED. See the documented balances and optional assumptions below; finance payables are INCLUDED in debt and acquisition payable is separate.</div></Panel><Panel title="WACC × Terminal Growth Sensitivity" subtitle="Operating EV · IDR trillions; not share-price estimates"><div className="tablewrap"><table><thead><tr><th>Δ WACC \ Δ g</th>{[-1,-.5,0,.5,1].map(x=><th key={x}>{x>0?'+':''}{x}%</th>)}</tr></thead><tbody>{(result.sensitivity_ev_bn||[]).map((r,i)=><tr key={i}><td className="mono">{[-2,-1,0,1,2][i]>0?'+':''}{[-2,-1,0,1,2][i]}%</td>{r.map((v,j)=><td key={j} className={'mono '+(i===2&&j===2?'bg-blue-100 font-bold':'')}>{v===null?'—':fmt(v/1000,2)}</td>)}</tr>)}</tbody></table></div></Panel></div><EquityBridge reported={result?.reported_bridge||boot.reported_bridge} result={result} bridge={bridge} setBridge={setBridge} onCalculate={requestEquityBridge} busy={busy} analystCase={boot?.analyst_case}/></>}</>}
function Relative(){
 const toggle=t=>setPeerTickers(p=>p.includes(t)?p.filter(x=>x!==t):[...p,t]);
 const candidates=result?.peer_candidates||boot.ev_ebitda_candidates||{};
 const screen=rel.find(x=>x.method==='EV/EBITDA');
 const perShare=rel.filter(x=>x.method!=='EV/EBITDA');
 return <>
  <div className="flex flex-wrap items-center justify-between gap-3 mb-4"><div>
   <h1 className="title">Relative Valuation & Comparable Peers</h1>
   <p className="hint">P/E and P/BV equity multiples · EV/EBITDA is a separately labelled, unverified screening proxy</p>
  </div><button className="btn" onClick={()=>calculate()} disabled={busy}>↻ Apply Peer Selection</button></div>
  <Panel title="Comparable Group" subtitle="TSPC and SOHO are primary comparability candidates. Select supplementary peers for sensitivity.">
   <div className="flex flex-wrap gap-3">{universe.filter(c=>c.ticker!=='KLBF.JK').map(c=><label className="option" key={c.ticker}><input type="checkbox" checked={peerTickers.includes(c.ticker)} onChange={()=>toggle(c.ticker)}/><b>{c.ticker}</b><span className="hint text-xs">{c.role==='Core comparable'?'Core':'Sensitivity'}</span></label>)}</div>
   <div className="text-xs hint mt-3">Click Apply Peer Selection to update each method. Two eligible peers are required for a median. DVLA now has a separate, provider-cross-checked screening estimate (not primary-PDF-verified). Select DVLA and click Apply to include it in the screening median; the default core set remains TSPC + SOHO.</div>
  </Panel>
  <Panel title="Peer Market Multiples — FY2025" subtitle="Dated historical quotes; EBITDA and simplified EV use unreconciled FY2025 audit candidates">
   <div className="tablewrap"><table><thead><tr><th>Ticker / company</th><th>Share price</th><th>P/E</th><th>P/BV</th><th>EV/EBITDA proxy*</th><th>Basis</th></tr></thead>
   <tbody>{universe.filter(c=>c.ticker!=='KLBF.JK').map(c=>{const proxy=candidates[c.ticker]||{};return <tr key={c.ticker}>
    <td><b>{c.ticker}</b><div className="text-xs hint">{c.name}</div></td><td>{IDR(c.market_price)}</td>
    <td>{c.pe===null?'N/A':fmt(c.pe,2)+'×'}</td><td>{c.pb===null?'N/A':fmt(c.pb,2)+'×'}</td>
    <td className={proxy.multiple_x===null||proxy.multiple_x===undefined?'danger':'text-amber-700'}>{proxy.multiple_x==null?'Excluded':fmt(proxy.multiple_x,2)+'× · '+(proxy.status==='PROVIDER_SCREEN_ONLY'?'Provider screen':'Screen')}</td>
    <td><span className="status">{c.role}</span></td></tr>})}</tbody></table></div>
   <p className="hint text-xs mt-3">* Screen only: simplified EV = market capitalization + reported book debt + book NCI − full reported cash. EBITDA amounts come from unreconciled FY2025 audit candidates. Missing non-operating asset/claims adjustments and required operating cash are NOT assumed zero for a certified EV; therefore these ratios cannot be investment targets.</p>
  </Panel>
  <Panel title="EV/EBITDA Transparency — Screening Model" subtitle="The bridge and EBITDA denominator are visible so the ratio can be checked; not a certified comparables valuation">
   <div className="tablewrap"><table><thead><tr><th>Ticker</th><th>Market cap (Rp bn)</th><th>Debt book</th><th>NCI book</th><th>Cash book</th><th>Simplified EV (Rp bn)</th><th>EBITDA candidate (Rp bn)</th><th>Ratio</th></tr></thead><tbody>{peerTickers.map(t=>{const x=candidates[t]||{};return <tr key={t}>
    <td><b>{t}</b></td><td>{fmt(x.market_cap_bn,2)}</td><td>{fmt(x.debt_book_bn,2)}</td><td>{fmt(x.nci_book_bn,2)}</td><td>{fmt(x.cash_book_bn,2)}</td><td>{fmt(x.simplified_ev_bn,2)}</td><td>{fmt(x.ebitda_candidate_bn,2)}</td><td>{x.multiple_x==null?'Excluded':fmt(x.multiple_x,2)+'×'+(x.status==='PROVIDER_SCREEN_ONLY'?' *':'')}</td>
   </tr>})}</tbody></table></div>
   <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mt-4">
    <Kpi label="Selected-screen median EV/EBITDA" value={screen?.median==null?'N/A':fmt(screen.median,2)+'×'} extra={`${screen?.n||0} eligible peer proxies`}/>
    <Kpi label="KLBF EBITDA audit candidate" value={screen?.klbf_ebitda_candidate_bn==null?'N/A':BN(screen.klbf_ebitda_candidate_bn)} extra="Operating EBIT + unreconciled D&A; provisional"/>
    <Kpi label="KLBF implied operating EV · screen" value={screen?.implied_ev_bn==null?'N/A':BN(screen.implied_ev_bn)} extra="Enterprise value ONLY — not Rp/share"/>
   </div>
   <div className="hint text-xs mt-3">Selected P25–P75 EV range: {screen?.implied_ev_low_bn==null?'N/A':BN(screen.implied_ev_low_bn)} to {screen?.implied_ev_high_bn==null?'N/A':BN(screen.implied_ev_high_bn)}. Do not blend this EV screen with P/E or P/BV share prices. The KLBF D&A estimate is not certified.</div>
  </Panel>
  <Panel title="Implied KLBF Equity Valuation Range — Preliminary" subtitle="Only P/E and P/BV imply Rp per share; selected peer P25 / median / P75 are descriptive, not statistical bounds">
   <div className="tablewrap"><table><thead><tr><th>Method</th><th>Valid peers</th><th>P25 multiple</th><th>Median multiple</th><th>P75 multiple</th><th>Low (Rp/sh)</th><th>Median (Rp/sh)</th><th>High (Rp/sh)</th></tr></thead><tbody>{perShare.map(x=><tr key={x.method}>
   <td><b>{x.method}</b></td><td>{x.n}</td><td>{fmt(x.p25,2)}</td><td>{fmt(x.median,2)}</td><td>{fmt(x.p75,2)}</td><td>{IDR(x.low)}</td><td className="emphasis font-bold">{IDR(x.fair_value)}</td><td>{IDR(x.high)}</td>
   </tr>)}</tbody></table></div>
  </Panel>
 </>;
}
function Assumptions(){const rows=[['revenue_growth','Revenue growth (%)',-5,20,.25],['ebit_margin','Operating EBIT margin (%)',0,35,.25],['da_to_revenue','D&A / Revenue (%)',0,10,.1],['capex_to_revenue','CapEx / Revenue (%)',0,20,.1],['ncwc_to_revenue','Operating NCWC / Revenue (%)',0,50,.5],['tax_rate','Sustainable tax rate (%)',0,40,.5],['wacc','WACC (%)',3,24,.25],['terminal_growth','Terminal growth (%)',0,6,.1],['terminal_roic','Terminal ROIC (%)',3,50,.5]];return <><div className="flex flex-wrap justify-between items-center gap-3 mb-4"><div><h1 className="title">Valuation Drivers & Parameter Modeler</h1><p className="hint">Interactive scenario controls, with all assumptions explicitly identified</p></div><div className="flex gap-2"><button className="btn-light" onClick={()=>setValues(boot.defaults)}>Restore defaults</button><button className="btn" disabled={busy} onClick={()=>{calculate();setPage('valuation')}}>↻ Recalculate DCF</button></div></div><Panel title="KLBF Forecast and Capital Assumptions" subtitle="Projected, analyst-adjustable values; neither company guidance nor reported history"><div className="grid grid-cols-1 lg:grid-cols-2 gap-x-8"><div>{rows.slice(0,5).map(([key,label,min,max,step])=><div className="ctrl" key={key}><label>{label}</label><input type="range" min={min} max={max} step={step} value={values?.[key]??0} onChange={e=>changeVal(key,Number(e.target.value))}/><input className="input mono text-right" type="number" step={step} min={min} max={max} value={values?.[key]??0} onChange={e=>changeVal(key,Number(e.target.value))}/></div>)}</div><div>{rows.slice(5).map(([key,label,min,max,step])=><div className="ctrl" key={key}><label>{label}</label><input type="range" min={min} max={max} step={step} value={values?.[key]??0} onChange={e=>changeVal(key,Number(e.target.value))}/><input className="input mono text-right" type="number" step={step} min={min} max={max} value={values?.[key]??0} onChange={e=>changeVal(key,Number(e.target.value))}/></div>)}</div></div></Panel><div className="bg-slate-50 border border-slate-200 rounded px-4 py-3 text-xs hint mb-4"><b>Cost-of-capital audit:</b> current 12.20695% WACC is based on assumed 6.5% IDR risk-free, beta 0.9, ERP 6.69%, pretax borrowing cost 8%, target debt share 5%, and 22% tax (Ke 12.521%). This is a mathematical assumption set, not a verified FY2025 market-rate estimate. Source and model reconciliation details are in Reports &amp; Sources.</div><div className="warning">The inputs are assumptions for sensitivity analysis. Historical changes are managed in Historical Data Studio; forecast ratios remain user-controlled. Historical D&A and operating working capital are only partially reconciled. There are no automatic assumptions of zero for missing enterprise-to-equity items.</div></>}
function Sources(){return <><div className="flex flex-wrap items-center justify-between gap-3 mb-3"><h1 className="title">Source Register & Data Validation</h1><button className="btn" disabled={busy||!result?.ready||!isKLBF} onClick={exportExcel}>↓ Download Excel Financial Model (.xlsx)</button></div><p className="hint mb-4">Historical source dates, provenance, and unresolved issues</p>
{(result?.historical?.modified||result?.peer_inputs_modified)&&<Panel title="Applied analyst data updates" subtitle="These override the bundled audit only in the current browser session; they are not independently certified."><div className="text-sm"><b>KLBF historical:</b> {result.historical?.modified?'Manual update':'Bundled snapshot'} · <b>Updated:</b> {result.historical?.last_updated||'—'} · <b>Quote date:</b> {result.historical?.market_date||'—'}</div><p className="hint text-sm mt-2">{result.historical?.source_note||'See Historical Data Studio for dated peer quote overrides.'}</p><div className="label-note mt-2">{result.peer_inputs_modified?'One or more peer quote changes are applied; peer original financial denominators remain unchanged.':'No peer quote overrides applied.'}</div></Panel>}
<Panel title="Primary Financial Documentation" subtitle="Financial base FY2025. Report publication dates and limits are recorded separately."><div className="tablewrap"><table><thead><tr><th>Issuer</th><th>Period</th><th>Source</th><th>Publication date</th><th>Evidence</th></tr></thead><tbody>{(boot.source_register||[]).filter(x=>['FY2025','H1 2026'].includes(x.period)).map((x,i)=><tr key={i}><td><b>{x.issuer}</b></td><td>{x.period}</td><td><a className="source-link" href={x.url} target="_blank" rel="noreferrer">{x.document}</a></td><td>{x.publication_date||'Unverified'}</td><td className="text-left max-w-md whitespace-normal text-xs hint">{x.date_status}</td></tr>)}</tbody></table></div></Panel><Panel title="KLBF Input Audit Trail" subtitle="Exact amount in IDR billions; source is from the original Step 37 audit, not inferred by this interface"><div className="tablewrap"><table><thead><tr><th>Input</th><th>Source candidate</th><th>Official / reported</th><th>Status</th><th>Document reference</th></tr></thead><tbody>{(boot.input_audit||[]).filter(x=>x.ticker==='KLBF.JK'&&x.period==='2025-12-31').slice(0,24).map((x,i)=><tr key={i}><td><b>{x.field}</b></td><td className="mono">{fmt(x.raw_yahoo,2)}</td><td className="mono">{fmt(x.official,2)}</td><td className="text-left whitespace-normal"><span className="status">{x.status}</span></td><td className="text-left whitespace-normal text-xs hint max-w-md">{x.source}</td></tr>)}</tbody></table></div></Panel><Panel title="Methodology & Data Limitations" subtitle="Detailed model qualifications retained for audit; open a topic to review"><div className="space-y-3 text-sm text-slate-700">
<details className="rounded border border-slate-200 p-3"><summary className="font-semibold cursor-pointer">EV/EBITDA — financial-data reconciliation</summary><div className="mt-3 text-xs leading-6">The candidate EBITDA definitions are not yet reconciled across published sources. FY2025 saved EBITDA candidates include TSPC Rp2,084.92 billion and SOHO Rp820.75 billion; third-party market summaries use different denominators. Debt and lease scope, minority interest economic value, operating/restricted cash and other enterprise claims remain unresolved. EV/EBITDA multiples shown elsewhere are screening proxies, not audited transaction targets.</div></details>
<details className="rounded border border-slate-200 p-3"><summary className="font-semibold cursor-pointer">DVLA FY2025 — provider screening cross-check</summary><div className="mt-3 text-xs leading-6">The stored market-data snapshot implies EBITDA Rp261.49 billion and a simplified EV of approximately Rp1,506.65 billion, giving around 5.76×. A 25 March 2026 market summary uses EBITDA around Rp257.5 billion, giving around 5.85× with the same EV numerator, but separately reports 9.03× with a different debt/EV definition. Current liabilities and pension obligations should not automatically be classified as interest-bearing debt. The DVLA FY2025 PDF has not been independently read for this proxy. Its use as a comparable remains an analyst judgment.</div><div className="mt-2 text-xs">{(boot.ev_ebitda_candidates||{})['DVLA.JK']?.source_urls?.issuer_financial_reports && <a className="source-link" href={boot.ev_ebitda_candidates['DVLA.JK'].source_urls.issuer_financial_reports} target="_blank" rel="noreferrer">DVLA official reports ↗</a>}</div></details>
<details className="rounded border border-slate-200 p-3"><summary className="font-semibold cursor-pointer">Enterprise value, equity value and information cutoff</summary><div className="mt-3 text-xs leading-6">Enterprise-level DCF and EV/EBITDA outputs cannot be labelled per-share fair value without a complete enterprise-to-equity bridge. P/E and P/BV peer outputs are conditional estimates, not an audited blended target. FY2025 statements became available during 2026, after the 30 December 2025 quoted price used as a historical reference. Price-gap percentages therefore describe a retrospective mathematical comparison, not tradable upside or an investment recommendation. Historical data must remain distinct from forecast assumptions and analyst proxies.</div></details>
</div></Panel><Panel title="KLBF Analyst Case — Evidence and Judgments" subtitle="Optional scenario in DCF Step 2; valuation status does not become certified by filling in a form.">
  <div className="text-sm mb-3">The hypothetical bridge includes FY2025 book balances for financial investments and associates (notes 7, 11, 12), and employee benefit liability (note 36). The required operating cash reserve, economic NCI, and liability treatment remain analyst judgments.</div>
  <div className="tablewrap"><table><thead><tr><th>Evidence</th><th>Book value (IDR bn)</th><th>Audit note</th></tr></thead><tbody>{Object.entries(boot.analyst_case?.facts||{}).map(([key,f])=><tr key={key}><td>{key.replaceAll('_',' ')}</td><td className="mono">{fmt(f.value,3)}</td><td className="whitespace-normal text-xs hint">{f.source}</td></tr>)}</tbody></table></div>
  <p className="text-xs hint mt-3">Open items: audited D&A difference of 13.949bn in amortization classifications, full organic NCWC, economic NCI/pension valuation, operating versus restricted cash, market-sourced CAPM/WACC, contemporaneous reporting date. No analyst assumption is an issuer fact.</p>
 </Panel><Panel title="Project Scope & Methodology"><div className="space-y-3 text-sm text-slate-700"><div><b>Fixed coverage:</b> KLBF, TSPC, SIDO, DVLA, MERK, SOHO. No unrestricted ticker entry or fabricated data.</div><div><b>Valuation:</b> historical FCFF, five-year operating DCF, Bear/Base/Bull, WACC/terminal sensitivity, P/E and P/BV peer multiples, and a separately qualified EV/EBITDA screening proxy.</div><div><b>Not provided:</b> final DCF equity fair value, weighted blended target or BUY/SELL recommendation while economic bridge claims are incomplete.</div><div><b>Architecture:</b> Starlette/Python valuation API and React-based web interface.</div></div></Panel></>}
if(!boot)return <main className="p-8">{error||'Loading source-backed dashboard...'}</main>;
return <><header className="app-header" style={{background:'#0d0d0d',color:'#f6f6f6'}}><div className="flex justify-between items-center gap-4 flex-wrap px-5 py-3 border-b border-slate-700"><div className="flex items-center gap-3"><div className="font-extrabold text-base tracking-wide">VALUDESK</div></div><div className="flex items-center gap-3"><span className="text-xs text-slate-400 hidden sm:block mono">AUDIT ANCHOR: FY2025</span><span className="tag">6 HEALTHCARE TICKERS</span></div></div><div className="flex flex-wrap items-center gap-3 px-5 py-3 bg-[#171717]"><div className="text-xs text-slate-400 mono">SELECTED SECURITY</div><select className="head-select px-3 py-2 font-bold" value={ticker} onChange={e=>chooseTicker(e.target.value)}>{boot.companies.map(x=><option key={x.ticker} value={x.ticker}>{x.ticker} — {x.name}</option>)}</select><span className="hidden sm:block text-slate-300 text-xs truncate flex-1">{co?.name}</span><span className="text-xs text-amber-300 mono">{isKLBF?'ANALYST CASE · PRELIMINARY':'COMPARABLE ONLY'}</span></div></header><div className="layout"><aside className="sidebar"><div className="section">RESEARCH WORKFLOWS</div>{menu.map(([id,ico,text])=><button key={id} className={'navitem '+(page===id?'on':'')} onClick={()=>setPage(id)}><span className="text-lg mono">{ico}</span><span>{text}</span></button>)}<div className="section mt-5">COVERAGE UNIVERSE</div><div className="case">{boot.companies.map(c=><button key={c.ticker} onClick={()=>chooseTicker(c.ticker)} className={'flex justify-between items-center text-left w-full px-3 py-2 text-xs rounded '+(ticker===c.ticker?'active-peer':'text-slate-400 hover:text-white')}><b className="mono">{c.ticker}</b><span className="text-[9px]">{c.ticker==='KLBF.JK'?'CASE':'PEER'}</span></button>)}</div><div className="section mt-6">ACADEMIC USE</div><div className="px-3 text-xs text-slate-400">Case focus: KLBF FY2025<br/>Method: DCF + Comparables</div></aside><main className="main">{error&&<div className="warning mb-4">{error}</div>}{dataMessage&&<div className="alert-strip mb-4">{dataMessage}</div>}
{page==='data'?<HistoricalDataEditor draft={historicalDraft} setDraft={setHistoricalDraft} active={historicalActive} peerDraft={peerDraft} setPeerDraft={setPeerDraft} peerActive={peerActive} onApply={applyHistorical} onReset={resetHistorical} onPeerApply={applyPeer} onPeerRemove={removePeer} onSave={saveInputs} onLoad={loadInputs} companies={boot.companies} busy={busy}/>:!isKLBF&&page!=='sources'?<PeerOnlyView company={co} onHome={()=>chooseTicker('KLBF.JK')} onData={()=>setPage('data')} onRelative={()=>{setTicker('KLBF.JK');setPage('relative')}}/>:page==='approach'?<ApproachSelectionView decision={result?.approach_selection} onOpenBridge={()=>setPage('valuation')} onOpenPeers={()=>setPage('relative')}/>:page==='dashboard'?Dashboard():page==='financial'?Financial():page==='valuation'?DCF():page==='relative'?Relative():page==='reconciliation'?<><ReconciliationView result={result} bridge={bridge} onOpenDcf={()=>setPage('valuation')} onOpenPeers={()=>setPage('relative')}/><ApproachSelectionView embedded decision={result?.approach_selection} onOpenBridge={()=>setPage('valuation')} onOpenPeers={()=>setPage('relative')}/></>:page==='assumptions'?Assumptions():Sources()}<footer className="flex flex-wrap justify-between gap-3 border-t border-slate-200 mt-6 py-6 text-xs hint"><span>ValuDesk 2.8.1 · FY2025 research · independent valuation workflow</span><span>Educational research only · No synthetic historical figures</span></footer></main></div></>}
ReactDOM.createRoot(document.getElementById('root')).render(<App/>);
