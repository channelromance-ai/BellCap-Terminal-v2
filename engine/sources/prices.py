"""
Daily prices for everything the terminal covers: Twelve Data first, Yahoo
for whatever Twelve Data didn't deliver.

On the free plan Twelve Data has FX and gold but not silver, oil or indices,
so those come from US-listed ETFs that track them. Three of those ETFs hold
foreign shares priced in dollars (DAX, EWU, EWJ), so a dollar move would read
as an index move; they are converted back to their home currency with the
same day's FX close. EWJ tracks MSCI Japan, not the Nikkei: close, not equal.

Each instrument comes from ONE source for its whole history. If the backup
is used, the whole series is Yahoo's, never stitched onto ETF history, because
an ETF and its index sit at different levels and a splice would read as a
crash or a rally. `sources` records which one every instrument came from.

These prices are for the engine and never committed to the public repo:
both vendors' terms are personal use.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from . import twelvedata, yahoo


@dataclass(frozen=True)
class Instrument:
    name: str
    group: str
    td: str                         # Twelve Data symbol
    yahoo: str                      # backup ticker
    proxy: str | None = None        # what the Twelve Data symbol stands in with
    fx: tuple[str, str] | None = None   # (pair, "div" | "mul") to undo USD pricing


INSTRUMENTS = [
    *[Instrument(p, "fx", f"{p[:3]}/{p[3:]}", f"{p}=X") for p in
      ("EURUSD", "GBPUSD", "USDJPY", "USDCHF", "USDCAD", "AUDUSD", "NZDUSD")],
    Instrument("XAUUSD", "metals", "XAU/USD", "GC=F"),
    Instrument("XAGUSD", "metals", "SLV", "SI=F", proxy="SLV ETF"),
    Instrument("WTI", "energy", "USO", "CL=F", proxy="USO ETF"),
    Instrument("BRENT", "energy", "BNO", "BZ=F", proxy="BNO ETF"),
    Instrument("NAS100", "indices", "QQQ", "^NDX", proxy="QQQ ETF"),
    Instrument("US500", "indices", "SPY", "^GSPC", proxy="SPY ETF"),
    Instrument("US30", "indices", "DIA", "^DJI", proxy="DIA ETF"),
    Instrument("GER40", "indices", "DAX", "^GDAXI", proxy="DAX ETF in EUR",
               fx=("EURUSD", "div")),
    Instrument("UK100", "indices", "EWU", "^FTSE", proxy="EWU ETF in GBP",
               fx=("GBPUSD", "div")),
    Instrument("JP225", "indices", "EWJ", "^N225", proxy="EWJ (MSCI Japan) in JPY",
               fx=("USDJPY", "mul")),
]
BY_NAME = {i.name: i for i in INSTRUMENTS}


def to_home_currency(bars: pd.DataFrame, fx_close: pd.Series, how: str) -> pd.DataFrame:
    """Re-price a USD-listed ETF in its home currency, day by day. Days without
    an FX close are dropped rather than guessed."""
    rate = fx_close.reindex(bars.index)
    out = bars.div(rate, axis=0) if how == "div" else bars.mul(rate, axis=0)
    return out.dropna()


def fetch() -> tuple[dict[str, pd.DataFrame], dict[str, str], dict[str, str]]:
    """Returns ({name: OHLC}, {name: source label}, {name: error})."""
    bars, errors = twelvedata.fetch({i.td: i.name for i in INSTRUMENTS})
    sources = {n: (f"twelvedata ({BY_NAME[n].proxy})" if BY_NAME[n].proxy
                   else "twelvedata") for n in bars}

    # Undo USD pricing before any backup runs: the backup is already local.
    for name in list(bars):
        inst = BY_NAME[name]
        if inst.fx:
            pair, how = inst.fx
            if pair in bars:
                bars[name] = to_home_currency(bars[name], bars[pair]["close"], how)
            else:
                del bars[name], sources[name]
                errors[name] = f"no {pair} close to convert {inst.td} with"

    missing = {BY_NAME[n].yahoo: n for n in errors}
    if missing:
        backup, backup_errors = yahoo.fetch(missing)
        for name, df in backup.items():
            bars[name], sources[name] = df, f"yahoo ({BY_NAME[name].yahoo})"
            errors.pop(name)
        for name, err in backup_errors.items():
            errors[name] = f"{errors[name]}; backup: {err}"
    return bars, sources, errors
