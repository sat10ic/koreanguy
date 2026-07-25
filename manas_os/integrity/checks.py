"""manas_os/integrity/checks.py -- individual integrity checks.

Each check is a pure function over a READ-ONLY sqlite3.Connection
(row_factory=sqlite3.Row) that returns:

    {"name": str, "status": "PASS"|"WARN"|"FAIL", "detail": str, "evidence": dict}

No check here writes to the database, and none of them call
manas_os.db.connect()/init_db() (those write on open -- see db/__init__.py
and report.py's docstring). Callers are responsible for opening the
connection via `sqlite3.connect(f"file:{path}?mode=ro", uri=True)`.

Tables read (schema drift notes inline per check -- verified against the
real manas_os/data/manas.db on 2026-07-25, PRAGMA table_info, not assumed
from db/schema.sql alone, since some tables here are created lazily and are
NOT declared there, e.g. `refusals`):
  daily_prices, scan_candidates, refusals, discovery_bucket, agent_verdicts,
  pipeline_runs, sector_metrics, plus a handful of ingest-stage target
  tables used only by check_silent_skips (see STAGE_TABLE_MAP below).
"""
from __future__ import annotations

import json
import re
import sqlite3
from datetime import date
from pathlib import Path
from typing import Any

from manas_os import market_calendar

# ---------------------------------------------------------------------------
# shared helpers
# ---------------------------------------------------------------------------


def _result(name: str, status: str, detail: str, evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    assert status in ("PASS", "WARN", "FAIL"), status
    return {"name": name, "status": status, "detail": detail, "evidence": evidence or {}}


def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (name,)
    ).fetchone()
    return row is not None


def _sessions_since(d: date, today: date) -> int:
    """Trading sessions strictly after `d`, up to and including `today`.
    0 if d >= today. Mirrors market_calendar's trading_days_between
    convention (exclusive of both endpoints) plus 1 for `today` itself when
    today is a trading day."""
    if d >= today:
        return 0
    n = market_calendar.trading_days_between(d, today)
    if market_calendar.is_trading_day(today):
        n += 1
    return n


# ---------------------------------------------------------------------------
# a. check_freshness -- THE WATCHDOG
# ---------------------------------------------------------------------------


def check_freshness(conn: sqlite3.Connection, today: date) -> dict[str, Any]:
    """FAIL if pipeline_runs has no row for the most recent COMPLETED NSE
    trading session (market_calendar.last_trading_day(today)), or if
    MAX(daily_prices.trade_date) is older than that session.

    This is the check for the actual incident this module exists to catch:
    the pipeline silently not running for two days with nothing telling the
    user. Uses manas_os/market_calendar.py for trading-day logic (one-writer-
    per-metric rule -- this module does not reimplement a second calendar).
    """
    name = "freshness"
    expected_session = market_calendar.last_trading_day(today)
    expected_session_s = expected_session.isoformat()

    has_run = (
        conn.execute(
            "SELECT 1 FROM pipeline_runs WHERE run_date = ? LIMIT 1",
            (expected_session_s,),
        ).fetchone()
        is not None
    )

    price_row = conn.execute(
        "SELECT MAX(trade_date) FROM daily_prices WHERE series = 'EQ'"
    ).fetchone()
    last_price_date = price_row[0] if price_row else None

    # pipeline_runs.run_date has been observed (real DB, 2026-07-25) to hold
    # non-date strings from a mis-keyed writer (e.g. 'order-wins-master.csv',
    # 'n/a') -- a bare MAX(run_date) returns garbage. Filter to ISO dates for
    # any "last run date" evidence so this check never crashes or misreports
    # on that pollution.
    last_run_row = conn.execute(
        "SELECT MAX(run_date) FROM pipeline_runs "
        "WHERE run_date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'"
    ).fetchone()
    last_run_date = last_run_row[0] if last_run_row else None

    stale_prices = last_price_date is None or date.fromisoformat(last_price_date) < expected_session
    sessions_behind = 0
    if last_price_date and stale_prices:
        sessions_behind = _sessions_since(date.fromisoformat(last_price_date), expected_session)

    fail = (not has_run) or stale_prices
    status = "FAIL" if fail else "PASS"

    reasons = []
    if not has_run:
        reasons.append(f"no pipeline_runs row for {expected_session_s}")
    if stale_prices:
        reasons.append(
            f"daily_prices last EQ trade_date is {last_price_date!r}, "
            f"{sessions_behind} session(s) behind {expected_session_s}"
        )
    detail = (
        f"Expected session {expected_session_s}: " + "; ".join(reasons) + "."
        if reasons
        else f"Pipeline ran and prices are current through the expected session ({expected_session_s})."
    )

    evidence = {
        "expected_session": expected_session_s,
        "has_pipeline_run_for_expected_session": has_run,
        "last_pipeline_run_date": last_run_date,
        "last_price_date": last_price_date,
        "sessions_behind": sessions_behind,
    }
    return _result(name, status, detail, evidence)


