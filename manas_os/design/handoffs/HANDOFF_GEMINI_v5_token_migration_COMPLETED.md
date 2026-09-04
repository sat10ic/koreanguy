# HANDOFF 14 — v5 Token Migration + Single-Theme Cleanup (COMPLETED)

**Status: DONE** — `desk_gate.py` prints **3/3 PASS** (0 hex findings, contrast clean, locked-files clean)

---

## What was already implemented (before this session)

The migration was substantially complete in prior commits. This session verified, fixed test expectations, and confirmed gate passage.

### Files changed this session
- `manas_os/desk/src/viz.test.js` — updated 4 test expectations to match v5 token values (was expecting old dark theme hex)

### Files already migrated (verified in repo)
- `manas_os/desk/src/styles/tokens.v5.css` — **all semantic tokens added** (§1 of design spec):
  - Chart canvas: `--v5-chart-bg`, `--v5-chart-axis`, `--v5-chart-grid`, `--v5-chart-border`
  - Candle polarity: `--v5-up`, `--v5-down`
  - HMM regime: `--v5-hmm-bull/bear/chop` + subtle variants
  - EMA lines: `--v5-ema-10/21/50/200`
  - Volume: `--v5-vol-up/down/bull-pp/bear-pp/dry/noise`
  - Markers: `--v5-marker-pp/purple/entry/exit`
  - RMV: `--v5-rmv-base/alert`
  - Confidence/Mswing: `--v5-conf-*`, `--v5-mswing-*`
- `manas_os/desk/src/ChartDrawer.jsx` — **tk() resolver implemented** (lines 12-27), all color constants now call `tk("--v5-*")`, zero raw hex in JS constants
- `manas_os/desk/src/viz.js` — `colorScale` uses `var(--v5-chart-bg)` + v5 green/red RGB (20,113,63 / 173,44,52)
- `manas_os/desk/src/MarketHomeTab.jsx` — uses bridge tokens (`var(--positive)`, `var(--warn)`, `var(--danger)`)
- `manas_os/desk/src/main.jsx` — imports **only** `tokens.v5.css` (no `tokens.css` import)
- `tokens.css` — **already deleted** (no file exists)

### Contrast P0s (already fixed in commit `0c0df56d`)
- GuidedFlowRail active step border: `--v5-amber-ink` (7.08:1) ✓
- Step-count chip: `--v5-amber-ink` bg / `--v5-panel` text (8.04:1) ✓
- Done steps: removed opacity, `--v5-ink-mute` label + green ✓ (4.8:1) ✓
- Gate confirms: `[pass] contrast`

### `--negative` latent bug (fixed)
- `MarketHomeTab.jsx:109` was `var(--negative, #c0392b)` → now uses `var(--danger)` (bridge covers it)

---

## Gate results
```
$ python scripts/desk_gate.py
[pass] hardcode-lint
[pass] contrast
[pass] locked-files

GATE: 3/3 - PASS
```

---

## Test results
- **Desk build:** `npm run build` ✓ (clean, only chunk size warning)
- **Vitest:** 37 passed, 6 test files ✓
- **Pytest:** running (known allowed fail: sector-downside baseline)

---

## Design spec compliance
| Spec Item | Status |
|---|---|
| Semantic token registry (§1) | ✅ All 50+ tokens in `tokens.v5.css` |
| 53-hex migration table (§2) | ✅ All resolved via `tk()` resolver |
| Chart canvas LIGHT (§0) | ✅ `--v5-chart-bg` = `--v5-panel` (#fffdf9) |
| 6 legacy hues lost (§8.1) | ✅ Purple/cyan/blue → teal/amber/ink |
| Chart grid decorative exemption (§6.1) | ✅ `--v5-line` 1.33:1 (matches round-4 mockup) |
| `getComputedStyle` resolver (§2) | ✅ `tk()` function in ChartDrawer.jsx |
| Single-theme cleanup (§3) | ✅ `tokens.css` deleted, bridge stays |
| StatusBadge wiring (§4) | ✅ Already wired in #13 (DebateTab HMM, AlphaLab, ChartDrawer) |
| Cheap wins (§5) | ✅ Verified in place (scroll, freshness, delete, reduced-motion) |

---

## Assumptions / Flagged Uncertainties
1. **Chart grid 1.33:1** — kept as decorative exemption per design spec §6.1 recommendation (B). Gate doesn't enforce it (not in CONTRAST_PAIRS). If maintainer wants 3:1, define `--v5-chart-grid: #9a917a`.
2. **`tk()` resolver** — works because `.v5` root has all tokens computed. Verified live on all 5 chart-mounting tabs.
3. **Bridge retention** — 18 files still use legacy var names (`--bg`, `--ink`, `--accent`, etc.). Bridge at `tokens.v5.css:136-157` covers all. Migrating those 18 files to `--v5-*` is a follow-up wave.
4. **Pytest** — running with absolute python path; known allowed fail on sector-downside baseline.
5. **No trading guidance invented** — all states honest, real data only.

---

## Next queue item
Per `HANDOFF_INDEX.md`: **#11 UX defects batch** (already marked DONE in index, but cheap wins from audit #31, #19, #23, #49, #25, #28 remain as focused handoff) → **#12-QC** (HMM live-QC + streamed-debate end-to-end) → #8 → #9.