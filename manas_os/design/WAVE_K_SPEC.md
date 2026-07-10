# WAVE_K_DISCOVERY — Spec: turning the refusal cascade into a discovery-first funnel

**Author:** Opus deep research over the Arora corpus, 2026-07-10. Transcribed verbatim by the
orchestrator from the research deliverable.
**Scope honored:** no threshold changed anywhere; spec + harness design + source evidence only.
risk/plan.py remains the sole money-math author (its LOCKED thresholds are *proposed* for
change with evidence; its authority is untouched). One writer per new metric.
**Reading note:** CHARTGYM compilation carries annotated charts as external image URLs w/ text
captions — captions and per-week symbol+date headers were read (usable for the label set);
pixel annotations not inspected. Codeable numeric criteria come from the transcript sources.

## PART A — What Arora actually picks, and where our pipeline excludes it

Selection = two-part: a universe/velocity screen, then a structure read (buying force + clean
contraction). Cited values:
- Universe/velocity ("one scan is enough"): groww 3.txt — NSE only (BSE rejected for
  liquidity), 30d avg volume >= 2 lakh shares, relative volume > 3x, day change >= 3%.
  Reinforced by CHARTSMAZE_TEMPLATE_CRITERIA.md (turnover Price×MA20vol > 3-5cr, exclude 5%
  circuit; NITIN/HIREN/CHHIRAG templates).
- Buying force: groww 2.txt + CH3.1 Layout and Scans.md ("green number") — stock up
  >= 30-35% from its 3-month (65-day) LOW. His #1 momentum signal — measured off the low,
  not off the 52w high.
- Velocity ("purple dot"): groww 2.txt, CH3.1 — dot prints on >5% move (either direction) on
  >5 lakh volume; more dots = faster+more liquid; ZERO dots (Reliance, Maruti) = skip
  regardless of setup. An ADR/velocity gate — refuses slow names outright.
- Correction depth: groww 2.txt — pullback <= 25-30% from leg high; >30% = avoid. Good
  examples 17/19/26%; bad 45%.
- Consolidation quality (VCP): groww 2 + groww 4 — no big red-dot (heavy-volume down) day in
  the pullback; up-volume >> down-volume; contracting ranges (100->70->80->90/95 then break).
  "For me VCP is a principle, not a pattern" (groww 5).
- Extension from 10-week MA: CH3.1 ("yellow number") — wants 8-12% from the 10wMA, refuses
  25-40%+; NATURE-RELATIVE (small caps run 40%+, large caps ~17%).
- Swing expectation per-stock: groww 5 — small caps swing 64-151%, large caps 20-30%; compare
  each candidate to ITS OWN history for the target.
- RS is visual, not a rating: CH3.1 — "no RS rating, no '85 and above'... stock in an uptrend
  when the market is down = your future leader."

### The 8 mismatches (our rule -> source it contradicts)
1. Pool anchored to 52-week high (detector_shortlist close>=0.85x252dH; gate_trend_template
   refuses nearness<0.85) vs Arora's 3-month-low anchor — rising-off-the-low reversals
   (BSOFT, Zentec, NCC in 6 Manas Entry) never enter our pool.
2. NO velocity/ADR gate exists. symbol_timing computes adr display-only; no purple-dot count
   anywhere. His FIRST filter is exactly this. We neither find fast movers nor exclude slow.
3. Absolute % stop caps (plan.py STOP_CAP_EXCEPTIONAL=7.5, ABSOLUTE=8.0, regime 4-6%) vs his
   nature-relative, timeframe-flexible stops ("2.5% default... but the stock is a beast";
   CH3.1: hourly/15-min entry gives a 1-1.5% stop). High-ADR name = wider stop with SMALLER
   SIZE, or tighter LTF stop — never a hard 7.5% wall.
4. Contraction/consolidation quality never computed as a discovery signal (only narrow
   launch_pad/ipo_base TVCP): no correction-depth<=30%, no no-heavy-red-day, no range
   contraction metric — the core of groww 2/4.
