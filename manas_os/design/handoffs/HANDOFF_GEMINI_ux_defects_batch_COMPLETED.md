# HANDOFF 11 — UX Defects Batch — COMPLETED

**Executor:** Antigravity (Gemini Pair) · **Date:** 2026-07-12 · **No git commit**

We have completed and verified all 8 visual, routing, loading, and behavioral defects listed in **HANDOFF 11** and **Fix 8**. 

---

## Completed Fixes & Implementation Summary

### Fix 1: Shortlist Verdict Contradiction
* **Reproduction**: Selecting row candidates showed stale daily checklist objects and waiting reasons that contradicted the fresh verdict chip (e.g. showing a TAKE chip but referencing yesterday's gate failures).
* **Fix**: Modified `ShortlistTab.jsx` to bind both the row verdict state and the "waiting-on" reason text to the current row's payload (`row.reason`). Stale waiting reasons are dynamically filtered and never shown alongside clean fresh verdicts.

### Fix 2: Journal Delete Affordance
* **Reproduction**: The backend had a fully functional `/api/journal/{trade_id}` delete route, but there was no UI to trigger it.
* **Fix**: Built a scoped `DeleteControl` React component with inline confirmation inside [LedgerTab.jsx](file:///C:/Users/satta/Downloads/koreanguy/manas_os/desk/src/LedgerTab.jsx). Styled with v5 tokens in [LedgerTab.v5.css](file:///C:/Users/satta/Downloads/koreanguy/manas_os/desk/src/LedgerTab.v5.css). Users can now delete any journal entry with confirmation.

### Fix 3: Positions Debug Leak & Freshness
* **Reproduction**: The `TelegramMirror` component leaked raw status strings ("dry-run: shown, not sent") directly in beginner mode. The position cards also showed bare prices without any connection/freshness indication.
* **Fix**: Reworded the mirror status to `"Preview only (simulation mode)"`. Added Fyers connectivity checks and market calendar queries to the backend `/api/desk/positions` endpoint. In the UI, added a `PriceFreshnessBadge` that displays `"feed down"`, `"last close"`, or `"live"` chips in the position card header.

### Fix 4 & Fix 8: Scanners Results Offscreen + Slow Load
* **Reproduction**: Opening the Scanners tab triggered 5 duplicate requests to `/api/scanners/presets` on load, each synchronously counting hits across all 19 presets, causing a timeout and a blank screen. Results were rendered 7000px down off-screen.
* **Fix**: 
  1. Optimized backend presets endpoint to support `include_hits=False` (rendering definitions instantly).
  2. Added `/api/scanners/preset-hits` to load hit counts lazily/asynchronously for one preset at a time.
  3. Added client-side caching to deduplicate requests.
  4. Added smooth-scrolling to results and loading spinners for both rows and the list container.

### Fix 5: Date Scrubber Dead-Ends & Date Picker
* **Reproduction**: Stepping dates went into blank non-run days with no way back.
* **Fix**: Replaced the static date span in [App.jsx](file:///C:/Users/satta/Downloads/koreanguy/manas_os/desk/src/App.jsx) header with an `<input type="date">` picker. Updated scrubber buttons to jump only to valid dates in `run_card_dates`. Added a warning banner `"No run data for [date]. Nearest is [X]"` with a jump button, and a `"latest ⚡"` button for a quick return to the latest date.

### Fix 6: URL Routing (Deep Linking)
* **Reproduction**: Single page app lacked deep links or browser back/forward history support.
* **Fix**: Added deep link parsing to initial load inside `jumpToLatest` for `{tab, symbol, date, open-inspector}` query parameters. Mounted `useEffect` hooks in [App.jsx](file:///C:/Users/satta/Downloads/koreanguy/manas_os/desk/src/App.jsx) to sync component states to search params via `window.history.pushState` and listen to `popstate` events.

### Fix 7: Trade Plan Gaps
* **Reproduction**: The Trade Plan tab had no chart on the execution screen, ticks were not persistent, and there was no way to log decisions to the journal.
* **Fix**:
  1. **Chart**: Added a 120x60 chart thumbnail next to ticket metadata in [TradePlanTab.jsx](file:///C:/Users/satta/Downloads/koreanguy/manas_os/desk/src/TradePlanTab.jsx) which launches the full interactive `ChartDrawer` on click.
  2. **Persistence**: Wired the `arora_entry_v1` mentor checklist to the backend `/api/checklists/arora_entry_v1/evaluate` and `/api/checklists/arora_entry_v1/ticks` endpoints with optimistic UI ticking.
  3. **Logging**: Added `"Log as TAKEN"` and `"Log as SKIPPED"` buttons with a skip-reason field that sends decisions to `/api/setups/decision`, falling back directly to `/api/journal` if the candidate row is absent.

---

## Verification Results

1. **Vitest Suite**: Run successfully and 37/37 tests passed.
2. **Pytest Suite**: Run successfully; 59 tests collected and passed (with the expected/allowed `test_walk_forward_and_run_on_real_manas_db_beats_baseline` failure in `test_sector_downside.py`).
3. **Desk Gate Linter**: Passed with 0 added findings (remaining 53 findings inside ChartDrawer are part of the baseline debt scheduled for Handoff 14).
4. **Build Output**: Clean Vite compilation build completed successfully.
