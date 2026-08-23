# HANDOFF W3c PC UI recovery -- COMPLETED

## Outcome

The desktop shell, FEED, and LEDGER are rebuilt as the evidence desk at
1920×1080, and every measured defect from the audit is repaired. All ten
visual done-test items pass at exactly 1920×1080 against the served
production bundle; all command done-tests pass. No data meaning, API contract,
or backend behavior changed.

Measured before → after (real browser, production bundle at 127.0.0.1:8100):

| Measurement | Before | After |
|---|---|---|
| `.page` geometry | 1240px wide at x=0 (680px dead right field) | 1680px wide at x=120, header on the same grid |
| Body reading copy | 12px | 14px |
| FEED composition | 507px post-text island inside an 1188px panel | primary ~1216px workspace + 400px rail (filters, traders, desk counts); prose at ~62ch with strips/meta full width |
| LEDGER RATEGAIN expanded image | rendered 1709px, x=994→right 2703; panel scrollWidth 2675 vs clientWidth 1184 (clipped by `overflow:hidden`) | rendered at media-box width; panel scrollWidth == clientWidth; `document.scrollWidth === 1920` |
| Navigation | 7 tabs including STYLE | exactly the six product tabs; `?tab=STYLE` still renders |
| Console at 1920 | clean | clean (zero errors, zero warnings, zero ≥400 responses) |

Other delivered items: the thread spine is the signature element (2px rule
down each conversation); long unresolved copy shows as `N unresolved ▾` with
the complete strings expanding on disclosure (FEED) and `⚠ N unresolved` count
in the collapsed LEDGER table with full strings in expanded detail; the
expanded detail is a robust grid (`minmax(0,1fr)` + fixed 460px media column,
`min-width:0`, contained images) with evidence always visible.

## Attribution

Attribution-ID: attr-w3c-pcui-glm53-executor-20260823-001

Attribution-ID: attr-w3c-pcui-glm53-executor-20260823-002

Implementation was executed directly by GLM 5.3 via ZCode under the handoff's
explicit "do the work yourself; do not spawn further agents" instruction. The
orchestrator verification record is deliberately **not** appended: the handoff
assigns it to the reviewing model after it personally repeats the browser and
command done-tests.

## Files changed

- `traderlog/design/VISUAL_LANGUAGE.md` -- §1a desktop composition rules
  (1680px grid, 14–15px reading copy / 11–12px metadata, 2px-major/1px-interior
  borders, mono-identifiers); conflicting Required/§4/§5 clauses replaced;
  evidence-desk revision recorded.
- `traderlog/design/WIREFRAMES.md` -- shell ASCII (six product tabs, STYLE dev
  route, 1680 grid note); FEED section rewritten as the two-column evidence
  desk with rail provenance and unresolved-disclosure contract; LEDGER section
  gains the W3c containment rules and unresolved-indicator element.
- `traderlog/ui/src/styles/tokens.css` -- W3c type scale (`--fs-body` 14px,
  `--fs-ui` 12px metadata, `--fs-val` 16px), `--w-content: 1680px`, 1.45
  reading line-height.
- `traderlog/ui/src/styles/app.css` -- centered shell (`.topbar-in`, `.page`
  1680 centered), feed-layout/rail/desk classes, `.post-text` 62ch measure,
  1px event-strip border, unresolved toggle styles, `.detail-grid`
  containment track rules, `.media-box img` containment rule.
- `traderlog/ui/src/styles/thread.css` -- the spine as signature element: 2px
  structural rule on roots and replies, capped on the last reply.
- `traderlog/ui/src/App.jsx` -- `NAV_TABS` (six product tabs) vs `ALL_TABS`
  (STYLE routed, not navigated); header contents wrapped in `.topbar-in`.
- `traderlog/ui/src/screens/Feed.jsx` -- two-column evidence-desk composition
  (review queue + posts primary; filters/traders/desk rail); unresolved
  count + inline disclosure. Every existing filter and behavior preserved.
- `traderlog/ui/src/screens/Ledger.jsx` -- collapsed-table unresolved
  indicator (`⚠ N unresolved`); full strings remain in expanded detail.
- `traderlog/tests/test_pc_layout.py` -- NEW: 1920×1080 real-browser tests
  (centered grid + six tabs + 14px copy + rail; STYLE route outside nav;
  expanded-media containment against the real 1709px archived image served
  read-only through `/api/media`; console clean).

