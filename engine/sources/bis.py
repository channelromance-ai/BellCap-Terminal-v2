"""
Central bank policy rates for all eight currencies, from the Bank for
International Settlements (WS_CBPOL, daily).

One request replaces v1's hand-maintained POLICY_RATES table. The BIS records
each bank's official steering rate (the Fed's is the midpoint of the target
range, the ECB's the deposit rate) and updates within a few days of a
decision, so a move shows up without anyone typing it in.
"""

from __future__ import annotations

import pandas as pd

from ..http import get
from ._util import read_csv, years_back

URL = "https://stats.bis.org/api/v2/data/dataflow/BIS/WS_CBPOL/1.0/D.{areas}"
AREAS = {"US": "USD", "XM": "EUR", "GB": "GBP", "JP": "JPY", "CH": "CHF",
         "CA": "CAD", "AU": "AUD", "NZ": "NZD"}


def parse(raw: bytes) -> pd.DataFrame:
    df = read_csv(raw, usecols=["REF_AREA", "TIME_PERIOD", "OBS_VALUE"])
    df["TIME_PERIOD"] = pd.to_datetime(df["TIME_PERIOD"])
    out = df.pivot_table(index="TIME_PERIOD", columns="REF_AREA",
                         values="OBS_VALUE")
    out = out.rename(columns={a: f"{c}.POLICY" for a, c in AREAS.items()})
    out.columns.name = None
    out.index.name = "date"
    return out.sort_index()


def fetch(years: int = 3) -> pd.DataFrame:
    return parse(get(URL.format(areas="+".join(AREAS)), timeout=60, params={
        "startPeriod": years_back(years).isoformat(), "format": "csv"}))
