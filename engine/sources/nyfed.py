"""
New York Fed reference rates: EFFR (where fed funds actually trade inside the
target range) and SOFR. Official, keyless, and updated each business morning
for the day before.
"""

from __future__ import annotations

import json

import pandas as pd

from ..http import get
from ._util import years_back

URL = "https://markets.newyorkfed.org/api/rates/{kind}/{rate}/search.json"


def parse(raw: bytes, column: str) -> pd.Series:
    rows = json.loads(raw)["refRates"]
    s = pd.Series({pd.Timestamp(r["effectiveDate"]): r["percentRate"]
                   for r in rows}, name=column, dtype=float)
    s.index.name = "date"
    return s.sort_index()


def fetch(years: int = 3) -> pd.DataFrame:
    params = {"startDate": years_back(years).isoformat(),
              "endDate": pd.Timestamp.today().date().isoformat()}
    effr = parse(get(URL.format(kind="unsecured", rate="effr"), params=params),
                 "USD.EFFR")
    sofr = parse(get(URL.format(kind="secured", rate="sofr"), params=params),
                 "USD.SOFR")
    return pd.concat([effr, sofr], axis=1)
