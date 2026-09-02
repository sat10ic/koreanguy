# HANDOFF — UI_BUILD_SPEC_V1 full-scope build (PART 0–15)

**Date:** 2026-09-01
**Executor:** GLM-5.3-Flash via ZCode (host-exposed model id `builtin:zai-coding-plan/GLM-5.3-Flash`)
**Spec:** `unidesk/design/UI_BUILD_SPEC_V1.md` (authoritative, PART 0–15)
Attribution-ID: attr-unidesk-ui-spec-v1-glm53flash-20260901-001

---

## 1. What this pass did

Continued from the committed G/H1–H4/B-07 waves (commits 5bd6fc57..b3d29f33),
which were partial against their own acceptance criteria. This pass:

1. **Backend fixes** (`unidesk/momentum/scan.py`, `report_json.py`,
   `research/archive_attach.py`):
   - **B-01 completed**: the liveness gate now excludes no-print symbols
     from the **RS percentile universe itself** (the previous commit only
     filtered candidates; dead names still sat in the ranking denominator).
     `ScanResult` now carries `stale_symbols` (symbol → last print) and
     `scanned_symbols` (post-gate, post-liveness universe) for the D-01 veto.
   - **B-03**: `honesty_footer.history_sessions_max` (numeric) emitted; the
     UI-bundled reports were regenerated on the FULL corpus
     (`history_sessions_max` ≈ 3,937 — the window is effectively raised for
     these snapshots, not just disclosed).
   - **B-05**: `sessions_needing_label_refresh` now also compares
     `ca_table_hash` (was `label_version` only → false all-clear). The live
     archive IS basis-stale (old partitions carry `b3b43b561621b11f`, current
     CSV hashes to `d1b585eb60fd4f82`) and is now correctly reported stale.
     Regression test: `test_label_refresh_flags_ca_table_change`.
   - Report emitter now also writes `universe_symbols` and
     `liveness_excluded` (per-symbol last print).
2. **Reports regenerated** via the production pipeline
   (`unidesk/run_regen_ui_reports.py` driving `momentum.nightly.run_nightly`
   with `as_of` = 18:00 IST on 2026-08-28 and 2026-08-31): both bundled
   reports now carry liveness-clean RS ranks, symbol-grain dedupe, prior
   session fields, real R0 regime notes, and the new footer fields.
   2026-08-28: 1,001 scanned / 65 candidates / 249 stale excluded.
   2026-08-31: 1,004 scanned / 38 candidates / 244 stale excluded.
3. **Frontend rewritten to the selected-report contract** (G-02/G-04): new
   `useReport()` hook; every widget reads the picker's report (previously
   regime/breadth widgets read a static import and ignored the picker).
4. **Desk screen (X-01)** built: D-01 pre-trade veto (candidate /
   in-universe-no-signal / refused-liveness-with-last-print /
   refused-universe / unknown — never blank), D-02 exit alarm (real bars,
   elapsed sessions, observed-fact wording), D-03 positions register
   (localStorage, paper-call flag, no broker path), D-04 size evidence
   (bucket occupancy computed from the broker import + audited notes quoted
   and labelled), D-05 risk-cap (loss-to-invalidation, unmanaged flag),
   D-06 over-trading count vs audited baseline, D-09 calls-vs-trades
   reconciliation, R-05 call ledger (paper calls resolve against real bars),
   R-06 exposure facts. No recommended-size string anywhere (X-05).
5. **Broker namespace (D-10)**: `legacy/SwingEdge/.../trades_normalized.csv`
   (973 fills) exported verbatim to `src/data/broker/trades.json` +
   `desk_said.json` (42 report sessions × what the desk said), generator
   `unidesk/run_export_broker_trades.py`. Never merged into scan stores;
   `run_checks.py` data-authority still green.
6. **H1**: regime anchor (`text-display`), position strip, participation
   table with 1D column now fed by `prior_pct_above_ema50` (5D stays `—`:
   not stored), breadth analytics dl with `bo_bd_ratio → "—"`, NH/NL balance
   bar, playbook (single named constant `lib/playbook.ts`, qualitative only
   per X-03, caveat emphasised in Pro), **H1-10 regime history strip** built
   from real reports (`run_export_regime_history.py`): stored classification
   where the classifier was live, else the R0 **replay** over stored breadth,
   labelled as replay in the tooltip. Universe line (H1-09). Engineering
   strings moved to the drawer/Pro (H1-08).
