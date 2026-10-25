"""
The forecast shown on every price chart.

  cone        where price is likely to stay over the next week or month: 68%
              and 95% bands from the last 60 sessions' volatility, widening
              with the square root of time. This part holds up regardless of
              any model: volatility is far more predictable than direction.
  lean        the centre line's tilt. Zero unless a signal has passed
              testing (edge.proven). Even then it is shrunk by how strong the
              evidence is (1 - 4/t^2), so a t of 2.1 gets almost no tilt and a
              t of 4 gets three quarters of the measured effect.
  rates level for pairs with daily yields on both legs: where the fair-value
              regression puts price today. A reference line, not a target.

Decided 2026-10-25: no signal has a proven lean yet, so cones are flat and
the model's bias is shown separately next to its track record.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .edge import HORIZONS, proven
from .ts import rnd, upto

VOL_SESSIONS = 60


def daily_vol(close: pd.Series, asof) -> float | None:
    rets = np.log(upto(close, asof)).diff().dropna().iloc[-VOL_SESSIONS:]
    return float(rets.std()) if len(rets) >= 20 else None


def lean(kind: str, read: dict, calib: dict | None, horizon: str) -> tuple[float, list[str]]:
    """Expected move over the horizon in volatility units, and why."""
    stats = ((calib or {}).get("horizons") or {}).get(horizon, {})
    parts, total = [], 0.0
    signals = [(f"{kind}_score", (read.get("macro_diff") if kind == "pair" else read.get("score")),
                100.0, "macro score")]
    if kind == "pair":
        signals.append(("pair_fair_value", read.get("residual_z"), 1.0, "rates fair value"))
    for key, x, scale, label in signals:
        st = stats.get(key)
        if x is None or not proven(st):
            continue
        shrink = max(0.0, 1 - 4 / st["t"] ** 2)
        total += st["slope"] * (x / scale) * shrink
        parts.append(f"{label} (t={st['t']}, shrunk to {shrink:.0%})")
    return total, parts


def cone(close: pd.Series, asof, sessions: int, drift_vol: float = 0.0) -> dict | None:
    c = upto(close, asof)
    vol = daily_vol(close, asof)
    if vol is None or c.empty:
        return None
    last = float(c.iloc[-1])
    dates = pd.bdate_range(c.index[-1] + pd.Timedelta(days=1), periods=sessions)
    k = np.arange(1, sessions + 1)
    centre = last * np.exp(drift_vol * vol * np.sqrt(sessions) * k / sessions)
    width = vol * np.sqrt(k)
    digits = 5 if last < 20 else 2
    band = lambda z: [rnd(v, digits) for v in centre * np.exp(z * width)]
    return {"sessions": sessions, "dates": [d.date().isoformat() for d in dates],
            "centre": [rnd(v, digits) for v in centre],
            "lo68": band(-1), "hi68": band(1), "lo95": band(-2), "hi95": band(2),
            "daily_vol_pct": rnd(100 * vol, 3)}


def forecast(kind: str, read: dict, close: pd.Series, asof, calib: dict | None) -> dict:
    out = {}
    for label, sessions in HORIZONS.items():
        drift, why = lean(kind, read, calib, label)
        c = cone(close, asof, sessions, drift)
        if c:
            c["lean"] = why or None
            out[label] = c
    return out
