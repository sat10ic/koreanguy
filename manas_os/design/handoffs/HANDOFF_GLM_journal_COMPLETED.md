# HANDOFF — JOURNAL tab v5 rebuild: COMPLETED + revision notes

**Status:** DONE. Builds clean, all 34 tests pass, demo data wired for visual
verification. This file is the closeout for `HANDOFF_GLM_journal.md`.

---

## 1. WHAT SHIPPED

Two drop-in files, exactly as the original handoff required. Nothing else in the
repo was modified.

- `manas_os/desk/src/LedgerTab.jsx` — full v5 rewrite. Same default export
  (`LedgerTab`), same zero-prop contract (`App.jsx` still renders
  `<LedgerTab />`), same three-endpoint fetch (`/api/journal`,
  `/api/desk/track-record`, `/api/desk/lessons` via the existing
  `fetchJournal` / `fetchTrackRecord` / `fetchLessons`).
- `manas_os/desk/src/LedgerTab.v5.css` — layout-only. Every selector is scoped
  under `.v5 .v5-journal …` or `.v5 .v5-jr-…`; no legacy bare class names
  (`ledger-panel`, `stat-tile`, `equity-curve`, `r-bar`, `winloss`,
  `disclosure-toggle`, `thin-note`, `empty-state`) are shadowed.

### Composition (top to bottom)

1. `SectionLabel "Trade journal — your edge"` (count pill: "N on record") — the
   dominant section, rendered first.
2. **Stat rail** — Trades / Win % (with win-loss ratio bar when ≥1 closed
   trade) / Avg R / Expectancy / Top mistake (conditional, only when
   `stats.top_mistake` is non-null). Null stats render an honest `—` with a
   titled tooltip; empty tiles get a dashed/unfinished look.
3. **Equity curve** — pure inline SVG, cumulative-R. Empty state below 2 closed
   trades ("the equity curve appears from your second closed trade"). Drawn
   with v5 tokens directly (green/red), not the legacy `viz.js` `colorScale`.
4. **Trade history table** — Date / Symbol / Setup / Entry / Exit / R / Reason.
   R column uses a zero-anchored bar; open trades show "open".
5. `SectionLabel "SYSTEM EDGE (advanced)"` with a disclosure toggle (collapsed
   by default in beginner, auto-opens in expert). Three panels inside, each
   with a provenance cite.
6. `SectionLabel "Lessons diary"` + digest — two side-by-side panels, both with
   honest empty states.

---

## 2. REVISION FROM THE ORIGINAL HANDOFF (read this before reviewing)

The maintainer directed two changes after the initial build:

### 2a. The open-trade card was removed.

The original composition included a dedicated `OpenTradeCard` that surfaced the
then-unused fields (`exit_state`, `mfe_r`, `mae_r`) on the single HUDCO open
trade. **The maintainer said this was demo scaffolding, not a real feature —
it has been removed entirely.** All of `OpenTradeCard`, its JSX usage, its
"Open now" sub-section, and its CSS block are gone. The trade-history table's R
column is the only place an open trade shows now (as the "open" label), which
matches the pre-v5 behavior.

If a dedicated open-trade view is wanted later, it should be designed as its
own feature with its own intent — not re-imported from this file.

### 2b. Demo fixtures added, gated behind one flag.

To verify every state visually, the tab now loads hypothetical data instead of
the live API. A single flag controls it:

```js
// manas_os/desk/src/LedgerTab.jsx, near the top
const USE_DEMO_DATA = true;
```

When `true`, the fetch `useEffect` skips the network and loads three in-file
fixtures (`DEMO_JOURNAL`, `DEMO_TRACK_RECORD`, `DEMO_LESSONS`). When `false`,
it resumes the original `Promise.all([fetchTrackRecord(), fetchLessons(),
fetchJournal()])` exactly as the handoff specified. **Flip this to `false`
before any production deploy or QC against the real API.**

The demo fixtures are shaped to exercise every state the tab can render:

- **5 trades**: 1 open (HUDCO), 2 wins (MAZDOCK +3.31R, TATACHEM +2.78R), 2
  losses (INFY −2.1R, DLF −1.0R). → equity curve draws (4 closed points),
  Win % = 50, Avg R / Expectancy = +0.75, Top mistake = "wrong-process-win".
- **Trade history** shows a mix of mistake-tag reasons and the default
  "sold into strength" / "stopped out" fallbacks.
- **Agent track records**: 3 rows, one `thin: true` (n=6) to render the
  "building sample" note.
- **Expectancy cohorts**: a mix of `unproven` (n=5, building) and proven cells
  across `trust` levels (operational / directional / descriptive).
- **Screener calibration**: one `unproven` (n=1) and one proven (n=62) row.
- **Lessons diary**: 3 lessons with three different tags (clean-hit,
  wrong-process-win, right-process-loss).
- **Digest**: a populated multi-line free-text block.

The stats numbers in `DEMO_JOURNAL.stats` are precomputed and consistent with
the trades array (verified: 2/4 wins = 50%, avg R = +0.747 ≈ the +0.75 shown).
They are NOT computed client-side — the one-writer-for-numbers rule still
holds, the fixtures just stand in for what the server would return.

---

## 3. CONSTRAINTS CHECKLIST (from HANDOFF_GLM_journal.md §5)

