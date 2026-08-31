# HANDOFF — N5 wave C-1 (runner + S_ep snapshot bindings) — COMPLETED

Date: 2026-08-31. Lands the first of three sub-waves that wire the N5
modules (S_ep, S_tight, compare_edge) into a real-data experiment
runner. This slice ships the runner skeleton, the S_ep snapshot
bindings, and a per-detector coverage report that names exactly which
inputs are missing. The actual ``EdgeVerdict`` (Experiment A/B) is
deferred to wave C-3 + Wave E (net-bps writer fix) per the plan
revision the owner picked.

Attribution-ID: attr-unidesk-n5-wave-c1-runner-and-bindings-claude-sonnet5-20260831-001

## What landed

- ``unidesk/research/candidates.py::_snapshot`` — extended with an
  ``n5_inputs`` block carrying ``ep`` (7 named fields) and ``tight``
  (a placeholder ``base_episode: None`` that will be populated in
  C-2). The legacy ``setup_inputs`` block is untouched; the binding
  falls back to it for backward-compat reads.
- ``unidesk/momentum/scoring/_snapshot_bindings.py`` (new) — the
  only surface that knows the snapshot layout. Two public callables:
  ``score_ep_from_snapshot(symbol, session, snapshot) -> EPDecision``
  and ``s_tight_status_from_snapshot(snapshot) -> dict``. The S_ep
  binding is real; the S_tight binding returns a status dict
  (not_built_yet) so the runner can call both in a single loop.
- ``unidesk/run_n5_experiment.py`` (new) — the CLI runner.
  ``--experiment dry-run`` walks the event store and emits a per-
  detector coverage report to ``unidesk/design/n5/dry_run_*.json``.
  ``--experiment a`` and ``--experiment b`` raise NotImplementedError
  with a precise list of the missing preconditions (net_bps writer
  fix; S_tight base_episode block).
- ``unidesk/tests/test_n5_snapshot_bindings.py`` (new) — 7 tests
  covering: full inputs match pure scorer, missing components drop
  honestly, missing gap_pct returns zero coverage, bool-in-numeric
  rejected, legacy setup_inputs recovery, neither-block raises,
  legacy S_tight returns not_built_yet.
- ``unidesk/tests/test_truncation_invance.py`` — two new
  REGISTRY entries classify the new bindings as ``skip`` (the
  binding takes a frozen-snapshot dict, not a raw chronological
  series, so the truncation-invariance check does not apply).

## Verification (done-test for C-1)

```text
$ .venv-orderflow/Scripts/python.exe -m pytest unidesk/tests -q
322 passed, 25 skipped in 142.23s (0:02:22)
(prior wave: 314 passed, 23 skipped. +8 tests from this slice, +0
regressions. The +2 skipped is the test_truncation_invariance
REGISTRY entries for the two new bindings, classified as skip.)

$ .venv-orderflow/Scripts/python.exe unidesk/run_n5_experiment.py \
    --experiment dry-run --only-valid-detector --report-session 2026-07-31
[n5] dry-run -> ...unidesk/design/n5/dry_run_2026-07-31.json
  total events: 2,526, with gap_pct: 214, with full S_ep coverage: 0 (0.0%)

$ python -c "import json; d=json.load(open('unidesk/design/n5/dry_run_2026-07-31.json'))..."
  per_detector_ep:
    base_breakout       n=  5  scored=  5  mean_s_ep=44.95  mean_coverage=0.650
    episodic_pivot      n= 11  scored= 11  mean_s_ep=67.68  mean_coverage=0.650
    inside_bar          n= 97  scored= 97  mean_s_ep= 5.91  mean_coverage=0.650
    ipo_base            n= 14  scored= 14  mean_s_ep=12.40  mean_coverage=0.650
    momentum_burst      n=  3  scored=  3  mean_s_ep=17.28  mean_coverage=0.650
    power_play          n=  1  scored=  1  mean_s_ep=24.07  mean_coverage=0.450
    pullback            n= 81  scored= 81  mean_s_ep= 5.41  mean_coverage=0.650
    reversal_reclaim    n=  2  scored=  2  mean_s_ep=27.72  mean_coverage=0.650
  per_detector_tight_status: all rows = not_built_yet
  unknowns: {COMPRESSION_PERCENTILE_UNAVAILABLE, DELIVERY_SHOCK_UNAVAILABLE,
             CIRCUIT_DETECTION_NOT_WIRED} for every detector; power_play
             additionally has CLOSE_LOC_UNAVAILABLE because one event's
             setup_inputs.close_location was None.

$ .venv-orderflow/Scripts/python.exe unidesk/run_checks.py
  [attribution] pass — 70 records, 46 completed handoffs
  [orderflow_ledger] pass, [contracts] pass, [data_authority] pass,
  [leakage] pass. unidesk checks: all green.
```

