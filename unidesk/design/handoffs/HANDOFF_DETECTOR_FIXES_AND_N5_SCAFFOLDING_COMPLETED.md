# HANDOFF — Trading-logic detector fixes + N5 experiment scaffolding — COMPLETED

Date: 2026-08-31. Pickup of the uncommitted working tree that HANDOFF.md and
HANDOFF_FIXES_AND_FORWARD_PLAN_REVIEW_COMPLETED.md flagged but left unowned.
Scoped strictly to detector input/output, the new experiment/scorer modules,
and the one failing truncation-invariance fixture the prior review surfaced.

Attribution-ID: attr-unidesk-detector-fixes-n5-scaffolding-claude-sonnet5-20260831-001

## What was in the working tree at pickup (verified by direct diff, not assumed)

A diff against `HEAD` (`6ae5ae17`, "Settings/trust/leak-guard") showed ~479
lines of working-tree changes across the detector module, scoring module,
test files, and supporting fixtures. Two clear buckets:

**Bucket A — Trading-logic fixes for the 2026-08-30 audit findings.** The
deep review (Opus, see HANDOFF_FIXES_AND_FORWARD_PLAN_REVIEW_COMPLETED.md)
flagged four classes of defect; this slice closes three of the four:

1. `pullback` anchor-proximity had no direction (a stock 2.5% above EMA21
   satisfied a rule meant to require a decline). Fix: `compute_setup_inputs`
   now emits BOTH `pullback_signed_anchor_pct` (signed distance from EMA21)
   AND `pullback_from_high_pct` (decline from trailing-10 high). The
   detector consumes the signed value plus the decline as gating rules.
   Regression: `test_detector_logic_fixes.py::test_pullback_rejects_stock_extended_above_anchor_without_decline`
   — fails against the old code, passes against the new.

2. `reversal_reclaim` compared past closes to TODAY'S EMA21 (collapsing the
   detector into a continuation screen — past closes were routinely below
   today's higher EMA21, manufacturing a fake "reclaim" every day in
   uptrends). Fix: each window session now uses ITS OWN EMA21 value from
   `compute_setup_inputs`, gated on the EMA21 series being fully warmed up
   for every session in the window. Unresolved (None) when the warm-up is
   incomplete — never a guess off a half-formed average.

3. `momentum_burst`'s anti-chase AVWAP guard was structurally inert because
   `avwap_extension_adr` was always None. Fix: `compute_setup_inputs` now
   anchors to the swing-low session over the trailing 40 bars and computes
   cumulative typical-price × volume from that anchor, with extension
   measured in ADR units. Unresolved (None) below a 20-session history or
   when ADR / cumulative volume are unavailable — never zero-filled.

