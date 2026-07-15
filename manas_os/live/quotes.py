"""Latest-LTP cache for the live loop -- Stage 1's contribution to the
LIVE-FIRST decision (manas_os/design/LIVE_FIRST_DECISION.md): a small,
persisted "what is the last price we saw" table that a later desk-facing
endpoint (and, later still, the SSE tick stream) can read without going back
to Fyers or waiting on the FSM.

One-writer rule holds here too: this module only ever records what a tick
said, never computes P&L, risk, or anything display-derived from it -- that
stays the API layer's job, reading whatever this table already states.

Persisted (not purely in-memory) so a process restart doesn't erase "what
did we last see" -- consistent with the rest of the live/ package's
restart-safe design.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Iterable

from manas_os.providers.base import SnapshotRow


_EXTRA_COLUMNS = {
    "open": "REAL",
    "high": "REAL",
    "low": "REAL",
    "volume": "REAL",
    "prev_close": "REAL",
    "avg_vol_n": "REAL",
    "provider": "TEXT NOT NULL DEFAULT 'fyers'",
}


def ensure_schema(conn) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS live_quotes ("
        "symbol TEXT PRIMARY KEY,ltp REAL NOT NULL,bar_ts TEXT,open REAL,high REAL,low REAL,"
        "volume REAL,prev_close REAL,avg_vol_n REAL,provider TEXT NOT NULL DEFAULT 'fyers',"
        "updated_at TEXT DEFAULT (datetime('now')))"
    )
    have = {row[1] for row in conn.execute("PRAGMA table_info(live_quotes)")}
    for name, ddl in _EXTRA_COLUMNS.items():
        if name not in have:
            conn.execute(f"ALTER TABLE live_quotes ADD COLUMN {name} {ddl}")


def update_quote(conn, symbol: str, ltp: float, bar_ts: str | None = None) -> None:
    ensure_schema(conn)
    conn.execute(
        "INSERT INTO live_quotes (symbol, ltp, bar_ts, updated_at) VALUES (?, ?, ?, datetime('now')) "
        "ON CONFLICT(symbol) DO UPDATE SET ltp=excluded.ltp, bar_ts=excluded.bar_ts, "
        "updated_at=datetime('now')",
        (symbol.strip().upper(), ltp, bar_ts),
    )
    conn.commit()


def update_snapshot(
    conn,
    row: SnapshotRow,
    *,
    provider: str,
    observed_at: str,
    commit: bool = True,
) -> None:
    """Persist a normalized provider snapshot without mutating EOD history."""
    if not row.ok or row.last is None:
        return
    ensure_schema(conn)
    conn.execute(
        "INSERT INTO live_quotes "
        "(symbol,ltp,bar_ts,open,high,low,volume,prev_close,avg_vol_n,provider,updated_at) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,datetime('now')) "
        "ON CONFLICT(symbol) DO UPDATE SET "
        "ltp=excluded.ltp,bar_ts=excluded.bar_ts,open=excluded.open,high=excluded.high,"
        "low=excluded.low,volume=excluded.volume,prev_close=excluded.prev_close,"
        "avg_vol_n=excluded.avg_vol_n,provider=excluded.provider,updated_at=datetime('now')",
        (
            row.symbol.strip().upper(), row.last, observed_at, row.today_open,
            row.today_high, row.today_low, row.today_volume, row.prev_close,
            row.avg_vol_n, provider,
        ),
    )
    if commit:
        conn.commit()


def get_quotes(conn, symbols: Iterable[str] | None = None) -> dict[str, dict[str, Any]]:
    """Returns {SYMBOL: {ltp, bar_ts, updated_at}}. Never raises on a missing
    table (a fresh DB with no live session run yet is a legitimate state, not
    an error)."""
    ensure_schema(conn)
    columns = "symbol,ltp,bar_ts,open,high,low,volume,prev_close,avg_vol_n,provider,updated_at"
    if symbols is not None:
        symbols = [s.strip().upper() for s in symbols]
        if not symbols:
            return {}
        placeholders = ",".join("?" for _ in symbols)
        try:
            rows = conn.execute(
                f"SELECT {columns} FROM live_quotes WHERE symbol IN ({placeholders})",
                symbols,
            ).fetchall()
        except Exception:
            rows = []
    else:
        try:
            rows = conn.execute(f"SELECT {columns} FROM live_quotes").fetchall()
        except Exception:
            rows = []
    return {
        r["symbol"]: {
            "ltp": r["ltp"], "bar_ts": r["bar_ts"], "open": r["open"],
            "high": r["high"], "low": r["low"], "volume": r["volume"],
            "prev_close": r["prev_close"], "avg_vol_n": r["avg_vol_n"],
            "provider": r["provider"], "updated_at": r["updated_at"],
        }
        for r in rows
    }


def annotate_freshness(
    cached: dict[str, dict[str, Any]],
    *,
    now: datetime,
    max_age_seconds: int = 90,
) -> dict[str, dict[str, Any]]:
    """Add per-quote freshness; malformed timestamps fail closed."""
    out: dict[str, dict[str, Any]] = {}
    for symbol, quote in cached.items():
        fresh = False
        age_seconds = None
        try:
            observed = datetime.fromisoformat(str(quote.get("bar_ts") or ""))
            if observed.tzinfo is None:
                observed = observed.replace(tzinfo=now.tzinfo)
            age_seconds = (now - observed.astimezone(now.tzinfo)).total_seconds()
            fresh = -5.0 <= age_seconds <= float(max_age_seconds)
        except (TypeError, ValueError):
            pass
        out[symbol] = {
            **quote,
            "fresh": fresh,
            "age_seconds": None if age_seconds is None else round(age_seconds, 1),
        }
    return out


def resolve_prices(
    conn,
    symbols: list[str],
    *,
    on_or_before: str,
    now: datetime,
    market_open: bool,
    allow_live: bool,
) -> dict[str, dict[str, Any]]:
    """Resolve many symbols with one live-cache read and one EOD query."""
    clean_symbols = list(dict.fromkeys(symbol.strip().upper() for symbol in symbols if symbol.strip()))
    if not clean_symbols:
        return {}

    resolved: dict[str, dict[str, Any]] = {}
    if allow_live and market_open:
        cached = annotate_freshness(get_quotes(conn, clean_symbols), now=now)
        for clean_symbol, quote in cached.items():
            if not quote.get("fresh"):
                continue
            resolved[clean_symbol] = {
                "price": quote.get("ltp"),
                "state": "LIVE",
                "provider": quote.get("provider") or "fyers",
                "as_of": quote.get("bar_ts"),
                "fresh": True,
            }

    missing = [symbol for symbol in clean_symbols if symbol not in resolved]
    if missing:
        placeholders = ",".join("?" for _ in missing)
        rows = conn.execute(
            "SELECT symbol,close,trade_date,source FROM ("
            "SELECT symbol,close,trade_date,source,"
            "ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY trade_date DESC) AS rn "
            "FROM daily_prices WHERE series='EQ' AND trade_date<=? "
            f"AND symbol IN ({placeholders})) WHERE rn=1",
            (on_or_before, *missing),
        ).fetchall()
        for row in rows:
            resolved[row["symbol"]] = {
                "price": row["close"],
                "state": "EOD_FINAL",
                "provider": row["source"] or "bhavcopy",
                "as_of": row["trade_date"],
                "fresh": False,
            }

    for clean_symbol in clean_symbols:
        resolved.setdefault(clean_symbol, {
            "price": None,
            "state": "EMPTY",
            "provider": None,
            "as_of": None,
            "fresh": False,
        })
    return resolved


def resolve_price(
    conn,
    symbol: str,
    *,
    on_or_before: str,
    now: datetime,
    market_open: bool,
    allow_live: bool,
) -> dict[str, Any]:
    """Canonical single-symbol wrapper around the bulk resolver."""
    clean_symbol = symbol.strip().upper()
    return resolve_prices(
        conn,
        [clean_symbol],
        on_or_before=on_or_before,
        now=now,
        market_open=market_open,
        allow_live=allow_live,
    )[clean_symbol]


def latest_as_of(conn) -> str | None:
    ensure_schema(conn)
    try:
        row = conn.execute("SELECT MAX(updated_at) AS m FROM live_quotes").fetchone()
        return row["m"] if row else None
    except Exception:
        return None
