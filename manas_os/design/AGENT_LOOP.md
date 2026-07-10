# AGENT_LOOP — orchestration prompt for building the Manas agentic scanner
# (I, the main thread, re-read this every cycle. This is the loop I run until DONE.)

## MISSION
Build the LLM-agent trading system end-to-end on top of the existing deterministic engine:
deterministic filters (regime / themes / sectors / technicals) shortlist 10-20 names →
2-3 LLM debate agents argue the shortlist through the user's setup lenses (Manas Arora
Strong Start, EP theme, IPO base, high tight flag, PEAD drift) → chart screenshots at
multiple timeframes get a VISION agent promote/demote pass → a SIZER agent picks final
names + position size from environment + risk appetite → Telegram entry signals → a
JOURNAL-COACH agent sends exit/management signals → agents learn from their own outcomes
via MD lesson files injected back into their prompts. Future hooks: Sharpe per cohort,
Markov regime models. The user WANTS the LLM layer to have real latitude — improve its
judgment with better context, do not strangle it with parameters.

## ROLES (model routing)
- **ME (Fable/Opus main thread)** — orchestrator + advisor. Write specs, verify each
  cycle's output against the aim, tune the next cycle, keep this file's STATE current.
  Never bulk-code.
- **CODEX** — the coder. One batch at a time via codex-rescue subagent (--fresh,
  background). **BATCH SIZE RULE (user, 2026-07-08): keep Codex batches SMALL — one
  module/table/endpoint per batch, ~30 min of work max; Codex freezes on big batches.**
  Split wave steps into sub-batches when in doubt (e.g. A1 tables = one batch, A2
  rewiring = a second). **If Codex goes blank (queued or silent >20min) or runs out of
  credits → switch coder to a SONNET subagent with the same batch prompt** (general-
  purpose agent, model sonnet). Note the switch in STATE.
- **EVERY subagent prompt MUST include: "do NOT spawn subagents; do the work yourself;
  your final message is the report"** — both Sonnet coder-fallback and research agents
  have failed by delegating to children and returning "waiting" (3 occurrences 2026-07-08).
- **SONNET subagents** — grunt work: reading the study folder, extracting specs from
  PDFs/notes, summarizing logs, data audits, fixture prep, prompt-pack assembly.
- **HAIKU subagents** — cheap bulk reads (e.g. CHARTGYM page-by-page extraction) when
  Sonnet is overkill.
