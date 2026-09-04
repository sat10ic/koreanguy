"""Point-in-time fundamentals ingest for W5.

This stage writes quarterly rows to symbol_fundamentals. It is deliberately a
source-stage boundary: scanner code can later consume it through one helper
without coupling gates to a vendor API.
"""
from __future__ import annotations

from datetime import date, datetime
import time
from typing import Any, Callable

from manas_os import config

STAGE = "ingest_fundamentals"
SOURCE = "yfinance_fundamentals"
DEFAULT_LIMIT = 25
GROWTH_FIELDS = ("eps_yoy", "eps_qoq", "sales_yoy", "opm_yoy")

FetchFn = Callable[[str, str], list[dict[str, Any]]]


def ensure_schema(conn) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS symbol_fundamentals ("
        "symbol TEXT NOT NULL, report_date TEXT NOT NULL, as_of TEXT NOT NULL, "
        "period TEXT DEFAULT 'quarterly', revenue REAL, operating_income REAL, "
        "net_income REAL, eps REAL, operating_margin REAL, sales_yoy REAL, eps_yoy REAL, "
        "opm_yoy REAL, roe REAL, pe_ratio REAL, debt_to_equity REAL, market_cap_cr REAL, "
        "source TEXT, ingested_at TEXT DEFAULT (datetime('now')), "
        "PRIMARY KEY (symbol, report_date, as_of))"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_symbol_fundamentals_symbol_asof "
        "ON symbol_fundamentals(symbol, as_of)"
    )


def _num(value: Any) -> float | None:
    if value is None:
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if out == out else None


def _pct(new: Any, old: Any) -> float | None:
    new_f = _num(new)
    old_f = _num(old)
    if new_f is None or old_f in (None, 0):
        return None
    return (new_f - old_f) / abs(old_f) * 100.0


def _date_str(value: Any) -> str:
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return str(value)[:10]


def _row_value(frame: Any, names: tuple[str, ...], pos: int) -> float | None:
    if frame is None or getattr(frame, "empty", True) or pos >= len(frame.columns):
        return None
    for name in names:
        if name in frame.index:
            return _num(frame.loc[name].iloc[pos])
    return None


def _ratio_percent(value: Any) -> float | None:
    raw = _num(value)
    if raw is None:
        return None
    return raw * 100.0 if abs(raw) <= 1.0 else raw


def fetch_yfinance(symbol: str, as_of: str) -> list[dict[str, Any]]:
    """Fetch quarterly fundamentals for one NSE symbol via yfinance."""
    import yfinance as yf  # imported lazily; tests use an injected fetcher

    ticker = yf.Ticker(symbol + ".NS")
    try:
        info = ticker.get_info() or {}
    except Exception:
        info = {}
    try:
        q = ticker.quarterly_income_stmt
    except Exception:
        q = None
    if q is None or getattr(q, "empty", True):
        return []

    q = q.sort_index(axis=1, ascending=False)
    market_cap = _num(info.get("marketCap"))
    common = {
        "symbol": symbol.upper(),
        "as_of": as_of,
        "period": "quarterly",
        "roe": _ratio_percent(info.get("returnOnEquity")),
        "pe_ratio": _num(info.get("trailingPE")),
        "debt_to_equity": _num(info.get("debtToEquity")),
        "market_cap_cr": None if market_cap is None else market_cap / 10_000_000.0,
        "source": SOURCE,
    }

    rows: list[dict[str, Any]] = []
    margins: list[float | None] = []
    eps_values: list[float | None] = []
    revenue_values: list[float | None] = []
    for idx, col in enumerate(q.columns):
        revenue = _row_value(q, ("Total Revenue", "Operating Revenue"), idx)
        operating_income = _row_value(q, ("Operating Income", "EBIT"), idx)
        net_income = _row_value(
            q,
            ("Net Income", "Net Income Common Stockholders", "Normalized Income"),
            idx,
        )
        eps = _row_value(q, ("Diluted EPS", "Basic EPS"), idx)
        margin = None if revenue in (None, 0) or operating_income is None else operating_income / revenue * 100.0
        revenue_values.append(revenue)
        eps_values.append(eps)
        margins.append(margin)
        rows.append({
            **common,
            "report_date": _date_str(col),
            "revenue": revenue,
            "operating_income": operating_income,
            "net_income": net_income,
            "eps": eps,
            "operating_margin": margin,
            "sales_yoy": None,
            "eps_yoy": None,
            "opm_yoy": None,
        })

    for idx, row in enumerate(rows):
        if idx + 4 < len(rows):
            row["sales_yoy"] = _pct(revenue_values[idx], revenue_values[idx + 4])
            row["eps_yoy"] = _pct(eps_values[idx], eps_values[idx + 4])
            old_margin = margins[idx + 4]
            row["opm_yoy"] = None if row["operating_margin"] is None or old_margin is None else row["operating_margin"] - old_margin
        elif idx == 0:
            row["sales_yoy"] = _ratio_percent(info.get("revenueGrowth"))
            row["eps_yoy"] = _ratio_percent(info.get("earningsQuarterlyGrowth"))
            row["opm_yoy"] = None
    return rows


