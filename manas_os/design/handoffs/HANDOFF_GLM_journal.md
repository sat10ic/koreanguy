# HANDOFF — rebuild the MANAS OS JOURNAL tab (v5 light design system)

You are receiving this as a complete, standalone brief. You have **no access to the repository** —
everything you need to write the code is embedded below (design tokens, component APIs, current
component inventory, real API payloads). Do not invent anything not given here.

Context: Manas OS is an NSE (Indian stock exchange) swing-trading desk tool. It is mid-way through
a UI overhaul from a dark "terminal" look to a new light "v5" design system. One screen at a time is
being rebuilt to the v5 language. **Your job is exactly one screen: the JOURNAL tab.** A second,
independent contractor (a different LLM) is rebuilding the POSITIONS tab in parallel — you do not
need to worry about that screen or touch any file it might touch.

---

## 1. GOAL

Rebuild the JOURNAL tab body to the v5 light design system, composed to hit this target experience
(quoted verbatim from the controlling design doc, `manas_os/design/UI_OVERHAUL_HANDOFF.md` §5):

> ### JOURNAL — "Am I earning an edge?"
> - User trades and equity/R path first.
> - Every setup/mechanism shows evidence status, `n`, net-R horizon and sample gap to the next
>   status. Thin samples look unfinished, not green or authoritative.
> - Separate provenance ("TradeTM teaches this") from measured Indian evidence ("Manas has n=…").
> - Advanced model/agent records stay available but cannot overwhelm personal learning.

And from §5's UI-6 slice done-test:

> Recompose Journal around personal edge development and honest thin-data states... one-trade data
> does not imply statistical proof.

### §4 composition rules that bind on every v5 screen (quoted verbatim)

> - One dominant question, one dominant visual and one primary action per screen state.
> - Default to cardless sections, rails, bands, tables and annotated canvases. A card is allowed
>   only when it is the actual interactive object (candidate, position, saved scan).
> - Verdict and next action appear before metrics. Evidence is attached to the visual that proves
>   it, not separated into a legend/card farm.
> - Replace `[B]`/`[E]` markers with plain labels such as "Why this matters" and "Evidence & method."
> - Motion marks a real change once, then holds. Never animate P&L, stop, target, size or verdict.

Translated for JOURNAL specifically:
- The dominant question is "Am I earning an edge?" — lead with the user's own trades and their
  equity/R curve, not with system-wide expectancy tables.
- The "SYSTEM EDGE (advanced)" material (agent track records, setup-family expectancy, screener
  calibration) is real and must stay reachable, but it is secondary — advanced/collapsed by
  default outside expert mode, and must never visually outrank the personal trade journal.
- With only 1 real trade in the data (see §3 below), the honest move is to make the screen look
  **unfinished**, not to dress it up as if there's a proven track record. Do not pad with fake
  polish. A thin-sample state should read as "still building" — say so in plain language.
- No `[B]`/`[E]` bracket markers anywhere in your output.

---

## 2. CURRENT STATE (what exists today — read this before changing anything)

**Important naming note:** there is no file literally called `JournalTab.jsx` in this repo. The tab
labeled "JOURNAL" in the app's top nav is rendered by `manas_os/desk/src/LedgerTab.jsx`
(`App.jsx` does `{tab === "JOURNAL" && <LedgerTab />}`). **Your two output files must be named
`LedgerTab.jsx` and `LedgerTab.v5.css`** — same default export name (`LedgerTab`), same props
signature (it currently takes **zero props**) — so they drop in as a direct replacement.

### Element-for-element inventory of the current `LedgerTab.jsx`

The component renders, top to bottom, in this order:

