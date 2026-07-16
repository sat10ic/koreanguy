"""Forward earnings calendar — the ONE missing EP data piece (see
``design/EARNINGS_SEASON_HANDHOLD_WAVE_2026-07-17.md``): we know how a stock
reacted to earnings after the fact (ChartsMaze EP feeds, disclosures.py); we
never knew WHO REPORTS TOMORROW until this stage exists.

Primary source: BSE's own forthcoming-results calendar
``https://api.bseindia.com/BseIndiaAPI/api/Corpforthresults/w`` — no cookie
wall, plain JSON, confirmed via the unofficial BennyThadikaran/BseIndiaApi
client (``resultCalendar()``). This endpoint IS the "board meetings, purpose
= Results" filter the plan called for: BSE serves forthcoming-results board
meetings as their own dedicated calendar rather than a generic board-meeting
feed with a purpose column, so there is no separate purpose field to filter
on — every row returned is a results meeting. Sample row shape::

    {"scrip_Code": "521070", "short_name": "ALOKTEXT",
     "Long_Name": "ALOK INDUSTRIES LTD.", "meeting_date": "23 Oct 2023",
     "URL": "https://www.bseindia.com/..."}

BSE rows carry a scrip code + company name, not an NSE symbol, so they are
mapped via the existing NIFTYMIDSML400 constituents master
(``manas_os/data/niftymidsml400_constituents.csv`` — the same file
``sources/universe_breadth.py::load_constituents`` reads symbols from).
Company names that don't resolve are SKIPPED with a count, never guessed.

Secondary (stub this pass): NSE's own event calendar. The plan's placeholder
guess (``nseindia.com/api/event-calendar``) turned out not to be the live
endpoint; the real one — confirmed from BennyThadikaran/NseIndiaApi's
``boardMeetings()`` — is ``https://www.nseindia.com/api/corporate-board-
meetings``. NSE sits behind an Akamai/cookie wall (bare `requests` gets
401/403); ``fetch_nse_calendar`` attempts a browser-header GET and reports
the failure honestly rather than faking rows. The real fix is a warmed
browser session — the Playwright session the (untracked, sibling)
``chartsmaze_extractor/`` tool already maintains for other NSE/BSE scrapes is
the natural place to lift a cookie jar from; wiring that up is future work,
not this pass. NSE rows carry ``bm_symbol`` directly (already the NSE
trading symbol), so they need no name resolution.

Table: ``earnings_calendar(symbol, meeting_date, purpose, source, fetched_at)``
point-in-time, idempotent upsert on (symbol, meeting_date, source) — the same
value re-ingested on a later day just refreshes ``fetched_at``.
"""
from __future__ import annotations

import csv
import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

import requests

STAGE = "ingest_earnings_calendar"
SOURCE_BSE = "bse_board_meetings"
SOURCE_NSE = "nse_event_calendar"

_ROOT = Path(__file__).resolve().parents[1]
_CONSTITUENTS = _ROOT / "data" / "niftymidsml400_constituents.csv"

_BSE_API_URL = "https://api.bseindia.com/BseIndiaAPI/api/Corpforthresults/w"
_NSE_API_URL = "https://www.nseindia.com/api/corporate-board-meetings"
_NSE_HOME_URL = "https://www.nseindia.com/get-quotes/equity?symbol=SBIN"
_TIMEOUT = 12

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
_BSE_HEADERS = {
    "User-Agent": _UA,
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Origin": "https://www.bseindia.com",
    "Referer": "https://www.bseindia.com/",
}
_NSE_HEADERS = {
    "User-Agent": _UA,
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/companies-listing/corporate-filings-event-calendar",
}

_LTD_RE = re.compile(r"\b(LIMITED|LTD)S?\b\.?")
_PUNCT_RE = re.compile(r"[.,()'’]")
_WS_RE = re.compile(r"\s+")

_RESULTS_KEYWORDS = ("financial result", "unaudited", "audited", "quarterly result")


# ─────────────────────────────────────────────────────────────────────────────
# Schema
# ─────────────────────────────────────────────────────────────────────────────

