# WIREFRAMES_V3 — Method-first IA rebuild (binding order 2026-07-11, + amendments ~02:40)

Fulfils `CONSTRAINT_METHOD_FIRST_IA.md` incl. its three amendments. The 5-tab
**system-shaped** IA (DESK / DEBATE / MARKET / POSITIONS / LEDGER) is **replaced**
by a **workflow-shaped** IA that walks the TradeTM/Arora method
(SCAN → ENTRY → SIZE & RISK → MANAGE → EXIT), in beginner language.

**This is a frontend rebuild + thin API reshapes only.** No backend engine
change here: pipeline, discovery bucket, four_phase, debate, morning_setups,
signal_guide, sizer, positions-coach, expectancy, and the **living
`agent_watchlist`** all already exist and are REUSED. Each reshape below is
"read a column already written / regroup an existing payload / derive a field
from already-computed values."

**Parallel backend wave assumed (WAVE_M M2/M3, amendment 3 — "the filter is the
defect"):** the discovery bucket (~120 quality names/day: EP / IPO base /
reversal / pullback / flag by ADR+RS) is being wired into the LIVE pool; hard
kills (RS floor, 52wH nearness, regime family-kill) become **scored objections**.
Tradability + risk gates stay hard; NO_TRADE stays hard; LOCKED money-math
unchanged. **These wireframes are drawn to that post-M2/M3 world**: SCAN shows
~100–150 live candidates/day grouped by setup family with objection chips — NOT
"1 survivor + 9 near-misses." If M2/M3 land after the frontend, SCAN degrades
gracefully to whatever the pool currently returns (fewer rows, same layout).

## Reading key
- `[B]` = beginner-default (always visible). `[E]` = expert-only, revealed by the
  header `[beginner|expert]` toggle (density, full tables, raw transcripts,
  activity log). Beginner is DEFAULT.
- Every element annotated `⟨…⟩`: **cite** = corpus nugget id (INDIA_PLAYBOOK keys
  TTM-*/AR-*/SG-*/WK/U*/R*), **quote** = owner's words, **field** = existing
  payload path, **NEW** = a reshape listed in that screen's table.
- Done-test: screenshot each screen, diff element-for-element vs its ASCII here;
  a beginner completes find→plan→size→enter→manage→exit reading ONLY screens.

## How the amendments reconcile with the original rule
The original rule said "LLM debate is EVIDENCE behind verdicts, never the primary
surface." Amendment 1 keeps the **DEBATE screen visible** — the LLM workflow is
SHOWN, made beginner-friendly. Reconciliation, both true at once:
- **SCAN is the primary DECISION surface** — verdict chips + objection chips; a
  trader acts from here. The model reasoning is a one-line "why", not the surface.
- **DEBATE is a visible COMPANION screen** — it SHOWS the seats' bull/bear/chair/
  vision/sizer reasoning in plain language (seat names, plain verdicts, collapsed
  density). Not hidden in an expander; not the place you decide from.

## Tab list (the argument)
Top nav = **6 tabs**; **TRADE PLAN** is a full-screen per-name route opened from
SCAN / WATCHLIST / DEBATE (a detail page, not a nav tab).

