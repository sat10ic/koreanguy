-- Manas AI Trading OS — SQLite schema (manas.db)
-- Conventions: dates ISO 'YYYY-MM-DD'; symbols uppercase NSE; every table carries ingested_at.
-- Idempotent: CREATE ... IF NOT EXISTS. Later phases add tables to this same file.
-- Point-in-time discipline: rows are never overwritten with revised history; re-runs upsert
-- by natural key only.

-- ─────────────────────────────────────────────────────────────────────────────
-- MARKET DATA (P0)
-- ─────────────────────────────────────────────────────────────────────────────

-- One row per symbol per trading day. Delivery fields come from bhavcopy sec_bhavdata_full.
CREATE TABLE IF NOT EXISTS daily_prices (
    symbol        TEXT NOT NULL,
    trade_date    TEXT NOT NULL,
    series        TEXT DEFAULT 'EQ',
    open          REAL, high REAL, low REAL, close REAL, prev_close REAL,
    last_price    REAL, avg_price REAL,
    volume        INTEGER,
    turnover      REAL,
    num_trades    INTEGER,
    delivery_qty  INTEGER,
    delivery_pct  REAL,
    source        TEXT,                 -- 'fyers' | 'bhavcopy'
    ingested_at   TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (symbol, trade_date, series)
);

-- Rebuildable tradeable universe as-of each date (point-in-time; avoids survivorship bias).
CREATE TABLE IF NOT EXISTS universe (
    symbol        TEXT NOT NULL,
    as_of_date    TEXT NOT NULL,
    name          TEXT,
    series        TEXT DEFAULT 'EQ',
    sector        TEXT,
    industry      TEXT,
    market_cap_cr REAL,
    avg_turnover_cr REAL,
    is_tradeable  INTEGER DEFAULT 1,    -- passes price + liquidity filter
    ingested_at   TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (symbol, as_of_date)
);

-- Wide per-symbol per-day indicator features (adopted indicators.py writes here).
-- indicator_registry (below) is the DISPLAY/WEIGHT source of truth; this is the STORAGE.
CREATE TABLE IF NOT EXISTS features_daily (
    symbol        TEXT NOT NULL,
    trade_date    TEXT NOT NULL,
    -- columns added by the indicator engine (sma*, ema*, atr*, adr*, rsi14, stage,
    -- tightness, rvol, swing_high_20, swing_low_20, high_252, low_252, minervini_pass, ...)
    feature_json  TEXT,                 -- flexible bag for engine output; promoted columns added later
    ingested_at   TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (symbol, trade_date)
);

-- ─────────────────────────────────────────────────────────────────────────────
-- BREADTH + REGIME (P0 ingest / P1 compute)
-- ─────────────────────────────────────────────────────────────────────────────

-- One row per trading day, from the accessible breadth Google Sheet (XP inputs live here).
CREATE TABLE IF NOT EXISTS breadth_daily (
    trade_date        TEXT PRIMARY KEY,
    advances          INTEGER,
    declines          INTEGER,
    up_4pct           INTEGER,          -- today_4.5+ proxy input
    down_4pct         INTEGER,          -- 4.5- input
    up_25pct_month    INTEGER,
    down_25pct_month  INTEGER,
    up_50pct_month    INTEGER,
    down_50pct_month  INTEGER,
    pct_above_10dma   REAL,             -- 10MA% (XP input)
    pct_above_20dma   REAL,             -- 20MA% (XP input)
    pct_above_40dma   REAL,
    pct_above_50dma   REAL,             -- long-term participation (Participation panel)
    pct_10dma_gt_20dma REAL,
    pct_20dma_gt_40dma REAL,
    nifty             REAL,
    nifty_chg_pct     REAL,
    source            TEXT DEFAULT 'breadth_sheet',
    ingested_at       TEXT DEFAULT (datetime('now'))
);

