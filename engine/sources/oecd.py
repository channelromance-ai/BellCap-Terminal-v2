"""
OECD data explorer (SDMX, keyless): headline CPI for the economies whose
national publishers aren't wired in yet, and monthly 3-month and 10-year rates
for the currencies without a usable daily yield source.

Both are monthly and lag by a few weeks, so they are a floor, not a feed. CPI
prefers the monthly series and falls back to quarterly (Australia and New
Zealand publish quarterly). Japan and Switzerland are left out on purpose:
the OECD's copies of their CPI stopped updating (2021 and 2025).
"""

from __future__ import annotations

import pandas as pd

from ..http import get
from ._util import read_csv

BASE = "https://sdmx.oecd.org/public/rest/data/"
CPI = "OECD.SDD.TPS,DSD_PRICES@DF_PRICES_ALL,/{areas}.M+Q.N.CPI.PA._T.N.GY"
RATES = "OECD.SDD.STES,DSD_STES@DF_FINMARK,/{areas}.M.IR3TIB+IRLT.PA....."
CPI_AREAS = {"USA": "USD", "GBR": "GBP", "CAN": "CAD", "AUS": "AUD", "NZL": "NZD"}
RATE_AREAS = {"GBR": "GBP", "CHE": "CHF", "AUS": "AUD", "NZL": "NZD"}
# The UK 3-month interbank series was LIBOR-based and stopped in Feb 2026.
DISCONTINUED = {"GBP.3M_M"}
RATE_NAMES = {"IR3TIB": "3M_M", "IRLT": "10Y_M"}


def _period(p: str) -> pd.Timestamp:
    """Stamp on the last day of the period: September's CPI isn't known on
    1 September, and stamping it there flatters any backtest."""
    freq = "Q" if "Q" in p else "M"
    return pd.Period(p.replace("-Q", "Q"), freq=freq).end_time.normalize()


def parse_cpi(raw: bytes) -> pd.DataFrame:
    df = read_csv(raw, usecols=["REF_AREA", "FREQ", "TIME_PERIOD", "OBS_VALUE"])
    cols = {}
    for area, ccy in CPI_AREAS.items():
        mine = df[df["REF_AREA"] == area]
        best = mine[mine["FREQ"] == "M"] if (mine["FREQ"] == "M").any() else mine
        cols[f"{ccy}.CPI"] = pd.Series(best["OBS_VALUE"].values,
                                       index=best["TIME_PERIOD"].map(_period))
    out = pd.DataFrame(cols).sort_index()
    out.index.name = "date"
    return out


def parse_rates(raw: bytes) -> pd.DataFrame:
    df = read_csv(raw, usecols=["REF_AREA", "MEASURE", "TIME_PERIOD", "OBS_VALUE"])
    df["col"] = df["REF_AREA"].map(RATE_AREAS) + "." + df["MEASURE"].map(RATE_NAMES)
    df["date"] = df["TIME_PERIOD"].map(_period)
    out = df.pivot_table(index="date", columns="col", values="OBS_VALUE")
    out.columns.name = None
    return out.drop(columns=DISCONTINUED, errors="ignore").sort_index()


def fetch(start: str = "2019-01") -> pd.DataFrame:
    params = {"startPeriod": start, "format": "csvfile"}
    cpi = parse_cpi(get(BASE + CPI.format(areas="+".join(CPI_AREAS)),
                        params=params, timeout=60))
    rates = parse_rates(get(BASE + RATES.format(areas="+".join(RATE_AREAS)),
                            params=params, timeout=60))
    return cpi.join(rates, how="outer")
