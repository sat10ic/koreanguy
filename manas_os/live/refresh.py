"""Fyers REST snapshot refresh for the canonical live quote cache."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Iterable

from manas_os import config
from manas_os.providers.fyers import FyersProvider

from . import quotes

_IST = timezone(timedelta(hours=5, minutes=30))


def _universe_symbols(conn, limit: int = 4000) -> list[str]:
    row = conn.execute(
        "SELECT MAX(trade_date) AS d FROM daily_prices WHERE series='EQ'"
    ).fetchone()
    if not row or not row["d"]:
        return []
    rows = conn.execute(
        "SELECT DISTINCT symbol FROM daily_prices WHERE series='EQ' AND trade_date=? "
        "ORDER BY symbol LIMIT ?",
        (row["d"], max(1, min(int(limit), 4000))),
    ).fetchall()
    return [str(item["symbol"]).strip().upper() for item in rows]


def refresh_quotes(
    conn,
    *,
    provider: Any | None = None,
    symbols: Iterable[str] | None = None,
    observed_at: datetime | None = None,
    universe_limit: int = 4000,
) -> dict[str, Any]:
    provider = provider or FyersProvider.from_config(config.load_config())
    provider_name = str(getattr(provider, "name", "unknown"))
    if not provider.is_available():
        return {
            "state": "auth_required",
            "provider": provider_name,
            "requested": 0,
            "written": 0,
            "failed": 0,
            "as_of": None,
        }
    source_symbols = _universe_symbols(conn, universe_limit) if symbols is None else symbols
    requested_symbols = sorted(
        {
            str(symbol).strip().upper()
            for symbol in source_symbols
            if str(symbol).strip()
        }
    )
    when = observed_at or datetime.now(_IST)
    as_of = when.isoformat(timespec="seconds")
    rows = provider.get_snapshot(requested_symbols, lookback=0)
    written = 0
    failed = 0
    for row in rows:
        if row.ok and row.last is not None:
            quotes.update_snapshot(
                conn, row, provider=provider_name, observed_at=as_of, commit=False
            )
            written += 1
        else:
            failed += 1
    conn.commit()
    return {
        "state": "ready" if written else "empty",
        "provider": provider_name,
        "requested": len(requested_symbols),
        "written": written,
        "failed": failed + max(0, len(requested_symbols) - len(rows)),
        "as_of": as_of,
    }


def stage(conn, _run_date: str) -> None:
    result = refresh_quotes(conn)
    if result["state"] == "auth_required":
        raise RuntimeError("Fyers authentication required for live quote refresh")
    if result["state"] == "empty":
        raise RuntimeError("Fyers live quote refresh returned no usable rows")
