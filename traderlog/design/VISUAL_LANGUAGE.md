# VISUAL LANGUAGE — binding

**Read this before designing or building any screen.** It sits above
`WIREFRAMES.md`: the wireframes say what goes on a screen, this says what it may
look like. A screen that satisfies its wireframe and violates this file is a
defect.

**Rewritten 2026-08-23.** The previous direction was "editorial statistical
almanac" — serif display faces, warm newsprint washes, hairline rules. It was
inherited from Manas OS's locked aesthetic bar rather than chosen for this tool,
and the repo owner rejected it outright. A trader-intel instrument is not a
magazine. Everything below replaces it; nothing from the editorial direction
survives.

**W3c PC revision, 2026-08-23.** The owner then rejected the first
neo-brutalist *result* at 1920×1080: a 1240px left-anchored page, 12px reading
copy, and box-heavy composition that followed this file's prose literally while
producing a poor instrument. The binding direction is now an **evidence desk** —
part exchange blotter, part research notebook. Thread, event, chart evidence,
and citation are the visual grammar. §1a's desktop rules supersede any
conflicting clause below; the renderer ladder (§2), truth/evidence rules, and
the empty-state contract are unchanged.

---

## 1a. Desktop composition rules (binding, W3c)

- **Grid:** a centered **1680px content grid** at 1920×1080 (120px left and
  right). The header's contents align to the same 1680px grid as the content —
  one horizontal system, never two.
- **Type:** normal reading copy is **14–15px**. 11–12px is **metadata only**
  (timestamps, captions, hints, table data cells may stay compact). Uppercase is
  for structural micro-labels, not every sentence. Density comes from useful
  comparison and hierarchy, not from small text packed into bordered boxes.
- **Borders:** 2px solid black defines **major regions** (the shell, panels,
  the thread spine). 1px rules may separate rows, evidence lines, and interior
  structure. Not every subsection is a heavy 2px box.
- **Mono** is for numbers, dates, confidence values, and identifiers — never
  prose.
- **Colour** remains state- or interaction-bearing, never decoration.
- The only acceptance viewport for desktop work is **1920×1080**.

---

## 1. The direction

**Neo-brutalist / utilitarian. Light surface. Very dense.**

**Owner acceptance viewport, 2026-08-23:** audit the current TraderLog visual
overhaul at **1920x1080 only** unless the owner explicitly requests another
viewport. Do not substitute mobile, tablet, laptop, or multi-viewport findings
for the PC review.

Hard edges, heavy black borders, flat blocks of solid colour, chunky confident
type, zero decoration. It should look **engineered and deliberate** — like a
machine's control surface built by someone who cared about function and refused
to prettify it. Nothing soft. Nothing rounded. Nothing that fades.

Test: *does every element look like it was placed by an engineer defending a
decision, or by a designer filling space?* If a mark cannot say what it encodes,
delete it.

Second test: *could you describe this screen entirely as rectangles, rules, and
type?* If it needs a soft transition, a wash, or a glow to look finished, the
composition is wrong.

### Banned outright

Two families are banned: the generic AI trading terminal (still), and the
editorial aesthetic this file just replaced.

| Banned | Family | Why |
|---|---|---|
| Rounded corners of any radius | brutalist | Radius is **0** everywhere. No exceptions, including buttons and chips. |
| Soft/blurred shadows, `box-shadow` with blur | brutalist | Only a hard offset shadow is allowed (§3), never a blurred one |
| Gradients of any kind — linear, radial, on any surface or mark | both | Flat fills only |
| Serif type anywhere | editorial | The old display face is gone. Grotesk and mono only. |
| Warm newsprint / cream / beige surfaces | editorial | Surfaces are white, near-white, or black |
| Hairline 1px borders as the primary separator | editorial | Borders are **2px solid black**. Hairlines read as timid here. |
| Dark canvas, neon, glow, bloom, glassmorphism, backdrop-blur | AI-terminal | — |
| Donut chart with a number in the hole, gauges, radial progress | AI-terminal | Bad at reading values, universally overused |
| A row of 6 soft KPI cards | AI-terminal | The universal AI-dashboard tell |
| Purple / indigo / violet | AI-terminal | The default LLM palette |
| Force-directed graphs, 3D, isometric | AI-terminal | — |
| Animated counters, pulsing, shimmer, fade-in | both | We never animate a price, stop, result, or verdict |
| Emoji as a data encoding | both | Fine as a marker in copy; never as a value |
| Icon-library chrome (lucide/heroicons everywhere) | both | Type, rules and blocks carry this design |

### Required

