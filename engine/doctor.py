"""
Health check for every source and every series.

"The request worked" is not the same as "the data is current": RBNZ's old
file and the ECB's HICP both download perfectly and stopped updating months
ago. So each series is judged on its latest date against its max age, and a
source that fails outright marks all of its series as failed rather than
dropping them from the report.

The repo is public, so its run summaries and artifacts are too. Price rows
report date and source but never a value: vendor prices are personal-use
data and don't get published, even as one number in a health table.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from .catalog import GAPS, PRICES, SOURCES
from .collect import Collected, collect


def _row(spec, series: pd.Series, source: str, failed: bool, today,
         show_value: bool = True) -> dict:
    s = series.dropna()
    date = s.index[-1] if len(s) else None
    age = (today - date).days if date is not None else None
    status = ("fail" if failed and date is None else "missing" if date is None
              else "stale" if age > spec.max_age else "ok")
    return {"id": spec.id, "name": spec.name, "group": spec.group,
            "source": source, "status": status, "points": len(s),
            "last_date": date.date().isoformat() if date is not None else None,
            "last_value": round(float(s.iloc[-1]), 4) if show_value and len(s) else None,
            "age_days": age, "max_age": spec.max_age}


def check(data: Collected, today: pd.Timestamp | None = None) -> dict:
    today = (today or pd.Timestamp.now(tz="UTC")).tz_localize(None).normalize()
    failed = {s["source"] for s in data.sources if not s["ok"]}
    rows = []
    for module, specs in SOURCES.items():
        name = module.__name__.rsplit(".", 1)[-1]
        for spec in specs:
            col = data.macro.get(spec.id, pd.Series(dtype=float))
            rows.append(_row(spec, col, name, name in failed, today))
    for spec in PRICES:
        bars = data.bars.get(spec.id)
        close = bars["close"] if bars is not None else pd.Series(dtype=float)
        rows.append(_row(spec, close, data.price_sources.get(spec.id, "-"),
                         spec.id in data.price_errors, today, show_value=False))

    cal = data.calendar
    calendar = ({"ok": True, "events": len(cal),
                 "high_impact": int((cal["impact"] == "High").sum())}
                if cal is not None else {"ok": False, "error": data.calendar_error})
    counts = pd.Series([r["status"] for r in rows]).value_counts().to_dict()
    return {"checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "summary": counts, "sources": data.sources, "series": rows,
            "price_errors": data.price_errors, "calendar": calendar, "gaps": GAPS}


def markdown(report: dict) -> str:
    icon = {"ok": "✅", "stale": "🟡", "missing": "⚪", "fail": "❌"}
    lines = ["## BellCap data health", "",
             f"Checked {report['checked_at']} · " + " · ".join(
                 f"{icon[k]} {k} {v}" for k, v in sorted(report["summary"].items())),
             "", "| | Series | Source | Last date | Value | Age (days) |",
             "|---|---|---|---|---|---|"]
    for r in report["series"]:
        value = r["last_value"] if r["last_value"] is not None else "-"
        age = r["age_days"] if r["age_days"] is not None else "-"
        lines.append(f"| {icon[r['status']]} | {r['name']} | {r['source']} | "
                     f"{r['last_date'] or '-'} | {value} | {age} / {r['max_age']} |")
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


def run(out_dir: str = "data", data: Collected | None = None) -> dict:
    report = check(data or collect())
    Path(out_dir).mkdir(exist_ok=True)
    Path(out_dir, "health.json").write_text(json.dumps(report, indent=1))
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write(markdown(report))
    return report
