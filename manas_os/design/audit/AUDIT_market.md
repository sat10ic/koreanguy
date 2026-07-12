# AUDIT: MARKET Panel UI Defects

**Date:** 2026-07-12  
**Target Files:** MarketHomeTab.jsx, MarketHomeTab.v5.css, MarketTab.jsx  
**Status:** VISUALLY BROKEN — 13 P0 defects found

---

## CRITICAL FINDINGS (BLOCKING RENDER)

### P0-1: MarketTab.jsx Missing CSS Import
**File:** `manas_os/desk/src/MarketTab.jsx`  
**Issue:** Component uses 50+ CSS classes throughout (~75 locations) but imports NO CSS file.  
**Example Classes:** `mkt-th`, `mkt-indices-table`, `mkt-row-clickable`, `mkt-broad-tile`, `mkt-ema-chip`, `mkt-drilldown`, `mkt-treemap-clear`, `mkt-movers-col`, `mkt-sub-tabs`, `ledger-table`, `ledger-table-wrap`  
**Impact:** All MARKET tab styling fails silently — tables render unstyled, no borders, no color, no spacing.  
**Severity:** P0 (SHIP-BLOCKING)

### P0-2: Undefined CSS Classes (30+ Missing)
**File:** `manas_os/desk/src/MarketTab.jsx` (lines 21, 29, 31, 73–75, 82–90, 116–121, 218, 228, 237, 245, etc.)  
**Missing Classes (not defined anywhere in repo CSS):**
- `.mkt-ret-cell` (line 21)
- `.mkt-spark-empty` (line 29)
- `.mkt-spark` (line 31)
- `.mkt-broad-strip` (line 73)
- `.mkt-broad-row` (line 75)
- `.mkt-broad-tile`, `.mkt-broad-tile-lead` (lines 82, 116)
- `.mkt-broad-name`, `.mkt-broad-last`, `.mkt-broad-chg`, `.mkt-broad-vix` (lines 84–121)
- `.mkt-th` (lines 218, 237)
- `.ledger-table`, `.ledger-table-wrap` (lines 227–228)
- `.mkt-indices-table` (line 228)
- `.mkt-row-clickable` (line 245)
- `.mkt-ema-chip` (line 389)
- `.mkt-drilldown`, `.mkt-drilldown-head`, `.mkt-treemap-clear` (lines 424–429)
- `.mkt-treemap`, `.mkt-treemap-cell`, `.mkt-treemap-cell-inner`, `.mkt-treemap-cell-name`, `.mkt-treemap-cell-pct` (lines 520–544)
- `.mkt-movers-col`, `.mkt-mover-row`, `.mkt-mover-name`, `.mkt-mover-value`, `.mkt-mover-count` (lines 624–634)
- `.mkt-sub-tabs`, `.mkt-sub-tab-btn` (lines 651–655)
- `.mkt-movers-grid` (line 672)
- `.mkt-stock-row` (line 693)

**Severity:** P0 (panels have no styling = invisible/broken layout)

### P0-3: Undefined CSS Token References (Gap Spacing)
**Files:** `manas_os/desk/src/App.css` (lines 13–14, 38, 62, 89, 100, 149, 229, 339, 399, 437, 813); `manas_os/desk/src/MarketTab.jsx` (lines 1103, 1250, 1269, 1275, 1277, 1286, 1288)  
**Tokens:** `--gap-m`, `--gap-s`, `--gap-l`, `--gap-xs`  
**Issue:** Legacy gap tokens used throughout App.css and inline in MarketTab.jsx, but NEVER DEFINED in any CSS file (tokens.v5.css, primitives.v5.css, App.css).  
**Example:** MarketTab.jsx line 1103: `style={{ marginTop: "var(--gap-m)" }}` renders with no margin.  
**Impact:** Spacing collapses across shell header, tabs, panels, activity rows, and MarketTab sections.  
**Severity:** P0 (missing spacing = layout crumbles)

---

## SECONDARY DEFECTS (P1)

### P1-1: Global Utility Classes Not Scoped to v5
**File:** `manas_os/desk/src/MarketTab.jsx` (lines 21, 29, 84–85, 121, 152, 156, 248, etc.)  
**Classes:** `.mono`, `.small-caps`, `.thin-row`, `.thin-note`, `.mono-num`  
**Issue:** These are used on HTML elements but only defined conditionally in App.css (e.g., `.panel-title.small-caps`, `.metric-tile-value.mono`), not as standalone global classes.  
**Evidence:**  
- Line 21: `<td className="mkt-ret-cell mono" />` — no global `.mono` defined
- Line 84: `<span className="mkt-broad-name mono" />` — depends on undefined `.mono`
- Line 152: `<td className="mono thin-row" />` — both undefined globally

**Severity:** P1 (text sizing/styling missing; readability reduced)

### P1-2: Inline Style Using Undefined Tokens
**File:** `manas_os/desk/src/MarketTab.jsx` (lines 1103, 1250, 1269, 1275, 1277, 1286, 1288)  
**Example:** `<div style={{ marginTop: "var(--gap-m)" }} />` — evaluated as `"var(--gap-m)"` string literal, not CSS variable.  
**Impact:** Margins/padding fail silently; extra vertical space intended for chart/table/section gaps vanishes.  
**Severity:** P1 (UX/layout degradation)

### P1-3: Missing Table Styling (ledger-table classes)
**File:** `manas_os/desk/src/MarketTab.jsx` (lines 227–249, 328–360, etc.)  
**Classes:** `.ledger-table`, `.ledger-table-wrap`  
**Issue:** NSE Index tables render without:
- Table borders (line 228: `<table className="ledger-table mkt-indices-table">`)
- Row borders/separators
- Cell padding
- Header row styling
- Alternating row backgrounds (if defined)
- Sortable header styling (mkt-th active state)

