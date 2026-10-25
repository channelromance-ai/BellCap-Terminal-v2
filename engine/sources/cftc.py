"""
CFTC Commitments of Traders, straight from the CFTC's public reporting API
(no openbb dependency as in v1).

Two reports, because "speculators" means different people in different
markets:

  financial futures (TFF)    currencies and stock indices: leveraged funds,
                             the hedge-fund bucket that trades macro
  disaggregated              gold, silver, crude: managed money

Net position is shown as a share of open interest, so a contract that doubled
in size doesn't read as a doubling of conviction.

Look-ahead: positions are as of Tuesday but published Friday 15:30 ET. Each
row is stamped with the Friday it became public, so nothing downstream can
"know" positioning three days before the market did.
"""

from __future__ import annotations

import json

import pandas as pd

from ..http import get
from ._util import years_back

BASE = "https://publicreporting.cftc.gov/resource/{dataset}.json"
TFF = ("gpe5-46if", "lev_money_positions_long", "lev_money_positions_short")
DISAGG = ("72hh-3qpy", "m_money_positions_long_all", "m_money_positions_short_all")
MARKETS = {
    "COT.EUR": ("099741", TFF), "COT.GBP": ("096742", TFF),
    "COT.JPY": ("097741", TFF), "COT.CHF": ("092741", TFF),
    "COT.CAD": ("090741", TFF), "COT.AUD": ("232741", TFF),
    "COT.NZD": ("112741", TFF), "COT.SPX": ("13874A", TFF),
    "COT.NDX": ("209742", TFF), "COT.GOLD": ("088691", DISAGG),
    "COT.SILVER": ("084691", DISAGG), "COT.WTI": ("067651", DISAGG),
}


def parse(raw: bytes, report: tuple[str, str, str]) -> pd.DataFrame:
    """Net long as % of open interest, one column per contract code."""
    _, long_col, short_col = report
    df = pd.DataFrame(json.loads(raw))
    if df.empty:
        return df
    net = (pd.to_numeric(df[long_col]) - pd.to_numeric(df[short_col]))
    df["net_pct"] = 100 * net / pd.to_numeric(df["open_interest_all"])
    tuesday = pd.to_datetime(df["report_date_as_yyyy_mm_dd"]).dt.normalize()
    df["date"] = tuesday + pd.Timedelta(days=3)          # public on Friday
    out = df.pivot_table(index="date", columns="cftc_contract_market_code",
                         values="net_pct")
    out.columns.name = None
    return out


def fetch(years: int = 3) -> pd.DataFrame:
    since = years_back(years).isoformat()
    frames = []
    for report in (TFF, DISAGG):
        codes = {code: col for col, (code, rep) in MARKETS.items() if rep is report}
        where = (f"report_date_as_yyyy_mm_dd >= '{since}' AND "
                 f"cftc_contract_market_code in ({','.join(repr(c) for c in codes)})")
        raw = get(BASE.format(dataset=report[0]), timeout=60, params={
            "$where": where, "$limit": 50000,
            "$select": f"report_date_as_yyyy_mm_dd,cftc_contract_market_code,"
                       f"open_interest_all,{report[1]},{report[2]}"})
        frames.append(parse(raw, report).rename(columns=codes))
    return pd.concat(frames, axis=1).sort_index()
