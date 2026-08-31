# HANDOFF — History real-data wiring (UI plan row 4) — COMPLETED

Date: 2026-08-31. Wires the static Vite terminal to the real research event
store via `unidesk/run_history_outcomes_export.py` and a new
`unidesk_terminal/src/data/outcomes.ts`. Closes the "HISTORY/outcome-join
backend is not built yet" gap that CANONICAL §1 named (rows 38-39: History
real coverage owed by N4).

Attribution-ID: attr-unidesk-history-real-data-wiring-claude-sonnet5-20260831-001

## What was in scope (per UI plan row 4)

- `unidesk/run_history_outcomes_export.py` — the existing refuse-on-
  label-mixed safety gate now ships a real export. Two real bugs were
  closed in the same slice:
  1. `ev.session` did not exist; the field is recovered from `event_id`
     (last `:` segment) or `timestamp.date()` via `event_store.session_of`.
  2. The first export included the negative-class archive (every scanned
     symbol-day, ~75k calls) which the History screen mis-renders as
     "unknown" calls. The export now filters to events where at least
     one detector returned VALID — real candidates, by design of
     `research.candidates.freeze_scan` (the negative class is research
     substrate, not a "call" to display in the History UI).
- `unidesk_terminal/src/data/outcomes_2026-08-28.json` — build-time
  Vite snapshot of the export: 11,591 candidate calls across 231
  symbols, dates 2024-11-28 → 2026-08-28, label stamp
  `outcome-labels-v4-net-cost` on every row.
- `unidesk_terminal/src/data/outcomes.ts` — typed wrapper exposing
  `REAL_CALLS` (newest-first) and `OUTCOMES_META` (report session,
  labels version, count, netBps coverage, distinct symbols covered).
- `unidesk_terminal/src/data/fixtures.ts` — `OutcomeCall` interface
  gained optional `netBps` / `stopHit` / `gapThrough` (the synthetic
  fixture trio leaves them undefined; the real export populates them).
- `unidesk_terminal/src/screens/History.tsx` — switched primary content
  from synthetic `YESTERDAYS_CALLS` to real `REAL_CALLS`. Header copy
  no longer claims "Only one report has run on real data" — that was
  stale the moment N1 landed. Added a visible warning panel when the
  net-bps coverage is 0 (currently always).

## Verification (measured, not assumed)

```text
$ .venv-orderflow/Scripts/python.exe unidesk/run_history_outcomes_export.py
[outcomes] 11591 labled calls for tonight's 231 symbols
  -> unidesk_terminal/src/data/outcomes_2026-08-28.json
  (real wall-clock: ~5min for the load_events walk over 396 partitions
   + ~2s for the actual export)

$ python -c "import json; d=json.load(open('unidesk_terminal/src/data/outcomes_2026-08-28.json')); ..."
  count: 11,591
  outcome distribution: stopped_out=4,974, unresolved=3,497, hit_target=3,120
  setupType distribution: inside_bar=5,176, pullback=3,329, ipo_base=1,428,
                         episodic_pivot=577, power_play=338,
                         reversal_reclaim=276, base_breakout=258,
                         momentum_burst=209
  date fill rate: 11,591/11,591 (100%)
  date range: 2024-11-28 .. 2026-08-28
  netBps null rate: 11,591/11,591 (100% — see "Honesty notes" below)
  label versions: outcome-labels-v4-net-cost: 11,591 (single version)

$ cd unidesk_terminal && ./node_modules/.bin/tsc -b
  exit=0  (no type errors)

$ cd unidesk_terminal && ./node_modules/.bin/vite build
  vite v8.2.2 building client environment for production...
  ✓ 2439 modules transformed.
  dist/index.html                     0.48 kB
  dist/assets/index-C2YcsYgw.css     20.44 kB
  dist/assets/index-D5aQdZxE.js   5,255.27 kB │ gzip: 902.86 kB
  ✓ built in 11.41s

$ .venv-orderflow/Scripts/python.exe -m pytest unidesk/tests -q
  314 passed, 23 skipped in 258.97s (unchanged from prior wave)

$ .venv-orderflow/Scripts/python.exe unidesk/run_checks.py
  [attribution] pass — 69 records, 45 completed handoffs
  [orderflow_ledger] pass — 8 records validated
  [contracts] pass, [data_authority] pass, [leakage] pass
  [stale_state]/[provenance] not_built_yet (U-P3 / U-P7)
  unidesk checks: all green
```

