-- TraderLog schema.
--
-- Conventions (same as manas_os, so a model moving between them learns one set):
--   * dates are ISO 'YYYY-MM-DD'; timestamps are ISO-8601 with offset
--   * symbols are uppercase NSE tickers
--   * every table carries ingested_at
--   * upsert by natural key only; never overwrite history
--   * every statement is CREATE TABLE IF NOT EXISTS, so this file re-runs
--     harmlessly on every init_db() and retrofits new tables onto an existing DB
--
-- Adding a COLUMN to a table that already shipped goes through
-- _migrate_add_columns() in db/__init__.py, NOT by editing the CREATE below --
-- editing it silently does nothing to databases that already exist.
--
-- Single-writer-per-table is enforced by convention and documented in
-- CANONICAL.md §6. If you need to write a table that is not yours, stop.

-- ---------------------------------------------------------------------------
-- 1. Traders
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS traders (
  handle          TEXT PRIMARY KEY,          -- X handle WITHOUT the leading @
  display_name    TEXT,
  tier            TEXT DEFAULT 'WATCH',      -- CORE | WATCH | ARCHIVE
  tags            TEXT,                      -- JSON array: ["swing","ep","ipo"]
  active          INTEGER NOT NULL DEFAULT 1,
  -- Last post timestamp we have seen. Drives the ingest freshness check and
  -- the `since` argument on the next fetch.
  last_seen_ts    TEXT,
  notes           TEXT,
  is_mock         INTEGER NOT NULL DEFAULT 0,
  ingested_at     TEXT NOT NULL
);

-- ---------------------------------------------------------------------------
-- 2. Raw ingest -- immutable. Written once on first sight, never edited except
--    to stamp deleted_at. The archive on disk is the source of truth; these
--    rows are the index into it.
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS posts (
  post_id         TEXT PRIMARY KEY,          -- X post id, stable
  handle          TEXT NOT NULL,
  conversation_id TEXT,                      -- root post id of the thread
  in_reply_to     TEXT,                      -- parent post id, NULL for roots
  ts_utc          TEXT NOT NULL,
  ts_ist          TEXT NOT NULL,             -- denormalised: every UI surface is IST
  text            TEXT,
  url             TEXT,
  lang            TEXT,
  -- Path to the immutable JSON capture under data/raw/. Nothing downstream may
  -- re-fetch a post: threads run for weeks and X's search window does not.
  raw_path        TEXT,
  fetched_at      TEXT NOT NULL,
  -- Set when a post we had previously captured is no longer present upstream.
  -- The row and its archive are KEPT. Traders delete losers; dropping them
  -- would bias every derived style metric toward flattery.
  deleted_at      TEXT,
  is_mock         INTEGER NOT NULL DEFAULT 0,
  ingested_at     TEXT NOT NULL,
  FOREIGN KEY (handle) REFERENCES traders(handle)
);
CREATE INDEX IF NOT EXISTS idx_posts_handle_ts   ON posts(handle, ts_ist DESC);
CREATE INDEX IF NOT EXISTS idx_posts_conv        ON posts(conversation_id);
CREATE INDEX IF NOT EXISTS idx_posts_deleted     ON posts(deleted_at) WHERE deleted_at IS NOT NULL;

CREATE TABLE IF NOT EXISTS post_media (
  post_id         TEXT NOT NULL,
  idx             INTEGER NOT NULL,          -- 0-based position within the post
  local_path      TEXT NOT NULL,             -- under data/media/
  sha256          TEXT NOT NULL,
  media_type      TEXT,                      -- image | video | other
  -- Vision output for this image (see CONTRACTS.md §4). NULL until the vision
  -- pass runs. Written by llm/vision.py ONLY.
  vision_json     TEXT,
  vision_model    TEXT,
  vision_at       TEXT,
  is_mock         INTEGER NOT NULL DEFAULT 0,
  ingested_at     TEXT NOT NULL,
  PRIMARY KEY (post_id, idx),
  FOREIGN KEY (post_id) REFERENCES posts(post_id)
);