def upsert(conn, rows: list[dict[str, Any]]) -> int:
    if not rows:
        return 0
    conn.executemany(
        "INSERT OR REPLACE INTO symbol_fundamentals "
        "(symbol, report_date, as_of, period, revenue, operating_income, net_income, eps, "
        "operating_margin, sales_yoy, eps_yoy, opm_yoy, roe, pe_ratio, debt_to_equity, "
        "market_cap_cr, source) VALUES "
        "(:symbol, :report_date, :as_of, :period, :revenue, :operating_income, :net_income, :eps, "
        ":operating_margin, :sales_yoy, :eps_yoy, :opm_yoy, :roe, :pe_ratio, :debt_to_equity, "
        ":market_cap_cr, :source)",
        rows,
    )
    return len(rows)


def symbols_for_run(conn, run_date: str, limit: int = DEFAULT_LIMIT) -> list[str]:
    row = conn.execute(
        "SELECT MAX(scan_date) AS d FROM scan_candidates WHERE scan_date <= ?",
        (run_date,),
    ).fetchone()
    if row and row["d"]:
        rows = conn.execute(
            "SELECT DISTINCT symbol FROM scan_candidates WHERE scan_date = ? "
            "ORDER BY rank IS NULL, rank, symbol LIMIT ?",
            (row["d"], limit),
        ).fetchall()
        if rows:
            return [r["symbol"] for r in rows]

    row = conn.execute(
        "SELECT MAX(trade_date) AS d FROM symbol_quality WHERE trade_date <= ?",
        (run_date,),
    ).fetchone()
    if row and row["d"]:
        rows = conn.execute(
            "SELECT DISTINCT symbol FROM symbol_quality WHERE trade_date = ? ORDER BY symbol LIMIT ?",
            (row["d"], limit),
        ).fetchall()
        return [r["symbol"] for r in rows]
    return []


def latest_snapshot(conn, symbol: str, as_of: str) -> dict[str, Any] | None:
    ensure_schema(conn)
    row = conn.execute(
        "SELECT * FROM symbol_fundamentals WHERE symbol = ? AND as_of <= ? "
        "ORDER BY as_of DESC, report_date DESC LIMIT 1",
        (symbol.upper(), as_of),
    ).fetchone()
    return dict(row) if row else None


def growth_for(
    conn,
    symbol: str,
    as_of: str,
    fallback_quality: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Growth fields for scanner use: fundamentals first, compact quality fallback."""
    ensure_schema(conn)
    fallback_quality = fallback_quality or {}
    out = {field: fallback_quality.get(field) for field in GROWTH_FIELDS}
    latest = conn.execute(
        "SELECT MAX(as_of) AS d FROM symbol_fundamentals WHERE symbol = ? AND as_of <= ?",
        (symbol.upper(), as_of),
    ).fetchone()
    if not latest or not latest["d"]:
        return out
    rows = conn.execute(
        "SELECT report_date, eps, eps_yoy, sales_yoy, opm_yoy "
        "FROM symbol_fundamentals WHERE symbol = ? AND as_of = ? AND report_date <= ? "
        "ORDER BY report_date DESC LIMIT 2",
        (symbol.upper(), latest["d"], as_of),
    ).fetchall()
    if not rows:
        return out
    current = dict(rows[0])
    for field in ("eps_yoy", "sales_yoy", "opm_yoy"):
        if current.get(field) is not None:
            out[field] = current[field]
    if len(rows) > 1:
        qoq = _pct(current.get("eps"), rows[1]["eps"])
        if qoq is not None:
            out["eps_qoq"] = qoq
    return out


def run(
    conn,
    run_date: str,
    *,
    symbols: list[str] | None = None,
    fetcher: FetchFn | None = None,
) -> dict[str, Any]:
    started = time.monotonic()
    ensure_schema(conn)
    max_symbols = int(config.get("fundamentals.max_symbols", DEFAULT_LIMIT) or DEFAULT_LIMIT)
    symbols = [s.upper() for s in (symbols or symbols_for_run(conn, run_date, max_symbols))]
    if not symbols:
        conn.execute(
            "INSERT INTO pipeline_runs (run_date, stage, source, status, rows_affected, duration_s, detail) "
            "VALUES (?, ?, ?, 'skip', 0, ?, ?)",
            (run_date, STAGE, SOURCE, round(time.monotonic() - started, 3), "no symbols available"),
        )
        conn.commit()
        return {"status": "skip", "rows": 0, "symbols": 0}

    fetch = fetcher or fetch_yfinance
    rows_written = 0
    failures: list[str] = []
    try:
        for symbol in symbols:
            try:
                rows_written += upsert(conn, fetch(symbol, run_date))
            except Exception:
                failures.append(symbol)
        status = "ok" if rows_written else ("fail" if failures else "skip")
        detail = f"symbols={len(symbols)} rows={rows_written} failures={len(failures)}"
        if failures:
            detail += " failed=" + ",".join(failures[:20])
        conn.execute(
            "INSERT INTO pipeline_runs (run_date, stage, source, status, rows_affected, duration_s, detail) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (run_date, STAGE, SOURCE, status, rows_written, round(time.monotonic() - started, 3), detail),
        )
        conn.commit()
        return {"status": status, "rows": rows_written, "symbols": len(symbols), "failures": failures}
    except Exception as exc:  # noqa: BLE001
        conn.execute(
            "INSERT INTO pipeline_runs (run_date, stage, source, status, rows_affected, duration_s, detail) "
            "VALUES (?, ?, ?, 'fail', 0, ?, ?)",
            (run_date, STAGE, SOURCE, round(time.monotonic() - started, 3), str(exc)),
        )
        conn.commit()
        return {"status": "fail", "rows": 0, "symbols": len(symbols), "detail": str(exc)}