- Debate/vision/sizer/coach agents AT RUNTIME = OpenRouter models (configurable in
  config.yaml `advisor.*` / new `agents.*` keys) — pick 2-3 DIFFERENT model families for
  debate diversity, one vision-capable model for the chart pass.
  **TESTING RULE (user, 2026-07-08): use the latest capable FREE OpenRouter models.**
  At testing time, query the live model list (GET https://openrouter.ai/api/v1/models),
  filter pricing==0 (":free" variants), pick the newest/largest capable ones from
  DIFFERENT families + one free vision-capable model. Do not hardcode a stale list in
  code — model ids live in config.yaml only; testing burns zero credits.

## THE LOOP (each cycle)
1. READ STATE (bottom of this file) → pick the next unchecked wave step.
2. SPEC: if the step lacks a written contract, write/extend it (AGENTIC_BUILD_SPEC.md).
3. BUILD: launch ONE coder batch (Codex; Sonnet on fallback rule above).
4. GRUNT (parallel OK): launch Sonnet/Haiku for any reading/extraction the NEXT step needs.
5. VERIFY myself when the batch lands: pytest (never regress), exercise the new
   stage/endpoint against the real DB with a live or dry-run call, read actual outputs
   (agent transcripts, telegram dry-run payloads, screenshots). Light-touch on style,
   strict ONLY on: no crashes, no silent failures, agent outputs logged, money-math
   validated by risk/plan.py.
6. ANALYZE vs the aim: does the cycle's output move the pipeline toward the MISSION
   picture? Note gaps in STATE.
7. FINETUNE: fold findings into the next cycle's spec. Update STATE. Commit + push.
8. Schedule the next wakeup; repeat until DONE-TEST passes.

## AUDIT & EVOLVE (added 2026-07-09, user directive — the loop rewrites itself)
- **Wave-close audits are DELEGATED, not self-graded**: at the end of every wave (and
  every ~3 cycles inside a long wave), launch an independent auditor with the
  no-delegation clamp — SONNET for code-level (cross-file consistency, error paths, SQL,
  test gaps), OPUS for architecture/judgment-level (does the built thing serve the
  mission; where is the design drifting). Auditor reports findings; orchestrator verifies
  each finding before acting (auditor claims are claims).
- **Findings drive EVOLUTION, not just fixes**: when audits or the outcome ledger show an
  agent going the wrong direction, REWRITE its prompt/spec — the debate system prompt,
  chair instruction, lens files, sizer/coach prompts, and the coder-batch prompt templates
  are all mutable. Every prompt change gets a dated entry in AGENTIC_BUILD_SPEC.md
  ("PROMPT REV:" prefix) stating what changed and which finding/night motivated it —
  versioned evolution, never silent drift.
- **The loop's own protocol is amendable**: process failures become rules in THIS file
  same-day (precedent: small-batch rule, no-delegation clamp, append-only STATE,
  Codex->Sonnet fallback — all born from failures). If a rule stops earning its keep,
  amend it with a dated note.
- **Runtime agents evolve on evidence**: lesson digest + agent track records (outcome_r
  joins) are the signal; prompt revs cite them. Keep latitude — tune context and framing,
  never bolt on hard caps the user rejected.

## WAVES
**A. Foundations (agent plumbing)**
A1 [x] `agent_verdicts` table (agent TAKE/SKIP/rank/narratives per scan_date+symbol+agent)
      + `scan_agent_logs` (every call: prompt hash, model, latency, tokens, parsed ok,
      validation outcome). Agents NEVER write to `refusals` (keeps gate analytics clean).
A2 [x] Option-1 wiring: cascade shortlist (target 10-20; make the pool cutoff a config
      `agents.shortlist_size`, default 15 — tune in wave E) feeds the debate; deterministic
      path always runs; agent layer additive on top.
A3 [x] Study distillation (Sonnet/Haiku): read `manas_os/design/study/*/main.md` (other
      files only if main.md points to them) + the CHARTGYM compilation of Manas Arora's
      PDF → produce `manas_os/design/agents/LENS_STRONG_START.md` (chart markers, entry
      conditions in Arora's own terms), `LENS_EP.md`, `LENS_IPO.md`, `LENS_HTF.md`,
      `LENS_PEAD.md` — these are the debate agents' lens prompts. Distill faithfully from
      the sources; cite file+section per rule so drift is checkable.
**B. Debate layer**
B1 [x] Debate orchestrator `manas_os/agents/debate.py`: ONE call per model (2-3 models),
      ALL shortlist names in the prompt (joint comparative ranking beats per-symbol calls),
      each model argues every lens, returns structured JSON: per-symbol {lens_scores,
      bull_case, bear_case, verdict TAKE/SKIP, conviction 1-5}. Context pack per symbol:
      compressed technicals (trend, EMA alignment, dist-from-50EMA, volume trend, stage),
      fundamentals, regime + regime_age_days, base rates from setup_expectancy, and the
      last-N lesson digest (wave D). Retry once on bad JSON.
B2 [x] Chair merge: rank-aggregate the 2-3 models' verdicts (mean conviction, disagreement
      flagged as its own signal — a 5/1 split is information), persist to agent_verdicts.
**C. Vision + sizing + signals**
C1 [x] Chart renderer: headless PNGs per finalist (daily ~120 bars, weekly ~2yr) via
      mplfinance/plotly from daily_prices — saved under data/agent_charts/{date}/{sym}_{tf}.png.
C2 [x] Vision agent: send both timeframes per finalist to the vision model with the
      relevant LENS file; returns promote/demote + what it sees (base quality, pivot,
      volume signature). Adjusts chair ranking (bounded: ±2 ranks, veto allowed with
      stated reason).
C3 [x] Sizer agent: input = final list, governor law, portfolio heat, user risk appetite
      (config `agents.risk_appetite: aggressive`), expectancy base rates. Output = picks
      + size as a MULTIPLIER 0.25x-1.25x of the risk/plan.py base size + reasoning.
      risk/plan.py validates the resulting qty (the only arithmetic authority); sizer
      chooses within the validated envelope — latitude without hallucinated math.
C4 [x] Telegram entry signal: nightly message per pick (name, lens, conviction, plan
      numbers from risk/plan, sizer multiplier + why, top bear risk). Reuse
      telegram_engine armed_list plumbing; dry-run mode until user OKs live.
**D. Journal coach + self-training**
D1 [x] Coach agent: daily pass over open positions (trail_plan/two_strike outputs + bars +
      original thesis from agent_verdicts) → Telegram management/exit signals with the
      original bull case quoted ("your thesis was X — it broke/held because Y").
D2 [x] Lesson loop: when a position closes or a T+10 outcome lands for an agent TAKE:
      auto-generate `manas_os/design/agents/lessons/{date}_{sym}.md` — what each agent
      said, what happened, why right/wrong (one LLM call, grounded in the stored
      transcripts + price path). A rolling digest (last 20 lessons, compressed by Sonnet)
      is injected into every debate/sizer prompt. Prune/curate quarterly — lessons must
      stay lessons, not noise (market volatility acknowledged: a right process losing is
      logged as GOOD process, per the decision-vs-outcome principle in the study docs).
**F. The living UI (after C/D land; contract: AGENT_UI.md — GREENFIELD: new manas_os/desk/
app, zero imports from the old frontend; keep only MBI + XP as data, rendered fresh)**
F1 [ ] /api/desk/feed + DESK activity stream & morning brief
F2 [ ] DEBATE theater (verdicts, conviction splits, vision PNGs)
F3 [ ] POSITIONS lifecycle cards quoting original theses
F4 [ ] LEDGER: agent track records + lessons diary
F5 [ ] live-mode polish (in-flight indicators, date scrubber)
**E. Tuning + future**
E1 [ ] Shortlist-size experiment: run the loop at N=10/15/20 for a week each (or replay
      sample), compare debate quality + cost + hit-rate → fix `agents.shortlist_size`.
E2 [ ] Quant hooks: Sharpe per lens-cohort in the scoreboard; Markov regime-transition
      probabilities as a context field (spec first, small).
E3 [ ] Paper month → graduation criteria written in LEARNINGS before any live sizing.

## DONE-TEST (the loop ends when ALL true)
- Nightly run end-to-end on real data produces: shortlist → 2-3-model debate transcripts
  logged → vision-adjusted ranking → sized picks → Telegram (dry-run or live) entry
  digest → coach signals for open positions. Zero crashes across 5 consecutive sessions.
- agent_verdicts + scan_agent_logs populating; lesson files generating on closed outcomes;
  lesson digest visibly present in the next day's prompts.
- User has seen one full night's output and approves switching Telegram from dry-run.

## STANDING NOTES
- The deterministic layer stays (user instruction: shortlist BY the existing filters) —
  it is the shortlist maker + math authority, the agents are the judgment layer.
- Don't be defensive with agent latitude: conviction, ranking, veto, sizing multiplier,
  narrative are THEIRS. Only crash-safety, logging, and money-arithmetic are hard rails.
- Cost control: one debate round per model per night; vision only on top ~8; retries
  capped at 1. Models swappable in config without code change.
- User's phrase to honor: "open to the volatile nature of the market" — lessons and base
  rates inform, they never auto-tighten thresholds.

## STATE (update every cycle — APPEND dated lines, never rewrite history)
- 2026-07-08: Loop created. Cycle 1: A1/A2 (agent tables + Option-1 rewiring, Codex) and
  A3 (5 LENS files, Sonnet, citations verified; PEAD rebuilt from Feedback/) done.
- 2026-07-09: B1a context pack (Sonnet fallback — Codex sandbox read-only; regime_age,
  weekly closes look-ahead-safe, honest omissions). B1b hardening (skip+log, retry-once,
  real token usage). B2 two-stage chair (deterministic aggregation + strike-only risk
  gate, failure-safe partial). C1 chart renderer (PNGs eyeballed). C2 vision (±2 clamp,
  veto; orchestrator fixed tie-break bug — promoted name wins boundary ties). C3 sizer
  (multiplier in validated envelope; orchestrator fixed wiring — no longer gated on
  optional vision). C4 dry-run signals (agent_signals table). D1 coach (LLM-independent
  exit signals; exercised live on HUDCO). D2 lessons (fill-checked backfill, stub-safe,
  rolling digest). E4+E5 (per-family lens trim ~4x prompt cut; 429 backoff). 259 tests.
- NIGHT 1 (free models, real DB): Nemotron-120B debated grounded; chair struck both on
  distribution risk; cascade-skip correct; hy3 truncation + qwen 429 handled gracefully.
  Durability fix: per-model commits (first attempt lost work to end-of-stage commit).
- NIGHT 2: lens trim confirmed (real usage 11,154/2,037); chair strike call died
  upstream -> aggregate persisted, sizer ran, signals none. Degradation chain validated.
  Roster: seats 2/3 swapped to gemma-4-31b + nemotron-nano-30b (hy3/qwen flaky).
- WAVES A-D + E4/E5 COMPLETE. REMAINING: E1 shortlist experiment, E6 chair-strike review
  (double-counts gate-priced risks?), AD4 run_card, AD10 catastrophe-stop replay, E2
  quant hooks, E3 paper-month graduation — and WAVE F living-desk UI (AGENT_UI.md,
  greenfield manas_os/desk/). Telegram dry-run until user flips agents.telegram_live.
- PROCESS NOTE: STATE updates via string-replace silently no-op'd cycles 2-10 (this
  block was rebuilt 2026-07-09). Rule: APPEND dated lines; verify the file changed
  (git diff) before committing a doc update.