-- ---------------------------------------------------------------------------
-- 3. Classification
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS post_class (
  post_id         TEXT PRIMARY KEY,
  -- trade_event | breadth | watch_idea | theme | education | noise
  kind            TEXT NOT NULL,
  confidence      REAL,
  symbols         TEXT,                      -- JSON array of detected NSE symbols
  -- ep | momentum_burst | breakout | pullback | vcp | ipo_base | swing_range
  -- | unclear. Captured from the first classification pass rather than added
  -- later: retrofitting it would mean re-running every historical post.
  play_type       TEXT,
  conviction_words TEXT,                     -- JSON array, verbatim
  model           TEXT,                      -- which model actually decided
  run_id          INTEGER,                   -- -> llm_runs.id
  is_mock         INTEGER NOT NULL DEFAULT 0,
  ingested_at     TEXT NOT NULL,
  FOREIGN KEY (post_id) REFERENCES posts(post_id)
);
CREATE INDEX IF NOT EXISTS idx_post_class_kind ON post_class(kind);
-- NOTE: the index on play_type is created in db/__init__.py AFTER the column
-- migration runs, not here. This whole file executes BEFORE
-- _migrate_add_columns, so indexing a migration-added column here fails on any
-- database that already exists on disk.
-- Rule: schema.sql may only index columns present in its own CREATE statement.

-- ---------------------------------------------------------------------------
-- 4. Positions -- reconstructed from threads. Re-derived in full whenever a
--    thread changes; never patched incrementally.
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS positions (
  position_id     TEXT PRIMARY KEY,          -- sha1(handle|symbol|root_post_id)
  handle          TEXT NOT NULL,
  symbol          TEXT NOT NULL,
  root_post_id    TEXT NOT NULL,
  -- open | added | partial | closed | scratched | unclear
  status          TEXT NOT NULL,
  opened_at       TEXT,
  closed_at       TEXT,
  net_result_pct  REAL,
  holding_days    INTEGER,
  confidence      REAL,
  -- Full reconciler output (CONTRACTS.md §3). state_json is the position; the
  -- columns above are denormalised out of it for querying.
  state_json      TEXT NOT NULL,
  -- {field_name: post_id} for EVERY populated field. A field with no entry here
  -- is a defect: it means a number was produced that no post justifies. The
  -- parse check in checks/ asserts this table-wide.
  evidence_json   TEXT NOT NULL,
  -- JSON array of things the trader never stated ("stop never given"). The
  -- reconciler must populate this instead of inferring. Never guess a number.
  unresolved_json TEXT,
  -- sha256 of the concatenated thread content. Reconciliation is skipped when
  -- unchanged, so an unchanged thread costs nothing.
  thread_hash     TEXT,
  reconciled_at   TEXT,
  reconcile_model TEXT,
  is_mock         INTEGER NOT NULL DEFAULT 0,
  ingested_at     TEXT NOT NULL,
  FOREIGN KEY (handle) REFERENCES traders(handle)
);
CREATE INDEX IF NOT EXISTS idx_positions_handle  ON positions(handle);
CREATE INDEX IF NOT EXISTS idx_positions_symbol  ON positions(symbol);
CREATE INDEX IF NOT EXISTS idx_positions_status  ON positions(status);

CREATE TABLE IF NOT EXISTS position_events (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  position_id     TEXT NOT NULL,
  post_id         TEXT NOT NULL,             -- the citation. NOT NULL by design.
  -- entry | add | sl_set | sl_move | target_set | target_hit
  -- | partial_exit | exit | scratch | commentary
  kind            TEXT NOT NULL,
  price           REAL,
  qty_pct         REAL,                      -- portion of the position, when stated
  stated_at       TEXT NOT NULL,             -- IST timestamp of the post
  seq             INTEGER,                   -- order within the thread
  confidence      REAL,
  note            TEXT,
  is_mock         INTEGER NOT NULL DEFAULT 0,
  ingested_at     TEXT NOT NULL,
  FOREIGN KEY (position_id) REFERENCES positions(position_id),
  FOREIGN KEY (post_id)     REFERENCES posts(post_id)
);
CREATE INDEX IF NOT EXISTS idx_pos_events_pos ON position_events(position_id, seq);

