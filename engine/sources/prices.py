"""
Daily prices for everything the terminal covers, at the real market level.

Each instrument tries its sources in order and keeps the first that answers:

  FX majors, gold         Twelve Data, then Yahoo
  US500 NAS100 US30 JP225 FRED (the official index closes), then Yahoo
  WTI BRENT silver        Yahoo front-month futures (what CFD prices follow),
  GER40 UK100             and Yahoo's DAX / FTSE index levels
  any of the above        last resort: the Twelve Data ETF stand-in

Fixed 2026-10-27: the stand-ins used to be primary, so the site showed USO's
price (~166) as "WTI" while oil traded near 100. An ETF tracks its market's
percentage moves, not its level, so it is now only a fallback, and its
source label says "ETF" so the site can warn that the level isn't the
market's. Three of those ETFs hold foreign shares priced in dollars (DAX,
EWU, EWJ) and are converted back to their home currency first.

Futures roll monthly, which puts a small jump in oil's daily series at each
roll. It barely moves daily statistics; it's the price CFDs follow.

Each instrument comes from ONE source for its whole history, never spliced:
two sources sit at different levels, and a splice reads as a crash or a
rally. Prices are for the engine and never committed to the public repo.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from . import fred, twelvedata, yahoo

LABEL = {"td": "twelvedata", "yahoo": "yahoo", "fred": "fred"}


@dataclass(frozen=True)
class Instrument:
    name: str
    group: str
    td: str                         # Twelve Data symbol (the ETF, for stand-ins)
    yahoo: str
    order: tuple[str, ...]          # sources to try, in order
    fred: str | None = None
    proxy: str | None = None        # what the Twelve Data symbol is, if a stand-in
    fx: tuple[str, str] | None = None   # (pair, "div" | "mul") to undo USD pricing


FX_ORDER, INDEX_ORDER, YAHOO_ORDER = ("td", "yahoo"), ("fred", "yahoo", "td"), ("yahoo", "td")
INSTRUMENTS = [
    *[Instrument(p, "fx", f"{p[:3]}/{p[3:]}", f"{p}=X", FX_ORDER) for p in
      ("EURUSD", "GBPUSD", "USDJPY", "USDCHF", "USDCAD", "AUDUSD", "NZDUSD")],
    Instrument("XAUUSD", "metals", "XAU/USD", "GC=F", FX_ORDER),
    Instrument("XAGUSD", "metals", "SLV", "SI=F", YAHOO_ORDER, proxy="SLV ETF"),
    Instrument("WTI", "energy", "USO", "CL=F", YAHOO_ORDER, proxy="USO ETF"),
    Instrument("BRENT", "energy", "BNO", "BZ=F", YAHOO_ORDER, proxy="BNO ETF"),
    Instrument("NAS100", "indices", "QQQ", "^NDX", INDEX_ORDER, fred="NASDAQ100", proxy="QQQ ETF"),
    Instrument("US500", "indices", "SPY", "^GSPC", INDEX_ORDER, fred="SP500", proxy="SPY ETF"),
    Instrument("US30", "indices", "DIA", "^DJI", INDEX_ORDER, fred="DJIA", proxy="DIA ETF"),
    Instrument("GER40", "indices", "DAX", "^GDAXI", YAHOO_ORDER, proxy="DAX ETF in EUR",
               fx=("EURUSD", "div")),
    Instrument("UK100", "indices", "EWU", "^FTSE", YAHOO_ORDER, proxy="EWU ETF in GBP",
               fx=("GBPUSD", "div")),
    Instrument("JP225", "indices", "EWJ", "^N225", INDEX_ORDER, fred="NIKKEI225",
               proxy="EWJ (MSCI Japan) in JPY", fx=("USDJPY", "mul")),
]
BY_NAME = {i.name: i for i in INSTRUMENTS}


def to_home_currency(bars: pd.DataFrame, fx_close: pd.Series, how: str) -> pd.DataFrame:
    """Re-price a USD-listed ETF in its home currency, day by day. Days without
    an FX close are dropped rather than guessed."""
    rate = fx_close.reindex(bars.index)
    out = bars.div(rate, axis=0) if how == "div" else bars.mul(rate, axis=0)
    return out.dropna()


def _fred(names: list[str], today=None) -> tuple[dict, dict]:
    """FRED index closes as bars (close only: open/high/low = close)."""
    today = (today or pd.Timestamp.now(tz="UTC")).tz_localize(None).normalize()
    got, errs = {}, {}
    for n in names:
        try:
            s = fred.series(BY_NAME[n].fred, f"{today.year - 6}-01-01")
            s = s[(s.index < today) & (s.index.dayofweek < 5)]
            got[n] = pd.DataFrame({f: s for f in ("open", "high", "low", "close")})
        except Exception as e:  # noqa: BLE001 - next source takes over
            errs[n] = f"fred: {e}"
    return got, errs


def _td(names: list[str], bars: dict) -> tuple[dict, dict]:
    got, errs = twelvedata.fetch({BY_NAME[n].td: n for n in names})
    for n in list(got):
        inst = BY_NAME[n]
        if inst.fx:
            pair, how = inst.fx
            if pair in bars:
                got[n] = to_home_currency(got[n], bars[pair]["close"], how)
            else:
                errs[n] = f"no {pair} close to convert {inst.td} with"
                del got[n]
    return got, errs


def _label(src: str, inst: Instrument) -> str:
    if src == "td":
        return f"twelvedata ({inst.proxy}: ETF price, not the market level)" if inst.proxy else "twelvedata"
    if src == "fred":
        return f"fred ({inst.fred})"
    return f"yahoo ({inst.yahoo})"


def fetch() -> tuple[dict[str, pd.DataFrame], dict[str, str], dict[str, str]]:
    """Returns ({name: OHLC}, {name: source label}, {name: error})."""
    todo = {i.name: list(i.order) for i in INSTRUMENTS}
    bars, sources, errors = {}, {}, {}
    while any(todo.values()):
        # FX goes first so the ETF fallbacks have FX closes to convert with.
        for src in ("td", "fred", "yahoo"):
            batch = [n for n, order in todo.items() if order and order[0] == src]
            if not batch:
                continue
            if src == "td":
                got, errs = _td(batch, bars)
            elif src == "fred":
                got, errs = _fred(batch)
            else:
                got, errs = yahoo.fetch({BY_NAME[n].yahoo: n for n in batch})
            for n in batch:
                todo[n].pop(0)
                if n in got:
                    bars[n], sources[n], todo[n] = got[n], _label(src, BY_NAME[n]), []
                    errors.pop(n, None)
                else:
                    errors[n] = "; ".join(filter(None, [errors.get(n), errs.get(n, f"{src}: no data")]))
    return bars, sources, errors
