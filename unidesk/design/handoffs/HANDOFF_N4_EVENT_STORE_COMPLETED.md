# HANDOFF N4 parquet event store + outcome attach — COMPLETED (this slice)

Date: 2026-08-29.

Attribution-ID: attr-unidesk-n4-event-store-grok46-20260829-001

## Outcome

N3 official CA-with-ratios is still not on disk (`manas.db` has no ratio
table). Built the unblocked N4 remainder:

- Parquet event store: `data/market/research/events/date=YYYY-MM-DD/events.parquet`.
  Freeze includes INVALID / INSUFFICIENT_DATA. Same-day rewrite, not a
  mixed-hash append. Nested snapshot/outcomes stored as JSON strings.
- Nightly freezes the scan into that store after the report.
- `attach_outcomes` labels from bars **strictly after** the decision
  session (next open = fill). Missing future or ATR → `UNRESOLVED`, never
  a zeroed outcome. Original freeze events stay unlabeled.

## Files

- `unidesk/research/event_store.py` (new)
- `unidesk/research/candidates.py` (`future_after`, `attach_outcomes`)
- `unidesk/momentum/nightly.py`
- `unidesk/tests/test_n4_research_spine.py`
- `plan/UNIFIED_DESK_BUILD_MANUAL_V2.md`
- `plan/PHASE0_DATA_BUILD_SPEC.md`
- `plan/UNIFIED_DESK_INTEGRATION_PLAN.md`
- `unidesk/TASKS.md`, `GOAL.md`, `CANONICAL.md`, `HANDOFF.md`,
  `unidesk/design/PHASE0_GAP.md`

## Verification

```text
.venv-orderflow/Scripts/python.exe -m pytest unidesk/tests/test_n4_research_spine.py unidesk/tests/test_nightly_scan_report.py -q
→ 15 passed
```

## Honest partials

- Outcomes are not attached across the 1M-bar archive this slice (helper
  exists; the run is not).
- 4y/1y folds still refuse on the short calendar.
- Ablation ladder not started.
- Official NSE CA-with-ratios still open; `daily_prices` not adopted.
- Predictive AI still forbidden.
