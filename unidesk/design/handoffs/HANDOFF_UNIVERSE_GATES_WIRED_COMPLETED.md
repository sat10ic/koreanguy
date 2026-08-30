# F5 fix: universe tradeability gates wired into `scan_universe`

## Finding (F5)

`unidesk/momentum/universe/gates.py` already implemented price floor (Rs
30), avg-turnover floor (Rs 2cr/day, trailing 20 sessions), a probable-ETF
keyword heuristic, and a circuit-lock/illiquid-freeze heuristic —
copy-adopted from `manas_os/alpha/activity.py`, and covered by its own
unit tests — but `momentum/scan.py`'s `scan_universe` never imported it.
The only filter on the universe was `len(bars) >= min_sessions`. Every
detector's `rs_rank` input is a cross-sectional percentile computed over
that same ungated universe, so penny stocks, ETFs, and circuit-locked
names were distorting every `rs_rank >= N`-style detector gate.

## Fix

`scan_universe` now accepts `apply_universe_gates` (+ `gate_min_price`,
`gate_min_avg_turnover_cr`, `gate_exclude_etf`, all defaulting to
`gates.py`'s own named constants — no new magic numbers). When enabled,
each non-quarantined symbol is run through `evaluate_gates` **before**
the universe's 20-day returns (`universe_returns`, the RS-ranking input)
are built — same principle, same code shape, as the existing CA-quarantine
exclusion just above it in the same function. A gate-failed symbol is
excluded from both `universe_returns` and the main scan loop, and counted
under a new named `skipped` bucket (`universe_gate_price_floor`,
`universe_gate_turnover_floor`, `universe_gate_probable_etf`,
`universe_gate_circuit_locked`, or `universe_gate_no_price_history`),
first-failing-reason priority, matching `evaluate_gates`'s own internal
check order — never a silent drop, never double-counted.

**Design decision — default OFF in `scan_universe`, default ON in
`nightly.py`:** every existing `scan_universe` call site (most of the test
suite, `research/archive_attach.py`, `momentum/detectors/gold.py`) uses
small synthetic fixtures or is out of scope for this task (both of those
production files are on the explicit do-not-touch list for this slice).
Flipping the gate default to True inside `scan_universe` itself would have
silently broken dozens of unrelated existing tests whose fixtures use
unrealistic turnover (e.g. `volume=800` at `close=50`), including tests
whose actual point is orthogonal to universe eligibility (e.g.
`test_freeze_scan_keeps_invalid_symbols` in `test_n4_research_spine.py`,
which deliberately keeps a low-volume "FLAT" symbol IN the scan to prove
invalid-but-scanned symbols are retained). Rather than touch those
unrelated fixtures or risk the do-not-touch files, `apply_universe_gates`
defaults to `False` in `scan_universe`, and the one production entry point
this task IS in scope to touch — `momentum/nightly.py`'s `run_nightly` —
opts in explicitly (`apply_universe_gates=True`) and logs the exclusion
breakdown. `research/archive_attach.py` and `momentum/detectors/gold.py`
keep their current (ungated) `scan_universe` calls untouched, as directed;
gating those is out of scope here.

`report.py` and `report_json.py`'s honesty footers were extended (additive
only) to surface the new `universe_gate_*` skip counts, so a trader reading
the nightly report sees e.g. "841 symbols excluded from RS ranking...
turnover floor: 841, price floor: 463, ..." rather than a silently smaller
universe.

## ETF heuristic false positive (explicit disclosure, per task instruction)

`is_probable_etf` is a **substring** match over a keyword set. Verified
against the real archive (`data/bhavcopy/sec_bhavdata_full_31122024.csv`,
2752 unique EQ-series symbols) on 2026-08-30, TWO real false positives were
found (not hypothesized — confirmed against actual data):

