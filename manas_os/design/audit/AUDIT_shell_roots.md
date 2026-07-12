# Mechanical UI-Defect Audit: Manas OS Desk Shell

**Date:** 2026-07-12  
**Scope:** manas_os/desk/src/ (main.jsx, App.jsx, App.css, tokens.v5.css, primitives.v5.css)  
**Status:** Read-only audit; 15 undefined CSS custom properties found across 7 files.

---

## Executive Summary

The desk is **visually broken globally** due to **cascading undefined CSS variables** introduced by an incomplete "single-theme cleanup" commit. The deleted file `src/tokens.css` contained spacing tokens (--gap-*) and radius tokens (--radius-*) that were supposed to be moved to `App.css` but were **never written**. Additionally, three feature CSS files (`AlphaLab.css`, `DebateTab.v5.css`) reference new v5 token names that were never defined in `tokens.v5.css`.

---

## Root Cause

**PRIMARY:** `src/tokens.css` was deleted (git status shows `D`) and its spacing/radius tokens were NOT migrated. These tokens are actively used in:
- `App.css` (header, navigation, panels, spacing)
- `DeskTab.jsx` and `MarketTab.jsx` (inline styles with `height: var(--gap-m)`, etc.)

**SECONDARY:** Three CSS files reference new v5 token names that were never added to `tokens.v5.css`:
- `AlphaLab.css` uses --v5-paper, --v5-serif, --v5-blue, --v5-blue-wash, --v5-rule
- `DebateTab.v5.css` uses --v5-green-ink, --v5-red-ink, --v5-amber-dim

This creates a cascade: all unstyled elements render with no color/spacing/borders, causing "panels off" / "fonts off" / "layout collapsed" appearance.

---

## Defects by Severity

### P0 — BLOCKS ENTIRE UI (Top 5)

#### 1. Spacing Tokens Never Migrated from Deleted tokens.css
**File:** `App.css:13, 28, 38, 62, 89, 284–285, 399, 437, 528, 548, 639, 767, 813, 838`  
**Issue:** References to `var(--gap-l)`, `var(--gap-m)`, `var(--gap-s)`, `var(--gap-xs)` (7 undefined vars)  
**Impact:** Header spacing, padding, gaps collapse to 0px. Header/tabs/panels squeeze together.  
**Severity:** **P0** — Affects header layout, tab bar spacing, all panel padding  
**Files Using:** App.css (8 refs), DeskTab.jsx (2 refs), MarketTab.jsx (4 refs)  

**Example (App.css:13):**
```css
.shell-header {
  gap: var(--gap-l);  /* undefined — no spacing between header elements */
}
```

---

#### 2. Radius Tokens Never Migrated
**File:** `App.css:62 (--radius-pill)`, `App.css:109 (--v5-r-sm, but also --radius and --radius-sm used in body)`  
**Issue:** References to `var(--radius)`, `var(--radius-pill)`, `var(--radius-sm)` (3 undefined vars)  
**Impact:** Button and element corners render sharp (no border-radius). Affects date-scrubber buttons, mode-toggle, regime-pill.  
**Severity:** **P0** — Breaks button affordances globally  
**Files Using:** App.css (3 refs)  

**Example (App.css:62):**
```css
.date-scrubber {
  border-radius: var(--v5-r-sm);  /* defined */
}
.mode-toggle {
  border-radius: var(--v5-r-sm);  /* defined */
}
.regime-pill {
  border-radius: var(--radius-pill);  /* UNDEFINED */
}
```

---

#### 3. AlphaLab Tab Entirely Broken (5 Undefined v5 Tokens)
**File:** `AlphaLab.css:13, 17, 23, 28, 29, 37, 39, 40, 44, 48, 49, 53, 57, 68, 77, 78, 81, 87, 93, 103, 104, 108, 116, 117, 123, 126, 130, 131, 137, 138, 145, 146, 147, 153, 158, 159, 160, 161, 170, 174, 175, 179, 180, 193, 202, 206, 215, 239, 245, 246, 252, 266, 267, 271, 282, 283, 289, 292, 293, 297, 298, 302, 303, 312, 315, 320, 337, 338, 339, 340, 341, 342, 346, 349, 350, 351`  
**Issue:** `--v5-paper` (bg), `--v5-serif` (should be `--v5-disp`), `--v5-blue`, `--v5-blue-wash`, `--v5-rule` — 5 undefined vars across 50+ properties  
**Impact:** AlphaLab tab renders with no background color, wrong fonts, no accent colors for blue elements.  
**Severity:** **P0** — Entire tab is unusable  
**Files Using:** AlphaLab.css (50+ refs)  

**Examples:**
```css
.alpha-hero { background: var(--v5-paper); }  /* undefined */
.alpha-hero h1 { font: 600 clamp(28px, 4vw, 48px)/1.02 var(--v5-serif); }  /* undefined; should be --v5-disp */
.alpha-note-link { color: var(--v5-blue) !important; }  /* undefined; no blue in current palette */
.alpha-note { border-left: 3px solid var(--v5-blue); }  /* undefined */
```

---

#### 4. DebateTab v5 Colors Undefined (3 Tokens)
**File:** `DebateTab.v5.css`  
**Issue:** References to `--v5-green-ink`, `--v5-red-ink`, `--v5-amber-dim` (3 undefined vars)  
**Impact:** Debate tab verdict chips and sentiment indicators render without color.  
**Severity:** **P0** — Breaks verdict chip rendering  
**Files Using:** DebateTab.v5.css (3 refs)  

