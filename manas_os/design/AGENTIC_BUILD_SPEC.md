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

## C1 — chart renderer (SMALL batch; new manas_os/agents/charts.py + tests)
mplfinance is INSTALLED (0.12.10b0) under the main interpreter. render_charts(conn,
scan_date, symbols) -> dict[symbol, {daily: path, weekly: path}]:
- daily: last ~120 daily bars from daily_prices, candlestick + volume panel + EMA 10/21/50
  overlays, tight_layout, savefig PNG width~1200px.
- weekly: ~2 years resampled to W-FRI ohlc (pandas resample on the daily frame), candles +
  volume, EMA 10/30 overlays.
- Output: data/agent_charts/{scan_date}/{SYMBOL}_daily.png / _weekly.png (mkdir parents;
  overwrite ok — idempotent). Return only files actually written; symbol with <30 daily
  bars -> skipped with a note in the return dict (never a crashed run).
- matplotlib Agg backend explicitly (headless, no display).
- No LLM calls here; pure rendering. Not yet wired into the pipeline stage (C2 wires it).
Tests (manas_os/tests/test_agent_charts.py): fixture symbol via insert_price_ramp ->
both PNGs exist and are >5KB; thin symbol (10 bars) -> skipped note, no file, no raise;
weekly resample has <=110 candles for 2y.

## C2 — vision agent (SMALL batch; new manas_os/agents/vision.py + tests, minimal debate.py wiring)
vision.run(conn, scan_date, finalists) after chair inside the agents_debate stage:
- finalists = chair TAKE rows ordered by rank, capped at agents.vision_top_n (default 8).
- Render via charts.render_charts (call it here — this is the pipeline wiring for C1).
- ONE call per finalist to the vision model (agents.vision_model config; free vision model
  chosen at test time from the OpenRouter live list): messages with BOTH PNGs base64
  image_url parts + text = the relevant LENS file for that symbol's setup_family + the AD8
  anti-anchoring note. Output JSON {action: promote|demote|veto|hold, magnitude: 1-2 (for
  promote/demote), what_i_see: <=3 sentences, reason}.
- Apply bounded: rank adjustment clamped to +-2; veto -> chair verdict flipped to SKIP with
  vision reason appended; persist agent='vision' rows (verdict PROMOTE/DEMOTE/SKIP/HOLD,
  reasoning = what_i_see + reason); chair rows updated with final ranks.
- Failure-safe per finalist: one vision call failing logs + leaves that name's rank alone;
  vision model unset -> stage skips silently with pipeline note.
Tests (mocked client): promote +1 reorders correctly and clamps at +-2; veto flips chair
verdict to SKIP with reason; per-finalist failure leaves rank untouched; unset model no-ops.

## C3 — sizer agent (SMALL batch; new manas_os/agents/sizer.py + tests, minimal debate.py wiring)
sizer.run(conn, scan_date, client=None) after vision inside agents_debate stage:
- Input picks: chair rows with verdict TAKE after vision, ordered by final rank.
- ONE LLM call (agents.sizer_model or first agents.models): context = per-pick plan numbers
  from scan_candidates (entry/stop/rr/suggested_qty — risk/plan authority), governor law
  dict, /portfolio heat numbers (open_risk_pct, cap), agents.risk_appetite config
  (default 'aggressive'), expectancy base rates per pick, India VIX + AD9 tier bands if
  available, AD7 note: "report thinking in NET terms — costs drag small accounts", the AD11
  primer, lesson digest slot. Output JSON per pick {take: bool, multiplier: 0.25-1.25,
  reasoning <=3 sentences}.
- Validation: multiplier clamped [0.25, 1.25]; final_qty = floor(suggested_qty * multiplier)
  re-validated by risk_plan.validate (entry/stop/mm from the candidate row; regime; profile)
  — validate() failing -> multiplier stepped down 0.25 at a time until pass or 0.25 floor
  (log each step); take=false -> multiplier 0, verdict SKIP.
- Persist agent='sizer' rows: verdict TAKE/SKIP, conviction=None, rank=pick order,
  lens_scores_json={"multiplier": m, "final_qty": q, "validated": true}, reasoning.
