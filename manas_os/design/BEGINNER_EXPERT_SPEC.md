# Beginner / Expert Progressive Disclosure — Build Spec

Status: authoritative build doc. A coding agent executes this without judgment calls.
Scope: the whole Manas AI Trading OS surface, present and incoming.
Owner intent: the Beginner/Expert switch is currently **cosmetic** (only `Read.jsx`
consumes `useDensity()`, and only to shrink a font; `RegimeSummary.jsx` renders XP /
MBI / breadth / participation / grid / quadrants / trend **unconditionally**). This spec
makes the switch **real** and redesigns the Regime beginner view to be genuinely
one-glance.

Grounded in the real code as of this writing:
- `frontend/src/DensityContext.jsx` — `density ∈ {"beginner","expert"}`, default `beginner`, `useDensity()`, `<DensityToggle/>`.
- `frontend/src/components/RegimeSummary.jsx` — renders PostureCommandBar → HomeSetupsPanel → FlipDial strip (XP/4.5R/MBI/Breadth) → ParticipationPanel → BreadthGrid → SetupStickers → MarketQuadrant → RegimeTrend → TechnicalDetail → DataStamp. **None of this is density-gated today.**
- `frontend/src/components/PostureCommandBar.jsx` — already the beginner-shaped verdict banner (badge + APPROACH line + Read). Keep as the beginner anchor.
- `frontend/src/components/Read.jsx` — the only current density consumer.
- `frontend/src/components/InfoDot.jsx` — glossary affordance + `GLOSSARY` map.

---

## 1. PHILOSOPHY — the single rule that decides every show/hide

> **THE RULE (`decision-per-screen`):** In Beginner mode, each screen shows exactly **one
> decision the user can act on right now**, stated as a plain-English verdict, plus the
> minimum evidence needed to trust that verdict. Everything that is *internals* — the raw
> numbers, ratios, grids, and secondary panels that *produced* the verdict — is hidden
> behind an explicit "Show details" affordance or unlocked by Expert mode. If an element
> does not change what the beginner does today, it is not on the beginner surface.**

Corollaries the coding agent applies mechanically:

- **B1. Plain-English always leads.** Every beginner-visible block leads with a word/sentence a non-trader understands ("Be aggressive today", "Sit out", "Strong earnings, gapping up"). Raw jargon numbers (20R, 50R, 4.5R, ADR, RS-rank, AVWAP) are **never** the primary content in Beginner.
- **B2. No unearned numbers.** A raw number appears in Beginner **only** when it is itself the decision (position size in shares, stop price, risk %, entry price). All *diagnostic* numbers are Expert-only.
- **B3. Glossary is on by default in Beginner.** Every domain term rendered in Beginner carries an `<InfoDot/>`. In Expert, InfoDots still exist but are quieter (see §2).
- **B4. One decision per screen.** Beginner screens do not present competing calls-to-action. Regime → "how aggressive today". Setups → "which one, and the plan". Watchlist → "hold or exit". Journal → "am I improving".
- **B5. Same data, less of it.** Beginner and Expert read the **same** API payload. The toggle only changes *how much is rendered and how it is labeled* — never the underlying values, never the safety/stale states.

Expert mode is the strict superset: everything Beginner shows **plus** raw values, extra
columns, secondary panels, and `technical_detail` expanded by default. Expert never hides
anything Beginner shows.

---

## 2. WHAT THE SWITCH ACTUALLY TOGGLES — concrete mechanics

`useDensity()` returns `density`. Define a derived boolean at the top of every
density-aware component:

```js
const { density } = useDensity();
const expert = density === "expert";
```

The toggle drives **six independent axes**. Each axis is a mechanical transform; a
component may use one or several.

### Axis A — Label swap (jargon ⇄ plain)
Introduce a single shared map so labels are DRY. Create
`frontend/src/densityLabels.js`:

```js
// Plain label (beginner) ⇄ technical label (expert). One source of truth.
export const LABELS = {
  posture:      { plain: "Today's game plan",     tech: "Market posture" },
  xp:           { plain: "Market energy",          tech: "XP dial" },
  r4p5:         { plain: "Big-mover balance",      tech: "4.5R burst" },
  mbi:          { plain: "Day color",              tech: "MBI" },
  breadth20:    { plain: "How many stocks are healthy", tech: "Breadth 20d" },
  readiness:    { plain: "Match strength",         tech: "Readiness" },
  ep:           { plain: "Earnings surprise",      tech: "EP" },
  ants:         { plain: "Quiet accumulation",     tech: "ANTS" },
  avwap:        { plain: "Big-money average price", tech: "AVWAP" },
  rs:           { plain: "Leadership vs market",   tech: "RS line" },
  exit_state:   { plain: "Trade health",           tech: "Exit state" },
};
export const labelFor = (key, expert) => (LABELS[key]?.[expert ? "tech" : "plain"] ?? key);
```
Every component renders `labelFor("xp", expert)` instead of a hardcoded string.