-- Cross-thread link proposals below the confidence floor. Nothing here is
-- applied until a human resolves it. Written by llm/link.py, resolved via the UI.
CREATE TABLE IF NOT EXISTS review_queue (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  kind            TEXT NOT NULL,             -- link_event | ambiguous_symbol | low_conf_parse
  post_id         TEXT,
  position_id     TEXT,
  question        TEXT NOT NULL,             -- plain English, for a human
  proposed_json   TEXT,                      -- what the model wanted to do
  confidence      REAL,
  status          TEXT NOT NULL DEFAULT 'open',  -- open | accepted | rejected
  resolved_by     TEXT,
  resolved_at     TEXT,
  is_mock         INTEGER NOT NULL DEFAULT 0,
  ingested_at     TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_review_open ON review_queue(status) WHERE status = 'open';

-- ---------------------------------------------------------------------------
-- 5. Other extracted surfaces
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS breadth_notes (
  post_id         TEXT PRIMARY KEY,
  handle          TEXT NOT NULL,
  trade_date      TEXT NOT NULL,
  stance          TEXT,                      -- risk_on | neutral | risk_off | unclear
  claims_json     TEXT,                      -- JSON array of discrete claims made
  symbols         TEXT,
  confidence      REAL,
  is_mock         INTEGER NOT NULL DEFAULT 0,
  ingested_at     TEXT NOT NULL,
  FOREIGN KEY (post_id) REFERENCES posts(post_id)
);
CREATE INDEX IF NOT EXISTS idx_breadth_notes_date ON breadth_notes(trade_date);

CREATE TABLE IF NOT EXISTS watch_ideas (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  post_id         TEXT NOT NULL,
  handle          TEXT NOT NULL,
  symbol          TEXT NOT NULL,
  kind            TEXT NOT NULL,             -- watch | ep | ipo | theme
  trigger_text    TEXT,                      -- "above 1,240 on volume"
  level           REAL,
  stated_at       TEXT NOT NULL,
  -- open | triggered | expired | superseded. Set by derive/, not by the LLM.
  status          TEXT NOT NULL DEFAULT 'open',
  confidence      REAL,
  is_mock         INTEGER NOT NULL DEFAULT 0,
  ingested_at     TEXT NOT NULL,
  FOREIGN KEY (post_id) REFERENCES posts(post_id)
);
CREATE INDEX IF NOT EXISTS idx_watch_symbol ON watch_ideas(symbol, stated_at DESC);

CREATE TABLE IF NOT EXISTS themes (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  name            TEXT NOT NULL UNIQUE,
  symbols_json    TEXT,
  first_seen      TEXT,
  last_seen       TEXT,
  mention_count   INTEGER DEFAULT 0,
  is_mock         INTEGER NOT NULL DEFAULT 0,
  ingested_at     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS edu_items (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  post_id         TEXT NOT NULL,
  handle          TEXT NOT NULL,
  title           TEXT,
  -- The teachable claim, in the trader's own framing. Quote where possible --
  -- this is what practice-vs-preach is scored against, so paraphrase drift
  -- corrupts the measurement.
  principle_text  TEXT NOT NULL,
  topic_tags      TEXT,                      -- JSON array: ["stops","sizing","entries"]
  stated_at       TEXT NOT NULL,
  confidence      REAL,
  is_mock         INTEGER NOT NULL DEFAULT 0,
  ingested_at     TEXT NOT NULL,
  FOREIGN KEY (post_id) REFERENCES posts(post_id)
);

-- Does the trader do what they say? Written by derive/preach.py.
CREATE TABLE IF NOT EXISTS edu_links (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  edu_id          INTEGER NOT NULL,
  position_id     TEXT NOT NULL,
  verdict         TEXT NOT NULL,             -- followed | violated | na
  evidence        TEXT,                      -- why, citing event ids
  confidence      REAL,
  is_mock         INTEGER NOT NULL DEFAULT 0,
  ingested_at     TEXT NOT NULL,
  FOREIGN KEY (edu_id)      REFERENCES edu_items(id),
  FOREIGN KEY (position_id) REFERENCES positions(position_id)
);

-- Per-trader derived style. One row per trader per computation date, so the
-- profile itself has history and drift is visible.
CREATE TABLE IF NOT EXISTS trader_style (
  handle              TEXT NOT NULL,
  as_of               TEXT NOT NULL,
  n_positions         INTEGER,
  median_hold_days    REAL,
  stated_win_rate     REAL,                  -- of CLOSED positions with a stated result
  avg_result_pct      REAL,
  avg_r               REAL,
  sector_tilt_json    TEXT,
  entry_type_json     TEXT,
  -- Stop discipline: how often a stop was stated at all, and how often a stated
  -- stop was actually honoured rather than quietly widened.
  stop_stated_pct     REAL,
  stop_honored_pct    REAL,
  preach_score        REAL,                  -- followed / (followed + violated)
  is_mock             INTEGER NOT NULL DEFAULT 0,
  ingested_at         TEXT NOT NULL,
  PRIMARY KEY (handle, as_of)
);

-- ---------------------------------------------------------------------------
-- 6. Adopted market data (W4/W5). Shapes match manas_os so the adopted modules
--    need minimal edits.
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS daily_prices (
  symbol          TEXT NOT NULL,
  trade_date      TEXT NOT NULL,
  series          TEXT,
  open            REAL, high REAL, low REAL, close REAL, prev_close REAL,
  volume          REAL,
  turnover        REAL,
  num_trades      REAL,
  delivery_pct    REAL,
  source          TEXT,                      -- 'bhavcopy' is canonical
  ingested_at     TEXT NOT NULL,
  PRIMARY KEY (symbol, trade_date)
);
CREATE INDEX IF NOT EXISTS idx_daily_prices_date ON daily_prices(trade_date);

CREATE TABLE IF NOT EXISTS breadth_daily (
  trade_date        TEXT PRIMARY KEY,
  advances          REAL, declines REAL,
  -- up_4pct/down_4pct are PERCENTAGES (0..100) of the NIFTYMIDSML400
  -- universe, post the interim corporate-action exclusion in
  -- adopted/universe_breadth.py. Percent inputs are the EMPIRICALLY VALIDATED
  -- XP convention (C6 RETRACTED 2026-08-24, design/AUDIT_LEDGER.md): the
  -- retracted percent->count conversion was a ~4x scale error. adopted/
  -- regime_daily.py feeds these columns straight into xp.compute_xp
  -- unconverted, and at a reseed point xp_for_date seeds its z-state from
  -- this column's own observed value (C8, same addendum). MBI's r4.5 burst
  -- ratio reads them as-is because it is scale-invariant.
  up_4pct           REAL, down_4pct REAL,
  pct_above_10dma   REAL, pct_above_20dma REAL,
  pct_above_50dma   REAL, pct_above_200dma REAL,
  new_highs_52w     REAL, new_lows_52w REAL,
  net_new_highs_pct REAL,
  nifty             REAL, nifty_chg_pct REAL,
  universe_size     INTEGER,
  source            TEXT,
  ingested_at       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS breadth_counts (
  trade_date      TEXT PRIMARY KEY,
  counts_json     TEXT NOT NULL,             -- the ~38 raw counts
  universe_size   INTEGER,
  ingested_at     TEXT NOT NULL
);

-- XP dial + MBI score. Adopted reverse-engineering (regime/xp.py and
-- regime/snapshot.py::compute_mbi). NOT the governor layer -- no pillars, no
-- market_mode, no quadrant: TraderLog scores other people's market reads, it
-- does not gate anybody's trades.
--
-- xp_value is a RECURSION on the prior row's xp_value/xp_z_state. Backfill in
-- strict date order. A gap in breadth_daily is a chain break, not something to
-- interpolate across. At a reseed point (first date, or after a gap) the
-- z-state seeds from the session's own observed breadth_daily.up_4pct
-- (percent scale, C8); config seeds are only a fallback when no breadth value
-- exists. Backfill additionally warms up the first 20 sessions in memory
-- (compute-and-skip): nothing is persisted until session 21, so the
-- series-start transient is discarded rather than presented as data (C8).
CREATE TABLE IF NOT EXISTS regime_daily (
  trade_date      TEXT PRIMARY KEY,
  xp_value        REAL,
  xp_z_state      REAL,
  xp_band         TEXT,                      -- LOW | BUILDING | STRONG | EXTREME
  r10             REAL, r20 REAL, r50 REAL, r4p5 REAL,
  band_r10        TEXT, band_r20 TEXT, band_r50 TEXT, band_r4p5 TEXT,
  mbi_day_color   TEXT,                      -- GREEN | WHITE | RED
  mbi_score       INTEGER,
  warning_day     INTEGER,                   -- 1 when >= 3 bands are RED
  source_date     TEXT,                      -- breadth_daily row actually used
  is_mock         INTEGER NOT NULL DEFAULT 0,
  ingested_at     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS alpha_activity_signals (
  symbol          TEXT NOT NULL,
  trade_date      TEXT NOT NULL,
  q_ratio         REAL,                      -- avg trade qty vs its 20-session mean
  d_ratio         REAL,                      -- delivery% vs prior-19-session mean
  activity_score  REAL,
  formula_version TEXT,
  ingested_at     TEXT NOT NULL,
  PRIMARY KEY (symbol, trade_date)
);

-- ---------------------------------------------------------------------------
-- 6b. Attention engine (W9/W10). Spec: design/ATTENTION_ENGINE.md
--
-- priority is DELIBERATELY not a buy signal. It ranks what to look at. The
-- freshness term decays with age since first mention so the score cannot reward
-- crowding -- eight traders on a name over three weeks must score LOWER than
-- three traders inside two sessions, or this becomes a buy-the-top machine.
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS symbol_attention (
  symbol          TEXT NOT NULL,
  trade_date      TEXT NOT NULL,
  attention       REAL,                      -- raw weighted event sum
  priority        REAL,                      -- attention x all multipliers
  n_traders       INTEGER,
  n_entries       INTEGER,                   -- money: entries + adds
  n_mentions      INTEGER,                   -- talk: watch ideas + bare mentions
  first_seen      TEXT,
  sessions_since_first INTEGER,
  freshness       REAL, regime_mult REAL, theme_mult REAL,
  activity_mult   REAL, play_fit REAL,
  dominant_play   TEXT,
  theme           TEXT,
  -- cluster exits, deleted entry posts, stop violations. Surfaced as an explicit
  -- flag, never silently netted into priority -- a reader must see WHY something
  -- was demoted.
  caution_json    TEXT,
  components_json TEXT,                      -- per-event contributions, drill-down
  is_mock         INTEGER NOT NULL DEFAULT 0,
  ingested_at     TEXT NOT NULL,
  PRIMARY KEY (symbol, trade_date)
);
CREATE INDEX IF NOT EXISTS idx_attention_date ON symbol_attention(trade_date, priority DESC);

-- Does the score actually predict anything? Until the top decile beats the
-- universe median at +10 sessions over >=60 clusters, the HEATMAP screen ranks
-- by raw attention and states that priority is unproven.
CREATE TABLE IF NOT EXISTS attention_validation (
  as_of           TEXT NOT NULL,
  decile          INTEGER NOT NULL,
  n_clusters      INTEGER,
  fwd_5d          REAL, fwd_10d REAL, fwd_20d REAL,
  universe_10d    REAL,
  beats_universe  INTEGER,
  ingested_at     TEXT NOT NULL,
  PRIMARY KEY (as_of, decile)
);

-- ---------------------------------------------------------------------------
-- 7. Operational
-- ---------------------------------------------------------------------------

-- Every LLM call. This is what makes the free -> paid -> local migration a
-- measurement rather than a guess, and it records which model ACTUALLY served
-- a call, which matters because tiers are fallback chains.
CREATE TABLE IF NOT EXISTS llm_runs (
  id                INTEGER PRIMARY KEY AUTOINCREMENT,
  task              TEXT NOT NULL,           -- classify | vision | reconcile | link
  tier              TEXT NOT NULL,           -- cheap | smart | vision
  provider          TEXT,                    -- openrouter | ollama
  model             TEXT,                    -- the model that actually answered
  attempt           INTEGER DEFAULT 1,       -- >1 means an earlier tier entry failed
  ref_id            TEXT,                    -- post_id / position_id
  prompt_tokens     INTEGER,
  completion_tokens INTEGER,
  cost_usd          REAL,
  latency_ms        INTEGER,
  ok                INTEGER NOT NULL,
  error             TEXT,
  ts                TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_llm_runs_ts ON llm_runs(ts DESC);

CREATE TABLE IF NOT EXISTS pipeline_runs (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  stage           TEXT NOT NULL,
  run_date        TEXT NOT NULL,
  status          TEXT NOT NULL,             -- ok | skip | fail
  rows            INTEGER,
  duration_ms     INTEGER,
  detail          TEXT,
  ts              TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_pipeline_runs ON pipeline_runs(stage, run_date DESC);

-- Transactional outbox (adopted pattern). Enqueue in the SAME transaction as the
-- business write; deliver separately. delivery_ambiguous covers the crash
-- between "sent" and "recorded as sent" -- never assume a send failed.
CREATE TABLE IF NOT EXISTS telegram_outbox (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  dedupe_key      TEXT NOT NULL UNIQUE,
  body            TEXT NOT NULL,
  state           TEXT NOT NULL DEFAULT 'pending',  -- pending|sent|failed|delivery_ambiguous
  attempts        INTEGER NOT NULL DEFAULT 0,
  last_error      TEXT,
  created_at      TEXT NOT NULL,
  sent_at         TEXT
);
CREATE INDEX IF NOT EXISTS idx_outbox_state ON telegram_outbox(state);

CREATE TABLE IF NOT EXISTS settings (
  id              INTEGER PRIMARY KEY CHECK (id = 1),
  data_json       TEXT NOT NULL
);
