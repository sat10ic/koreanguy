"""Reference-data ingestion from Chartsmaze dumps (DECISIONS D10-era sources).

One-time/periodic reference tables that bhavcopy cannot provide, parsed from
the dated dump folders the owner already has:

* industry mapping   — ``sector-analytics-*-stocks.csv``  (ticker,industry,rs)
* industry→sector    — ``sector-analytics-*-industries.csv`` (name,sector,pct)
* results calendar   — ``analytics/results-calendar.csv``  (results dates + growth)
* nexus fill-in      — ``manas_os/data/nexus_industry_map.csv`` (read-only;
  Chartsmaze keeps any symbol it already mapped — taxonomies disagree)

Persisted as parquet under ``data/market/reference/``. Headers carry a UTF-8
BOM (the U+FEFF character before the first header name) — stripped.
Unknown/malformed rows are skipped and counted, never coerced (R12).
Symbols go through ``normalize_symbol``. UniDesk does not import ``manas_os``.
"""
from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from typing import Optional

import pyarrow as pa
import pyarrow.parquet as pq

from unidesk.contracts.base import ContractError
from unidesk.momentum.universe.symbol_master import normalize_symbol

SOURCE_TIER_CHARTSMAZE = "CHARTSMAZE"
SOURCE_TIER_NEXUS = "NEXUS_INDUSTRY_MAP"
DEFAULT_NEXUS_CSV = (
    Path(__file__).resolve().parents[3] / "manas_os" / "data" / "nexus_industry_map.csv"
)

REFERENCE_SCHEMA_INDUSTRY = pa.schema([
    ("symbol", pa.string()),
    ("industry", pa.string()),
    ("source_tier", pa.string()),
])
REFERENCE_SCHEMA_SECTOR = pa.schema([
    ("industry", pa.string()),
    ("sector", pa.string()),
])
REFERENCE_SCHEMA_RESULTS = pa.schema([
    ("symbol", pa.string()),
    ("results_date", pa.string()),   # ISO date; kept as string until a typed event store exists
    ("eps_yoy_pct", pa.float64()),
    ("sales_yoy_pct", pa.float64()),
    ("source_file", pa.string()),
])


def _read_rows(path: Path) -> list[dict]:
    with open(path, "r", encoding="utf-8-sig", newline="") as fh:  # utf-8-sig strips BOM
        return list(csv.DictReader(fh))


def parse_industry_mapping(path: Path) -> tuple[list[dict], dict]:
    """``ticker,industry,rs`` → normalized (symbol, industry) rows."""
    rows_out: list[dict] = []
    skipped = 0
    for row in _read_rows(path):
        raw = (row.get("ticker") or "").strip().upper()
        industry = (row.get("industry") or "").strip()
        if not raw or not industry:
            skipped += 1
            continue
        try:
            symbol = normalize_symbol(raw)
        except ContractError:
            skipped += 1
            continue
        rows_out.append({
            "symbol": symbol,
            "industry": industry,
            "source_tier": SOURCE_TIER_CHARTSMAZE,
        })
    return rows_out, {"skipped": skipped}


def parse_nexus_industry_map(path: Path) -> tuple[list[dict], dict]:
    """``symbol,industry,in_our_universe`` from the manas RO dump.

    ``in_our_universe`` is manas's flag, not UniDesk's — we keep the industry
    label either way. Empty/malformed symbols are skipped and counted.
    """
    rows_out: list[dict] = []
    skipped = 0
    for row in _read_rows(path):
        raw = (row.get("symbol") or "").strip().upper()
        industry = (row.get("industry") or "").strip()
        if not raw or not industry:
            skipped += 1
            continue
        try:
            symbol = normalize_symbol(raw)
        except ContractError:
            skipped += 1
            continue
        rows_out.append({
            "symbol": symbol,
            "industry": industry,
            "source_tier": SOURCE_TIER_NEXUS,
        })
    return rows_out, {"skipped": skipped}


def overlay_industry_rows(primary: list[dict], fill: list[dict]) -> tuple[list[dict], dict]:
    """``primary`` (Chartsmaze) wins on symbol. ``fill`` (nexus) only adds gaps.

    The two taxonomies disagree on almost every overlapping name — mixing
    labels for the same symbol would silently rewrite Chartsmaze. Coverage
    reporting is the caller's job.
    """
    by: dict[str, dict] = {}
    for row in primary:
        symbol = row["symbol"]
        by[symbol] = {
            "symbol": symbol,
            "industry": row["industry"],
            "source_tier": row.get("source_tier") or SOURCE_TIER_CHARTSMAZE,
        }
    filled = 0
    blocked = 0
    for row in fill:
        symbol = row["symbol"]
        if symbol in by:
            blocked += 1
            continue
        by[symbol] = {
            "symbol": symbol,
            "industry": row["industry"],
            "source_tier": row.get("source_tier") or SOURCE_TIER_NEXUS,
        }
        filled += 1
    merged = [by[k] for k in sorted(by)]
    stats = {
        "primary": len({r["symbol"] for r in primary}),
        "fill_offered": len({r["symbol"] for r in fill}),
        "filled": filled,
        "blocked_overlap": blocked,
        "total": len(merged),
    }
    return merged, stats


