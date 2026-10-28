"""
Fetch everything once per run.

The doctor and the model both work from what this returns, so a run makes one
request per source no matter how many things read the data. A source that
fails is recorded, not raised: missing inputs are the model's problem to
handle visibly, not a reason to publish nothing.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

import pandas as pd

from .catalog import SOURCES
from .sources import forexfactory, prices, twelvedata


@dataclass
class Collected:
    macro: pd.DataFrame                       # every non-price series, by date
    bars: dict[str, pd.DataFrame]             # instrument -> daily OHLC
    price_sources: dict[str, str]             # instrument -> where it came from
    price_errors: dict[str, str]
    sources: list[dict] = field(default_factory=list)
    calendar: pd.DataFrame | None = None
    calendar_error: str | None = None
    hourly: dict[str, pd.DataFrame] = field(default_factory=dict)   # FX + gold, UTC, for the Asia profile


def _timed(fn):
    t0 = time.time()
    try:
        return fn(), None, round(time.time() - t0, 1)
    except Exception as e:  # noqa: BLE001 - every failure is reported, none stops the run
        return None, f"{type(e).__name__}: {e}", round(time.time() - t0, 1)


def collect() -> Collected:
    frames, status = [], []
    for module in SOURCES:
        frame, error, secs = _timed(module.fetch)
        status.append({"source": module.__name__.rsplit(".", 1)[-1],
                       "ok": error is None, "error": error, "seconds": secs})
        if frame is not None:
            frames.append(frame)
    macro = pd.concat(frames, axis=1).sort_index() if frames else pd.DataFrame()

    result, error, secs = _timed(prices.fetch)
    bars, price_sources, price_errors = result or ({}, {}, {})
    if error:
        price_errors = {i.name: error for i in prices.INSTRUMENTS}
    status.append({"source": "prices", "ok": not price_errors,
                   "error": "; ".join(f"{k}: {v}" for k, v in price_errors.items()) or None,
                   "seconds": secs})

    fx_and_gold = {i.td: i.name for i in prices.INSTRUMENTS if i.order == prices.FX_ORDER}
    result, error, secs = _timed(lambda: twelvedata.fetch_hourly(fx_and_gold))
    hourly, hourly_errors = result or ({}, {})
    status.append({"source": "hourly", "ok": not (error or hourly_errors),
                   "error": error or "; ".join(f"{k}: {v}" for k, v in hourly_errors.items()) or None,
                   "seconds": secs})

    calendar, cal_error, _ = _timed(forexfactory.fetch)
    return Collected(macro, bars, price_sources, price_errors, status,
                     calendar, cal_error, hourly)
