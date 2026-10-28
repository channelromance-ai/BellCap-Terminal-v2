"""
The Asia session, the hours the user trades: 23:00-08:00 UTC (Sydney and
Tokyo; 6pm-3am in Winnipeg on daylight time, 5pm-2am in winter).

For every pair and gold, from hourly closes over the last 60 trading days:

  share      the Asia session's range as a share of the whole day's range.
             Asia is 9 of 24 hours (37.5%); measured 2026-10-28, NZD, AUD and
             JPY pairs and gold make 55-70% of their day's range in Asia, EUR,
             GBP and CAD pairs 39-51%.
  active     share >= ASIA_ACTIVE_SHARE: the market actually moves while the
             user is at the screen. The site's ASIA switch filters on this.
  avg range  the typical Asia session high-low, in % and in price
  last       the last COMPLETED Asia session: its range against the typical
             one, and its net move

A trading day here runs 23:00 to 23:00 UTC, so its first nine hours are the
Asia session. Crosses come from hourly closes of their legs, so their ranges
are close-to-close (slightly smaller than true high-low); same for all, so the
comparison holds. Indices and oil have no hourly feed here: JP225 is counted
as active (its cash market is Tokyo), the rest as not.
"""

from __future__ import annotations

import pandas as pd

from . import config as C
from . import fx
from .ts import rnd

ASIA_HOURS = 9                    # 23:00-08:00 UTC
DAYS = 60
ALWAYS_ACTIVE = {"JP225"}


def by_day(close: pd.Series) -> pd.DataFrame:
    """Per trading day (23:00 UTC start): Asia high-low, full-day high-low,
    Asia first and last close."""
    c = close.dropna()
    shifted = c.index + pd.Timedelta(hours=1)
    df = pd.DataFrame({"c": c.values, "day": shifted.normalize(), "asia": shifted.hour < ASIA_HOURS})
    day = df.groupby("day")["c"].agg(lambda s: s.max() - s.min()).rename("day_range")
    a = df[df["asia"]].groupby("day")["c"]
    out = pd.concat([day, a.agg(lambda s: s.max() - s.min()).rename("asia_range"),
                     a.first().rename("asia_open"), a.last().rename("asia_close"),
                     a.size().rename("asia_bars")], axis=1)
    return out.dropna()


def profile(close: pd.Series, now: pd.Timestamp) -> dict | None:
    d = by_day(close)
    # Only finished sessions: today's counts once 08:00 UTC has passed.
    session_end = d.index - pd.Timedelta(hours=1) + pd.Timedelta(hours=ASIA_HOURS)
    d = d[(session_end <= now.tz_localize(None)) & (d["asia_bars"] >= 6)].iloc[-DAYS:]
    d = d[d["day_range"] > 0]
    if len(d) < 20:
        return None
    price = float(close.dropna().iloc[-1])
    share = float((d["asia_range"] / d["day_range"]).mean())
    avg = float(d["asia_range"].mean())
    last = d.iloc[-1]
    digits = 5 if price < 20 else 2
    return {"share": rnd(share, 2), "active": share >= C.ASIA_ACTIVE_SHARE,
            "avg_range": rnd(avg, digits), "avg_range_pct": rnd(100 * avg / price, 3),
            "last_date": str((d.index[-1] - pd.Timedelta(days=1)).date()),
            "last_range": rnd(float(last["asia_range"]), digits),
            "last_vs_avg": rnd(float(last["asia_range"]) / avg, 2) if avg else None,
            "last_move_pct": rnd(100 * (last["asia_close"] / last["asia_open"] - 1), 2)}


def in_session(iso_time: str) -> bool:
    h = pd.Timestamp(iso_time).tz_convert("UTC").hour
    return h >= 23 or h < 8


def read(hourly: dict[str, pd.DataFrame], calendar: list[dict], now=None) -> dict:
    now = now or pd.Timestamp.now(tz="UTC")
    markets = {}
    if hourly:
        closes = {**{k: v["close"] for k, v in hourly.items()}, **fx.pair_closes(fx.usd_value(hourly))}
        for name, c in closes.items():
            p = profile(c, now)
            if p:
                markets[name] = p
    for name in ALWAYS_ACTIVE:
        markets.setdefault(name, {"active": True, "note": "cash market trades in the Tokyo session"})
    return {"window": "23:00-08:00 UTC", "active_share": C.ASIA_ACTIVE_SHARE, "markets": markets,
            "events": [e for e in calendar if in_session(e["time"])]}


if __name__ == "__main__":
    hours = pd.date_range("2026-08-02 22:00", "2026-10-27 22:00", freq="h")
    # A market that only moves in Asia hours: up 1 each Asia hour, flat otherwise.
    step = pd.Series([1.0 if (h.hour >= 23 or h.hour < 8) else 0.0 for h in hours], index=hours)
    close = 100 + step.cumsum()
    p = profile(close, pd.Timestamp("2026-10-27 22:30", tz="UTC"))
    assert p["share"] == 1.0 and p["active"], p
    flat_asia = 100 + pd.Series([0.0 if (h.hour >= 23 or h.hour < 8) else 1.0 for h in hours], index=hours).cumsum()
    q = profile(flat_asia, pd.Timestamp("2026-10-27 22:30", tz="UTC"))
    assert q["share"] < 0.2 and not q["active"], q
    assert in_session("2026-10-28T23:30:00+00:00") and in_session("2026-10-28T01:00:00+00:00")
    assert not in_session("2026-10-28T12:30:00+00:00")
    print("asia: ok")
