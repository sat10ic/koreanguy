"""ChartsMaze read adapters + P0 freshness check + P1 sector/industry ingest.

ChartsMaze exports a dated folder per trading day::

    <chartsmaze_dir>/<YYYY-MM-DD>/
        analytics/   market-breadth.csv, sector-analytics-*.csv, rrg-*.csv,
                     industry-analytics.csv, ...
        scanners/    gap-up.csv, inside-bar-daily.csv, ...
        templates/   nitin-template.csv, ...
        tools/       order-wins-new.csv, ...

P0 scope: reader helpers (market-breadth, sector-analytics) + a ``run`` that
records folder availability and CSV count in pipeline_runs.
P1 scope (this module): populate sector_metrics, industry_metrics, and
stock_industry_rs from the sector/industry relative-strength exports and
industry-analytics.csv.

Public surface:
    read_market_breadth(run_date) -> DataFrame
    read_sector_analytics(run_date, metric='Relative Strength', level='sectors') -> DataFrame
    read_industry_analytics(run_date) -> DataFrame
    parse_industry_analytics(text) -> list[dict]      # pure; for unit tests
    run(conn, run_date) -> int   # csv count; logs pipeline_runs + populates tables
"""
from __future__ import annotations

import csv
import io
import re
import time
from pathlib import Path
from typing import Any

import pandas as pd

from manas_os import config
from manas_os.regime.sectors import canonical_sector_key

_DEFAULT_DIR = "data/chartsmaze"
_SOURCE = "chartsmaze"
_STAGE = "ingest_chartsmaze"


def chartsmaze_dir() -> Path:
    raw = config.get("sources.chartsmaze_dir", _DEFAULT_DIR)
    p = Path(raw)
    if not p.is_absolute():
        p = (Path(__file__).resolve().parents[1] / p).resolve()
    return p


def date_dir(run_date: str) -> Path:
    """The dated folder for ``run_date`` (YYYY-MM-DD)."""
    return chartsmaze_dir() / run_date


# ─────────────────────────────────────────────────────────────────────────────
# Fetch-failure classification (root-cause preservation).
#
# extractor.py (chartsmaze_extractor/) shells out via a subprocess from both
# the CLI (`manas run-eod`) and the API's background pipeline thread. When it
# fails, the ONLY information the caller used to keep was the process exit
# code -- an expired login (needs `python login.py` + interactive OTP) and
# any other subprocess failure both rendered identically as "exit 1"
# downstream, in `/api/data/coverage` and the desk staleness banner. These
# helpers classify a captured stdout+stderr into a machine-readable
# ``reason_code`` plus a human message that is SAFE to persist and display --
# never a cookie/token/password/OTP value, see `_redact` below.
# ─────────────────────────────────────────────────────────────────────────────

# Substrings extractor.py / login.py are known to emit on an expired scraper
# session (see chartsmaze_extractor/run_cron.py: "session/session fail ...
# error=session_invalid" then "Session invalid. Run python login.py and
# complete the OTP flow."). Matched case-insensitively against the combined
# stdout+stderr tail.
_AUTH_EXPIRED_MARKERS = ("session_invalid", "session invalid", "run python login.py")

# Conservative redaction: strip anything shaped like a credential/session
# value before it is ever written to job_steps.error or returned by an API
# response. Errs toward over-redacting -- a diagnostic tail that says
# "<redacted>" is still useful; one that leaks a live cookie is not.
_REDACT_PATTERNS = (
    re.compile(r"(?i)\b(cookie|token|password|passwd|secret|otp|auth[_-]?code|api[_-]?key)\s*[:=]\s*\S+"),
    re.compile(r"(?i)\bbearer\s+\S+"),
)


def _redact(text: str) -> str:
    """Best-effort scrub of credential/session-shaped substrings."""
    for pattern in _REDACT_PATTERNS:
        text = pattern.sub("<redacted>", text)
    return text