- **Radius 0. Borders 2px solid black for major regions; 1px rules for interior
  rows and evidence lines.** Shadows none (except §3's hard offset).
- **Every panel is a hard-bordered rectangle.** Boxes are the grammar here — the
  opposite of the previous direction, where boxes were a last resort. Interior
  structure inside a panel does not need its own heavy box.
- **Flat colour only.** A fill is one value. Bars are solid blocks.
- **Uppercase, letterspaced, bold for structural micro-labels** (section and
  column headers, chips, kind tags) — never for sentences or prose.
- **Mono for every numeral**, tabular figures, right-aligned in tables. Mono is
  for numbers, dates, confidence, and identifiers — never prose.
- **Colour carries state only** — and must stay redundant with position, shape,
  or text. The screen has to survive greyscale.
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
| Core trading terminal | **[Apache ECharts](https://github.com/apache/echarts)** | live dashboards, time-series, heatmaps, and coordinated multi-panel analytics |
| Custom analytical graphics | **[Vega-Lite](https://github.com/vega/vega-lite)** | regime bands, percentile strips, benchmark zones, RR bars, layered signals, and other bespoke quantitative views |
| LLM-created analytical visuals | **[Microsoft Flint Chart](https://github.com/microsoft/flint-chart)** | dumbbells, bullet charts, ranged dots, slope charts, waterfalls, and ad-hoc panels; review the generated spec and emit to ECharts or Vega-Lite by default |
| Heavy interactive exploration | **[Plotly.js](https://github.com/plotly/plotly.js)** | zoom/hover/crosshair-heavy exploration, financial charts, and interactive diagnostics only |

Choose the first row that satisfies the need. Plotly is optional, not a second
default terminal renderer. Flint is the agent-generation path, not a runtime
excuse to bypass checked-in component contracts, accessibility, tokens, or
source-backed data.

Brutalist finish rules that apply to every one of them:
- Every chart sits inside a 2px black bordered frame.
- Marks are **flat solid fills with a 1.5–2px black stroke** where they need
  definition. No soft edges, no opacity ramps for decoration.
- Bars are rectangles, full-height within their row, hard-ended. Not rounded,
  not tapered.
- Axis lines are 2px black. Gridlines, if any, are 1px and a flat grey — never
  dotted-and-fading.

| # | Form | Job |
|---|---|---|
| 2.1 | **PositionBars** | one row per position on a shared time axis; clustering in time is the finding |
| 2.2 | **Dumbbell** | any stated-vs-actual pair; the GAP is the finding |
| 2.3 | **StripPlot** | distributions; replaces a bare median, exposes bimodality |
| 2.4 | **BandLine** | bounded series over time with threshold bands as flat rects |
| 2.5 | **Ribbon** | one hard block per session; categorical state over time |
| 2.6 | **StackedStrip** | composition in one bar, labelled in place. Never a pie |
| 2.7 | **SmallMultiples** | grid of miniatures on a SHARED scale |
| 2.8 | **Treemap** | HEATMAP screen only (W9); flat fills, 2px black gutters |
| 2.9 | **CalendarGrid** | cadence; weeks × weekdays, one hard cell per session |

---

## 3. Buttons and controls

Controls look **physical and mechanical**, not glassy.

- **The one permitted shadow** is a hard offset: `3px 3px 0 var(--ink)`, no blur.
  It is the brutalist press affordance. On `:active` the element translates
  `2px, 2px` and the shadow shrinks to `1px 1px 0`. Nothing else in the app
  casts a shadow.
- **Hover inverts**: background goes black, text goes white. Instant, no
  transition on colour. This is the primary interactive signal.
- **Segmented control** for ≤4 mutually exclusive options, preferred over a
  dropdown — it shows the alternatives without a click. Active segment is
  filled black with white text.
- **Filter chips** carry an explicit ✕ when active.
- **Sortable column headers** with a caret; sorting is the primary interaction
  on a dense table.
- **Row expansion** uses a real disclosure caret, never a bare row click.
- Minimum hit target 28px. **Focus ring is a 2px black outline with 2px offset**
  and is never removed.

---

## 4. Layout

- **One centered 1680px content grid at 1920×1080** (§1a). Header and content
  align to it; nothing anchors hard-left with a dead right field.
- **The grid is visible.** Hard 2px rules divide regions. Adjacent panels share
  borders rather than floating apart on whitespace.
- **Asymmetry is fine**; a uniform 4-up card grid is not.
- **No serif, ever.** The single most important number on a screen earns its
  emphasis through **size and weight** — large, black, mono or heavy grotesk —
  not through a different family.
- **One dominant number per screen**, maximum. More than one is the KPI-card
  pattern in brutalist clothing.
- Section labels are uppercase, letterspaced, 700 weight, small.
- Tables: 2px black header rule, 1px row rules, mono right-aligned numerals,
  ~22px rows.

---

## 5. How to check your work

Before calling a screen done:

1. Screenshot or inspect it. Does any element appear on the banned list in §1?
2. Is any `border-radius` non-zero anywhere? Is any `box-shadow` blurred?
   Is any serif font in use? Any gradient? All four must be no.
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
