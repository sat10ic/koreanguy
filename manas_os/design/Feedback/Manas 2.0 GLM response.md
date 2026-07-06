# Manas OS — From Free-Data Reskin to Edge: A Buildable Roadmap

*Quant research response, grounded in the actual codebase (`scanner/candidates.py`, `engine/universe_filter.py`, `engine/eod_detectors.py`, `regime/snapshot.py`, `scanner/outcomes.py`, `risk/__init__.py`, `alerts/eod.py`).*

## Part 0 — Why it scores 3/10 (diagnosis only a code read can give)

The review says "the gate doesn't gate" and "readiness is saturated." Both are correct, and both have a single arithmetic root cause each. Naming them is prerequisite to fixing them.

**The readiness formula is degenerate by construction.** From `candidates.py:502-515`:
```
readiness = 20 (base)
          + min(30, count*7.5)   # confluence: 4 screeners → 30 pts
          + 15                    # theme (top-quartile sector)
          + 8/7                   # earnings: eps_yoy>0 → 8, eps_qoq>0 → 7
          + 0-10                  # delivery
          + 0-15                  # rs
          + 10                    # any trigger signal
          + 8/7/10/8              # launch_pad / ants / ep / ipo
```
A name that hits **4 ChartsMaze screeners + a top-quartile sector + eps_yoy>0 + delivery≥60 + rs≥70 + one EMA touch** scores `20+30+15+8+10+10.5+10 = 103.5 → clamped to 100`. That is *any moderately trending pharma name in a strong sector.* The formula is **additive over uncorrelated signals with no disqualifiers**, so it saturates at exactly the population the feed is full of. This is why 67 cards grade A+ and the top 12 are all ≥97.5. It is not a miscalibration — it is a structurally wrong scoring shape.

**The gate admits hundreds, then "selects" 80.** `candidates.py:591`:
```python
pool_symbols = list(dict.fromkeys(list(pool.keys()) + latest_symbols[:300]))
```
The candidate pool is the **union** of (confluence pool) and (the first 300 alphabetical EQ symbols on the latest trade date). Anything in that 300 that passes a `launch_pad`/`ep`/`ipo_base` detector fallback is admitted. `universe_filter.evaluate_symbol` then only drops ETFs/`<₹30`/`<₹5cr turnover`/circuit-locked/microcap-when-mcap-known. **There is no stop-distance gate, no R:R gate, no regime-aware count cap, no extension filter.** A "gate" with five floors and no ceiling on quality is a liquidity pre-filter, not an opinion.

**The 27% stop** comes from `candidates.py:129`: `stop = min(prior_lows)` over the trailing 20 sessions. On a trending name the 20-day low is structurally far away; it is **never bounded against `config.risk.max_stop_pct = 3.0`** — that config key is read by nothing.

**The EPS +55250%** is raw `quality["eps_yoy"]` surfaced at `candidates.py:427` (`f"+{eps_yoy:.0f}%"`) with no sanity clamp; ChartsMaze growth fields are ratios that occasionally carry percent-encoded or mis-parsed values. The "+-5%" sign bug is the same path.

**The readiness-vs-exit contradiction** (CAPLIPOINT) is two independent engines: `readiness` is built in `candidates.py`, `exit_state` in `eod_detectors.py:68`. They are never reconciled — a name can be `readiness 100` and `Weakening` simultaneously because nothing reads both.

**`risk/` is an empty file.** There is no `validate_plan()`, no `position_size()`, no `circuit_adjusted_stop()`. The sizer lives only in the frontend.

These six facts are the entire reason for 3/10. Everything below targets them.

---

## Area 1 — High-accuracy ENTRY (the selectivity problem)

**(a) Mechanism.** Precision in NSE momentum comes from **refusal, not addition**. Replace the additive score with a **latlice / gated rank**:
1. **Hard disqualifiers (must-pass, boolean):** regime allows this setup-type · `dist_from_21ema ≤ 5%` (not chasing) · `dist_from_pivot ≤ 4%` OR a fresh-leg breakout-day entry · best-valid stop ≤ 7% · R:R ≥ 1.5 · circuit band > stop distance · delivery_z ≥ 0 (no distribution into the trigger) · not in a pump-signature.
2. **Tiebreak rank (only among qualifiers):** a *non-saturating* score — e.g. rank by `(delivery_z, rs, confluence_families)`, displayed as an ordinal "1 of N that cleared the gate today," not a 0-100 that everyone maxes.

