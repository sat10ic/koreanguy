"""manas_os/scanner/theme_pulse.py — correlated-group ("theme") surfacing.

Answers the standing gap this module exists to close: a live Monday incident
where WABAG + EIEL + DENTA (a "water" industry group) were all respecting
10/20 EMA at the same time across scan/WATCH/discovery, and nobody was told
-- each name was read in isolation. This module groups the SAME scan_date's
scan/WATCH/discovery lanes by ChartsMaze industry and flags a group as a
"theme" when enough of it is moving together at once, mechanically (no ML,
no LLM narrative).

Lanes (per scan_date), each a set of distinct symbols:
  scan       -- scan_candidates                              (gate-passed)
  watch      -- discovery_bucket WHERE classification='WATCH'  (anticipation)
  discovery  -- discovery_bucket WHERE classification='DISCOVERY'

Industry membership: the latest stock_industry_rs snapshot on/before
scan_date (ChartsMaze Basic Industry labels), mapped to a canonical sector
key via manas_os.regime.sectors.INDUSTRY_TO_SECTOR (stored alongside as
sector_key). A symbol with no stock_industry_rs row on/before scan_date is
simply excluded from grouping (never guessed).

Fire rule (Assumption -- both numbers are a first-pass guess, tell me if
wrong):
  >= MIN_MEMBERS_STRONG (3) lane-members share an industry, OR
  >= MIN_MEMBERS_WEAK (2) lane-members share an industry AND the group's
     aggregate 5d return > WEAK_RETURN_THRESHOLD_PCT (4.0)%.

"Aggregate 5d return" = simple mean of the GROUP's own member symbols' 5d
close-to-close return (daily_prices, entry = latest EQ close on/before
scan_date, base = the close 5 EQ sessions earlier for that symbol) -- not
industry_metrics/perf_1w, which is a different lookback and scores the
FULL industry rather than just the names actually showing up in scan/WATCH/
discovery today. A member missing either close is excluded from the average
(n drops honestly; never imputed).
"""
from __future__ import annotations

import json
import time
from typing import Any

from manas_os.regime.sectors import INDUSTRY_TO_SECTOR, display_label


def _sector_key_for_industry(industry: str) -> str:
    """Canonical sector key for a ChartsMaze Basic Industry label, via the
    same INDUSTRY_TO_SECTOR map industries_for_sector() reverses (NOT
    canonical_sector_key(), which maps the coarser MARS sector-CSV labels --
    a different vocabulary; 'Water Supply & Management' as an industry has
    no entry there but does in INDUSTRY_TO_SECTOR). Unmapped industries fall
    back to their own uppercased label so a new ChartsMaze industry still
    surfaces as its own group instead of vanishing (same honesty rule
    canonical_sector_key uses)."""
    return INDUSTRY_TO_SECTOR.get(industry) or industry.strip().upper()

STAGE = "theme_pulse"
SOURCE = "scan_candidates+discovery_bucket+stock_industry_rs"

LANES: tuple[str, ...] = ("scan", "watch", "discovery")
MIN_MEMBERS_STRONG = 3     # Assumption: >=3 lane-members sharing an industry is a theme regardless of return -- tell me if wrong.
MIN_MEMBERS_WEAK = 2       # Assumption: 2 members can still be a theme if...
WEAK_RETURN_THRESHOLD_PCT = 4.0  # ...their aggregate 5d return exceeds this -- tell me if wrong.
RETURN_LOOKBACK_SESSIONS = 5
PRICE_SERIES = "EQ"


def ensure_schema(conn) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS theme_pulse ("
        "scan_date TEXT NOT NULL, industry TEXT NOT NULL, sector_key TEXT, "
        "member_symbols_json TEXT NOT NULL, avg_5d_pct REAL, lanes_json TEXT NOT NULL, "
        "created_at TEXT DEFAULT (datetime('now')), "
        "PRIMARY KEY (scan_date, industry))"
    )


def _chunks(seq: list, n: int):
    for i in range(0, len(seq), n):
        yield seq[i : i + n]


def _lane_symbols(conn, scan_date: str) -> dict[str, set[str]]:
    scan = {
        r[0] for r in conn.execute(
            "SELECT DISTINCT symbol FROM scan_candidates WHERE scan_date = ?", (scan_date,)
        ).fetchall()
    }
    watch = {
        r[0] for r in conn.execute(
            "SELECT DISTINCT symbol FROM discovery_bucket WHERE scan_date = ? AND classification = 'WATCH'",
            (scan_date,),
        ).fetchall()
    }
    discovery = {
        r[0] for r in conn.execute(
            "SELECT DISTINCT symbol FROM discovery_bucket WHERE scan_date = ? AND classification = 'DISCOVERY'",
            (scan_date,),
        ).fetchall()
    }
    return {"scan": scan, "watch": watch, "discovery": discovery}


