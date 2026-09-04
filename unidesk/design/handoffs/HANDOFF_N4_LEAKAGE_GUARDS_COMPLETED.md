# HANDOFF N4 leakage guards (directive 1, a-e) — COMPLETED (this slice)

Date: 2026-08-30.

Attribution-ID: attr-unidesk-n4-leakage-guards-claude-sonnet5-20260830-001

## Scope

HANDOFF.md directive 1, sub-items (a) through (e) only. Items (f) archive-wide
outcome attach, (g) ablation ladder P7.4, and (h) candidate store persistence
verification are explicitly OUT of scope for this slice and remain open.
`unidesk/research/costs.py` and `unidesk/research/leakage_suite.py` were read
in full before starting and confirmed already complete (the decoy the Opus
pre-flight review caught) — neither was touched.

## Outcome

### (a) Module-enumerating truncation-property test

New file `unidesk/tests/test_truncation_invariance.py`. Enumerates every
public top-level function defined in every module under
`unidesk/momentum/features/`, `unidesk/momentum/primitives/`,
`unidesk/momentum/scoring/` via `pkgutil.iter_modules` (same directory-walk
convention as `momentum/detectors/registry.py`'s `DETECTOR_NAMES`) — 40
callables found across 8 feature modules, 2 primitives modules
(`contraction.py`, `pivots.py`), and 2 scoring modules
(`entry_quality.py`, `stock_quality.py`).

Every enumerated callable MUST have an explicit `REGISTRY` entry classified
`series` (19, run the truncation-invariance check `f(series[:k]) ==
f(series)[:k]` against realistic synthetic OHLCV over several cuts),
`special` (1: `fractal_pivots`, whose confirmation-lag semantics get a
dedicated pivot-specific check comparing `known_at`-filtered full-series
pivots against a truncated-series computation), or `skip` (20, each with an
explicit reason — e.g. all-scalar single-instant queries, tail-of-passed-
series functions with no external index that structurally cannot leak, or
functions operating on caller-precomputed point-in-time scalars/mappings
rather than a raw chronological series). A separate test,
`test_every_enumerated_callable_is_registered`, fails loudly if a newly
added module/function under any of the three packages has no `REGISTRY`
entry, and also fails if a `REGISTRY` entry references a callable that no
longer exists — the registry cannot silently drift stale in either
direction.

40 parametrized cases: 20 pass the real check, 20 explicit skips (visible
in `-rs` output with their reasons).

### (b) Labels-future-only assertion

`unidesk/research/labels.py` gained `assert_future_only(sessions,
decision_session)` — fails closed (`ContractError`) if any session is not
strictly after the decision session. `labels.py`'s functions
(`long_outcome`, `breakout_hold`) take already-sliced future arrays with no
decision-index of their own, so the assertion is wired at the one real
production call site, `research/candidates.py:attach_outcomes`, as
defense-in-depth alongside (not instead of) the existing `future_after`
filter. New file `unidesk/tests/test_labels_future_only.py` (6 tests):
direct unit tests of the assertion (accept/reject on planted decision-bar
and past-bar leaks) plus an integration test that poisons the future map
with a catastrophic value on the decision bar itself and confirms
`attach_outcomes` never lets it into the computed MAE.

### (c)+(d) Adjustment-basis guard

Read `research/candidates.py`, `research/event_store.py`, and `momentum/
scan.py` (lines ~101 `adjust_ohlcv`, ~64-65 `ScanResult.adjusted_symbols`/
`actions_applied`) in full first, per instructions. `attach_outcomes` (not
`event_store.py`) turned out to be the real outcome-attach call site;
`event_store.py` only persists/loads events and has no outcome logic.

- `SymbolScan` (`momentum/scan.py`) gained `adjusted: bool = False`, set
  from `adj["adjusted"]` (already computed by `adjust_ohlcv` per symbol,
  previously only aggregated into `ScanResult.adjusted_symbols` and
  dropped per-symbol).
- `corp_actions.py` gained `confirmed_actions_content_hash(path=None)` —
  SHA-256 (16 hex chars) of the CSV's actual bytes, not its path/mtime; a
  missing file hashes the empty string.
- `candidates.py:_snapshot()` now carries `"adjusted"` and
  `"ca_table_hash"` on every per-symbol snapshot dict.
- `candidates.py:config_hash_for()` now folds in the confirmed-actions
  content hash and `research/costs.py`'s `COSTS_VERSION` (imported, not
  reimplemented) alongside the existing detector-name hash — two scans run
  under different CA-table content, or a different frozen cost model, no
  longer collapse to the same config hash.