5. R:R floor measured off NEAREST micro-resistance (plan.structural_target; entry+1ATR
   synthetic) under-measures fresh-high/IPO names — blue-sky names have trivially-close
   "overhead" -> tiny measured move -> artificially low R:R. Arora targets the stock's own
   typical swing. DIRECT CAUSE of GROWW's R:R 1.19.
6. Regime gate hard-drops whole families (SELECTIVE = {catalyst, base/pattern} only) vs D2/
   momentum working on individual strength even in muted tapes (D2 text Q6); reversals/
   strong-starts are bread-and-butter in all but NO_TRADE.
7. RS hard floor 80 (gates.RS_FLOOR) vs visual RS, future leaders found before any rating
   catches up.
8. Single-timeframe (daily) everything vs his four-screen layout; LTF used to RESCUE trades
   failing the daily-stop threshold — precisely the GROWW failure mode.

## PART B — The GROWW autopsy
Refusal: "stop 7.5% exceeds 7.5% cap (SELECTIVE, exceptional); R:R 1.19 below 1.5 floor."
Recently-listed fast mover (ipo_base -> exceptional 7.5% cap). Ran the next day. Two
independent kills, both absolute-vs-relative errors a practitioner overrides:
- Stop cap (mismatch 3): knife-edge on an absolute number. Source-faithful: cap as k×ADR20;
  for a high-ADR IPO, 7.5% daily can be <1×ADR (structurally TIGHT). Take with reduced size
  (validate already sizes off risk) or drop to LTF for a 1.5% stop. Our code computes only a
  daily-bar stop — no way to tighten, no way to judge 7.5% as ADR-normal vs ADR-extreme.
- R:R floor (mismatch 5): 1.19 comes from nearest-resistance logic on a just-listed blue-sky
  name with no meaningful overhead. Source-faithful: measured move from the stock's OWN
  swing-magnitude history; for a fresh high-velocity IPO that's a multi-ATR burst.
Conclusion: neither is a genuine untradeable — exactly the class of refusal that should be a
SCORED OBJECTION in Stage 2, not a silent kill.

## PART C — Discovery-first funnel redesign (refuse-SECOND)

### Stage 1 — SENSITIVE BUCKET (30-80 names/day; recall-optimized)
> **2026-07-11 (WAVE K10, C2 decision):** restated to **~100-140 names/day, deduped by
> distinct symbol** — the 30-80 figure predates the archetype set growing to 8-9
> recall-first detectors (each with its own per-archetype cap, K7-K10); a Stage-1 union
> across that many detectors correctly lands near 100-140/day, not 30-80. No global
> Stage-2 ranker was built to force it back down (see WAVE_K10_SPEC.md Part F) — the
> aggressive narrowing stays at Stage-2/gate where per-name evidence can rank names on
> comparable ground. Original line preserved below for history.
Dynamic (percentile / ADR-relative), never absolute. Enter on base eligibility AND >=1
archetype; archetype tags travel to Stage 2.
Base eligibility: NSE EQ; price>=30; 30d avg vol >= 2 lakh sh; turnover >= 3cr; exclude 5%-
circuit/ETF/ASM [groww 3, CHARTSMAZE criteria]. Buying force >= 30% from 65d low OR top-40th-
pctile 63d momentum [groww 2, CH3.1]. Velocity: purple_dot_count_60d >= threshold OR ADR20 in
top universe pctile [groww 2, CH3.1].
Archetypes (each SENSITIVE — recall is the point):
 a. Strong-Start-ready: prev-day range in bottom pctile of own 20d ranges + uptrend
    [Tightness Study]
 b. Pullback-to-rising-MA: close near rising 10/20 SMA; correction depth <=30% from leg
    high; no heavy-red-day in pullback [groww 2, 6 Manas Entry]
 c. Tightness/VCP coil: ATR20 bottom pctile; contracting successive pullbacks [groww 4, 2]
 d. Reversal: strong prior uptrend + down 3-5 days on declining volume [6 Manas Entry]
 e. D2/episodic: Day-1 >=10% expansion (or 20% circuit) out of consolidation [D2 text]
 f. EP / IPO base: existing detectors.
