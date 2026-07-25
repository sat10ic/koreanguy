"""manas_os/integrity/report.py -- runs every integrity check and renders
Markdown. Consumed by `manas integrity` (manas_os/cli/__init__.py::_cmd_integrity).

run_all() opens the ONLY real-DB connection this package makes, and it is
STRICTLY read-only: `sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)`.
Never db.connect()/db.init_db() -- those write on open (WAL init, settings
row upsert, ALTER-based migrations) and that write is exactly what made
`manas scorecard` die with "database is locked" against a live pipeline
(see db/__init__.py's connect() docstring). An integrity audit that can
itself corrupt or lock the thing it is auditing would defeat the point.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import date
from pathlib import Path
from typing import Any

from manas_os import market_calendar
from manas_os.integrity import checks

_STATUS_ORDER = {"FAIL": 0, "WARN": 1, "PASS": 2}


def run_all(db_path: str | Path, today: date) -> dict[str, Any]:
    """Execute every check against `db_path` (opened read-only) as of `today`.

    Returns {"today", "expected_session", "overall_status", "n_checks",
    "n_fail", "n_warn", "checks": [check_result, ...]}. overall_status is the
    worst individual status (FAIL > WARN > PASS).
    """
    uri = f"file:{db_path}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    try:
        expected_session = market_calendar.last_trading_day(today)
        expected_session_s = expected_session.isoformat()

        results = [
            checks.check_freshness(conn, today),
            checks.check_silent_skips(conn, expected_session_s),
            checks.check_verdict_grading(conn, today),
            checks.check_card_consistency(conn, expected_session_s),
            checks.check_overfit_capacity(conn),
            checks.check_survivorship(conn),
            checks.check_lookahead(),
        ]
    finally:
        conn.close()

    overall = min((r["status"] for r in results), key=lambda s: _STATUS_ORDER[s]) if results else "PASS"
    n_fail = sum(1 for r in results if r["status"] == "FAIL")
    n_warn = sum(1 for r in results if r["status"] == "WARN")

    return {
        "today": today.isoformat(),
        "expected_session": expected_session_s,
        "overall_status": overall,
        "n_checks": len(results),
        "n_fail": n_fail,
        "n_warn": n_warn,
        "checks": results,
    }


def to_markdown(result: dict[str, Any]) -> str:
    """Render a run_all() result as Markdown, leading with a one-line
    headline a beginner can read without opening the evidence JSON."""
    overall = result["overall_status"]
    n_checks = result["n_checks"]
    n_fail = result["n_fail"]
    n_warn = result["n_warn"]

    headline_tail = ""
    fresh = next((c for c in result["checks"] if c["name"] == "freshness"), None)
    if fresh is not None and fresh["status"] == "FAIL":
        sessions_behind = fresh["evidence"].get("sessions_behind")
        if sessions_behind:
            headline_tail = f" Pipeline last ran {sessions_behind} session(s) behind."
        elif not fresh["evidence"].get("has_pipeline_run_for_expected_session"):
            headline_tail = " Pipeline did not run for the most recent session."

    lines: list[str] = []
    lines.append(
        f"INTEGRITY: {overall} -- {n_fail} of {n_checks} checks failing "
        f"({n_warn} warning(s)).{headline_tail}"
    )
    lines.append("")
    lines.append(f"As of {result['today']} (expected session: {result['expected_session']}).")
    lines.append("")
    lines.append("| Check | Status | Detail |")
    lines.append("| --- | --- | --- |")
    for c in result["checks"]:
        detail_cell = c["detail"].replace("|", "\\|").replace("\n", " ")
        lines.append(f"| {c['name']} | {c['status']} | {detail_cell} |")
    lines.append("")

    for c in result["checks"]:
        lines.append(f"## [{c['status']}] {c['name']}")
        lines.append("")
        lines.append(c["detail"])
        lines.append("")
        if c["evidence"]:
            lines.append("<details><summary>evidence</summary>")
            lines.append("")
            lines.append("```json")
            lines.append(json.dumps(c["evidence"], indent=2, default=str))
            lines.append("```")
            lines.append("")
            lines.append("</details>")
            lines.append("")

    return "\n".join(lines)
