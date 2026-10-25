"""
VIX daily history straight from Cboe, the index's owner. One file, full
history since 1990, no key.
"""

from __future__ import annotations

import pandas as pd

from ..http import get
from ._util import numeric_frame, read_csv

URL = "https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX_History.csv"


def parse(raw: bytes) -> pd.DataFrame:
    df = read_csv(raw)
    df.index = pd.to_datetime(df.pop("DATE"), format="%m/%d/%Y")
    return numeric_frame(df, {"CLOSE": "VIX"})


def fetch() -> pd.DataFrame:
    return parse(get(URL))
