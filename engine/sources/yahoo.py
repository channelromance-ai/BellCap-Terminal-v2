"""
Backup prices from Yahoo Finance via yfinance, used only for instruments
Twelve Data failed to deliver.

Yahoo throttles shared cloud addresses (it is why v1 had to fetch from the
PC), so this is a backup and never the plan. yfinance is an optional install:
without it, a Twelve Data failure just leaves that instrument missing.
"""

from __future__ import annotations

import pandas as pd

try:
    import yfinance as yf
except ImportError:
    yf = None


def fetch(tickers: dict[str, str], period: str = "6y",
          today: pd.Timestamp | None = None
          ) -> tuple[dict[str, pd.DataFrame], dict[str, str]]:
    """{ticker: name} -> ({name: OHLC frame}, {name: error})."""
    if yf is None:
        return {}, {name: "yfinance is not installed" for name in tickers.values()}
    today = (today or pd.Timestamp.now(tz="UTC")).tz_localize(None).normalize()
    try:
        raw = yf.download(list(tickers), period=period, interval="1d",
                          auto_adjust=False, group_by="ticker",
                          progress=False, threads=False)
    except Exception as e:  # noqa: BLE001
        return {}, {name: f"yfinance: {e}" for name in tickers.values()}
    bars, errors = {}, {}
    for ticker, name in tickers.items():
        try:
            df = raw[ticker][["Open", "High", "Low", "Close"]].dropna()
        except KeyError:
            df = pd.DataFrame()
        df.columns = ["open", "high", "low", "close"]
        df.index = pd.to_datetime(df.index).tz_localize(None).normalize()
        df.index.name = "date"
        df = df[(df.index < today) & (df.index.dayofweek < 5)]
        if df.empty:
            errors[name] = f"Yahoo returned no bars for {ticker}"
        else:
            bars[name] = df
    return bars, errors
