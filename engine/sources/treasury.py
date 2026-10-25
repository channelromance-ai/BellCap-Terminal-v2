"""
US Treasury daily par yield curves, nominal and real (TIPS).

Published by Treasury itself around 18:00 ET each business day. One CSV per
calendar year, so history is a handful of small requests. Nominal minus real
at the same maturity is the market's inflation breakeven, which is why FRED's
breakeven series aren't needed.
"""

from __future__ import annotations

from datetime import date

import pandas as pd

from ..http import get
from ._util import numeric_frame, read_csv

URL = ("https://home.treasury.gov/resource-center/data-chart-center/"
       "interest-rates/daily-treasury-rates.csv/{year}/all")
NOMINAL = {"3 Mo": "USD.3M", "1 Yr": "USD.1Y", "2 Yr": "USD.2Y",
           "5 Yr": "USD.5Y", "10 Yr": "USD.10Y", "30 Yr": "USD.30Y"}
REAL = {"5 YR": "USD.REAL5Y", "10 YR": "USD.REAL10Y"}


def parse(raw: bytes, columns: dict[str, str]) -> pd.DataFrame:
    df = read_csv(raw)
    df.index = pd.to_datetime(df.pop("Date"), format="%m/%d/%Y")
    return numeric_frame(df, {k: v for k, v in columns.items() if k in df})


def _curve(kind: str, columns: dict[str, str], years: int) -> pd.DataFrame:
    this = date.today().year
    parts = []
    for y in range(this - years, this + 1):
        raw = get(URL.format(year=y), params={
            "type": kind, "field_tdr_date_value": y, "_format": "csv"})
        parts.append(parse(raw, columns))
    return pd.concat(parts).sort_index()


def fetch(years: int = 6) -> pd.DataFrame:
    nominal = _curve("daily_treasury_yield_curve", NOMINAL, years)
    real = _curve("daily_treasury_real_yield_curve", REAL, years)
    out = nominal.join(real, how="outer")
    out["USD.BE10Y"] = out["USD.10Y"] - out["USD.REAL10Y"]
    out["USD.BE5Y"] = out["USD.5Y"] - out["USD.REAL5Y"]
    return out