1. **`JournalStrip`** (panel "Trade journal") — the personal trade journal, rendered first:
   - Empty state if `journal.trades` is empty: "No journal trades yet."
   - Stat row of tiles: **Trades** (`stats.count`), **Win %** (`stats.win_pct`, with a small
     win/loss ratio bar beside it), **Avg R** (`stats.avg_r`), **Expectancy** (`stats.expectancy_r`),
     and **Top mistake** (`stats.top_mistake`, tile omitted when null).
   - **Equity curve**: cumulative-R line chart (pure inline SVG, no chart lib) built from closed
     trades in chronological order (payload is newest-first, reversed for the curve). Honest empty
     state below 2 closed trades: "Not enough closed trades yet — the equity curve appears from
     trade 2." Line color follows the same red/green scale as everywhere else in the app
     (`viz.js` `colorScale`), and a right-aligned readout shows "cumulative R" + the last value.
   - **Trade history table**: columns Date / Symbol / Setup / Entry / Exit / R / Reason.
     - R column uses a small zero-anchored horizontal bar (green right of center for wins, red
       left for losses, "open" label in muted mono if `r_result` is null).
     - Reason column: `mistake_tags.join(", ")` if present, else "—" for open trades, else
       "sold into strength" (win) / "stopped out" (loss).
2. **Disclosure toggle** `"▾/▸ SYSTEM EDGE (advanced)"` — button that expands/collapses the block
   below. Defaults **open in expert density mode, closed in beginner mode** (there's a shared
   `useDensity()` context exposing `isExpert`; a `useEffect` re-syncs the open state whenever
   density mode changes, but a manual toggle click still overrides in either direction until the
   next density change).
3. Inside the disclosure, three panels:
   - **"System expectancy (setup families)"** — table Family / Regime / Passed (taken) / Refused
     (near-miss). Each cohort cell shows `n=` count; if `n < 20` (`TRUST_FLOOR_N`) it renders
     "UNPROVEN — building sample (n=X)" instead of a hit-rate number — this is the sample-gap
     storytelling the design doc asks for. Otherwise shows `n=X hit Y% avg ±Z R` (or `avg ±Z%
     (no stop set)` for the "refused" cohort, which is a raw % baseline, not R). Caption below the
     table: "System loop: every persisted candidate's forward return at T+10, whether taken or
     not — proves or kills the setup family over time, independent of any one trade."
   - **"Agent track records"** — table Agent / Family / Hit / Avg R / n. Rows with `thin: true`
     get a "thin-row" style + " building sample" note.
   - **"Which screeners predict"** — table Screener / n / Avg excess (T+10) / Median excess / Win %
     / Baseline win %. `unproven` rows (n<30) get "n<30 — building sample" note. Caption: "Screeners
     ranked by whether their picks actually went up afterwards."