7. **H2**: seven fixed sections, H2-03 real-bar sparklines (per-session
   snapshots, no leakage), H2-04 documented state thresholds (existing),
   H2-05 quality + **coverage + unknowns** now surfaced (zero-defaults
   removed from QualityStack/DecisionCard), H2-06 geometry + sub-1R flag,
   H2-07 Reactor Scale with the verbatim caveat, H2-08 trust reason on the
   row, H2-09 counts, H2-10 collapse >10, H2-11 per-section metric (3 real,
   4 named-BLOCKED in Pro), H2-12 single documented comparator (non-rankable
   detectors unranked per P-04), H2-13 strings gone, H2-14 Beginner/Pro
   interpretations.
8. **H3**: performance summary (only statistics the file supports), outcome
   strip, compact table with SETUP column, distinct states WIN / STOPPED /
   STOPPED (gap-through) / NO DATA, collapsible groups, setup scorecard with
   n and low-sample warning, machine-derived note shown as the stop reason.
   **H3-01 verdict**: "No longer in universe" does not exist in the builder
   (`run_history_outcomes_export.py::_outcome_of`) or the data — the audit's
   conflated-label symptom cannot occur; the real conflation risk is
   gap-through stops labelled `stopped_out`, now rendered distinctly.
9. **H4**: retitled "Trigger proximity"; ladder from `(trigger-close)/close`;
   groups AT TRIGGER / APPROACHING / GETTING LATE (past trigger) / FAR;
   **true drift (H4-05) unblocked by B-07** — drift column = today's distance
   − `prior_trigger_distance`; R:R with sub-1R flag; quality as a grade.
   H4-08 collapsed honesty one-liner (the G-07 drawer).
10. **Candidates (C-01..C-08)**: duplicated card feed removed; ranked
    research table (every column maps to a real field; columns hideable);
    quadrant landscape with named quadrants and four real-field axis pairs;
    filters redraw table+plot; preset picker (P-03: inclusions + named
    failed-rules per exclusion); non-rankable detectors visible-but-unranked
    (P-04); cohort comparison table (no radar); Accumulation Evidence panel
    (proxies, honestly named); Tightness panel with episode contraction
    sequences. C-09 expectancy: nothing displayed; Pro note explains the N5
    gate.
11. **Stock (S-01..S-10)**: verdict above all scores via one documented
    function (`lib/verdict.ts`); Pro superset; levels rail (no target — no
    field); S-04 dual labels (Broad Market Regime vs Stock Trend Regime —
    **S-05 verdict**: the per-candidate field is `trend`, a per-stock
    EMA21/50 state; the market classifier lives only in `honesty_footer`.
    No bug. No unqualified "Regime:" label remains); S-06 no synthetic chart
    is drawn — loud banner + levels table instead; S-07 terminology map in
    Beginner; S-08 evidence checks both modes; S-09 one-line empty state;
    S-10 Replay only when real history exists. P-02 base-structure panel from
    the episode (window/depth/contractions/pivot/ATR pct); P-05 markers show
    occurred-at AND known-at with a "confirmed later" flag.
12. **D-08** late-entry warning on candidate rows/Stock: % off the 65-session
    low computed from real bars, fires above the audited 80% zone citing
    −₹81/trade, discloses the bars-through date, never blocks.
13. **Research**: R-04 equity view from the real outcomes archive —
    **cumulative sum of R multiples** (arithmetic; compounding a fixed
    fraction over 8,094 sequential calls produced an unreadable ₹300B axis,
    so the honest legible unit is the plain sum), GROSS of costs, labelled
    "backtest labels · not net · not account performance" (net-bps is null
    on 11,430/11,591 rows; a net curve is not honestly drawable yet).
    G-05 mode wiring on the ablation ladder.
