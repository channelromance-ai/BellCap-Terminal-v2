"""
One scheduled run, start to finish:

  1. today's read                      model.build
  2. the weekly history, topped up     backtest.rebuild (only missing weeks)
  3. the track record                  edge.calibrate
  4. forecasts and thesis cards        forecast, thesis
  5. chart files for every page        charts.build
  6. everything saved privately        store

Steps 2-3 run every time so the track record on the site is always the one
the forecasts were actually gated by.
"""

from __future__ import annotations

import pandas as pd

from . import backtest, charts, edge, forecast, fx, model, setups, store, surprises, thesis
from .collect import Collected
from .config import MODEL_VERSION
from .ts import rnd, upto


SPARK_SESSIONS = 65      # ~3 months for the small line charts in tables
RANGE_SESSIONS = 252     # 1-year range bars


def market_strip(close, asof) -> dict:
    """What a table row needs without loading the instrument's chart file:
    last, 1-day change, a 3-month sparkline and the 1-year range."""
    c = upto(close, asof)
    if len(c) < 2:
        return {}
    d = 5 if c.iloc[-1] < 20 else 2
    year = c.iloc[-RANGE_SESSIONS:]
    return {"last": rnd(c.iloc[-1], d), "chg_1d_pct": rnd(100 * (c.iloc[-1] / c.iloc[-2] - 1), 2),
            "spark": [rnd(v, d) for v in c.iloc[-SPARK_SESSIONS:]],
            "lo_1y": rnd(year.min(), d), "hi_1y": rnd(year.max(), d),
            "avg_1y": rnd(year.mean(), d)}


def run(data: Collected, health: dict, progress=None) -> dict:
    snapshot, record = model.build(data, health)
    asof = model.default_asof(data)

    history = backtest.rebuild(data, store.load_json(store.history_path()), progress)
    calib = edge.calibrate(history, data)
    # The live log graded the same way: reads the model actually published,
    # never refit, so this is the out-of-sample record that matters most.
    live = edge.weekly(store.load_log(), MODEL_VERSION)
    calib["live"] = edge.calibrate(live, data) if live else None

    closes = edge.instrument_closes(data)
    forecasts = {}
    for p in snapshot["pairs"]:
        if p["pair"] in closes:
            forecasts[p["pair"]] = forecast.forecast("pair", p, closes[p["pair"]], asof, calib)
    for a in snapshot["assets"]:
        if a["name"] in closes:
            forecasts[a["name"]] = forecast.forecast("asset", a, closes[a["name"]], asof, calib)

    snapshot["ideas"] = thesis.build_cards(snapshot, closes, asof, calib)
    tickets, graded = setups.update(store.load_json(setups.PATH), snapshot["ideas"],
                                    data.bars, closes, asof)
    snapshot["setups"] = {"record": setups.summary(graded),
                          "live": [g for g in graded if g["status"] in ("pending", "open")],
                          "recent": [g for g in graded if g["status"] in ("closed", "expired")][-15:]}
    snapshot["forecasts"] = {
        name: {h: {"centre": c["centre"][-1], "lo68": c["lo68"][-1], "hi68": c["hi68"][-1],
                   "lo95": c["lo95"][-1], "hi95": c["hi95"][-1], "lean": c["lean"],
                   "daily_vol_pct": c["daily_vol_pct"]}
               for h, c in f.items()}
        for name, f in forecasts.items()}
    snapshot["track_record"] = calib
    snapshot["markets"] = {name: market_strip(c, asof) for name, c in closes.items()}
    record["forecasts"] = {name: {h: [v["centre"], v["lo68"], v["hi68"]] for h, v in f.items()}
                           for name, f in snapshot["forecasts"].items()}

    shown = history + ([backtest.slim(record)]
                       if not history or history[-1]["asof"] < record["asof"] else [])
    files = charts.build(snapshot, closes, data.macro, fx.strength(fx.usd_value(data.bars)),
                         asof, shown, forecasts)
    files.update({"edge.json": calib, "health.json": health,
                  store.history_path(): history,
                  setups.PATH: tickets,
                  surprises.PATH: surprises.merge(store.load_json(surprises.PATH), data.calendar,
                                                  pd.Timestamp.now(tz="UTC"))})
    store.save(snapshot, record)
    store.save_files(files)
    return {"asof": snapshot["asof"], "model": MODEL_VERSION, "history_reads": len(history),
            "files": len(files) + 3, "health": health["summary"],
            "proven_signals": [f"{h}:{k}" for h, s in calib.get("horizons", {}).items()
                               for k, v in s.items() if edge.proven(v)]}
