# UI BUILD SPEC v1 — element-by-element, non-skippable

**Audience:** any LLM or engineer implementing the desk UI.
**Status:** authoritative. Supersedes ad-hoc UI instructions in prior handoffs.
**Source material:** `trading_tool_ui_ux_feature_audit_CONSOLIDATED.md` (design
direction, owner-supplied) + `AUDIT_2026-09-01_METRICS_AND_CURRENCY.md`
(data-correctness findings) + live verification of the running app.

---

# PART 0 — RULES OF ENGAGEMENT (read before writing any code)

## 0.1 The completion protocol — this is not optional

Every task in this document has an ID like `H1-03`. When you finish work, you
**must** output a completion table covering **every ID in the document**, with
one of exactly three statuses:

```
DONE      — implemented and the acceptance test passes
BLOCKED   — cannot be done; you must state the specific blocker
SKIPPED   — deliberately not done; you must state why
```

A task you did not attempt is `SKIPPED`, not omitted. **Silently omitting IDs
is the single failure mode this document exists to prevent.** If your report
does not account for every ID, the work is not finished.

## 0.2 Anti-fabrication rules (highest priority — violating these is worse than not building)

1. **Never invent a number.** Every value on screen must trace to a field in
   `tonight_<date>.json`, `outcomes_<date>.json`, `stock_history_<date>.json`,
   `research_coverage_<date>.json`, or `settings_<date>.json`.
2. **Never zero-default.** A missing score renders as `—`, never `0`. A `0`
   reads as a real verdict.
3. **Never hardcode a market figure** in a `.ts`/`.tsx` file. If you find one,
   delete it and read the real field.
4. **Never blend fabricated rows into a real list.** This already caused real
   harm: a fixture claiming TRENT at ₹6120 when the real close was ₹2898.
5. If a required field does not exist, the correct action is an **honest empty
   state** naming what is missing — not a plausible-looking substitute.

## 0.3 Beginner vs Pro — the contract

```
BEGINNER = interpretation first, jargon hidden
PRO      = interpretation PLUS every raw metric
```

Pro mode must never show **less** than Beginner. The toggle changes cognitive
load, never capability. Engineering strings (`raw scan signals`, `liveness
gate`, `breadth_only`, `derived CA view`, `pass in loop`) are **Pro-only or
diagnostics-only**, never in Beginner.

## 0.4 Visual direction (applies to every screen)

Target: **Financial Times data graphics × Linear restraint × Bloomberg
density**. Editorial, ruled sections, typographic hierarchy.

**Do not** use: rounded card grids of one number each, gradients, glows,
decorative icons, rainbow metric colours.

**Do** use: thin rules, aligned numeric columns, tabular layouts, inline bars,
sparklines, one restrained accent.

Colour semantics — the only permitted meanings:
```
white/grey  neutral        green  positive
red         negative       amber  caution / regime
muted blue  informational
```
Never colour a metric that carries no directional meaning.

Typographic hierarchy, in order of weight:
```
1. market state / action verdict
2. numeric value
3. metric label
4. source / provenance
```

## 0.55 IMPLEMENTATION CONVENTIONS — read this before any UI task

This section exists so a task like "render the breadth analytics" is
mechanically executable without design judgement. **Every UI task in this
document assumes you have read this section.**

### A. Exact data-access expressions

The report is already typed and exported. Do **not** re-import raw JSON.

```ts
// unidesk_terminal/src/data/tonight.ts already exports:
import {
  TONIGHT_REPORT,        // TonightReport  — the whole parsed report
  REAL_CANDIDATES,       // Candidate[]    — mapped candidate rows
  REAL_SESSION,          // {date, asOf, universeScanned, ...}
  REAL_HONESTY_FOOTER,   // string[]
  TONIGHT_JSON_FILENAME,
} from "../data/tonight";

import { DEFAULT_REPORT, getReport, getAvailableSessions }
  from "../data/reportRegistry";
```

Field paths you will need, verbatim:

```ts
const hf = TONIGHT_REPORT.honesty_footer;

hf.pct_above_ema50                      // 56.4
hf.above_ema21 / hf.above_ema21_of      // 676 / 1295
hf.universe_scanned                     // 1295
hf.universe_skipped_insufficient_history
hf.universe_gate_skips_total
hf.universe_gate_skips                  // {turnover_floor: n, price_floor: n, ...}
hf.regime_note                          // "CHOP (breadth 56.4% ...)"
hf.regime_built                         // true
hf.actions_applied                      // 4
hf.adjusted_symbols                     // 2
hf.breadth.near_highs_pct               // 8.6
hf.breadth.near_lows_pct                // 4.2
hf.breadth.analytics.net_nh_nl          // 0.1544...
hf.breadth.analytics.up_down_close_pct  // 72.897...
hf.breadth.analytics.volume_ratio       // 0.3339...
hf.breadth.analytics.volatility_ratio   // 0.5473...
hf.breadth.analytics.bo_bd_ratio        // null  → render "—"

// per candidate (raw shape, before toCandidate mapping)
c.symbol, c.close, c.detector, c.setup_title, c.trend, c.sessions
c.adr_pct, c.rs_rank, c.rvol, c.contraction, c.delivery_ratio
c.trigger, c.invalidation, c.rr
c.stock_quality.score, c.stock_quality.coverage, c.stock_quality.unknowns
c.setup_quality, c.entry_quality, c.geometry_notes
c.activity_score.activity_score         // Reactor Scale
c.trust.status, c.trust.reason, c.trust.version, c.trust.rankable

TONIGHT_REPORT.base_episodes            // BaseEpisode[]  (D-07)
TONIGHT_REPORT.setups                   // grouped setup blocks
```

**Rule:** if a field is not in the list above, it does not exist. Check PART 1.2
before assuming otherwise, and mark the task `BLOCKED` naming the field.

### B. Components that already exist — reuse, do not rebuild

| Component | Path (under `src/`) | Use it for |
|---|---|---|
| `Sparkline` | `components/ui/Sparkline.tsx` | `H2-03` row sparklines, `H1` trend strips |
| `Chip` | `components/ui/Chip.tsx` | states (`READY`, `WATCH`), tone via `tone` prop |
| `FilterChip` | `components/ui/FilterChip.tsx` | Candidates filters (`C-05`) |
| `ScrollRail` | `components/ui/ScrollRail.tsx` | horizontal overflow |
| `VintageBadge` | `components/ui/VintageBadge.tsx` | data-vintage marking |
| `QualityStack` | `components/widgets/QualityStack.tsx` | `H2-05`, `S-01` — **currently zero-defaults, fix per `H2-05`** |
| `ContributorBars` | `components/widgets/ContributorBars.tsx` | score decomposition |
| `RegimeStrip` | `components/widgets/RegimeStrip.tsx` | `H1-02` position strip |
| `HonestyFooter` | `components/widgets/HonestyFooter.tsx` | `G-07` drawer, `H4-08` |
| `CandidateCard` | `components/widgets/CandidateCard.tsx` | replace per `H2-02` |
| `CandidateScatter` | `components/widgets/CandidateScatter.tsx` | `C-03` landscape |
| `DecisionCard` | `components/widgets/DecisionCard.tsx` | `S-01` verdict |
| `SetupEvidencePanel` | `components/widgets/SetupEvidencePanel.tsx` | `S-08` |
| `StockChart` | `components/widgets/StockChart.tsx` | `S-06` — gate on real history |
| `AppShell` / `LeftRail` / `TopBar` | `components/shell/` | `G-02`, `X-01` new nav entry |

`Sparkline` signature (do not change it):
```ts
<Sparkline values={number[]} width={96} height={28}
           color="var(--text-secondary)" fill={false} strokeWidth={1.5} />
```

