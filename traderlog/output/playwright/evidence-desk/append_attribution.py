"""Append this session's attribution records to design/MODEL_WORK_LOG.jsonl.

Append-only, one object per distinct contribution. The completion report
design/handoffs/HANDOFF_UI_evidence_desk_completion_2026-08-23_COMPLETED.md
cites every id below (round-trip required by run_checks attribution check).
"""
import json
import sys
from pathlib import Path

root = Path(r"C:\Users\satta\Downloads\koreanguy\traderlog")
LEDGER = root / "design" / "MODEL_WORK_LOG.jsonl"
REPORT = "design/handoffs/HANDOFF_UI_evidence_desk_completion_2026-08-23_COMPLETED.md"
D = "2026-08-23"

def rec(rid, wave, deliverable, role, model, host, basis, scope, files, status="completed", vs="verified", notes=""):
    return {
        "id": rid, "completed_at": D, "wave": wave, "deliverable": deliverable,
        "role": role, "model": model, "host_tool": host, "identity_basis": basis,
        "scope": scope, "files": files, "completion_report": REPORT,
        "status": status, "verification_status": vs, "notes_limitations": notes,
    }

F = "deepseek-v4-flash"
H_SUB = "DeepSeek Harness Desktop subagent"
H_MAIN = "DeepSeek Harness Desktop"

