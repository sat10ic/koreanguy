# AGENTIC_BUILD_SPEC — per-wave contracts for AGENT_LOOP.md (grows each cycle)

## A1 — agent tables (no touching `refusals`)
```sql
CREATE TABLE IF NOT EXISTS agent_verdicts (
  scan_date TEXT NOT NULL, symbol TEXT NOT NULL, agent TEXT NOT NULL,  -- model id or 'chair'/'vision'/'sizer'
  verdict TEXT NOT NULL,           -- TAKE | SKIP | PROMOTE | DEMOTE
  conviction INTEGER,              -- 1-5
  rank INTEGER,
  lens_scores_json TEXT, bull_case TEXT, bear_case TEXT, reasoning TEXT,
  outcome_r REAL,                  -- backfilled at T+10 / close
  created_at TEXT DEFAULT (datetime('now')),
  PRIMARY KEY (scan_date, symbol, agent));
CREATE TABLE IF NOT EXISTS scan_agent_logs (
  log_id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_date TEXT, agent TEXT, model TEXT, prompt_sha TEXT,
  latency_ms INTEGER, tokens_in INTEGER, tokens_out INTEGER,
  parsed_ok INTEGER, validation TEXT, error TEXT,
  created_at TEXT DEFAULT (datetime('now')));
```
Ensure-schema helpers in the agents module; additive only.

## A2 — Option-1 wiring (cascade shortlists, agents judge on top)
Current state (verify by reading): a prior wave REPLACED the deterministic scan with an
LLM debate (`AGENTIC_WORKFLOW.md`; grep `scan_candidates_deterministic` to find it), with
deterministic only as network-failure fallback, and the LLM writing to `refusals`.
REWIRE to:
1. Deterministic cascade ALWAYS runs first and persists candidates/refusals exactly as
   before (it is the shortlist maker + math authority).
2. Shortlist for agents = top `agents.shortlist_size` (config, default 15) of the FULL
   ranked pre-governor pass list (not the governor-capped display list — agents see more
   than the feed shows).
3. The debate layer (existing single-call code, refactor into `manas_os/agents/debate.py`)
   consumes the shortlist and writes ONLY to agent_verdicts + scan_agent_logs. Delete its
   writes to refusals/candidates. Its entry/stop/target/qty outputs are DROPPED from the
   contract — plan numbers come from the candidates rows (risk/plan.py already computed
   them). Keep bull/bear/verdict/conviction.
4. Pipeline order: scan_candidates → agents_debate (new stage, failure-safe no-op without
   config key) → expectancy → ...
5. Frontend debate panel keeps working — repoint it to agent_verdicts data (an
   `agent_debate` field on the card payload or a small /api/agents/verdicts?date= endpoint,
   whichever is less code).
Tests: tables created; debate stage no-ops cleanly without key; with a MOCKED client the
verdicts persist and refusals table is untouched by the agent path (assert rowcount
unchanged); shortlist honors agents.shortlist_size.

## A3 — lens files (Sonnet/Haiku deliverable, not Codex)
Contract in AGENT_LOOP.md A3. Output dir `manas_os/design/agents/`. Each LENS file:
recognition markers (chart + volume + context), disqualifiers, entry/exit notes in the
source's own vocabulary, each rule cited to file+section. No invented rules.

## B1/B2, C1-C4, D1/D2 — spec'd in the next cycles after A lands (this file grows).

## Code-review findings on the A1/A2 batch (fix inside B1a/B1b — do not batch separately)
R1 (B1a) `debate._load_shortlist` reads scan_candidates top-N by rank — VERIFY it persists the
   FULL cascade pass list, not a governor-capped subset; if capped, widen persistence so agents
   see up to shortlist_size names beyond the display cap (A2 spec intent).
R2 (B1b) `_validate_payload` raises on ONE malformed item, discarding the model's entire
   response — change to skip-and-log the bad item, keep the valid ones; raise only if zero valid.
R3 (B1b) spec said retry once on bad JSON with the parse error appended — currently no retry.
   Add single retry per model. Also: tokens_in/out are word-count placeholders — read real usage
   from the OpenRouter response when the client exposes it, else keep placeholder and label it.

