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
B1 [ ] Debate orchestrator `manas_os/agents/debate.py`: ONE call per model (2-3 models),
      ALL shortlist names in the prompt (joint comparative ranking beats per-symbol calls),
      each model argues every lens, returns structured JSON: per-symbol {lens_scores,
      bull_case, bear_case, verdict TAKE/SKIP, conviction 1-5}. Context pack per symbol:
      compressed technicals (trend, EMA alignment, dist-from-50EMA, volume trend, stage),
      fundamentals, regime + regime_age_days, base rates from setup_expectancy, and the
      last-N lesson digest (wave D). Retry once on bad JSON.
B2 [ ] Chair merge: rank-aggregate the 2-3 models' verdicts (mean conviction, disagreement
      flagged as its own signal — a 5/1 split is information), persist to agent_verdicts.
**C. Vision + sizing + signals**
C1 [ ] Chart renderer: headless PNGs per finalist (daily ~120 bars, weekly ~2yr) via
      mplfinance/plotly from daily_prices — saved under data/agent_charts/{date}/{sym}_{tf}.png.
C2 [ ] Vision agent: send both timeframes per finalist to the vision model with the
      relevant LENS file; returns promote/demote + what it sees (base quality, pivot,
      volume signature). Adjusts chair ranking (bounded: ±2 ranks, veto allowed with
      stated reason).
C3 [ ] Sizer agent: input = final list, governor law, portfolio heat, user risk appetite
      (config `agents.risk_appetite: aggressive`), expectancy base rates. Output = picks
      + size as a MULTIPLIER 0.25x-1.25x of the risk/plan.py base size + reasoning.
      risk/plan.py validates the resulting qty (the only arithmetic authority); sizer
      chooses within the validated envelope — latitude without hallucinated math.
C4 [ ] Telegram entry signal: nightly message per pick (name, lens, conviction, plan
      numbers from risk/plan, sizer multiplier + why, top bear risk). Reuse
      telegram_engine armed_list plumbing; dry-run mode until user OKs live.
**D. Journal coach + self-training**
D1 [ ] Coach agent: daily pass over open positions (trail_plan/two_strike outputs + bars +
      original thesis from agent_verdicts) → Telegram management/exit signals with the
      original bull case quoted ("your thesis was X — it broke/held because Y").
D2 [ ] Lesson loop: when a position closes or a T+10 outcome lands for an agent TAKE:
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

## STATE (update every cycle)
- 2026-07-08: Loop created. Cycle 1: A3 DONE + verified (5 LENS files under
  design/agents/; citations spot-checked verbatim vs 6 Manas Entry.md. Coverage:
  StrongStart/EP STRONG, IPO strong-but-single-source). PEAD rewritten STRONG from
  design/Feedback/ research briefs + own T2.2 backtest in a separate measured-on-our-
  data block (user pointed at the Feedback folder); HTF enriched with evidence-tier
  verdict (ranked weakest setup, 7/7 — smaller sizing recommended); both still flag
  uncited gaps as NEEDS SOURCE instead of padding. A1/A2 DONE + verified
  (Codex, 13m): agent_verdicts + scan_agent_logs tables live; deterministic cascade
  restored as primary; agents_debate additive stage after scan_candidates, no-ops with
  'skip' pipeline row when config absent (exercised on real DB), refusals untouched
  (n=165,183 before==after); 217 tests green (baseline 213), build clean. NEXT (cycle 2,
  SMALL batches per the new rule): B1a OpenRouter multi-model client + context-pack
  builder → B1b debate call + JSON parse per model → B2 chair merge.
