# HANDOFF INS-1 Radar backend -- COMPLETED

## Outcome

Certain: implemented the deterministic, cited `GET /api/radar` backend. It reads
the existing `post_class.symbols` JSON array, preserves exact chronological
source evidence, reports coverage debt, and returns validated co-attention only.
All day windows and strongest-cluster boundaries derive from source timestamps in
Asia/Kolkata; the derive module accepts supplied rows only, and endpoint
integration uses a disposable database.

## Attribution

Attribution-ID: attr-ins1-radar-backend-executor-exact-model-unavailable-20260825-001

Attribution-ID: attr-ins1-radar-backend-calendar-correction-executor-exact-model-unavailable-20260825-001

Attribution-ID: attr-ins1-radar-backend-orchestrator-exact-model-unavailable-20260825-001

## Files changed

- `derive/radar.py` -- pure symbol/handle normalization, calendar clustering, coverage debt, and ordering.
- `api/app.py` -- read-only `/api/radar` row selection and response wiring.
- `tests/test_radar.py` -- pure derivation and disposable-database endpoint coverage.
- `design/CONTRACTS.md` -- `/api/radar` response, Asia/Kolkata calendar-window,
  and tie-break contract.
- `design/MODEL_WORK_LOG.jsonl` -- append-only executor attribution.

## Verification

```text
pytest traderlog/tests/test_radar.py -q
7 passed in 2.97s

python -m compileall -q traderlog/derive/radar.py traderlog/api/app.py traderlog/tests/test_radar.py
exit 0

pytest traderlog/tests -q
282 passed, 2 warnings in 87.72s

python traderlog/run_checks.py
exit 0
db W0 25 tables; ingest W1 16/17 traders fresh; parse W2 3 real positions, all cited;
golden W2 5 fixtures, prompts current; attribution W0 46 records, 10 completed handoffs;
derive W4 latest 5 breadth and regime sessions match; ui W0 7 screens, dist present;
telegram W7 sending disabled in config
```

## Orchestrator verification

The orchestrator independently reran the focused suite and queried the real
read-only endpoint. The production response returned HTTP 200 with an
Asia/Kolkata window ending 2026-08-25, two ranked symbols (FCL and DATAPATTNS),
and exact archived evidence. A separate database pass verified that every ranked
symbol exists in `daily_prices`, every mention count and distinct-handle count
recomputed from evidence, every evidence field matched its `posts` row, and
every cluster spans exactly seven inclusive dates. The initial UTC/boundary
implementation was rejected and corrected before acceptance.

**Still open:** the Radar UI and its 1920x1080 browser acceptance are a separate
slice.

## Correction

- The initial executor version used UTC calendar dates and reported the earliest
  in-window mention as `strongest_cluster.start_date`. Before acceptance, this
  was corrected to Asia/Kolkata dates and the actual inclusive seven-day boundary
  (`end_date - 6`). Regression coverage includes UTC-to-IST midnight rollover
  and a sparse seven-day window.

## Risks

- Asia/Kolkata is the documented calendar anchor. An exchange-session-specific anchor would require a contract change before implementation.
- The output reports classifier/symbol coverage debt but cannot establish source-symbol precision without future source review.
