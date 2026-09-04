"""Provider-neutral intraday history storage with a Fyers history adapter.

The table stores only canonical Asia/Kolkata timestamps and deliberately keeps
``provider`` in its primary key.  This module is data plumbing: it does not
derive signals, rank symbols, place orders, or participate in risk maths.
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
import json
import sqlite3
from typing import Any, Iterable
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

try:
    INDIA_TZ = ZoneInfo("Asia/Kolkata")
except ZoneInfoNotFoundError:  # minimal Windows/Python runtimes may omit tzdata
    INDIA_TZ = timezone(timedelta(hours=5, minutes=30), "Asia/Kolkata")
UTC = timezone.utc
INTERVAL_MINUTES = {"1m": 1, "5m": 5}
FYERS_RESOLUTION = {"1m": "1", "5m": "5"}

# Half-open intervals make every boundary unambiguous: 09:30 belongs to the
# second segment and 15:30 is outside the regular NSE session.
TRADETM_SEGMENTS = (
    (time(9, 15), time(9, 30), "09:15-09:30"),
    (time(9, 30), time(10, 0), "09:30-10:00"),
    (time(10, 0), time(12, 0), "10:00-12:00"),
    (time(12, 0), time(13, 30), "12:00-13:30"),
    (time(13, 30), time(15, 0), "13:30-15:00"),
    (time(15, 0), time(15, 30), "15:00-15:30"),
)

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS intraday_bars (
    provider TEXT NOT NULL,
    symbol TEXT NOT NULL,
    interval TEXT NOT NULL CHECK (interval IN ('1m', '5m')),
    bar_ts TEXT NOT NULL CHECK (bar_ts LIKE '%+05:30'),
    trade_date TEXT NOT NULL,
    segment TEXT,
    open REAL NOT NULL,
    high REAL NOT NULL,
    low REAL NOT NULL,
    close REAL NOT NULL,
    volume REAL NOT NULL,
    provider_symbol TEXT,
    request_from TEXT,
    request_to TEXT,
    provenance_json TEXT NOT NULL,
    ingested_at TEXT NOT NULL,
    PRIMARY KEY (provider, symbol, interval, bar_ts)
);
CREATE INDEX IF NOT EXISTS idx_intraday_bars_symbol_time
    ON intraday_bars(symbol, interval, bar_ts);
"""


class IntradaySourceError(RuntimeError):
    """A provider or normalization failure safe to surface to an operator."""


class RateLimitError(IntradaySourceError):
    """The provider declined a request because its request budget was reached."""


def ensure_schema(conn: sqlite3.Connection) -> None:
    """Install the idempotent intraday schema on an existing connection."""
    conn.executescript(_SCHEMA_SQL)


def _validate_interval(interval: str) -> str:
    value = str(interval).strip().lower()
    if value not in INTERVAL_MINUTES:
        raise ValueError("interval must be '1m' or '5m'")
    return value


def _normalise_symbol(symbol: str) -> str:
    value = str(symbol).strip().upper()
    if not value:
        raise ValueError("symbol is required")
    return value


def as_ist(value: datetime | date | str | int | float) -> datetime:
    """Return an aware Asia/Kolkata datetime from common provider inputs.

    Epoch values are seconds since UTC.  Naive datetime/ISO values are treated
    as exchange-local wall time; aware values are converted to exchange time.
    A bare date represents midnight in Asia/Kolkata.
    """
    if isinstance(value, bool):
        raise ValueError("boolean is not a timestamp")
    if isinstance(value, (int, float)):
        parsed = datetime.fromtimestamp(value, UTC)
    elif isinstance(value, datetime):
        parsed = value
    elif isinstance(value, date):
        parsed = datetime.combine(value, time.min)
    else:
        text = str(value).strip()
        if not text:
            raise ValueError("timestamp is required")
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=INDIA_TZ)
    return parsed.astimezone(INDIA_TZ).replace(microsecond=0)


