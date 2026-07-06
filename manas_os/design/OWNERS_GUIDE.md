# MANAS OWNER'S GUIDE — every deterministic mechanism, in plain language

For you, the operator. What each piece computes, why it exists, **what you may tweak,
where, and what you should never touch**. Nothing in the tool is a black box — every
number below decomposes into rules you can read in the named file.

Golden rule for tweaking: **change ONE number per quarter, write it in
`design/LEARNINGS.md`, and let the journal judge it.** Rapid-fire tweaking = overfitting
your own noise.

---

## 1. THE DAILY PIPELINE (what runs every evening, in order)
`manas run-eod` → one command, seven stages, each logs to `pipeline_runs`:

| Stage | What it does | File |
|---|---|---|
| ingest_bhavcopy | NSE prices + delivery% into `daily_prices` | `sources/bhavcopy.py` |
| universe_breadth | NIFTYMIDSML400 breadth (up/down 4.5%, %>MAs) | `sources/universe_breadth.py` |
| ingest_chartsmaze (+scanners, disclosures) | sector RS, 26 screeners, ASM, EPS growth, order-wins/deals | `sources/chartsmaze*.py`, `sources/disclosures.py` |
| indicators | per-stock EMAs/ATR/ADR/RSI/stage etc → `features_daily` | `engine/indicators.py` |
| ingest_mars | sector-vs-benchmark strength | `regime/mars_ingest.py` |
| regime_snapshot | XP + MBI + market_mode | `regime/snapshot.py` |
| scan_candidates | the refusal cascade + ranked feed + refusal ledger | `scanner/candidates.py` |

---

