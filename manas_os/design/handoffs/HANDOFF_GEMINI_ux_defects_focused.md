# HANDOFF (BATCH) — UX Defects: Reduced-Motion + Debate/Positions/Journal/Keyboard (Gemini)

Repo `C:\Users\satta\Downloads\koreanguy`, branch `emergent`. Standing rules: HANDOFF_INDEX.md.
Subset of #11 UX defects batch — high-impact, bounded-scope items from `UX_CRAFT_AUDIT_2026-07-12.md`.

---

## Scope (6 items)

### #31 Reduced-motion guards (P1)
**Finding:** Only 3 of 10 CSS files respect `prefers-reduced-motion: reduce`. `App.css` declares 11 animation/transition rules with zero guard.
**Files to fix:** `App.css`, `MarketHomeTab.v5.css`, `DebateTab.v5.css`, `ShortlistTab.v5.css`, `ScannersTab.v5.css`, `TradePlanTab.v5.css`, `PositionsTab.v5.css`, `JournalTab.v5.css`, `ChartDrawer.v5.css`, `primitives.v5.css` (already has guard at 963-966 — use as pattern).
**Pattern to replicate:**
```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}
```
**Scope:** Wrap all `transition`, `animation`, `scroll-behavior` declarations in each file.

---

### #19 DebateTab: pipeline note clickable (P1)
**Finding:** "1 pipeline note(s) logged" is not clickable — logged anomaly the user cannot read.
**Location:** `DebateTab.jsx` deep-dive card render (around line 181-188), where `card.errors` / `card.pipeline_notes` exists but isn't exposed.
**Fix:** Make the note text a button/link that expands a detail panel showing `card.errors` array (or `pipeline_notes`). Use existing `Collapsible` pattern from `primitives.v5.css` or inline `<details>`.

---

### #23 PositionsTab: origin-thesis link (P1)
**Finding:** HUDCO card says "Entry steps were on the original DEBATE card" but provides NO link to that card/date.
**Location:** `PositionsTab.jsx:229-241` (TelegramMirror area) + position card render.
**Data available:** Position has `origin_debate_date` and `origin_symbol` (or can be derived from `setup_decisions` join).
**Fix:** Render "Open origin debate (2026-07-03)" link → navigates to DEBATE tab with deep-link `#deepdive-HUDCO` (implement hash routing if not exists, or scroll to symbol in DebateTab).

---

### #49 PositionsTab: no-thesis dead-end copy (P2)
**Finding:** "ORIGINAL THESIS: no agent thesis" — dead-end copy. Say why (manually added) and offer "run debate now".
**Location:** Same area as #23, `PositionsTab.jsx` where thesis is rendered.
**Fix:** Replace with: "Manually added — no agent thesis. [Run debate for HUDCO]" where button calls `pushSymbolToDebate(symbol)` (API exists at `POST /api/debate/push`).

---

### #25 JournalTab: manual add-trade (P1)
**Finding:** User cannot write anything — no add-trade, no edit, no manual lesson. "LESSONS DIARY from ~/.manas/lessons" is filesystem-only.
**Location:** `JournalTab.jsx` / `LedgerTab.jsx` (the journal UI).
**Backend:** `POST /api/journal` exists (check `app.py`), `DELETE /api/journal/{trade_id}` exists (app.py:3352), but no `PUT` for edit.
**Fix:**
1. Add "Add Trade" button → modal/form with: symbol, date, entry, exit, qty, side, verdict (TAKE/SKIP), notes
2. Wire to `POST /api/journal` → reload
3. Add inline edit for entry/exit/R on existing rows (click cell → input → blur saves via `PUT /api/journal/{trade_id}` — may need backend add)
4. Add "Add Lesson" input at bottom of diary section → persists to `journal_trades.lesson` or separate `lessons` table

---

### #28 Keyboard shortcuts (P1)
**Finding:** No keyboard shortcuts at all — no "/" to focus search, no keydown listener.
**Location:** `App.jsx` (global keydown) + `SearchInput` component.
**Shortcuts to implement:**
- `/` → focus search input
- `?` → toggle guided flow rail (beginner) / show help toast
- `g h` → go to MARKET (home)
- `g d` → go to DEBATE
- `g p` → go to POSITIONS
- `g j` → go to JOURNAL
- `g s` → go to SHORTLIST
- `g a` → go to ALPHA
- `g t` → go to TRADE PLAN
- `Escape` → close modals/drawers/expanded cards
**Implementation:** Single `useEffect` keydown listener in `App.jsx` (before tab render), dispatch to handlers. Search focus via `ref.current.focus()`.

---

## Guardrails

- Money-math LOCKED — UI never computes stop/target/qty/risk
- Real data only; honest empty/"needs ingest" states
- `.v5` tokens only; plain SVG; a11y AA; reduced-motion (now enforced)
- Additive DB migrations only (journal `PUT` may need one)
- Never print rupee glyph — use "Rs"
- `pytest manas_os/tests -q` green + `cd manas_os/desk && npm run build` + `npx vitest run`
- `python scripts/desk_gate.py` must remain 3/3 PASS (no new findings)

---

## Output

`HANDOFF_GEMINI_ux_defects_focused_COMPLETED.md` containing:
- Files changed per item
- Reduced-motion: list of 10 CSS files modified + diff snapshots
- Debate pipeline note: component change + interaction proof
- Positions origin link: deep-link implementation + test
- Positions no-thesis: copy + "run debate" button wiring
- Journal add-trade: form + API wiring + (if needed) backend `PUT` route note for maintainer
- Keyboard shortcuts: `App.jsx` listener + shortcut map
- Test results (pytest, build, vitest)
- Gate result: `python scripts/desk_gate.py` → 3/3 PASS

---

## Execution order

1. Reduced-motion guards (10 CSS files — mechanical, do first)
2. Keyboard shortcuts (single `App.jsx` change, high impact)
3. Debate pipeline note clickable (localized)
4. Positions origin-thesis link + no-thesis copy (same file, related)
5. Journal add-trade + edit (largest — may need backend `PUT` route; flag for maintainer)
6. Run gate + full test suite

Do NOT commit. Maintainer QCs and commits.