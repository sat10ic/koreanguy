# HANDOFF — rebuild the MANAS OS POSITIONS tab (v5 light design system)

You are receiving this as a complete, standalone brief. You have **no access to the repository** —
everything you need to write the code is embedded below (design tokens, component APIs, current
component inventory, real API payloads). Do not invent anything not given here.

Context: Manas OS is an NSE (Indian stock exchange) swing-trading desk tool. It is mid-way through
a UI overhaul from a dark "terminal" look to a new light "v5" design system. One screen at a time is
being rebuilt to the v5 language. **Your job is exactly one screen: the POSITIONS tab.** A second,
independent contractor (a different LLM) is rebuilding the JOURNAL tab in parallel — you do not need
to worry about that screen or touch any file it might touch.

---

## 1. GOAL

Rebuild the POSITIONS tab body to the v5 light design system, composed to hit this target
experience (quoted verbatim from the controlling design doc,
`manas_os/design/UI_OVERHAUL_HANDOFF.md` §5):

> ### POSITIONS — "What needs action now?"
> - Urgent EXIT/TRIM/MOVE STOP/HOLD is the first visual hierarchy.
> - Combine price/R path, stop, thesis state and management-template conformance in one lifecycle
>   canvas.
> - Replace every native prompt with validated dialogs/sheets; keep previous confirmed position
>   visible during mutation.

And from §5's UI-6 slice done-test:

> Build lifecycle canvas and validated mutation dialogs... user can manage and close a position
> without native prompts.

### §4 composition rules that bind on every v5 screen (quoted verbatim)

> - One dominant question, one dominant visual and one primary action per screen state.
> - Default to cardless sections, rails, bands, tables and annotated canvases. A card is allowed
>   only when it is the actual interactive object (candidate, position, saved scan).
> - Verdict and next action appear before metrics. Evidence is attached to the visual that proves
>   it, not separated into a legend/card farm.
> - Replace `[B]`/`[E]` markers with plain labels such as "Why this matters" and "Evidence & method."
> - Motion marks a real change once, then holds. Never animate P&L, stop, target, size or verdict.

Translated for POSITIONS specifically:
- A position IS the "actual interactive object" the §4 card exception names — a position-per-card
  layout is fine (the current code already does this and the design doc's §3 keep-list explicitly
  preserves "urgent-position sorting" and "R thermometer" as existing strengths, not defects). What
  needs to change is: the coach prose reads as generic-panel filler instead of decisive, and the
  card repetition/chrome needs v5 restraint (cardless internal structure inside the position card,
  not another stack of nested mini-panels).
- Coach verdict (EXIT/TRIM/MOVE_STOP/HOLD) + the plain-English action line must be the first thing
  in each card, ahead of entry/stop/qty metrics — this already happens in the current code
  (`VerdictHead` renders first) and must stay that way.
- Urgent (EXIT-now) positions must sort to the top of the list — already true today, keep it.
- No `[B]`/`[E]` bracket markers anywhere in your output (the current code has one literal `[B]`
  caption — `"[B] Use this as the daily hold/trim/exit instruction..."` — replace it with plain
  text, no bracket tag).
- **The one concrete interaction change required:** replace the two `window.prompt()` calls (edit
  stop, edit qty) with inline validated forms/sheets, per the hard constraints in §5 below.

---

## 2. CURRENT STATE (what exists today — read this before changing anything)