- 2026-07-09 (cycle 13): AD4 run_card + E6 chair anti-double-count landed (Sonnet
  fallback, 266 green). AUDIT-1 (independent Sonnet audit of waves A-E) found 1 CRITICAL
  (outcome_r wiped on same-night rerun by INSERT OR REPLACE in all four writers) + 7
  more; ALL FIXED same-day (AU1-AU8: upserts preserving outcome history + rerun test,
  atomic lesson writes, honest total-outage run_card, chair strike skip-and-log, floor-
  exhaustion test, _shared.py consolidation, public get_sender, tie/multi-position
  tests). 273 green. Audit-and-evolve protocol now standing (loop file). NEXT: F0 desk
  backend gaps (G1-G5), then F1 greenfield desk app per DESK_WIREFRAMES.md.
- 2026-07-09 (cycle 14): F0 desk backend gaps G1-G5 landed (Codex; run_card regime now
  carries XP/MBI/ratios + morning_brief with deterministic fallback; chart/track-record/
  lessons endpoints). Orchestrator fixes: hermetic brief test (real .env key was leaking
  into tests -> live LLM call), PROMPT REV: brief context now display-rounded (free model
  regurgitated 17-decimal floats). 278 green. Exercised live: regime block + brief
  compose on real DB. NEXT: F1 greenfield desk shell + DESK tab per DESK_WIREFRAMES.
- 2026-07-09 (cycles 15-16): F1 greenfield desk LIVE on real data (shell + DESK tab:
  brief, regime strip, activity stream with expandable real night rows, degraded-night
  honesty; /api/desk/feed; 280 green; zero old-frontend imports). Restyled to the user's
  DESIGN_SPEC (dark #0a0a0a / cyan / purple / green; verified via computed styles —
  user later granted discretion, dark kept with reasons logged). node_modules briefly
  staged in F1 commit — removed + gitignored same day. NEXT: F2 DEBATE theater.