New one-writer metrics (additive, NO gating this wave): adr20, purple_dot_count_60d,
pct_up_from_65d_low, correction_depth_from_leg_high, prev_day_tightness_pctile,
range_contraction_flag.

### Stage 2 — RANK + REFUSE (existing gates recast)
- Hard-refuse ONLY genuine untradeables: ASM, sub-30/illiquid/ETF, circuit-locked, lottery/
  pump signature (stays in gate_tradability).
- Everything else = SCORED OBJECTION surfaced to the debate, not a silent kill: trend-
  template (nearness, RS floor, EMA-stack), fresh-leg (already shadow via
  enforce_staleness=False), participation, plan R:R floor / stop cap. Ranking = LOCKED
  tiebreak + archetype-match count + velocity percentile.
- plan.py stays sole money-math writer. Two PROPOSED (not applied) threshold changes:
  (1) stop cap as k×ADR20 alongside the absolute ceiling; (2) EXCEPTIONAL-family measured
  move defaults to own-history ADR-burst, not nearest resistance.

### Validation — sensitivity/recall metric
Recall = % of hand-labeled practitioner picks present in the Stage-1 bucket on their entry
date (and day before). Label set from: CHARTGYM per-week symbol+date headers (GESHIP,
NAVINFLOUR, POCL, BSOFT, JAYNECOIND...), Tightness Study named examples (Birlasoft 12-Jun,
Intellect 21-Aug, EMS 6-Nov...), 6 Manas Entry trades (Parag Milk, Tata Invest, BSOFT,
Zentec, NCC), and GROWW. Secondary: bucket-size distribution (30-80), precision proxy
(bucket forward-return vs universe).

## PART D — Tasks (Sonnet-sized; harness FIRST)
K1 Labeled practitioner pick-set -> manas_os/data/labels/practitioner_picks.csv
   {symbol, entry_date, archetype, source_cite}; map to daily_prices; unmapped log.
K2 BASELINE recall harness (scratch, read-only): current pool recall % per archetype +
   bucket-size distribution. THE number that quantifies the complaint. No production change.
K3 Additive discovery metrics (shadow, one writer each, unit tests). Persist to
   counterfactual_* only.
K4 Stage-1 sensitive bucket (counterfactual only; archetype tags; 30-80/day target) in
   backtest/replay.py persist_counterfactual path — does NOT touch scan_candidates.
K5 Stage-2 recast spec + shadow wiring: would_object field alongside would_refuse_stale;
   hard-refuse only untradeables. No behavior flip.
K6 Recall delta report: baseline vs Stage-1 recall, per-archetype, bucket sizes; explicit
   GROWW row (present? which archetype?).
K7 GROWW autopsy fixture: reproduce the exact refusal; demonstrate in shadow that ADR-
   relative stop + own-history measured move convert both kills into passing objections.
   Evidence for the two plan proposals; no plan.py edit.
Order: K1 -> K2 -> K3 -> K4 -> K5 -> K6 -> K7.

Key files: scanner/candidates.py (detector_shortlist L441, confluence_pool L342,
symbol_timing adr L280, candidate_for_symbol L629); scanner/gates.py (ALLOWED_FAMILIES L22,
RS_FLOOR L28, nearness L178, fresh-leg L187); risk/plan.py (STOP_CAP_* L20-23, RR_FLOOR L24,
structural_target L116, validate L186); engine/eod_detectors.py; engine/universe_filter.py
(GateConfig L56). Sources: study/Manas Arora/groww {2,3,4,5}.txt, Course Notes/6 Manas
Entry.md, cleaned/CH3.1 Layout and Scans.md, cleaned/Strong_Start_Tightness_Study.md,
study/Tradetm/D2 Entry text, design/CHARTSMAZE_TEMPLATE_CRITERIA.md, LEARNINGS.md WAVE_J/J7.