# ---------------------------------------------------------------------------
# b. check_silent_skips
# ---------------------------------------------------------------------------

# stage -> (table, date_column, non_null_column_or_None). Verified by reading
# each stage's source (cli/__init__.py::_load_stages ordering + the writer
# module's INSERT target) and cross-checked against real pipeline_runs rows
# on 2026-07-23/24 -- see the integrity build report for the row-by-row
# comparison. `non_null_column` is set only for ingest_mars: sector_metrics
# rows for a date are ALSO written by the (unrelated) sectors/breadth stage,
# so a plain row-count check would miss MARS writing nothing -- it has to
# check the mars_score column specifically, non-null.
STAGE_TABLE_MAP: dict[str, tuple[str, str, str | None]] = {
    "ingest_bhavcopy": ("daily_prices", "trade_date", None),
    "ingest_mars": ("sector_metrics", "snapshot_date", "mars_score"),
    "ingest_fii_dii": ("fii_dii_daily", "trade_date", None),
    "ingest_universe_breadth": ("breadth_daily", "trade_date", None),
    "ingest_nse_indices": ("sector_index_prices", "trade_date", None),
    "indicators": ("features_daily", "trade_date", None),
    "footprint_driver": ("footprint_daily", "trade_date", None),
    "scan_candidates": ("scan_candidates", "scan_date", None),
    "discovery_bucket": ("discovery_bucket", "scan_date", None),
    "regime_snapshot": ("regime_snapshots", "snapshot_date", None),
    "alpha_features": ("alpha_feature_snapshots", "as_of_date", None),
}

# Stages seen in pipeline_runs.stage (real DB) this check does NOT verify.
# Listed explicitly per the build spec ("list any stage you could not map
# rather than silently ignoring it") -- mostly because their target table is
# shared with another stage (ingest_nse_deals and ingest_disclosures both
# write `disclosures`, so a row-count-only check can't attribute a skip to
# either one specifically) or because confidently identifying the write
# target needed more source-reading than this wave covered.
UNMAPPED_PIPELINE_STAGES: tuple[str, ...] = (
    "advisor", "agents_coach", "agents_debate", "alpha_memory",
    "alpha_symbol_identity", "breadth_counts", "candidate_outcomes",
    "classify_universe", "eod_alerts", "expectancy", "focus_themes",
    "ingest_chartsmaze", "ingest_chartsmaze_scanners", "ingest_disclosures",
    "ingest_earnings_calendar", "ingest_fundamentals", "ingest_nse_deals",
    "ml_breakout_rf", "ml_direction", "ml_sector_downside", "regime_backfill",
    "regime_hmm", "regime_vol_har", "screener_calibration", "setup_regime",
    "telegram_digest", "theme_pulse",
)