def _most_recent_industry_rs_date(conn, on_or_before: str) -> str | None:
    row = conn.execute(
        "SELECT MAX(snapshot_date) AS d FROM stock_industry_rs WHERE snapshot_date <= ?",
        (on_or_before,),
    ).fetchone()
    return row["d"] if row and row["d"] else None


def _industry_by_symbol(conn, symbols: set[str], scan_date: str) -> dict[str, str]:
    """Latest ChartsMaze industry label per symbol, from stock_industry_rs,
    at or before scan_date. Symbols with no snapshot on/before scan_date are
    simply absent from the returned dict (excluded from grouping)."""
    if not symbols:
        return {}
    out: dict[str, str] = {}
    for chunk in _chunks(sorted(symbols), 400):
        placeholders = ",".join("?" for _ in chunk)
        rows = conn.execute(
            f"SELECT s.ticker, s.industry FROM stock_industry_rs s "
            f"JOIN (SELECT ticker, MAX(snapshot_date) AS d FROM stock_industry_rs "
            f"      WHERE snapshot_date <= ? AND ticker IN ({placeholders}) "
            f"      GROUP BY ticker) latest "
            f"ON s.ticker = latest.ticker AND s.snapshot_date = latest.d",
            (scan_date, *chunk),
        ).fetchall()
        for ticker, industry in rows:
            out[ticker] = industry
    return out


def _five_day_returns(conn, symbols: set[str], scan_date: str) -> dict[str, float]:
    """symbol -> 5d close-to-close % return ending on the latest EQ session
    on/before scan_date. Mirrors scorecard._forward_returns's ROW_NUMBER/
    OFFSET pattern, just walking backward (DESC) instead of forward.
    Missing either end point excludes that symbol (n drops, not imputed)."""
    if not symbols:
        return {}
    latest: dict[str, float] = {}
    base: dict[str, float] = {}
    for chunk in _chunks(sorted(symbols), 400):
        placeholders = ",".join("?" for _ in chunk)
        rows = conn.execute(
            f"SELECT symbol, rn, close FROM ("
            f"  SELECT symbol, close, "
            f"         ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY trade_date DESC) AS rn "
            f"  FROM daily_prices "
            f"  WHERE series = ? AND trade_date <= ? AND symbol IN ({placeholders})"
            f") WHERE rn IN (1, ?)",
            (PRICE_SERIES, scan_date, *chunk, RETURN_LOOKBACK_SESSIONS + 1),
        ).fetchall()
        for sym, rn, close in rows:
            if close is None:
                continue
            if rn == 1:
                latest[sym] = float(close)
            elif rn == RETURN_LOOKBACK_SESSIONS + 1:
                base[sym] = float(close)

    out: dict[str, float] = {}
    for sym in symbols:
        b = base.get(sym)
        l = latest.get(sym)
        if b and l is not None:
            out[sym] = round((l - b) / b * 100.0, 4)
    return out


