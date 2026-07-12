# UI CORRECTION PLAN — de-wonk recovery (2026-07-12)

Multiple LLMs edited the desk (all UNCOMMITTED) and left it visually broken. 6 Haiku per-panel
audits (`manas_os/design/audit/AUDIT_*.md`) + maintainer verification pinned it to ONE dominant
root + per-panel residue. It BUILDS clean — this is CSS/runtime, not compile errors. Fix-forward
(the churn contains real work — the guided system, legend, etc. — do NOT wholesale-revert).

## Root cause (verified)
The "single-theme cleanup" DELETED `src/tokens.css` but did not finish migrating its tokens.
`--gap-*` (32 uses), `--radius-*`, and several `--v5-*` names were left undefined → spacing
collapses, AlphaLab/verdict chips lose color/font. Fonts + routing verified FINE.

## WAVE A — global token backfill ✅ DONE (commit this)
`desk/src/styles/compat-backfill.css` (imported after tokens.v5.css in main.jsx): restores
`--gap-*`/`--radius-*` as theme-neutral literals + aliases `--v5-red-ink/-green-ink/-amber-dim`,
`--v5-paper/-blue/-blue-wash/-rule/-serif` to existing LIGHT tokens. One file → un-breaks spacing,
AlphaLab, and debate verdict chips at once. Build clean. (Delete the file once consumers migrate to
canonical v5 names — tracked as a WAVE C cleanup.)

## WAVE B — real crashes / broken components (P0, do next)
| # | File:line | Defect | Fix |
|---|---|---|---|
| B1 | TradePlanTab.jsx ~462 vs 555 | `sizer`/`plan` used in `handleLogTaken` BEFORE declaration → runtime crash on "log TAKEN" | move the `sizer`/`plan` destructure above the handler (TDZ) |
| B2 | DebateLivePanel.jsx | 7 undefined CSS classes (`.v5-live-dot`, `.v5-live-kicker`, `.alpha-explain`, `.v5-debate-live-status/-stages/-seats`, `.v5-seat-body`) → live-debate panel collapses | add the missing rules (new `DebateLivePanel.v5.css` or into DebateTab.v5.css), `.v5`-scoped, tokens only |
| B3 | MarketTab.jsx | legacy component: NO css import + 30+ undefined `.mkt-*`/`.ledger-table` classes (UI-7 deleted them) | FIRST check if MarketTab is still mounted (grep App.jsx). If yes → restore `.mkt-*` CSS (recover from `git show HEAD~N:...App.css`) + add import; if dead → delete the component |
| B4 | PositionsTab.jsx ~502 | close-modal cancel doesn't reset form → previous trade's exit price reused on next position | reset modal form state on open/cancel/close |
| B5 | LedgerTab.jsx ~192 | R-bar fill passes a CSS-var STRING as an inline JS value → transparent bars | use a className or a resolved value, not `style={{...'var(--x)'}}` where a computed value is required |

## WAVE C — per-panel residue (P1/P2)
- C1 dark-island hardcoded `#1f1f1f` hovers (App.css:653 `.activity-row:hover`) → `var(--v5-panel-2)`.
- C2 ScannersTab: builder `ResultList` missing `isLoading` prop (line ~649); `.scn-result-list`
  no max-height + 50ms scrollIntoView jank; hit-count fetch no timeout (stuck "-"). → loading state +
  max-height + lazy/timeout counts (folds in the earlier scanners-empty fix8).
- C3 ShortlistTab ~191: `chair_verdict==="TAKE" ? "Active:" : "Waiting on:"` defaults null → "Waiting
  on"; add explicit pending-vs-unrecorded state (also the stale-verdict-vs-line one-opinion issue).
- C4 rgba/token purity: App.css cyan/amber glows (lines 46/227), DebateTab.v5.css (797/801/805),
  PositionsTab.v5.css (7 borders), LedgerTab.v5.css (9 borders + modal backdrop 598) → tokenize;
  low priority / cosmetic.
- C5 TradePlanTab.v5.css:347 `gap: var(--v5-r-sm)` uses a RADIUS token for spacing → `--gap-s`.
- C6 migrate consumers off the legacy `--gap-*`/`--radius-*` + the `--v5-*` aliases onto canonical
  names, then DELETE compat-backfill.css.

## WAVE D — verify + commit
Restart API (`run_manas_api.py`) + desk (`npm run dev`), drive each of the 7 panels + ALPHA +
ChartDrawer on real 2026-07-10 data (DOM/text check), confirm spacing/color/fonts render and the
B-wave crashes are gone. Commit as one "de-wonk recovery" set. Then re-run the guided-system
punch-list (#13) that was pending before this broke.

## Execution note
Wave A is committed. Waves B-D are ~10 concrete grounded fixes — do inline or as ONE Gemini handoff
(reference this file + the AUDIT_*.md ledgers). Do NOT let another LLM touch shared token/App.css
files without the maintainer wiring — that's what caused this.