def check_silent_skips(conn: sqlite3.Connection, run_date: str) -> dict[str, Any]:
    """FAIL for any mapped stage whose pipeline_runs.status='skip' for
    `run_date` AND whose target table/column gained 0 rows for that date --
    the "MARS wrote nothing for weeks and nobody knew" pattern."""
    name = "silent_skips"

    skip_stages = sorted(
        r[0]
        for r in conn.execute(
            "SELECT DISTINCT stage FROM pipeline_runs WHERE run_date = ? AND status = 'skip'",
            (run_date,),
        ).fetchall()
    )

    checked: list[str] = []
    offenders: list[str] = []
    for stage in skip_stages:
        mapping = STAGE_TABLE_MAP.get(stage)
        if mapping is None:
            continue
        table, date_col, null_col = mapping
        if not _table_exists(conn, table):
            continue
        if null_col:
            sql = f"SELECT COUNT(*) FROM {table} WHERE {date_col} = ? AND {null_col} IS NOT NULL"
            col_desc = f"{table}.{null_col} non-null"
        else:
            sql = f"SELECT COUNT(*) FROM {table} WHERE {date_col} = ?"
            col_desc = f"{table} rows"
        n = conn.execute(sql, (run_date,)).fetchone()[0]
        checked.append(stage)
        if n == 0:
            offenders.append(f"{stage}: status=skip, {col_desc} = 0")

    unmapped_skip_stages = [s for s in skip_stages if s not in STAGE_TABLE_MAP]

    status = "FAIL" if offenders else "PASS"
    if not skip_stages:
        detail = f"No stage reported status=skip on {run_date}."
    elif not checked:
        detail = (
            f"{len(skip_stages)} stage(s) reported status=skip on {run_date}, "
            f"none of them mapped by this check -- see evidence.unmapped_skip_stages."
        )
    else:
        detail = (
            f"{len(offenders)} of {len(checked)} mapped skip-status stage(s) on {run_date} "
            f"wrote zero rows to their target table/column."
        )

    evidence = {
        "run_date": run_date,
        "skip_stages_seen": skip_stages,
        "skip_stages_checked": checked,
        "unmapped_skip_stages": unmapped_skip_stages,
        "offenders": offenders,
        "stages_this_check_does_not_map_at_all": list(UNMAPPED_PIPELINE_STAGES),
    }
    return _result(name, status, detail, evidence)


# ---------------------------------------------------------------------------
# c. check_verdict_grading
# ---------------------------------------------------------------------------


def check_verdict_grading(conn: sqlite3.Connection, today: date | None = None) -> dict[str, Any]:
    """FAIL if any agent_verdicts row whose scan_date is at least 5 trading
    sessions old has outcome_r IS NULL -- ungraded LLM opinions rendered as
    decisions. `today` defaults to date.today() (call signature otherwise
    matches the spec's check_verdict_grading(conn); the optional kwarg only
    exists so tests can inject a fixed date)."""
    name = "verdict_grading"
    if today is None:
        today = date.today()

    if not _table_exists(conn, "agent_verdicts"):
        return _result(name, "PASS", "agent_verdicts table does not exist.", {})

    total = conn.execute("SELECT COUNT(*) FROM agent_verdicts").fetchone()[0]
    graded = conn.execute(
        "SELECT COUNT(*) FROM agent_verdicts WHERE outcome_r IS NOT NULL"
    ).fetchone()[0]

    ungraded_dates = [
        r[0]
        for r in conn.execute(
            "SELECT DISTINCT scan_date FROM agent_verdicts WHERE outcome_r IS NULL"
        ).fetchall()
    ]
    stale_dates = []
    for d in ungraded_dates:
        try:
            dd = date.fromisoformat(d)
        except (TypeError, ValueError):
            continue
        if _sessions_since(dd, today) >= 5:
            stale_dates.append(d)
    stale_dates.sort()

    if stale_dates:
        placeholders = ",".join("?" for _ in stale_dates)
        n_stale_ungraded = conn.execute(
            f"SELECT COUNT(*) FROM agent_verdicts WHERE outcome_r IS NULL "
            f"AND scan_date IN ({placeholders})",
            stale_dates,
        ).fetchone()[0]
        oldest_ungraded = stale_dates[0]
    else:
        n_stale_ungraded = 0
        oldest_ungraded = None

    status = "FAIL" if n_stale_ungraded > 0 else "PASS"
    detail = (
        f"{n_stale_ungraded} verdict(s) ungraded (outcome_r NULL) with scan_date >=5 "
        f"trading sessions old (oldest: {oldest_ungraded}); {graded}/{total} graded overall."
        if n_stale_ungraded
        else f"No stale ungraded verdicts; {graded}/{total} graded overall."
    )
    evidence = {
        "total": total,
        "graded": graded,
        "ungraded": total - graded,
        "stale_ungraded": n_stale_ungraded,
        "oldest_stale_ungraded_scan_date": oldest_ungraded,
        "today": today.isoformat(),
    }
    return _result(name, status, detail, evidence)


