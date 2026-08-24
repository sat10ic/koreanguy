# VISUAL LANGUAGE — binding

**Read this before designing or building any screen.** It sits above
`WIREFRAMES.md`: the wireframes say what goes on a screen, this says what it may
look like. A screen that satisfies its wireframe and violates this file is a
defect.

**Scouting × Wire — 2026-08-24 (owner decision).** The fourth visual direction
is binding and is specified in full in `design/REDESIGN_SCOUTING_WIRE.md` —
dark ground, citrus accent meaning exactly one thing (money was risked), wire
triage bands on TODAY, the shared time axis on LEDGER. **On build it supersedes
§1, §1a and §3 below in full.** Where any clause in §1/§1a/§3 conflicts with
`REDESIGN_SCOUTING_WIRE.md`, the redesign document wins. The renderer ladder
(§2), the component contract (§6), the truth/evidence rules and the empty-state
contract carry over unchanged. Every colour still resolves through the tokens
in `ui/src/styles/tokens.css` — that file is the only place a colour literal
may exist.

**Quiet editorial terminal — 2026-08-23 (owner decision).** This revision
REPLACES the prior evidence-desk / paper-ink direction in full. The 2px black
frames, pure `#000` ink, hard 3px offset shadows, saturated signal colours
(hazard yellow, electric blue), and black block-invert hover are gone; nothing
of the neo-brutalist finish survives. The binding mood is a **calm
trading/research instrument** — warmer, quieter, more surgical.

What survives **unchanged** from the evidence desk (the owner's keep-list):

- The evidence-desk spine: post → reply → trade event → archived chart
  evidence. A generic card grid is not a substitute.
- The two-column FEED workspace (primary thread column + secondary rail), the
  centered **1680px desktop grid** (§1a), and the section-to-section
  information architecture.
- Every element and datum of the six product screens (WIREFRAMES.md is
  unchanged and its element lists are still binding).
- The thread spine (now the same quiet 1px ink rule — kept as the signature,
  never deleted), contained thumbnails beside the evidence they support,
  truthfully counted unresolved disclosure, and the compact future-block empty
  states.
- The renderer ladder (§2), the component contract (§6), and the
  implementation rules (§7).
- Zero document overflow at the acceptance viewport; roles/aria, keyboard
  access, and the 11px label floor.

Where any clause below conflicts with this revision, this revision wins —
including §6's "2px black bordered rectangle" empty-state clause (empty states
render as ONE compact muted line, `.chart-empty`, never a framed rectangle).

## The binding appearance

- **Mood:** a calm instrument, not a brutalist poster. Density comes from
  hierarchy, not from boxes.
- **Colour:** warm-neutral canvas; panels/paper a hair lighter; ink is a soft
  near-black, never pure black; ONE deep restrained blue accent for
  interaction, navigation, links, and active states; amber for unresolved;
  green and red **only** for genuine measured positive/negative states.
  Every colour resolves through the tokens in `ui/src/styles/tokens.css` —
  that file is the only place a colour literal may exist.
- **Structure:** ONE **1px** structural rule (ink) defines each major region
  (shell, panels, the thread spine). Interior uses 1px hairlines
  (`--rule`) or nothing. **No nested boxes.**
- **Type:** refined grotesk with tabular numerals for every numeric. Scale is
  unchanged (body 14px, mega 40px, value 16px, ui 12px, label/micro 11px
  floor). Sentence case everywhere except the compact nav tab rail
  (uppercase, quiet underlined labels) and single-word table column
  micro-labels.
- **Controls:** sentence-case content, calm 1px outline, muted ink. Buttons
  and flat controls are lighter: thin 1px border, one subtle 1px offset press
  affordance, no heavy shadows. Radius stays 0.
- **Denied:** card grids, fake KPIs, gradients, glows, rounded corners, any
  shadow beyond a soft 1px, invented metrics, decorative charts, random
  icons, ornamental anything.

---

## 1a. Desktop composition rules (binding, W3c)

