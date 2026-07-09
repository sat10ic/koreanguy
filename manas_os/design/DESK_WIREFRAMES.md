# DESK_WIREFRAMES — layout contract for the living-desk frontend (greenfield manas_os/desk/)

Build law: build TO these ASCII blocks, element-for-element. Done-test per panel is
two-direction: (1) every element here exists on screen; (2) nothing on screen is absent
here. VISUAL DIRECTION: 'DESIGN_SPEC - desk.md' (user-authored 2026-07-09, per user 'inspiration not law' — orchestrator holds styling discretion and has chosen to follow it: dark charcoal/cyan/purple/green, compact density, mono data values; deviate only where usability clearly wins, note deviations). This file governs LAYOUT. Every [data: ...] tag names the table/endpoint feeding the element.
Every number rendered must exist in a payload today — invented metrics are defects; where
a panel needs a field that does NOT exist yet it is marked **BACKEND-GAP** and listed at
the file end. [B] = plain-English beginner caption shown as help text. NO old-frontend
vocabulary: no posture command bars, no poster bands, no DensityContext.

## GLOBAL SHELL (wraps every tab)
```
┌───────────────────────────────────────────────────────────────────────────────────┐
│ MANAS DESK   ◀ [ 2026-07-08 ▾ ] ▶   ● REGIME: SELECTIVE · day 6   XP 62   ⦿DRY-RUN │  ← header
│              └date scrubber, replays any past night┘  └MBI day-color chip┘ └badge┘  │
├───────────────────────────────────────────────────────────────────────────────────┤
│  [ DESK ]   DEBATE   POSITIONS   LEDGER                          ◔ pipeline running │  ← tab nav + live dot
└───────────────────────────────────────────────────────────────────────────────────┘
[data: header regime+age = run_card.regime {mode,age_days}; MBI day-color + XP = MBI/XP feed
 (BACKEND-GAP-1); DRY-RUN vs LIVE = config agents.telegram_live; scrubber date drives every
 tab's ?date= param; live dot = pipeline_runs has an in-progress row for today]
[B] "The date arrows scrub back in time — pick a past night and the whole desk replays it."
GLOBAL STATE — stale data banner (shown above tab nav when data older than scrubbed date):
┌───────────────────────────────────────────────────────────────────────────────────┐
│ ⚠ Data fresh only through 2026-07-07 — last night's run did not complete.           │
└───────────────────────────────────────────────────────────────────────────────────┘
[data: run_card.pipeline last stage status; banner if any stage != ok for scrubbed date]
```

## 1. DESK — the living home  [data: GET /api/desk/feed?date= + GET /api/desk/run-card?date=]
```
┌─ MORNING BRIEF ─────────────────────────────────────────────────────────────────────┐
│ Last night the desk reviewed 14 names. Models agreed on 2 (SYRMA, KPIL), split 2-1   │
│ on GABRIEL. Vision demoted SYRMA — "base too loose". Sizer took KPIL 0.75x            │
│ (SELECTIVE, heat 0.5/2.0%). One coach alert: HUDCO stop unchanged, wobble normal.     │
│ [data: run_card morning_brief narrative — BACKEND-GAP-2 (run_card has no narrative    │
│  string today; AGENT_UI says one cheap LLM call composes+stores it at end of run)]    │
├─ REGIME STRIP (the two explicit KEEPS, rendered fresh) ──────────────────────────────┤
│  ● MBI  day-color GREEN   adv/dec 312/188   ratio 1.66      │   XP  62 ▲   dial ◕      │
│  [data: MBI breadth + XP value = MBI/XP feed — BACKEND-GAP-1]                          │
│  [B] "MBI = how broad the market's strength is today. XP = the desk's readiness score"│
├─ ACTIVITY STREAM  (reverse-chronological; each row expands to its artifact) ──────────┤
│ 18:41  ⬢SIZER     2 picks sized · KPIL 0.75x (why: split debate, fresh regime)     ▸ │
│ 18:39  ⬢VISION    demoted SYRMA — "base too loose" · promoted KPIL +1              ▸ │
│ 18:36  ⬢GEMMA     disagrees on GABRIEL (2/5 vs Nemotron 4/5) — flagged            ▸ │
│ 18:33  ⬢NEMOTRON  ranked 14 names · top: KPIL, SYRMA, GABRIEL                      ▸ │
│ 18:31  ⬢GATES     1,029 → 259 → 34 → 14 shortlist (SELECTIVE, day 6)              ▸ │
│ 18:30  ⬢PIPELINE  data fresh through 2026-07-08 · 16 stages ok                     ▸ │
│ [data: scan_agent_logs (agent,model,latency,created_at) + pipeline_runs + agent_verdicts;│
│  agent chip = stable identity per model/role; ▸ expands to transcript/chart/plan]     │
├─ IN-FLIGHT ROW (live mode; AD5 worker states waiting|running|done|failed|blocked) ────┤
│ 18:42  ⬢GEMMA     reading 14 charts…  ◔ running (started 41s ago)                     │
│ [data: scan_agent_logs row exists, latency_ms NULL → "running"; heartbeat = created_at │
│  age; failed→"429, retrying"; blocked→"waiting on upstream stage"]                     │
└───────────────────────────────────────────────────────────────────────────────────┘
DEGRADED-NIGHT VARIANT (thin/failed night must look INTENTIONAL, not broken):
┌───────────────────────────────────────────────────────────────────────────────────┐
│ MORNING BRIEF: Thin night. Shortlist of 2. One model (Nemotron) returned clean;      │
│ two others rate-limited (429) or truncated. Chair struck both on distribution risk.  │
│ Sizer took 0 — the desk sat out. Nothing to send. This is a normal quiet night.      │
│ ⬢NEMOTRON done · ⬢QWEN failed 429 · ⬢HY3 failed truncated · ⬢CHAIR struck 2/2       │
│ [data: run_card debate[].parsed_ok + errors[]; degraded framing driven by counts,     │
│  never a red error state — a struck/sat-out night renders as a deliberate outcome]    │
└───────────────────────────────────────────────────────────────────────────────────┘
EMPTY VARIANT: "No run for 2026-07-08 yet. The desk runs after market close (~18:30)."
[data: /api/desk/run-card returns {available:false}]
```