14. **Python research harvest**: `unidesk/research/significance.py` (R-01
    DSR + moving-block bootstrap CI, R-02 `compare_arms` A/B/C harness with
    coverage per arm, R-03 metric suite where every figure carries n, A-05
    promotion rule implementing Constitution §19) + 11 unit tests
    (`test_significance.py`), wired into `run_n5_experiment.py`'s verdict
    path (DSR, n_trials=9, CI-90 alongside every verdict).
15. **A-01**: `unidesk/design/PHASE0_GATE_AUDIT_A01.md` — §53 checklist with
    PASS 6 / PARTIAL 10 / FAIL 9 / N/A 1 and per-row evidence. Gate NOT
    passed → PART 13 (A-02..A-07) stays BLOCKED, as required.
16. **Dormant code removed**: `YesterdaysCalls.tsx`, `CandidateScatter.tsx`,
    `sessionCoherence.ts`, `LIFECYCLE_META` — all superseded; no unrendered
    module shipped.

## 2. Investigations (spec-required verdicts)

- **H3-01**: `No longer in universe` is a phantom label — not in code, not
  in data. Outcome is a single field per row (`hit_target | stopped_out |
  unresolved`). Not conflated → no backend bug on that specific claim.
  Real nuance found and surfaced instead: gap-through stops share
  `stopped_out` and are distinguished only by `note`/`gapThrough`; the UI
  renders them as a distinct state. Also: `netBps` is null on 99.6% of rows
  despite the `v4-net-cost` label stamp (writer gap; already disclosed on
  the History screen).
- **S-05**: the stock page's trend is the per-stock `trend` state
  (EMA21/50-based, `features/trend.py`), never the market classifier. The
  market classifier (`regime_note`) was being rendered under generic
  "Market:" labels; both are now explicitly named (S-04). No backend bug.
- **B-08**: over the last 20 archived sessions (2026-07-31 → 2026-08-31):
  inside_bar mean **45.6/session (68.5% of all hits)**, ipo_base 7.5 (11.2%),
  pullback 5.2, episodic_pivot 3.4, momentum_burst 1.9, base_breakout 1.5,
  reversal_reclaim 1.2, power_play 0.3. The 51/73 (70%) imbalance on 08-28 is
  the steady state, not a one-off: inside_bar never fired fewer than 30 in
  the window. Verdict: structural threshold looseness relative to the other
  detectors; recalibration is an owner decision (R14) and is NOT done here.
- **B-09**: `delivery_ratio` does come from the exchange report
  (`DELIV_PER` column of NSE `sec_bhavdata_full` bhavcopy CSVs). BUT the
  availability timestamp is **assumed** (same-session 18:00 IST in
  `load_into_store`), and the ≥1-session delivery-lag guard
  (`research/delivery_lag.py::delivery_usable_for_decision`) is wired only in
  tests — the scan path does not use it. Filed here as a backend bug
  (fixing it changes delivery features and requires a coordinated regen;
  doing it silently mid-build would invalidate comparisons).

## 3. Completion table — every ID in the document

