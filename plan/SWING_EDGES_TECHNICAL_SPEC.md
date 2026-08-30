<!-- Adopted 2026-08-29 as the OPERATING research manual for the momentum
     research program (unidesk DECISIONS D11): frozen definitions, parameter
     register, cost model, kill criteria, validation protocol. It governs HOW
     waves W-D onward are researched and falsified. As-built map of the
     tool that implements this spec: plan/UNIFIED_DESK_BUILD_MANUAL_V2.md. -->

# Indian Equity Swing Edges — Technical Specification

**Status:** Research spec (not production trading rules)  
**Market:** NSE/BSE cash equities, swing / momentum horizon (typically 3–20 sessions)  
**Bias:** Long-primary. Shorts only where stock futures exist and liquidity is real.  
**Last updated:** 2026-08-29  
**Implementation:** `unidesk/` per `plan/UNIFIED_DESK_BUILD_MANUAL_V2.md` §5 / §12. This file stays the frozen champion; that file is the as-built map. Do not treat unimplemented sections here as already coded.

### As-built map (2026-08-29, D14–D18) — do not re-plan

| Spec item | Code |
|---|---|
| §1.4 cost model | `unidesk/research/costs.py` + `unidesk/config/costs.yaml` (`costs-v1-spec-1.4`) |
| §1.5 feature library | `unidesk/momentum/features/spec_library.py` (sma, median-RVOL, delivery_z, pocket_pivot, tight_ratio, stack_bull, stage2). Mean-RVOL still exists separately. |
| §1.6 walk-forward | expanding folds + 5-session embargo in `unidesk/research/walkforward.py`. 4y/1y **refused** until the bar calendar is long enough. |
| §2 R0 | `unidesk/momentum/regime.py`. Midcap 150 vs SMA50 when ≥50 sessions (`breadth_and_midcap150_sma50`); else `breadth_only`. VIX 1y z-score and Nifty SMA200 not yet in the label rule. |
| T1–T5 detectors | eight rule-engine detectors in `unidesk/momentum/detectors/` (see Build Manual V2 §12.5). S_tight / VCP preset / EP signature score / F&O PIT still open. Clean-room `base_pattern` exists as a research detector (public metric defs); not in the nightly registry. |
| F1 | **deferred** (this spec §14). |
| Leakage / embargo | `unidesk/research/leakage.py` + planted-bug suite. Constitution ±60-session embargo is coded; Phase 0 is not accepted so AI challenger work is forbidden. |
| PIT membership 2016– | **partial:** 18 dated snapshots Jul–Aug 2026 only (D17). Do not back-fill today's list (D14.5). |
| Industry / sector (for RS peers) | D18: `industry_mapping.parquet` 2,772 names. Chartsmaze primary; nexus fills unmapped only. Not official NSE industry; taxonomies must not be mixed. |

This document specifies seven related edges:

| ID | Family | Name |
|---|---|---|
| F1 | Information | Material filing drift with tape confirmation |
| T1 | Tape / bull | Tightness-scored continuation in RS leaders |
| T2 | Tape / bear | Failed pivots and undercut-and-rally |
| T3 | Tape / chop | Range fades and anti-chop isolation |
| T4 | Tape / object | IPO first constructive base |
| T5 | Tape / object | Episodic Pivot signature + first flag |
| R0 | Shared | Market regime classifier (gate for T1–T5, overlay for F1) |

F1 is the earlier information-attention idea. T1–T5 are price-action systems. They share universe filters, data, cost model, and the regime layer. They must be tested separately and combined only after each one stands on its own.

---

## 0. Design principles

1. **First-principles constraint.** Each edge exists only if something was too slow, expensive, or attention-heavy for a human desk to do every day across ~1,000–2,000 names.
2. **No silent beta.** Every book is measured against sector-neutral and against a dumb technical or event baseline. If alpha dies after that, the idea is rejected.
3. **India microstructure is part of the signal.** Circuits, delivery volume, pre-open, call auctions after circuit hits, F&O vs cash-only, and lock-in calendars are first-class fields, not footnotes.
4. **Label before you model.** Rules and features are specified so a walk-forward test can be run without an LLM in the loop. LLMs are allowed only where the label is language (filings). Tape ideas must run on numeric series alone.
5. **Capacity before romance.** A pattern that only works below ₹3 crore ADV is not an edge for a book that cannot trade it.
6. **Kill criteria are mandatory.** If a pre-committed test fails, the strategy is parked. No post-hoc feature fishing to save it.

---

## 1. Shared infrastructure

