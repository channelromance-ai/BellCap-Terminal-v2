"""
Cross-market correlations: which markets move together, and how much of each
one's movement the others account for.

For every pair and market (plus VIX, the US 10y yield and the dollar index)
against every other, from daily changes:

  corr        over the last 60 sessions, and over a year for comparison, so a
              relationship that's strengthening or breaking shows up
  beta        the typical move here per unit move there: per 1% for prices,
              per 10bp for the yield, per 1 point for VIX
  explained   corr squared: the share of this market's day-to-day moves that
              move together with the other one
  implied     the other market's last-month move times beta: where this market
              "should" be if the relationship held, set against where it is

This is co-movement, not cause. Oil and USDCAD moving together doesn't say
which one is pushing, and both can be answering a third thing.

Timing: FX daily bars close at midnight UTC and the ETF stand-ins at the 16:00
New York close, four hours apart. That slightly weakens same-day correlations
between FX and the indices, oil and silver; the ranking is still informative.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import fx
from .ts import rnd

SHORT, LONG, MONTH = 60, 250, 20
TOP = 6
UNITS = {"US10Y": "bp", "VIX": "pts"}
PER = {"US10Y": 10.0, "VIX": 1.0}          # beta is per 10bp / per 1 VIX point; else per 1%


def changes(closes: dict[str, pd.Series], macro: pd.DataFrame, values: pd.DataFrame,
            asof) -> pd.DataFrame:
    """Daily % log returns for prices, bp for the yield, points for VIX."""
    cols = {n: 100 * np.log(c).diff() for n, c in closes.items()}
    cols["USDIDX"] = 100 * np.log(fx.dollar_index(values)).diff()
    if "USD.10Y" in macro:
        cols["US10Y"] = 100 * macro["USD.10Y"].dropna().diff()
    if "VIX" in macro:
        cols["VIX"] = macro["VIX"].dropna().diff()
    df = pd.DataFrame(cols)
    df = df[(df.index <= asof) & (df.index.dayofweek < 5)]
    return df.dropna(how="all").iloc[-(LONG + 5):]


def build(closes: dict, macro: pd.DataFrame, values: pd.DataFrame, asof) -> dict:
    r = changes(closes, macro, values, asof)
    short, long = r.iloc[-SHORT:], r
    c60 = short.corr(min_periods=40)
    c250 = long.corr(min_periods=150)
    cov60, var60 = short.cov(min_periods=40), short.var()
    month = r.iloc[-MONTH:].sum(min_count=15)
    names = list(r.columns)
    top = {}
    for a in names:
        rows = []
        for b in names:
            c = c60.at[a, b]
            if a == b or pd.isna(c):
                continue
            beta = cov60.at[a, b] / var60[b] * PER.get(b, 1.0) if var60[b] else None
            implied = (cov60.at[a, b] / var60[b]) * month[b] if var60[b] and pd.notna(month[b]) else None
            rows.append({"name": b, "corr": rnd(c, 2), "corr_1y": rnd(c250.at[a, b], 2),
                         "beta": rnd(beta, 3), "per": f"{PER.get(b, 1):g}{UNITS.get(b, '%')}",
                         "explained": rnd(c * c, 2),
                         "other_1m": rnd(month[b], 2), "other_unit": UNITS.get(b, "%"),
                         "implied_1m": rnd(implied, 2)})
        rows.sort(key=lambda x: -abs(x["corr"]))
        top[a] = {"actual_1m": rnd(month[a], 2), "unit": UNITS.get(a, "%"), "partners": rows[:TOP]}
    grid = lambda m: [[rnd(m.at[a, b], 2) for b in names] for a in names]
    return {"names": names, "window": SHORT, "corr": grid(c60), "corr_1y": grid(c250), "top": top}


if __name__ == "__main__":
    days = pd.bdate_range("2025-01-01", periods=300)
    rng = np.random.default_rng(5)
    oil = pd.Series(np.exp(np.cumsum(rng.normal(0, .02, 300))) * 70, index=days)
    noise = rng.normal(0, .002, 300)
    cad = pd.Series(np.exp(-0.25 * np.log(oil / 70) + np.cumsum(noise)) * 1.38, index=days)   # oil up -> USDCAD down
    other = pd.Series(np.exp(np.cumsum(rng.normal(0, .01, 300))) * 100, index=days)
    values = pd.DataFrame({"USD": 1.0, "CAD": 1 / cad}, index=days)
    out = build({"WTI": oil, "USDCAD": cad, "XX": other}, pd.DataFrame(), values, days[-1])
    wti = next(x for x in out["top"]["USDCAD"]["partners"] if x["name"] == "WTI")
    assert wti["corr"] < -0.8, wti
    assert abs(wti["beta"] + 0.25) < 0.03, wti                      # -0.25% per 1% of oil
    assert abs(wti["implied_1m"] - (-0.25 * wti["other_1m"])) < 0.2
    print("correlations: ok")
