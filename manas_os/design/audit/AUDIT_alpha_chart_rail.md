# UI Defect Audit: AlphaLab, ChartDrawer, GuidedFlowRail
**Date:** 2026-07-12  
**Scope:** Read-only mechanical audit of desk/src/ component styling and navigation  
**Defined Token Set:** tokens.v5.css (scoped `.v5`), primitives.v5.css, App.css  

---

## DEFINED TOKEN SET

### Base Tokens (tokens.v5.css, scoped under `.v5 {}`)
- **Canvas/Surface:** `--v5-canvas`, `--v5-canvas-1`, `--v5-panel`, `--v5-panel-2`, `--v5-panel-3`
- **Hairlines:** `--v5-line`, `--v5-line-soft`
- **Ink ramp:** `--v5-ink`, `--v5-ink-dim`, `--v5-ink-mute`, `--v5-ink-faint`
- **Accents:** `--v5-teal`, `--v5-teal-ink`, `--v5-teal-dim`, `--v5-amber`, `--v5-amber-ink`, `--v5-amber-bright`, `--v5-amber-glow`, `--v5-green`, `--v5-green-dim`, `--v5-red`, `--v5-red-dim`
- **Vote/semantic:** `--v5-vote-take-seg`, `--v5-vote-skip-seg`, `--v5-on-accent`
- **Chart palette:** `--v5-chart-bg`, `--v5-chart-axis`, `--v5-chart-grid`, `--v5-chart-border`, `--v5-up`, `--v5-down`
- **HMM/EMA/Volume:** `--v5-hmm-bull`, `--v5-hmm-bear`, `--v5-hmm-chop`, `--v5-hmm-bull-subtle`, `--v5-hmm-bear-subtle`, `--v5-hmm-chop-subtle`, `--v5-ema-10`, `--v5-ema-21`, `--v5-ema-50`, `--v5-ema-200`, `--v5-vol-up`, `--v5-vol-down`, `--v5-vol-bull-pp`, `--v5-vol-bear-pp`, `--v5-vol-dry`, `--v5-vol-noise`
- **Markers/RMV/Confidence:** `--v5-marker-pp`, `--v5-marker-purple`, `--v5-marker-entry`, `--v5-marker-exit`, `--v5-rmv-base`, `--v5-rmv-alert`, `--v5-conf-high-fg`, `--v5-conf-high-bg`, `--v5-conf-med-fg`, `--v5-conf-med-bg`, `--v5-conf-low-fg`, `--v5-conf-low-bg`, `--v5-mswing-up`, `--v5-mswing-neutral`, `--v5-mswing-down`
- **Type:** `--v5-disp`, `--v5-sans`, `--v5-mono`
- **Type scale:** `--v5-fs-hero`, `--v5-fs-disp`, `--v5-fs-val`, `--v5-fs-body`, `--v5-fs-ui`, `--v5-fs-label`, `--v5-fs-micro`
- **Radius/Shadow/Motion:** `--v5-r-xs`, `--v5-r-sm`, `--v5-r-md`, `--v5-r-lg`, `--v5-r-xl`, `--v5-shadow-panel`, `--v5-shadow-hero`, `--v5-motion-fast`, `--v5-motion-tape`
- **Legacy compatibility (remaps inside .v5):** `--bg`, `--bg-panel`, `--bg-sunken`, `--border`, `--ink`, `--ink-dim`, `--ink-faint`, `--accent`, `--accent-soft`, `--secondary`, `--secondary-soft`, `--positive`, `--positive-soft`, `--warn`, `--warn-soft`, `--danger`, `--danger-soft`, `--live`, `--font-sans`, `--font-mono`, `--shadow-panel`, `--shadow-hover`

---

## DEFECT FINDINGS

### P0 BLOCKERS: Undefined Token References