### 1.1 Universe

**Primary tradable universe (daily rebuild):**

- NSE cash, equity segment.
- Market-cap band: Nifty Midcap 150 + Nifty Smallcap 250 constituents, plus any name that was in either index in the prior 12 months (avoid survivorship).
- Optional research tail: remaining NSE 500 / Nifty Total Market names that pass liquidity.
- Exclude: ETFs, REITs/InvITs (unless later promoted), suspended scrips, SME/BSE SME as a *default*. SME is a separate optional bucket with its own cost model.

**Hard liquidity gates (entry day, trailing 20 sessions):**

| Gate | Default | Rationale |
|---|---|---|
| Median daily traded value | ≥ ₹8 crore | Impact and exit |
| Median daily volume | ≥ 100,000 shares | Fill realism |
| Median spread proxy | ≤ 25 bps (high-low/close or bid-ask if available) | Cost |
| Price | ≥ ₹30 | Avoid junk ticks and series-change noise |
| Circuit status | Not frozen on a 5% band for ≥3 of last 5 sessions | Cannot manage risk |

Tighten to ₹15–20 crore ADV for any book intended to hold >₹50 lakh per name.

**F&O overlay:** maintain a flag `has_stock_futures = true/false`. T2 shorts are allowed only when this is true and stock-fut near-month ADV is usable.

### 1.2 Sessions and clocks

- Exchange: Asia/Kolkata.
- Pre-open: 09:00–09:08, matching 09:08–09:15.
- Regular: 09:15–15:30.
- Post-close filings often hit 15:30–20:00 and weekends. F1 must timestamp *exchange publish time*, not news-wire time.
- No overnight futures signals in v1. Cash close-to-close is the research default. Intraday bars are required only for T5 Day-1 and for circuit/auction flags.

### 1.3 Data contracts

Minimum fields, daily bar:

```
symbol, nse_code, date
open, high, low, close, vwap
volume, traded_value
delivery_qty, delivery_pct          # NSE bhavcopy / delivery report
adv_20, adv_value_20
high_20, high_50, high_252
low_20, low_50
sma_10, sma_21, sma_50, sma_200
ema_10, ema_21
atr_14, atrp_14                     # ATR / close
rvol_20                             # volume / median(volume, 20)
delivery_z_20
ret_1, ret_5, ret_10, ret_20
rs_sector_20, rs_nifty_20           # residual or ratio RS
sector_id, industry_id
mcap_cr, free_float_mcap_cr
index_membership                    # mid150 / small250 / other
has_stock_futures
circuit_band_pct                    # 2/5/10/20
upper_circuit_hit, lower_circuit_hit
auction_flag                        # special/call auction that session
```

Plus corporate actions: splits, bonuses, rights — prices must be adjusted for backtests; *raw* prices kept for circuit and gap logic on the event day.

**F1 extra:**

```
filing_id, symbol, published_at_ist
source              # NSE corp filing / BSE / credit rating
category_raw
category_model      # order_win, capacity, rating, insider_buy, ...
text, text_lang
extracted_value_inr
materiality_sales   # value / ttm_sales
materiality_mcap    # value / mcap
firmness            # firm | qualified | vague
novelty             # vs last 4 similar events
```

**IPO extra (T4):**

```
ipo_id, list_date, issue_price, list_open, list_high, list_low, list_close
list_premium_vs_issue
subscription_times                  # optional
lockin_expiry_dates[]               # pre-IPO / anchor if available
free_float_at_list
days_since_list
```

**Benchmark series:** Nifty 50, Nifty Midcap 150, Nifty Smallcap 250, sector indices (Nifty Industry Classification), India VIX.

### 1.4 Cost and friction model (mandatory in every test)

Use conservative cash-delivery assumptions unless the book is explicitly MIS/futures.

| Item | Default haircut |
|---|---|
| Brokerage + GST (round trip) | 6–15 bps all-in retail/pro blend |
| STT delivery (round trip, approx.) | ~15 bps sell-side dominant; model 20 bps RT conservative |
| Exchange/SEBI/stamp | 3–5 bps RT |
| Impact | `min(15 bps, 8 bps * (order_value / adv_value))` each side |
| Slippage on gap entries | 10–25 bps extra for T5 Day-1 |
| Circuit days | If limit hit and you needed to exit, mark exit at next free auction/open; do not assume magic fills |

Report **gross** and **net**. Net is the only number that can accept a strategy.

Position sizing for research: 10 bps of book risk per name at stop distance, cap 5% of name ADV on entry day. Capacity test: scale until impact model doubles.