def classify_fetch_output(stdout: str | None, stderr: str | None, returncode: int) -> tuple[str, str]:
    """Classify a failed ChartsMaze extractor subprocess run.

    Returns ``(reason_code, message)``:
      - ``reason_code`` is machine-readable (``"auth_expired"`` or
        ``"unknown"``) so callers like ``/api/chartsmaze/status`` can branch
        without re-parsing free text.
      - ``message`` is redacted and safe to persist/display; it always keeps
        a short tail of the raw output (see ``_redact``) so an unrecognized
        future failure mode is still diagnosable rather than reduced back to
        a bare exit code.
    """
    combined = f"{stdout or ''}\n{stderr or ''}"
    tail = _redact(combined.strip())[-500:]
    tail_suffix = f" | tail: {tail}" if tail else ""
    lowered = combined.lower()
    if any(marker in lowered for marker in _AUTH_EXPIRED_MARKERS):
        return "auth_expired", "Session invalid. Run python login.py and complete the OTP flow." + tail_suffix
    return "unknown", f"exit {returncode}" + tail_suffix


_REASON_CODE_RE = re.compile(r"^reason_code=(\w+)\s+(.*)$", re.DOTALL)


def parse_reason_code(error_text: str | None) -> tuple[str | None, str | None]:
    """Split a job_steps.error string of the form ``reason_code=<code> <msg>``.

    Returns ``(None, error_text)`` when the string doesn't carry the prefix
    (older rows, or a step that failed before classification existed).
    """
    if not error_text:
        return None, None
    match = _REASON_CODE_RE.match(error_text)
    if not match:
        return None, error_text
    return match.group(1), match.group(2)


def fetch_failure_reason(conn) -> dict[str, Any] | None:
    """Most recent recorded ``fetch_chartsmaze`` job_steps outcome, classified.

    Returns ``None`` when fetch_chartsmaze has never recorded a step (fresh
    install, or every run so far used cached files with fetch_sources=False)
    -- never raises, this is a best-effort read for status surfaces.
    """
    try:
        row = conn.execute(
            "SELECT s.status, s.error, s.finished_at, j.run_date "
            "FROM job_steps s JOIN jobs j ON j.job_id = s.job_id "
            "WHERE s.name = 'fetch_chartsmaze' ORDER BY s.step_id DESC LIMIT 1"
        ).fetchone()
    except Exception:
        return None
    if row is None:
        return None
    result = dict(row)
    reason_code, reason = (None, None)
    if result.get("status") == "fail":
        reason_code, reason = parse_reason_code(result.get("error"))
    result["reason_code"] = reason_code
    result["reason"] = reason
    return result


_DATE_DIR_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def latest_available_dump(before: str | None = None) -> str | None:
    """Newest dated dump subfolder actually present under chartsmaze_dir().

    Used to turn a bare "folder missing" symptom into an actionable message
    that names what IS there. When ``before`` is given, only dumps on or
    before that date are considered; the default (None) reports the newest
    dump present overall. Returns None when the root is absent/empty.
    """
    root = chartsmaze_dir()
    if not root.is_dir():
        return None
    names = [p.name for p in root.iterdir() if p.is_dir() and _DATE_DIR_RE.match(p.name)]
    if before is not None:
        names = [n for n in names if n <= before]
    return max(names) if names else None


def missing_folder_message(run_date: str) -> str:
    """Accurate, actionable text for a missing dated ChartsMaze dump.

    Distinguishes "the whole ChartsMaze root is absent" (nothing has ever
    landed -- misconfigured path, or a fresh checkout) from "root is fine,
    this date's dump just hasn't arrived yet" (names the newest dump that
    IS present, so a reader isn't sent hunting for a folder that exists a
    few days back under a different date). Reused by both chartsmaze.py and
    chartsmaze_scanners.py (chartsmaze_scanners already reuses date_dir --
    same precedent, no duplicated folder-resolution logic).
    """
    root = chartsmaze_dir()
    if not root.is_dir():
        return f"chartsmaze root missing: {root}"
    latest = latest_available_dump()
    if latest:
        return f"no chartsmaze dump for {run_date} (latest available: {latest})"
    return f"chartsmaze root present but empty: {root}"


def read_market_breadth(run_date: str) -> pd.DataFrame:
    """Read analytics/market-breadth.csv.

    The file is transposed: rows are metrics ("Type of Info"), columns are
    dates. Real exports are RAGGED — some metric rows carry more date columns
    than the header — so we read with the tolerant python engine and pad short
    rows to the widest row. The first column holds the metric label; remaining
    columns are ISO dates.
    """
    path = date_dir(run_date) / "analytics" / "market-breadth.csv"
    with open(path, "r", encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.reader(fh))
    if not rows:
        return pd.DataFrame()
    width = max(len(r) for r in rows)
    header = rows[0] + [f"col_{i}" for i in range(len(rows[0]), width)]
    padded = [r + [None] * (width - len(r)) for r in rows[1:]]
    return pd.DataFrame(padded, columns=header)


