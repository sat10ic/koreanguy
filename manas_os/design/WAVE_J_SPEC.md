# WAVE_J_ENTRY_QUALITY — Design Spec

**Status:** DESIGN (feeds a Sonnet implementation wave)
**Author:** senior quant/design review (Opus), 2026-07-10
**Scope guard (LOCKED):** No gate/plan threshold in the current cascade changes in this
wave. WAVE_J builds counterfactual detectors + replay evidence only. A threshold moves only
in a later, separate decision after the §3 bar clears. One writer per metric. Refusal-first
identity stays — every new rule = a named refusal, never a score nudge.

## 0. Goal
Gate-passed cohort has no edge (n=55; median managed R ~ -1.05 under every exit variant;
93-100% stop-out; MFE mostly never favorable; 29% never traded above their own pivot).
Exit levers exhausted (E-A..E-D). The detectors decide WHICH names enter — the only
remaining lever. WAVE_J redesigns entry quality as testable, replay-validated refusals
encoding the Arora methodology the detectors were supposed to encode but don't.

## 1. DIAGNOSIS
1.1 LOAD-BEARING BUG: candidate_for_symbol passes breakout_age=None (candidates.py ~792);
    gate_fresh_leg's staleness check and FRESH_BREAKOUT/FRESH_PULLBACK state machine are
    both gated on breakout_age is not None -> the tool's ONLY anti-staleness/anti-chase
    machinery is dead code in production; every survivor tags fallback "FRESH". Nothing
    stops entries mid-to-late in a leg.
1.2 Entry = static prior-20-day-high pivot, filled unconditionally next-open. Nothing
    requires close to be near the pivot from below -> names 6% below their pivot "enter"
    at a price never crossed. This IS the E-B finding: 16/55 (29%) never traded above
    their pivot — mechanical artifact, opposite of Arora's confirmation entry.
1.3 NO compression precondition. Tightness Study: >80% of real Strong-Start wins had an
    extremely tight previous day. Zero RMV/tightness requirement in the cascade ->
    population dominated by uncoiled names -> the MFE-never-favorable signature.
1.4 Close-based detectors assume next-day continuation but check no trigger-day quality
    (gap size, low holding above prior close, close position in range); participation's
    breakout-day volume check only runs for pocket_pivot/ep — most families get none.
1.5 Arora's "4th green day" hard disqualifier not encoded anywhere; persistency and the
    RMV 9-greens guard exist in manas_indicators but are unwired.
1.6 mswing (vs index) and burst_power (climax exhaustion) ported+tested, never consulted.
Flaw class: the cascade filters STRUCTURE and STRENGTH but never TIMING and COIL.

## 2. REDESIGN — hypotheses (each a named refusal; a-priori thresholds from Arora source;
##    live only in counterfactual replay until §3 clears). Ranked H1~H2 > H3 > H4 > H5 > H6.
- H1 Compression-first: eligible only if trigger-day rmv rank<=2 OR (rmv<=15 AND
  (tightness_setup OR vdu_setup)). Targets the coil gap; most likely to move MEDIAN.
- H2 Leg-freshness: refuse persistency(10EMA) count >= 8 (STALE_COUNT=8 a priori); HARD
  refuse 4th-or-later consecutive green day. Fixes 1.1 the right way + encodes 1.5.
- H3 Buy-stop default fill: trade exists only if a session actually trades above the
  pivot (exit_variants.find_entry_bar buy_stop); else NON-TRADE (not a loss). Removes the
  29% phantoms; measured on hit_1r% + trade count, not median (E-B showed median flat).
- H4 Trigger-day quality (EOD Strong Start proxy): strong_start True AND gap<=5% AND
  close-in-upper-half AND volume state in {bull_pp, high_up} or range-expansion — for ALL
  families.
- H5 mswing filter: refuse color in {down, neutral_negative} vs index. Likely overlaps RS.
- H6 Burst exhaustion: refuse count_19>=1 OR rounded>=8. Guard/evidence chip only.

## 3. VALIDATION PROTOCOL
3.1 New backtest/entry_variants.py (pure) composing refusals over trigger-day bars with
    walk_managed_exit (exit modeling unchanged -> entry effects isolated). Driver =
    repo-root scratch script mirroring _gate_recal_evidence.py.
