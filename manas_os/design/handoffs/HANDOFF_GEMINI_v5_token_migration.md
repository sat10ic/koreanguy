# HANDOFF 14 — v5 Token Migration + Single-Theme Cleanup (Gemini)

Repo `C:\Users\satta\Downloads\koreanguy`, branch `emergent`. Standing rules: HANDOFF_INDEX.md.
**The aesthetic release blocker:** `desk_gate.py` baseline 53 findings (all ChartDrawer raw hex).
This wave closes them to 0. Done-test = `python scripts/desk_gate.py` prints **3/3 PASS**.

---

## Load-bearing facts (verified)

1. **53 raw-hex constants** in `desk/src/ChartDrawer.jsx:8-23` + scattered usage:
   - `HMM_COLORS` (4 states × 2 = 8 values)
   - `VOLUME_COLORS` (3 states × 2 = 6 values)
   - `CONFIDENCE_LABEL` (3 states × 2 = 6 values)
   - `MSWING_LABEL` (4 states × 2 = 8 values)
   - `EMA_LEGEND` (4 EMAs × 2 = 8 values)
   - Plus inline raw hex in JSX style objects (~25 more)

2. **Legacy `tokens.css` still imported** — `App.jsx:17` imports `App.css` which uses `tokens.css` vars.
   Bridge aliases at `tokens.v5.css:76-98` map some legacy names. Two live theme sources conflict.

3. **3 contrast P0s** in `primitives.v5.css` (GuidedFlowRail) — must fix as part of this wave:
   - Active step border: `--v5-amber-bright` on `--v5-amber-glow` → 2.96:1 (need 3:1)
   - Step-count chip: `--v5-amber-bright` bg / `--v5-panel` text → 3.37:1 (need 4.5:1)
   - Done steps `opacity: 0.55` → label 2.16:1 (need 4.5:1)

4. **Design spec source:** `manas_os/design/V5_TOKEN_MIGRATION_DESIGN.md` (GLM-produced) contains:
   - Semantic token registry (exact `--v5-*` values)
   - 53-row migration table (ChartDrawer constant → v5 token)
   - Contrast fix spec (exact token swaps)
   - Status-chip 5-state design (LIVE/SHADOW/WARMING/EXPERIMENTAL/NEEDS-DATA)
   - Single-theme removal plan
   - Cheap-win visual specs

---

## Scope

### 1. Define missing semantic tokens in `desk/src/styles/tokens.v5.css`
Add every `--v5-*` token from the design spec's registry. All values must derive from the locked
v5 palette (teal/amber/green/red + ink ramp). Use `rgba(var(--v5-*-rgb), opacity)` for subtle
variants. No new hue families.

### 2. Migrate `desk/src/ChartDrawer.jsx` — replace all 53 raw hex with v5 tokens
- Replace constant objects (`HMM_COLORS`, `VOLUME_COLORS`, etc.) with token references
- Replace inline style hex in JSX with token references (CSS vars or class-based)
- Add semantic class names in `ChartDrawer.v5.css` for legend pills, volume bars, EMA lines, etc.
- **Zero raw hex** in ChartDrawer.jsx after migration (comments excluded)

### 3. Migrate co-mounted files (ChartDrawer mounts on 5 tabs)
- `desk/src/MarketHomeTab.jsx` + `MarketHomeTab.v5.css` (3 raw hex found by gate)
- `desk/src/ScannersTab.jsx` + `ScannersTab.v5.css` (3 raw hex)
- `desk/src/ShortlistTab.jsx` (uses ChartDrawer thumbs)
- `desk/src/DebateTab.jsx` + `DebateTab.v5.css` (1 raw hex)
- `desk/src/TradePlanTab.jsx` (uses ChartDrawer)
- `desk/src/viz.js` (3 raw hex) — migrate to token references

### 4. Fix 3 contrast P0s in `desk/src/components/v5/primitives.v5.css`
Exact swaps per design spec:
```css
/* P0 ID 1: Active step border */
.gfr-step--active { border-left-color: var(--v5-amber-ink); } /* was --v5-amber-bright */

/* P0 ID 2: Step-count chip */
.gfr-step__count { background: var(--v5-amber-ink); color: var(--v5-panel); }

/* P0 ID 3: Done steps — remove opacity dim, use icon + mute ink */
.gfr-step--done .gfr-step__label { color: var(--v5-ink-mute); opacity: 1; }
.gfr-step--done .gfr-step__icon { color: var(--v5-green); } /* ✓ icon */
```

### 5. Wire StatusBadge into 3 warming/experimental organs (cheap wins)
- `DebateTab.jsx:184` — HMM context: `<StatusBadge status="WARMING" why={r.hmm_caption} />`
- `AlphaLab.jsx:85` — Research Bench: `<StatusBadge status="NEEDS-DATA" why="Run the nightly update to seed the registry." />`
- `ChartDrawer.jsx:244,636` — ModelStateBox: `<StatusBadge status="EXPERIMENTAL" />`

### 6. Single-theme cleanup: retire `tokens.css`
- Remove `tokens.css` import from `App.css` / `App.jsx` import chain
- Verify bridge at `tokens.v5.css:76-98` covers all legacy refs (add missing aliases if needed)
- Zero console errors, zero visual regression on all 7 tabs

### 7. Cheap wins (visual fixes)
- **Scanner preset click:** add `scrollIntoView({behavior: 'smooth'})` in `ScannersTab.jsx` openPreset
- **PositionsTab freshness chip:** render "EOD 07-10" / "live 10:42" / "feed down" based on `fyers_connected` + `data_as_of`
- **Journal delete:** wire `DeleteControl.onDelete` → `api.deleteJournalTrade()` → reload
- **Reduced-motion guards:** add `@media (prefers-reduced-motion: reduce)` to all 10 CSS files
  (copy pattern from `primitives.v5.css:963-966`)

---

## Guardrails

- Describe the TOOL, never give financial advice
- Money-math LOCKED — UI/analytics never compute stop/target/qty/risk
- Real data only; honest empty/"needs ingest"/PENDING states
- `.v5`-scoped CSS with tokens only; plain SVG; a11y AA; reduced-motion
- Additive DB migrations only (not needed here)
- Never print rupee glyph — use "Rs"
- `pytest manas_os/tests -q` green + `cd manas_os/desk && npm run build` + `npx vitest run`
- **`python scripts/desk_gate.py` on THIS wave** — must print 3/3 PASS

---

## Output

`HANDOFF_GEMINI_v5_token_migration_COMPLETED.md` containing:
- Files changed (full list)
- Token registry added to `tokens.v5.css` (show diff)
- Migration table applied (ChartDrawer + co-mounted files)
- Contrast fixes in `primitives.v5.css` (show diff)
- StatusBadge wiring (3 locations)
- `tokens.css` removal verification
- Cheap-win implementations
- **Gate result:** `python scripts/desk_gate.py` output showing 3/3 PASS
- Test results (pytest, build, vitest)
- Any assumptions / flagged uncertainties

---

## Execution order (single-writer discipline)

1. Add semantic tokens to `tokens.v5.css`
2. Migrate ChartDrawer.jsx + ChartDrawer.v5.css
3. Migrate co-mounted files (MarketHome, Scanners, Debate, viz.js)
4. Fix contrast P0s in primitives.v5.css
5. Wire StatusBadge (3 locations)
6. Remove tokens.css import + verify bridge
7. Cheap wins (scroll, freshness, delete, reduced-motion)
8. Run `desk_gate.py` → must be 3/3 PASS
9. Run full test suite + build + vitest
10. Write completion note

Do NOT commit. Maintainer QCs and commits.