def read_sector_analytics(
    run_date: str,
    metric: str = "Relative Strength",
    level: str = "sectors",
) -> pd.DataFrame:
    """Read analytics/sector-analytics-<metric>-<level>.csv.

    ``metric`` ∈ {'Relative Strength', 'Moving Average', 'Near 52w High'};
    ``level`` ∈ {'sectors', 'industries', 'stocks'}. Sector/industry files carry
    ``name,pct`` columns.
    """
    fname = f"sector-analytics-{metric}-{level}.csv"
    path = date_dir(run_date) / "analytics" / fname
    return pd.read_csv(path, encoding="utf-8-sig")


def read_stock_relative_strength(run_date: str) -> pd.DataFrame:
    """Read per-stock industry RS from ChartsMaze.

    Source: analytics/sector-analytics-Relative Strength-stocks.csv with
    ticker, industry, rs columns. ``run`` persists these rows so APIs do not
    depend on the source dump remaining mounted at request time.
    """
    df = read_sector_analytics(run_date, "Relative Strength", "stocks")
    return df.rename(columns={c: c.strip().lower() for c in df.columns})


# industry-analytics.csv — the "Themes" tab source. Real header (with a UTF-8
# BOM on the first column), columns carry trailing "(%)" / "(cr.)" suffixes:
#     ﻿Basic Industry, Industry 1D Performance(%), Industry 1W Performance(%),
#     Industry 1M Performance(%), Industry 3M Performance(%),
#     Industry 1D Performance Rank, Industry 1W Rank, Industry 1M Rank,
#     Industry 3M Rank, Number of Stocks, Group Market Cap, Industry % from 52W High

# Normalized target column -> list of raw-header substrings to match (case-insensitive,
# after stripping BOM/spaces). First match wins; keeps us robust to renaming.
_INDUSTRY_COL_MAP: dict[str, list[str]] = {
    "name":              ["basic industry", "industry"],
    "perf_1d":           ["industry 1d performance"],
    "perf_1w":           ["industry 1w performance"],
    "perf_1m":           ["industry 1m performance"],
    "perf_3m":           ["industry 3m performance"],
    "rank_1m":           ["industry 1m performance rank", "industry 1m rank"],
    "rank_3m":           ["industry 3m performance rank", "industry 3m rank"],
    "num_stocks":        ["number of stocks"],
    "market_cap_cr":     ["group market cap"],
    "pct_from_52w_high": ["industry % from 52w high", "% from 52w high"],
}


def _norm_header(h: str) -> str:
    return " ".join(h.strip().lstrip("\ufeff").lower().split())