Helpers: `lib/ohlc.ts` (`ema`, `anchoredVwap`, `generateOhlc` ← synthetic, gate
it), `lib/status.ts` (`LIFECYCLE_META`), `lib/sessionCoherence.ts`.

### C. Design tokens — use these, never hardcode px or hex

```
font    --font-sans  --font-mono
size    --text-caption 11  --text-body 14  --text-h4 16  --text-h3 18
        --text-h2 22  --text-h1 28  --text-display 44
space   --spacing-1 4 … --spacing-16 64
radius  --radius-chip 6  --radius-card 10  --radius-modal 16
colour  --surface-0/1  --text-primary/secondary/tertiary/muted  --border*
```
Numeric columns use `font-mono-num`. Prefer existing Tailwind semantic classes
already present in the codebase (`text-ink-primary`, `bg-surface-1`,
`border-border`, `rounded-card`, `text-caption`) over new ones.

### D. Worked example — how to execute one task correctly

Task `H1-05` (surface breadth analytics). A correct implementation:

```tsx
// src/components/widgets/BreadthAnalytics.tsx   (new file)
import { TONIGHT_REPORT } from "../../data/tonight";

const ROWS = [
  { key: "net_nh_nl",          label: "NH-NL balance",   fmt: (v: number) => v.toFixed(3) },
  { key: "up_down_close_pct",  label: "Up/Down close",   fmt: (v: number) => `${v.toFixed(1)}%` },
  { key: "volume_ratio",       label: "Volume ratio",    fmt: (v: number) => v.toFixed(3) },
  { key: "volatility_ratio",   label: "Volatility ratio",fmt: (v: number) => v.toFixed(3) },
  { key: "bo_bd_ratio",        label: "BO/BD ratio",     fmt: (v: number) => v.toFixed(3) },
] as const;

export function BreadthAnalytics() {
  const a = TONIGHT_REPORT.honesty_footer.breadth?.analytics;
  if (!a) return null;                       // absent → omit section (PART 1.3)
  return (
    <div className="border-t border-border pt-3">
      <h3 className="text-caption uppercase text-ink-tertiary">Market breadth</h3>
      <dl className="mt-2 grid grid-cols-[1fr_auto] gap-y-1">
        {ROWS.map(r => {
          const v = a[r.key as keyof typeof a] as number | null | undefined;
          return (
            <div key={r.key} className="contents">
              <dt className="text-caption text-ink-secondary">{r.label}</dt>
              <dd className="font-mono-num text-body text-ink-primary">
                {v === null || v === undefined ? "—" : r.fmt(v)}
              </dd>
            </div>
          );
        })}
      </dl>
    </div>
  );
}
```

Note what makes this correct: real field path, `null → "—"` (never `0`), whole
section omitted when absent, tokens not hex, no invented label.

### E. Verification loop for every UI task

```bash
cd unidesk_terminal && npm run build     # must exit 0, zero TS errors
npm run dev                              # then open the screen and LOOK at it
```
A task is not DONE until you have rendered the screen and confirmed the
acceptance criterion visually. "It compiles" is not acceptance.

## 0.5 Dependency order — build in this sequence

```
PART 1 (data contract)  →  PART 2 (global)  →  PART 9 (backend)
                        →  PART 3..8 (screens, any order)
```
PART 9 backend tasks unblock several screen tasks; read PART 9 before starting
screens so you know which fields will exist.

---

# PART 1 — DATA CONTRACT

## 1.1 Fields that EXIST TODAY in `tonight_<date>.json`

Per candidate (verified present on 73/73 unless noted):

```
symbol           string
close            number     verified correct vs raw bhavcopy, 0 mismatches/73
detector         string     base_breakout|episodic_pivot|inside_bar|ipo_base|
                            momentum_burst|pullback|reversal_reclaim
setup_title      string
trend            string     STRONG_UPTREND|UPTREND|...
sessions         int        history depth used (see PART 9 — currently capped)
adjusted         bool       was this symbol CA-adjusted
adr_pct          number     verified: 1 deviation / 73
rs_rank          number     0-100 percentile — SEE PART 9, currently unsafe
rvol             number     max 8.83, median 0.48
contraction      number
delivery_ratio   number
trigger          number     entry level
invalidation     number     stop level
rr               number     72/73 present; median 1.26, 44% below 1.0
stock_quality    object     {score, coverage, unknowns[], ...}
setup_quality    object
entry_quality    object
activity_score   object     {activity_score, q_ratio, d_ratio, ...}  Reactor Scale
trust            object     {status, reason, version, rankable}
geometry_notes   —          present
```

Top level:
```
session_date, as_of, schema_version, candidates[], setups[],
base_episodes[], detector_trust, honesty_footer
```

`honesty_footer`:
```
universe_scanned, universe_skipped_insufficient_history,
universe_gate_skips{}, universe_gate_skips_total,
pct_above_ema50, above_ema21, above_ema21_of,
regime_note, regime_built,
actions_applied, adjusted_symbols, adjustment_status, adjustment_note,
breadth{near_highs_5pct, near_lows_5pct, near_highs_pct, near_lows_pct,
        analytics{net_nh_nl, volatility_ratio, volume_ratio,
                  up_down_close_pct, bo_bd_ratio}},
detection_inputs_policy, disclaimer
```

## 1.2 Fields that DO NOT exist — do not render, do not invent

```
composite            0/73   — no composite score is computed
sector / industry    absent from candidate rows
theme                absent
1D / 5D deltas       absent — no prior-session comparison is stored
prior-session trigger distance  absent — blocks true "drift" (PART 6)
MFE / MAE per call   present only in outcomes_<date>.json, not tonight
earnings date        absent
ASM / GSM flag       absent
bulk / block deals   absent
```

Any design element in the source audit that depends on the above is
**BLOCKED** until the backend emits it. Mark it `BLOCKED`, state the field.

## 1.3 The null-rendering ladder (memorise this)

| Situation | Render |
|---|---|
| field present, real | the value |
| field present, `null` | `—` with a tooltip naming why if known |
| field absent from schema | omit the row entirely; do not show a blank label |
| whole section has no real data | one-line honest empty state, not a bordered card |
| value exists but is untrustworthy (see PART 9) | value + explicit caution marker |

---

# PART 2 — GLOBAL ELEMENTS

### `G-01` Delete the `SESSION` fixture
**File:** `unidesk_terminal/src/data/fixtures.ts`
Delete the exported `SESSION` object entirely (`date`, `universeScanned`,
`universeSkipped`, `pctAboveEma50`, `aboveEma21`, `aboveEma21Of`).
**Accept:** `grep -rn "SESSION" src/` returns no hits outside `REAL_SESSION`.

### `G-02` TopBar date follows the selected report
**File:** `src/components/shell/TopBar.tsx:43`
Currently renders `As of {SESSION.date}` → shows a two-month-old date on every
screen. Read the **selected** report's `session_date` via `reportRegistry.ts`.
**Accept:** header date equals the report chosen in the picker, and changes
when the picker changes. No screen shows a date the user did not select.

### `G-03` Delete the `REGIME` fixture
**File:** `fixtures.ts` (`export const REGIME`), used at `Tonight.tsx:97`.
It hardcodes `label:"BULL", aboveEma50Pct: 65.86, nearHighsPct: 22.4,
nearLowsPct: 6.1`. The backend now computes the real regime.
**This is the highest-severity UI defect: the front page currently asserts
BULL while the system computed CHOP.**
**Accept:** the regime shown equals `honesty_footer.regime_note`. Grep for
`65.86` returns nothing.

### `G-04` Shared report-selection state
If no shared selection state exists, create the smallest possible one (React
context or a module-level selector in `reportRegistry.ts`). No state library.
**Accept:** changing the report updates TopBar, Home 1, Home 2 together.

### `G-05` Beginner/Pro toggle wired to real behaviour
**Accept:** toggling changes at least one visible element on every screen; Pro
never shows fewer fields than Beginner; engineering strings appear only in Pro.

