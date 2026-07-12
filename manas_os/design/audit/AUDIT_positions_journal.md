# UI-Defect Audit: POSITIONS & JOURNAL Panels
**Date:** 2026-07-12  
**Scope:** PositionsTab.jsx/v5.css (POSITIONS) + LedgerTab.jsx/v5.css (JOURNAL)  
**Method:** Mechanical token verification, raw color detection, interaction audit

---

## DEFINED TOKEN SET

**Base Colors:** --v5-canvas, --v5-canvas-1, --v5-panel, --v5-panel-2, --v5-panel-3, --v5-line, --v5-line-soft  
**Text:** --v5-ink, --v5-ink-dim, --v5-ink-mute, --v5-ink-faint  
**Semantic:** --v5-teal, --v5-teal-ink, --v5-teal-dim, --v5-amber, --v5-amber-ink, --v5-amber-bright, --v5-amber-glow, --v5-green, --v5-green-dim, --v5-red, --v5-red-dim  
**Fonts:** --v5-disp, --v5-sans, --v5-mono  
**Sizes:** --v5-fs-hero, --v5-fs-disp, --v5-fs-val, --v5-fs-body, --v5-fs-ui, --v5-fs-label, --v5-fs-micro  
**Radius:** --v5-r-xs, --v5-r-sm, --v5-r-md, --v5-r-lg, --v5-r-xl  
**Effects:** --v5-shadow-panel, --v5-shadow-hero, --v5-motion-fast, --v5-motion-tape

---

## PANEL AUDIT

### PANEL 1: POSITIONS (PositionsTab.jsx / PositionsTab.v5.css)

**Status:** PASSED (TOKEN REFS) + CRITICAL BUG (CLOSE MODAL INTERACTION)

#### CSS Token Verification
- **Result:** ✓ PASS — all 35 var(--v5-*) refs defined
- **Coverage:** colors, fonts, spacing, radius all use system tokens
- No undefined token references

#### Raw Color Violations (Non-Token Hex/RGBA)
**Severity: P1 (Accessibility & maintenance)**

| Line | Issue | Recommendation |
|------|-------|-----------------|
| 99 | `rgba(173, 44, 52, 0.025)` – red overlay in .v5-pos-card.v5-urgent | Extract to --v5-red + opacity token, currently hardcoded |
| 137 | `rgba(20, 113, 63, 0.25)` – green border in .v5-pos-verdict-pill.v5-tone-hold | Should use --v5-green with opacity token |
| 235 | `rgba(23, 24, 27, 0.15)` – shadow in .v5-pos-thermometer-dot | Reuse --v5-shadow-panel or create --v5-shadow-sm |
| 383 | `rgba(184, 127, 26, 0.2)` – amber border in .v5-pos-banner | Should use --v5-amber-bright with opacity |
| 553 | `rgba(247, 246, 242, 0.7)` – modal backdrop in .v5-pos-modal-backdrop | Matches --v5-canvas but hardcoded; use --v5-canvas with opacity |
| 711 | `rgba(173, 44, 52, 0.2)` – red border in .v5-pos-freshness.v5-freshness-feed-down | Reuse --v5-red with opacity |
| 721 | `rgba(13, 108, 108, 0.2)` – teal border in .v5-pos-freshness.v5-freshness-live | Reuse --v5-teal with opacity |

**Impact:** Cross-origin opacity values break theming consistency; opacity ratios differ (0.025 vs 0.2 vs 0.7).

#### JSX Interaction Audit

**CRITICAL BUG P0 — Close Modal State Leakage:**
- **File:** PositionsTab.jsx, lines 289–598 (CloseModal component)
- **Issue:** Modal does not reset form state on cancel. If user:
  1. Opens close modal for symbol INFY
  2. Enters exit price: 210.5
  3. Clicks Cancel (`onCancel()`)
  4. Opens close modal for next position TCS
  5. **BUG:** Form still shows INFY's exit price 210.5; no setState reset
