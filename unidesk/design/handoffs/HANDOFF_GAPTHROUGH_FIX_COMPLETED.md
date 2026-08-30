# HANDOFF gap-through stop undercount — COMPLETED

Date: 2026-08-30. The swing-edges/AI-native review's most consequential
finding, fixed and regression-tested.

Attribution-ID: attr-unidesk-n4-gapthrough-fix-glm53flash-20260830-001

## Outcome

`long_outcome` (research/labels.py) now accepts the future window's OPENS.
On the first bar whose low touches the stop: if that bar OPENED below the
stop, the realistic exit is the open (loss ≈ −4R in the reviewer's
entry-100/stop-95/open-80 example), else the stop (−1R). New Outcome fields
`exit_price` + `gap_through`; `potential_r_multiple` stays observational.
Without opens, the stop-fill assumption is kept but flagged
`gap_through=None` (unknown — explicitly not assumed fine).

Wired through production: `candidates.attach_outcomes` (opens already loaded
for entry fills) and `walkforward.simulate_long`/`stop_aware_return_bps`
(gap_open parameter; docstring corrected — the stop bar's open is EOD data,
not an intraday peek).

## Files changed

- `unidesk/research/labels.py`, `unidesk/research/candidates.py`,
  `unidesk/research/walkforward.py`, `unidesk/tests/test_labels.py` (2 new tests)

## Verification

```text
.venv-orderflow/Scripts/python.exe -m pytest orderflow/tests unidesk/tests -q
  -> 370 passed, 21 skipped (skips audited: all documented non-time-series
     or real-data-conditional; none suspicious)
.venv-orderflow/Scripts/python.exe unidesk/run_checks.py -> exit 0
```

## Honest partials

- **ARCHIVE REGENERATION REQUIRED**: the event store was built on the old
  labels; stored outcomes understate gap-through losses and must be
  regenerated before Experiment A/B reads a single number.
- Short-horizon PARTIAL framing inconsistency between attach_outcomes and
  walkforward (review finding) remains open.
- Net-of-cost storage in the archive (review finding) remains open.
- Skip audit: all 21 skips are documented non-time-series or
  real-data-conditional tests — nothing suspicious.

## Addendum (2026-08-30) — v3 label schema + regeneration launch

The follow-on slice (label version bump to `outcome-labels-v3-gap-aware`,
writer whitelist widened to persist `exit_price`/`gap_through`, gross_bps
made gap-aware, archive regeneration launched) is reported against this
same handoff.

Attribution-ID: attr-unidesk-n4-gapthrough-fix-glm53flash-20260830-002
