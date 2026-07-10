"""FOCUS aggregation layer — theme-of-the-day + EP/IPO shortlists, built ON
TOP of the per-stock discovery machinery (discovery_bucket, WAVE K K4).
Answers "what to concentrate on NOW" by rolling qualifying discovery_bucket
members up to their ChartsMaze basic_industry and ranking industries by
breadth-of-strength, not by any single stock's score.

Data sources (all already-persisted, nothing new ingested here):
  - discovery_bucket   -- per-symbol archetypes + metrics (discovery.py)
  - screener_hits      -- basic_industry membership (full universe; the
    chartsmaze stock-RS CSV only covers ~290 names/12 industries and would
    silently drop chemicals/specialty names, so it is NOT used here as the
    membership source)
  - industry_metrics   -- perf_1m/perf_1w industry-level returns
  - eod_detectors.listing_status -- IPO recency (days_since_listing)

Deterministic, no ML. Honest n-floor: an industry only becomes a FOCUS theme
when >= MIN_QUALIFYING_MEMBERS discovery_bucket members share it -- a lone
strong stock in a small industry is a stock call, not a theme call.
"""
from __future__ import annotations

import json
import time
from typing import Any

from manas_os.engine import eod_detectors

STAGE = "focus_themes"
SOURCE = "discovery_bucket"

MIN_QUALIFYING_MEMBERS = 3      # n-floor: below this an "industry" is noise
TOP_THEMES = 5
TOP_STOCKS_PER_THEME = 6
MEMBERSHIP_LOOKBACK_DAYS = 30   # screener_hits basic_industry freshness window
IPO_MAX_DAYS = 252              # ~12 trading months; matches ipo_base's own window
WATCH_LOOKBACK_DAYS = 5         # screener-hit recency for EP/IPO watch candidates
TOP_WATCH = 12

EP_SCREENERS = ("earnings-gap-up", "positive-earnings-reaction")
IPO_SCREENERS = ("ipo-setups", "past-IPO-listings")


def ensure_schema(conn) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS focus_themes ("
        "scan_date TEXT NOT NULL, industry TEXT NOT NULL, rank INTEGER NOT NULL, "
        "score_json TEXT NOT NULL, created_at TEXT DEFAULT (datetime('now')), "
        "PRIMARY KEY (scan_date, industry))"
    )


def _latest_bucket_date(conn, scan_date: str) -> str | None:
    row = conn.execute(
        "SELECT MAX(scan_date) AS d FROM discovery_bucket WHERE scan_date <= ?",
        (scan_date,),
    ).fetchone()
    return row["d"] if row and row["d"] else None


def _bucket_rows(conn, bucket_date: str) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT symbol, archetypes_json, metrics_json FROM discovery_bucket WHERE scan_date = ?",
        (bucket_date,),
    ).fetchall()
    out = []
    for r in rows:
        out.append({
            "symbol": r["symbol"],
            "archetypes": json.loads(r["archetypes_json"]),
            "metrics": json.loads(r["metrics_json"]),
        })
    return out


def _industry_membership(conn, as_of: str) -> tuple[dict[str, str], dict[str, float]]:
    """Latest basic_industry + rs_rating per symbol from screener_hits, looking
    back up to MEMBERSHIP_LOOKBACK_DAYS from `as_of` (screener_hits is not
    populated every session for every symbol)."""
    rows = conn.execute(
        "SELECT symbol, basic_industry, rs_rating, trade_date FROM screener_hits "
        "WHERE trade_date <= ? AND trade_date >= date(?, ?) AND basic_industry IS NOT NULL "
        "ORDER BY trade_date DESC",
        (as_of, as_of, f"-{MEMBERSHIP_LOOKBACK_DAYS} day"),
    ).fetchall()
    industry_by_symbol: dict[str, str] = {}
    rs_by_symbol: dict[str, float] = {}
    for r in rows:
        sym = r["symbol"]
        if sym not in industry_by_symbol:
            industry_by_symbol[sym] = r["basic_industry"]
        if sym not in rs_by_symbol and r["rs_rating"] is not None:
            rs_by_symbol[sym] = r["rs_rating"]
    return industry_by_symbol, rs_by_symbol


def _industry_perf(conn, as_of: str) -> dict[str, dict[str, Any]]:
    row_date = conn.execute(
        "SELECT MAX(snapshot_date) AS d FROM industry_metrics WHERE snapshot_date <= ?",
        (as_of,),
    ).fetchone()
    d = row_date["d"] if row_date else None
    if not d:
        return {}
    rows = conn.execute(
        "SELECT name, perf_1m, perf_1w, num_stocks FROM industry_metrics WHERE snapshot_date = ?",
        (d,),
    ).fetchall()
    return {r["name"]: dict(r) for r in rows}


