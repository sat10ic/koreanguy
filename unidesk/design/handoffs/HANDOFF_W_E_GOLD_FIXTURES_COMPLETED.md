# HANDOFF W-E gold fixtures — COMPLETED

Date: 2026-08-29. Slice: P2.3 gold fixtures (positive AND negative real
examples per detector) and per-detector disable.

Attribution-ID: attr-unidesk-we-gold-fixtures-grok46-20260829-001

## Outcome

- `unidesk/momentum/detectors/inputs.py` — point-in-time setup inputs
  (gap, close location, inside-bar geometry, listing-age proxy, room to
  series high in ADR units, EMA21 proximity, reclaim/failed-breakdown
  proxies) computed from completed OHLCV. Warm-up is None, never guessed.
- `unidesk/momentum/detectors/registry.py` — eight named detectors, each
  separately disableable; unknown names fail closed.
- Nightly scan now runs all eight detectors (was burst / partial-EP /
  power-play only) and freezes `setup_inputs` on each `SymbolScan`.
- Gold fixtures: 32 frozen real cases (2 positive + 2 negative × 8
  detectors) harvested from the bhavcopy backlog at 2025-11-14, 2026-04-02,
  2026-05-15, 2026-06-30, 2026-07-03. Tests replay the JSON; they do not
  re-ingest 646k bars.

## Files changed

- `unidesk/momentum/detectors/inputs.py`, `registry.py`, `gold.py`, `__init__.py` (new/updated)
- `unidesk/momentum/scan.py`, `unidesk/momentum/report.py`
- `unidesk/tests/test_detector_registry.py`, `unidesk/tests/test_gold_fixtures.py` (new)
- `unidesk/tests/fixtures/p2_3_gold.json` (new)
- `unidesk/GOAL.md`, `unidesk/TASKS.md`

## Verification

```text
.venv-orderflow/Scripts/python.exe -m pytest orderflow/tests unidesk/tests -q -> 245 passed
.venv-orderflow/Scripts/python.exe unidesk/run_checks.py -> exit 0
```

## Honest partials

- `listing_age_sessions` is store-length, not a listing calendar.
- `avwap_extension_adr` is None (no EOD AVWAP anchor yet).
- `rs_improving` is own 20d-return improvement, not cross-sectional rank.
- GBT scorer (P2.9) and similarity (P2.10) remain deferred.
- Power-play positives were absent on Jun/Jul 2026 scan dates and were
  taken from 2026-04-02; that is recorded in the fixture `as_of` field.