## 2. DEBATE — the theater  [data: GET /api/agents/verdicts?date= (agent_verdicts, all agents)]
```
┌─ KPIL · lens STRONG START · CHAIR: TAKE ────────────────────────────────────────────┐
│ Conviction   Nemotron ●●●●○(4)   Gemma ●●●○○(3)   Qwen ●●●●●(5)     spread 2          │
│              └────── stacked model dots; disagreement gap highlighted ──────┘         │
│ [data: agent_verdicts.conviction per model row; chair row verdict; lens = setup_family;│
│  spread + disagreement flag = chair row lens_scores_json.conviction_spread/disagreement]│
├─ BULL (per model, attributed) ───────────┬─ BEAR (per model, attributed) ────────────┤
│ Nemotron: "quiet base + delivery surge,  │ Gemma: "third pullback, extension risk,   │
│  pivot clean at 892"                      │  RR only 1.8"  ← dissenter, given weight   │
│ Qwen: "tight VCP, volume dry-up"          │ Nemotron: "gap-fill overhead at 910"      │
│ [data: agent_verdicts.bull_case / bear_case, verbatim, per model row — never blended]  │
├─ VISION STRIP ───────────────────────────────────────────────────────────────────────┤
│ [ KPIL_daily.png ]   [ KPIL_weekly.png ]   stamp: "pivot clean, volume dry-up ✓ +1"  │
│ [data: chart PNGs = data/agent_charts/{date}/{SYM}_{daily,weekly}.png via image endpoint│
│  BACKEND-GAP-3; stamp = agent_verdicts vision row reasoning (what_i_see) + verdict]    │
├─ PLAN  [math: engine — authored by risk/plan.py, NOT the LLM] ────────────────────────┤
│ entry 892.0   stop 861.5   target 953.0   RR 2.0   base qty 34                        │
│ [data: scan_candidates row entry/stop/target/rr/suggested_qty]                         │
│ SIZER: 0.75x → final qty 25 · "split debate, fresh regime, VIX 14 favors size"        │
│ [data: sizer agent_verdicts row lens_scores_json.multiplier/final_qty + reasoning]     │
├─ FOOTER ──────────────────────────────────────────────────────────────────────────────┤
│ base rate STRONG_START × SELECTIVE: 6/13 (46%, n=13)   Nemotron on STRONG_START 5/9   │
│ [data: base rate = setup_expectancy via expectancy.chip_for; per-model record chip =   │
│  agent_verdicts grouped by agent×setup_family on outcome_r — BACKEND-GAP-4 (no endpoint)]│
└───────────────────────────────────────────────────────────────────────────────────┘
ZERO-TAKE NIGHT STATE ("the desk sat out — here's why"):
┌───────────────────────────────────────────────────────────────────────────────────┐
│ The desk took nothing on 2026-07-08. 2 names debated, both struck.                   │
│  SYRMA  — chair struck: "distribution risk, near ASM watch"                          │
│  RELTD  — chair struck: "correlated with SYRMA, event risk in bear case"             │
│ [data: agent_verdicts chair rows verdict=SKIP + reasoning (strike_reason)]            │
└───────────────────────────────────────────────────────────────────────────────────┘
EMPTY: "No debate for this date — shortlist was empty or the debate stage didn't run."
```

