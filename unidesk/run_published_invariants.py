"""Run the published invariants against the newest bundled report and record
the results in unidesk/STATE.json (checks.inv:*), then export the UI's
desk-checks snapshot.

B2-4: this script IS now a step of run_desk_refresh.py (after the exports,
before the npm build), so the desk verifies itself on every refresh — no
agent in the loop. A flagged invariant aborts the refresh before anything
is rebuilt.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from unidesk.checks.published_invariants import ALL_INVARIANTS  # noqa: E402

STATE = REPO / "unidesk" / "STATE.json"


def main() -> int:
    state = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}
    checks = state.get("checks", {})
    failed = 0
    for name, fn in ALL_INVARIANTS:
        try:
            checks[f"inv:{name}"] = fn()
        except Exception as exc:
            checks[f"inv:{name}"] = f"ERROR: {exc}"
            failed += 1
    flagged = {k: v for k, v in checks.items()
               if k.startswith("inv:") and ("DEGENERATE" in str(v).upper() or str(v).upper().startswith("FAIL") or str(v).upper().startswith("ERROR"))}
    state["checks"] = checks
    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    STATE.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    print(f"[invariants] {len(ALL_INVARIANTS)} run, {len(flagged)} flagged: {sorted(flagged)}")
    return 1 if flagged else 0


if __name__ == "__main__":
    raise SystemExit(main())
