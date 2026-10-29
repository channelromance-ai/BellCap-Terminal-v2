"""
Policy rates straight from the source, for banks with an honest daily feed.

The BIS (bis.py) covers all eight but loads each country a week or so late,
so after a decision the terminal showed the old rate for days (found
2026-10-29, after the Fed, BoC and RBNZ decisions). These official series
carry the decision by the next morning:

  USD   FRED target range, midpoint (DFEDTARU / DFEDTARL), as the BIS uses
  CAD   Bank of Canada Valet, target for the overnight rate (V39079)
  EUR   ECB data portal, deposit facility rate

collect.py merges them over the BIS columns: these where they have a value,
the BIS for every other date and for GBP, JPY, CHF, AUD and NZD, whose
banks don't serve daily data to automated tools. Each part fails on its own.
"""

from __future__ import annotations

import json

import pandas as pd

from ..http import get
from . import fred
from ._util import read_csv, years_back


def _usd(start) -> pd.Series:
    hi, lo = fred.series("DFEDTARU", start.isoformat()), fred.series("DFEDTARL", start.isoformat())
    return ((hi + lo) / 2).dropna()


def _cad(start) -> pd.Series:
    rows = json.loads(get("https://www.bankofcanada.ca/valet/observations/V39079/json",
                          params={"start_date": start.isoformat()}))["observations"]
    return pd.Series({pd.Timestamp(r["d"]): float(r["V39079"]["v"]) for r in rows if r.get("V39079")})


def _eur(start) -> pd.Series:
    df = read_csv(get("https://data-api.ecb.europa.eu/service/data/FM/D.U2.EUR.4F.KR.DFR.LEV",
                      params={"startPeriod": start.isoformat(), "format": "csvdata"}),
                  usecols=["TIME_PERIOD", "OBS_VALUE"])
    return pd.Series(df["OBS_VALUE"].astype(float).values, index=pd.to_datetime(df["TIME_PERIOD"]))


PARTS = {"USD.POLICY": _usd, "CAD.POLICY": _cad, "EUR.POLICY": _eur}


def fetch(years: int = 6) -> pd.DataFrame:
    start, cols, errors = years_back(years), {}, []
    for col, part in PARTS.items():
        try:
            cols[col] = part(start).sort_index()
        except Exception as e:  # noqa: BLE001 - the BIS still covers this one
            errors.append(f"{col}: {e}")
    if not cols:
        raise RuntimeError("; ".join(errors))
    out = pd.DataFrame(cols)
    out.index.name = "date"
    return out
