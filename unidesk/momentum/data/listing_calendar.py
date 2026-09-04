"""NSE official IPO listing-calendar ingest and listing-age feature.

Fills the gap ``events.py``/``gold.py`` already admit exists: there was no
listing calendar on disk anywhere, so ``ipo_base``'s ``listing_age_sessions``
input was a *store-length proxy* (the length of whatever bhavcopy history
happened to be loaded for a symbol — see
``unidesk.momentum.detectors.inputs.build_setup_inputs``), not a real
listing date. ``trust.py`` blocks ``ipo_base`` for exactly this reason
(``listing_age_is_not_verified``). This module does not change that trust
status — it is owner-gated (see ``trust.py`` module docstring) — it only
gives the desk a real, hashed, point-in-time listing calendar to eventually
verify against.

Source: NSE's own public equities master list
(``https://archives.nseindia.com/content/equities/EQUITY_L.csv``), which
NSE publishes with a ``DATE OF LISTING`` column for every listed symbol.
This is DATA_AUTHORITY primary/official — unlike the Chartsmaze vendor dump
``events.py`` already parses for the same *field* (``SOURCE_TIER =
SECONDARY_REPAIR``). The two are kept distinct: this module's rows carry
``source_tier = NSE_EQUITY_MASTER``, never silently merged into or mistaken
for the Chartsmaze rows.

Reuse, not a second parser: NSE's raw column layout (``SYMBOL, NAME OF
COMPANY, SERIES, DATE OF LISTING, ...``; dates as ``DD-MON-YYYY``, e.g.
``06-OCT-2008``) does not match what
``unidesk.momentum.data.events.parse_ipo_listings`` expects (``Stock Name,
Listing Date``; ``DD/MM/YYYY`` | ``YYYY-MM-DD`` | ``DD-MM-YYYY``). Rather
than write a second symbol-normalizing / date-parsing IPO parser, this
module only reshapes the raw NSE rows into that exact CSV shape
(``normalize_nse_equity_master``) — the ingest script then writes that
reshaped CSV to disk and replays it through ``parse_ipo_listings``
unchanged, and relabels the resulting ``source_tier``/``source_file`` from
Chartsmaze's default to NSE's (the parser has no way to know its caller
isn't Chartsmaze).

Point-in-time safety: NSE serves ``EQUITY_L.csv`` as a live "current state"
file — there is no historical-versions endpoint. Each ingest run therefore
freezes a dated, immutable snapshot under
``data/market/reference/listing_calendar/<snapshot_date>/`` (raw bytes +
its own content hash + the normalized/parsed rows + a manifest with
``first_seen_at``), following ``corp_actions.confirmed_actions_content_hash``'s
convention: hash the file's actual bytes, never its path or mtime. A
listing date is static per symbol once observed, but the *file* — and
therefore which symbols it covers — has a version; older dated snapshots
stay on disk for audit/replay even after a newer one is ingested. The
"latest" table (``data/market/reference/listing_calendar.parquet``) that
``load_listing_calendar`` reads is always the most recent successful
ingest's output.
"""
from __future__ import annotations

import csv
import hashlib
from datetime import date
from pathlib import Path
from typing import Optional

import pyarrow as pa
import pyarrow.parquet as pq

from unidesk.contracts.base import ensure_date
from unidesk.momentum.data.calendar import TradingCalendar
from unidesk.momentum.universe.symbol_master import normalize_symbol

REPO = Path(__file__).resolve().parents[3]

SOURCE_TIER = "NSE_EQUITY_MASTER"
NSE_EQUITY_MASTER_URL = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
# archives.nseindia.com (unlike www.nseindia.com) is a static file host and
# does not require a cookie/session dance -- a plain browser-shaped
# User-Agent is enough (matches unidesk/fetch_nse_bhavcopy.py's convention).
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) research-eod"}

DEFAULT_SNAPSHOT_ROOT = REPO / "data" / "market" / "reference" / "listing_calendar"
DEFAULT_LATEST_PARQUET = REPO / "data" / "market" / "reference" / "listing_calendar.parquet"

