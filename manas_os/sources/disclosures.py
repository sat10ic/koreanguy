"""ChartsMaze disclosure-feed ingestion.

Reads the dated ChartsMaze ``tools/`` disclosure CSVs from the latest dump
folder at or before the requested run date, then stores catalyst / surveillance
events point-in-time.
"""
from __future__ import annotations

import csv
import json
import re
import time
from io import StringIO
from pathlib import Path

from manas_os.sources import chartsmaze

_SOURCE = "chartsmaze_disclosures"
_STAGE = "ingest_disclosures"

_FEEDS: dict[str, tuple[str, str]] = {
    "order_wins": ("order-wins-new.csv", "order_win"),
    "announcements": ("corporate-announcements-new.csv", "announcement"),
    "bulk_deals": ("bulk-deals-new.csv", "bulk_deal"),
    "insider": ("insider-trading-new.csv", "insider"),
    "circuit_revisions": ("circuit-limit-revision-history-new.csv", "circuit_revision"),
    "episodic_pivot": ("episodic-pivot.csv", "episodic_pivot"),
}

_SYMBOL_HEADERS = {"stock name", "symbol", "ticker"}


def _norm_header(value: str) -> str:
    return " ".join(str(value).strip().lstrip("\ufeff").lower().split())


def _symbol_col(fieldnames: list[str]) -> str | None:
    for name in fieldnames:
        if _norm_header(name) in _SYMBOL_HEADERS:
            return name
    return None


def _date_col(fieldnames: list[str]) -> str | None:
    exact = {
        "date", "trade date", "announcement date", "deal date",
        "intimation date", "revision date", "created at",
    }
    for name in fieldnames:
        norm = _norm_header(name)
        if norm in exact or norm.endswith(" date"):
            return name
    return None


def _iso_date(raw, fallback: str) -> str:
    s = str(raw or "").strip()
    if not s:
        return fallback
    m = re.search(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})", s)
    if m:
        y, mo, d = m.groups()
        return f"{int(y):04d}-{int(mo):02d}-{int(d):02d}"
    m = re.search(r"(\d{1,2})[-/](\d{1,2})[-/](\d{4})", s)
    if m:
        d, mo, y = m.groups()
        return f"{int(y):04d}-{int(mo):02d}-{int(d):02d}"
    return fallback


def _to_float(raw) -> float | None:
    s = str(raw or "").strip().replace(",", "").replace("%", "")
    if s in ("", "-", "--", "NA", "N/A", "n.a."):
        return None
    try:
        return float(s)
    except ValueError:
        m = re.search(r"-?\d+(?:\.\d+)?", s)
        return float(m.group(0)) if m else None


def _latest_dump_dir(run_date: str) -> Path | None:
    root = chartsmaze.chartsmaze_dir()
    if not root.is_dir():
        return None
    candidates = []
    for child in root.iterdir():
        if child.is_dir() and re.fullmatch(r"\d{4}-\d{2}-\d{2}", child.name):
            if child.name <= run_date:
                candidates.append(child)
    return max(candidates, key=lambda p: p.name) if candidates else None


