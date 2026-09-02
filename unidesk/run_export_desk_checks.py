"""Export the desk's published self-check invariants for the UI (foolproof
layer — the desk shows its own verification results, no LLM in the loop).

Source: unidesk/STATE.json `checks` (written by the invariant runner:
unidesk/checks/published_invariants.py). Values are pass/fail facts with
measured detail, e.g. "88 prices match bhavcopy for 2026-09-01".

Output: unidesk_terminal/src/data/desk_checks.json
"""
from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
STATE = REPO / "unidesk" / "STATE.json"
OUT = REPO / "unidesk_terminal" / "src" / "data" / "desk_checks.json"

# Human-readable names for the invariant keys (UI copy, Beginner-friendly).
NAMES = {
    "inv:outcome_labels": "Outcome labels: every call classified, one current label version",
    "inv:funnel_nested": "Funnel is nested: universe > gated > candidates > high quality > near trigger",
    "inv:prices_match_source": "Candidate prices match the exchange bhavcopy, to the paisa",
    "inv:no_hardcoded_market_values": "No market number is hard-coded in the app",
    "inv:ranked_symbols_traded": "Every candidate actually traded on the session date (liveness)",
    "inv:scores_have_variance": "Scores actually vary (a constant score is flagged DEGENERATE)",
    "inv:no_fabricated_rows": "No fabricated rows merged into real output",
}

if __name__ == "__main__":
    state = json.loads(STATE.read_text(encoding="utf-8"))
    checks = []
    for key, value in state.get("checks", {}).items():
        if not key.startswith("inv:"):
            continue
        failed = isinstance(value, str) and "DEGENERATE" in value.upper() or (isinstance(value, str) and value.upper().startswith("FAIL"))
        checks.append({
            "key": key,
            "name": NAMES.get(key, key.removeprefix("inv:")),
            "detail": value,
            "pass": not failed,
        })
    payload = {
        "source": "unidesk/STATE.json checks (unidesk/checks/published_invariants.py)",
        "generator": "unidesk/run_export_desk_checks.py",
        "session": state.get("updated_at"),
        "checks": checks,
    }
    OUT.write_text(json.dumps(payload, indent=1), encoding="utf-8")
    failed_n = sum(1 for c in checks if not c["pass"])
    print(f"[export] {len(checks)} desk self-checks ({failed_n} flagged) -> {OUT}")