# ---------------------------------------------------------------------------
# d. check_card_consistency
# ---------------------------------------------------------------------------


def _get_json_path(obj: Any, path: str) -> Any:
    cur = obj
    for part in path.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None
    return cur


# Real-schema note: scan_candidates has no boolean `label` field -- the
# closest thing is the `setup` column, which literally holds display text
# like "Strong Start Ready" (confirmed against the real DB: setup='Strong
# Start Ready', setup_type='strong_start_ready'). timing_json ALSO has no
# literal `strong_start` boolean key in this schema version (the spec's "at
# minimum" example) -- rule 1 below is kept verbatim from the spec for
# forward-compatibility (a future writer could add that key) but currently
# matches zero rows; that is disclosed, not hidden. Rule 2 is the one that
# actually catches the real defect this check exists for: 57 of 61 real
# "Strong Start Ready" rows (2026-07-25 measurement) carry timing_json.rvol
# < 1.0 -- i.e. volume is explicitly NOT elevated (timing_json.read literally
# says "volume is not yet expanded") while the card's own label claims
# readiness.
CARD_RULES: tuple[dict[str, Any], ...] = (
    {
        "rule": "strong_start_flag_false",
        "label_column": "setup",
        "label_substring": "strong start",
        "json_field": "timing_json",
        "path": "strong_start",
        "predicate": (lambda v: v is False),
        "why": "label claims a strong start but timing_json.strong_start is False",
    },
    {
        "rule": "strong_start_rvol_not_confirmed",
        "label_column": "setup",
        "label_substring": "strong start",
        "json_field": "timing_json",
        "path": "rvol",
        "predicate": (lambda v: isinstance(v, (int, float)) and v < 1.0),
        "why": "label claims a strong start but timing_json.rvol < 1.0 (volume not actually elevated)",
    },
)


def check_card_consistency(conn: sqlite3.Connection, scan_date: str) -> dict[str, Any]:
    """FAIL on any scan_candidates row whose `setup` label contradicts its
    own timing_json/evidence_json, per CARD_RULES (label_substring,
    json_field, json_path, predicate) -- trivial to extend with more rules."""
    name = "card_consistency"
    if not _table_exists(conn, "scan_candidates"):
        return _result(name, "PASS", "scan_candidates table does not exist.", {})

    rows = conn.execute(
        "SELECT symbol, setup, timing_json, evidence_json FROM scan_candidates WHERE scan_date = ?",
        (scan_date,),
    ).fetchall()

    offenders: list[dict[str, Any]] = []
    for r in rows:
        label = (r["setup"] or "")
        label_lower = label.lower()
        for rule in CARD_RULES:
            if rule["label_substring"] not in label_lower:
                continue
            raw = r[rule["json_field"]]
            if not raw:
                continue
            try:
                payload = json.loads(raw)
            except (TypeError, ValueError):
                continue
            value = _get_json_path(payload, rule["path"])
            if rule["predicate"](value):
                offenders.append(
                    {
                        "symbol": r["symbol"],
                        "label": label,
                        "rule": rule["rule"],
                        "json_field": rule["json_field"],
                        "path": rule["path"],
                        "value": value,
                        "why": rule["why"],
                    }
                )

    status = "FAIL" if offenders else "PASS"
    detail = (
        f"{len(offenders)} card(s) on {scan_date} contradict their own timing_json/evidence_json "
        f"(see evidence.offenders)."
        if offenders
        else f"No label/JSON contradictions found among {len(rows)} scan_candidates row(s) on {scan_date}."
    )
    evidence = {"scan_date": scan_date, "n_rows_checked": len(rows), "offenders": offenders}
    return _result(name, status, detail, evidence)