## 3. POSITIONS — the coach on duty  [data: GET /api/watchlist coach field + journal + agent_signals]
```
┌─ HUDCO · open · entry Jul 3 @ 214.0 ────────────────────────────────────────────────┐
│ R-path  ┤              ╭──╮        now +1.4R                                          │
│    +2R ─┤          ╭───╯  ╰─╮   ── trail stop 228 ──                                  │
│    +1R ─┤     ╭────╯        ╰──                                                       │
│     0  ─┤╭────╯   INITIATION │ TREND │ EXTENSION                                      │
│         └┴─────────────────────────────────────────                                   │
│ [data: R series computed from daily_prices + candidate entry/stop; phase bands +      │
│  trail line = eod_detectors.trail_plan (phase, trail_stop)]                           │
│ COACH: "HOLD — wobble normal until 892 breaks."                                       │
│ [data: agent_signals channel='coach' latest message for symbol]                       │
│ ┌ ORIGINAL THESIS (Nemotron, Jul 3) ──────────────────────────────────────────────┐  │
│ │ "quiet base + delivery surge." Still intact — delivery holding, base low untouched.│ │
│ └──────────────────────────────────────────────────────────────────────────────────┘  │
│ [data: thesis = agent_verdicts model bull_case near trade date; coach quotes it back]  │
├─ TELEGRAM MIRROR ─────────────────────────────────────────────────────────────────────┤
│ ✔ sent 18:44  "HUDCO HOLD · stop 228 · thesis intact"   (dry-run: shown, not sent)    │
│ [data: agent_signals.sent (1=sent / 0=dry-run persisted); badge mirrors global DRY/LIVE]│
└───────────────────────────────────────────────────────────────────────────────────┘
URGENT / EXIT-OVERDUE VARIANT (two_strike exit_now — never suppressed, LOCKED rule):
┌───────────────────────────────────────────────────────────────────────────────────┐
│ ⛔ ADORWELD · EXIT NOW — two strikes fired (close < trail 2 sessions).                │
│    Coach: "your thesis (base breakout) broke — support gave way on volume."           │
│ [data: agent_signals coach row stance=urgent; deterministic action from two_strike]   │
└───────────────────────────────────────────────────────────────────────────────────┘
EMPTY: "No open positions. Entry signals appear here once the desk takes a name."
```

## 4. LEDGER — memory made visible  [data: agent_verdicts outcomes + lessons/*.md + journal]
```
┌─ AGENT TRACK RECORDS (agent × lens × regime) ───────────────────────────────────────┐
│ AGENT      LENS           REGIME      HIT     AVG R    n    TREND                     │
│ Nemotron   STRONG_START   SELECTIVE   5/9     +0.7     9    ▲                         │
│ Gemma      EP             SELECTIVE   3/7     -0.1     7    ▼                          │
│ Vision     (promote)      all         7/9     +1.1     9    ▲                          │
│ [data: agent_verdicts grouped agent×setup_family×regime on outcome_r — BACKEND-GAP-4;  │
│  trend arrow = recent-vs-prior avg R sign]                                             │
├─ LESSONS DIARY (newest first; tagged) ────────────────────────────────────────────────┤
│ 2026-06-28 SYRMA  [right-process-loss] Models 4/5 conviction; clean base; market       │
│                   rolled over day 2. Good read, bad tape. Kept the stop, -1R.          │
│ 2026-06-25 KPIL   [clean-hit] 2-1 split, chair took it; +2.3R by T+10.                 │
│ [data: manas_os/design/agents/lessons/{date}_{SYM}.md — tag + body — BACKEND-GAP-5     │
│  (no endpoint serves lesson md files yet)]                                             │
├─ DIGEST IN FORCE — "what the desk carries forward" (injected into tomorrow's prompts) ─┤
│ • Third-stage bases in SELECTIVE: demand tighter RR (≥2.2).                            │
│ • Delivery-surge + quiet base has been the desk's best STRONG_START tell.              │
│ [data: manas_os/design/agents/lessons/_digest.md, verbatim — BACKEND-GAP-5]            │
├─ TRADE JOURNAL · EQUITY CURVE · EXPECTANCY MATRIX (existing data, placed here) ───────┤
│ [journal table | equity curve line | expectancy grid: lens×regime cells with n]       │
│ [data: journal trades table; equity from closed R; expectancy = setup_expectancy]      │
└───────────────────────────────────────────────────────────────────────────────────┘
EMPTY: "No closed outcomes yet — track records and lessons fill in as trades resolve."
```

