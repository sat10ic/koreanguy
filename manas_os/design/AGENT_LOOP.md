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