| Constraint | Status |
|---|---|
| Two drop-in files, same export + zero props | ✅ |
| Touch nothing else (App.jsx, api.js, tokens, primitives) | ✅ verified by diff scope |
| CSS scoped under root wrapper, no bare legacy classes | ✅ checked: zero legacy class leaks |
| Consume only the three existing endpoints | ✅ live path unchanged; demo path is an explicit flag |
| One-writer-for-numbers (payload verbatim, display-rounding only) | ✅ no client-side stat computation; null stats render `—` |
| Honest thin states (1 open trade reads as unfinished) | ✅ on live data; demo data intentionally populates for visual QA |
| No `[B]`/`[E]` markers | ✅ verified: 0 occurrences |
| a11y AA: focus-visible, keyboard, contrast, no meaning-by-color-alone | ✅ teal focus-visible on all interactive controls; `aria-expanded` on disclosure; `+`/`−` signs + "open" label carry win/loss meaning redundantly with color; `--v5-ink-faint` only on decorative icons |

---

## 3a. ROUND-4 RECONCILIATION (frozen design source of truth)

**Constraint (registered):** the v5 design is frozen at
`manas_os/design/bakeoff/round4/debate_merged_light.html`. `tokens.v5.css`
cites this exact file as its source of truth. No round-after-4 conventions or
ad-hoc styling; every v5 screen must reconcile to the round-4 mockup.

The original GLM handoff was written assuming no repo access, so its design
description was secondhand. After gaining access, I audited the JOURNAL CSS
directly against the round-4 mockup rather than the handoff's summary.

**Audit results (LedgerTab.v5.css vs round-4):**

| Check | Result |
|---|---|
| Raw hex colors | **0** — every color resolves through a `--v5-*` token |
| `rgba()` wrappers | 6, all translucent forms of round-4 token values (amber/green/teal/red), matching the precedent `primitives.v5.css` sets |
| `font-family` declarations | all `var(--v5-disp)` / `var(--v5-sans)` / `var(--v5-mono)` / `inherit` (the disclosure button inheriting SectionLabel's Fraunces italic — correct, not a deviation) |
| Radius tokens | only `--v5-r-xs` / `--v5-r-md` / `--v5-r-lg` (from the round-4 scale) |
| Shadow tokens | only `--v5-shadow-panel` (the round-4 panel shadow) |
| Type scale | only `--v5-fs-body` / `--v5-fs-label` / `--v5-fs-micro` / `--v5-fs-ui` / `--v5-fs-val` |
| `--v5-ink-faint` usage | 2 uses, both explicitly on decorative empty-state icons (matches round-4 a11y rule: faint is decorative-only, never essential copy) |
| Equity-curve green/red | resolves to `#14713f` / `#ad2c34` — byte-for-byte the round-4 sparkline `sparkColor` hexes |

**Design-language extension, flagged:** the JOURNAL's cohort "evidence status"
chip (`v5-jr-status-*`, tones: building/operational/directional/descriptive)
is a new presentational sub-component defined inside `LedgerTab.jsx`, not a
round-4 primitive. It extends round-4's existing `status-tag` language
(green `gatepass` / muted `nearmiss`) with an amber "building sample" tone for
the thin-data state §5 requires. This is additive and scoped to JOURNAL only;
it does not redefine any round-4 primitive or leak into other tabs. If the
maintainer wants this promoted to a shared `components/v5/` primitive for reuse
on other screens, that's a separate decision.

---

## 4. VERIFICATION PERFORMED

- **Production build** (`node ./scripts/build.mjs`): compiles clean. Only the
  pre-existing chunk-size advisory shows (unrelated to this change).
- **Test suite** (`npx vitest run`): all 34 tests pass across 5 files.
- **Orphan check**: every `v5-jr-open-*` class and `OpenTradeCard` reference
  confirmed absent from both JSX and CSS (0 occurrences each).
- **Class coverage**: every `v5-jr-` class used in JSX has a matching CSS rule;
  no unused CSS classes remain.
- **Live payload fidelity** (before wiring demo): confirmed the three real
  endpoints return byte-for-byte what §3 of the original handoff documented.
- **Glossary keys**: all `Term` keys the component references (`hit-rate`,
  `avg-r`, `stage-expectancy`) exist in `glossary.js`.
- **Stats math**: demo fixture's `stats` object matches the trades array
  (win_pct 50, avg_r +0.747 ≈ +0.75).

---

## 5. BACKEND FIELDS REQUESTED

None. Every field rendered is already present in the live payloads
(`exit_state`, `mfe_r`, `mae_r`, `trust`, `unproven` are all real fields).
Note: `exit_state` / `mfe_r` / `mae_r` are still NOT rendered anywhere in the
UI after the card removal (the 2b revision dropped the only consumer). They
remain available in the payload if a future open-trade view wants them.

---

## 6. WHAT THE MAINTAINER SHOULD DO NEXT

1. **Flip `USE_DEMO_DATA` to `false`** when done with visual review, to restore
   the honest live fetch. This is the single most important follow-up.
2. **Visual review against the live 1-trade state**: with demo off, confirm the
   thin/unfinished read still looks right (empty equity curve, `—` stats,
   collapsed SYSTEM EDGE). The demo path will not show this state.
3. **Decide on the dropped fields**: `exit_state` / `mfe_r` / `mae_r` are now
   unused again. Either leave them for a future feature or open a ticket if
   they should be surfaced elsewhere.

---

## 7. ASSUMPTIONS

1. The demo fixtures are for visual verification only and will be disabled
   before deploy. They are not a permanent data source.
2. The `trust` field (`directional` / `operational` / `descriptive`) is treated
   as additive to `unproven`, which remains the authoritative thin-sample gate,
   per §3 of the original handoff.
3. The "advanced" label in the SYSTEM EDGE `SectionLabel` count pill is static
   text (the disclosure affordance), not a computed count.