### `G-06` Global session date appears exactly once
Remove repeated date stamps from section headers (source audit §1).
**Accept:** the session date appears once per screen.

### `G-07` Diagnostics drawer
Create one collapsible `ⓘ Data / Diagnostics` element. Move into it:
`adjustment_note`, `detection_inputs_policy`, `universe_gate_skips`,
`actions_applied`, `adjusted_symbols`, provenance strings.
**Accept:** none of those strings appear in Beginner mode outside the drawer.

---

# PART 3 — HOME 1 · MARKET STATE

Answers: *what kind of market is tonight?*

### `H1-01` Regime headline as the page anchor
Render `honesty_footer.regime_note`'s state (CHOP/BULL/BEAR) as the largest
element on the page, with its one-line explanation beneath.
**Accept:** regime is visually dominant; text matches the JSON exactly.

### `H1-02` Regime position strip
```
Risk-Off ───── Weak ───── CHOP ───── Healthy ───── Strong
                            ▲
```
Position from `pct_above_ema50`. No glow, no gradient.
**Accept:** marker position corresponds to the real breadth value.

### `H1-03` Delete the four KPI cards
Replace the `65.9% / 64.5% / 22.4% / 6.1%` card row with the ruled table in
`H1-04`. **Accept:** no four-card KPI row remains.

### `H1-04` Market participation as one ruled table
```
MARKET PARTICIPATION
─────────────────────────────────────────────────
                    TODAY    BAR              1D    5D
Above EMA21         52.2%    █████████░░░░    —     —
Above EMA50         56.4%    ██████████░░░    —     —
Near 52W High        8.6%    ██░░░░░░░░░░░    —     —
Near 52W Low         4.2%    █░░░░░░░░░░░░    —     —
```
Sources: `above_ema21/above_ema21_of`, `pct_above_ema50`,
`breadth.near_highs_pct`, `breadth.near_lows_pct`.
**1D and 5D columns render `—`** — no prior-session data is stored (PART 1.2).
Do **not** compute them from a second report file unless `B-07` is done.
**Accept:** every number traceable to the footer; delta columns show `—`.

### `H1-05` Breadth analytics row — currently invisible, must be shown
`honesty_footer.breadth.analytics` holds the reverse-engineered Market Breadth
V2 work and is rendered nowhere:
```
NH-NL balance      +0.154      net_nh_nl
Up/Down close       72.9%      up_down_close_pct
Volume ratio         0.334     volume_ratio
Volatility ratio     0.547     volatility_ratio
BO/BD ratio            —       bo_bd_ratio  (null today → render —)
```
**Accept:** all five appear; `bo_bd_ratio` shows `—`, not `0`.

### `H1-06` NH/NL balance bar
```
Low dominance ◀────────●──────────▶ High dominance
                    +0.154
```
**Accept:** driven by `net_nh_nl`.

### `H1-07` Tonight's Playbook
```
TONIGHT'S PLAYBOOK
EXPOSURE       <derived from regime>
FAVOUR         <setup types for this regime>
AVOID          <setup types to avoid>
SELECTIVITY    <derived from regime>
```
**Constraint:** the mapping regime→playbook must be a single named, documented
constant in one file, clearly labelled as a **heuristic, not validated**. Do
not present it as evidence-backed. Show that label in Pro mode.
**Accept:** playbook changes with regime; the "not yet validated" caveat is
visible in Pro.

### `H1-08` Remove engineering text from Beginner
Strings to move to the `G-07` drawer: `breadth_only`, `not yet folded into
report.py's regime line`, `reverse engineered from`, `liveness gate`,
`R0 breadth-only classifier (N2)`.
**Accept:** none visible in Beginner.

### `H1-09` Universe line
One quiet line: `1,295 scanned · 75 skipped · 1,380 gated out`
from `universe_scanned`, `universe_skipped_insufficient_history`,
`universe_gate_skips_total`. Breakdown lives in the drawer.
**Accept:** present, single line, matches the footer.

### `H1-10` Regime history strip — `BLOCKED` unless `B-07`
```
20-DAY REGIME HISTORY
C C H H H S S H C C C W W C C H C C C C
                                     ▲ TODAY
```
Requires prior sessions' regime values. If `B-07` is not done, mark
`BLOCKED — requires multi-session regime history`. **Do not fabricate.**

---

# PART 4 — HOME 2 · TONIGHT'S SETUP FEED

Answers: *which few stocks deserve attention, and why?*

**Reality check before you design:** the current feed is **51 inside_bar,
9 pullback, 6 ipo_base, 4 momentum_burst, 1 base_breakout, 1 episodic_pivot,
1 reversal_reclaim** out of 73. Six of seven sections are nearly empty. Build
the seven-section structure, but it must look correct with a single row, and
`H2-09` handles the imbalance honestly.

### `H2-01` Keep the seven setup sections
```
Base Breakout · Episodic Pivot · Inside Bar · IPO Base
Power Play · Pullback · Reversal / Reclaim
```
**Accept:** all seven present; a section with 0 candidates renders one quiet
line (`No candidates`), not a bordered empty card.

### `H2-02` Replace large cards with compact rows
```
01  DIFFNKG   ₹485.50  ▂▃▄▅▆▇   RS 91  RVOL 4.3x  -1.8%  READY
```
Columns: `RANK | SYMBOL | PRICE | SPARKLINE | RS | RVOL | PIVOT DIST | STATE`
**Accept:** no candidate card taller than ~3 text lines; one row grammar used
under every setup section.

### `H2-03` Sparkline from real history
Use `stock_history_<date>.json` via `getRealHistory(symbol)`.
If the symbol is absent → render nothing in that cell. **Never** render a
synthetic sparkline. **Accept:** every sparkline traces to real bars.

### `H2-04` Replace "Not classified" with actionable states
```
PRIME · READY · NEAR PIVOT · WATCH · EXTENDED · LOOSE · LOW LIQ · REJECT
```
Derive from `trigger` vs `close` (pivot distance) plus `stock_quality.score`.
Document the thresholds in one constant. **Accept:** no row reads
"Not classified"; state rules live in one place.

### `H2-05` Surface `stock_quality` — it exists on 73/73 and is invisible
Show `stock_quality.score` (1dp) with `coverage` as a %, plus the `unknowns[]`
list compactly. **A score of 97.9 at coverage 0.85 with a named unknown must
not read as a confident 97.9.**
**Accept:** score, coverage and unknowns all visible; "NO QUALITY SCORE
COMPUTED" string is gone.

### `H2-06` Surface trade geometry — exists on 73/73, invisible
Show `trigger`, `invalidation`, and `rr`.
**Flag `rr < 1.0` visually** — 44% of candidates are below 1.0R and should not
read as equally attractive. **Accept:** all three visible; sub-1R marked.

### `H2-07` Surface Reactor Scale (`activity_score`)
Render `activity_score.activity_score`. **Must carry this caveat verbatim**
(tooltip or caption):
> "must never be presented as institutional identity, trade direction, or a
> risk input"
**Accept:** value visible; caveat text present verbatim.

### `H2-08` Surface `trust`
Where `trust.status != clean`, show the status and its `reason` on the row.
`base_breakout` currently carries `REVIEW_REQUIRED`.
**Accept:** reason text visible, not just a colour.

### `H2-09` Section headers carry decision value
```
INSIDE BAR                                        51 FOUND
38 watch · 9 ready · 4 extended
```
**Accept:** counts derive from the `H2-04` states and sum to the section total.

### `H2-10` Collapsible sections
Sections with >10 candidates start collapsed; others expanded.
**Accept:** page fits ~2 screens at 1920×1080 without scrolling through 51 rows.

