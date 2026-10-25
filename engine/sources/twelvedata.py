"""
Daily prices from Twelve Data's official API, on the free plan.

The free plan covers FX and spot gold, which is what this pulls: the seven
USD majors (the 21 crosses are rebuilt from these downstream) and XAU/USD.
Silver, oil and the indices need a paid plan, so they don't come from here.

Limits: 8 credits a minute and 800 a day, one credit per symbol. A full pull
is 8 credits, spaced to stay under the per-minute cap. The key comes from the
TWELVEDATA_API_KEY environment variable (a GitHub secret in the cloud, .env
locally) and is never logged or written to anything published.

Twelve Data's daily FX bar runs midnight to midnight UTC, not the 17:00 New
York close that FX trades on. For swing horizons the difference is noise; for
anything intraday it is not, and the hourly jobs don't use these bars.
"""

from __future__ import annotations

import json
import os
import time

import pandas as pd

from ..http import FetchError, get

URL = "https://api.twelvedata.com/time_series"
SYMBOLS = {"EUR/USD": "EURUSD", "GBP/USD": "GBPUSD", "USD/JPY": "USDJPY",
           "USD/CHF": "USDCHF", "USD/CAD": "USDCAD", "AUD/USD": "AUDUSD",
           "NZD/USD": "NZDUSD", "XAU/USD": "XAUUSD"}
SPACING_SECONDS = 8.0


def parse(raw: bytes, name: str, today: pd.Timestamp | None = None) -> pd.DataFrame:
    """Closed weekday bars only. Today's bar is still forming, and the
    Sunday-evening reopen shows up as a stub bar; publishing either as a
    close is how v1 printed a partial Friday on 2026-09-18."""
    today = (today or pd.Timestamp.now(tz="UTC")).tz_localize(None).normalize()
    body = json.loads(raw)
    if body.get("status") != "ok":
        raise FetchError(f"Twelve Data {name}: {body.get('message', 'no data')}")
    df = pd.DataFrame(body["values"])
    df.index = pd.to_datetime(df.pop("datetime"))
    df.index.name = "date"
    df = df[["open", "high", "low", "close"]].astype(float).sort_index()
    df = df[~df.index.duplicated(keep="last")]
    df = df[(df.index < today) & (df.index.dayofweek < 5)]
    df.columns = pd.MultiIndex.from_product([[name], df.columns])
    return df


def fetch(days: int = 800) -> pd.DataFrame:
    """OHLC for every symbol, columns (instrument, field)."""
    key = os.environ.get("TWELVEDATA_API_KEY")
    if not key:
        raise FetchError("TWELVEDATA_API_KEY is not set")
    frames = []
    for i, (symbol, name) in enumerate(SYMBOLS.items()):
        if i:
            time.sleep(SPACING_SECONDS)
        frames.append(parse(get(URL, retries=1, params={
            "symbol": symbol, "interval": "1day", "outputsize": days,
            "apikey": key}), name))
    return pd.concat(frames, axis=1)
