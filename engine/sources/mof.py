"""
Japanese government bond yields from Japan's Ministry of Finance.

Two files: the full history up to the end of last month, and the current
month. Missing tenors are written as "-". The history file's footer has a
stray Shift-JIS byte, so undecodable bytes are replaced rather than fatal.
"""

from __future__ import annotations

import pandas as pd

from ..http import get
from ._util import numeric_frame, read_csv

BASE = "https://www.mof.go.jp/english/policy/jgbs/reference/interest_rate/"
URLS = [BASE + "historical/jgbcme_all.csv", BASE + "jgbcme.csv"]
TENORS = {"2Y": "JPY.2Y", "10Y": "JPY.10Y"}


def parse(raw: bytes) -> pd.DataFrame:
    df = read_csv(raw, skiprows=1, na_values="-", encoding_errors="replace")
    df = df[df["Date"].str.match(r"^\d{4}/\d{1,2}/\d{1,2}$", na=False)]
    df.index = pd.to_datetime(df.pop("Date"), format="%Y/%m/%d")
    return numeric_frame(df, TENORS)


def fetch(years: int = 3) -> pd.DataFrame:
    out = pd.concat([parse(get(u, timeout=60)) for u in URLS])
    out = out[~out.index.duplicated(keep="last")].sort_index()
    return out[out.index >= pd.Timestamp.today() - pd.DateOffset(years=years)]
