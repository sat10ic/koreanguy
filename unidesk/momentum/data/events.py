"""Chartsmaze event-table ingest (Phase 0 spec §12/§15; D14 source_tier).

These dumps are a *secondary* vendor (DATA_AUTHORITY: chartsmaze_raw,
provisional). They do not overwrite official bhavcopy rows. They fill
tables the exchange files in this repo do not yet carry:

* IPO listing dates
* circuit-band revisions (effective-dated)
* corporate-announcement review queue (no auto-adjust — announcements
  do not carry split ratios)
* vendor market-breadth series (Above 50/200 MA %) for R0 calibration,
  never as a silent substitute for our own breadth computation

Malformed rows are skipped and counted (R12).
"""
from __future__ import annotations

import csv
import re
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from unidesk.contracts.base import ContractError, ensure_date, require_str
from unidesk.momentum.universe.symbol_master import normalize_symbol

SOURCE_TIER = "SECONDARY_REPAIR"
CA_TYPES = (
    "SPLIT", "BONUS", "CONSOLIDATION", "RIGHTS", "DIVIDEND",
    "SPECIAL_DIVIDEND", "BUYBACK", "MERGER", "DEMERGER", "SCHEME",
    "SYMBOL_CHANGE", "FACE_VALUE_CHANGE", "RECORD_DATE", "OTHER",
)

_DATE_FMTS = ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y")


