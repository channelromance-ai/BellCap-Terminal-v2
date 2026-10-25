"""
Long-history data for research runs: about two decades instead of six years.

The daily update stays on its lighter 6-year fetch; this exists so a signal
can be tested across several full cycles (2008, 2015, 2020, 2022) before it
is allowed anywhere near the forecast. Same sources and the same model, only
further back:

  FX majors     FRED H.10 from 1999 (Twelve Data's free plan reaches ~2021)
  other prices  Twelve Data, 5000 bars: ETFs from late 2006, gold from 2008,
                the DAX ETF from 2014. USD-listed ETFs are converted back to
                their home currency with the FRED closes, as prices.py does.
  macro         every catalogue source asked for `years` of history

Costs about 10 Twelve Data credits and one FRED request per pair.
"""

from __future__ import annotations

import inspect
from datetime import date

import pandas as pd

from .catalog import SOURCES
from .collect import Collected
from .sources import cboe, eurostat, fred, oecd, prices, twelvedata


def _fetch_macro(module, years: int) -> pd.DataFrame:
    if module is oecd:
        return module.fetch(start=f"{date.today().year - years}-01")
    if module is eurostat:
        return module.fetch(months=12 * years + 12)
    if module is cboe or "years" not in inspect.signature(module.fetch).parameters:
        return module.fetch()
    return module.fetch(years=years)


def collect_long(years: int = 24, progress=print) -> Collected:
    frames, status = [], []
    for module in SOURCES:
        name = module.__name__.rsplit(".", 1)[-1]
        try:
            frames.append(_fetch_macro(module, years))
            status.append({"source": name, "ok": True, "error": None})
        except Exception as e:  # noqa: BLE001 - report, keep going
            status.append({"source": name, "ok": False, "error": f"{type(e).__name__}: {e}"})
        progress(f"  {name}: {'ok' if status[-1]['ok'] else status[-1]['error']}")
    macro = pd.concat(frames, axis=1).sort_index()

    bars = fred.fx_bars(f"{date.today().year - years}-01-01")
    progress(f"  fred fx: {len(bars)} pairs from {min(b.index[0] for b in bars.values()).date()}")
    others = {i.td: i.name for i in prices.INSTRUMENTS if i.group != "fx"}
    td, errors = twelvedata.fetch(others, days=5000)
    for name, df in td.items():
        inst = prices.BY_NAME[name]
        if inst.fx:
            pair, how = inst.fx
            df = prices.to_home_currency(df, bars[pair]["close"], how)
        bars[name] = df
    progress(f"  twelvedata: {len(td)} instruments, errors: {errors or 'none'}")
    sources = {n: "fred (H.10)" for n in fred.FX.values()}
    sources.update({n: "twelvedata (5000 bars)" for n in td})
    return Collected(macro, bars, sources, errors, status)