- Failure-safe: LLM failure -> sizer skips (picks stay unsized; pipeline row 'partial').
Tests (mocked): multiplier clamp; validate-fail steps down until pass (fixture with heat
near cap); take=false persists SKIP; LLM failure -> partial, no sizer rows.

## C4 — telegram entry signal, DRY-RUN default (SMALL batch; new manas_os/agents/signals.py + tests)
signals.run(conn, scan_date, run_date) as the LAST step inside agents_debate stage:
- Picks = sizer rows with verdict TAKE (lens_scores_json.multiplier/final_qty), joined to
  their chair row (conviction, disagreement flag), scan_candidates row (entry/stop/rr —
  the plan numbers), and best bear_case (highest-conviction model's bear text).
- Render ONE message per pick (plain text, no rupee glyph in console logs): symbol, setup
  family + lens tag, chair conviction + verdict split, plan entry/stop/RR/final_qty,
  sizer multiplier + one-line why, "top risk:" bear line, and the fixed suffix
  "signal — manual execution only; not advice".
- DRY-RUN default: agents.telegram_live (default false) — when false, messages are
  PERSISTED to a new table agent_signals(scan_date, symbol, channel, message, sent,
  created_at, PRIMARY KEY(scan_date, symbol, channel)) with sent=0 and NOT transmitted.
  When true, send via the existing alerts/telegram_engine transport (reuse its bot-token
  config + send helper if one exists; else stub send_telegram(message) in signals.py
  reading telegram.bot_token/chat_id from config) and set sent=1 on success.
- Failure-safe: send failures log + leave sent=0; no crash; pipeline detail notes count.
Tests (mocked): dry-run persists rendered messages with sent=0 and correct plan numbers
from the candidates row; live=true with a mocked transport marks sent=1; send failure
keeps sent=0 without raising; message contains the manual-execution suffix.

## D1 — journal coach agent (SMALL batch; new manas_os/agents/coach.py + tests)
coach.run(conn, run_date) as a NEW pipeline stage 'agents_coach' registered after
agents_debate in cli (separate stage — positions exist even when no scan ran):
- For each OPEN journal trade (exit IS NULL): gather the deterministic read (existing
  eod_detectors.trail_plan + two_strike on bars, exactly like /api/watchlist coach field),
  the ORIGINAL THESIS = that symbol's chair/model rows from agent_verdicts near the trade
  date (bull_case + conviction; absent for pre-agent trades -> note "no agent thesis"),
  and current price context (close, open R).
- ONE LLM call for ALL open positions (agents.coach_model or first agents.models): input =
  per-position {deterministic verdict/phase/action/trail_stop/fired rules, original thesis,
  r now} + AD11 primer + AD7 net-of-costs note. Output JSON per position {stance:
  agree|urgent|note, message <=3 sentences quoting the thesis ("your thesis was X — it
  held/broke because Y")}. The COACH NEVER overrides the deterministic verdict — it
  narrates it (one-writer: trail_plan/two_strike own the action).
- Persist to agent_signals (channel='coach', scan_date=run_date, symbol): message =
  deterministic action line + the coach narrative + manual-execution suffix; dry-run/live
  same as C4 via the shared sender. urgent stance (two_strike exit_now) sends even in
  digest-quiet modes — exit alerts never suppressed (LOCKED rule).
- Failure-safe: LLM failure -> messages still persist with ONLY the deterministic action
  line (coach narrative absent) — the exit signal must never depend on an LLM call.
- No open positions -> clean skip row.
Tests (mocked): open position + mocked LLM -> coach message quotes thesis + suffix;
LLM failure -> deterministic-only message still persisted (the critical test);
exit_now position -> channel row flagged urgent; no positions -> skip.

## D2 — lesson loop (SMALL batch; new manas_os/agents/lessons.py + tests)
lessons.run(conn, run_date) as final step inside agents_coach stage (same stage — memory
work rides with the coach):
1. OUTCOME BACKFILL: for agent_verdicts rows (agent='chair') with outcome_r IS NULL whose
   scan_date is >=10 trading sessions old: compute T+10 forward R from daily_prices using
   the candidate row's entry/stop (fill-checked: high must touch entry first, else outcome
   'never_triggered' -> outcome_r stays NULL, reasoning appended '[never triggered]').
   Update outcome_r on ALL that symbol's agent rows (chair + models + vision + sizer).
2. LESSON FILES (AD3): for each newly-backfilled chair TAKE (or closed journal trade with
   agent thesis): ONE LLM call per lesson -> manas_os/design/agents/lessons/{scan_date}_
   {SYM}.md — one paragraph, ticker-scoped: what the models said (quote conviction/split),
   what happened (R path summary computed in Python and given to the LLM — never ask the
   LLM for numbers), why right/wrong, tagged one of: clean-hit | clean-miss |
   right-process-loss (GOOD process, market noise) | wrong-process-win (LUCK, flag it).
   LLM failure -> a deterministic stub lesson (numbers only, no narrative) still written.
3. DIGEST: regenerate lessons/_digest.md = last 20 lesson files compressed to <=15 lines
   total (one LLM call; failure -> keep previous digest). context_pack already injects it.
Tests (mocked LLM): backfill computes hand-checked R + never-triggered case; lesson file
written with tag; LLM failure -> stub lesson still written; digest regenerates; outcome_r
propagates to all agent rows for the symbol.

## E4+E5 — nightly reliability pair (SMALL batch; context_pack.py + debate.py only)
E4 lens-injection trim (first live night: 43k chars of lens text likely caused hy3's JSON
truncation): context_pack build_pack gains a families param (the distinct setup_family
values present in the shortlist); lens_notes includes ONLY the LENS files relevant to
those families (map: catalyst->EP+PEAD+STRONG_START, base/pattern->STRONG_START+HTF,
ipo/ipo_base->IPO+STRONG_START; unknown->STRONG_START) — typical night drops from 5 files
to 2-3. Keep full-set behavior behind agents.full_lens_notes: true (default false).
E5 free-tier backoff: in debate.run's model loop, sleep agents.call_gap_s (default 15)
between MODEL calls (not before the first); on HTTP 429 specifically, one extra retry
after agents.rate_limit_backoff_s (default 60) IN ADDITION to the existing bad-JSON retry
(429 retry does not consume the JSON retry). Both sleeps skipped when client is injected
(tests stay fast).
Tests: pack for a catalyst-only shortlist contains EP text but not HTF; full_lens_notes
true restores all; 429-then-success mock persists verdicts with 2 log rows; injected
client causes no sleeps (time-mock or elapsed assertion).

## AD4 — run_card (SMALL batch; new manas_os/agents/run_card.py + tests)
run_card.write(conn, run_date) as the FINAL step of agents_coach stage: one JSON file
data/run_cards/{run_date}.json (dir gitignored like agent_charts) — the canonical artifact
of the night: {run_date, scan_date, regime: {mode, age_days}, pipeline: [stage/status/
duration from pipeline_runs for run_date], shortlist: [symbol/rank/family/plan numbers],
debate: [per model: verdicts count, parsed_ok, tokens], chair: [symbol/verdict/conviction/
struck+reason], vision: [...], sizer: [...], signals: [channel/symbol/sent], coach:
[symbol/action/urgent], lessons_written: [...], errors: [...]}. All read from existing
tables — zero new computation, zero LLM. Idempotent overwrite. Also expose
GET /api/desk/run-card?date= (append at END of api/app.py) returning the file's JSON or
{available:false}. Tests: card written with expected top-level keys from a seeded night
(reuse existing mocked fixtures); endpoint 200 + available:false path.

## E6 — chair anti-double-count (orchestrator-applied prompt/spec change)
Chair stage-2 input gains the per-symbol GATE EVIDENCE summary (gates passed + the
one-opinion/grade-cap notes already in the candidate row) with instruction: "The
deterministic gate already priced these risks (grade caps, evidence chips). Strike ONLY
on risks NOT already reflected there: portfolio concentration, correlated exposure across
picks, or event risk named in bear cases. Do not strike for a risk the gate already
graded." Test: chair prompt contains the gate summary; a mocked strike citing an
already-graded risk still persists (we log, we don't block the model) but the prompt
discourages it — behavioral tuning measured via the ledger over nights, not hard-coded.

## F0 — desk backend prerequisites (SMALL batch; closes DESK_WIREFRAMES BACKEND-GAPs 1-5)
All appended at END of api/app.py unless noted; zero UI.
G1 MBI/XP into run_card.regime: extend run_card.write to also read the latest
   regime_snapshots row (xp_value, mbi_day_color, r4p5/r10/r20/r50) -> run_card.regime
   gains {xp, mbi_day_color, ratios}.
G2 morning_brief: at run_card.write time, ONE LLM call (agents.brief_model or first model)
   composing <=4 plain sentences from the card's own numbers (handed to it — never asked
   to compute); stored as run_card.morning_brief; LLM failure -> deterministic fallback
   string built from counts ("Reviewed N names, chair took M..."); never blocks the card.
G3 GET /api/desk/chart?date=&symbol=&tf=daily|weekly -> serves the PNG from
   data/agent_charts (FileResponse, 404-safe JSON when absent).
G4 GET /api/desk/track-record -> aggregate from agent_verdicts where outcome_r NOT NULL:
   per (agent, lens?) fall back to per agent x setup_family via the chair rows' symbols'
   families: {agent, family, n, hit_rate (outcome_r>=1), avg_r}. Thin cells n<5 flagged.
G5 GET /api/desk/lessons?limit= -> list lessons/*.md (filename, tag parsed from content,
   first line) + the _digest.md text.
Tests: run_card contains xp/mbi + morning_brief (mocked LLM + fallback path); chart route
serves a real fixture PNG + 404 path; track-record math hand-checked on seeded outcomes;
lessons endpoint lists fixture files.

## AUDIT-1 FIXES (independent Sonnet audit 2026-07-09, orchestrator-verified; ONE batch)
AU1 CRITICAL agents/debate.py+chair.py+vision.py+sizer.py: every INSERT OR REPLACE INTO
    agent_verdicts nulls outcome_r/created_at on a same-night rerun (REPLACE = delete+
    reinsert). Convert ALL agent_verdicts writes to ON CONFLICT(scan_date,symbol,agent)
    DO UPDATE preserving outcome_r (COALESCE(excluded.outcome_r, agent_verdicts.outcome_r))
    and created_at. Add the missing same-date-rerun idempotency test across
    debate->chair->vision->sizer->lessons (backfilled outcome_r survives a rerun).
AU2 HIGH lessons.py _write_lesson: direct write_text -> tmp+rename atomic (match the
    digest's existing pattern) so a mid-write crash can't feed a truncated file to the
    digest LLM.
AU3 HIGH total-outage night: when all models fail (rows==0), chair/vision/sizer/signals
    skip AND no run_card exists unless coach had positions. Make run_card.write
    unconditional at the end of agents_coach stage (even when coach skips) and ensure the
    card records the debate-stage failure honestly (errors list from pipeline_runs).
AU4 MED chair.py _validate_strikes: raises on first malformed item, nuking the whole
    strike pass — apply R2 skip-and-log semantics (skip bad items, keep valid, raise only
    if zero valid AND items were present).
AU5 MED sizer floor-exhaustion: add the missing test (step-down to 0.25 still failing ->
    SKIP persisted with a non-empty reason).
AU6 MED consolidate duplicated helpers (_load_env_file/_api_key/_models/ensure_schema/
    _chat unwrap) into manas_os/agents/_shared.py; all agent modules import from it
    (mechanical; no behavior change; tests stay green).
AU7 LOW signals.py/coach.py depend on telegram_engine._telegram_sender (private name) —
    add a public get_sender() in telegram_engine and use it.
AU8 LOW add tests: chair.aggregate rank ties (two models, tied ranks), coach with 2 open
    positions in one call.

## F1 — greenfield desk app: shell + DESK tab (contract: DESK_WIREFRAMES.md shell + §1)
NEW app manas_os/desk/ (Vite+React, own package.json, port 5174; `npm create vite` layout;
fresh minimal tokens in one desk/src/tokens.css — light theme, mono for numbers, sans for
prose; ZERO imports from manas_os/frontend/**). Also ONE new backend endpoint (append END
of api/app.py): GET /api/desk/feed?date= -> ordered events for the activity stream built
from scan_agent_logs + pipeline_runs for that run_date: [{ts, actor (stage or agent id),
state per AD5 (done|failed|running), line (one-sentence render of the row), expand:
{...raw row}}] — server-composed lines, no client derivation.
Build ONLY per the wireframe blocks:
- GLOBAL SHELL: header (MANAS DESK, date scrubber driving ?date=, regime chip mode+age +
  MBI day-color + XP from run-card endpoint, DRY-RUN/LIVE badge from run-card or config
  surface), 4-tab nav (DEBATE/POSITIONS/LEDGER as placeholder panes saying "wave F2-F4"),
  stale banner per wireframe rule.
- DESK tab: morning-brief block (run_card.morning_brief), regime strip (MBI ratios + XP,
  rounded display), activity stream rows with expand, degraded-night variant (errors from
  run_card rendered as failed rows — must look intentional), empty state.
Done-test (orchestrator): npm run dev on 5174; two-direction screenshot-vs-DESK_WIREFRAMES
audit of shell + DESK with real run-card data; zero old-frontend imports (grep).
Tests: backend test for /api/desk/feed (seeded logs -> ordered events, honest empty).

## F1 ADDENDUM (2026-07-09): user-authored visual spec
'DESIGN_SPEC - desk.md' is the styling law for manas_os/desk: implement its color palette
(#0a0a0a bg, #141414 surface, #00d4ff/#b366ff/#00ff66 accents, #ff4444/#ffaa00 states),
typography table (Helvetica + mono data values, sizes/weights as tabled), 56px header,
compact density, hover/tooltip/expand interactions per its component library.
tokens.css implements the palette/typography verbatim. The F1 done-test now checks BOTH
DESK_WIREFRAMES layout AND this spec's styling.

## F2 — DEBATE theater tab (contract: DESK_WIREFRAMES.md §2 + DESIGN_SPEC components)
New manas_os/desk/src/DebateTab.jsx (replaces the placeholder pane). Data: run-card (chair/
vision/sizer arrays + shortlist plans), agent_verdicts via a thin new GET /api/desk/debate?
date= (append END api/app.py): per symbol {chair row, model rows (bull/bear/conviction),
vision row, sizer row, plan numbers from scan_candidates, base_rate via expectancy.chip_for,
track_record chips from the /api/desk/track-record aggregate}. Blocks per wireframe §2:
candidate header (symbol, family lens tag, chair verdict, conviction dots per model with
disagreement gap), BULL|BEAR columns attributed per model (purple agent chips), vision strip
(PNGs via /api/desk/chart + stamped verdict), plan block labeled "math: engine", sizer line
(multiplier + reasoning), footer (base rate + per-model track chips). Zero-TAKE night state
("the desk sat out") listing struck names + reasons. Empty state. Styling per DESIGN_SPEC
(conviction dots cyan/dim, disagreement gap #ffaa00, veto #ff4444).
Tests: backend /api/desk/debate test (seeded night -> shaped payload; empty honest).
Done-test (orchestrator): browser two-direction vs §2 with the real 2026-07-07 night data.

## F3 — POSITIONS tab (contract: DESK_WIREFRAMES.md §3 + DESIGN_SPEC components)
New manas_os/desk/src/PositionsTab.jsx (replaces placeholder). Thin backend GET
/api/desk/positions?date= (append END api/app.py): open journal trades + per-position
{deterministic read (trail_plan phase/action/trail_stop, two_strike fired/exit_now),
open R + R-path series (per-session R from entry using daily closes — computed server-side),
original thesis (agent_verdicts chair/model rows near trade date; honest 'no agent thesis'),
latest coach message from agent_signals channel='coach', urgent flag}. Blocks per §3:
lifecycle card (R-path sparkline with phase bands, trail line, coach headline, quoted
ORIGINAL THESIS block, urgent/exit-overdue variant in #ff4444), Telegram mirror strip
(coach signals with sent status), empty state. Sparkline = inline SVG polyline (no chart
lib). PROMPT-REV rider (small, agents/sizer.py context): when base_rates is no_data, hand
the string "no base rates available" instead of the raw dict (sizer echoed garbage).
Tests: /api/desk/positions (seeded open trade -> shape incl. R-path all <= date; empty
honest). npm build + pytest (baseline 282).
