"""
Small time-series helpers that every model module shares.

All of them take an `asof` date and ignore anything after it, and none of them
backfill. Macro series arrive on their own calendars (daily, monthly stamped
at month end, weekly COT stamped on publication day); the only safe way to
line them up is "the last value known on or before this date".
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def upto(s: pd.Series | None, asof: pd.Timestamp) -> pd.Series:
    if s is None:     # a missing series is empty, still indexed by date
        return pd.Series(dtype=float, index=pd.DatetimeIndex([]))
    s = s.dropna()
    return s[s.index <= asof].sort_index()


def last(s: pd.Series | None, asof: pd.Timestamp):
    """(date, value) of the latest observation on or before asof, or None."""
    s = upto(s, asof)
    return (s.index[-1], float(s.iloc[-1])) if len(s) else None


def value_at(s: pd.Series, when: pd.Timestamp) -> float | None:
    s = s[s.index <= when]
    return float(s.iloc[-1]) if len(s) else None


def change(s: pd.Series | None, days: int, asof: pd.Timestamp) -> float | None:
    """Latest value minus the value `days` before the latest observation.

    Measured from the latest observation's own date, so a monthly series
    gives a clean month-on-month or quarter-on-quarter change rather than a
    mix of stale and fresh prints."""
    s = upto(s, asof)
    if s.empty:
        return None
    base = value_at(s, s.index[-1] - pd.Timedelta(days=days))
    return None if base is None else float(s.iloc[-1]) - base


def pct_change(s: pd.Series | None, days: int, asof: pd.Timestamp) -> float | None:
    s = upto(s, asof)
    if s.empty:
        return None
    base = value_at(s, s.index[-1] - pd.Timedelta(days=days))
    return None if not base else 100 * (float(s.iloc[-1]) / base - 1)


def change_z(s: pd.Series | None, asof: pd.Timestamp, sessions: int,
             history: int, log: bool = False, min_moves: int = 60) -> float | None:
    """How unusual the latest `sessions`-long move is against the same move
    over the past `history` sessions. log=True for prices (moves as returns).
    Monthly series pass a smaller min_moves: three years is only 36 prints."""
    s = upto(s, asof)
    if len(s) < sessions + min_moves:
        return None
    x = np.log(s) if log else s
    moves = (x - x.shift(sessions)).dropna().iloc[-history:]
    sd = moves.std()
    return None if not sd or np.isnan(sd) else float((moves.iloc[-1] - moves.mean()) / sd)


def percentile(s: pd.Series | None, asof: pd.Timestamp, window: int) -> float | None:
    """Where the latest value sits in its trailing window, 0-100."""
    s = upto(s, asof).iloc[-window:]
    if len(s) < 20:
        return None
    return float(100 * (s < s.iloc[-1]).mean() + 50 * (s == s.iloc[-1]).mean())


def efficiency_ratio(close: pd.Series, sessions: int) -> float | None:
    """Kaufman: net move / total path. 1 = straight line, 0 = pure chop."""
    c = close.iloc[-(sessions + 1):]
    if len(c) < sessions + 1:
        return None
    path = c.diff().abs().sum()
    return float(abs(c.iloc[-1] - c.iloc[0]) / path) if path else None


def ordinal(n: float) -> str:
    """1 -> '1st', 82 -> '82nd', 93 -> '93rd', 11 -> '11th'."""
    n = int(round(n))
    suffix = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def clip(x: float | None, lo: float = -2.0, hi: float = 2.0) -> float | None:
    return None if x is None else float(min(hi, max(lo, x)))


def rnd(x, n: int = 2):
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x), n)
