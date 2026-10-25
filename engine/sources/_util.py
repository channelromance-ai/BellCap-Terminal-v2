from __future__ import annotations

import io
from datetime import date

import pandas as pd


def years_back(n: int) -> date:
    today = date.today()
    return today.replace(year=today.year - n)


def numeric_frame(df: pd.DataFrame, rename: dict[str, str]) -> pd.DataFrame:
    """Keep the renamed columns, coerce to numbers, drop empty rows, sort."""
    out = df[list(rename)].rename(columns=rename)
    out = out.apply(pd.to_numeric, errors="coerce").dropna(how="all")
    out.index.name = "date"
    return out[~out.index.duplicated(keep="last")].sort_index()


def read_csv(raw: bytes, **kw) -> pd.DataFrame:
    return pd.read_csv(io.BytesIO(raw), encoding="utf-8-sig", **kw)
