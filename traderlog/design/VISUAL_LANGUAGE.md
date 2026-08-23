# VISUAL LANGUAGE — binding

**Read this before designing or building any screen.** It sits above
`WIREFRAMES.md`: the wireframes say what goes on a screen, this says what it may
look like. A screen that satisfies its wireframe and violates this file is a
defect.

Written 2026-08-23 after the W0 shell was judged bland — correctly. It was tables
with bars beside them. Data that could be a picture must be a picture.

---

## 1. The reference, and the anti-reference

**Build toward:** a printed statistical almanac. Financial Times and Economist
data pages, Tufte small multiples, Swiss data print, the dense results pages of a
cricket almanac. Marks drawn as **ink on paper**.

Test: *could this graphic be printed in two colours on newsprint and still carry
its meaning?* If it needs a glow, a gradient, or a dark background to read, it is
decoration pretending to be information.

**Do not build toward:** the default "AI trading terminal". Every model reaches
for this when told to make a trading UI look good, and it is what we are
explicitly refusing.

### Banned outright

| Banned | Why |
|---|---|
| Dark canvas, neon cyan/green, glow, bloom | Bloomberg cosplay. The theme is light and locked. |
| Glassmorphism, frosted panels, backdrop blur | Decoration with no informational job |
| Gradient fills on any data mark | A gradient encodes nothing; it just looks "designed" |
| Drop shadows on data | Shadows are for surfaces, never for bars, lines, or dots |
| Donut chart with a big number in the hole | The single most-used AI dashboard cliché |
| Gauges, speedometers, radial progress | Terrible at reading values, universally overused |
| A row of 6 rounded KPI cards | The universal AI-dashboard tell. Banned as a layout. |
| Purple / indigo / violet accents | The default LLM palette. Not in our tokens. |
| Force-directed network graphs | Impressive-looking, near-unreadable, always slop |
| 3D anything, isometric anything | — |
| Animated counters, pulsing dots, shimmer | We never animate a price, stop, result, or verdict |
| Sparkline in every table cell as texture | Sparklines are for series that matter, not wallpaper |
| Emoji as a data encoding | Fine as a marker in copy; never as a value |
| `rounded-2xl` on everything | Our radius scale tops out at 10px for panels |
| Icon-library chrome (lucide/heroicons everywhere) | Type and rules carry this design, not icons |

### Required

- **Ink discipline.** Colour carries state only: green/red/amber/teal from
  `tokens.css`. Never colour to differentiate categories that have no state.
- **Every chart has a scale.** Labelled axis, a reference line, or direct labels
  on the marks. A shape with no scale is not a chart.
- **`n` is always visible** anywhere a percentage or an average appears.
- **Direct labelling over legends.** Put the label on the mark. A legend is a
  lookup task we are asking the reader to perform.
- **Charts sized to their data**, not stretched to fill a grid cell.
- **Hairlines, not boxes.** 1px rules in `--line` separate; heavy borders do not.
- **Density is good.** This is a research instrument for one expert user. Small
  type, tight leading, many marks per square inch. It should look *closer* to a
  results page than to a landing page.

---

## 2. Chart vocabulary

The house set. Prefer one of these over inventing a new form. All are plain
inline SVG in `ui/src/components/charts.jsx` — **no chart library, ever.**
`lightweight-charts` is not a dependency of this project.

### 2.1 Position bar — the workhorse for LEDGER

One horizontal row per position. Time runs left to right across a shared axis, so
rows are comparable at a glance and clustering in time becomes visible — which is
the entire point of the attention engine.

```
        Jul 20        Aug 01        Aug 15        Aug 22
        │             │             │             │
DIXON   ●━━━━━━━━━━▲━━━━━━━━━━━━━━━━━━━━━━━━━━━━○   +9.9%
        entry      SL↑                        exit
BEL     ●━━━━━━━━━━━━━━━━━━━●━━━━━━━━━━━━━━━━━○     +8.7%
                            add
KPIT              ●━━━━━━━━━━━━━━━━━━━━━━━━━━━━━▶   open, no stop ⚠
```

- `●` filled = entry · `●` on the line = add · `▲` = stop moved up ·
  `○` hollow = exit · `▶` = still open (arrow, not a hard stop)
- Bar colour: green if the stated result was positive, red if negative,
  `ink-mute` if open or unstated. **Never a gradient along the bar.**