## Repo-research adoptions (2026-07-08, from direct reads of the reference repos)
AD1 (data layer, small batch alongside B-wave): loader registry with ordered free-source
    fallback chains behind one fetch protocol + a single OHLCV sanity guard that drops
    dirty bars at the boundary (Vibe-Trading agent/backtest/loaders/registry.py pattern).
    We half-have this (bhavcopy girish→tilak); formalize: one protocol, ordered sources,
    bad-bar filter, per-source health logged to pipeline_runs.
AD2 (B1/B2 restructure — supersedes the flat chair design): debate = analyst reports →
    adversarial bull/bear argument → RISK GATE → chair/portfolio merge (TradingAgents
    pattern, no LangGraph needed). Concretely: each model's single call still returns
    per-symbol verdicts, BUT the chair step becomes two stages: (a) debate summarizer
    (merge arguments, flag disagreements), (b) risk-gate pass that can strike names on
    stated risk grounds before ranking. Cleaner traceability than one merge blob.
AD3 (D2 lessons granularity): reflection = ONE PARAGRAPH per closed outcome, ticker-scoped,
    PLUS a cross-ticker digest; inject recent same-ticker + cross-ticker lessons into the
    next run's prompts (TradingAgents trading_memory.md + RakshaQuant loss-loop granularity).
AD4 (D2/F): emit run_card.json per nightly run — one canonical artifact: scan params,
    shortlist, verdicts, sized picks, outcomes-when-known, benchmark delta (Vibe-Trading).
    The desk feed + coach read THIS, not ad-hoc queries.
AD5 (F1): activity-stream event schema = worker states waiting/running/done/failed/blocked
    with heartbeats during long calls (Vibe-Trading swarm status schema) — don't invent one.
NOTES: NSETradeAgents deserves a second look at five-dimension setup scoring + hybrid ATR
trailing when tuning (wave E). TradingAgents' own docs warn LLM sampling variance makes
agent-in-loop backtests non-reproducible — treat agent-layer replay as indicative only;
deterministic layer remains the only backtestable claim (already our position).
AD6 (advisor/debate context pack, tiny): free India news feed via Google News RSS with
    India locale params (news.google.com/rss/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en)
    per shortlist symbol (RakshaQuant stock_discovery.py). Advisory context ONLY — headlines
    with timestamps into the context pack, never into backtests (look-ahead rule), never a
    gate input. Cache per run; skip silently on fetch failure.
AD7 (sizer/coach, small): net-of-costs R — simple configurable NSE cost stack
    (brokerage + STT/statutory bps + slippage bps, RakshaQuant costs.py approximation
    pattern) so coach/lessons report NET R, not gross. One helper, config-driven; keeps
    small-account realism in the agents' outcome feedback.
INDIA-DIVE VERDICT (NSETradeAgents + RakshaQuant read directly): both real-but-thin on
NSE mechanics — no bhavcopy/ASM/circuit/delivery handling in either; our deterministic
layer is already deeper than the reference repos'. The India edge stays OURS (delivery %,
ASM gate, circuit feasibility, pump signature); the repos' value was architecture patterns
(AD1-AD5), not India hacks.
AD8 (B1 debate prompt + validation, small): ANTI-ANCHORING rule — composite scores are
    computed deterministically in Python and shown to the LLM; the LLM never invents its
    own composite number (NSETradeAgents 5-axis scoring design). Our debate JSON already
    limits agents to verdict/conviction/rank — extend validation to reject any numeric
    "score" fields the model volunteers.
AD9 (C3 sizer context, small): India VIX as a sizer context field (^INDIAVIX via existing
    price sources) with the reference tiering 100/85/65/50% size bands at VIX <15/15-20/
    20-25/>25 (india-trade-cli). CONTEXT for the sizer's multiplier choice, not a hard
    gate — the sizer cites it in reasoning.
AD10 (coach/exit, wave E tuning): catastrophe stop SEPARATE from the trail — hard exit at
    -15% from position peak regardless of trail state, alongside the existing trail_plan
    phases (NSETradeAgents hybrid: 2xATR trail activating after +12%, floor/cap). Compare
    against current trail on replay before adopting numbers.
AD11 (debate/sizer system prompts, tiny): a fixed "Indian market structure" primer block
    in agent prompts — T+1 delivery settlement, weekly index expiry Thursdays, India VIX
    bands, STT/GST/brokerage drag on small accounts, NSE hours incl. pre-open
    (india-trade-cli prompts.py pattern). Static text, versioned in the repo.