def ensure_schema(conn) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS earnings_calendar ("
        "symbol TEXT NOT NULL, meeting_date TEXT NOT NULL, purpose TEXT, "
        "source TEXT NOT NULL, fetched_at TEXT, "
        "PRIMARY KEY (symbol, meeting_date, source))"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_earnings_calendar_date "
        "ON earnings_calendar(meeting_date)"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Symbol master (reuse — never invent a new mapping table)
# ─────────────────────────────────────────────────────────────────────────────

def _normalize_company_name(name: str | None) -> str:
    s = (name or "").strip().upper()
    s = _PUNCT_RE.sub("", s)
    s = _LTD_RE.sub("", s)
    s = _WS_RE.sub(" ", s).strip()
    return s


def load_symbol_master(path: Path | str = _CONSTITUENTS) -> dict[str, str]:
    """Normalized-company-name -> NSE symbol, from the existing NIFTYMIDSML400
    constituents CSV (``universe_breadth.load_constituents`` reads the same
    file for its symbol list). Empty dict if the file is absent."""
    p = Path(path)
    if not p.exists():
        return {}
    out: dict[str, str] = {}
    with p.open("r", encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            name = (row.get("Company Name") or "").strip()
            sym = (row.get("Symbol") or "").strip().upper()
            if name and sym:
                out[_normalize_company_name(name)] = sym
    return out


def resolve_symbol(
    company_name: str | None, short_name: str | None, master: dict[str, str]
) -> str | None:
    """BSE row -> NSE symbol via the constituents master. Tries the BSE
    ``short_name`` directly first (frequently identical to the NSE symbol),
    then falls back to a normalized company-name lookup. Returns None
    (never a guess) when neither matches."""
    symbols = set(master.values())
    candidate = (short_name or "").strip().upper()
    if candidate and candidate in symbols:
        return candidate
    return master.get(_normalize_company_name(company_name))


# ─────────────────────────────────────────────────────────────────────────────
# BSE primary — pure parser (fixture-testable with no network)
# ─────────────────────────────────────────────────────────────────────────────

def _parse_bse_date(raw: str) -> str | None:
    raw = (raw or "").strip()
    if not raw:
        return None
    for fmt in ("%d %b %Y", "%d-%b-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def parse_bse_calendar(
    rows: list[dict[str, Any]], master: dict[str, str] | None = None
) -> tuple[list[dict[str, Any]], int]:
    """Pure: BSE ``Corpforthresults/w`` JSON rows -> normalized calendar rows.

    Returns ``(rows, unresolved_count)``. A row missing a usable meeting_date
    is dropped silently (malformed upstream data); a row whose company name
    doesn't resolve to an NSE symbol is counted in ``unresolved_count`` and
    skipped — never guessed.
    """
    master = master if master is not None else load_symbol_master()
    out: list[dict[str, Any]] = []
    unresolved = 0
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        long_name = row.get("Long_Name") or row.get("long_name") or ""
        short_name = row.get("short_name") or row.get("Short_Name") or ""
        scrip_code = str(row.get("scrip_Code") or row.get("scrip_code") or "").strip()
        meeting_date = _parse_bse_date(str(row.get("meeting_date") or ""))
        if not meeting_date:
            continue
        symbol = resolve_symbol(long_name, short_name, master)
        if not symbol:
            unresolved += 1
            continue
        out.append({
            "symbol": symbol,
            "meeting_date": meeting_date,
            "purpose": "Results",
            "source": SOURCE_BSE,
            "scrip_code": scrip_code,
            "company_name": str(long_name).strip(),
        })
    return out, unresolved


def fetch_bse_calendar(
    from_date: str | None = None, to_date: str | None = None, timeout: int = _TIMEOUT
) -> list[dict[str, Any]]:
    """Network fetch of BSE's forthcoming-results calendar (raw JSON rows).

    ``from_date``/``to_date`` are ``YYYYMMDD`` strings; omitted means BSE's
    own default forthcoming window. Raises on any failure (timeout, non-2xx,
    unexpected shape) — never fabricates rows; the caller (``run``) decides
    whether that's a skip.
    """
    params: dict[str, str] = {}
    if from_date and to_date:
        params["fromdate"] = from_date
        params["todate"] = to_date
    resp = requests.get(_BSE_API_URL, headers=_BSE_HEADERS, params=params, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()
    if not isinstance(data, list):
        raise ValueError(f"unexpected BSE response shape: {type(data).__name__}")
    return data


# ─────────────────────────────────────────────────────────────────────────────
# NSE secondary — pure parser + honest-failure fetch (stub this pass)
# ─────────────────────────────────────────────────────────────────────────────

def _parse_nse_date(raw: str) -> str | None:
    raw = (raw or "").strip()
    if not raw:
        return None
    try:
        return datetime.strptime(raw, "%d-%b-%Y").date().isoformat()
    except ValueError:
        return None


def _nse_purpose(bm_purpose: str, bm_desc: str) -> str:
    text = f"{bm_purpose or ''} {bm_desc or ''}".lower()
    return "Results" if any(k in text for k in _RESULTS_KEYWORDS) else "Other"


def parse_nse_calendar(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Pure: NSE ``corporate-board-meetings`` JSON rows -> normalized rows.

    NSE rows carry ``bm_symbol`` directly (already the NSE trading symbol —
    no name resolution needed). Rows with no usable symbol/date are dropped.
    """
    out: list[dict[str, Any]] = []
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        symbol = str(row.get("bm_symbol") or "").strip().upper()
        meeting_date = _parse_nse_date(str(row.get("bm_date") or ""))
        if not symbol or not meeting_date:
            continue
        out.append({
            "symbol": symbol,
            "meeting_date": meeting_date,
            "purpose": _nse_purpose(row.get("bm_purpose", ""), row.get("bm_desc", "")),
            "source": SOURCE_NSE,
            "company_name": str(row.get("sm_name") or "").strip(),
        })
    return out


def fetch_nse_calendar(timeout: int = _TIMEOUT) -> list[dict[str, Any]]:
    """Best-effort NSE fetch. NSE sits behind an Akamai/cookie wall; a bare
    GET (even with browser headers) typically 401/403s from an unattended
    host. Raises a clear, honest error in that case — it does NOT fall back
    to fabricated data. The real fix is a warmed cookie jar (Playwright
    session, e.g. the one ``chartsmaze_extractor/`` already maintains for
    other NSE scrapes); that upgrade is out of scope for this pass.
    """
    session = requests.Session()
    session.headers.update(_NSE_HEADERS)
    try:
        session.get(_NSE_HOME_URL, timeout=timeout)
    except requests.RequestException as exc:
        raise ConnectionError(f"NSE cookie warm-up failed: {type(exc).__name__}: {exc}") from exc

    resp = session.get(_NSE_API_URL, params={"index": "equities"}, timeout=timeout)
    if resp.status_code in (401, 403):
        raise PermissionError(
            f"NSE event-calendar blocked ({resp.status_code}) — cookie wall; "
            "needs a warmed browser session (Playwright), not a bare request"
        )
    resp.raise_for_status()
    data = resp.json()
    if not isinstance(data, list):
        raise ValueError(f"unexpected NSE response shape: {type(data).__name__}")
    return data


# ─────────────────────────────────────────────────────────────────────────────
# Upsert + stage entrypoint
# ─────────────────────────────────────────────────────────────────────────────

def upsert(conn, rows: list[dict[str, Any]], fetched_at: str) -> int:
    if not rows:
        return 0
    payload = [
        {
            "symbol": r["symbol"],
            "meeting_date": r["meeting_date"],
            "purpose": r.get("purpose"),
            "source": r["source"],
            "fetched_at": fetched_at,
        }
        for r in rows
    ]
    conn.executemany(
        "INSERT INTO earnings_calendar (symbol, meeting_date, purpose, source, fetched_at) "
        "VALUES (:symbol, :meeting_date, :purpose, :source, :fetched_at) "
        "ON CONFLICT(symbol, meeting_date, source) DO UPDATE SET "
        "purpose=excluded.purpose, fetched_at=excluded.fetched_at",
        payload,
    )
    return len(payload)


def _log_run(conn, run_date: str, status: str, rows: int, duration: float, detail: str) -> None:
    conn.execute(
        "INSERT INTO pipeline_runs (run_date, stage, source, status, "
        "rows_affected, duration_s, detail) VALUES (?,?,?,?,?,?,?)",
        (run_date, STAGE, SOURCE_BSE, status, rows, duration, detail),
    )


def run(
    conn,
    run_date: str,
    *,
    bse_fetcher: Callable[..., list[dict[str, Any]]] | None = None,
    nse_fetcher: Callable[..., list[dict[str, Any]]] | None = None,
) -> int:
    """Fetch + ingest the forward earnings calendar. Never raises: BSE is the
    primary source (failure -> honest `skip`, not `fail` — a dead network or
    an upstream layout change must never break run-eod); NSE is a best-effort
    secondary layered on top in the same stage, also failure-safe.
    """
    started = time.monotonic()
    ensure_schema(conn)
    fetched_at = datetime.now().isoformat(timespec="seconds")
    bse_fetch = bse_fetcher or fetch_bse_calendar
    nse_fetch = nse_fetcher or fetch_nse_calendar

    detail: dict[str, Any] = {}
    total_rows = 0
    bse_ok = False
    try:
        raw = bse_fetch()
        parsed, unresolved = parse_bse_calendar(raw)
        written = upsert(conn, parsed, fetched_at)
        total_rows += written
        bse_ok = True
        detail["bse"] = {"fetched": len(raw), "written": written, "unresolved": unresolved}
    except Exception as exc:  # noqa: BLE001
        detail["bse"] = {"error": f"{type(exc).__name__}: {exc}"}

    try:
        raw_nse = nse_fetch()
        parsed_nse = parse_nse_calendar(raw_nse)
        written_nse = upsert(conn, parsed_nse, fetched_at)
        total_rows += written_nse
        detail["nse"] = {"fetched": len(raw_nse), "written": written_nse}
    except Exception as exc:  # noqa: BLE001
        detail["nse"] = {"error": f"{type(exc).__name__}: {exc}"}

    status = "ok" if bse_ok or total_rows else "skip"
    _log_run(
        conn, run_date, status, total_rows, time.monotonic() - started,
        json.dumps(detail, sort_keys=True, separators=(",", ":")),
    )
    conn.commit()
    return total_rows