`base_breakout` (audit finding #1 — the inverted room rule) is already
committed (`fef0841f` / `cb67bc91`); the trust table reflects the corrected
behavior in REVIEW_REQUIRED with `pending_reaudit` reason strings. This
slice did not change it.

**Bucket B — N5 experiment + scorer scaffolding** (the modules HANDOFF_N5*
keeps referring to as "still in progress" without owning them):

- `unidesk/momentum/detectors/ep_signature.py` — T5 S_ep signature
  (5-component deterministic composite, circuit_ep + climax_on_climax
  guards explicit, never zero-filled).
- `unidesk/momentum/scoring/tightness.py` — S_tight coil-quality scorer
  + `contraction_sequence` (spec §1.5: each subsequent pullback ≤ 0.75 ×
  the previous).
- `unidesk/research/experiments.py` — Experiment A/B verdict engine
  (book_stats + compare_edge with KEEP_CANDIDATE / BASELINE_WINS /
  INSUFFICIENT_N verdicts).
- `unidesk/run_gold_reharvest_bb.py` — gold fixture re-harvester for the
  corrected base_breakout room rule. READ-ONLY over the bhavcopy archive;
  the only file it writes is the gold fixture JSON itself.

Each module has its own test file. Pre-fix the test suite had 273 + 21
skipped; this slice lands **+41 tests passing**, **+2 skipped** in
truncation-invariance (avwap special-case skip still honored). Net: 314
passing, 23 skipped.

## What this slice changed directly

**Fixed one failing truncation-invariance test.**
`test_truncation_invariance[...contraction_sequence]` was the failure
HANDOFF.md called out as "flagged for whoever owns that slice." Direct
read showed the test fixture `[8.0, 6.0, 4.5, 3.4, 2.6]` does NOT satisfy
the rule it claims to demonstrate — `3.4 > 0.75 × 4.5 = 3.375` and
`2.6 > 0.75 × 3.4 = 2.55`. Replaced with `[8.0, 6.0, 4.0, 3.0, 2.0]`
(ratios .75, .667, .75, .667 — every step genuinely ≤ 0.75 × previous,
boundary inclusive). The implementation (`all(d2 <= ratio * d1 for ...)`)
was correct against the spec — the test data was simply wrong. **The
spec at plan/SWING_EDGES_TECHNICAL_SPEC.md:193 is `each depth ≤ 0.75 *
previous`**, matches implementation, no behavior change.

## What this slice did NOT do

- Did NOT commit `unidesk/research/archive_attach.py` /
  `unidesk/run_archive_attach_resume.py` / STATE.json — those changes are
  part of the **separate** v4-regen story (still in flight; the live
  processes PIDs 31472 + 5036 are stuck, see HANDOFF.md To-continue).
  Committing them now would mix a detector-fixes wave with an open regen
  story and break the per-wave attribution.
- Did NOT commit `unidesk/design/handoffs/HANDOFF_N4_ARCHIVE_REGENERATION_COMPLETED.md`
  (untracked in the working tree). That file's claim "zero of 863,771
  events have label_version != OUTCOME_LABELS_VERSION" was true when it
  was written (v2-regen had just completed), but a follow-on v4 bump +
  v4-regen happened, and the file now misrepresents current store state
  (12 sessions / 30,314 events still on v2-stop-aware at this writing).
  Stale, not committed; flagged for the v4-regen cleanup wave.
- Did NOT touch `unidesk/HANDOFF.md` itself — its To-continue block is
  still the right shape (History wired only after store settle; regen
  cleanup is its own wave). The HANDOFF.md To-continue is owned by the
  v4-regen-cleanup wave that resolves the live-process issue.

## Verification (measured, not claimed)

```text
pytest unidesk/tests -q --no-header
  314 passed, 23 skipped in 211.49s (0:03:31)
  (target tests all in scope: detector logic fixes, experiments/ep,
   truncation-invariance tightness case, full regression suite)

pytest unidesk/tests/test_detector_logic_fixes.py \
       unidesk/tests/test_experiments_ep.py -q
  23 passed in 0.28s

python unidesk/run_checks.py
  [attribution] pass — 67 records, 43 completed handoffs
  [orderflow_ledger] pass — 8 records validated
  [contracts] pass — 12 contracts import; flow+decision round-trip; enums fail closed
  [data_authority] pass — 20 stores owned/classified
  [leakage] pass — planted future-bar leak is caught
  [stale_state] not_built_yet (owed by U-P3)
  [provenance] not_built_yet (owed by U-P7)
```

## Direct store readback (separate concern, also verified this session)

The two concurrent regen processes (PIDs 31472 + 5036) are alive but
NOT advancing — newest partition mtime 14+ hours old, 30-sec sampling
identical across two snapshots. 12 of 396 partitions still carry v2
events; the contention between the two writers is the apparent hang.
This slice does NOT touch the regen; a separate wave must kill the
duplicates and restart a single clean pass before History wiring is safe.

## Files

`unidesk/momentum/detectors/inputs.py`,
`unidesk/momentum/detectors/setups.py`,
`unidesk/momentum/detectors/registry.py`,
`unidesk/momentum/detectors/trust.py`,
`unidesk/momentum/detectors/ep_signature.py` (new),
`unidesk/momentum/scoring/tightness.py` (new),
`unidesk/research/experiments.py` (new),
`unidesk/run_gold_reharvest_bb.py` (new),
`unidesk/tests/test_detector_logic_fixes.py` (new),
`unidesk/tests/test_experiments_ep.py` (new),
`unidesk/tests/test_truncation_invariance.py` (fixture fix),
`unidesk/tests/fixtures/p2_3_gold.json`,
`unidesk/tests/test_detectors_geometry.py`,
`unidesk/tests/test_report_json.py`,
`unidesk/design/handoffs/HANDOFF_DETECTOR_FIXES_AND_N5_SCAFFOLDING_COMPLETED.md`
(this file).

## Next slice

The v4-regen cleanup wave: kill PID 5036 + PID 21808 (the duplicate /
dead-stuck python processes), let PID 31472 finish the remaining 12
stale sessions, then verify all-v4 from disk. Only after that can
History wiring proceed.