Not modified (owned but unneeded): `ui/src/components/ui.jsx`,
`tests/test_browser_review.py` (last changed by the W3 producer slice).

## Verification

Baseline before edits (shared worktree had moved past the handoff's expected
numbers, reported per instructions): `run_checks.py` exit 0 with **9
attribution records** (handoff expected 8), 3 completed handoffs, 12 posts,
3 positions, 0 review rows, no check failures.

```text
$ cd traderlog/ui && npm run build
built in 2.46s (css 19.71 kB, js 195.77 kB)

$ python -m pytest traderlog/tests/test_browser_review.py traderlog/tests/test_pc_layout.py -q
9 passed, 2 warnings in 25.80s

$ python -m pytest traderlog/tests -q
175 passed, 2 warnings in 44.64s

$ python traderlog/run_checks.py
STATE.json updated. No failures. (attribution check green)

$ git diff --check -- traderlog
clean
```

1920×1080 visual done-test, personally measured in a real browser against the
served production bundle:

1. Viewport exactly 1920×1080 (Playwright context).
2. `.page` 1680px at x=120 on FEED, LEDGER, TRADERS, and every expanded detail.
3. `document.documentElement.scrollWidth === 1920` on FEED, LEDGER, and each
   expanded LEDGER detail (all three positions expanded and measured).
4. Every `.panel` satisfies `scrollWidth <= clientWidth + 1` (zero exceptions,
   including RATEGAIN expanded).
5. No rendered image has `left < 0` or `right > 1920` (zero exceptions).
6. Every `.media-box img` renders at or below its `.media-box` clientWidth;
   the 1709px-intrinsic image renders contained (also asserted as a permanent
   regression test in `test_pc_layout.py`).
7. Visible navigation is exactly FEED, TRADERS, LEDGER, BREADTH, IDEAS,
   LIBRARY; `?tab=STYLE` renders.
8. Zero console errors and zero console warnings across FEED, LEDGER,
   TRADERS, and STYLE loads.
9. Zero ≥400 API responses.
10. FEED kind filter works (trade_event → 2 posts); LEDGER symbol sort works;
    all three disclosures open and close.

After screenshots (all at exactly 1920×1080):

- `output/playwright/traderlog-pc-recovery/feed-after-1920x1080.png`
- `output/playwright/traderlog-pc-recovery/ledger-after-1920x1080.png`
- `output/playwright/traderlog-pc-recovery/ledger-rategain-expanded-after-1920x1080.png`
- `output/playwright/traderlog-pc-recovery/ledger-fastzonetrader-fcl-expanded-1920x1080.png`
- `output/playwright/traderlog-pc-recovery/ledger-vcpswing-fcl-expanded-1920x1080.png`
- `output/playwright/traderlog-pc-recovery/traders-shell-regression-1920x1080.png`

Before state reproduced from the audit's evidence and re-measured live before
editing: `output/playwright/traderlog-pc-audit/` (feed, ledger,
ledger-expanded at 1920×1080).

## Honest partials

- Orchestrator verification is open by design: the reviewing model must
  personally repeat the browser and command done-tests and append its own
  ledger record; this report's executor verification does not close that.
- TRADERS, BREADTH, IDEAS, LIBRARY, and STYLE screens received only incidental
  shell benefits (centered grid, type scale). Their own compositions at
  1920×1080 are outside this handoff and unaudited; the audit's defect #6
  (empty framed charts dominating) is noted as a regression surface only.
- The 375×812 path is exercised only by the existing no-overflow browser test;
  mobile was explicitly not an acceptance viewport for this handoff.
- The two pytest warnings are the pre-existing uvicorn/websockets
  deprecations from threaded serving (reported honestly, not browser
  console warnings).
- The desk rail's counts are computed client-side over the loaded feed page
  (posts shown / threads / events joined); they describe the page, not the
  corpus, and are labeled as "shown".

No file under `traderlog/ingest/`, `traderlog/llm/`, `traderlog/api/`,
`traderlog/db/`, `traderlog/data/` (production database never opened; one
archived media file served read-only), `traderlog/adopted/`, no W4 file, and
nothing under `manas_os/` was touched. Not committed.
