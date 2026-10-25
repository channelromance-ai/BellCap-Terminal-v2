"""
BellCap Terminal v2 - command line.

    python run.py update     fetch everything, check health, build the read, save it
    python run.py show       print the latest saved read (on your PC, not in CI)
    python run.py doctor     check every source and series, write data/health.json
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def load_env(path: str = ".env") -> None:
    """Local runs read keys from .env; in GitHub Actions they're secrets."""
    p = Path(path)
    if not p.exists():
        return
    for line in p.read_text().splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


def cmd_doctor() -> int:
    from engine import doctor
    report = doctor.run()
    for r in report["series"]:
        print(f"{r['status']:8} {r['id']:16} {r['source']:11} "
              f"{r['last_date'] or '-':11} {r['last_value'] if r['last_value'] is not None else '-':>10} "
              f"age {r['age_days'] if r['age_days'] is not None else '-'}/{r['max_age']}")
    for s in report["sources"]:
        if not s["ok"]:
            print(f"SOURCE FAILED {s['source']}: {s['error']}")
    cal = report["calendar"]
    print("calendar:", cal if not cal["ok"] else
          f"{cal['events']} events, {cal['high_impact']} high impact")
    print("summary:", report["summary"])
    return 0


def cmd_update() -> int:
    """In GitHub Actions the run log is public, so this prints that a read was
    saved and nothing about what it says."""
    from engine import doctor, model, store
    from engine.collect import collect
    data = collect()
    health = doctor.run(data=data)
    snapshot, record = model.build(data, health)
    where = store.save(snapshot, record)
    print(f"read for {snapshot['asof']} saved to {where} "
          f"(model {snapshot['model_version']}, health {health['summary']})")
    if not os.environ.get("GITHUB_ACTIONS"):
        return cmd_show()
    return 0


def cmd_show() -> int:
    from engine import store
    snap = store.latest()
    if snap is None:
        print("no saved read yet - run: python run.py update")
        return 1
    reg = snap["regime"]
    print(f"\nRead as of {snap['asof']}   risk regime: {reg.get('state')} "
          f"(VIX {reg.get('vix')}, {reg.get('vix_pct_1y')}th pct, 1m {reg.get('vix_1m_move')})")
    print("\nCURRENCIES  score  rates   path  mom3m   cpi  gap   positioning")
    for c in sorted(snap["currencies"], key=lambda r: -(r["score"] or -999)):
        print(f"  {c['ccy']}  {c['score'] if c['score'] is not None else '-':>6}  "
              f"{c['quality']:<11} {c['path_bp'] if c['path_bp'] is not None else '-':>5} "
              f"{c['momentum_3m_bp'] if c['momentum_3m_bp'] is not None else '-':>6} "
              f"{c['cpi'] if c['cpi'] is not None else '-':>5} "
              f"{c['cpi_gap'] if c['cpi_gap'] is not None else '-':>5}  {c['cot_flag'] or ''}")
    print("\nPAIRS WITH A MACRO BIAS   diff  rates-vs-price  fair-value z  link")
    for p in snap["pairs"]:
        if p["bias"]:
            print(f"  {p['pair']} {p['bias']:<5}  {p['macro_diff']:>6}  "
                  f"{p['rates_vs_price'] or '-':<14}  "
                  f"{p['residual_z'] if p['residual_z'] is not None else '-':>11}  "
                  f"{p['link_corr'] if p['link_corr'] is not None else '-'}")
    print("\nASSETS   score  1m%    3m%    positioning")
    for a in snap["assets"]:
        extra = f"  gold/real-yield link {a['link_check']['state']}" if a["link_check"] else ""
        print(f"  {a['name']:<7} {a['score'] if a['score'] is not None else '-':>5}  "
              f"{a['return_1m_pct']:>6} {a['return_3m_pct']:>6}  {a['cot_flag'] or ''}{extra}")
    upcoming = [e for e in snap["calendar"] if not e["past"] and e["impact"] == "High"]
    print(f"\nHIGH-IMPACT EVENTS STILL TO COME THIS WEEK: {len(upcoming)}")
    for e in upcoming[:12]:
        print(f"  {e['time'][:16]}  {e['currency']}  {e['title']}")
    if snap["data_warnings"]:
        print("\nDATA WARNINGS:", "; ".join(snap["data_warnings"]))
    return 0


COMMANDS = {"update": cmd_update, "show": cmd_show, "doctor": cmd_doctor}

if __name__ == "__main__":
    load_env()
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd not in COMMANDS:
        print(__doc__)
        sys.exit(2)
    sys.exit(COMMANDS[cmd]())
