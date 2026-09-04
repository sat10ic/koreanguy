# HANDOFF (DESIGN) — v5 Token Migration + Single-Theme Cleanup (GLM)

Repo `C:\Users\satta\Downloads\koreanguy`, branch `emergent`. You (GLM) have repo access.
This is a **DESIGN** handoff: produce a concrete, buildable design SPEC (+ optional HTML mockup),
NOT production React. Gemini implements from `HANDOFF_GEMINI_v5_token_migration.md` afterward.
Do NOT git commit. Never print the rupee glyph to console — use "Rs".

---

## The problem you are solving (the release blocker)

`scripts/desk_gate.py` baseline: **53 findings** (all ChartDrawer raw hex).
This wave must close them to **0** — done-test = `python scripts/desk_gate.py` prints **3/3 PASS**.

The desk is 7 tabs on v5 LIGHT (locked). `ChartDrawer.jsx` mounts on 5 tabs and is a "legacy black island in the light shell" (AESTHETIC_BAR 2026-07-11 §1). It contains 53 raw-hex color constants. Legacy `tokens.css` is still imported as a 2nd live theme source. Three contrast P0s in the GuidedFlowRail also fail WCAG AA.

---

## Load-bearing facts (verified, curl-able)

1. **ChartDrawer raw-hex inventory** (exact lines in `desk/src/ChartDrawer.jsx:8-23`):
   - `HMM_COLORS` — 4 states (bull/bear/neutral/warming) × 2 (bg/text) = 8 values
   - `VOLUME_COLORS` — 3 states × 2 = 6 values
   - `CONFIDENCE_LABEL` — 3 states × 2 = 6 values
   - `MSWING_LABEL` — 4 states × 2 = 8 values
   - `EMA_LEGEND` — 4 EMAs × 2 = 8 values
   - Inline JSX style objects: ~25 more raw hex

2. **Co-mounted files with gate findings**:
   - `MarketHomeTab.jsx` + `MarketHomeTab.v5.css` — 3 raw hex
   - `ScannersTab.jsx` + `ScannersTab.v5.css` — 3 raw hex
   - `DebateTab.jsx` + `DebateTab.v5.css` — 1 raw hex
   - `viz.js` — 3 raw hex
   - `ShortlistTab.jsx` / `TradePlanTab.jsx` — use ChartDrawer (inherit its tokens)

3. **Legacy `tokens.css` still live**: `App.jsx:17` imports `App.css` which uses `tokens.css` vars.
   Bridge aliases at `tokens.v5.css:76-98` map some legacy names. Two theme sources conflict.

4. **3 contrast P0s** in `primitives.v5.css` (GuidedFlowRail):
   - Active step border: `--v5-amber-bright` on `--v5-amber-glow` → **2.96:1** (need 3:1 non-text)
   - Step-count chip: `--v5-amber-bright` bg / `--v5-panel` text → **3.37:1** (need 4.5:1 text)
   - Done steps `opacity: 0.55` → label **2.16:1** (need 4.5:1)

5. **v5 token source of truth**: `desk/src/styles/tokens.v5.css` + `manas_os/design/bakeoff/round4/debate_merged_light.html` (the frozen round-4 mockup). Palette: warm off-white `#f7f6f2` canvas, ink ramp, teal `#0d6c6c`, amber `#8a5a12`, green `#14713f`, red `#ad2c34`, Fraunces/Public Sans/IBM Plex Mono. Radius ladder `--v5-r-*`, shadows `--v5-shadow-*`, type scale `--v5-fs-*`.

---

## Deliverables — a DESIGN SPEC at `manas_os/design/V5_TOKEN_MIGRATION_DESIGN.md` covering:

### 1. Semantic Token Registry (append to `tokens.v5.css`)
Define every missing `--v5-*` token needed. Each must:
- Derive from the locked v5 palette (no new hues)
- Use `rgba(var(--v5-*-rgb), <alpha>)` for translucent variants (matches `primitives.v5.css` precedent)
- Be named semantically: `--v5-hmm-bull`, `--v5-hmm-bull-text`, `--v5-volume-bull-pp`, `--v5-confidence-high`, `--v5-mswing-positive`, `--v5-ema-10`, etc.
- Include RGB variants for rgba() use: `--v5-hmm-bull-rgb: 13, 108, 108`

Produce a **table**: ChartDrawer constant → new `--v5-*` token (exact 53 rows).

### 2. Contrast Fix Spec (exact token swaps in `primitives.v5.css`)
| P0 ID | Selector | Current | New Token(s) | Target Ratio |
|-------|----------|---------|--------------|--------------|
| 1 | `.gfr-step--active` border-left-color | `--v5-amber-bright` | `--v5-amber-ink` | 7.08:1 |
| 2 | `.gfr-step__count` bg/text | `--v5-amber-bright` / `--v5-panel` | `--v5-amber-ink` / `--v5-panel` | 8.04:1 |
| 3 | `.gfr-step--done .gfr-step__label` | `opacity: 0.55` | remove opacity; `color: --v5-ink-mute` + `✓` icon in `--v5-green` | 4.8:1 |

### 3. StatusBadge 5-State Design (LIVE/SHADOW/WARMING/EXPERIMENTAL/NEEDS-DATA)
- Color, shape, icon, tooltip copy for each state
- Must pass AA on all locked token pairs (verify contrast)
- Reuses existing `StatusBadge` component in `primitives.v5.css:1089-1093` (WARMING variant exists at 5.64:1)

### 4. Single-Theme Removal Plan
- Which legacy token refs remain in codebase after bridge (`grep -r "var(--[^v5]" desk/src`)
- Exact bridge aliases to add to `tokens.v5.css:76-98` to cover them
- Import removal sequence (App.css → App.jsx)

### 5. Cheap-Win Visual Specs
- Scanner preset click: scroll-into-view behavior
- PositionsTab freshness chip: 3 states (EOD / live / feed down) + token colors
- Journal delete: confirmation UX (inline, not modal)
- Reduced-motion guard pattern to replicate across 10 CSS files

### 6. Migration Order (dependency-aware)
1. Add semantic tokens to `tokens.v5.css`
2. ChartDrawer.jsx + ChartDrawer.v5.css (largest surface)
3. Co-mounted files (MarketHome, Scanners, Debate, viz.js)
4. Contrast fixes in primitives.v5.css
5. StatusBadge wiring (3 locations)
6. tokens.css import removal + bridge verification
7. Cheap wins

---

## Format

Markdown at `manas_os/design/V5_TOKEN_MIGRATION_DESIGN.md` with:
- Token registry table (53 rows)
- Contrast fix table (3 rows)
- StatusBadge 5-state spec (color/icon/tooltip per state)
- Bridge alias list
- Migration order
- **ASCII wireframes** for: ChartDrawer legend pills, volume bars, EMA lines, status chips
- **OPTIONAL but valued**: self-contained HTML mockup of ChartDrawer in v5 language (like round-4 mockup) so the design reads at a glance

Flag any design decision you're unsure about for the maintainer rather than guessing.

---

## Output note

End with: the spec file path, the 53-row migration table, the 3 contrast swaps, the 5-state StatusBadge spec, and your single strongest design recommendation for making the token migration maintainable long-term (e.g., "add a token lint to desk_gate.py" / "introduce a ChartDrawer token module" / etc.). Real, grounded design — no invented trading guidance, honest states only.