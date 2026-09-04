# HANDOFF INS-1 Radar UI -- COMPLETED

## Outcome

Certain: replaced the visible IDEAS screen with the verified `/api/radar`-only
RADAR workspace. RADAR refetches for the requested 7/30/90-day and 2/3/4
distinct-trader controls, ranks only NSE-validated symbols, exposes source
evidence and coverage debt, and maps legacy `?tab=IDEAS` URLs to
`?tab=RADAR`. Themes and Setups are not rendered.

## Attribution

Attribution-ID: attr-ins1-radar-ui-executor-exact-model-unavailable-20260825-001

Attribution-ID: attr-ins1-radar-ui-review-correction-executor-exact-model-unavailable-20260825-001

Attribution-ID: attr-ins1-radar-ui-dead-code-cleanup-executor-exact-model-unavailable-20260825-001

Attribution-ID: attr-ins1-radar-ui-orchestrator-exact-model-unavailable-20260825-001

## Files changed

- `ui/src/App.jsx` -- registered RADAR navigation and the IDEAS-to-RADAR URL migration.
- `ui/src/api.js` -- added the named `fetchRadar(params)` client.
- `ui/src/screens/Radar.jsx` -- added the selected-symbol co-attention table and evidence rail.
- `ui/src/screens/Ideas.jsx` -- removed after route/import migration.
- `ui/src/styles/app.css` -- added Radar-only token-backed desktop layout and states.
- `tests/test_browser_radar.py` -- added disposable-DB behavior and 1920x1080 acceptance coverage.
- `tests/test_pc_layout.py` and `tests/test_browser_review.py` -- migrated only obsolete IDEAS tab expectations and Radar's required compact zero state, under orchestrator approval.
- `design/MODEL_WORK_LOG.jsonl` -- appended executor attribution.

## Verification

```text
Baseline
python traderlog/run_checks.py
exit 0 (118.1s)
wave W8 | 3360 posts | 3 positions | 0 in review | commit f617faaf
all checks OK: db, ingest, parse, golden, attribution, derive, ui; telegram disabled

Red test before implementation
pytest traderlog/tests/test_browser_radar.py -q
2 failed, 2 warnings in 20.09s
Both failures were the expected missing `.radar-workspace` timeout from the pre-Radar build.

Build
npm run build (traderlog/ui)
exit 0 (30.2s)
✓ 1250 modules transformed.
✓ built in 25.33s

Focused real-browser disposable-DB acceptance at exactly 1920x1080
pytest traderlog/tests/test_browser_radar.py traderlog/tests/test_pc_layout.py -q
9 passed, 2 warnings in 36.27s
The Radar tests assert: first-row selection, server refetches for controls,
exact evidence and source link, coverage debt, zero results, legacy IDEAS
migration, centered 1680px grid, no document/panel overflow, keyboard row
selection, zero browser console errors/warnings, and zero HTTP responses >=400.

Full suite
pytest traderlog/tests -q
284 passed, 2 warnings in 96.32s

Final generated checks
python traderlog/run_checks.py
exit 0 (132.3s)
OK attribution W0 48 records, 11 completed handoffs
wave W8 | 3360 posts | 3 positions | 0 in review | commit f617faaf
STATE.json updated. No failures.

Owned-file whitespace check
git diff --check -- <owned tracked files>
git diff --no-index --check -- NUL <each owned new file>
exit 0
The command emitted only Windows LF-to-CRLF working-copy notices.
```

## Honest partials

- The Vite build emits its existing Rollup advisory for a minified chunk over
  500 kB. The build exits 0; the 1920x1080 browser acceptance asserts zero
  runtime console warnings and errors.
- Classifier source-symbol precision is not established by NSE ticker validation;
  the UI exposes coverage debt but cannot detect every semantically wrong ticker.

## Review correction

Certain: corrected the review findings without expanding the handoff scope.

```text
Red focus regression
pytest traderlog/tests/test_browser_radar.py -q
1 failed, 1 passed, 2 warnings in 11.54s
The failure proved ArrowDown selected the adjacent row but left focus on the old button.

Correction build
npm run build (traderlog/ui)
exit 0 (35.2s)
✓ 1250 modules transformed.
✓ built in 29.37s

Focused real-browser disposable-DB verification at exactly 1920x1080
pytest traderlog/tests/test_browser_radar.py traderlog/tests/test_pc_layout.py -q
9 passed, 2 warnings in 30.65s
The Radar acceptance now asserts focus follows ArrowDown and returns on ArrowUp.

Scoped whitespace check runs after this report and attribution correction.
```

The selected row now uses a 1px token-backed border, and the removed
`fetchIdeas` client and request noun leave the legacy backend endpoint untouched.

## Dead CSS cleanup correction

Certain: removed only selectors exclusive to the deleted Ideas screen:
`.idea-*`, `.mention`, `.followthrough`, `.ticker-board*`, and `.ticker-row`.
Shared styles such as `metric-row` and Chip styling remain untouched.

```text
Build
npm run build (traderlog/ui)
exit 0 (16.5s)
✓ 1250 modules transformed.
✓ built in 14.20s

Focused real-browser disposable-DB verification at exactly 1920x1080
pytest traderlog/tests/test_browser_radar.py traderlog/tests/test_pc_layout.py -q
9 passed, 2 warnings in 24.91s

Stale-selector search and scoped whitespace check run after this correction record.
```

## Orchestrator verification

The orchestrator independently reviewed tests before implementation, inspected
the live DOM and screenshot, and rejected three issues before acceptance: a
banned 2px selected-row border, arrow selection without focus movement, and dead
Ideas client/CSS artifacts. Terra corrected each issue and added focus regression
coverage.

The final root probe served the real production database read-only in isolated
Chromium at exactly 1920x1080. It observed FCL and DATAPATTNS as the two default
ranked rows, moved selection and DOM focus from FCL to DATAPATTNS with ArrowDown,
refetched `/api/radar` for 7 days and 3 traders, and rendered the compact zero
state. Measurements: page width 1680px at x=120, document/body width 1920px,
zero overflowing Radar regions, zero console errors/warnings, zero failed
requests, and zero HTTP responses >=400. Screenshots:

- `output/playwright/traderlog-radar-root-1920-workspace.png`
- `output/playwright/traderlog-radar-root-1920.png`