def parse_industry_sector(path: Path) -> dict:
    """``name,sector,pct`` → {industry: sector}."""
    mapping: dict = {}
    for row in _read_rows(path):
        name = (row.get("name") or "").strip()
        sector = (row.get("sector") or "").strip()
        if name and sector:
            mapping[name] = sector
    return mapping


def sector_of(industry_rows: list[dict], industry_sector: dict) -> dict:
    """Compose {symbol: sector}; symbols whose industry lacks a rollup get
    industry-as-sector ONLY if no rollup entry exists — the rollup wins, and
    unresolved ones are simply absent (caller reports coverage)."""
    out: dict = {}
    for row in industry_rows:
        sector = industry_sector.get(row["industry"], row["industry"])
        out[row["symbol"]] = sector
    return out


def parse_results_calendar(path: Path, source_file: Optional[str] = None) -> tuple[list[dict], dict]:
    """``Stock Name, Quarterly Results Date, ...`` → event rows.

    DD/MM/YYYY dates; unparseable rows skipped+counted. Growth columns are
    optional and None when blank."""
    rows_out: list[dict] = []
    skipped = 0
    for row in _read_rows(path):
        raw = (row.get("Stock Name") or "").strip().upper()
        date_raw = (row.get("Quarterly Results Date") or "").strip()
        if not raw or not date_raw:
            skipped += 1
            continue
        try:
            symbol = normalize_symbol(raw)
            results_date = datetime.strptime(date_raw, "%d/%m/%Y").date().isoformat()
        except (ContractError, ValueError):
            skipped += 1
            continue

        def _pct(key: str) -> Optional[float]:
            v = (row.get(key) or "").strip()
            if v in ("", "-"):
                return None
            try:
                return float(v)
            except ValueError:
                return None

        rows_out.append({
            "symbol": symbol,
            "results_date": results_date,
            "eps_yoy_pct": _pct("YoY % EPS Latest"),
            "sales_yoy_pct": _pct("YoY % Sales Latest"),
            "source_file": source_file or path.name,
        })
    return rows_out, {"skipped": skipped}


def _industry_persist_rows(industry_rows: list[dict]) -> list[dict]:
    out = []
    for row in industry_rows:
        out.append({
            "symbol": row["symbol"],
            "industry": row["industry"],
            "source_tier": row.get("source_tier") or SOURCE_TIER_CHARTSMAZE,
        })
    return out


def persist_reference(root: Path, *, industry_rows: list[dict],
                      industry_sector: dict, results_rows: list[dict]) -> Path:
    ref = Path(root) / "reference"
    ref.mkdir(parents=True, exist_ok=True)
    pq.write_table(
        pa.Table.from_pylist(
            _industry_persist_rows(industry_rows), schema=REFERENCE_SCHEMA_INDUSTRY),
        ref / "industry_mapping.parquet")
    pq.write_table(
        pa.Table.from_pylist(
            [{"industry": k, "sector": v} for k, v in sorted(industry_sector.items())],
            schema=REFERENCE_SCHEMA_SECTOR),
        ref / "industry_sector.parquet")
    pq.write_table(
        pa.Table.from_pylist(results_rows, schema=REFERENCE_SCHEMA_RESULTS),
        ref / "results_calendar.parquet")
    return ref


def load_industry_mapping(root: Path) -> dict:
    """{symbol: industry} from the persisted parquet."""
    table = pq.read_table(Path(root) / "reference" / "industry_mapping.parquet")
    return {r["symbol"]: r["industry"] for r in table.to_pylist()}


def load_industry_sources(root: Path) -> dict:
    """{symbol: source_tier}. Missing column (pre-overlay parquet) → Chartsmaze."""
    table = pq.read_table(Path(root) / "reference" / "industry_mapping.parquet")
    out = {}
    for r in table.to_pylist():
        out[r["symbol"]] = r.get("source_tier") or SOURCE_TIER_CHARTSMAZE
    return out


def fill_industry_mapping_from_nexus(
    root: Path,
    nexus_csv: Optional[Path] = None,
) -> dict:
    """Load existing Chartsmaze parquet, add nexus-only symbols, rewrite.

    Does not import manas_os. Fails closed if the Chartsmaze parquet is
    missing — nexus is a fill, not a replacement.
    """
    mapping_path = Path(root) / "reference" / "industry_mapping.parquet"
    if not mapping_path.exists():
        raise ContractError(
            f"Chartsmaze industry mapping missing at {mapping_path}; "
            "nexus fill will not invent the primary table"
        )
    existing = pq.read_table(mapping_path).to_pylist()
    primary = [
        {
            "symbol": r["symbol"],
            "industry": r["industry"],
            "source_tier": r.get("source_tier") or SOURCE_TIER_CHARTSMAZE,
        }
        for r in existing
    ]
    fill, parse_stats = parse_nexus_industry_map(Path(nexus_csv or DEFAULT_NEXUS_CSV))
    merged, stats = overlay_industry_rows(primary, fill)
    pq.write_table(
        pa.Table.from_pylist(merged, schema=REFERENCE_SCHEMA_INDUSTRY),
        mapping_path,
    )
    stats["nexus_skipped"] = parse_stats["skipped"]
    stats["path"] = str(mapping_path)
    return stats


def load_sector_rollup(root: Path) -> dict:
    table = pq.read_table(Path(root) / "reference" / "industry_sector.parquet")
    return {r["industry"]: r["sector"] for r in table.to_pylist()}