### 1.5 Shared feature library

All tape systems use the same feature functions so tests stay comparable.

**Trend / stage**

- `stack_bull`: close > ema10 > ema21 > sma50 > sma200
- `stage2`: close > sma200 and sma200 slope 50d > 0 and close ≥ 1.15 * sma200_min_126
- `stage4`: inverse
- `ext_21`: (close / ema21 − 1) / atrp_14

**Relative strength**

- `rs_ratio = close / sector_index_close`, then 20d and 63d slope
- `rs_rank`: percentile of 20d residual return vs universe after sector dummy
- `nh_nl_stock`: 20d new high / new low flags

**Volume / delivery**

- `rvol_20`, `rvol_50`
- `vdu`: volume < 0.6 * median(volume, 20) and range < 0.7 * atr_14
- `pocket_pivot`: close > prev_close and volume > max(volume on down-closes of prior 10 sessions)
- `delivery_expand`: delivery_pct > median(delivery_pct, 20) + 0.5σ
- `climax_bar`: range > 2.0 * atr_14 and rvol_20 > 2.0

**Structure**

- Swing points: 5-bar fractal highs/lows (configurable 3/5/8)
- `contraction_depths[]`: each pullback % from local peak
- `contraction_ok`: ≥2 pullbacks and each depth ≤ 0.75 * previous
- `base_width_atr`: (base_high − base_low) / atr_14
- `tight_10`: max(high_10) / min(low_10) − 1 ≤ 0.08 (parameter)
- `box_quality`: parallel touch count of 10–30d highs/lows (see T3)

**Gaps / EP primitives**

- `gap_pct = open / prev_close − 1`
- `close_loc = (close − low) / (high − low)`
- `prior_compression`: percentile of atrp_14 vs trailing 126d ≤ 30
- `ep_day_low`, `ep_day_vwap` stored as event anchors

### 1.6 Research stack (suggested)

- Daily panel: Parquet partitioned by date.
- Point-in-time index membership and corporate actions.
- Backtest engine: event-driven, next-bar or close+1 open as specified per strategy. No same-bar lookahead.
- Walk-forward: expanding or 4y train / 1y test, embargo 5 sessions.
- Stats: n trades, hit rate, avg win/loss, payoff, net expectancy, profit factor, max DD, MAR, CPS (cost as % of gross), capacity curve, year-by-year.

---

## 2. R0 — Regime classifier

Tape ideas are **regime-gated**. F1 is regime-*weighted*, not fully gated.

### 2.1 Inputs (daily, universe = Nifty 500 or Total Market)

- `pct_above_200`, `pct_above_50`, `pct_above_20`
- Nifty 50 and Midcap 150 vs own sma50 / sma200
- `nh_nl_20` net new highs minus new lows / count
- India VIX z-score vs 1y
- 20d realized vol of Nifty vs 1y median

### 2.2 Labels

| Label | Rule (default) | Permission set |
|---|---|---|
| `BULL` | Midcap 150 > sma50 and sma50 rising and `pct_above_200` ≥ 0.60 | T1 primary; T5 allowed; T4 allowed; T2 disabled; T3 isolation-only |
| `BEAR` | Midcap 150 < sma50 and sma50 falling and `pct_above_200` ≤ 0.40 | T2 primary; T1 disabled; T5 size ×0.5 or off; T4 off unless RS exceptional |
| `CHOP` | otherwise, or `pct_above_200` in [0.40, 0.60] and Nifty 20d realized vol < 1y median | T3 primary; T1 only if stock RS rank ≥ 90 and tight_10; T5 reduced size |

Hysteresis: require 3 consecutive sessions in the new state before flipping. Prevents flicker.

### 2.3 Output

```
date, regime, regime_confidence, pct_above_200, mid150_trend, vix_z
```

Store this series. Every trade row must join it. Reporting slices by regime.

### 2.4 Test / kill for R0 itself

R0 is not a money system. Kill and rebuild it if:

- T1 expectancy in declared `BULL` ≤ T1 expectancy in declared `BEAR` (gate is inverted).
- Flip rate > 12 per year (too noisy).

---

## 3. F1 — Material filing drift with tape confirmation

### 3.1 Hypothesis

Exchange filings are public instantly. Pricing of *relative materiality* across the mid/small universe is not. Attention concentrates on Nifty 50 and already-moving story stocks. A material, firm, novel disclosure is followed by 5–20 session drift **if and only if** the tape confirms after the print.

### 3.2 Why AI is required

