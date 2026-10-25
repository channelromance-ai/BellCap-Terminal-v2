"""
Euro-area HICP inflation from Eurostat, the official publisher.

Uses prc_hicp_minr, the dataset introduced with the 2026 move to ECOICOP 2
and 2025=100. Both the older prc_hicp_manr and the ECB portal's ICP series
froze at December 2025 when that happened. They still download fine, so only
a date check catches it.

Annual rates: headline, core (ex energy, food, alcohol and tobacco), and
services, which is the part the ECB watches most closely.
"""

from __future__ import annotations

import json

import pandas as pd

from ..http import get

URL = ("https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/"
       "prc_hicp_minr")
SERIES = {"TOTAL": "EUR.CPI", "TOT_X_NRG_FOOD": "EUR.CORECPI",
          "SERV": "EUR.SERVICESCPI"}


def parse(raw: bytes, column: str) -> pd.Series:
    """JSON-stat with a single series: values are keyed by time position."""
    body = json.loads(raw)
    times = body["dimension"]["time"]["category"]["index"]   # {"2026-09": 2}
    by_pos = {pos: period for period, pos in times.items()}
    # Stamped on the month's last day: the figure describes the whole month.
    s = pd.Series({pd.Period(by_pos[int(k)], freq="M").end_time.normalize(): v
                   for k, v in body["value"].items()}, name=column, dtype=float)
    s.index.name = "date"
    return s.sort_index()


def fetch(months: int = 40) -> pd.DataFrame:
    return pd.concat([parse(get(URL, params={
                          "geo": "EA", "unit": "RCH_A", "coicop18": code,
                          "lastTimePeriod": months}), col)
                      for code, col in SERIES.items()], axis=1)
