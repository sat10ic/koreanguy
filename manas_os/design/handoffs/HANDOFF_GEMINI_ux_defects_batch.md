# HANDOFF 11 — UX defects batch (from the comprehensive audit) (Gemini)

Repo `C:\Users\satta\Downloads\koreanguy`, branch `emergent`. Standing rules: HANDOFF_INDEX.md.
Concrete P1/P2 defects from `manas_os/design/UX_AUDIT_FULL.md` (read the full ledger for evidence).
REPRODUCE each on the live desk (real 2026-07-10 data) BEFORE fixing; paste real before/after DOM.

## Fixes
1. **SHORTLIST verdict contradiction** (one-opinion violation, P0-ish): rows show a "WAITING ON"
   line that contradicts the verdict chip (e.g. LENSKART shows TAKE chip + yesterday's gate-failure
   text; KTKBANK SKIP chip + "chair verdict TAKE conviction 4"). Make the row's verdict/state and
   the waiting-on line come from ONE current source; never show a stale reason next to a fresh
   verdict. Fix in ShortlistTab + the watchlist payload if the field is stale.
2. **JOURNAL delete** (quick win): `DELETE /api/journal/{trade_id}` exists (app.py:3352), no UI.
   Add a delete affordance per trade (confirm inline, reversible-toast if feasible) so the HUDCO
   test entry can be removed. Every trade deletable, not just some.
3. **POSITIONS debug leak + freshness**: the `TelegramMirror` renders "dry-run: shown, not sent"
   raw status to the user — reword to a plain user-facing line (or hide in beginner mode). The
   live price ("NOW 207.0") has NO freshness/source marker while Fyers is disconnected — add a
   source+age chip (e.g. "last close" / "live 12:31" / "feed down"). Never show a bare number that
   looks live when it isn't.
4. **SCANNERS results offscreen**: clicking a preset renders results ~7000px below the fold with no
   scroll/feedback; also ~5 duplicate `/api/scanners/presets` fetches on load. Scroll-to / reveal
   the results with a loading state on click; dedupe the fetch (fetch once, cache).
5. **Date scrubber dead-ends**: stepping the date walks into "No run yet" empty days with no way
   back to the latest run. Add a date picker + a "latest" jump; disable/skip non-run days or show
   the honest "no run for this date — nearest is X" with a one-click jump.
6. **URL routing**: no route state — browser back exits the whole app, nothing is shareable/
   reloadable. Add URL sync for {tab, symbol, date, open-inspector} (React Router or query-param
   state) so back/forward + reload + deep links work.
7. **TRADE PLAN gaps**: (a) no chart on the execution screen — add the ChartDrawer/thumbnail for
   the symbol; (b) the mentor checklist doesn't persist ticks — wire persistence (endpoint exists
   per handoff 6/9); (c) no "log this decision → journal" action — add a TAKEN/SKIPPED→journal
   button that writes the decision (reuse the journal capture path).

## Guardrails
Money-math/gates untouched; one-writer; real data + honest states; `.v5` tokens; a11y AA;
reduced-motion. Additive backend fields only if truly needed (flag them).

## Output
`HANDOFF_GEMINI_ux_defects_batch_COMPLETED.md`: per-item reproduce→fix with REAL before/after DOM
evidence, files changed, tests, anything deferred. No simulated proofs.

## Fix 8 (ADDED 2026-07-12) — SCANNERS tab appears to have NO presets
Reproduced: /api/scanners/presets with a no-run date returns 19 fast; with a real-data date
(2026-07-10) it computes each preset hit-count synchronously over daily_prices and is SLOW (tens
of seconds), exceeding the desk fetch timeout, so the tab renders EMPTY with no loading state and
reads as "no scans available". The audit's 5 duplicate preset fetches compound it.
Fix: render preset DEFINITIONS immediately (static), load hit-counts lazily/async per preset (or
one batched count call); add a real loading state ("loading 19 scans...") + per-row count spinner,
never a blank tab; dedupe the fetch (fetch once, cache); precompute counts server-side if cheap.
Verify on a real-data date: 19 presets render within ~1s, counts fill in, never an empty tab.
