# Codex handoff — UI-2 Live Work (2026-07-11)

## Outcome

UI-2 is complete on branch `emergent`. The desk now creates a durable job before work begins,
then shows that work in a Round-4-conformant Live Work inspector without page refreshes.

The next build slice is **UI-3: MARKET recomposition**, using the completed Live Work strip and
inspector rather than reintroducing legacy pipeline polling.

## User-locked visual constraint

Round-4 is the visual authority. This is **not** a new design exercise. Every later UI slice
must follow:

- `design/bakeoff/round4/debate_merged_light.html`
- `design/UI_BUILD_DIRECTION.md`
- the explicit UI-2 reminder in `design/UI2_LIVEWORK_DIRECTION.md`

Do not introduce another palette/type system or a generic dashboard-card treatment.

## Delivered commits

| Commit | Scope |
|---|---|
| `50b06561` | UI-2a: `jobs`, steps, events and artifacts tables; sacrificial emitter; shared API/CLI runner; polling endpoints. |
| `33d04ffe` | UI-2b: SSE replay, cursor handling, heartbeat/done semantics, orphan recovery, cooperative cancel, append-only retry. |
| `ec404071` | UI-2c: immediate job reservation/ID, live frontend stream/reducer, Round-4 Live Work inspector, MARKET strip/summary. |

## Working contract

- `POST /api/jobs` returns a reserved `job_id` immediately.
- `GET /api/jobs`, `GET /api/jobs/{id}`, `GET /api/jobs/{id}/events`, and
  `GET /api/jobs/{id}/events/stream` serve the durable rail.
- SSE resumes by cursor/`Last-Event-ID`; the browser falls back to polling and deduplicates by
  event ID.
- Cancel is cooperative between stages. Retry appends `attempt + 1`; it never rewrites prior
  step evidence.
- `/api/pipeline/status`, risk/money math and stage function signatures remain compatibility
  surfaces and must not be changed by UI work.

## Main implementation files

- Backend: `jobs.py`, `api/app.py`, `db/schema.sql`, `cli/__init__.py`
- Frontend stream: `desk/src/livework/useJobStream.js`
- Inspector: `desk/src/livework/LiveWorkInspector.jsx`, `livework.v5.css`
- Stage UI: `desk/src/components/v5/StageRail.jsx`, `StepRow.jsx`
- Integration: `desk/src/App.jsx`, `desk/src/MarketHomeTab.jsx`, `desk/src/api.js`
- Tests: `tests/test_jobs_schema.py`, `test_jobs_runner.py`, `test_jobs_sse.py`,
  `desk/src/livework/useJobStream.test.js`

## Verified evidence

- Backend jobs suite: 13 passed.
- Desk Vitest suite: 37 passed across 6 files.
- Production desk build passed; only the existing Vite >500 kB chunk advisory appeared.
- Browser rendered against the restarted current API at 1470x900 and 390x844.
- A real run was started from the desk: `fetch_bhavcopy` finished in 12.296s, then
  `fetch_chartsmaze` started; the inspector streamed both events and the main MARKET data stayed
  visible.
- The only browser-console error was the existing missing `/favicon.ico` 404.

## Current live state (check before acting)

At this handoff, job `1` (`run-eod`, run date `2026-07-10`) is still `running` in
`fetch_chartsmaze`. A cooperative cancellation was requested at event `5`; it will take effect
after that current source stage returns. Confirm with:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/jobs/1/events?after=0
```

Do not kill or restart the API merely to force cancellation: that would turn an intentional
cooperative-cancel verification into an interrupted job.

## UI-3 starting point

1. Read the three locked visual files above plus `UI_OVERHAUL_HANDOFF.md` section 11.
2. Keep `LiveWorkProvider` mounted in `App.jsx`; consume `LiveWorkStrip` and
   `LiveWorkInspector`, do not add polling state back to MARKET.
3. Recompose `MarketHomeTab.jsx` around real `/api/desk/market` and run-card fields only.
   Preserve beginner/expert density, data freshness and manual-decision language.
4. Verify source values against API payloads, then run Vitest/build and real responsive browser
   checks. Do not use fake zeroes, synthetic signals or broker-routing language.

## Worktree hygiene

The worktree contains unrelated modified/untracked material, including `LedgerTab.jsx`,
`PositionsTab.jsx`, `run_cards/2026-07-09.json`, other design handoffs/bakeoff artifacts and
`output/playwright/`. Preserve them. Stage only explicit files for a UI-3 commit.