- **Root:** `onCancel()` callback (line 502) only hides modal, does not clear `exitPrice` / `reasonTag` state
- **Evidence:** Lines 493–496 declare local state; lines 502–507 handle Escape key but do NOT call `setExitPrice("")` / `setReasonTag("target")`
- **Severity:** P0 — User submits wrong exit price for next trade
- **Fix:** Add state reset in onCancel path: `setExitPrice(""); setReasonTag("target");`

**Inline Editor SL/Qty Interaction OK:**
- Lines 294–327: `setEditState("idle")` + `setInputValue("")` properly reset on cancel/save ✓
- Escape key guard (300–309) works correctly ✓

#### Font Coverage
- All font-family refs use defined tokens (--v5-sans, --v5-mono, --v5-disp) ✓

#### Imports & Dependencies
- All imports present: api.js, DensityContext.jsx, Glossary.jsx, components/v5/index.js ✓
- CSS import: "./PositionsTab.v5.css" ✓

---

### PANEL 2: JOURNAL (LedgerTab.jsx / LedgerTab.v5.css)

**Status:** FAILED (CRITICAL: INLINE STYLE BUG) + P1 RAW COLORS

#### CSS Token Verification
- **Result:** ✓ PASS — all 30 var(--v5-*) refs defined
- No undefined token references

#### Raw Color Violations (Non-Token RGBA)
**Severity: P1 (Accessibility & maintenance)**

| Line | Issue | Recommendation |
|------|-------|-----------------|
| 296 | `rgba(184, 127, 26, 0.28)` – amber border in .v5-jr-status-amber | Create --v5-amber-bright-opacity-28 or inline opacity helper |
| 301 | `rgba(20, 113, 63, 0.25)` – green border in .v5-jr-status-green | Create --v5-green-opacity-25 token |
| 306 | `rgba(13, 108, 108, 0.22)` – teal border in .v5-jr-status-teal | Create --v5-teal-opacity-22 token |
| 445 | `rgba(20, 113, 63, 0.25)` – green border in .v5-jr-tag-clean-hit | Same as line 301, code duplication |
| 450 | `rgba(173, 44, 52, 0.25)` – red border in .v5-jr-tag-clean-miss | Create --v5-red-opacity-25 token |
| 456 | `rgba(184, 127, 26, 0.28)` – amber border in tags | Duplicate of line 296 |
| 516 | `rgba(173, 44, 52, 0.25)` – red border in .v5-jr-delete-confirm-btn | Duplicate of line 450 |
| 598 | `rgba(20, 20, 24, 0.45)` – dark overlay in .v5-jr-modal-backdrop | Hardcoded dark; use --v5-ink with opacity |
| 664 | `rgba(173, 44, 52, 0.4)` – red border in .v5-jr-modal-error | Reuse --v5-red with opacity |

**Impact:** 9 hardcoded rgba values, 6 duplicate opacity pairs, opacity inconsistency (0.22, 0.25, 0.28, 0.4, 0.45).

#### JSX Interaction Audit

**CRITICAL BUG P0 — R-Bar Fill Color Won't Render:**
- **File:** LedgerTab.jsx, lines 183–205 (RBar component)
- **Issue:** Inline style passes CSS variable strings as JS values
  ```javascript
  // Line 190–194
  const style = {
    width: `${pct}%`,
    background: up ? "var(--v5-green)" : "var(--v5-red)",  // ← BUG
    ...(up ? { left: "50%" } : { right: "50%" }),
  };
  ```
- **Why it fails:** JavaScript object values cannot be CSS variables. Browser receives the literal string `"var(--v5-green)"`, not the computed color value.
- **Visual symptom:** R-bar fill div (line 198: `.v5-jr-r-bar-fill`) appears with no background color; bar renders as transparent/invisible.
- **Correct approach:** Use CSS class approach instead of inline style:
  ```javascript
  // Option 1: Use className + CSS
  <div className={`v5-jr-r-bar-fill ${up ? "v5-jr-r-pos" : "v5-jr-r-neg"}`} style={{ width: `${pct}%`, ...positioning }} />
  // Option 2: Use CSS custom property setter in JS
  style={{ width: `${pct}%`, "--r-color": up ? "var(--v5-green)" : "var(--v5-red)", ...}}
  // Then in CSS: background: var(--r-color);
  ```