LISTING_CALENDAR_SCHEMA = pa.schema([
    ("symbol", pa.string()),
    ("listing_date", pa.string()),      # ISO date
    ("source_tier", pa.string()),
    ("source_file", pa.string()),
    ("content_hash", pa.string()),      # of the raw NSE snapshot this row came from
    ("snapshot_date", pa.string()),     # ISO date the snapshot was captured
    ("first_seen_at", pa.string()),     # ISO UTC timestamp, stable across re-ingests of same content
])

_NSE_MONTHS = {
    "JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAY": 5, "JUN": 6,
    "JUL": 7, "AUG": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12,
}


def _parse_nse_date(raw: str) -> Optional[date]:
    """``DD-MON-YYYY`` (e.g. ``06-OCT-2008``), NSE's own format. Anything
    else -- blank, malformed, unknown month -- is None, never guessed."""
    raw = (raw or "").strip().upper()
    if len(raw) != 11 or raw[2] != "-" or raw[6] != "-":
        return None
    try:
        day = int(raw[0:2])
        month = _NSE_MONTHS[raw[3:6]]
        year = int(raw[7:11])
        return date(year, month, day)
    except (KeyError, ValueError):
        return None


def fetch_nse_equity_master(url: str = NSE_EQUITY_MASTER_URL, *, timeout: int = 30) -> bytes:
    """GET the raw NSE equity master CSV. Raises on any failure -- callers
    (the ingest script) must stop and report plainly, never fall back to a
    fabricated or substitute listing calendar."""
    import requests

    resp = requests.get(url, headers=HEADERS, timeout=timeout)
    resp.raise_for_status()
    if not resp.content:
        raise RuntimeError(f"NSE equity master fetch returned an empty body from {url}")
    return resp.content


def normalize_nse_equity_master(raw_bytes: bytes) -> tuple[list[dict], dict]:
    """Raw ``EQUITY_L.csv`` bytes -> ``{"Stock Name", "Listing Date"}`` rows
    in the exact shape ``events.parse_ipo_listings`` expects (see module
    docstring). Column names in the source carry stray leading spaces
    (`` SERIES``, `` DATE OF LISTING``, ...) -- stripped before lookup.
    Malformed/blank rows are skipped and counted (R12 convention), never
    coerced."""
    text = raw_bytes.decode("utf-8-sig", errors="strict")
    reader = csv.DictReader(text.splitlines())
    out: list[dict] = []
    skipped = 0
    for row in reader:
        clean = {(k or "").strip(): (v or "").strip() for k, v in row.items()}
        symbol = clean.get("SYMBOL", "")
        listing = _parse_nse_date(clean.get("DATE OF LISTING", ""))
        if not symbol or listing is None:
            skipped += 1
            continue
        isin = clean.get("ISIN NUMBER", "")
        out.append({"Stock Name": symbol, "Listing Date": listing.strftime("%d-%m-%Y"),
                    "ISIN": isin})
    return out, {"skipped": skipped, "kept": len(out)}


