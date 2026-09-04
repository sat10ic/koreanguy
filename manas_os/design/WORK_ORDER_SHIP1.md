# SHIP-1 WORK ORDER (Opus review x Fable counter-review, reconciled 2026-07-10)
Verdict at review time: 3/10. Items 1-6 ship-blockers; 7-9 ML/edge; 10-14 polish; 15-18 behind.
Executor: Sonnet batches; Fable verifies each against acceptance test. Full text lives in the
review transcripts; this file is the canonical checklist.

1. E1-PERSIST replay expectancy -> setup_expectancy (per-family n/hit/median R, passed-vs-refused; idempotent; LEARNINGS entry)  [x]
2. E2 proof on cards+ledger (base-rate chip w/ n, UNPROVEN below floor, never n/a when data exists)  [x]
3. Phantom run_card fix (no card on no-fresh-scan nights or no_op:true; /latest skips; stale header)  [x]
4. POSITIONS repair (journal_trades.qty migration, days-held/SL bindings, coach fallback not "unavailable", advisor_notes persist, dedupe exit text, fix HMR break)  [x]
5. Deterministic morning brief (template over run_card fields; shared formatter w/ strip; r4p5 as ratio; zero LLM tokens)  [x]
6. Near-miss selector: debate pool = soft-gate fails only; hard-fails listed on watchlist as NEAR_MISS(hard:gate), not debated; honest shrink  [x]
   2026-07-10: "regime" reclassified SOFT (RAIN case) — family bans are debated objections; hard set = tradability/risk.
7. I13 LightGBM+SHAP direction classifier (walk-forward only; labeled probability FACT + top-3 drivers; EXPERIMENTAL chip; never gates/sizes)  [x]
8. Screener-hit forward-return calibration (per-screener T+5/10/20 excess vs baseline, n-floored table)  [x]
9. Delivery% accumulation/distribution tag (rolling rising-delivery-on-up-days; fact chip + context line; lift logged before stronger role)  [x]
10. Telegram digest gains watchlist PROMOTE/DEMOTE + hard-fail count  [x]
11. MARKET "SECTORS UP" -> "LEAST DOWN" on all-red days  [x]
12. Gate-funnel exclusive first-failed-gate attribution (sums reconcile)  [x]
13. Mobile overflow: 375px no horizontal body scroll  [x]
14. DEALS: % of mcap + rank by it + de-emphasize known prop/HFT counterparties  [x]
15. I14 hierarchical-Bayes sector downside (empirical-Bayes ridge; EXPERIMENTAL column on MARKET)  [x]
16. I1 HAR-RV vol pillar (display-only until QLIKE pass logged)  [x]
17. I5 prep: causal backfill assertion test -> HMM trains on backfilled n>=150; label hidden until 20-session live agreement  [x]
18. Glossary density pass across all five tabs  [x]

Constraints (binding): one writer per metric; risk/plan.py sole money-math author; gate
thresholds LOCKED (6 changes selector only); every stat shows n + trust-ladder suppression.
