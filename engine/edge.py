"""
Did the reads predict anything? Every past read next to what happened next.

For each weekly read and each instrument, the forward return over one week
(5 sessions) and one month (20), divided by that instrument's own volatility
so a 1% move in USDJPY and a 1% move in silver aren't treated as the same
thing. Then three questions per signal:

  slope    on a typical read date, did a higher score go with a better
           forward return across instruments? Measured date by date and
           averaged (Fama-MacBeth), because 28 pairs on the same Friday are
           not 28 independent bets - they share eight currencies.
  t        is that average slope distinguishable from zero? Only
           non-overlapping dates count: monthly returns from weekly reads
           overlap, so for one month only every fourth read is used.
  hit      when there was a bias, how often did price move its way?

A signal counts as proven only if |t| >= 2 over the whole history AND it
points the same way with |t| >= 1.5 in each half on its own. One good stretch
isn't an edge: the fair-value signal reached t = -2.1 overall on 2026-10-25
entirely from its second half (first half -0.3), and this rule rejects it.
forecast.py only tilts a cone for a proven signal; otherwise the honest
forecast is "no lean", and the page says so.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import fx
from .collect import Collected
from .config import ASSET_BIAS_MIN

HORIZONS = {"1w": 5, "1m": 20}
STEP = {"1w": 1, "1m": 4}          # weekly reads to skip so returns don't overlap
VOL_SESSIONS = 60
MIN_ROWS_PER_DATE = 5
T_REQUIRED = 2.0
T_REQUIRED_EACH_HALF = 1.5


def instrument_closes(data: Collected) -> dict[str, pd.Series]:
    closes = {k: v["close"] for k, v in data.bars.items()}
    closes.update(fx.pair_closes(fx.usd_value(data.bars)))
    return closes


def _forward(close: pd.Series, when: pd.Timestamp, h: int):
    """(normalised forward return, vol) from the last close on or before `when`."""
    i = close.index.searchsorted(when, side="right") - 1
    if i < VOL_SESSIONS or i + h >= len(close):
        return None, None
    rets = np.log(close.iloc[i - VOL_SESSIONS:i + 1]).diff().dropna()
    vol = rets.std()
    if not vol:
        return None, None
    fwd = float(np.log(close.iloc[i + h] / close.iloc[i]))
    return fwd / (vol * np.sqrt(h)), float(vol)


def panel(history: list[dict], data: Collected) -> pd.DataFrame:
    closes = instrument_closes(data)
    rows = []
    for rec in history:
        when = pd.Timestamp(rec["asof"])
        items = [("pair", n, p.get("macro_diff"), p.get("bias"), p.get("residual_z"))
                 for n, p in rec["pairs"].items()]
        items += [("asset", n, a.get("score"), _asset_bias(a.get("score")), None)
                  for n, a in rec["assets"].items()]
        for kind, name, score, bias, resid in items:
            if name not in closes or score is None:
                continue
            row = {"asof": when, "kind": kind, "name": name, "score": score / 100,
                   "bias": {"long": 1, "short": -1}.get(bias, 0), "residual_z": resid}
            for label, h in HORIZONS.items():
                row[label], _ = _forward(closes[name], when, h)
            rows.append(row)
    return pd.DataFrame(rows)


def _asset_bias(score):
    if score is None or abs(score) < ASSET_BIAS_MIN:
        return None
    return "long" if score > 0 else "short"


def fama_macbeth(df: pd.DataFrame, x: str, y: str, step: int) -> dict:
    """Average date-by-date slope over the whole history, plus the t of each
    half separately so a signal that only worked in one stretch shows it."""
    dates = sorted(df["asof"].unique())[::step]
    whole = _fm(df, dates, x, y)
    mid = len(dates) // 2
    whole["t_halves"] = [_fm(df, dates[:mid], x, y)["t"], _fm(df, dates[mid:], x, y)["t"]]
    return whole


def _fm(df: pd.DataFrame, dates: list, x: str, y: str) -> dict:
    slopes = []
    for d in dates:
        g = df[(df["asof"] == d)][[x, y]].dropna()
        if len(g) >= MIN_ROWS_PER_DATE and g[x].var() > 0:
            slopes.append(np.cov(g[x], g[y])[0, 1] / g[x].var())
    n = len(slopes)
    if n < 8:
        return {"slope": None, "t": None, "dates": n}
    mean, sd = float(np.mean(slopes)), float(np.std(slopes, ddof=1))
    return {"slope": round(mean, 4), "t": round(mean / (sd / np.sqrt(n)), 2) if sd else None,
            "dates": n}


def hit_rate(df: pd.DataFrame, y: str, step: int) -> dict:
    keep = set(sorted(df["asof"].unique())[::step])
    g = df[df["asof"].isin(keep) & (df["bias"] != 0)][["bias", y]].dropna()
    if g.empty:
        return {"hit": None, "signals": 0, "avg_return_sd": None}
    signed = g["bias"] * g[y]
    return {"hit": round(float((signed > 0).mean()), 3), "signals": int(len(g)),
            "avg_return_sd": round(float(signed.mean()), 3)}


def calibrate(history: list[dict], data: Collected) -> dict:
    df = panel(history, data)
    out = {"reads": len(history),
           "from": history[0]["asof"] if history else None,
           "to": history[-1]["asof"] if history else None,
           "t_required": T_REQUIRED, "horizons": {}}
    if df.empty:
        return out
    for label in HORIZONS:
        step = STEP[label]
        pairs, assets = df[df["kind"] == "pair"], df[df["kind"] == "asset"]
        out["horizons"][label] = {
            "pair_score": {**fama_macbeth(pairs, "score", label, step),
                           **hit_rate(pairs, label, step)},
            "pair_fair_value": fama_macbeth(pairs.dropna(subset=["residual_z"]),
                                            "residual_z", label, step),
            "asset_score": {**fama_macbeth(assets, "score", label, step),
                            **hit_rate(assets, label, step)},
        }
    return out


def proven(stat: dict | None) -> bool:
    if not stat or stat.get("t") is None or abs(stat["t"]) < T_REQUIRED:
        return False
    halves = stat.get("t_halves") or [None, None]
    return all(h is not None and np.sign(h) == np.sign(stat["t"])
               and abs(h) >= T_REQUIRED_EACH_HALF for h in halves)