- **Grid:** a centered **1680px content grid** at 1920×1080 (120px left and
  right). The header's contents align to the same 1680px grid as the content —
  one horizontal system, never two.
- **Type:** normal reading copy is **14–15px**. 11–12px is **metadata only**
  (timestamps, captions, hints; table data cells may stay compact). Sentence
  case is the default for prose and headings; uppercase is reserved for the
  compact nav tab rail and single-word table column micro-labels. Density
  comes from useful comparison and hierarchy, not from small text packed into
  bordered boxes.
- **Borders:** ONE **1px** structural rule (ink) defines each **major region**
  (the shell, panels, the thread spine). 1px hairlines (`--rule`) may separate
  rows, evidence lines, and interior structure. Not every subsection is a
  bordered box, and no region nests a second box.
- **Mono** is for numbers, dates, confidence values, and identifiers — never
  prose.
- **Colour** remains state- or interaction-bearing, never decoration.
- The only acceptance viewport for desktop work is **1920×1080**.

---

## 1. The direction

**Quiet editorial terminal. Warm-neutral. Light. Very dense.**

A calm trading/research instrument on a warm paper canvas. Soft near-black
ink, hairline structure, restrained signal colours, one deep blue accent. It
should look **surgical and deliberate** — a desk someone works at for hours,
not a poster.

Test: *would this screen still work printed on warm paper with a thin pen?* If
a mark cannot say what it encodes, delete it.

Second test: *could you describe this screen entirely as rules, hairline
separators, and type?* If it needs a wash, a glow, or a 2px box to look
finished, the composition is wrong.

### Banned outright

Two families are banned: the generic AI trading terminal (still), and the
hard-edged neo-editorial/brutalist look this file just replaced.

| Banned | Family | Why |
|---|---|---|
| Rounded corners of any radius | both | Radius is **0** everywhere. No exceptions, including buttons and chips. |
| Soft/blurred shadows, `box-shadow` with blur | both | Only the subtle 1px hard offset is allowed (§3) |
| Any shadow stronger than a 1px offset | old direction | The old 3px hard shadow is gone with it |
| Black block-invert hover on controls/rows | old direction | Hover is a warm tint (`--surface-2`) or an underline; never a solid black block |
| Gradients of any kind — linear, radial, on any surface or mark | both | Flat fills only |
| Serif type anywhere | editorial | Grotesk and mono only |
| Pure `#000` ink | old direction | Ink is the soft near-black `--ink`; pure black is banned as a colour value |
| 2px (or heavier) borders on major regions or interior elements | old direction | One 1px structural rule per region; 1px hairlines inside |
| Dark canvas, neon, glow, bloom, glassmorphism, backdrop-blur | AI-terminal | — |
| Donut chart with a number in the hole, gauges, radial progress | AI-terminal | Bad at reading values, universally overused |
| A row of 6 soft KPI cards (or any card grid) | AI-terminal | The universal AI-dashboard tell |
| Purple / indigo / violet | AI-terminal | The default LLM palette |
| Force-directed graphs, 3D, isometric | AI-terminal | — |
| Animated counters, pulsing, shimmer, fade-in | both | We never animate a price, stop, result, or verdict |
| Emoji as a data encoding | both | Fine as a marker in copy; never as a value |
| Icon-library chrome (lucide/heroicons everywhere) | both | Type, rules and blocks carry this design |

### Required

- **Radius 0. ONE 1px structural rule per major region; 1px hairlines for
  interior rows and evidence lines.** No nested boxes.
- **Sentence case for prose, headings, chips, buttons, and panel titles.**
  Uppercase only for the compact nav tab rail and single-word table column
  micro-labels.
- **Mono for every numeral**, tabular figures, right-aligned in tables. Mono is
  for numbers, dates, confidence, and identifiers — never prose.
- **Colour carries state only** — and must stay redundant with position, shape,
  or text. The screen has to survive greyscale. The palette: amber for
  unresolved, green/red for genuine measured states, the single blue accent
  for interaction/navigation/active — everything else is the warm ink ladder.
