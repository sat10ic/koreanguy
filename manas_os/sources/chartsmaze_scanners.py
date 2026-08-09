"""ChartsMaze screener-hits + quality-signals ingestion.

ChartsMaze exports (see manas_os/sources/chartsmaze.py for the P0/P1 reader
of the same dated-folder tree) also carry per-stock technical screener hits
under ``scanners/*.csv`` and ``templates/*.csv``, plus quality/negative
signals under ``tools/asm.csv``, ``analytics/results-calendar.csv`` and
``tools/order-wins-new.csv``. This module owns two tables end-to-end:

    screener_hits    -- one row per (trade_date, symbol, screener)
    symbol_quality   -- one row per (trade_date, symbol)

This is ingestion + a read helper ONLY. No confluence ranking / setup-quality
gating is built here — :func:`confluence_for_date` is a pure aggregation read
that a later Setups-feed task will consume.

Public surface:
    run(conn, run_date) -> int                 # rows written across both tables
    confluence_for_date(conn, run_date) -> dict
"""
from __future__ import annotations

import csv
import time
from pathlib import Path

from manas_os.sources import chartsmaze

_SOURCE = "chartsmaze_scanners"
_STAGE = "ingest_chartsmaze_scanners"

# filename (bare, as found under scanners/ or templates/) -> (screener_name, bearish)
# screener_name follows chartsmaze.py's convention of using the CSV stem
# (see e.g. "sector-analytics-<metric>-<level>" filenames) — bare stem, no
# "-template"/"-scanner" suffix stripped, so callers can round-trip. Only
# 'shorting-scanner' is bearish (sentiment-inverted); everything else is
# bullish/neutral technical-setup data.
SCREENER_REGISTRY: dict[str, tuple[str, bool]] = {
    # scanners/
    "vcp.csv":                          ("vcp", False),
    "tight-setup-daily.csv":            ("tight-setup-daily", False),
    "tight-setup-weekly.csv":           ("tight-setup-weekly", False),
    "momentum-scanner.csv":             ("momentum-scanner", False),
    "shakeout-10EMA.csv":               ("shakeout-10EMA", False),
    "shakeout-21EMA.csv":               ("shakeout-21EMA", False),
    "shakeout-50EMA.csv":               ("shakeout-50EMA", False),
    "shakeout-200EMA.csv":              ("shakeout-200EMA", False),
    "gap-up.csv":                       ("gap-up", False),
    "gap-filling.csv":                  ("gap-filling", False),
    "earnings-gap-up.csv":              ("earnings-gap-up", False),
    "flag-pennants.csv":                ("flag-pennants", False),
    "highest-volume.csv":               ("highest-volume", False),
    "horizontal-resistance-daily.csv":  ("horizontal-resistance-daily", False),
    "inside-bar-daily.csv":             ("inside-bar-daily", False),
    "inside-bar-weekly.csv":            ("inside-bar-weekly", False),
    "ipo-setups.csv":                   ("ipo-setups", False),
    "past-IPO-listings.csv":            ("past-IPO-listings", False),
    "past-winners.csv":                 ("past-winners", False),
    "positive-earnings-reaction.csv":   ("positive-earnings-reaction", False),
    "rs-high-before-price-high.csv":    ("rs-high-before-price-high", False),
    "shorting-scanner.csv":             ("shorting-scanner", True),   # bearish
    "top-gainers.csv":                  ("top-gainers", False),
    "volume-footprint.csv":             ("volume-footprint", False),
    "volume-spike.csv":                 ("volume-spike", False),
    "circuit-revision.csv":             ("circuit-revision", False),
    # templates/ (named trader templates; bare stem without "-template")
    "chhirag-template.csv":             ("chhirag", False),
    "himanshu-template.csv":            ("himanshu", False),
    "hiren-template.csv":               ("hiren", False),
    "nitin-template.csv":               ("nitin", False),
    "shashank-template.csv":            ("shashank", False),
}