def write_normalized_csv(rows: list[dict], path: Path) -> Path:
    """Write the ``Stock Name,Listing Date`` intermediate CSV that gets
    replayed through ``events.parse_ipo_listings`` -- kept on disk (inside
    the dated snapshot dir) rather than a throwaway temp file, so the
    reshape step is itself inspectable/reproducible."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        # ISIN rides along when the source master carried it — the
        # IPOListingFact boundary (listing_fact_for) needs it, and
        # parse_ipo_listings tolerates the extra column.
        fieldnames = ["Stock Name", "Listing Date", "ISIN"]
        writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return path


def content_hash(raw_bytes: bytes) -> str:
    """SHA-256 (first 16 hex chars) of the raw snapshot's actual bytes --
    mirrors ``corp_actions.confirmed_actions_content_hash``: hash content,
    never path/mtime, so two snapshots with identical bytes always collapse
    to the same basis and differing content never collides."""
    return hashlib.sha256(raw_bytes).hexdigest()[:16]


def persist_listing_calendar(rows: list[dict], path: Optional[Path] = None) -> Path:
    """Write the "latest" listing-calendar table. A full reference-master
    replace, not an append log -- each ingest's output wholesale-replaces
    the previous one (dated snapshots under DEFAULT_SNAPSHOT_ROOT retain
    history)."""
    target = Path(path or DEFAULT_LATEST_PARQUET)
    target.parent.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pylist(rows, schema=LISTING_CALENDAR_SCHEMA)
    pq.write_table(table, target)
    return target


def load_listing_calendar(path: Optional[Path] = None) -> dict:
    """``{symbol: listing_date}`` from the persisted "latest" snapshot.

    A missing file returns an empty dict (never raises) -- a scan run
    before any ingest, or for a symbol the snapshot doesn't cover, must
    degrade to "unknown listing date" (None downstream), not crash."""
    target = Path(path or DEFAULT_LATEST_PARQUET)
    if not target.exists():
        return {}
    table = pq.read_table(target)
    out: dict = {}
    for row in table.to_pylist():
        try:
            out[row["symbol"]] = date.fromisoformat(row["listing_date"])
        except (TypeError, ValueError, KeyError):
            continue
    return out


def listing_fact_for(
    symbol: str,
    *,
    listing_date: date,
    isin: str,
    content_hash: str,
    first_seen_at: str,
    source_url: str = NSE_EQUITY_MASTER_URL,
) -> Optional["IPOListingFact"]:
    """E-1 boundary adapter (event-track §3.1): lift a persisted listing row
    into the ``research.market_events.IPOListingFact`` contract. Returns
    ``None`` when the row predates ISIN capture or any required field is
    missing — fail-closed, never an invented identifier."""
    from datetime import datetime

    from unidesk.research.market_events import IPOListingFact

    if not isin or not content_hash:
        return None
    try:
        seen = datetime.fromisoformat(first_seen_at)
    except ValueError:
        return None
    try:
        return IPOListingFact(
            symbol=symbol, isin=isin, listing_date=listing_date,
            source_url=source_url, available_at=seen, retrieved_at=seen,
            source_hash=content_hash,
        )
    except ContractError:
        return None


def sessions_since_listing(
    trading_calendar: TradingCalendar,
    listing_date: Optional[date],
    as_of: date,
) -> Optional[int]:
    """Trading-session age as of ``as_of`` — sessions elapsed, computed on
    the trading calendar (``TradingCalendar.session_distance``), never
    calendar days.

    Returns ``None`` (never 0, never a guess) when:
    * ``listing_date`` is unknown (symbol absent from the calendar),
    * ``as_of`` precedes ``listing_date`` (not yet listed at that
      point in time), or
    * either date is not itself an observed session in
      ``trading_calendar`` (warm-up / calendar gap).

    Counting convention: the listing session itself counts as session 1
    (``session_distance`` + 1), matching
    ``inputs.build_setup_inputs``'s store-length proxy it replaces
    (``listing_age_sessions = n``, the *count* of bars including the
    first) -- so ``ipo_base``'s calibrated ``min_age``/``max_age``
    thresholds keep the same meaning if this feature is ever wired in to
    replace the proxy.
    """
    if listing_date is None:
        return None
    as_of = ensure_date(as_of, "as_of")
    listing_date = ensure_date(listing_date, "listing_date")
    if as_of < listing_date:
        return None
    distance = trading_calendar.session_distance(listing_date, as_of)
    if distance is None:
        return None
    return distance + 1


def listing_age_sessions_for(
    symbol: str,
    as_of: date,
    *,
    listing_dates: dict,
    trading_calendar: TradingCalendar,
) -> Optional[int]:
    """Convenience wrapper: sessions elapsed since ``symbol`` listed, as of
    ``as_of``, given an already-loaded ``{symbol: listing_date}`` map (e.g.
    from ``load_listing_calendar``) and a ``TradingCalendar``. ``None`` on
    any of the reasons documented on ``sessions_since_listing``, plus an
    unrecognized ``symbol``."""
    normalized = normalize_symbol(symbol)
    listing_date = listing_dates.get(normalized)
    return sessions_since_listing(trading_calendar, listing_date, as_of)