**Fresh-leg detection:** enter near the *origin* of a move, not after extension. Rule: a valid entry bar is (i) the breakout/pocket-pivot day itself, or (ii) the first 1-3 sessions of a reclaim where `close ≤ 1.05 × 21EMA`. Reject if `close > 1.08 × 21EMA AND rvol is already declining` — that is the chase that round-trips. The `dist_pivot` field is already computed (`candidates.py:131`); it is used as a chip and never as a gate. Make it a gate.

**Gap acceptance for EP:** the current `earnings_power` detector (`eod_detectors.py:188`) requires `gap_pct>0 + neglected_base + range≤8`. Good instincts, but it does not distinguish a *high-quality* gap (gap-and-go, fills <25%) from a weak one (gap then fills >50%, distribution into strength). Add: **reject EP if the day closes below the gap midpoint** (gap-fill > 50%). High-quality NSE earnings gaps rarely give back more than 30-40% of the gap intraday.

**Confluence quality > count:** today `_confluence_component` gives 30 pts for 4+ screeners regardless of family (`candidates.py:279`). Two screeners from *uncorrelated families* (a base/pattern family — VCP/tight/launch-pad — plus a momentum family — breakout/pocket-pivot/RS) carry more information than five from one family. Count **distinct families**, not raw hits.

**(b) Exact data fields.** `daily_prices` (close, high, low, prev_close, volume, delivery_qty, delivery_pct) · `screener_hits.screeners` (family mapping needed) · `symbol_quality.eps_yoy/eps_qoq/sales_yoy/asm_stage/market_cap_cr` · sector RS from `sector_metrics.rs_score` · 21EMA computed in `eod_detectors.ema()`.

**(c) Explainability.** Every disqualifier is a named, inspectable rule: "Excluded — chasing: close 8.4% above 21EMA." "Excluded — risk: best stop 9.1% > 7% cap." The tiebreak rank is an ordinal, not a fake-precision 97.5/100. The beginner sees "3 setups cleared tonight's gate"; the expert sees the per-rule pass/fail matrix.

**(d) Validation design (runnable on existing data).** Walk-forward over 2025-03→2026-07 (~340 sessions). The `outcomes` table already computes `forward_r` at T+5/10/20 — the plumbing exists (`outcomes.py:96`). Define **hit = forward_r ≥ +1.0 at T+10**. Bucket every historical candidate by each gate's presence/absence and compare hit rates: extension-gate-on vs off, delivery_z vs absolute-60, rs≥80 vs rs≥70. Require **≥200 outcomes per bucket** before trusting a delta; show n-count on every claim.

**(e) Quality metric.** *Realized T+10 hit rate (fwd_r≥1) and median forward_r, per (setup_type × regime) cell.* This is the one number that tells you precision moved. Secondary: **A+ cards per night** (should fall from ~67 to ~3-8; the target range IS the metric — a feed that serves 3-8 high-grade names is the product).

**What measurably separates 60%+ from 40% in NSE (testable hypothesis):** entry within 3% of a valid base · RS ≥ 80 (70 is too loose — most uptrending names clear 70) · regime SELECTIVE-or-better · **delivery% above the stock's own 50-day average** (not the absolute 60 floor — a 30%-average name delivering 50% is the signal; a 60%-always name delivering 60% is noise). Four conditions, all backtestable today.

**Flag — theatre:** pre-open / opening-range next-day entries are real edges in NSE *but we lack historical pre-open data* (Fyers captures live intraday; no historical pre-open store). Do not build the alert logic until you are capturing and persisting 9:00-9:15 IST indications; you cannot validate it otherwise. It is theatre today.

