"""Universe classification stage — populates the ``universe`` table.

The ``universe`` table (symbol, as_of_date, sector, industry, is_tradeable, …)
was defined in schema.sql but never had a producer — it sat empty, which is why
``alpha/features.py`` read ``universe.sector`` as an empty dict and the alpha
screen showed "unmapped" for every symbol.

This stage is that missing producer. For each ``run_date`` it:
  1. Builds the priced universe (every EQ row with close >= 1 on run_date).
  2. Computes ``is_tradeable`` via the SAME liquidity gate
     (``engine.universe_filter``) the alpha-features fallback uses — so
     populating ``universe`` never shrinks the alpha snapshot.
  3. Resolves ``industry`` from a 3-layer fallback chain:
       a. ``screener_hits.basic_industry`` (ChartMaze nightly, ~80% coverage)
       b. Screener.in company-page scrape (gap-fill for the rest)
       c. NULL (honest "unclassified" — symbol stays in the universe)
  4. Resolves ``sector`` via the canonical ``regime.sectors.INDUSTRY_TO_SECTOR``
     map (112 industries -> 23 sector keys), already hand-classified.
  5. Upserts one row per symbol into ``universe`` (PK symbol + as_of_date).

CRITICAL: every priced symbol gets a ``universe`` row, even if its industry is
unknown. ``alpha/features.py:54-55`` uses ``is_tradeable`` as a hard eligibility
gate once the table is non-empty — if we only wrote classifiable symbols, we'd
silently drop the rest from the alpha snapshot.
"""
from __future__ import annotations

import html as html_mod
import re
import time
from typing import Callable

import requests

from manas_os.regime.sectors import INDUSTRY_TO_SECTOR

STAGE = "classify_universe"
SOURCE = "classify_universe"

# Screener.in scrape config (matches fii_dii.py / nse_indices.py conventions).
_SCREENER_URL = "https://www.screener.in/company/{symbol}/"
_SCREENER_HOME = "https://www.screener.in"
_TIMEOUT = 15
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}
# title="Sector">VALUE</a>  /  title="Industry">VALUE</a>
_SCREENER_SECTOR_RE = re.compile(r'title="Sector">\s*([^<]+?)\s*</a>')
_SCREENER_INDUSTRY_RE = re.compile(r'title="Industry">\s*([^<]+?)\s*</a>')

# Screener.in's sector taxonomy differs from our canonical keys. Map the known
# Screener sector labels to our sector keys so a Screener-sourced symbol still
# lands a real sector even when its industry label doesn't match
# INDUSTRY_TO_SECTOR exactly.
_SCREENER_SECTOR_TO_KEY: dict[str, str] = {
    "Automobile": "AUTO",
    "Banking": "BANK",
    "Financial Services": "FINANCIAL_SERVICES",
    "Consumer Durables": "CONSUMER_DURABLES",
    "Consumer Non-Durables": "FMCG",
    "FMCG": "FMCG",
    "Information Technology": "IT",
    "Technology": "IT",
    "Media": "MEDIA",
    "Metals & Mining": "METAL",
    "Metals": "METAL",
    "Healthcare": "PHARMA",
    "Pharmaceuticals": "PHARMA",
    "Real Estate": "REALTY",
    "Realty": "REALTY",
    "Energy": "ENERGY",
    "Power": "ENERGY",
    "Infrastructure": "INFRASTRUCTURE",
    "Construction": "INFRASTRUCTURE",
    "Capital Goods": "CAPITAL_GOODS",
    "Chemicals": "CHEMICALS",
    "Telecommunication": "TELECOM",
    "Telecom": "TELECOM",
    "Textiles": "TEXTILES",
    "Utilities": "UTILITIES",
    "Oil & Gas": "OIL_GAS",
    "Diversified": "DIVERSIFIED",
    "Services": "SERVICES",
    "Forest Materials": "FOREST_MATERIALS",
}


# ─────────────────────────────────────────────────────────────────────────────
# Pure helpers (unit-testable without network or DB)
# ─────────────────────────────────────────────────────────────────────────────

