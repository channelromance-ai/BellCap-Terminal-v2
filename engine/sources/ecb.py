"""
European Central Bank data portal (SDMX, keyless): the euro short-term rate,
where euro overnight money actually trades. The policy rate comes from bis.py.

Inflation is not taken from here: the portal's ICP series froze at December
2025 with the HICP rebase. See eurostat.py.
"""

from __future__ import annotations

import pandas as pd

from ..http import get
from ._util import read_csv, years_back

URL = "https://data-api.ecb.europa.eu/service/data/{flow}/{key}"
SERIES = {
    "EUR.ESTR": ("EST", "B.EU000A2X2A25.WT"),
}


def parse(raw: bytes, column: str) -> pd.Series:
    df = read_csv(raw, usecols=["TIME_PERIOD", "OBS_VALUE"])
    s = pd.to_numeric(df["OBS_VALUE"], errors="coerce")
    s.index = pd.to_datetime(df["TIME_PERIOD"])
    s.index.name = "date"
    return s.dropna().rename(column).sort_index()


def fetch(years: int = 6) -> pd.DataFrame:
    start = years_back(years).isoformat()
    return pd.concat([parse(get(URL.format(flow=flow, key=key), params={
                                "startPeriod": start, "format": "csvdata"}),
                            col)
                      for col, (flow, key) in SERIES.items()], axis=1)