**Telegram alert structure:** push ONLY setups that are (grade A+) AND (cleared the gate) AND (regime ∈ RISK_ON/SELECTIVE) AND (revalidated = price cleared prior-day high with volume ≥ 1.2× avg). Everything else → one 7pm digest. One alert = one symbol, fields: `{symbol, setup, why (3 named rules), entry trigger, stop, size at regime cap, R:R, confirm button}`. The **confirm button writes to `journal_trades`** with the candidate snapshot attached — this is the bridge to Area 5's loop and kills the "empty manual form" failure. Trigger-push vs digest is itself a selectivity decision; if you push 12/night you are spamming, not alerting.

---

## Area 2 — Tight RISK planning

**(a) Mechanism.** Compute **three candidate stops** and pick the *tightest structurally valid* one:
- **Trigger-bar low / undercut low** (tightest; for pocket-pivot/shakeout/EP-continuation).
- **1.5 × ATR(14)** below the trigger low (for noisy names where the bar low gets hunted).
- **Structure:** below the base low or the 21EMA (for pullback/reclaim setups).

"Tightest structurally valid" = the smallest stop that sits below a real level, not the mathematical minimum (which would be 0.1% and useless).

**Hard risk gates (a trade that fails any is REFUSED — not displayed, not alerted):**
| Gate | Rule | Why |
|---|---|---|
| Max stop distance | best stop ≤ 7% (warn 5-7%, clean ≤5%) | `max_stop_pct=3.0` in config is unenforced and too tight; 7% rejects true chases, 3% nukes the feed |
| R:R floor | `(target−entry)/(entry−stop) ≥ 1.5` | `trade_plan` computes `rr` (`eod_detectors.py:272`) but never gates on it |
| Size within regime | `capital × regime_risk_pct / stop_dist` ≤ `max_open_risk_pct` | bands exist in `risk_profile` but aren't enforced |
| Circuit band > stop | intended stop distance < lower-circuit band | **NSE-specific:** a 5%-circuit name cannot be exited at your stop |

**(b) India-specific hazards (these are real money):**
- **Circuit limits cap same-day risk-free exits.** A name in a 5% lower circuit *cannot be sold* if it locks down — your "3% stop" is fictional. `circuit_locked()` (`universe_filter.py:65`) only detects high==low *after* it locks. You need the **circuit band (2/5/10/20%)** from the ChartsMaze circuit-revision feed (on-disk, un-ingested per STATE_OF_TOOL §1). Rule: if a name is in a 5% band, your *effective* stop is ≥5% regardless of placement — either accept the larger size haircut or refuse the trade.
- **Block-deal slippage in liquidity floor.** The ₹5cr turnover floor is averaged over 20 days, so a single block deal can mask illiquidity. Add: reject if today's turnover > 10× the 20-day average (likely a block deal, not organic liquidity).
- **ASM/GSM freeze.** Already excluded on entry (`asm_stage IS NOT NULL`, `candidates.py:607`) — good. But an ASM **transition** (a held name moving INTO long-term ASM) is a top signal; track it as a forced exit review, not just an entry block.

**(c) Explainability.** Build a `risk/plan.py` module — the **single writer** of the size number (anti-mashup) — with `validate(plan, regime, circuit_band) -> {pass, reasons[]}`. Every card shows: entry, *which* stop method was chosen and why, size, ₹risk, R:R, and either a green "risk clears" or a red "REFUSED: stop 8.2% > 7% cap." A refused card does not reach Telegram.

**(d) Validation.** Simulate the stop rule on historical A+ candidates: for each, compute the 3 candidate stops, apply the gate, record whether T+5/T+10 forward return stayed above the stop (i.e. would you have been stopped out?) vs the unbounded `min(prior_lows)` rule. Metric: **median realized stop distance** (should drop from ~12-27% to ~3-5%) and **% of candidates refused by the gate** (should be high — that is the point).

**(e) Quality metric.** *Median stop distance on accepted setups* (target ≤4.5%) · *R:R on accepted setups* (target ≥2.0 median) · *realized loss R on stopped trades* (target ≤ −1.0R median; no −4R outliers from 27% stops).

---

## Area 3 — PROFIT maintenance / drawdown avoidance