### `H2-11` One setup-specific metric per section
```
Base Breakout → pivot distance      Episodic Pivot → gap/catalyst
Inside Bar    → range compression   IPO Base       → weeks since listing
Power Play    → gain + depth        Pullback       → distance from EMA/AVWAP
Reversal      → reclaimed level
```
Render only where the backing field exists; otherwise omit the column and mark
that setup's metric `BLOCKED — field <name> not emitted`.
**Accept:** each section names its extra metric or explicitly reports it blocked.

### `H2-12` Rank within each section
Number rows `01, 02, 03…`. Ranking key must be a single documented function.
**Accept:** ordering is deterministic and documented.

### `H2-13` Remove pipeline language
Delete from the primary view: `RAW SCAN SIGNALS`, `NO QUALITY SCORE COMPUTED`,
`REAL SCAN — N SESSIONS`, `Trigger / invalidation not computed`.
**Accept:** none present in Beginner.

### `H2-14` Beginner interprets, Pro quantifies
```
Beginner:  RS 91 → "Top 9% of market"    RVOL 4.3x → "Exceptional volume"
Pro:       RS 91 | RVOL 4.34 | ADR 5.2 | Pivot -1.83
```
**Accept:** both modes verified on the same row.

---

# PART 5 — HOME 3 · PRIOR CALLS / OUTCOMES

Answers: *did the scanner have edge, which setups worked, and why not?*

### `H3-01` Investigate `No longer in universe` vs `Stopped out` — DO THIS FIRST
The source audit flags rows showing both simultaneously. These are **not
equivalent**: a symbol leaving today's universe is not yesterday's trade
hitting its stop. Read `outcomes_<date>.json` and the code that builds it.
**Accept:** you state in your report which field drives each label, and whether
they are conflated. If conflated, that is a **backend bug** — file it, do not
paper over it in the UI.

### `H3-02` Performance summary above individual rows
```
YESTERDAY'S CALLS                                    42
TRIGGERED 18 · UNTRIGGERED 17 · WON 8 · STOPPED 6 · ACTIVE 4
Hit rate 57%   Avg R +0.42R   Best +2.8R   Worst -1.0R
```
Only render statistics the outcomes file actually supports; others `—`.
**Accept:** every statistic traceable; no invented aggregate.

### `H3-03` Outcome strip
```
W W — S W A — — S W W — S A W — —
W=win S=stopped A=active —=never triggered
```
**Accept:** counts match `H3-02`.

### `H3-04` Compact outcome table
```
STOCK      SETUP       RESULT   RETURN   MFE     MAE
DIFFNKG    Breakout    WIN      +1.8R    +2.1R   -0.3R
```
**Accept:** replaces full-width repeated rows.

### `H3-05` MFE / MAE columns
Already in `outcomes_<date>.json`. Guard nulls per PART 1.3 — **this file
previously crashed the screen via `.toFixed()` on null**.
**Accept:** screen renders with null MFE/MAE present; no console error.

### `H3-06` Distinct outcome states
```
WIN · ACTIVE · STOPPED · NO TRIGGER · INVALIDATED · EXPIRED · DATA ISSUE
```
`Stopped out` must stop being a catch-all.
**Accept:** at least `NO TRIGGER` and `DATA ISSUE` are distinguishable from
`STOPPED`.

### `H3-07` Collapsible outcome groups
```
▼ WINNERS / ACTIVE  ▶ STOPPED  ▶ NEVER TRIGGERED  ▶ INVALID / DATA ISSUE
```

### `H3-08` Setup-level scorecard
```
Base Breakout    12   ███████░░░   +0.62R
Inside Bar        8   ████░░░░░░   -0.18R
```
**Accept:** computed from outcomes, sample size shown beside every figure. A
setup with n<10 must be visibly marked as low-sample.

### `H3-09` Failure reason per stopped trade
```
STOPPED  -1.0R   Failed breakout · never held pivot
```
If no reason field exists, mark `BLOCKED — no failure-reason field emitted`.
Do **not** infer a narrative reason in the UI.

---

# PART 6 — HOME 4 · WATCHLIST DRIFT

### `H4-01` Rename to reflect what it shows
Today it shows distance-to-trigger, not drift. Until `B-07` lands, title it
**"Trigger Proximity"**. **Accept:** name matches content.

### `H4-02` Proximity ladder
```
DIFFNKG    ───────────────●──────    -1.6%   READY
BODALCHEM  ─────────────────●────     0.0%   TRIGGER
TMB        ─────────────────────●    +2.7%   EXTENDED
```
**Accept:** position derives from `(trigger/close - 1)`.

### `H4-03` States replace identical amber dots
```
FAR · WATCH · NEAR · READY · TRIGGER · LATE · EXTENDED · INVALID
```

### `H4-04` Visually separate approaching / at / past trigger
Group into `APPROACHING`, `AT TRIGGER`, `GETTING LATE`.

### `H4-05` True drift — `BLOCKED` unless `B-07`
Requires prior-session trigger distance, which is not stored.
Mark `BLOCKED — no prior-session distance stored`. Do not fake a delta.

### `H4-06` R:R shown honestly
Median is 1.26 and **44% are below 1.0R**. Show `rr`, sort by it optionally,
and mark sub-1R rows.
**Accept:** a sub-1R candidate is visually distinguishable from a 3R one.

### `H4-07` Quality score secondary to proximity
Render as a grade or small bar, not a dominant number.

### `H4-08` Collapse the honesty footer
```
DATA QUALITY  ✓ 1,295 scanned · 75 excluded          [details]
```
Full text into the `G-07` drawer.

---

# PART 7 — CANDIDATES · CROSS-SECTIONAL LAB

Candidates must stop duplicating Home 2.

### `C-01` Remove duplicated setup cards
**Accept:** Candidates does not repeat Home 2's card feed.

### `C-02` Ranked research table
```
#  STOCK      SETUP   QUALITY  ENTRY  RS   RVOL  TIGHT  R:R  STATE
01 DIFFNKG    BB        97      73    91   4.3x   88    2.1  READY
```
Columns hideable. Every column maps to a PART 1.1 field.
**Accept:** no column exists without a backing field.

### `C-03` Opportunity landscape with named quadrants
```
                 SETUP QUALITY HIGH
      WATCH          │      PRIME ZONE
─────────────────────┼──────────────────► ENTRY QUALITY
      IGNORE         │      SPECULATIVE
```
**Accept:** quadrants labelled; top names permanently labelled; click → Stock.

### `C-04` Selectable axes
`Setup×Entry`, `RS×Accumulation`, `Tightness×Entry`, `Risk×Reward`.
Only offer axis pairs whose fields exist.
**Accept:** every offered axis maps to a real field.

### `C-05` Filters redraw the landscape
**Accept:** filtering updates both table and plot.

### `C-06` Accumulation panel — partial
`activity_score`, `delivery_ratio`, `rvol` exist. Bulk/block data does not.
Label the composite **"Accumulation Evidence"** or **"Institutional Interest"**
— never "Institutional Buying" (these are proxies).
**Accept:** no claim of confirmed institutional activity.

### `C-07` Tightness / VCP panel
`contraction` exists; the full contraction sequence may not.
Render what exists; mark the rest `BLOCKED — <field>`.

### `C-08` Cohort comparison
Select multiple candidates, compare in aligned columns. **No radar charts.**

### `C-09` Historical expectancy — `BLOCKED`
Requires validated per-setup expectancy, which does not exist and is gated
behind the N5 experiment. Mark `BLOCKED — N5 not run`. **Do not display any
expectancy number.**

---

# PART 8 — STOCK DETAIL

### `S-01` Beginner leads with a verdict
```
DIFFNKG                       ₹485.50
VERDICT   WAIT
Strong stock, strong setup, but the entry is unattractive right now.
```
Verdict from `entry_quality` + `stock_quality` + pivot distance, via one
documented function. **Accept:** verdict visible above all scores.

### `S-02` Pro shows verdict + every raw metric
**Accept:** Pro is a strict superset of Beginner.

