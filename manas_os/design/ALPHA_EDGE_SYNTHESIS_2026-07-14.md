# ALPHA / EDGE SYNTHESIS — Indian swing trading (2026-07-14)

Consolidates the edge discussion across the recent sessions (SMF/Reactor, breakoutscanner ML,
top-trader principles, choppy-tape analysis, Umang intraday, Brian Shannon AVWAP). This is the
reference for WHAT we're chasing as edge, WHERE each idea stands, and the discipline every idea
must pass before it touches a real trade decision. Status markers: `Certain / Likely / Assumption
/ Unverified` per the standing bar.

---

## 0. The core edge thesis (LOCKED — do not re-litigate)
Indicators are commodities. The edge is: **regime-first refusal + deterministic risk math + a
private journal dataset + honest evidence grading.** In order (from ALPHA_LEARNING_CONSTRAINTS.md):
regime/breadth recognition → opportunity/leadership ranking → chart/setup interpretation → risk
context → calibrated forecasts as *secondary* evidence. No LLM/ML/score ever authors position size
or overrides a gate. Every new "signal" is SHADOW until it beats a simple baseline out of sample.

---

## 1. Measured state of the tape (our bhavcopy, through 2026-07-10/-14)
`Certain` (recomputed from `breadth_counts` + `daily_prices`):
- **Breadth improving, leadership forming**: new-52w-highs consistently beat new-lows (67-138 NH vs
  7-45 NL); %>20DMA ~50-65%.
- **Follow-through is broken (the defining feature)**: breakout sustained/failed ratio swings
  0.43-1.65, *frequently <1*. Of 2,685 stocks up >=4% in a day, median T+1 = +0.09%, T+3 = +0.21%,
  and **48% are negative by T+3**. A 4% pop is a coin-flip that on median goes nowhere.
- **Umang's 4.5R breadth gate (= our `r4p5`) is red ~60% of recent days** (9 of 15 sessions <400).
Read: a **choppy / transition tape** — breadth turning up before momentum sticks. The disciplined
posture (all top traders agree): trade fewer + smaller, book faster, hold cash, build the leader
watchlist, press only when follow-through returns. Do NOT switch strategies to chase activity.

---

## 2. Edge-candidate registry
Each = source idea → our current state → queued handoff → the test that decides it.

