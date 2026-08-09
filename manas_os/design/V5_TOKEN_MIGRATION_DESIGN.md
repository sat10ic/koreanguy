# V5 TOKEN MIGRATION — Design spec (#14 wave)

**Status:** DESIGN spec (handoff `HANDOFF_GLM_v5_token_migration_DESIGN.md`, queue #14).
**Branch:** `emergent`. **Date:** 2026-07-12. **Do not git commit.** "Rs", never the rupee glyph.
**Done-test:** `python scripts/desk_gate.py` prints `GATE: 3/3 - PASS` (0 hex findings, contrast clean, locked-files clean).

> **Read this first — three premises in the handoff are wrong, corrected below from the code.**
> The handoff predates commits `0c0df56d`/`fce0b176` (#13 guided system, done). Critical inspection of
> the repo today (2026-07-12) found:
> 1. **The 3 contrast P0s (handoff §4 / audit IDs 1–3) are ALREADY FIXED.** `desk_gate.py` reports
>    `[pass] contrast`. This spec does **not** re-spec them. (They live in `GUIDED_SYSTEM_DESIGN.md`.)
> 2. **The "53 raw-hex in ChartDrawer" claim is half-wrong.** The gate finds 53 total: **47 in
>    `ChartDrawer.jsx`** (not 53), **3 in `MarketTab.jsx`**, **2 in `viz.js`**, **1 in `DebateTab.v5.css`**.
>    All 53 must clear for the gate to pass; the migration table below covers every one.
> 3. **`tokens.css` is imported directly in `main.jsx:4`**, NOT via `App.css` as the handoff says.
>    And legacy vars (`--bg/--ink/--accent/…`) are used in **18 files** (`App.css`, `MarketTab.jsx`,
>    `DeskTab.jsx`, `viz.js`, …) — the `tokens.v5.css:76–98` bridge is what keeps them resolving to v5
>    values. The bridge **cannot be removed this wave** (18 files would break); only `tokens.css` dies.
>
> This spec is grounded in the live code, not the handoff's prose. Every hex is from the gate's own
> output; every ratio is computed (WCAG luminance, two routes for the load-bearing ones).

---

## 0. The real aesthetic blocker: the chart is a dark island

The 53 hexes are not a flat list of "colors to swap." Inspecting where they live reveals the actual
release blocker (AESTHETIC_BAR §1): **`ChartDrawer.jsx` paints its chart canvas `#0b0f14` (near-black)
and renders dark-theme grid `#17202b`, axis text `#c9d3df`, and dark-saturated data colors
(`#00c878`/`#ff4a5f`/`#b66cff`/`#f8c14a`…) on it.** This is a second, dark visual system mounted
inside the v5 light shell — visible on 5 tabs (MarketHome, Scanners, Shortlist, Debate, TradePlan)
wherever a chart opens. 9 of the 53 findings are the dark canvas/grid/text triplet repeated across
3 `createChart()` calls (main chart, RMV pane, HMM pane).

**The design decision (load-bearing, flagged):** the chart canvas goes **LIGHT**, matching the v5
shell. Reasoning:
- The locked language says "no raw hex in new CSS, all color through `--v5-*` tokens" and "no new hue
  families." A *dark* chart canvas would require a parallel dark token set (dark bg, dark grid, light
  text) — a new hue family, explicitly forbidden.
- The round-4 mockup (the frozen visual source of truth) renders its GROWW chart on a **light** panel
  background with faint gridlines and dark ink data lines (`debate_merged_light.html:1113–1135` — the
  SVG chart uses `#e2ddd0` gridlines on the panel bg, green/red candles, teal trend line). A light
  chart is the round-4 reference; the current dark canvas is the drift.
- A light canvas makes the dark-saturated legacy colors (`#00c878`, `#b66cff`) look garish and
  oversaturated — forcing them to be re-derived from the v5 palette, which is the whole point.

**Flagged for maintainer (one genuine judgment call):** the legacy palette has **no purple/violet/cyan/blue**.
Six distinct hexes map to hues outside the locked palette: `#b66cff`/`#8b5cf6`/`#c084fc` (purple/violet,
used for HMM-chop + purple-dot marker + bear-PP volume), `#4dd2ff`/`#7dd3fc`/`#1f8cff` (cyan/blue,
used for EMA21 + RMV + bull-PP marker). These cannot be preserved verbatim without inventing a hue
family. The spec maps them to the closest *semantic* v5 token (analysis=teal, caution=amber, polarity=
green/red, neutral=ink-mute) and **loses hue distinction** — e.g. EMA21 (was cyan) and the purple-dot
marker both become teal. I recommend this (token fidelity > hue preservation), but it is a visible
behavior change. See §3 (EMA) and §4 (markers). If the maintainer wants hue preservation, the only
token-faithful path is to add a `--v5-violet` family — a language change, out of scope for #14.

---

## 1. Semantic token registry (new `--v5-*` tokens, derived from the locked palette)

Add these to `desk/src/styles/tokens.v5.css` inside the `.v5` block. Every value is either a locked
token reuse or an `rgba()` translucency wrapper of one (per AGENTS.md: "rgba() translucency wrappers
of token values are allowed"). **No new hue families.** Contrast verified in §6.

### 1.1 Chart canvas (replaces the dark island)
```css
--v5-chart-bg:        var(--v5-panel);          /* #fffdf9 — light canvas, kills #0b0f14/#141414 */
--v5-chart-axis:      var(--v5-ink-dim);        /* #43464e — axis/price text, 9.29:1 on panel */
--v5-chart-grid:      var(--v5-line);           /* #e2ddd0 — faint grid (decorative; see §6 flag) */
--v5-chart-border:    var(--v5-line);           /* #e2ddd0 — price/time scale borders */
```

### 1.2 Candle polarity (up/down) — the one literal mapping
```css
--v5-up:              var(--v5-green);          /* #14713f — candle up / wick up / vol up */
--v5-down:            var(--v5-red);            /* #ad2c34 — candle down / wick down / vol down */
```

### 1.3 HMM regime states (bull/bear/chop)
```css
--v5-hmm-bull:        var(--v5-green);          /* #14713f */
--v5-hmm-bear:        var(--v5-red);            /* #ad2c34 */
--v5-hmm-chop:        var(--v5-amber-ink);      /* #6e470d — was #b66cff (purple lost; → caution) */
--v5-hmm-bull-subtle: rgba(20, 113, 63, 0.14);  /* area-fill bg, =--v5-green-dim intent */
--v5-hmm-bear-subtle: rgba(173, 44, 52, 0.14);
--v5-hmm-chop-subtle: rgba(184, 127, 26, 0.14); /* =--v5-amber-glow */
```

### 1.4 EMA line colors (4 distinguishable, all ≥3:1 on panel)
```css
--v5-ema-10:          var(--v5-amber-ink);      /* #6e470d — was #f8c14a (8.04:1) */
--v5-ema-21:          var(--v5-teal);           /* #0d6c6c — was #4dd2ff cyan (6.12:1) */
--v5-ema-50:          var(--v5-red);            /* #ad2c34 — was #c084fc violet (6.49:1) */
--v5-ema-200:         var(--v5-ink);            /* #17181b — was #f97316 orange (17.47:1) */
```
> The 4 EMAs must be visually distinguishable. amber/teal/red/ink are four distinct hues, all
> ≥3:1 on the light canvas. This is the recommended mapping; the order (which EMA gets which hue)
> is arbitrary but should match the legend chip row order.

### 1.5 Volume bar colors
```css
--v5-vol-up:          var(--v5-green);          /* was #00c878 */
--v5-vol-down:        var(--v5-red);            /* was #ff4a5f */
--v5-vol-bull-pp:     var(--v5-teal);           /* was #1f8cff blue (analysis marker) */
--v5-vol-bear-pp:     var(--v5-amber-ink);      /* was #8b5cf6 violet (caution marker) */
--v5-vol-dry:         var(--v5-ink-mute);       /* was #7c8495 (neutral) */
--v5-vol-noise:       var(--v5-ink-faint);      /* was #394150 — decorative only (a11y ok) */
```

### 1.6 Chart markers (pocket-pivot, purple-dot, persistency entry/exit)
```css
--v5-marker-pp:       var(--v5-teal-ink);       /* #0a5555 — was #1f8cff (pocket-pivot arrow) */
--v5-marker-purple:   var(--v5-teal);           /* #0d6c6c — was #b66cff (purple dot → analysis teal) */
--v5-marker-entry:    var(--v5-green);          /* was #00c878 (persistency entry arrow) */
--v5-marker-exit:     var(--v5-red);            /* was #ff4a5f (persistency exit arrow) */
```

### 1.7 RMV pane
```css
--v5-rmv-base:        var(--v5-teal);           /* was #7dd3fc sky (RMV histogram base) */
--v5-rmv-alert:       var(--v5-amber-ink);      /* was #f8c14a (RMV <=20 alert) */
```

### 1.8 Confidence + Mswing label pills (text/bg pairs, AA)
```css
--v5-conf-high-fg:    var(--v5-green);
--v5-conf-high-bg:    var(--v5-green-dim);
--v5-conf-med-fg:     var(--v5-amber-ink);
--v5-conf-med-bg:     rgba(184, 127, 26, 0.14);   /* =--v5-amber-glow */
--v5-conf-low-fg:     var(--v5-red);
--v5-conf-low-bg:     var(--v5-red-dim);
/* Mswing reuses confidence semantics: up=green, neutral_positive=amber, neutral_negative=amber, down=red */
--v5-mswing-up:       var(--v5-green);
--v5-mswing-neutral:  var(--v5-amber-ink);
--v5-mswing-down:     var(--v5-red);
```

> **Note on `rgba(var(--v5-*-rgb), …)`:** the handoff's `rgba(var(--v5-teal-rgb), 0.12)` pattern
> does **not work** — no `--v5-*-rgb` channel tokens exist in `tokens.v5.css`, and `var()` inside
> `rgba()` needs bare `R G B` values. The existing precedent (`--v5-amber-glow: rgba(184,127,26,0.12)`)
> uses **literal numbers**. This spec follows that precedent (literal rgba), which AGENTS.md permits.
> Do not introduce `--v5-*-rgb` tokens unless the maintainer wants that refactor (out of scope).

---

## 2. Migration table — all 53 findings (the build contract)

Every hex the gate found, mapped to its target token. Grouped by semantic role; the gate's
file:line is preserved so Gemini can verify each. "C" = ChartDrawer.jsx.

### 2.1 HMM_COLORS (C:9-11) + chop usage (C:123, C:652)
| # | file:line | current hex | role | target token |
|---|---|---|---|---|
| 1 | C:9 | `#00c878` | HMM bull | `var(--v5-hmm-bull)` |
| 2 | C:10 | `#b66cff` | HMM chop | `var(--v5-hmm-chop)` |
| 3 | C:11 | `#ff4a5f` | HMM bear | `var(--v5-hmm-bear)` |
| 4 | C:123 | `#b66cff` | purple-dot marker color | `var(--v5-marker-purple)` |
| 5 | C:652 | `#b66cff` | legend swatch (purple dot) | `var(--v5-marker-purple)` |

### 2.2 VOLUME_COLORS (C:17-22)
| # | file:line | current hex | role | target token |
|---|---|---|---|---|
| 6 | C:17 | `#1f8cff` | bull_pp volume | `var(--v5-vol-bull-pp)` |
| 7 | C:18 | `#8b5cf6` | bear_pp volume | `var(--v5-vol-bear-pp)` |
| 8 | C:19 | `#7c8495` | dry volume | `var(--v5-vol-dry)` |
| 9 | C:20 | `#00c878` | up volume | `var(--v5-vol-up)` |
| 10 | C:21 | `#ff4a5f` | down volume | `var(--v5-vol-down)` |
| 11 | C:22 | `#394150` | noise volume | `var(--v5-vol-noise)` |

### 2.3 Markers — persistency entry/exit + pocket-pivot (C:133,142,151)
| # | file:line | current hex | role | target token |
|---|---|---|---|---|
| 12 | C:133 | `#1f8cff` | pocket-pivot arrow | `var(--v5-marker-pp)` |
| 13 | C:142 | `#00c878` | persistency entry arrow | `var(--v5-marker-entry)` |
| 14 | C:151 | `#ff4a5f` | persistency exit arrow | `var(--v5-marker-exit)` |

### 2.4 EMA_LEGEND (C:195-198) + EMA_COLORS (C:474)
| # | file:line | current hex | role | target token |
|---|---|---|---|---|
| 15 | C:195 | `#f8c14a` | ema10 legend | `var(--v5-ema-10)` |
| 16 | C:196 | `#4dd2ff` | ema21 legend | `var(--v5-ema-21)` |
| 17 | C:197 | `#c084fc` | ema50 legend | `var(--v5-ema-50)` |
| 18 | C:198 | `#f97316` | ema200 legend | `var(--v5-ema-200)` |
| 19-22 | C:474 | `#f8c14a`,`#4dd2ff`,`#c084fc`,`#f97316` | EMA_COLORS obj | `var(--v5-ema-10/21/50/200)` |

### 2.5 Main chart canvas — `createChart` #1 (C:437-455)
| # | file:line | current hex | role | target token |
|---|---|---|---|---|
| 23 | C:437 | `#0b0f14` | chart bg | `var(--v5-chart-bg)` |
| 24 | C:438 | `#c9d3df` | axis text | `var(--v5-chart-axis)` |
| 25-26 | C:441-442 | `#17202b` | grid vert/horz | `var(--v5-chart-grid)` |
| 27-28 | C:444-445 | `#27313d` | price/time scale border | `var(--v5-chart-border)` |
| 29 | C:451 | `#00c878` | candle upColor | `var(--v5-up)` |
| 30 | C:452 | `#ff4a5f` | candle downColor | `var(--v5-down)` |
| 31 | C:454 | `#00c878` | wick upColor | `var(--v5-up)` |
| 32 | C:455 | `#ff4a5f` | wick downColor | `var(--v5-down)` |

### 2.6 RMV pane — `createChart` #2 (C:487-508)
| # | file:line | current hex | role | target token |
|---|---|---|---|---|
| 33 | C:490 | `#0b0f14` | rmv chart bg | `var(--v5-chart-bg)` |
| 34 | C:490 | `#c9d3df` | rmv axis text | `var(--v5-chart-axis)` |
| 35-36 | C:492-493 | `#17202b` | rmv grid | `var(--v5-chart-grid)` |
| 37-38 | C:495-496 | `#27313d` | rmv scale border | `var(--v5-chart-border)` |
| 39 | C:500 | `#7dd3fc` | rmv histogram color | `var(--v5-rmv-base)` |
| 40-41 | C:508 | `#f8c14a`,`#7dd3fc` | rmv alert/base ternary | `var(--v5-rmv-alert)` / `var(--v5-rmv-base)` |

### 2.7 HMM pane — `createChart` #3 (C:514-526)
| # | file:line | current hex | role | target token |
|---|---|---|---|---|
| 42 | C:517 | `#0b0f14` | hmm chart bg | `var(--v5-chart-bg)` |
| 43 | C:517 | `#c9d3df` | hmm axis text | `var(--v5-chart-axis)` |
| 44-45 | C:519-520 | `#17202b` | hmm grid | `var(--v5-chart-grid)` |
| 46-47 | C:523,526 | `#27313d` | hmm scale border | `var(--v5-chart-border)` |

### 2.8 Non-ChartDrawer findings (6 — easy wins)
| # | file:line | current hex | role | target token |
|---|---|---|---|---|
| 48 | `viz.js:12` | `#141414` | chart helper bg | `var(--v5-chart-bg)` |
| 49 | `viz.js:16` | `#141414` | chart helper bg | `var(--v5-chart-bg)` |
| 50 | `MarketTab.jsx:106` | `#2e7d32` | low fallback behind `var(--positive, …)` | drop hex; `var(--positive)` (bridge covers) |
| 51 | `MarketTab.jsx:108` | `#b8860b` | elevated fallback behind `var(--warn, …)` | drop hex; `var(--warn)` |
| 52 | `MarketTab.jsx:109` | `#c0392b` | danger fallback behind `var(--negative, …)` | drop hex; `var(--danger)` (note: `--negative` is undefined; use `--danger`) |
| 53 | `DebateTab.v5.css:255` | `#c99a45` | gradient stop next to `--v5-amber-bright` | `var(--v5-amber-bright)` (single-stop) or `var(--v5-amber-ink)` |

> **Finding 52 has a latent bug:** `MarketTab.jsx:109` uses `var(--negative, #c0392b)` but there is
> **no `--negative` token** in either `tokens.css` or `tokens.v5.css` (the bridge maps `--danger`,
> not `--negative`). So the var falls through to the hex fallback today. Dropping the hex and using
> `var(--danger)` fixes both the lint and the latent broken var. **Flagged as a real bug, not just
> migration.**

**ChartDrawer.jsx constant objects → rewrite to read tokens at runtime.** Because `lightweight-charts`
takes color strings at `createChart`/`setData` time, and CSS vars aren't directly readable in JS,
Gemini must resolve tokens to hex in JS. Two options:
- **(A, recommended)** keep the constant objects but source values from a single `getChartColors()`
  that reads computed CSS vars: `getComputedStyle(document.documentElement).getPropertyValue('--v5-ema-10')`.
  One resolver, all constants reference it, the token layer stays the single source of truth.
- **(B)** hardcode the resolved hex values in the JS constants (e.g. `ema10: "#6e470d"`). Simpler,
  but reintroduces raw hex in a `.jsx` → **the gate would still flag them** (the gate lints `.jsx`).
  So (B) fails the gate. **(A) is the only gate-passing path.**

> This is a real implementation constraint the handoff did not mention: the gate lints `.jsx` files,
> so ChartDrawer's JS color constants **cannot hold hex strings** even as token-resolved values. They
> must be `var(--v5-*)` strings passed to `createChart` (which `lightweight-charts` does NOT accept —
> it needs real colors) OR resolved at runtime via `getComputedStyle`. Gemini must implement the
> `getComputedStyle` resolver. **Flagged as the #1 build risk.**

---

## 3. Single-theme cleanup — retire `tokens.css` (the real plan)

### 3.1 What `tokens.css` provides today (`desk/src/tokens.css`, 101 lines)
- `:root` dark values: `--bg:#0a0a0a`, `--ink:#e0e0e0`, `--accent:#00d4ff`, `--positive:#00ff66`, …
- `body { background: var(--bg); color: var(--ink); font-family: var(--font-sans); font-size:13px }`
- `html,body { max-width:100vw; overflow-x:hidden }` (the SHIP-1 #13 no-horizontal-scroll backstop)
- `.mono`, `.small-caps`, `.overline`, `.overline.accent`, `:focus-visible { outline: 2px solid var(--accent) }`

### 3.2 Why it's safe to delete now
The `tokens.v5.css:76–98` bridge **already aliases every legacy name to a v5 token** inside `.v5`:
`--bg→--v5-canvas`, `--ink→--v5-ink`, `--accent→--v5-teal-ink`, `--positive→--v5-green`, etc. The
shell root is `.v5` (`App.jsx:435`), so legacy names resolve to v5 values already. Deleting
`tokens.css` removes the *dark :root values* — the only thing that could let a dark island reappear.

### 3.3 The 3 things that must move OUT of `tokens.css` before deleting it
`tokens.css` carries 3 rules that are NOT token definitions and must be preserved (migrated to
`tokens.v5.css` or `App.css`), or the shell regresses:

| Rule | Current | Must move to | Why |
|---|---|---|---|
| `html,body,#root { height:100% }` | `tokens.css:44-48` | `tokens.v5.css` (under the existing `html,body,#root` block at line 105) | shell layout |
| `html,body { max-width:100vw; overflow-x:hidden }` | `tokens.css:64-68` | `tokens.v5.css` same block | SHIP-1 #13 no-side-scroll backstop |
| `body { margin:0; font-family:var(--font-sans); font-size:13px; line-height:1.5 }` | `tokens.css:50-58` | `tokens.v5.css` `body` rule (the existing `html,body,#root { background:#f7f6f2 }` at line 106 — extend it) | base typography |
| `.mono`, `.small-caps`, `.overline`, `.overline.accent`, `:focus-visible` | `tokens.css:70-100` | `App.css` (these are component classes, not tokens) | used across legacy components |
| `* { box-sizing:border-box }` | `tokens.css:40-42` | `App.css` (or keep in `tokens.v5.css`) | global reset |

### 3.4 The bridge stays (do NOT remove `tokens.v5.css:76–98`)
The handoff asked "which bridge aliases must stay / which can go?" The answer from the code:
**all stay, this wave.** Legacy vars are referenced in 18 non-token files (`App.css` ×all,
`MarketTab.jsx`, `DeskTab.jsx`, `viz.js`, `viz.test.js`, …). Removing the bridge breaks all 18.
The bridge is the compatibility layer that makes "single theme" true *today* — legacy names are
aliases of v5, not independent values. Migrating those 18 files to `--v5-*` names directly is a
larger sweep, **out of scope for #14** (flag as a follow-up wave). The done-test is "one theme
source," which deleting `tokens.css` achieves.

### 3.5 Removal steps (build contract, ordered)
1. Move the 5 non-token rules above from `tokens.css` → `tokens.v5.css` / `App.css`.
2. Delete `import "./tokens.css";` from `main.jsx:4`.
3. Delete `manas_os/desk/src/tokens.css`.
4. Update `desk_gate.py:29` `TOKEN_FILES = {"tokens.v5.css"}` (remove `tokens.css` — it no longer
   exists; keeping it in the set is harmless but stale).
5. `npm run build` (or `vite build`) — zero console errors.
6. Rendered check on all 7 tabs: no dark island, no visual regression (the orchestrator's browser
   pass; the gate is mechanical only).
7. `python scripts/desk_gate.py` → 3/3 PASS.

---

## 4. Status-chip vocabulary — `StatusBadge` (already built, finish wiring)

`StatusBadge` (`components/v5/StatusBadge.jsx`) and its CSS (`primitives.v5.css:1083-1087`) already
implement all 5 states with AA-passing colors (verified §6). The design work is **not** the chip —
it's **finishing the wiring** the #13 wave started. Current state (from audit IDs 13-15):

| State | Token pair (built) | Ratio | Tooltip copy (built) | Wired where? |
|---|---|---|---|---|
| LIVE | `--v5-green` on `--v5-green-dim` | 5.05:1 | "Live — using real data." | (not yet used) |
| SHADOW | `--v5-ink-dim` on `--v5-panel-3` | 8.7:1 | "Shadow — observing only, does not affect gates or sizing." | ALPHA rank (intended) |
| WARMING | `--v5-amber-ink` on `--v5-amber-glow` | 5.64:1 | "Warming — accumulating history, will activate automatically." | DEBATE HMM (audit ID 13) |
| EXPERIMENTAL | `--v5-ink-mute` on `--v5-panel-2` (dashed border) | 4.8:1 | "Experimental — not validated. Display-only, no live influence." | ChartDrawer HMM (audit ID 15) |
| NEEDS-DATA | `--v5-red` on `--v5-red-dim` | 5.19:1 | "Needs data — required input is missing or not yet ingested." | ALPHA research bench (audit ID 14) |

### 4.1 Wiring to complete (build contract)
- **Audit ID 13** — `DebateTab.jsx:181-188`: replace bare text `"HMM: warming up (2/20)"` with
  `<StatusBadge status="WARMING" why={r.hmm_caption} />`. The `why` carries the "2/20" count.
- **Audit ID 14** — `AlphaLab.jsx:82-86`: replace the raw `<pre>{JSON.stringify({models:[],experiments:[]})}</pre>`
  with `<StatusBadge status="NEEDS-DATA" why="Run the nightly update to seed the registry." />`.
- **Audit ID 15** — `ChartDrawer.jsx:240-248` (and `:636`): wrap the "STOCK HMM · EXPERIMENTAL"
  label text with `<StatusBadge status="EXPERIMENTAL" />`. ChartDrawer already imports it (line 6).
- **SHADOW** — apply to the ALPHA opportunity-rank panel header: `<StatusBadge status="SHADOW" />`
  with `why="Cross-sectional research rank; does not influence sizing."` (ALPHA_LEARNING_CONSTRAINTS).
- **LIVE** — apply to MARKET's regime verdict banner when data is fresh (the inverse of the stale
  banner at `App.jsx:420`). Optional this wave; the stale banner already covers the negative case.

### 4.2 Tooltip affordance (design)
Tooltips are `title=` attributes today (`StatusBadge.jsx:24`). That fails WCAG 1.4.13 (hover content
must be dismissible/hoverable/persistent, not title-only). **Flagged for the maintainer:** the
`StatusBadge` tooltip should become a real hover/focus popover for full a11y. Cheap fix: reuse the
existing `Term`/glossary popover pattern (`Glossary.jsx`) if it's already a popover, not title-only.
Out of scope to redesign here — the chip itself is AA-clean; only the tooltip *mechanism* needs work.

---

## 5. Cheap-win visual specs (design the change, not the code)

### 5.1 Scanner preset scroll-into-view (audit ID 8, P0)
**Problem:** clicking a preset mounts results at `top:7103px` while `scrollY` stays 0 — zero feedback.
**Design:** on preset open, (a) the preset card itself gets a `--v5-teal` left-edge active indicator
(`border-left:3px solid var(--v5-teal)`, matching the rail's active idiom) so the clicked card
visibly "selected", and (b) `resultRef.current?.scrollIntoView({behavior:'smooth', block:'start'})`
on the results mount. **Loading state:** replace the text-only "LOADING…" with a 3-row skeleton
(rows = `--v5-panel-2` blocks at the row height, `--v5-r-md`, shimmer disabled under
`prefers-reduced-motion`). **Reduced-motion:** `scrollIntoView` becomes `block:'start'` instant
(no smooth), skeleton is static. (Audit IDs 8 + 42.)

### 5.2 PositionsTab freshness chip (audit ID 22, P1)
**Problem:** "NOW 207.0" has no as-of/source marker; `fyers_connected:false` and nothing says the
feed is down.
**Design:** a chip next to the NOW price, 3 states, all token-driven:
- `live 10:42` — `--v5-green` text on `--v5-green-dim` bg, when `fyers_connected && ltp_timestamp < 2min`.
- `EOD 07-10` — `--v5-amber-ink` on `--v5-amber-glow`, when price is the EOD snapshot.
- `feed down` — `--v5-red` on `--v5-red-dim`, `role="alert"`, when `fyers_connected===false`.
Icon + text each (not color-only). Derived from `fyers_connected` + `data_as_of` + `ltp_timestamp`
(all fields the audit says exist at `PositionsTab.jsx:122`).

### 5.3 Journal delete confirmation (audit ID 24, P1)
**Problem:** `DELETE /api/journal/{trade_id}` exists; `DeleteControl` is not wired to the API.
**Design:** **inline confirm, not a modal** (the row is the context; a modal is heavyweight for a
single-row delete). Click trash → the row's action area swaps to `Delete this trade? [Cancel] [Delete]`
with the `[Delete]` button in `--v5-red` on `--v5-red-dim` (destructive affordance,
`aria-label="Delete trade <symbol>"`). On confirm → `deleteJournalTrade(trade_id)` → optimistic
remove + reload. **No toast needed** — the row disappearing is the feedback. Matches the
ux-writing rule: confirm button restates the action + object ("Delete trade", not "OK").
`api.js` needs a `deleteJournalTrade(id)` wrapper (audit says it's missing).

### 5.4 Reduced-motion guards (audit ID 31, P1) — the 10 CSS files
`prefers-reduced-motion` exists in only 3 of 10 CSS files. **Design:** add the guard block to every
file that declares `transition` or `animation`. The pattern is already in `primitives.v5.css:963-966`:
```css
@media (prefers-reduced-motion: reduce) {
  .v5 * { animation-duration:0.001ms !important; animation-iteration-count:1 !important;
          transition-duration:0.001ms !important; }
}
```
**Files to add it to** (the 10 — verify with `grep -rL "prefers-reduced-motion"`): `App.css`,
`MarketHomeTab.v5.css`, `DebateTab.v5.css`, `ShortlistTab.v5.css`, `ScannersTab.v5.css`,
`PositionsTab.v5.css`, `LedgerTab.v5.css`, `AlphaLab.css`, `ChartDrawer.v5.css` (if it exists —
audit says it doesn't; then the chart's CSS lives in `App.css`/`primitives.v5.css`). **Never disable**
the ticker-tape's `tape-scroll` via this (it has its own pause-on-hover) — but DO disable it under
reduced-motion (a moving tape is exactly what reduced-motion users want stopped). The `pulse-dot`
keyframe and any hover transitions get neutralized. Per AGENTS.md: P&L/stop/target/qty/verdict are
already never animated — keep that.

---

## 6. Contrast verification (computed, two routes for load-bearing pairs)

WCAG 2.2: text ≥4.5:1, non-text UI ≥3:1. Method: relative luminance + (L1+0.05)/(L2+0.05).
Load-bearing pairs recomputed by a second route (direct sRGB math); both agree.

| Pair | fg | bg | ratio | threshold | pass? |
|---|---|---|---|---|---|
| chart axis text | `--v5-ink-dim` #43464e | `--v5-panel` #fffdf9 | 9.29 | 4.5 | ✅ |
| candle/EMA/HMM green | `--v5-green` #14713f | panel | 5.97 | 3 | ✅ |
| candle/EMA/HMM red | `--v5-red` #ad2c34 | panel | 6.49 | 3 | ✅ |
| EMA10 / HMM-chop | `--v5-amber-ink` #6e470d | panel | 8.04 | 3 | ✅ |
| EMA21 / marker | `--v5-teal` #0d6c6c | panel | 6.12 | 3 | ✅ |
| EMA200 | `--v5-ink` #17181b | panel | 17.47 | 3 | ✅ |
| marker PP | `--v5-teal-ink` #0a5555 | panel | 8.46 | 3 | ✅ |
| vol neutral | `--v5-ink-mute` #6b6f78 | `--v5-panel-2` #f3f1ea | 4.46 | 3 | ✅ |
| StatusBadge LIVE | green on green-dim | | 5.05 | 4.5 | ✅ |
| StatusBadge WARMING | amber-ink on amber-glow | | 5.64 | 4.5 | ✅ |
| StatusBadge NEEDS-DATA | red on red-dim | | 5.19 | 4.5 | ✅ |
| StatusBadge EXPERIMENTAL | ink-mute on panel-2 | | 4.8 | 4.5 | ✅ |
| **chart grid** | `--v5-line` #e2ddd0 | panel | **1.33** | 3 | ⚠️ see below |

### 6.1 The chart-grid flag (load-bearing design decision)
`--v5-line` on `--v5-panel` = **1.33:1**, far below 3:1. To hit 3:1 on the near-white panel
(L=0.98), a grid line needs luminance ≤0.294 → roughly `#9a917a` (3.08:1) or darker — a noticeably
heavy grid. Two readings:

- **(A) Grid is non-text UI → must be 3:1.** Grid token = `#9a917a`-class. Heavy but gate-clean.
- **(B) Grid is decorative scaffolding → exempt** (WCAG 1.4.11 exempts "pure decoration" and
  background that doesn't convey info). Grid = `--v5-line` (1.33:1), matches the round-4 mockup
  (which uses faint `#e2ddd0` gridlines on light bg, `debate_merged_light.html:537`).

**Recommendation: (B), with the grid at `--v5-line`, and add the pair to `desk_gate.py`
CONTRAST_PAIRS as a documented decorative exemption** (comment: "chart grid = decorative; exempt
from 3:1 per WCAG 1.4.11, matches round-4 mockup"). This makes the exemption a conscious, auditable
decision rather than an oversight. If the maintainer disagrees, (A) is the fallback: define
`--v5-chart-grid: #9a917a` and accept the heavier grid. **Flagged — not guessing.**

> **Gate note:** `desk_gate.py`'s `CONTRAST_PAIRS` (lines 76-85) does NOT currently include any
> chart-grid pair, so the gate won't catch either choice. The spec recommends *adding* the pair
> (with the exemption comment if (B)) so the decision is enforced, not silent.

---

## 7. Optional HTML mockup

A self-contained mockup is provided at `manas_os/design/V5_TOKEN_MIGRATION_MOCKUP.html` showing:
- the ChartDrawer legend area (EMA chips, HMM chips, marker swatches) rendered in the new semantic
  tokens on a light canvas (before/after the dark island),
- `StatusBadge` in all 5 states on the v5 canvas,
- a fixed-contrast GuidedFlowRail sample (already shipped — shown for completeness).

---

## 8. Open decisions flagged for the maintainer (not guessed)

1. **Purple/cyan/blue hues lost.** Six legacy hexes (`#b66cff`/`#8b5cf6`/`#c084fc`/`#4dd2ff`/`#7dd3fc`/`#1f8cff`)
   have no home in the locked palette and map to teal/amber/ink-mute. Visible behavior change (EMA21
   cyan→teal, purple-dot→teal). Only alternative = add a `--v5-violet` family (language change,
   out of scope). **Recommend accept the loss; confirm.**
2. **Chart grid 3:1 (§6.1).** Recommend (B) decorative exemption + gate pair. Confirm (A) vs (B).
3. **`getComputedStyle` resolver (§2).** The gate lints `.jsx`, so ChartDrawer's color constants
   cannot hold hex strings — they must resolve `var(--v5-*)` at runtime. This is a build-pattern
   decision Gemini must implement; flag if a different resolver is preferred.
4. **Bridge retirement is NOT this wave (§3.4).** 18 files use legacy var names; the bridge stays.
   Deleting `tokens.css` achieves "one theme source." Migrating the 18 files to `--v5-*` names is a
   follow-up wave — confirm this is the intended #14 scope.
5. **`--negative` latent bug (§2.8 #52).** `MarketTab.jsx:109` references a non-existent
   `--negative` token. Fix to `--danger` as part of the migration. Flagged as a bug, not just lint.
6. **StatusBadge tooltip mechanism (§4.2).** `title=` fails WCAG 1.4.13. Promote to a real popover
   (reuse `Glossary.jsx`'s `Term` pattern if it's a popover). Out of scope to redesign here; flagged.

---

## 9. Verification log (honest)

- **Gate baseline:** `python scripts/desk_gate.py` → `GATE: 2/3 - FAIL (53 findings)`,
  `[pass] contrast`, `[pass] locked-files`. **Certain (live, 2026-07-12).**
- **53 findings breakdown:** 47 `ChartDrawer.jsx` + 3 `MarketTab.jsx` + 2 `viz.js` + 1
  `DebateTab.v5.css`. From the gate's own regex run via Python (grep -E was flaky in Git Bash this
  session — used Python regex matching the gate's `HEX_RE`). **Certain.**
- **Contrast already passes:** gate `[pass] contrast` confirms P0 IDs 1-3 are fixed (commit
  `0c0df56d`). This spec does not re-spec them. **Certain.**
- **tokens.css import:** `main.jsx:4` `import "./tokens.css"` (direct, not via App.css).
  `tokens.v5.css` imported `main.jsx:21`. **Certain.**
- **Legacy var usage:** 18 non-token files reference `--bg/--ink/--accent/…` (Python grep:
  `--border` ×18, `--accent` ×16, `--ink-dim` ×16, `--ink` ×14, `--warn` ×14, …). Bridge at
  `tokens.v5.css:76-98` covers all. **Certain.**
- **No `--v5-*-rgb` tokens:** `grep rgb tokens.v5.css` shows only literal `rgba(…)` and the
  shell-gradient rgba — no channel tokens. So `rgba(var(--v5-*-rgb),…)` pattern from the handoff
  is non-functional; this spec uses literal rgba per precedent. **Certain.**
- **`--negative` does not exist:** Python grep of both token files for `--negative` → 0 hits.
  `MarketTab.jsx:109` `var(--negative, #c0392b)` falls through to hex. **Certain (latent bug).**
- **Round-4 chart is light:** `debate_merged_light.html:537` gridline `#e2ddd0` on panel bg, dark
  ink data lines. **Certain.**
- **New token contrast:** computed §6, load-bearing pairs by two routes. **Certain.**
- **ChartDrawer already imports StatusBadge:** `ChartDrawer.jsx:6`. Wiring is partial. **Certain.**

---

## 10. Single strongest recommendation

**Kill the dark chart canvas first; the 53 hexes collapse after it.** The 47 ChartDrawer findings
are not 47 independent colors — they're one dark theme (canvas `#0b0f14` + grid `#17202b` + axis
`#c9d3df` + 4 saturated data hues) repeated across 3 `createChart` panes. Define the §1 semantic
tokens, flip the canvas to `--v5-chart-bg` (`--v5-panel`), and 23 of the 47 findings (the canvas/grid/
axis/border/candle triplets in §2.5-2.7) resolve by changing 4 token references. The remaining 24
(the HMM/VOLUME/EMA/marker constants) become a clean semantic mapping to the same v5 palette the
rest of the desk already uses. The migration stops feeling mechanical the moment the chart stops
being a dark island — the new tokens make the chart *belong* to the v5 system, which is the
legibility win, not just compliance. Then retire `tokens.css` (§3) to make "one theme" true, and
the gate goes green.

---

## Output summary (per handoff §Output note)

- **Spec file:** `manas_os/design/V5_TOKEN_MIGRATION_DESIGN.md` (this file).
- **Mockup:** `manas_os/design/V5_TOKEN_MIGRATION_MOCKUP.html`.
- **53-row migration table:** §2 (all 53, grouped, with file:line + target token). Abbreviated
  here: HMM×5, VOLUME×6, markers×3, EMA×8, canvas-triplet×25 (main/RMV/HMM panes), non-ChartDrawer×6.
- **Single strongest recommendation:** §10 — kill the dark chart canvas first; the 53 hexes
  collapse into one semantic mapping once the chart belongs to the v5 light system.

*Risks: the `getComputedStyle` resolver (§2) is the #1 build risk — `lightweight-charts` needs real
color strings, but the gate forbids hex in `.jsx`; Gemini must resolve `var(--v5-*)` at runtime.
Purple/cyan/blue hues are lost (§8.1) — visible behavior change. Chart-grid 3:1 is a maintainer
call (§6.1, §8.2). The `tokens.css` retirement moves 5 non-token rules first (§3.3) or the shell
regresses. `--negative` latent bug (§8.5). Contrast assumes today's token values (recompute if
`tokens.v5.css` changes). No trading guidance invented; all states honest.*