- Row height 18px. Twenty positions fit on one screen without scrolling.

### 2.2 Dumbbell — for any stated-vs-actual pair

Two dots joined by a rule. The *gap* is the finding, and a dumbbell makes the gap
the most visible thing on the row. Use for stop stated vs honoured, preached vs
practised, claimed vs measured.

```
stop stated ──────────────────○━━━━━━━━━●      71% → 62%
                        honoured        stated
```

Hollow dot = the weaker number, filled = the stronger, rule between them tinted
amber when the gap exceeds 10 points. Far better than two separate bars, which
force the reader to do the subtraction.

### 2.3 Strip plot — for distributions

One tick per observation on a shared axis, with a median rule. Replaces every
"median hold 11d" scalar. A number hides bimodality; a strip plot shows a trader
who holds two days or three weeks and nothing between.

```
hold days   ┃ ┃┃┃  ┃ ┃┃ ┃    ┃  ┃          ┃        ┃
            0    5    10   15   20   25   30      45
                    ▲ median 11
```

### 2.4 Band line — for any bounded series over time

A line with its threshold bands drawn as flat background rects. Already built for
XP; generalise it. Bands are `panel-2`/`panel-3` washes, **never coloured fills**.
Endpoint gets a dot and a direct label.

### 2.5 Ribbon — one cell per session

Categorical state over time, one small rect per trading day. Already built for
MBI day colour. Reuse for: regime, per-trader posting cadence, whether a stop was
in place. Dense, scannable, prints fine.

### 2.6 Stacked strip — for composition

A single horizontal bar split proportionally, segments labelled in place. Use for
play-type mix and sector tilt. **Not a pie. Not a donut.** A row of stacked strips
across traders is directly comparable; a row of pies is not.

```
@swingdesk   ███████████ breakout 61 ░░░░░ pullback 24 ▒▒▒ ep 15
```

### 2.7 Small multiples — the highest-value form we are not yet using

A grid of identical miniature charts, one per trader or per symbol, on a **shared
scale**. This is the single strongest way to make this tool feel like an
instrument rather than a report, and it is the form most likely to be replaced by
a slop alternative. Do not replace it with a big combined chart.

```
 @swingdesk    @baseandgo    @tapewatcher   @ipobase
 ▁▂▅▇▆▃▂▁      ▁▁▃▄▆▇▇▅      ▂▃▂▁▁▂▃▂      ▁▁▁▂▁▁▁▁
 +18% 21 pos   +9% 14 pos    -2% 9 pos     — 2 pos
```

### 2.8 Treemap — HEATMAP screen only (W9)

Flat fills, hairline gutters, symbol in condensed type, area = priority, tint =
freshness. Squarified layout. No borders, no shadows, no rounded corners.

### 2.9 Calendar grid — cadence

Weeks × weekdays, one cell per session. For posting frequency and for spotting
the weeks a trader went quiet, which is itself information.

---

## 3. Buttons and controls

Controls should look *pressable and printed*, not glassy.

- **Segmented control** for mutually exclusive views (`5d · 20d · 90d`). One
  hairline-bordered row, active segment gets `panel-3` fill and bold weight.
  Preferred over dropdowns wherever there are ≤4 options — it shows the
  alternatives without a click.
- **Filter chips** with an explicit ✕ when active. The current state must be
  readable without opening anything.
- **Sortable column headers** with a caret. Tables are dense; sorting is the
  primary interaction and it is currently missing everywhere.
- **Row expansion** with a real disclosure caret, not a whole-row click with no
  affordance (the current LEDGER does this and it is undiscoverable).
- **A time scrubber** on any screen with history, so "as of" is a control rather
  than always-now.
- Minimum hit target 28px. Focus ring is the token `:focus-visible` outline —
  never removed.

---

## 4. Layout

- **One composed canvas per screen**, not a uniform card grid. Screens have a
  lead graphic that earns its space, then supporting density beneath.
- **Asymmetry is allowed and preferred.** A 2:1 split reads as designed; four
  equal quadrants read as a template.
- Panels are containers of last resort. If two things belong together, a rule and
  whitespace beat two boxes.
- **Serif display (`--disp`) for the one number that matters on a screen**, and
  only that one. Everything else is sans or mono. Six serif hero numbers on one
  screen is the KPI-card tell wearing a different hat.
- Mono (`--mono`) for numerals in tables, always tabular-nums, right-aligned.

