# HANDOFF W3c — 1920×1080 PC UI recovery

## Goal

Rebuild TraderLog's desktop shell, FEED, and LEDGER into a deliberate
evidence-first trading-intelligence workspace at **1920×1080**, fixing the
proven Ledger media overflow and the current left-anchored, under-used PC
layout without changing data meaning or backend behavior.

This is an implementation handoff. Do the work yourself; do **not** spawn
further agents or delegate any part of it.

## Read before planning or editing

Read these files completely, in this exact order:

1. `traderlog/AGENTS.md`
2. `traderlog/CANONICAL.md`
3. `traderlog/STATE.json`
4. `traderlog/HANDOFF.md`
5. `traderlog/TASKS.md`
6. `traderlog/design/CONTRACTS.md`
7. `traderlog/design/VISUAL_LANGUAGE.md`
8. `traderlog/design/WIREFRAMES.md`
9. this file

Inspect the live instance before editing. The only visual acceptance viewport
for this handoff is **1920×1080**. Do not substitute mobile, tablet, laptop, or
multi-viewport findings for the requested PC work.

Run before the first edit:

```text
python traderlog/run_checks.py
```

Expected baseline on 2026-08-23: 25 tables, 12 real posts, 3 cited positions,
0 open review items, 8 attribution records, 3 completed handoffs, and no check
failures. If the shared worktree has moved, report the actual baseline rather
than forcing these numbers.

## Owner decisions that bind this work

- **PC-only audit and acceptance:** 1920×1080.
- The current result is visually rejected. Do not treat the existing
  neo-brutalist implementation as accepted merely because it follows the old
  prose literally.
- Avoid generic AI-dashboard styling: no soft KPI-card grid, gradient, glow,
  glass, neon, purple, gratuitous icons, fake charts, decorative animation, or
  filler metrics.
- The replacement direction is an **evidence desk**: part exchange blotter,
  part research notebook. Thread, event, chart evidence, and citation are the
  visual grammar.
- Keep the application light and information-dense, but density must come from
  useful comparison and hierarchy, not 12px text packed into bordered boxes.
- X ingestion remains paused. Do not import or modify the provisional 30-day
  capture.
- Production remains real-data-only. Do not seed mock data.
- Do not commit.

## Evidence from the verified 1920×1080 audit

These are measured defects, not design opinions:

1. `.page` is 1240px wide and left anchored at x=0, leaving 680px of the 1920px
   viewport unused while navigation sits at the far-right edge. The header and
   content use different horizontal grids.
2. Body text computes to 12px.
3. FEED panels are 1188px wide, but primary post copy is approximately 507px
   wide, producing a small text island and a large unused field.
4. Expanding RATEGAIN in LEDGER renders one archived image 1709px wide from
   x=994 to x=2703. The 1188px detail panel then has `scrollWidth=2675` and
   clips evidence because `.panel` uses `overflow:hidden` and `.media-box img`
   has no containment rule.
5. STYLE is exposed beside the six product tabs despite describing itself as a
   non-product reference screen.
6. Empty framed charts dominate other screens. They are regression surfaces
   only here; do not redesign those screens in this handoff.

Verified before screenshots:

- `output/playwright/traderlog-pc-audit/feed-1920x1080.png`
- `output/playwright/traderlog-pc-audit/ledger-1920x1080.png`
- `output/playwright/traderlog-pc-audit/ledger-expanded-1920x1080.png`

## Files you own

Implementation:

- `traderlog/ui/src/App.jsx`
- `traderlog/ui/src/components/ui.jsx`
- `traderlog/ui/src/screens/Feed.jsx`
- `traderlog/ui/src/screens/Ledger.jsx`
- `traderlog/ui/src/styles/app.css`
- `traderlog/ui/src/styles/thread.css`
- `traderlog/ui/src/styles/tokens.css`

Verification:

- `traderlog/tests/test_browser_review.py`
- `traderlog/tests/test_pc_layout.py` (new, if cleaner than extending the
  existing browser test)

