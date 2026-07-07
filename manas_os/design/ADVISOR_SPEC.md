# ADVISOR — LLM second-opinion layer via OpenRouter (spec)

Role: an ADVISOR, never an engine. It reads what the deterministic system already decided
(regime, cards, refusals, plans, positions, heat) plus raw market structure (gaps, drawdowns,
breadth trend, upcoming events) and writes short OPINIONS. It cannot gate, rank, size, stop,
or alert-push. One-writer rule intact: every number on screen still comes from the engines;
the advisor only produces labeled text. (Binding rationale: VIZ_BRAINSTORM.md Part 2 —
"the LLM may generate text, suggestions, and drafts; never a number that ranks, sizes,
gates, or exits.")

## Module layout (new, isolated)
```
manas_os/advisor/
  __init__.py
  client.py     # OpenRouter HTTP client (stdlib urllib or httpx if already a dep)
  context.py    # builds the context pack — READS existing tables/payload builders only
  advisor.py    # pipeline stage: run(conn, run_date) -> writes advisor_notes; never raises
  guard.py      # output guard (adopt the numeric+phrase filter pattern from legacy/scripts/analyst.py — adopt, never import)
```

## Config (config.yaml — never committed; keys under `advisor:`)
```yaml
advisor:
  enabled: true
  api_key: "sk-or-..."          # OpenRouter key
  model: "deepseek/deepseek-chat"   # user-swappable; any OpenRouter model id
  max_tokens: 1200
  daily_budget_calls: 3         # hard cap: nightly digest (1) + on-demand (2)
```
Missing key or enabled:false → stage no-ops with a pipeline_runs "skipped" row. NEVER a crash.

## Context pack (context.py — assembled ONLY from existing single-writer payloads)
One JSON blob, ~3-4k tokens:
- regime: latest regime_snapshot row + governor(mode) law dict
- breadth trend: last 10 breadth_daily rows (pct_above_20dma, advances/declines, up/down-4%)
- cards: today's governor-capped candidates (symbol, family, rank, gates evidence, plan
  entry/stop/rr/qty, expectancy chip)
- refusals: top 10 near-misses (symbol, failed_gate, reason)
- positions: open journal trades + coach verdict (phase, r, trail_stop, exit_now, fired[])
- heat: /api/portfolio/heat dict
- structure events (computed in context.py from daily_prices, display-only arithmetic):
  index gap today (open vs prev close, NIFTY proxy), any card/position that gapped >2%,
  any position in >1R drawdown from peak open-R, distribution-day count last 5 sessions
- events: next-5-session disclosures for held/card symbols from the disclosures table
  (kind='corporate-announcement' etc). NOTE: a true earnings CALENDAR (future dates) is NOT
  on disk today — if absent, the advisor flags only what disclosures/data show; do not fake.

## The call (advisor.py, nightly after expectancy stage in run-eod)
System prompt (fixed, in code): "You are a second-opinion advisor for a rules-based NSE
swing-trading system. The rules have already decided. For each area give a SHORT opinion:
agree / caution / disagree + why, citing only numbers present in the context. You cannot
change any plan. Output JSON array of notes: {scope: regime|entry|exit|risk|event, symbol
or null, stance: agree|caution|disagree, note: <=2 sentences, watch_for: <=1 sentence}."
Scopes to cover when material: regime read (macro), each card (entry), each open position
(exit/hold), portfolio heat (risk/sizing), structure events (gaps/drawdowns/events).

## Guard (guard.py — non-negotiable)
1. Parse JSON strictly; malformed → discard call, log fail row, no retry loops (1 retry max).
2. Numeric filter: a note may only contain numbers that appear verbatim in the context pack
   (entry/stop/r values etc). Any novel price/qty/percent → note rejected with reason logged.
3. Phrase filter: reject notes containing imperative trade instructions ("buy now", "exit
   immediately", "increase size") — stances are opinions, not commands.
4. Every rendered note carries the fixed suffix chip: "AI opinion — advisory, not a signal."

## Persistence + the advisor's own scoreboard
```sql
CREATE TABLE IF NOT EXISTS advisor_notes (
  note_date TEXT NOT NULL, scope TEXT NOT NULL, symbol TEXT,
  stance TEXT NOT NULL, note TEXT NOT NULL, watch_for TEXT,
  model TEXT, user_action TEXT,          -- null | agreed | dismissed
  outcome_r REAL,                        -- backfilled at T+10 for entry/exit scopes
  created_at TEXT DEFAULT (datetime('now')),
  PRIMARY KEY (note_date, scope, COALESCE(symbol,'')) );
```
The advisor gets the SAME expectancy treatment as any setup family: its entry-scope
disagreements joined to outcomes at T+10 → "advisor disagree-hit-rate n=…" on the Journal
screen once n≥20. If its disagreements systematically beat the gate → that's documented
evidence for a threshold calibration pass (LEARNINGS entry), not for giving it power.

## API + UI (presentation only)
- `GET /api/advisor/today` → {available, as_of, notes:[...]}; `POST /api/advisor/note-action`
  {note_date, scope, symbol, action: agreed|dismissed}.
- Render: one "ADVISOR" strip per relevant screen (Regime: regime-scope note; Setups: entry
  notes inline under each card's evidence line; Watchlist: exit notes on coach cards; Journal:
  the advisor scoreboard). Muted style + the advisory chip. Beginner sees it collapsed to one
  line; expert expanded. It NEVER renders above the deterministic verdict it comments on.
- On-demand button (expert only): "ask advisor" on a card → one scoped call (counts against
  daily_budget_calls).

## Pipeline + tests
- Register stage `advisor` in cli after expectancy; pipeline_runs row like every stage.
- Tests (mock the HTTP client; never call network in tests): context pack contains only
  existing-payload fields; guard rejects novel-number note + imperative note; run() persists
  notes + is a no-op without api_key; note-action endpoint upserts user_action; malformed
  JSON → fail row, no crash.

## Explicitly OUT of scope
- Any advisor influence on rank/grade/qty/stop/gates/alerts. No push notifications from it.
- Intraday calls (EOD only, until the live loop T4 exists).
- Auto-acting on "agree" — user taps are journal data, nothing else.
