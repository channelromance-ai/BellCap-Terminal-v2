"""
Where reads are kept: the private data repo, never this public one.

In GitHub Actions the private repo (bellcap-v2-data) is checked out into
./private and BELLCAP_PRIVATE_DIR points at it; the workflow commits and
pushes it afterwards, so the token never passes through Python. Locally the
same files land in data/private, which is gitignored.

  latest.json             the newest snapshot, what the web app reads
  snapshots/<asof>.json   one per read date; a later run the same day replaces it
  log/reads.jsonl         append-only: every run, never edited. Git history in
                          the private repo makes any later edit visible, which
                          is what lets the edge report be trusted.
"""

from __future__ import annotations

import json
import os
from pathlib import Path


def private_dir() -> Path:
    return Path(os.environ.get("BELLCAP_PRIVATE_DIR", "data/private"))


def _dump(obj) -> str:
    # allow_nan=False: a NaN that slipped through is a bug to see, not to publish
    return json.dumps(obj, allow_nan=False, separators=(",", ":"))


def save(snapshot: dict, record: dict) -> Path:
    root = private_dir()
    (root / "snapshots").mkdir(parents=True, exist_ok=True)
    (root / "log").mkdir(parents=True, exist_ok=True)
    text = _dump(snapshot)
    (root / "latest.json").write_text(text)
    (root / "snapshots" / f"{snapshot['asof']}.json").write_text(text)
    with open(root / "log" / "reads.jsonl", "a", encoding="utf-8") as f:
        f.write(_dump(record) + "\n")
    return root


def latest() -> dict | None:
    p = private_dir() / "latest.json"
    return json.loads(p.read_text()) if p.exists() else None
