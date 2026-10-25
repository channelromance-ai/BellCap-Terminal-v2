"""
All 28 pairs, currency strength and a broad dollar index, from the seven USD
majors.

Every currency is expressed as "US dollars per one unit" (USD itself is 1),
so any pair is just base/quote. A cross only exists on days when both of its
legs have a close; nothing is filled in.

Only closes are derived. A cross's true high and low can't be rebuilt from its
legs' highs and lows, so anything that needs a range uses close-to-close moves.
"""

from __future__ import annotations

from itertools import combinations

import numpy as np
import pandas as pd

from .config import CCYS, PAIR_PRIORITY


def usd_value(bars: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Columns = currencies, values = USD per unit. Dates where any leg is
    missing stay NaN for that leg only."""
    cols = {"USD": None}
    for ccy in CCYS:
        if ccy == "USD":
            continue
        if f"{ccy}USD" in bars:
            cols[ccy] = bars[f"{ccy}USD"]["close"]
        elif f"USD{ccy}" in bars:
            cols[ccy] = 1.0 / bars[f"USD{ccy}"]["close"]
    frame = pd.DataFrame({k: v for k, v in cols.items() if v is not None})
    frame["USD"] = 1.0
    return frame[[c for c in CCYS if c in frame]].sort_index()


def pair_names() -> list[tuple[str, str]]:
    rank = {c: i for i, c in enumerate(PAIR_PRIORITY)}
    return [(a, b) if rank[a] < rank[b] else (b, a)
            for a, b in combinations(CCYS, 2)]


def pair_closes(values: pd.DataFrame) -> dict[str, pd.Series]:
    out = {}
    for base, quote in pair_names():
        if base in values and quote in values:
            out[base + quote] = (values[base] / values[quote]).dropna()
    return out


def strength(values: pd.DataFrame) -> pd.DataFrame:
    """Each currency against the equal-weighted other seven, as a log index
    (0.01 = about 1% stronger). Only days where all eight are known."""
    logv = np.log(values.dropna())
    return logv.sub(logv.mean(axis=1), axis=0) * len(logv.columns) / (len(logv.columns) - 1)


def dollar_index(values: pd.DataFrame) -> pd.Series:
    """Equal-weighted USD against the other seven, rebased to 100. Unlike DXY
    it isn't 58% euro, and it includes AUD and NZD."""
    others = values.drop(columns="USD").dropna()
    idx = np.exp(-np.log(others).mean(axis=1))
    return (100 * idx / idx.iloc[0]).rename("USDIDX")
