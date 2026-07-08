# AGENTIC_HANDOFF — pick up the agentic-scanner build from here
# (For any fresh LLM/orchestrator taking over. Read THIS first, then the 4 files in §2.)

## 1. What is being built (one paragraph)
Manas OS pivoted (user decision 2026-07-08, after rating the old frontend 0/10) to an
LLM-agents trading desk on top of the existing deterministic engine: cascade filters
shortlist 10-20 NSE names → 2-3 free OpenRouter models debate them through five setup
lenses (Manas Arora Strong Start, EP, IPO base, high tight flag, PEAD) → a vision model
promotes/demotes off multi-timeframe chart PNGs → a sizer agent picks final names +
position multiplier (validated by risk/plan.py, the only math authority) → Telegram entry
signals → a journal-coach agent sends exit/management signals → agents self-train via MD
lesson files injected back into their prompts. UI = "living desk" (activity stream,
debate theater, agent track records). The user EMBRACES LLM latitude — improve the agents'
judgment with context; do not re-litigate the idea or strangle it with parameters.

## 2. The four control files (in read order)
1. `AGENT_LOOP.md` — the loop protocol you RUN: roles, model routing, waves A-F, the
   per-cycle procedure, DONE-TEST, and STATE (current position — trust STATE over memory).
2. `AGENTIC_BUILD_SPEC.md` — per-wave zero-judgment contracts (grows each cycle; write the
   next wave's spec there BEFORE launching its coder batch).
3. `AGENT_UI.md` — the UI contract for wave F (living desk). Screenshot-vs-contract,
   two-direction rule, light theme.
4. `AGENTIC_AUDIT.md` + `AGENTIC_WORKFLOW.md` — the user's architectural audit (Option 1:
   math generates → LLM filters; validation + outcome loops are the gaps that matter) and
   the record of the first agentic implementation (which had the LLM replacing the
   cascade + writing to refusals — wave A2 rewires exactly that).

## 3. Operating rules (hard-won; violating these is how trust was lost)
- **Roles**: orchestrator (you) specs + verifies, never bulk-codes. Codex codes (ONE batch
  at a time, --fresh, background). If Codex sits "queued" >20min twice or its credits die →
  same batch prompt to a Sonnet general-purpose subagent; note the switch in AGENT_LOOP
  STATE. Sonnet = grunt reads/extractions; Haiku = cheap bulk reads.
- **Verify yourself, every cycle**: pytest from repo root (never regress the baseline you
  measured at cycle start), exercise new stages against the real DB (dry-run), read actual
  artifacts (transcripts, PNGs, Telegram dry-run payloads). Executor self-reports and
  ticked checkboxes are claims, not facts. Silence/`ok` statuses can mask dead paths — the
  data pipeline was broken for days behind four stacked "ok"s (see LEARNINGS 2026-07-07/08).
- **Money math**: risk/plan.py is the single writer of entry/stop/target/qty. Agents
  output verdicts/conviction/narratives/multipliers — never prices or quantities.
- **Agent tables only**: agents write agent_verdicts + scan_agent_logs. NEVER refusals/
  candidates (keeps the gate analytics + near-miss studies clean).
- **Free models for testing**: query https://openrouter.ai/api/v1/models, filter :free,
  pick newest capable from different families + one free vision model. Ids in config.yaml
  only (gitignored — document keys in code comments).
- **Protected files**: scanner/gates.py, risk/plan.py, regime/governor.py,
  backtest/replay.py — orchestrator hand-edits only, with tests.
- **Commit discipline**: one commit per verified cycle, what+why message, push to
  `emergent`. Never commit config.yaml or data/.
- Python: C:\Users\satta\AppData\Local\Programs\Python\Python314\python.exe (312 fallback).
  Codex sandbox often can't run pytest/npm — it must say so plainly; you run them.

## 4. State of the underlying tool (what the agents stand on)
- Deterministic engine WORKS and is tested (~176+ tests green at handoff; measure fresh):
  refusal cascade (6 gates, named reasons), risk/plan.py (LOCKED stop caps, R:R floor,
  AGGRESSIVE default profile), regime governor (feed caps 8/4/2/0), ordinal ranking,
  refusal ledger, expectancy loop with shrinkage (setup_expectancy — inject its cells as
  base rates into agent prompts), PEAD study, exit engine (trail_plan/two_strike), flow
  stepper, telegram digest slice (armed_list, no live send), advisor module (guarded
  OpenRouter client — reuse its client/guard patterns for the new agents).
- Data pipeline: FIXED 2026-07-08 after four stacked breaks (button didn't fetch → girish
  mirror lags (use --source both) → ingest read a stale mirror dir → config.yaml override).
  Bhavcopy lives in repo-root data/bhavcopy. If coverage dates stick, check that chain
  first (LEARNINGS has the full postmortem).
- Old frontend: user verdict 0/10 — do NOT resume the wireframe rebuild; wave F replaces
  it with the living-desk UI.
- Useful background artifacts: full-history replay verdict may exist at
  <scratchpad>/replay_verdict.json (passed-vs-refused cohorts in R terms); near-miss
  per-gate interim verdict is in LEARNINGS (fresh-leg strongly vindicated).

## 5. Where the build stands
READ `AGENT_LOOP.md` STATE — it is updated every cycle and outranks anything here.
At handoff-writing time: cycle 1 in flight (Codex building A1/A2 agent tables + Option-1
rewiring; Sonnet distilling study/ + CHARTGYM into the five LENS_*.md files under
design/agents/). Next after that: verify per loop step 5 → spec B1/B2 (debate
orchestrator + chair merge) → cycles continue A→B→C→D→F→E per the wave list.

## 6. The user (how to work with them)
- Beginner trader, small account, aggressive-growth intent; wants hand-holding surfaces
  and plain English on every number.
- Burned by: agents looping without output, checkbox-done vs reality gaps, patchwork
  UI passes, token burn without shipped value. Lead every report with verified outcomes;
  one screenshot/artifact beats paragraphs; never claim done unverified.
- Standing instructions: don't challenge the LLM-agents direction — sharpen it; keep
  agent latitude (conviction/veto/sizing multiplier are theirs); "open to the volatile
  nature of the market" — lessons inform, never auto-tighten; one Codex at a time;
  free models for testing; light UI theme.
- Wants eventually: Sharpe per cohort, Markov regime models, and the lesson-file
  self-training loop as the compounding asset.