A human cannot read, extract value, and compare to TTM sales / history for 50–200 filings a day. Classification of firm vs vague language is an NLP task. The confirmation layer is numeric and cheap.

### 3.3 Event pipeline

1. Ingest NSE corporate announcements + BSE + rating agency feeds with `published_at_ist`.
2. Deduplicate by symbol + hash of normalized text within 24h.
3. LLM extract (or rules + LLM):
   - `category_model`
   - `extracted_value_inr` (null allowed)
   - `firmness` ∈ {firm, qualified, vague}
   - `novelty` vs last 4 events of same category
4. Materiality:
   - `mat = extracted_value_inr / ttm_sales` if value present
   - else `mat_proxy` from category priors (rating upgrade = medium, “strategic MoU” = low)
5. Keep candidate if:
   - `firmness = firm`
   - `mat` in top quintile of that category over trailing 3y **or** `mat ≥ 0.08` of TTM sales
   - `category_model` ∈ investable set (below)
   - not a scheduled result *unless* treated as PEAD sub-sleeve (optional, separate)

**Investable categories (v1):** firm order / contract win, capacity expansion with capex number, credit rating upgrade, large insider *purchase* (SEBI SAST / insider), unexpected special dividend / buyback sized vs mcap, legally binding JV with numbered economics.

**Exclude (v1):** vague MoU, “exploring,” bonus/split without cash, routine AGM, already-telegraphed capex restated, promoter *sale*, GST/tax show-cause unless later confirmed (governance tail risk).

### 3.4 Tape confirmation (mandatory)

Do **not** buy the first tick after the filing.

Wait until first session where all of:

- Filing published ≥ 4 hours before (if published after 14:30, first eligible bar is next regular close or T+1 open — pick one and freeze it).
- `ret` vs sector from filing-close to now > 0
- `rvol_20 ≥ 1.2` or `delivery_expand`
- not `ext_21 > 3.0` (already vertical)
- liquidity gates pass
- price not through a 20% circuit freeze that prevents a stop

Entry: next open after confirmation close (conservative) **or** confirmation close (research A/B).

### 3.5 Exit

- Time: 10 sessions default; also report 5 and 20.
- Hard invalidation: close back below the pre-filing day’s low, or −1.5 × atr_14 from entry.
- Giveback: trail to ema10 after +2 × atr_14.
- Event failure: if a clarifying filing within 5 sessions downgrades firmness to vague, flatten next open.

### 3.6 Sizing

Risk 0.75–1.0% of book to the invalidation. Max 4 concurrent F1 names. Cap 4% of ADV.

### 3.7 Baselines

- B0: buy every order-win keyword, no materiality, no tape filter
- B1: 12-1 midcap momentum, weekly rebalance
- B2: sector ETF / Midcap 150 buy-and-hold over same holding window

F1 must beat B0 net. If it only beats B0 but not B1, it is a momentum relabel.

### 3.8 Kill criteria

- Walk-forward net 10d sector-adjusted alpha ≈ 0 after 2022
- Alpha only in ADV < ₹5 crore
- Pre-event 5d drift > post-event 10d drift (you are late)
- Profit concentrated in one category that is already a public scanner (“defence order”)
- LLM labels cannot be reproduced with κ > 0.7 on a frozen gold set of 500 filings

### 3.9 Gold set and leakage

Hand-label 500 historical filings. Freeze the prompt. Point-in-time fundamentals only (no restated TTM that was not public). Never join a filing to the same-bar close if `published_at` ≥ 15:00 unless using next session.

---

## 4. T1 — Bull: tightness-scored continuation

### 4.1 Hypothesis

In a bull regime, midcap leaders pay continuation. Crude 52-week-high + volume scans are crowded. The scarce object is *quality of the coil*: contracting swings, volume dry-up, delivery that does not vanish, RS already leading.

### 4.2 Gate

`regime == BULL`. If R0 flickers to CHOP, new T1 entries pause; open trades use tighter trail.

### 4.3 Candidate filter (daily)

- `stage2` or `stack_bull`
- `rs_rank` ≥ 70 vs sector (parameter)
- close within 8% of `high_50` or `high_252` (not a deep repair job)
- not `ext_21 > 2.5` unless last 10 bars `tight_10`

### 4.4 Structure score `S_tight` ∈ [0, 100]

Compute on last 15–40 sessions:

| Component | Weight | Pass idea |
|---|---|---|
| Contraction monotonicity | 25 | `contraction_ok` |
| Final swing depth | 15 | last pullback ≤ 8% (param) |
| Volume dry-up on last swing | 20 | down-leg volume < 70% of prior down-leg |
| Range compression | 15 | atrp_14 ≤ 40th pct of 126d |
| Delivery integrity | 10 | delivery_pct not in bottom quintile |
| RS hold during base | 15 | rs_ratio does not make a 20d low |

Trade only `S_tight ≥ 70` (calibrate on train; freeze).

### 4.5 Entry triggers (either)

1. **Pivot break:** close > high of final contraction, `rvol_20 ≥ 1.5`, `pocket_pivot` preferred.
2. **Anticipatory pocket pivot:** `pocket_pivot` while still inside base, `S_tight ≥ 80`, close > ema10.

Entry execution: next open (default) vs breakout stop order (optional live). Research books next open to stay honest.

### 4.6 Stop / exit

- Stop: low of final contraction minus 0.2 × atr_14, or 8% max.
- Time: 15 sessions or giveback of 50% of open profit after day 8.
- Trend fail: close < ema21 and ema10 cross down through ema21.
- Regime fail: if R0 → BEAR, flatten within 2 sessions.

### 4.7 Baselines

- Buy every close > `high_252` with `rvol_20 ≥ 1.5` in BULL
- Buy every name with close > sma50 and rsi_14 > 60
- Midcap 150 Momentum 50 total return, sampled on the same days

### 4.8 Kill criteria

- Tightness book net expectancy ≤ raw 52w-high book
- Edge disappears at ADV ≥ ₹10 crore
- Works only in 2020–21 or only in one sector (defence / capital goods)

---

## 5. T2 — Bear: failed pivots and undercut-and-rally

### 5.1 Hypothesis

In a bear regime, breakouts are supply. Two residual tape edges: fade failed highs on names you can short, and buy springs only in the strongest surviving RS names.

### 5.2 Gate

`regime == BEAR`. T2-Long U&R also allowed on the first 10 sessions of a flip from BEAR → CHOP (optional sleeve).

### 5.3 Sleeve A — Failed breakout short (F&O only)

**Setup (lookback 20–40d):**

- Name made a clear 20d or base high.
- Breakout day: close > that high and `rvol_20 ≥ 1.5`.
- Failure: within 3 sessions, close back below the breakout level **and** below breakout-day VWAP.
- `has_stock_futures` and stock-fut impact acceptable.

**Entry:** next open after failure close.  
**Stop:** breakout-day high + 0.3 × atr_14.  
**Cover:** 5–8 sessions, or reclaim of failure day high, or R0 → BULL.  
**Size:** half of long-sleeve risk; gap risk is real.

### 5.4 Sleeve B — Undercut-and-rally long

**Universe:** even in BEAR, take only `rs_rank ≥ 80` on a 63d window *or* name still above its own sma200 (rare; keep them).

**Setup:**

- Climactic down bar: `climax_bar` and close in lower third (`close_loc ≤ 0.35`)
- Next 1–3 sessions: close back above climax-bar high **or** above ema10, with down-volume shrinking
- Prefer a spring: undercut of a 10–20d low that immediately fails to hold

**Entry:** next open after reclaim.  
**Stop:** climax-bar low.  
**Exit:** +1.5 to 2.5 × atr_14, ema10 loss, or 8 sessions. This is a bounce, not a new Stage 2.

### 5.5 Baselines

- Short every close < sma50 in BEAR (dumb)
- Long every rsi_14 < 30 in BEAR (dumb oversold)
- Flat (cash) — T2 must beat cash on a risk-adjusted basis, not just print activity

### 5.6 Kill criteria

- Sleeve A 5d net drift ≥ 0 after costs (failed breakouts do not actually fail)
- Sleeve B indistinguishable from random oversold bounces (same expectancy as rsi < 30)
- Cannot get realistic short fills after modelling circuit + basis — then Sleeve A is deleted and T2 becomes “flat + optional springs” only

---

## 6. T3 — Chop: second-touch fades and anti-chop isolation

### 6.1 Hypothesis

When breadth is mixed and index vol is compressed, first breakouts of dirty ranges die. Edge is (1) fading the *second* weak tag of a clean box, and (2) owning the few names whose own trend is expanding while the index is not.

### 6.2 Gate

`regime == CHOP`.

### 6.3 Sleeve A — Range fade

**Box definition (10–30 sessions):**

- At least 2 highs within 0.6 × atr_14 of each other
- At least 2 lows within 0.6 × atr_14 of each other
- Box height between 1.2 and 4.0 × atr_14
- `box_quality ≥ 0.6` (touches, parallelism, time spent inside)