def sector_for_industry(industry: str | None) -> str | None:
    """Canonical sector key for a ChartMaze-style industry label.

    Uses the hand-classified ``regime.sectors.INDUSTRY_TO_SECTOR`` map
    (112 industries -> 23 sector keys). Returns None for unknown/NULL industry.
    """
    if not industry:
        return None
    return INDUSTRY_TO_SECTOR.get(industry.strip())


def _clean_screener_label(raw: str | None) -> str | None:
    """Unescape HTML entities and trim a scraped Screener label."""
    if not raw:
        return None
    return html_mod.unescape(raw).strip() or None


def parse_screener_html(text: str) -> tuple[str | None, str | None]:
    """Pure parser: extract (sector_label, industry_label) from a Screener.in
    company-page HTML body. Returns (None, None) if neither pattern matches.

    Screener's breadcrumb exposes ``title="Sector">VALUE</a>`` and
    ``title="Industry">VALUE</a>``. Labels carry HTML entities (&amp; etc.)
    which are unescaped here.
    """
    sec_m = _SCREENER_SECTOR_RE.search(text)
    ind_m = _SCREENER_INDUSTRY_RE.search(text)
    sector = _clean_screener_label(sec_m.group(1) if sec_m else None)
    industry = _clean_screener_label(ind_m.group(1) if ind_m else None)
    return sector, industry


def classify_symbol(
    symbol: str,
    basic_industry: str | None,
    screener_industry: str | None,
    screener_sector: str | None,
) -> tuple[str | None, str | None]:
    """Resolve (industry, sector) for one symbol from the fallback chain.

    Pure: no network, no DB. Takes the pre-fetched data and applies the
    classification priority:
      1. ChartMaze basic_industry (authoritative for our taxonomy) + its
         canonical sector via INDUSTRY_TO_SECTOR.
      2. Screener.in industry, mapped through INDUSTRY_TO_SECTOR if the label
         matches; else Screener's own sector label via _SCREENER_SECTOR_TO_KEY.
      3. NULL / NULL.

    Returns (industry, sector_key). sector_key is a canonical key (AUTO, IT,
    ...) or None; industry is the human label or None.
    """
    # Layer 1: ChartMaze basic_industry
    if basic_industry:
        bi = basic_industry.strip()
        sec = sector_for_industry(bi)
        if sec:
            return bi, sec
        # industry known but not in map — keep the industry, sector unknown
        return bi, None

    # Layer 2: Screener.in
    if screener_industry:
        si = screener_industry.strip()
        sec = sector_for_industry(si)
        if sec:
            return si, sec
        # try matching the Screener industry to a known industry by substring
        for known_ind, known_sec in INDUSTRY_TO_SECTOR.items():
            if si.lower() == known_ind.lower():
                return known_ind, known_sec
    # fall back to Screener's sector label
    if screener_sector:
        key = _SCREENER_SECTOR_TO_KEY.get(screener_sector.strip())
        if key:
            return screener_industry, key

    # Layer 3: unknown
    return None, None


# ─────────────────────────────────────────────────────────────────────────────
# Screener.in network layer (isolated — tests inject a fake fetcher)
# ─────────────────────────────────────────────────────────────────────────────

def _make_session() -> requests.Session:
    sess = requests.Session()
    sess.headers.update(_HEADERS)
    try:
        sess.get(_SCREENER_HOME, timeout=_TIMEOUT)  # prime cookies
    except requests.RequestException:
        pass  # cookie-priming is best-effort; pages may still work
    return sess


def fetch_screener_industry(
    sess: requests.Session,
    symbol: str,
) -> tuple[str | None, str | None]:
    """Fetch one symbol's Screener.in page and return (sector, industry).

    Returns (None, None) on any failure (404, timeout, parse miss) — never
    raises. The caller treats None as "leave industry NULL".
    """
    try:
        resp = sess.get(_SCREENER_URL.format(symbol=symbol), timeout=_TIMEOUT)
    except requests.RequestException:
        return None, None
    if resp.status_code != 200:
        return None, None
    return parse_screener_html(resp.text)


