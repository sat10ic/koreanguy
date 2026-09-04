"""Partitioned Parquet writer for canonical quotes and depth snapshots.

U-P0.5 core (R9: record before research). Append-style: each flush writes one
immutable file per (session-date, symbol); no in-place rewrites, no
compaction — DuckDB reads the globs. Optional fields are written as nulls
when absent (R5/R12): what the feed did not supply stays missing forever.
"""
from __future__ import annotations

import json
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional

import pyarrow as pa
import pyarrow.parquet as pq

from orderflow.market_data.schemas import DepthSnapshot, QuoteUpdate

QUOTE_SCHEMA = pa.schema([
    ("ts_exchange", pa.timestamp("us", tz="UTC")),
    ("ts_received", pa.timestamp("us", tz="UTC")),
    ("symbol", pa.string()),
    ("ltp", pa.float64()),
    ("open", pa.float64()),
    ("high", pa.float64()),
    ("low", pa.float64()),
    ("prev_close", pa.float64()),
    ("session_volume", pa.int64()),
    ("last_trade_qty", pa.int64()),
])

DEPTH_SCHEMA = pa.schema([
    ("ts_exchange", pa.timestamp("us", tz="UTC")),
    ("ts_received", pa.timestamp("us", tz="UTC")),
    ("symbol", pa.string()),
    ("bids_price", pa.list_(pa.float64())),
    ("bids_quantity", pa.list_(pa.int64())),
    ("bids_order_count", pa.list_(pa.int64())),
    ("asks_price", pa.list_(pa.float64())),
    ("asks_quantity", pa.list_(pa.int64())),
    ("asks_order_count", pa.list_(pa.int64())),
    ("total_buy_qty", pa.int64()),
    ("total_sell_qty", pa.int64()),
    ("feed_latency_ms", pa.float64()),
])

HEALTH_SCHEMA = pa.schema([
    ("at", pa.timestamp("us", tz="UTC")),
    ("symbol", pa.string()),
    ("state", pa.string()),
    ("reasons", pa.list_(pa.string())),
    ("order_flow_enabled", pa.bool_()),
    ("flow_state", pa.string()),
])

LIFECYCLE_SCHEMA = pa.schema([
    ("at", pa.timestamp("us", tz="UTC")),
    ("symbol", pa.string()),
    ("kind", pa.string()),
    ("detail_json", pa.string()),
    ("sequence", pa.int64()),
])

GAP_SCHEMA = pa.schema([
    ("started_at", pa.timestamp("us", tz="UTC")),
    ("ended_at", pa.timestamp("us", tz="UTC")),
    ("symbol", pa.string()),
    ("duration_s", pa.float64()),
    ("cause", pa.string()),
])

_SAFE = re.compile(r"[^A-Za-z0-9_-]+")
_SAFE_DETAIL_KEYS = frozenset({
    "after_reconnect", "attempt", "cause", "delay_s", "reason",
    "reconnects", "stale_after_s", "symbols",
})


def _safe_symbol(symbol: str) -> str:
    return _SAFE.sub("_", symbol)


def _dt(value: Optional[datetime]):
    if value is None:
        return None
    if value.tzinfo is None:
        raise ValueError("recorded timestamps must be timezone-aware")
    return value.astimezone(timezone.utc)


def _quote_row(q: QuoteUpdate) -> dict:
    return {
        "ts_exchange": _dt(q.ts_exchange),
        "ts_received": _dt(q.ts_received),
        "symbol": q.symbol,
        "ltp": q.ltp,
        "open": q.open,
        "high": q.high,
        "low": q.low,
        "prev_close": q.prev_close,
        "session_volume": q.session_volume,
        "last_trade_qty": q.last_trade_qty,
    }


def _optional_level_values(levels, field: str):
    values = [getattr(level, field) for level in levels]
    return None if not values or all(value is None for value in values) else values


def _depth_row(d: DepthSnapshot) -> dict:
    return {
        "ts_exchange": _dt(d.ts_exchange),
        "ts_received": _dt(d.ts_received),
        "symbol": d.symbol,
        "bids_price": [lv.price for lv in d.bids],
        "bids_quantity": [lv.quantity for lv in d.bids],
        "bids_order_count": _optional_level_values(d.bids, "order_count"),
        "asks_price": [lv.price for lv in d.asks],
        "asks_quantity": [lv.quantity for lv in d.asks],
        "asks_order_count": _optional_level_values(d.asks, "order_count"),
        "total_buy_qty": d.total_buy_qty,
        "total_sell_qty": d.total_sell_qty,
        "feed_latency_ms": d.feed_latency_ms,
    }