## Honesty notes (the gap I did NOT close this slice)

The most important thing this slice is honest about: **net-of-cost is
still not on disk.** 0 of 11,591 calls (and 0 of 863,771 events) have
a non-null `net_bps`. The v4-net-cost stamp is real; the
`net_bps` field is not. The history export was deliberately built
to surface this gap (the "Net-of-cost numbers are not on disk yet"
warning panel) rather than silently fill in something fictional.

**Root cause (one-line summary):** `candidates.py::attach_outcomes`
looks up `adv_value` in the snapshot dict; the snapshot dict never
carries an `adv_value` key. The v3-regen and v4-regen both completed
with this code path, so every persisted outcome has `net_bps=None`
even though the writer code nominally populates it when `adv_value`
is present. The fix is to thread `adv_series` (added to
`build_future_map` in the v4 regen-aware driver commit) into the
freeze-scan snapshot, then make `attach_outcomes` compute `net_bps`
from `adv_series[session_index]` and the day's `close × 0.05 × volume`
order size. This is a small, contained change to two functions and
one new regression test, but it is its own wave — the History
wiring's done-test is "real outcomes render in the terminal," which
is now satisfied (with the honest caveat about net_bps).

**What the UI does about it:**
- The warning panel only renders when `OUTCOMES_META.netBpsCoverage === 0`
  (currently always). It cites the exact label version stamp and the
  exact coverage ratio. When the wire is fixed, the panel disappears
  with no UI change needed (the gate is data-driven).
- The `formatNetBps()` helper renders null as `—` (en-dash), the same
  way `rMultiple: null` already rendered as `—`. No special-case
  branch for "real data has no net"; the type system enforces the
  nullable shape.
- `c.note` from the export omits the "net" line when `net_bps is
  null`, so the row-level text doesn't claim net-of-cost facts the
  archive doesn't actually carry.

## Risks

- The export walks all 396 partitions on every invocation (~5min
  wall-clock on this machine). For nightly use, this is acceptable,
  but it is a 100x slower path than reading the 31MB JSON. If a
  later wave needs to read the export more than once per session,
  cache the JSON or switch the terminal to a runtime fetch.
- `outcomes_2026-08-28.json` is committed as a build-time snapshot,
  same convention as `tonight_2026-08-28.json`. There is no
  multi-date picker yet (UI plan row 5) — the next wave's job. When
  the picker lands, this slice's `_2026-08-28` filename convention
  will need to generalize to a session list (or the JSON gets
  regenerated nightly with the new date).
- The `_setup_type` helper iterates the detector map in dict
  iteration order (insertion order in CPython 3.7+), so the "primary
  detector" picked for each call is deterministic per the detector
  registry, but the registry order is also editorial (see
  unidesk/momentum/detectors/registry.py). A future wave that wants
  the "best by quality score" detector rather than "first by registry
  order" should change the iteration here. This slice keeps the
  registry-order rule because the v3/v4 waves both already publish
  the registry in that order; the export is just a faithful join.
- 5 / 11,591 calls (0.04%) have `rMultiple: null` and `outcome:
  "hit_target"` — these are PARTIAL or UNRESOLVED events that the
  outcome mapper classified as hit_target because `r_multiple < 1.0`
  was not present (the existing `_outcome_of` rule: stop_hit →
  stopped_out; else hit_target regardless of R). This is the
  pre-existing semantics from the v2-regen wave, not introduced by
  this slice; flagged for the next label-cleanup wave.

## Files

`unidesk/run_history_outcomes_export.py`,
`unidesk_terminal/src/data/outcomes_2026-08-28.json` (new),
`unidesk_terminal/src/data/outcomes.ts` (new),
`unidesk_terminal/src/data/fixtures.ts` (OutcomeCall interface),
`unidesk_terminal/src/screens/History.tsx`,
`unidesk/design/handoffs/HANDOFF_N4_HISTORY_REAL_DATA_WIRING_COMPLETED.md`
(this file),
`unidesk/design/MODEL_WORK_LOG.jsonl`.