"""Source-abstraction layer for FilingsEdge ingestion.

Wraps every external data source behind our own interface so a library swap
or endpoint change never touches downstream M-stage code (handoff spec §4.1).

Two principles:
  1. Lazy imports — the actual libraries (jugaad_data, pdfplumber) are optional.
     We probe for them and fall back to direct HTTP via curl_cffi (installed)
     which impersonates a browser and bypasses most NSE fingerprint blocks.
  2. Raw files preserved (inbox pattern) — every download is saved to
     data/inbox/YYYY-MM-DD/ before parsing, so a parser break never loses data.

Politeness: post-market batch only, 2-5s randomized delays, realistic
User-Agent, aggressive caching. This is a nightly job, not HFT.
"""
from __future__ import annotations

import os
import time
import random
import logging
from datetime import datetime
from pathlib import Path

import requests

logger = logging.getLogger('filings.sources')

_ROOT = Path(__file__).resolve().parents[2]
INBOX_DIR = _ROOT / 'data' / 'inbox'

# curl_cffi is the preferred HTTP client for NSE (browser impersonation).
# Fall back to plain requests if unavailable — NSE may then 403 occasionally.
try:
    from curl_cffi import requests as cffi_requests  # type: ignore
    _HAVE_CFFI = True
except ImportError:
    _HAVE_CFFI = False
    logger.info("curl_cffi not available; using plain requests (NSE may block)")

_BROWSER_HEADERS = {
    'User-Agent': ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                   'AppleWebKit/537.36 (KHTML, like Gecko) '
                   'Chrome/120.0.0.0 Safari/537.36'),
    'Accept': 'text/html,application/json,application/pdf,*/*',
    'Accept-Language': 'en-US,en;q=0.9',
}


def inbox_path(trade_date: str) -> Path:
    """Return (creating) the inbox dir for a given trade date."""
    p = INBOX_DIR / trade_date
    p.mkdir(parents=True, exist_ok=True)
    return p


def polite_sleep(min_s: float = 2.0, max_s: float = 5.0):
    """Randomized delay between requests. Never parallel-hammer NSE."""
    time.sleep(random.uniform(min_s, max_s))


def http_get(url: str, *, params: dict | None = None,
             headers: dict | None = None, timeout: int = 30,
             impersonate: bool = True) -> requests.Response:
    """HTTP GET with browser impersonation when available.

    NSE endpoints require browser-like headers and a session cookie handshake.
    curl_cffi's impersonate mode handles this transparently; plain requests
    will work for some endpoints and 403 for others.
    """
    h = {**_BROWSER_HEADERS, **(headers or {})}
    if impersonate and _HAVE_CFFI:
        # curl_cffi.requests.get signature mirrors requests closely
        return cffi_requests.get(url, params=params, headers=h,
                                 timeout=timeout, impersonate='chrome120')
    return requests.get(url, params=params, headers=h, timeout=timeout)


def save_raw(trade_date: str, filename: str, content: bytes) -> Path:
    """Save raw bytes to the immutable inbox. Returns the saved path.

    Never overwrites — if filename exists, appends a counter. This is the
    inbox pattern: raw files are the recovery substrate when parsers break.
    """
    d = inbox_path(trade_date)
    path = d / filename
    if path.exists():
        stem, _, ext = filename.rpartition('.')
        i = 1
        while path.exists():
            path = d / f"{stem}_{i}.{ext}" if ext else d / f"{stem}_{i}"
            i += 1
    path.write_bytes(content)
    return path


# --- Library availability probes (called lazily by ingest modules) ---------

def have_jugaad() -> bool:
    try:
        import jugaad_data  # noqa: F401
        return True
    except ImportError:
        return False


def have_pdfplumber() -> bool:
    try:
        import pdfplumber  # noqa: F401
        return True
    except ImportError:
        return False


def extract_pdf_text(pdf_path: Path, max_chars: int = 6000) -> str:
    """Extract text from a PDF. Prefers pdfplumber; falls back to a stub.

    Most NSE announcement PDFs are digital text; OCR is explicitly out of
    scope for v1 (handoff spec §3). If pdfplumber isn't installed, returns
    empty string and logs a warning — the caller should mark the row
    needs_review rather than crash.
    """
    if not have_pdfplumber():
        logger.warning("pdfplumber not installed; cannot extract %s "
                       "(mark for review)", pdf_path)
        return ""
    import pdfplumber
    out: list[str] = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                t = page.extract_text() or ""
                out.append(t)
                if sum(len(x) for x in out) >= max_chars:
                    break
    except Exception as e:
        logger.warning("PDF extract failed for %s: %s", pdf_path, e)
        return ""
    return "\n".join(out)[:max_chars]


def today_iso() -> str:
    return datetime.now().strftime('%Y-%m-%d')
