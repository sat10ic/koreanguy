# HANDOFF — de-wonk recovery Waves B/C/D (Gemini)

Repo `C:\Users\satta\Downloads\koreanguy`, branch `emergent`. You have repo access. Do NOT git
commit — the maintainer QCs + commits. Never print the rupee glyph to console (use "Rs").

## Context (read these first)
Multiple LLMs edited the desk and left it visually broken; a maintainer already ran 6 per-panel
audits and fixed the global root. READ: `manas_os/design/UI_CORRECTION_PLAN.md` (the ordered plan)
+ the 6 ledgers `manas_os/design/audit/AUDIT_*.md` (file:line evidence). WAVE A is already done +
committed: `desk/src/styles/compat-backfill.css` restored the orphaned tokens (`--gap-*`,
`--radius-*`, `--v5-red-ink/-green-ink/-amber-dim`, `--v5-paper/-blue/-blue-wash/-rule/-serif`).
Do NOT remove that file yet. The build is clean; this is CSS/runtime cleanup, not compile fixes.

## HARD RULES (this whole mess came from breaking them)
- Do NOT edit `tokens.v5.css`, `compat-backfill.css`, `App.css`, or any `components/v5/*` shared
  primitive UNLESS a fix below explicitly names it — and if you do, change ONLY the exact lines
  named. No re-theming, no bulk restyle, no touching the design system.
- Money-math / gates / one-writer untouched. Real data + honest states. `.v5`-scoped, tokens only
  (no new raw hex). a11y AA. Reduced-motion respected.
- Reproduce each defect on the running desk BEFORE fixing; paste REAL before/after DOM/console
  evidence in the completion file. No "simulated" proofs.

## WAVE B — real crashes / broken components (P0, do first, in order)
1. **TradePlanTab.jsx** — `handleLogTaken` (~line 462) reads `sizer`/`plan` before they are
   declared (~lines 555-556) → runtime crash / TDZ when the user logs a TAKEN decision. Move the
   `sizer`/`plan` derivation ABOVE the handler. Verify: click "log TAKEN" on a real symbol, no crash,
   journal row written.
2. **DebateLivePanel.jsx** — 7 CSS classes referenced but undefined (`.v5-live-dot`,
   `.v5-live-kicker`, `.alpha-explain`, `.v5-debate-live-status`, `.v5-debate-live-stages`,
   `.v5-debate-live-seats`, `.v5-seat-body`) → the live-debate panel collapses. Add the rules in a
   new `desk/src/components/v5/DebateLivePanel.v5.css` (import it from DebateLivePanel.jsx),
   `.v5`-scoped, tokens only. Match the v5 look (see DebateTab.v5.css for the idiom). Verify the
   panel renders during an on-demand debate.
3. **MarketTab.jsx** — legacy component: imports NO css and uses 30+ undefined `.mkt-*` /
   `.ledger-table` classes (UI-7 deleted them). FIRST determine if it's still mounted: grep App.jsx
   for `MarketTab`. IF mounted → recover its CSS block from git (`git log -p -- manas_os/desk/src/App.css`
   or an earlier commit, find the `.mkt-*` rules) into a new `MarketTab.v5.css` migrated to v5
   tokens, and import it; IF NOT mounted anywhere → delete MarketTab.jsx (dead code). State which
   you found + did. Verify MARKET tab renders fully (it also has MarketHomeTab — don't break that).
4. **PositionsTab.jsx** (~line 502) — the close-modal doesn't reset its form on cancel/close, so the
   previous trade's exit price leaks into the next position's modal. Reset modal form state on
   open AND on cancel/close. Verify: open close-modal on position A, cancel, open on position B →
   fields are blank/defaulted, not A's values.
5. **LedgerTab.jsx** (~line 192) — the R-bar fill passes a CSS-variable STRING as an inline JS
   style value where a computed value is required → bars render transparent. Fix so the fill color
   actually applies (use a className + CSS, or a resolved color). Verify: closed trades show
   green/red R bars.

## WAVE C — per-panel residue (P1/P2)
6. **Dark-island hovers**: `App.css:653` `.activity-row:hover { background:#1f1f1f }` (and any other
   hardcoded `#1f1f1f`/dark hex hover found via grep) → `var(--v5-panel-2)`. (This is an explicitly
   named App.css line — the ONLY App.css edit allowed.)
7. **ScannersTab.jsx**: builder path calls `ResultList` WITHOUT `isLoading` (~line 649) → spinner +
   rows at once; `.scn-result-list` has no max-height (results render far offscreen); the preset
   hit-count fetch has no timeout (stuck "-") and there are ~5 duplicate `/api/scanners/presets`
   fetches. Fix: pass `isLoading`; add a max-height + scroll to the result list; render preset
   DEFINITIONS instantly with a "loading N scans…" state and lazy/async or timeout-guarded counts;
   dedupe the fetch (fetch once, cache). Verify on a real-data date: presets render <1s, counts
   fill in, results are on-screen, never a blank tab.
8. **ShortlistTab.jsx** (~line 191) — `chair_verdict==="TAKE" ? "Active:" : "Waiting on:"` shows
   "Waiting on:" even when the verdict is null/unrecorded, and can contradict the verdict chip.
   Add an explicit pending-vs-unrecorded state; ensure the row verdict + the "waiting on" line come
   from ONE current source (no stale line beside a fresh chip).
9. **TradePlanTab.v5.css:347** — `gap: var(--v5-r-sm)` uses a RADIUS token for spacing →
   `var(--gap-s)`.
10. **rgba/token purity (P2, cosmetic — do only if time)**: tokenize the raw rgba borders/backdrops
    in `DebateTab.v5.css` (797/801/805), `PositionsTab.v5.css` (7 borders), `LedgerTab.v5.css`
    (9 borders + modal backdrop 598), `App.css` glows (46/227). Use existing `--v5-*` washes; do
    NOT invent new colors.

## WAVE D — verify + finish
- `cd manas_os/desk && npm run build` clean + `npx vitest run` green; `python -m pytest manas_os/tests -q`
  unchanged (this is desk-only; if you touch any .py, flag it).
- Restart API (`python run_manas_api.py`) + `npm run dev`; DOM-drive ALL 7 tabs + ALPHA + ChartDrawer
  on real 2026-07-10 data: spacing/colors/fonts render, no console errors, the Wave-B crashes gone.
- Do NOT delete `compat-backfill.css` in this handoff (migrating every consumer to canonical token
  names is a separate later cleanup — leave a note listing the remaining `--gap-*`/`--v5-paper` etc.
  consumers if you can, but don't do the migration now).

## Output
`HANDOFF_GEMINI_dewonk_BCD_COMPLETED.md`: per-item reproduce→fix with REAL before/after DOM/console
evidence, files changed, the MarketTab mounted-or-dead decision, build/test results, anything
deferred. No simulated proofs.
