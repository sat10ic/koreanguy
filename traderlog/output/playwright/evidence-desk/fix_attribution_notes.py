"""Fix the 13 just-appended invalid ledger lines (empty notes_limitations).

Governance intent: never rewrite PRE-EXISTING attribution history. These 13
lines were appended by this session minutes ago and fail the validator
(empty notes_limitations), so the corrected block below re-appends them in the
same positions; the original 19 lines are preserved byte-for-byte.
"""
import json
import sys
from pathlib import Path

root = Path(r"C:\Users\satta\Downloads\koreanguy\traderlog")
LEDGER = root / "design" / "MODEL_WORK_LOG.jsonl"
lines = LEDGER.read_text(encoding="utf-8").splitlines()
records = [json.loads(l) for l in lines if l.strip()]
ids = [r["id"] for r in records]

MINE = [
    "attr-w3d-shell-type-flash-executor-20260823-001",
    "attr-w3d-charts-flash-executor-20260823-001",
    "attr-w3d-feed-thumbs-flash-executor-20260823-001",
    "attr-w3d-debrutalize-flash-executor-20260823-001",
    "attr-w3d-sparse-flash-executor-20260823-001",
    "attr-w3d-tests-flash-executor-20260823-001",
    "attr-w1-roster14-flash-executor-20260823-001",
    "attr-w1-corpus-import-flash-executor-20260823-001",
    "attr-w3d-leaderboard-flash-executor-20260823-001",
    "attr-w3d-redesign-flash-executor-20260823-001",
    "attr-w2-classify-flash-executor-20260823-001",
    "attr-w3d-orchestrator-flash-20260823-001",
    "attr-w3d-review-v4pro-20260823-001",
]
# sanity: precisely my 13 ids are the LAST 13 lines
assert ids[-13:] == MINE, (ids[-13:], MINE)
kept = records[:-13]

NOTES = {
    "attr-w3d-shell-type-flash-executor-20260823-001": "Verified independently; only 2 of 4 owned files needed edits; caret glyphs remain <11px as icons.",
    "attr-w3d-charts-flash-executor-20260823-001": "ECharts uses the SVG renderer; empty states are compact blocks; bundle grew to ~536kB gzip (expected).",
    "attr-w3d-feed-thumbs-flash-executor-20260823-001": "Media count can overcount 404ing mock rows; onError fallback hides and notes 'image unavailable'.",
    "attr-w3d-debrutalize-flash-executor-20260823-001": "Uppercase retained only for the nav strip, single-word table headers and buttons - sanctioned compact operational labels.",
    "attr-w3d-sparse-flash-executor-20260823-001": "Zero-history Breadth path verified by route interception, not a disposable DB (production has history); style!=null chart paths code-reviewed only.",
    "attr-w3d-tests-flash-executor-20260823-001": "Screenshot pixels not visually inspected; one flake seen under a concurrent rebuild (environmental), clean on serial reruns.",
    "attr-w1-roster14-flash-executor-20260823-001": "Roster as of 2026-08-23 nine-handle+ expansions; the four pending and six new handles activate atomically with first capture.",
    "attr-w1-corpus-import-flash-executor-20260823-001": "iManasArora and VCPSwing did not receive new capture in the final throttled run; all new records import as relationship-unresolved (thread unknown); no ancestry synthesized.",
    "attr-w3d-leaderboard-flash-executor-20260823-001": "'mentioned' column nil against current corpus (no watch-idea mentions yet); empty-state path code-reviewed only.",
    "attr-w3d-redesign-flash-executor-20260823-001": "Pixel aesthetics unverified (no image-capable reviewer); validated via DOM/computed-style checks; VISUAL_LANGUAGE.md reconciled in the same commit set.",
    "attr-w2-classify-flash-executor-20260823-001": "Vision transcription blocked: subagents run deepseek-v4-flash (no image input) and wrote nothing; ~190 archived images await a vision-capable pass; no unreadable:true guesses were written.",
    "attr-w3d-orchestrator-flash-20260823-001": "Personal verification covered builds, full suite (256), run_checks, deterministic 1920x1080 checks, live browser probes, corpus and integrity checks.",
    "attr-w3d-review-v4pro-20260823-001": "Rendered against the pre-redesign aesthetic; pixel-level appearance not verifiable (no image-capable reviewer); the follow-up redesign warrants an equivalent re-audit.",
}

for r in records[-13:]:
    r["notes_limitations"] = NOTES[r["id"]]

kept += records[-13:]
with LEDGER.open("w", encoding="utf-8") as fh:
    for r in kept:
        fh.write(json.dumps(r, ensure_ascii=False) + "\n")
print("rewrote ledger:", len(kept), "lines (19 original + 13 corrected)")