Specifications and completion records:

- `traderlog/design/VISUAL_LANGUAGE.md`
- `traderlog/design/WIREFRAMES.md`
- `traderlog/TASKS.md`
- `traderlog/HANDOFF.md`
- `traderlog/design/MODEL_WORK_LOG.jsonl` (append only)
- `traderlog/design/handoffs/HANDOFF_W3c_pc_ui_recovery_COMPLETED.md` (new)

Do not edit outside this list. Preserve unrelated work in the shared worktree.

## Files and systems you must not touch

- Everything under `traderlog/ingest/`, `traderlog/llm/`, `traderlog/api/`,
  `traderlog/db/`, `traderlog/data/`, and `traderlog/adopted/`
- `traderlog/ui/src/components/charts.jsx`
- `traderlog/ui/src/screens/Traders.jsx`
- `traderlog/ui/src/screens/Breadth.jsx`
- `traderlog/ui/src/screens/Ideas.jsx`
- `traderlog/ui/src/screens/Library.jsx`
- `traderlog/ui/src/screens/Style.jsx`
- `traderlog/ui/package.json` and lockfiles; add no dependency
- Everything under `manas_os/`
- The production database and provisional Chrome capture

No API or JSON contract changes are authorized. If the desired UI appears to
need one, stop and record the gap under `## Honest partials`; do not invent a
field or a second data writer.

## Required implementation

### 1. Reconcile the binding design docs first

Update `VISUAL_LANGUAGE.md` and the FEED/LEDGER sections of `WIREFRAMES.md`
before CSS/JSX. Preserve the renderer ladder and truth/evidence rules. Replace
conflicting clauses that require 11–12px body copy or make every subsection a
heavy 2px box.

The revised desktop rules must state:

- a centered **1680px content grid** at 1920×1080 (120px left and right);
- header contents align to the same 1680px grid;
- normal reading copy is 14–15px; 11–12px is metadata only;
- uppercase is for structural micro-labels, not every sentence;
- 2px borders define major regions; 1px rules may separate rows and evidence;
- mono is for numbers, dates, confidence, and identifiers, not prose;
- colour remains state- or interaction-bearing, never decoration.

### 2. Repair the shell and navigation

- Center the application on the 1680px grid. Do not leave the current 680px
  blank right field.
- Align brand, navigation, lede, filters, and content to one horizontal system.
- Visible production navigation contains exactly FEED, TRADERS, LEDGER,
  BREADTH, IDEAS, and LIBRARY.
- Remove STYLE from visible navigation. It may remain directly reachable via
  `?tab=STYLE`; preserve the component and do not delete its code.
- Preserve deep-linkable `?tab=` behavior for all six product tabs.

### 3. Recompose FEED as the evidence desk

- Use the 1680px width deliberately. A two-column composition is expected: the
  thread/feed workspace is primary; filters and compact operating context form
  the secondary rail.
- The review queue, when non-empty, remains above posts in the primary
  workspace. Do not hide or demote work owed by the human.
- Make the reply/thread rail the signature visual element. Root posts and
  self-replies must scan as one conversation without nested-card clutter.
- Keep prose at a readable measure, but do not repeat the current 507px island
  inside a 1188px panel.
- Preserve every current filter, unclassified handling, confidence,
  unresolved behavior, evidence disclosure, media count, deletion treatment,
  source link, and review action.
- Long unresolved copy must not dominate the row. Show a short truthful
  summary/count and keep the complete text accessible through disclosure. Do
  not drop or paraphrase evidence.

### 4. Repair and clarify LEDGER

- Keep the shared-axis timeline and sortable table; do not replace either with
  generic cards.
- Compress each table's unresolved row to a truthful indicator such as
  `3 unresolved`; show full strings in expanded detail.
- Expanded detail uses a robust grid with `min-width:0` on shrinkable tracks.
  The event/citation column is primary and the media/evidence column is
  predictable, approximately 440–500px at this viewport.
