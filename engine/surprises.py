"""
Data surprises, collected from today so they can be tested later.

No free source has surprise history, and Forex Factory's export has
forecasts but never actuals. But each release's "previous" field is the
actual of the release before it, so pairing consecutive releases of the same
event gives forecast and actual for every high and medium impact release,
in every currency, for free. The actual arrives with the next release (a
month later for most), which is fine for research.

Ceiling: "previous" is sometimes the revised figure rather than the first
print, which blurs a few surprises. Swap in first prints from FRED or
Eurostat for the big US and euro releases if that ever matters.

Stored privately as log/calendar.json, keyed by "time|currency|title". A
forecast is only updated before its release, so the stored one is the last
consensus the market saw.
"""

from __future__ import annotations

import re

import pandas as pd

PATH = "log/calendar.json"
UNITS = {"K": 1e3, "M": 1e6, "B": 1e9, "T": 1e12}


def number(text) -> float | None:
    """'0.3%' -> 0.3, '198K' -> 198000, '-47' -> -47, '' -> None."""
    m = re.fullmatch(r"\s*([<>]?)(-?\d+(?:\.\d+)?)\s*([KMBT%]?)\s*", str(text or ""))
    if not m:
        return None
    return float(m.group(2)) * UNITS.get(m.group(3), 1.0)


def merge(store: dict | None, calendar: pd.DataFrame | None, now: pd.Timestamp) -> dict:
    store = dict(store or {})
    if calendar is None:
        return store
    for e in calendar[calendar["impact"].isin(["High", "Medium"])].itertuples(index=False):
        key = f"{e.time.isoformat()}|{e.currency}|{e.title}"
        row = store.get(key, {"time": e.time.isoformat(), "currency": e.currency,
                              "title": e.title, "impact": e.impact})
        if e.time > now or "forecast" not in row:     # freeze consensus at release
            row["forecast"], row["previous"] = e.forecast or None, e.previous or None
        store[key] = row
    return store


def with_actuals(store: dict) -> list[dict]:
    """Each release with its actual (= the next release's 'previous') and
    surprise = actual - forecast, where both parse as numbers."""
    by_event: dict[tuple, list] = {}
    for row in store.values():
        by_event.setdefault((row["currency"], row["title"]), []).append(row)
    out = []
    for rows in by_event.values():
        rows.sort(key=lambda r: r["time"])
        for this, nxt in zip(rows, rows[1:] + [None]):
            actual = number(nxt["previous"]) if nxt else None
            forecast = number(this.get("forecast"))
            out.append({**this, "actual": actual,
                        "surprise": None if actual is None or forecast is None else actual - forecast})
    return sorted(out, key=lambda r: r["time"])


if __name__ == "__main__":
    assert number("0.3%") == 0.3 and number("198K") == 198000 and number("-47") == -47
    assert number("") is None and number("Tentative") is None
    t0, t1 = pd.Timestamp("2026-10-01T12:30Z"), pd.Timestamp("2026-11-05T12:30Z")
    cal = lambda t, f, p: pd.DataFrame([{"time": t, "currency": "USD", "impact": "High",
                                         "title": "CPI m/m", "forecast": f, "previous": p}])
    s = merge(None, cal(t0, "0.3%", "0.2%"), t0 - pd.Timedelta(hours=1))
    s = merge(s, cal(t0, "0.9%", "0.2%"), t0 + pd.Timedelta(hours=1))   # after release: frozen
    s = merge(s, cal(t1, "0.2%", "0.5%"), t1 - pd.Timedelta(days=2))    # next release reveals 0.5
    first = with_actuals(s)[0]
    assert first["forecast"] == "0.3%" and first["actual"] == 0.5 and abs(first["surprise"] - 0.2) < 1e-9
    print("surprises: ok")
