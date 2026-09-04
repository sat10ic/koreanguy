"""DuckDB research views over the parquet store (U-P0.5).

Read-only research layer: same files the recorder wrote, queried in place.
A quoted ``GlobalDirectory``-style table scan over ``**/*.parquet`` globs;
missing optional columns surface as NULLs, exactly as recorded (R12).
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from orderflow.market_data.schemas import DepthLevel, DepthSnapshot

try:
    import duckdb
except ImportError as exc:  # pragma: no cover - environment-specific
    duckdb = None
    _duckdb_import_error = exc


class DuckRepository:
    """SQL access over the partitioned parquet store."""

    def __init__(self, root: Path) -> None:
        if duckdb is None:
            raise ImportError(
                "duckdb is required for the research layer "
                f"({ _duckdb_import_error }). Install it into the session venv."
            )
        self.root = Path(root)
        if not self.root.exists():
            raise FileNotFoundError(f"no parquet store at {self.root}")
        self.con = duckdb.connect()  # in-memory: research reads, never writes

    def _glob(self, kind: str) -> str:
        pattern = self.root / "**" / f"{kind}-*.parquet"
        return str(pattern).replace("\\", "/").replace("'", "''")

    def _install(self, kind: str) -> bool:
        """Create the view if any files exist for this kind; an empty store is
        not an error, it just yields no rows."""
        if not any(self.root.rglob(f"{kind}-*.parquet")):
            return False
        self.con.execute(
            f"CREATE OR REPLACE VIEW {kind} AS SELECT * FROM "
            f"read_parquet('{self._glob(kind)}', union_by_name=true, hive_partitioning=false)"
        )
        return True

    def install_views(self) -> dict:
        return {
            kind: self._install(kind)
            for kind in ("quotes", "depth", "health", "lifecycle", "gaps")
        }

    def quotes(self, symbol: Optional[str] = None, start=None, end=None):
        if not self._install("quotes"):
            return []
        clauses = ["TRUE"]
        params = []
        if symbol:
            clauses.append("symbol = ?")
            params.append(symbol)
        if start is not None:
            clauses.append("ts_received >= ?")
            params.append(start)
        if end is not None:
            clauses.append("ts_received < ?")
            params.append(end)
        where = " AND ".join(clauses)
        return self.con.execute(
            f"SELECT * FROM quotes WHERE {where} ORDER BY ts_received", params
        ).fetchall()

    def depth(self, symbol: Optional[str] = None, start=None, end=None):
        if not self._install("depth"):
            return []
        clauses = ["TRUE"]
        params = []
        if symbol:
            clauses.append("symbol = ?")
            params.append(symbol)
        if start is not None:
            clauses.append("ts_received >= ?")
            params.append(start)
        if end is not None:
            clauses.append("ts_received < ?")
            params.append(end)
        where = " AND ".join(clauses)
        return self.con.execute(
            f"SELECT * FROM depth WHERE {where} ORDER BY ts_received", params
        ).fetchall()

    def coverage(self) -> list:
        """Per symbol/day event counts — the honest-coverage summary."""
        parts = []
        if self._install("quotes"):
            parts.append(
                "SELECT symbol, CAST(ts_received AS DATE) AS day, 'quote' AS kind, COUNT(*) AS n FROM quotes GROUP BY 1, 2, 3"
            )
        if self._install("depth"):
            parts.append(
                "SELECT symbol, CAST(ts_received AS DATE) AS day, 'depth' AS kind, COUNT(*) AS n FROM depth GROUP BY 1, 2, 3"
            )
        if not parts:
            return []
        return self.con.execute(
            " UNION ALL ".join(parts) + " ORDER BY day, symbol, kind"
        ).fetchall()

    def health(self, symbol: Optional[str] = None):
        return self._simple_rows("health", "at", symbol)

    def lifecycle(self):
        if not self._install("lifecycle"):
            return []
        return self.con.execute(
            'SELECT * FROM lifecycle ORDER BY "at", sequence'
        ).fetchall()

    def gaps(self):
        return self._simple_rows("gaps", "started_at", None)

    def _simple_rows(self, kind: str, order_column: str, symbol: Optional[str]):
        if not self._install(kind):
            return []
        if symbol is None:
            return self.con.execute(
                f'SELECT * FROM {kind} ORDER BY "{order_column}"'
            ).fetchall()
        return self.con.execute(
            f'SELECT * FROM {kind} WHERE symbol=? ORDER BY "{order_column}"',
            [symbol],
        ).fetchall()

    def replay_depth(self, symbol: str, *, day: str | None = None) -> list[DepthSnapshot]:
        """Rebuild canonical depth snapshots in recorded receive-time order."""
        if not self._install("depth"):
            return []
        clauses = ["symbol = ?"]
        params = [symbol]
        if day is not None:
            clauses.append("CAST(ts_received AS DATE) = CAST(? AS DATE)")
            params.append(day)
        cursor = self.con.execute(
            "SELECT * FROM depth WHERE " + " AND ".join(clauses) + " ORDER BY ts_received",
            params,
        )
        names = [column[0] for column in cursor.description]
        return [self._depth_snapshot(dict(zip(names, row))) for row in cursor.fetchall()]

    def latest_book(self, symbol: str, *, day: str | None = None) -> DepthSnapshot | None:
        snapshots = self.replay_depth(symbol, day=day)
        return snapshots[-1] if snapshots else None

    @staticmethod
    def _depth_snapshot(row: dict) -> DepthSnapshot:
        def levels(side: str) -> tuple[DepthLevel, ...]:
            prices = row.get(f"{side}_price") or []
            quantities = row.get(f"{side}_quantity") or []
            counts = row.get(f"{side}_order_count")
            if len(prices) != len(quantities):
                raise ValueError(f"recorded {side} price/quantity lengths disagree")
            counts = [None] * len(prices) if counts is None else counts
            if len(counts) != len(prices):
                raise ValueError(f"recorded {side} order-count length disagrees")
            return tuple(
                DepthLevel(price=price, quantity=quantity, order_count=count)
                for price, quantity, count in zip(prices, quantities, counts, strict=True)
            )

        return DepthSnapshot(
            ts_exchange=row.get("ts_exchange"),
            ts_received=row["ts_received"],
            symbol=row["symbol"],
            bids=levels("bids"),
            asks=levels("asks"),
            total_buy_qty=row.get("total_buy_qty"),
            total_sell_qty=row.get("total_sell_qty"),
            feed_latency_ms=row.get("feed_latency_ms"),
        )