def _to_float(raw) -> float | None:
    if raw is None:
        return None
    s = str(raw).strip().replace("%", "").replace(",", "")
    if s in ("", "-", "--", "NA", "N/A"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _to_int(raw) -> int | None:
    f = _to_float(raw)
    return int(round(f)) if f is not None else None


def parse_industry_analytics(text: str) -> list[dict]:
    """Pure parser: industry-analytics.csv text -> list of normalized dicts.

    BOM-tolerant, header-substring matching (real columns get renamed by
    ChartsMaze from time to time). Returns one dict per data row with the keys
    of ``_INDUSTRY_COL_MAP``; rows with no name are skipped.
    """
    rows = list(csv.reader(io.StringIO(text)))
    if not rows:
        return []
    header = rows[0]
    norm = [_norm_header(h) for h in header]

    # For each target key, find the first matching column index.
    col_idx: dict[str, int | None] = {}
    for key, candidates in _INDUSTRY_COL_MAP.items():
        col_idx[key] = next(
            (i for i, nh in enumerate(norm) if any(c in nh for c in candidates)),
            None,
        )

    out: list[dict] = []
    for raw_row in rows[1:]:
        if not raw_row:
            continue
        def cell(key: str):
            i = col_idx.get(key)
            return raw_row[i] if i is not None and i < len(raw_row) else None

        name = (cell("name") or "").strip()
        if not name:
            continue
        out.append({
            "name": name,
            "perf_1d":           _to_float(cell("perf_1d")),
            "perf_1w":           _to_float(cell("perf_1w")),
            "perf_1m":           _to_float(cell("perf_1m")),
            "perf_3m":           _to_float(cell("perf_3m")),
            "rank_1m":           _to_int(cell("rank_1m")),
            "rank_3m":           _to_int(cell("rank_3m")),
            "num_stocks":        _to_int(cell("num_stocks")),
            "market_cap_cr":     _to_float(cell("market_cap_cr")),
            "pct_from_52w_high": _to_float(cell("pct_from_52w_high")),
        })
    return out


def read_industry_analytics(run_date: str) -> pd.DataFrame:
    """Read analytics/industry-analytics.csv into a normalized DataFrame.

    Uses the pure :func:`parse_industry_analytics` so the BOM + column-rename
    logic lives in one tested place.
    """
    path = date_dir(run_date) / "analytics" / "industry-analytics.csv"
    text = Path(path).read_text(encoding="utf-8-sig")
    return pd.DataFrame(parse_industry_analytics(text))


def _count_csvs(folder: Path) -> int:
    return sum(1 for _ in folder.rglob("*.csv"))


def _log_run(conn, run_date, status, rows, duration, detail) -> None:
    conn.execute(
        "INSERT INTO pipeline_runs (run_date, stage, source, status, "
        "rows_affected, duration_s, detail) VALUES (?,?,?,?,?,?,?)",
        (run_date, _STAGE, _SOURCE, status, rows, duration, detail),
    )


def _upsert_sector_metrics(conn, run_date: str, rs_rows: pd.DataFrame,
                           ma_rows: pd.DataFrame | None) -> int:
    """Populate sector_metrics for run_date from sector-analytics frames.

    rs_rows: sector-analytics-Relative Strength-sectors.csv (name, pct) → rs_score.
    ma_rows (optional): sector-analytics-Moving Average-sectors.csv — same
    (name, pct) shape, pct is a "% of stocks above their MA" string like '64%'.
    ChartsMaze does not split this into 20/50 DMA, so we store it as
    breadth_50_pct (the MA-participation proxy) and leave breadth_20_pct NULL
    rather than fabricating two distinct values from one.
    """
    if rs_rows is None or rs_rows.empty:
        return 0
    ma_by_name: dict[str, float | None] = {}
    if ma_rows is not None and not ma_rows.empty:
        name_col = next(
            (c for c in ma_rows.columns if c.lower().startswith("name")),
            ma_rows.columns[0],
        )
        for _, r in ma_rows.iterrows():
            raw = str(r[name_col]).strip()
            # Normalize to canonical key so the MA breadth merges onto the same
            # row as the RS value (ChartsMaze labels match between the two files,
            # but canonicalizing is defensive and matches the MARS ingest path).
            key = canonical_sector_key(raw, "chartsmaze")
            breadth_val = None
            for col in ma_rows.columns:
                if col == name_col:
                    continue
                breadth_val = _to_float(r.get(col))
                if breadth_val is not None:
                    break
            ma_by_name[key] = breadth_val

    written = 0
    for _, r in rs_rows.iterrows():
        raw_name = str(r["name"]).strip()
        if not raw_name:
            continue
        sector_key = canonical_sector_key(raw_name, "chartsmaze")
        rs_pct = _to_float(r.get("pct"))
        breadth = ma_by_name.get(sector_key)
        conn.execute(
            "INSERT INTO sector_metrics "
            "(snapshot_date, sector_key, rs_score, breadth_50_pct) "
            "VALUES (?, ?, ?, ?) "
            "ON CONFLICT(snapshot_date, sector_key) DO UPDATE SET "
            "rs_score=excluded.rs_score, breadth_50_pct=excluded.breadth_50_pct, "
            "ingested_at=datetime('now')",
            (run_date, sector_key, rs_pct, breadth),
        )
        written += 1
    return written


def _upsert_industry_metrics(conn, run_date: str, rows: list[dict]) -> int:
    if not rows:
        return 0
    conn.executemany(
        "INSERT INTO industry_metrics "
        "(snapshot_date, name, perf_1d, perf_1w, perf_1m, perf_3m, rank_1m, "
        " rank_3m, num_stocks, market_cap_cr, pct_from_52w_high) "
        "VALUES (:d, :name, :perf_1d, :perf_1w, :perf_1m, :perf_3m, :rank_1m, "
        "        :rank_3m, :num_stocks, :market_cap_cr, :pct_from_52w_high) "
        "ON CONFLICT(snapshot_date, name) DO UPDATE SET "
        "perf_1d=excluded.perf_1d, perf_1w=excluded.perf_1w, "
        "perf_1m=excluded.perf_1m, perf_3m=excluded.perf_3m, "
        "rank_1m=excluded.rank_1m, rank_3m=excluded.rank_3m, "
        "num_stocks=excluded.num_stocks, market_cap_cr=excluded.market_cap_cr, "
        "pct_from_52w_high=excluded.pct_from_52w_high, ingested_at=datetime('now')",
        [{"d": run_date, **r} for r in rows],
    )
    return len(rows)


def _upsert_stock_industry_rs(conn, run_date: str, rows: pd.DataFrame) -> int:
    """Persist exact ticker -> Basic Industry membership and industry-level RS."""
    if rows is None or rows.empty:
        return 0
    required = {"ticker", "industry", "rs"}
    if not required <= set(rows.columns):
        return 0

    values = []
    for _, row in rows.iterrows():
        raw_ticker = row.get("ticker")
        raw_industry = row.get("industry")
        ticker = "" if pd.isna(raw_ticker) else str(raw_ticker).strip().upper()
        industry = "" if pd.isna(raw_industry) else str(raw_industry).strip()
        if not ticker or not industry:
            continue
        values.append((run_date, ticker, industry, _to_float(row.get("rs"))))
    if not values:
        return 0

    conn.executemany(
        "INSERT INTO stock_industry_rs (snapshot_date, ticker, industry, rs) "
        "VALUES (?, ?, ?, ?) "
        "ON CONFLICT(snapshot_date, ticker) DO UPDATE SET "
        "industry=excluded.industry, rs=excluded.rs, ingested_at=datetime('now')",
        values,
    )
    return len(values)


def run(conn, run_date: str) -> int:
    """Freshness check + populate sector, industry, and per-stock RS tables.

    Verifies the date folder exists, counts CSVs (P0 freshness), then ingests
    the P1 tables from sector-analytics-Relative Strength-sectors.csv,
    industry-analytics.csv, and sector-analytics-Relative Strength-stocks.csv
    when present. Each ingest is best-effort: a missing file is not fatal — the
    run still records an 'ok' row with whatever was populated.

    Returns the CSV count (0 if the folder is missing).
    """
    started = time.monotonic()
    folder = date_dir(run_date)
    if not folder.is_dir():
        _log_run(conn, run_date, "skip", 0, time.monotonic() - started,
                 missing_folder_message(run_date))
        conn.commit()
        return 0

    count = _count_csvs(folder)
    sectors_written = 0
    industries_written = 0
    stocks_written = 0
    detail_parts = [f"{folder.name}: {count} csv"]

    # --- Sectors (RS + best-effort MA breadth) -----------------------------
    try:
        rs = read_sector_analytics(run_date, "Relative Strength", "sectors")
        try:
            ma = read_sector_analytics(run_date, "Moving Average", "sectors")
        except Exception:
            ma = None
        sectors_written = _upsert_sector_metrics(conn, run_date, rs, ma)
        detail_parts.append(f"sectors={sectors_written}")
    except Exception as exc:
        detail_parts.append(f"sectors=skip({type(exc).__name__})")

    # --- Industries / Themes ----------------------------------------------
    try:
        ind_rows = parse_industry_analytics(
            (folder / "analytics" / "industry-analytics.csv").read_text(encoding="utf-8-sig")
        )
        industries_written = _upsert_industry_metrics(conn, run_date, ind_rows)
        detail_parts.append(f"industries={industries_written}")
    except Exception as exc:
        detail_parts.append(f"industries=skip({type(exc).__name__})")

    # --- Per-stock Basic Industry membership + RS --------------------------
    try:
        stock_rows = read_stock_relative_strength(run_date)
        stocks_written = _upsert_stock_industry_rs(conn, run_date, stock_rows)
        detail_parts.append(f"stocks={stocks_written}")
    except Exception as exc:
        detail_parts.append(f"stocks=skip({type(exc).__name__})")

    _log_run(conn, run_date, "ok", count, time.monotonic() - started,
             " · ".join(detail_parts))
    conn.commit()
    return count