def compute_focus(conn, scan_date: str) -> dict[str, Any]:
    """Rank industries by breadth of discovery-bucket strength on/before
    `scan_date`. Returns {available, as_of, themes: [...], reason}."""
    bucket_date = _latest_bucket_date(conn, scan_date)
    if not bucket_date:
        return {"available": False, "as_of": None, "themes": [],
                "reason": "no discovery_bucket rows on/before scan_date"}
    bucket = _bucket_rows(conn, bucket_date)
    if not bucket:
        return {"available": False, "as_of": bucket_date, "themes": [],
                "reason": "empty discovery_bucket for as_of date"}

    industry_by_symbol, rs_by_symbol = _industry_membership(conn, bucket_date)
    industry_perf = _industry_perf(conn, bucket_date)

    groups: dict[str, list[dict[str, Any]]] = {}
    for entry in bucket:
        industry = industry_by_symbol.get(entry["symbol"])
        if not industry:
            continue
        groups.setdefault(industry, []).append(entry)

    themes = []
    for industry, members in groups.items():
        n = len(members)
        if n < MIN_QUALIFYING_MEMBERS:
            continue

        rs_vals = [rs_by_symbol[m["symbol"]] for m in members if m["symbol"] in rs_by_symbol]
        avg_rs = round(sum(rs_vals) / len(rs_vals), 1) if rs_vals else None

        pct_up_vals = [m["metrics"].get("pct_up_from_65d_low") for m in members
                       if m["metrics"].get("pct_up_from_65d_low") is not None]
        pct_strong = (round(100.0 * sum(1 for v in pct_up_vals if v >= 30.0) / len(pct_up_vals), 1)
                      if pct_up_vals else None)

        purple_vals = [m["metrics"].get("purple_dot_count_60d") for m in members
                       if m["metrics"].get("purple_dot_count_60d") is not None]
        purple_density = (round(100.0 * sum(1 for v in purple_vals if v >= 1) / len(purple_vals), 1)
                           if purple_vals else None)

        perf = industry_perf.get(industry)
        ind_return_20d = perf["perf_1m"] if perf else None

        # Composite score = simple average of the available 0-100-scale
        # breadth components (RS, %-strong, purple-density). No invented
        # weights; components missing for a given industry are simply
        # excluded from that industry's average rather than defaulted to 0.
        components = [v for v in (avg_rs, pct_strong, purple_density) if v is not None]
        score = round(sum(components) / len(components), 1) if components else 0.0

        top_stocks = sorted(
            members,
            key=lambda m: (
                rs_by_symbol.get(m["symbol"], -1.0),
                m["metrics"].get("momentum_63d") if m["metrics"].get("momentum_63d") is not None else -999.0,
            ),
            reverse=True,
        )[:TOP_STOCKS_PER_THEME]

        themes.append({
            "industry": industry,
            "score": score,
            "member_count": n,
            "avg_rs": avg_rs,
            "pct_members_up65d_ge30": pct_strong,
            "purple_dot_density_pct": purple_density,
            "industry_return_20d_pct": ind_return_20d,
            "num_stocks_in_industry": perf["num_stocks"] if perf else None,
            "top_stocks": [
                {
                    "symbol": m["symbol"],
                    "rs": rs_by_symbol.get(m["symbol"]),
                    "pct_up_from_65d_low": m["metrics"].get("pct_up_from_65d_low"),
                    "purple_dot_count_60d": m["metrics"].get("purple_dot_count_60d"),
                    "adr20": m["metrics"].get("adr20"),
                    "archetypes": m["archetypes"],
                }
                for m in top_stocks
            ],
        })

    themes.sort(key=lambda t: t["score"], reverse=True)
    for i, t in enumerate(themes, start=1):
        t["rank"] = i

    return {
        "available": bool(themes),
        "as_of": bucket_date,
        "themes": themes,
        "reason": None if themes else f"no industry had >= {MIN_QUALIFYING_MEMBERS} qualifying discovery_bucket members",
    }


def persist_focus(conn, scan_date: str, focus: dict[str, Any]) -> int:
    ensure_schema(conn)
    conn.execute("DELETE FROM focus_themes WHERE scan_date = ?", (scan_date,))
    rows = 0
    for t in focus.get("themes", [])[:TOP_THEMES]:
        conn.execute(
            "INSERT INTO focus_themes (scan_date, industry, rank, score_json) VALUES (?, ?, ?, ?)",
            (scan_date, t["industry"], t["rank"], json.dumps(t)),
        )
        rows += 1
    return rows