---

#### 5. Hardcoded Dark Color in Light Theme
**File:** `App.css:653`  
**Issue:** `.activity-row:hover { background: #1f1f1f; }` — hardcoded dark color (#1f1f1f is from old dark island theme)  
**Impact:** Activity rows are invisible on light background when hovered.  
**Severity:** **P0** — Breaks interactive element hover state in light theme  

**Current code:**
```css
.activity-row:hover {
  background: #1f1f1f;  /* dark island color, breaks light theme */
  box-shadow: var(--shadow-hover);
  border-color: var(--border);
}
```
Should be:
```css
.activity-row:hover {
  background: var(--bg-sunken);  /* or --v5-panel-2 */
  box-shadow: var(--shadow-hover);
  border-color: var(--border);
}
```

---

## Summary of Undefined Variables

| Variable | Defined In | Used In | Count | Severity |
|----------|-----------|---------|-------|----------|
| `--gap-l` | *MISSING* | App.css:13 | 1 | P0 |
| `--gap-m` | *MISSING* | App.css:28, 89, 437, DeskTab.jsx, MarketTab.jsx | 5 | P0 |
| `--gap-s` | *MISSING* | App.css:38, 62, 89, 399, 639, 813, 838, DeskTab.jsx | 8 | P0 |
| `--gap-xs` | *MISSING* | App.css:813, 838 | 2 | P0 |
| `--radius` | *MISSING* | App.css:434, 564 | 2 | P0 |
| `--radius-pill` | *MISSING* | App.css:162, 73 | 1 | P0 |
| `--radius-sm` | *MISSING* | App.css:109 | 1 | P0 |
| `--v5-paper` | *MISSING* | AlphaLab.css:13, 49, 123, 146, 289 | 5 | P0 |
| `--v5-serif` | *MISSING* | AlphaLab.css:17, 53, 126, 170, 292 | 5 | P0 |
| `--v5-blue` | *MISSING* | AlphaLab.css:28, 37, 44, 87, 158, 159, 174, 180 | 8 | P0 |
| `--v5-blue-wash` | *MISSING* | AlphaLab.css:87, 137, 160 | 3 | P0 |
| `--v5-rule` | *MISSING* | AlphaLab.css:68, 77, 103, 116, 117, 145, 193, 206 | 8 | P0 |
| `--v5-green-ink` | *MISSING* | DebateTab.v5.css | 1 | P0 |
| `--v5-red-ink` | *MISSING* | DebateTab.v5.css | 1 | P0 |
| `--v5-amber-dim` | *MISSING* | DebateTab.v5.css | 1 | P0 |

---

## Font References (VERIFIED ✓)

- `@fontsource-variable/fraunces` imported in `main.jsx:9–10` ✓
- `@fontsource/public-sans` imported in `main.jsx:11–15` ✓
- `@fontsource/ibm-plex-mono` imported in `main.jsx:16–19` ✓
- All three fonts defined in `tokens.v5.css:107–109` ✓
- No dangling font imports or mismatches detected.

---

## Routing/Redirects (VERIFIED ✓)

No infinite loops, bad tab resets, or broken URL handlers detected:
- `navigateTab(nextTab)` validates `TABS.includes(nextTab)` (App.jsx:323–324) ✓
- `useEffect([jumpToLatest])` handles URL params safely (App.jsx:423–425) ✓
- `handlePopState` syncs back/forward without loops (App.jsx:540–568) ✓
- Trade plan route uses `tradePlan !== null` state check (App.jsx:308–314) ✓

---

## Dangling/Duplicated CSS Blocks (NONE)

No obvious duplicate rules or malformed selectors detected. CSS syntax is valid across all files.

---

## Conclusion

**The ONE root cause is the deletion of `tokens.css` with incomplete migration.**

The file contained these spacing/radius tokens that were never re-added:
```css
--gap-xs, --gap-s, --gap-m, --gap-l, --radius-sm, --radius-pill, --radius
```

These are actively referenced in `App.css` (8 uses) and JSX inline styles (6 uses). Without them, all spacing collapses, buttons have no rounded corners, and the layout is broken globally.

Additionally:
- **AlphaLab.css** was written to use 5 new v5 token names that were never added to `tokens.v5.css` (--v5-paper, --v5-serif, --v5-blue, --v5-blue-wash, --v5-rule).
- **DebateTab.v5.css** was written to use 3 new v5 tokens (--v5-green-ink, --v5-red-ink, --v5-amber-dim) that were never defined.
- **App.css:653** hardcodes a dark theme color in a light-theme context.

### To Fix (Priority Order):

1. **Restore spacing/radius tokens to App.css** (or create new file) — defines all --gap-* and --radius-* vars
2. **Add missing v5 tokens to tokens.v5.css** — define --v5-paper, --v5-serif, --v5-blue, --v5-blue-wash, --v5-rule, --v5-green-ink, --v5-red-ink, --v5-amber-dim
3. **Fix App.css:653** — replace `#1f1f1f` with `var(--bg-sunken)` or `var(--v5-panel-2)`
4. **Verify font cascade** — currently depends on Fraunces → Georgia (serif fallback); verify intended serif font is available if --v5-serif differs from --v5-disp