### Axis B — Panel visibility (hide/show whole sections)
Beginner renders only the panels in each screen's **BEGINNER set** (§3). Expert renders
the full set. Implement as a plain conditional, **not** CSS `display:none` (do not ship
hidden DOM):
```jsx
{expert && <ParticipationPanel />}
{expert && <BreadthGrid />}
{expert && <TopIndicesPanel />}
{expert && <RegimeTrend />}
```

### Axis C — Numeric-internals collapse
Diagnostic numbers (the FlipDial strip, MBI ratio rows, raw score components) are **not
rendered inline in Beginner**. They move behind a single `<ShowDetails>` expander
(collapsed by default in Beginner) OR are Expert-only. See §3 Regime for exact placement.
Create one reusable expander `frontend/src/components/ShowDetails.jsx`:
```jsx
export default function ShowDetails({ label = "Show the numbers", testid, children }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="mt-2" data-testid={testid}>
      <button onClick={() => setOpen(v => !v)} data-testid={`${testid}-toggle`}
        className="font-mono text-[9px] uppercase tracking-overline text-ink3 hover:text-ink2">
        {open ? "▾ hide the numbers" : `▸ ${label}`}
      </button>
      {open && <div className="mt-1">{children}</div>}
    </div>
  );
}
```

### Axis D — Column sets (tables)
Tables (Setups feed, Watchlist, Journal) expose `beginnerColumns` vs `expertColumns`
arrays. Beginner shows the decision columns only; Expert appends the diagnostic columns.
Never two table components — one component, one `columns = expert ? EXPERT_COLS : BEGINNER_COLS`.

### Axis E — technical_detail default state
The `technical_detail` audit string (var=value trail) exists on many payloads. In
Beginner it is **collapsed** (current `TechnicalDetail` behavior — keep). In Expert it is
**expanded by default**. Pass `defaultOpen={expert}` into `TechnicalDetail`.

### Axis F — InfoDot prominence
Beginner: InfoDots render at full affordance (current styling). Expert: InfoDots still
render (never remove the glossary) but at reduced opacity so they don't clutter a dense
view. Add to `InfoDot`:
```jsx
const { density } = useDensity();
// beginner: default; expert: dimmer, same behavior on hover/click
className={`... ${density === "expert" ? "opacity-40 hover:opacity-100" : ""}`}
```

**Density-awareness is opt-in per component but required for every listed surface.** The
QC gate (§6) fails the build if a listed component does not import `useDensity`.

---

## 3. PER-SCREEN SPEC

For every screen: BEGINNER view (exact elements, plain language) and EXPERT ADDS (the
superset delta). Failure and stale states are identical in both modes and listed once.

### 3.1 REGIME (flagship redesign — the complaint)

**The ONE thing a beginner needs here: "How aggressive can I be today, and why —
and what do I do with it."** Everything else is internals.

`RegimeSummary.jsx` must become density-aware. It currently is not. Rewrite render order:

#### BEGINNER view — top to bottom, nothing else:
1. **PostureCommandBar** (keep as-is; it is already the verdict banner). This is the
   answer: big badge (Risk-On / Selective / Defensive / No-Trade) + the concrete APPROACH
   line ("trade up to 5 positions, full size, A & B setups. Risk 0.5–1.0% per trade.") +
   the one-sentence `Read`. Keep the DivergenceFlag caution in its footer.
2. **Three plain supporting sentences** (new small block, `data-testid="regime-why"`),
   generated from fields already in the payload — no new numbers surfaced:
   - Sentence 1 (breadth): *"Most stocks are healthy — {N} out of 100 are trading above their recent average."* (derive N = rounded `breadth_20dma_pct`; if null, omit the count and say "Breadth data unavailable.")
   - Sentence 2 (energy trend): *"Market energy is {rising/steady/fading} and currently {low/building/strong/extreme}."* (direction from XP since-yesterday delta sign; band from `xpBand`.) **No XP number shown.**
   - Sentence 3 (swing verdict): reuse the existing `HomeSetupsPanel` verdict word — *"Short-term trades are {swing-friendly / picky / better to sit out} right now."*
