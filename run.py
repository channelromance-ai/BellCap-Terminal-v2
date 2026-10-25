"""
BellCap Terminal v2 - command line.

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


COMMANDS = {"doctor": cmd_doctor}

if __name__ == "__main__":
    load_env()
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd not in COMMANDS:
        print(__doc__)
        sys.exit(2)
    sys.exit(COMMANDS[cmd]())