The exit engine (`eod_detectors.exit_state`) is actually the best-built piece — named rules (below-21EMA, below-50/200SMA, lower-low, downside-reversal, distribution days) → Intact/Weakening/Broken. The gap is **no trailing-profit logic** and **no portfolio layer.**

**(a) Mechanism — adaptive trailing by profit state:**
| State | Trail | Action |
|---|---|---|
| 0 to +1R | tighter of 21EMA or trigger-bar low | hold full |
| +1R reached | move stop to breakeven; trail 10EMA | **book 1/3** |
| +1R to +2R | 10EMA or 2-bar low | hold 2/3 |
| +2R or extension | 1-bar / undercut low | **book another 1/3** on extension |
| 21EMA lost on volume | n/a | **sell the turn** (weakness exit) |

The asymmetry: losers are killed small by the Area-2 gate (−1R max); winners are partial-booked so you keep ~60% of a big move instead of round-tripping. The heuristic — *"sell into weakness on a new trend break (lose 21EMA on rising volume = sell the turn); sell into strength on extension (3 days up >X% or close > 2 ATR above 21EMA = feed the strength)"* — is the profit-retention rule free sites don't productize.

**(b) Portfolio drawdown control (the single-user-account guard):**
- **Max open risk** = Σ position risk% ≤ `max_open_risk_pct` (config has 2.5/2.0/1.5/1.0 by regime — enforce it).
- **Max sector exposure** = ≤ 2 concurrent positions per sector. This single rule kills the "80% pharma" concentration risk.
- **Regime downgrade rule:** RISK_ON→SELECTIVE = no new adds; →DEFENSIVE = trim into next strength session; →NO_TRADE = flat except EP exceptions. *Regime changes position management, not just the feed.*

**(c) Explainability.** Each held position carries: current trail method + why ("+1.4R, booking 1/3, stop to breakeven, trailing 10EMA"). Portfolio panel shows: open risk used vs cap, sector concentration, "next regime action."

**(d) Validation.** Replay every historical A+ candidate with (a) the adaptive trail vs (b) a naive 21EMA trail vs (c) hold-to-target. Compare **captured R** (median and distribution). This is the one place the `outcomes` table is insufficient — you need to simulate the *exit path*, not just the T+N close. Build a small `backtest/trailing_replay.py` over `daily_prices`. Target: adaptive trail captures ≥1.5× the median R of the 21EMA-only trail without raising the loss tail.

**(e) Quality metric.** *Average winner R* (target ≥ +2.0R) · *average loser R* (target ≤ −1.0R) · **expectancy per trade** (the asymmetry: `win_rate × avg_win − loss_rate × avg_loss`, target ≥ +0.3R) · *max portfolio drawdown* in a replay (target < 12%).

---

## Area 4 — Smart REGIME awareness (compute → enforce)

The regime page *computes* a posture but it is advisory. The edge is enforcement. Today `filter_candidates` hardcodes `limit=80` (`candidates.py:700`) regardless of posture.

**(a) Mechanism — regime as a hard governor:**
| Posture | Feed count | Allowed setups | Size cap (risk/trade) |
|---|---|---|---|
| RISK_ON | top 12 | all cleared | 0.50-0.65% |
| SELECTIVE | top 6 | EP, IPO-base, A+ pullback, launch-pad | 0.35-0.50% |
| DEFENSIVE | top 3 | EP-with-surprise, A+ reversal only | 0.20-0.35% |
| NO_TRADE | 0 | none (tracking-only) | 0-0.20% |

The `preferred`/`avoid` lists already exist in `risk_profile` (`snapshot.py:280`) as JSON — they are display-only. **Enforce them:** in DEFENSIVE, drop non-EP setups entirely at the API.

**(b) The missing pillar is free — add VIX.** Volatility is currently UNKNOWN (`snapshot.py:220`) because no VIX/ATR aggregate is stored. NSE India VIX is free and public (niftyindices.com). Add a 30-line source. Rules: VIX > 20 → suppress size one band; VIX rising 3 consecutive sessions → tighten trails one band. This is the one missing data pillar and it costs nothing. Do not claim volatility-awareness works without it.