def _read_csv(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8-sig")
    return list(csv.DictReader(StringIO(text)))


def parse_disclosure_csv(text: str, kind: str, dump_date: str) -> list[dict]:
    """Parse one disclosure CSV using dynamic headers.

    Returns rows with ``trade_date``, ``symbol``, ``kind`` and ``detail`` keys.
    """
    rows = list(csv.DictReader(StringIO(text)))
    if not rows:
        return []
    fields = list(rows[0].keys())
    sym_col = _symbol_col(fields)
    date_col = _date_col(fields)
    out = []
    for row in rows:
        symbol = ((row.get(sym_col) if sym_col else "") or "").strip().upper()
        if not symbol:
            continue
        trade_date = _iso_date(row.get(date_col) if date_col else None, dump_date)
        out.append({
            "trade_date": trade_date,
            "symbol": symbol,
            "kind": kind,
            "detail": {str(k).strip().lstrip("\ufeff"): v for k, v in row.items()},
        })
    return out


def _extract_circuit_band(row: dict) -> float | None:
    for key, value in row.items():
        if _norm_header(key) == "to":
            return _to_float(value)
    for key, value in row.items():
        norm = _norm_header(key)
        if norm.startswith("to ") or "new band" in norm or "revised" in norm:
            val = _to_float(value)
            if val is not None:
                return val
    return None


def _upsert_disclosure(conn, row: dict) -> None:
    conn.execute(
        "INSERT INTO disclosures (trade_date, symbol, kind, detail_json) "
        "VALUES (?, ?, ?, ?) "
        "ON CONFLICT(trade_date, symbol, kind) DO UPDATE SET "
        "detail_json=excluded.detail_json",
        (
            row["trade_date"], row["symbol"], row["kind"],
            json.dumps(row["detail"], sort_keys=True, separators=(",", ":")),
        ),
    )


def _upsert_circuit_band(conn, symbol: str, as_of: str, band_pct: float) -> None:
    conn.execute(
        "INSERT INTO circuit_bands (symbol, as_of, band_pct) VALUES (?, ?, ?) "
        "ON CONFLICT(symbol, as_of) DO UPDATE SET band_pct=excluded.band_pct",
        (symbol, as_of, band_pct),
    )


def _log_run(conn, run_date, status, rows, duration, detail) -> None:
    conn.execute(
        "INSERT INTO pipeline_runs (run_date, stage, source, status, "
        "rows_affected, duration_s, detail) VALUES (?,?,?,?,?,?,?)",
        (run_date, _STAGE, _SOURCE, status, rows, duration, detail),
    )


def has_recent_disclosure(conn, symbol: str, as_of: str, window_sessions: int = 5) -> bool:
    symbol = (symbol or "").strip().upper()
    if not symbol or window_sessions <= 0:
        return False
    dates = conn.execute(
        "SELECT DISTINCT trade_date FROM disclosures "
        "WHERE trade_date <= ? ORDER BY trade_date DESC LIMIT ?",
        (as_of, window_sessions),
    ).fetchall()
    if not dates:
        return False
    recent = [r["trade_date"] for r in dates]
    placeholders = ",".join("?" for _ in recent)
    row = conn.execute(
        f"SELECT 1 FROM disclosures WHERE symbol=? AND trade_date IN ({placeholders}) LIMIT 1",
        (symbol, *recent),
    ).fetchone()
    return row is not None


def circuit_band(conn, symbol: str, as_of: str) -> float | None:
    symbol = (symbol or "").strip().upper()
    if not symbol:
        return None
    row = conn.execute(
        "SELECT band_pct FROM circuit_bands "
        "WHERE symbol=? AND as_of <= ? ORDER BY as_of DESC LIMIT 1",
        (symbol, as_of),
    ).fetchone()
    return float(row["band_pct"]) if row is not None and row["band_pct"] is not None else None


def run(conn, run_date: str) -> int:
    """Ingest ChartsMaze disclosure feeds. Never raises."""
    started = time.monotonic()
    try:
        folder = _latest_dump_dir(run_date)
        if folder is None:
            _log_run(conn, run_date, "skip", 0, time.monotonic() - started,
                     "chartsmaze disclosure folder missing")
            conn.commit()
            return 0

        tools_dir = folder / "tools"
        counts = {name: 0 for name in _FEEDS}
        bands = 0
        errors: list[str] = []
        for feed_name, (filename, kind) in _FEEDS.items():
            path = tools_dir / filename
            if not path.is_file():
                continue
            try:
                parsed = parse_disclosure_csv(
                    path.read_text(encoding="utf-8-sig"), kind, folder.name
                )
                for row in parsed:
                    _upsert_disclosure(conn, row)
                    counts[feed_name] += 1
                    if kind == "circuit_revision":
                        band = _extract_circuit_band(row["detail"])
                        if band is not None:
                            _upsert_circuit_band(conn, row["symbol"], row["trade_date"], band)
                            bands += 1
            except Exception as exc:
                errors.append(f"{feed_name}=err({type(exc).__name__})")

        total = sum(counts.values()) + bands
        detail = {"dump": folder.name, "feeds": counts, "circuit_bands": bands}
        if errors:
            detail["errors"] = errors
        _log_run(conn, run_date, "ok", total, time.monotonic() - started,
                 json.dumps(detail, sort_keys=True, separators=(",", ":")))
        conn.commit()
        return total
    except Exception as exc:
        _log_run(conn, run_date, "fail", 0, time.monotonic() - started,
                 f"{type(exc).__name__}: {exc}")
        conn.commit()
        return 0
