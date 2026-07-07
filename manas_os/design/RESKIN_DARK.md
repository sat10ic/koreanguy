# RESKIN — dark "control-room" theme (token-level, one pass)

WHY: the wireframe rebuild fixed STRUCTURE, but the light theme keeps the tool looking like
its old self ("old parts recycled" — user, 2026-07-07). design_guidelines.json §$meta already
reserves this move: "tokens are theme-namespaced so a future dark 'control-room' can reuse the
semantic layer." This pass swaps ONLY token values + chart palettes. No layout changes — the
two-direction wireframe fidelity already verified per screen must not regress.

## NORTH STAR (user-confirmed 2026-07-07, via screenshot of WIREFRAMES.md itself)
The tool should look like the WIREFRAMES.md ASCII rendered live: dark terminal, monospace
everywhere, thin box-drawn frames with the SECTION TITLE EMBEDDED IN THE TOP BORDER
("┌─ GOVERNOR PANEL ─────┐" style). The wireframe document IS the aesthetic, not just the
layout contract.

## TUI frame language (in addition to the token remap below)
- New shared component `Frame.jsx` (poster/ dir): renders as an HTML <fieldset> with a
  <legend> — the native way to embed a title in the border. Styling: 1px solid hairline
  border, NO border-radius (square corners like ASCII), legend = mono, uppercase,
  tracking-overline, ink3, padded "─ TITLE ─" feel (legend text pulled into the border line).
  Optional `tag` prop for the right-aligned annotation ("[B]" / "SELECTIVE CAP: 4") rendered
  in the legend row's right side (absolute-positioned span, same mono style).
- EVERY panel on every screen becomes a Frame: GOVERNOR PANEL, TOP SETUPS STRIP, REFUSAL
  FUNNEL, each setup CARD, PLAN / EXPECTANCY sub-blocks, HEAT ROW panels, POSITION COACH
  CARDS, WATCH TABLE, EQUITY CURVE, EXPECTANCY MATRIX, etc. — the section names come from
  the ASCII's own frame titles, verbatim.
- Typography: mono-first. ALL chrome, labels, numbers, table cells = JetBrains Mono. The
  sans stack survives ONLY for READ/WHY plain-English prose sentences (per the original
  design rule). Uppercase + tracking on all frame titles and column headers.
- Borders: square corners everywhere (radius 0 on frames/chips/tiles), 1px hairlines. Inner
  separators = the same hairline (like the ASCII's inner box lines).
- Buttons/chips: square, mono, bordered — "[TAKEN]" reads like ASCII brackets (bracket
  glyphs optional; bordered mono uppercase is enough).

## Token remap (tailwind.config.js — same semantic names, new values)
Surfaces:
  bg        #0b0d10   (app background — near-black blue-grey)
  card      #12151a   (cards, panels, header)
  raised    #1a1e25   (inset rows, chips, nested tiles)
  ink       #e8eaed   (primary text)
  ink2      #a8b0bb   (secondary text)
  ink3      #737d8a   (captions, sub-labels)
  ink4      #5c6672   (column headers, eyebrows)
  inkDisabled #454e59
  hairline  #232830   (1px borders)
  hairline2 #1d2229
  hairline3 #171b21
Bands (state colors — same MEANINGS; fg brightened for dark, bg = dark tints):
  bull  fg #4ade80  bg #0c2818  border #1d4a2e  dot #22c55e
  warn  fg #fbbf24  bg #2a1f08  border #4a3a12  dot #f6a609
  bear  fg #f87171  bg #2a1210  border #4a221e  dot #e5484d
  muted fg #a8b0bb  bg #1a1e25  border #232830  dot #737d8a
  blue  fg #60a5fa  bg #0e1a2e  border #1d3a5c  dot #4a90ff
Posture: same mapping; NO_TRADE inverts to ink-on-light (#e8eaed bg, #0b0d10 text) so "sit
out" stays the hardest-reading state on dark.
Typography/spacing/radii: UNCHANGED (JetBrains Mono + sans read stays; tabular-nums stays).

## Chart palettes (the part token-swap alone won't fix)
- Audit every ECharts option builder (JournalPage, SetupsPage, RegimeSummary, WatchlistPage,
  FocusPage) for hardcoded light-theme hexes (#fff backgrounds, #14161a text, light gridlines).
  Replace with a single shared `chartTheme.js` exporting {text, subtext, grid, axis, bandFg...}
  values read from ONE place, so future theme changes are one-file.
- lightweight-charts (ChartDrawer): set layout.background/textColor + grid line colors from the
  same chartTheme.js. Candles: up #22c55e / down #e5484d unchanged (state colors).
- Heatmap grey-cell (n<20) → #1a1e25 with #737d8a label on dark.

## Rules
- NO layout/JSX structure changes — token values, chartTheme, and className color usages only.
  If a component hardcodes a light hex (bg-white etc), swap to the token class, not a new hex.
- WCAG: every fg/bg pair above clears 4.5:1 — do not eyeball-adjust individual values.
- index.html: keep font preloads; add `color-scheme: dark` + body bg to avoid white flash.
- design_guidelines.json: append a `dark` theme block mirroring the table above (source of
  truth stays the JSON; tailwind maps 1:1 from it).
- Done-test: screenshot each of the 6 screens in both beginner + expert — dark surfaces
  everywhere (zero white flashes/panels), state colors legible, charts dark-native. Then the
  standard two-direction wireframe audit must still pass unchanged.