- Every archived image must obey its container:
  `display:block; width:100%; max-width:100%; height:auto; object-fit:contain`
  or an equivalent tested rule. Intrinsic dimensions must never enlarge the
  grid or panel.
- Evidence stays visible on expansion; it is not optional and not hidden
  behind another toggle.
- Preserve all current position details and media. Do not reinterpret any
  extracted number.

### 5. Remove unfinished-product theatre from this slice

- Add no placeholder metrics, decorative charts, or synthetic examples.
- FEED and LEDGER must look complete with 12 posts and 3 positions.
- Other screens stay outside implementation scope. The shared shell may improve
  them incidentally; do not edit their screen files.

## Functional behavior that must remain green

- FEED trader/kind/confidence filters, unresolved toggle, and unclassified filter
- Review accept/reject pending and error behavior
- LEDGER trader/status/symbol/confidence filters and sortable columns
- LEDGER disclosure open/close for all three current positions
- Direct source links and real media rendering
- `?tab=` deep links and browser refresh
- Zero mock rows in production

## 1920×1080 visual done-test

Use a real browser at exactly 1920×1080 against the served production bundle at
`http://127.0.0.1:8100`. Build before inspecting; do not mistake source changes
for served changes.

Capture after screenshots:

- `output/playwright/traderlog-pc-recovery/feed-after-1920x1080.png`
- `output/playwright/traderlog-pc-recovery/ledger-after-1920x1080.png`
- `output/playwright/traderlog-pc-recovery/ledger-rategain-expanded-after-1920x1080.png`
- one expanded screenshot for Fastzonetrader FCL
- one expanded screenshot for VCPSwing FCL
- `output/playwright/traderlog-pc-recovery/traders-shell-regression-1920x1080.png`

Measure and include in the completion report:

1. Viewport is exactly 1920×1080.
2. Shared content grid is 1680px and centered at x=120.
3. `document.documentElement.scrollWidth === 1920` on FEED, LEDGER, and each
   expanded LEDGER detail.
4. Every `.panel` satisfies `scrollWidth <= clientWidth + 1`.
5. No rendered image has `left < 0` or `right > 1920`.
6. Every `.media-box img` is no wider than its containing `.media-box`.
7. STYLE is absent from visible navigation; the direct development route still
   renders if retained.
8. Browser console has zero errors and zero warnings.
9. Relevant API requests return 200.
10. FEED filters, LEDGER sorting, and all three disclosure rows work.

Do not report document width alone as proof: the old `overflow:hidden` masked a
2675px child while the document still measured 1920. Panel and image
containment checks are mandatory.

## Command done-test

From the repository root:

```text
cd traderlog/ui
npm run build
cd ../..
pytest traderlog/tests/test_browser_review.py traderlog/tests/test_pc_layout.py -q
pytest traderlog/tests -q
python traderlog/run_checks.py
git diff --check -- traderlog
```

If `test_pc_layout.py` is not created, omit only that path from the focused
command and explain why its assertions live in `test_browser_review.py`. Final
checks must pass. Existing uvicorn/websockets deprecation warnings may be
reported honestly; new browser console warnings are not acceptable.

## Completion and attribution

Do not commit.

Write:

`traderlog/design/handoffs/HANDOFF_W3c_pc_ui_recovery_COMPLETED.md`

Use `COMPLETION_TEMPLATE.md`. Append one executor record to
`traderlog/design/MODEL_WORK_LOG.jsonl` before closing and put its exact
`Attribution-ID:` in the completion report. Record only documented identity;
use `unknown` or `exact-model-unavailable` rather than guessing. Leave the
orchestrator verification record for the reviewing model after it personally
repeats the browser and command done-tests.

The report must include:

- exact files changed;
- before/after geometry for page grid and expanded RATEGAIN media;
- screenshot paths;
- commands and verbatim pass/fail totals;
- unverified behavior under `## Honest partials`;
- confirmation that no ingestion, database, API, LLM, W4, or `manas_os` file
  was touched.
