# WIREFRAMES_V4 — Method-first IA on the locked SPINE (owner-approved 2026-07-11 ~09:00)

**Supersedes `WIREFRAMES_V3.md` in full.** V3's 6-tab spine
(TONIGHT/SCAN/DEBATE/POSITIONS/JOURNAL/MARKET) is replaced by the spine the owner
locked after V3: **MARKET · SCANNERS · SHORTLIST · DEBATE · POSITIONS · JOURNAL**,
plus a per-stock **TRADE PLAN** route and a first-class **CHART** (split-panel on
SCANNERS/SHORTLIST/POSITIONS + full-screen route). Every reusable V3 piece is
carried forward and re-homed (mapping in the Supersession table at the end); no
V3 payload reshape is thrown away, several are re-pointed.

Fulfils `CONSTRAINT_METHOD_FIRST_IA.md` including ALL amendments — the trader-flow
verbatim (owner ~09:00): *"traders have scanners, from which they shortlist few
stocks after observing their long term price behaviour, then move them to a
shortlist… based on market conditions, regime trends, and again observing price
and volume on charts, they take a call to enter, having their own position sizing
rules… again based on the stock's movement and market conditions, they adjust
their stops, and try to sell while still on strength."* The spine IS that
sentence: MARKET (conditions) → SCANNERS (scan) → SHORTLIST (observe long-term,
curate) → DEBATE (take a call) → TRADE PLAN (enter + size) → POSITIONS (adjust
stops, sell into strength) → JOURNAL (review).

## Why this spine (owner order, over V3)
The owner asked, verbatim: *"where is the page to run different scans as per the
traders? … shortlist screen … charts view?"* V3 buried scanning inside a "SCAN
POOL" segment and had no named-trader scanner page and no persistent shortlist
distinct from the nightly pool. V4 splits them:
- **SCANNERS** = the *act of scanning* — named practitioner scanners as preset
  cards + a Chartink-style custom builder. This is the missing "page to run
  different scans as per the traders."
- **SHORTLIST** = the *persistent curated set* the LLMs (Curator role) maintain
  across days — this is amendment 2's living watchlist, promoted to its own tab.
- **MARKET** = home, because the method reads conditions FIRST (four-phase / MBI /
  breadth) before it scans. V3's TONIGHT verdict-hero moves here.

## Staged LLM roles (owner-locked; one role per method stage)
| Role | Stage / Tab | What it does | Backs onto |
|---|---|---|---|
| **Scout** | SCANNERS | one-line annotation per scanner hit ("why this row is interesting") | `agent_verdicts` model rows / scan_metrics |
| **Curator** | SHORTLIST | adds / drops / promotes names with a dated reason each | `agent_watchlist` (status + reason) |
| **Council** | DEBATE | the multi-seat bull/bear/chair debate (KEPT visible, amendment 1) | `agent_verdicts` (chair/models/vision) |
| **Sizer** | TRADE PLAN | final size authority — multiplier, final qty, paper-only refusal | `agent_verdicts` agent=sizer |
| **Coach** | POSITIONS | per-position manage/exit verdict + layman why | `/api/positions/{id}/coach` |

## Reading key (unchanged from V3)
- `[B]` = beginner-default (always visible). `[E]` = expert-only, revealed by the
  header `[beginner|expert]` toggle. Beginner is DEFAULT.