---

## 5. How to check your work

Before calling a screen done:

1. Screenshot it. Does any element appear on the banned list in §1?
2. Cover every number with your hand. Does the screen still communicate its
   headline? If not, it is a table wearing a costume.
3. Count the graphics. A screen with zero non-tabular marks is not finished.
4. Count the serif hero numbers. More than one per screen is a defect.
5. Is every percentage accompanied by its `n`?
6. Would this print legibly in greyscale? Run it and see — colour must be
   redundant with position, shape, or label, never the sole carrier of meaning.

---

## 6. Component contract — `ui/src/components/charts.jsx`

Build exactly these. Do not add props, do not rename, do not invent extra
variants. Every one is plain inline SVG, `viewBox` + `width="100%"`,
`role="img"` with an `aria-label` stating the finding in words, colour only from
CSS custom properties.

```jsx
// 2.1 — one row per position on a SHARED time axis (this is the point:
// rows must be comparable, so clustering in time is visible)
<PositionBars
  from="2026-07-20" to="2026-08-22"        // shared domain for every row
  rows={[{
    id: "abc",
    label: "DIXON", sublabel: "@swingdesk",
    start: "2026-08-01", end: "2026-08-24",  // end null => still open
    result: 9.9,                              // null => unstated; drives colour
    warn: "no stop stated",                   // optional ⚠ suffix
    events: [{ at: "2026-08-09", kind: "add"|"sl_up"|"sl_down"|"exit" }],
  }]}
  onRowClick={fn}
/>

// 2.2 — the GAP is the finding. Rule tinted amber when |a-b| > gapWarn.
// `n` (per-row via rows[].n, or one for all via the prop) is REQUIRED whenever
// the values are percentages — §1. Added 2026-08-23: the first version of this
// contract had nowhere to put a denominator, which put §1 and §6 in conflict.
<Dumbbell rows={[{ label, a: {value, label}, b: {value, label}, n }]}
          max={100} gapWarn={10} suffix="%" n={183} />

// 2.3 — one tick per observation + median rule. Replaces a bare median scalar.
<StripPlot values={[3,5,5,11,28]} median={11} suffix="d" />

// 2.4 — line + flat threshold-band rects behind it. Generalises the XP chart.
<BandLine points={[{x:"2026-08-01", y:23.1}]}
          bands={[{at:15,label:"low"},{at:40,label:"building"}]}
          log />                                // log scale opt-in

// 2.5 — one small rect per session. Generalises the MBI ribbon.
<Ribbon cells={[{ key:"2026-08-21", state:"GREEN"|"WHITE"|"RED"|"NONE",
                  warn:false, title:"tooltip text" }]} />

// 2.6 — one bar split proportionally, labelled IN PLACE. Never a pie.
// `n` and `suffix` added 2026-08-23, same §1 reason as Dumbbell.
<StackedStrip segments={[{ label:"breakout", value:61 }]} n={183} suffix="%" />

// 2.7 — grid of miniatures on a SHARED scale. Do not merge into one big chart.
<SmallMultiples items={[{ label:"@swingdesk", values:[1,3,2,5],
                          caption:"+18% · 21 pos" }]} />
```

Controls, in `ui/src/components/ui.jsx`:

```jsx
<Segmented options={["5d","20d","90d"]} value onChange />   // ≤4 options: never a <select>
<SortableTh label="net" active dir="asc"|"desc" onClick />  // tables must sort
<Disclosure open onToggle />                                // real caret, not a bare row click
```

**Empty states are part of the contract.** Every chart renders a labelled empty
frame with a one-line reason when it has no data — never `null`, never a
zero-height SVG, never a collapsed panel. The database is real-data-only and
currently sparse, so the empty state is what will actually be on screen most
often. It must look deliberate.

---

## 7. Implementation notes

- Plain inline SVG. Components live in `ui/src/components/charts.jsx`.
- `viewBox` + `width="100%"` so charts scale; never fixed pixel widths.
- Colour comes from CSS custom properties (`fill="var(--green)"`), so a token
  change propagates. **No raw hex in a component, ever** — same rule as the CSS.
- `role="img"` and an `aria-label` stating the finding in words on every chart.
  A chart that cannot be described in a sentence probably should not exist.
- `@media (prefers-reduced-motion)` already handled globally. Charts do not
  animate on load. There is no argument for it.