-- Nightly regime snapshot = the Top Decision Strip + quadrant + posture.
-- xp_z_state is persisted because XP recurses on the prior day's z_state and XP.
CREATE TABLE IF NOT EXISTS regime_snapshots (
    snapshot_date       TEXT PRIMARY KEY,
    market_mode         TEXT,           -- RISK_ON | SELECTIVE | DEFENSIVE | NO_TRADE
    xp_value            REAL,
    xp_z_state          REAL,
    em_value            REAL,           -- null until EM sheet shared
    em_source           TEXT,           -- 'proxy' | 'sheet' | null
    mbi_day_color       TEXT,           -- GREEN | WHITE | RED
    warning_day         INTEGER DEFAULT 0,
    r10 REAL, r20 REAL, r50 REAL, r4p5 REAL,
    pillars_passed      INTEGER,
    allowed_risk_min_pct REAL,
    allowed_risk_max_pct REAL,
    max_open_risk_pct    REAL,
    preferred_setups_json TEXT,
    avoid_setups_json     TEXT,
    quadrant_json         TEXT,         -- {momentum,swing,trend,bias: {state,confidence,reason}}
    explanation_text      TEXT,
    data_stale            INTEGER DEFAULT 0,  -- 1 => inputs stale; market_mode hard-degraded
    ingested_at           TEXT DEFAULT (datetime('now'))
);

-- Universe-health table on the regime page (breadth per universe bucket).
CREATE TABLE IF NOT EXISTS regime_universe_metrics (
    snapshot_date TEXT NOT NULL,
    universe_key  TEXT NOT NULL,        -- NIFTY_50 | NIFTY_500 | ...
    above_10_pct REAL, above_20_pct REAL, above_50_pct REAL, above_200_pct REAL,
    up_4p5_pct REAL, down_4p5_pct REAL, r4p5 REAL,
    new_highs INTEGER, new_lows INTEGER,
    status_label TEXT,
    ingested_at TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (snapshot_date, universe_key)
);

-- Sector heatmap (from ChartsMaze sector analytics).
CREATE TABLE IF NOT EXISTS sector_metrics (
    snapshot_date TEXT NOT NULL,
    sector_key    TEXT NOT NULL,
    breadth_20_pct REAL, breadth_50_pct REAL,
    rs_score REAL,
    setup_count_a INTEGER, setup_count_b INTEGER, setup_count_c INTEGER,
    leading_setups TEXT,
    action_label  TEXT,                 -- FOCUS | WATCH | AVOID
    ingested_at TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (snapshot_date, sector_key)
);

-- Daily closes + SMA50 for sector indices and the MARS benchmark, cached so
-- MARS is recomputable without re-fetching. `symbol` holds both sector indices
-- (NIFTY AUTO, NIFTY IT, ...) and the benchmark (NIFTYMIDSML400 / NIFTY 500).
CREATE TABLE IF NOT EXISTS sector_index_prices (
    symbol        TEXT NOT NULL,
    trade_date    TEXT NOT NULL,
    close         REAL,
    sma50         REAL,
    ingested_at   TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (symbol, trade_date)
);
CREATE INDEX IF NOT EXISTS idx_sector_idx_prices_date ON sector_index_prices(trade_date);

-- Industry / "Themes" leaderboard (from ChartsMaze industry-analytics.csv).
-- Sibling to sector_metrics: the finer Basic-Industry rows (Investment Banking,
-- Electrical - Power Equipment, ...) that the regime page's "Themes" tab shows.
CREATE TABLE IF NOT EXISTS industry_metrics (
    snapshot_date     TEXT NOT NULL,
    name              TEXT NOT NULL,        -- Basic Industry label
    perf_1d           REAL,
    perf_1w           REAL,
    perf_1m           REAL,
    perf_3m           REAL,
    rank_1m           INTEGER,
    rank_3m           INTEGER,
    num_stocks        INTEGER,
    market_cap_cr     REAL,
    pct_from_52w_high REAL,
    action_label      TEXT,                 -- reserved; populated by full P1 regime work
    ingested_at TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (snapshot_date, name)
);

-- Setup-availability panel (bridge from regime to execution).
CREATE TABLE IF NOT EXISTS setup_availability (
    snapshot_date TEXT NOT NULL,
    setup_family  TEXT NOT NULL,        -- STRONG_START | EP | VCP | PULLBACK | ...
    count_total INTEGER, count_a INTEGER, count_b INTEGER, count_c INTEGER,
    permission_state TEXT,              -- ALLOWED | SELECTIVE | HALF_SIZE | OFF
    reason_text TEXT,
    ingested_at TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (snapshot_date, setup_family)
);

