"""NSE index daily closes via nse-archives (NikhilSuthar/indian-market-data).

Finstack MCP is not connected in this session; this adapter is the
public-archive path the owner named as the alternative. Source is NSE
``ind_close_all`` (price index, not TRI — Phase 0 spec forbids mixing).

India VIX, Nifty 50, Midcap 150, Nifty 500, Smallcap 250 are the R0 set.
"""
from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Iterable, Optional

from unidesk.contracts.base import ContractError, ensure_date, require_float
from unidesk.momentum.features.spec_library import sma

SOURCE_TIER = "NSE_ARCHIVES_IND_CLOSE_ALL"
WANTED = {
    "Nifty 50": "NIFTY_50",
    "Nifty 500": "NIFTY_500",
    "Nifty Midcap 150": "NIFTY_MIDCAP_150",
    "Nifty Smallcap 250": "NIFTY_SMALLCAP_250",
    "India VIX": "INDIA_VIX",
}

# ROTATION R-0.2: NSE sectoral indices carried by ind_close_all. Sector RS is
# measured from the exchange's own index — constituent membership is the
# exchange's problem, not ours (HANDOFF_2026-09-04_MARKET_ROTATION §3.1).
SECTORAL = {
    "Nifty Auto": "NIFTY_AUTO",
    "Nifty Bank": "NIFTY_BANK",
    "Nifty Financial Services": "NIFTY_FIN_SERVICE",
    "Nifty FMCG": "NIFTY_FMCG",
    "Nifty IT": "NIFTY_IT",
    "Nifty Media": "NIFTY_MEDIA",
    "Nifty Metal": "NIFTY_METAL",
    "Nifty Pharma": "NIFTY_PHARMA",
    "Nifty Private Bank": "NIFTY_PVT_BANK",
    "Nifty PSU Bank": "NIFTY_PSU_BANK",
    "Nifty Realty": "NIFTY_REALTY",
    "Nifty Energy": "NIFTY_ENERGY",
    "Nifty Infrastructure": "NIFTY_INFRA",
    "Nifty Commodities": "NIFTY_COMMODITIES",
    "Nifty Consumption": "NIFTY_CONSUMPTION",
    "Nifty CPSE": "NIFTY_CPSE",
}

ALL_INDICES = {**WANTED, **SECTORAL}

# R-0.1: legacy MANAS_SECTOR_INDEX_PRICES rows spell names UPPERCASE. Their
# index_id was already canonical; this map normalises the NAME for display and
# makes the dedupe below idempotent across tiers.
LEGACY_NAME_MAP = {
    "NIFTY 50": ("NIFTY_50", "Nifty 50"),
    "NIFTY 500": ("NIFTY_500", "Nifty 500"),
    "NIFTY MIDCAP 150": ("NIFTY_MIDCAP_150", "Nifty Midcap 150"),
    "NIFTY SMALLCAP 250": ("NIFTY_SMALLCAP_250", "Nifty Smallcap 250"),
}

_TIER_PREFERENCE = {"NSE_ARCHIVES_IND_CLOSE_ALL": 0}  # unknown tiers sort after


def canonicalise_index_rows(rows: list[dict]) -> tuple[list[dict], dict]:
    """R-0.1: one canonical row per (session, index_id).

    Legacy MANAS rows and NSE_ARCHIVES rows describe the same indices with
    different name spellings; on overlapping sessions the store carried both.
    Normalises the name spelling, drops tier duplicates (preferring
    NSE_ARCHIVES, the nightly pipeline's own provenance), and asserts the
    invariant: no session carries two rows for one canonical index."""
    stats = {"input": len(rows), "renamed": 0, "tier_dupes_dropped": 0}
    by_key: dict = {}
    for row in rows:
        name = str(row.get("index_name") or "").strip()
        index_id = row.get("index_id") or LEGACY_NAME_MAP.get(name, (None, name))[0]
        if index_id is None:
            stats["renamed"] += 0
        display = None
        for canon_id, canon_name in ALL_INDICES.items():
            if canon_id == index_id:
                display = canon_name
                break
        if display is None:
            for legacy, (cid, cname) in LEGACY_NAME_MAP.items():
                if name.upper() == legacy:
                    index_id, display = cid, cname
                    stats["renamed"] += 1
                    break
        if display is None:
            display = name
        fixed = dict(row)
        fixed["index_id"] = index_id
        fixed["index_name"] = display
        key = (fixed["session"], index_id)
        prev = by_key.get(key)
        if prev is None:
            by_key[key] = fixed
        else:
            stats["tier_dupes_dropped"] += 1
            if _TIER_PREFERENCE.get(fixed.get("source_tier"), 9) < _TIER_PREFERENCE.get(prev.get("source_tier"), 9):
                by_key[key] = fixed
    out = [by_key[k] for k in sorted(by_key)]
    stats["output"] = len(out)

    seen: set = set()
    for row in out:
        key = (row["session"], row["index_id"])
        if key in seen:
            raise ContractError(f"duplicate index row after canonicalisation: {key}")
        seen.add(key)
    return out, stats


