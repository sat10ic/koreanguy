# HANDOFF Bhavcopy real-data pipeline — COMPLETED

Date: 2026-08-29. Slice: historical EOD data path (U-P0.3 real-data half),
under the owner's autonomous-build directive (D8).

Attribution-ID: attr-unidesk-bhavcopy-pipeline-glm53flash-20260829-001

## Outcome

- `unidesk/momentum/data/bhavcopy.py` — ingests the repo's 303-file bhavcopy
  backlog (both `cm*bhav.csv` and `sec_bhavdata_full*.csv` generations,
  identical schema): EQ-series filter, symbol normalization with the amended
  charset (`&` restored for M&M-class tickers — DATA_POLICY amendment),
  per-row numeric validation (fail-loud on garbage, skip-and-count on
  non-normalizable symbols), publication policy D 18:00 IST, O(1) cross-file
  dedupe (overlapping generations: first-sorted-file wins).
- Verified end-to-end: **646,052 unique bars, 2,760 symbols,
  2025-03-19 → 2026-07-03, ~73 s.**
- First real feature computation (TRENT through 2026-07-03): EMA21/50,
  trend state WEAK (price under a falling EMA50), ADR20 2.7% of price,
  ATR14 3.6%, RVOL 0.80, delivery ratio 1.07, delivery 43–57% — all sane,
  all from real files, not fixtures.
- Store duplicate guards made O(1) via internal key-sets (identical
  rejection semantics; the list scans were quadratic at 600k bars and would
  not have completed).
- DECISIONS D8 (autonomous-build directive + read-only shared-store policy)
  and D9 (bhavcopy source adoption + charset amendment) recorded; DATA_POLICY
  charset amended with a dated note.

## Files changed

- `unidesk/momentum/data/bhavcopy.py` (new), `unidesk/momentum/data/market_store.py`
  (O(1) guards), `unidesk/momentum/universe/symbol_master.py` + `unidesk/momentum/DATA_POLICY.md`
  (charset amendment), `unidesk/DECISIONS.md` (D8/D9), `unidesk/tests/test_bhavcopy_ingest.py`
  (6 tests incl. real-backlog smoke), `unidesk/GOAL.md`, `unidesk/DECISIONS.md`.

## Verification

```text
.venv-orderflow/Scripts/python.exe -m pytest orderflow/tests unidesk/tests -q -> 173 passed
.venv-orderflow/Scripts/python.exe unidesk/run_checks.py -> exit 0
Full-backlog run: 303 files -> 646,052 bars / 2,760 symbols in 73.2 s
```

## Honest partials

- Publication time 18:00 IST is a POLICY assumption, not a verified
  publication timestamp (bhavcopy lands ~19:00–21:00 in practice; a bar
  being visible "too early" within the same evening session is impossible
  for a swing desk querying next-day, which is the actual usage).
- DELIV_PER blank rows become None and disable delivery-dependent features
  per policy; blank-rate across the backlog not yet profiled.
- Only EQ series ingested (BE/BZ and others skipped by filter).
- The MomentumContextSnapshot / Model A harness wiring (W-D remainder) now
  has data but is not yet run against the full universe.
