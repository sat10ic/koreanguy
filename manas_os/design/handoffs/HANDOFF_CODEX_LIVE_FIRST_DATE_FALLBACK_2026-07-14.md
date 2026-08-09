# sat10ic os — live-first market data and date fallback handoff

Date: 2026-07-14

## Outcome

The desk no longer renders blank merely because the selected calendar date has no exact scan. It resolves to the latest completed market session on or before the requested date and labels that fallback. Fresh Fyers REST snapshots are now the canonical price source during the live session; finalized `daily_prices` remains the fallback and historical source.

## Root cause verified against `data/manas.db`

- `daily_prices` extends through 2026-07-13.
- `scan_candidates` and `regime_snapshots` extend through 2026-07-10.
- The EOD job for 2026-07-12 was a Sunday run: bhavcopy was unavailable and its scanner resolved to 2026-07-10.
- The 2026-07-13 bhavcopy imports did not run the full downstream scanner/regime/debate chain.
- `live_quotes` had no rows and the Fyers provider currently reports `auth_required`.

Changing the UI to 13 or 14 July therefore requested data that did not exist at every layer. Several endpoints required exact-date matches and returned empty states even though useful prior-session data existed.

## Implemented contract

1. `GET /api/desk/run-card?date=...`, `GET /api/desk/debate?date=...`, and `GET /api/alpha/leaders?date=...` resolve the newest record whose market date is less than or equal to the requested date.
2. Responses preserve `requested_date`, the actual resolved date, and `resolved_from_previous_session` where applicable. No future data is used.
3. `POST /api/live/refresh` fetches Fyers REST snapshots, normalizes them, and writes only to `live_quotes`; it does not overwrite finalized EOD bars.
4. `GET /api/live/quotes` returns `LIVE`, `STALE`, or `EMPTY`. A quote is live only during market hours and within the freshness threshold.
5. Debate cards and the chart drawer resolve price from fresh live data first, then the latest finalized EOD close. The source state is visible as `LIVE` or `EOD FINAL`.
6. The EOD job/CLI attempts live refresh as an explicit observable stage. Missing Fyers authentication is a visible stage failure, not silent blank data.
7. Debate price resolution is bulked into one cache read plus one EOD query, avoiding one database query per card.

## Current verified runtime state

For a request dated 2026-07-14:

- Run card: available; requested 2026-07-14; resolved run card 2026-07-12; scan date 2026-07-10.
- Debate: available; 32 cards; scan date 2026-07-10.
- Card prices: `EOD_FINAL`; latest observed price date 2026-07-13 where available.
- Fyers refresh: `auth_required`; live cache state `EMPTY`.

This distinction is intentional: the UI is populated, but it does not pretend that the 10 July scan or 13 July EOD prices are live 14 July data.

## Verification

- Backend focused/regression suite: 96 passed.
- Frontend unit suite: 37 passed.
- Production desk build: passed (existing bundle-size warning only).
- Python compile check: passed.
- Browser: TODAY and DECIDE populated at `?date=2026-07-14`; relevant API requests returned HTTP 200; `EOD FINAL` was present in the rendered debate UI.
- A screenshot-viewer black-band artifact was checked by DOM computed styles and direct PNG pixel sampling; the captured page pixels use the expected light Round-4 colors.

Known test-environment warning: Python 3.14/pytest raises an ignored `PermissionError` while cleaning its Windows `pytest-current` link after the suite has already passed. Ruff is not installed in this environment.

## Operational dependency

Authenticate Fyers in the configured runtime before expecting `LIVE`. Then call `POST /api/live/refresh` or run the EOD/update pipeline. Until that succeeds, the system will correctly remain on `EOD_FINAL` and show stale-date messaging.

Running bhavcopy ingestion alone does not create a new regime, scanner, debate, or run card. A complete downstream EOD run is still required to advance those dates beyond 2026-07-10.

## Files in this wave

- `live/quotes.py`
- `live/refresh.py`
- `providers/fyers.py`
- `api/app.py`
- `alpha/services.py`
- `cli/__init__.py`
- `db/schema.sql`
- `desk/src/DebateTab.jsx`
- `desk/src/ChartDrawer.jsx`
- `desk/src/DebateTab.v5.css`
- `desk/src/App.css`
- `tests/test_live_market_data.py`
- `tests/test_fyers_provider.py`
- date-fallback assertions in the desk/alpha/run-card test modules

## Repository hygiene note

The worktree already contains a large set of overlapping Gemini/user changes and deleted study files. This wave was not committed or staged so those unrelated changes would not be captured accidentally.