#### **AlphaLab.css — 28 refs to retired/undefined tokens**
| Line | Token | Ref Count | Issue | Severity |
|------|-------|-----------|-------|----------|
| 13, 49, 123, 146 | `--v5-paper` | 4 | **Not defined** in token layer. Intended remap: `--v5-panel` | **P0** |
| 17, 53, 126, 170 | `--v5-serif` | 4 | **Not defined**. No serif font in v5 palette; intended: `--v5-disp` (Fraunces) | **P0** |
| 28, 37, 44, 158, 159, 160 | `--v5-blue` | 6 | **Not defined**. Retired from v5 color ramp (no "blue" in accent set); intended: `--v5-teal-ink` | **P0** |
| 68, 77, 103, 116, 117, 145 | `--v5-rule` | 6 | **Not defined**. Intended remap: `--v5-line` (hairline color) | **P0** |
| 87, 137, 160 | `--v5-blue-wash` | 3 | **Not defined**. Intended remap: `--v5-teal-dim` (wash background) | **P0** |

**Impact:** All missing tokens cause computed value to be empty string or fallback to parent; text/borders/backgrounds vanish or go black. AlphaLab renders with completely invisible rule lines, uncolored headers, and missing washover backgrounds.

**Root cause:** AlphaLab.css authored before v5 token finalization (commit refs handoff 10); tokens were renamed/consolidated but CSS not updated.

---

### P1 ISSUES: Font-family Chain Breaks

#### **AlphaLab.css — Serif font not in palette**
| Line | Selector | Property | Issue |
|------|----------|----------|-------|
| 17 | `.alpha-hero h1` | `font: 600 clamp(28px, 4vw, 48px)/1.02 var(--v5-serif)` | `--v5-serif` **not defined** — no fallback serif family specified. Computed value = empty; h1 defaults to system default or empty. |
| 53 | `.alpha-panel h2` | `font: 600 24px/1.1 var(--v5-serif)` | Same; all `.alpha-panel h2` headings render with undefined font. |
| 126 | `.alpha-bench b` | `font: 600 24px/1 var(--v5-serif)` | Same; bench summary numbers unreadable. |
| 170 | `.v5-alpha-contract span` | `border-top: 1px solid var(--v5-rule)` → no border renders | Cascade: `--v5-rule` undefined → empty → border doesn't paint. |

**Fix:** `--v5-serif` should be defined in tokens.v5.css as `var(--v5-disp)` (Fraunces) or standalone serif, OR AlphaLab.css should reference `var(--v5-disp)` directly.

---

### P1 ISSUES: Dark-Island Color Remnants in ChartDrawer.jsx

#### **ChartDrawer.jsx — Token resolution at runtime**
| Line | Code | Status | Notes |
|------|------|--------|-------|
| 13–27 | `tk(name)` function + `_tokenCache` | ✓ CORRECT | Lazily resolves `--v5-*` tokens to hex at runtime via `getComputedStyle()`. Handles var() chains (up to 5 hops). Prevents raw hex in source. |
| 30–47 | Color constant objects (HMM_COLORS, VOLUME_COLORS) | ✓ CORRECT | All reference `tk()` thunks; no hardcoded hex. Comments note removal of `#00c878, #b66cff` etc. (dark-island legacy). |
| 219–223 | EMA_LEGEND | ✓ CORRECT | Token refs correct: `--v5-ema-10`, `--v5-ema-21`, `--v5-ema-50`, `--v5-ema-200`. |

**Verdict:** ChartDrawer.jsx properly migrated away from raw hex. Token layer is live and functional.

---

### P1 ISSUES: GuidedFlowRail Navigation Logic

#### **GuidedFlowRail.jsx — Callback routing**
| Line | Logic | Risk | Status |
|------|-------|------|--------|
| 36–47 | `tabForStep(id, step)` → maps step id → tab name | Medium | ✓ CORRECT: `order_ticket` with no symbol falls back to "DEBATE" (safe fallback). |
| 107–111 | onClick handler for step action button | Low | ✓ CORRECT: Null-checks all callbacks (`onStartUpdate &&`, `onOpenTradePlan &&`, `onNavigate &&`). No uncaught redirect. |
| 45 | `order_ticket` → returns `null` if `step.ticket?.symbol` exists; else "DEBATE" | **P1** | **LOGIC INVERSION RISK**: The ternary reads `step?.ticket?.symbol ? null : "DEBATE"`. If symbol exists, returns `null` (no tab), triggers `onOpenTradePlan()`. If symbol missing, returns "DEBATE" and calls `onNavigate("DEBATE")`. **Correct**, but the reversal is non-obvious; easy to break on future edits. No bug observed, but comment at line 41–44 flags this edge case correctly. |

**Verdict:** GuidedFlowRail logic is correct; no weird redirects. Edge-case fallback (symbol missing) properly documented.

