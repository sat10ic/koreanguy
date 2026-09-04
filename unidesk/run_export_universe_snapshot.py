"""ROTATION R-0.3 — nightly universe membership snapshot.

The reference ``universe_snapshots.parquet`` had stopped at 2026-08-20
(HANDOFF_2026-09-04_MARKET_ROTATION §3.2): a membership table that ages
quietly rots every sector/group aggregate built on it. This step appends
tonight's scanned universe — {symbol, as_of_date, sector, industry,
is_tradeable} — so membership stops going stale.

    .venv-orderflow/Scripts/python.exe unidesk/run_export_universe_snapshot.py \
        [--session 2026-09-03]

Dedupe: one row per (as_of_date, symbol) — a re-run for the same session
rewrites that session's rows, never duplicates them.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from unidesk.contracts.base import ContractError, require_str  # noqa: E402

REPORTS = REPO / "data" / "market" / "reports"
SECTOR_PARQUET = REPO / "data" / "market" / "reference" / "industry_sector.parquet"
INDUSTRY_PARQUET = REPO / "data" / "market" / "reference" / "industry_mapping.parquet"
DEST = REPO / "data" / "market" / "reference" / "universe_snapshots.parquet"
SOURCE_TIER = "UNIDESK_NIGHTLY"


def _newest_session() -> str:
    newest = sorted(REPORTS.glob("tonight_*.json"), reverse=True)[0]
    return json.loads(newest.read_text(encoding="utf-8"))["session_date"]


def _symbol_sector_map() -> dict:
    """industry_mapping.parquet: symbol -> industry; industry_sector.parquet:
    industry -> sector. Two joins, both small."""
    import pyarrow.parquet as pq

    industry_to_sector: dict = {}
    if SECTOR_PARQUET.exists():
        t = pq.read_table(SECTOR_PARQUET)
        for i in range(t.num_rows):
            ind = str(t.column("industry")[i].as_py() or "")
            sec = str(t.column("sector")[i].as_py() or "") or None
            if ind:
                industry_to_sector[ind] = sec

    out: dict = {}
    if INDUSTRY_PARQUET.exists():
        t = pq.read_table(INDUSTRY_PARQUET)
        for i in range(t.num_rows):
            sym = str(t.column("symbol")[i].as_py() or "").upper()
            ind = str(t.column("industry")[i].as_py() or "") or None
            if not sym:
                continue
            out[sym] = {"sector": industry_to_sector.get(ind), "industry": ind}
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--session", default=None, help="ISO date; default = newest bundled report")
    args = ap.parse_args()

    session = args.session or _newest_session()
    date.fromisoformat(session)

    report_path = REPORTS / f"tonight_{session}.json"
    if not report_path.exists():
        print(f"[universe-snapshot] no report for {session}")
        return 1
    report = json.loads(report_path.read_text(encoding="utf-8"))
    universe = report.get("honesty_footer", {}).get("universe_symbols") or []
    if not universe:
        print("[universe-snapshot] report carries no universe_symbols — aborting")
        return 1

    sector_map = _symbol_sector_map()
    new_rows = []
    for raw in universe:
        try:
            symbol = require_str(str(raw).upper(), "symbol")
        except ContractError:
            continue
        info = sector_map.get(symbol, {})
        new_rows.append({
            "symbol": symbol,
            "as_of_date": session,
            "series": "EQ",
            "sector": info.get("sector"),
            "industry": info.get("industry"),
            "is_tradeable": True,
            "source_tier": SOURCE_TIER,
            "source_file": f"tonight_{session}.json",
        })

    import pyarrow as pa
    import pyarrow.parquet as pq

    if DEST.exists():
        old = pq.read_table(DEST).to_pylist()
        old = [r for r in old if str(r.get("as_of_date"))[:10] != session]
    else:
        old = []
    merged = old + new_rows
    merged.sort(key=lambda r: (str(r.get("as_of_date")), str(r.get("symbol"))))

    schema = pa.schema([
        ("symbol", pa.string()), ("as_of_date", pa.string()), ("series", pa.string()),
        ("sector", pa.string()), ("industry", pa.string()), ("is_tradeable", pa.bool_()),
        ("source_tier", pa.string()), ("source_file", pa.string()),
    ])
    table = pa.Table.from_pylist([{**r,
        "as_of_date": str(r.get("as_of_date"))[:10],
        "is_tradeable": bool(r.get("is_tradeable", True))} for r in merged], schema=schema)
    DEST.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, DEST)

    import collections

    dates = collections.Counter(str(r["as_of_date"]) for r in merged)
    print(f"[universe-snapshot] {session}: {len(new_rows)} rows appended "
          f"({len(dates)} sessions, {len(merged)} total) -> {DEST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