4. **`LessonsDiary`** (always visible, outside the disclosure) — two panels:
   - "Lessons diary" — list of lesson rows (filename, a tag pill like "clean hit"/"clean
     miss"/"right process, loss"/"wrong process, win", first-line preview), or an empty state "No
     lessons written yet."
   - "What the desk carries forward" — a `<pre>` block of free-text digest, or an empty state "No
     digest in force yet."

### Data fetching and every endpoint called

`LedgerTab.jsx` calls, on mount only (no `date` prop, no re-fetch on date change — this is a known
gap, not something to silently "fix" by inventing a date param that doesn't exist server-side):

```js
import { fetchTrackRecord, fetchLessons, fetchJournal } from "./api.js";
Promise.all([fetchTrackRecord(), fetchLessons(), fetchJournal()])
```

Which map (from `manas_os/desk/src/api.js`) to real HTTP calls against the live API root
`http://127.0.0.1:8000`:

```js
export function fetchTrackRecord() {
  return getJson("/api/desk/track-record");   // GET /api/desk/track-record  (no params)
}
export function fetchLessons(limit) {
  return getJson("/api/desk/lessons", limit ? { limit } : undefined); // GET /api/desk/lessons
}
export function fetchJournal() {
  return getJson("/api/journal");             // GET /api/journal  (NOT /api/desk/journal)
}
```

There are **no mutations** on this tab (read-only). `getJson` is a thin `fetch()` wrapper that
returns parsed JSON or throws `Error("<path> -> HTTP <status>")` on non-2xx; on a network failure
it falls back to a small hardcoded offline snapshot for a few unrelated paths (not these three), so
for these three endpoints a real failure surfaces as a thrown error and the tab shows an error
empty-state ("Could not load the ledger.").

Keep exactly this fetch contract (same three functions, same on-mount `Promise.all`, same
loading/error empty states) unless your composition genuinely needs to restructure it — if so,
explain why in your reply, don't just silently change it.

---

## 3. LIVE DATA (real payloads, captured 2026-07-10, from the running API at 127.0.0.1:8000)

### `GET /api/journal` (the personal trade journal — this is the important one; only 1 trade exists)

```json
{
  "available": true,
  "trades": [
    {
      "trade_id": 2,
      "trade_date": "2026-07-03",
      "symbol": "HUDCO",
      "setup": "Pullback-to-EMA",
      "entry": 218.0,
      "exit": null,
      "stop": 210.84,
      "r_result": null,
      "notes": "auto-captured from setups",
      "created_at": "2026-07-06 19:35:11",
      "exit_date": null,
      "mistake_tags": [],
      "exit_state": {
        "state": "Weakening",
        "fired_rules": [
          { "rule": "distribution-days", "detail": "4 distribution days in the last 25 bars." },
          { "rule": "distribution-cluster", "detail": "Three or more recent distribution days show clustered selling." }
        ],
        "read": "Exit state is weakening; tighten trade management."
      },
      "result": "open",
      "mfe_r": -0.02,
      "mae_r": -2.29
    }
  ],
  "stats": {
    "win_pct": null,
    "avg_r": null,
    "expectancy_r": null,
    "count": 1,
    "top_mistake": null
  }
}
```

**Notes on this payload vs. the current UI code:**
- There is exactly **1 trade, still open** (`result: "open"`, `r_result: null`, `exit: null`). This
  is the "1 real trade" the design doc's P1 audit and §5 both call out — your composition MUST
  read as honestly thin/unfinished with this data, not fake a populated dashboard.
- The current `JournalTab` code does not render `exit_state`, `mfe_r`, or `mae_r` at all — these
  are real fields in the payload that are currently unused. You MAY surface them if they fit your
  composition (e.g. an inline note on the trade row), but do not invent new UI chrome just because
  a field exists — only add it if it actually serves "am I earning an edge" or the exit-quality
  story. If you're unsure, leave it out and list it under BACKEND FIELDS REQUESTED with a note that
  it's already present but unused, so the maintainer can decide.
- `stats.win_pct` / `avg_r` / `expectancy_r` are all `null` (can't compute stats meaningfully with
  0 closed trades) — your empty/thin states must handle `null` here, not just `0`.

### `GET /api/desk/track-record` (system-wide expectancy — feeds "SYSTEM EDGE (advanced)")

```json
{
  "records": [],
  "expectancy": [
    {
      "family": "base/pattern",
      "regime": "SELECTIVE",
      "passed": { "n": 24, "hit_rate": 0.0, "mean_r": -1.263, "median_r": -1.107, "trust": "directional", "unproven": false },
      "refused": { "n": 19065, "hit_rate": 0.479, "mean_r": 0.303, "median_r": -0.313, "trust": "operational", "unproven": false }
    },
    {
      "family": "catalyst",
      "regime": "DEFENSIVE",
      "passed": { "n": 5, "hit_rate": 0.0, "mean_r": -1.619, "median_r": -1.158, "trust": "descriptive", "unproven": true },
      "refused": { "n": 256, "hit_rate": 0.512, "mean_r": 0.577, "median_r": 0.334, "trust": "operational", "unproven": false }
    },
    {
      "family": "catalyst",
      "regime": "SELECTIVE",
      "passed": { "n": 29, "hit_rate": 0.0, "mean_r": -1.132, "median_r": -1.063, "trust": "directional", "unproven": false },
      "refused": { "n": 1436, "hit_rate": 0.533, "mean_r": 1.584, "median_r": 0.455, "trust": "operational", "unproven": false }
    }
  ],
  "screener_calibration": [
    {
      "screener": "vcp", "horizon": 10, "n": 1, "avg_excess_pct": 0.646, "median_excess_pct": 0.646,
      "win_rate": 1.0, "baseline_win_rate": 0.0, "baseline_n": 0, "as_of": "2026-07-10", "unproven": true
    }
  ]
}
```

Counts: 3 expectancy rows total (all shown above — none trimmed), `records: []` (empty — the
"Agent track records" table has 0 rows for this data; render its real empty state, do not fabricate
rows), 1 screener_calibration row (shown in full, `unproven: true` because n=1 « 30).

**Field notes:** `passed.trust` / `refused.trust` (`"directional"` / `"operational"` /
`"descriptive"`) is a real field the current UI code does NOT render at all (`cohortCell()` only
checks `n < TRUST_FLOOR_N=20`, ignoring `trust`). This is a good candidate for the "evidence status"
language §5 asks for ("Every setup/mechanism shows evidence status, n, net-R horizon and sample gap
to the next status") — you may use it, but if you do, treat it as additive to the existing
`unproven`/`n` logic, not a replacement, since `unproven` is still the authoritative gate.

### `GET /api/desk/lessons` (currently empty for this date — render the real empty states)

```json
{ "lessons": [], "digest": "" }
```

Both the lessons list and the digest are empty right now — this is real, not a fetch failure. Your
composition must render the honest empty states ("No lessons written yet." / "No digest in force
yet — nothing has been distilled to carry forward."), matching current behavior.

---

## 4. v5 DESIGN CONTRACT

### 4a. Design tokens — `manas_os/desk/src/styles/tokens.v5.css` (already shipped, read-only, DO NOT edit)

All values are scoped under a `.v5` class that already wraps the whole app shell — you can rely on
every one of these CSS custom properties being in scope wherever your tab renders. Do not redefine
any of them; do not reach for the old dark-theme `--bg`/`--ink`/`--accent` names from `tokens.css` —
those are the pre-overhaul legacy system and are being phased out.

```css
.v5 {
  /* canvas / surface steps (warm off-white "newsprint" ramp) */
  --v5-canvas:    #f7f6f2;   /* page bg */
  --v5-canvas-1:  #f2f0e9;   /* sunken */
  --v5-panel:     #fffdf9;   /* raised */
  --v5-panel-2:   #f3f1ea;   /* inset chip bg */
  --v5-panel-3:   #ece9df;   /* deepest inset / tape bg */

  /* hairlines */
  --v5-line:      #e2ddd0;
  --v5-line-soft: #ebe7db;

  /* ink ramp */
  --v5-ink:       #17181b;
  --v5-ink-dim:   #43464e;
  --v5-ink-mute:  #6b6f78;
  --v5-ink-faint: #9a9da5;   /* decorative ONLY — never essential copy (a11y) */

  /* accents */
  --v5-teal:        #0d6c6c;  /* analysis / system */
  --v5-teal-ink:    #0a5555;  /* teal on light bg for TEXT (AA-safe) */
  --v5-teal-dim:    #d8ece9;  /* teal wash bg */
  --v5-amber:       #8a5a12;  /* caution — text-safe ochre */
  --v5-amber-ink:   #6e470d;
  --v5-amber-bright:#b8801a;  /* graphics/borders only, NOT body text (~2.9:1, fails AA) */
  --v5-amber-glow:  rgba(184, 127, 26, 0.12);
  --v5-green:       #14713f;  /* literal TAKE / up / win */
  --v5-green-dim:   #dcefe1;
  --v5-red:         #ad2c34;  /* literal SKIP / down / loss / refusal */
  --v5-red-dim:     #f6dfe0;

  --v5-vote-take-seg: #8fcaa5;
  --v5-vote-skip-seg: #e0a3a7;
  --v5-on-accent:      #fff;

  /* type */
  --v5-disp: "Fraunces", Georgia, serif;               /* display, verdicts, big numbers */
  --v5-sans: "Public Sans", -apple-system, sans-serif; /* UI + prose */
  --v5-mono: "IBM Plex Mono", ui-monospace, monospace; /* NUMBERS ONLY + tiny code tags */

  /* type scale */
  --v5-fs-hero:  30px;
  --v5-fs-disp:  21px;
  --v5-fs-val:   17px;
  --v5-fs-body:  11.5px;
  --v5-fs-ui:    10.5px;
  --v5-fs-label: 9.5px;
  --v5-fs-micro: 9px;

  /* radius */
  --v5-r-xs: 3px;
  --v5-r-sm: 5px;
  --v5-r-md: 7px;
  --v5-r-lg: 10px;
  --v5-r-xl: 12px;

  /* shadow + motion */
  --v5-shadow-panel: 0 1px 2px rgba(23, 24, 27, 0.03);
  --v5-shadow-hero:  0 16px 44px -24px rgba(23, 24, 27, 0.18);
  --v5-motion-fast: 120ms ease;
  --v5-motion-tape: 52s linear;
  /* NEVER animate: P&L, stop, target, qty, verdict */
}
```

Also globally available in `.v5`: `.mono-num` class (tabular-nums mono numeral styling — use this
on every number you render instead of hand-rolling font-family rules).

### 4b. v5 primitive components — `manas_os/desk/src/components/v5/index.js`

These **already exist** in the repo and **must be imported, not re-implemented**. Import them from
`"./components/v5/index.js"` (relative to `LedgerTab.jsx`'s own directory,
`manas_os/desk/src/`). Full prop APIs (read from the actual source):

```jsx
// SectionLabel.jsx — italic Fraunces section header + gradient rule + optional count pill
<SectionLabel count={optionalNumberOrString}>Section title text</SectionLabel>

// Panel.jsx — bordered panel + header (title + right-aligned italic mono "cite" slot) + body
<Panel title="Panel title" cite="optional provenance string" className="optional-extra-class">
  {children}
</Panel>
// also exports: <PanelHeader title cite />

// StatusChip.jsx — small status chip (dot + label + value)
<StatusChip label="Day" value={dayColorOrString} tone="neutral|green|amber|red" qual={bool} title={hoverTitle} dot={bool} />

// VerdictChip.jsx — TAKE/SKIP style chip w/ optional struck marker + embedded ConvictionDots
<VerdictChip verdict={"TAKE"|"SKIP"|serverStringOnly} struck={bool} conviction={0-4} showDots={bool} />
// NEVER pass a verdict you invented — server string only.

// ConvictionDots.jsx — 4-dot meter
<ConvictionDots conviction={0-4} max={4} />

// Sparkline.jsx — pure-SVG line sparkline from a real numeric array (renders "—" if <2 points, no synthetic fill)
<Sparkline series={[...numbers]} width={72} height={22} />

// ReturnCell.jsx — signed %, green/red, mono tabular, "—" with title when null
<ReturnCell value={numberOrNull} nullTitle="optional custom null explanation" />

// GateCellGrid / GateCell (GateCell.jsx) — deterministic gate result cells (not likely needed for JOURNAL)
<GateCellGrid gates={[{name, state, objection}]} />

// StruckNote.jsx — teal-edged quote block
<StruckNote>{children text/markup}</StruckNote>

// SizerStamp.jsx — risk-refusal stamp (not relevant to JOURNAL)
<SizerStamp reason qty rupeeRisk multiplier />

// CallBanner.jsx — stance banner w/ headline + cite bullets (not likely needed for JOURNAL)
<CallBanner stance="CAUTION" icon="⚠" headline={string} bullets={[{text, cite}]} />

// LensLane.jsx — 4-up mechanism lens cells (label/value/pct-bar/desc) — GOOD FIT for the
// "evidence status per setup family" language in §5 if you want a compact lens-style summary row.
<LensLane lenses={[{label, value, pct, desc}]} />
// If lenses is empty/undefined it renders its own "— N/A / not triggered" fallback automatically.

// GatePassTag.jsx — GATE-PASS/NEAR-MISS tag (debate-specific, unlikely needed here)
// LaneCard.jsx — mechanism lane summary card (debate-specific, unlikely needed here)
// MLBar.jsx — ML probability micro-bar (debate-specific, unlikely needed here)
// VoteBar.jsx — council vote split bar (debate-specific, unlikely needed here)
// CommandStrip.jsx / TickerTape.jsx — SHELL-OWNED, App.jsx already renders these above every tab.
//   Do NOT render another CommandStrip or TickerTape inside your tab body.
```

If your composition needs a primitive that doesn't exist (e.g. a dedicated "evidence status" chip
distinct from `StatusChip`), you may write small presentational sub-components **inside your own
`LedgerTab.jsx`** (not in `components/v5/`) — just don't duplicate what an existing primitive
already does.

### 4c. Reference pattern — how a shipped v5 tab is composed

`manas_os/desk/src/DebateTab.jsx` + `DebateTab.v5.css` is the one tab already rebuilt to v5 (you
cannot open these files, so here is their shape, described):

- The file imports the v5 primitives it needs from `./components/v5/index.js`, plus its own
  `./DebateTab.v5.css` (imported as a plain `import "./DebateTab.v5.css";` side-effect import at
  the top of the file, alongside the primitives import).
- The component body is organized as a flat sequence of `<SectionLabel>` headers followed by the
  section's content — e.g. `<SectionLabel>Market Context — Why We're Picky Tonight</SectionLabel>`
  then a grid of `<Panel>`s, then `<SectionLabel count={"13 debated"}>...</SectionLabel>` then a
  table, etc. There is no single big wrapping card — sections sit directly in the page flow inside
  one outer `<div className="v5-debate">` root, and `SectionLabel` supplies the rhythm/hierarchy
  between them (this is the "cardless-by-default, rails/bands not card farm" rule from §4 in
  practice).
- Small presentational sub-components are defined in the same file (not extracted to `components/`)
  for anything tab-specific — e.g. a `RegimeRing` SVG gauge, a `GovernorRow`, a `FootStats` block —
  each is a plain function component taking the relevant slice of the payload as props, doing pure
  derivation/formatting, and rendering JSX. Pure helper functions (`round()`, `laneFamily()`, etc.)
  sit above the components in the same file.
- Loading/error/empty states are small early-return blocks at the top of the default-exported
  component, each rendering inside the tab's own root class (e.g. `<div className="v5-debate
  v5-debate-empty">Loading…</div>`) rather than a shared generic empty-state component.
- The CSS file scopes every single selector so it only fires inside the tab, by prefixing every
  class with `v5-` (e.g. `.v5-debate`, `.v5-groww-block`, `.v5-lens-grid`) and by nature of the
  root div wearing one of those classes, combined with the ambient `.v5` ancestor already on the
  app shell for the design tokens. It does not use generic bare class names that could leak into
  other tabs (no bare `.panel`, `.table`, `.row`, etc — those are legacy `App.css` names already in
  global use elsewhere and must not be touched or shadowed).
- All numeric values in JSX get the `mono-num` class (or use a primitive like `ReturnCell` /
  `Sparkline` that already applies it) — body/label text uses the default Public Sans, never mono.

Follow this same shape for `LedgerTab.jsx`: one outer root div (suggest class `v5-journal` or similar,
your call, just make sure the CSS is scoped to it), `SectionLabel` + `Panel`/table sections in flow,
tab-specific sub-components defined in the same file, a same-named `.v5.css` file with everything
prefixed to avoid leaking.

---

## 5. HARD CONSTRAINTS

1. **Output = exactly two complete drop-in files:**
   - `LedgerTab.jsx` — full rewrite of the JOURNAL tab body. Must keep the same default export
     name (`LedgerTab`) and the same props contract (zero props — `App.jsx` renders `<LedgerTab
     />` with nothing passed in).
   - `LedgerTab.v5.css` — layout-only CSS. **Every single selector must be scoped** so it only
     applies inside your tab's root wrapper (e.g. prefix everything `.v5-journal-...` or nest under
     a root class), because the tab content renders inside a `.v5` ancestor that already exists —
     do not redefine `.v5` itself or any token variable.

2. **Touch nothing else.** Do not edit or output `app.py`, `tokens.v5.css`, any file under
   `components/v5/`, `App.jsx`, `main.jsx`, `api.js`, or any other file. Import v5 primitives
   read-only, exactly as documented above. Do not rename/move/delete anything.

3. **Consume ONLY the existing endpoints shown in §2/§3** (`/api/journal`, `/api/desk/track-record`,
   `/api/desk/lessons`, via the existing `fetchJournal` / `fetchTrackRecord` / `fetchLessons`
   functions in `api.js` — call them exactly as they are, do not invent new params they don't
   accept). If your composition needs a field that is not in these payloads and cannot be derived
   client-side from what's given, **do not invent it and do not compute it client-side** — list it
   under "BACKEND FIELDS REQUESTED" in your reply instead.

4. **ONE-WRITER-FOR-RISK / one-writer-for-numbers:** every R value, win rate, expectancy figure,
   and P&L-adjacent number must come from the payload verbatim (formatted/rounded for display only —
   rounding for display is fine, e.g. `Math.round(n*10)/10`). Never compute a derived statistic the
   server didn't already compute (e.g. do not compute your own win rate from the trades array if
   `stats.win_pct` is null — that null IS the honest answer, render it as such).

5. **Honest states are the whole point of this screen:**
   - The journal has **1 open trade and 0 closed trades**. The equity curve, win rate, avg R, and
     expectancy must all render their genuine "not enough data yet" state — do not synthesize a
     placeholder curve or a fake percentage.
   - "SYSTEM EDGE (advanced)" content (which has real, larger-n data) must never visually
     outrank or crowd out the thin personal journal — keep it collapsed/secondary as today, or an
     equivalent progressive-disclosure pattern, and make sure a n=1 or n<20 cohort visibly reads as
     unfinished/building, not green/proven. Use the real `unproven`/`n`/`trust` fields for this,
     never a hardcoded threshold your own component invents beyond what's already in §3's payload
     (i.e. keep respecting `TRUST_FLOOR_N=20` server-implied semantics — the `unproven` field
     itself already encodes the important threshold logic for expectancy/screener rows).
   - Preserve the "Lessons diary" and digest empty states exactly as described (both are
     genuinely empty right now, not broken).
   - No synthetic chart series ever. Plain inline SVG (as the current `EquityCurve`/`RBar` do) or
     omit — no new chart library dependency.

6. **a11y AA on the light theme:** real visible `:focus-visible` styling on every interactive
   element (the disclosure toggle, any buttons you add), full keyboard operability, body text
   contrast ≥ 4.5:1 (do not use `--v5-ink-faint` for anything that isn't decorative), titled `"—"`
   for any null/unavailable numeric value (a `title` attribute explaining why, similar to
   `ReturnCell`'s `nullTitle`), and never convey meaning by color alone (e.g. win/loss must also
   have a `+`/`-` sign or textual label, not just green/red).

---

## 6. OUTPUT FORMAT

Reply with the two complete files in separate code blocks, then a short list of **BACKEND FIELDS
REQUESTED** and any assumptions you made. Your code will be reconciled and QC'd by the maintainer —
flag uncertainties rather than inventing.