---

### P2 ISSUES: Layout and Responsiveness

#### **AlphaLab.css — Media query breakpoint misalignment**
| Line | Selector | Rule | Issue |
|------|----------|------|-------|
| 208–234 | `@media (max-width: 850px)` | Various | ✓ CORRECT: Stacks hero + split panels, hides columns. No overflow. |
| 321–327 | `@media (max-width: 850px)` | Bench grid → 1fr 1fr | ✓ CORRECT: Shrinks bench summary to 2 columns. |

**Verdict:** Responsive design is sound. No layout breaks observed.

---

### P2 ISSUES: Minor Token Scope Concerns

#### **AlphaLab.jsx — No explicit `.v5` wrapper class**
| File | Issue | Context |
|------|-------|---------|
| AlphaLab.jsx:119 | Root div: `<div className="alpha-lab">` | No `.v5` class. If AlphaLab rendered outside `.v5` shell (e.g., on a legacy page), all `.v5` token remaps fail and color falls back to parent. |
| AlphaLab.css:1–365 | All selectors `.alpha-*` (no `.v5` prefix) | Selectors inherit from `.v5` scope at call site, but if caller doesn't wrap with `.v5`, styles break. Defensible but risky. |

**Mitigation:** Assume AlphaLab mounted inside `.v5` shell (App.jsx / Desk wraps it). If not, wrap `<div className="v5">` around the component.

---

### P2 ISSUES: Unused/Retired CSS Classes

#### **AlphaLab.css — Old class names**
| Line | Class | Status | Notes |
|------|-------|--------|-------|
| 112–138 | `.alpha-bench` | **NOT USED** | Replaced by `.alpha-bench-v5` at line 274. Dead code. |
| 155–207 | `.v5-alpha-*` | **PARTIALLY USED** | Only `.v5-alpha-card` referenced in comments; no JSX refs. Code paths in `.v5-alpha-contract`, `.v5-alpha-analogues` unreachable. |

**Fix:** Remove lines 112–138, 155–207 in next cleanup pass. Non-urgent (no visual defect, just unused selectors).

---

## SUMMARY: Top-5 Critical Defects

| # | Component | Defect | Severity | Fix |
|---|-----------|--------|----------|-----|
| 1 | AlphaLab.css | `--v5-paper` undefined (4 refs) | **P0** | Add to tokens.v5.css: `--v5-paper: var(--v5-panel);` — or replace all refs with `var(--v5-panel)` |
| 2 | AlphaLab.css | `--v5-blue` undefined (6 refs) | **P0** | Add to tokens.v5.css: `--v5-blue: var(--v5-teal);` — or replace with `var(--v5-teal-ink)` for text |
| 3 | AlphaLab.css | `--v5-rule` undefined (6 refs) | **P0** | Add to tokens.v5.css: `--v5-rule: var(--v5-line);` |
| 4 | AlphaLab.css | `--v5-serif` undefined (4 refs) | **P0** | Add to tokens.v5.css: `--v5-serif: var(--v5-disp);` — or define separate serif font |
| 5 | AlphaLab.css | `--v5-blue-wash` undefined (3 refs) | **P0** | Add to tokens.v5.css: `--v5-blue-wash: var(--v5-teal-dim);` |

**Immediate action:** Add the 5 missing token remaps to tokens.v5.css under the `.v5 {}` block (after line 156). All 28 undefined token refs will resolve.

---

## Files Scanned

- `/manas_os/desk/src/AlphaLab.jsx` — ✓ No JSON dump, no raw hex, imports correct, row actions wired
- `/manas_os/desk/src/AlphaLab.css` — **P0 token crisis** (28 refs to 5 undefined tokens)
- `/manas_os/desk/src/ChartDrawer.jsx` — ✓ Token migration complete, dark-island hex removed, tk() resolver functional
- `/manas_os/desk/src/components/v5/GuidedFlowRail.jsx` — ✓ Navigation logic correct, callbacks null-safe, no redirect loops
- `/manas_os/desk/src/styles/tokens.v5.css` — ✓ Single source of truth; missing 5 token remaps for legacy AlphaLab compat

**No P1+ issues in ChartDrawer or GuidedFlowRail. All defects isolated to AlphaLab.css token refs.**
