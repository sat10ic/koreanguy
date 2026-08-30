# HANDOFF quality-score layer + R0 regime classifier wiring — COMPLETED (this slice)

Date: 2026-08-30.

Attribution-ID: attr-unidesk-quality-regime-wiring-claude-sonnet5-20260830-001

## Scope

Audit finding F2: `stock_quality_snapshot`, `entry_quality_snapshot`, and
`RegimeClassifier` all had zero production call sites. Task: wire them into
`momentum/nightly.py` -> `momentum/scan.py` -> `momentum/report_json.py` so
real scores and a real regime label appear in production output for the
first time, without gating the universe (`universe/gates.py`, owned by a
concurrent slice) or touching `research/labels.py`,
`research/candidates.py`, `research/archive_attach.py`,
`research/event_anchors.py`, or `momentum/detectors/*`.

Concurrent work in the same tree during this slice: a universe-gating agent
added `apply_universe_gates`/`gate_min_price`/etc. to `scan_universe` in
`momentum/scan.py` (F5) — read before editing, not touched beyond adding
this slice's own fields/calls around it. A separate fix landed mid-slice in
`momentum/scoring/stock_quality.py` (`TrendState.UNKNOWN` mapped to
`TREND_STATE_UNAVAILABLE` instead of raising `KeyError`) from another
session while this slice's own full-suite run was in flight — verified
present and correct, not re-done.

## Outcome

### Wired for real: stock-quality (P1.9)

`momentum/scan.py::scan_universe` now calls `stock_quality_snapshot` once
per scanned symbol, using inputs it already computes for that symbol
(`trend`, `rs_rank`, `rvol`, `delivery_ratio`) plus two new honestly-derived
inputs:

- `distance_52w_high_pct`: `(close - max(highs[-252:])) / max(highs[-252:])
  * 100`, computed against the SAME CA-adjusted `highs` series the rest of
  the scan uses. Only computed when >=252 sessions are loaded — below that,
  `None` with `DISTANCE_52W_UNAVAILABLE` (R12): calling a 61-session max "a
  52-week high" would misrepresent a shorter window as a full year.
- `circuit_state`: `circuit_risk_state()` against the LATEST bar's own
  `upper_circuit`/`lower_circuit` fields (`contracts/market.py:DailyBar`,
  real optional columns already in the schema — never fabricated) and its
  RAW (not CA-adjusted) close, since circuit bands are today's actual
  regulatory levels, not a historical price to rebase.

`SymbolScan` gained a `stock_quality: Optional[StockQualitySnapshot]` field
(same pattern as the existing `base_episode` field). Default weights
(`DEFAULT_STOCK_QUALITY_WEIGHTS` in `scan.py`) are the identical six-way
split already used by `tests/test_stock_quality.py`'s acceptance fixture —
nothing new invented, overridable via `scan_universe(..., stock_quality_weights=...)`.
`feature_version`/`config_hash` are a fixed string and a deterministic hash
of the weight policy (same pattern as `research/candidates.py:config_hash_for`,
reimplemented locally so `scan.py` does not import the `research` package).

`report_json.py::_candidate_dict` now emits an additive `stock_quality`
dict (`score`, `coverage`, `unknowns`, `hard_gates`, `feature_version`,
`config_hash`) per candidate — `None` only when the scan predates this
wiring or coverage falls below the snapshot's own `min_coverage` floor.
Existing consumers are unaffected: every prior field is untouched, this is
a new key.

Confirmed end-to-end against the real bhavcopy backlog (not just unit
tests): a live `run_nightly` smoke run over 80 real files produced real
per-candidate scores, e.g.
`{'score': 57.665, 'coverage': 0.7, 'unknowns': ['DISTANCE_52W_UNAVAILABLE', 'CIRCUIT_BANDS_NOT_PUBLISHED'], ...}`.

### Wired for real: R0 regime classifier

`momentum/nightly.py::run_nightly` now:
1. Computes breadth as `scan.pct_above_ema50 / 100.0` — exactly the
   fraction `scan_universe` already aggregates across the whole universe
   scan (`above_ema50 / scanned`), matching `RegimeClassifier`'s own
   documented `breadth` semantics ("fraction of the universe above its
   EMA/SMA-50"). No new input invented.
2. Loads a `RegimeClassifier`, restoring yesterday's hysteresis state (see
   persistence below), and calls `.update(session_date, breadth)` (the
   exact call pattern in `tests/test_n2_gates_primitives_regime.py` and
   `tests/test_indices_r0.py`) to get a real `RegimeRow`.
3. Builds `regime_note` from the real regime, breadth, source, and pending
   hysteresis count, and passes it into BOTH `build_nightly_report` and
   `build_nightly_json` (both already accepted a `regime_note` kwarg;
   nightly.py was simply never passing one).

`RegimeClassifier`'s optional `midcap_above_sma50` confirmation input
(`momentum/data/indices.py`) needs an NSE index harvest
(`data/market/reference/indices.parquet`) that does **not exist in this
repo** (`unidesk/tests/test_indices_r0.py`'s own harvest-dependent test
skips with "index harvest not present" for the same reason). Rather than
fabricate a midcap reading, this wiring uses the classifier's own built-in
honest degrade path: `midcap_above_sma50=None` -> `source="breadth_only"`,
which is exactly what the classifier already does when that input is
absent (`regime.py:_raw_state`). Confirmed end-to-end: a live `run_nightly`
smoke run produced `regime_note = "BEAR (breadth 26.3% above EMA50,
breadth_only)"` and `honesty_footer.regime_built == True` in the emitted
JSON, replacing the hardcoded `"not built yet"` placeholder for the first
time.