def _recent_screener_symbols(conn, as_of: str, screeners: tuple[str, ...]) -> dict[str, str]:
    """symbol -> most recent matching screener name, within WATCH_LOOKBACK_DAYS."""
    placeholders = ",".join("?" for _ in screeners)
    rows = conn.execute(
        f"SELECT symbol, screener, trade_date FROM screener_hits "
        f"WHERE trade_date <= ? AND trade_date >= date(?, ?) AND screener IN ({placeholders}) "
        f"ORDER BY trade_date DESC",
        (as_of, as_of, f"-{WATCH_LOOKBACK_DAYS} day", *screeners),
    ).fetchall()
    out: dict[str, str] = {}
    for r in rows:
        out.setdefault(r["symbol"], r["screener"])
    return out


def _batch_trading_days(conn, symbols: set[str], as_of: str) -> dict[str, int]:
    """symbol -> count of distinct EQ trading days up to `as_of`, in ONE
    batched query. Used as a cheap pre-filter before the expensive per-symbol
    listing_status() call (whose rename check is an uncached ~1.5s full-table
    REPLACE() scan) -- days-so-far is exactly listing_status's own
    days_since_listing for a symbol whose first row IS its true listing date,
    so this narrows hundreds of screener-hit candidates down to the handful
    actually young enough to be an IPO before paying the expensive check."""
    if not symbols:
        return {}
    placeholders = ",".join("?" for _ in symbols)
    rows = conn.execute(
        f"SELECT symbol, COUNT(DISTINCT trade_date) AS days FROM daily_prices "
        f"WHERE series = 'EQ' AND trade_date <= ? AND symbol IN ({placeholders}) GROUP BY symbol",
        (as_of, *symbols),
    ).fetchall()
    return {r["symbol"]: r["days"] for r in rows}