The tab is `manas_os/desk/src/PositionsTab.jsx`, default-exported as `PositionsTab`, taking one prop:
`date` (a `YYYY-MM-DD` string, passed down from the app shell's date scrubber). **Your two output
files must be named `PositionsTab.jsx` and `PositionsTab.v5.css`**, same default export name, same
single `date` prop.

### Element-for-element inventory of the current `PositionsTab.jsx`

Top-level structure:
1. **Toolbar** — one button, "Add position", opens the add-position form.
2. **`PositionForm`** (conditionally shown when adding) — plain HTML form: Symbol, Entry, SL, Qty,
   Date inputs, Submit ("Add") / Cancel buttons, inline error text on failure.
3. **Empty state** if `positions.length === 0`: "No open positions." / "Add a manual position or
   take a setup from the desk."
4. **List of `PositionCard`**, one per open position, **sorted urgent-first**
   (`(b.urgent?1:0)-(a.urgent?1:0)`).
5. **`CloseModal`** (conditionally shown, backdrop + centered form) when closing a position: exit
   price input, reason-tag select (`target|stop-hit|fear|need-cash|thesis-change|other`), Close
   (danger) / Cancel buttons, inline error text on failure.

### `PositionCard` internal structure (per position, top to bottom)

1. **`VerdictHead`** — FIRST element in the card (already correctly ordered per §5's "verdict
   before metrics" rule):
   - A verdict pill (`coach_verdict`, forced to "EXIT" display when `urgent` is true even if the
     raw verdict differs) with CSS class driven by `verdictClass()`: `exit|trim|move-stop|hold`.
   - The plain-English `action_line` next to the pill (or a fallback "EXIT NOW — day-low break +
     two-strike fired." if urgent and no `action_line`).
   - `pnl_rupees` (signed, ₹ prefix) + `pnl_pct` (signed, parenthesized) beside the verdict, colored
     by `colorScale()` (from `viz.js` — a shared red/green scale utility used across the app; you
     do not have this file, but the v5 primitives already replicate the same red/green semantics
     via `--v5-green`/`--v5-red`, so use those tokens directly rather than needing the utility).
   - **NOTE THE RUPEE SIGN:** the current code prints a literal `₹` character in JSX. Do NOT print
     `₹` to any console/log yourself while working — just know the app displays it inline; keep
     doing so with `₹` or `Rs` consistently in your JSX, your choice, but stay consistent within
     the file.
   - If `urgent`, an extra red "EXIT NOW: {fired.join(", ")} fired" sub-line.
2. **Card header row**: symbol name (large), a mono meta line "entry X / SL Y / qty Z / days held
   N", "SL today: {todays_stop}", and "Open R {±R}R" (colored by sign).
3. **`RThermometer`** — a horizontal rail with marks for stop / entry / current (derived from
   `entry + open_r * (entry - stop)`) / target (only if `position.target` is present — it currently
   never is in the live payload, see §3; render is correctly written to omit the target mark rather
   than fabricate one when absent — preserve that behavior).
4. **Action row**: three buttons — "Edit SL", "Edit qty" (both currently `window.prompt()` — **this
   is what you must replace**, see §5), "Close" (danger, opens `CloseModal`).
5. **Coach block**: `coachWhyText()` — prefers `advisor_note` (LLM narrative persisted nightly),
   falls back to `plain_why` (deterministic exit-engine text), falls back to "Coach read
   unavailable for this position (no priced sessions yet)." Below it, a caption line (currently the
   literal `[B]` marker — replace with plain text, e.g. "Use this as the daily hold/trim/exit
   instruction; no new LLM call is made from this screen."). If `advisor_note_stale` is true, an
   additional muted line quoting `advisor_note_stale_text` as a "stale note (superseded by
   verdict)".
6. **`RPathSparkline`** — a custom inline-SVG chart (not the shared `Sparkline` primitive — it needs
   phase-colored background bands (INITIATION/TREND/EXTENSION derived from each day's R value), a
   dashed trail-stop reference line, and the R-path polyline itself) built from `position.r_path`
   (array of `{date, r}`). Honest empty state: "R-path unavailable (no priced sessions yet)" when
   `r_path` is empty. You may keep this as tab-local custom SVG (it's specific enough that the
   shared `Sparkline` primitive, which only draws a plain single-color line from a bare number
   array, doesn't cover the phase-band + trail-stop-line requirements) — do not force-fit it into
   `Sparkline` if the composition would lose the phase bands or trail-stop line as a result; if you
   do simplify it, say so explicitly in your reply.
7. **R-path caption row**: "trail stop {trail_stop} / phase {phase}".
8. **Optional banner**: `position.banner` (mono text) if present (currently always null in the live
   payload — render it if truthy, don't remove the capability).
9. **Expert-mode-only** (`useDensity().isExpert`) additional block:
   - "fired: {fired.join(", ")}" if any fired rules.
   - A pointer line noting entry steps live on the DEBATE tab's trade-plan card, not repeated here.
   - `OriginalThesisBox` — renders `original_thesis.bull_case` as a quote + attribution
     (`agent, scan_date`), or "no agent thesis" when the thesis object only has a `note` field (as
     in the live payload today — see §3).
   - `TelegramMirror` — shows whether the nightly coach message was actually sent to Telegram
     ("sent HH:MM" / "dry-run: shown, not sent") plus the message body (first line stripped since
     it duplicates the coach-why text above it).

### Data fetching and every endpoint/mutation called

```js
import { addPosition, closePosition, fetchPositions, updatePosition } from "./api.js";
```

Mapping to real HTTP calls (from `manas_os/desk/src/api.js`) against the live API root
`http://127.0.0.1:8000`:

```js
export function fetchPositions(date) {
  return getJson("/api/desk/positions", { date });   // GET /api/desk/positions?date=YYYY-MM-DD
}
export function addPosition(payload) {
  return postJson("/api/desk/positions", payload);   // POST /api/desk/positions
  // payload: { symbol, entry, stop, qty, date } (strings from the form, server presumably coerces)
}
export function updatePosition(tradeId, payload) {
  return postJson(`/api/desk/positions/${tradeId}/update`, payload); // POST .../{id}/update
  // payload today: { stop: "<string>" } OR { qty: "<string>" } — one field at a time, from window.prompt
}
export function closePosition(tradeId, payload) {
  return postJson(`/api/desk/positions/${tradeId}/close`, payload); // POST .../{id}/close
  // payload: { exit_price: "<string>", reason_tag: "target"|"stop-hit"|"fear"|"need-cash"|"thesis-change"|"other" }
}
```

`postJson` throws `Error("<path> -> HTTP <status>")` (with `.status` set) on non-2xx — a 409 status
specifically means "an operation is already in flight," surfaced today only in `DebateTab`'s push
box, not currently handled specially in `PositionsTab` (you may add a friendly message for 409 on
these mutations if you want, but it's not required — no evidence the server returns 409 here).

`fetchPositions(date)` re-runs on every `date` prop change (with a `cancelled` guard against
stale responses). After every successful mutation (`addPosition`/`updatePosition`/`closePosition`),
the component calls `load()` again to refetch the full list — **keep this refetch-after-mutation
pattern**; it's how "keep the previous confirmed position visible during mutation" should mostly
already work today for the list overall, but the individual card being edited currently has no
visible pending/saving/error state of its own (the whole tab just sets a single shared `busy`
boolean disabling all buttons) — this is exactly the gap §5 wants fixed at the per-position level
(see hard constraint 5 below).

---

## 3. LIVE DATA (real payload, captured 2026-07-10, from the running API at 127.0.0.1:8000)

### `GET /api/desk/positions?date=2026-07-10`

There is **exactly 1 open position** in the live data (HUDCO, urgent EXIT). Full payload, verbatim,
every field kept (nothing trimmed — this is the entire array):

```json
{
  "run_date": "2026-07-11",
  "positions": [
    {
      "trade_id": 2,
      "symbol": "HUDCO",
      "trade_date": "2026-07-03",
      "entry": 218.0,
      "stop": 210.84,
      "qty": 100.0,
      "close": 206.96,
      "pnl_rupees": -1104.0,
      "pnl_pct": -5.06,
      "setup": "Pullback-to-EMA",
      "setup_family": "base/pattern",
      "phase": "INITIATION",
      "action": "HOLD — structure stop; wobble is normal",
      "action_line": "EXIT TODAY - 2 exit rules fired (stop-breached, below-21EMA). Sell the full position near the close.",
      "trail_stop": 210.84,
      "r": -1.54,
      "coach_verdict": "EXIT",
      "todays_stop": 210.84,
      "plain_why": "EXIT TODAY - 2 exit rules fired (stop-breached, below-21EMA). Sell the full position near the close.",
      "advisor_note": null,
      "advisor_note_stale": true,
      "advisor_note_stale_text": "No original thesis was recorded for this trade. The HOLD action is consistent with the Pullback-to-EMA setup; the stop at 210.84 has not been violated, and the current -1.54R wobble is within normal early-stage fluctuation.",
      "days_held": 5,
      "open_r": -1.54,
      "r_path": [
        { "date": "2026-07-03", "r": -0.341 },
        { "date": "2026-07-06", "r": -0.476 },
        { "date": "2026-07-07", "r": -1.021 },
        { "date": "2026-07-09", "r": -1.842 },
        { "date": "2026-07-10", "r": -1.542 }
      ],
      "fired": ["stop-breached", "below-21EMA"],
      "exit_now": true,
      "urgent": true,
      "banner": null,
      "original_thesis": { "note": "no agent thesis" },
      "coach": {
        "message": "HUDCO coach: HOLD - do nothing. Stop stays at 210.84. Wobble in the first few days is normal; the trade isn't wrong until the stop breaks.\nNo original thesis was recorded for this trade. The HOLD action is consistent with the Pullback-to-EMA setup; the stop at 210.84 has not been violated, and the current -1.54R wobble is within normal early-stage fluctuation.\n\"There is no such thing as a mental stop-loss. If it isn't a live order, it doesn't exist — a 50% drawdown has been traced to exactly this mistake.\" [TTM-D11, AR-Stop-Hit]\n\"Quantify fear with a number: the moment you assign the exact rupee amount you'll accept losing from the peak, the dread vanishes. You don't need to predict the top.\" [TTM-H-II3]\nsignal — manual execution only; not advice",
        "sent": false,
        "created_at": "2026-07-10 16:48:09"
      }
    }
  ]
}
```

**Notes on this payload:**
- `target` is **not present** in this object at all — confirms the current `RThermometer` code's
  comment is accurate ("payload carries none today") — do not fabricate a target mark on the
  thermometer.
- `original_thesis` is `{"note": "no agent thesis"}` — the empty-thesis shape, exactly what
  `OriginalThesisBox`'s truthy-`thesis.note` branch handles today. Keep handling this shape.
  `coach.message` **contains an embedded literal rupee amount is NOT present, but it does contain
  TradeTM source citations in `[TAG]` bracket form** (e.g. `[TTM-D11, AR-Stop-Hit]`) — these are
  legitimate content citations from the coaching corpus, NOT the `[B]`/`[E]` UI-marker pattern
  §4 asks you to remove; leave citation brackets inside the coach message text alone, only remove
  the `[B]` **UI caption marker** described in item 5 of the inventory above.
  - `action` (HOLD wording) vs `action_line`/`plain_why` (EXIT wording) genuinely disagree in this
  record — this is real, observed server behavior (the `urgent`/`coach_verdict:"EXIT"` fields win;
  `action` looks like a stale/lower-priority field). The current UI already resolves this correctly
  by trusting `coach_verdict`+`urgent`+`action_line` and never rendering the `action` field at all —
  **keep it that way**: do not surface `action` anywhere in your composition, it would contradict
  the verdict shown.
- Only one position exists, so you cannot visually verify multi-card stacking/sort order against
  real data — build the sort/stacking logic correctly per the spec (urgent first) and trust it.

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
  --v5-green:       #14713f;  /* literal TAKE / up / profit */
  --v5-green-dim:   #dcefe1;
  --v5-red:         #ad2c34;  /* literal SKIP / down / loss / EXIT */
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
`"./components/v5/index.js"` (relative to `PositionsTab.jsx`'s own directory,
`manas_os/desk/src/`). Full prop APIs (read from the actual source):

```jsx
// SectionLabel.jsx — italic Fraunces section header + gradient rule + optional count pill
<SectionLabel count={optionalNumberOrString}>Section title text</SectionLabel>

// Panel.jsx — bordered panel + header (title + right-aligned italic mono "cite" slot) + body.
// Use sparingly per §4's cardless rule — a position card itself may use Panel-like chrome since
// it IS the interactive object, but don't wrap every internal sub-block in its own nested Panel.
<Panel title="Panel title" cite="optional provenance string" className="optional-extra-class">
  {children}
</Panel>
// also exports: <PanelHeader title cite />

// StatusChip.jsx — small status chip (dot + label + value)
<StatusChip label="..." value={...} tone="neutral|green|amber|red" qual={bool} title={hoverTitle} dot={bool} />

// VerdictChip.jsx — TAKE/SKIP-shaped chip. NOTE: this component's tone logic is hardcoded to
// TAKE=green / anything-else=SKIP-red ("v5-take"/"v5-skip"), which does NOT match POSITIONS'
// verdict vocabulary (EXIT/TRIM/MOVE_STOP/HOLD). Do NOT force-fit this component for the
// coach-verdict pill — build your own small verdict pill in PositionsTab.jsx using the raw
// --v5-red/--v5-amber/--v5-green tokens with a tone mapping appropriate to EXIT(red)/TRIM(amber)/
// MOVE_STOP(amber)/HOLD(neutral-green-ish), matching the current verdictClass() semantics
// (exit|trim|move-stop|hold). This is a documented, intentional exception to "always reuse the
// primitive" — flag it in your reply as an assumption.
<VerdictChip verdict={"TAKE"|"SKIP"} struck={bool} conviction={0-4} showDots={bool} />

// ConvictionDots.jsx — 4-dot meter (unlikely needed for POSITIONS)
<ConvictionDots conviction={0-4} max={4} />

// Sparkline.jsx — pure-SVG plain single-color line sparkline from a bare numeric array
// (renders "—" if <2 points). Does NOT support phase-color bands or a dashed reference line —
// see the R-path note in §2 item 6; you likely need custom inline SVG for the R-path chart
// instead of this primitive, same as the current code does.
<Sparkline series={[...numbers]} width={72} height={22} />

// ReturnCell.jsx — signed %, green/red, mono tabular, "—" with title when null. Good fit for
// pnl_pct.
<ReturnCell value={numberOrNull} nullTitle="optional custom null explanation" />

// GateCellGrid / GateCell, SizerStamp, CallBanner, GatePassTag, LaneCard, MLBar, VoteBar,
// LensLane — all DEBATE/SCANNERS-specific, not expected to be relevant to POSITIONS. Skip unless
// you find a genuine fit; don't force one in.

// StruckNote.jsx — teal-edged quote block. Could be repurposed for the "original thesis" quote
// block or the stale-advisor-note callout if it fits your composition (both are quote-shaped
// content today) — optional, your call.
<StruckNote>{children text/markup}</StruckNote>

// CommandStrip.jsx / TickerTape.jsx — SHELL-OWNED, App.jsx already renders these above every tab.
// Do NOT render another CommandStrip or TickerTape inside your tab body.
```

If your composition needs a primitive that doesn't exist (e.g. the coach-verdict pill noted above,
or a stop/target rail styling for the R-thermometer), write small presentational sub-components
**inside your own `PositionsTab.jsx`** (not in `components/v5/`) — just don't duplicate what an
existing primitive already does.

### 4c. Reference pattern — how a shipped v5 tab is composed

`manas_os/desk/src/DebateTab.jsx` + `DebateTab.v5.css` is the one tab already rebuilt to v5 (you
cannot open these files, so here is their shape, described):

- The file imports the v5 primitives it needs from `./components/v5/index.js`, plus its own
  `./DebateTab.v5.css` (imported as a plain `import "./DebateTab.v5.css";` side-effect import at
  the top of the file, alongside the primitives import).
- The component body is organized as a flat sequence of `<SectionLabel>` headers followed by the
  section's content — e.g. `<SectionLabel>Market Context — Why We're Picky Tonight</SectionLabel>`
  then a grid of `<Panel>`s, then a table, etc. There is no single big wrapping card — sections sit
  directly in the page flow inside one outer root `<div className="v5-debate">`, and `SectionLabel`
  supplies the rhythm/hierarchy between them (this is the "cardless-by-default" rule from §4 in
  practice, at the page level — individual interactive objects like a symbol's deep-dive block are
  still visually distinct blocks, just not nested nano-panels for every sub-fact).
- Small presentational sub-components are defined in the same file (not extracted to `components/`)
  for anything tab-specific — e.g. a custom SVG gauge, a governor-status row, a foot-stats block —
  each a plain function component taking the relevant slice of the payload as props, doing pure
  derivation/formatting, and rendering JSX. Pure helper functions (`round()`, status derivations,
  etc.) sit above the components in the same file. **This is exactly the pattern to follow for
  `RThermometer`, `RPathSparkline`, `VerdictHead`-equivalent, `PositionCard`, etc. in your rebuild —
  keep them as in-file sub-components.**
- Loading/error/empty states are small early-return blocks at the top of the default-exported
  component, rendering inside the tab's own root class.
- The CSS file scopes every single selector so it only fires inside the tab, by prefixing every
  class with a tab-specific prefix (e.g. `.v5-debate`, `.v5-groww-block`, `.v5-lens-grid`) combined
  with the outer root div wearing that class, plus the ambient `.v5` ancestor already on the app
  shell for the design tokens. It does not use generic bare class names that could leak into other
  tabs (no bare `.panel`, `.position-card`, `.table`, `.row`, etc — those are legacy `App.css`
  names already in global use elsewhere and must not be touched or shadowed — pick fresh v5-prefixed
  names even where the old class name is similar, e.g. don't reuse `position-card`, use something
  like `v5-pos-card`).
- All numeric values in JSX get the `mono-num` class (or use a primitive like `ReturnCell` /
  `Sparkline` that already applies it) — body/label text uses the default Public Sans, never mono.

Follow this same shape for `PositionsTab.jsx`: one outer root div (suggest class `v5-positions` or
similar, your call), `SectionLabel`/toolbar/list sections in flow, tab-specific sub-components
(including the position card itself, the thermometer, the R-path chart, and your new inline edit
forms) defined in the same file, a same-named `.v5.css` file with everything prefixed to avoid
leaking.

---

## 5. HARD CONSTRAINTS

1. **Output = exactly two complete drop-in files:**
   - `PositionsTab.jsx` — full rewrite of the POSITIONS tab body. Must keep the same default
     export name (`PositionsTab`) and the same props contract: one prop, `date`.
   - `PositionsTab.v5.css` — layout-only CSS. **Every single selector must be scoped** so it only
     applies inside your tab's root wrapper, because the tab content renders inside a `.v5`
     ancestor that already exists — do not redefine `.v5` itself or any token variable.

2. **Touch nothing else.** Do not edit or output `app.py`, `tokens.v5.css`, any file under
   `components/v5/`, `App.jsx`, `main.jsx`, `api.js`, or any other file. Import v5 primitives
   read-only, exactly as documented above. Do not rename/move/delete anything.

3. **Consume ONLY the existing endpoints/mutations shown in §2/§3** (`fetchPositions`,
   `addPosition`, `updatePosition`, `closePosition`, calling exactly the routes and payload shapes
   documented — do not invent new query params or new POST fields the server doesn't already
   accept). If your composition needs a field that is not in the payload and cannot be derived
   client-side from what's given, **do not invent it and do not compute it client-side** — list it
   under "BACKEND FIELDS REQUESTED" in your reply instead.

4. **ONE-WRITER-FOR-RISK — this is the single most important rule for this screen.** Display
   server-provided `stop`/`todays_stop`/`trail_stop`/`qty`/`r`/`open_r`/`pnl_rupees`/`pnl_pct`
   verbatim (rounding for display only is fine). **NEVER compute or infer money math in the UI** —
   e.g. never compute your own P&L from `entry`/`close`/`qty` even though you technically could;
   always render the server's `pnl_rupees`/`pnl_pct` fields. The `RThermometer`'s `current` mark is
   the one existing exception where the current code already derives a display position
   (`entry + open_r * (entry - stop)`) purely for *plotting a dot on a rail*, not for stating a
   number anywhere as authoritative — that specific derivation is fine to keep (it's positional
   math for a chart, not a new financial figure presented as truth), but do not extend that pattern
   to anything else.

5. **Replace both native `window.prompt` calls with an inline validated form/sheet.** This is the
   concrete UI-6 requirement. Design the interaction with these explicit states per position card
   (or per active edit target):
   - **idle** — normal card, "Edit SL" / "Edit qty" buttons visible.
   - **editing** — clicking "Edit SL" (or "Edit qty") opens an inline form (not a native `prompt`,
     not necessarily a full-screen modal either — an inline expansion within the card, or a small
     anchored sheet, your call) pre-filled with the current value, with Save/Cancel actions and
     basic validation (numeric, and for stop specifically: reject a value that is not a sane number
     — the server is the real authority on business-rule validation, so client-side validation here
     should just prevent obviously malformed submissions, e.g. empty/non-numeric/negative, not
     attempt to replicate server risk rules).
   - **saving** — Save button shows a busy/pending state, inputs disabled, previous confirmed value
     stays visibly readable nearby (e.g. "current: 210.84" label) so the user isn't staring at a
     blank state while the mutation is in flight.
   - **error** — if `updatePosition` rejects, show the error inline in the same form (not a
     separate toast that could be missed), keep the form open with the user's entered value intact
     so they can retry, and the position's last-confirmed values must remain visible/unblocked
     elsewhere in the card the whole time (i.e. a failed stop-edit must not blank out the R
     thermometer or verdict head).
   - On success, close the inline editor and reflect the refetched value (existing `load()`
     refetch-after-mutation pattern — keep it).
   - Same idle/editing/saving/error state machine applies to the Close-position flow (replacing
     `CloseModal`'s current bare form — that one is already NOT a native prompt, it's a real modal,
     so you may keep it as a modal/sheet, but it should also gain the same saving/error inline
     handling instead of only a bare `formError` line at the bottom, and must keep the position
     visible behind/around it, not fully occlude ongoing context, during the save).

6. **Honest states / urgent-first ordering:**
   - Keep urgent (EXIT-now) positions sorted first, unconditionally.
   - Preserve every existing honest-empty-state string (no open positions, R-path unavailable, no
     coach signal sent yet, "no agent thesis") — reword for tone/consistency if you want, but the
     underlying null-handling logic (do not fabricate a chart, a thesis, or a coach message when
     the field is absent) must be preserved exactly.
   - No synthetic price/R series ever. Plain inline SVG (as current `RThermometer`/`RPathSparkline`
     do) or omit — no new chart library dependency.
   - No `[B]`/`[E]` bracket UI markers (see §2 item 5's specific literal-`[B]` caption to remove).
     TradeTM source citation tags embedded inside `coach.message` text (e.g. `[TTM-D11,
     AR-Stop-Hit]`) are content, not UI markers — leave those alone.

7. **a11y AA on the light theme:** real visible `:focus-visible` styling on every interactive
   element (buttons, form inputs, the new inline editors), full keyboard operability (the inline
   edit forms must be reachable/dismissable via keyboard, Escape should cancel an open editor),
   body text contrast ≥ 4.5:1 (do not use `--v5-ink-faint` for anything that isn't decorative),
   titled `"—"` for any null/unavailable numeric value, and never convey meaning by color alone
   (verdict pills need the text label EXIT/TRIM/MOVE_STOP/HOLD, not just a color; P&L needs the
   `+`/`-` sign, not just green/red).

---

## 6. OUTPUT FORMAT

Reply with the two complete files in separate code blocks, then a short list of **BACKEND FIELDS
REQUESTED** and any assumptions you made. Your code will be reconciled and QC'd by the maintainer —
flag uncertainties rather than inventing.