- `attach_outcomes()` compares the future series' stated basis
  (`series["adjusted"]` / `series["ca_table_hash"]`, both optional) against
  the snapshot's basis. A mismatch — `adjusted` flags disagree, or both
  sides state a `ca_table_hash` and they differ — refuses a real outcome:
  `UNRESOLVED` / `reason="adjustment_basis_mismatch"`, same convention as
  the pre-existing `no_future_series`/`no_future_bars`/etc. guards. Neither
  side stating a basis (the pre-existing default) is a no-op — this keeps
  every caller that predates this change working exactly as before
  (verified: `test_n4_research_spine.py` and
  `test_nightly_scan_report.py` still pass unmodified).

New file `unidesk/tests/test_adjustment_basis_guard.py` (10 tests):
snapshot carries the fields; CA-content-hash is content-sensitive (same
content/different path → same hash; changed content → different hash;
missing file → stable empty-content hash); `config_hash_for` changes when
CA-table content changes and is stable when only the path changes;
`attach_outcomes` resolves on a matching basis, refuses on an
`adjusted`-flag mismatch, refuses on a `ca_table_hash` mismatch, and stays
backward-compatible when neither side states a basis.

### (e) Unconfirmed corporate-action guard — the important one

The "194 unconfirmed open-gap candidates" are NOT a persisted file
anywhere in the repo (confirmed by search) — they are the live output of
`momentum/data/splits.py:scan_store_for_splits` (which drives
`corp_actions.py:detect_split_candidates_bars`) minus whatever is already
in `config/confirmed_actions.csv` (4 names today).

- `splits.py` gained `unconfirmed_candidate_sessions(candidates,
  confirmed)` — groups the detector's `SplitCandidate` output by symbol
  into the set of gap sessions NOT covered by a confirmed action with a
  matching `(symbol, ex_date)`. This function only groups the existing
  backlog; it infers no ratios and adjusts nothing (same conservative
  posture as the rest of `corp_actions.py`).
- `attach_outcomes()` gained an optional `unconfirmed_ca_sessions` param
  (symbol -> gap sessions). If any session actually used to compute an
  event's outcome (the horizon-bounded future window, post-`future_after`)
  falls on one of those unconfirmed gap sessions, the event is refused a
  real outcome: `UNRESOLVED` / `reason="unconfirmed_corporate_action"`.
  Omitting the parameter is a no-op — production wiring of this parameter
  into the (not-yet-built) archive-wide attach run is item (f), out of
  scope here.

New file `unidesk/tests/test_unconfirmed_ca_guard.py` (6 tests), built
against a REAL detector output (not an invented date): constructs a store
with a genuine ~2:1 overnight gap, runs the actual
`scan_store_for_splits`/`unconfirmed_candidate_sessions` pipeline, and
proves (1) the fixture really is flagged by the real detector, (2)
confirming the action removes it from the backlog, (3) `attach_outcomes`
refuses with `unconfirmed_corporate_action` when the outcome window spans
the real unconfirmed gap, (4) a **negative control**: the identical
fixture WITHOUT the guard parameter resolves and produces the exact
~-50%-type catastrophic MAE the guard exists to prevent — proving the
guard in test (3) is doing real work, not vacuously passing, (5) a
candidate outside the outcome window does not block resolution (the guard
is not overzealous), (6) omitting the parameter is a no-op.

One incidental finding surfaced while building fixture (3): the existing
`detect_split_candidates_bars` re-locates a candidate's bar index via
`closes.index(cand.prev_close)`, which returns the FIRST matching close in
the array — with a flat pre-gap price series this silently mis-locates the
`SplitCandidate.session` to the wrong day. Worked around it in the test
fixture (a monotonic pre-gap ramp so every pre-gap close is unique) rather
than fixing the production function, since it is outside this task's
scope; flagged in Risks below for a future slice.