-- SHIP-1 #17 (I5): HMM regime CONFIRMATION gate (never a replacement for
-- market_mode above). regime/regime_hmm.py is the one writer. `source`
-- distinguishes nightly-live rows ('live') from validation/backfill runs
-- ('backfill') — the RENDER RULE display gate only counts 'live' rows.
CREATE TABLE IF NOT EXISTS hmm_regime (
    session_date  TEXT PRIMARY KEY,
    state         INTEGER,
    label         TEXT,              -- RISK_ON | SELECTIVE | DEFENSIVE | NO_TRADE (same vocabulary as market_mode)
    p_state       REAL,
    source        TEXT DEFAULT 'live',
    ingested_at   TEXT DEFAULT (datetime('now'))
);

-- ─────────────────────────────────────────────────────────────────────────────
-- REGISTRY + OPS (P0)
-- ─────────────────────────────────────────────────────────────────────────────

-- Single source of truth for how every metric is labelled, scoped, and weighted.
-- Storage of values is elsewhere (features_daily / regime_snapshots); this drives DISPLAY.
CREATE TABLE IF NOT EXISTS indicator_registry (
    indicator_key      TEXT PRIMARY KEY,
    label              TEXT,
    beginner_label     TEXT,
    one_line_help      TEXT,
    page_scope         TEXT,            -- csv: regime,scanner,chart,...
    preset_scope       TEXT,            -- csv of preset keys, or '*'
    default_visibility TEXT,            -- visible | badge | hidden
    readiness_weight   REAL DEFAULT 0,
    version            TEXT DEFAULT 'v1'
);