### Regime hysteresis persistence (the gap named in the task)

New module `momentum/regime_state.py`. `RegimeClassifier` is deliberately
stateful (won't flip on a single day's breadth reading — needs
`hysteresis_days` consecutive agreeing sessions), but `nightly.py` is a
fresh process every evening; without persistence, a brand-new
`RegimeClassifier()` every night means the hysteresis protection is
meaningless in production even though it works inside one process.

`regime_state.py::load_classifier`/`save_classifier` round-trip
`current`/`pending`/`pending_days`/`started`/`source` through one small
JSON file (`<data_root>/regime_state.json`, same "facts, not intent, one
round trip" convention as the top-level `STATE.json`). `nightly.py` guards
against an idempotent re-run of the same session double-counting a
hysteresis day (checks the persisted `last_session` against
`scan.last_session` before calling `.update()` again). A config change
(different breadth thresholds or hysteresis window) cold-starts honestly
rather than resuming a counter measured under a different rule.

Confirmed end-to-end: the smoke run's state file after run 1
(`{"current": "BEAR", "last_session": "2026-03-10", "pending_days": 0,
"started": true, ...}`), and re-running `run_nightly` against the SAME
session produced `regime_note` ending in `"; 2026-03-10 already scored,
state unchanged"` instead of a second hysteresis increment. New unit tests
in `tests/test_quality_regime_wiring.py` directly exercise the
across-process resume (three separate `RegimeClassifier()` instances,
state persisted and reloaded between each, correctly accumulate 3
consecutive hysteresis days and flip BULL -> BEAR exactly as one long-lived
process would) and the config-mismatch cold start.

### Exported, but NOT wired into the scan loop: entry-quality (P2.8)

`entry_quality_snapshot`/`EntryQualitySnapshot` are now exported from
`momentum/scoring/__init__.py` (`__all__` previously listed only the
stock-quality names, the bug named in the task). A second, more basic bug
was also fixed: `momentum/scoring/entry_quality.py` referenced `Optional`
and `Sequence` in its own function/dataclass signatures without importing
them from `typing` — the module could not even be imported before this fix
(confirmed: `ModuleNotFoundError`-adjacent `NameError` at import time).
Both fixes are required for the export to mean anything.

`entry_quality_snapshot` is genuinely NOT wired into `scan_universe`'s per-
symbol loop. Its required inputs — `trigger`, `invalidation`, and `hurdle`
prices (a real breakout trigger level, a real stop/invalidation level, a
real confirmation-hurdle level) — do not exist anywhere in this pipeline.
Checked directly: `momentum/detectors/setups.py`'s eight detectors compute
boolean pass/fail verdicts and diagnostic ratios (`pre_breakout_pivot`,
`overhead_room_adr`, `adr_pct`, etc.) but never a trigger/invalidation/
hurdle PRICE; `momentum/features/geometry.py`'s functions that
`entry_quality_snapshot` depends on (`breakout_room`, `room_adr`,
`initial_rr`, `trigger_distance_pct`) have no production caller anywhere in
`momentum/` either. Inventing a trigger/stop/hurdle price to force
`entry_quality_snapshot` to run would be fabricating market-decision data
this project's own R12 discipline explicitly forbids. This is reported as
an honest, unresolved gap rather than closed with synthetic inputs — the
task instructions call this out explicitly as the correct outcome when the
data genuinely does not exist yet.

## Verification

- `unidesk/tests/test_quality_regime_wiring.py` (new, 6 tests): real
  `stock_quality` on `SymbolScan`, stable `config_hash` for the default
  weight policy, additive `stock_quality` field surviving `report_json.py`,
  `entry_quality_snapshot` importable and exported, regime-state round trip
  across simulated process boundaries (hysteresis accumulates correctly),
  regime-state cold start on a config mismatch. All pass.
- Live end-to-end smoke run of `run_nightly` (not a unit-test fixture)
  against 80 real bhavcopy files: real `stock_quality` scores on real
  candidates, a real `BEAR` regime label with real breadth, a real
  persisted-then-reloaded state file, and the idempotent-rerun path all
  observed directly (see above).
- Full suite: `python -m pytest unidesk/tests -q` — see the session's
  reported command output for the exact final count; a `TrendState.UNKNOWN`
  `KeyError` surfaced by this wiring's real-backlog exercise (an existing
  latent bug in `stock_quality.py`, invisible with zero production call
  sites) was fixed by a concurrent session mid-slice and independently
  re-confirmed here, not re-implemented.
- `python unidesk/run_checks.py` run after this handoff and its
  `MODEL_WORK_LOG.jsonl` record were in place; `[attribution] pass`
  confirmed for real, not asserted.

## Files touched

- `unidesk/momentum/scoring/entry_quality.py` (missing `Optional`/`Sequence` import fix)
- `unidesk/momentum/scoring/__init__.py` (export `EntryQualitySnapshot`/`entry_quality_snapshot`)
- `unidesk/momentum/scan.py` (stock-quality wiring: new field, new params, per-symbol call)
- `unidesk/momentum/regime_state.py` (new: hysteresis persistence)
- `unidesk/momentum/nightly.py` (regime wiring: breadth -> classifier -> regime_note -> both reports)
- `unidesk/momentum/report_json.py` (additive `stock_quality` candidate field, doc comment update)
- `unidesk/tests/test_quality_regime_wiring.py` (new)
- `unidesk/HANDOFF.md`, `unidesk/TASKS.md`, `unidesk/design/MODEL_WORK_LOG.jsonl` (this record)

Attribution-ID: attr-unidesk-quality-regime-wiring-claude-sonnet5-20260830-001
