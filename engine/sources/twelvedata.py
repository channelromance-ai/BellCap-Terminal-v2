"""
Daily bars from Twelve Data's official API, on the free plan.

The free plan covers FX, spot gold and US-listed ETFs. Silver, oil and the
indices need a paid plan, so prices.py uses ETFs as stand-ins for those.

Limits: 8 credits a minute and 800 a day, one credit per symbol. Requests are
spaced to stay under the per-minute cap, and each symbol fails on its own so
one bad ticker can't take the rest down. The key comes from the
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
    return df[(df.index < today) & (df.index.dayofweek < 5)]


def fetch(symbols: dict[str, str], days: int = 800
          ) -> tuple[dict[str, pd.DataFrame], dict[str, str]]:
    """{symbol: name} -> ({name: OHLC frame}, {name: error})."""
    key = os.environ.get("TWELVEDATA_API_KEY")
    if not key:
        return {}, {name: "TWELVEDATA_API_KEY is not set" for name in symbols.values()}
    bars, errors = {}, {}
    for i, (symbol, name) in enumerate(symbols.items()):
        if i:
            time.sleep(SPACING_SECONDS)
        try:
            bars[name] = parse(get(URL, retries=1, params={
                "symbol": symbol, "interval": "1day", "outputsize": days,
                "apikey": key}), name)
        except Exception as e:  # noqa: BLE001 - one symbol never sinks the rest
            errors[name] = str(e)
    return bars, errors