# ─────────────────────────────────────────────────────────────────────────────
# DB reads
# ─────────────────────────────────────────────────────────────────────────────

def _priced_universe(conn, run_date: str) -> list[str]:
    """Every EQ symbol with close >= 1 on run_date (the breadth universe)."""
    return [
        r[0] for r in conn.execute(
            "SELECT DISTINCT symbol FROM daily_prices "
            "WHERE trade_date = ? AND series = 'EQ' AND close >= 1 "
            "ORDER BY symbol ASC",
            (run_date,),
        )
    ]


def _basic_industry_map(conn) -> dict[str, str]:
    """Latest non-null ``screener_hits.basic_industry`` per symbol.

    ChartMaze nightly fills basic_industry; we take the most recent non-null
    value per symbol so coverage accumulates even if a given night's dump
    omitted a name.
    """
    rows = conn.execute(
        "SELECT symbol, basic_industry FROM screener_hits "
        "WHERE basic_industry IS NOT NULL AND basic_industry != '' "
        "GROUP BY symbol "
        "HAVING MAX(trade_date)"
    )
    return {r["symbol"]: r["basic_industry"] for r in rows}


def _compute_tradeable(conn, run_date: str, symbols: list[str]) -> tuple[set[str], dict[str, dict]]:
    """Apply the canonical liquidity gate (same one alpha/features.py falls
    back to) to get the tradeable set + per-symbol metrics.

    Returns (tradeable_set, metrics_by_symbol) where metrics_by_symbol carries
    market_cap_cr / avg_turnover_cr for the universe row (best-effort).
    """
    try:
        from manas_os.engine.universe_filter import GateConfig, filter_universe
        result = filter_universe(
            conn, run_date,
            cfg=GateConfig(min_price=30.0, min_avg_turnover_cr=5.0, exclude_etf=True),
        )
        tradeable = set(result["tradeable"])
        metrics = {m["symbol"]: m for m in result.get("excluded", [])}
        # filter_universe returns metrics for excluded names; for tradeable ones
        # we don't get metrics back, so leave them NULL — the gate is what matters.
        return tradeable, metrics
    except Exception:
        # If the filter module can't run, mark everything tradeable (matches
        # alpha/features.py's fallback: eligible_symbols=None => no filter).
        return set(symbols), {}


# ─────────────────────────────────────────────────────────────────────────────
# Upsert
# ─────────────────────────────────────────────────────────────────────────────

def _upsert_rows(conn, run_date: str, rows: list[dict]) -> int:
    """Idempotent upsert on (symbol, as_of_date) PK."""
    if not rows:
        return 0
    cols = ["symbol", "as_of_date", "series", "sector", "industry",
            "is_tradeable", "market_cap_cr", "avg_turnover_cr"]
    placeholders = ", ".join("?" for _ in cols)
    updates = ", ".join(f"{c}=excluded.{c}" for c in cols if c not in ("symbol", "as_of_date"))
    sql = (
        f"INSERT INTO universe ({', '.join(cols)}) "
        f"VALUES ({placeholders}) "
        f"ON CONFLICT(symbol, as_of_date) DO UPDATE SET {updates}, "
        f"ingested_at=datetime('now')"
    )
    conn.executemany(sql, [[r.get(c) for c in cols] for r in rows])
    return len(rows)


