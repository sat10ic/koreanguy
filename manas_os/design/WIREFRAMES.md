# MANAS 2.0 — ASCII Wireframes (Phase 3 handoff)

Layout contract for the visual rebuild. Shell (5 tabs + header) is KEPT; every panel body
below is NEW. Charting: ECharts for panels, lightweight-charts inside ChartDrawer.
`[B]` = beginner-mode element · `[E]` = expert-only (inside accordion / ShowDetails).
Data source noted per panel. One smart graph + one decision per screen.

═══════════════════════════════════════════════════════════════════════════════════════
GLOBAL SHELL (kept)
═══════════════════════════════════════════════════════════════════════════════════════
┌─────────────────────────────────────────────────────────────────────────────────────┐
│ MANAS OS   ●SELECTIVE  2026-07-06   [beginner|expert]  [⟳ Update]  ●Fyers  ●Data OK │ ← staleness chip
├─────────────────────────────────────────────────────────────────────────────────────┤   replaces Health tab
│  REGIME   SETUPS   FOCUS   WATCHLIST   JOURNAL                                      │
├─────────────────────────────────────────────────────────────────────────────────────┤
│ [B] ▼ TODAY'S FLOW  ①Data✓ ②Regime✓ ③Positions(1 action!) ④Setups(2 to review) ⑤Done│ ← T3.8 stepper
│     current step expanded w/ ONE primary button; [E] collapses to one-line strip    │   /api/flow/today
└─────────────────────────────────────────────────────────────────────────────────────┘

═══════════════════════════════════════════════════════════════════════════════════════
1. REGIME — "today's law"                                    /api/regime/summary + governor
═══════════════════════════════════════════════════════════════════════════════════════
┌── GOVERNOR PANEL (hero) ────────────────────────────────────────────────────────────┐
│  SELECTIVE — trade small and picky                                          [B]     │
│  ┌────────────┬─────────────┬──────────────────┬────────────────┬───────────┐      │
│  │ MAX CARDS  │ RISK/TRADE  │ ALLOWED SETUPS   │ OPEN-RISK CAP  │ PUSHES    │      │
│  │    4       │ 0.50-0.75%  │ [EP] [Base/Pat]  │  2.0% (1.2 used)│  ON       │      │
│  └────────────┴─────────────┴──────────────────┴────────────────┴───────────┘      │
│  WHY (plain): breadth cooling 3 days · leadership narrowing to 2 sectors ·          │
│               no distribution cluster yet                                    [B]     │
└──────────────────────────────────────────────────────────────────────────────────────┘
┌── TOP SETUPS STRIP [B] ──────────────────────────────────────────────────────────────┐
│  ① KPIL  EP  rank 1/4   ② ATUL pullback 2/4    → "2 of 4 reviewed"   [go to Setups] │
└──────────────────────────────────────────────────────────────────────────────────────┘
┌── [E] ▸ SHOW THE NUMBERS (accordion) ────────────────────────────────────────────────┐
│ ┌ Breadth heatmap (ECharts) ───────────┐ ┌ Sector rotation scatter (ECharts) ──────┐│
│ │ rows: XP band/4.5R/20R/50R/day-color │ │  y=RS Δ1w                ● PHARMA       ││
│ │ cols: last 20 sessions, hover=value  │ │  │        improving │ leading          ││
│ │ ██░░██████░░░░██████                 │ │  ┼──────────────────┼─────── x=RS      ││
│ └──────────────────────────────────────┘ │  │ lagging          │ weakening ●IT    ││
│ ┌ XP + participation lines (ECharts) ──┐ └──────────────────────────────────────────┘│
│ │ 60 sessions, 2 lines, labelled       │  Indices strip: NIFTY +0.3 · MIDSML +0.8…  │
└──────────────────────────────────────────────────────────────────────────────────────┘

═══════════════════════════════════════════════════════════════════════════════════════
2. SETUPS — "the feed that says NO"            /api/setups + /api/setups/refusals
═══════════════════════════════════════════════════════════════════════════════════════
┌── REFUSAL FUNNEL (hero, ECharts) ────────────────────────────────────────────────────┐
│   Universe 2,384 ─▶ Screeners 412 ─▶ Gates 37 ─▶ ✅ PASSED 4     (SELECTIVE cap: 4) │
│      └─ tradability -78 · trend-template -190 · fresh-leg -64 · risk -43   [hover]  │
└──────────────────────────────────────────────────────────────────────────────────────┘
┌── CARD (one per survivor, max = governor cap) ───────────────────────────────────────┐
│ KPIL   EP · catalyst          RANK 1 of 4 today          [TAKEN] [SKIPPED ▾reason]  │
│ gates: ●regime ●tradable ●trend ●fresh ●particip ●risk   (hover dot = reason)  [B]  │
│ ┌ PLAN ────────────────────────────────────────────────┐ ┌ EXPECTANCY ────────────┐ │
│ │ entry 924.50 · stop 892 (3.5%, gap-day low)          │ │ EP×SELECTIVE: 62% hit  │ │
│ │ R:R 2.4 · qty 1,850 (0.50% = ₹6,012 risk)            │ │ +0.8R med (n=47, sys)  │ │
│ │ watch-for: gap fills >50% = plan dead                │ │ yours: n=3 — thin      │ │
│ └──────────────────────────────────────────────────────┘ └────────────────────────┘ │
│ evidence: EPS +45%/+38% · gap 4.8% held · delivery +1.6σ · sector leading      [B]  │
│ [probation chip if ipo/flag family: "unproven — building sample, half size"]        │
└──────────────────────────────────────────────────────────────────────────────────────┘
┌── [E] ▸ NEAR-MISSES (top 10 refused) ── "SUNPHARMA — failed fresh-leg: 9.2% > 8%" ──┘

