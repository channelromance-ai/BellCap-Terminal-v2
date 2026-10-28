"""
One full read: currencies, pairs, assets, risk regime and calendar, as of
one date.

`build` returns two things:
  snapshot   everything the web app shows (private: it contains vendor prices
             and the trade case)
  record     a compact line for the score log: the scores and biases plus the
             closes they were made at, so forward returns can be attached
             later without refetching anything
"""

from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

from . import assets, fx, macro, pairs
from .catalog import point_in_time
from .collect import Collected
from .config import MODEL_VERSION
from .ts import rnd, upto


def default_asof(data: Collected) -> pd.Timestamp:
    """The latest session with an EURUSD close: the newest date everything
    price-based can honestly be read at."""
    eur = data.bars.get("EURUSD")
    if eur is not None and len(eur):
        return eur.index[-1]
    return pd.Timestamp.now(tz="UTC").tz_localize(None).normalize() - pd.offsets.BDay(1)


def calendar_rows(cal: pd.DataFrame | None, now: pd.Timestamp) -> list[dict]:
    if cal is None or cal.empty:
        return []
    keep = cal[cal["impact"].isin(["High", "Medium"])].sort_values("time")
    return [{"time": t.isoformat(), "currency": c, "impact": i, "title": ti,
             "forecast": f or None, "previous": p or None, "past": bool(t < now)}
            for t, c, i, ti, f, p in keep.itertuples(index=False)]


def build(data: Collected, health: dict | None = None,
          asof: pd.Timestamp | None = None, pit: pd.DataFrame | None = None
          ) -> tuple[dict, dict]:
    """`pit` is the point-in-time view of data.macro; the history rebuild
    passes it in so it is computed once rather than once per read."""
    asof = asof or default_asof(data)
    view = pit if pit is not None else point_in_time(data.macro)
    values = fx.usd_value(data.bars)
    closes = fx.pair_closes(values)
    ccy_reads = macro.read_all(view, asof, fx.strength(values))
    pair_reads = pairs.read_all(ccy_reads, closes, view, asof)
    asset_reads = assets.read_all(view, data.bars, fx.dollar_index(values), asof)
    regime = assets.risk_regime(view, asof)

    last_close = {}
    for name, series in {**{k: v["close"] for k, v in data.bars.items()}, **closes}.items():
        s = upto(series, asof)
        if len(s):
            last_close[name] = rnd(s.iloc[-1], 6)

    now = pd.Timestamp.now(tz="UTC")
    warnings = [f"{r['name']}: {r.get('note') or r['status']}" for r in (health or {}).get("series", [])
                if r["status"] != "ok"]
    snapshot = {
        "model_version": MODEL_VERSION,
        "generated_at": now.isoformat(timespec="seconds"),
        "asof": asof.date().isoformat(),
        "regime": regime,
        "currencies": [r.to_dict() for r in ccy_reads],
        "pairs": [p.to_dict() for p in pair_reads],
        "assets": [a.to_dict() for a in asset_reads],
        "calendar": calendar_rows(data.calendar, now),
        "price_sources": data.price_sources,
        "data_warnings": warnings,
    }
    record = {
        "run_at": snapshot["generated_at"],
        "asof": snapshot["asof"],
        "model_version": MODEL_VERSION,
        "regime": regime.get("state"),
        "currencies": {r.ccy: {"score": r.score, "components": r.components}
                       for r in ccy_reads},
        "pairs": {p.pair: {"macro_diff": p.macro_diff, "bias": p.bias,
                           "rates_vs_price": p.rates_vs_price,
                           "residual_z": p.residual_z, "link_corr": p.link_corr}
                  for p in pair_reads},
        "assets": {a.name: {"score": a.score} for a in asset_reads},
        "closes": last_close,
        "price_sources": data.price_sources,
    }
    return snapshot, record