# ---------------------------------------------------------------------------
# e. check_overfit_capacity
# ---------------------------------------------------------------------------

OVERFIT_FILES: tuple[str, ...] = (
    "scanner/candidates.py",
    "scanner/gates.py",
    "scanner/discovery.py",
    "risk/plan.py",
    "engine/eod_detectors.py",
    "regime/governor.py",
)

# Module-level ALL_CAPS scalar numeric constant, e.g. `RS_FLOOR = 80.0` or
# `MIN_AVG_VOL_30D = 200_000  # 2 lakh shares/day`. Deliberately scalar-only
# (no dicts/tuples/sets) -- those are lookup tables, not individually-tuned
# thresholds, and counting their elements would conflate "one knob" (e.g.
# MAX_CARDS = {...}) with N knobs.
_CONST_RE = re.compile(r"^([A-Z][A-Z0-9_]*)\s*(?::\s*[^=]+)?=\s*(-?[\d_]+\.?[\d_]*)\s*(?:#.*)?$")


def _count_module_constants(path: Path) -> int:
    if not path.exists():
        return 0
    n = 0
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if _CONST_RE.match(line):
            n += 1
    return n


def check_overfit_capacity(conn: sqlite3.Connection, root: Path | None = None) -> dict[str, Any]:
    """FAIL if (tunable numeric constants across the decision-path files) /
    (independent evaluation dates, scan_dates with >=20 distinct symbols) >
    1.0. This is EXPECTED to fail -- it is measuring real unfalsifiability,
    not a code defect this module can fix. `root` defaults to the real
    manas_os/ directory; the optional override exists only so tests can
    point OVERFIT_FILES at fixture files instead of the live repo."""
    name = "overfit_capacity"
    manas_root = root if root is not None else Path(__file__).resolve().parents[1]

    per_file: dict[str, int] = {}
    total = 0
    for rel in OVERFIT_FILES:
        n = _count_module_constants(manas_root / rel)
        per_file[rel] = n
        total += n

    n_dates = conn.execute(
        "SELECT COUNT(*) FROM ("
        "  SELECT scan_date FROM scan_candidates GROUP BY scan_date HAVING COUNT(DISTINCT symbol) >= 20"
        ")"
    ).fetchone()[0]

    ratio = (total / n_dates) if n_dates else None
    status = "FAIL" if (n_dates == 0 or (ratio is not None and ratio > 1.0)) else "PASS"
    ratio_s = f"{ratio:.1f}" if ratio is not None else "undefined (0 dates)"
    detail = (
        f"{total} tunable numeric constant(s) across {len(OVERFIT_FILES)} decision-path file(s) "
        f"vs {n_dates} independent evaluation date(s) (scan_date with >=20 distinct symbols) "
        f"-- ratio {ratio_s}:1. Any threshold fit against this many dates is unfalsifiable."
    )
    evidence = {
        "per_file_counts": per_file,
        "total_params": total,
        "independent_dates": n_dates,
        "ratio": ratio,
    }
    return _result(name, status, detail, evidence)


# ---------------------------------------------------------------------------
# f. check_survivorship
# ---------------------------------------------------------------------------


def _alive_symbols(conn: sqlite3.Connection) -> set[str]:
    max_date = conn.execute(
        "SELECT MAX(trade_date) FROM daily_prices WHERE series = 'EQ'"
    ).fetchone()[0]
    if not max_date:
        return set()
    rows = conn.execute(
        "SELECT DISTINCT symbol FROM daily_prices "
        "WHERE series = 'EQ' AND trade_date >= date(?, '-60 days')",
        (max_date,),
    ).fetchall()
    return {r[0] for r in rows}