═══════════════════════════════════════════════════════════════════════════════════════
3. FOCUS (IPO + EP lens) — same funnel + cards filtered to catalyst family; adds
   base-age / days-since-listing / circuit-state columns. NO separate engine.
═══════════════════════════════════════════════════════════════════════════════════════

═══════════════════════════════════════════════════════════════════════════════════════
4. WATCHLIST — "positions + heat"     /api/watchlist + /api/portfolio/heat + coach
═══════════════════════════════════════════════════════════════════════════════════════
┌── HEAT ROW ──────────────────────────────────────────────────────────────────────────┐
│ ┌ OPEN RISK gauge ─────┐ ┌ SECTOR donut ─┐ ┌ PROGRESSIVE EXPOSURE ────────────────┐ │
│ │ 1.2% ▓▓▓▓▓░░░ cap 2.0│ │ PHARMA 2 ⚠max │ │ last-10-trade avg R: +0.3 → full size│ │
│ └──────────────────────┘ └───────────────┘ └──────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────────────────┘
┌── POSITION COACH CARDS (open positions first) [B] ──────────────────── T3.9 ─────────┐
│ ⚠ TITAN  +1.1R → ACTION: move stop to 902 (breakeven) + sell ⅓ (620 sh)  [steps ▾]  │
│ ● KPIL   +0.4R → HOLD — initiation phase, wobble is normal until 892 breaks          │
│ 🔴 HFCL  EXIT TODAY — 2 rules fired (lost trail + distribution). Unacted 2 days!     │
└──────────────────────────────────────────────────────────────────────────────────────┘
┌── WATCH TABLE (sortable, color-banded) ──────────────────────────────────────────────┐
│ SYM    │RS │ADR%│dlv_z│dist-pivot│exit-state│trail   │days│open R│                   │
│ ATUL   │91 │ 4.2│+1.3 │  -0.8%   │ Intact   │21EMA   │ —  │  —   │  ← sort any col   │
└──────────────────────────────────────────────────────────────────────────────────────┘

═══════════════════════════════════════════════════════════════════════════════════════
5. JOURNAL — "the moat rendered"          /api/journal + expectancy + outcomes
═══════════════════════════════════════════════════════════════════════════════════════
┌── EQUITY CURVE in R (ECharts line, hero) ──── cumulative R, drawdown shaded ─────────┐
└──────────────────────────────────────────────────────────────────────────────────────┘
┌ EXPECTANCY MATRIX (heatmap) ─────────────┐ ┌ MFE/MAE scatter ──────┐ ┌ R histogram ─┐
│           RISK_ON  SELECTIVE  DEFENSIVE  │ │  MFE│  ° winners      │ │ ▂▄█▄▂ losers │
│ catalyst   +0.9R    +0.6R      n<20 grey │ │     │ °°  ° kept?     │ │ capped -1R?  │
│ base/pat   +0.4R    n<20       n<20      │ │     └────── MAE       │ └──────────────┘
│ momentum   +0.2R    -0.1R      n<20      │ └───────────────────────┘                 │
│  (cell = posterior R · label = n)        │  MISTAKE PARETO: fear-exit ████ chase ██  │
└──────────────────────────────────────────┴───────────────────────────────────────────┘
┌ FOUR-COHORT STRIP: taken +0.6R │ pushed-skipped +0.9R(!) │ armed-skipped │ refused -0.2R ┐
│  READ: "you skip winners — your pushed-skipped outperform your taken"            [B] │
└──────────────────────────────────────────────────────────────────────────────────────┘

═══════════════════════════════════════════════════════════════════════════════════════
6. CHART DRAWER (overlay, opens on any symbol click)   /api/symbol/{s}/ohlc + journal
═══════════════════════════════════════════════════════════════════════════════════════
┌ KPIL  [SETUP|TREND|EXIT tabs]                                            [CLOSE] ────┐
│ ┌ lightweight-charts: candles + vol ──────────────────────────────────────────────┐ │
│ │   zoom/pan/crosshair native · EMA 10/21/50 · AVWAP(auto-anchor, reason on hover)│ │
│ │   ── buy-zone band ── · ─ stop line ─ · ▲entry ▼exit arrows · ●pocket-pivot     │ │
│ └──────────────────────────────────────────────────────────────────────────────────┘ │
│ compact legend (one line) · stage: 2 · trail: 21EMA · [E] RS-line pane · TTM pane    │
└──────────────────────────────────────────────────────────────────────────────────────┘

═══════════════════════════════════════════════════════════════════════════════════════
MODE RULES: [B] beginner = flow stepper + governor + coach + ≤cap cards, plain English
everywhere; [E] expert = strict superset via accordions/ShowDetails. Safety states
(stale banner, DATA DOWN, EXIT alerts) render identically in BOTH modes — never hidden.
═══════════════════════════════════════════════════════════════════════════════════════
