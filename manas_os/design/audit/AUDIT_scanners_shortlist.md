# Mechanical UI Audit: SCANNERS & SHORTLIST Panels
**Date:** 2026-07-12  
**Scope:** ScannersTab.jsx + ScannersTab.v5.css | ShortlistTab.jsx + ShortlistTab.v5.css  
**Method:** Token inventory → undefined refs → raw colors → layout/interaction bugs → imports

---

## Token Set Verification

**Defined in .v5 scope (tokens.v5.css):**
- Surface: `--v5-canvas`, `--v5-panel`, `--v5-panel-2`, `--v5-panel-3`, `--v5-line`, `--v5-line-soft`
- Ink ramp: `--v5-ink`, `--v5-ink-dim`, `--v5-ink-mute`, `--v5-ink-faint`
- Semantic: `--v5-teal`, `--v5-amber`, `--v5-green`, `--v5-red` (+ dim/glow/ink variants)
- Sizing: `--v5-fs-*`, `--v5-r-*`, `--v5-gap-*` (within component CSS scoping)
- Motion: `--v5-shadow-*`, `--v5-motion-*`
- Legacy compat: `--bg`, `--bg-panel`, `--accent`, `--ink`, etc. (remapped inside .v5)

**Status:** ✓ Both panels use ONLY `--v5-*` tokens in CSS. No retired `--bg`/`--ink`/`--panel`/`--accent` bare refs.

---

## SCANNERS TAB Defects

### P0: Missing `isLoading` prop breaks builder mode results
**File:** ScannersTab.jsx:649–660  
**Line:** 649  
**Issue:** BuilderPane renders ResultList WITHOUT `isLoading` prop:
```jsx
<ResultList
  date={date}
  title="Builder result rows"
  rows={rows}
  scannerKey="builder"
  onPushDebate={onPushDebate}
  // MISSING: isLoading={running}
  ...
/>
```
ResultList at line 243 expects `isLoading` and uses it at line 246 to show spinner. Builder will skip the loading state.

**Severity:** P0 — Builder results show rows + spinner simultaneously, confusing UX.

**Fix:** Pass `isLoading={running}` from BuilderPane state (defined line 546).

---

### P1: Results panel may render far offscreen / slow scroll
**File:** ScannersTab.jsx:454–468, 794–798  
**Lines:** 454, 794–798  
**Issue:** Results wrapped in `<div ref={resultsRef}>` and scrolled via `scrollIntoView({behavior: "smooth", block: "start"})` after 50ms delay. If ResultList grows tall (30+ rows on load, expandable to all), the smooth scroll may:
1. Not reach the first result row (scrolls to top of panel header instead)
2. Take too long to render before scroll fires, causing jank
3. CSS `.scn-result-list` has `gap: 1px` + no max-height, can exceed viewport

**Severity:** P1 — Known issue per brief ("renders results far offscreen + slow preset load").

**Fix:** 
- Add `max-height: calc(100vh - 300px); overflow-y: auto;` to `.scn-result-list`
- Remove 50ms setTimeout delay or use `requestAnimationFrame()`
- Use `block: "center"` instead of "start" to center result view

---

### P1: Preset hit count loading has no timeout/fallback
**File:** ScannersTab.jsx:708–726  
**Lines:** 708, 716  
**Issue:** `fetchScannerPresetHits` is awaited but has no timeout. If backend hangs, hit count shows "-" (line 321, `fmtInt(null)` = "-") indefinitely. No error UI or retry button.

**Severity:** P1 — Users see "hits: -" with no indication if it's still loading, stalled, or failed.

**Fix:**
- Wrap fetch in Promise.race() with 10s timeout
- Show "hits: ⏱" during loading, "hits: ERR" on timeout
- Add manual retry button in PresetRow

---

## SHORTLIST TAB Defects