### `S-03` Levels visual
```
STOP        CURRENT      TRIGGER       TARGET
│             ●            │             │
411          485          493           535
```
Target only if a field backs it; else omit.

### `S-04` Rename `Regime: BULL` on the stock page
It is the **stock's** trend, and it currently contradicts Home 1's market
regime. Rename:
```
Beginner:  BROADER MARKET  CHOP   ·   THIS STOCK  BULLISH
Pro:       Broad Market Regime CHOP · Stock Trend Regime BULL
```
**Accept:** no unqualified "Regime" label remains on the stock page.

### `S-05` Verify which variable feeds the stock regime
State in your report whether it is the market classifier or a per-stock trend
state. If it is the market classifier, that is a **bug** — file it.

### `S-06` Synthetic-chart warning must be unmissable
When `getRealHistory(symbol)` returns undefined:
```
┌────────────────────────────────────────────┐
│ DEMO CHART · SYNTHETIC DATA · DO NOT TRADE │
└────────────────────────────────────────────┘
```
**Preferred: do not render a tradable-looking chart at all.** Show the levels
table instead. **Accept:** no synthetic chart can be mistaken for real.

### `S-07` Beginner terminology map
```
Invalidation    → Setup fails below      Extension     → How stretched is price
Room to trigger → Distance to breakout   Risk:Reward   → Reward vs risk
Composite       → Overall setup quality
```
**Accept:** Beginner shows none of the left column.

### `S-08` Setup evidence, both modes
```
Beginner: ✓ Strong trend  ✓ Top 9% RS  ✓ High volume  ✓ Tightening
Pro:      Trend Strong | RS 91.1 | RVOL 4.34x | Contraction 1.47
```

### `S-09` Shrink empty states
`PAST SIGNALS — none recorded` as one line, not a bordered panel.

### `S-10` Hide Replay when there is nothing to replay
**Accept:** no disabled Replay button on a stock with no history.

---

# PART 9 — BACKEND TASKS (several screens depend on these)

### `B-01` LIVENESS GATE — highest priority in this document
**9 of 73 candidates (12%) had no trade on the session date.** UJJIVAN's last
real print was **2024-05-02** — over two years earlier — shown at ₹589.50 with
`rs_rank` 84.7 and a trigger.

Worse, **the stalest names rank highest**: ALPHAGEO (99.4) and SHALPAINTS
(99.2) are the top two RS ranks in the report and both stopped trading before
the session. A frozen price against a drifting universe manufactures fake
leaders.

**Fix:** exclude any symbol with no print on the session date from the
candidate list **and from the RS-ranking universe**. Phase 0 spec §35 already
requires `traded_today` / `suspended` / `series_active`.
**Accept:** zero candidates whose last bar predates the session date; RS ranks
recomputed without them.

### `B-02` Deduplicate candidates
73 rows / **71 distinct symbols** — `FILATEX` and `UJJIVAN` appear twice (once
per firing detector). Either emit one row per symbol carrying a detector list,
or state the grain is symbol×detector everywhere a count is shown.
**Accept:** counts and distinct symbols reconcile, or the grain is labelled.

### `B-03` Disclose history depth
Nightly ingests only the **600 most recent files**; max `sessions` is 570 while
4,007 sessions exist on disk. Every "52-week high" is computed from ≤2.3 years.
**Accept:** the footer states effective history depth, or the window is raised.

### `B-04` Regenerate the archive on the 4-action CA basis
All 396 partitions carry the rejected `ca_table_hash 191ac96a61cdfae7`; the
verified table is `d1b585eb60fd4f82`. Use `run_regen_full.py` — **not** the
resume driver.
**Accept:** every event carries `d1b585eb60fd4f82`.

### `B-05` Fix the staleness detector
`sessions_needing_label_refresh` (`archive_attach.py:126`) compares only
`label_version`, so a CA-table change reports "0 sessions need refresh" — a
false all-clear. Compare `ca_table_hash` too.
**Accept:** changing only the CA table marks all partitions stale; regression
test added.

### `B-06` Fix the invalid attribution record
`run_checks.py` currently **FAILS**: record
`attr-unidesk-audit-fixes-cline-20260831-001` is missing `host_tool`, `scope`.
**Accept:** `run_checks.py` exits green.

### `B-07` Emit prior-session comparison fields
Unblocks `H1-04` deltas, `H1-10` regime history, `H4-05` true drift.
Emit per candidate: prior close, prior trigger distance, prior `rs_rank`; and
per report: prior regime label.
**Accept:** those three UI tasks can move from BLOCKED to DONE.

### `B-08` Investigate the inside_bar dominance
**51 of 73 candidates (70%) come from one detector**; base_breakout and
episodic_pivot fire once each. Either the inside_bar threshold is too loose or
the others are too strict. This distorts the entire feed.
**Accept:** you report the firing rate per detector over the last 20 sessions
and state whether the imbalance is expected.

### `B-09` Verify the delivery-percentage source
`delivery_ratio` feeds accumulation UI. Confirm it comes from the exchange
delivery report, and that its availability timestamp is respected.

---

# PART 11 — DECISION & DISCIPLINE LAYER

## 11.0 Why this part exists

The desk is being built as a **scanner**. The owner's audited 420-trade history
(`BROKER_AUDIT_2026-07-18.md`, `TRADE_AUTOPSY_2026-07-19.md`) shows his losses
are **not** discovery losses:

| Verified leak | Measured cost |
|---|---|
| 86 late exits (hesitation after Broken fires) | **−₹4,381** — largest single bucket |
| Buying late in moves (>80% off 65d low) | worst tag, −₹81/trade |
| Micro-sizing (₹300–5k) | ₹10–25k was his **only** profitable bucket |
| One unmanaged −91% position (RNBDENIMS) | outweighed months |
| Over-trading (~7/wk, 64 same-day round trips, 27 revenge re-entries) | — |
| **90 of 94 checked entries were names the gate refused or never surfaced** | — |

Verified **strengths**: finds momentum early (extended-but-early entries were
his best cohort, +₹48 avg); strong structural exit reflex (322 structure exits
net-positive, only 2 panic exits in 420).

**Conclusion:** he does not have an exit-skill problem, he has an
**exit-latency** problem; and his discretionary selection is the weak link
relative to the tool. A better scanner improves none of the six rows above.
This part builds the layer that does.

## 11.1 CHARTER CONSTRAINTS — binding on every task in this part

From `traderlog/CANONICAL.md:97-103`:

> - **LLM proposes, never decides.** No model output may author a stop, a size,
>   or a risk number.
> - **Manual execution only.** No order routing, ever.
> - **No dormant code.** A module ships only if it is wired into a pipeline AND
>   surfaced in the UI.

Therefore, in this part:

1. **Nothing here may emit a prescriptive size, stop, or risk number.** Show
   the owner's **own historical outcome distribution** and let him decide.
   Permitted: *"your ₹10–25k bucket returned X; this setup sits in your 90th
   percentile."* Forbidden: *"size ₹18,000."*
2. **No order routing, no broker write path.** Read-only, manual entry only.
3. Every module built here must be **surfaced in the UI in the same slice**, or
   it is dormant code and must not be merged.

---

### `D-01` Pre-trade veto — cheapest, largest measured impact
Input: a symbol the owner is about to buy. Output, in one screen:
```
UJJIVAN          NOT IN TONIGHT'S UNIVERSE
Refused because: no print on 2026-08-28 (last trade 2024-05-02)

RELIANCE         NOT A CANDIDATE
In universe, but no detector fired.

DIFFNKG          CANDIDATE · Base Breakout · READY
Trigger 493.20 · Invalidation 411.00 · R:R 2.1
```
Sources: candidate list, `honesty_footer.universe_gate_skips`, liveness (`B-01`).
**Depends on `B-01`** — without the liveness gate this will pass dead names.
**Accept:** entering a symbol returns one of {candidate, in-universe-no-signal,
refused-with-named-reason, unknown-symbol}. Never a blank.

