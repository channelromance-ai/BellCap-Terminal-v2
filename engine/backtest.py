"""
History rebuild: the model re-run on the last session of every past week.

This is what makes the forecast and the track record honest. Each past read
uses only what was knowable then: prices up to that session, and macro data
re-dated to when it was published (catalog.point_in_time). Then edge.py puts
each read next to what the market actually did afterwards.

What it can't undo: it uses today's version of revised data (GDP and CPI get
revised; yields and prices don't). That flatters the inflation component a
little, and is the reason the live score log matters more as it grows.

Only finished weeks are rebuilt, so a read taken on a Wednesday is never
stored as "that week's close". Results are kept per model version: change
the model, and it is rebuilt from scratch rather than mixed with old reads.
"""

from __future__ import annotations

import pandas as pd

from . import config as C
from .catalog import point_in_time
from .collect import Collected
from .model import build

# A read needs this many sessions of FX history behind it (fair value uses 250).
WARMUP_SESSIONS = 260


def read_dates(data: Collected) -> list[pd.Timestamp]:
    """The last session of each finished week, after the warm-up."""
    common = None
    for name in ("EURUSD", "GBPUSD", "USDJPY", "USDCHF", "USDCAD", "AUDUSD", "NZDUSD"):
        idx = data.bars[name].index if name in data.bars else pd.DatetimeIndex([])
        common = idx if common is None else common.intersection(idx)
    if common is None or len(common) <= WARMUP_SESSIONS:
        return []
    sessions = pd.Series(common[WARMUP_SESSIONS:], index=common[WARMUP_SESSIONS:])
    weekly = sessions.groupby(sessions.index.to_period("W-FRI")).max()
    this_week = sessions.index[-1].to_period("W-FRI")
    return [d for p, d in weekly.items() if p < this_week]


def slim(record: dict) -> dict:
    """History records keep the signals and drop what can be rebuilt."""
    return {k: v for k, v in record.items()
            if k not in ("run_at", "closes", "price_sources")}


def rebuild(data: Collected, existing: list[dict] | None = None,
            progress=None) -> list[dict]:
    """Every finished week's read for the current model version. Existing
    reads for this version are kept; only missing weeks are computed."""
    kept = [r for r in existing or [] if r.get("model_version") == C.MODEL_VERSION]
    have = {r["asof"] for r in kept}
    todo = [d for d in read_dates(data) if d.date().isoformat() not in have]
    pit = point_in_time(data.macro) if todo else None
    for i, d in enumerate(todo):
        _, record = build(data, asof=d, pit=pit)
        kept.append(slim(record))
        if progress and (i % 25 == 0 or i == len(todo) - 1):
            progress(i + 1, len(todo), d)
    return sorted(kept, key=lambda r: r["asof"])
