# Mechanical UI Defect Audit: DEBATE & TRADE PLAN Panels
**Date:** 2026-07-12  
**Scope:** DebateTab.jsx, DebateTab.v5.css, TradePlanTab.jsx, TradePlanTab.v5.css, DebateLivePanel.jsx  
**Status:** Read-only audit (no fixes applied)

---

## Executive Summary

**Critical defects found: 5 (P0: 2, P1: 3)**

The DEBATE panel's live-stream component (`DebateLivePanel.jsx`) references 7 undefined CSS classes, causing layout collapse. The TRADE PLAN panel has a broken variable reference at runtime. Both panels reference undefined color tokens. One CSS rule uses a radius token for spacing.

---

## Defect List (Severity Order)

### P0 — Breaks Rendering / Runtime Error

#### 1. **DebateLivePanel.jsx: Missing CSS classes break layout**
- **File:** `manas_os/desk/src/components/v5/DebateLivePanel.jsx`
- **Lines:** 48, 62, 64, 68, 75, 81, 107, 112
- **Issue:** Component references 7 CSS classes NOT defined in any stylesheet:
  - Line 48, 112: `.v5-live-dot` — animated status dot (no style)
  - Line 62: `.v5-live-kicker` — "LIVE DEBATE ON-DEMAND" label (no style)
  - Line 64: `.alpha-explain` — legacy class name, no v5 replacement
  - Line 68: `.v5-debate-live-status` — status badge container (no style)
  - Line 75: `.v5-debate-live-stages` — progress stepper section (no style)
  - Line 81: `.v5-debate-live-seats` — council grid section (no style)
  - Line 107: `.v5-seat-body` — seat card content area (no style)
- **Expected:** All classes should be defined in `DebateTab.v5.css` (parent imports it)
- **Impact:** Live panel layout collapses; seats/stages/status render unstyled
- **Severity:** P0 — user sees broken UI

#### 2. **TradePlanTab.jsx line 462: Undefined variables `sizer` and `plan`**
- **File:** `manas_os/desk/src/TradePlanTab.jsx`
- **Line:** 462
- **Issue:** 
  ```javascript
  const qtyValue = sizer ? sizer.final_qty : plan ? plan.suggested_qty : 0;
  ```
  Variables `sizer` and `plan` are NOT in scope. They are defined later at lines 555–556:
  ```javascript
  const plan = guide.plan;
  const sizer = guide.sizer;
  ```
  The `handleLogTaken()` function (lines 458–496) references them before they're declared.
- **Expected:** Refactor `handleLogTaken()` to accept `guide` or restructure to use closure vars
- **Impact:** TypeError at runtime when user clicks "Log Trade / Taken"; trade logging fails
- **Severity:** P0 — user-facing crash

---

### P1 — Visual Defects / Invalid Tokens

#### 3. **DebateTab.v5.css: Undefined color tokens `--v5-red-ink` and `--v5-green-ink`**
- **File:** `manas_os/desk/src/DebateTab.v5.css`
- **Lines:** 829, 833, 837, 857
- **Issue:** Four CSS rules reference tokens NOT defined in `tokens.v5.css`:
  - Line 829: `.v5-seat-badge--take { color: var(--v5-green-ink); }` — no such token
  - Line 833: `.v5-seat-badge--skip { color: var(--v5-red-ink); }` — no such token
  - Line 837: `.v5-seat-badge--fail { color: var(--v5-red-ink); }` — no such token
  - Line 857: `.v5-seat-error-note { color: var(--v5-red-ink); }` — no such token
  
  **Defined tokens for comparison:**
  - `--v5-red`: `#ad2c34` (line 37 tokens.v5.css)
  - `--v5-green`: `#14713f` (line 35 tokens.v5.css)
  - `--v5-teal-ink`: `#0a5555` (line 29 tokens.v5.css) ← only `*-ink` that exists
- **Expected:** Replace with `--v5-red` and `--v5-green` (no `-ink` suffix) OR add missing token definitions to tokens.v5.css
- **Impact:** Browser ignores invalid var() → fallback to inherited color (likely wrong)
- **Severity:** P1 — badge text color renders incorrectly