## Files

- `unidesk/tests/test_truncation_invariance.py` (new)
- `unidesk/tests/test_labels_future_only.py` (new)
- `unidesk/tests/test_adjustment_basis_guard.py` (new)
- `unidesk/tests/test_unconfirmed_ca_guard.py` (new)
- `unidesk/research/labels.py` (`assert_future_only`)
- `unidesk/research/candidates.py` (`_snapshot`, `config_hash_for`,
  `freeze_scan`, `attach_outcomes`)
- `unidesk/momentum/scan.py` (`SymbolScan.adjusted`)
- `unidesk/momentum/data/corp_actions.py` (`confirmed_actions_content_hash`)
- `unidesk/momentum/data/splits.py` (`unconfirmed_candidate_sessions`)
- `unidesk/HANDOFF.md`, `unidesk/TASKS.md` (this slice's log/backlog update)

## Verification

```text
python -m pytest unidesk/tests -q
→ 314 passed, 22 skipped  (pre-existing suite unchanged; +63 new tests
  across the four new files, 21 of which are the truncation test's
  explicit, reasoned skips)

python -m pytest unidesk/tests orderflow/tests -q
→ 314 passed, 22 skipped  (combined baseline was 272 passed, 1 skipped;
  no regression, all growth is this slice's new tests)

python unidesk/run_checks.py
→ [attribution] pass, [contracts] pass, [data_authority] pass,
  [leakage] pass, [stale_state]/[provenance] not_built_yet (pre-existing,
  owned by other waves) — "unidesk checks: all green"
```

Re-ran `python unidesk/run_checks.py` a second time after appending the
`MODEL_WORK_LOG.jsonl` record and confirmed `[attribution] pass` still
holds (round-trip check).

## Honest partials / out of scope

- **Production wiring of `leakage.py`'s three guards
  (`assert_feature_not_after_decision`, `same_symbol_embargo`,
  `same_event_collision`) is still zero production call sites** — this was
  explicitly called out as real-but-out-of-scope for this task and remains
  open. It is a real gap, separate from what (a) fixes.
- Item (f): archive-wide outcome attach over the 1M-bar corpus — not run,
  per the hard constraint. The guards built here (c/d/e) are what gate it,
  but wiring `unconfirmed_ca_sessions=unconfirmed_candidate_sessions(...)`
  and a real CA-basis-aware future map into that run is separate work.
- Item (g) ablation ladder P7.4, item (h) candidate-store persistence
  verification: not started.
- The `contraction.py`/`stage2`-style "tail of whatever series is passed"
  functions are classified `skip` in the truncation test with the
  reasoning that they cannot structurally see beyond what's passed to
  them — true, but their SAFETY still depends on every caller always
  slicing to exactly the decision-time prefix before calling. That caller-
  side discipline is not independently verified by this task; it is a
  documented assumption, not a proven property.
- `detect_split_candidates_bars`'s `closes.index(cand.prev_close)`
  bar-relocation bug (see above, under item (e)) is a real pre-existing
  defect that can mis-locate a flagged candidate's session when the
  pre-gap price is flat/repeating. Not fixed here (out of scope); flagged
  for a future slice.
- `attach_outcomes`'s `adjustment_basis_mismatch` and
  `unconfirmed_corporate_action` guards were unit/integration tested
  directly against the function with hand-built and detector-real fixtures.
  They have NOT been exercised against the real archive-wide future-bar
  data (that data pull/shape is item (f)'s job) — the guard logic itself is
  verified; its behavior against the real 1M-bar corpus is not.

## Risks

- The `closes.index()` relocation bug in `detect_split_candidates_bars`
  means the REAL "194 unconfirmed candidates" backlog produced by
  `scan_store_for_splits` over the actual archive may currently carry some
  mis-dated sessions for symbols with flat/repeating pre-gap closes. This
  does not weaken the guard's logic (it will still refuse whatever session
  the backlog says), but the backlog's own dates should be spot-checked
  before item (f) runs against real data.