### `D-02` Exit alarm — attacks the −₹4,381 bucket
For each symbol in the owner's open-positions register (`D-03`), evaluate
structure state on the latest session and surface those that broke.
```
POSITIONS NEEDING ACTION                                   2
FILATEX     structure broken 2026-08-28 · closed below invalidation 74.10
AUTOIND     structure broken 2026-08-27 · 2 sessions ago
```
Show **sessions elapsed since the break** — latency is the measured leak.
**Charter:** state the observed fact ("closed below invalidation"). Do not
author an instruction ("sell now").
**Accept:** a held name that closed below its recorded invalidation appears
here, with elapsed sessions, on the session it breaks.

### `D-03` Positions register — manual, read-only
Manual entry: symbol, entry date, entry price, size (₹), recorded invalidation.
Persisted locally. **No broker API, no routing** (charter).
**Accept:** positions persist across reloads; `D-02` and `D-05` read from it;
nothing writes to a broker.

### `D-04` Size-evidence panel — descriptive, never prescriptive
From the imported broker history (`D-10`), show the owner's realised outcomes
bucketed by position size:
```
YOUR OUTCOMES BY POSITION SIZE          (420 trades, FY25-26)
₹300 – 5k      n=..   avg ₹..   ← your most-used bucket
₹5k – 10k      n=..   avg ₹..
₹10k – 25k     n=..   avg ₹..   ← your only profitable bucket
```
Alongside: where the current setup sits in his own quality distribution.
**Charter:** no recommended number. The panel presents his record; he decides.
**Accept:** every figure traces to the broker import; no suggested size string
appears anywhere.

### `D-05` Risk-cap check — attacks the −91% outlier
Given the positions register and a stated account size, show for each position
the loss to its recorded invalidation, in ₹ and as % of capital, and flag any
position with **no recorded invalidation** — that is how RNBDENIMS happened.
**Accept:** a position with no invalidation is visibly flagged as unmanaged.

### `D-06` Over-trading indicator
Count entries in the trailing 7 sessions from the positions register; show
against his audited baseline (~7/week, 64 same-day round trips, 27 revenge
re-entries).
**Charter:** descriptive count and comparison, not a block or a permission gate.
**Accept:** the count is visible and the historical baseline is stated.

### `D-07` Base-stage classification surfaced — the BananaPatterns payoff
`momentum/detectors/base_episode.py` (`base_episode_from_bars`,
`match_base_preset`) and `base_pattern.py` already exist, are calibrated, and
`base_episodes[]` is already emitted at report top level — **and rendered
nowhere.** Under the "no dormant code" rule that is a charter violation today.
Surface the stage per candidate:
```
EARLY BASE · MID BASE · FINAL CONTRACTION · BREAKOUT · EXTENDED
```
**Accept:** every candidate with a `base_episode` shows its stage; those
without show `—`, never a guessed stage.

### `D-08` Late-entry warning — attacks his worst entry tag
His worst cohort is buying >80% off the 65-day low. Compute that percentile per
candidate and warn above the threshold, on the candidate row and the stock page.
```
⚠ 87% off 65d low — your worst historical entry zone (−₹81/trade avg)
```
**Accept:** the warning fires on real data, cites his own audited figure, and
does not block the trade.

### `D-09` Call-vs-trade reconciliation
Join the broker history (`D-10`) to what the desk said on that date: was the
name a candidate, in-universe-no-signal, or refused? Report the split.
This is the measurement that produced "90 of 94" — make it a live, repeatable
view rather than a one-off audit.
**Accept:** for any past trade the screen states what the desk said that night,
or `no report for that session`.

### `D-10` Broker-history import — its own store, never blended
Import the audited trade history into a **separate** table/namespace. It must
never merge into scan output, candidate lists, or the research archive.
**Data contract:** this is a *distinct source* from PART 1 — different grain,
different provenance, different trust. Label it as such wherever it surfaces.
**Accept:** no scan/archive file gains broker-derived fields; `run_checks.py`
data-authority check still passes.

### `D-11` L1.5 analogue panel — `BLOCKED`
"This setup resembles N historical cases; X% continued, median +YR."
Requires Phase 2.5 (Constitution §7) and the N5 archive. **Phase 0 spec §1.2
explicitly excludes L1.5.** Mark `BLOCKED — Phase 2.5 gate, N5 not run`.
Do **not** ship any similarity or expectancy number before that gate.

### `D-12` Order-flow exit assist — `BLOCKED`, and scope it narrowly when it lands
When N7 is activated, its highest-value use for this owner is **exit latency on
already-held names**, not discovery. Scope it to the positions register only.
**Charter:** observational; no routing, ever.
Mark `BLOCKED — N7 not activated`.

### `D-13` Practitioner-claim testbed — optional, high differentiation
Take one named practitioner rule (Arora / TradeTM / Stocksgeeks), express it as
a deterministic filter, run it over the 2010–2026 archive with real costs and
stop-aware labels, and report what it actually did — including a negative
result. Depends on `B-04` (clean archive).
**Accept:** one claim tested end-to-end with its counterfactual stated.

---

# PART 12 — CLASH RESOLUTION (read before touching PARTS 3–8)

PART 11 does not overwrite PARTS 3–8, but it collides with them in six places.
Resolve each exactly as stated; do not improvise.

### `X-01` Navigation — one new screen, not scattered widgets
Current nav is six system-shaped tabs (Tonight, Candidates, Stock, History,
Research, Settings). PART 11 needs a home for veto / positions / exits / size
evidence. **Add exactly one screen: `Desk`.** Do not sprinkle these across
existing screens.

This also moves the IA toward the owner's stated preference — screens as
**scan → judge → size → manage → exit** rather than system tabs:
```
Tonight    scan        Candidates  judge
Stock      judge       Desk        size / manage / exit
History    review      Research    evidence
```
**Accept:** exactly one screen added; no PART 11 feature lives on Tonight or
Candidates.

### `X-02` History vs Desk — never merge the two grains
`H3-*` (History) = **what the scanner called** and how those calls resolved.
`D-09` (Desk) = **what the owner actually traded**. Different grain, different
source, different trust.
Blending them repeats the TRENT failure — the user could not tell tool output
from something else.
**Rule:** History never shows broker trades. Desk never shows scanner calls the
owner did not trade. `D-09` is the only place they meet, and it must label both
sides explicitly ("desk said" vs "you did").
**Accept:** no screen shows a row where the two sources are indistinguishable.

### `X-03` Playbook (`H1-07`) vs size evidence (`D-04`) — different scopes
Both speak to exposure and will look contradictory if unmanaged.
- `H1-07` is **market-level** and a **heuristic** — qualitative only
  (`EXPOSURE: REDUCED`). It must emit **no numbers**.
- `D-04` is **position-level** and **descriptive of the owner's own record**.
**Rule:** the Playbook never states a size, a rupee amount, or a position count.
**Accept:** no numeric exposure figure appears in `H1-07`.

### `X-04` Build order — three hard dependencies
```
B-01 (liveness gate)      →  D-01   veto passes dead names without it
D-03 (positions register) →  D-02, D-05, D-06
D-10 (broker import)      →  D-04, D-09
B-04 (clean archive)      →  D-13
```
`D-07` and `D-08` depend on **nothing new** — build them first from PART 11.
**Accept:** no dependent task is marked DONE while its prerequisite is not.

### `X-05` Charter — the sizing question, resolved
A size **is** a risk number, and the charter forbids model-authored risk
numbers. Resolution: `D-04` presents the owner's **own realised outcomes by
size bucket** — a descriptive statistic over his history, not a model output
and not an instruction.
**Rule:** if any task in PART 11 would print a recommended size, stop and
report it as `BLOCKED — charter: no model-authored risk number`.
**Accept:** grep the diff for a recommended-size string; there must be none.