## CHART DRAWER — overlay from any symbol click (any tab)
```
┌─ KPIL ─────────────────────────────────────────────────────────────────  [ ✕ ]──────┐
│  ╿ candles, ~120 daily bars, EMA 10/21/50 overlays                                    │
│  ┤▓▒░ ── buy-zone band 888–895 ──   ── stop line 861.5 ──                             │
│  ┤   volume panel below                                                                │
│  │ vision note: "pivot clean, volume dry-up ✓ — promote"                              │
│  [data: candles/EMAs from daily_prices (or reuse rendered agent_charts PNG);           │
│   buy-zone/stop = scan_candidates entry/stop; vision note = agent_verdicts vision row] │
└───────────────────────────────────────────────────────────────────────────────────┘
[B] "The shaded band is the price zone to buy in; the line below is where the plan gives up."
```

## STATES APPENDIX (safety states render IDENTICALLY on every tab)
- EMPTY — each tab has its own line above; always a plain explanation of why it's empty +
  when data arrives, never a blank panel or spinner-forever.
- DEGRADED (models failed) — driven by run_card.debate[].parsed_ok + errors[]. Failed agents
  render as greyed chips with the reason (429 / truncated / struck); the night's outcome
  (thin shortlist, zero-take, struck) is framed as INTENTIONAL, never a red error screen.
- STALE-DATA — global banner (see shell) whenever the scrubbed date's last pipeline stage
  status != ok; the tab still renders the freshest data it has, banner names the cutoff.
- DRY-RUN vs LIVE — single source: config agents.telegram_live. Header badge (⦿DRY-RUN /
  ●LIVE) + every Telegram-mirror row label. DRY-RUN shows the exact message, marked not-sent.
  Exit/urgent coach signals surface in BOTH modes — never suppressed (LOCKED rule).

## BACKEND-GAP items (fields a panel needs that do NOT exist in a payload today)
- **BACKEND-GAP-1** MBI day-color + breadth ratios + XP value: the two explicit KEEPS.
  Not in run_card (regime carries only {mode, age_days}). Needs a feed/endpoint exposing
  MBI breadth (adv/dec, day-color) and the XP score for the scrubbed date.
- **BACKEND-GAP-2** run_card has NO morning_brief narrative string. AGENT_UI specifies one
  cheap LLM call composes and STORES it at end of run. Needs a stored `morning_brief` field
  (on run_card or its own table) — the DESK header block is empty without it.
- **BACKEND-GAP-3** No HTTP route serves the agent chart PNGs (data/agent_charts/... is
  gitignored, filesystem-only). DEBATE vision strip + Chart Drawer need an image endpoint.
- **BACKEND-GAP-4** Per-agent×lens(×regime) track record (hit rate, avg R, n, trend) is
  computable from agent_verdicts.outcome_r but no endpoint aggregates it. DEBATE footer
  chips + LEDGER track-record table both depend on it.
- **BACKEND-GAP-5** Lesson .md files and _digest.md are on disk only; no endpoint serves
  them. LEDGER lessons diary + digest-in-force block need one.
(All other rendered values map to existing tables/endpoints: agent_verdicts, scan_agent_logs,
 agent_signals, scan_candidates, pipeline_runs, setup_expectancy, journal, /api/watchlist,
 /api/desk/feed, /api/desk/run-card.)
```

## ADDENDUM (2026-07-09, user): regime + setups context — the old tool's good parts, desk-native
### DESK tab gains a GOVERNOR LAW row (below the regime metric tiles)
```
┌─ TODAY'S LAW ───────────────────────────────────────────────────────────────────┐
│ [MAX CARDS 4] [RISK/TRADE 0.50-0.75%] [ALLOWED: CATALYST · BASE/PAT] [OPEN-RISK │
│  0.5/2.0%] [PUSHES ON]                                                  [B]     │
└──────────────────────────────────────────────────────────────────────────────────┘
[data: /api/setups governor + /api/portfolio/heat — same metric-tile component]
```
### DEBATE tab gains a REFUSAL FUNNEL header (above the candidate cards — what fed the debate)
```
┌─ THE GATE ──────────────────────────────────────────────────────────────────────┐
│  UNIVERSE 1,029 ─▶ SCREENERS 259 ─▶ GATES 34 ─▶ SHORTLIST 2 ─▶ DEBATED 2        │
│  drops: tradability −770 · regime −744 · trend −219 · particip −29 · risk −33    │
│  [B] "everything the desk refused before the models even argued"                 │
└──────────────────────────────────────────────────────────────────────────────────┘
[data: /api/setups/refusals by_gate + shortlist count from /api/desk/debate]
```
### DEBATE candidate cards gain the six GATE DOTS row (from scan_candidates.gates_json,
hover = evidence) under the header band — the deterministic pedigree of every debated name.
Styling: all three reuse F-UPLIFT components (metric tiles, pills, stat rows). NOT ported:
old posture command bars, poster bands, breadth spark clutter — the desk stays desk-shaped.