- 2026-07-09 (cycle 17): F2 DEBATE theater LIVE on the real night (attributed bull/bear,
  conviction dots, honest no-vision stamp, math:engine plan, sizer reasoning citing
  net-costs India context); /api/desk/debate; 282 green. Orchestrator fixed a UTC/IST
  scrubber bug (prev jumped 2 days, next dead — local-parts date formatting now).
  PROMPT-REV queued: hand sizer 'no base rates available' text instead of raw no_data
  dict (it echoed garbage). NEXT: F3 POSITIONS tab.
- 2026-07-09 (cycle 18): F3 POSITIONS live (lifecycle card w/ SVG sparkline + phase
  bands + trail line, honest no-thesis, coach headline, Telegram mirror, urgent variant;
  /api/desk/positions reusing coach helpers; sizer no_data PROMPT REV landed; 284 green;
  agent verified live on real HUDCO -1.02R INITIATION). Roster: nemotron-only (user —
  others failing). NEXT: F-UPLIFT U1-U8 (user priority over F4).
- 2026-07-09: model budget update (user): $5 OpenRouter balance loaded — low-cost PAID
  models allowed alongside free. Roster now: nemotron-120b:free + deepseek-chat (paid) +
  qwen3-next-80b (paid) for debate diversity; gemma-4-31b (paid) vision. Paid tiers avoid
  the free-pool 429s. Cost watch: scan_agent_logs token counts are the meter (~<1c/night
  at current sizes); flag in STATE if a night exceeds ~5c.
- 2026-07-09 (cycle 19): F-UPLIFT U1-U8 landed + verified via computed styles (56px
  header, XP badge, regime pill, 4 metric tiles 8px-radius, brief card w/ overline,
  timeline rail + state dots + agent chips, formatted expand grids; screenshot tool
  itself flaky — DOM/state verified instead; USER should eyeball 5174). NEXT: F4 LEDGER,
  then night 3 on the new paid+free roster.
- 2026-07-09 (cycle 20): F4 LEDGER live (track-record table w/ honest building-sample
  empty state, lessons diary + digest-in-force block, journal summary tiles; 284 green;
  descoped regime/trend columns honestly vs fabricating). All 4 desk tabs BUILT.
  NEXT: F5 (governor law row + refusal funnel + gate dots), then NIGHT 3 on the paid+free
  roster.
- 2026-07-09 (cycle 21): F5 verified live — TODAY'S LAW tile row on DESK; THE GATE
  funnel on DEBATE (real: 2382->1620->938->2->2, per-gate drops) + six gate dots per
  candidate w/ evidence hovers; run_card carries governor+heat; 284 green. Finviz/
  deepvue audit folded as VIZ-PASS V1-V7 (V1/V3/V4/V5/V7 ride into F6; V2 treemap own
  batch; V6 bubble skipped till book >=8 positions). Single-interface rule locked (no
  beg/expert split). NEXT: NIGHT 3 (paid roster) then F6 MARKET w/ viz-pass.
- 2026-07-10 (cycle 22): NIGHT 3 on paid+free roster — ALL THREE families parsed ok
  (nemotron 21.6s, deepseek 18.5s, qwen 11.6s), chair ok, vision ran. Cost ~half a cent
  (32.4k in / 2.8k out). Real multi-model signal: ARSSBL unanimous 3-TAKE conv 3/4/5;
  JAMNAAUTO unanimous 3-SKIP. Vision VETOED the 3-TAKE on a LENS-ROUTING BUG (family
  'catalyst' fell through to Strong Start lens; vetoed 'IPO Base doesn't match Strong
  Start') — orchestrator fixed _lens_path to route setup-first (IPO Base->LENS_IPO,
  catalyst->LENS_EP); 284 green. Night 4 validates the fix. NEXT: F6 MARKET tab w/
  VIZ-PASS V1/V3/V4/V5/V7 baked in.
- 2026-07-10 (cycle 23): F6 MARKET tab + VIZ-PASS V1/V3/V4/V5/V7 verified (286 green;
  live: 15 bulk deals rendered from disclosures, regime gauge on DESK, color-scaled
  cells, sizer multiplier bar). DATA GAPS surfaced: only 1 sector index has history
  (run scripts/import_nse_index_history.py backfill), insider feed 0 rows for the date
  (feed coverage, not code). NEXT: V2 treemap + index-history backfill rider, F7 FII/DII,
  then next independent audit over the whole desk.
- 2026-07-10 (cycle 24): V2 sector treemap live (hand-rolled squarify, click filters
  movers; honest num_stocks proxy noted); index-history backfill: 183 indices / 29k rows.
  TWO DATA-SHAPE ISSUES OPEN -> next batch: (a) returns None on the new index names
  (helper/name mismatch), (b) index taxonomy noise (strategy/factor indices flood the
  sector set; VIX rendered as a row — should feed AD9 sizer context instead). 286 green.