* **ABSLAMC** — Aditya Birla Sun Life AMC, a real stock (that session:
  close Rs 837.80, turnover Rs 32.17cr). The bare `"ABSL"` keyword matched
  it as a substring (ABSL is also the issuer prefix of several real
  ABSL-house ETFs). Fixed by **removing** `"ABSL"` from `_ETF_KEYWORDS`
  entirely (not papering over with an override) — the genuine ABSL ETFs in
  the archive (ABSLBANETF, ABSLLIQUID) are still caught on their own merits
  by the `"ETF"`/`"LIQUID"` keywords.
* **JETFREIGHT** — a real logistics stock, caught purely because `"ETF"`
  is a substring of "J-ETF-REIGHT". This is the *general* failure mode of
  substring matching (any keyword can collide with any real symbol that
  happens to contain those letters in sequence), not specific to ABSL.
  Fixed via a small `_KNOWN_NON_ETF_OVERRIDES` exact-match set
  (`{"ABSLAMC", "JETFREIGHT"}`) checked before the keyword scan.

**Disclosed limitation, not claimed as complete:** this is a targeted
patch for the two false positives actually found in the real archive scan
that backs this fix. It is NOT a proof that no other substring collision
exists among the ~2750 real symbols in the archive, nor a general
word-boundary rewrite of the heuristic (NSE symbol naming is inconsistent
enough — trailing digit suffixes like `NIFTY1`, `LIQUID1`, `ADD`-suffixed
variants like `BANKETFADD` — that a blanket suffix-only rule would
silently flip some genuine ETFs to false negatives; that tradeoff was not
made here). `is_probable_etf`'s own docstring already says "a cheap
pre-filter, never ground truth" — a symbol newly flagged as probable-ETF
should still be spot-checked, exactly as before this fix.

## Real numbers (full archive, `data/bhavcopy/`, 503 files, 1,004,896 bars,
`as_of=now`, `run_detectors=False`)

```
[ingest]  1,004,896 bars from 503 files
[ungated] scanned=2529  skipped={insufficient_sessions: 283, unconfirmed_corporate_action: 185}
[gated]   scanned=1380  skipped={insufficient_sessions: 68, unconfirmed_corporate_action: 185,
                                  universe_gate_turnover_floor: 841,
                                  universe_gate_price_floor: 463,
                                  universe_gate_probable_etf: 56,
                                  universe_gate_circuit_locked: 4}
```

Totals reconcile exactly both ways (2529+283+185 = 2997 = 1380+68+185+841+
463+56+4): every symbol in `by_symbol` is accounted for in both runs,
nothing silently dropped. `insufficient_sessions` drops from 283 to 68
under gating — not a discrepancy: many low-bar symbols also fail
price/turnover on their thin sample and are now bucketed under the
gate reason instead (first-failing-reason priority is checked before the
`min_sessions` check in the main loop), which is a more informative label
for those names, not a double-count or an unaccounted symbol.

**Universe shrinks from 2,529 to 1,380 tradeable symbols (-45.4%) once
gated** — confirming F5's premise: the RS-ranking denominator was
materially distorted by ungated names.

**ABSLAMC / JETFREIGHT check, against the real archive directly**
(`unidesk/momentum/universe/gates.py:evaluate_gates`):
```
ABSLAMC:    is_probable_etf=False, tradeable=True
            price=Rs 1047.90, avg_turnover_cr=Rs 18.95cr, etf=False, circuit_locked=False
JETFREIGHT: is_probable_etf=False, tradeable=False
            reasons: price Rs22.39 < Rs30.00 floor; avg turnover Rs0.42cr < Rs2.00cr floor
```
ABSLAMC correctly stays IN the gated universe (real, liquid stock, not an
ETF). JETFREIGHT is correctly excluded, but for its real, legitimate
reason (thin/penny) — NOT because of the ETF keyword bug, which is
confirmed fixed (`is_probable_etf("JETFREIGHT")` is `False`).

## Tests added