def _partition(ts_received: datetime) -> tuple[str, str]:
    ts_received = _dt(ts_received)
    day = ts_received.astimezone(timezone.utc).date().isoformat()
    return day, ts_received.strftime("%H%M%S%f")[:-3]


class ParquetWriter:
    """Append quotes/depth snapshots as partitioned parquet files.

    One file per (date, symbol, kind, flush) — flush granularity is the
    caller's choice (per message for research sharpness, batched for rate).
    """

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self._lifecycle_sequence = 0

    def write_quotes(self, quotes: Iterable[QuoteUpdate]) -> int:
        rows = [(_partition(q.ts_received), _quote_row(q)) for q in quotes]
        return self._flush(rows, QUOTE_SCHEMA, "quotes")

    def write_depth(self, snapshots: Iterable[DepthSnapshot]) -> int:
        rows = [(_partition(d.ts_received), _depth_row(d)) for d in snapshots]
        return self._flush(rows, DEPTH_SCHEMA, "depth")

    def write_event(self, event) -> int:
        if isinstance(event, QuoteUpdate):
            return self.write_quotes([event])
        if isinstance(event, DepthSnapshot):
            return self.write_depth([event])
        raise TypeError(f"unsupported event type {type(event)!r}")

    def write_health(self, at: datetime, verdict, *, symbol: str = "__FEED__") -> int:
        return self.write_health_batch([(at, verdict, symbol)])

    def write_health_batch(self, records) -> int:
        rows = []
        for at, verdict, symbol in records:
            state = getattr(verdict.state, "value", str(verdict.state))
            row = {
                "at": _dt(at),
                "symbol": symbol,
                "state": state,
                "reasons": list(verdict.reasons),
                "order_flow_enabled": verdict.order_flow_enabled,
                "flow_state": verdict.flow_state,
            }
            rows.append((_partition(at), row))
        return self._flush(rows, HEALTH_SCHEMA, "health")

    def write_lifecycle(self, event, *, symbol: str = "__FEED__") -> int:
        detail = {
            key: value for key, value in dict(event.detail).items()
            if key in _SAFE_DETAIL_KEYS
        }
        row = {
            "at": _dt(event.at),
            "symbol": symbol,
            "kind": str(event.kind),
            "detail_json": json.dumps(
                detail, ensure_ascii=True, sort_keys=True, separators=(",", ":")
            ),
            "sequence": self._lifecycle_sequence,
        }
        self._lifecycle_sequence += 1
        return self._flush([(_partition(event.at), row)], LIFECYCLE_SCHEMA, "lifecycle")

    def write_gap(
        self,
        started_at: datetime,
        ended_at: datetime,
        cause: str,
        *,
        symbol: str = "__FEED__",
    ) -> int:
        duration_s = (ended_at - started_at).total_seconds()
        if duration_s < 0:
            raise ValueError("gap end cannot precede gap start")
        row = {
            "started_at": _dt(started_at),
            "ended_at": _dt(ended_at),
            "symbol": symbol,
            "duration_s": duration_s,
            "cause": str(cause),
        }
        return self._flush([(_partition(started_at), row)], GAP_SCHEMA, "gaps")

    def _flush(self, rows, schema: pa.Schema, kind: str) -> int:
        grouped: dict[tuple[str, str], list[tuple[str, dict]]] = {}
        for (day, stamp), row in rows:
            safe_symbol = _safe_symbol(row["symbol"])
            grouped.setdefault((day, safe_symbol), []).append((stamp, row))
        written = 0
        for (day, symbol), batch in grouped.items():
            folder = self.root / f"date={day}" / f"symbol={symbol}"
            folder.mkdir(parents=True, exist_ok=True)
            table = pa.Table.from_pylist([row for _, row in batch], schema=schema)
            stamp = batch[0][0]
            unique = uuid.uuid4().hex
            final_path = folder / f"{kind}-{stamp}-{unique}.parquet"
            temp_path = folder / f".{kind}-{unique}.tmp"
            try:
                pq.write_table(table, temp_path)
                os.link(temp_path, final_path)
            finally:
                temp_path.unlink(missing_ok=True)
            written += 1
        return written
