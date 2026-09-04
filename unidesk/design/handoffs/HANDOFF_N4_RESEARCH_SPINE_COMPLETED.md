# HANDOFF N4 research spine — COMPLETED (first slice)

Date: 2026-08-29.

Attribution-ID: attr-unidesk-n4-research-spine-grok46-20260829-001

## Outcome

N3 remainder needed official files that are not in the repo (2016–2024-08
bhavcopy, index/VIX, PIT membership, CA-with-ratios). A current Nifty
Midcap/Smallcap constituent CSV exists under `traderlog/data/` — it was
**not** used (D14.5: today's list is not historical membership).

Built the unblocked N4 slice:

- `unidesk/research/candidates.py` — freeze every symbol's detector
  decisions as `ResearchEvent`, including INVALID / INSUFFICIENT_DATA.
- `unidesk/research/walkforward.py` — expanding folds, 5-session embargo,
  next-bar fill (no same-session), `simulate_long` gross+net. `years_4_1_folds`
  raises on a short calendar instead of shrinking the spec.
- `unidesk/research/leakage_suite.py` — honest PIT helpers plus planted
  bugs the tests must catch (future bars, full-sample mean, today's
  membership, future gold).
- `run_checks` leakage is no longer a stub: planted future-bar leak must
  be distinguishable.

## Files changed

- `unidesk/research/candidates.py`, `walkforward.py`, `leakage_suite.py` (new)
- `unidesk/tests/test_n4_research_spine.py` (new)
- `unidesk/checks/runner.py` (leakage smoke)
- `unidesk/TASKS.md`, `unidesk/GOAL.md`, `unidesk/HANDOFF.md`,
  `unidesk/design/PHASE0_GAP.md`

## Verification

```text
.venv-orderflow/Scripts/python.exe -m pytest orderflow/tests unidesk/tests -q
.venv-orderflow/Scripts/python.exe unidesk/run_checks.py -> exit 0
```

## Honest partials

- No parquet-partitioned event store yet (in-memory freeze only).
- Outcomes are not attached on the 1M-bar archive this slice.
- 4y/1y walk-forward is specified and refused until history is long enough.
- Ablation ladder (P7.4) not started.
- N3 official files remain the blocker for full R0 and 4y/1y.
