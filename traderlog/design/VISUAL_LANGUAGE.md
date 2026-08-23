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

---

## 1. The direction

**Neo-brutalist / utilitarian. Light surface. Very dense.**

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

- **Radius 0. Borders 2px solid black. Shadows none** (except §3's hard offset).
- **Every panel is a hard-bordered rectangle.** Boxes are the grammar here — the
  opposite of the previous direction, where boxes were a last resort.
- **Flat colour only.** A fill is one value. Bars are solid blocks.
- **Uppercase, letterspaced, bold for every label and header.** Labels are
  structural, not decorative.
- **Mono for every numeral**, tabular figures, right-aligned in tables.
- **Colour carries state only** — and must stay redundant with position, shape,
  or text. The screen has to survive greyscale.
- **Every chart has a scale**: labelled axis, reference line, or direct labels.
- **`n` is always visible** beside any percentage or average.
- **Density is the point.** 11–12px body, many marks per screen. This is an
  expert instrument for one user, not an onboarding surface.
  Rows are **~22px plain, ~30px where the row carries an interactive control**.
  That is not slack: a 28×28 minimum hit target cannot live inside a 22px row.
  Accessibility wins that argument. The control's *visual* box stays small (18px)
  and its hit area is extended with a pseudo-element so it does not drive layout
  height further — see `.disclosure` in `app.css`.
- **Numeric precision is adaptive, and this is a correctness rule, not styling.**
  Below ₹100, show 2 decimals; at or above, show none. A fixed 0dp once rendered
  a real broker fill price of `39.05` as `39` — rounding away evidence a trader
  actually stated is the same class of error as inventing a number.

---

## 2. Chart vocabulary

The house set, unchanged in *function* from the previous direction — the forms
were right, only their finish changes. All are plain inline SVG in
`ui/src/components/charts.jsx`. **No chart library, ever.**

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
8. Is it dense enough? Rows ~22px, body 11–12px. If it feels roomy, tighten it.

---

## 6. Component contract — `ui/src/components/charts.jsx`

Build exactly these. Do not add props, do not rename, do not invent variants.
Plain inline SVG, `viewBox` + `width="100%"`, `role="img"` with an `aria-label`
stating the finding in words, colour only from CSS custom properties.

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

- Plain inline SVG. Components live in `ui/src/components/charts.jsx`.
- `viewBox` + `width="100%"`; never fixed pixel widths.
- Colour comes from CSS custom properties (`fill="var(--ok)"`), so a token change
  propagates. **No raw hex in a component, ever.**
- `role="img"` and an `aria-label` stating the finding on every chart. A chart
  that cannot be described in a sentence probably should not exist.
- Charts do not animate on load. There is no argument for it.
- `tokens.css` is the only file allowed to contain a colour literal.
