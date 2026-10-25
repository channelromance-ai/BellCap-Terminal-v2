"""
Chart files for the web app's detail pages, one per pair, asset and
currency. Each holds the last three years of what that page draws, so a
page loads one small file instead of the whole history.

Values are rounded to what a chart can show; series are written as parallel
date/value lists because that is the smallest JSON that charts read directly.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import config as C
from .ts import rnd, upto

YEARS = 3


def _series(s: pd.Series | None, asof, digits: int, scale: float = 1.0) -> dict:
    s = upto(s, asof)
    s = s[s.index >= asof - pd.DateOffset(years=YEARS)]
    return {"dates": [d.date().isoformat() for d in s.index],
            "values": [rnd(v * scale, digits) for v in s.values]}


def _rebased(s: pd.Series | None, asof) -> dict:
    """Strength as % change since the start of the chart window. The raw
    index level mostly reflects quoting conventions (how many yen to a
    dollar), so only its change means anything."""
    s = upto(s, asof)
    s = s[s.index >= asof - pd.DateOffset(years=YEARS)]
    return _series(s - s.iloc[0], asof, 2, 100) if len(s) else _series(None, asof, 2)


def _digits(close: pd.Series) -> int:
    return 5 if len(close) and close.iloc[-1] < 20 else 2


def fair_value_line(close: pd.Series, spread: pd.Series, asof) -> dict | None:
    """The fair-value regression's fitted line over the window it was fitted
    on: where rates alone would have put price, day by day."""
    df = pd.concat([np.log(upto(close, asof)).rename("p"), upto(spread, asof).rename("s")],
                   axis=1).dropna().iloc[-C.FAIR_VALUE_SESSIONS:]
    if len(df) < C.FAIR_VALUE_SESSIONS // 2 or df["s"].std() == 0:
        return None
    slope, intercept = np.polyfit(df["s"], df["p"], 1)
    fitted = np.exp(intercept + slope * df["s"])
    d = _digits(upto(close, asof))
    return {"dates": [x.date().isoformat() for x in df.index],
            "values": [rnd(v, d) for v in fitted]}


def front_spread(base: dict, quote: dict, macro: pd.DataFrame) -> pd.Series | None:
    if not base.get("front_end_id") or not quote.get("front_end_id"):
        return None
    a, b = macro.get(base["front_end_id"]), macro.get(quote["front_end_id"])
    if a is None or b is None:
        return None
    if base["quality"] == quote["quality"] == "daily":
        return (a - b).dropna()
    both = pd.concat([a, b], axis=1).ffill().dropna()   # monthly: align on prints
    return both.iloc[:, 0] - both.iloc[:, 1]


def score_history(history: list[dict], kind: str, name: str, field: str) -> dict:
    pts = [(r["asof"], r[kind].get(name, {}).get(field)) for r in history]
    pts = [(d, v) for d, v in pts if v is not None]
    return {"dates": [d for d, _ in pts], "values": [v for _, v in pts]}


def pair_chart(p: dict, ccy: dict, close: pd.Series, macro, asof, history, forecast) -> dict:
    b, q = ccy[p["base"]], ccy[p["quote"]]
    spread = front_spread(b, q, macro)
    out = {"name": p["pair"], "kind": "pair", "digits": _digits(upto(close, asof)),
           "close": _series(close, asof, _digits(upto(close, asof))),
           "spread_bp": _series(spread, asof, 0, 100) if spread is not None else None,
           "spread_quality": p["spread_quality"],
           "fair_value": (fair_value_line(close, spread, asof)
                          if p["spread_quality"] == "daily" and spread is not None else None),
           "score": score_history(history, "pairs", p["pair"], "macro_diff"),
           "forecast": forecast}
    return out


def asset_chart(a: dict, close: pd.Series, asof, history, forecast) -> dict:
    d = _digits(upto(close, asof))
    return {"name": a["name"], "kind": "asset", "digits": d, "close": _series(close, asof, d),
            "score": score_history(history, "assets", a["name"], "score"),
            "forecast": forecast}


def currency_chart(c: dict, macro: pd.DataFrame, strength: pd.DataFrame, asof, history) -> dict:
    ccy = c["ccy"]
    get = macro.get
    return {"name": ccy, "kind": "currency",
            "policy": _series(get(f"{ccy}.POLICY"), asof, 3),
            "front_end": _series(get(c["front_end_id"]), asof, 3) if c.get("front_end_id") else None,
            "front_end_id": c.get("front_end_id"),
            "long_end": _series(get(C.LONG_END[ccy]), asof, 3),
            "cpi": _series(get(C.INFLATION[ccy]), asof, 2),
            "cpi_target": C.INFLATION_TARGET[ccy],
            "cot": _series(get(C.COT[ccy]), asof, 1) if ccy in C.COT else None,
            "strength": _rebased(strength.get(ccy), asof) if ccy in strength else None,
            "score": score_history(history, "currencies", ccy, "score")}


def build(snapshot: dict, closes: dict, macro: pd.DataFrame, strength: pd.DataFrame,
          asof, history: list[dict], forecasts: dict) -> dict[str, dict]:
    """{relative path: chart} for every pair, asset and currency."""
    ccy = {c["ccy"]: c for c in snapshot["currencies"]}
    files = {}
    for p in snapshot["pairs"]:
        if p["pair"] in closes:
            files[f"charts/{p['pair']}.json"] = pair_chart(
                p, ccy, closes[p["pair"]], macro, asof, history, forecasts.get(p["pair"]))
    for a in snapshot["assets"]:
        if a["name"] in closes:
            files[f"charts/{a['name']}.json"] = asset_chart(
                a, closes[a["name"]], asof, history, forecasts.get(a["name"]))
    for c in snapshot["currencies"]:
        files[f"charts/ccy/{c['ccy']}.json"] = currency_chart(c, macro, strength, asof, history)
    return files
