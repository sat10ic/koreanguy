"""python -m traderlog.checks — the audit harness.

Prints a pass/fail table, rewrites STATE.json, exits non-zero if anything failed.
"""
from __future__ import annotations

import sys

from traderlog.checks.runner import OWNER_WAVE, run_all, write_state

_GLYPH = {
    "pass": "OK  ",
    "dry_run": "--  ",
    "not_built_yet": "..  ",
}


def _glyph(status: str) -> str:
    if status.startswith("fail"):
        return "FAIL"
    if status.startswith("stale"):
        return "WARN"
    return _GLYPH.get(status, "??  ")


def _mock_data_notice(state: dict) -> str | None:
    """Describe mock provenance without concealing real ingest evidence."""
    if not state["showing_mock_data"]:
        return None
    if state["counts"].get("posts_real", 0) > 0:
        return (
            "  NOTE: database also contains MOCK data; real posts have been ingested. "
            "Mock rows are excluded from live ingest validation."
        )
    return "  NOTE: database contains MOCK data. Nothing here has been ingested."


def main() -> int:
    results = run_all()
    state = write_state(results)

    print()
    print("  TRADERLOG CHECKS")
    print("  " + "-" * 68)
    for r in results:
        wave = OWNER_WAVE.get(r.name, "")
        detail = r.detail or ("" if r.status == "pass" else r.status)
        if r.status.startswith("fail"):
            detail = r.status[6:]
        print(f"  {_glyph(r.status)}  {r.name:<10} {wave:<4} {detail[:46]}")
    print("  " + "-" * 68)

    failed = [r for r in results if not r.ok]
    pending = [r.name for r in results if r.status == "not_built_yet"]

    # ASCII only below: the Windows console this project runs on is cp1252 and
    # mangles box-drawing / typographic characters.
    c = state["counts"]
    print(
        f"  wave {state['wave']} | {c['posts']} posts | {c['positions']} positions"
        f" | {c['review_open']} in review | commit {state['last_verified_commit']}"
    )
    mock_notice = _mock_data_notice(state)
    if mock_notice:
        print(mock_notice)
    if pending:
        print(f"  not built yet: {', '.join(pending)} -- a green run does not yet")
        print("  mean the tool works end to end. Each wave flips its own check.")
    print(f"  STATE.json updated. {'FAILED' if failed else 'No failures.'}")
    print()

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
