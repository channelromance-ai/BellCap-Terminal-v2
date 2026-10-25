"""
Every series the engine expects, where it comes from, and how old it may get.

`max_age` is in calendar days and is the line between "fine" and "stale".
Daily market data gets 5 (a weekend plus a holiday), the BIS a little longer
because it publishes a few days after a decision. Monthly and quarterly
figures are dated on the last day of the period they describe, so their
allowance is the publication lag plus a little: 60 days, and 120 quarterly.

GAPS lists what the model would like and has no acceptable free source for.
Writing them down keeps a missing input visible in every health report
instead of quietly scoring as zero.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .sources import (bis, boc, bundesbank, cboe, cftc, ecb, eurostat, mof,
                      nyfed, oecd, prices, treasury)


@dataclass(frozen=True)
class Spec:
    id: str
    name: str
    group: str
    max_age: int
    # Days between the date a value is stamped with and the day it was
    # public. September CPI is stamped 30 Sep and released mid-October; the
    # model must not see it on 1 October. See point_in_time().
    lag: int = 0


def _specs(group, max_age, lag=0, **names):
    return [Spec(i.replace("_", "."), n, group, max_age, lag) for i, n in names.items()]


CCYS = ["USD", "EUR", "GBP", "JPY", "CHF", "CAD", "AUD", "NZD"]

SOURCES = {
    treasury: _specs("rates", 5, USD_3M="US 3-month bill", USD_1Y="US 1-year",
                     USD_2Y="US 2-year", USD_5Y="US 5-year", USD_10Y="US 10-year",
                     USD_30Y="US 30-year")
              + _specs("real", 5, USD_REAL5Y="US 5y real (TIPS)",
                       USD_REAL10Y="US 10y real (TIPS)",
                       USD_BE5Y="US 5y breakeven inflation",
                       USD_BE10Y="US 10y breakeven inflation"),
    nyfed: _specs("money", 5, USD_EFFR="Effective fed funds", USD_SOFR="SOFR"),
    cboe: _specs("risk", 5, VIX="VIX"),
    bundesbank: _specs("rates", 5, EUR_2Y="German 2-year (Schatz)",
                       EUR_10Y="German 10-year (Bund)"),
    ecb: _specs("money", 5, EUR_ESTR="Euro short-term rate"),
    eurostat: _specs("inflation", 60, lag=18, EUR_CPI="Euro area HICP y/y",
                     EUR_CORECPI="Euro area core HICP y/y",
                     EUR_SERVICESCPI="Euro area services HICP y/y"),
    mof: _specs("rates", 5, JPY_2Y="Japan 2-year", JPY_10Y="Japan 10-year"),
    boc: _specs("rates", 5, CAD_2Y="Canada 2-year", CAD_10Y="Canada 10-year"),
    bis: [Spec(f"{c}.POLICY", f"{c} policy rate", "policy", 12) for c in CCYS],
    # Lags follow the NATIONAL release, which is when the market learned the
    # number; the OECD reposts it later, but in a live run a value that isn't
    # posted yet simply isn't there, so only the backtest needs this rule.
    oecd: _specs("inflation", 60, lag=15, USD_CPI="US CPI y/y")
          + _specs("inflation", 60, lag=21, GBP_CPI="UK CPI y/y", CAD_CPI="Canada CPI y/y")
          + _specs("inflation", 60, lag=30, AUD_CPI="Australia CPI y/y")
          + _specs("inflation", 120, lag=21, NZD_CPI="New Zealand CPI y/y (quarterly)")
          # A month's average of daily market rates is known on its last day.
          + [Spec(f"{c}.{t}_M", f"{c} {label} (monthly avg)", "rates", 60, lag=1)
             for c in ("GBP", "CHF", "AUD", "NZD")
             for t, label in (("3M", "3-month rate"), ("10Y", "10-year"))
             if f"{c}.{t}_M" not in oecd.DISCONTINUED],
    cftc: [Spec(col, f"{col[4:]} speculative net % OI", "positioning", 10)
           for col in cftc.MARKETS],
}

LAGS = {spec.id: spec.lag for specs in SOURCES.values() for spec in specs if spec.lag}


def point_in_time(macro):
    """Re-date lagged series to the day they became public. The model reads
    this view, live and in the history rebuild alike, so a backtest can never
    know a number before the market did, and live reads are judged by the
    same rule they were tested under."""
    out = macro.copy()
    for col, lag in LAGS.items():
        if col in out:
            s = out.pop(col).dropna()
            s.index = s.index + pd.Timedelta(days=lag)
            out = out.join(s.rename(col), how="outer")
    return out.sort_index()


# Prices are fetched by sources/prices.py (Twelve Data, Yahoo backup), not
# per module, so they are listed separately.
PRICES = [Spec(i.name, f"{i.name} daily price", i.group, 5)
          for i in prices.INSTRUMENTS]

GAPS = {
    "GBP / AUD / NZD daily yields": "BoE, RBA and RBNZ refuse non-browser "
        "requests. Decided 2026-10-25: use the monthly OECD 10y (and 3m "
        "where it exists) instead of disguising requests.",
    "CHF daily yields": "SNB stopped publishing daily Confederation yields "
        "in July 2025; monthly OECD rates stand in.",
    "JPY / CHF inflation": "OECD copies are stale; national publishers not "
        "wired in yet.",
}
