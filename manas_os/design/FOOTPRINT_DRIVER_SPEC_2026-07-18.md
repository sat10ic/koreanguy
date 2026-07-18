# INSTITUTIONAL-FOOTPRINT DRIVER — activity v2 into the edge pipeline (wave 3)

Basis: v2 validated vs vendor demo sheet (Spearman 0.978 daily rank, spikes reproduce —
SMF_DEMO_SHEET_FIT_2026-07-18.md). Vendor's own methodology (tutorial): the score FLAGS unusual
institutional interest; the TRADE comes from your own price-action plan. That is exactly our
architecture — score never authors risk. LOCKED RAILS UNCHANGED: one-writer risk; score never
sizes/stops; rank influence only through promotion gates.

## Signal grammar (from validated v2 + vendor semantics + his dashboard columns)
- Tiers: >=3.5 ABNORMAL (ours) ~ his "strong" band starts ~5; >=8 EXTREME. Display both scales;
  chip copy uses plain words ("unusual", "extreme").
- PERSISTENCE beats spikes: streak (consecutive days >=3.5) + 4-day avg (his dashboard columns) —
  accumulation is a campaign, not a day.
- CONTEXT decides meaning (the key patch):
  * spike/streak WHILE PRICE QUIET IN BASE  -> STEALTH ACCUMULATION (gold case)
  * spike ON breakout/trigger day           -> CONFIRMATION (participation)
  * spike AFTER extension / on down closes  -> CHURN/DISTRIBUTION RISK (exit-side)
- Delivery display bands (vendor leak): delivery/traded >=50% strong · 25-50 moderate · <25 weak.

## Pipeline wiring (all existing machinery)
1. SCAN (have): alpha_activity_signals computed nightly (~2k symbols).
2. -> DEBATE auto-push: (UNUSUAL score AND in scan-pool-or-WATCH) joins the council shortlist as
   a "footprint" evidence line on the card. Shortlist cap 15 respected; footprint is selector
   INPUT evidence, shadow-weighted until replay proves it.
3. -> WATCHLIST auto-suggest: STEALTH-ACCUMULATION combo = (streak>=2 of >=3.5) AND (price in
   base/coil per WATCH-lane detector) AND (within 5% of pivot) -> auto-suggested WATCH card,
   reason: "institutional footprint building in a quiet base — Nth day". This fuses the
   anticipation lane with the footprint engine: the wait + the accumulation evidence together.
4. -> CARD CHIP everywhere (scan/debate/watchlist/positions): "Footprint 5.4 (unusual) · 3d
   streak · delivery 56% strong" + trend micro-bars (his 10-day trend column).
5. ENTRY: NEVER by score. Entry stays price-action (armed pivot / strong-start / plan). Score
   arms attention + can pre-arm the WATCH trigger. (Vendor says the same: score->shortlist->
   own plan.)
6. EXIT-SIDE: EXTREME footprint on down/churn days while holding = exit-engine evidence chip
   ("heavy churn against the position"); complements existing weak-delivery objection.
7. LEARNING (the moat): outcomes cells by footprint-tier x regime in setup_expectancy + Q4
   IC/ICIR on the factor. Promotion gates decide if footprint ever gains rank weight; until
   then evidence/display only.
8. EDGE-STACK: footprint = the "Volume Rush / institutional" chip of the 6-edge stack (partially
   implements the HVE leg; HVQ/HVY markers still separate).

## Done-tests
- A stealth-accumulation name (streak in base near pivot) auto-appears in WATCH with the reason line.
- A high-score gate-passed name shows the footprint evidence line on its DEBATE card.
- Positions show the churn warning when EXTREME fires against a holding.
- setup_expectancy gains footprint-tier cells; factors/health reports the factor's IC.
- Nothing about stops/qty/rank changes without a promotion-gate entry (leakage_audit clean).

Calibration note: Codex sparring run pending — if it finds a materially better formulation,
bands recalibrate before build; wiring above is invariant to that.