def _num(value) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(",", "")
    if text in ("", "-", "NA", "None"):
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _row_date(row: dict) -> Optional[date]:
    for key in ("Index Date", "reporting_date", "DATE", "Date"):
        raw = row.get(key)
        if raw is None or str(raw).strip() == "":
            continue
        if hasattr(raw, "date"):
            return raw.date() if not isinstance(raw, date) else raw
        text = str(raw).strip()
        for fmt in ("%d-%m-%Y", "%d-%b-%Y", "%Y-%m-%d", "%d/%m/%Y"):
            try:
                return datetime.strptime(text, fmt).date()
            except ValueError:
                continue
    return None


def parse_ind_close_all_rows(rows: Iterable[dict], *, source_file: str = "",
                             include_sectoral: bool = True) -> list[dict]:
    """Keep the R0 broad set plus (R-0.2) the sectoral indices. Price close;
    TRI is never stored here."""
    wanted = {**WANTED, **SECTORAL} if include_sectoral else dict(WANTED)
    out = []
    for row in rows:
        name = str(row.get("Index Name") or "").strip()
        index_id = wanted.get(name)
        if index_id is None:
            continue
        session = _row_date(row)
        close = _num(row.get("Closing Index Value") or row.get("Close"))
        if session is None or close is None or close <= 0:
            continue
        out.append({
            "session": session.isoformat(),
            "index_id": index_id,
            "index_name": name,
            "open": _num(row.get("Open Index Value")),
            "high": _num(row.get("High Index Value")),
            "low": _num(row.get("Low Index Value")),
            "close": close,
            "source_tier": SOURCE_TIER,
            "source_file": source_file,
        })
    return out


def series_for(rows: list[dict], index_id: str) -> list[tuple[date, float]]:
    pts = []
    for row in rows:
        if row["index_id"] != index_id:
            continue
        pts.append((date.fromisoformat(row["session"]), require_float(row["close"], "close")))
    pts.sort(key=lambda x: x[0])
    return pts


def above_sma(points: list[tuple[date, float]], as_of: date, span: int = 50) -> Optional[bool]:
    """True if the index close at ``as_of`` is above its own SMA. None if warm-up."""
    as_of = ensure_date(as_of, "as_of")
    prefix = [(d, v) for d, v in points if d <= as_of]
    if len(prefix) < span:
        return None
    closes = [v for _, v in prefix]
    ma = sma(closes, span)
    last = ma[-1]
    if last is None:
        return None
    return closes[-1] > last


def fetch_ind_close_all(session: date):
    """Network: NSE archives through nse-archives. Isolated for tests."""
    from nsedata import nse
    frame = nse.get("capital_market", "indices", "ind_close_all", session.isoformat())
    return frame.to_dict(orient="records")


def persist_index_rows(rows: list[dict], path: Path) -> Path:
    import pyarrow as pa
    import pyarrow.parquet as pq
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pylist(rows)
    pq.write_table(table, path)
    return path


def load_index_rows(path: Path) -> list[dict]:
    import pyarrow.parquet as pq
    return pq.read_table(path).to_pylist()


def harvest_sessions(sessions: list[date], *, dest: Path, fetcher=fetch_ind_close_all) -> dict:
    """Fetch ind_close_all for each session; skip failures; write parquet."""
    kept, failed = [], []
    for session in sessions:
        try:
            raw = fetcher(session)
            rows = parse_ind_close_all_rows(
                raw, source_file=f"ind_close_all_{session.isoformat()}",
            )
            if not rows:
                failed.append(session.isoformat())
                continue
            kept.extend(rows)
        except Exception:
            failed.append(session.isoformat())
    # last write wins on (session, index_id)
    uniq = {}
    for row in kept:
        uniq[(row["session"], row["index_id"])] = row
    out = [uniq[k] for k in sorted(uniq)]
    if out:
        persist_index_rows(out, dest)
    return {"sessions_ok": len({r["session"] for r in out}),
            "rows": len(out), "failed": failed, "path": str(dest)}