3. **HomeSetupsPanel** (keep) — the top ≤5 quality-gated setups as the actionable next
   step. This is the bridge from "how aggressive" to "on what". Each card stays plain:
   symbol, readiness number (this number is *earned* — it's a decision input), one-line read.
4. **`<ShowDetails label="Show the numbers">`** — collapsed. Inside it, and **only**
   inside it in Beginner, render the FlipDial strip (XP / 4.5R / MBI ratios / Breadth
   sparkline). A curious beginner can peek; it is never forced.
5. **Stale / failure states** (see below) render in place of everything above when active.
6. **DataStamp** (keep, always).

Everything else — **ParticipationPanel, BreadthGrid, SetupStickers, MarketQuadrant grid,
RegimeTrend, TopIndicesPanel, SectorsThemesPanel, expanded technical_detail — is NOT
rendered in Beginner.**

#### EXPERT ADDS (render in this order, after the beginner block, FlipDial strip promoted inline):
- FlipDial strip rendered **inline** (not inside ShowDetails) with full XP value + band, 4.5R burst value + sparkline, MBI day-color chip + the 20R/50R/4.5R numeric ratio rows + action copy, Breadth-20d sparkline.
- **ParticipationPanel** (60-session participation chart).
- **BreadthGrid** (20-session breadth color grid).
- **SectorsThemesPanel** (sectors & themes leaderboard + perf-flip).
- **TopIndicesPanel** (top-indices panel).
- **MarketQuadrant** grid (Momentum / Swing / Trend / Bias cards).
- **RegimeTrend** (regime-history).
- **`technical_detail`** expanded by default (`defaultOpen={true}`).

Net effect: Beginner Regime = one verdict + three sentences + the setups to act on + an
optional "show the numbers" peek. Expert Regime = today's full cockpit.

### 3.2 SETUPS

- **BEGINNER:** confluence-ranked feed as cards. Each card: symbol, **one readiness
  number** (0–100, earned), a plain-English one-line read, and — when a card is
  selected/expanded — the **trade-plan advisor** in plain terms (entry price, stop price,
  risk-reward as "risk ₹X to make ₹Y", position size in shares, one "watch for" line).
  Evidence chips render as **plain-language chips** (see §4). No score-breakdown table.
- **EXPERT ADDS:** the numeric **score-breakdown** (each filter → points contributed),
  raw evidence values on chips, extra columns if rendered as a table (RS-rank, ADR, RVOL,
  dist-to-pivot), and `technical_detail` expanded.

### 3.3 FOCUS CENTER (new — IPO + EP filtered lens)

- **BEGINNER:** two labeled shelves — "New listings setting up" (IPO-base) and "Big
  earnings surprises" (EP) — each a short list of plain cards (symbol + one plain read +
  readiness). A one-line explainer at top of each shelf ("Recently-listed stocks forming
  their first tradeable pattern." / "Stocks that just beat earnings and are being bought.").
- **EXPERT ADDS:** the raw qualifying metrics per card (EPS/sales growth %, gap %, base
  depth/length, days-since-listing), sort/filter controls, and the score-breakdown.

### 3.4 WATCHLIST

- **BEGINNER:** one row per name. Columns (`BEGINNER_COLS`): symbol, **trade health**
  (plain badge from exit-state engine: **Healthy / Weakening / Exit** — mapping Intact→Healthy,
  Weakening→Weakening, Broken→Exit), and one plain action line ("Holding fine." /
  "Losing strength — tighten your stop." / "Broke down — plan your exit."). When adding a
  new name, the **position sizer** shows only the decision outputs: shares to buy, stop
  price, risk in ₹.
- **EXPERT ADDS (`EXPERT_COLS` append):** entry-timing metrics (dist-to-pivot, RVOL,
  ADR), the raw exit-state internals (which MAs/levels broke), AVWAP value, RS-line
  reading, and the sizer's full math (R-multiple, account-risk %).

### 3.5 JOURNAL

- **BEGINNER:** the one question — "Am I improving?" Show a single plain expectancy verdict
  ("Your system is making money over time." / "You're losing money on average — review
  your mistakes.") plus the mistake-tag list as plain chips with counts. Trades list shows
  symbol, in/out, result in ₹ and R.
- **EXPERT ADDS:** the numeric expectancy value (avg R/trade), win-rate, payoff ratio,
  per-tag expectancy breakdown, and full per-trade columns.

### 3.6 CHART DRAWER

- **BEGINNER:** candles + volume + EMAs, the **buy-zone / stop** shaded band, and
  entry/exit arrows. A one-line caption under the chart in plain English ("Buy zone
  ₹X–₹Y, stop below ₹Z."). Advanced overlays are **off by default**.
- **EXPERT ADDS (toggleable overlays, on by default in Expert):** pocket-pivot markers,
  AVWAP line, RS-line, TTM histogram, and a legend with raw values. Provide an overlay
  toggle rail; in Beginner the rail is collapsed under "More overlays".

### Shared FAILURE / STALE states (identical in BOTH modes — never gated)
- **Stale data:** PostureCommandBar shows "Stale" badge + "wait for fresh data before
  sizing risk"; strip greys out (`opacity-60 grayscale`). The stale verdict overrides the
  posture in both modes.
- **API unreachable:** the existing `EmptyBlock "Couldn't reach the API"` with the run
  command. Same in both modes.
- **No snapshot / no setups:** existing `EmptyBlock` / `Read band="muted" verdict="NO SETUPS"`.
  Same in both modes.
- Safety states are **never** dependent on `density`. A beginner must never be shielded
  from a risk-off or stale signal.

---

## 4. HOW EACH NEW ADVANCED FEATURE DEGRADES

Each new signal ships with a `beginner` string and an `expert` string. Put these in a
shared `frontend/src/signalCopy.js` so the same signal reads identically everywhere it
appears (chip, card, drawer). Pattern:

```js
export function describeSignal(kind, raw, expert) { /* returns string */ }
```

| Signal | BEGINNER label (plain) | EXPERT detail (raw) |
|---|---|---|
| **EP** (earnings-power gap) | "Strong earnings surprise, gapping up" | "EP: EPS +45%/+38% QoQ/YoY, sales +31%, gap +6.2%" |
| **IPO-base** (mini-coil / TVCP) | "New listing tightening up — first real base" | "IPO-base: mini-coil, 11% deep, 18 sessions, TVCP contraction 3→1.4%" |
| **ANTS** (accumulation) | "Being quietly accumulated" | "ANTS: 12/15 up-closes, +38% over 15d on rising volume" |
| **Absolute-Strength chip** | "Trending up on its own, not just vs market" | "AbsStr: +22% / 20d, above rising 21EMA" |
| **EPS-growth chip** | "Fast-growing earnings" | "EPS +45% latest Q, 3-Q accel" |
| **Exit-state engine** | "Trade health: Healthy / Weakening / Exit" | "Exit: Intact / Weakening (lost 21EMA) / Broken (below stop + 50EMA)" |
| **AVWAP auto-anchor** | "Trading above big-money average price" | "AVWAP (anchored {event} {date}): ₹X, price +3.1% above" |
| **Readiness score-breakdown** | one number 0–100 + "matches N of its named checks" | full table: each named filter → points contributed, with raw values |

Rules for the degrade:
- Beginner string = **verdict + direction**, no raw magnitude. Expert string = the raw
  magnitudes that produced it.
- The Beginner string always carries an `<InfoDot term="..."/>`; add glossary entries to
  `GLOSSARY` in `InfoDot.jsx` for every new term (`ep`, `ipo-base`, `ants`, `abs-strength`,
  `eps-growth`, `exit-state`, `avwap`). One-line definitions, plain English.
- Both strings derive from the **same** payload fields — never compute a beginner-only or
  expert-only value.

---

## 5. ONBOARDING / FIRST-RUN — the 30-second "what do I do today" flow

Goal: a first-time beginner is never dropped into a cold cockpit. Minimal, skippable,
never gamified.

**First run (detected via `localStorage "manas_seen_v1"` absent):** a 3-step inline
coach-mark sequence overlaid on the real Regime screen (not a separate tour page — anchor
to the actual elements so the user learns the surface):

1. **Step 1 → PostureCommandBar:** "Start here. This tells you how aggressive to be
   today and exactly how many trades and what size." [Next]
2. **Step 2 → the three "why" sentences:** "This is *why* — in plain English. Tap any ⓘ
   to learn a term." [Next]
3. **Step 3 → HomeSetupsPanel:** "These are today's best candidates. Pick one to see its
   plan (entry, stop, size)." [Got it]

On dismiss, set `localStorage.manas_seen_v1 = "1"`. Add a persistent "Replay intro" link
in the header/settings so it's re-triggerable.

**Daily "what do I do today" strip (always present, both modes, Regime top):** a single
sentence assembled from posture + setups count:
> *"Today: {posture verdict}. {n} setups passed the filter — {trade up to X / be picky /
> sit out}."*
This is the 30-second answer even before scrolling.

The onboarding shows **only in Beginner default**; if the user has flipped to Expert it is
suppressed (an Expert self-selected out of hand-holding).

---

## 6. ANTI-MASHUP + CONSISTENCY GUARDRAILS

The toggle is a **presentation layer over one data source**. It must never fork logic or
create two codebases.

- **G1. One component per surface.** Never `RegimeBeginner.jsx` + `RegimeExpert.jsx`. Each
  component reads `useDensity()` and branches on `expert` internally. Panel visibility is a
  conditional render inside the *same* component.
- **G2. One data fetch.** Beginner and Expert call the **same** API endpoints with the
  **same** params. The density flag never reaches the network layer. No density-conditional
  fetching, no beginner-only or expert-only payload.
- **G3. Shared copy maps.** `densityLabels.js` (labels) and `signalCopy.js` (signal
  strings) are the single source of truth. A label/signal is defined once; both modes read
  from the same map. No inline hardcoded jargon in components.
- **G4. Derived, not stored, verdicts.** Plain-English verdicts (posture approach, exit
  health, expectancy sentence) are computed from payload fields by pure helper functions
  reused across screens — not duplicated per component and not persisted differently per mode.
- **G5. What must NEVER differ between modes:**
  - the underlying numeric values (a readiness of 72 is 72 in both; Beginner just doesn't
    show the breakdown),
  - the **stale / degraded / no-data / risk-off safety states** (§3 shared states),
  - the set of candidates that pass the quality gate,
  - which posture / exit-state is active.
  Only *rendering depth and labeling* differ.
- **G6. DRY test:** the QC gate greps every listed surface component for `useDensity`
  import; any surface component that renders diagnostic numbers unconditionally (like
  today's `RegimeSummary`) fails review.

---

## 7. THE ONE THING TO NOT DO

**Do NOT dumb down in a way that hides risk, and do NOT add a third mode.** Specifically:

- Never suppress a stale, degraded, risk-off, or "sit out" signal to keep the beginner
  view "clean". Safety states are mode-independent (G5). Hiding a caution to reduce clutter
  is the one unforgivable failure.
- No third "intermediate" mode, no per-panel density sliders, no gamified XP-points /
  streaks / confetti onboarding. Two modes, one binary, presentation-only. Progressive
  disclosure is achieved by the `<ShowDetails>` expander within Beginner — not by
  proliferating modes.

---

## 8. IMPLEMENTATION CHECKLIST (execution order for the coding agent)

1. Add `frontend/src/densityLabels.js` (`LABELS`, `labelFor`).
2. Add `frontend/src/signalCopy.js` (`describeSignal`).
3. Add `frontend/src/components/ShowDetails.jsx`.
4. Make `InfoDot.jsx` density-aware (Axis F) + add new glossary terms (§4).
5. **Rewrite `RegimeSummary.jsx` render body to branch on `expert`** per §3.1 — this is the
   headline fix that makes the toggle non-cosmetic. Add the `regime-why` three-sentence
   block and wrap the FlipDial strip in `<ShowDetails>` for Beginner / inline for Expert.
   Gate ParticipationPanel / BreadthGrid / SectorsThemesPanel / TopIndicesPanel /
   MarketQuadrant / RegimeTrend behind `expert`.
6. Make SetupsPage, FocusCenter, WatchlistPage, JournalPage, ChartDrawer density-aware per
   §3.2–3.6 (label swap + column sets + hide diagnostic blocks).
7. Add the first-run coach-marks + daily "what do I do today" strip (§5).
8. QC gate (§6 G6): CI grep asserting every surface component imports `useDensity`, and a
   snapshot test that Beginner Regime renders **no** ParticipationPanel/BreadthGrid/
   TopIndices/RegimeTrend DOM while Expert does; and that stale/no-data states render
   identically under both densities.

**Acceptance:** flipping Beginner→Expert on the Regime screen must visibly add the
FlipDial strip inline, the participation chart, the breadth grid, the sectors/indices
leaderboards, the quadrant grid, and the regime-history — while Beginner shows only
posture + three sentences + setups + an optional "show the numbers" peek. Same payload,
same numbers, same safety states.