- **Beginner vs expert is specified per screen** (owner: *"beginner/expert must
  differ visibly on EVERY screen"*). Global rule: **beginner** = verdict sentence,
  ≤5 columns, plain checklists, 1-line LLM summaries; **expert** = full columns,
  transcripts, objection weights/scores, activity log.
- Every element annotated `⟨…⟩`: **cite** = corpus nugget / screener-registry row
  / archetype; **quote** = owner's words; **field** = existing payload path; **NEW**
  = a reshape listed in that screen's table.
- Done-test: screenshot each screen, diff element-for-element vs its ASCII here; a
  beginner completes scan→shortlist→decide→plan→size→enter→manage→exit reading
  ONLY the screens.

## STATUS vocabulary for SCANNERS presets (no dormant fake UI — owner standing rule)
Each preset card carries a status chip driven by whether its data reaches a
surface today:
- **LIVE** — feeds the nightly pool / a surfaced payload right now (discovery
  archetype in `candidates.py`, or a screener already read into a shown field).
- **DATA-READY** — rows are ingested into `screener_hits`/`symbol_quality`
  (`chartsmaze_scanners.py` SCREENER_REGISTRY) but never surfaced; card renders
  hits from a thin read, **no new detector needed**.
- **BUILD** — no data flow yet; card renders **greyed "coming"**, non-interactive,
  with the one-line recipe visible so the owner sees the intent.

═══════════════════════════════════════════════════════════════════════════════
GLOBAL SHELL
═══════════════════════════════════════════════════════════════════════════════
```
┌────────────────────────────────────────────────────────────────────────────────┐
│ ◤ MANAS  ◀ 2026-07-09 ▶   SELECTIVE·day3 ▮▮▯▯   🔍[ symbol search ]  [beg|exp] ⟳ │
├────────────────────────────────────────────────────────────────────────────────┤
│  MARKET   SCANNERS   SHORTLIST   DEBATE   POSITIONS   JOURNAL                    │
├────────────────────────────────────────────────────────────────────────────────┤
│ DATA AS OF 2026-07-09 (today) · next update ~19:25 · build 3f2a1  [amber if <today]│
└────────────────────────────────────────────────────────────────────────────────┘
```
- Brand + date scrubber ⟨field App.jsx date-scrubber; KEEP⟩
- Regime gauge `SELECTIVE·day3` ⟨field card.regime.mode/age_days; KEEP RegimeGauge⟩
- **Universal symbol search** 🔍 ⟨quote amendment ~09:30 "universal symbol search:
  on-demand LLM debate of any symbol"⟩ ⟨NEW shell control; enter symbol → POST
  /api/desk/debate/push → lands a card on DEBATE marked "user-pushed"; see DEBATE⟩
- `[beginner|expert]` toggle ⟨quote "beginner friendly"; NEW shell state `mode`,
  localStorage; drives every `[E]` reveal⟩ — carried from V3-T1
- `⟳ UPDATE` ⟨field startUpdate → /api/pipeline/run; KEEP⟩
- Freshness stamp ⟨field computeFreshnessStamp; KEEP⟩

═══════════════════════════════════════════════════════════════════════════════
1 · MARKET — HOME: "what the market is giving, and what to do about it"
   consumes /api/desk/run-card · /api/desk/market · /api/pipeline/status · /api/regime/*
═══════════════════════════════════════════════════════════════════════════════
This is V3's TONIGHT tab re-homed as the landing screen (method reads conditions
first), with V3's MARKET *evidence* (treemap/movers/indices) folded in below the
fold instead of on a separate 6th tab.
```
┌── THE VERDICT (hero, sentence-first) ─────────────────────────────── [B] ──────┐
│  SIT OUT — 3 clean names ready, take them small.                                │
│  ● SELECTIVE market · Lack-of-Demand phase · MBI white (mixed breadth)          │
│  Tonight: 3 actionable · 20 shortlisted · 118 scanned  [→ SCANNERS] [→ SHORTLIST]│
└─────────────────────────────────────────────────────────────────────────────────┘
┌── MARKET LAW (one plain paragraph, numbers underneath) ──────────── [B] ───────┐
│  "Selective law: up to 4 cards, EP + pullback lead, risk 0.50–0.75% a trade,    │
│   open-risk 1.2/2.0% used, pushes ON."                                           │
│   MAX 4 │ RISK 0.50–0.75% │ ALLOWED EP·PULLBACK │ OPEN 1.2/2.0% │ PUSHES ON      │
│   Why: breadth cooling · leadership narrowing · Lack-of-Demand → base/break lead │
│   ⚠ Choppy brake OFF  (turns ON at 3–4 stops/week — then no new entries)         │
└─────────────────────────────────────────────────────────────────────────────────┘
┌── LIVE PIPELINE (only while a run is in flight) ─────────────────── [B] ───────┐
│  ⟳ Building tonight's desk … stage 18/26  scan_candidates                        │
│  ▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮░░░░░░░░  ~4 min left · data live ~19:25                       │
└─────────────────────────────────────────────────────────────────────────────────┘
┌── WHAT TO DO NOW (evening routine stepper) ──────────────────────── [B] ───────┐
│  ① Read the law ✓   ② Manage open (1 needs action!) → POSITIONS                 │
│  ③ Run tonight's scanners (118 hits) → SCANNERS   ④ Review shortlist → SHORTLIST │
│  ⑤ Size & arm the takes → TRADE PLAN   ⑥ Done — orders placed, stops live        │
│  [ current step expanded, ONE primary button; [E] collapses to one-line strip ] │
└─────────────────────────────────────────────────────────────────────────────────┘
┌── MARKET EVIDENCE (folded from old MARKET tab) ─────────── [B] summary / [E] full┐
│  NIFTY +0.3% · MIDSML +0.8% · VIX 13.4 (calm) · Leading: PHARMA, REALTY          │
│  Rotation: 6 names moving in PHARMA → real theme                                 │
│  [E] ▸ four-phase evidence · MBI bands · sector treemap (click-filters movers) · │
│      sector/theme movers · sectoral/thematic/ChartsMaze/bulk-deals dense tables  │
└─────────────────────────────────────────────────────────────────────────────────┘
┌── [E] ▸ WHAT THE MODELS SAY  ·  ▸ REGIME NUMBERS  ·  ▸ ACTIVITY LOG ────────────┐
│  ML P(up10d) · delivery accumulation · HMM · sector-downside · vol forecast      │
│  XP/R10/R20/R50/R4.5 tiles + four-phase evidence · full nightly activity stream  │
└─────────────────────────────────────────────────────────────────────────────────┘
```
**Element annotations**
- Verdict stance + headline ⟨field card.tonights_call.stance/headline; KEEP TonightsCall⟩ ⟨quote "the verdict … one plain sentence-first"⟩
- Regime/phase/MBI line ⟨field regime.four_phase + governor.market_mode + regime.mbi_day_color⟩ ⟨cite TTM-C1; SG-MBI⟩
- `3 actionable · 20 shortlisted · 118 scanned` ⟨field NEW debate.pool_summary {actionable, shortlisted, scanned_total}; shortlisted = agent_watchlist active count⟩ ⟨quote amendment 3 funnel⟩
- Market-law paragraph + tiles ⟨field lawRead(governor,heat); KEEP LawRow⟩ ⟨cite R2/R3/R4⟩
- Choppy-brake line ⟨field regime.choppy_brake⟩ ⟨cite AR-Poor-Market-Signal⟩
- Progress bar `stage 18/26 · ETA · data live ~19:25` ⟨field /api/pipeline/status NEW stage_index,total_stages,eta_seconds,data_live_hint⟩ ⟨quote sub-order "stage x/26, ETA, data live ~19:25"⟩
- Stepper ①–⑥ ⟨field tonights_call.what_to_do + positions urgent count + pool_summary.actionable⟩ ⟨quote "step by step instructions … scanning, entry conditions, position sizing, risk, exit"⟩
- Market-evidence summary + `[E]` full ⟨field /api/desk/market NEW market_context (summary) + KEEP MarketTab components (BroadIndicesStrip/SectorTreemap/SectorThemeMoversPanel/dense tables) rendered under `[E]`⟩ ⟨cite TTM-G2⟩
- `[E]` models-say / regime-numbers / activity ⟨field card.models_say, regime.ratios, /api/desk/feed; KEEP⟩

**Beginner vs expert (MARKET):** beginner sees the verdict sentence, the law
paragraph + 5 tiles, the stepper, and a one-line market-evidence summary. Expert
adds the four-phase/MBI/treemap/movers/dense-table evidence, models-say, regime
ratios, and the activity log.

**Payload reshapes (MARKET)**
| Endpoint | New/changed field | Source (already computed) |
|---|---|---|
| /api/pipeline/status | `stage_index`,`total_stages`,`eta_seconds`,`data_live_hint` | `_load_stages()` length + current index + `started_at`/elapsed |
| /api/desk/debate | `pool_summary` `{actionable,shortlisted,scanned_total}` | count candidates by verdict + join agent_watchlist active count |
| /api/desk/market | `market_context` summary | first N broad-indices + vix + movers rows |

═══════════════════════════════════════════════════════════════════════════════
2 · SCANNERS — "run the scans, the way each trader runs them" (THE new page)
   consumes NEW /api/scanners/presets · NEW /api/scanners/run · /api/desk/debate
═══════════════════════════════════════════════════════════════════════════════
Two stacked sections: **A · Named practitioner scanner presets** (cards), then
**B · Custom screener builder** (Chartink-style). Both list result rows with the
same row grammar. Every result row: `[★ shortlist] [→ debate] [chart]`.
```
┌── segmented control ───────────────────────────────────────────────────────────┐
│  [ PRACTITIONER SCANNERS ]   [ CUSTOM BUILDER ]                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```
─────────────────────────── SECTION A · PRACTITIONER SCANNERS ───────────────────
Preset cards, each: **name · owner · one-line recipe · hits count · STATUS chip**.
Click a card → its result rows expand below (or fill the right split-panel).
```
┌─ ARORA BASELINE ────────── LIVE ─┐  ┌─ PERSISTENT MOMENTUM ───── LIVE ─┐
│ owner: Manas Arora (screener.in) │  │ owner: TradeTM / Arora           │
│ recipe: liquid + >200DMA uptrend │  │ recipe: >10EMA 20d, >20EMA 30d,  │
│   + RS-led, near 52w-high        │  │   >50EMA 50d — trend never broke │
│ hits: 46            [open ▾]      │  │ hits: 31            [open ▾]      │
└──────────────────────────────────┘  └──────────────────────────────────┘
┌─ EARNINGS POWER (EP) ───── LIVE ─┐  ┌─ D2 / EPISODIC ─────────── LIVE ─┐
│ owner: TradeTM                   │  │ owner: TradeTM                   │
│ recipe: 30%+ EPS&sales, gapped   │  │ recipe: day-1 burst → day-2      │
│   post-result, neglected before  │  │   inside/tight follow-through    │
│ hits: 4             [open ▾]      │  │ hits: 3             [open ▾]     │
└──────────────────────────────────┘  └──────────────────────────────────┘
┌─ IPO INSIDE-BAR ────────── LIVE ─┐  ┌─ UNDERCUT & RECOVER ────── LIVE ─┐
│ owner: Umang / IPO playbook      │  │ owner: Manas Arora               │
│ recipe: recent listing + base +  │  │ recipe: undercut 10&20MA then    │
│   inside/NR7 bar coil            │  │   reclaim — reversal/busted      │
│ hits: 2             [open ▾]      │  │ hits: 5             [open ▾]     │
└──────────────────────────────────┘  └──────────────────────────────────┘
┌─ VCP / TIGHTNESS ───────── LIVE ─┐  ┌─ TODAY'S MOVERS ──────── DATA-RDY┐
│ owner: Minervini / Arora         │  │ owner: builder preset            │
│ recipe: volatility contraction,  │  │ recipe: top %chg + volume + ADR  │
│   strong-start bottom-pctile     │  │   — day-1 bursts feed D2 watch   │
│ hits: 7             [open ▾]      │  │ hits: 22            [open ▾]     │
└──────────────────────────────────┘  └──────────────────────────────────┘
┌─ MBI-GATED ENGAGEMENT ──── BUILD ┐  ← greyed, non-interactive, recipe shown
│ owner: Umang (Stocksgeeks)       │
│ recipe: only engage when MBI     │
│   green-band regime confirms     │
│ hits: —          (coming)        │
└──────────────────────────────────┘
── ChartsMaze trader templates (ingested nightly) ──────────────────────────────
┌─ CHHIRAG ──────────── DATA-RDY ─┐  ┌─ HIMANSHU ─────────── DATA-RDY ─┐
│ recipe: mcap 1000–2L cr, ₹turn  │  │ recipe: RS 70–100, vol gainers,│
│   >5cr/50d, ex-5%-circuit       │  │   gap-up, listed >2024-01      │
│ hits: 88            [open ▾]     │  │ hits: 40            [open ▾]    │
└─────────────────────────────────┘  └────────────────────────────────┘
┌─ HIREN ────────────── DATA-RDY ─┐  ┌─ NITIN ────────────── DATA-RDY ─┐
│ recipe: ₹turn >3cr/20d + 1M ret │  │ recipe: inside-bar/NR7 within   │
│   20–100% OR 3M 30–300%         │  │   10/21/50/200 EMA bands        │
│ hits: 61            [open ▾]     │  │ hits: 54            [open ▾]    │
└─────────────────────────────────┘  └────────────────────────────────┘
┌─ SHASHANK ─────────── DATA-RDY ─┐
│ recipe: EPS/sales/NP YoY >10%,  │
│   ROE/ROCE>15, D/E<1, >200DMA   │
│ hits: 29            [open ▾]     │
└─────────────────────────────────┘

── result rows (shared grammar; shown when a card is opened) ───────────────────
  ┌────────────────────────────────────────────────────────────────────────────┐
  │ KPIL  ↑42% off 65d-low · ADR 4.1% · ●●●●● 5 dots · RS 86 · pullback 12%      │
  │   Scout: "clean EP pullback to 21EMA, delivery rising"      [★] [→ debate] ▤ │
  ├────────────────────────────────────────────────────────────────────────────┤
  │ SUNPHARMA  ↑36% · ADR 3.2% · ●●● 3 dots · RS 74 · pullback 9%                │
  │   Scout: "sector leading but RS soft"                       [★] [→ debate] ▤ │
  └────────────────────────────────────────────────────────────────────────────┘
```
**Element annotations (Section A)**
- Preset card set ⟨quote "named trader scanners (incl ChartsMaze trader templates)
  must be a real page"⟩ ⟨cite discovery archetypes in scanner/discovery.py:
  Arora-baseline=candidates.py pool; persistent_momentum; ep_ipo; d2_episodic;
  recent_listing+inside-bar; reversal+busted_reversal; vcp_coil+strong_start_ready⟩
  ⟨cite ChartsMaze templates = chartsmaze_scanners.py SCREENER_REGISTRY
  chhirag/himanshu/hiren/nitin/shashank⟩
- Per-card **owner + one-line recipe** ⟨NEW static PRESET_REGISTRY map: {key,
  name, owner, recipe, cite, status}; recipes cite CHARTSMAZE_TEMPLATE_CRITERIA.md
  (chhirag/himanshu/hiren/nitin/shashank exact values) + archetype detectors⟩
- **hits count** ⟨field NEW /api/scanners/presets returns per-preset today's hit
  count: LIVE from discovery_bucket archetype membership / candidates pool;
  DATA-READY from screener_hits COUNT(trade_date,screener); BUILD → null⟩
- **STATUS chip** ⟨NEW per STATUS vocabulary above; drives greying⟩ ⟨quote owner
  standing rule "unimplemented presets appear greyed 'coming' — no dormant fake UI"⟩
- Result-row key numbers `↑% off 65d-low · ADR · purple dots · RS · pullback` ⟨field
  scan_metrics {pct_up_65d_low,adr20,purple_dots_60d,correction_depth_pct} +
  rs_rating⟩ ⟨cite Playbook §4 four P0 velocity/force metrics⟩
- **Scout annotation** (one line) ⟨field NEW row.scout_note = chair/model reasoning
  first sentence via CitedText⟩ ⟨cite staged-role table: Scout⟩
- Row actions `[★ shortlist] [→ debate] [chart]` ⟨quote "every row: shortlist /
  debate / chart"⟩ ⟨field ★ → POST /api/watchlist/candidates (Curator add);
  → debate → POST /api/desk/debate/push; chart → ChartDrawer⟩

─────────────────────────── SECTION B · CUSTOM BUILDER (Chartink-style) ──────────
```
┌── BUILD A SCREEN (stack conditions, all must pass) ──────────────── [B] ───────┐
│  WHEN a stock has…                                                              │
│   [ %change    ] [ ≥ ] [ 5    ] %            (✕)                                │
│   [ volume      ] [ ≥ ] [ 2x 20d-avg ]       (✕)                                │
│   [ ADR         ] [ ≥ ] [ 3.5  ] %           (✕)                                │
│   [ RS rating   ] [ ≥ ] [ 80   ]             (✕)                                │
│   [ + add condition ▾ ]                                                         │
│      metrics: close · %change · volume · ADR · RS · %off 52w-high · %off low ·  │
│               EMA position (>10/21/50/200) · purple dots · delivery %           │
│   [ Run screen ]   [ 💾 Save as… "my movers" ]      matches: 17                 │
└─────────────────────────────────────────────────────────────────────────────────┘
┌── SAVED SCREENS ──────────────────────────────────────────────── [B] ─────────┐
│  ▸ my movers (17)   ▸ tight+RS (9)   ▸ delivery accumulation (12)   [ + preset ]│
└─────────────────────────────────────────────────────────────────────────────────┘
   [ result rows — same grammar as Section A; each: [★ shortlist] [→ debate] [chart] ]
```
**Element annotations (Section B)**
- Stackable-conditions builder ⟨quote amendment ~09:30 "Chartink-style SCREENER
  BUILDER … stackable conditions over existing per-stock metrics (close, %change,
  volume, ADR, RS, %off low/high, EMA position, purple dots, delivery)"⟩
- Metric vocabulary ⟨field features_daily / discovery_bucket metrics + scan_metrics
  + rs_rating + delivery; each condition = {metric, op, value}⟩
- Run + matches ⟨NEW POST /api/scanners/run {conditions[]} → symbols[] with same
  scan_metrics row shape⟩
- **Save-as-named-screen** ⟨quote "save-as-named-screen"⟩ ⟨NEW /api/scanners/saved
  CRUD; localStorage mirror for offline⟩
- TODAY'S MOVERS as a saved preset ⟨quote "Preset: TODAY'S MOVERS (top %change +
  volume + ADR) — day-1 bursts feed D2 watch per doctrine"⟩ ⟨cite TTM-B5b D2⟩
- Push-to-debate from any builder row ⟨quote "push the stock to the debate panel
  to the llms … on top of whatever it itself screens"⟩

**Beginner vs expert (SCANNERS):** beginner sees preset cards with recipe + hits
+ ≤5 row columns (symbol, move%, ADR, dots, Scout one-liner) and a simple 4-row
builder. Expert adds: per-preset full column set (RS, delivery, mcap, turnover,
sector), the full metric dropdown incl EMA-relations and %off-high, condition
weights, and a raw hit table with sortable headers.

**Payload reshapes (SCANNERS)**
| Endpoint | New/changed field | Source (already computed) |
|---|---|---|
| NEW /api/scanners/presets | `[{key,name,owner,recipe,cite,status,hits,rows[]}]` | LIVE: discovery_bucket_map archetype membership + candidates pool; DATA-READY: screener_hits/symbol_quality by screener; BUILD: status only |
| NEW /api/scanners/run | `{symbols:[{symbol,scan_metrics,rs,scout_note}]}` from `{conditions:[{metric,op,value}]}` | features_daily + discovery_bucket metrics filter; pure query |
| NEW /api/scanners/saved | GET/POST/DELETE named condition-sets | new tiny table `saved_screens(name,conditions_json)` |
| /api/desk/debate | `scout_note` per row (first sentence of chair/model reasoning) | existing agent_verdicts reasoning via CitedText |
| NEW POST /api/desk/debate/push | on-demand debate of `{symbol}`; card marked `user_pushed` | reuse run_cascade single-symbol path + context pack |

═══════════════════════════════════════════════════════════════════════════════
3 · SHORTLIST — "the names you're watching, curated by the desk across days"
   consumes /api/desk/watchlist (+event history) · /api/desk/debate (chair verdict)
═══════════════════════════════════════════════════════════════════════════════
This IS amendment 2 (the living LLM watchlist), promoted from a V3 segment to its
own tab. The **Curator** role owns adds/drops with dated reasons. Owner flow:
*"they shortlist few stocks after observing their long term price behaviour."* So
each row leads with a **weekly-first chart thumb** and its multi-day event log.
```
┌── the desk curates this list across days — adds, drops, promotes, demotes ─────┐
│  Curator added 2 · dropped 1 · promoted 1 since last night.        [chart split▤]│
└─────────────────────────────────────────────────────────────────────────────────┘
┌ PROMOTED ↑ ───────────────────────────────────────────────────────── [B] ─────┐
│ ┌───────────────────────────────────────────────────────────────────────────┐ │
│ │ [wk▤] NCC   IPO base · on list 4d · conviction 3→4      Council: TAKE [plan→]│ │
│ │   07-06 added:  "IPO base tightening, RS 84, 3 purple dots"   — Curator      │ │
│ │   07-08 held:   "still coiling, inside bar forming"          — Curator      │ │
│ │   07-09 PROMOTE:"double inside bar — immediate trade"        — Curator      │ │
│ └───────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────────┘
┌ HOLDING — ─────────────────────────────────────────────────────────── [B] ─────┐
│ │ [wk▤] ZENTEC  reversal · on list 2d · conviction 2      Council: SKIP  [chart▤]│ │
│ │   07-08 added: "undercut 10&20MA and reclaimed, watching follow-through" — Cur│ │
└─────────────────────────────────────────────────────────────────────────────────┘
┌ DEMOTED ↓ / DROPPED ✕ ─────────────────────────────────────────────── [B] ─────┐
│ │ BSOFT  pullback · DROPPED 07-09: "broke 21EMA on volume, thesis void" — Curator│ │
│ │ RVNL   ✕ dropped 07-07 (missing 2 nights running)                             │ │
└─────────────────────────────────────────────────────────────────────────────────┘
```
**Element annotations**
- Curator summary line ⟨field NEW watchlist.curator_delta {added,dropped,promoted}⟩ ⟨cite staged-role: Curator⟩
- Grouping PROMOTED/HOLDING/DEMOTED/DROPPED ⟨field agent_watchlist.status ∈ {PROMOTE,HOLD,DEMOTE,DROP}; KEEP status ordering⟩ ⟨quote "a LIVING watchlist the LLMs add / remove over days"⟩
- **Weekly-first chart thumb** `[wk▤]` ⟨quote spine "observing their long term price behaviour" + "weekly-first on scanner hits"⟩ ⟨field ChartDrawer default timeframe=weekly when opened from SHORTLIST/scanner⟩
- Per-symbol tier + on-list duration + conviction trend ⟨field wl.tier, chair conviction; NEW days_on_list⟩
- **Dated event log** ⟨field NEW watchlist.rows[].events[] {date,status,prev_status,reason} — query agent_watchlist across scan_dates⟩ ⟨quote "each add/remove with a visible dated reason ('added 07-10: IPO base tightening'…)"⟩ ⟨cite agent_watchlist.reason already plain-English per status⟩
- 2-night grace before DROP ⟨field wl.miss_streak⟩ ⟨cite AR-Stopped-Out-Reentry⟩
- Council verdict + `[plan →]` / chart ⟨field wl.chair_verdict; deep-links⟩

**Beginner vs expert (SHORTLIST):** beginner sees group + symbol + one-line
latest Curator reason + Council verdict chip + chart thumb. Expert expands the
full dated event log per name, conviction spread, miss-streak counter, and the
raw add/drop activity feed.

**Payload reshapes (SHORTLIST)**
| Endpoint | New/changed field | Source |
|---|---|---|
| /api/desk/watchlist | `events[]` per row + `days_on_list` + `curator_delta` | query agent_watchlist history across scan_dates (table keyed by scan_date) |
| /api/watchlist/candidates (POST) | already exists — ★ from SCANNERS writes here | KEEP |

═══════════════════════════════════════════════════════════════════════════════
4 · DEBATE — "the desk's argument, in plain words" (Council; amendment 1: STAYS)
   consumes /api/desk/debate · POST /api/desk/debate/push (user-pushed cards)
═══════════════════════════════════════════════════════════════════════════════
```
┌── how the desk decided tonight (read top to bottom) ──────────────── [B] ──────┐
│  4 model seats debate each name → the CHAIR rules TAKE/SKIP → the SIZER sets qty.│
│  Seats: Scout · Skeptic · Analyst · Historian (hover = which model).            │
│  ⓘ You pushed 1 name today (search box) — marked ★user-pushed below.            │
└─────────────────────────────────────────────────────────────────────────────────┘
┌── KPIL · EP ·  COUNCIL: TAKE (conviction 4)  ───────────────────── [B] ────────┐
│  ┌ BULL ─────────────────────────────┐  ┌ BEAR ────────────────────────────┐   │
│  │ Scout ●●●●○ : "EP pullback to 21EMA│  │ Skeptic ●●○○○ : "breadth thin,    │   │
│  │   on held gap, delivery rising"    │  │   a single-name push"             │   │
│  │ Analyst ●●●●○ : "sector leading"   │  │ Historian ●●●○○ : "EP hit 62%,    │   │
│  │                                    │  │   n only 47"                      │   │
│  └────────────────────────────────────┘  └───────────────────────────────────┘   │
│  CHAIR ruling (plain): "Take it — bull case clears the thin-breadth worry small."│
│  VISION (chart read): daily "clean higher-low above 21EMA" ✓ · weekly base ✓     │
│  SIZER: ×0.9 → final 1,665 (base 1,850) — trimmed for thin breadth  [TRADE PLAN→]│
│  ▸ [E] full transcripts · lens scores · disagreement spread                      │
└─────────────────────────────────────────────────────────────────────────────────┘
┌── ★ EMSLIMITED · user-pushed · COUNCIL: SKIP ────────────────────── [B] ────────┐
│  (same card shape — debated on demand from your search; tool's own scan continues)│
└─────────────────────────────────────────────────────────────────────────────────┘
   [ one card per debated name, ordered by chair rank; user-pushed pinned on top ]
```
**Element annotations**
- Workflow explainer ⟨quote amendment 1 "LLM workflow SHOWN … only language + views become beginner friendly"⟩
- **user-pushed banner + pinned card** ⟨field debate.symbols[].user_pushed; NEW⟩ ⟨quote "card lands on DEBATE tab marked 'user-pushed'. Tool's own screening continues underneath"⟩
- Seat names (plain) ⟨field modelSeatLabel(agent); KEEP — raw model id in hover⟩
- Council verdict + conviction ⟨field sym.chair.verdict/conviction; KEEP — labelled COUNCIL⟩ ⟨cite staged-role: Council⟩
- BULL/BEAR columns + conviction dots ⟨field sym.models[].bull_case/bear_case/conviction via CitedText; KEEP ModelDebateBlock, beginner language⟩ ⟨quote "debate screen STAYS … do not demote to hidden evidence"⟩
- CHAIR ruling plain ⟨field sym.chair.reasoning stripped⟩
- VISION strip ⟨field sym.vision.verdict/reasoning + chart thumbs; KEEP⟩ ⟨cite sub-order "LLM inputs must include stage, purple dots, volume markers"⟩
- SIZER line + [TRADE PLAN→] ⟨field sym.sizer.multiplier/final_qty/reasoning; KEEP⟩ ⟨cite staged-role: Sizer⟩
- `[E]` transcripts / lens scores / disagreement spread ⟨field models raw + conviction_spread⟩

**Beginner vs expert (DEBATE):** beginner sees seat one-liners, the plain chair
ruling, the vision ✓/✗ line, and the sizer result. Expert opens full transcripts,
per-lens numeric scores, objection weights, and the disagreement spread.

**Payload reshapes (DEBATE)**
| Endpoint | New/changed field | Source |
|---|---|---|
| /api/desk/debate | `user_pushed` bool per symbol | POST /api/desk/debate/push tags the row |
| POST /api/desk/debate/push | debate one symbol on demand, full context pack | reuse run_cascade single-symbol path (also used by SCANNERS + shell search) |

═══════════════════════════════════════════════════════════════════════════════
5 · TRADE PLAN — "the pre-trade checklist + sizing, made concrete" (per-name route)
   consumes /api/desk/signal-guide (+ debate row for plan/sizer/gates)
═══════════════════════════════════════════════════════════════════════════════
Opened from SCANNERS / SHORTLIST / DEBATE row. Full-screen. **Sizer** is the
final authority in Section B.
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
┌── B · POSITION SIZE — SIZER (the math, on your capital) ─────────── [B] ───────┐
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
┌── if Sizer refused ────────────────────────────────────────────────  [B] ──────┐
│  ⚠ PAPER ONLY — final qty 0. Paper-trade the steps to build the sample.         │
└─────────────────────────────────────────────────────────────────────────────────┘
   [E] ▸ EXPECTANCY (base-rate) · ▸ full Council debate (→ DEBATE) · ▸ AI signals
```
**Element annotations** (unchanged in substance from V3 §4; role labelled Sizer)
- Header family + template intent ⟨field guide.family → NEW template_intent⟩ ⟨cite TTM-F13/F16⟩
- A · Entry steps ☐1–7 ⟨field signal-guide.steps[] {n,title,instruction,check,source_cite}; KEEP HowToTradeThis, promoted to full screen⟩ ⟨quote "entry condition steps (ORB rules, buy-stop level, day-low stop)"⟩ ⟨cite EP=TTM-B2/S10; strong_start=AR-Strong-Start; d2=TTM-B5c; ipo=SG-Inside-Bar⟩
- step why/do/source ⟨field step.instruction/check/humanizeSourceCite⟩ ⟨quote sub-order "one plain sentence per step + why + exact broker action"⟩
- B · capital input ⟨NEW client setting `capital` localStorage⟩ ⟨cite R1 size=risk₹÷(entry−stop)⟩
- risk₹ band ⟨field governor.risk_band × capital⟩ ⟨cite R2⟩ · base/sizer/bar ⟨field plan.suggested_qty, sym.sizer.*; KEEP SizerBar⟩ ⟨cite staged-role: Sizer⟩
- provisional staging ⟨cite R14b/TTM-H-V1⟩
- C · stop%≤cap ⟨cite R5/C4⟩ · k×ADR display-only ⟨field NEW risk_checks.k_adr from scan_metrics.adr20⟩ ⟨cite C4/TTM-D7⟩ · open-risk before→after ⟨field heat.open_risk_pct⟩ ⟨cite R4⟩ · concurrent tight-SL ⟨cite R3/C3⟩ · no-mental-stops ⟨cite R12/TTM-D11⟩
- paper-only banner ⟨field sizer.final_qty==0; KEEP⟩

**Beginner vs expert (TRADE PLAN):** beginner sees the 7 checklist steps, the
capital box + final qty, the 4 risk checks as ✓/✗, and the paper-only banner.
Expert adds expectancy cohorts, the full Council debate inline, and raw AI signal
scores.

**Payload reshapes (TRADE PLAN)**
| Endpoint | New/changed field | Source |
|---|---|---|
| /api/desk/signal-guide | `risk_checks` `{stop_pct,regime_stop_cap,k_adr,open_risk_now,open_risk_after,concurrent_tight_sl,concurrent_cap}` | plan + governor cap + scan_metrics.adr20 + /api/portfolio/heat + open-positions count |
| /api/desk/signal-guide | `template_intent` velocity/magnitude/hybrid | static map from family (TTM-F13) |
| (shell) | `capital` user setting | localStorage; client ₹risk math |

═══════════════════════════════════════════════════════════════════════════════
6 · POSITIONS — "manage & exit, one instruction per position" (Coach)
   consumes /api/desk/positions · /api/positions/{id}/coach
═══════════════════════════════════════════════════════════════════════════════
```
┌── JBMA · TREND phase · +2.3R ────────────────────────────── [B] ── !urgent? ──┐
│  ▶ HOLD — trail stop to 214, don't touch it.                     — Coach        │
│  entry 198 / SL 214(today) / qty 400 / held 6d   P&L +₹9,200 (+11.6%)  [chart▤] │
│  ┌ R-path sparkline (INITIATION→TREND→EXTENSION bands, trail line) ───────────┐ │
│  └───────────────────────────────────────────────────────────────────────────┘ │
│  why: closed above 21EMA, higher-low intact; day-low 214 is your line.          │
│  [ Edit SL ] [ Edit qty ] [ Close ]   ▸ original thesis · ▸ telegram mirror     │
└─────────────────────────────────────────────────────────────────────────────────┘
┌── RAIN · INITIATION · −0.6R ─────────────────────────── [B] ── ! EXIT NOW ────┐
│  ✖ EXIT NOW — day-low break + two-strike fired.                  — Coach        │
│  entry 320 / SL 302 / qty 250 / held 2d   P&L −₹4,500 (−5.6%)                    │
│  why: closed below prior day-low; second strike. Exit at market, no second-guess.│
└─────────────────────────────────────────────────────────────────────────────────┘
```
**Element annotations**
- Verdict-first line ▶HOLD/⤺TRIM/⤢MOVE-STOP/✖EXIT + `— Coach` ⟨field coach_verdict + action_line; RELAYOUT to top⟩ ⟨cite staged-role: Coach; Playbook §6 hold / §7 exits⟩ ⟨quote spine "adjust their stops, and try to sell while still on strength"⟩
- Phase + open-R ⟨field position.phase, open_r; KEEP⟩ ⟨cite TTM-F13⟩
- ₹ P&L ⟨field position.pnl_rupees, pnl_pct; surfaced⟩ · entry/SL/qty/held ⟨field entry, todays_stop, qty, days_held⟩
- R-path sparkline ⟨field r_path + trail_stop; KEEP RPathSparkline⟩
- why (layman) ⟨field advisor_note ?? plain_why⟩ · day-low/two-strike ⟨field position.fired⟩ ⟨cite TTM-E2⟩
- EXIT-NOW banner ⟨field exit_now/urgent/fired⟩ ⟨cite R12⟩ · Edit/Close/thesis/telegram ⟨field update/close, original_thesis; KEEP collapsed⟩

**Beginner vs expert (POSITIONS):** beginner sees the Coach verdict line, P&L, the
one-line why, and the three action buttons. Expert opens the original thesis, the
telegram mirror, the full R-path with band math, and the fired-trigger detail.

**Payload reshapes (POSITIONS):** none — pure relayout (Coach verdict to top,
₹P&L surfaced, thesis/telegram collapsed).

═══════════════════════════════════════════════════════════════════════════════
7 · JOURNAL — "your trades first; system R&D behind Advanced"
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
- Your-trades table ⟨field /api/journal; KEEP LedgerTab, user-first⟩ ⟨quote "user's trades first, system R&D behind 'advanced'"⟩
- R + ₹P&L + reason ⟨field outcome_r, realized ₹, reason_tag⟩
- `▶ ADVANCED` ⟨field track-record + lessons + expectancy; KEEP behind `[E]`⟩

**Beginner vs expert (JOURNAL):** owner's own note — this is the one tab that was
already differentiated. Beginner = your-trades ledger only. Expert = the R&D block
(cohort track record, expectancy, lessons digest).

**Payload reshapes (JOURNAL):** none.

═══════════════════════════════════════════════════════════════════════════════
CHART — split-panel (SCANNERS/SHORTLIST/POSITIONS) + full-screen route
═══════════════════════════════════════════════════════════════════════════════
```
┌─ list (left) ─┐┌─ CHART (right split-panel, or full-screen) ───────────────────┐
│ KPIL   TAKE   ││  KPIL  [D] [W]•  candles + vol + 10/21 EMA + ● purple dots     │
│ SUNPH  WATCH  ││  ┌──────────────────────────────────────────────────────────┐ │
│ ATUL   PAPER  ││  │  (weekly default when opened from a scanner/shortlist hit)│ │
│ …             ││  └──────────────────────────────────────────────────────────┘ │
│               ││  ▮▮▮ volume                                                    │
│               ││  legend chips: [10EMA][21EMA][●dots] · [+ e50/stage/shakeout ▾]│
└───────────────┘└───────────────────────────────────────────────────────────────┘
```
- Split-panel on SCANNERS/SHORTLIST/POSITIONS ⟨quote "chart split-panel on
  SCANNERS/SHORTLIST/POSITIONS"⟩ + full-screen route ⟨quote "full-screen chart route"⟩
- **Default layers: candles + volume + 10 EMA + 21 EMA + purple dots** ⟨field
  overlays ema10/ema21 + markers.purple_dot; KEEP⟩ ⟨cite Playbook §4; sub-order
  "user kept PD explicitly"; default-on⟩
- **Weekly-first when opened from a scanner/shortlist hit** ⟨quote "weekly-first on
  scanner hits"⟩ ⟨NEW ChartDrawer `initialTimeframe` prop = 'weekly' from
  SCANNERS/SHORTLIST, 'daily' from POSITIONS⟩
- Behind toggle: ema50/ema200 / persistency / pocket-pivot / stage / shakeout /
  RMV / HMM ⟨field remaining overlays; CHANGE default-off⟩
- Legend as chips, no inline e10/e50 text ⟨field footer legend; KEEP chips; remove inline labels⟩
- Reshape: ChartDrawer `layers` + `initialTimeframe` client state; default
  {candles,volume,ema10,ema21,purple_dot}. No API change.

═══════════════════════════════════════════════════════════════════════════════
BUILD PLAN — Codex-executable slices, dependency order
═══════════════════════════════════════════════════════════════════════════════
Frontend + thin-API only (no backend engine change); "thin API" = read an existing
column / regroup a payload / derive from already-computed values. Each slice names
files + acceptance + the wireframe section it satisfies. **Slice 1 ships the new
IA immediately** (shell + nav + MARKET home) so the owner sees the spine first.

- **V4-T1 · Shell + nav + MARKET home.** Files: `App.jsx`, `App.css`,
  NEW `MarketHomeTab.jsx` (from DeskTab's TonightsCall/LawRow + MarketTab strips).
  6-tab nav (MARKET·SCANNERS·SHORTLIST·DEBATE·POSITIONS·JOURNAL), `[beg|exp]`
  toggle (localStorage `mode`) via context, universal symbol-search box (stub →
  T8), verdict hero + market-law + stepper + market-evidence summary; MarketTab
  evidence under `[E]`. Accept: 6 tabs render; MARKET is the landing screen;
  screenshot==ASCII §1; expert flips a global class. (Section 1; dep: none)
- **V4-T2 · /api/pipeline/status progress fields.** `api/app.py` (3162). Add
  stage_index/total_stages/eta_seconds/data_live_hint. Accept: `18/26`+ETA during
  a run; unit-test index/total from `_load_stages()`. (Section 1 progress bar; dep: none)
- **V4-T3 · /api/desk/debate scan_metrics + scout_note + pool_summary.**
  `api/app.py` (4134). Add scan_metrics (discovery_bucket/features_daily), rs,
  scout_note (first sentence of chair/model reasoning via existing cite-strip),
  pool_summary {actionable,shortlisted,scanned_total}, user_pushed bool. Accept:
  each symbol carries 4 metrics or honest null + a one-line scout_note. (Sections
  1,2,4; dep: none)
- **V4-T4 · /api/scanners/presets.** NEW `api/app.py` route + NEW static
  `PRESET_REGISTRY` (name/owner/recipe/cite/status per preset). LIVE hits from
  discovery_bucket_map archetype membership + candidates pool; DATA-READY hits from
  screener_hits/symbol_quality COUNT by screener; BUILD → status only. Accept:
  returns all presets with correct status chip + today's hit count (or null for
  BUILD). (Section 2A; dep: none)
- **V4-T5 · /api/scanners/run + /api/scanners/saved.** NEW `api/app.py` routes +
  NEW `saved_screens(name,conditions_json)` table. run: filter features_daily/
  discovery_bucket metrics by {metric,op,value}[]; saved: GET/POST/DELETE. Accept:
  a 4-condition screen returns matching symbols with scan_metrics rows; save/reload
  round-trips. (Section 2B; dep: T3 for scan_metrics shape)
- **V4-T6 · SCANNERS tab.** NEW `ScannersTab.jsx`. Segmented control (Practitioner
  | Builder); preset cards (owner+recipe+hits+STATUS chip, greyed when BUILD);
  builder (stackable conditions, saved screens); shared result-row grammar with
  `[★][→debate][chart]`. Accept: screenshot==ASCII §2 both sections; BUILD presets
  greyed and non-interactive; every row has the 3 actions. (Section 2; dep: T1,T4,T5)
- **V4-T7 · /api/desk/watchlist events + curator_delta.** `api/app.py` (1945/
  watchlist). Add events[] {date,status,prev_status,reason} across scan_dates +
  days_on_list + curator_delta. Accept: a symbol shows its dated add/promote/drop
  log; delta counts add/drop/promote since last night. (Section 3; dep: none)
- **V4-T8 · POST /api/desk/debate/push + shell search + user-pushed.**
  `api/app.py` + `App.jsx` search box + `DebateTab.jsx`. Single-symbol debate via
  run_cascade path; tag row user_pushed; pin on DEBATE. Accept: searching a symbol
  or hitting `→ debate` on a scanner row lands a pinned user-pushed card; tool's
  own scan rows still present. (Sections shell,2,4; dep: T3)
- **V4-T9 · SHORTLIST tab.** NEW `ShortlistTab.jsx`. PROMOTE/HOLD/DEMOTE/DROP
  groups, weekly-first chart thumb, per-symbol dated Curator event log, Council
  verdict chip, `[plan→]`. Accept: screenshot==ASCII §3; events render; chart
  thumb opens weekly-first. (Section 3; dep: T1,T7,T12)
- **V4-T10 · DEBATE tab (relanguaged, Council label, user-pushed pin).**
  `DebateTab.jsx`. Workflow explainer + per-name bull/bear (seat names, cite-
  stripped) + Council chair ruling + vision + Sizer line + `[TRADE PLAN→]`;
  transcripts/lens/spread behind `[E]`; user-pushed pinned. Accept: screenshot==
  ASCII §4; debate visible, plain language. (Section 4; dep: T1,T3,T8)
- **V4-T11 · /api/desk/signal-guide risk_checks + template_intent.** `api/app.py`
  (4444). Assemble risk_checks + template_intent. Accept: block present for a sized
  name; k×ADR display-context only. (Section 5; dep: T3 for adr20)
- **V4-T12 · Chart split-panel + weekly-first + layer defaults + full-screen route.**
  `ChartDrawer.jsx` (+ split-panel host in ScannersTab/ShortlistTab/PositionsTab).
  Default layers {candles,volume,ema10,ema21,purple_dot}; `initialTimeframe` prop
  (weekly from scanner/shortlist, daily from positions); chip legend; remove inline
  EMA text; full-screen route. Accept: first paint shows only default set; opens
  weekly from a scanner hit; split-panel docks right. (Chart section; dep: T1)
- **V4-T13 · TRADE PLAN route (Sizer).** NEW `TradePlanTab.jsx` (promote
  HowToTradeThis). Full-screen entry steps + Sizer sizing-math (capital input) +
  risk-checks + paper-only; expert expectancy/AI; link to DEBATE + chart. Accept:
  screenshot==ASCII §5; a beginner sizes off capital with every step+why+broker
  action+cite. (Section 5; dep: T1,T6,T11)
- **V4-T14 · POSITIONS relayout (Coach).** `PositionsTab.jsx`. Coach verdict-first,
  ₹P&L, collapse thesis/telegram, layman why, daily chart split-panel. Accept:
  screenshot==ASCII §6. (Section 6; dep: T1,T12)
- **V4-T15 · JOURNAL user-first + advanced.** `LedgerTab.jsx`→`JournalTab.jsx`.
  User trades first, R&D behind `[E]`. Accept: screenshot==ASCII §7. (Section 7; dep: T1)
- **V4-T16 · Glossary/term sweep + beginner/expert audit + done-test.** All tabs.
  Every jargon term inline-explained; verify each screen's beginner/expert split
  matches its spec block; screenshot each screen on real data, diff vs ASCII; walk
  scan→shortlist→decide→plan→size→enter→manage→exit reading only screens. Accept:
  fidelity pass green on every tab. (all; dep: all)

═══════════════════════════════════════════════════════════════════════════════
SUPERSESSION — V3 → V4 mapping (nothing lost; several re-homed)
═══════════════════════════════════════════════════════════════════════════════
**WIREFRAMES_V3.md is fully superseded.** V3's reusable pieces map forward:

| V3 piece | V4 disposition |
|---|---|
| V3 TONIGHT tab (verdict hero, law, stepper, progress bar) | → **MARKET home** (§1), stepper extended to 6 steps (adds SCANNERS + SHORTLIST) |
| V3 SCAN·POOL segment (family groups, objection chips, scan_metrics) | → **SCANNERS** (§2A) reframed as *named practitioner presets* + Scout annotations |
| V3 SCAN·WATCHLIST segment (living list, events) | → **SHORTLIST** tab (§3), owned by Curator role, weekly-first thumbs added |
| V3 DEBATE tab | → **DEBATE** (§4), relabelled Council, user-pushed pinning added |
| V3 TRADE PLAN route | → **TRADE PLAN** (§5), Section B relabelled Sizer |
| V3 POSITIONS relayout | → **POSITIONS** (§6), relabelled Coach |
| V3 JOURNAL | → **JOURNAL** (§7), unchanged |
| V3 MARKET (6th tab) | → folded into **MARKET home** `[E]` evidence (no longer a separate tab) |
| V3 pipeline_status / debate scan_metrics+objections / watchlist events / signal-guide risk_checks / market_context reshapes | **all carried forward**; debate reshape gains scout_note + pool_summary rename (actionable/shortlisted/scanned_total) |
| V3 build plan V3-T1..T15 | superseded by **V4-T1..T16**; net-new work = /api/scanners/presets+run+saved, PRESET_REGISTRY, debate/push + shell search, chart split-panel + weekly-first, staged-role labels |

**The old-IA UX-polish wave** (DESK/DEBATE/MARKET/POSITIONS/LEDGER as currently
composed): its **backend/correctness fixes SURVIVE and are consumed by V4** (stop-
breach coach fix, pnl_rupees/pnl_pct, seat names, cite-stripping helpers,
agent_watchlist writer). Its **cosmetic OLD-IA surfaces are SUPERSEDED** — health
pill folds into the freshness stamp + MARKET verdict; the old verdict banner
becomes MARKET's counts + SCANNERS Scout lines; the 5 system-shaped tabs are
replaced, not reskinned. Rule (unchanged from V3): don't re-solve a running-wave
*correctness* fix; do rebuild the *surface* it lives on.

*End WIREFRAMES_V4.md — every element carries a cite/quote/field; screenshot-vs-
ASCII is the done-test per the owner's standing wireframe-fidelity rule.*
</content>
</invoke>