## B1a — debate context-pack builder + multi-model client wiring (SMALL batch)
File: manas_os/agents/context_pack.py (NEW). One function
`build_pack(conn, scan_date, shortlist) -> dict` producing the debate context:
- per-symbol compact block (exists in debate._user_prompt — MOVE it here, extend with):
  regime + regime_age_days (count consecutive regime_snapshots with same market_mode),
  base rates from setup_expectancy via expectancy.chip_for (family x regime cells with n),
  50-day weekly-close summary (anti recency-overfit: ~10 weekly closes from daily_prices),
  India VIX latest if present in index price tables (AD9; absent -> omit, never fake).
- deterministic composite scores shown, LLM never invents its own (AD8).
- the LENS files' text (design/agents/LENS_*.md) concatenated once at pack level (not per
  symbol), and the India-structure primer block (AD11) as a static string constant.
- lesson digest slot: reads design/agents/lessons/_digest.md if it exists, else omits (D2
  will populate it later).
R1 check folded in: confirm scan_candidates persists the full cascade pass list (read
scanner/candidates.py persist path); if the governor caps what lands in scan_candidates,
widen persistence to the full pass list (agents see beyond the display cap).
debate.py: replace _user_prompt internals with build_pack; keep everything else untouched.
Tests: pack contains regime_age_days + base-rate cells with n; weekly summary has <=11
points all dated <= scan_date (look-ahead guard); lens text present once; no invented
fields when tables empty (honest omission).

## B1b — debate call hardening (SMALL batch; debate.py only + its tests)
1. R2: _validate_payload skips-and-logs malformed items (bad verdict/conviction) instead of
   raising away the model's whole response; raise only if ZERO valid items survive. Skipped
   items noted in the scan_agent_logs validation field ("skipped=N: SYMA(bad verdict),...").
2. R3: retry ONCE per model on JSON parse/validation failure, appending the exact error to
   the retry user message ("Your previous response failed: <err>. Return ONLY the JSON
   array, no markdown."); cap 1 retry; both attempts logged separately.
3. Real token usage: OpenRouterClient response includes usage tokens if the client returns
   them — extend client.chat to also return usage dict when present; scan_agent_logs gets
   real prompt/completion tokens, falling back to word-count with validation note
   "tokens=approx" when absent.
4. AD8 double-check: validation rejects/strips volunteered numeric composite score fields.
Tests: mocked client returning (a) one bad item among good ones -> good persisted, bad
logged; (b) garbage then valid JSON on retry -> persisted, 2 log rows; (c) garbage twice ->
fail row, no verdicts; (d) usage dict present -> real token counts in log row.

## B2 — two-stage chair merge (SMALL batch; new manas_os/agents/chair.py + tests)
After all model calls land in agent_verdicts for a scan_date, chair.run(conn, scan_date):
STAGE 1 — summarize/aggregate (pure Python, no LLM): per symbol across model rows: mean
  conviction, verdict split (e.g. 2 TAKE / 1 SKIP), rank aggregate (mean of ranks, missing
  rank = worst+1), disagreement flag when conviction spread >= 3 OR verdicts split; carry
  each model's bull/bear intact (no blending of text).
STAGE 2 — risk-gate strike pass (ONE LLM call, chair model = agents.chair_model or first
  agents.models entry): input = stage-1 aggregate + each symbol's bear cases + plan numbers
  + portfolio heat + governor law; output JSON per symbol {strike: bool, strike_reason} —
  it may STRIKE names on stated risk grounds only (concentration, correlated exposure,
  event risk named in bear cases); it cannot reorder, cannot change convictions, cannot
  add names. Struck names keep their rows, get chair verdict SKIP.
Persist ONE chair row per symbol to agent_verdicts (agent='chair'): verdict TAKE/SKIP
  (struck -> SKIP), conviction = round(mean), rank = final rank after aggregation (struck
  names ranked last), reasoning = "models 2T/1S, spread 2; struck: <reason>" style,
  lens_scores_json = {"verdict_split": "...", "conviction_spread": N, "disagreement": bool}.
Failure-safe: LLM stage failing -> stage-1 aggregate persists WITHOUT strikes, pipeline row
  status 'partial' (never lose the aggregation because the risk pass died).
Pipeline: chair runs inside agents_debate stage after the model loop (same stage, no new
  cli entry). Tests (mocked): aggregation math hand-computed; disagreement flag on 5v2;
  strike -> SKIP + reason persisted; LLM failure -> partial with aggregate rows.