**Fade long:** second (or third) tag of box low, `rvol_20` on the tag ≤ 1.0, next bar holds above the low.  
**Fade short:** only if `has_stock_futures`; second tag of box high on weak volume, fail to close through.

**Stop:** 0.4 × atr_14 beyond the box extreme.  
**Target:** box midline first, opposite rail second.  
**Time kill:** 6 sessions if midline not seen.

Do not fade the first touch. That is the control that should lose or be flat — if first-touch fade already wins, the “second touch” story is unnecessary and probably overfit.

### 6.4 Sleeve B — Isolation longs

Rank universe by `iso = z(rs_sector_20) + z(atrp_14 / atrp_nifty_14) + z(delivery_z_20)`.

Buy top decile if also `stack_bull` on the *stock* (index may be flat).  
Stop: ema21. Exit: leave top quintile for 3 days, or R0 leaves CHOP into BEAR.

### 6.5 Baselines

- Buy first breakout of same boxes
- Midcap 150 while in CHOP
- Random names with rsi 40–60

### 6.6 Kill criteria

- First-breakout book ≥ second-touch fade net
- Isolation book alpha dies after sector neutralization (hidden midcap beta)
- Box detector cannot be specified without discretionary charting (if two implementers get <70% overlap on boxes, the definition is too soft)

---

## 7. T4 — IPO first constructive base

### 7.1 Hypothesis

Listing-day premium is crowded. Blind post-list buying is poor. After the float circus (circuits, short-covering auctions, hype), the first tight coil with drying volume is a distinct object. Most discretionary traders have already left the name.

### 7.2 Universe

- Mainboard IPOs, list_date from 2016 onward for research.
- Days since list: 8 to 180 (first and second base family). After 180d the name graduates into T1.
- SME IPOs: **off by default**. If tested, separate file, ADV gate ×3, circuit-aware exits.

### 7.3 Base definition

From list_date + 8:

- Peak after listing, then pullback depth 8–35% (cap 50% as “wide IPO base,” scored down)
- Duration 5–40 sessions for the first base (allow longer second base)
- Right side: last 5–8 bars `tight_10` or last swing ≤ 8%
- Volume on right side < volume on listing week (normalize by shares, not rupees, if price exploded)
- Close holds above `max(list_close * 0.92, ema10)` — parameterize
- `S_tight` reused from T1, threshold 65 (slightly looser; IPO series are short)

Lock-in: if a known lock-in expiry falls inside the next 10 sessions, either skip or require extra tightness. Do not ignore the calendar.

### 7.4 Entry / exit

- Entry: close above base high with `rvol_20 ≥ 1.3`, next open.
- Stop: right-side low or 10%, whichever is tighter.
- Exit: 10–15 sessions, or close back in base, or +3 × atr_14 scale-out 50%.

### 7.5 Microstructure flags (features, not vibes)

- `listed_on_upper_circuit` day 1
- `auction_squeeze_day1` if auction print >> regular close
- `list_premium_vs_issue`
- `adv_collapse` = adv_5 after day 10 / listing-day value

Huge listing premium + adv collapse + no tightness = hard skip.

### 7.6 Baselines

- Buy listing-day close, hold 15 sessions
- Buy day-10 close blindly
- T1 rules applied as if it were a seasoned stock (no IPO logic)

### 7.7 Kill criteria

- Base-break net ≤ listing-day-hold net
- Works only when R0 is BULL (pure beta)
- Lock-in weeks account for most losses and cannot be filtered
- Sample too small after liquidity gates (if n < 80 trades in 10y, publish as case study, not a system)

---

## 8. T5 — Episodic Pivot signature + first flag

### 8.1 Hypothesis

An EP is a tape event: neglected name, sudden range/volume shock, close strong. Chasing 09:15 is negative after costs. The swing object is Day-2+ follow-through and the first 3–10 day flag that holds the EP-day low.

Catalyst text is **optional**. v1 must work on price/volume/delivery alone. F1 may later attach as a quality booster, not as a required input.

### 8.2 Day-0 / Day-1 signature `S_ep`

On session t:

| Feature | Default hurdle |
|---|---|
| `gap_pct` or open-drive vs prev_close | ≥ 8% (report 5/8/12) |
| `rvol_20` | ≥ 3.0 (cash); ≥ 2.0 if F&O heavy name |
| `close_loc` | ≥ 0.65 |
| `prior_compression` | atrp percentile ≤ 35 over 126d **or** 20d range / 126d range ≤ 0.5 |
| Delivery shock | delivery_qty > 2 × median |
| Liquidity | ADV gate; skip if price < ₹30 |
| Extension pre-event | not already +40% in prior 20d (avoid climax-on-climax) |