def _read_rows(path: Path) -> list[dict]:
    with open(path, "r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def _parse_date(raw: str) -> Optional[date]:
    raw = (raw or "").strip()
    if not raw:
        return None
    for fmt in _DATE_FMTS:
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None


def _sym(raw: str) -> Optional[str]:
    try:
        return normalize_symbol((raw or "").strip().upper())
    except ContractError:
        return None


def parse_ipo_listings(path: Path) -> tuple[list[dict], dict]:
    """``Stock Name, Listing Date, ...`` → {symbol, listing_date}."""
    out, skipped = [], 0
    for row in _read_rows(path):
        symbol = _sym(row.get("Stock Name") or row.get("ticker") or "")
        listing = _parse_date(row.get("Listing Date") or "")
        if symbol is None or listing is None:
            skipped += 1
            continue
        out.append({
            "symbol": symbol,
            "listing_date": listing.isoformat(),
            "source_tier": SOURCE_TIER,
            "source_file": path.name,
        })
    return out, {"skipped": skipped, "kept": len(out)}


def parse_circuit_revisions(path: Path) -> tuple[list[dict], dict]:
    """``Effective Date, Stock Name, From, To`` → effective-dated band rows."""
    out, skipped = [], 0
    for row in _read_rows(path):
        symbol = _sym(row.get("Stock Name") or "")
        effective = _parse_date(row.get("Effective Date") or "")
        try:
            from_pct = float((row.get("From") or "").strip())
            to_pct = float((row.get("To") or "").strip())
        except ValueError:
            skipped += 1
            continue
        if symbol is None or effective is None:
            skipped += 1
            continue
        out.append({
            "symbol": symbol,
            "effective_date": effective.isoformat(),
            "from_pct": from_pct,
            "to_pct": to_pct,
            "source_tier": SOURCE_TIER,
            "source_file": path.name,
        })
    return out, {"skipped": skipped, "kept": len(out)}


def classify_announcement(subject: str, details: str = "") -> str:
    """Map vendor subject/details onto the Phase 0 ca_type taxonomy.

    Conservative: keyword hits in Subject+Details only (never the company
    name). No ratio is inferred. Auto-adjust remains False upstream.
    """
    subject = (subject or "").strip()
    blob = f"{subject} {details or ''}".lower()
    if subject == "Dividend" or re.search(r"\bdividend of rs\b", blob):
        return "DIVIDEND"
    if "buyback" in blob:
        return "BUYBACK"
    if re.search(r"\bstock split\b", blob) or re.search(r"\bsplit of (equity )?share", blob):
        return "SPLIT"
    if re.search(r"\bbonus (issue|share)", blob):
        return "BONUS"
    if "rights issue" in blob:
        return "RIGHTS"
    if re.search(r"consolidat\w* of (equity )?share", blob):
        return "CONSOLIDATION"
    if subject == "Record Date":
        return "RECORD_DATE"
    return "OTHER"


def parse_corporate_announcements(path: Path) -> tuple[list[dict], dict]:
    """``Stock Name, Date, Subject, Details`` → review-queue CA rows.

    ``auto_adjustable`` is always False: these rows do not carry a ratio.
    """
    out, skipped = [], 0
    by_type: dict[str, int] = {}
    for row in _read_rows(path):
        symbol = _sym(row.get("Stock Name") or "")
        announced = _parse_date(row.get("Date") or "")
        subject = (row.get("Subject") or "").strip()
        if symbol is None or announced is None or not subject:
            skipped += 1
            continue
        ca_type = classify_announcement(subject, row.get("Details") or "")
        by_type[ca_type] = by_type.get(ca_type, 0) + 1
        out.append({
            "symbol": symbol,
            "announcement_date": announced.isoformat(),
            "subject": subject,
            "ca_type": ca_type,
            "auto_adjustable": False,
            "source_tier": SOURCE_TIER,
            "source_file": path.name,
        })
    return out, {"skipped": skipped, "kept": len(out), "by_type": by_type}


def parse_vendor_breadth(path: Path) -> tuple[list[dict], dict]:
    """Wide Chartsmaze breadth CSV → one row per session for MA% series.

    Looks up the rows named ``Above 50MA %`` and ``Above 200MA %``. Other
    rows are ignored. Values are percents (0–100), stored as fractions 0–1.
    """
    with open(path, "r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.reader(fh)
        rows = list(reader)
    if not rows:
        return [], {"skipped": 0, "kept": 0}
    header = rows[0]
    dates = []
    for col in header[1:]:
        d = _parse_date(col)
        dates.append(d)
    wanted = {}
    for row in rows[1:]:
        if not row:
            continue
        name = (row[0] or "").strip()
        if name in ("Above 50MA %", "Above 200MA %"):
            wanted[name] = row[1:]
    if "Above 50MA %" not in wanted:
        return [], {"skipped": len(rows) - 1, "kept": 0}
    out, skipped = [], 0
    a50 = wanted["Above 50MA %"]
    a200 = wanted.get("Above 200MA %", [])
    for i, session in enumerate(dates):
        if session is None:
            skipped += 1
            continue
        try:
            p50 = float(a50[i]) / 100.0
        except (ValueError, IndexError):
            skipped += 1
            continue
        p200 = None
        if i < len(a200):
            try:
                p200 = float(a200[i]) / 100.0
            except ValueError:
                p200 = None
        if not (0.0 <= p50 <= 1.0):
            skipped += 1
            continue
        out.append({
            "session": session.isoformat(),
            "pct_above_50": round(p50, 4),
            "pct_above_200": None if p200 is None else round(p200, 4),
            "source_tier": SOURCE_TIER,
            "source_file": path.name,
        })
    return out, {"skipped": skipped, "kept": len(out)}


def circuit_band_as_of(revisions: list[dict], symbol: str, as_of: date) -> Optional[float]:
    """Latest ``to_pct`` for ``symbol`` with effective_date <= as_of.

    Missing history is None, never today's band (D14.5).
    """
    as_of = ensure_date(as_of, "as_of")
    symbol = require_str(symbol, "symbol")
    latest = None
    latest_date = None
    for row in revisions:
        if row["symbol"] != symbol:
            continue
        eff = date.fromisoformat(row["effective_date"])
        if eff <= as_of and (latest_date is None or eff >= latest_date):
            latest_date = eff
            latest = float(row["to_pct"])
    return latest
