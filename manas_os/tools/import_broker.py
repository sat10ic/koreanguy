"""Import Zerodha equity tradebooks into the Manas journal.

The public helpers in this module are also used by ``broker_audit``.  The
importer deliberately keeps broker P&L separate from ``journal_trades.r_result``:
Zerodha tradebooks do not contain the initial stop needed to compute an R
multiple, so inventing one would corrupt the journal's R statistics.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sqlite3
import sys
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Iterable, Sequence

SOURCE = "zerodha_import"
TRADEBOOK_COLUMNS = {
    "symbol", "trade_date", "trade_type", "quantity", "price", "trade_id",
    "order_id", "order_execution_time",
}


@dataclass(frozen=True)
class Fill:
    symbol: str
    side: str
    qty: float
    price: float
    executed_at: datetime
    trade_date: date
    order_id: str
    trade_ids: tuple[str, ...]


@dataclass(frozen=True)
class Match:
    symbol: str
    direction: str
    qty: float
    entry_price: float
    exit_price: float
    entry_at: datetime
    exit_at: datetime
    entry_order_id: str
    exit_order_id: str
    pnl: float
    return_pct: float
    cycle: int
    import_key: str

    @property
    def holding_days(self) -> int:
        return (self.exit_at.date() - self.entry_at.date()).days


@dataclass(frozen=True)
class OpenLot:
    symbol: str
    qty: float
    price: float
    opened_at: datetime
    order_id: str
    direction: str


@dataclass(frozen=True)
class ImportResult:
    inserted: int
    skipped: int
    duplicate_trade_ids: int
    matches: tuple[Match, ...]
    open_lots: tuple[OpenLot, ...]


def _clean_header(value: object) -> str:
    return str(value or "").strip().lower().replace(" ", "_")


def _id_sort(value: str) -> tuple[int, int | str]:
    return (0, int(value)) if value.isdigit() else (1, value)


def _fill_sort(fill: Fill) -> tuple[object, ...]:
    first_trade_id = min(fill.trade_ids, key=_id_sort) if fill.trade_ids else fill.order_id
    return (fill.executed_at, _id_sort(first_trade_id), fill.symbol, fill.side)


def _parse_date(value: object) -> date:
    text = str(value or "").strip()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%d-%b-%Y", "%d %b %Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    try:
        return datetime.fromisoformat(text).date()
    except ValueError as exc:
        raise ValueError(f"unrecognized trade date {text!r}") from exc


def _parse_timestamp(value: object, fallback: date) -> datetime:
    text = str(value or "").strip()
    if not text:
        return datetime.combine(fallback, datetime.min.time())
    normalized = text.replace("T", " ")
    for fmt in (
        "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f",
        "%d-%m-%Y %H:%M:%S", "%d/%m/%Y %H:%M:%S",
        "%d-%b-%Y %H:%M:%S", "%d %b %Y %H:%M:%S",
    ):
        try:
            return datetime.strptime(normalized, fmt)
        except ValueError:
            pass
    try:
        parsed = datetime.fromisoformat(normalized)
        return parsed.replace(tzinfo=None) if parsed.tzinfo else parsed
    except ValueError as exc:
        raise ValueError(f"unrecognized execution timestamp {text!r}") from exc


def read_tradebooks(paths: Sequence[str | Path]) -> tuple[list[dict[str, object]], int]:
    """Read and merge tradebooks, keeping the first identical ``trade_id``.

    A repeated trade ID with different economic fields is rejected rather than
    silently selecting one copy.
    """
    unique: dict[str, dict[str, object]] = {}
    duplicates = 0
    for raw_path in paths:
        path = Path(raw_path)
        with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames is None:
                raise ValueError(f"{path}: empty CSV or missing header")
            mapping = {_clean_header(name): name for name in reader.fieldnames}
            missing = TRADEBOOK_COLUMNS - mapping.keys()
            if missing:
                raise ValueError(f"{path}: missing columns: {', '.join(sorted(missing))}")
            for line_no, source_row in enumerate(reader, start=2):
                row = {name: source_row[original] for name, original in mapping.items()}
                trade_id = str(row.get("trade_id") or "").strip()
                if not trade_id:
                    raise ValueError(f"{path}:{line_no}: empty trade_id")
                normalized = {
                    "symbol": str(row.get("symbol") or "").strip().upper(),
                    "trade_date": _parse_date(row.get("trade_date")),
                    "trade_type": str(row.get("trade_type") or "").strip().upper(),
                    "quantity": float(str(row.get("quantity") or "0").replace(",", "")),
                    "price": float(str(row.get("price") or "0").replace(",", "")),
                    "trade_id": trade_id,
                    "order_id": str(row.get("order_id") or trade_id).strip(),
                    "order_execution_time": row.get("order_execution_time"),
                }
                if normalized["trade_type"] not in {"BUY", "SELL"}:
                    raise ValueError(f"{path}:{line_no}: unsupported trade_type {normalized['trade_type']!r}")
                if not normalized["symbol"]:
                    raise ValueError(f"{path}:{line_no}: empty symbol")
                if (not math.isfinite(normalized["quantity"]) or not math.isfinite(normalized["price"])
                        or normalized["quantity"] <= 0 or normalized["price"] <= 0):
                    raise ValueError(f"{path}:{line_no}: quantity and price must be positive")
                previous = unique.get(trade_id)
                if previous is not None:
                    comparable = ("symbol", "trade_date", "trade_type", "quantity", "price", "order_id")
                    if any(previous[key] != normalized[key] for key in comparable):
                        raise ValueError(f"conflicting rows share trade_id {trade_id!r}")
                    duplicates += 1
                    continue
                unique[trade_id] = normalized
    return list(unique.values()), duplicates


def aggregate_fills(rows: Iterable[dict[str, object]]) -> list[Fill]:
    """Collapse same-order executions to one weighted-average fill."""
    groups: dict[tuple[object, ...], list[tuple[dict[str, object], datetime]]] = defaultdict(list)
    for row in rows:
        trade_day = row["trade_date"]
        assert isinstance(trade_day, date)
        executed = _parse_timestamp(row.get("order_execution_time"), trade_day)
        key = (row["symbol"], row["trade_type"], row["order_id"], trade_day)
        groups[key].append((row, executed))
    fills: list[Fill] = []
    for (symbol, side, order_id, trade_day), members in groups.items():
        qty = sum(float(row["quantity"]) for row, _ in members)
        notional = sum(float(row["quantity"]) * float(row["price"]) for row, _ in members)
        executed = min(timestamp for _, timestamp in members)
        fills.append(Fill(
            symbol=str(symbol), side=str(side), qty=qty, price=notional / qty,
            executed_at=executed, trade_date=executed.date(), order_id=str(order_id),
            trade_ids=tuple(sorted(str(row["trade_id"]) for row, _ in members)),
        ))
    return sorted(fills, key=_fill_sort)


@dataclass
class _MutableLot:
    qty: float
    price: float
    opened_at: datetime
    order_id: str
    direction: str


def _match_key(fill_in: Fill, fill_out: Fill, qty: float) -> str:
    payload = "|".join((
        SOURCE, fill_in.symbol, fill_in.order_id, fill_out.order_id,
        fill_in.executed_at.isoformat(), fill_out.executed_at.isoformat(),
        fill_in.side, fill_out.side, f"{fill_in.price:.10f}", f"{fill_out.price:.10f}",
        f"{qty:.10f}",
    ))
    return "zerodha:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def fifo_match(fills: Sequence[Fill]) -> tuple[list[Match], list[OpenLot]]:
    """FIFO match long and intraday-short inventory, including partial exits."""
    books: dict[str, deque[_MutableLot]] = defaultdict(deque)
    cycles: dict[str, int] = defaultdict(lambda: 1)
    matches: list[Match] = []
    for fill in sorted(fills, key=_fill_sort):
        book = books[fill.symbol]
        incoming_direction = "long" if fill.side == "BUY" else "short"
        remaining = fill.qty
        while remaining > 1e-9 and book and book[0].direction != incoming_direction:
            lot = book[0]
            closed_qty = min(remaining, lot.qty)
            entry_price, exit_price = (
                (lot.price, fill.price) if lot.direction == "long" else (lot.price, fill.price)
            )
            pnl = ((fill.price - lot.price) if lot.direction == "long" else (lot.price - fill.price)) * closed_qty
            cost = lot.price * closed_qty
            entry_fill = Fill(fill.symbol, "BUY" if lot.direction == "long" else "SELL", closed_qty,
                              lot.price, lot.opened_at, lot.opened_at.date(), lot.order_id, ())
            matches.append(Match(
                symbol=fill.symbol, direction=lot.direction, qty=closed_qty,
                entry_price=entry_price, exit_price=exit_price,
                entry_at=lot.opened_at, exit_at=fill.executed_at,
                entry_order_id=lot.order_id, exit_order_id=fill.order_id,
                pnl=pnl, return_pct=(pnl / cost * 100.0 if cost else 0.0),
                cycle=cycles[fill.symbol],
                import_key=_match_key(entry_fill, fill, closed_qty),
            ))
            lot.qty -= closed_qty
            remaining -= closed_qty
            if lot.qty <= 1e-9:
                book.popleft()
            if not book:
                cycles[fill.symbol] += 1
        if remaining > 1e-9:
            book.append(_MutableLot(remaining, fill.price, fill.executed_at, fill.order_id, incoming_direction))
    open_lots = [
        OpenLot(symbol, lot.qty if lot.direction == "long" else -lot.qty, lot.price,
                lot.opened_at, lot.order_id, lot.direction)
        for symbol, book in sorted(books.items()) for lot in book if lot.qty > 1e-9
    ]
    return matches, open_lots


def ensure_broker_schema(conn: sqlite3.Connection) -> None:
    """Apply only additive, idempotent broker-import schema changes."""
    conn.execute(
        "CREATE TABLE IF NOT EXISTS broker_open_lots ("
        "symbol TEXT NOT NULL, qty REAL NOT NULL, avg_cost REAL NOT NULL, "
        "first_buy_date TEXT NOT NULL, import_key TEXT NOT NULL UNIQUE)"
    )
    have = {row[1] for row in conn.execute("PRAGMA table_info(journal_trades)")}
    additions = {
        "exit_date": "TEXT", "source": "TEXT", "import_key": "TEXT",
        "broker_realized_pnl": "REAL", "broker_return_pct": "REAL",
        "broker_entry_order_id": "TEXT", "broker_exit_order_id": "TEXT",
        "broker_direction": "TEXT", "broker_holding_days": "INTEGER",
    }
    for name, ddl in additions.items():
        if name not in have:
            conn.execute(f"ALTER TABLE journal_trades ADD COLUMN {name} {ddl}")
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_journal_trades_import_key "
        "ON journal_trades(import_key) WHERE import_key IS NOT NULL"
    )


def _open_lot_rows(open_lots: Sequence[OpenLot]) -> list[tuple[str, float, float, str, str]]:
    grouped: dict[tuple[str, str], list[OpenLot]] = defaultdict(list)
    for lot in open_lots:
        grouped[(lot.symbol, lot.direction)].append(lot)
    rows = []
    for (symbol, direction), lots in sorted(grouped.items()):
        signed_qty = sum(lot.qty for lot in lots)
        absolute_qty = sum(abs(lot.qty) for lot in lots)
        avg_cost = sum(abs(lot.qty) * lot.price for lot in lots) / absolute_qty
        first_date = min(lot.opened_at.date() for lot in lots).isoformat()
        payload = f"{SOURCE}|{symbol}|{direction}|{signed_qty:.10f}|{avg_cost:.10f}|{first_date}"
        key = "zerodha-open:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()
        rows.append((symbol, signed_qty, avg_cost, first_date, key))
    return rows


def import_tradebooks(paths: Sequence[str | Path], db_path: str | Path) -> ImportResult:
    rows, duplicate_count = read_tradebooks(paths)
    matches, open_lots = fifo_match(aggregate_fills(rows))
    conn = sqlite3.connect(str(db_path))
    try:
        ensure_broker_schema(conn)
        inserted = 0
        skipped = 0
        with conn:
            for match in matches:
                notes = json.dumps({
                    "source": SOURCE, "direction": match.direction,
                    "entry_order_id": match.entry_order_id, "exit_order_id": match.exit_order_id,
                    "realized_pnl": round(match.pnl, 2), "return_pct": round(match.return_pct, 6),
                    "note": "r_result is null: broker export has no initial stop from which to derive R.",
                }, sort_keys=True)
                cursor = conn.execute(
                    "INSERT OR IGNORE INTO journal_trades ("
                    "trade_date, exit_date, symbol, setup, entry, exit, qty, r_result, notes, "
                    "source, import_key, broker_realized_pnl, broker_return_pct, "
                    "broker_entry_order_id, broker_exit_order_id, broker_direction, broker_holding_days) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (match.entry_at.date().isoformat(), match.exit_at.date().isoformat(), match.symbol,
                     "Zerodha FIFO", match.entry_price, match.exit_price, match.qty, notes, SOURCE,
                     match.import_key, match.pnl, match.return_pct, match.entry_order_id,
                     match.exit_order_id, match.direction, match.holding_days),
                )
                if cursor.rowcount == 1:
                    inserted += 1
                else:
                    skipped += 1
            conn.execute("DELETE FROM broker_open_lots")
            conn.executemany(
                "INSERT INTO broker_open_lots (symbol, qty, avg_cost, first_buy_date, import_key) "
                "VALUES (?, ?, ?, ?, ?)", _open_lot_rows(open_lots),
            )
        return ImportResult(inserted, skipped, duplicate_count, tuple(matches), tuple(open_lots))
    finally:
        conn.close()


def _print_open_lots(open_lots: Sequence[OpenLot]) -> None:
    rows = _open_lot_rows(open_lots)
    print("\nOPEN LOTS")
    print(f"{'SYMBOL':<18} {'QTY':>12} {'AVG COST':>14} {'FIRST BUY':>12}")
    if not rows:
        print("(none)")
    for symbol, qty, avg_cost, first_date, _ in rows:
        print(f"{symbol:<18} {qty:>12.4f} {avg_cost:>14.2f} {first_date:>12}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Import Zerodha tradebooks into the Manas journal")
    parser.add_argument("--tradebook", action="append", required=True, help="Zerodha tradebook CSV; repeatable")
    parser.add_argument("--db", required=True, help="SQLite database path")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = import_tradebooks(args.tradebook, args.db)
    except Exception as exc:  # CLI boundary: give a concise, non-fabricated failure
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"journal inserted={result.inserted} skipped={result.skipped}")
    print(f"input duplicate trade_ids={result.duplicate_trade_ids}")
    _print_open_lots(result.open_lots)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