### `X-06` "No dormant code" upgrades four existing tasks
The charter rule *"a module ships only if it is wired into a pipeline AND
surfaced in the UI"* means these are **compliance items, not polish**:
```
H1-05  breadth analytics    computed, not rendered
H2-05  stock_quality        computed on 73/73, not rendered
H2-07  activity_score       computed on 73/73, not rendered
D-07   base_episodes        emitted, not rendered
```
**Accept:** each of the four is either surfaced or explicitly reported
`BLOCKED` with a reason. "Deferred to a later pass" is not an acceptable status
for these four.

---

# PART 13 — FUTURE WAVES: AI INTEGRATION, DONE HONESTLY

## 13.0 The gate structure — do not skip a rung

From `ai_native_indian_swing_research_constitution_v1.md` §1 and
`phase0_implementation_data_build_spec_v1.md` §0/§1.2/§54:

```
L0  raw rule            ← exists (8 detectors)
L1  engineered score    ← exists (stock/setup/entry quality)
L1.5 engineered-state analogue retrieval   ← MANDATORY BEFORE ANY NEURAL NET
L2  supervised learned representation
L3  learned-space analogues
L4  empirical outcome distribution
L5  deterministic execution
```

> **"Phase 0 contains no predictive AI."** — Phase 0 spec §0
> Explicitly excluded in Phase 0: T1/T5 signals, **L1.5 analogue retrieval**,
> neural encoders, intraday EP models. — §1.2
> **"No learned model should be trained before this gate."** — §54

**Therefore every task in PART 13 is `BLOCKED` until Phase 0 passes its own
Definition of Done (spec §53).** Report them as blocked; do not build ahead.
The point of writing them now is so the UI and data shapes built in PARTS 1–12
do not have to be torn up later.

### `A-01` Phase 0 gate audit — the precondition for everything here
Produce a checklist against spec §53 with each row PASS/FAIL and evidence.
Known-open at time of writing: 2016+ history target (archive starts 2010 on
disk but the nightly ingests only 600 files — see `B-03`), immutable raw
archive + SHA256 source manifest (§30), build manifest (§31), availability
ledger (§26), PIT index membership (§17), `make rebuild` determinism (§2.2),
security identity keyed on `security_id`/ISIN rather than symbol (§8).
**Accept:** a table with every §53 item marked, no item unmarked.

### `A-02` L1.5 analogue retrieval — the first AI rung
Engineered-vector retrieval over the research archive. **No neural network.**
Vector (Constitution §7): `gap_pct, rvol_20, close_loc, prior_atr_percentile,
S_ep, RS, delivery_z, extension, liquidity, market_regime`.
Distance: **cosine only** (§10). Neighbours: **k = 25 or 50 only** (§10).
Output: the empirical outcome distribution of retrieved neighbours.
**Hard constraints:**
- neighbours must respect the same-symbol embargo — `leakage.py::embargo_overlapping_events`
  already exists and is unused; wire it here
- max 20% of neighbours from one industry + calendar week (§6.3)
- point-in-time normalisation only; no full-sample z-scores (§6.4)
**Accept:** a retrieval returns k neighbours, none violating embargo, with an
outcome distribution and explicit sample count.

### `A-03` L1.5 UI surface — conviction, not prediction
```
SIMILAR HISTORICAL SETUPS                      43 matches
Continued within 10D            61%
Typical upside                  +9.6%
Typical adverse move            -2.4%
Sample                          43 (12 in CHOP regime)
```
**Forbidden on this surface (Constitution §22):** cosine similarity values,
latent cluster IDs, embedding norms, any "prediction" or "confidence" framing.
Title it **"Similar historical setups"**, never "forecast".
**Accept:** no similarity metric or model-internal number is visible; sample
size always shown beside every statistic.

### `A-04` L2 encoder — only after L1.5 is measured
Temporal CNN only (§10). Sequence lengths **20 or 40 only**. Multi-task
targets: `cont_10d` (binary), `fail_3d` (binary), `mfe_10d`, `mae_10d` (§2).
Retrieval must use the **penultimate latent**, not the predicted outputs —
otherwise the analogue layer is circular (§2).
**Accept:** `BLOCKED` until `A-02` has produced a measured L1.5 result. State
the L1.5 lift when you unblock it.

### `A-05` Promotion rule — must exist before any model is judged
Constitution §19: lift persists in **≥3 of 5 walk-forward folds**;
block-bootstrap **90% CI excludes zero**; **≥15–20% net expectancy improvement**
or materially lower MAE at similar expectancy. Freeze the procedure **before**
the final holdout.
Report three-dimensionally (§4): **quality × coverage × stability**, and
classify the result as `RANKER`, `SNIPER FILTER`, or `NO EDGE`.
**Accept:** the rule is implemented as code and a deliberately null signal
fails it.

### `A-06` Coverage reporting — non-negotiable (§20)
Every AI result reports: candidate count, trade count, coverage vs champion,
top-decile coverage, sector concentration, year concentration, ADV distribution.
**Accept:** no AI result is presentable without all seven.

### `A-07` The honest-negative path
Constitution §26 Outcome B: if L1.5/L2 add nothing, **delete the layer** and
keep the simpler system — that is a successful result.
**Accept:** the plan names, in advance, what result would cause deletion.

---

# PART 14 — BANANAPATTERNS INTEGRATION

## 14.0 What already exists — do not rebuild it

| Asset | Path | State |
|---|---|---|
| Integration boundary spec | `unidesk/design/BANANAPATTERNS_INTEGRATION_SPEC.md` | authoritative |
| Clean-room detector | `unidesk/momentum/detectors/base_pattern.py` | built, calibrated |
| Episode adapter | `unidesk/momentum/detectors/base_episode.py` | `base_episode_from_bars`, `match_base_preset` |
| Trust map | `unidesk/momentum/detectors/trust.py` | emitted as `detectorTrust` |
| Validation harness | `unidesk/momentum/validation/bananapatterns.py` | retained |
| Public snapshot | `data/market/validation/bananapatterns_universe.json` | reference only |
| Technical audit | `deliverables/BananaPatterns_Technical_Audit_2026-08-29.docx` | 18pp, public surface only |
| Recovery plan | `unidesk/tasks/bananapatterns_recovery_plan.md` | slice sequencing |

## 14.1 Boundaries — from the integration spec, binding

> **Always:** preserve raw detector outputs, version derived objects, disclose
> unavailable data, test no-look-ahead.
> **Ask first:** change the public terminal route shape, migrate a persistent
> store, add dependencies, make N5/promotion claims.
> **Never:** overwrite prior archive labels, fetch private vendor data, use a
> vendor output as production fallback, **or present a screen as advice**.

Also binding: the clean-room detector **must not call BananaPatterns at
runtime**; `detectorTrust` is **additive** and must not change existing
booleans or enums; unsafe/questionable detectors are **non-rankable**.

**Important honest note:** external validation was executed and its premise
falsified (2026-08-29) — the public universe anonymises most symbols, only 25
of 4,673 rows matched NSE tickers, and rvol/adr were null on all 25. **No
claim of parity or superiority may be made in either direction.** Do not
present BananaPatterns comparison numbers in the UI.

### `P-01` Surface base lifecycle stage — see `D-07`
`TONIGHT_REPORT.base_episodes` is emitted and rendered nowhere → dormant code.
Stages: `EARLY BASE · MID BASE · FINAL CONTRACTION · BREAKOUT · EXTENDED`.
**Accept:** stage visible per candidate that has an episode; `—` otherwise.