3.2 Same 285-session window; NO fitted parameters (thresholds a priori) — walk-forward =
    per-month OOS reporting, not refitting. SELECTIVE/DEFENSIVE reported separately;
    RISK_ON/momentum = unmeasurable, say so.
3.3 Cells (family x regime x variant); trust floor n>=30; 20-29 directional; <20 thin.
3.4 SUCCESS BAR to PROPOSE (not make) a threshold change — all four, in a n>=30 cell:
    (1) median managed R >= +0.3R; (2) hit_1r% >= 33%; (3) paired: kept cohort beats
    current passed median by >= +0.5R AND removed cohort <= kept cohort (refusal removes
    the worse names, not random thinning); (4) replicated across two disjoint sub-windows
    (2025-03..12, 2026-01..07), same sign, both medians >= 0.
3.5 Negative results are valid and logged (like HMM 18.8%). Never tune to force a pass.

## 4. OVERFITTING TRAPS (binding)
1. Never tune thresholds on the 55 trades — evaluation only.
2. Multiple comparisons: pre-registered ranking privileged; prefer the coherent H1+H2+H3
   bundle over cherry-picking the best single scorer; two-window replication mandatory.
3. Regime-window bias: one 16-month SELECTIVE/DEFENSIVE tape; never extrapolate to
   families/regimes with zero survivors.
4. Survivorship: shrinking to a luckier small cell != edge (n floor + removed-cohort test).
5. Median and hit_1r% are the bar; mean can be tail-flattered (E-A/E-C lesson).
6. No WAVE_J metric wires into risk/plan.py, sizing, chair, debate, or rank — eligibility
   refusals + evidence chips only. Grep-verify.

## 5. TASKS
J1 scanner/entry_quality.py (one writer): rmv_eligible, leg_fresh, strong_start_quality,
   mswing_ok, burst_exhausted — each {"pass","reason","evidence"} in gates.py _gate shape;
   thresholds as constants citing the Arora source; unit tests per branch.
J2 backtest/entry_variants.py (pure): apply_entry_refusals(trigger_bars,index_bars,
   hypotheses)->{"eligible","failed"}; compose w/ walk_managed_exit(buy_stop); no
   look-ahead; reproduction guard test (empty set + next_open == E1 baseline exactly).
J3 driver _wave_j_entry_evidence.py (scratch): variants {baseline,H1,H2,H3,H1+H2,
   H1+H2+H3,+H4,+H5,+H6}; per-(family x regime) tables (n, stopout%, avgR, medR, avgMFE,
   hit_1r%) + removed-cohort tables + two-sub-window replication. Print, don't persist.
J4 LEARNINGS.md entry: all tables, 5-line verdict, explicit §3.4 pass/fail per hypothesis.
   If cleared -> phrased as proposal for a later threshold wave; else honest negative.
J5 (conditional on J4 pass) design/WAVE_J_THRESHOLD_PROPOSAL.md — exact gates.py/
   candidate_for_symbol change + before/after numbers + QC checklist. NOT implemented here.
J6 (do now, low-risk latent-bug fix): wire a real computed leg-age (persistency count or
   bars-since-pivot-cross) into the cascade AS EVIDENCE ONLY (refusal thresholds
   unchanged) so the live refusal ledger records real leg-age. Flag in LEARNINGS.

Key files: scanner/gates.py (fresh-leg dead when breakout_age=None), scanner/candidates.py
(~249/278/739/792/793), engine/eod_detectors.py, engine/manas_indicators.py (all wired
here for the first time), backtest/exit_variants.py + replay.py, design/agents/
LENS_STRONG_START.md + study 6 Manas Entry.md + Strong_Start_Tightness_Study.md,
design/LEARNINGS.md.

Bottom line: the loss is an entry-POPULATION defect — structure filtered, timing and coil
never. H1+H2 most likely to move the median; H3 cheap and removes phantoms. Counterfactual
evidence against the §3.4 bar across two sub-windows; no LOCKED threshold moves until
cleared and re-QC'd.
