"""
German government yields (Schatz 2y, Bund 10y) from the Bundesbank's fitted
yield curve. Bunds are what the market means by "the euro rate", so they stand
in for EUR rather than an average of euro-area sovereigns.

The CSV is German-formatted: semicolons, decimal commas, and ten lines of
metadata before the data.
"""

from __future__ import annotations

import io

import pandas as pd

from ..http import get
from ._util import years_back

URL = "https://api.statistiken.bundesbank.de/rest/data/BBSIS/{key}"
SERIES = {"EUR.2Y": "D.I.ZST.ZI.EUR.S1311.B.A604.R02XX.R.A.A._Z._Z.A",
          "EUR.10Y": "D.I.ZST.ZI.EUR.S1311.B.A604.R10XX.R.A.A._Z._Z.A"}


def parse(raw: bytes, column: str) -> pd.Series:
    df = pd.read_csv(io.BytesIO(raw), sep=";", header=None, usecols=[0, 1],
                     encoding="utf-8-sig", dtype=str)
    df = df[df[0].str.match(r"^\d{4}-\d{2}-\d{2}$", na=False)]
    s = pd.to_numeric(df[1].str.replace(",", ".", regex=False),
                      errors="coerce")
    s.index = pd.to_datetime(df[0])
    s.index.name = "date"
    return s.dropna().rename(column)


def fetch(years: int = 3) -> pd.DataFrame:
    start = years_back(years).isoformat()
    return pd.concat([parse(get(URL.format(key=key),
                                params={"startPeriod": start, "format": "csv"}),
                            col)
                      for col, key in SERIES.items()], axis=1)
