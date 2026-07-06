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
P1 scope (this module): populate sector_metrics + industry_metrics from the
sector-analytics-Relative Strength-sectors.csv and industry-analytics.csv files.

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
import time
from pathlib import Path

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
    ticker, industry, rs columns. This is a read-only drill-down source; the
    EOD pipeline does not write a duplicate stock-membership metric.
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


def run(conn, run_date: str) -> int:
    """Freshness check + populate sector_metrics / industry_metrics.

    Verifies the date folder exists, counts CSVs (P0 freshness), then ingests
    the two P1 tables from sector-analytics-Relative Strength-sectors.csv and
    industry-analytics.csv when present. Each ingest is best-effort: a missing
    file is not fatal — the run still records an 'ok' row with whatever was
    populated.

    Returns the CSV count (0 if the folder is missing).
    """
    started = time.monotonic()
    folder = date_dir(run_date)
    if not folder.is_dir():
        _log_run(conn, run_date, "skip", 0, time.monotonic() - started,
                 f"chartsmaze folder missing: {folder}")
        conn.commit()
        return 0

    count = _count_csvs(folder)
    sectors_written = 0
    industries_written = 0
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

    _log_run(conn, run_date, "ok", count, time.monotonic() - started,
             " · ".join(detail_parts))
    conn.commit()
    return count
