"""
Cross-market correlations: what is moving with what right now, and how much
of each market's movement its partners account for.

"Right now" is the last 20 sessions (about a month), set against 60 sessions
and a year so a link that's forming or breaking stands out. From daily changes
of all 28 pairs, the 10 markets, VIX, the US 10y yield and the dollar index:

  corr        20-session correlation (also 60-session and 1-year)
  beta        the typical move here per unit move there, over the 20 sessions:
              per 1% for prices, per 10bp for the yield, per 1 point for VIX
  explained   corr squared: the share of day-to-day moves the two share
  implied     the partner's last-month move times beta, against what this
              market actually did

Two lists for the overview: the strongest links between DIFFERENT markets
right now (siblings like WTI/Brent or two USD pairs skipped), and the links
furthest from their 1-year norm (forming or breaking).

Noise: with 20 observations a correlation below about +/-0.45 can appear by
chance, so the lists only include links at least that strong. This is
co-movement, not cause. FX closes at midnight UTC and the futures/indices at
their own closes, which slightly weakens same-day links across the two.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import fx
from .sources import prices
from .ts import rnd

NOW, MID, LONG = 20, 60, 250
NOISE = 0.45            # |corr| a 20-session sample can reach by chance
TOP, LIST = 6, 15
UNITS = {"US10Y": "bp", "VIX": "pts"}
PER = {"US10Y": 10.0, "VIX": 1.0}          # beta per 10bp / per 1 VIX point; else per 1%


def family(name: str) -> set[str]:
    """Currencies for a pair, the group for a market; USDIDX is the dollar.
    Two names sharing a family are siblings, not a cross-market link."""
    if name in prices.BY_NAME and prices.BY_NAME[name].group != "fx":
        return {prices.BY_NAME[name].group}
    if name == "USDIDX":
        return {"USD"}
    return {name[:3], name[3:]} if len(name) == 6 else {name}


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
    now = r.iloc[-NOW:]
    c20, c60, c250 = now.corr(min_periods=15), r.iloc[-MID:].corr(min_periods=40), r.corr(min_periods=150)
    cov, var = now.cov(min_periods=15), now.var()
    month = now.sum(min_count=15)
    names = list(r.columns)
    top = {}
    for a in names:
        rows = []
        for b in names:
            c = c20.at[a, b]
            if a == b or pd.isna(c):
                continue
            slope = cov.at[a, b] / var[b] if var[b] else None
            rows.append({"name": b, "corr": rnd(c, 2), "corr_60": rnd(c60.at[a, b], 2),
                         "corr_1y": rnd(c250.at[a, b], 2),
                         "beta": rnd(None if slope is None else slope * PER.get(b, 1.0), 3),
                         "per": f"{PER.get(b, 1):g}{UNITS.get(b, '%')}", "explained": rnd(c * c, 2),
                         "other_1m": rnd(month[b], 2), "other_unit": UNITS.get(b, "%"),
                         "implied_1m": rnd(None if slope is None or pd.isna(month[b]) else slope * month[b], 2)})
        rows.sort(key=lambda x: -abs(x["corr"]))
        top[a] = {"actual_1m": rnd(month[a], 2), "unit": UNITS.get(a, "%"), "partners": rows[:TOP]}

    links, shifts = [], []
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            if family(a) & family(b):
                continue
            now_c, year_c = c20.at[a, b], c250.at[a, b]
            if pd.isna(now_c):
                continue
            row = {"a": a, "b": b, "corr": rnd(now_c, 2), "corr_1y": rnd(year_c, 2)}
            if abs(now_c) >= NOISE:
                links.append(row)
            if pd.notna(year_c) and max(abs(now_c), abs(year_c)) >= NOISE:
                shifts.append({**row, "shift": rnd(now_c - year_c, 2)})
    links.sort(key=lambda x: -abs(x["corr"]))
    shifts.sort(key=lambda x: -abs(x["shift"]))
    grid = lambda m: [[rnd(m.at[a, b], 2) for b in names] for a in names]
    return {"names": names, "window": NOW, "noise": NOISE, "asof": str(r.index[-1].date()),
            "corr": grid(c20), "corr_60": grid(c60), "corr_1y": grid(c250),
            "top": top, "links": links[:LIST], "shifts": shifts[:LIST]}


if __name__ == "__main__":
    days = pd.bdate_range("2025-01-01", periods=300)
    rng = np.random.default_rng(5)
    oil = pd.Series(np.exp(np.cumsum(rng.normal(0, .02, 300))) * 70, index=days)
    cad = pd.Series(np.exp(-0.25 * np.log(oil / 70) + np.cumsum(rng.normal(0, .002, 300))) * 1.38,
                    index=days)                                    # oil up -> USDCAD down
    other = pd.Series(np.exp(np.cumsum(rng.normal(0, .01, 300))) * 100, index=days)
    values = pd.DataFrame({"USD": 1.0, "CAD": 1 / cad}, index=days)
    out = build({"WTI": oil, "USDCAD": cad, "XX": other}, pd.DataFrame(), values, days[-1])
    wti = next(x for x in out["top"]["USDCAD"]["partners"] if x["name"] == "WTI")
    assert wti["corr"] < -0.8 and abs(wti["beta"] + 0.25) < 0.05, wti      # -0.25% per 1% of oil
    assert any({l["a"], l["b"]} == {"WTI", "USDCAD"} for l in out["links"])  # cross-market link listed
    assert not any({l["a"], l["b"]} == {"USDCAD", "USDIDX"} for l in out["links"])  # siblings skipped
    print("correlations: ok")
