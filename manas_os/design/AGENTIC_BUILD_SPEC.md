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