## LIVE LEG — real-time footprint proxy (rides P4 live loop; user 2026-07-18)
Physics: delivery %% is EOD-only (NSE publishes post-close) -> the validated full score CANNOT
exist intraday. The LIVE PROXY = the q-leg only: running avg-trade-size (cumulative volume /
cumulative trade count from the Fyers tick/quote stream) vs the symbol's own 20d EOD baseline.
q-only validated at Spearman 0.82 vs vendor scores -- good enough for CONFIRM/FILTER duty, never
selection. EOD run delivers the full-score verdict each evening ("live proxy said X, delivery
confirmed/denied").
Scope: ARMED-LIST symbols only (~10-30: WATCH lane + EP-PREP + open positions) -- not universe.
Uses (each = a check inside the existing P4 FSM confirmation stage, paper-first):
- STRONG-START CONFIRM: gap-holds + live avg-trade-size ratio >= its abnormal band = institutions
  participating in the start, not retail froth -> strengthens the 9:15-9:45 confirm.
- FAKE-BREAKOUT FILTER: price clears pivot but avg-trade-size SHRINKS vs baseline = suspect
  breakout (retail-sized prints) -> confirm-delay or refuse the push.
- SHAKEOUT/ABSORPTION READ: flush on small-trade prints then recovery on large prints inside the
  base = absorption (bullish shakeout); flush on LARGE prints = real distribution -> exit alert.
- FAKE-REVERSAL FILTER: bounce attempts on shrinking trade size = weak hands only.
Rails: paper mode + FSM replay harness first (exists); alerts only after replay shows the checks
reduce false-positives on recorded sessions; live NEVER authors risk (unchanged). Build order:
after P4 stage-2 (live LTP layer) lands; the check functions are pure and testable on recorded
tick logs first.

## SILENT-FLOW MATRIX — score x volume x direction (user 2026-07-18)
The score alone says "big participants active"; VOLUME LEVEL + PRICE DIRECTION say what they are
doing and whether anyone noticed. All from bhavcopy (volume vs 20d avg, close direction, range,
delivery, score). Per symbol-day classify:

| Score | Volume | Price | Read |
|---|---|---|---|
| HIGH | LOW/normal | flat, in base | SILENT ACCUMULATION -- institutions absorbing quietly; volume screens miss this BY DESIGN (the alpha case) |
| HIGH | HIGH | up/breakout | PUBLIC MARKUP -- everyone sees it; confirmation, not early |
| HIGH | any | down days at/after highs | SILENT OFFLOADING -- big prints into strength; esp. repeated high-score red days while price holds near highs |
| HIGH | HIGH | down, narrow range | ABSORPTION (Wyckoff) -- flush met by size; bullish if in/near base |
| LOW | HIGH | moving | RETAIL CHURN/froth -- small prints driving volume; fade-grade evidence |

Rolling structure (the campaign view, 20d window):
- silent_accum_days / silent_dist_days counts + NET SILENT FLOW = delivery-weighted signed
  balance (sign by close direction, weight by score, LOW-volume days NOT down-weighted -- the
  whole point is stealth days count fully).
- Card chip: "Silent flow: +6 accum days / 1 dist day (20d) -- net accumulating" or the mirror
  "3 offload days near highs -- distribution risk" (exit-side evidence on holdings).
- WATCH auto-suggest upgrade: stealth-accumulation combo (spec above) now requires/boosts on
  SILENT-quadrant days specifically, not just any score streak.
- OFFLOADING alert: >=3 silent-dist days in 10 near 52wH on a holding -> exit-engine evidence
  ("institutions appear to be selling into this strength").
Rails unchanged: display/evidence + expectancy cells (quadrant x regime) + Q4 IC; promotion
gates before any rank/gate influence. Done-test: quadrant classifier reproduces hand-labeled
examples; net-silent-flow chip renders on cards; offloading alert fires on a seeded fixture.

## UI — FLOW BOARD + STICKER REGISTRY (user 2026-07-18; wave-3 build w/ the classifier)
### Flow Board (the matrix, visual)
A WATCH/watchlist panel: five horizontal LANES = Silent Accumulation / Absorption / Public
Markup / Retail Churn / Silent Offloading. Each lane: lane title + one-line plain read + the
watchlist/armed symbols currently classified there as SymbolChips with a mini balance tag
("+6/1" = accum/dist days 20d) + net-flow micro-bars. Empty lane = honest "none today". Symbols
click through to chart/card. Sort inside lane by net silent flow. EOD-stamped per freshness rules.
### Sticker registry (ONE canonical set, app-wide -- anti-mashup: single source file)
desk/src/stickers.js exports the ONLY sticker definitions {code, glyph, label, plainRead,
sourceField, tokenColor}. Initial set (each maps to an EXISTING computed field -- no sticker
without a data source):
  SA silent-accum | SO silent-offload | AB absorption | FP footprint-unusual (tier)
  SS strong-start-ready | D2 day-2 setup | EP catalyst/earnings | IPO fresh-listing
  W anticipation-coil (WATCH) | NT new-tonight | LDR edge-stack high (when built)
  EXT extended/churn-risk | ASM surveillance-caution
Rules (visual-safety, binding):
- max 3 stickers per row/card + "+N" overflow popover; priority order defined in the registry.
- one shared <Sticker> component; v5 tokens ONLY (no new colors); mono 2-3 char glyphs; AA
  contrast; title/aria = plainRead (hover teaches the beginner the linkage).
- every sticker clickable -> the evidence that earned it (drill-in), never decorative.
- a STICKER LEGEND panel reachable from any tab header (the glossary of linkages).
- done-test: desk_gate + npm build clean, rendered pass on every tab (no wraps/overlaps at
  1280w, beginner + expert), each sticker traces to a live field on a real symbol, legend
  complete, screenshot QC before ship (the don't-break-visually gate).

## BUILD NUMERICS (2026-07-18, orchestrator — authoritative for the wave-3 backend build)
Codex correctly refused to invent thresholds; this section supplies them. Anything marked
(Assumption) is a code invention pending replay calibration — flag in code comments, do not
present as vendor/corpus doctrine.

### Source of the score — REUSE, do not recompute
`alpha_activity_signals` (manas_os/alpha/activity.py) is the ONE writer of the v2 score and
already holds per-(symbol, as_of_date): score, avg_trade_qty_ratio20, delivery_ratio19,
delivery_pct, persistence_sessions, state, quality_status. footprint.py is a CLASSIFIER layer
that JOINS alpha_activity_signals + daily_prices. It never recomputes the score.

### Tier constants (vendor-verbatim, from the ADJUDICATION section below)
ABNORMAL = 3.5 (score > 3.5) · STRICT = 4.0 · EXTREME = 8.0 (ours, Assumption) ·
STREAK = >=3 consecutive sessions score > 3.5 · AVG4 = 4-session mean score > 5.0.
Delivery bands: delivery_pct >= 50 strong · 25–50 moderate · < 25 weak.

### Price/volume vocabulary (bhavcopy-only, per symbol-day; ADR20 = mean of
(high-low)/close*100 over 20 sessions — same formula as scanner/discovery_metrics.adr20)
- volume_ratio = day volume / 20d avg volume (exclude today from the avg).
- volume HIGH: volume_ratio >= 1.5 (Assumption; gates.py uses 1.2 for breakout-day
  participation — 1.5 is deliberately stricter for "everyone noticed").
  volume LOW: volume_ratio <= 0.8 (Assumption). Else NORMAL.
- day direction: close > prev_close = up, < = down, else flat-tick.
- price FLAT: |day change %| <= 0.35 * ADR20 (Assumption — scale-aware, not a fixed %).
- range NARROW: (high-low)/close*100 <= 0.5 * ADR20 (Assumption).
- IN BASE: close >= 0.85 * max(high, last 60 sessions) AND close <= that high (i.e. within a
  15% correction of the 60d leg high, below the pivot). Mirrors CORRECTION_DEPTH_MAX family
  logic without importing discovery.
- NEAR HIGHS: close >= 0.95 * max(high, last 252 sessions).
- BREAKOUT DAY: close > max(high, prior 20 sessions ex-today) AND volume_ratio >= 1.2 (the
  existing gates.py breakout-day participation number).
- EXTENDED: close > 1.08 * EMA21 (the LOCKED exit-mode extension number).
- SPLIT-SUSPECT (exclude from tiers/streaks): close/prev_close outside [0.55, 1.45]
  (Assumption — catches 1:2 and worse splits/bonuses; circuit moves stay inside).

### context (3-way, from the Signal grammar section) — evaluated only when score > 3.5
1. stealth_accumulation_in_base: IN BASE and price FLAT (or |change| < ADR20) and NOT
   volume HIGH.
2. breakout_confirmation: BREAKOUT DAY (any volume read — the score itself is the size
   evidence).
3. churn_against_holding: (EXTENDED or NEAR HIGHS) and down day.
Else context = null ("unusual, uncategorized").

### lane (5-way Flow Board, from the SILENT-FLOW MATRIX table) — per symbol-day
1. silent_accumulation: score > 3.5 AND volume NOT HIGH AND price FLAT AND IN BASE.
2. public_markup:       score > 3.5 AND volume HIGH AND up day (or BREAKOUT DAY).
3. silent_offloading:   score > 3.5 AND down day AND (NEAR HIGHS or EXTENDED).
4. absorption:          score > 3.5 AND volume HIGH AND down day AND range NARROW AND
                        (IN BASE or NEAR HIGHS).
5. retail_churn:        score <= 2.0 (Assumption for "LOW") AND volume HIGH AND NOT flat.
Precedence when several match: absorption > silent_offloading > silent_accumulation >
public_markup > retail_churn. Else lane = null. `context` and `lane` are BOTH returned —
context is the 3-way meaning chip, lane is the Flow Board placement; they are separate
outputs, not a conflict.

### Rolling campaign view (20 sessions)
silent_accum_days / silent_dist_days = lane-1 / lane-3 day counts; net_silent_flow =
sum over 20d of sign(close-prev_close) * score on lane-1/3/4 days (delivery-weighted per the
matrix section: weight additionally by delivery_pct/100). LOW-volume days count fully.

### Schema DDL (additive)
CREATE TABLE IF NOT EXISTS footprint_daily (
  trade_date TEXT NOT NULL, symbol TEXT NOT NULL,
  score REAL, tier TEXT, streak_days INTEGER, avg4 REAL,
  delivery_band TEXT, volume_ratio REAL, day_change_pct REAL,
  context TEXT, lane TEXT, split_suspect INTEGER NOT NULL DEFAULT 0,
  silent_accum_days_20 INTEGER, silent_dist_days_20 INTEGER, net_silent_flow REAL,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  PRIMARY KEY (trade_date, symbol));

### API contracts
GET /api/footprint/{symbol}?date= -> {available, symbol, date, score, tier, streak_days,
  avg4, delivery_band, context, lane, split_suspect, doctrine_flags: {abnormal, strict,
  streak3, avg4_over5}, campaign: {silent_accum_days_20, silent_dist_days_20,
  net_silent_flow}, series: [last 20 {date, score, lane}]}
GET /api/footprint/board?date= -> {available, date, lanes: {silent_accumulation: [...],
  absorption: [...], public_markup: [...], retail_churn: [...], silent_offloading: [...]}}
  each entry {symbol, score, context, streak_days, balance: "Nacc/Ndist", net_silent_flow};
  board scope = symbols present in scan_candidates OR discovery_bucket OR watchlist for that
  date (not the whole universe), sorted by |net_silent_flow| desc inside each lane.

 -- Sonnet (v2 unrefit Spearman 0.969) + Codex (best fit 0.967, 3.7pct 2dp match). Formula unrecoverable (order-distribution variable / feed change); RANKING settled as reproduced. VENDOR-VERBATIM screen rules from transcript (Codex extract, replaces my invented tiers): >3.5 = abnormal (matches our ABNORMAL_LEVEL exactly); screening = last 3 consecutive days >3.5 (optionally 5); stricter daily filter >4; aggregate screen = 4-day avg >5; DIRECTION-NEUTRAL (accumulation or distribution -- context matrix decides); exclude split-distorted days. Adopt these as the WATCH/debate-push thresholds. Corrections: 216 F&O demo symbols; RELIANCE spike = 88.9pct in vendor sheet (not top-decile).
