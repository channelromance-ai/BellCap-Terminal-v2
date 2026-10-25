"""
FRED (St. Louis Fed) through its API, with a free key in FRED_API_KEY.

Used for long history: the Fed's H.10 daily exchange rates go back to 1971
(1999 for the euro), which is what lets the research rebuild cover two
decades instead of the 5-6 years Twelve Data's free plan reaches.

H.10 rates are noon New York buying rates, not the 17:00 close, and they skip
US holidays. Fine for weekly and monthly reads; not for intraday work. The
key's parameter name (api_key) is redacted from any error message by http.py.
"""

from __future__ import annotations

import json
import os

import pandas as pd

from ..http import FetchError, get

URL = "https://api.stlouisfed.org/fred/series/observations"

# FRED series -> pair, already quoted the market way round.
FX = {"DEXUSEU": "EURUSD", "DEXUSUK": "GBPUSD", "DEXJPUS": "USDJPY",
      "DEXSZUS": "USDCHF", "DEXCAUS": "USDCAD", "DEXUSAL": "AUDUSD",
      "DEXUSNZ": "NZDUSD"}


def parse(raw: bytes, column: str) -> pd.Series:
    """Missing days come through as "." and are dropped."""
    rows = json.loads(raw).get("observations", [])
    s = pd.Series({pd.Timestamp(r["date"]): r["value"] for r in rows}, name=column)
    s = pd.to_numeric(s, errors="coerce").dropna()
    s.index.name = "date"
    return s.sort_index()


def series(series_id: str, start: str = "1999-01-01") -> pd.Series:
    key = os.environ.get("FRED_API_KEY")
    if not key:
        raise FetchError("FRED_API_KEY is not set")
    return parse(get(URL, timeout=60, params={
        "series_id": series_id, "api_key": key, "file_type": "json",
        "observation_start": start}), series_id)


def fx_bars(start: str = "1999-01-01") -> dict[str, pd.DataFrame]:
    """Daily closes for the seven majors as bar frames (open=high=low=close:
    H.10 publishes one rate a day)."""
    out = {}
    for sid, pair in FX.items():
        close = series(sid, start)
        out[pair] = pd.DataFrame({f: close for f in ("open", "high", "low", "close")})
    return out
