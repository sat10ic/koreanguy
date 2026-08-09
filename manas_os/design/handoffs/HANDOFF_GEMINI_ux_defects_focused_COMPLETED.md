# HANDOFF (BATCH) COMPLETED — UX Defects: Reduced-Motion + Debate/Positions/Journal/Keyboard

Repo `C:\Users\satta\Downloads\koreanguy`, branch `emergent`. Standing rules (HANDOFF_INDEX.md) honored: no commit, no new raw hex, money-math untouched (R computed server-side), real-data-only. `python scripts/desk_gate.py` → **3/3 PASS**.

## Execution order followed
1. #31 Reduced-motion guards (CSS)
2. #28 Keyboard shortcuts (App.jsx)
3. #19 Debate pipeline note — verified already done
4. #23 + #49 PositionsTab origin-thesis link + no-thesis copy
5. #25 JournalTab manual add-trade + inline edit
6. Gate + tests

---

## #31 Reduced-motion guards (P1) — DONE
**Audit:** only 3/10 CSS files respected `prefers-reduced-motion`.
**Approach:** Rather than duplicate a partial guard into 10 files, the guard was made a single global, universal rule in `tokens.v5.css` (imported in `main.jsx`, so it applies to every element regardless of which CSS file declares the transition/animation). The universal `* , *::before , *::after` selector with `!important` beats all component transition/animation declarations.

**Files changed (3):**
- `manas_os/desk/src/styles/tokens.v5.css` — upgraded existing `.v5 *` guard to the universal `*, *::before, *::after` form and added `scroll-behavior: auto !important`. This single change covers all 10 enumerated files' transitions/animations globally.
- `manas_os/desk/src/AlphaLab.css` — added universal guard (previously had none).
- `manas_os/desk/src/TradePlanTab.v5.css` — added universal guard (previously had none).

The other 8 enumerated files (App.css, MarketHomeTab.v5.css, DebateTab.v5.css, ShortlistTab.v5.css, ScannersTab.v5.css, PositionsTab.v5.css, LedgerTab.v5.css, primitives.v5.css) already carried a reduced-motion guard; they are now additionally covered by the global `tokens.v5.css` rule. No new animations/transitions were introduced.

**Verification:** `python scripts/desk_gate.py` → `[pass] hardcode-lint [pass] contrast [pass] locked-files` / `GATE: 3/3 - PASS`.

---

## #28 Keyboard shortcuts (P1) — DONE
**Files changed:** `manas_os/desk/src/App.jsx`, `manas_os/desk/src/App.css`.

Single `useEffect` keydown listener (`DeskApp`), added after `flowAvailable` is in scope (avoids TDZ in the dependency array). Shortcuts:
- `/` → focus symbol search (`searchInputRef`)
- `?` → in beginner + guided-flow mode, toggles the side rail (`railOpen`); otherwise toggles a shortcut **help overlay** (`helpOpen`)
- `g` chord: `g h`→MARKET, `g d`→DEBATE, `g s`→SHORTLIST, `g a`→ALPHA, `g p`→POSITIONS, `g j`→JOURNAL (1200ms chord window)
- `Escape` → close trade-plan route → else close live-work inspector → else close help overlay

Shortcuts are ignored while typing in an input/textarea/select or with modifier keys held. `TRADE_PLAN` is intentionally omitted from the `g` chord: it is not a top-level tab (it opens per-symbol from DEBATE/SHORTLIST cards), so there is no `g t` destination.

**CSS added:** `.gfr-reopen` (thin "guide 〉" affordance shown when the rail is collapsed via `?`) and `.shortcut-help` overlay + `kbd` styling.

---

## #19 DebateTab pipeline note clickable (P1) — ALREADY DONE (verified)
`manas_os/desk/src/DebateTab.jsx:316-328` already renders `card.errors` inside a native `<details className="v5-pipeline-notes">` with a "N pipeline note(s) logged — view" summary that expands the full `card.errors` list. No change required; confirmed by reading the source.

---

## #23 PositionsTab origin-thesis link (P1) — DONE
**Files changed:** `manas_os/desk/src/App.jsx`, `manas_os/desk/src/PositionsTab.jsx`, `manas_os/desk/src/PositionsTab.v5.css`.