## 2. THE REGIME (how aggressive today) — `regime/`
- **XP dial** (`xp.py`): recursive breadth-energy formula on the 400-stock midsmall universe.
  Bands: <15 low · 15-40 building · 40-100 strong · >100 extreme. **Don't tweak the formula**
  (it's calibrated to the reference); seeds live in config (`regime.xp_seed`).
- **MBI ratios** (`snapshot.py`): 20R (≥75 green / <50 red), 50R (≥85 / <60), 4.5R burst
  (<50 red / 200-400 green / ≥400 orange). Day color = net of column colors; warning day =
  3+ red columns. **Thresholds are the reference methodology — don't tweak.**
- **market_mode**: RISK_ON / SELECTIVE / DEFENSIVE / NO_TRADE from pillars+breadth+warnings.
- **THE GOVERNOR** (`governor.py`) — regime becomes law. ⚙ TWEAKABLE (with care):

| mode | max cards shown | allowed setup families | pushes |
|---|---|---|---|
| RISK_ON | 8 | all | on |
| SELECTIVE | 4 | catalyst, base/pattern | on |
| DEFENSIVE | 2 | catalyst only | off |
| NO_TRADE | 0 | none | off |

Tweak in `regime/governor.py` (`MAX_CARDS`, `ALLOWED_FAMILIES`). Widening these is the
single easiest way to destroy the tool's edge — the refusal IS the product.

---

## 3. THE CASCADE (which stocks even qualify) — `scanner/gates.py`
Every candidate must pass ALL six gates, in order. Each failure = a named reason in the
refusal ledger (`/api/setups/refusals`). Current live behavior: ~600 pool → ~23 pass.

1. **Regime** — is this setup family allowed today (table above)?
2. **Tradability** — not ETF (keyword list in `engine/universe_filter.py` — ⚙ ADD symbols
   when you spot a leaked fund), price ≥ ₹30, avg turnover ≥ ₹5cr, not circuit-locked,
   **not ASM-flagged**, not a lottery profile (single-day gain ≥18% on a ≤₹3000cr name),
   not a pump signature (delivery 3σ spike + micro-cap + no disclosure).
   ⚙ TWEAKABLE floors: `GateConfig` in `universe_filter.py` (min_price, min_avg_turnover_cr,
   min_market_cap_cr). MAX/pump thresholds in `gates.py` — leave unless the journal proves otherwise.
3. **Trend template** (J Law) — close > 50SMA > 200SMA, EMA stack 9>21>50 ("Lead"),
   within 15% of 52-week high (nearness ≥ 0.85), RS ≥ 80. Catalyst setups (EP/IPO) are
   exempt from history/nearness. ⚙ `RS_FLOOR`, `NEARNESS_ENTRY` in `gates.py` — 0.85/80
   are research-anchored; loosen only with journal evidence.
4. **Fresh leg** — refuses extended names: >8% above 21EMA, or >8% above pivot, or leg
   older than 15 bars, or parabolic-at-high on fading volume. This is your anti-chase
   protection. ⚙ `EXT21_STALE`, `PIVOT_STALE` — don't raise these; chasing is the #1 killer.
5. **Participation** — delivery_z ≥ 0 (delivery vs the stock's OWN 50-day norm — a 60%-always
   name at 60% is noise; a 30%-name at 55% is accumulation). Breakout-day entries also need
   volume ≥ 1.2× average and range expansion (TR ≥ 1.2×ATR14, else "narrow-range" caution).
6. **Risk** — see §4. If the math doesn't clear, the trade is refused, not displayed.

**Rank** (no more 0-100 score): survivors are ordered 1..M by (delivery_z, sector-adjusted
momentum, confluence families). "Rank 2 of 4 today." Grades: A+ = top-3 AND ≥2 boosts;
A = any boost; B = passed. A name showing real weakness (distribution/lower-low) is capped B.

---

## 4. RISK MATH (stop / size / R:R) — `risk/plan.py` (the ONLY writer of these numbers)
- **Stop** = tightest of three REAL levels: trigger-bar low · entry−1.2×ATR20 · 10-bar base
  low (with buffer). Never an arbitrary %.
- **Caps** (initial stop distance): RISK_ON ≤6% · SELECTIVE ≤5% · DEFENSIVE ≤4% ·
  EP/IPO exception ≤7.5% · **>8% always refused** · <1% refused (noise).
- **R:R floor 1.5** (currently soft — measured-move is derived; structural targets coming).
- **Size** = capital × risk% ÷ stop-distance, qty floored.
- **YOUR PROFILE** ⚙ — `config.yaml` under `risk:`:
  - `profile: aggressive` (default — small account, grow fast) or `standard`
  - `capital: 1000000` ← **SET THIS to your real capital**
  - Aggressive bands: 0.75%/0.50%/0.30% risk per trade by regime (hard max 1.0%/0.75%/0.40%),
    open-risk ceiling 3.0%/2.0%/1.0%, max 5 open positions, max 2/day new.
  - The aggression is in SIZE ONLY — stops and gates are identical in both profiles.
- **Sector rule**: max 2 open per sector; a 3rd correlated name sizes at half.
- **Progressive exposure**: if your last-10 closed trades average negative R, size halves
  automatically until you're back above water. Not tweakable — this is the drawdown brake.

---

## 5. SETUP DETECTORS (what patterns it sees) — `engine/eod_detectors.py`, `price_action.py`
All pure OHLCV rules; each fires with a plain-English detail string:
- **EP (episodic pivot)**: ≥30% QoQ AND YoY growth in EPS+sales, quiet pre-gap base
  (25-bar band ≤25%, drift ≤10%), gap-up, mkt-cap >₹300cr, skip if gap+range >12%.
  ⚙ the 30% growth bar is the StockBee reference — leave it.
- **IPO base**: first inside-bar/mini-coil or range-squeeze after listing, hard ≤4% stop.
- **Launch Pad**: price within 3% of 21/50SMA+65EMA cluster, stacked & rising, volume confirm.
- **Pocket pivot / shakeout / EMA touch-reclaim / VCP / ANTS accumulation**: classic
  momentum/accumulation triggers, all thresholded in code with comments.
- **Exit engine (Market Navigator)**: named weakness rules → Intact / Weakening / Broken.
  Broken (50/200SMA lost) = exit voice; two-strike composite (any 2 in 5 sessions) = exit now.
- **Trail plan**: 0→+1R hold structure stop · at +1R move to breakeven + book ⅓ ·
  trend-trail 10EMA (catalyst) or 21EMA · extension (>8% over 21EMA) book another tranche.
  ⚙ the booking fractions (⅓, 25-33%) are Luk-style defaults; journal will tell you if
  your winners need more room.

---

## 6. THE JOURNAL LOOP (your private edge — feed it!)
- Every card gets **TAKEN / SKIPPED (+reason)** — skipping is a decision; log it. The tool
  snapshots the full context automatically.
- Nightly, every candidate (taken or not) gets T+5/10/20 forward returns, MFE/MAE.
- Expectancy per (setup × regime) cell with shrinkage toward the parent mean — a cell's
  numbers are only trusted at n≥20 (descriptive), n≥75 (ranking), n≥150 (operational).
  Your personal cells need n≥30 before they override the system's.
- **Probation**: IPO-base/flag/high-ADR setups trade at HALF size with an
  "unproven — building sample" chip until their cell earns ≥40 observations with positive
  expectancy. Evidence-strong setups (EP, pullback) start at full size.
- ⚙ YOUR JOB: log every decision honestly (especially skips and mistake tags). This
  dataset is the one thing no free site can copy — after ~6 months it starts telling you
  which setups pay YOU, in which regimes.

## 7. WHAT YOU TWEAK vs WHAT YOU DON'T
**Tweak freely**: `risk.capital`, `risk.profile`, ETF keyword additions, watchlist, mentors.
**Tweak quarterly, one at a time, logged in LEARNINGS.md**: gate floors (RS, nearness,
turnover), governor card caps, trail booking fractions.
**Never tweak**: XP/MBI formulas (reference-calibrated), the >8% stop refusal, the
progressive-exposure brake, ASM exclusion, the one-opinion rule, additive scoring (gone —
don't reintroduce), anything the journal hasn't earned with n≥ the trust ladder.

**Where numbers live**: LOCKED table → the plan file · gates → `scanner/gates.py` ·
risk → `risk/plan.py` + `config.yaml` · governor → `regime/governor.py` ·
detectors → `engine/eod_detectors.py` · every change log → `design/LEARNINGS.md`.