def check_survivorship(conn: sqlite3.Connection) -> dict[str, Any]:
    """Compare the share of now-dead symbols (no EQ price bar in the last 60
    days relative to MAX(trade_date)) between scan_candidates and refusals.
    WARN if the ratio between cohorts' dead-symbol rate exceeds 3x. Also
    reports, per cohort, how many rows never resolve a T+10 forward close at
    all (via a LEAD(close, 10) window over each symbol's own EQ session
    sequence, mirroring scanner/scorecard.py's horizon convention) and how
    many of those are dead symbols -- a delisting that silently drops out of
    an average flatters that cohort's stats."""
    name = "survivorship"
    if not _table_exists(conn, "scan_candidates") or not _table_exists(conn, "refusals"):
        return _result(
            name, "WARN", "scan_candidates and/or refusals table does not exist; cannot compare cohorts.", {}
        )

    alive = _alive_symbols(conn)

    # Materialize the forward-10-session close lookup ONCE in TEMP space
    # (not the read-only main DB -- SQLite TEMP tables live in a separate
    # temp database even on a mode=ro connection) so both cohorts reuse it
    # instead of re-scanning all of daily_prices twice.
    conn.execute("DROP TABLE IF EXISTS fwd10")
    conn.execute(
        "CREATE TEMP TABLE fwd10 AS "
        "SELECT symbol, trade_date, "
        "       LEAD(close, 10) OVER (PARTITION BY symbol ORDER BY trade_date) AS close_t10 "
        "FROM daily_prices WHERE series = 'EQ'"
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_fwd10 ON fwd10(symbol, trade_date)")

    def _cohort_stats(table: str, date_col: str) -> dict[str, Any]:
        symbols = {r[0] for r in conn.execute(f"SELECT DISTINCT symbol FROM {table}").fetchall()}
        dead = symbols - alive
        dead_rate = (len(dead) / len(symbols)) if symbols else 0.0

        missing = conn.execute(
            f"SELECT t.symbol FROM {table} t "
            f"LEFT JOIN fwd10 ON fwd10.symbol = t.symbol AND fwd10.trade_date = t.{date_col} "
            f"WHERE fwd10.close_t10 IS NULL"
        ).fetchall()
        n_missing = len(missing)
        n_missing_dead = sum(1 for (sym,) in missing if sym in dead)

        return {
            "n_symbols": len(symbols),
            "n_dead_symbols": len(dead),
            "dead_rate": round(dead_rate, 4),
            "n_rows_missing_t10": n_missing,
            "n_rows_missing_t10_dead_symbol": n_missing_dead,
        }

    scan_stats = _cohort_stats("scan_candidates", "scan_date")
    refused_stats = _cohort_stats("refusals", "scan_date")

    a, b = scan_stats["dead_rate"], refused_stats["dead_rate"]
    if a == 0 and b == 0:
        ratio: float | None = 1.0
    elif a == 0 or b == 0:
        ratio = None  # one side is zero -- "Nx" is meaningless, report as unbounded
    else:
        ratio = max(a, b) / min(a, b)

    status = "WARN" if (ratio is None or ratio > 3.0) else "PASS"
    ratio_s = f"{ratio:.1f}" if ratio is not None else "unbounded (one cohort has 0 dead symbols)"
    detail = (
        f"scan_candidates dead-symbol rate {a:.1%} ({scan_stats['n_dead_symbols']}/{scan_stats['n_symbols']}) "
        f"vs refusals dead-symbol rate {b:.1%} ({refused_stats['n_dead_symbols']}/{refused_stats['n_symbols']}) "
        f"-- ratio {ratio_s}."
    )
    evidence = {
        "scan_candidates": scan_stats,
        "refusals": refused_stats,
        "dead_rate_ratio": ratio,
    }
    return _result(name, status, detail, evidence)


# ---------------------------------------------------------------------------
# g. check_lookahead
# ---------------------------------------------------------------------------

# Matches SQL like MAX(trade_date), MAX(scan_date), MAX("as_of_date") --
# case-SENSITIVE on the literal "MAX(" so Python's builtin max(...) (lower-
# case, e.g. `max(candidates)`) never matches; restricted to identifiers
# containing "date" so it does NOT flag MAX(high), MAX(mars_score), etc.
# Every date-ish column in this repo's SQL is lowercase (trade_date,
# scan_date, as_of_date, snapshot_date, ...), so the inner match stays
# case-sensitive too. High false-positive rate is expected for anything
# outside the decision path (freshness/display code legitimately wants
# "latest") -- see _is_decision_path.
_MAX_DATE_RE = re.compile(r"MAX\(\s*[\"'`]?[\w.]*date[\w.]*[\"'`]?\s*\)")

_DECISION_PREFIXES = ("scanner/", "risk/", "engine/")
_DECISION_EXACT = ("regime/governor.py",)

_SKIP_DIR_PARTS = ("tests", "__pycache__")

# Reviewed exemptions: file:line -> WHY it is not look-ahead. Each entry was
# verified by reading every caller. An entry with an empty reason is itself a
# failure (see check_lookahead) so this list cannot rot into a silent mute.
#
# footprint.symbol_payload / board_payload take `requested_date` and only fall
# back to MAX(trade_date) when the caller passes None. Both callers are the
# api/app.py:4831/4843 endpoints, which always pass requested_date=date; the
# MAX branch is the interactive "show me the latest board" default and is not
# reachable from candidates.run / discovery.run / backtest replay. Verified
# 2026-07-25 by enumerating callers.
_LOOKAHEAD_EXEMPTIONS: dict[str, str] = {
    "scanner/footprint.py:329": "API payload default; both callers pass requested_date explicitly",
    "scanner/footprint.py:380": "API payload default; both callers pass requested_date explicitly",
}


def _is_decision_path(rel_posix: str) -> bool:
    if rel_posix in _DECISION_EXACT:
        return True
    return rel_posix.startswith(_DECISION_PREFIXES)


def check_lookahead(root: Path | None = None) -> dict[str, Any]:
    """Static scan of manas_os/**/*.py (skip tests/, __pycache__/) for
    MAX(<date col>) SQL with no `<=` bound in a nearby window (same line, or
    2 lines above/below -- covers the common `WHERE date_col <= ?` on the
    next line pattern used throughout this repo). FAILs only for hits inside
    the decision path (scanner/, risk/, regime/governor.py, engine/) --
    freshness/display/API code legitimately wants "latest" and is reported
    as INFO instead, per the build spec's explicit high-false-positive-rate
    warning. `root` defaults to the real manas_os/ directory; the optional
    override exists only so tests can scan a fixture tree."""
    name = "lookahead"
    manas_root = root if root is not None else Path(__file__).resolve().parents[1]

    decision_hits: list[str] = []
    info_hits: list[str] = []
    exempted_hits: list[str] = []
    # An exemption with no stated reason is a silent mute -- fail on it.
    unreasoned = sorted(k for k, v in _LOOKAHEAD_EXEMPTIONS.items() if not (v or "").strip())

    for path in sorted(manas_root.rglob("*.py")):
        rel = path.relative_to(manas_root)
        parts = rel.parts
        if any(p in _SKIP_DIR_PARTS for p in parts):
            continue
        rel_posix = rel.as_posix()
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        lines = text.splitlines()
        for i, line in enumerate(lines):
            if not _MAX_DATE_RE.search(line):
                continue
            window = "\n".join(lines[max(0, i - 2) : i + 3])
            if "<=" in window:
                continue
            key = f"{rel_posix}:{i + 1}"
            hit = f"{key}: {line.strip()}"
            if not _is_decision_path(rel_posix):
                info_hits.append(hit)
            elif key in _LOOKAHEAD_EXEMPTIONS:
                exempted_hits.append(f"{hit}  [exempt: {_LOOKAHEAD_EXEMPTIONS[key]}]")
            else:
                decision_hits.append(hit)

    status = "FAIL" if (decision_hits or unreasoned) else "PASS"
    detail = (
        f"{len(decision_hits)} unbounded MAX(<date>) hit(s) in the decision path "
        f"(scanner/, risk/, regime/governor.py, engine/); {len(exempted_hits)} reviewed exemption(s); "
        f"{len(info_hits)} elsewhere reported as INFO only."
    )
    if unreasoned:
        detail += f" {len(unreasoned)} exemption(s) carry no reason: {', '.join(unreasoned)}."
    evidence = {
        "decision_path_hits": decision_hits,
        "reviewed_exemptions": exempted_hits,
        "exemptions_without_reason": unreasoned,
        "info_hits_elsewhere": info_hits,
    }
    return _result(name, status, detail, evidence)