`S_ep` weighted score; take top events per day (usually 0–6 names).

Circuit handling:

- If upper circuit locks early and stays locked, do **not** treat close_loc as informative. Tag `circuit_ep`. Those enter a delayed list: first free-trading session that holds the locked day’s close becomes Day-1.
- Lower-circuit gap-downs are out of scope for v1 longs.

### 8.3 Entries

**Path A — Delayed Day-1 (optional, higher friction):**  
After 09:30 (or after first 15-min range), if price holds opening-range high / VWAP and has already traded ≥ 0.8 × ADV. Research this on 15-min data. If 15-min history is incomplete, drop Path A.

**Path B — First flag (primary swing path):**  
After Day-1 EP, wait 3–10 sessions:

- pullback ≤ 50% of EP-day range and holds `ep_day_low`
- last 3–5 bars tight (`max high / min low − 1 ≤ 0.07`)
- volume contracts vs EP day
- entry: close > flag high, next open

**Fail immediately if:** close < `ep_day_low` on `rvol_20 ≥ 1.2`.

### 8.4 Exit

- Stop: `ep_day_low` (Path B) or opening-range low (Path A)
- Time: 8–12 sessions
- Trail: ema10 after +2 × atr_14
- Exhaustion: climax bar in direction of trade after day 4 → scale 50%

### 8.5 Baselines

- Buy every gap ≥ 10% at open, exit in 5d
- Buy every gap ≥ 10% at close, exit in 5d
- Path B without `prior_compression`

### 8.6 Kill criteria

- Path B net ≤ gap-and-go net
- `prior_compression` adds no lift
- Day-2 losers dominate unless you peek at the catalyst (then T5 is not a tape edge; fold into F1)
- Path A untradeable after modelling 09:15–09:30 spreads and circuits

---

## 9. Portfolio construction when running more than one book

Do not turn all six on with full size on day one.

**v1 stack (recommended build order)**

1. R0 + shared data
2. T1 vs raw breakout (highest trade count, cleanest labels)
3. T5 Path B vs gap-and-go
4. F1 vs keyword baseline
5. T4 (low n, do not overfit)
6. T3 then T2 (regime-scarce; easy to fool yourself)

**Conflict rules**

- One symbol, one strategy. Priority if collision: T5 > F1 > T1 > T4 > T3 > T2-long.
- Net long cap vs Midcap 150 beta: if combined book projected beta > 1.2, cut T1 first.
- Max names: 8–12. Max 25% of book in IPOs. Max 30% in open EPs (gap risk).
- Correlation: if two names share industry_id and entered the same day from T1, take the higher `S_tight` only.

**Combined reporting**

Show a simple equal-risk mix and a regime-weighted mix:

- BULL: T1 50 / T5 25 / F1 25  
- CHOP: T3 50 / T5 20 / F1 20 / T1 10  
- BEAR: T2 60 / F1 20 / cash 20  

These weights are placeholders until each sleeve has its own Sharpe and DD.

---

## 10. Validation protocol (applies to every ID)

### 10.1 Splits

- Train: 2016-01-01 → 2021-12-31  
- Validate: 2022-01-01 → 2023-12-31 (tune only thresholds, not new features)  
- Holdout: 2024-01-01 → latest (one look)

Also report year-by-year from 2016. A strategy that dies in 2023–26 is dead even if 2017–19 was pretty.

### 10.2 Mandatory diagnostics

For each sleeve:

1. Event-time CAR at t+1, +5, +10, +20, with 10/50/90 bands  
2. Pre-event CAR (−10, −1) — leakage / already-priced  
3. Expectancy by ADV quintile  
4. Expectancy by sector  
5. Expectancy by R0 label  
6. Cost as % of gross edge  
7. Turnover and days-in-trade  
8. Max adverse excursion vs stop (are stops in the noise?)  
9. Implementation shortfall vs next-open assumption  
10. Stability of feature signs when you jitter parameters ±20%

### 10.3 Multiple-testing budget

Each strategy may tune at most **five** numeric thresholds after the spec is frozen. Additional features require a new spec version and a fresh holdout.

### 10.4 What “works” means

Accept a sleeve only if **all** hold:

- Holdout net expectancy > 0  
- Holdout beats its specified baseline on net PF or net CAGR at similar DD  
- ADV-filtered capacity ≥ ₹2 crore notionals without killing expectancy  
- Parameter jitter does not flip the sign of expectancy  
- A second implementer can code the candidate rule from this document without looking at charts

---

## 11. Implementation architecture (research → paper → live)

```
┌──────────────┐    ┌─────────────────┐    ┌──────────────────┐
│ NSE bhav     │    │ Corp filings    │    │ Index + VIX      │
│ delivery     │    │ rating feeds    │    │ sector indices   │
│ corp actions │    │ IPO calendar    │    │ F&O membership   │
└──────┬───────┘    └────────┬────────┘    └────────┬─────────┘
       │                     │                      │
       ▼                     ▼                      ▼
┌─────────────────────────────────────────────────────────────┐
│ Point-in-time warehouse (Parquet) + feature jobs (nightly)  │
└────────────────────────────┬────────────────────────────────┘
                             ▼
                    ┌────────────────┐
                    │ R0 regime job  │
                    └────────┬───────┘
           ┌─────────────────┼─────────────────┐
           ▼                 ▼                 ▼
        T1–T5             F1 NLP            Reports
        scanners          extractors        + blotter
           │                 │
           └────────┬────────┘
                    ▼
            Candidate store
            (scores, stops, ADV)
                    ▼
            Simulator / live broker
            (next-open default)
```

**Live v1 recommendations**

- Signals computed after 15:45 using that day’s official OHLC + delivery (delivery can lag; if missing, use volume-only features and mark quality down).
- Orders for next session: 09:15 marketable limit at previous close ± 0.3 × atr, cancel if unfilled by 09:45 except T5 Path A.
- Kill-switch: if 4 consecutive losers in a sleeve, pause sleeve for 5 sessions.
- Do not auto-trade SME, <₹8 crore ADV, or names on 5% circuits.

**NLP for F1**

- Frozen model version + frozen prompt in git.
- Extract JSON only; reject if schema invalid.
- Human review queue for `mat ≥ 0.20` or value parse failures.
- Store raw text forever for audit.

---

## 12. Parameter register (defaults to freeze before validate)

| ID | Parameter | Default | Allowed tune |
|---|---|---|---|
| R0 | bull_breadth | 0.60 | 0.55–0.65 |
| R0 | bear_breadth | 0.40 | 0.35–0.45 |
| R0 | hysteresis_days | 3 | 2–5 |
| F1 | hold_days | 10 | 5, 10, 20 |
| F1 | min_mat_sales | 0.08 | 0.05–0.12 |
| F1 | confirm_rvol | 1.2 | 1.0–1.5 |
| T1 | s_tight_min | 70 | 60–80 |
| T1 | break_rvol | 1.5 | 1.2–2.0 |
| T1 | max_hold | 15 | 10–20 |
| T2A | fail_window | 3 | 2–5 |
| T2B | hold | 8 | 5–12 |
| T3 | min_touches | 2 | 2–3 |
| T3 | fade_time | 6 | 4–8 |
| T4 | min_days_listed | 8 | 5–15 |
| T4 | max_days_listed | 180 | 120–252 |
| T5 | min_gap | 0.08 | 0.05–0.12 |
| T5 | min_rvol | 3.0 | 2.0–4.0 |
| T5 | flag_max_days | 10 | 6–12 |

Anything not in this table is a new spec version.

---

## 13. Explicit non-goals

- Intraday scalps, expiry F&O, option selling.
- Predicting Nifty direction.
- LLM-written “buy because management quality is good.”
- Copying Nifty Midcap 150 Momentum 50 and calling it research.
- Unshortable microcaps, operator 5% circuit ramps, unlisted grey market.
- Using future revisions of financials or restated filings.

---

## 14. Suggested first two experiments (one week of engineering)

**Experiment A — T1 vs raw breakout, BULL only, 2018–2025.**  
Output: table of net PF, n, DD, and a plot of CAR. Decision: keep T1 or throw away tightness.

**Experiment B — T5 Path B vs buy-the-gap-close, 2018–2025.**  
Output: same plus split on `prior_compression` yes/no. Decision: keep EP-as-tape or admit you need F1’s catalyst layer.

Do not build the NLP stack until A and B exist. F1 without a working warehouse and R0 is how this project turns into a filing toy.

---

## 15. Document control

| Version | Date | Notes |
|---|---|---|
| 0.1 | 2026-08-29 | Initial spec: F1 + T1–T5 + R0 |

Next revision should only add: exact sector taxonomy used, exact filing category ontology, and the gold-set labelling guide for F1.
