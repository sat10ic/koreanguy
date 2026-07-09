# WAVE I — Edge adoptions from the 23-repo audit (2026-07-10)

User directive: edge/alpha first, nothing off limits, coherence the only constraint.
Audit method: 4 parallel reviewers over all 23 repos. 15/23 = homework/empty (named in
audit logs). 8 carried something. Adoption list below, ranked by expected edge per effort.
Every adoption = ONE new writer module + replay-harness validation before it gets a vote
(trust ladder unchanged). Nothing replaces the deterministic gate or the XP/MBI engine —
these are additional pillars/inputs.

## I1 — HAR-RV volatility pillar  [source: CuriousObservator/LSHAR-model, methodology]
- New regime/vol_har.py: HAR-RV forecaster (daily/weekly/monthly RV terms) on NIFTY
  returns + India VIX level → next-5d realized-vol forecast + rising/falling band.
- Wires: regime_snapshot gains vol_forecast field; context_pack regime block cites it
  ("vol forecast: rising, 14→17"); governor MAY later consume it (only after validation).
- Validation: replay 300+ historical sessions, QLIKE vs naive lag baseline; log to
  LEARNINGS.md. Until pass: display-only, marked "experimental".
- LS-periodogram augmentation: SKIP (their own numbers show thin edge).

## I2 — Accuracy-weighted debate (DebaterTracker concept)  [tradingagents-india]
- We already store per-model track records (agent_verdicts.outcome_r + track-record
  endpoint). Chair aggregation gains a weight per model = shrunk hit-rate (same k=25
  shrinkage as expectancy). Deterministic — no LLM change. Weight floor 0.5/cap 1.5 so
  no model is silenced or deified on thin n.
- Validation: weights activate only when a model has n>=40 scored verdicts; until then
  all weights 1.0. Test: fixture where model A n=60 hit 0.7 vs B n=60 hit 0.3 shifts a
  2-1 split.

## I3 — FinBERT sentiment on disclosures  [Vegapunk pattern, reimplemented]
- New sources/sentiment.py: local FinBERT (CPU) scores corporate_announcements headlines
  per symbol per day → announcement_sentiment table (score -1..1, n_items).
- Wires: context_pack per-symbol block gains "news/announcement sentiment: +0.6 (3 items)"
  — a FACT for the debate, never a composite score. Desk: chip on debate cards.
- Validation: spot-audit 30 scored headlines by hand before enabling in prompts.
- Dependency note: transformers+torch CPU — heavy install; keep optional
  (skip stage gracefully when not installed).

## I4 — FII/DII conditional read  [hte-1313/fii-dii-market-ml concept]
- Extend fii_dii ingest analytics: discretize daily FII/DII into buy/sell/neutral bands;
  compute historical P(DII response | FII action, regime mode) from our own stored
  history; context_pack market block gains one line ("FII selling 3d, DII absorbing —
  historically 68% of such days in SELECTIVE resolved flat/up in 5d, n=41").
- Deterministic counting, no PyMC. Suppress line when n<20 (trust ladder).

## I5 — HMM regime confirmation gate (deferred trigger stands)  [shreyasfegade/regime
  feature set + CC-Shivansh-Gupta fitting discipline]
- Build ONLY when regime_snapshots history >= 150 sessions of live-computed XP/MBI (per
  plan). regime/regime_hmm.py: 4-state GaussianHMM, features = log return, 5d/20d vol,
  volume z, 10d momentum; 10 random restarts; fold-scoped scaling; walk-forward refit.
  Emits a CONFIRMING label alongside (never instead of) XP/MBI mode.
- MIT source for reference; reimplement, adopt-not-import.

## I6 — Design hygiene (no new features)
- PSI drift check on lesson digest (Vegapunk pattern): monthly stage flags when lesson
  base distribution vs last quarter shifts (stale lessons warning on desk).
- Soft posterior gating (portfolio-advisor): EXPERIMENT NOTE only — gates keep LOCKED
  hard thresholds; revisit after E1 shortlist experiment.

## Industry classification (user preference: ChartsMaze/NSE-official mapping)
- Audit found NO repo carrying NSE's 4-tier classification. Route: NSE master sources
  directly (equity master / index constituents; nsepython library as fetch helper) →
  nse_classification table; ChartsMaze daily mapping stays primary, NSE-official becomes
  the authoritative fallback + drift check between the two. Fold into the ETF-master-list
  task (same NSE master-file fetch).

## Explicit rejections (logged so we don't re-litigate)
- Composite score patterns (AI-trader 0.5/0.3/0.2 blend) — banned anti-pattern (AD8).
- Deep temporal clustering (radhikakumar0705) — black-box layer over a working breadth
  engine; took only its feature checklist + regime-conditional eval pattern.
- Intraday scalping (suprabhat-ai), F&O/tick systems (AI-trader) — wrong timeframe/asset.
- AGPL code (nse-portfolio-risk-scanner) — patterns only, no code copy.