| Candidate | Source | Our state | Handoff | Verdict / test |
|---|---|---|---|---|
| **SMF / Reactor activity** (abnormal avg-trade-qty + delivery) | Kedia SMF video; dossier `SMF_..._REVERSE_ENGINEERING` | `alpha/activity.py` v2 analogue built (±0.25 vs source on July screenshots); direction-neutral | `HANDOFF_GEMINI_smf_activity_screener` + `..._volume_profile_levels` | `Likely` weak standalone (direction-neutral, adverse-selects into illiquids). Value only as an accumulation FEATURE / exit-distribution input. Test: does SMF-persistent(liquid, non-quarantined) at a fresh-breakout beat delivery_z/RVOL baseline at T+10? |
| **Quiet PRE-move accumulation** (delivery rising + absorption-on-weakness in a tight base) | Arora "spot early"; Wyckoff | MISSING — `ants_accumulation` fires only AFTER ~15% move | `HANDOFF_GEMINI_dii_footprint` (item 1) | `Likely` the highest-value early lead. Test: does quiet-accum at T0 precede the eventual breakout / beat baseline fwd return? |
| **F&O open-interest buildup** (long buildup = early institutional positioning) | market structure | MISSING — only an `is_fno` flag, no OI | `HANDOFF_GEMINI_dii_footprint` (item 2) | New DATA (NSE F&O bhavcopy, ~0 lag). Best early derivatives tell. Ingest first, then test. |
| **RS-line new-high BEFORE price** (leader held up while index corrects) | Minervini/Qullamaggie | MISSING — have RS *rating* not the RS *line* | `HANDOFF_GEMINI_rsline_priorleg` | `Likely` #1 leadership tell for an FII-outflow tape. Test vs RS-rating baseline. |
| **Prior-momentum-leg precondition** (big advance → tight base) | Qullamaggie | MISSING — setups fire on any base | `HANDOFF_GEMINI_rsline_priorleg` | Separates "leader resting" from "random range". Test: setups WITH prior-leg vs without. |
| **Breakout-climate throttle** (market's own BO-follow-through modulates selectivity) | the choppy-tape analysis | data live (BO-S/F, Tier-0); not wired | `HANDOFF_GEMINI_breakout_climate_throttle` | The formal choppy-market fix. Replay-A/B gate; tighten-only; never touches money-math. |
| **Bulk/block/insider as POSITIVE lead** | disclosures | ingested but used only DEFENSIVELY (pump-exclusion) | `HANDOFF_GEMINI_dii_footprint` (item 3) | Named, same-day, hard footprint. Rewire as accumulation evidence. |
| **FII/DII divergence overlay** (FII sell / DII absorb) | current macro | aggregate cash ingested, divergence not surfaced | `HANDOFF_GEMINI_dii_footprint` (item 4) | Context field, not a gate. Cheap. |
| **RF breakout-outcome model** (P(+3% before -2.5% in 10 bars)) | breakoutscanner `ml_engine.py` | not built; `direction_lgbm` fills the slot | `HANDOFF_GEMINI_rf_breakout_outcome_model` | Their impl has NO train/test split → would fail our gates. Build our way (walk-forward, resolver-labelled) or skip. Shadow-only. |
| **Weekly-timeframe breakout** | breakoutscanner | only daily | `HANDOFF_GEMINI_weekly_breakout_scan` | Additive setup family, low priority. Same gates. |
| **4.5R intraday breadth gate** (green/red "is intraday tradeable today") | Umang intraday | = our `r4p5`, already computed | (surface only) | Cheap tile; his single reproducible contribution. |
| **Anchored-VWAP as exit + EP entry-timing** | Brian Shannon | `avwap_auto_anchor` computed but DISPLAY-ONLY (single anchor) | (proposed handoff) | Promote to exit-composite input + EP reclaim entry; multi-anchor overlay. Test vs plain trail. |
| **MF monthly holdings** | AMFI | none | `HANDOFF_GEMINI_dii_footprint` (item 5) | DEMOTED to LATE confirmation — 15-45d lag, not a lead. |

---

## 3. How they compose (the one coherent picture)
Not twelve strategies — one funnel, regime-first, for a choppy leadership tape:
1. **Regime/climate** decides IF and how much to trade (governor + breakout-climate throttle;
   4.5R red = mostly sit out).
2. **Early accumulation watchlist** (quiet-accum + F&O OI + bulk/block/insider + SMF) = who's being
   accumulated BEFORE the move — so we're early, per Arora.
3. **Leadership filter** (RS-line-new-high-before-price + prior-leg) = which of those are the true
   leaders holding up while the index bleeds.
4. **Chart/entry** (existing gates + AVWAP reclaim + volume-profile levels) = the trigger + tight
   invalidation.
5. **Deterministic risk** (locked) authors stop/size — nothing above touches it.
6. **Exit** — faster in chop: book into the one-day strength, AVWAP-break + two-strike composite.
7. **Journal loop** grades every decision → expectancy with shrinkage = the compounding moat.

Everything in steps 2-4 is EVIDENCE/priors until it clears the gate in §4. The moat is 5-7, which
already exist.

---

## 4. The validation discipline (non-negotiable — the same gate for every item above)
`alpha/promotion_gates.py` + `alpha/resolver.py` + `backtest/replay.py`:
1. point-in-time, no-leakage features (T-1 truncation audit);
2. walk-forward vs a SIMPLE baseline (RS / delivery_z / RVOL / momentum) — must beat it OOS;
3. realistic Indian costs (STT + brokerage + slippage) + liquidity/circuit/ASM;
4. regime + sector + setup-family stability, placebo/permutation;
5. min-sample + shrinkage; frozen experiment record incl. failures;
6. >=20 live shadow sessions before ANY ranking/sizing/gate influence.
A signal that matches a guru's number, or "works" on a cherry-picked chart, is NOT edge. Only the
OOS-beats-baseline-after-costs result is.

---

## 5. Rejected / not adopted (with reason)
- **Exact SMF/Reactor formula clone** — proven unrecoverable (missing order-size variable + a
  March-2025 formula break); we ship the honest analogue, never claim the proprietary score.
- **"Only Price Pays" / ignore-breadth** (Shannon philosophy) — opposite of our regime-first edge;
  the current tape proves breadth was the whole story. Take his AVWAP tooling, not his stance.
- **Switching to intraday/day-trading to escape the chop** — the fade kills intraday momentum too;
  Umang's own 4.5R gate is red most days; worse tax/cost/skill profile. Adapt (book faster), don't
  switch styles.
- **MF-monthly as a lead** — too lagged; confirmation only.
- **breakoutscanner RF as-is** — no train/test split; overfit.
- **Evolutionary factor mining, WQ-cloud, SaaS memory** (from the external-repo audits) — overfit
  factory / external-dependency; SQLite stays canonical.

---

## 6. Data gaps blocking edge (acquire these to unlock the above)
- `Certain` **Fyers intraday backfill BLOCKED on auth** — blocks Umang's spot-burst, Shannon's
  intraday management, true volume-profile (5-min), any intraday validation.
- **F&O open-interest bhavcopy** — not ingested; the cheapest high-value early institutional signal.
- **AMFI monthly MF portfolios** — verify a clean free source before building (confirmation-tier).

---

## 7. Priority (highest edge-per-effort first)
1. **Breakout-climate throttle** — formalizes the choppy-tape discipline; data already live.
2. **RS-line-before-price + prior-leg** — the leadership tell for exactly this FII-outflow tape.
3. **Quiet pre-move accumulation + F&O OI ingest** — the "spot it early" Arora edge.
4. **4.5R intraday-gate tile + AVWAP→exit/EP-entry** — cheap, reuse existing plumbing.
5. **SMF screener + volume-profile** — honest attention tool; validate before any weight.
6. Weekly-breakout, RF model, MF-monthly — lower priority / staged.

All shadow-first; nothing changes a trade decision until §4 passes. The edge is the discipline that
makes us say NO to most of this until it earns its way in — especially in a tape that punishes
conviction.