records = [
    rec("attr-w3d-shell-type-flash-executor-20260823-001", "W3d",
        "Slice A shell/type/hierarchy", "executor", F, H_SUB, "host_verified",
        "Raised 9-10px label tokens to an 11px floor, audited uppercase/mono usage to compact operational labels only, demoted the nested 2px .media-box to a 1px interior rule; preserved the 1680px grid and zero overflow.",
        ["ui/src/styles/tokens.css", "ui/src/styles/app.css"]),
    rec("attr-w3d-charts-flash-executor-20260823-001", "W3d",
        "Chart migration to the binding renderer ladder", "executor", F, H_SUB, "host_verified",
        "Replaced inline-SVG internals of all seven chart components with ECharts (PositionBars, Ribbon, SmallMultiples) and Vega-Lite (Dumbbell, StripPlot, BandLine, StackedStrip) behind the unchanged VISUAL_LANGUAGE section 6 contracts; tokens resolved at the adapter boundary; 11px label floor; compact empty blocks; responsive; no load animation.",
        ["ui/src/components/charts.jsx", "ui/package.json", "ui/package-lock.json", "ui/src/styles/app.css"]),
    rec("attr-w3d-feed-thumbs-flash-executor-20260823-001", "W3d",
        "Slice B FEED archived-image thumbnails", "executor", F, H_SUB, "host_verified",
        "Replaced the image-count text on FEED post cards with contained /api/media/{post_id}/{idx} thumbnails beside the extracted evidence, with per-image 404 fallback and preserved pagination/filters/spine/thread-unknown behavior.",
        ["ui/src/screens/Feed.jsx", "ui/src/styles/app.css"]),
    rec("attr-w3d-debrutalize-flash-executor-20260823-001", "W3d",
        "Slice A2 thorough de-brutalization", "executor", F, H_SUB, "host_verified",
        "Sentence-case headers across the shell and all six screens, de-banded panel heads, quiet 1px chips, desk KPI tiles to a ledger line, TRADERS hero grid to a lead card, BREADTH dials to one evidence block, FEED desk/panel count consistency fix.",
        ["ui/src/screens/Feed.jsx", "ui/src/screens/Breadth.jsx", "ui/src/screens/Traders.jsx", "ui/src/screens/Ideas.jsx", "ui/src/components/ui.jsx", "ui/src/styles/app.css"]),
    rec("attr-w3d-sparse-flash-executor-20260823-001", "W3d",
        "Slice C sparse/future-wave states", "executor", F, H_SUB, "host_verified",
        "Compact future-block explanatory states naming the upstream capability (W2/W4/W6) replacing framed empty charts on TRADERS/LEDGER/BREADTH/IDEAS/LIBRARY; no decorative placeholders.",
        ["ui/src/screens/Traders.jsx", "ui/src/screens/Ledger.jsx", "ui/src/screens/Breadth.jsx", "ui/src/screens/Ideas.jsx", "ui/src/screens/Library.jsx", "ui/src/styles/app.css"]),
    rec("attr-w3d-tests-flash-executor-20260823-001", "W3d",
        "Browser-evidence test extension (desktop only)", "executor", F, H_SUB, "host_verified",
        "Added 1920x1080 browser tests: FEED thumbnail containment, thread ancestry labels, six-tab screenshot evidence, zero-row compact-state coverage, real-shaped-data note; additive; 256 tests green; 375px mobile test untouched.",
        ["tests/test_pc_layout.py", "tests/test_browser_review.py"]),
    rec("attr-w1-roster14-flash-executor-20260823-001", "W1",
        "Strict importer 8 to 14 approved handles + atomic first-capture roster creation", "executor", F, H_SUB, "host_verified",
        "Extended APPROVED_HANDLES to the 14 owner-authorized handles and added apply-path roster creation (WATCH, is_mock=0, atomic activation via store_posts) with regression tests; identity/URL/media validation unchanged.",
        ["ingest/provisional_import.py", "tests/test_provisional_import.py"]),
    rec("attr-w1-corpus-import-flash-executor-20260823-001", "W1",
        "14-handle DevTools capture and strict production import", "executor", F, H_MAIN, "host_verified",
        "Captured posts and replies tabs through the read-only DevTools route from the owner's Chrome session (separate profile copy, debug port), archived-first import through the strict validator, avatar-URL hygiene, backups, PRAGMA integrity, run_checks: 251 new posts, 147 media, 10 new handles activated (453 posts, 14/14 fresh, 262 media files).",
        ["run_import_provisional.py", "ingest/provisional_import.py", "data/traderlog.db"],
        vs="verified",
        notes="iManasArora and VCPSwing did not receive new capture in the final throttled run; all new records import as relationship-unresolved (thread unknown) - no ancestry is synthesized."),
    rec("attr-w3d-leaderboard-flash-executor-20260823-001", "W3d",
        "IDEAS ticker leaderboard", "executor", F, H_SUB, "host_verified",
        "Client-side Ticker leaderboard panel (entered/holding/exited/mentioned-unresolved) over /api/positions + /api/ideas, click-through to LEDGER symbol filter, wireframe reconciled, empty-state copy.",
        ["ui/src/screens/Ideas.jsx", "ui/src/App.jsx", "ui/src/styles/app.css", "design/WIREFRAMES.md"]),
    rec("attr-w3d-redesign-flash-executor-20260823-001", "W3d",
        "Quiet editorial terminal redesign (owner-directed new direction)", "executor", F, H_SUB, "host_verified",
        "Rebuilt the aesthetic: warm-neutral canvas, soft near-black ink, 1px structural borders, one deep-blue accent, quiet chips/controls, underlined tab rail, sentence-case multi-word headers; all token names preserved; VISUAL_LANGUAGE.md reconciled; every data element, the evidence-desk spine, contracts and a11y kept.",
        ["ui/src/styles/tokens.css", "ui/src/styles/app.css", "ui/src/styles/thread.css", "ui/src/screens/Traders.jsx", "ui/src/screens/Breadth.jsx", "design/VISUAL_LANGUAGE.md"]),
    rec("attr-w2-classify-flash-executor-20260823-001", "W2",
        "Corpus classification via this chat (validated apply_verified_* path)", "executor", F, H_MAIN, "host_verified",
        "Classified ~365 corpus posts through classify.apply_verified_classification with citation discipline (kind/symbols literal in post text/play_type/conviction), source label deepseek-v4-flash-vision-exp (this chat report); per-kind outcomes incl. correct noise for non-trading content.",
        ["llm/classify.py", "data/traderlog.db"],
        vs="partial",
        notes="Vision transcription is BLOCKED: subagents run deepseek-v4-flash (no image input) and honestly wrote nothing; only the vision-capable session can read archived images, so post_media.vision_json for ~190 images remains pending (no unreadable:true guesses were written)."),
    rec("attr-w3d-orchestrator-flash-20260823-001", "W3d",
        "Evidence-desk wave orchestration and personal verification", "orchestrator", F, H_MAIN, "host_verified",
        "Read-first chain, slice briefs and boundaries, subagent implementation routing, DB backups, ingest operations, and personal verification of every completion claim: builds, 256-test full suite, run_checks, deterministic 1920x1080 DOM checks, live browser probes, corpus and integrity verification.",
        ["ui/src", "tests/test_pc_layout.py", "tests/test_browser_review.py", "ingest/provisional_import.py", "TASKS.md", "HANDOFF.md"]),
    rec("attr-w3d-review-v4pro-20260823-001", "W3d",
        "DeepSeek V4 Pro final review of the evidence-desk wave", "reviewer", "deepseek-v4-pro", "DeepSeek Harness Desktop (workflow override)", "host_verified",
        "Independent review-only audit: ran all five done-tests (build, 256 tests, run_checks, deterministic verify, screenshots), swept the owner complaint checklist (a-f) and found all GONE, verified contracts/palette/a11y, returned structured findings with zero blockers or majors (2 nits).",
        ["ui/src/styles/tokens.css", "ui/src/styles/app.css", "ui/src/styles/thread.css", "ui/src/components/ui.jsx", "ui/src/components/charts.jsx", "tests/test_pc_layout.py", "tests/test_browser_review.py"],
        vs="verified",
        notes="Rendered against the pre-redesign aesthetic; pixel-level appearance not verifiable (no image-capable reviewer); the follow-up redesign is reported separately and warrants an equivalent re-audit."),
]

existing = {json.loads(line)["id"] for line in LEDGER.read_text(encoding="utf-8").splitlines() if line.strip()}
dup = [r["id"] for r in records if r["id"] in existing]
if dup:
    print("DUPLICATE IDS:", dup); sys.exit(1)
with LEDGER.open("a", encoding="utf-8") as fh:
    for r in records:
        fh.write(json.dumps(r, ensure_ascii=False) + "\n")
print("appended:", len(records), "records; total now:", len(existing) + len(records))