## Honesty notes

- The dry-run report's headline number (0% full S_ep coverage) is
  correct, not a defect. 3 of 5 S_ep components are intentionally
  None today (prior_compression_pctile, delivery_shock,
  circuit_locked). The 0.650 coverage is the natural 65% weight
  the existing gap_pct + rvol + close_loc triple carries; the
  report names every dropped component. The next wave (C-2) will
  add the S_tight block; the circuit-detection wiring is its own
  small follow-up; the two percentile/shock proxies are deferred
  behind a documented decision (the owner chose not to invent them
  this wave; see plan revision).
- The ``circuit_locked=False`` default is a real, documented
  limitation: the freeze-scan layer does not run a day-classifier,
  so the S_ep close_quality component is computed for what may
  actually be locked days. The CIRCUIT_DETECTION_NOT_WIRED unknown
  is appended to every decision so a coverage reader sees the gap
  in the report, not in the binding source. A small follow-up
  wave will read the day-classifier output (already computed in
  ``momentum/scan.py``) and propagate the bool.
- The legacy ``setup_inputs`` recovery is a one-way migration
  aid: it lets the binding read v3/v4-regen-frozen events that
  predate this schema. Once the regen re-runs and re-freezes
  under the new schema, the recovery path will short-circuit
  (n5_inputs.ep will be present on disk and read directly). No
  data is rewritten; the binding is the single chokepoint.
- ``episodic_pivot`` has the highest mean S_ep (67.68) in the
  report, which is the directionally correct result for the
  spec's intent ("EP days with a real gap + rvol + close quality
  should rank above coil-style detectors"). Inside-bar / pullback
  (5.91 / 5.41) are low because the EP component stack rewards
  the gap+rvol+close triple that these setups structurally lack.
  This is signal, not a bug, but it is also a small-sample read
  (97 / 81 events) and the per-detector S_ep distribution will
  not stabilise until the A/B runner reads many more sessions.

## Risks / what's next

- **Wave C-2 (S_tight base_episode block):** needs BaseEpisode
  extended with ``pullback_depths`` (the per-coil pullback
  sequence, not just the final depth) and three more inputs
  (atrp_percentile, delivery_bottom_quintile, rs_made_20d_low)
  threaded into freeze_scan. Once C-2 lands, the tight block on
  the snapshot is populated and the S_tight binding becomes a
  real ``tightness_score()`` call.
- **Wave C-3 (book construction + A/B):** ``Trade`` book needs
  ``net_bps`` per the spec, and net_bps is currently 0 / 863,771
  on disk. The runner has a clear ``NotImplementedError`` path
  that names this; C-3 + Wave E (net-bps writer fix) unblock
  the verdict path together.
- **Schema migration:** the next regen freeze will write the new
  ``n5_inputs`` block on every event. The binding's backward-
  compat path becomes dead code, but it is left in (with the
  legacy key map) because the S_tight block is still a stub and
  the regen will not populate it; the binding's on-the-fly
  recovery for the EP side keeps the dry-run working even on a
  partial re-freeze.

## Files

``unidesk/research/candidates.py``,
``unidesk/momentum/scoring/_snapshot_bindings.py`` (new),
``unidesk/run_n5_experiment.py`` (new),
``unidesk/tests/test_n5_snapshot_bindings.py`` (new),
``unidesk/tests/test_truncation_invariance.py`` (REGISTRY entries),
``unidesk/design/handoffs/HANDOFF_N5_WAVE_C1_RUNNER_AND_BINDINGS_COMPLETED.md``
(this file),
``unidesk/design/MODEL_WORK_LOG.jsonl``.
