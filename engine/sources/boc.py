"""
Bank of Canada Valet API: benchmark 2y and 10y yields. The policy rate comes
from bis.py with the other seven.
"""

from __future__ import annotations

import json

import pandas as pd

from ..http import get
from ._util import numeric_frame, years_back

SERIES = {"BD.CDN.2YR.DQ.YLD": "CAD.2Y", "BD.CDN.10YR.DQ.YLD": "CAD.10Y"}
URL = "https://www.bankofcanada.ca/valet/observations/" + ",".join(SERIES) + "/json"


def parse(raw: bytes) -> pd.DataFrame:
    rows = json.loads(raw)["observations"]
    df = pd.DataFrame([{k: (v["v"] if isinstance(v, dict) else v)
                        for k, v in r.items()} for r in rows])
    df.index = pd.to_datetime(df.pop("d"))
    return numeric_frame(df, {k: v for k, v in SERIES.items() if k in df})


def fetch(years: int = 6) -> pd.DataFrame:
    return parse(get(URL, params={"start_date": years_back(years).isoformat()}))