- 2026-07-10 (cycle 25): taxonomy+returns cleanup verified (290 green): classify_index
  BROAD/SECTORAL/THEMATIC (52 default, 159 w/ toggle), India VIX extracted as
  vix:{value,band} (live: 14.68 normal) + AD9 context_pack symbol fix — sizer VIX
  context now live; case-normalization fixed broad-index leak into treemap; original
  'returns None' was a stale-server artifact (real returns confirmed: Nifty50 -2.12 1d).
  NEXT: F7 FII/DII ingest, then AUDIT-2 over the desk.
- 2026-07-10 (cycle 26): F7 FII/DII LIVE (Groww SSR source — NSE's own API is Akamai-
  walled, documented; 21 days ingested, real nets on the MARKET strip; failure-safe
  skip stage after ingest_bhavcopy; 296 green). Classifier outage paused the loop
  ~30min mid-cycle; resumed clean. NEXT: AUDIT-2 (desk + /api/desk endpoints), then
  full status report to user.
- 2026-07-10 (cycle 27): AUDIT-2 (desk + endpoints) — security axes CLEAN (no XSS, SQL
  parameterized, chart route traversal-proof); findings fixed same-day: atomic run_card
  write, chart date semantic validation (2026-13-99 was passing the digit regex — real
  catch), dead code removed, vitest harness + 8 pure-fn tests. 297 py + 8 js green.
  BUILD PHASE ESSENTIALLY COMPLETE -> soak cadence: nightly runs accumulate lessons/track
  records; remaining gated on market days (E1 shortlist experiment, E3 paper-month
  graduation, AD10 catastrophe replay). Telegram-live flip = user's decision.