### `P-02` Base geometry panel on Stock
From the episode: base window, pivot, floor, depth %, contraction count,
individual contraction depths, duration.
```
BASE STRUCTURE
Window        2026-05-12 → 2026-08-21   (71 sessions)
Depth                 13.31%
Contractions          3      -18.2% → -11.4% → -6.3%
Pivot            ₹1003.70
```
**Accept:** every number traces to the `BaseEpisode`; nothing recomputed in the
UI.

### `P-03` Screen presets as pure predicates
Presets (VCP / Blue sky / Multi-year / IPO base) are **named predicates over
BaseEpisodes** that return included **and excluded** rule reasons.
**Accept:** selecting a preset shows, for each excluded candidate, the specific
rule that excluded it. A preset that cannot explain a rejection is incomplete.

### `P-04` Non-rankable detectors cannot be ranked
`trust.rankable === false` (e.g. `base_breakout`, currently `REVIEW_REQUIRED`)
must be excluded from any ranking or preset "actionable" list, while remaining
visible with its reason.
**Accept:** a non-rankable detector never appears in a ranked/actionable
position.

### `P-05` Failed-poke markers carry confirmation time
Never render a failed-poke as if it were known on its occurrence date.
**Accept:** each marker shows its confirmation timestamp; a point-in-time
replay at the occurrence date does not show it.

### `P-06` Never present a screen as advice
**Accept:** no preset output uses instructional language ("buy", "take",
"recommended"). Presets describe structure; the human decides.

---

# PART 15 — FOOLPROOFING HARVEST FROM THE REFERENCE REPOS

## 15.0 Rules for adopting anything from an external repo

All five reviewed repos (`tanmaykaper/Paper-Trading-Bot`,
`Algo-Ankit/TradeProject`, `chandewardnyanesh/kronos-nse-terminal`,
`85599/kjscreener`, `ombhojwani11/NSE-Institutional-Swing-Strategy`) are
yfinance-based with **no corporate-action handling and no point-in-time
versioning**. **Do not port architecture. Harvest ideas only.**

1. **Clean-room only.** Read their LICENSE. Adopt the *idea*, write the code
   here, cite the source in the module docstring — the convention already used
   by `base_pattern.py` and `features/activity.py`.
2. **No new runtime dependency** without asking (integration-spec boundary).
3. Anything adopted must be **wired and surfaced in the same slice**, or it is
   dormant code.

### `R-01` Deflated Sharpe Ratio — the single most valuable harvest
Source idea: `Algo-Ankit/TradeProject`. The repo has **zero statistical
testing** and is about to compare 8 detectors — that manufactures a winner by
construction. Implement in `unidesk/research/significance.py`:
DSR accounting for number of configurations tried, plus a block-bootstrap CI.
**Accept:** a deliberately null signal fails promotion under DSR; unit tests
against known inputs.

### `R-02` A/B/C controlled-backtest structure
Source idea: `Paper-Trading-Bot`. Maps onto Constitution §7's three
competitors: champion / champion+L1.5 / champion+L2.
**Accept:** the harness runs all three arms on the same sample and reports
coverage per arm.

### `R-03` Standard walk-forward metric suite
Source idea: `kronos-nse-terminal`. `compare_edge()` is a bare mean comparison.
Add Sharpe, max drawdown, hit rate, P&L curve, expectancy — each with sample
size attached.
**Accept:** no metric is displayed without its `n`.

### `R-04` Equity-curve view ("Growth of ₹10,000")
Source idea: `kjscreener`. Makes the claim legible at a glance.
**Accept:** curve is net of the cost model, and labelled as backtest, not
account performance.

### `R-05` Paper-trading / call ledger
Source idea: `Paper-Trading-Bot`. Closes the loop: the desk records its own
calls and their outcomes, accumulating a track record without waiting for N5.
Overlaps `D-03`/`D-09` — build once, on the `Desk` screen.
**Accept:** a call recorded tonight is resolvable tomorrow without manual
bookkeeping.

### `R-06` Risk engine — sizing inputs, exposure checks
Source idea: `TradeProject`. **Charter limit (`X-05`): may compute and display
exposure and loss-to-invalidation; may NOT author a recommended size.**
**Accept:** gross/net exposure visible; no prescriptive size string.

### `R-07` Kill switch / live risk monitor — `SKIPPED` by design
Requires live execution, which the charter forbids ("**Manual execution only.
No order routing, ever.**").
**Accept:** recorded as deliberately skipped, with the charter citation.

### `R-08` Kronos foundation model — `BLOCKED` by constitution
Constitution §10 freezes the encoder family to a Temporal CNN and forbids
architecture expansion until a new research version is declared; §0 forbids
predictive AI before the Phase 0 gate.
**Accept:** recorded as blocked with both citations.

### `R-09` Delivery / turnover anomaly features
Source idea: `NSE-Institutional-Swing-Strategy`. `delivery_ratio` and Reactor
Scale already exist; OI-based features require F&O data this project does not
have.
**Accept:** state which proposed features are computable from existing data and
which are blocked on missing sources.

---

# PART 10 — COMPLETION CHECKLIST

Reproduce this table in full in your report. Every row gets DONE / BLOCKED /
SKIPPED plus a note. **A missing row means the work is incomplete.**

```
GLOBAL   G-01 G-02 G-03 G-04 G-05 G-06 G-07
HOME 1   H1-01 H1-02 H1-03 H1-04 H1-05 H1-06 H1-07 H1-08 H1-09 H1-10
HOME 2   H2-01 H2-02 H2-03 H2-04 H2-05 H2-06 H2-07 H2-08 H2-09 H2-10
         H2-11 H2-12 H2-13 H2-14
HOME 3   H3-01 H3-02 H3-03 H3-04 H3-05 H3-06 H3-07 H3-08 H3-09
HOME 4   H4-01 H4-02 H4-03 H4-04 H4-05 H4-06 H4-07 H4-08
CANDID   C-01 C-02 C-03 C-04 C-05 C-06 C-07 C-08 C-09
STOCK    S-01 S-02 S-03 S-04 S-05 S-06 S-07 S-08 S-09 S-10
BACKEND  B-01 B-02 B-03 B-04 B-05 B-06 B-07 B-08 B-09
DECISION D-01 D-02 D-03 D-04 D-05 D-06 D-07 D-08 D-09 D-10
         D-11 D-12 D-13
CLASH    X-01 X-02 X-03 X-04 X-05 X-06
AI WAVES A-01 A-02 A-03 A-04 A-05 A-06 A-07
BANANA   P-01 P-02 P-03 P-04 P-05 P-06
HARVEST  R-01 R-02 R-03 R-04 R-05 R-06 R-07 R-08 R-09
```

**Expected statuses today.** PART 13 (`A-*`) is `BLOCKED` behind the Phase 0
gate — only `A-01` (the gate audit) is actionable now. `R-07` is `SKIPPED` by
charter, `R-08` `BLOCKED` by constitution. If you mark any `A-02`..`A-07` as
DONE, you have violated the Phase 0 gate and the work must be reverted.

**Suggested first slice** (highest measured impact, fewest dependencies):
`B-01` → `D-01` (veto), then `D-07` + `D-08` (base stage + late-entry warning,
no new dependencies), then `G-01`/`G-02`/`G-03` (kill the fixtures).

## Final gate — all must hold

1. `npm run build` passes with zero TypeScript errors.
2. No hardcoded market number anywhere in `src/` (grep `65.86`, `2563`,
   `2026-07-03` → no hits).
3. Every screen shows the same session date, following the picker.
4. The regime shown equals `honesty_footer.regime_note`.
5. No screen renders `0` for an uncomputed score.
6. No synthetic chart can be mistaken for real data.
7. `python unidesk/run_checks.py` exits green.
8. `python -m pytest unidesk/tests -q` no new failures.
9. Every ID in PART 10 accounted for.

**If you cannot complete an item, say so explicitly. A partial build honestly
reported is acceptable. A partial build reported as complete is not.**