-- Singleton settings row (adopted ssrvol pattern): all runtime config as one JSON blob.
CREATE TABLE IF NOT EXISTS settings (
    id          INTEGER PRIMARY KEY CHECK (id = 1),
    data_json   TEXT NOT NULL DEFAULT '{}',
    updated_at  TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS watchlist (
    symbol         TEXT PRIMARY KEY,
    note           TEXT,
    alerts_enabled INTEGER DEFAULT 1,
    added_at       TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS journal_trades (
    trade_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_date      TEXT NOT NULL,
    symbol          TEXT NOT NULL,
    setup           TEXT,
    entry           REAL,
    exit            REAL,
    stop            REAL,
    qty             REAL,
    r_result        REAL,
    mistake_tags_json TEXT,
    first_exit_flag_date TEXT,
    notes           TEXT,
    created_at      TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_journal_trades_date ON journal_trades(trade_date);

CREATE TABLE IF NOT EXISTS scan_candidates (
    scan_date       TEXT NOT NULL,
    symbol          TEXT NOT NULL,
    setup           TEXT NOT NULL,
    readiness       REAL,
    grade           TEXT,
    rs              REAL,
    rs_as_of        TEXT,
    delivery_pct    REAL,
    delivery_as_of  TEXT,
    pivot           REAL,
    entry           REAL,
    stop            REAL,
    rr              REAL,
    suggested_qty   INTEGER,
    target          REAL,
    sector          TEXT,
    industry        TEXT,
    evidence_json   TEXT,
    read            TEXT,
    timing_json     TEXT,
    source          TEXT DEFAULT 'scanner',
    ingested_at     TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (scan_date, symbol, setup)
);
CREATE INDEX IF NOT EXISTS idx_scan_candidates_date_readiness
    ON scan_candidates(scan_date, readiness DESC);

-- Plumbing-only outcome tracker. `scan_candidates` remains the display feed;
-- this durable pair is for forward-return learning jobs without building the
-- weekly retro engine yet.
CREATE TABLE IF NOT EXISTS candidates (
    candidate_date TEXT NOT NULL,
    symbol         TEXT NOT NULL,
    setup          TEXT NOT NULL,
    readiness      REAL,
    grade          TEXT,
    entry          REAL,
    stop           REAL,
    rr             REAL,
    suggested_qty  INTEGER,
    sector         TEXT,
    industry       TEXT,
    source_payload_json TEXT,
    created_at     TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (candidate_date, symbol, setup)
);
CREATE INDEX IF NOT EXISTS idx_candidates_date ON candidates(candidate_date);

CREATE TABLE IF NOT EXISTS outcomes (
    candidate_date TEXT NOT NULL,
    symbol         TEXT NOT NULL,
    setup          TEXT NOT NULL,
    horizon        INTEGER NOT NULL,
    as_of_date     TEXT,
    forward_return_pct REAL,
    forward_r      REAL,
    status         TEXT NOT NULL DEFAULT 'pending',
    updated_at     TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (candidate_date, symbol, setup, horizon),
    FOREIGN KEY (candidate_date, symbol, setup)
        REFERENCES candidates(candidate_date, symbol, setup)
        ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_outcomes_status ON outcomes(status, horizon);

-- WAVE_J7: counterfactual entry-population cohort for entry_variants replay.
-- Separate from scan_candidates/candidates by design (WAVE_J_SPEC.md task 2):
-- the real cascade output stays pure; this table holds confluence-pool names
-- that pass ALL gates or fail ONLY a soft gate (trend-template/fresh-leg/
-- participation), one writer (backtest/replay.py persist_counterfactual),
-- reusing the SAME candidate_for_symbol plan path -- no second plan formula.
CREATE TABLE IF NOT EXISTS counterfactual_candidates (
    scan_date      TEXT NOT NULL,
    symbol         TEXT NOT NULL,
    setup_family   TEXT NOT NULL,
    entry          REAL,
    stop           REAL,
    regime         TEXT,
    failed_gate    TEXT,          -- NULL = passed all gates; else one of SOFT_GATES
    created_at     TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (scan_date, symbol, setup_family)
);
CREATE INDEX IF NOT EXISTS idx_counterfactual_candidates_date ON counterfactual_candidates(scan_date);

CREATE TABLE IF NOT EXISTS counterfactual_outcomes (
    scan_date      TEXT NOT NULL,
    symbol         TEXT NOT NULL,
    setup_family   TEXT NOT NULL,
    horizon        INTEGER NOT NULL,
    status         TEXT NOT NULL DEFAULT 'pending',
    entry_fill     REAL,
    exit_date      TEXT,
    exit_price     REAL,
    exit_reason    TEXT,
    managed_r      REAL,
    managed_mfe_r  REAL,
    managed_mae_r  REAL,
    hit_1r         INTEGER,
    hit_2r         INTEGER,
    updated_at     TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (scan_date, symbol, setup_family, horizon),
    FOREIGN KEY (scan_date, symbol, setup_family)
        REFERENCES counterfactual_candidates(scan_date, symbol, setup_family)
        ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_counterfactual_outcomes_status ON counterfactual_outcomes(status, horizon);

-- WAVE K K4: Stage-1 SENSITIVE BUCKET (counterfactual only; does not feed
-- scan_candidates/gates). See scanner/discovery.py + design/WAVE_K_SPEC.md PART C.
CREATE TABLE IF NOT EXISTS discovery_bucket (
    scan_date       TEXT NOT NULL,
    symbol          TEXT NOT NULL,
    archetypes_json TEXT NOT NULL,
    metrics_json    TEXT NOT NULL,
    created_at      TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (scan_date, symbol)
);
CREATE INDEX IF NOT EXISTS idx_discovery_bucket_date ON discovery_bucket(scan_date);

-- WAVE M M7: EOD strong-start-ready / D2-ready detector output -- the
-- "TOMORROW MORNING (9:07-9:30)" handoff checklist. NOT fired signals: each
-- row is a setup to verify at tomorrow's open. Written by discovery.run
-- (persist_morning_setups); see engine/eod_detectors.py strong_start_ready/
-- d2_ready and design/WAVE_M_CONFORMANCE.md gap #2.
CREATE TABLE IF NOT EXISTS morning_setups (
    scan_date       TEXT NOT NULL,
    symbol          TEXT NOT NULL,
    setup_type      TEXT NOT NULL,   -- 'strong_start_ready' | 'd2_ready'
    branch          TEXT,            -- D2 branch (strong_close_gap_up | wick_play); NULL for strong-start
    evidence_json   TEXT NOT NULL,
    resolve_json    TEXT NOT NULL,   -- conditions only the 9:15 open can answer
    entry_rule      TEXT NOT NULL,
    stop_rule       TEXT NOT NULL,
    created_at      TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (scan_date, symbol, setup_type)
);
CREATE INDEX IF NOT EXISTS idx_morning_setups_date ON morning_setups(scan_date);

CREATE TABLE IF NOT EXISTS alert_log (
    alert_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_date     TEXT NOT NULL,
    symbol         TEXT,
    alert_type     TEXT NOT NULL,
    severity       TEXT NOT NULL,
    title          TEXT NOT NULL,
    detail         TEXT NOT NULL,
    evidence_json  TEXT,
    source_key     TEXT,
    created_at     TEXT DEFAULT (datetime('now')),
    UNIQUE(alert_date, symbol, alert_type, title)
);
CREATE INDEX IF NOT EXISTS idx_alert_log_date ON alert_log(alert_date);

CREATE TABLE IF NOT EXISTS alert_state (
    symbol           TEXT PRIMARY KEY,
    last_alert_date  TEXT,
    last_alert_type  TEXT,
    last_detail      TEXT,
    updated_at       TEXT DEFAULT (datetime('now'))
);

-- Per-stage run log — powers Pipeline Health + the "data didn't update today" detection.
CREATE TABLE IF NOT EXISTS pipeline_runs (
    run_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    run_date    TEXT NOT NULL,
    stage       TEXT NOT NULL,          -- ingest_breadth | ingest_bhavcopy | indicators | regime | scan | ...
    source      TEXT,
    status      TEXT,                   -- ok | fail | skip
    rows_affected INTEGER DEFAULT 0,
    duration_s  REAL,
    detail      TEXT,
    ran_at      TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS advisor_notes (
  note_date TEXT NOT NULL, scope TEXT NOT NULL, symbol TEXT NOT NULL DEFAULT '',
  stance TEXT NOT NULL, note TEXT NOT NULL, watch_for TEXT,
  model TEXT, user_action TEXT,
  outcome_r REAL,
  created_at TEXT DEFAULT (datetime('now')),
  PRIMARY KEY (note_date, scope, symbol) );

CREATE TABLE IF NOT EXISTS agent_verdicts (
  scan_date TEXT NOT NULL, symbol TEXT NOT NULL, agent TEXT NOT NULL,
  verdict TEXT NOT NULL,
  conviction INTEGER,
  rank INTEGER,
  lens_scores_json TEXT, bull_case TEXT, bear_case TEXT, reasoning TEXT,
  outcome_r REAL,
  -- G1: PASSED (gate survivor) | NEAR_MISS (refusals fill, debated but not
  -- gate-cleared) — carried per shortlist item so the UI/watchlist can show
  -- which debated names are actually tradeable vs discussion-only.
  tier TEXT,
  -- Chartink screener + push-to-debate amendment (2026-07-11 ~09:30): NULL =
  -- nightly scanner debate; 'user_pushed' = on-demand symbol pushed from the
  -- screener/search box (POST /api/desk/debate/push).
  source TEXT,
  created_at TEXT DEFAULT (datetime('now')),
  PRIMARY KEY (scan_date, symbol, agent)
);

-- G1: living watchlist — one row per debated symbol per night, tracking
-- PROMOTE/HOLD/DEMOTE/DROP deltas vs the previous scan_date's chair verdict.
CREATE TABLE IF NOT EXISTS agent_watchlist (
  scan_date TEXT NOT NULL, symbol TEXT NOT NULL,
  tier TEXT, status TEXT NOT NULL, prev_status TEXT, reason TEXT,
  -- Consecutive nights the symbol has been absent from actual debate while
  -- still shown on the list (grace period before DROP fires at 2 misses).
  miss_streak INTEGER DEFAULT 0,
  created_at TEXT DEFAULT (datetime('now')),
  PRIMARY KEY (scan_date, symbol)
);

CREATE TABLE IF NOT EXISTS scan_agent_logs (
  log_id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_date TEXT, agent TEXT, model TEXT, prompt_sha TEXT,
  latency_ms INTEGER, tokens_in INTEGER, tokens_out INTEGER,
  parsed_ok INTEGER, validation TEXT, error TEXT,
  created_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_daily_prices_date  ON daily_prices(trade_date);
CREATE INDEX IF NOT EXISTS idx_features_date       ON features_daily(trade_date);
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_date  ON pipeline_runs(run_date);

-- ChartsMaze screener hits — one row per (symbol, screener) that fired on
-- trade_date. bearish=1 for sentiment-inverted screeners (shorting-scanner);
-- excluded from bullish confluence counts but still stored for visibility.
CREATE TABLE IF NOT EXISTS screener_hits (
    trade_date    TEXT NOT NULL,
    symbol        TEXT NOT NULL,
    screener      TEXT NOT NULL,
    bearish       INTEGER DEFAULT 0,
    rs_rating     REAL,
    basic_industry TEXT,
    ingested_at   TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (trade_date, symbol, screener)
);
CREATE INDEX IF NOT EXISTS idx_screener_hits_date ON screener_hits(trade_date);

-- Per-symbol quality/negative-signal side data (ASM surveillance, market cap,
-- F&O eligibility, latest results growth) — feeds the future confluence-ranked
-- Setups feed's quality gate. Ingestion only here; no ranking logic.
CREATE TABLE IF NOT EXISTS symbol_quality (
    trade_date    TEXT NOT NULL,
    symbol        TEXT NOT NULL,
    market_cap_cr REAL,
    asm_stage     TEXT,
    eps_qoq       REAL,
    eps_yoy       REAL,
    sales_yoy     REAL,
    opm_yoy       REAL,
    is_fno        INTEGER,
    exchange      TEXT,
    ingested_at   TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (trade_date, symbol)
);

-- Point-in-time quarterly fundamentals. `symbol_quality` remains the compact
-- scanner side table; this history table stores the report-dated raw-ish source
-- rows W5 uses for CANSLIM/EP/fundamental panels.
CREATE TABLE IF NOT EXISTS symbol_fundamentals (
    symbol          TEXT NOT NULL,
    report_date     TEXT NOT NULL,
    as_of           TEXT NOT NULL,
    period          TEXT DEFAULT 'quarterly',
    revenue         REAL,
    operating_income REAL,
    net_income      REAL,
    eps             REAL,
    operating_margin REAL,
    sales_yoy       REAL,
    eps_yoy         REAL,
    opm_yoy         REAL,
    roe             REAL,
    pe_ratio        REAL,
    debt_to_equity  REAL,
    market_cap_cr   REAL,
    source          TEXT,
    ingested_at     TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (symbol, report_date, as_of)
);
CREATE INDEX IF NOT EXISTS idx_symbol_fundamentals_symbol_asof
    ON symbol_fundamentals(symbol, as_of);

-- ChartsMaze disclosure feeds (order wins, announcements, bulk deals,
-- insider trades, circuit revisions, episodic pivots).
CREATE TABLE IF NOT EXISTS disclosures (
    trade_date   TEXT NOT NULL,
    symbol       TEXT NOT NULL,
    kind         TEXT NOT NULL,
    detail_json  TEXT,
    PRIMARY KEY (trade_date, symbol, kind)
);
CREATE INDEX IF NOT EXISTS idx_disclosures_symbol_date
    ON disclosures(symbol, trade_date);

CREATE TABLE IF NOT EXISTS circuit_bands (
    symbol    TEXT NOT NULL,
    as_of     TEXT NOT NULL,
    band_pct  REAL,
    PRIMARY KEY (symbol, as_of)
);
CREATE INDEX IF NOT EXISTS idx_circuit_bands_symbol_date
    ON circuit_bands(symbol, as_of);

-- F7: FII/DII daily cash-provisional flows (Rs. crore), one row per trade date.
CREATE TABLE IF NOT EXISTS fii_dii_daily (
    trade_date TEXT PRIMARY KEY,
    fii_buy    REAL,
    fii_sell   REAL,
    fii_net    REAL,
    dii_buy    REAL,
    dii_sell   REAL,
    dii_net    REAL,
    source     TEXT,
    ingested_at TEXT DEFAULT (datetime('now'))
);

-- SHIP-1 #7: LightGBM direction-classifier scores (EXPERIMENTAL). A labeled
-- probability FACT — never read by gates/sizer/composite scoring (AD8).
-- Written by manas_os/ml/direction_lgbm.py's `ml_direction` pipeline stage,
-- which is a no-op skip when lightgbm is not installed.
CREATE TABLE IF NOT EXISTS ml_scores (
    scan_date        TEXT NOT NULL,
    symbol           TEXT NOT NULL,
    p_up_10d         REAL,
    top_drivers_json TEXT,
    created_at       TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (scan_date, symbol)
);

-- Per-stock 3-state HMM regime pane (EXPERIMENTAL, AlgoPoint-style). One
-- GaussianHMM fit per (symbol, as_of) is cached here since the fit itself
-- is the latency-expensive part of /api/desk/chart-data. Never gates/sizes
-- (AD8) -- manas_os/ml/stock_hmm.py is the one writer.
CREATE TABLE IF NOT EXISTS stock_hmm_cache (
    symbol       TEXT NOT NULL,
    as_of        TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    computed_at  TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (symbol, as_of)
);

-- STRONG START / ARORA FOCUS LIST -- PERSISTENT (NOT nightly-regenerated)
-- user/screener/LLM push list. See scanner/focus_list.py (one writer) and
-- design/STRONG_START_FOCUS_SPEC.md. A symbol can be added once (upsert on
-- symbol); remove sets active=0 rather than deleting the row.
CREATE TABLE IF NOT EXISTS focus_list (
    symbol      TEXT NOT NULL PRIMARY KEY,
    source      TEXT NOT NULL,        -- 'user' | 'screener' | 'llm'
    reason      TEXT,
    added_at    TEXT DEFAULT (datetime('now')),
    active      INTEGER DEFAULT 1
);

-- UI-2 live-work rail. Append-oriented telemetry only; never trading inputs.
CREATE TABLE IF NOT EXISTS jobs (
    job_id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT NOT NULL, run_date TEXT,
    status TEXT NOT NULL CHECK (status IN ('queued','running','succeeded','partial','failed','cancelled','interrupted')),
    requested_by TEXT, params_json TEXT, pid INTEGER, started_at TEXT, finished_at TEXT,
    heartbeat_at TEXT, error TEXT, created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_jobs_kind_date ON jobs(kind, run_date DESC);

CREATE TABLE IF NOT EXISTS job_steps (
    step_id INTEGER PRIMARY KEY AUTOINCREMENT, job_id INTEGER NOT NULL REFERENCES jobs(job_id),
    seq INTEGER NOT NULL, name TEXT NOT NULL, attempt INTEGER NOT NULL DEFAULT 1,
    status TEXT NOT NULL CHECK (status IN ('pending','running','ok','fail','skip','cancelled')),
    started_at TEXT, finished_at TEXT, duration_s REAL, rows_affected INTEGER,
    detail TEXT, error TEXT, UNIQUE(job_id, seq, attempt)
);
CREATE INDEX IF NOT EXISTS idx_job_steps_job ON job_steps(job_id, seq, attempt);

CREATE TABLE IF NOT EXISTS job_events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT, job_id INTEGER NOT NULL REFERENCES jobs(job_id),
    step_id INTEGER REFERENCES job_steps(step_id), event_type TEXT NOT NULL, payload_json TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_job_events_job ON job_events(job_id, event_id);

CREATE TABLE IF NOT EXISTS job_artifacts (
    artifact_id INTEGER PRIMARY KEY AUTOINCREMENT, job_id INTEGER NOT NULL REFERENCES jobs(job_id),
    step_id INTEGER REFERENCES job_steps(step_id), kind TEXT NOT NULL, ref TEXT NOT NULL,
    label TEXT, meta_json TEXT, created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_job_artifacts_job ON job_artifacts(job_id, artifact_id);

-- ── Added in later phases (P2 scanner/journal, P3/P4 alerts) ──
-- scan_results, candidates, trades, alert_log, alert_state
