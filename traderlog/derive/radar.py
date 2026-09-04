"""Pure, cited derivation for the INS-1 Symbol co-attention Radar."""
from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from datetime import date, datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo


SOURCE_KINDS = frozenset({"trade_event", "watch_idea", "theme"})
_KOLKATA = ZoneInfo("Asia/Kolkata")


def _utc_datetime(value: Any) -> datetime | None:
    """Return an aware UTC datetime, rejecting absent or malformed source values."""
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def _normalize_symbol(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    if normalized.startswith("#"):
        normalized = normalized[1:].strip()
    normalized = normalized.upper()
    return normalized or None


def _normalize_handle(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    if normalized.startswith("@"):
        normalized = normalized[1:].strip()
    return normalized.casefold() or None


def _symbols_from_json(value: Any) -> tuple[set[str] | None, int]:
    """Return normalized post symbols, or ``None`` for invalid JSON.

    The second item counts invalid array values. A post contributes at most one
    mention per normalized symbol even if its classifier array repeats it.
    """
    if not isinstance(value, str):
        return None, 0
    try:
        parsed = json.loads(value)
    except (TypeError, ValueError):
        return None, 0
    if not isinstance(parsed, list):
        return None, 0

    symbols: set[str] = set()
    invalid_values = 0
    for item in parsed:
        symbol = _normalize_symbol(item)
        if symbol is None:
            invalid_values += 1
        else:
            symbols.add(symbol)
    return symbols, invalid_values


def _strongest_cluster(mentions: list[dict[str, Any]]) -> dict[str, Any]:
    """Choose the best inclusive seven-calendar-day cluster deterministically.

    Candidate windows end on each mention's Asia/Kolkata calendar date. Ties choose the
    most recent end date after distinct normalized traders and mention count.
    """
    ordered = sorted(mentions, key=lambda mention: (mention["date"], mention["post_id"]))
    best: tuple[int, int, date, list[dict[str, Any]]] | None = None
    for end_date in sorted({mention["date"] for mention in ordered}):
        start_date = end_date - timedelta(days=6)
        window = [
            mention for mention in ordered if start_date <= mention["date"] <= end_date
        ]
        candidate = (
            len({mention["trader_key"] for mention in window}),
            len(window),
            end_date,
            window,
        )
        if best is None or candidate[:3] > best[:3]:
            best = candidate

    assert best is not None  # callers invoke this only for a non-empty symbol.
    distinct_traders, mention_count, end_date, window = best
    return {
        "start_date": (end_date - timedelta(days=6)).isoformat(),
        "end_date": end_date.isoformat(),
        "distinct_trader_count": distinct_traders,
        "mention_count": mention_count,
    }


def build_radar(
    rows: Iterable[Mapping[str, Any]],
    *,
    validated_symbols: Iterable[str],
    days: int,
    min_traders: int,
    window_end: str,
) -> dict[str, Any]:
    """Build a deterministic Radar payload from database-independent source rows.

    ``days`` is an inclusive Asia/Kolkata calendar-day window ending on
    ``window_end``. ``window_end`` and all source timestamps remain UTC values;
    only their calendar-date grouping converts to Asia/Kolkata.
    ``rows`` need the selected post and classifier fields; this function does no
    database I/O and retains the exact evidence fields supplied by the caller.
    """
    if not 1 <= days <= 730:
        raise ValueError("days must be in the range 1..730")
    if not 1 <= min_traders <= 17:
        raise ValueError("min_traders must be in the range 1..17")
    parsed_window_end = _utc_datetime(window_end)
    if parsed_window_end is None:
        raise ValueError("window_end must be an ISO-8601 UTC timestamp")

    window_end_date = parsed_window_end.astimezone(_KOLKATA).date()
    window_start_date = window_end_date - timedelta(days=days - 1)
    validated = {
        normalized
        for value in validated_symbols
        if (normalized := _normalize_symbol(value)) is not None
    }
    by_symbol: dict[str, list[dict[str, Any]]] = {}
    classified_eligible_post_count = 0
    included_mention_count = 0
    invalid_symbol_json_count = 0
    invalid_symbol_value_count = 0
    invalid_timestamp_count = 0
    invalid_handle_count = 0

    for row in rows:
        kind = row.get("kind")
        if kind not in SOURCE_KINDS:
            continue

        parsed_ts = _utc_datetime(row.get("ts_utc"))
        if parsed_ts is None:
            invalid_timestamp_count += 1
            continue
        mention_date = parsed_ts.astimezone(_KOLKATA).date()
        if not window_start_date <= mention_date <= window_end_date:
            continue
        classified_eligible_post_count += 1

        trader_key = _normalize_handle(row.get("handle"))
        if trader_key is None:
            invalid_handle_count += 1
            continue

        symbols, invalid_values = _symbols_from_json(row.get("symbols"))
        if symbols is None:
            invalid_symbol_json_count += 1
            continue
        invalid_symbol_value_count += invalid_values

        for symbol in symbols:
            evidence = {
                "post_id": row.get("post_id"),
                "handle": row.get("handle"),
                "ts_utc": row.get("ts_utc"),
                "url": row.get("url"),
                "text": row.get("text"),
                "kind": kind,
                "confidence": row.get("confidence"),
            }
            by_symbol.setdefault(symbol, []).append(
                {
                    "date": mention_date,
                    "parsed_ts": parsed_ts,
                    "post_id": str(row.get("post_id") or ""),
                    "trader_key": trader_key,
                    "evidence": evidence,
                }
            )
            included_mention_count += 1

    ranked_symbols: list[dict[str, Any]] = []
    unvalidated_symbols: list[dict[str, Any]] = []
    unvalidated_mention_count = 0
    for symbol, mentions in by_symbol.items():
        ordered = sorted(mentions, key=lambda mention: (mention["parsed_ts"], mention["post_id"]))
        trader_count = len({mention["trader_key"] for mention in ordered})
        if symbol not in validated:
            unvalidated_mention_count += len(ordered)
            unvalidated_symbols.append(
                {
                    "symbol": symbol,
                    "mention_count": len(ordered),
                    "distinct_trader_count": trader_count,
                }
            )
            continue
        if trader_count < min_traders:
            continue
        ranked_symbols.append(
            {
                "symbol": symbol,
                "mention_count": len(ordered),
                "distinct_trader_count": trader_count,
                "first_mention_ts": ordered[0]["evidence"]["ts_utc"],
                "last_mention_ts": ordered[-1]["evidence"]["ts_utc"],
                "strongest_cluster": _strongest_cluster(ordered),
                "evidence": [mention["evidence"] for mention in ordered],
            }
        )

    ranked_symbols.sort(
        key=lambda symbol: (
            -symbol["strongest_cluster"]["distinct_trader_count"],
            -date.fromisoformat(symbol["strongest_cluster"]["end_date"]).toordinal(),
            -symbol["distinct_trader_count"],
            symbol["symbol"],
        )
    )
    unvalidated_symbols.sort(key=lambda symbol: symbol["symbol"])

    return {
        "requested": {"days": days, "min_traders": min_traders},
        "window": {
            "start_date": window_start_date.isoformat(),
            "end_date": window_end_date.isoformat(),
        },
        "classified_eligible_post_count": classified_eligible_post_count,
        "included_mention_count": included_mention_count,
        "coverage_debt": {
            "invalid_symbol_json_count": invalid_symbol_json_count,
            "invalid_symbol_value_count": invalid_symbol_value_count,
            "invalid_timestamp_count": invalid_timestamp_count,
            "invalid_handle_count": invalid_handle_count,
            "unvalidated_mention_count": unvalidated_mention_count,
            "unvalidated_symbols": unvalidated_symbols,
        },
        "co_attention": ranked_symbols,
    }
