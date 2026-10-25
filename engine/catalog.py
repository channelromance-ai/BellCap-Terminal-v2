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

from .sources import (bis, boc, bundesbank, cboe, cftc, ecb, eurostat, mof,
                      nyfed, oecd, treasury, twelvedata)


@dataclass(frozen=True)
class Spec:
    id: str
    name: str
    group: str
    max_age: int


def _specs(group, max_age, **names):
    return [Spec(i.replace("_", "."), n, group, max_age) for i, n in names.items()]


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
    eurostat: _specs("inflation", 60, EUR_CPI="Euro area HICP y/y",
                     EUR_CORECPI="Euro area core HICP y/y",
                     EUR_SERVICESCPI="Euro area services HICP y/y"),
    mof: _specs("rates", 5, JPY_2Y="Japan 2-year", JPY_10Y="Japan 10-year"),
    boc: _specs("rates", 5, CAD_2Y="Canada 2-year", CAD_10Y="Canada 10-year"),
    bis: [Spec(f"{c}.POLICY", f"{c} policy rate", "policy", 12) for c in CCYS],
    oecd: _specs("inflation", 60, USD_CPI="US CPI y/y", GBP_CPI="UK CPI y/y",
                 CAD_CPI="Canada CPI y/y", AUD_CPI="Australia CPI y/y")
          + _specs("inflation", 120, NZD_CPI="New Zealand CPI y/y (quarterly)")
          + [Spec(f"{c}.{t}_M", f"{c} {label} (monthly avg)", "rates", 60)
             for c in ("GBP", "CHF", "AUD", "NZD")
             for t, label in (("3M", "3-month rate"), ("10Y", "10-year"))
             if f"{c}.{t}_M" not in oecd.DISCONTINUED],
    cftc: [Spec(col, f"{col[4:]} speculative net % OI", "positioning", 10)
           for col in cftc.MARKETS],
    twelvedata: [Spec(f"PX.{n}", f"{n} daily price", "prices", 5)
                 for n in twelvedata.SYMBOLS.values()],
}

GAPS = {
    "GBP.2Y / AUD.2Y / NZD.2Y daily": "Publishers (BoE, RBA, RBNZ) refuse "
        "non-browser requests; monthly OECD rates stand in. Awaiting a "
        "decision on how to source these.",
    "CHF.2Y daily": "SNB stopped publishing daily Confederation yields in "
        "July 2025.",
    "JPY.CPI / CHF.CPI": "OECD copies are stale; national publishers not "
        "wired in yet (phase 2).",
    "Silver, oil, index prices": "Not on Twelve Data's free plan; source "
        "pending a decision.",
}
