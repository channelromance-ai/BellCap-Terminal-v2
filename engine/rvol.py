"""
Hourly relative volume (RVOL) for gold: was the hour that just finished
busier than that same hour normally is?

Ported from v1, where the source was verified: Yahoo's hourly COMEX gold bars
sum to 94-97% of settlement volume on normal days. Each completed hour is
compared with the same New York hour over the previous 15 trading days and
flagged at 1.5x. Observation only, never scored.

The roll: GC=F is whichever contract Yahoo calls front, and in the days
before a switch volume drains into the next one (16-42% of normal the evening
before the July 2026 switch). Summing the nearest two contracts measures
total activity regardless of which is labelled front.

Why not Twelve Data: checked 2026-10-25. Its hourly GLD volume summed to
1.5-3.6x its own daily total, erratically, while Yahoo's summed to 85-97%.
Yahoo throttles shared cloud addresses, so a blocked run reports
"unavailable" rather than a number (decided with the user 2026-10-25).
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pandas as pd

from . import config as C

NY = "America/New_York"
# Gold's liquid delivery months. October is listed but volume rolls straight
# from August to December, so leaving it out doesn't move a ratio.
GC_MONTHS = {2: "G", 4: "J", 6: "M", 8: "Q", 12: "Z"}
ZERO_SHARE_MAX = 0.2      # a baseline more than 20% zero bars is too thin to judge


def last_trading_day(year: int, month: int) -> date:
    """Third-last business day of the delivery month (holidays ignored: at
    worst a day out, on a day the expiring contract trades almost nothing)."""
    d = date(year + (month == 12), month % 12 + 1, 1)
    seen = 0
    while seen < 3:
        d -= timedelta(days=1)
        if d.weekday() < 5:
            seen += 1
    return d


def gc_candidates(asof: date, count: int) -> list[tuple[str, date]]:
    out, year, month = [], asof.year, asof.month
    for _ in range(36):
        if month in GC_MONTHS and last_trading_day(year, month) >= asof:
            out.append((f"GC{GC_MONTHS[month]}{year % 100:02d}.CMX", last_trading_day(year, month)))
            if len(out) == count:
                break
        month, year = (1, year + 1) if month == 12 else (month + 1, year)
    return out


def session_hour(hour_start: pd.Timestamp) -> bool:
    """Globex gold: Sunday 18:00 to Friday 17:00 New York, daily break 17-18."""
    ts = pd.Timestamp(hour_start).tz_convert(NY)
    dow, hour = ts.dayofweek, ts.hour
    if dow == 5:
        return False
    if dow == 6:
        return hour >= 18
    if dow == 4:
        return hour < 17
    return hour != 17


def _yahoo_hourly(symbol: str) -> pd.Series:
    import yfinance as yf
    df = yf.download(symbol, period="60d", interval="1h", auto_adjust=False, progress=False,
                     multi_level_index=False, threads=False, timeout=20)
    if df is None or df.empty or "Volume" not in df.columns:
        return pd.Series(dtype=float)
    idx = df.index if df.index.tz is not None else df.index.tz_localize("UTC")
    return pd.Series(df["Volume"].astype(float).values, index=idx.tz_convert(NY))


def sum_contracts(parts: list[pd.Series]) -> pd.Series:
    """Total volume per hour; an hour one contract didn't trade counts as zero for it."""
    clean = [p[~p.index.duplicated(keep="last")] for p in parts if not p.empty]
    if not clean:
        return pd.Series(dtype=float)
    return pd.concat(clean, axis=1).fillna(0.0).sum(axis=1).sort_index()


def gold_hourly(asof: date, fetch=_yahoo_hourly) -> tuple[pd.Series, list[str]]:
    """Front + next contract, or an error: a missing leg in roll week brings
    back the exact gap the sum exists to remove. Only exception: a contract a
    week from expiry that Yahoo has already dropped trades nil, so the next
    one along takes its place."""
    used, parts = [], []
    for sym, ltd in gc_candidates(asof, 3):
        series = fetch(sym)
        if series.empty:
            if not used and (ltd - asof).days <= 7:
                continue
            raise RuntimeError(f"{sym} returned no hourly data")
        used.append(sym)
        parts.append(series)
        if len(used) == 2:
            break
    if len(used) < 2:
        raise RuntimeError(f"needed two gold contracts, got {used or 'none'}")
    return sum_contracts(parts), used


