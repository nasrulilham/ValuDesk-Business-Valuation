"""Pure valuation calculations for ValuDesk Step 34.

Amounts in BILLIONS of the issuer's *reporting currency*.
Shares in BILLIONS of shares; equity billions / shares billions => currency/share.
All assumptions explicitly supplied. No live prices, Yahoo calls or Streamlit here.
Valuation is a retrospective fiscal-year-end illustration until contemporaneous
financial inputs and other claims are independently reconciled.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
import math

import pandas as pd


class ModelInputError(ValueError):
    """Invalid or economically inconsistent valuation input."""


@dataclass(frozen=True)
class WACCInputs:
    risk_free: float
    beta: float
    equity_risk_premium: float
    cost_debt_pretax: float
    target_debt_weight: float
    tax_rate: float


@dataclass(frozen=True)
class ForecastAssumptions:
    revenue_growth: float
    ebit_margin: float
    da_to_revenue: float
    capex_to_revenue: float
    ncwc_to_revenue: float
    tax_rate: float
    wacc: float
    terminal_growth: float
    terminal_roic: float | None = None


@dataclass(frozen=True)
class EquityBridge:
    cash: float
    interest_bearing_debt: float
    non_operating_assets: float
    non_controlling_and_other_claims: float
    shares_billion: float


def _finite(name, value):
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ModelInputError(f"{name} must be a numeric value.") from exc
    if not math.isfinite(result):
        raise ModelInputError(f"{name} is missing or non-finite.")
    return result


def calculate_wacc(values: WACCInputs) -> dict:
    r = _finite("Risk-free rate", values.risk_free)
    beta = _finite("Beta", values.beta)
    erp = _finite("Equity risk premium", values.equity_risk_premium)
    kd = _finite("Cost of debt", values.cost_debt_pretax)
    d = _finite("Target debt weight", values.target_debt_weight)
    tax = _finite("Tax rate", values.tax_rate)
    if not (-0.05 <= r <= 0.30 and 0 <= beta <= 5 and 0 <= erp <= 0.30):
        raise ModelInputError("Risk-free rate, beta or ERP outside the screening ranges.")
    if not (0 <= kd <= 0.50 and 0 <= d < 1 and 0 <= tax <= 0.60):
        raise ModelInputError("Cost of debt, target debt weight or tax rate outside screening ranges.")
    ke = r + beta * erp
    wacc = ke * (1 - d) + kd * (1 - tax) * d
    if not 0 < wacc <= 0.60:
        raise ModelInputError("WACC must be positive and within 60% for this model.")
    return {"cost_equity": ke, "after_tax_cost_debt": kd * (1 - tax), "wacc": wacc}


def validate_model(revenue_base, ncwc_base, a: ForecastAssumptions, b: EquityBridge):
    revenue = _finite("Historical revenue", revenue_base)
    nwc = _finite("Historical net operating WC", ncwc_base)
    if revenue <= 0:
        raise ModelInputError("Historical revenue must be positive.")
    if not -revenue <= nwc <= 2 * revenue:
        raise ModelInputError("Historical NCWC is unusually large; check definitions and units.")
    checks = {
        "Revenue growth": (a.revenue_growth, -0.50, 1.00),
        "EBIT margin": (a.ebit_margin, -0.50, 0.80),
        "D&A / revenue": (a.da_to_revenue, 0, 0.50),
        "CapEx / revenue": (a.capex_to_revenue, 0, 0.80),
        "NCWC / revenue": (a.ncwc_to_revenue, -0.50, 1.00),
        "Tax rate": (a.tax_rate, 0, 0.60),
        "WACC": (a.wacc, 0.001, 0.60),
        "Terminal growth": (a.terminal_growth, -0.05, 0.10),
    }
    for name, (value, low, high) in checks.items():
        val = _finite(name, value)
        if not low <= val <= high:
            raise ModelInputError(f"{name} ({val:.2%}) outside allowed model range.")
    roic = _finite("Terminal ROIC", a.terminal_roic)
    if not 0 < roic <= 1 or not 0 <= a.terminal_growth < roic:
        raise ModelInputError("Stable state requires 0 <= g < terminal ROIC <= 100%; shrinking firms need a separate runoff model.")
    if a.terminal_growth >= a.wacc:
        raise ModelInputError("Terminal growth must be strictly lower than WACC.")
    for name, value in {
        "Cash": b.cash,
        "Interest-bearing debt": b.interest_bearing_debt,
        "Non-operating assets": b.non_operating_assets,
        "NCI and other claims": b.non_controlling_and_other_claims,
    }.items():
        if _finite(name, value) < 0:
            raise ModelInputError(f"{name} cannot be negative in the equity bridge.")
    if _finite("Shares outstanding (billions)", b.shares_billion) <= 0:
        raise ModelInputError("Shares outstanding must be positive and exclude treasury shares.")


def project_cash_flows(base_revenue: float, base_ncwc: float, fiscal_year: int,
                       a: ForecastAssumptions, years: int = 5) -> pd.DataFrame:
    """Annual end-of-year FCFF forecast; terminal value evaluated at end of year N.

    The first-year change in NCWC uses base period NCWC as prior-year stock.
    All ratios are forecast assumptions, not validated facts.
    """
    if not 1 <= years <= 15:
        raise ModelInputError("Forecast period must be 1 to 15 years.")
    previous_revenue = _finite("Base revenue", base_revenue)
    previous_ncwc = _finite("Base NCWC", base_ncwc)
    rows = []
    for t in range(1, years + 1):
        revenue = previous_revenue * (1 + a.revenue_growth)
        ebit = revenue * a.ebit_margin
        nopat = ebit * (1 - a.tax_rate)
        da = revenue * a.da_to_revenue
        capex = revenue * a.capex_to_revenue
        ncwc = revenue * a.ncwc_to_revenue
        delta_wc = ncwc - previous_ncwc
        fcff = nopat + da - capex - delta_wc
        rows.append({
            "FY": fiscal_year + t, "Year": t,
            "Revenue": revenue, "EBIT": ebit, "NOPAT": nopat,
            "D&A": da, "CapEx": capex, "NCWC": ncwc,
            "Delta NCWC": delta_wc, "FCFF": fcff,
        })
        previous_revenue, previous_ncwc = revenue, ncwc
    frame = pd.DataFrame(rows)
    frame.attrs["terminal_roic"] = a.terminal_roic
    return frame


def operating_value(forecast: pd.DataFrame, wacc: float, terminal_growth: float,
                    terminal_roic=None) -> dict:
    """End-of-year DCF; stable reinvestment = g/ROIC, rather than growing FY5 FCFF.

    Explicit annual CF horizon is measured from the historical anchor. This
    function does not roll stale statements forward to a current valuation date.
    """
    wacc = _finite("WACC", wacc)
    g = _finite("Terminal growth", terminal_growth)
    roic = _finite("Terminal ROIC", terminal_roic if terminal_roic is not None
                   else forecast.attrs.get("terminal_roic"))
    if not (0 < wacc <= .60 and 0 <= g < wacc and g < roic <= 1):
        raise ModelInputError("Require 0 <= g < WACC, g < ROIC <= 100%, and positive WACC.")
    if forecast.empty or not {"FCFF", "NOPAT"}.issubset(forecast.columns):
        raise ModelInputError("FCFF and NOPAT forecast required.")
    cfs = [_finite("Forecast FCFF", x) for x in forecast["FCFF"]]
    terminal_nopat = _finite("Terminal NOPAT", forecast.iloc[-1]["NOPAT"]) * (1 + g)
    if terminal_nopat <= 0:
        raise ModelInputError("Stable terminal NOPAT must be positive.")
    reinvestment = terminal_nopat * g / roic
    terminal_fcff = terminal_nopat - reinvestment
    pv_explicit = sum(cf / (1 + wacc) ** (i + 1) for i, cf in enumerate(cfs))
    tv = terminal_fcff / (wacc - g)
    pv_tv = tv / (1 + wacc) ** len(cfs)
    ev = pv_explicit + pv_tv
    if ev <= 0:
        raise ModelInputError("Operating enterprise value is non-positive.")
    return {"pv_explicit_fcff": pv_explicit, "terminal_nopat": terminal_nopat,
            "terminal_reinvestment": reinvestment, "terminal_roic": roic,
            "terminal_reinvestment_rate": g / roic, "terminal_fcff": terminal_fcff,
            "terminal_value_at_horizon": tv, "pv_terminal_value": pv_tv,
            "enterprise_value": ev, "terminal_ev_share": pv_tv / ev}


def enterprise_and_equity(forecast: pd.DataFrame, wacc: float,
                          terminal_growth: float, b: EquityBridge, terminal_roic=None) -> dict:
    result = operating_value(forecast, wacc, terminal_growth, terminal_roic)
    for name in ("cash", "interest_bearing_debt", "non_operating_assets",
                 "non_controlling_and_other_claims"):
        if _finite(name, getattr(b, name)) < 0:
            raise ModelInputError(f"{name} cannot be negative.")
    shares = _finite("Shares", b.shares_billion)
    if shares <= 0:
        raise ModelInputError("Shares must be positive and exclude treasury.")
    equity = (result["enterprise_value"] + b.cash + b.non_operating_assets
              - b.interest_bearing_debt - b.non_controlling_and_other_claims)
    if equity <= 0:
        raise ModelInputError("Reconciled equity value <= 0; review claims or forecast.")
    return {**result, "equity_value": equity, "fair_value_per_share": equity / shares}


def value_dcf(base_revenue: float, base_ncwc: float, fiscal_year: int,
              assumptions: ForecastAssumptions, bridge: EquityBridge,
              years: int = 5) -> dict:
    validate_model(base_revenue, base_ncwc, assumptions, bridge)
    forecast = project_cash_flows(base_revenue, base_ncwc, fiscal_year,
                                  assumptions, years)
    result = enterprise_and_equity(forecast, assumptions.wacc,
                                   assumptions.terminal_growth, bridge)
    return {"forecast": forecast, **result}


def scenario_assumptions(base: ForecastAssumptions) -> dict[str, ForecastAssumptions]:
    """Transparent illustrative deltas, all rates are fractions.

    Bear/Bull presets are not statistically estimated or company guidance.
    """
    return {
        "Bear": replace(base,
                        revenue_growth=base.revenue_growth - 0.03,
                        ebit_margin=base.ebit_margin - 0.015,
                        capex_to_revenue=base.capex_to_revenue + 0.005,
                        ncwc_to_revenue=base.ncwc_to_revenue + 0.02,
                        wacc=base.wacc + 0.01,
                        terminal_growth=base.terminal_growth - 0.005),
        "Base": base,
        "Bull": replace(base,
                        revenue_growth=base.revenue_growth + 0.03,
                        ebit_margin=base.ebit_margin + 0.015,
                        capex_to_revenue=max(0.0, base.capex_to_revenue - 0.003),
                        ncwc_to_revenue=base.ncwc_to_revenue - 0.02,
                        wacc=base.wacc - 0.01,
                        terminal_growth=base.terminal_growth + 0.005),
    }


def sensitivity_grid(forecast: pd.DataFrame, base_wacc: float,
                     base_terminal_growth: float, b: EquityBridge,
                     steps: tuple = (-0.02, -0.01, 0.0, 0.01, 0.02),
                     g_steps: tuple = (-0.01, -0.005, 0.0, 0.005, 0.01)) -> pd.DataFrame:
    """Values per share. Missing/invalid WACC-g pairs are NaN, never fabricated."""
    data = []
    for wshift in steps:
        w = base_wacc + wshift
        row = {"WACC": f"{w * 100:.2f}%"}
        for gshift in g_steps:
            g = base_terminal_growth + gshift
            key = f"{g * 100:.2f}%"
            try:
                if not (0 < w <= 0.60 and -0.05 <= g <= 0.10):
                    raise ModelInputError("Sensitivity pair outside screening ranges.")
                row[key] = enterprise_and_equity(forecast, w, g, b)["fair_value_per_share"]
            except ModelInputError:
                row[key] = float("nan")
        data.append(row)
    return pd.DataFrame(data).set_index("WACC")
