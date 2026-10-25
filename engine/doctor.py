"""
Health check for every source and every series.

"The request worked" is not the same as "the data is current": RBNZ's old
file and the ECB's HICP both download perfectly and stopped updating months
ago. So each series is judged on its latest date against its max age, and a
source that fails outright marks all of its series as failed rather than
dropping them from the report.

Writes data/health.json and, when running in GitHub Actions, a table to the
job summary page so the result can be read without opening a log.
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from .catalog import GAPS, SOURCES
from .sources import forexfactory


def _last(frame: pd.DataFrame, col: str):
    s = frame[col].dropna() if col in frame else pd.Series(dtype=float)
    if isinstance(s, pd.DataFrame):          # OHLC frames: judge on the close
        s = s["close"].dropna()
    return (s.index[-1], float(s.iloc[-1]), len(s)) if len(s) else (None, None, 0)


def check(today: pd.Timestamp | None = None) -> dict:
    today = (today or pd.Timestamp.now(tz="UTC")).tz_localize(None).normalize()
    rows, sources = [], []
    for module, specs in SOURCES.items():
        name = module.__name__.rsplit(".", 1)[-1]
        t0 = time.time()
        try:
            frame, error = module.fetch(), None
        except Exception as e:  # noqa: BLE001 - report every failure, don't stop
            frame, error = pd.DataFrame(), f"{type(e).__name__}: {e}"
        sources.append({"source": name, "ok": error is None, "error": error,
                        "seconds": round(time.time() - t0, 1)})
        for spec in specs:
            col = spec.id[3:] if spec.id.startswith("PX.") else spec.id
            date, value, n = _last(frame, col)
            age = (today - date).days if date is not None else None
            status = ("fail" if error else "missing" if date is None
                      else "stale" if age > spec.max_age else "ok")
            rows.append({"id": spec.id, "name": spec.name, "group": spec.group,
                         "source": name, "status": status, "points": n,
                         "last_date": date.date().isoformat() if date is not None else None,
                         "last_value": None if value is None else round(value, 4),
                         "age_days": age, "max_age": spec.max_age})
    calendar = _check_calendar()
    counts = pd.Series([r["status"] for r in rows]).value_counts().to_dict()
    return {"checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "summary": counts, "sources": sources, "series": rows,
            "calendar": calendar, "gaps": GAPS}


def _check_calendar() -> dict:
    try:
        cal = forexfactory.fetch()
        high = cal[cal["impact"] == "High"]
        return {"ok": True, "events": len(cal), "high_impact": len(high),
                "first": cal["time"].min().isoformat(),
                "last": cal["time"].max().isoformat()}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def markdown(report: dict) -> str:
    icon = {"ok": "✅", "stale": "🟡", "missing": "⚪", "fail": "❌"}
    lines = ["## BellCap data health", "",
             f"Checked {report['checked_at']} · " + " · ".join(
                 f"{icon[k]} {k} {v}" for k, v in sorted(report["summary"].items())),
             "", "| | Series | Source | Last date | Value | Age (days) |",
             "|---|---|---|---|---|---|"]
    for r in report["series"]:
        lines.append(f"| {icon[r['status']]} | {r['name']} | {r['source']} | "
                     f"{r['last_date'] or '-'} | {r['last_value'] if r['last_value'] is not None else '-'} | "
                     f"{r['age_days'] if r['age_days'] is not None else '-'} / {r['max_age']} |")
    failed = [s for s in report["sources"] if not s["ok"]]
    if failed:
        lines += ["", "### Failed sources", ""]
        lines += [f"- **{s['source']}**: {s['error']}" for s in failed]
    cal = report["calendar"]
    lines += ["", "### Calendar", "",
              f"- {cal['events']} events this week, {cal['high_impact']} high impact"
              if cal["ok"] else f"- ❌ {cal['error']}"]
    lines += ["", "### Known gaps", ""] + [f"- **{k}**: {v}" for k, v in report["gaps"].items()]
    return "\n".join(lines) + "\n"


def run(out_dir: str = "data") -> dict:
    report = check()
    Path(out_dir).mkdir(exist_ok=True)
    Path(out_dir, "health.json").write_text(json.dumps(report, indent=1))
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write(markdown(report))
    return report