#### 4. **DebateTab.v5.css: Raw hex colors in rgba() wrappers (outside token palette)**
- **File:** `manas_os/desk/src/DebateTab.v5.css`
- **Lines:** 797, 801, 805
- **Issue:** Three CSS rules embed raw hex values inside rgba(), violating the token-only rule:
  - Line 797: `.v5-seat-card--done { background: rgba(16, 185, 129, 0.02); }` — green (#10b981)
  - Line 801: `.v5-seat-card--failed { background: rgba(239, 68, 68, 0.02); }` — red (#ef4444)
  - Line 805: `.v5-seat-card--pending { background: rgba(245, 158, 11, 0.02); }` — amber (#f59e0b)
  
  **Per design spec** (tokens.v5.css line 6): "Every color/type value resolves through a --v5-* token … the only exception is inside rgba() wrappers **of a token value** for translucency."
  
  These are raw Tailwind-style colors, not based on any defined token (e.g., `rgba(var(--v5-green), 0.02)` would be valid).
- **Expected:** Either use `rgba(var(--v5-green), 0.02)` or define palette colors as tokens first
- **Impact:** Colors are undocumented and inconsistent with the locked palette; drift risk if design changes
- **Severity:** P1 — design system violation; semantic colors leak

#### 5. **TradePlanTab.v5.css line 347: Wrong token type for `gap`**
- **File:** `manas_os/desk/src/TradePlanTab.v5.css`
- **Line:** 347
- **Issue:**
  ```css
  .v5-tp-mentor-select-row {
    gap: var(--v5-r-sm);
  }
  ```
  Uses `--v5-r-sm` (radius: 5px) as a gap value. Should be a spacing token. The rule is in a flex layout, so gap controls spacing between items.
- **Expected:** Use actual spacing (e.g., `gap: 10px;` or reference a spacing token if one existed)
- **Impact:** Gap is 5px (radius), likely too tight; visual spacing broken
- **Severity:** P1 — layout defect; awkward spacing in mentor checklist row

---

## Summary Table (Top 5 by Severity)

| Rank | File | Line(s) | Issue | Type | Severity |
|------|------|---------|-------|------|----------|
| 1 | DebateLivePanel.jsx | 48, 62, 64, 68, 75, 81, 107, 112 | 7 undefined CSS classes | Missing style | P0 |
| 2 | TradePlanTab.jsx | 462 | `sizer`, `plan` undefined in scope | Runtime error | P0 |
| 3 | DebateTab.v5.css | 829, 833, 837, 857 | `--v5-red-ink` / `--v5-green-ink` undefined | Bad token ref | P1 |
| 4 | DebateTab.v5.css | 797, 801, 805 | Raw hex in rgba() (not from palette) | Design system | P1 |
| 5 | TradePlanTab.v5.css | 347 | `gap: var(--v5-r-sm)` (radius used as spacing) | Wrong token type | P1 |

---

## Handoff Notes

**Live-stream UI component** (`DebateLivePanel.jsx`) is new/incomplete; CSS classes are referenced but never created. The parent component (`DebateTab.jsx`) imports the stylesheet, so all missing classes should be added to `DebateTab.v5.css`.

**Trade Plan trade logging** (`TradePlanTab.jsx::handleLogTaken`) references variables out of scope. Refactor needed to expose `guide` to the handler or move variable declarations.

**Color token inconsistency**: The only `-ink` tokens defined are `--v5-teal-ink` (line 29) and `--v5-amber-ink`. Red/green don't have `-ink` variants in the palette; this may be a naming error from porting old code.

---

## Verification

- **Token definitions scanned:** `styles/tokens.v5.css`, `components/v5/primitives.v5.css`, `App.css`
- **Files audited:** 5 (DebateTab.jsx/css, TradePlanTab.jsx/css, DebateLivePanel.jsx)
- **Lines checked:** ~1,900 total
- **Imports verified:** All imports resolve correctly except CSS class references
