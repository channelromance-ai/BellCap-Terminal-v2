"""
This week's economic calendar from Forex Factory's public JSON export:
time, currency, impact, forecast and previous for every scheduled release.

It only ever covers the current week and carries no actuals, so it answers
"what's coming", not "what surprised". The export is rate limited (a couple of
requests per five minutes); one call per run is well inside that.
"""

from __future__ import annotations

import json

import pandas as pd

from ..http import get

URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"


def parse(raw: bytes) -> pd.DataFrame:
    df = pd.DataFrame(json.loads(raw))
    df["time"] = pd.to_datetime(df.pop("date"), utc=True)
    df = df.rename(columns={"country": "currency"})
    return df[["time", "currency", "impact", "title", "forecast", "previous"]]


def fetch() -> pd.DataFrame:
    return parse(get(URL))
