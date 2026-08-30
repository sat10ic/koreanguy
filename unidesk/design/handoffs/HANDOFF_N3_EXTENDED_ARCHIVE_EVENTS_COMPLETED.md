# HANDOFF N3 extended archive + event tables — COMPLETED (this slice)

Date: 2026-08-29.

Attribution-ID: attr-unidesk-n3-archive-events-grok46-20260829-001

## Outcome

- **D15:** `data/bhavcopy/` is the historical EOD archive (the downloader's
  target). Measured this session: **503 files, 0 skipped, 1,004,896 bars,
  2024-09-02 → 2026-08-28**. Nightly `--backlog` default corrected. The
  extractor folder (646k bars) is a stale subset.
- **Chartsmaze event tables** (`unidesk/momentum/data/events.py`), tagged
  `source_tier=SECONDARY_REPAIR`, never overwriting bhavcopy:
  IPO listings; circuit revisions with `circuit_band_as_of` (None before
  first revision — D14.5); 10,972 corporate announcements as a review
  queue (`auto_adjustable=False`, no ratios); vendor Above-50/200 MA%
  breadth series for calibration only.
- **Known-split confirmation:** `adjustment_kills_the_gap` is close-to-close.
  Real 2:1 names that pass: ANANDRATHI 2026-06-03, BEML 2025-11-03,
  AGIIL 2025-02-07, ANUHPHR 2025-07-15. Detector found 194 open-gap
  candidates; open-gap ≠ confirmed (ASHOKLEY printed a 2:1 *open* that
  the close filled — correctly rejected).

## Files changed

- `unidesk/DECISIONS.md` (D15)
- `unidesk/momentum/nightly.py` (default backlog path)
- `unidesk/momentum/data/events.py`, `unidesk/momentum/data/splits.py` (new)
- `unidesk/momentum/DATA_POLICY.md`
- `unidesk/tests/test_events.py`, `unidesk/tests/test_known_split.py` (new)
- `unidesk/tests/test_bhavcopy_ingest.py`
- `unidesk/GOAL.md`, `unidesk/TASKS.md`, `unidesk/CANONICAL.md`,
  `unidesk/HANDOFF.md`, `unidesk/design/PHASE0_GAP.md`

## Verification

```text
.venv-orderflow/Scripts/python.exe -m pytest orderflow/tests unidesk/tests -q
.venv-orderflow/Scripts/python.exe unidesk/run_checks.py -> exit 0
Real ingest: 503 files, 1,004,896 bars, 194 split candidates
```

## Honest partials

- History still starts 2024-09-02, not 2016-01-01.
- No official index/VIX/PIT membership files; R0 stays breadth_only.
- Chartsmaze announcements have no split ratios — they cannot confirm a
  factor. Auto-adjust remains off.
- Vendor breadth is calibration, not the R0 input.
- Full-archive ingest is ~100 s; not in the unit-test default path.
