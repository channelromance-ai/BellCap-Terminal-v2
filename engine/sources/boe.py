"""
Bank of England interactive database: gilt yields (nominal zero-coupon 2y and
10y), Bank Rate and SONIA, in a single request.

The BoE publishes the curve with a one-business-day lag, so the latest row
often has Bank Rate but empty yields. That is normal, not a failure.
"""

from __future__ import annotations

import pandas as pd

from ..http import get
from ._util import numeric_frame, read_csv, years_back

URL = "https://www.bankofengland.co.uk/boeapps/database/_iadb-fromshowcolumns.asp"
SERIES = {"IUDSNZC": "GBP.2Y", "IUDMNZC": "GBP.10Y",
          "IUDBEDR": "GBP.POLICY", "IUDSOIA": "GBP.SONIA"}


def parse(raw: bytes) -> pd.DataFrame:
    df = read_csv(raw)
    df.index = pd.to_datetime(df.pop("DATE"), format="%d %b %Y")
    return numeric_frame(df, {k: v for k, v in SERIES.items() if k in df})


def fetch(years: int = 3) -> pd.DataFrame:
    return parse(get(URL, params={
        "csv.x": "yes", "Datefrom": years_back(years).strftime("%d/%b/%Y"),
        "Dateto": "now", "SeriesCodes": ",".join(SERIES), "CSVF": "TN",
        "UsingCodes": "Y", "VPD": "Y", "VFD": "N"}))