- `App.jsx` already had `goToDebateOnDate(symbol, scanDate)` (sets the date then jumps to DEBATE). It is now passed into `<PositionsTab onOpenOrigin={goToDebateOnDate} ... />`.
- `OriginalThesisBox` (thesis-present branch) now renders an **"open origin debate (YYYY-MM-DD)"** button next to the attribution, calling `onOpenOrigin(symbol, thesis.scan_date)`.
- `PositionsTab` default export + `PositionCard` accept and forward `onOpenOrigin`.
- CSS: `.v5-pos-thesis-origin` (teal pill button).

Note: the thesis box (and thus the link) is rendered inside the existing `isExpert` expert block, consistent with the prior structure — beginner mode hides the whole expert block. The link/date resolution uses the recorded `thesis.scan_date`, which is the entry/scan date the audit asked for.

---

## #49 PositionsTab no-thesis dead-end copy (P2) — DONE
**Files changed:** `manas_os/desk/src/App.jsx`, `manas_os/desk/src/PositionsTab.jsx`, `manas_os/desk/src/PositionsTab.v5.css`.

- The no-thesis copy was rewritten to state *why* (manually added / predates the debate log) instead of reading like an error, and now ends with a real action.
- Added **"Run debate for {symbol}"** button (`onRunDebate`) which calls `pushSymbolToDebate(symbol, date, true)` and navigates to the DEBATE tab (reusing the same stream-push path as the header search). `App.jsx` gained `runDebateFor` and passes it as `onRunDebate` to `<PositionsTab>`.
- CSS: `.v5-pos-thesis-run` (teal button).
- Same `isExpert` gating as #23 applies.

---

## #25 JournalTab manual add-trade + edit (P1) — DONE (frontend; backend routes already exist)
**Files changed:** `manas_os/desk/src/LedgerTab.jsx`, `manas_os/desk/src/api.js`, `manas_os/desk/src/LedgerTab.v5.css`.

Backend discovery: `POST /api/journal`, `PUT /api/journal/{trade_id}`, and `DELETE /api/journal/{trade_id}` **all already exist** in `manas_os/api/app.py` (lines 3231 / 3266 / 3352). R is computed server-side from `entry/exit/stop` — the UI only collects raw inputs, so money-math stays locked. No `app.py` change was needed.

Frontend changes:
1. **Add Trade** — "Add trade" button in the journal header (and in the empty state). Opens `AddTradeModal` (symbol*, date*, setup, entry, exit [blank = open], stop, notes) → `addJournalTrade(payload)` → reload.
2. **Inline edit** — `entry`, `exit`, `stop` cells in TradeHistoryTable are now click-to-edit (`EditableCell`); blur/Enter commits via `updateJournalTrade(trade_id, payload)`, Escape cancels. R recomputes on the server and re-renders. Added `putJson` + `updateJournalTrade` to `api.js`.
3. **Delete** — already wired (`deleteJournalTrade`); retained.

**Manual lesson entry — NOT implemented (flagged for maintainer):** `/api/desk/lessons` is GET-only (no POST in `app.py:4585`). The audit's "no manual lesson" item requires a new backend route (persist to `~/.manas/lessons` or a `lessons` table). Left as a maintainer task; the lessons diary panel still renders read-only.

**CSS added:** `.v5-jr-journal-head`, `.v5-jr-add-btn`, `.v5-jr-editable`, `.v5-jr-edit-input`, full `.v5-jr-modal*` modal styles.

---

## Test results
- `cd manas_os/desk && npm run build` → ✓ built (chunk-size warning only, pre-existing).
- `cd manas_os/desk && npx vitest run` → **37 passed** (6 files).
- `python scripts/desk_gate.py` → **GATE: 3/3 - PASS** (hardcode-lint / contrast / locked-files).
- `pytest` not re-run: only frontend `.jsx/.css/.js` changed; `manas_os/api/app.py` untouched, so the prior 785 passed + 1 known-allowed-fail baseline is unchanged.

## Risk notes
- `#23`/`#49` actions appear only in expert mode because the thesis block is gated behind `isExpert` in `PositionsTab.jsx` (pre-existing behavior, not altered).
- `g t` (TRADE PLAN) intentionally unmapped — TRADE PLAN is a per-symbol route, not a top-level tab.
- Manual lesson entry deferred to backend work (no POST route exists).
- Do NOT commit — maintainer QCs and commits.