def compute_theme_pulse(conn, scan_date: str) -> dict[str, Any]:
    """Group scan/WATCH/discovery lane members by industry for scan_date and
    return the qualifying themes (fire rule in the module docstring). Pure
    read; never writes. Returns {available, as_of, themes, reason}."""
    lanes = _lane_symbols(conn, scan_date)
    union_symbols: set[str] = set()
    for syms in lanes.values():
        union_symbols |= syms
    if not union_symbols:
        return {
            "available": False, "as_of": scan_date, "themes": [],
            "reason": "no scan_candidates/discovery_bucket rows for scan_date",
        }

    industry_by_symbol = _industry_by_symbol(conn, union_symbols, scan_date)
    returns_by_symbol = _five_day_returns(conn, union_symbols, scan_date)

    groups: dict[str, set[str]] = {}
    for sym in union_symbols:
        industry = industry_by_symbol.get(sym)
        if not industry:
            continue
        groups.setdefault(industry, set()).add(sym)

    themes: list[dict[str, Any]] = []
    for industry, members in groups.items():
        n = len(members)
        if n < MIN_MEMBERS_WEAK:
            continue

        ret_vals = [returns_by_symbol[m] for m in members if m in returns_by_symbol]
        avg_5d_pct = round(sum(ret_vals) / len(ret_vals), 2) if ret_vals else None

        fires = n >= MIN_MEMBERS_STRONG or (
            n >= MIN_MEMBERS_WEAK and avg_5d_pct is not None and avg_5d_pct > WEAK_RETURN_THRESHOLD_PCT
        )
        if not fires:
            continue

        lanes_for_theme = {
            lane: sorted(lane_syms & members) for lane, lane_syms in lanes.items() if lane_syms & members
        }
        sector_key = _sector_key_for_industry(industry)
        themes.append({
            "industry": industry,
            "sector_key": sector_key,
            "sector_label": display_label(sector_key),
            "member_symbols": sorted(members),
            "member_count": n,
            "avg_5d_pct": avg_5d_pct,
            "lanes": lanes_for_theme,
        })

    themes.sort(key=lambda t: (t["member_count"], t["avg_5d_pct"] or 0.0), reverse=True)
    return {
        "available": bool(themes),
        "as_of": scan_date,
        "themes": themes,
        "reason": None if themes else (
            f"no industry had >= {MIN_MEMBERS_STRONG} lane-members, or >= {MIN_MEMBERS_WEAK} "
            f"with aggregate 5d return > {WEAK_RETURN_THRESHOLD_PCT}%"
        ),
    }


def persist_theme_pulse(conn, scan_date: str, result: dict[str, Any]) -> int:
    ensure_schema(conn)
    conn.execute("DELETE FROM theme_pulse WHERE scan_date = ?", (scan_date,))
    rows = 0
    for t in result.get("themes", []):
        conn.execute(
            "INSERT INTO theme_pulse (scan_date, industry, sector_key, member_symbols_json, avg_5d_pct, lanes_json) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                scan_date, t["industry"], t["sector_key"],
                json.dumps(t["member_symbols"]), t["avg_5d_pct"], json.dumps(t["lanes"]),
            ),
        )
        rows += 1
    return rows


def read_persisted(conn, scan_date: str) -> list[dict[str, Any]] | None:
    """Themes actually persisted for scan_date (exact match), reconstructed
    into the same shape compute_theme_pulse's `themes` entries have (plus
    sector_label, recomputed from sector_key since it isn't stored). None
    when nothing was persisted for that date (caller decides the fallback)."""
    ensure_schema(conn)
    rows = conn.execute(
        "SELECT industry, sector_key, member_symbols_json, avg_5d_pct, lanes_json "
        "FROM theme_pulse WHERE scan_date = ? ORDER BY industry",
        (scan_date,),
    ).fetchall()
    if not rows:
        return None
    out = []
    for r in rows:
        members = json.loads(r["member_symbols_json"])
        lanes = json.loads(r["lanes_json"])
        out.append({
            "industry": r["industry"],
            "sector_key": r["sector_key"],
            "sector_label": display_label(r["sector_key"]) if r["sector_key"] else None,
            "member_symbols": members,
            "member_count": len(members),
            "avg_5d_pct": r["avg_5d_pct"],
            "lanes": lanes,
        })
    out.sort(key=lambda t: (t["member_count"], t["avg_5d_pct"] or 0.0), reverse=True)
    return out


def _log(conn, run_date: str, status: str, rows: int, started: float, detail: str) -> None:
    conn.execute(
        "INSERT INTO pipeline_runs (run_date, stage, source, status, rows_affected, "
        "duration_s, detail) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (run_date, STAGE, SOURCE, status, rows, round(time.monotonic() - started, 3), detail),
    )


def run(conn, run_date: str) -> dict[str, Any]:
    """Nightly stage entry point. Registered AFTER discovery_bucket (needs
    scan_candidates + discovery_bucket populated for run_date). Never
    raises; failure-safe like discovery.run / focus.run."""
    started = time.monotonic()
    try:
        ensure_schema(conn)
        result = compute_theme_pulse(conn, run_date)
        rows = persist_theme_pulse(conn, run_date, result)
        _log(conn, run_date, "ok", rows, started, f"as_of={result.get('as_of')} themes={rows}")
        conn.commit()
        return {"status": "ok", "rows": rows, "as_of": result.get("as_of")}
    except Exception as exc:  # noqa: BLE001
        _log(conn, run_date, "fail", 0, started, str(exc))
        conn.commit()
        return {"status": "fail", "rows": 0, "detail": str(exc)}