def _to_float(raw) -> float | None:
    if raw is None:
        return None
    s = str(raw).strip().replace(",", "")
    if s in ("", "-", "--", "NA", "N/A", "N.A.", "n.a."):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _to_int01(raw) -> int | None:
    if raw is None:
        return None
    s = str(raw).strip().lower()
    if s in ("", "-", "--", "na", "n/a", "n.a."):
        return None
    if s in ("yes", "y", "true", "1"):
        return 1
    if s in ("no", "n", "false", "0"):
        return 0
    return None


def _symbol_col(fieldnames: list[str]) -> str | None:
    """Find the symbol column: usually 'Stock Name', some analytics files use 'ticker'."""
    for name in fieldnames:
        norm = name.strip().lstrip("﻿").lower()
        if norm in ("stock name", "ticker"):
            return name
    return None


def _read_rows(path: Path) -> list[dict]:
    with open(path, "r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def parse_screener_csv(text: str) -> list[dict]:
    """Pure parser for a scanners/*.csv or templates/*.csv row-shape.

    Returns dicts with keys: symbol, rs_rating, basic_industry, market_cap_cr.
    Header columns vary by file (VCP has extra swing-date columns; some carry
    a "Market Cap"/"Market Cap(Cr.)" column) — read dynamically via DictReader,
    never assume column order.
    """
    rows = list(csv.DictReader(text.splitlines()))
    if not rows:
        return []
    fieldnames = rows[0].keys() if rows else []
    sym_col = _symbol_col(list(fieldnames))
    out = []
    for row in rows:
        sym_raw = row.get(sym_col) if sym_col else None
        symbol = (sym_raw or "").strip().upper()
        if not symbol:
            continue
        market_cap = None
        for cap_col in ("Market Cap", "Market Cap(Cr.)"):
            if cap_col in row:
                v = _to_float(row.get(cap_col))
                if v is not None:
                    market_cap = v
                    break
        out.append({
            "symbol": symbol,
            "rs_rating": _to_float(row.get("RS Rating")),
            "basic_industry": (row.get("Basic Industry") or "").strip() or None,
            "market_cap_cr": market_cap,
        })
    return out


def parse_asm_csv(text: str) -> list[dict]:
    """tools/asm.csv -> [{symbol, asm_stage}]."""
    rows = list(csv.DictReader(text.splitlines()))
    out = []
    for row in rows:
        sym_col = _symbol_col(list(row.keys()))
        symbol = (row.get(sym_col) if sym_col else "" or "").strip().upper()
        if not symbol:
            continue
        stage = (row.get("ASM Stage") or "").strip() or None
        out.append({"symbol": symbol, "asm_stage": stage})
    return out


def parse_results_calendar_csv(text: str) -> list[dict]:
    """analytics/results-calendar.csv -> [{symbol, eps_qoq, eps_yoy, sales_yoy, opm_yoy}]."""
    rows = list(csv.DictReader(text.splitlines()))
    out = []
    for row in rows:
        sym_col = _symbol_col(list(row.keys()))
        symbol = (row.get(sym_col) if sym_col else "" or "").strip().upper()
        if not symbol:
            continue
        out.append({
            "symbol": symbol,
            "eps_qoq": _to_float(row.get("QoQ % EPS Latest")),
            "eps_yoy": _to_float(row.get("YoY % EPS Latest")),
            "sales_yoy": _to_float(row.get("YoY % Sales Latest")),
            "opm_yoy": _to_float(row.get("YoY % OPM Latest")),
        })
    return out


def parse_order_wins_csv(text: str) -> list[dict]:
    """tools/order-wins-new.csv -> [{symbol, market_cap_cr, exchange, is_fno}]."""
    rows = list(csv.DictReader(text.splitlines()))
    out = []
    for row in rows:
        sym_col = _symbol_col(list(row.keys()))
        symbol = (row.get(sym_col) if sym_col else "" or "").strip().upper()
        if not symbol:
            continue
        out.append({
            "symbol": symbol,
            "market_cap_cr": _to_float(row.get("Market Cap")),
            "exchange": (row.get("Exchange") or "").strip() or None,
            "is_fno": _to_int01(row.get("Is F&O Stock")),
        })
    return out


def _log_run(conn, run_date, status, rows, duration, detail) -> None:
    conn.execute(
        "INSERT INTO pipeline_runs (run_date, stage, source, status, "
        "rows_affected, duration_s, detail) VALUES (?,?,?,?,?,?,?)",
        (run_date, _STAGE, _SOURCE, status, rows, duration, detail),
    )


def _upsert_screener_hit(conn, trade_date, symbol, screener, bearish, rs_rating, basic_industry) -> None:
    conn.execute(
        "INSERT INTO screener_hits "
        "(trade_date, symbol, screener, bearish, rs_rating, basic_industry) "
        "VALUES (?, ?, ?, ?, ?, ?) "
        "ON CONFLICT(trade_date, symbol, screener) DO UPDATE SET "
        "bearish=excluded.bearish, rs_rating=excluded.rs_rating, "
        "basic_industry=excluded.basic_industry, ingested_at=datetime('now')",
        (trade_date, symbol, screener, int(bearish), rs_rating, basic_industry),
    )


def _upsert_symbol_quality(conn, trade_date, symbol, fields: dict) -> None:
    """Merge-upsert one symbol_quality row: only overwrite a column when the
    new value is non-null, and only when a column is present in this row's
    fields (so multiple partial-field calls compose without clobbering)."""
    existing = conn.execute(
        "SELECT market_cap_cr, asm_stage, eps_qoq, eps_yoy, sales_yoy, opm_yoy, "
        "is_fno, exchange FROM symbol_quality WHERE trade_date=? AND symbol=?",
        (trade_date, symbol),
    ).fetchone()
    merged = {
        "market_cap_cr": None, "asm_stage": None, "eps_qoq": None, "eps_yoy": None,
        "sales_yoy": None, "opm_yoy": None, "is_fno": None, "exchange": None,
    }
    if existing is not None:
        for k in merged:
            merged[k] = existing[k]
    for k, v in fields.items():
        if v is not None:
            merged[k] = v
    conn.execute(
        "INSERT INTO symbol_quality "
        "(trade_date, symbol, market_cap_cr, asm_stage, eps_qoq, eps_yoy, "
        " sales_yoy, opm_yoy, is_fno, exchange) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
        "ON CONFLICT(trade_date, symbol) DO UPDATE SET "
        "market_cap_cr=excluded.market_cap_cr, asm_stage=excluded.asm_stage, "
        "eps_qoq=excluded.eps_qoq, eps_yoy=excluded.eps_yoy, "
        "sales_yoy=excluded.sales_yoy, opm_yoy=excluded.opm_yoy, "
        "is_fno=excluded.is_fno, exchange=excluded.exchange, "
        "ingested_at=datetime('now')",
        (trade_date, symbol, merged["market_cap_cr"], merged["asm_stage"],
         merged["eps_qoq"], merged["eps_yoy"], merged["sales_yoy"], merged["opm_yoy"],
         merged["is_fno"], merged["exchange"]),
    )


def run(conn, run_date: str) -> int:
    """Ingest screener_hits + symbol_quality for run_date. Never raises.

    Resolves the dated dump folder via chartsmaze.date_dir (same exact-match
    lookup chartsmaze.py itself uses — reused here directly, not duplicated).
    Each source file is parsed independently and wrapped in its own
    try/except so one malformed/missing CSV doesn't kill the whole run.
    """
    started = time.monotonic()
    folder = chartsmaze.date_dir(run_date)
    if not folder.is_dir():
        _log_run(conn, run_date, "skip", 0, time.monotonic() - started,
                 chartsmaze.missing_folder_message(run_date))
        conn.commit()
        return 0

    hits_written = 0
    quality_symbols: set[str] = set()
    detail_parts = []

    # --- scanners/ + templates/ -> screener_hits ---------------------------
    for subdir in ("scanners", "templates"):
        d = folder / subdir
        if not d.is_dir():
            continue
        for fname, (screener_name, bearish) in SCREENER_REGISTRY.items():
            path = d / fname
            if not path.is_file():
                continue
            try:
                text = path.read_text(encoding="utf-8-sig")
                rows = parse_screener_csv(text)
                for r in rows:
                    _upsert_screener_hit(
                        conn, run_date, r["symbol"], screener_name, bearish,
                        r["rs_rating"], r["basic_industry"],
                    )
                    hits_written += 1
                    if r["market_cap_cr"] is not None:
                        _upsert_symbol_quality(
                            conn, run_date, r["symbol"],
                            {"market_cap_cr": r["market_cap_cr"]},
                        )
                        quality_symbols.add(r["symbol"])
            except Exception as exc:
                detail_parts.append(f"{fname}=err({type(exc).__name__})")

    detail_parts.append(f"hits={hits_written}")

    # --- tools/asm.csv -> symbol_quality.asm_stage --------------------------
    try:
        path = folder / "tools" / "asm.csv"
        if path.is_file():
            for r in parse_asm_csv(path.read_text(encoding="utf-8-sig")):
                _upsert_symbol_quality(conn, run_date, r["symbol"], {"asm_stage": r["asm_stage"]})
                quality_symbols.add(r["symbol"])
            detail_parts.append("asm=ok")
    except Exception as exc:
        detail_parts.append(f"asm=err({type(exc).__name__})")

    # --- analytics/results-calendar.csv -> eps/sales/opm --------------------
    try:
        path = folder / "analytics" / "results-calendar.csv"
        if path.is_file():
            for r in parse_results_calendar_csv(path.read_text(encoding="utf-8-sig")):
                _upsert_symbol_quality(conn, run_date, r["symbol"], {
                    "eps_qoq": r["eps_qoq"], "eps_yoy": r["eps_yoy"],
                    "sales_yoy": r["sales_yoy"], "opm_yoy": r["opm_yoy"],
                })
                quality_symbols.add(r["symbol"])
            detail_parts.append("results_calendar=ok")
    except Exception as exc:
        detail_parts.append(f"results_calendar=err({type(exc).__name__})")

    # --- tools/order-wins-new.csv -> market_cap_cr/exchange/is_fno ---------
    try:
        path = folder / "tools" / "order-wins-new.csv"
        if path.is_file():
            for r in parse_order_wins_csv(path.read_text(encoding="utf-8-sig")):
                _upsert_symbol_quality(conn, run_date, r["symbol"], {
                    "market_cap_cr": r["market_cap_cr"],
                    "exchange": r["exchange"],
                    "is_fno": r["is_fno"],
                })
                quality_symbols.add(r["symbol"])
            detail_parts.append("order_wins=ok")
    except Exception as exc:
        detail_parts.append(f"order_wins=err({type(exc).__name__})")

    detail_parts.append(f"quality_symbols={len(quality_symbols)}")
    total_rows = hits_written + len(quality_symbols)
    _log_run(conn, run_date, "ok", total_rows, time.monotonic() - started,
             " · ".join(detail_parts))
    conn.commit()
    return total_rows


def confluence_for_date(conn, run_date: str) -> dict:
    """Pure read/aggregation: per-symbol count of DISTINCT non-bearish
    screeners that hit on run_date, plus rs_rating/basic_industry.

    No ranking/scoring here — a later task builds the confluence-ranked,
    quality-gated Setups feed on top of this.

    Returns {symbol: {"count": int, "screeners": [...], "rs_rating": float|None,
                       "basic_industry": str|None}}
    """
    rows = conn.execute(
        "SELECT symbol, screener, rs_rating, basic_industry FROM screener_hits "
        "WHERE trade_date = ? AND bearish = 0 ORDER BY symbol, screener",
        (run_date,),
    ).fetchall()
    out: dict[str, dict] = {}
    for row in rows:
        symbol = row["symbol"]
        entry = out.setdefault(symbol, {
            "count": 0, "screeners": [], "rs_rating": None, "basic_industry": None,
        })
        entry["screeners"].append(row["screener"])
        entry["count"] = len(entry["screeners"])
        if entry["rs_rating"] is None and row["rs_rating"] is not None:
            entry["rs_rating"] = row["rs_rating"]
        if entry["basic_industry"] is None and row["basic_industry"]:
            entry["basic_industry"] = row["basic_industry"]
    return out
