"""Raw + derived market-data storage (build-manual U-P0.5 / P0.2 Task 2).

Layout: ``<root>/date=YYYY-MM-DD/symbol=SYM/<kind>-<n>.parquet``.
Nulls are stored as nulls (R5/R12) — a missing optional field is never
backfilled with zeros. The writer never touches live connections; callers
feed it canonical events.
"""
from orderflow.storage.parquet_writer import ParquetWriter
from orderflow.storage.duckdb_repo import DuckRepository
from orderflow.storage.recorder import ContinuousRecorder

__all__ = ["ParquetWriter", "DuckRepository", "ContinuousRecorder"]