def evaluate(volume: pd.Series, hour_start: pd.Timestamp) -> dict:
    """One hour against the mean of the same New York hour on the previous
    trading days. Too short or mostly-zero history is 'thin', not a ratio."""
    hour_start = pd.Timestamp(hour_start).tz_convert(NY)
    out = {"hour": f"{hour_start:%a %H:%M}-{hour_start + pd.Timedelta(hours=1):%H:%M} ET",
           "hour_start": hour_start.isoformat(), "status": "", "volume": None,
           "baseline": None, "rvol": None, "flag": False}
    volume = volume[~volume.index.duplicated(keep="last")]
    if hour_start not in volume.index:
        return {**out, "status": "no bar"}
    history = volume[(volume.index < hour_start) & (volume.index.hour == hour_start.hour)]
    history = history.iloc[-C.RVOL_BASELINE_DAYS:]
    out["volume"] = int(volume.loc[hour_start])
    if (len(history) < C.RVOL_BASELINE_DAYS or (history == 0).mean() > ZERO_SHARE_MAX
            or history.mean() <= 0):
        return {**out, "status": "thin"}
    ratio = out["volume"] / history.mean()
    return {**out, "status": "ok", "baseline": int(history.mean()), "rvol": round(ratio, 2),
            "flag": bool(ratio >= C.RVOL_THRESHOLD)}


def reading(now: datetime | None = None, fetch=_yahoo_hourly) -> dict:
    """The last completed hour, plus the session so far for the page."""
    now = pd.Timestamp(now or datetime.now(timezone.utc)).tz_convert(NY)
    last = now.floor("h") - pd.Timedelta(hours=1)
    base = {"generated_at": now.tz_convert("UTC").isoformat(timespec="seconds"),
            "source": "Yahoo hourly, front + next COMEX gold contracts",
            "threshold": C.RVOL_THRESHOLD}
    if not session_hour(last):
        return {**base, "status": "closed"}
    try:
        series, contracts = gold_hourly(last.date(), fetch)
    except Exception as e:  # noqa: BLE001 - blocked or empty Yahoo: say so, never guess
        return {**base, "status": "unavailable", "detail": f"{type(e).__name__}: {str(e)[:120]}"}
    hours = [h for h in pd.date_range(last - pd.Timedelta(hours=23), last, freq="h")
             if session_hour(h)]
    session = [evaluate(series, h) for h in hours]
    return {**base, "status": "ok", "contracts": contracts, "latest": session[-1],
            "hours": [h for h in session if h["status"] != "no bar"]}


if __name__ == "__main__":
    assert gc_candidates(date(2026, 10, 25), 2)[0][0] == "GCZ26.CMX"
    assert session_hour(pd.Timestamp("2026-10-25 18:00", tz=NY))       # Sunday reopen
    assert not session_hour(pd.Timestamp("2026-10-26 17:00", tz=NY))   # daily break
    assert not session_hour(pd.Timestamp("2026-10-24 12:00", tz=NY))   # Saturday
    hrs = pd.date_range("2026-09-01", "2026-10-23 16:00", freq="h", tz=NY)
    hrs = hrs[[session_hour(h) for h in hrs]]
    a = pd.Series(100.0, index=hrs)
    b = pd.Series(50.0, index=hrs)
    a.iloc[-1] = 400.0                                                  # last hour: 450 vs 150 usual
    fake = lambda sym: a if sym.startswith("GCZ") else b
    r = reading(pd.Timestamp("2026-10-23 17:30", tz=NY), fetch=fake)
    assert r["status"] == "ok" and r["latest"]["rvol"] == 3.0 and r["latest"]["flag"], r["latest"]
    assert reading(pd.Timestamp("2026-10-24 12:30", tz=NY), fetch=fake)["status"] == "closed"
    broken = reading(pd.Timestamp("2026-10-23 17:30", tz=NY), fetch=lambda s: pd.Series(dtype=float))
    assert broken["status"] == "unavailable"
    print("rvol: ok")