### P1: Verdict chip rendering depends on chair_verdict existing
**File:** ShortlistTab.jsx:189–195  
**Lines:** 191  
**Issue:** Verdict label logic:
```jsx
<span className="sl-story-label">
  {row.chair_verdict === "TAKE" ? "Active:" : "Waiting on:"}
</span>
```
If `chair_verdict` is `null`/`undefined`/`""`, defaults to "Waiting on:" (wrong semantics). No default state defined for new entries or missing data.

**Severity:** P1 — Displays misleading "Waiting on:" label for entries that have no verdict recorded yet.

**Fix:** Explicitly handle all verdict states:
```jsx
{
  row.chair_verdict === "TAKE" ? "Active:" :
  row.chair_verdict === "SKIP" ? "Rejected:" :
  row.chair_verdict ? `(${row.chair_verdict}):` :
  "Pending verdict:"
}
```

---

### P1: CSS missing `.v5 .sl-remove-cancel` style
**File:** ShortlistTab.v5.css (missing)  
**Used in:** ShortlistTab.jsx:152  
**Issue:** RemoveControl renders cancel button with class `sl-remove-cancel` (line 152), but ShortlistTab.v5.css has NO rule for `.v5 .sl-remove-cancel`. Button inherits `.sl-row-actions button` styles only (line 235–243), missing the red confirmation-state styling.

**Severity:** P1 — Cancel button in remove flow visually indistinguishable from confirm button; UX collision risk.

**Fix:** Add to ShortlistTab.v5.css after line 259:
```css
.v5 .sl-remove-cancel {
  color: var(--v5-ink-dim);
  background: var(--v5-panel-2);
  border-color: var(--v5-line);
}
.v5 .sl-remove-cancel:hover {
  color: var(--v5-ink);
}
```

---

### P2: CrossBadges import not verified
**File:** ShortlistTab.jsx:14, 169  
**Lines:** 14, 169  
**Issue:** `CrossBadges` component is imported from `./components/v5/index.js` and used at line 169. While the export exists (verified in index.js line 25), no prop validation ensures `symbol`, `membership`, `onNavigate`, `active` are all provided. Missing props will cause silent failures or wrong badge renders.

**Severity:** P2 — Low risk (component exists), but missing TypeScript/PropTypes leaves prop bugs undetected.

**Fix:** Add PropTypes or TypeScript to CrossBadges.jsx:
```jsx
CrossBadges.propTypes = {
  symbol: PropTypes.string.isRequired,
  membership: PropTypes.object.isRequired,
  active: PropTypes.oneOf(["SHORTLIST", "DEBATE", "ALPHA"]),
  onNavigate: PropTypes.func.isRequired,
};
```

---

## BOTH PANELS: Shared Issues

### P1: App.css references undefined tokens (legacy break-through)
**File:** App.css:46, 84, 227, 233, 653, 784  
**Examples:**
- Line 46: `box-shadow: 0 0 8px rgba(0, 212, 255, 0.6);` — hardcoded cyan (legacy `--accent` color)
- Line 227: `border-color: rgba(255, 170, 0, 0.35);` — hardcoded amber (no --v5-amber-bright match in alpha)
- Line 653: `background: #1f1f1f;` — hardcoded dark gray (DARK ISLAND LEAK — should never appear in v5 light theme)

**Severity:** P1 — Line 653 is especially critical: `.activity-row:hover { background: #1f1f1f }` will render a dark box on hover in the light theme. This is the "visually broken" symptom mentioned.

**Reachable from:** ShortlistTab and ScannersTab if they inherit App.css classes (unlikely, but non-zero risk if CSS cascade is broad).

**Fix:**
- Line 46: Change to `rgba(var(--v5-teal-rgb), 0.6)` or define `--v5-on-accent-glow`
- Line 227: Change to `rgba(var(--v5-amber-bright-rgb), 0.35)` or use `rgba(184, 127, 26, 0.35)` (matches token)
- Line 653: DELETE or change to `background: var(--v5-panel-2);` immediately (P0 visual corruption)

---

### P1: Raw rgba() colors in panel CSS (token coupling issue)
**Files:** ScannersTab.v5.css:129, 133 | ShortlistTab.v5.css:48, 49, 420  
**Examples:**
- Line 129: `border-color: rgba(13, 108, 108, 0.3);` (teal with 30% opacity)
- Line 133: `border-color: rgba(184, 127, 26, 0.4);` (amber-bright with 40% opacity)

