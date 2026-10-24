# ValuDesk  — Equity Valuation Research 

**Scope:** Full five-year DCF and integrated valuation of PT Kalbe Farma Tbk (`KLBF.JK`), supported by five healthcare comparables (`TSPC`, `SIDO`, `DVLA`, `MERK`, `SOHO`). Peer securities are **not** marketed as independent DCF models.

## Start on Windows

1. Download **Code → Download ZIP** from GitHub, extract the archive, and open the folder containing `server.py` (do not run from inside a ZIP).
2. Install **Python 3.10 or newer**. Enable **Add Python to PATH** during installation.
3. Connect to the internet at least once (Python dependencies and browser React/Babel/Tailwind CDN assets are required).
4. Double-click `START_VALUDESK_WINDOWS.bat` in the extracted project folder.
5. Wait for `Application startup complete` and open <http://127.0.0.1:8000>.
6. Keep the terminal open while using the dashboard.

You do **not** need VS Code, Streamlit, or a GitHub account to run the extracted project. If port `8000` is in use, stop the prior server. A first-time run can take a few minutes.

**This ZIP is source code, not a packaged `.exe`.** Users require Windows, Python, and browser access to the CDNs. This project does not provide an offline browser dependency bundle.

## Main features

| Screen | What it does |
| --- | --- |
| Executive Dashboard | Conditional KLBF equity Bear/Base/Bull scenarios, operating EV, historical revenue and comparable metrics |
| Financial Analysis | Audited/provider historical financial inputs and fixed healthcare universe |
| **Historical Data Studio** | Update KLBF FY2022–2025 revenue, FY2025 key financials and market quote; record a source, market date, and last-updated date; adjust fixed-peer market quotes; validate and recalculate |
| DCF Valuation | Five-year FCFF, operating enterprise value, WACC/terminal growth sensitivity and explicit optional equity bridge |
| Relative Valuation | P/E, P/BV, EV/EBITDA screening, with selectable peers |
| Valuation Reconciliation | Compare per-share estimates without mixing share-price and enterprise-value units |
| **Valuation Decision** | Transparent method selection criteria, conditional central estimate/range and retrospective scenario classification with verification limitations |
| Model Assumptions | Adjust growth, profitability, reinvestment, WACC, terminal growth and ROIC, then recalculate |
| Reports & Sources | Original references, date caveats, evidence trails, known limitations |

### Updating financial and market inputs

1. Open **Historical Data Studio**.
2. Modify the relevant financial input or market quote. All financial amounts are **IDR billions** except share-price inputs and billions of shares.
3. For KLBF updates, enter a sufficient **Source / method** and **Last updated** date. For peer quote updates, select the ticker, enter price, price date, source and last-updated date.
4. Click **Apply & Recalculate**. The server checks units, non-finite/missing values, chronology and provenance; invalid submissions are rejected with an explanation.
5. For unchanged/default forecast ratios, KLBF historical updates rebase the corresponding forecast assumptions to updated reported values; analyst-adjusted sliders remain unchanged.
6. Change any other forecast parameters under **Model Assumptions** and recalculate as needed.
7. Review the preloaded analyst reference bridge (not user confirmed). To submit your own scenario, assess its assumptions, complete confirmations and calculate the conditional share-price range.
8. Use **Save input snapshot (.json)** to preserve entered values, dates, assumptions and peer updates. Use **Import saved snapshot** in the same form to reload and recalculate. **Inputs are session-scoped and are not uploaded to or stored by the server.**
9. Export a fresh formula-based Excel workbook from **DCF Valuation** or **Reports & Sources**. It uses the active financial inputs, scenario parameters, bridge and selected peers. Excel formula caches are populated for preview environments.
