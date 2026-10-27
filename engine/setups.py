"""
The swing template tickets on the thesis cards, logged and graded like real
orders.

Logged: every ticket the site shows, once per market and direction (a short
on CHFJPY stays one ticket while it's live, not a new one each day). Stored
append-only in the private repo as log/setups.json; nothing in it is edited.

Graded from the prices that followed, recomputed from scratch every run so
there is no stored state to drift:
  entry      a limit at the pullback level; unfilled after 5 sessions = expired
  stop/T1/T2 each target is graded on its own against the stop: +1.5R or +3R
             if the target trades first, -1R if the stop does. A bar touching
             both counts as the stop (we can't see the order within a bar).
  time       anything unresolved 20 sessions after the fill closes at that
             session's close, at whatever R that is.
Basis: high/low bars for the seven majors and the markets; closes only for
the 21 crosses, whose true high and low can't be rebuilt from free data.
Close-basis grading misses intraday touches, so it is labelled.
"""

from __future__ import annotations

import pandas as pd

PATH = "log/setups.json"
FILL_SESSIONS = 5
HOLD_SESSIONS = 20


def price_bars(name: str, bars: dict, closes: dict) -> tuple[pd.DataFrame | None, str]:
    if name in bars:
        return bars[name][["high", "low", "close"]], "high/low"
    if name in closes:
        c = closes[name]
        return pd.DataFrame({"high": c, "low": c, "close": c}), "close"
    return None, "-"


def grade(t: dict, px: pd.DataFrame | None, asof) -> dict:
    """Status and results of one ticket as of `asof`."""
    out = {**t, "status": "pending", "filled": None, "results": [None] * len(t["targets"]),
           "exits": [None] * len(t["targets"])}
    # Market tickets logged before 2026-10-27 were priced from ETF stand-ins
    # (WTI from USO at ~166). Graded against real levels they'd be nonsense,
    # so they're voided, not edited: the log stays as it was written.
    if t.get("kind") == "asset" and "price_source" not in t:
        return {**out, "status": "void"}
    if px is None:
        return out
    side = 1 if t["side"] == "long" else -1
    risk = abs(t["entry"] - t["stop"])
    after = px[(px.index > pd.Timestamp(t["issued"])) & (px.index <= asof)]
    hit = lambda bar, level, s: (bar["low"] <= level) if s < 0 else (bar["high"] >= level)
    for i, (day, bar) in enumerate(after.iterrows()):
        if out["filled"] is None:
            if i >= FILL_SESSIONS:
                return {**out, "status": "expired"}
            if not hit(bar, t["entry"], -side):
                continue
            out["filled"], fill_i = day.date().isoformat(), i
        for k, target in enumerate(t["targets"]):
            if out["results"][k] is not None:
                continue
            if hit(bar, t["stop"], -side):
                out["results"][k], out["exits"][k] = -1.0, day.date().isoformat()
            elif hit(bar, target, side):
                out["results"][k] = round(abs(target - t["entry"]) / risk, 2)
                out["exits"][k] = day.date().isoformat()
            elif i - fill_i >= HOLD_SESSIONS:
                out["results"][k] = round(side * (bar["close"] - t["entry"]) / risk, 2)
                out["exits"][k] = day.date().isoformat()
        if all(r is not None for r in out["results"]):
            return {**out, "status": "closed"}
    return {**out, "status": "open" if out["filled"] else "pending"}


def update(tickets: list[dict] | None, cards: list[dict], bars: dict, closes: dict,
           asof, sources: dict | None = None) -> tuple[list[dict], list[dict]]:
    """Add tickets for new setups, then grade everything.
    Returns (stored tickets, graded tickets)."""
    tickets = list(tickets or [])
    live = {(g["name"], g["side"]) for g in
            (grade(t, price_bars(t["name"], bars, closes)[0], asof) for t in tickets)
            if g["status"] in ("pending", "open")}
    day = asof.date().isoformat()
    for c in cards:
        s = c.get("setup")
        if s and (c["name"], s["side"]) not in live and not any(
                t["name"] == c["name"] and t["issued"] == day for t in tickets):
            tickets.append({"name": c["name"], "kind": c["kind"], "side": s["side"], "issued": day,
                            "entry": s["entry"], "stop": s["stop"], "targets": s["targets"],
                            "targets_r": s["targets_r"],
                            "basis": price_bars(c["name"], bars, closes)[1],
                            "price_source": (sources or {}).get(c["name"], "fx crosses")})
    graded = [grade(t, price_bars(t["name"], bars, closes)[0], asof) for t in tickets]
    return tickets, graded


def summary(graded: list[dict]) -> dict:
    """Record per target: how often it was reached before the stop, and the average R."""
    filled = [g for g in graded if g["filled"]]
    graded = [g for g in graded if g["status"] != "void"]
    out = {"tickets": len(graded), "pending": sum(g["status"] == "pending" for g in graded),
           "expired": sum(g["status"] == "expired" for g in graded),
           "open": sum(g["status"] == "open" for g in graded), "filled": len(filled), "targets": []}
    for k in range(max((len(g["targets"]) for g in graded), default=0)):
        done = [g["results"][k] for g in filled if g["results"][k] is not None]
        out["targets"].append({
            "r": graded[0]["targets_r"][k] if graded else None, "resolved": len(done),
            "hit": round(sum(r > 0 for r in done) / len(done), 3) if done else None,
            "avg_r": round(sum(done) / len(done), 2) if done else None})
    return out


if __name__ == "__main__":
    days = pd.bdate_range("2026-10-01", periods=30)
    bar = lambda lo, hi, c: {"high": hi, "low": lo, "close": c}
    px = pd.DataFrame([bar(99.8, 100.2, 100.0)] * 30, index=days)
    t = {"name": "X", "side": "long", "issued": "2026-10-01", "entry": 99.5, "stop": 98.5,
         "targets": [101.0, 102.5], "targets_r": [1.5, 3.0]}
    assert grade(t, px, days[-1])["status"] == "expired"              # never pulled back to 99.5
    px.iloc[2] = bar(99.4, 100.0, 99.8)                              # filled on day 3
    px.iloc[4] = bar(99.9, 101.1, 101.0)                             # T1 hit, T2 not
    px.iloc[6] = bar(98.4, 99.9, 98.6)                               # then stopped
    g = grade(t, px, days[-1])
    assert g["status"] == "closed" and g["results"] == [1.5, -1.0], g
    px.iloc[4] = bar(98.0, 101.5, 100.0)                             # stop and T1 same bar
    assert grade(t, px, days[-1])["results"][0] == -1.0              # counts as the stop
    stored, graded = update([t], [{"name": "X", "kind": "pair", "setup": {**t, "side": "long"}}],
                            {"X": px}, {}, days[3])                  # ticket still open -> no new one
    assert len(stored) == 1
    print("setups: ok")
