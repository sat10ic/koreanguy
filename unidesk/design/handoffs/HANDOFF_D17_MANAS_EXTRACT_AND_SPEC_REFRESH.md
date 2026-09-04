# HANDOFF D17 manas extract + V2 spec as-built — COMPLETED

Date: 2026-08-29.

Attribution-ID: attr-unidesk-d17-manas-extract-spec-grok46-20260829-001

## Outcome

- Read-only extract from `manas_os/data/manas.db` (D17). UniDesk does not
  import `manas_os`. Index parquet merged to **1,299 Nifty 50 sessions**
  (2021-06-01 → 2026-08-28) and **1,293 India VIX**; Midcap 150 / Nifty 500
  / Smallcap 250 **533 sessions** from 2024-07-08. SMA200 is computable on
  Nifty 50. 18 dated universe snapshots (43,980 rows).
- Controlling build spec refreshed in place:
  `plan/UNIFIED_DESK_BUILD_MANUAL_V2.md` (§0.1 as-built, §3 data map, §6
  wave status, §11 package map, rules R-O/R-P/R-Q). Integration plan
  sequencing is EOD-first. UI V2 notes the fixture prototype.

## Files changed

- `unidesk/momentum/data/manas_extract.py` (new)
- `unidesk/tests/test_manas_extract.py` (new)
- `unidesk/DECISIONS.md` (D17)
- `plan/UNIFIED_DESK_BUILD_MANUAL_V2.md`
- `plan/UNIFIED_DESK_INTEGRATION_PLAN.md`
- `plan/UNIFIED_DESK_UI_UX_MANUAL_V2.md`
- `plan/PHASE0_DATA_BUILD_SPEC.md` (as-built pointer)
- `unidesk/TASKS.md`, `HANDOFF.md`, `design/PHASE0_GAP.md`

## Verification

```text
.venv-orderflow/Scripts/python.exe -m pytest unidesk/tests/test_manas_extract.py unidesk/tests/test_indices_r0.py -q -> 10 passed
.venv-orderflow/Scripts/python.exe -m pytest orderflow/tests unidesk/tests -q
.venv-orderflow/Scripts/python.exe unidesk/run_checks.py -> exit 0
```

## Honest partials

- manas `daily_prices` (1.60M bars from 2021-07-12) is inventoried, not
  adopted as the EOD bar home.
- Universe PIT window is 18 dates in Jul–Aug 2026, not 2016–.
- Spec refresh is documentation of as-built; it does not close N5.
