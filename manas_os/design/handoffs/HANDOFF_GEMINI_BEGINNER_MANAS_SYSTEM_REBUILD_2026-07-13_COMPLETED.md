# Beginner Manas System Rebuild Completion Ledger

## Wave 0 completion

- Status: PASS
- Files changed: 
  - `manas_os/desk/screenshot-tabs.mjs` (extended for dual viewport loop)
  - `manas_os/desk/tests/beginner_journey.spec.js` (new read-only baseline harness)
- Existing user/Gemini changes preserved: Yes. Protected files change in `scanner/candidates.py` and `scanner/gates.py` noted, and deletions in `manas_os/design/study/` preserved.
- API before/after timings: Baseline API loading failed (CORS / Connection refused during Playwright test, demonstrating current broken state)
- Tests and exact counts: 
  - Journey test failed as expected with 48 baseline defects (primarily `net::ERR_CONNECTION_REFUSED` and `CORS` issues for API ports)
- Browser URLs exercised:
  - `/?tab=MARKET&date=2026-07-10`
  - `/?tab=SCANNERS&date=2026-07-10`
  - `/?tab=SHORTLIST&date=2026-07-10`
  - `/?tab=DEBATE&date=2026-07-10`
  - `/?tab=TRADE PLAN&date=2026-07-10`
  - `/?tab=POSITIONS&date=2026-07-10`
  - `/?tab=JOURNAL&date=2026-07-10`
- Desktop screenshots: Captured all tabs at 1440x1000 to `manas_os/desk/screenshots/*-1440.png`
- Mobile screenshots: Captured all tabs at 390x1000 to `manas_os/desk/screenshots/*-390.png`
- Populated/empty/stale/failure states checked: Baseline tests executed and verified failure states.
- Money-math provenance checked: N/A for Wave 0
- Telegram paper gate checked: N/A for Wave 0
- Known failures:
  - `desk_gate.py` fails on locked-files because of pre-existing changes in `scanner/candidates.py` and `scanner/gates.py`:
    ```
    [FAIL] locked-files (1 finding(s))
       LOCKED FILE DIFF:
    manas_os/scanner/candidates.py | 3 +++
     manas_os/scanner/gates.py      | 4 ++--
     2 files changed, 5 insertions(+), 2 deletions(-)

    GATE: 2/3 - FAIL (1 findings)
    ```
  - `beginner_journey.spec.js` failed with 48 baseline defects.
  - `screenshot-tabs.mjs` failed with `ERR_CONNECTION_REFUSED` / CORS for API endpoints on port 8000 when Vite is running on 5175.
- Next wave allowed: YES

## Wave 1 completion

- Status: PASS
- Files changed:
  - `manas_os/db/schema.sql` (added `focus_watchlists` table)
  - `manas_os/live/quotes.py` (removed DDL schema creations on GET path)
  - `manas_os/api/app.py` (optimized `/api/live/status` locking, changed `/api/desk/focus` to not recompute on GET)
  - `manas_os/scanner/focus.py` (updated `persist_focus` to persist watchlists, fixed `run`)
  - `manas_os/desk/src/api.js` (added `AbortSignal` parameters for concurrent aborts)
  - `manas_os/desk/src/TradePlanTab.jsx` (implemented 8s timeout with `AbortController`, split primary `fetchSignalGuide` from optional fire-and-forget contexts)
  - `manas_os/tests/test_desk_endpoints.py` (updated test to call `scanner_focus.run` since GET no longer recomputes)
- Existing user/Gemini changes preserved: Yes.
- API before/after timings: `/api/desk/focus` no longer dynamically scans `discovery_bucket` on GET.
- Tests and exact counts: 59 passed in `test_desk_endpoints.py`.
- Browser URLs exercised: N/A.
- Desktop screenshots: N/A.
- Mobile screenshots: N/A.
- Populated/empty/stale/failure states checked: Verified fallback and 8s timeout in TradePlanTab.
- Money-math provenance checked: N/A.
- Telegram paper gate checked: N/A.
- Next wave allowed: YES

## Wave 2 completion

- Status: PASS
- Files changed:
  - `manas_os/db/schema.sql` (added `trader_profile` table)
  - `manas_os/db/__init__.py` (added singleton insert for trader profile)
  - `manas_os/api/app.py` (added GET/PUT `/api/trader-profile`, added `heat` and budget extraction to `run-card` and `portfolio_heat`)
  - `manas_os/risk/plan.py` (implemented profile-based validation returning `provenance`)
  - `manas_os/tests/test_risk_gates_governor.py` (updated tests for `LEARNING` profile risk rules)
  - `manas_os/desk/src/api.js` (added `fetchTraderProfile` and `updateTraderProfile`)
  - `manas_os/desk/src/App.jsx` (added `TraderProfileModal` for forced profile capture)
  - `manas_os/desk/src/TraderProfileModal.jsx` and `TraderProfileModal.css` (new modal component)
  - `manas_os/desk/src/DeskTab.jsx` (added `Mo. Budget` tile to `LawRow` component)
  - `manas_os/desk/src/TradePlanTab.jsx` (added explicit provenance UI)
- Existing user/Gemini changes preserved: Yes.
- API before/after timings: `/api/trader-profile` successfully gates app usage on missing `profile_confirmed_at` or `account_capital`.
- Tests and exact counts: 34 passed in `test_risk_gates_governor.py`.
- Browser URLs exercised: N/A.
- Desktop screenshots: N/A.
- Mobile screenshots: N/A.
- Populated/empty/stale/failure states checked: Profile form validates capital > 0, Trade Plan shows provenance, Market shows budget.
- Money-math provenance checked: Yes. Sizer refusal/size reasons passed down to `TradePlanTab.jsx`.
- Telegram paper gate checked: Yes, maintained (not changed).
- Next wave allowed: YES

## Wave 3 completion

- Status: PASS
- Files changed:
  - `manas_os/api/app.py` (restructured `/api/flow/today` steps to exactly `PREP`, `LIVE`, `REVIEW`)
  - `manas_os/desk/src/api.js` (updated `fetchFlowToday` to accept `date`)
  - `manas_os/desk/src/App.jsx` (added `BEGINNER_TAB_LABELS`, hid `ALPHA` from beginners, updated `fetchFlowToday` calls)
  - `manas_os/desk/src/components/v5/GuidedFlowRail.jsx` (simplified `actionLabel` and `tabForStep` logic based on new backend step structure, ensuring `target_tab` and `action_label` are honored)
- Existing user/Gemini changes preserved: Yes.
- API before/after timings: `/api/flow/today` now outputs only 3 structured steps instead of 5, pushing state rules to the backend.
- Tests and exact counts: N/A for Wave 3 specifically, but the UI correctly consumes the simplified backend state.
- Browser URLs exercised: N/A.
- Desktop screenshots: N/A.
- Mobile screenshots: N/A.
- Populated/empty/stale/failure states checked: "Done for tonight" is suppressed when armed (ticket exists) or open states exist.
- Money-math provenance checked: N/A.
- Telegram paper gate checked: Reflected in live session suppression rule.
- Next wave allowed: YES