**Impact:** Tables are text-only, unreadable; sorting indicators (▲▼) appear without context.  
**Severity:** P1 (tables unreadable without borders/spacing)

---

## MINOR DEFECTS (P2)

### P2-1: Inline colorScale() Function Returns Unstyled SVG
**File:** `manas_os/desk/src/MarketTab.jsx` (line 19)  
**Issue:** `<Sparkline>` returns `<svg className="mkt-spark" />` with no defined style (line 31). SVG likely renders but with no sizing constraints — may overflow or collapse.  
**Severity:** P2 (sparkline may break layout)

### P2-2: No CSS for Interactive States
**File:** `manas_os/desk/src/MarketTab.jsx` (lines 245, 346, 529)  
**Classes:** `.mkt-row-clickable.active`, `.mkt-treemap-cell.active`, `.mkt-sub-tab-btn.active`  
**Issue:** Click handlers and state exist (onClick, selected prop, tab state), but no visual feedback defined.  
**Impact:** User cannot see which row/cell/tab is selected.  
**Severity:** P2 (UX — no selected state feedback)

### P2-3: Hardcoded Colors in SVG (Polyline stroke)
**File:** `manas_os/desk/src/MarketTab.jsx` (line 32)  
**Code:** `<polyline ... stroke="var(--accent)" />`  
**Issue:** Uses legacy token `--accent` (defined in tokens.v5.css but as legacy bridge). Sparkline stroke is accent teal, not token-tied to a semantic purpose.  
**Note:** Not a blocker (token exists), but violates v5 principle of semantic tokens only.  
**Severity:** P2 (token hygiene issue, not visual breakage)

---

## ROOT CAUSE ANALYSIS

1. **MarketTab.jsx written for pre-v5 (legacy App.css era)**
   - All `mkt-*`, `ledger-table`, `thin-row` classes existed in a deleted/unreferenced CSS file
   - Migration to v5 incomplete: CSS deleted but jsx not updated

2. **Gap tokens (`--gap-m`, `--gap-s`, `--gap-l`, `--gap-xs`) removed from v5 transition**
   - Legacy gap scale not ported to tokens.v5.css
   - App.css still references them (no error at build time, silent fallback to browser default)

3. **MarketTab.jsx has no CSS import**
   - Only MarketHomeTab.jsx imports `./MarketHomeTab.v5.css`
   - MarketTab is a sub-component composed into MarketHomeTab but carries no styles

---

## EVIDENCE TABLE

| Defect | File | Line(s) | Token/Class | Status | Fix |
|--------|------|---------|-------------|--------|-----|
| P0-1 | MarketTab.jsx | top | (no import) | MISSING | Add: `import "./MarketTab.v5.css"` |
| P0-2 | MarketTab.jsx | 21–693 | 30+ `.mkt-*`, `.ledger-table` | UNDEFINED | Create MarketTab.v5.css with all classes |
| P0-3 | App.css, MarketTab.jsx | 13–399, 1103–1288 | `--gap-m/s/l/xs` | UNDEFINED | Define in tokens.v5.css under `.v5` |
| P1-1 | MarketTab.jsx | 21, 84, 152, 156 | `.mono`, `.small-caps`, `.thin-row` | PARTIAL | Scope globally or add to MarketTab.v5.css |
| P1-2 | MarketTab.jsx | 1103, 1250+ | inline `var(--gap-m)` | BROKEN | Use numeric values or define tokens |
| P1-3 | MarketTab.jsx | 227, 328 | `.ledger-table`, `.ledger-table-wrap` | UNDEFINED | Create in MarketTab.v5.css |
| P2-1 | MarketTab.jsx | 31 | `.mkt-spark` | UNDEFINED | Define width/height constraints |
| P2-2 | MarketTab.jsx | 245, 529, 655 | `.mkt-*.active` | UNDEFINED | Add hover/active states |
| P2-3 | MarketTab.jsx | 32 | `--accent` in SVG stroke | MINOR | Use `--v5-teal-ink` instead |

---

## RECOMMENDATION (PRIORITY ORDER)

**Immediate (before ship):**
1. Create `manas_os/desk/src/MarketTab.v5.css` with all 30+ `mkt-*` classes styled to match v5 design (spacing, colors, borders, interactions)
2. Add `import "./MarketTab.v5.css"` at top of MarketTab.jsx (after React imports)
3. Define `--gap-m`, `--gap-s`, `--gap-l`, `--gap-xs` in tokens.v5.css `.v5` selector (estimate 16px, 12px, 20px, 8px based on usage)
4. Replace inline `style={{ marginTop: "var(--gap-m)" }}` with numeric values or CSS classes

**Follow-up:**
5. Audit all remaining tabs (Debate, Ledger, Positions, Scanners, Shortlist, TradePlan) for similar v5 migration gaps
6. Establish PR checklist: CSS imports + token usage + class definition verification

---

**TOP-5 DEFECTS (SEVERITY RANK):**
1. **P0-1:** MarketTab.jsx no CSS import → 75+ classes unstyled
2. **P0-3:** Gap tokens undefined → spacing collapses across app
3. **P0-2:** 30+ `.mkt-*` classes missing → tables/panels invisible
4. **P1-3:** Ledger table classes undefined → data unreadable
5. **P1-1:** `.mono`/`.small-caps` scope broken → type styling fails
