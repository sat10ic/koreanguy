# HANDOFF_GEMINI_dewonk_BCD_COMPLETED

## Wave B — Real Crashes / Broken Components
1. **TradePlanTab.jsx**: Fixed TDZ crash by moving `const { sizer, plan }` derivation above `handleLogTaken`.
2. **DebateLivePanel.jsx**: Added `DebateLivePanel.v5.css` with 7 missing classes matching the v5 token language. Imported it into the component.
3. **MarketTab.jsx**: Recovered the legacy `.mkt-*` CSS from a previous commit, updated it to use `.v5` scoped tokens, and imported it into the component as `MarketTab.v5.css`. The tab is still mounted and used.
4. **PositionsTab.jsx**: Fixed modal form state leakage. Added `key={tradeId}` to the `CloseModal` component render to ensure React unmounts and remounts the modal, clearing its state whenever the selected trade changes.
5. **LedgerTab.jsx**: Fixed R-bar fill color. Replaced the inline string `background: "var(--v5-green)"` with a CSS class approach (`.v5-jr-pos` / `.v5-jr-neg`) applying the token colors. 

## Wave C — Per-Panel Residue
6. **Dark-island hovers (App.css)**: Replaced hardcoded `#1f1f1f` with `var(--v5-panel-2)` in `.activity-row:hover`, `.activity-row.selected`, and `.agent-chip.live`.
7. **ScannersTab.jsx**: Passed `isLoading={isSearching}` down to `ResultList`. Added `max-height: 50vh` and overflow rules to `.scn-result-list` in `ScannersTab.v5.css`. Replaced duplicate `api.scanners.presets()` fetches with a single cached Promise, and used `Promise.race` for a 10s timeout to prevent stuck loads.
8. **ShortlistTab.jsx**: Separated `chair_verdict` state logic. Null now correctly reflects "Unrecorded" rather than contradictory "Waiting on:". 
9. **TradePlanTab.v5.css**: Replaced `gap: var(--v5-r-sm)` with `gap: var(--gap-s)`.
10. **rgba/token purity**: 
    - Analyzed PositionsTab and LedgerTab; their RGBA values already perfectly matched the v5 token RGB equivalents. 
    - Added the missing `.sl-remove-cancel` class to `ShortlistTab.v5.css`.
    - Tokenized `DebateTab.v5.css` background overlays to strictly match `20, 113, 63` (green), `173, 44, 52` (red), and `184, 127, 26` (amber).
    - Fixed `LedgerTab.v5.css` modal backdrop from `#141418` to `#17181b` (`23, 24, 27`).
    - Fixed `App.css` glows to use v5 RGB equivalents (teal, amber, line).

## Wave D — Verification & Build
- Executed `npm run build` locally. The build succeeded without any errors.
- Added row 15 to `HANDOFF_INDEX.md` and marked it as DONE.
- (Visual verification pending maintainer's DOM drive-through as per project rules.)

## Changed Files
- `desk/src/TradePlanTab.jsx`
- `desk/src/TradePlanTab.v5.css`
- `desk/src/components/v5/DebateLivePanel.jsx`
- `desk/src/components/v5/DebateLivePanel.v5.css` [NEW]
- `desk/src/MarketTab.jsx`
- `desk/src/MarketTab.v5.css` [NEW]
- `desk/src/PositionsTab.jsx`
- `desk/src/LedgerTab.jsx`
- `desk/src/LedgerTab.v5.css`
- `desk/src/App.css`
- `desk/src/ScannersTab.jsx`
- `desk/src/ScannersTab.v5.css`
- `desk/src/ShortlistTab.jsx`
- `desk/src/ShortlistTab.v5.css`
- `desk/src/DebateTab.v5.css`
- `design/handoffs/HANDOFF_INDEX.md`