def _cached_listing_status(conn, sym: str, bucket_date: str, cache: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """listing_status does a REPLACE()-based full-table scan on daily_prices
    (no usable index) to detect renames -- ~1.5s per call on the real DB.
    Memoized per (request, symbol) so callers sharing a cache dict never pay
    it twice for the same symbol."""
    if sym not in cache:
        cache[sym] = eod_detectors.listing_status(conn, sym, bucket_date)
    return cache[sym]


def _watch_row(conn, sym: str, screener_hit: str, bucket_date: str,
                bucket_by_symbol: dict[str, dict[str, Any]],
                listing_cache: dict[str, dict[str, Any]] | None = None,
                include_listing: bool = True) -> dict[str, Any]:
    entry = bucket_by_symbol.get(sym)
    metrics = entry["metrics"] if entry else {}
    if include_listing:
        listing = (_cached_listing_status(conn, sym, bucket_date, listing_cache)
                   if listing_cache is not None else eod_detectors.listing_status(conn, sym, bucket_date))
    else:
        listing = {}
    return {
        "symbol": sym,
        "screener_hit": screener_hit,
        "in_discovery_bucket": entry is not None,
        "archetypes": entry["archetypes"] if entry else [],
        "why": {
            "pct_up_from_65d_low": metrics.get("pct_up_from_65d_low"),
            "adr20": metrics.get("adr20"),
            "purple_dot_count_60d": metrics.get("purple_dot_count_60d"),
            "momentum_63d": metrics.get("momentum_63d"),
            "listing_status": listing.get("listing_status"),
            "days_since_listing": listing.get("days_since_listing"),
            "is_ipo": listing.get("is_ipo"),
        },
    }


def _rank_watch(rows: list[dict[str, Any]], limit: int = TOP_WATCH) -> list[dict[str, Any]]:
    def key(r: dict[str, Any]) -> tuple:
        w = r["why"]
        return (
            w.get("pct_up_from_65d_low") if w.get("pct_up_from_65d_low") is not None else -999.0,
            w.get("adr20") if w.get("adr20") is not None else -999.0,
            w.get("purple_dot_count_60d") if w.get("purple_dot_count_60d") is not None else -1,
        )
    ranked = sorted(rows, key=key, reverse=True)
    for i, r in enumerate(ranked, start=1):
        r["rank"] = i
    return ranked[:limit]


def ipo_watch(conn, scan_date: str, listing_cache: dict[str, dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    """Recent listings (<=IPO_MAX_DAYS trading sessions) ranked by discovery
    metrics. Candidates = IPO_SCREENERS hits (last WATCH_LOOKBACK_DAYS) UNION
    discovery_bucket 'ep_ipo' archetype members, filtered to genuinely recent
    listings via listing_status (days_since_listing). listing_status's rename
    check is an uncached ~1.5s full-table scan on the real DB, so pass a
    shared `listing_cache` dict when calling this alongside ep_watch."""
    bucket_date = _latest_bucket_date(conn, scan_date)
    if not bucket_date:
        return []
    bucket = _bucket_rows(conn, bucket_date)
    bucket_by_symbol = {e["symbol"]: e for e in bucket}
    hits = _recent_screener_symbols(conn, bucket_date, IPO_SCREENERS)
    candidates = set(hits) | {e["symbol"] for e in bucket if "ep_ipo" in e["archetypes"]}
    cache = listing_cache if listing_cache is not None else {}

    # Cheap batched pre-filter (one query) before the expensive per-symbol
    # rename-scan: screener hits alone can number in the hundreds. days-so-
    # far narrows to genuinely young symbols, but that set can still be too
    # large to run the ~1.5s full check on every member -- so rank by the
    # (cheap, already-loaded) discovery metrics FIRST and only pay the
    # expensive rename-aware listing_status on a small buffer around the
    # eventual top TOP_WATCH.
    trading_days = _batch_trading_days(conn, candidates, bucket_date)
    young = {sym for sym in candidates if (trading_days.get(sym) or IPO_MAX_DAYS + 1) <= IPO_MAX_DAYS}
    cheap_rows = [_watch_row(conn, sym, hits.get(sym, "ep_ipo_archetype"), bucket_date, bucket_by_symbol,
                              include_listing=False)
                  for sym in young]
    shortlist = _rank_watch(cheap_rows, limit=TOP_WATCH)

    rows = []
    for row in shortlist:
        sym = row["symbol"]
        listing = _cached_listing_status(conn, sym, bucket_date, cache)
        if listing.get("listing_status") != "known":
            continue
        days = listing.get("days_since_listing")
        if days is None or days > IPO_MAX_DAYS:
            continue
        rows.append(_watch_row(conn, sym, row["screener_hit"], bucket_date, bucket_by_symbol,
                                listing_cache=cache))
    return _rank_watch(rows)


def ep_watch(conn, scan_date: str, listing_cache: dict[str, dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    """Earnings-power / episodic-pivot shortlist. Candidates = EP_SCREENERS
    hits (last WATCH_LOOKBACK_DAYS) UNION discovery_bucket 'd2_episodic'
    archetype members, ranked by the same velocity/strength metrics. Listing
    status is NOT used for filtering here (EP names are rarely IPOs), so it
    is only attached when a symbol's status is already cached (e.g. from a
    prior ipo_watch call sharing the same `listing_cache`) -- never pays the
    ~1.5s rename-scan itself."""
    bucket_date = _latest_bucket_date(conn, scan_date)
    if not bucket_date:
        return []
    bucket = _bucket_rows(conn, bucket_date)
    bucket_by_symbol = {e["symbol"]: e for e in bucket}
    hits = _recent_screener_symbols(conn, bucket_date, EP_SCREENERS)
    candidates = set(hits) | {e["symbol"] for e in bucket if "d2_episodic" in e["archetypes"]}

    cache = listing_cache if listing_cache is not None else {}
    rows = []
    for sym in candidates:
        rows.append(_watch_row(conn, sym, hits.get(sym, "d2_episodic_archetype"), bucket_date, bucket_by_symbol,
                                listing_cache=cache, include_listing=sym in cache))
    return _rank_watch(rows)


def _log(conn, run_date: str, status: str, rows: int, started: float, detail: str) -> None:
    conn.execute(
        "INSERT INTO pipeline_runs (run_date, stage, source, status, rows_affected, "
        "duration_s, detail) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (run_date, STAGE, SOURCE, status, rows, round(time.monotonic() - started, 3), detail),
    )


def run(conn, run_date: str) -> dict[str, Any]:
    """Nightly stage entry point. Registered AFTER discovery_bucket. Never
    raises; failure-safe like discovery.run."""
    started = time.monotonic()
    try:
        ensure_schema(conn)
        bucket_date = _latest_bucket_date(conn, run_date)
        if bucket_date is None:
            _log(conn, run_date, "skip", 0, started, "no discovery_bucket for focus_themes")
            conn.commit()
            return {"status": "skip", "rows": 0, "as_of": None}
        focus = compute_focus(conn, run_date)
        rows = persist_focus(conn, run_date, focus)
        _log(conn, run_date, "ok", rows, started, f"as_of={focus.get('as_of')} themes={rows}")
        conn.commit()
        return {"status": "ok", "rows": rows, "as_of": focus.get("as_of")}
    except Exception as exc:  # noqa: BLE001
        _log(conn, run_date, "fail", 0, started, str(exc))
        conn.commit()
        return {"status": "fail", "rows": 0, "detail": str(exc)}