- **Every chart has a scale**: labelled axis, reference line, or direct labels.
- **`n` is always visible** beside any percentage or average.
- **Density comes from comparison and hierarchy** (§1a). Reading copy is
  14–15px; 11–12px is metadata only. Table rows may stay compact:
  **~26px plain, ~30px where the row carries an interactive control** — a
  28×28 minimum hit target cannot live inside a tighter row. Accessibility wins
  that argument. The control's *visual* box stays small (18px) and its hit area
  is extended with a pseudo-element so it does not drive layout height further —
  see `.disclosure` in `app.css`.
- **Numeric precision is adaptive, and this is a correctness rule, not styling.**
  Below ₹100, show 2 decimals; at or above, show none. A fixed 0dp once rendered
  a real broker fill price of `39.05` as `39` — rounding away evidence a trader
  actually stated is the same class of error as inventing a number.

---

## 2. Chart vocabulary

The house set is a semantic vocabulary, not a renderer lock. The forms remain
stable because each has a specific analytical job; their implementation follows
the binding renderer ladder below. Existing inline-SVG components may remain
while they are migrated, but new visualization work must not extend an
inline-SVG-only architecture.

| Need | Binding implementation | Use it for |
|---|---|---|
| **Price candles / OHLC** | **[lightweight-charts](https://github.com/tradingview/lightweight-charts)** | the price pane for a symbol: candles, volume, overlays. **This row only.** Do not reach for it for anything that is not an instrument's price series. |
| Core trading terminal | **[Apache ECharts](https://github.com/apache/echarts)** | live dashboards, time-series, heatmaps, and coordinated multi-panel analytics |
| Custom analytical graphics | **[Vega-Lite](https://github.com/vega/vega-lite)** | regime bands, percentile strips, benchmark zones, RR bars, layered signals, and other bespoke quantitative views |
| LLM-created analytical visuals | **[Microsoft Flint Chart](https://github.com/microsoft/flint-chart)** | dumbbells, bullet charts, ranged dots, slope charts, waterfalls, and ad-hoc panels; review the generated spec and emit to ECharts or Vega-Lite by default |
| Heavy interactive exploration | **[Plotly.js](https://github.com/plotly/plotly.js)** | zoom/hover/crosshair-heavy exploration, financial charts, and interactive diagnostics only |

**A price pane may only render bars that exist in `daily_prices`, for a symbol
validated against the NSE universe.** A candle chart is the most authoritative-
looking surface in this tool; a chart of the wrong instrument, or of invented
bars, is worse than no chart. If either is missing, render the labelled empty
state and say which.

Choose the first row that satisfies the need. Plotly is optional, not a second
default terminal renderer. Flint is the agent-generation path, not a runtime
excuse to bypass checked-in component contracts, accessibility, tokens, or
source-backed data.

House finish rules that apply to every one of them (quiet-editorial finish):
- A chart draws **no frame of its own**; the panel's single structural rule
  contains it. Never a second border around the graphic.
- Marks are **flat solid fills** with a 1–2px ink stroke where they need
  definition. No soft edges, no opacity ramps for decoration.
- Bars are rectangles, full-height within their row, hard-ended. Not rounded,
  not tapered.
- Axis lines are 1–2px ink. Gridlines, if any, are 1px and a flat warm grey
  (`--rule`) — never dotted-and-fading.
- Chart colour resolves entirely through the tokens (§7) — the palette change
  propagates to every renderer without touching chart code.

| # | Form | Job |
|---|---|---|
| 2.1 | **PositionBars** | one row per position on a shared time axis; clustering in time is the finding |
| 2.2 | **Dumbbell** | any stated-vs-actual pair; the GAP is the finding |
| 2.3 | **StripPlot** | distributions; replaces a bare median, exposes bimodality |
| 2.4 | **BandLine** | bounded series over time with threshold bands as flat rects |
| 2.5 | **Ribbon** | one hard block per session; categorical state over time |
| 2.6 | **StackedStrip** | composition in one bar, labelled in place. Never a pie |
| 2.7 | **SmallMultiples** | grid of miniatures on a SHARED scale |
| 2.8 | **Treemap** | HEATMAP screen only (W9); flat fills, 1px gutters |
| 2.9 | **CalendarGrid** | cadence; weeks × weekdays, one hard cell per session |

---

## 3. Buttons and controls

Controls are **flat and light**, like paper instrument controls, not chunky
mechanical blocks.

- **The one permitted shadow** is a subtle hard offset: `1px 1px 0 var(--ink)`,
  no blur. It is the press affordance. On `:active` the element translates
  `1px, 1px` and the shadow collapses to nothing. Nothing else in the app casts
  a shadow.
- **Hover** warms the control: background becomes `--surface-2`. Instant, no
  transition on colour. Text links underline in the accent. This is the
  primary interactive signal.
- **Segmented control** for ≤4 mutually exclusive options, preferred over a
  dropdown — it shows the alternatives without a click. Active segment is
  filled with the accent blue and `--on-ink` text.
- **Filter chips** carry an explicit ✕ when active; the active chip is filled
  with the accent blue.
- **Sortable column headers** with a caret; the caret takes the accent when
  active. Sorting is the primary interaction on a dense table.
- **Row expansion** uses a real disclosure caret, never a bare row click. The
  open roster/detail row is marked with a warm tint and a thin accent left bar.
- **Nav tab rail:** uppercase compact labels on a quiet **underlined rail** —
  the active tab is ink text with a 2px accent underline; hover only darkens
  the label. No fill, no box.
- Minimum hit target 28px. **Focus ring is a 2px accent outline with 2px
  offset** and is never removed.

---

## 4. Layout

- **One centered 1680px content grid at 1920×1080** (§1a). Header and content
  align to it; nothing anchors hard-left with a dead right field.
- **The grid is visible through ONE 1px structural rule per region.** Adjacent
  regions share rules rather than floating apart on whitespace. Interior
  structure is 1px hairlines or nothing — never a nested box.
- **Asymmetry is fine**; a uniform 4-up card grid is not.
- **No serif, ever.** The single most important number on a screen earns its
  emphasis through **size and weight** — large, ink, mono or heavy grotesk —
  not through a different family.
- **One dominant number per screen**, maximum. More than one is the KPI-card
  pattern in a quieter costume.
- Section labels are sentence case, small, 700 weight. Panel titles are
  sentence case with a hairline under them.
- Tables: 1px ink header rule, 1px `--rule` row hairlines, mono right-aligned
  numerals, ~22px rows. Single-word column heads may stay uppercase
  micro-labels; multi-word heads are sentence case.

---

## 5. How to check your work

Before calling a screen done:

1. Screenshot or inspect it. Does any element appear on the banned list in §1?
2. Is any `border-radius` non-zero anywhere? Is any `box-shadow` blurred or
   stronger than a 1px offset? Is any serif font in use? Any gradient? Any
   pure `#000`? Any 2px border anywhere? Any nested box (a bordered element
   inside an already-bordered region)? All must be no.
3. Cover every number with your hand. Does the screen still communicate its
   headline? If not, it is a table wearing a costume.
4. Count non-tabular graphics. Zero on a data screen = unfinished.
5. Count dominant numbers. More than one per screen = defect.
6. Is every percentage accompanied by its `n`?
7. Would it survive greyscale? Colour must be redundant with position, shape,
   or label — never the sole carrier of meaning.
8. Is it dense enough? Reading copy 14–15px, metadata 11–12px, rows compact
   but hit-target-safe (§1a). If it feels roomy, tighten; if reading copy
   shrinks below 14px to gain density, that is the 12px-box defect again.
9. Is prose sentence case, with uppercase only on the nav rail and
   single-word column heads?
10. Does every colour on screen resolve through `tokens.css`? A raw hex
    anywhere else is a defect.

---

## 6. Component contract — `ui/src/components/charts.jsx`

Build exactly these. Do not add props, do not rename, do not invent variants.
These React APIs are renderer-agnostic wrappers: callers must not depend on
ECharts, Vega-Lite, Flint, Plotly, or legacy inline-SVG internals. Every wrapper
exposes an accessible name stating the finding in words and resolves colour
through CSS custom properties.

```jsx
// 2.1 — one row per position on a SHARED time axis
<PositionBars
  from="2026-07-20" to="2026-08-22"
  rows={[{
    id, label, sublabel,
    start, end,                               // end null => still open
    result,                                   // null => unstated; drives colour
    warn,                                     // optional ⚠ suffix
    events: [{ at, kind: "add"|"sl_up"|"sl_down"|"exit" }],
  }]}
  onRowClick={fn}
/>

// 2.2 — the GAP is the finding. Rule tinted warning when |a-b| > gapWarn.
// `n` is REQUIRED whenever the values are percentages (§1).
<Dumbbell rows={[{ label, a: {value, label}, b: {value, label}, n }]}
          max={100} gapWarn={10} suffix="%" n={183} />

// 2.3 — one tick per observation + median rule
<StripPlot values={[3,5,5,11,28]} median={11} suffix="d" />

// 2.4 — line + flat threshold-band rects behind it
<BandLine points={[{x,y}]} bands={[{at,label}]} log />

// 2.5 — one hard block per session
<Ribbon cells={[{ key, state:"GREEN"|"WHITE"|"RED"|"NONE", warn, title }]} />

// 2.6 — one bar split proportionally, labelled IN PLACE. Never a pie.
<StackedStrip segments={[{ label, value }]} n={183} suffix="%" />

// 2.7 — grid of miniatures on a SHARED scale
<SmallMultiples items={[{ label, values, caption }]} />
```

Controls, in `ui/src/components/ui.jsx`:

```jsx
<Segmented options={["5d","20d","90d"]} value onChange />
<SortableTh label="net" active dir="asc"|"desc" onClick />
<Disclosure open onToggle />
```

**Empty states are part of the contract.** Every chart renders a labelled empty
frame — a 2px black bordered rectangle with a one-line reason — when it has no
data. Never `null`, never a zero-height SVG, never a collapsed panel. The
database is real-data-only and sparse, so the empty state is what will actually
be on screen most often. It must look deliberate.

> **Superseded by the quiet-editorial-terminal revision (2026-08-23):** the
> "2px black bordered rectangle" in the paragraph above is gone. Empty states
> render as ONE compact muted line (`.chart-empty`, ~12px, `--ink-3`) naming
> the reason — shared by every chart wrapper and already how
> `charts.jsx` behaves. Large framed empty graphics remain banned everywhere.

---

## 7. Implementation notes

- Components live in `ui/src/components/charts.jsx`; renderer-specific adapters
  stay behind those public React component contracts.
- ECharts is the default for terminal-scale and coordinated dashboard visuals.
- Vega-Lite owns bespoke statistical grammar and layered analytical marks.
- Flint-generated specifications are reviewed, normalized to project tokens and
  accessibility rules, and checked in as deterministic code/specs. Prefer its
  ECharts or Vega-Lite output; Plotly output is justified only by the interaction
  requirement below.
- Plotly.js is loaded only for views whose core value depends on deep zoom,
  hover, crosshair, or financial-chart exploration. Do not ship it for a static
  chart that ECharts or Vega-Lite can express.
- Legacy inline SVG remains valid during migration, but new chart behavior must
  follow the renderer ladder in §2.
- Charts are responsive; never use fixed pixel widths.
- Colour comes from CSS custom properties (`fill="var(--ok)"`), so a token change
  propagates. Translate those tokens into each library's config at the adapter
  boundary. **No raw hex in a component or chart spec, ever.**
- `role="img"` and an `aria-label` stating the finding on every chart. A chart
  that cannot be described in a sentence probably should not exist.
- Charts do not animate on load. There is no argument for it.
- `tokens.css` is the only file allowed to contain a colour literal.