- **Evidence:**
  - Line 198: render passes `style` object with background property
  - Line 192: background value is NOT a valid JS value (can't be computed at runtime)
  - Line 259–263 in CSS: `.v5-jr-pos { color: var(--v5-green); }` .v5-jr-neg { color: var(--v5-red); }` — these override only TEXT color, not background
- **Severity:** P0 — Equity curve's R-bar visual feedback completely broken; users can't assess win/loss at a glance
- **Testing:** Render a closed trade with r_result > 0; the bar fill should be green but appears invisible

**Delete Button State OK:**
- Lines 254–288: DeleteControl properly manages `confirming` state ✓
- Escape key does not affect delete (no listener) — acceptable ✓
- Delete payload sent correctly via onDelete callback ✓

**Editable Cell Interaction OK:**
- Lines 216–252: EditableCell properly handles input focus, blur, Enter, Escape ✓
- Form state isolated per field (trade.trade_id + field) ✓

**Table Row Actions:**
- Lines 290–363: TradeHistoryTable row rendering correct ✓
- No redirect or unexpected nav ✓

#### Font Coverage
- All font-family refs use defined tokens ✓

#### Imports & Dependencies
- All imports present: api.js, Glossary.jsx, DensityContext.jsx, components/v5/index.js ✓
- CSS import: "./LedgerTab.v5.css" ✓

---

## TOP 5 CRITICAL ISSUES (ACROSS BOTH PANELS)

### 1. **R-Bar Fill Color Silent Failure** — P0 BLOCKER
- **Panel:** JOURNAL (LedgerTab.jsx:192)
- **Impact:** Equity curve R-bars render invisible; no visual feedback on win/loss
- **Fix time:** 2 min — change to class-based coloring

### 2. **Close Modal Form State Leak** — P0 BLOCKER
- **Panel:** POSITIONS (PositionsTab.jsx:502)
- **Impact:** User submits previous trade's exit price to next position
- **Fix time:** 3 min — add state reset in onCancel

### 3. **Hardcoded RGBA Modal Backdrop** — P1 THEMATIC
- **Panel:** JOURNAL (LedgerTab.v5.css:598)
- **Impact:** Modal backdrop color inconsistent with theme tokens
- **Fix time:** 1 min — replace with --v5-ink opacity

### 4. **7 Hardcoded RGBA Borders (Positions Panel)** — P1 MAINTENANCE
- **Panel:** POSITIONS (PositionsTab.v5.css:99, 137, 235, 383, 553, 711, 721)
- **Impact:** Cross-origin opacity values; thematic inconsistency; a11y opacity compliance
- **Fix time:** 5 min — create opacity token layer (--v5-*-dim-opacity-XX)

### 5. **9 Hardcoded RGBA Borders (Journal Panel)** — P1 MAINTENANCE
- **Panel:** JOURNAL (LedgerTab.v5.css:296, 301, 306, 445, 450, 456, 516, 598, 664)
- **Impact:** Duplicate opacity values across 6 pairs; opacity inconsistency (0.22, 0.25, 0.28, 0.4, 0.45)
- **Fix time:** 8 min — create opacity token layer + dedup borders

---

## SUMMARY

| Metric | Result | Status |
|--------|--------|--------|
| Token refs undefined | 0 / 65 | ✓ PASS |
| Raw hex colors | 0 | ✓ PASS |
| Raw rgba colors | 16 | ✗ FAIL (P1) |
| Font-family undefined | 0 | ✓ PASS |
| **Critical JS bugs** | **2** | **✗ P0 BLOCKER** |
| Broken imports | 0 | ✓ PASS |

**Verdict:** DEPLOYMENT BLOCKED. Fix P0 issues (R-bar rendering, close-modal state) before ship. P1 rgba tokens can follow in next wave.
