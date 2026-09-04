# HANDOFF N3 confirmed CA derived view — COMPLETED (this slice)

Date: 2026-08-29.

Attribution-ID: attr-unidesk-n3-confirmed-ca-view-grok46-20260829-001

## Outcome

Confirmed corporate-action factors are now applied as a **derived view at
scan time**. Raw bhavcopy bars are never rewritten (the in-memory store
rejects two versions of the same session at the same `available_at`).

Seed table (`unidesk/config/confirmed_actions.csv`):

| Symbol | Ex-date | Factor | Source |
|---|---|---:|---|
| ANANDRATHI | 2026-06-03 | 0.5 | close_to_close_archive_v1 |
| BEML | 2025-11-03 | 0.5 | close_to_close_archive_v1 |
| AGIIL | 2025-02-07 | 0.5 | close_to_close_archive_v1 |
| ANUHPHR | 2025-07-15 | 0.5 | close_to_close_archive_v1 |

ASHOKLEY is not in the table (open-gap filled on the close — correctly
rejected). Detection still never auto-adjusts. Chartsmaze announcements
still have no ratios. `manas.db` has no CA-ratio table.

Nightly loads the seed and passes it to `scan_universe`. The TONIGHT
honesty footer names the derived view when actions are present.

## Files

- `unidesk/config/confirmed_actions.csv`
- `unidesk/momentum/data/corp_actions.py`
- `unidesk/momentum/scan.py`
- `unidesk/momentum/nightly.py`
- `unidesk/momentum/report.py`
- `unidesk/momentum/DATA_POLICY.md`
- `unidesk/tests/test_corp_actions.py`
- `unidesk/tests/test_nightly_scan_report.py`
- `data/market/reference/confirmed_actions.parquet`
- `plan/UNIFIED_DESK_BUILD_MANUAL_V2.md`
- `plan/PHASE0_DATA_BUILD_SPEC.md`
- `unidesk/TASKS.md`, `CANONICAL.md`, `GOAL.md`, `HANDOFF.md`,
  `unidesk/design/PHASE0_GAP.md`

## Verification

```text
.venv-orderflow/Scripts/python.exe -m pytest unidesk/tests/test_corp_actions.py unidesk/tests/test_nightly_scan_report.py unidesk/tests/test_known_split.py -q
→ 20 passed
```

## Honest partials

- Only four names. 194 detector candidates remain unconfirmed.
- Official NSE CA-with-ratios still open.
- manas `daily_prices` not adopted (D-decision).
- Did not write adjusted bars into the store (equal `available_at` is
  rejected as ambiguous). Derived view at read is the honest path.
- Predictive AI still forbidden.