- 2026-07-10 (cycle 28, soak #1): user pain-point wave — nothing ran unattended + desk
  opened on empty "today". Fixed: latest-night default (/api/desk/latest), header
  UPDATE button w/ live stage progress, stale-nudge run-now link, run_daily_update.bat
  (+chartsmaze scrape), start_desk.bat; schtasks registration classifier-blocked ->
  one-liner handed to user. Full night ran LIVE on 2026-07-09: 18/18 stages ok,
  shortlist=1 (MAHLOG), 3 paid+1 free models parsed, chair SKIP (distribution cluster,
  wide stop) — desk sat out honestly. UX review (new standing rule: feature-vs-ask +
  rendered-UI, not pipeline green) caught 3 defects, fixed: run_card cwd-split path,
  stale-partial rows from aborted rerun read as incomplete night (latest-attempt-per-
  stage), skip!=failure banner, brief decimal split ("79. 0"). 299 py + 8 js green;
  commits 7dbf3af9, 2cb3e1e1. SOAK HEALTH: tokens/night ~36k in / ~4k out (half-cent,
  no creep); 0 fail rows latest-attempt; lessons empty (correct — no TAKE outcomes yet);
  agent nights clean streak = 3 (07-07/08/09; DONE-TEST needs 5). Dry-run signal HUDCO
  sent=0. NEXT soak pass: verify tomorrow's night, watch clean-streak 4/5.
- 2026-07-10 (cycles 29-33, WAVE G/H/I sprint): user complaint list -> WAVE_G_SPEC (verbatim-
  traced, done-tests). SHIPPED+verified live: G1 debate 10-name floor w/ NEAR_MISS tiers +
  agent_watchlist PROMOTE/HOLD/DEMOTE/DROP + charts for all debated (rerun 07-09: 10 names,
  40 verdicts, watchlist+PNGs real); G2 tap-glossary every term (Codex); G3 MARKET restructure
  (broad strip, sector table, stock-only movers — root cause: old panel NEVER queried stocks;
  ETF leak fixed 3-layer, NSE-master-list chip filed); G4 positions manage+coach (Codex; notes
  clobber fixed in review). G5 exactness contract (simple-vol), G7 AVWAP_INDIA.md lens (Opus,
  engine tensions documented). WAVE_H (Tier-1 chartsmaze independence): H1 calibration harness
  built; first run exposed date/universe alignment bugs -> H1.1 fix batch on Codex. WAVE_I:
  23-repo audit (4 Sonnet reviewers, 15 homework/8 useful) -> 5 adoptions specced (accuracy-
  weighted chair I2, FII/DII conditional I4, HAR-RV vol pillar I1, FinBERT sentiment I3,
  gated HMM confirm I5) + rejections logged. Commits 52294416, 4e8ec61f, 115b3c6e. 319 green.
  SOAK: 0 fail rows; tokens 07-09 doubled to ~81k-in (expected: 10x debate breadth, ~2-3c/night
  — watch for creep). Clean agent-night streak 3/5. Standing user directives captured: edge-
  first/nothing-off-limits; ChartsMaze/NSE-official industry mapping preferred; Codex = coder.
  NEXT: H1.1 result -> H2 ports; I2 chair weighting; G5 Pine ports; tonight's automated night.
- 2026-07-10 (cycles 34-38, SHIP-1): Loop protocol upgraded per user — Opus runs the ship-
  grade 4-lens review, Fable counter-reviews, one reconciliation exchange, SONNET executes.
  First review verdict: 3/10 — expectancy layer empty (product premise unproven), phantom
  run_card default, positions coach broken, near-miss debate theater, ML deferred. 18-item
  reconciled WORK_ORDER_SHIP1.md. EXECUTED same night: item 6 (soft-gate-only debate pool,
  hard-fails on watchlist w/ zero tokens), items 3+5 (no_op run_cards + STALE banner;
  deterministic brief, LLM path deleted), items 1+2 (E1 replay 285 sessions PERSISTED ->
  setup_expectancy, proof-with-n on cards/ledger). CRITICAL HONEST FINDING: passed cohorts
  -1.15/-2.49R avg, 9-20% hit vs refused flat-positive — BUT -2.49R impossible under stops
  => outcomes graded unmanaged T+10 holds; stop-exit/MFE/MAE audit batch launched before
  any gate-recalibration talk. Also: G5a Pine ports (7 indicators, line-cited tests) + G5b
  indicator block into debate prompts; Telegram linked (bot token+chat_id in config, dry-run
  test delivered); repo found PUBLIC — user asked to flip private (Pine sources + secrets
  hygiene; history verified clean of tokens); cloud plan = GitHub Actions nightly then
  Oracle free VM. Commits 79a53925 et al; 340 green. IN FLIGHT: outcome audit, item 4
  positions repair. NEXT: ML block (I13 LightGBM+SHAP, screener calibration, delivery% tag).
- 2026-07-10/11 (cycles 39-44, SHIP-1 COMPLETE): all 18 reconciled work-order items executed
  by Sonnet + verified by Fable in one continuous run. Highlights: E1 replay persisted (285
  sessions) -> honest NO-EDGE finding on gate-passed cohorts (93-100% stop-out, MFE never
  favorable; chair's persistent SKIPs vindicated); outcome methodology fixed to managed
  stop-exits (gap-through-stop honest, MFE/MAE); positions fully repaired (qty migration,
  advisor_notes coach persist); no_op run_cards; deterministic brief; soft-gate-only debate
  pool; LightGBM+SHAP live (AUC .544, hit 55.3% vs 44.8%, 8/10 folds — EXPERIMENTAL chip);
  screener calibration wired (honest-empty, fills nightly); delivery accum/dist tags;
  telegram watchlist section; funnel reconciles; mobile clean; deals pct-of-mcap; sector-
  downside EB-ridge (Brier .2057<.2133) RISK* col; HAR-RV (QLIKE .273 vs 1.299 decisive)
  vol_forecast; causal backfill verified 285 sessions HMM-ready; glossary all tabs.
  370 py + 25 js green. NEXT: Opus review round 2 (re-score vs 3/10), reconcile -> SHIP-2;
  gate-recalibration EVIDENCE experiments (stop-width/entry-timing/regime replays); HMM
  build; GitHub Actions nightly (blocked on user flipping repo private).
- 2026-07-11 (cycles 45-48, SHIP-2): Opus round-2 (4/10) blockers all fixed + verified:
  night coherence (run_card keyed by scan_date, one night one card; near-miss cards show
  failed gate+reason; brief counts split), dark chips lit (ml_direction was reading legacy
  empty watchlist + lightgbm in wrong interpreter — 10 scores live, P(up) .40-.52 agreeing
  with chair SKIPs; delivery flags 3555 symbols), TONIGHT'S CALL deterministic stance block
  (SIT_OUT tonight) on desk/debate/telegram opener. Opus round-3: 6/10 ("the desk now tells
  ONE story header-to-cards"); residuals same-cycle: funnel honest+monotonic (no_hit_drop
  853 captioned, sums reconcile), de-jargoned call lines, vol_forecast as-of/stale suffix,
  coach telemetry humanized. Fable live-verified: desk opens 07-09 w/ rendered SIT OUT call,
  mobile 375 clean, de-jargoned line rendering. 378 green. Commits ..b29e1b4f. BLOCKED ON
  USER: repo private flip (-> GitHub Actions nightly + telegram live send test). NEXT: round-4
  targets = telegram real send, HAR-RV nightly coverage, gate-recalibration evidence replays,
  HMM build on causal backfill, G5c chart drawer.
- 2026-07-10 (cycles 49-53, WAVE J): Opus designed the entry-quality wave; found LATENT BUG
  (breakout_age=None -> fresh-leg staleness dead in production; entries at un-crossed
  pivots = the 29% phantoms; zero compression precondition). J1 refusals + J2 variant
  harness (reproduction guard) + J6 shadow leg-age fix (zero behavior change) landed; 454
  green. J3/J4 counterfactual evidence: ALL H1-H6 FAIL the pre-registered bar at n=55 —
  honest negative logged. Directional signal: H3 buy-stop confirm (hit_1r 9->25%, MFE -0.80
  ->-0.07), H1 removed-cohort test passes, H1+H2+H3 bundle 42.9% hit_1r at n=7. VERDICT:
  direction plausible, sample starved. NEXT: J7 sample-expansion replay (persist counter-
  factual candidates beyond gate survivors -> 150-300/cell), NIFTYMIDSML400 backfill to
  2025-03 for H5, then re-run the bar. Also this cycle: I5 HMM (benched by own validation
  — 18.8% agreement, display-gated), G5c chart drawer live (marker-sort crash fixed),
  nightly NSE index ingest (chartsmaze market-indices CSV was silently screenshot-only).
  Tonight's automated evening night = first fully-integrated run.
- 2026-07-10 evening (cycles 54-62): TradeTM corpus CLOSED (all 120 files FULL/DUP/META;
  335+ nuggets incl W-series from 5 giant transcripts via Codex after session-limit hit).
  INDIA_PLAYBOOK + PLAYBOOK_TO_TOOL_MAP synthesized (TradeTM backbone). APPLIED: core lens
  first in every debate, EP/IPO lenses w/ backbone params + W-rules, coach-line bank, four-
  phase caption, choppy line, signal guide (HOW TO TRADE THIS step-by-step on cards).
  WAVE_M conformance audit (Opus): tool = ~30% executable / ~90% encoded; 11 tasks; replay
  guardrails honored. QC = two-reviewer panel now (Opus + Codex); Codex round 1 -> 7 fixes
  (mswing corruption = TEST FIXTURE LEAKED INTO PROD DB via no-path connect — purged 121
  rows + guard; lens cites; a11y; freshness stamp w/ build sha). Discovery iteration:
  definitive recall 2/12 post-K4.1-fix (GROWW 4 archetypes, PARAGMILK; RAIN in; NBIFIN
  negative control REFUSED); 10 misses = reversal-at-momentum-bottom structural cause ->
  prior-strength+correction+trigger redesign in flight. Model roster: DSv4-pro/GLM-5/
  Kimi-K2-thinking/Qwen3.5-plus + Qwen3-VL vision. MARKET bugs live-found (strip triple-
  NIFTY50 fallback, treemap drill name-mismatch) -> fix batch. 07-10 data update running.
  522 green. BLOCKED ON USER: repo private, WAVE_L risk sign-off.
- 2026-07-10 night (cycles 63-68): FIRST TRUE INTEGRATED NIGHT on same-day data (mirrors
  lagged; fetched direct from nsearchives — chip filed to make direct-NSE primary). All 26
  stages green: GROWW PASSED the gate (IPO Base) on today's tape — the stock whose refusal
  started the discovery investigation; tonights_call CAUTION w/ negative-base-rate paper-
  trade guidance (expectancy layer + stance working as designed); FOCUS top-3 incl
  Jewellery = GOLDIAM/SKYGOLD (user's own morning picks — theme layer sees what he sees);
  all 4 modern seats parsed (reasoning-client fix: answers were in message.reasoning;
  effort:low + 8k + fallback chain); telegram digest delivered. MARKET fixes verified live
  (MidSmallcap-led strip; drill works — empty sectors = extractor exports only ~12
  Capital-Goods industries daily, chip filed). Signal guide (HOW TO TRADE THIS) shipped.
  WAVE K7: recall 2/12 -> 5/12 (7/23 full set) via 180d reversal re-anchor + honest size
  control (~119/day); NBIFIN control holds; next constraint = pullback-archetype
  SPECIFICITY. Freshness stamp (data-as-of + build sha) live. 539 green. NEXT: dual-review
  wave-close (Opus+Codex), specificity iteration, M7/M9. Blocked on user: repo private,
  WAVE_L sign-off.

## STATE 2026-07-10 ~21:40 (cycle 69) — Round-4 wave-close DONE
- Dual review: Opus 6.5/10 (headline: GROWW card 4-verdict contradiction; guide used suggested_qty 439 vs sizer 0 — trust-critical); Codex 5/10 (stale API build, hmm/stock_hmm drift, IDEAFORGE bars stop 2026-05-18, focus 5-vs-13, sizer 0.25-prose-vs-0x).
- Executed + verified live (615d8cc6, pushed): PAPER ONLY banner when final_qty=0; guide sizer-authoritative w/ step-0 refusal; sizerRead(0) fixed; deterministic 0x line; post-19:00 hint; stock_hmm alias + stale labels; GROWW HMM honest (141 bars <150); focus persisted top-5; 3 swallowed excepts -> logged {available:false,reason}. 542 green +3 new tests.
- OPEN from reviews: vision paraphrased-dup (exact-dup dedup misses it); IDEAFORGE data feed stops 2026-05-18 (pipeline gap, diagnose in next data wave); HMM series 46-97d gaps.
- NEXT: pullback-archetype SPECIFICITY (recall binding constraint), M7 EOD strong-start/D2, M9 four-phase classifier. Blocked on user: repo-private, WAVE_L sign-off, schtasks.

## STATE 2026-07-10 ~23:05 (cycles 70-72) — K8 + baseline correction + M7
- K8 (72671a14): pullback D1-D3 quality gates + D4 leg-force ranking. Recall-neutral, crowd ~200->41-57/day pre-cap. PARAGMILK misses D1 by 0.004; TATAINVEST cap casualty (rank 38/57 on leg-force).
- BASELINE CORRECTED: K7's 5/12 was stale-data artifact — 07-04/05 full bhavcopy backfill fixed daily_prices to ground truth (CHENNPETRO close verified vs raw CSV). TRUE recall = 3/12 (INTELLECT, BSOFT, GROWW). LEARNINGS updated; 3/12 is the number to beat; re-score after any price backfill.
- Vision paraphrased-dup fixed at source (0cb1ac73): what_i_see/reason overlap>0.6 -> drop reason; overlap-coefficient backstop in API.
- M7 (fcec29d7): strong_start_ready (tight-prev-day gate per LENS_STRONG_START) + d2_ready (day-1 burst >=10%/circuit, branch a/b pre-classified, c open-resolved). morning_setups table; /api/desk/focus tomorrow_morning; MarketTab 9:07-9:30 panel; D2 signal-guide. Tonight: 3 d2_ready (PPAP, IONEXCHANG, MOBIKWIK), 41 strong-start capped to 12. 554 green.
- NOTE: executor claimed live-curl verification but API was serving old build — restarted on HEAD, verified for real. Reinforce: verify against live server build_sha.
- NEXT: M9 four-phase classifier + choppy brake; recall iteration vs honest 3/12 (CHENNPETRO/COALINDIA likely strong_start-archetype not pullback; TATAINVEST rank/cap). Blocked on user: repo-private, WAVE_L, schtasks.

## STATE 2026-07-11 ~00:15 (cycle 73) — K9 DONE
- K9: pullback_to_50ma archetype (corpus: TTM-H-III4, PLAYBOOK L249). Recall 3/12 -> 4/12 (CHENNPETRO caught, predicted). No regressions; NBIFIN holds (turnover Rs0.84cr < 3cr). TATAINVEST still cap-evicted (spec's "possible" didn't land). 573 green.
- Honest skips documented in WAVE_K9_RECALL_SPEC.md: PARAGMILK fails corpus's own up-vol>>down-vol; COALINDIA zero purple dots; EMSLIMITED knife; NCC 6-down-days; ZENTEC trio -> busted_reversal detector = K10 candidate.
- Open tension C2: bucket sizes 116-141/day vs 30-80 target (8 archetypes x cap-20) — needs Stage-2 union-trimming or target restatement, not threshold moves.
- NEXT: wave-close review round 5 (Opus+Codex) over M7/M9/K8/K9; K10 busted_reversal design; M-task PROPOSALS await user. Blocked on user: repo-private, WAVE_L, schtasks.

## STATE 2026-07-11 ~01:00 (cycle 74) — Round-5 wave-close DONE
- Reviews: Opus 7.0/10 (round-4 trust fix HOLDS; new finds: four-phase doctrinal inversion — Lack of Supply lumped into choppy; sizer cited refused-cohort +1.58R as "positive edge" on GROWW whose own cohort 0/29). Codex 5/10 (signal-guide ignored morning_setups; focus no-date path returned 13; midnight hint; 0x reasoning residue).
- Executed a53ff715 (pushed): choppy set = {Lack of Demand, Supply Domination}, Lack of Supply constructive line; deterministic sizer refusal string (no edge text at 0x); signal-guide routes morning_setups (D2/strong-start templates w/ real day1 numbers); focus top-5 both paths; morning panel prints trigger/stop numbers + ORB expansion; family_label (ipo_base) alongside internal family; midnight/weekend hint via is_trading_day (07-11 Sat verified non-trading); vision dup not reproducible live (no change, watch).
- 578 green. Executable-conformance est ~40% (Opus). Trajectory 3->4->6->6.5->7.0.
- NEXT: K10 busted_reversal design (ZENTEC trio, NCC), C2 bucket-size tension (Stage-2 union trim), M-task PROPOSALS await user. Weekend: no new data until Mon ~19:00. Blocked on user: repo-private, WAVE_L, schtasks.

## STATE 2026-07-11 ~04:00 (cycles 75-79) — V4 pivot + M2/M3 LIVE
- USER ORDERS (all captured in CONSTRAINT_METHOD_FIRST_IA.md): method-first IA rebuild (trader flow verbatim: scanners->shortlist->enter->manage->sell); debate stays visible; living LLM watchlist; screener builder + push-to-debate; THE FILTER IS THE DEFECT -> M2/M3 ordered live (recall label-gate overridden).
- M2/M3 SHIPPED (ca7cd3fa, pushed): discovery bucket feeds live pool (pool 1->11 for 07-10, +16 from bucket of 150); RS/nearness/regime = scored objections; tradability/risk/NO_TRADE stay hard; refusals all named (user names now die at fresh-leg "extended 8-20% over 21EMA" = honest don't-chase, visible in screener/watchlist). NBIFIN still refused (turnover floor). Screener API live (TODAYS_MOVERS catches IONEXCHANG/GODREJIND/MUTHOOTMF/EMSLIMITED); push-to-debate endpoint + DebateTab box live; agent_verdicts.source=user_pushed.
- Practitioner screeners extracted -> knowledge/PRACTITIONER_SCREENERS.md (27 screens, status per screen).
- WIREFRAMES_V4 (pushed): MARKET/SCANNERS/SHORTLIST/DEBATE/POSITIONS/JOURNAL + TRADE PLAN route; 16 Codex slices. Codex slice 1 (shell+MARKET) running as job b9ga7fv92.
- UX audit round ran earlier (Fable+Opus debate, merged top-10; HUDCO below-stop-says-HOLD BLOCKER + build-stamp + telemetry findings) — old-IA executor killed by session restart; correctness items (stop-breach T1) folded into V4 slices T14; stamp fix landed via ca7cd3fa.
- LOOP MODE (user): wireframe->Codex codes->UX QC + runnability->repeat until final. QC milestones at slice T6 + T16.
- Blocked on user: repo-private, WAVE_L, schtasks.