def canonical_timestamp(value: datetime | date | str | int | float) -> str:
    return as_ist(value).isoformat(timespec="seconds")


def tradetm_segment(value: datetime | date | str | int | float) -> str | None:
    """Classify an exchange timestamp into the six TradeTM session segments."""
    current = as_ist(value).timetz().replace(tzinfo=None)
    for start, end, label in TRADETM_SEGMENTS:
        if start <= current < end:
            return label
    return None


def _number(value: Any, field: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid {field}: {value!r}") from exc
    if number != number or number in (float("inf"), float("-inf")):
        raise ValueError(f"invalid {field}: {value!r}")
    return number


def _normalise_candle(candle: Any) -> tuple[str, float, float, float, float, float]:
    if not isinstance(candle, (list, tuple)) or len(candle) < 6:
        raise ValueError("candle must be [timestamp, open, high, low, close, volume]")
    bar_ts = canonical_timestamp(candle[0])
    open_, high, low, close, volume = (
        _number(candle[1], "open"),
        _number(candle[2], "high"),
        _number(candle[3], "low"),
        _number(candle[4], "close"),
        _number(candle[5], "volume"),
    )
    if high < low or high < max(open_, close) or low > min(open_, close):
        raise ValueError(f"inconsistent OHLC candle at {bar_ts}")
    if volume < 0:
        raise ValueError(f"negative volume at {bar_ts}")
    return bar_ts, open_, high, low, close, volume


def upsert_bars(
    conn: sqlite3.Connection,
    *,
    provider: str,
    symbol: str,
    interval: str,
    candles: Iterable[Any],
    provider_symbol: str | None = None,
    request_from: datetime | str | int | float | None = None,
    request_to: datetime | str | int | float | None = None,
    fetched_at: datetime | str | int | float | None = None,
) -> int:
    """Idempotently normalize and upsert provider candles.

    The caller owns transaction boundaries.  ``fetch_and_store`` commits after
    each successful provider window so a later rate limit can be resumed.
    """
    ensure_schema(conn)
    interval = _validate_interval(interval)
    symbol = _normalise_symbol(symbol)
    provider = str(provider).strip().lower()
    if not provider:
        raise ValueError("provider is required")
    fetched = canonical_timestamp(fetched_at if fetched_at is not None else datetime.now(INDIA_TZ))
    request_from_s = canonical_timestamp(request_from) if request_from is not None else None
    request_to_s = canonical_timestamp(request_to) if request_to is not None else None
    provider_symbol = provider_symbol or symbol
    provenance = json.dumps(
        {
            "adapter": f"{provider}_history",
            "provider": provider,
            "provider_symbol": provider_symbol,
            "request_from": request_from_s,
            "request_to": request_to_s,
            "fetched_at": fetched,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    rows = []
    for candle in candles:
        bar_ts, open_, high, low, close, volume = _normalise_candle(candle)
        rows.append(
            (
                provider,
                symbol,
                interval,
                bar_ts,
                bar_ts[:10],
                tradetm_segment(bar_ts),
                open_,
                high,
                low,
                close,
                volume,
                provider_symbol,
                request_from_s,
                request_to_s,
                provenance,
                fetched,
            )
        )
    if not rows:
        return 0
    conn.executemany(
        "INSERT INTO intraday_bars "
        "(provider, symbol, interval, bar_ts, trade_date, segment, open, high, low, close, volume, "
        "provider_symbol, request_from, request_to, provenance_json, ingested_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
        "ON CONFLICT(provider, symbol, interval, bar_ts) DO UPDATE SET "
        "trade_date=excluded.trade_date, segment=excluded.segment, open=excluded.open, "
        "high=excluded.high, low=excluded.low, close=excluded.close, volume=excluded.volume, "
        "provider_symbol=excluded.provider_symbol, request_from=excluded.request_from, "
        "request_to=excluded.request_to, provenance_json=excluded.provenance_json, "
        "ingested_at=excluded.ingested_at",
        rows,
    )
    return len(rows)


def _is_rate_limit(value: Any) -> bool:
    if isinstance(value, dict):
        codes = (value.get("code"), value.get("status"), value.get("status_code"))
        if any(str(code).lstrip("-") == "429" for code in codes if code is not None):
            return True
        text = " ".join(str(value.get(k, "")) for k in ("message", "error", "detail"))
    else:
        status = getattr(value, "status_code", None)
        if status == 429:
            return True
        text = str(value)
    lowered = text.lower()
    return any(
        marker in lowered
        for marker in ("rate limit", "too many requests", "request limit", "limit reached", "api limit")
    )


class FyersHistoryAdapter:
    """Small Fyers-v3 history boundary with an injectable client for tests."""

    provider = "fyers"

    def __init__(
        self,
        client: Any | None = None,
        config_data: dict[str, Any] | None = None,
        symbol_mapper: Any | None = None,
    ):
        self._client = client
        self._config_data = config_data
        self._symbol_mapper = symbol_mapper

    def _resolve_client(self) -> Any:
        if self._client is not None:
            return self._client
        # Lazy imports keep an injected fake client independent of the Fyers SDK
        # and application config dependencies.
        from manas_os import config
        from manas_os.providers.fyers import FyersProvider

        cfg = self._config_data if self._config_data is not None else config.load_config()
        provider = FyersProvider.from_config(cfg)
        if not provider.is_available():
            raise IntradaySourceError("Fyers credentials/client are unavailable")
        self._client = provider._get_client()  # existing credential/client owner
        return self._client

    def provider_symbol(self, symbol: str) -> str:
        if self._symbol_mapper is not None:
            return str(self._symbol_mapper(symbol))
        from manas_os.providers.fyers import fyers_symbol

        return fyers_symbol(symbol)

    def history(self, symbol: str, interval: str, start: datetime, end: datetime) -> list[Any]:
        interval = _validate_interval(interval)
        payload = {
            "symbol": self.provider_symbol(symbol),
            "resolution": FYERS_RESOLUTION[interval],
            "date_format": "0",
            "range_from": str(int(start.astimezone(UTC).timestamp())),
            "range_to": str(int(end.astimezone(UTC).timestamp())),
            "cont_flag": "1",
        }
        try:
            response = self._resolve_client().history(payload)
        except Exception as exc:  # provider SDK exceptions vary by version
            if _is_rate_limit(exc):
                raise RateLimitError(str(exc)) from exc
            raise IntradaySourceError(str(exc)) from exc
        if _is_rate_limit(response):
            raise RateLimitError(str(response.get("message") or response))
        if not isinstance(response, dict) or response.get("s") != "ok":
            detail = response.get("message", "bad Fyers history response") if isinstance(response, dict) else "bad Fyers history response"
            raise IntradaySourceError(str(detail))
        candles = response.get("candles", [])
        if not isinstance(candles, list):
            raise IntradaySourceError("Fyers history response candles must be a list")
        return candles


def _latest_stored_timestamp(
    conn: sqlite3.Connection,
    provider: str,
    symbol: str,
    interval: str,
    start: datetime,
    end: datetime,
) -> datetime | None:
    row = conn.execute(
        "SELECT MAX(bar_ts) FROM intraday_bars "
        "WHERE provider = ? AND symbol = ? AND interval = ? AND bar_ts BETWEEN ? AND ?",
        (provider, symbol, interval, canonical_timestamp(start), canonical_timestamp(end)),
    ).fetchone()
    return as_ist(row[0]) if row and row[0] else None


def fetch_and_store(
    conn: sqlite3.Connection,
    *,
    symbol: str,
    interval: str,
    start: datetime | str | int | float,
    end: datetime | str | int | float,
    adapter: Any | None = None,
    window_size: timedelta = timedelta(days=30),
) -> dict[str, Any]:
    """Fetch/upsert chronological windows and return a failure-safe summary.

    Existing coverage advances the cursor to the first bar after the latest
    stored timestamp.  Every successful window is committed independently;
    rate limits and provider failures return the next resumable timestamp.
    """
    ensure_schema(conn)
    symbol = _normalise_symbol(symbol)
    interval = _validate_interval(interval)
    start_dt, end_dt = as_ist(start), as_ist(end)
    if start_dt > end_dt:
        raise ValueError("start must not be after end")
    if window_size <= timedelta(0):
        raise ValueError("window_size must be positive")
    adapter = adapter or FyersHistoryAdapter()
    provider = str(getattr(adapter, "provider", "fyers")).strip().lower()
    provider_sym = adapter.provider_symbol(symbol) if hasattr(adapter, "provider_symbol") else symbol
    step = timedelta(minutes=INTERVAL_MINUTES[interval])
    latest = _latest_stored_timestamp(conn, provider, symbol, interval, start_dt, end_dt)
    cursor = max(start_dt, latest + step) if latest else start_dt
    windows = 0
    received = 0
    upserted = 0
    status = "ok"
    error = None
    failed_at: datetime | None = None

    while cursor <= end_dt:
        window_end = min(end_dt, cursor + window_size)
        try:
            candles = adapter.history(symbol, interval, cursor, window_end)
            received += len(candles)
            upserted += upsert_bars(
                conn,
                provider=provider,
                symbol=symbol,
                interval=interval,
                candles=candles,
                provider_symbol=provider_sym,
                request_from=cursor,
                request_to=window_end,
            )
            conn.commit()
            windows += 1
        except RateLimitError as exc:
            conn.rollback()
            status, error, failed_at = "rate_limited", str(exc), cursor
            break
        except Exception as exc:  # preserve prior committed windows, return safely
            conn.rollback()
            status = "partial" if windows else "failed"
            error, failed_at = str(exc), cursor
            break
        cursor = window_end + step

    completeness = completeness_summary(
        conn,
        provider=provider,
        symbol=symbol,
        interval=interval,
        start=start_dt,
        end=end_dt,
    )
    next_from = canonical_timestamp(failed_at) if failed_at else None
    return {
        "status": status,
        "provider": provider,
        "provider_symbol": provider_sym,
        "symbol": symbol,
        "interval": interval,
        "range_from": canonical_timestamp(start_dt),
        "range_to": canonical_timestamp(end_dt),
        "windows_completed": windows,
        "bars_received": received,
        "bars_upserted": upserted,
        "next_from": next_from,
        "error": error,
        "completeness": completeness,
    }


def _expected_slots(start: datetime, end: datetime, interval: str) -> list[str]:
    step = timedelta(minutes=INTERVAL_MINUTES[interval])
    slots: list[str] = []
    day = start.date()
    while day <= end.date():
        if day.weekday() < 5:
            cursor = datetime.combine(day, time(9, 15), INDIA_TZ)
            close = datetime.combine(day, time(15, 30), INDIA_TZ)
            while cursor < close:
                if start <= cursor <= end:
                    slots.append(canonical_timestamp(cursor))
                cursor += step
        day += timedelta(days=1)
    return slots


def completeness_summary(
    conn: sqlite3.Connection,
    *,
    provider: str,
    symbol: str,
    interval: str,
    start: datetime | str | int | float,
    end: datetime | str | int | float,
) -> dict[str, Any]:
    """Summarize regular-session coverage for a requested window.

    Expected slots use NSE weekday session hours.  Exchange holidays are not
    inferred here, so the basis is stated explicitly instead of overstating
    completeness.
    """
    ensure_schema(conn)
    interval = _validate_interval(interval)
    symbol = _normalise_symbol(symbol)
    provider = str(provider).strip().lower()
    start_dt, end_dt = as_ist(start), as_ist(end)
    expected = _expected_slots(start_dt, end_dt, interval)
    rows = conn.execute(
        "SELECT bar_ts FROM intraday_bars WHERE provider = ? AND symbol = ? AND interval = ? "
        "AND bar_ts BETWEEN ? AND ? ORDER BY bar_ts",
        (provider, symbol, interval, canonical_timestamp(start_dt), canonical_timestamp(end_dt)),
    ).fetchall()
    stored = [str(row[0]) for row in rows]
    expected_set, stored_set = set(expected), set(stored)
    missing = sorted(expected_set - stored_set)
    unexpected = sorted(stored_set - expected_set)
    matched = len(expected_set & stored_set)
    coverage = round(matched / len(expected), 6) if expected else None
    return {
        "expected_bars": len(expected),
        "stored_bars": len(stored),
        "matched_expected_bars": matched,
        "missing_bars": len(missing),
        "unexpected_bars": len(unexpected),
        "coverage_ratio": coverage,
        "complete": (not missing) if expected else None,
        "first_bar_ts": stored[0] if stored else None,
        "last_bar_ts": stored[-1] if stored else None,
        "missing_examples": missing[:10],
        "basis": "NSE weekday regular session 09:15-15:30 Asia/Kolkata; exchange holidays not inferred",
    }


def _tables(conn: sqlite3.Connection) -> set[str]:
    return {str(row[0]) for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}


def tiered_coverage_symbols(conn: sqlite3.Connection, as_of: str) -> dict[str, Any]:
    """Select 5m/1m coverage solely from the currently available DB tables.

    5m is the latest known tradeable ``universe`` snapshot.  1m is the union
    of latest screener hits, active focus-list names, latest debated names, and
    currently open journal positions.  Missing/older-schema tables yield an
    explicit warning and an otherwise valid partial result.
    """
    as_of = str(as_of)[:10]
    available = _tables(conn)
    warnings: list[str] = []
    five_minute: set[str] = set()
    one_minute_reasons: dict[str, set[str]] = {}

    def add_one(rows: Iterable[Any], reason: str) -> None:
        for row in rows:
            symbol = _normalise_symbol(row[0])
            one_minute_reasons.setdefault(symbol, set()).add(reason)

    def missing(table: str) -> None:
        warnings.append(f"missing table {table}; omitted its coverage contribution")

    if "universe" in available:
        try:
            row = conn.execute("SELECT MAX(as_of_date) FROM universe WHERE as_of_date <= ?", (as_of,)).fetchone()
            if row and row[0]:
                five_minute.update(
                    _normalise_symbol(item[0])
                    for item in conn.execute(
                        "SELECT DISTINCT symbol FROM universe WHERE as_of_date = ? AND is_tradeable = 1",
                        (row[0],),
                    )
                )
        except sqlite3.OperationalError as exc:
            warnings.append(f"universe unavailable: {exc}")
    else:
        missing("universe")

    sources = (
        (
            "screener_hits",
            "scanner_hit",
            "SELECT DISTINCT symbol FROM screener_hits WHERE trade_date = "
            "(SELECT MAX(trade_date) FROM screener_hits WHERE trade_date <= ?)",
            (as_of,),
        ),
        (
            "focus_list",
            "focus_list",
            "SELECT DISTINCT symbol FROM focus_list WHERE active = 1",
            (),
        ),
        (
            "agent_verdicts",
            "debated",
            "SELECT DISTINCT symbol FROM agent_verdicts WHERE scan_date = "
            "(SELECT MAX(scan_date) FROM agent_verdicts WHERE scan_date <= ?)",
            (as_of,),
        ),
        (
            "journal_trades",
            "open_position",
            "SELECT DISTINCT symbol FROM journal_trades WHERE exit IS NULL",
            (),
        ),
    )
    for table, reason, sql, params in sources:
        if table not in available:
            missing(table)
            continue
        try:
            add_one(conn.execute(sql, params), reason)
        except sqlite3.OperationalError as exc:
            warnings.append(f"{table} unavailable: {exc}")

    one_minute = sorted(one_minute_reasons)
    return {
        "as_of": as_of,
        "5m": sorted(five_minute),
        "1m": one_minute,
        "1m_reasons": {symbol: sorted(one_minute_reasons[symbol]) for symbol in one_minute},
        "warnings": warnings,
    }
