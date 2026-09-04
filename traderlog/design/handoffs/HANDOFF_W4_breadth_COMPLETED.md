# HANDOFF W4 breadth + XP/MBI -- COMPLETED

## Outcome

W4 adopted the daily bhavcopy, raw breadth, NIFTYMIDSML400 breadth, XP, and MBI
pipeline. It rejects an internal bhavcopy `DATE1` mismatch before prices persist,
requires 85% actual-date constituent coverage (340/400), fails fast at upstream
stage boundaries, and makes `derive` require exact five-date breadth/regime parity
and non-null XP/MBI outputs. The dormant breadth-ratio/HL analytics module was
removed because it has no named API or UI consumer. BandLine now renders and
announces finite numeric latest values to one decimal.

## Attribution

Attribution-ID: attr-w4-breadth-terra-executor-20260823-001

Attribution-ID: attr-w4-breadth-gpt5-orchestrator-20260823-001

Attribution-ID: attr-w4-breadth-gpt5-reviewer-20260823-001

## Files changed

- `adopted/bhavcopy.py` -- reject a requested-date/internal-`DATE1` mismatch before upsert.
- `adopted/universe_breadth.py` -- enforce 85% coverage; fail configured 0-coverage dates and skip only absent configuration.
- `checks/runner.py` -- require five-date breadth/regime parity and non-null XP/MBI derive fields.
- `run_w4.py` -- stop dependent stages after bhavcopy, breadth-count, or universe-breadth failures.
- `adopted/breadth_analytics.py` and `tests/test_adopted_breadth_analytics.py` -- removed dormant analytics.
- `tests/test_adopted_bhavcopy.py`, `tests/test_adopted_universe_breadth.py`, `tests/test_check_derive.py`, `tests/test_run_w4.py` -- regression coverage for the integrity boundaries.
- `ui/src/components/charts.jsx` -- display and announce finite BandLine latest values to one decimal.
- `CANONICAL.md`, `TASKS.md`, `HANDOFF.md`, `design/handoffs/HANDOFF_SESSION_CONTINUE_2026-08-23.md`, and `design/MODEL_WORK_LOG.jsonl` -- W4 decision, state, and attribution records.

## Verification

```text
pytest traderlog/tests/test_adopted_bhavcopy.py traderlog/tests/test_adopted_breadth_counts.py traderlog/tests/test_adopted_universe_breadth.py traderlog/tests/test_adopted_xp_mbi.py traderlog/tests/test_adopted_regime_daily.py traderlog/tests/test_check_derive.py traderlog/tests/test_run_w4.py -q
56 passed in 6.17s

pytest traderlog/tests -q
231 passed, 2 warnings in 56.76s

npm run build (traderlog/ui)
✓ 43 modules transformed.
✓ built in 3.77s

python traderlog/run_checks.py
derive WARN: latest regime_daily session is 9d old; no failures.
```

## Honest partials

- This executor did not run production DB/API/Chrome acceptance. Root separately
  verified real (non-mock) API/DB data in Chrome at 1920×1080: document width
  1920, zero panel overflows, no long decimals, and aria label `Trend: 90 points,
  latest 7.3 (low).`
- Root orchestrator/reviewer attribution records are pending separate append-only
  entries. No production ingestion, LLM call, or commit was performed here.