def _log_run(conn, run_date: str, status: str, rows: int, dur: float, detail: str) -> None:
    conn.execute(
        "INSERT INTO pipeline_runs (run_date, stage, source, status, rows_affected, "
        "duration_s, detail) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (run_date, STAGE, SOURCE, status, rows, dur, detail),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Orchestration (mirrors breadth_sheet.run / fii_dii.run)
# ─────────────────────────────────────────────────────────────────────────────

def run(
    conn,
    run_date: str,
    *,
    screener_fetch: Callable[[requests.Session, str], tuple[str | None, str | None]] | None = None,
    screener_session: requests.Session | None = None,
) -> dict:
    """Populate ``universe`` for run_date and write a pipeline_runs row.

    Returns ``{"status", "rows_affected", "detail"}``. Never raises — a
    Screener.in outage degrades to ChartMaze-only coverage (industry NULL for
    the gap), not a stage failure.

    ``screener_fetch`` / ``screener_session`` are injection points for tests
    (avoid real network). In production both are None and the real fetcher runs.
    """
    started = time.monotonic()
    try:
        symbols = _priced_universe(conn, run_date)
        if not symbols:
            dur = time.monotonic() - started
            detail = f"no priced EQ rows for {run_date}"
            _log_run(conn, run_date, "skip", 0, dur, detail)
            conn.commit()
            return {"status": "skip", "rows_affected": 0, "detail": detail}

        bi_map = _basic_industry_map(conn)
        tradeable, _metrics = _compute_tradeable(conn, run_date, symbols)

        # Screener gap-fill: only for symbols NOT in the ChartMaze map.
        fetcher = screener_fetch or fetch_screener_industry
        sess = screener_session
        if sess is None and fetcher is fetch_screener_industry:
            sess = _make_session()

        screener_cache: dict[str, tuple[str | None, str | None]] = {}
        gap_symbols = [s for s in symbols if s not in bi_map]
        scraped_ok = 0
        # Circuit breaker (2026-07-17): when screener.in is unreachable every
        # fetch burns the full 15s timeout; a few hundred gap symbols then
        # wedges the whole pipeline for hours at ~0 CPU (observed live on the
        # 07-15 catch-up, twice). Scattered 404s are fine — only a CONSECUTIVE
        # failure streak with zero successes yet, or blowing the total time
        # budget, aborts the remaining fetches. The stage stays honest: the
        # detail line reports how many fetches were skipped and why.
        consecutive_fail = 0
        skipped = 0
        abort_reason: str | None = None
        fetch_started = time.monotonic()
        for i, sym in enumerate(gap_symbols):
            if consecutive_fail >= 8 and scraped_ok == 0:
                skipped = len(gap_symbols) - i
                abort_reason = "screener.in unreachable (8 consecutive failures, 0 successes)"
                break
            if time.monotonic() - fetch_started > 180:
                skipped = len(gap_symbols) - i
                abort_reason = "screener gap-fill time budget (180s) exhausted"
                break
            sec, ind = fetcher(sess, sym) if sess else fetcher(None, sym)
            screener_cache[sym] = (sec, ind)
            if ind:
                scraped_ok += 1
                consecutive_fail = 0
            else:
                consecutive_fail += 1

        # Build universe rows
        rows: list[dict] = []
        with_sector = 0
        for sym in symbols:
            bi = bi_map.get(sym)
            sc = screener_cache.get(sym, (None, None))
            industry, sector = classify_symbol(sym, bi, sc[1], sc[0])
            if sector:
                with_sector += 1
            rows.append({
                "symbol": sym,
                "as_of_date": run_date,
                "series": "EQ",
                "sector": sector,
                "industry": industry,
                "is_tradeable": 1 if sym in tradeable else 0,
                "market_cap_cr": None,
                "avg_turnover_cr": None,
            })

        written = _upsert_rows(conn, run_date, rows)
        dur = time.monotonic() - started
        detail = (
            f"universe={len(symbols)} classified={with_sector} "
            f"chartmaze={len(bi_map)} screener_gap={len(gap_symbols)} "
            f"scraped_ok={scraped_ok}"
        )
        if abort_reason:
            detail += f"; skipped {skipped} gap fetches — {abort_reason}"
        _log_run(conn, run_date, "ok", written, dur, detail)
        conn.commit()
        return {"status": "ok", "rows_affected": written, "detail": detail}
    except Exception as exc:
        dur = time.monotonic() - started
        _log_run(conn, run_date, "fail", 0, dur, f"{type(exc).__name__}: {exc}")
        conn.commit()
        raise
