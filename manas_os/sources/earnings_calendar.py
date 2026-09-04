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

BSE rows carry a scrip code + company name, not an NSE symbol, so they must
be mapped. ``resolve_symbol`` tries, in order (see its docstring for the
full rationale):

1. ``SYMBOL_OVERRIDES`` — a small hand-authored, editable dict for confirmed
   real short_name/company-name -> NSE-symbol mismatches. Empty by default;
   see the dict's own docstring for the 2026-07-18 audit that found none to
   seed it with yet.
2. **symbol_direct** — the BSE ``short_name`` compared directly against
   ``known_symbols`` (``load_known_symbols`` — every symbol our own
   ``daily_prices`` panel and ``universe`` table have ever carried, unioned
   with the constituents master's own symbols). This is the widened path:
   BSE's short_name is frequently *already* the exact NSE trading symbol,
   but the original implementation only checked it against the 400-name
   NIFTYMIDSML400 (mid/small-cap only) master, so every Nifty50/large-cap
   name (AXISBANK, HDFCBANK, ITC, RELIANCE-scale names, ...) was silently
   unresolved — that was the single largest source of drops, well ahead of
   any company-name-normalization gap.
3. **name_normalized** — normalized company name against the NIFTYMIDSML400
   constituents master (``manas_os/data/niftymidsml400_constituents.csv`` —
   the same file ``sources/universe_breadth.py::load_constituents`` reads
   symbols from). The original (only) path.

Rows that still don't resolve are **never dropped** — they are written to
``earnings_calendar`` under a synthetic ``_UNMAPPED_<scrip_code>`` symbol
with ``match_method='unmapped'`` and the raw ``company_name``/``scrip_code``
preserved, so the API surfaces them as "reports on this date, symbol not
yet mapped" instead of silently vanishing. Every row (mapped or not) records
*how* it mapped in the ``match_method`` column.

ISIN join (the textbook widest key) was evaluated and is NOT implemented:
the BSE ``Corpforthresults`` sample rows we've observed carry no ISIN field,
and no local table (checked ``schema.sql``, ``symbol_quality``, ``universe``)
carries an ISIN column either. `Unverified: BSE may expose ISIN on a
different endpoint we haven't checked — flag if you find one.` This tier is
skipped, not silently faked.

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

Table: ``earnings_calendar(symbol, meeting_date, purpose, source, fetched_at,
company_name, scrip_code, match_method)`` point-in-time, idempotent upsert on
(symbol, meeting_date, source) — the same value re-ingested on a later day
just refreshes ``fetched_at``. ``company_name``/``scrip_code``/
``match_method`` were added by the widen-mapping wave (2026-07-18); older
rows ingested before that wave carry NULL in those three columns until
re-ingested.
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

# match_method tags recorded on every row (mapped or not) -- see resolve_symbol.
MATCH_OVERRIDE = "override"
MATCH_SYMBOL_DIRECT = "symbol_direct"
MATCH_NAME_NORMALIZED = "name_normalized"
MATCH_NSE_DIRECT = "nse_direct"
MATCH_UNMAPPED = "unmapped"

# Synthetic-symbol prefix for rows that never resolved to a real NSE symbol.
# Keyed by BSE scrip_code so it's stable/unique per company across re-ingests
# (idempotent upsert, same as a real symbol) -- never dropped, never guessed.
UNMAPPED_SYMBOL_PREFIX = "_UNMAPPED_"

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
    # Additive migration for pre-existing DBs (same pattern as
    # scanner/discovery.py::ensure_schema) -- widen-mapping wave added these
    # three columns so every row records HOW it mapped.
    have = {r[1] for r in conn.execute("PRAGMA table_info(earnings_calendar)")}
    for name, ddl in (
        ("company_name", "TEXT"),
        ("scrip_code", "TEXT"),
        ("match_method", "TEXT"),
    ):
        if name not in have:
            conn.execute(f"ALTER TABLE earnings_calendar ADD COLUMN {name} {ddl}")
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


def load_known_symbols(conn) -> set[str]:
    """The widened symbol space for the ``symbol_direct`` match path: every
    symbol our own ``daily_prices`` price panel and ``universe`` table have
    ever carried, unioned. Deliberately DB-derived rather than a static
    file -- ``daily_prices`` alone carries ~3800 distinct symbols (the real
    NSE-tradeable universe we've ever ingested), vs. the 400-name
    NIFTYMIDSML400 constituents master, so this is what actually widens the
    BSE short_name fast path to Nifty50/large-cap names. ``universe`` is
    unioned in too even though it has been observed to lag ``daily_prices``
    (fewer distinct symbols, per a 2026-07-18 audit) -- cheap and can only
    help. Read-only; returns an empty set (never raises) if both tables are
    absent/empty, e.g. a brand-new DB."""
    out: set[str] = set()
    for table in ("daily_prices", "universe"):
        try:
            rows = conn.execute(f"SELECT DISTINCT symbol FROM {table}").fetchall()
        except Exception:  # noqa: BLE001 - table may not exist yet
            continue
        out.update(r[0] for r in rows if r[0])
    return out


# Hand-authored, editable overrides for CONFIRMED real short_name/company-name
# -> NSE-symbol mismatches -- i.e. cases where symbol_direct and
# name_normalized both fail *and* we've manually verified the true NSE
# trading symbol (never a guess; verify before adding a row here). Keyed by
# ``_normalize_company_name(Long_Name)`` so it reads the same way as
# ``load_symbol_master``'s own keys.
#
# `Unverified: empty as of 2026-07-18.` A live BSE Corpforthresults pull that
# day (513 rows) was audited against known_symbols (daily_prices ∪ universe,
# 3796 symbols at the time) plus the 400-name master: symbol_direct +
# name_normalized resolved 413/513 (80.5%, up from 136/513 = 26.5% before
# this wave). Every one of the 100 residual unresolved rows was checked by
# hand for a plausible near-match NSE symbol (substring search over
# daily_prices) and none was found -- each is a company genuinely outside
# manas_os's tracked NSE panel (BSE-only listing, illiquid microcap, or a
# very recent IPO like NSDL not yet in daily_prices), not a name-mapping
# bug. They correctly surface as ``match_method='unmapped'`` rows rather
# than being force-matched. Populate this dict as real mismatches are found
# on future pulls.
SYMBOL_OVERRIDES: dict[str, str] = {}


def resolve_symbol(
    company_name: str | None,
    short_name: str | None,
    master: dict[str, str],
    known_symbols: set[str] | None = None,
    overrides: dict[str, str] | None = None,
) -> tuple[str | None, str | None]:
    """BSE row -> ``(NSE symbol, match_method)``. Tries, in priority order:

    1. ``overrides`` (default ``SYMBOL_OVERRIDES``) -- hand-verified, wins
       outright when the normalized company name matches a key.
    2. ``short_name`` directly against ``known_symbols`` (default: just
       ``set(master.values())``, i.e. the original narrow behavior, when the
       caller doesn't pass a widened set -- callers with DB access should
       pass ``load_known_symbols(conn) | set(master.values())``).
    3. A normalized company-name lookup against ``master``.

    Returns ``(None, None)`` -- never a guess -- when nothing matches."""
    overrides = overrides if overrides is not None else SYMBOL_OVERRIDES
    if known_symbols is None:
        known_symbols = set(master.values())

    norm_name = _normalize_company_name(company_name)
    if norm_name in overrides:
        return overrides[norm_name], MATCH_OVERRIDE

    candidate = (short_name or "").strip().upper()
    if candidate and candidate in known_symbols:
        return candidate, MATCH_SYMBOL_DIRECT

    sym = master.get(norm_name)
    if sym:
        return sym, MATCH_NAME_NORMALIZED

    return None, None


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
    rows: list[dict[str, Any]],
    master: dict[str, str] | None = None,
    known_symbols: set[str] | None = None,
    overrides: dict[str, str] | None = None,
) -> tuple[list[dict[str, Any]], int]:
    """Pure: BSE ``Corpforthresults/w`` JSON rows -> normalized calendar rows.

    Returns ``(rows, unresolved_count)``. A row missing a usable meeting_date
    is dropped silently (malformed upstream data -- there's no date to place
    it on the calendar). A row whose company doesn't resolve to an NSE
    symbol is counted in ``unresolved_count`` but is NOT dropped: it's
    emitted with a synthetic ``_UNMAPPED_<scrip_code>`` symbol and
    ``match_method='unmapped'`` so callers can surface it instead of losing
    it silently. Every row carries ``match_method`` recording how (or
    whether) it resolved -- see ``resolve_symbol``.
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
        symbol, method = resolve_symbol(long_name, short_name, master, known_symbols, overrides)
        if not symbol:
            unresolved += 1
            method = MATCH_UNMAPPED
            symbol = f"{UNMAPPED_SYMBOL_PREFIX}{scrip_code or short_name.strip().upper() or 'UNKNOWN'}"
        out.append({
            "symbol": symbol,
            "meeting_date": meeting_date,
            "purpose": "Results",
            "source": SOURCE_BSE,
            "scrip_code": scrip_code,
            "company_name": str(long_name).strip(),
            "match_method": method,
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
            "match_method": MATCH_NSE_DIRECT,
            "scrip_code": None,
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
            "company_name": r.get("company_name"),
            "scrip_code": r.get("scrip_code"),
            "match_method": r.get("match_method"),
        }
        for r in rows
    ]
    conn.executemany(
        "INSERT INTO earnings_calendar (symbol, meeting_date, purpose, source, fetched_at, "
        "company_name, scrip_code, match_method) "
        "VALUES (:symbol, :meeting_date, :purpose, :source, :fetched_at, "
        ":company_name, :scrip_code, :match_method) "
        "ON CONFLICT(symbol, meeting_date, source) DO UPDATE SET "
        "purpose=excluded.purpose, fetched_at=excluded.fetched_at, "
        "company_name=excluded.company_name, scrip_code=excluded.scrip_code, "
        "match_method=excluded.match_method",
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

    master = load_symbol_master()
    # Union, never replace: load_known_symbols(conn) can legitimately be
    # empty (brand-new DB, no daily_prices/universe rows yet) -- falling
    # back to the master's own symbols keeps resolve_symbol at least as
    # capable as before this wave, never less.
    known_symbols = load_known_symbols(conn) | set(master.values())

    detail: dict[str, Any] = {}
    total_rows = 0
    bse_ok = False
    try:
        raw = bse_fetch()
        parsed, unresolved = parse_bse_calendar(raw, master, known_symbols=known_symbols)
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