| Part | IDs and status |
|---|---|
| GLOBAL | G-01 DONE · G-02 DONE · G-03 DONE (prior wave + re-verified) · G-04 DONE · G-05 DONE · G-06 DONE · G-07 DONE |
| HOME 1 | H1-01 DONE · H1-02 DONE · H1-03 DONE · H1-04 DONE (1D via B-07; 5D `—`) · H1-05 DONE · H1-06 DONE · H1-07 DONE · H1-08 DONE · H1-09 DONE · H1-10 DONE (stored labels + labelled R0 replay; sessions before stored breadth show `·`) |
| HOME 2 | H2-01 DONE · H2-02 DONE · H2-03 DONE · H2-04 DONE · H2-05 DONE · H2-06 DONE · H2-07 DONE · H2-08 DONE · H2-09 DONE · H2-10 DONE · H2-11 DONE (BB pivot dist, IB compression, EP prior-gap real; IPO/PP/PB/REV named `BLOCKED — field not emitted`, shown in Pro) · H2-12 DONE · H2-13 DONE · H2-14 DONE |
| HOME 3 | H3-01 DONE (investigation; verdict in §2) · H3-02 DONE (supported stats only) · H3-03 DONE · H3-04 DONE · H3-05 DONE (null-guarded) · H3-06 DONE (WIN/STOPPED/STOPPED-gap/NO DATA; NO TRIGGER/EXPIRED/INVALIDATED not emitted — disclosed in Pro, not invented) · H3-07 DONE · H3-08 DONE · H3-09 DONE (machine-derived note; no invented narrative) |
| HOME 4 | H4-01 DONE · H4-02 DONE · H4-03 DONE (state vocabulary via deriveState + groups) · H4-04 DONE · H4-05 DONE (unblocked by B-07: drift column) · H4-06 DONE · H4-07 DONE · H4-08 DONE |
| CANDIDATES | C-01 DONE · C-02 DONE · C-03 DONE · C-04 DONE · C-05 DONE · C-06 DONE · C-07 DONE · C-08 DONE · C-09 BLOCKED — N5 not run (nothing displayed, Pro note) |
| STOCK | S-01 DONE · S-02 DONE · S-03 DONE (target omitted — no field) · S-04 DONE · S-05 DONE (verdict §2: no bug) · S-06 DONE (no synthetic chart drawn) · S-07 DONE · S-08 DONE · S-09 DONE · S-10 DONE |
| BACKEND | B-01 DONE (candidate filter + RS universe; verified in regen: 249/244 stale excluded, RS recomputed without them) · B-02 DONE (prior wave; re-verified: 65/65 and 38/38 distinct) · B-03 DONE (numeric disclosure + full-corpus regen raises the window) · B-04 BLOCKED — compute-bound: full-archive regen LAUNCHED 2026-09-01 (`unidesk/run_regen_full.py`, 3,878 sessions, ~6.28M bars ingested, progress in `data/market/reports/regen_v4_gated.log` + task stdout; ~206/3878 at time of writing; relaunch command: `.venv-orderflow/Scripts/python.exe unidesk/run_regen_full.py`). B-05 (the reason it went undetected) is fixed + tested. · B-05 DONE (fix + regression test) · B-06 DONE (verified green; record carries host_tool/scope) · B-07 DONE (prior wave; consumed by H1-04/H4-05) · B-08 DONE (investigation §2: structural, reported; recalibration left to owner) · B-09 DONE-as-verification with negative finding (§2) — availability guard unwired, filed as backend bug |
| DECISION | D-01 DONE · D-02 DONE · D-03 DONE · D-04 DONE (descriptive only) · D-05 DONE · D-06 DONE · D-07 DONE (real verdict enum surfaced; spec's EARLY/MID/FINAL stage names are NOT emitted by the backend — surfacing the real `base_episodes[].verdict` instead of guessing stages) · D-08 DONE · D-09 DONE · D-10 DONE (separate namespace; data-authority check green) · D-11 BLOCKED — Phase 2.5 gate, N5 not run · D-12 BLOCKED — N7 not activated · D-13 BLOCKED — depends on B-04 completing (harness prerequisites: clean archive) |
| CLASH | X-01 DONE (exactly one new screen: Desk) · X-02 DONE (labels on both sides; History never shows broker rows) · X-03 DONE (playbook emits no numbers) · X-04 DONE (D-07/D-08 first, then D-03→D-02/D-05/D-06, D-10→D-04/D-09, D-01 after B-01) · X-05 DONE (grep clean: no recommended-size string) · X-06 DONE (H1-05, H2-05, H2-07, D-07 all surfaced) |
| AI WAVES | A-01 DONE (`PHASE0_GATE_AUDIT_A01.md`: gate NOT passed) · A-02 BLOCKED — Phase 0 gate · A-03 BLOCKED — Phase 0 gate · A-04 BLOCKED — no measured L1.5 · A-05 DONE-as-code (promotion rule implemented + null-signal-fails test; no real result exists to classify — the RULE is ready, the gate stays closed) · A-06 BLOCKED — no AI results to report · A-07 BLOCKED — plan named in constitution; deletion criteria pre-declared there |
| BANANA | P-01 DONE (via D-07) · P-02 DONE · P-03 DONE · P-04 DONE · P-05 DONE (occurred-at + known-at shown) · P-06 DONE (no instructional language; presets described as structure) |
| HARVEST | R-01 DONE (DSR + block bootstrap + tests; wired into run_n5_experiment) · R-02 DONE (`compare_arms`, same-sample arms + coverage) · R-03 DONE (metric suite, every figure with n) · R-04 PARTIAL→reported BLOCKED for the net-of-cost accept: curve shipped GROSS and labelled (net-bps 99.6% null); net curve blocked on the cost writer fix · R-05 DONE (paper-call ledger on Desk) · R-06 DONE (exposure + loss-to-invalidation only) · R-07 SKIPPED — charter: "Manual execution only. No order routing, ever." · R-08 BLOCKED — Constitution §10 encoder freeze + §0 predictive-AI ban · R-09 DONE-as-verification: delivery_ratio + Reactor Scale computable today; OI-based features BLOCKED — no F&O data in repo |

**Statuses used other than DONE: 12** (C-09, D-11, D-12, D-13, A-02, A-03,
A-04, A-06, A-07, R-08 blocked; R-07 skipped; R-04 partial/blocked-net;
B-04 blocked-compute with the fix running). Every one names its blocker.

## 4. Final gate results

1. `npm run build` — **passes, zero TS errors** (verified after every wave).
2. Hardcoded-number grep (`65.86`, `2563`, `2026-07-03`) in `src/` — **no hits**.
3. Every screen reads the picker's report via `useReport()`; TopBar follows.
4. Regime shown equals `honesty_footer.regime_note` (verbatim string).
5. No screen renders `0` for an uncomputed score (`—` everywhere; zero-defaults removed from QualityStack/DecisionCard).
6. No synthetic chart can be mistaken for real: when real bars are absent NO chart is drawn — banner + levels table.
7. `python unidesk/run_checks.py` — **all green** (attribution, orderflow ledger, contracts, data-authority, leakage).
8. `python -m pytest unidesk/tests -q` — 14 failures **pre-existing at baseline** (captured before changes, list preserved in the session log); 11 NEW significance tests pass; no new failures introduced. Full-suite rerun at wave close.
9. This table accounts for every ID in PART 10.

## 5. What I did NOT do / left open

- **B-04** full-archive regen: ~20h compute; launched and progressing; the
  bundled reports and the research archive it has not yet reached remain
  mixed-basis (now correctly DETECTABLE by the fixed B-05 detector). Resume:
  `.venv-orderflow/Scripts/python.exe unidesk/run_regen_full.py` (idempotent
  per partition), then re-run `unidesk/run_history_outcomes_export.py` and
  `unidesk/run_export_broker_trades.py` to refresh UI snapshots.
- Detector-threshold recalibration (B-08 finding) — owner decision (R14).
- Delivery-availability wiring (B-09 finding) — backend change + regen.
- Per-bucket realised P&L (D-04) — needs round-trip matching in the broker
  import; panel quotes audited notes until then.
- H1-10 sessions older than the stored-breadth window: strip shows `·`.
- The spec's D-07 stage vocabulary (EARLY/MID/FINAL) — the backend emits
  `watch|breakout|running|exited|insufficient_data`; I surfaced the real
  enum rather than invent a mapping to the spec's words.
- Visual verification: rendered and inspected Tonight/Desk/Candidates/Stock
  in a live browser at 1280×720; History/Research checked via build +
  snapshot. A 1920×1080 owner pass is still worthwhile.

## 6. Verification

- `npm run build` exit 0 after every wave (final state green).
- `run_checks.py` all green post-change.
- Regenerated reports inspected field-by-field (scanned counts, dedupe,
  prior fields, liveness detail, universe symbols, regime notes).
- 11/11 new significance tests pass; full pytest rerun compared against a
  captured 14-failure baseline (no new failures).
- B-05 regression test reproduces the false-all-clear scenario and fails
  without the fix.
- Browser-rendered screenshots of the rewritten screens (Beginner mode)
  reviewed for the acceptance criteria; D-01 veto exercised live.