**(c) Sector rotation via RRG quadrant.** ChartsMaze RRG exists. Replace the blunt "top-quartile RS = +15 pts" boost (`candidates.py:284`) with an RRG-quadrant filter: **Leading** quadrant = eligible; **Lagging/Improving** = neutral; **Weakening** = suppress. Sharper than absolute RS rank because it encodes *direction* of rotation.

**(d) "Days like today" analog matching.** Take today's `(XP, R20, R50, VIX)` vector, find the 10 nearest historical sessions by Euclidean distance in `regime_snapshots`, report their T+1..T+5 Nifty resolution. Explainable (list the dates), not a black box. **Honest caveat:** you have ~340 sessions — too thin for a 4-D nearest-neighbor. Ship it as a labeled "thin-sample analog (n=340)" chip; trust it at n≥500. Moderate theatre-risk; keep it behind the expert toggle.

**(e) Enforcement point = one function.** `regime.governor(mode, setup_type, grade, count_so_far) -> bool`. The Setups endpoint AND `alerts/eod.py` both call it. One writer of "is this allowed tonight" — anti-mashup. Currently `_candidate_alerts` reads mode loosely (`eod.py:50`); route it through the governor.

**(f) Validation.** The regime is already point-in-time stored (`regime_snapshots`). Backtest: did "RISK_ON days" produce higher median T+10 forward_r than "DEFENSIVE days"? If not, the regime classification is noise and the enforcement is enforcing the wrong thing. Quality metric: **median forward_r by posture** (RISK_ON should dominate DEFENSIVE by a clear margin; if it doesn't, recalibrate `classify_market_mode`).

---

## Area 5 — Market-MECHANICS (NSE specifics) — *where the real retail edge lives*

This is the highest-value section. The four edges below are **systematic, do not require capital scale, and are not productized by Chartink/TradingView/ChartsMaze.** Everything else (RS, VCP, breadth, pocket-pivot) is commodity.

**Edge 1 — Post-announcement drift in under-covered small caps (THE informational edge).**
Under-covered names — no/few analyst estimates — gap on results and **drift 5-15 sessions** as the news diffuses through retail. Institutions can't deploy into ₹500-5000cr names; you can. The fact that *you lack consensus data is itself the signal*: if you don't have estimates, neither does the market.
- **Mechanism:** EP detector + `market_cap_cr` 500-5000 + low-institutional-ownership proxy (high delivery%, no recent bulk deals) + RS ≥ 80.
- **Fields:** `symbol_quality.eps_yoy/eps_qoq/sales_yoy/market_cap_cr`, `daily_prices.delivery_pct`, `eod_detectors.earnings_power`, the un-ingested bulk-deals feed.
- **Validation (highest-impact backtest you can run):** bucket all historical EP setups by market-cap decile; small-cap EP should show materially higher T+10 drift than large-cap EP. If confirmed, this is the feed's anchor setup. **This is the single most important research bet in the roadmap.**

**Edge 2 — Delivery % as accumulation, via z-score not absolute threshold.**
The current `_delivery_component(≥60)` (`candidates.py:305`) is the wrong framing. A stock that *usually* delivers 30% suddenly delivering 55% is accumulation; a 60%-always name delivering 60% is noise.
- **Mechanism:** `delivery_z = (today_delivery_pct − mean50) / std50`. Gate: `delivery_z ≥ +1.5` to enter; `delivery_z` *rising into a flat base* (delivery trending up while price sideways) = accumulation-before-breakout, a leading signal.
- **Fields:** `daily_prices.delivery_pct` over 50 sessions.
- **Validation:** bucket candidates by delivery_z; rising-z-into-base should predict breakouts (T+5 fwd_r) better than absolute-60.

**Edge 3 — Pump-signature detection as an EXCLUSION filter.**
NSE low-float names hit circuits on operator activity with no fundamental news; they mean-revert and trap retail. Free sites show these as "momentum winners."
- **Mechanism (exclude):** circuit hit + **no adjacent earnings/announcement** + `delivery_z > 3` + market-cap < ₹1000cr = pump signature. Hard exclude; never alert.
- **Fields:** `circuit_locked` + the announcement/results feeds (ChartsMaze, on-disk) + `delivery_z` + `market_cap_cr`.
- This is an edge because **exclusion is itself alpha** — a feed that refuses pumped names protects the user from the exact traps Chartink's "top gainers" lead them into.

**Edge 4 — ASM/GSM transitions as a risk-off tell.**
- A held name moving INTO long-term ASM often tops. Add a watchlist rule: **ASM-transition = forced exit review.**
- Market-wide: a spike in small-cap ASM additions = speculation peaking = risk-off tell. Track the count; feed it as a (secondary) regime input.

**What's real vs theatre for a retail single-user:**
| Mechanic | Real edge? | Why |
|---|---|---|
| Post-earnings drift (small-cap) | ✅ Yes — institutions can't size in | anchor setup |
| Delivery-z accumulation | ✅ Yes — leading, underused | entry gate |
| Pump-signature exclusion | ✅ Yes — protects from traps | exclusion = alpha |
| ASM-transition signal | ✅ Yes — surveillance timing | exit + regime |
| Bulk/block-deal footprint | ✅ if ingested | "held above bulk price" filter |
| RS / VCP / breadth / pocket-pivot | ❌ Commodity | free on every site |

---

## Cross-cutting — The journal→outcome→learnings loop (the un-copyable moat)

The plumbing exists (`outcomes.py` writes T+5/10/20 fwd returns for *every* persisted candidate) but **nothing feeds it back.** This is the design:

**Two loops, kept rigorously separate:**

1. **System loop (research-grade, all candidates).** Forward returns of *every* persisted candidate — taken or not — aggregated per `(setup_type, regime)` → hit rate and median R. Used to **recalibrate readiness weights and regime caps.** This is what proves the edge is real over time. Add a pipeline stage `expectancy.run` writing `setup_expectancy(setup_type, regime, n, hit_rate, median_r, as_of)`.
2. **Trader loop (personal, taken trades only).** `journal_trades` + the new TAKEN/SKIPPED capture → personal expectancy per setup/regime/**mistake-tag**, surfaced on cards. This is the asset a competitor cannot copy because they don't have *your* decisions.

**Anti-overfit (the part most people get wrong):**
- **Rolling windows, not full-history refits.** Recompute on a rolling 130-session (half-year) window. A full-history refit overfits.
- **Require monotone improvement on a held-out 30-session slice** before adopting any weight change. No adoption without out-of-sample proof.
- **Publish every recalibration** in `LEARNINGS.md` as a human-readable changelog ("EP-in-SELECTIVE hit rate dropped to 0.35 over 130 sessions → risk cap lowered"). No silent reweighting.
- **Show n-count on every expectancy chip.** Hide / mark "thin sample" below threshold.

**Minimum data before trusting:**
- **System loop:** ≥200 outcomes per `(setup_type, regime)` cell before its hit-rate overrides the prior. Top setup-types will cross this in months; EP/IPO won't for a year — be honest, show "n=42, thin."
- **Trader loop:** ≥30 taken trades per setup-type. Below that, **display the system expectancy as the prior** ("setups like this resolve +0.3R historically; your personal record is too thin to differ"). This is the honest bridge between no-data and enough-data.

**The SKIPPED data is as valuable as TAKEN.** One-click capture from a setup card → `journal_trades` with `status ∈ {taken, skipped}` + reason tag. If skipped A+ setups systematically resolve +1R, that's a learning ("you over-pass A+ EP in SELECTIVE regimes"). The capture must be one tap from the card (or the Telegram confirm/skip buttons), or it stays an empty form. **This is the single biggest missed opportunity in STATE_OF_TOOL §3.5 — wire it first.**

**One-opinion reconciliation (the other un-copyable property).** Before the loop matters, a card must not contradict itself. Today `readiness` (candidates.py) and `exit_state` (eod_detectors.py) run independently → CAPLIPOINT shows "100 setup + EXIT WEAKENING." **Rule: exit-state is a hard modifier on readiness, not a parallel number.** A `Weakening` state caps display grade at B; `Broken` removes the card. One symbol, one opinion, by construction.

---

## Prioritized roadmap (mapped to your existing task numbers)

Ordered by edge-impact × buildability on current data. Each is explainable and validatable as described above.

| # | Task | Edge impact | Existing task | Effort |
|---|---|---|---|---|
| **1** | **Recalibrate the readiness SHAPE**: hard disqualifier latlice (extension, stop≤7%, R:R≥1.5, circuit>stop, delivery_z≥0) + ordinal tiebreak rank. Fix the saturation at its arithmetic root. | 🔴 Critical | #33 | M |
| **2** | **Build `risk/plan.py`**: the single writer of size; `validate()` refuses non-clearing trades. Bound stops, compute R:R, enforce regime size caps, circuit-adjust. | 🔴 Critical | #35 (part) | M |
| **3** | **Regime governor + feed count cap**: `regime.governor()` called by Setups API + alerts; posture-driven `limit` (12/6/3/0) and setup-type suppression. | 🔴 Critical | #33 | S |
| **4** | **One-opinion reconciliation**: exit-state as a hard modifier on readiness (Weakening→cap B, Broken→drop). Kills the CAPLIPOINT contradiction. | 🔴 Critical | #34 | S |
| **5** | **Data-integrity clamps**: bound eps_yoy to [-200%, +500%] (flag outliers as "untrusted"), fix "+-5%" sign, refuse/hide stops >7%. | 🟠 High | #35 | S |
| **6** | **Ingest un-ingested ChartsMaze feeds**: circuit-revision (for circuit-band stop logic), bulk/block-deals (footprint chip), announcements (pump-signature exclusion needs "no adjacent news"). | 🟠 High | new | M |
| **7** | **Delivery_z + post-earnings-drift backtest**: replace absolute-60 with delivery_z; validate Edge 1 (small-cap EP drift). Highest-research-value work. | 🟠 High | new | M |
| **8** | **Adaptive trailing + portfolio layer**: implement the +1R/+2R booking table; enforce max-open-risk and ≤2-per-sector. | 🟠 High | new | M |
| **9** | **Journal-as-loop (TAKEN/SKIPPED capture)**: one-tap from card + Telegram confirm/skip → journal with snapshot; wire `expectancy.run` aggregation; surface per-cell expectancy on cards (with n-count, thin-sample labels). | 🟠 High | #36 | L |
| **10** | **Add VIX source** (free) → volatility pillar in regime; wire size/trail suppression. | 🟡 Medium | new | S |
| **11** | **RRG-quadrant sector filter** replacing blunt top-quartile boost. | 🟡 Medium | new | S |
| **12** | **Pump-signature exclusion** (circuit + no-news + delivery_z>3 + small-cap). | 🟡 Medium | new | M |

**Cut / defer (theatre or premature):**
- Tasks #30-32 (more detectors: EP neglected-base polish, overhead-supply chip, ADR metric) — Fable is right; stop widening the feed. Revisit only after #1-5 land.
- "Days-like-today" analog — ship behind expert toggle with thin-sample label at n<500.
- Pre-open / opening-range alerts — **defer until Fyers pre-open capture is built and persisted**; unvalidatable today.
- Top-indices panel, the 26-screener confluence inflation — commodity; collapse into one expert accordion.

**Sequencing logic:** #1-5 are the edge half (they make the gate refuse and the numbers honest) — they are mostly *removals and clamps*, fast to build, and each one *raises* the score independently. #6-9 build the moat (mechanics awareness + the learning loop). #10-12 sharpen. Do not start #9's UI until #1-4 make the cards trustworthy — capturing decisions against a self-contradicting 100-card feed pollutes the loop you're trying to build.

---

**One-line summary of the thesis:** the indicators are a commodity; the edge is **a gate that refuses (#1-5), mechanics-awareness free sites don't productize (#6-8, Edge 1-4), and a compounding private expectancy loop (#9)** — and every one of those is buildable from data you already have, explainable by named rules, and validatable on the `outcomes` table that already exists.