Order: I2 (cheapest, uses existing data) → I4 → I1 → I3 → I6 → I5 (gated).

## Batch-5 additions (10 more repos audited 2026-07-10; 4 homework, 6 useful)
- I7 Portfolio circuit breakers [NeilNowgaonkar concept]: daily-loss halt (-2.5% day => no
  new entries), drawdown pause (-8% => 10-session cooling), max concurrent positions —
  enforce in risk/plan.py validate() + surface as a desk banner. We have per-trade and
  open-risk caps; these are the missing PORTFOLIO-level brakes.
- I8 Slippage-aware walk-forward [harsh1201 methodology, reimplement — no license]:
  replay harness gains slippage+cost model and concurrent-position accounting so
  expectancy numbers stop assuming frictionless fills.
- I9 ATR sanity-bound [asircar]: cross-check our stop distance vs entry-1.2*ATR and
  targets vs 1.5/2.5*ATR as a WARN chip (never a writer — risk/plan.py stays sole author).
- I10 Alert capping/UX [surajpattewar]: top-N + MIN_SCORE caps already exist via governor
  digest caps — adopt only the "position tracker sheet" idea as a desk export button (CSV).
- EXPERIMENT ONLY: ICT order-block/FVG detection [aryashreep] — backtest via replay before
  any gate role; candlestick pattern math [deshwalmahesh] — low priority.
- Industry-classification special interest: came up EMPTY across all 10 — NSE master-file
  route stands.

## H1.1 calibration result (2026-07-10, logged for LEARNINGS)
volume-spike: universe-restricted Jaccard 0.92/0.86-0.91/0.82-0.90 across 3 comparable
sessions at multiplier=3 (median 0.905 — MEETS the 0.90 bar; raw jaccard 0.33 confirms
the gap is universe scope, not formula). Caveat: only 3 distinct sessions in the archive
window — acceptance requires 15; nightly dumps accumulate ~1 comparable session/day, so
formal acceptance ~3 weeks out. Multiplier 3x locked as the working default meanwhile.

## Batch-6 + ML re-audit additions (2026-07-10, steelman rubric — code quality separated
## from idea quality per user correction; every ML technique got a test plan)
Ranked, with effort:
- I11 (S) Capital-allocation tiering [alpha-command, Minervini exposure model]: health
  score -> 6 exposure tiers (0/15/35/55/75/90% deployed) + VIX penalty + grade-based size
  multipliers. Near copy-paste onto our XP/MBI score + governor; gives the desk a daily
  "deploy X% / cash Y%" number. Complements I7 circuit breakers.
- I12 (S-M) Composite-Z institutional accumulation filter [ombhojwani11 methodology; core
  thresholds redacted in repo — we derive our own]: Z(delivery%) + Z(FII/DII flow) rolling
  20/60d -> COMPOSITE_Z; test "N consecutive days > 1.0" as entry evidence via replay.
  Raw ingredients all in our DB already.
- I13 (M) LightGBM directional classifier w/ SHAP [stocksense architecture]: features =
  delivery%, FII/DII, sector-RS, breadth regime, bulk/block flags; target = fwd-N return
  sign / trust-ladder hit; validation = walk-forward replay ONLY (no k-fold). SHAP output
  becomes explainable evidence, never a hidden score (AD8 respected: model output is a
  labeled probability FACT in context_pack). Follow-on I13b (S): drift-triggered retrain.
- I14 (M) Hierarchical Bayesian partial pooling on sector downside risk [fii-dii-market-ml
  deep dig]: panel (sector, day), predictors {FII_z, DII_z, imbalance, VIX chg, sector
  RV20} -> fwd-5d sector drawdown event; sector intercepts partially pooled (exactly right
  for 490 days / 11 sectors thin cells). Empirical-Bayes ridge approximation acceptable to
  avoid PyMC dependency.
- I15 (M) Offline contextual-bandit policy evaluation [same repo]: replay Thompson
  sampling over historical scan_candidates context/outcomes as an ALLOCATION-WEIGHTING
  audit on top of the regime stack. Offline only at current n.
- I16 (S each) Cheap spikes: vol-tercile RF gate feature [Enigma_24 salvage]; squared-lag-
  return + rolling-lag-vol features [ParshantR salvage]; 12-feature independent regime-
  label audit vs regime_snapshots [Anish2811 salvage]; VCP/triangle/double-bottom geometric
  flags [momentum-swing-bot] backtested before gate role; non-gating soft regime point-
  adjustment design review [nifty-quant-lab].
- Confirmed-empty under steelman (evidence-based): SwingPro "self-learning" (SQL count in
  a prompt, no mechanism), Enigma LSTM (1-timestep raw-price regression), tamil3yashni
  scanner (mislabeled video-skill repo), StockRead training code (gitignored, unrecoverable).
Revised order: I2 -> I11 -> I12 -> I4 -> I16 spikes -> I1 -> I13 -> I14 -> I3 -> I15 -> I6 -> I5 (gated).