`unidesk/tests/test_detector_registry.py::test_scan_applies_universe_gates_before_rs_ranking`
— one fixture symbol per gate (penny price, thin turnover, ETF-keyword
name `NIFTYBEES`, circuit-frozen tail) plus one clean symbol that clears
all four, run twice: once with `apply_universe_gates=False` (regression
proof — default behaviour unchanged, all 5 scanned), once with `True`
(only the clean symbol survives; each gate's `skipped` bucket count is
exactly 1, summing to 4).

`unidesk/momentum/universe/gates.py` had 14 existing gate tests, all still
passing unchanged (the ETF-keyword fix removed a false-positive collision
without disturbing them: `python -m pytest unidesk/tests -q -k gate` → 14
passed).

## Test run (full suite, `python -m pytest unidesk/tests -q`, this
session's final clean run)

```
283 passed, 21 skipped in 258.85s
```

**Note on the stated 342-passed/22-skipped baseline in this task's
brief:** the actual count in the working tree as verified here is lower
(283 passed / 21 skipped, 306 collected). This session ran concurrently
with at least one other active slice (the quality-layer/regime-wiring F2
fix, see `HANDOFF_QUALITY_LAYER_REGIME_WIRING_COMPLETED.md`, also
uncommitted in this same working tree) that was mid-edit to
`momentum/scan.py` and `momentum/scoring/stock_quality.py` while this
slice's own full-suite run was in flight — one earlier run transiently
showed 2 failures (`test_real_backlog_scan_smoke`,
`test_json_emits_cleanroom_base_episodes_separately_from_legacy_candidates`)
that both passed cleanly in isolation and on the final full run, consistent
with a mid-edit race rather than a real regression. The 342/22 figure this
task's brief cited does not match either commit HEAD (`fef0841f`, which
already has fewer tests than that) or this working tree; it is reported
here as **Unverified: stale relative to concurrent same-session churn**,
not reproduced or explained further — the number this fix is accountable
for is the delta it introduces (net +1 test, `test_scan_applies_universe_gates_before_rs_ranking`,
passing; zero test files removed; zero failures on the final clean run).

## `run_checks.py`

```
[attribution] pass
[contracts] pass
[data_authority] pass
[leakage] pass
[stale_state] not_built_yet (owed by U-P3)
[provenance] not_built_yet (owed by U-P7)
unidesk checks: all green (stubs honestly not_built_yet)
```
(Re-run after appending this record's `MODEL_WORK_LOG.jsonl` entry, per
the attribution round-trip check.)

## Files touched

- `unidesk/momentum/universe/gates.py` — ETF false-positive fix
  (`_KNOWN_NON_ETF_OVERRIDES`, `"ABSL"` removed from `_ETF_KEYWORDS`).
- `unidesk/momentum/scan.py` — `apply_universe_gates` + 3 threshold params
  on `scan_universe`; `_gate_skip_bucket`; gate exclusion wired before
  `universe_returns`, matching the CA-quarantine pattern exactly.
- `unidesk/momentum/nightly.py` — production entry point opts in
  (`apply_universe_gates=True`) and logs the exclusion breakdown.
- `unidesk/momentum/report.py`, `unidesk/momentum/report_json.py` —
  additive honesty-footer surfacing of `universe_gate_*` skip counts.
- `unidesk/tests/test_detector_registry.py` — new gate-integration test.
- `unidesk/HANDOFF.md`, `unidesk/TASKS.md` — F5 closed.
- `unidesk/design/MODEL_WORK_LOG.jsonl` — this record.

## Explicitly NOT touched (per task constraints)

`unidesk/research/labels.py`, `unidesk/research/candidates.py`,
`unidesk/research/archive_attach.py`, `unidesk/research/event_anchors.py`,
`unidesk/momentum/detectors/*` (including `gold.py`, whose `scan_universe`
call remains ungated — out of scope here). No archive-wide outcome-attach
run was performed. `git commit` was **not** run for this slice — held
pending the owner's review of this diff alongside the concurrent
quality-layer (F2) diff to the same file (`momentum/scan.py`), per explicit
instruction.

Attribution-ID: attr-unidesk-universe-gates-wired-claude-sonnet5-20260830-001