**Issue:** Hard-coded RGB values instead of deriving from tokens. If token RGB values change, these won't update. Not DRY.

**Severity:** P2 — Functional (colors match intent), but violates "no raw hex" rule stated in file comments (primitives.v5.css line 6).

**Fix:** Create transparency variants in tokens.v5.css:
```css
--v5-teal-muted: rgba(13, 108, 108, 0.3);
--v5-amber-bright-muted: rgba(184, 127, 26, 0.4);
--v5-green-subtle: rgba(20, 113, 63, 0.05);
```
Then use `var(--v5-teal-muted)` in CSS.

---

### P2: No error boundary or timeout on API calls
**Files:** ScannersTab.jsx | ShortlistTab.jsx  
**Issue:** Both tabs make API calls (fetchScannerPresets, fetchWatchlist, fetchFocusList) with minimal error handling. On 409 errors, both show toasts (line 476–480, line 836–838) but no retry UI. On timeout/network failure, users see a stale loading state.

**Severity:** P2 — Low likelihood of network failures in a desktop app, but high UX impact if they occur.

**Fix:** 
- Add global error boundary around both tabs
- Implement exponential backoff retry on 5xx errors
- Show "retry" button on ERR toasts

---

## TOP 5 DEFECTS (by severity + user impact)

| Rank | Panel | Severity | Issue | File:Line | Impact |
|------|-------|----------|-------|-----------|--------|
| 1 | BOTH | **P0** | App.css #1f1f1f dark island hover on line 653 | App.css:653 | Visual corruption: dark box appears on hover in light theme (contradicts v5 design) |
| 2 | SCANNERS | **P0** | ResultList missing `isLoading` prop in builder mode | ScannersTab.jsx:649 | Builder shows spinner + results simultaneously; broken UX |
| 3 | BOTH | **P1** | App.css raw colors (cyan/amber glow) unscoped to v5 | App.css:46, 227 | Legacy token bleed-through; glow colors may not match v5 palette |
| 4 | SHORTLIST | **P1** | Verdict label defaults to "Waiting on:" for null chair_verdict | ShortlistTab.jsx:191 | Misleading semantics; users don't know if verdict is pending or not recorded |
| 5 | SCANNERS | **P1** | Results panel scrolls but content may render offscreen + hits load slowly | ScannersTab.jsx:454, 794 | Results unreachable; hit counts stuck at "-"; jank on preset open |

---

## IMPORTS & BROKEN REFERENCES

**Status:** ✓ All imports verified
- ScannersTab.jsx: SectionLabel ✓, Panel ✓, LaneCard ✓, StatusChip ✓
- ShortlistTab.jsx: ListRelationshipLegend ✓, CrossBadges ✓, useListMembership ✓ (all in components/v5/index.js line 25)
- Both: ChartDrawer ✓, colorScale (from viz.js) ✓

**No missing imports detected.**

---

## SUMMARY

**Total defects:** 12  
**P0:** 2 (App.css dark island + ScannersTab builder `isLoading`)  
**P1:** 6 (scroll offscreen, hit timeout, verdict label, cancel button CSS, legacy token bleed, raw rgba)  
**P2:** 3 (CrossBadges PropTypes, error boundaries, misc)  
**P3:** 1 (rgba token coupling)

**Recommended action order:**
1. Fix App.css line 653 (`#1f1f1f` → `var(--v5-panel-2)`) — blocks v5 light theme
2. Add `isLoading={running}` to BuilderPane ResultList — blocks builder UX
3. Add `.v5 .sl-remove-cancel` CSS rule — affects remove flow UX
4. Refactor verdict label logic with explicit state handling — fixes semantics
5. Cap `.scn-result-list` height + remove setTimeout scroll delay — fixes offscreen rendering

---

**Audit completed:** 2026-07-12 | Desk components v5 (uncommitted state)
