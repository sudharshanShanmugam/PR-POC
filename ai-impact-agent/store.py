"""
Simple JSON file store for ImpactReports.
Persists all analyzed PRs to data/reports.json.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Optional

from models import ImpactReport

_STORE_PATH = Path(__file__).parent / "data" / "reports.json"
_lock = threading.Lock()


def _load() -> list[dict]:
    if not _STORE_PATH.exists():
        return []
    try:
        return json.loads(_STORE_PATH.read_text())
    except Exception:
        return []


def _save(records: list[dict]) -> None:
    _STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _STORE_PATH.write_text(json.dumps(records, indent=2))


def save_report(report: ImpactReport, pr_url: str = "") -> None:
    with _lock:
        records = _load()
        entry = report.model_dump()
        entry["pr_url"] = pr_url
        # Update existing or prepend
        for i, r in enumerate(records):
            if r["pr_number"] == report.pr_number and r["repo"] == report.repo:
                records[i] = entry
                _save(records)
                return
        records.insert(0, entry)
        _save(records)


def list_reports() -> list[dict]:
    with _lock:
        return _load()


def get_report(repo: str, pr_number: int) -> Optional[dict]:
    with _lock:
        for r in _load():
            if r["repo"] == repo and r["pr_number"] == pr_number:
                return r
        return None
