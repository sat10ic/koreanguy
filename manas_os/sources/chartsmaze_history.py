"""Import ChartsMaze's canonical Industry Graphical Analysis time series.

The source is a wide CSV: one Basic Industry per row, one trading date per
column, and each value is cumulative percentage performance from the first
date in the asset. We preserve the raw cumulative series with file provenance;
horizon returns are derived causally at read time.
"""
from __future__ import annotations

import csv
import sqlite3
from pathlib import Path


def import_industry_graphical(conn: sqlite3.Connection, path: str | Path) -> dict:
    source = Path(path)
    with source.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or reader.fieldnames[0] != "Basic Industry":
            raise ValueError("expected ChartsMaze Industry Graphical Analysis CSV")
        dates = [d for d in reader.fieldnames[1:] if d]
        rows = []
        industries = 0
        for record in reader:
            name = (record.get("Basic Industry") or "").strip()
            if not name:
                continue
            industries += 1
            for trade_date in dates:
                raw = (record.get(trade_date) or "").strip()
                if not raw:
                    continue
                try:
                    value = float(raw)
                except ValueError:
                    continue
                rows.append((trade_date, name, value, str(source.resolve())))
    conn.executemany(
        "INSERT OR REPLACE INTO chartsmaze_industry_history "
        "(trade_date, name, cumulative_return, source_file) VALUES (?, ?, ?, ?)",
        rows,
    )
    conn.commit()
    return {
        "rows": len(rows), "industries": industries,
        "min_date": min(dates) if dates else None,
        "max_date": max(dates) if dates else None,
        "source_file": str(source.resolve()),
    }


def horizon_return(conn: sqlite3.Connection, name: str, as_of: str, sessions: int) -> float | None:
    rows = conn.execute(
        "SELECT cumulative_return FROM chartsmaze_industry_history "
        "WHERE name = ? AND trade_date <= ? ORDER BY trade_date DESC LIMIT ?",
        (name, as_of, sessions + 1),
    ).fetchall()
    if len(rows) < sessions + 1:
        return None
    latest = 1.0 + float(rows[0][0]) / 100.0
    prior = 1.0 + float(rows[-1][0]) / 100.0
    if prior == 0:
        return None
    return (latest / prior - 1.0) * 100.0