| # | Tab | Method stage | Replaces |
|---|-----|--------------|----------|
| 1 | **TONIGHT** | market-reading + verdict + evening routine | DESK (recomposed) |
| 2 | **SCAN** | SCAN — two segments: `POOL` (tonight's ~120 by family) + `WATCHLIST` (living multi-day set) | DEBATE's funnel + `agent_watchlist` (surfaced) |
| 3 | **DEBATE** | the LLM workflow, shown beginner-friendly | DEBATE (relanguaged, KEPT visible per amendment 1) |
| 4 | **POSITIONS** | MANAGE + EXIT | POSITIONS (verdict-first relayout) |
| 5 | **JOURNAL** | review | LEDGER (user-trades-first) |
| 6 | **MARKET** | market-reading detail (feeds TONIGHT + SCAN strips) | MARKET (demoted 6th, reframed) |
| — | **TRADE PLAN** | ENTRY + SIZE & RISK (per selected name) | signal-guide expander → full screen route |

**Why WATCHLIST lives inside SCAN (not a 7th tab):** the amendment names it a
"SCAN/WATCHLIST screen" — one screen, two views. POOL = tonight's regenerated
candidates; WATCHLIST = the persistent object the LLMs curate across days. They
share the same rows/vocabulary, so a segmented control beats a new tab.

**Why MARKET stays a 6th tab (not folded away):** market-reading is a first-class
method stage — four-phase ⟨cite TTM-C1⟩, MBI bands ⟨cite SG-MBI⟩, bottoms-up
rotation needing 5–10 names ⟨cite TTM-G1/G2/G3⟩. Its *conclusion* folds into a
TONIGHT strip + a SCAN ribbon; its *evidence* (treemap/movers/deals/indices) is
too dense to inline and stays behind the demoted tab.

═══════════════════════════════════════════════════════════════════════════════
GLOBAL SHELL
═══════════════════════════════════════════════════════════════════════════════
```
┌────────────────────────────────────────────────────────────────────────────────┐
│ ◤ MANAS  ◀ 2026-07-09 ▶   SELECTIVE·day3 ▮▮▯▯   [beginner|expert]   ⟳ UPDATE   │
├────────────────────────────────────────────────────────────────────────────────┤
│  TONIGHT   SCAN   DEBATE   POSITIONS   JOURNAL   MARKET                         │
├────────────────────────────────────────────────────────────────────────────────┤
│ DATA AS OF 2026-07-09 (today) · next update ~19:25 · build 3f2a1  [amber if <today]│
└────────────────────────────────────────────────────────────────────────────────┘
```
- Brand + date scrubber ⟨field App.jsx date-scrubber; KEEP⟩
- Regime gauge `SELECTIVE·day3` ⟨field card.regime.mode/age_days; KEEP RegimeGauge⟩
- `[beginner|expert]` toggle ⟨quote "beginner friendly"; NEW shell state `mode`, localStorage; drives all `[E]` reveals⟩
- `⟳ UPDATE` ⟨field startUpdate → /api/pipeline/run; KEEP⟩
- Freshness stamp ⟨field computeFreshnessStamp; KEEP — supersedes the old "health pill" placement⟩

═══════════════════════════════════════════════════════════════════════════════
1 · TONIGHT — "what the market is giving, and what to do about it"
   consumes /api/desk/run-card · /api/desk/market(summary) · /api/pipeline/status
═══════════════════════════════════════════════════════════════════════════════
```
┌── THE VERDICT (hero, sentence-first) ─────────────────────────────── [B] ──────┐
│  SIT OUT — 3 clean names ready, take them small.                                │
│  ● SELECTIVE market · Lack-of-Demand phase · MBI white (mixed breadth)          │
│  Tonight: 3 actionable · 20 on watchlist · 118 in tonight's pool  [see → SCAN]  │
└─────────────────────────────────────────────────────────────────────────────────┘
┌── MARKET LAW (one plain paragraph, numbers underneath) ──────────── [B] ───────┐
│  "Selective law: up to 4 cards, EP + pullback lead, risk 0.50–0.75% a trade,    │
│   open-risk 1.2/2.0% used, pushes ON."                                           │
│   MAX 4 │ RISK 0.50–0.75% │ ALLOWED EP·PULLBACK │ OPEN 1.2/2.0% │ PUSHES ON      │
│   Why: breadth cooling · leadership narrowing · Lack-of-Demand → base/break lead │
│   ⚠ Choppy brake OFF  (turns ON at 3–4 stops/week — then no new entries)         │
└─────────────────────────────────────────────────────────────────────────────────┘
┌── IF THE PIPELINE IS RUNNING (live) ─────────────────────────────── [B] ───────┐
│  ⟳ Building tonight's desk … stage 18/26  scan_candidates                        │
│  ▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮░░░░░░░░  ~4 min left · data live ~19:25                       │
└─────────────────────────────────────────────────────────────────────────────────┘
┌── WHAT TO DO NOW (evening routine stepper) ──────────────────────── [B] ───────┐
│  ① Read the law ✓   ② Manage open (1 needs action!) → POSITIONS                 │
│  ③ Review tonight's names (3 actionable) → SCAN   ④ Size & arm → TRADE PLAN      │
│  ⑤ Done — orders placed, stops live                                             │
│  [ current step expanded, ONE primary button; [E] collapses to one-line strip ] │
└─────────────────────────────────────────────────────────────────────────────────┘
┌── MARKET CONTEXT STRIP (folded conclusion of MARKET tab) ────────── [B] ───────┐
│  NIFTY +0.3% · MIDSML +0.8% · VIX 13.4 (calm) · Leading: PHARMA, REALTY          │
│  Rotation: 6 names moving in PHARMA → real theme          [full picture → MARKET]│
└─────────────────────────────────────────────────────────────────────────────────┘
┌── [E] ▸ WHAT THE MODELS SAY  ·  ▸ REGIME NUMBERS  ·  ▸ ACTIVITY LOG ────────────┐
│  ML P(up10d) range · delivery accumulation · HMM · sector-downside · vol forecast│
│  XP/R10/R20/R50/R4.5 tiles + four-phase evidence · full nightly activity stream  │
└─────────────────────────────────────────────────────────────────────────────────┘
```
**Element annotations**
- Verdict stance + headline ⟨field card.tonights_call.stance/headline; KEEP TonightsCall⟩ ⟨quote "the verdict … one plain sentence-first layout"⟩
- Regime/phase/MBI line ⟨field regime.four_phase + governor.market_mode + regime.mbi_day_color⟩ ⟨cite TTM-C1; SG-MBI⟩
- `3 actionable · 20 watchlist · 118 pool` ⟨field NEW debate.pool_summary {actionable, watchlist, pool_total}; replaces old live/paper/near-miss counts under amendment 3⟩ ⟨quote amendment 3 funnel "2370 → bucket 120 → watchlist ~20 → actionable 1-5"⟩
- Market-law paragraph + tiles ⟨field lawRead(governor,heat); KEEP LawRow⟩ ⟨cite R2/R3/R4⟩
- Choppy-brake line ⟨field regime.choppy_brake⟩ ⟨cite AR-Poor-Market-Signal⟩
- Progress bar `stage 18/26 · ETA · data live ~19:25` ⟨field /api/pipeline/status; NEW stage_index,total_stages,eta_seconds,data_live_hint⟩ ⟨quote sub-order "stage x/26, ETA, data live ~19:25"⟩
- Stepper ①–⑤ ⟨field tonights_call.what_to_do + positions urgent count + pool_summary.actionable⟩ ⟨quote "what-to-do-now stepper (their evening routine)"⟩ ⟨precedent WIREFRAMES.md T3.8 stepper⟩
- Market-context strip ⟨field /api/desk/market; NEW market_context summary⟩ ⟨cite TTM-G2⟩
- `[E]` models-say / regime-numbers / activity ⟨field card.models_say, regime.ratios, /api/desk/feed; KEEP, expert-only⟩

**Payload reshapes (TONIGHT)**
| Endpoint | New/changed field | Source (already computed) |
|---|---|---|
| /api/pipeline/status | `stage_index`,`total_stages`,`eta_seconds`,`data_live_hint` | `_load_stages()` length + current_stage index + `started_at`/stages elapsed |
| /api/desk/debate | `pool_summary` `{actionable,watchlist,pool_total}` | count candidates by verdict/objection + join agent_watchlist active count |
| /api/desk/market | `market_context` summary | first N broad-indices + vix + movers rows |

═══════════════════════════════════════════════════════════════════════════════
2 · SCAN — "tonight's found names, the way the method scans" (POOL | WATCHLIST)
   consumes /api/desk/debate (POOL) · /api/desk/watchlist (+history) (WATCHLIST)
═══════════════════════════════════════════════════════════════════════════════
```
┌── segmented control ───────────────────────────────────────────────────────────┐
│  [ TONIGHT'S POOL (118) ]   [ WATCHLIST (20) ]                                   │
└─────────────────────────────────────────────────────────────────────────────────┘
```
────────────────────────────── VIEW A · TONIGHT'S POOL ─────────────────────────
```
┌── THE FILTER (honest, breadth-first) ─────────────────────────────  [B] ───────┐
│  2,370 universe ─▶ quality bucket 118 (EP/IPO/reversal/pullback/flag by ADR+RS) │
│  ─▶ 20 on watchlist ─▶ 3 actionable tonight.                                     │
│  No good pattern is silently dropped — weak names carry an objection chip, not a │
│  refusal.                                                                        │
└─────────────────────────────────────────────────────────────────────────────────┘

▼ EP / EARNINGS POWER (4)    recipe: 30%+ EPS&sales growth, gapped up post-result,
                             neglected before, ₹300cr+ · <45% trigger on gap day
  ┌──────────────────────────────────────────────────────────────────────────────┐
  │ KPIL  ↑42% off 65d-low · ADR 4.1% · ●●●●● 5 dots · pullback 12%          TAKE  │→
  │       entry 924.5 · stop 892 (3.5%) · gap 4.8% held                            │
  ├──────────────────────────────────────────────────────────────────────────────┤
  │ SUNPHARMA  ↑36% · ADR 3.2% · ●●● 3 dots · pullback 9%                  WATCH   │→
  │       ⚑ objection: RS 74 (soft, below 80) · ⚑ off 52wH (soft)                  │
  └──────────────────────────────────────────────────────────────────────────────┘

▼ PULLBACK 10–20 / TO RISING MA (6)   recipe: persistent trend (>10EMA 20d, >20EMA
                             30d, >50EMA 50d), pulling back to rising 10/20 EMA, depth ≤30%
  ┌──────────────────────────────────────────────────────────────────────────────┐
  │ ATUL  ↑31% off 65d-low · ADR 2.8% · ●●● 3 dots · at 20EMA · depth 14%   PAPER │→
  │       entry 6820 · stop 6610 (3.1%)   ⚠ sizer refused → paper only             │
  └──────────────────────────────────────────────────────────────────────────────┘

▶ REVERSAL / BUSTED (3)  ▶ IPO BASE (2)  ▶ D2 / EPISODIC (1)  ▶ STRONG-START-READY (2)
   ▶ FLAG / CONTINUATION (N)   [ collapsed family headers — each shows recipe + count ]

┌── ▶ STRUCTURALLY OUT (hard fails, not objections) ───────────── [B collapsed] ──┐
│  XYZ — tradability: turnover ₹0.8cr < 3cr.  ABC — 5% circuit band.  (kept hard)  │
└─────────────────────────────────────────────────────────────────────────────────┘
```
Row expands (compact; model reasoning is ONE line, full debate is on the DEBATE tab):
```
  │ KPIL … TAKE ▾                                                                  │
  │  ├ gates ●REG ●TRD ●TRND ●LEG ●PART ●RISK   objections: none                   │
  │  ├ why (1 line, plain): "clean EP pullback, breadth ok" — chair                │
  │  └ [ open TRADE PLAN → ]   [ see full debate → DEBATE ]   [ chart ▤ ]           │
```
**Element annotations (POOL)**
- The-filter narrative ⟨field debate.funnel + NEW pool_summary + agent_watchlist active count⟩ ⟨quote amendment 3 "if you're only shortlisting to 1 stock out of 2000 … something inherently wrong with your initial filtering"⟩ ⟨cite Playbook §B P0 recall fix⟩
- Family group headers + counts ⟨field group debate.symbols by `family_label`⟩ ⟨cite Playbook §3 archetypes⟩ ⟨quote "grouped by setup family … each family header showing ITS scan recipe"⟩
- Family recipe line ⟨NEW static `FAMILY_RECIPE[family_label]`, cite per family: EP=TTM-B1/S9; pullback=TTM-H-III1/TTM-C10; strong_start=AR-Strong-Start; d2=TTM-B5b; ipo=SG-VCP; reversal=AR-Undercut⟩
- Row key numbers `↑% off 65d-low · ADR · purple dots · pullback depth` ⟨field NEW debate.symbols[].scan_metrics⟩ ⟨cite Playbook §4 the four P0 velocity/force metrics: pct_up_from_65d_low, adr20, purple_dot_count_60d, correction_depth⟩ ⟨quote "the family's own key numbers"⟩
- Verdict chip TAKE / WATCH / PAPER / SKIP ⟨field chair.verdict + sizer.final_qty (0→PAPER) + objection presence (→WATCH)⟩
- **Objection chips** `⚑ RS 74 (soft) · ⚑ off 52wH (soft) · ⚑ regime-soft` ⟨field NEW debate.symbols[].objections[] {gate,severity:soft,reason,score}⟩ ⟨cite C6 RS→scored objection, C7 52wH→archetype not gate, C8 regime soft; amendment 3 M3⟩ ⟨quote "hard gates … become scored objections"⟩
- **Structurally-out group** (hard fails only) ⟨field gates with severity hard: tradability/risk; NO_TRADE⟩ ⟨cite U4 5%-circuit, U3 turnover — stay hard per amendment 3⟩
- Row `why` (1 line) ⟨field chair.reasoning (stripped via CitedText); ONE line only⟩ ⟨quote amendment 1 reconciliation: SCAN shows verdict, DEBATE shows the reasoning⟩
- `→ TRADE PLAN` / `→ DEBATE` / chart ⟨NEW deep-links⟩
- `[E]` funnel drops by-gate ⟨field funnel.by_gate⟩

────────────────────────── VIEW B · WATCHLIST (living) ─────────────────────────
```
┌── the models curate this list across days — adds, removes, promotes, demotes ──┐
│  PROMOTED ↑                                                                      │
│  ┌────────────────────────────────────────────────────────────────────────────┐ │
│  │ NCC   IPO base · on list 4d · conviction 3→4        chair TAKE   [plan →]    │ │
│  │   07-06 added: "IPO base tightening, RS 84, 3 purple dots"                   │ │
│  │   07-08 held:  "still coiling, inside bar forming"                           │ │
│  │   07-09 PROMOTE: "double inside bar — immediate trade"                       │ │
│  └────────────────────────────────────────────────────────────────────────────┘ │
│  HOLDING —                                                                       │
│  │ ZENTEC  reversal · on list 2d · conviction 2         chair SKIP   [chart ▤]  │ │
│  │   07-08 added: "undercut 10&20MA and reclaimed, watching for follow-through" │ │
│  DEMOTED ↓ / DROPPED ✕                                                           │
│  │ BSOFT  pullback · DROPPED 07-09: "broke 21EMA on volume, thesis void"        │ │
│  │ RVNL   ✕ dropped 07-07 (missing 2 nights running)                            │ │
└─────────────────────────────────────────────────────────────────────────────────┘
```
**Element annotations (WATCHLIST)** — this IS amendment 2 (the living watchlist)
- Grouping PROMOTED / HOLDING / DEMOTED / DROPPED ⟨field agent_watchlist.status ∈ {PROMOTE,HOLD,DEMOTE,DROP}; KEEP endpoint's status ordering⟩ ⟨quote "a LIVING watchlist the LLMs add stocks to and remove stocks from over days"⟩
- Per-symbol tier + on-list duration + conviction trend ⟨field wl.tier, chair conviction; NEW days_on_list⟩
- **Dated add/remove/promote event log** ⟨field NEW watchlist.rows[].events[] {date,status,prev_status,reason} — query agent_watchlist across scan_dates for that symbol⟩ ⟨quote "each add/remove with a visible dated reason ('added 07-10: IPO base tightening, RS 84' / 'removed 07-12: broke 21EMA on volume')"⟩ ⟨cite existing agent_watchlist `reason` is already a plain-English per-status line, per watchlist.py⟩
- 2-night grace before DROP ⟨field wl.miss_streak; reason "missing from debate N nights"⟩ ⟨cite AR-Stopped-Out-Reentry — track dropped names, re-enter if they set up again⟩
- Chair verdict + `[plan →]` / chart ⟨field wl.chair_verdict; deep-links⟩

**Payload reshapes (SCAN)**
| Endpoint | New/changed field | Source (already computed) |
|---|---|---|
| /api/desk/debate | `scan_metrics` per symbol `{pct_up_65d_low,adr20,purple_dots_60d,correction_depth_pct}` | discovery_bucket row (discovery.run writes these) / features_daily fallback; null-honest |
| /api/desk/debate | `objections[]` per symbol `{gate,severity:soft\|hard,reason,score}` | M3 scored objections in run_cascade; pre-M3 fall back to gates.pass=false split by soft/hard gate name |
| /api/desk/debate | (frontend) group by `family_label`; `FAMILY_RECIPE` static cite map | client regroup, no API change |
| /api/desk/watchlist | `events[]` per row + `days_on_list`; `available` for POOL-linked join | query agent_watchlist history across scan_dates for active symbols (table already keyed by scan_date) |

═══════════════════════════════════════════════════════════════════════════════
3 · DEBATE — "the LLM workflow, shown in plain words" (amendment 1: STAYS visible)
   consumes /api/desk/debate  (same payload as SCAN; different, transcript view)
═══════════════════════════════════════════════════════════════════════════════
```
┌── how the desk decided tonight (read top to bottom) ──────────────── [B] ──────┐
│  4 model seats debate each name → the CHAIR rules TAKE/SKIP → the SIZER sets qty.│
│  Seats: Scout · Skeptic · Analyst · Historian (hover = which model).            │
└─────────────────────────────────────────────────────────────────────────────────┘
┌── KPIL · EP ·  CHAIR: TAKE (conviction 4)  ─────────────────────── [B] ────────┐
│  ┌ BULL ─────────────────────────────┐  ┌ BEAR ────────────────────────────┐   │
│  │ Scout ●●●●○ : "EP pullback to 21EMA│  │ Skeptic ●●○○○ : "breadth is thin, │   │
│  │   on held gap, delivery rising"    │  │   a single-name push"             │   │
│  │ Analyst ●●●●○ : "sector leading"   │  │ Historian ●●●○○ : "EP hit-rate    │   │
│  │                                    │  │   62% but n only 47"              │   │
│  └────────────────────────────────────┘  └───────────────────────────────────┘   │
│  CHAIR ruling (plain): "Take it — bull case clears the thin-breadth worry small."│
│  VISION (chart read): daily "clean higher-low above 21EMA" ✓  · weekly base ✓   │
│  SIZER: ×0.9 → final 1,665 (base 1,850) — trimmed for thin breadth               │
│  ▸ [E] full transcripts · lens scores · disagreement spread                      │
└─────────────────────────────────────────────────────────────────────────────────┘
   [ one such card per debated name, ordered by chair rank ]
```
**Element annotations**
- Workflow explainer line ⟨quote amendment 1 "LLM workflow SHOWN … only language + views become beginner friendly"⟩
- Seat names (plain) ⟨field modelSeatLabel(agent); KEEP — raw model id in hover title⟩ ⟨quote "seat names"⟩
- Per-name CHAIR verdict + conviction ⟨field sym.chair.verdict/conviction; KEEP⟩
- BULL / BEAR columns w/ conviction dots ⟨field sym.models[].bull_case/bear_case/conviction via CitedText (cite-stripped); KEEP ModelDebateBlock — now beginner language, not hidden⟩ ⟨quote "debate screen STAYS … do not demote debate to hidden evidence"⟩
- CHAIR ruling plain ⟨field sym.chair.reasoning (stripped)⟩
- VISION strip ⟨field sym.vision.verdict/reasoning + chart thumbs; KEEP⟩ ⟨cite sub-order "LLM inputs must include stage, purple dots, volume markers"⟩
- SIZER line ⟨field sym.sizer.multiplier/final_qty/reasoning; KEEP⟩
- `[E]` full transcripts / lens scores / disagreement spread ⟨field models raw + chair conviction_spread/disagreement; expert-only density collapse⟩ ⟨quote "collapse density"⟩

**Payload reshapes (DEBATE):** none — reuses /api/desk/debate. This is a
relanguaged, plain-verdict view of the SAME payload SCAN uses (seat names, cite-
stripping, and density-collapse are all existing frontend helpers).

═══════════════════════════════════════════════════════════════════════════════
4 · TRADE PLAN — "the pre-trade checklist, made concrete" (per-name route)
   consumes /api/desk/signal-guide (+ debate row for plan/sizer/gates)
═══════════════════════════════════════════════════════════════════════════════
```
┌── KPIL · EP / EARNINGS POWER ─────────────────────────────────────── [B] ──────┐
│  Magnitude trade — hold the big move, sell into weakness not strength.  [chart ▤]│
└─────────────────────────────────────────────────────────────────────────────────┘
┌── A · ENTRY CONDITIONS (step by step) ────────────────────────────── [B] ──────┐
│  ☐ 1  Check the gap first     — if gap%+ORB% > 12% of yest close, SKIP today.   │
│         why: 5% circuit leaves no room to go risk-free.  do: read gap at 9:15.   │
│  ☐ 2  Wait for the 5-min opening range (9:15–9:20 close).                        │
│  ☐ 3  Buy the ORB-high breakout, low holding.  entry ref 924.5.                  │
│  ☐ 4  Day-0 risk-free test — enough room to move stop to breakeven today?        │
│  ☐ 5  Size off the WIDE provisional stop (892) first; resize on the real pullback│
│  ☐ 6  Place the live stop-loss NOW at 892.  final qty 1,665.                     │
│  ☐ 7  Exit line: CLOSE below 21EMA (or 50DMA if tight). Pullbacks = add, not exit│
│         each step: plain sentence · why · exact broker action · source cite      │
└─────────────────────────────────────────────────────────────────────────────────┘
┌── B · POSITION SIZE (the math, on your capital) ─────────────────── [B] ───────┐
│  Your capital ₹[ 12,00,000 ]   Risk this trade 0.50–0.75% = ₹6,000–9,000        │
│  Stop distance 924.5 − 892 = 32.5 (3.5%)  →  qty = ₹risk ÷ 32.5                  │
│  Base qty 1,850   Sizer ×0.9 → FINAL 1,665   ▮▮▮▮▮▮▮▯▯  (0.25–1.25x)             │
│  EP provisional staging: size now at the 4% stop; add the rest once a tighter    │
│  ~2% reversal point prints.                                                      │
└─────────────────────────────────────────────────────────────────────────────────┘
┌── C · RISK CHECKS ─────────────────────────────────────────────────  [B] ──────┐
│  ● Stop 3.5% ≤ cap 6% (SELECTIVE) ✓      ● k×ADR: 3.5% vs 1.7×ADR band ✓        │
│  ● Open risk 1.2% → 1.9% after this (cap 2.0%) ✓   ● Concurrent tight-SL 2/4 ✓  │
│  ● Hard stop must be a LIVE order — no mental stops.                             │
└─────────────────────────────────────────────────────────────────────────────────┘
┌── if sizer refused ──────────────────────────────────────────────── [B] ───────┐
│  ⚠ PAPER ONLY — final qty 0. Paper-trade the steps to build the sample.         │
└─────────────────────────────────────────────────────────────────────────────────┘
   [E] ▸ EXPECTANCY (base-rate) · ▸ full model debate (or → DEBATE tab) · ▸ AI signals
```
**Element annotations**
- Header family + template intent ⟨field guide.family → NEW template_intent⟩ ⟨cite TTM-F13/F16; TTM-H-II1 persistent vs absolute⟩
- A · Entry steps ☐1–7 ⟨field signal-guide.steps[] {n,title,instruction,check,source_cite}; KEEP HowToTradeThis, PROMOTED expander→full screen⟩ ⟨quote "entry condition steps (family-specific: ORB rules, buy-stop level, day-low stop)"⟩ ⟨cite per family EP=TTM-B2/S10; strong_start=AR-Strong-Start; d2=TTM-B5c; ipo=SG-Inside-Bar⟩
- step why/do/source ⟨field step.instruction/check/humanizeSourceCite; KEEP⟩ ⟨quote sub-order "one plain sentence per step + why + exact broker action"⟩
- B · capital input ⟨NEW client setting `capital` (localStorage)⟩ ⟨cite R1 size=risk₹÷(entry−stop)⟩ ⟨quote "their sizing math w/ the user's capital"⟩
- risk₹ band ⟨field governor.risk_band × capital⟩ ⟨cite R2⟩
- base qty / sizer / bar ⟨field plan.suggested_qty, sym.sizer.multiplier/final_qty; KEEP SizerBar⟩
- provisional-risk staging ⟨field EP step 5⟩ ⟨cite R14b/TTM-H-V1; W11⟩ ⟨quote "provisional-risk staging"⟩
- C · stop%≤cap ⟨field plan stop% vs governor cap⟩ ⟨cite R5/C4⟩
- k×ADR context (display-only) ⟨field NEW risk_checks.k_adr from scan_metrics.adr20⟩ ⟨cite C4/TTM-D7 — WAVE-M proposal shown as context, not a gate⟩
- open-risk before→after ⟨field heat.open_risk_pct + this trade's risk₹⟩ ⟨cite R4⟩
- concurrent tight-SL ⟨field open-positions count; cap 4⟩ ⟨cite R3/C3⟩
- no-mental-stops ⟨cite R12/TTM-D11⟩
- paper-only banner ⟨field step-0 refusal / sizer.final_qty==0; KEEP⟩

**Payload reshapes (TRADE PLAN)**
| Endpoint | New/changed field | Source |
|---|---|---|
| /api/desk/signal-guide | `risk_checks` `{stop_pct,regime_stop_cap,k_adr,open_risk_now,open_risk_after,concurrent_tight_sl,concurrent_cap}` | plan + governor cap + scan_metrics.adr20 + /api/portfolio/heat + open-positions count |
| /api/desk/signal-guide | `template_intent` velocity/magnitude/hybrid | static map from family (TTM-F13) |
| (shell) | `capital` user setting | localStorage; client ₹risk math |

═══════════════════════════════════════════════════════════════════════════════
5 · POSITIONS — "manage & exit, one instruction per position"
   consumes /api/desk/positions (verdict-first relayout; ₹ P&L)
═══════════════════════════════════════════════════════════════════════════════
```
┌── JBMA · TREND phase · +2.3R ────────────────────────────── [B] ── !urgent? ──┐
│  ▶ HOLD — trail stop to 214, don't touch it.                                    │
│  entry 198 / SL 214(today) / qty 400 / held 6d   P&L +₹9,200 (+11.6%)           │
│  ┌ R-path sparkline (INITIATION→TREND→EXTENSION bands, trail line) ───────────┐ │
│  └───────────────────────────────────────────────────────────────────────────┘ │
│  why: closed above 21EMA, higher-low intact; day-low 214 is your line.          │
│  [ Edit SL ] [ Edit qty ] [ Close ]   ▸ original thesis · ▸ telegram mirror     │
└─────────────────────────────────────────────────────────────────────────────────┘
┌── RAIN · INITIATION · −0.6R ─────────────────────────── [B] ── ! EXIT NOW ────┐
│  ✖ EXIT NOW — day-low break + two-strike fired.                                 │
│  entry 320 / SL 302 / qty 250 / held 2d   P&L −₹4,500 (−5.6%)                    │
│  why: closed below prior day-low; second strike. Exit at market, no second-guess.│
└─────────────────────────────────────────────────────────────────────────────────┘
```
**Element annotations**
- Verdict-first line ▶HOLD/⤺TRIM/⤢MOVE-STOP/✖EXIT ⟨field coach_verdict + action_line; RELAYOUT to top⟩ ⟨quote "verdict-first layout"⟩ ⟨cite Playbook §6 hold; §7 exits⟩
- Phase + open-R ⟨field position.phase, open_r; KEEP⟩ ⟨cite TTM-F13⟩
- ₹ P&L ⟨field position.pnl_rupees, pnl_pct; ALREADY on backend — surfaced⟩ ⟨quote "₹ P&L"⟩
- entry/SL/qty/held ⟨field entry, todays_stop, qty, days_held⟩
- R-path sparkline ⟨field r_path + trail_stop; KEEP RPathSparkline⟩
- why (layman) ⟨field advisor_note ?? plain_why; KEEP⟩ ⟨quote "layman copy"⟩
- day-low/two-strike in why ⟨field position.fired⟩ ⟨cite TTM-E2 day-low own trigger⟩
- EXIT-NOW banner ⟨field exit_now/urgent/fired; KEEP⟩ ⟨cite R12 exit-at-market⟩
- Edit/Close, thesis, telegram ⟨field update/close, original_thesis, coach; KEEP, collapsed⟩

**Payload reshapes (POSITIONS):** none — pure relayout (verdict to top, ₹P&L
surfaced, thesis/telegram collapsed).

═══════════════════════════════════════════════════════════════════════════════
6 · JOURNAL — "your trades first; system R&D behind Advanced"
   consumes /api/journal · /api/desk/track-record · /api/desk/lessons · /api/expectancy
═══════════════════════════════════════════════════════════════════════════════
```
┌── YOUR TRADES ─────────────────────────────────────────────────── [B] ────────┐
│  date   symbol  setup     entry  exit   R     ₹P&L    reason                     │
│  Jul3   JBMA    EP        198    —      +2.3  open    —                          │
│  Jun28  TATAINV pullback  980    1042   +1.9  +₹5,580 sold into strength         │
└─────────────────────────────────────────────────────────────────────────────────┘
┌── ▶ ADVANCED — SYSTEM R&D ──────────────────────────────────────── [E] ────────┐
│  Track record by family×regime · expectancy cohorts · nightly lessons digest     │
└─────────────────────────────────────────────────────────────────────────────────┘
```
- Your-trades table ⟨field /api/journal; KEEP LedgerTab, user-first⟩ ⟨quote "user's trades first, system R&D behind 'advanced' (already ordered in running UX wave)"⟩
- R + ₹P&L + reason ⟨field outcome_r, realized ₹, reason_tag⟩
- `▶ ADVANCED` R&D ⟨field track-record + lessons + expectancy; KEEP behind `[E]`⟩

**Payload reshapes (JOURNAL):** none new — keeps the running wave's ordering,
gates R&D behind `[E]`.

═══════════════════════════════════════════════════════════════════════════════
7 · MARKET — "why the market gives or denies trades" (demoted; feeds strips)
   consumes /api/desk/market · /api/regime/* (KEEP MarketTab wholesale)
═══════════════════════════════════════════════════════════════════════════════
```
┌ Four-phase + MBI read (plain) ─ [B] ┐  ┌ Broad indices + VIX bands ─ [B] ┐
│ Lack-of-Demand · MBI white · why…   │  │ NIFTY MIDSML SMLCAP · VIX 13.4  │
└─────────────────────────────────────┘  └─────────────────────────────────┘
┌ Sectors & themes — treemap ─ [B] ┐  ┌ Sector/theme movers ─ [B] ┐
│ squarified, click-filters movers  │  │ up / down / themes-up      │
└───────────────────────────────────┘  └────────────────────────────┘
┌ Sectoral │ Thematic │ ChartsMaze sectors │ Bulk deals   [E] dense tables ┐
```
- Four-phase/MBI plain header ⟨field regime.four_phase + mbi_day_color; NEW small plain header⟩ ⟨cite TTM-C1; SG-MBI⟩
- Broad indices + VIX ⟨field BroadIndicesStrip; KEEP⟩
- Treemap (squarify+click-filter) ⟨field SectorTreemap; KEEP⟩ ⟨cite TTM-G2⟩
- Movers ⟨field SectorThemeMoversPanel; KEEP⟩
- Sectoral/thematic/ChartsMaze/bulk-deals ⟨field MarketTab tables; KEEP, `[E]`⟩
- Feeds TONIGHT strip + SCAN ribbon via `market_context` (reshape under TONIGHT).

**Payload reshapes (MARKET):** only `market_context` (listed under TONIGHT).

═══════════════════════════════════════════════════════════════════════════════
CHARTS (ChartDrawer, opened from any screen)
═══════════════════════════════════════════════════════════════════════════════
- Default: candles + volume + **10 EMA + 21 EMA + purple dots** ⟨field overlays ema10/ema21 + markers.purple_dot; KEEP⟩ ⟨cite Playbook §4; sub-order "user kept PD explicitly"⟩
- Behind toggle: ema50/ema200 / persistency / pocket-pivot / stage / shakeout / RMV / HMM ⟨field remaining overlays+markers+panes; CHANGE default-off⟩
- Legend as chips, no inline e10/e50 text ⟨field footer legend; KEEP chips; remove inline labels⟩
- Reshape: ChartDrawer `layers` toggle state (client-only); default {candles,volume,ema10,ema21,purple_dot}. No API change.

═══════════════════════════════════════════════════════════════════════════════
BUILD PLAN — Sonnet-sized tasks, dependency order (frontend + thin API only)
═══════════════════════════════════════════════════════════════════════════════
No backend engine change. "thin API" = read an existing column / regroup an
existing payload / derive from already-computed values.

- **V3-T1 · Shell + IA skeleton.** `App.jsx`, `App.css`. 6 workflow tabs +
  `[beginner|expert]` toggle (localStorage `mode`) via context; keep header/
  gauge/freshness/update. Accept: 6 tabs render; expert flips a global class.
  (dep: none)
- **V3-T2 · /api/pipeline/status progress fields.** `api/app.py`. Add
  stage_index/total_stages/eta_seconds/data_live_hint. Accept: `18/26`+ETA
  during a run; unit-test index/total from `_load_stages()`. (dep: none)
- **V3-T3 · TONIGHT tab.** NEW `TonightTab.jsx`. Verdict hero + market-law +
  live progress bar + 5-step stepper + market-context strip; ModelsSay/Regime/
  Activity behind `[E]`. Accept: screenshot==ASCII §1; bar animates on Update.
  (dep: T1,T2,T9)
- **V3-T4 · /api/desk/debate scan_metrics + objections + morning_setups join.**
  `api/app.py`. Add scan_metrics (discovery_bucket/features_daily); add
  objections[] (M3 scored objections, or pre-M3 soft/hard gate split); surface
  morning_setups families; add pool_summary. Accept: each symbol has 4 metrics
  or honest null; soft objections carry {reason,score}; hard fails flagged
  separately. (dep: none; graceful pre-M2/M3)
- **V3-T5 · /api/desk/watchlist event history.** `api/app.py`. Add events[]
  {date,status,prev_status,reason} across scan_dates per active symbol +
  days_on_list. Accept: a symbol shows its dated add/promote/drop log. (dep: none)
- **V3-T6 · SCAN tab (POOL + WATCHLIST segments).** NEW `ScanTab.jsx`. POOL:
  group by family_label, `FAMILY_RECIPE` map, scan_metrics rows, objection
  chips, structurally-out group, 1-line why, deep-links. WATCHLIST: PROMOTE/
  HOLD/DEMOTE/DROP groups + per-symbol dated event log. Accept: screenshot==
  ASCII §2 both views; no bull/bear on the row surface; watchlist shows events.
  (dep: T1,T4,T5)
- **V3-T7 · DEBATE tab (relanguaged, KEPT visible).** `DebateTab.jsx`. Workflow
  explainer + per-name bull/bear (seat names, cite-stripped) + chair ruling +
  vision + sizer; raw transcripts/lens/spread behind `[E]`. Accept: screenshot
  ==ASCII §3; debate visible, plain language, not an expander. (dep: T1)
- **V3-T8 · /api/desk/signal-guide risk_checks + template_intent.** `api/app.py`.
  Assemble risk_checks + template_intent. Accept: block present for a sized
  name; k×ADR is display-context only. (dep: T4 for adr20)
- **V3-T9 · /api/desk/market market_context.** `api/app.py`. Add summary block.
  Accept: strips render from it. (dep: none)
- **V3-T10 · TRADE PLAN route.** NEW `TradePlanTab.jsx` (promote HowToTradeThis).
  Full-screen entry steps + sizing-math (capital input) + risk-checks +
  paper-only; expert expectancy/AI; link to DEBATE. Accept: screenshot==ASCII
  §4; a beginner sizes off capital with every step+why+broker action+cite.
  (dep: T1,T6,T8)
- **V3-T11 · POSITIONS relayout.** `PositionsTab.jsx`. Verdict-first, ₹P&L,
  collapse thesis/telegram, layman why. Accept: screenshot==ASCII §5. (dep: T1)
- **V3-T12 · MARKET demote + plain header + SCAN ribbon.** `MarketTab.jsx`,
  `ScanTab.jsx`. Four-phase/MBI header; dense tables behind `[E]`; SCAN ribbon
  from market_context. Accept: MarketTab intact but demoted; strips populated.
  (dep: T6,T9)
- **V3-T13 · Chart layer defaults.** `ChartDrawer.jsx`. Default layers set;
  toggle reveals the rest; chip legend; remove inline EMA text. Accept: first
  paint shows only the default set. (dep: T1)
- **V3-T14 · JOURNAL user-first + advanced.** `LedgerTab.jsx`→`JournalTab.jsx`.
  User trades first, R&D behind `[E]`. Accept: screenshot==ASCII §6. (dep: T1)
- **V3-T15 · Glossary/Term sweep + done-test.** All tabs. Every jargon term has
  an inline explanation; screenshot each screen on real data, diff vs ASCII;
  walk find→plan→size→enter→manage→exit reading only screens. Accept: fidelity
  pass green. (dep: all)

═══════════════════════════════════════════════════════════════════════════════
MIGRATION NOTE — the running UX-polish wave (OLD IA) vs V3
═══════════════════════════════════════════════════════════════════════════════
The running UX wave's **backend/correctness fixes SURVIVE and are consumed by
V3**; several **cosmetic OLD-IA outputs are SUPERSEDED** (their data still feeds
V3).

| Running-wave item | Nature | V3 disposition |
|---|---|---|
| Health pill | cosmetic header chip | SUPERSEDED — folds into freshness stamp + TONIGHT verdict line |
| Stop-breach fix (coach todays_stop / two-strike) | backend correctness | SURVIVES — POSITIONS verdict + EXIT-NOW read from it |
| Verdict banner (debate lead-line) | cosmetic placement | SUPERSEDED — becomes TONIGHT counts + SCAN "the filter" line (same verdict_summary/pool_summary fields) |
| Seat names (modelSeatLabel) | cosmetic, reusable | SURVIVES — used on the DEBATE tab (now first-class per amendment 1) |
| Layman cite-stripping (stripCitationCodes/CitedText/humanizeSourceCite) | cosmetic, reusable | SURVIVES — reused across TONIGHT/SCAN/DEBATE/TRADE PLAN |
| pnl_rupees/pnl_pct on positions | backend correctness | SURVIVES — surfaced as ₹P&L in POSITIONS |
| agent_watchlist writer (watchlist.py) + /api/desk/watchlist | backend, underused | SURVIVES + PROMOTED — becomes the SCAN·WATCHLIST view (amendment 2); only additive `events[]` reshape |

**Rule:** don't re-solve a running-wave *correctness* fix in V3; do rebuild the
*surface* it lives on. When both waves touch one file (App.jsx, DebateTab.jsx,
PositionsTab.jsx, MarketTab.jsx), V3's IA rebuild lands on top of the merged fix
— data contract preserved, layout changed.

*End WIREFRAMES_V3.md — every element carries a cite/quote/field; screenshot-vs-
ASCII is the done-test per the owner's standing wireframe-fidelity rule.*
