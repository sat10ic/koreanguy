"""Direction-neutral EOD abnormal-activity analogue.

This is a sat10ic-owned, shadow-only approximation built from official NSE
bhavcopy fields. It is deliberately not named Reactor Scale: the proprietary
formula and order/tick footprint are unavailable, so the output must never be
presented as institutional identity, trade direction, or a risk input.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from manas_os.engine.universe_filter import is_probable_etf

from .schema import ensure_schema

FORMULA_VERSION = "sat10ic_eod_activity_v2"
# V2 is a separately versioned current-period calibration.  Fifteen exact
# score rows plus their previous-day, four-day and ten-day aggregates from the
# user-supplied 2026-07-01/10 SMF screenshots provide 60 constraints across
# 150 underlying sessions.  The two dates were also fitted in opposite
# train/test directions; the stable change versus V1 is more weight on the
# average-trade-quantity ratio at high readings.  It remains an analogue.
Q_COEFFICIENT = 1.165335
D_COEFFICIENT = 1.04631
INTERACTION_COEFFICIENT = 1.152161
INTERACTION_EXPONENT = 0.84
INTERCEPT = -0.213928
SOURCE_NOTE = (
    "Abnormal activity; direction unresolved. Uses aggregate NSE bhavcopy, "
    "not individual orders, aggressor side, or participant identity."
)
ABNORMAL_LEVEL = 3.5
EXTREME_LEVEL = 8.0


def _raw_rows(conn, as_of: str) -> dict[str, list[dict[str, Any]]]:
    session_rows = conn.execute(
        "SELECT DISTINCT trade_date FROM daily_prices "
        "WHERE source='bhavcopy' AND series='EQ' AND trade_date<=? "
        "ORDER BY trade_date DESC LIMIT 40",
        (as_of,),
    ).fetchall()
    if not session_rows:
        return {}
    cutoff = session_rows[-1]["trade_date"]
    rows = conn.execute(
        "SELECT symbol,trade_date,volume,num_trades,turnover,delivery_pct,source "
        "FROM daily_prices WHERE series='EQ' AND source='bhavcopy' "
        "AND trade_date BETWEEN ? AND ?"
        " AND volume IS NOT NULL AND volume>0 AND num_trades IS NOT NULL AND num_trades>0"
        " AND delivery_pct IS NOT NULL ORDER BY symbol,trade_date",
        (cutoff, as_of),
    ).fetchall()
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row["symbol"]].append(dict(row))
    return {symbol: symbol_rows[-20:] for symbol, symbol_rows in grouped.items()}


def _classified_stock_symbols(conn, as_of: str) -> set[str] | None:
    """Return the point-in-time classified-stock set when that snapshot exists.

    ``series='EQ'`` is not an instrument-type guarantee on NSE.  The canonical
    universe stage leaves funds/unresolved instruments without industry/sector;
    using that date-matched classification removes them without future leakage.
    Older dates with no universe snapshot fall back to the established ETF-name
    guard in ``compute`` and remain explicitly less authoritative.
    """
    snapshot = conn.execute(
        "SELECT COUNT(*) AS n FROM universe WHERE as_of_date=?",
        (as_of,),
    ).fetchone()
    if not snapshot or int(snapshot["n"] or 0) == 0:
        return None
    return {
        str(row["symbol"])
        for row in conn.execute(
            "SELECT symbol FROM universe WHERE as_of_date=? "
            "AND industry IS NOT NULL AND sector IS NOT NULL",
            (as_of,),
        )
    }


def _score(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    if len(rows) < 20:
        return None
    current = rows[-1]
    avg_qty = [float(row["volume"]) / float(row["num_trades"]) for row in rows]
    inclusive_qty_mean = sum(avg_qty) / 20.0
    prior_delivery_mean = sum(float(row["delivery_pct"]) for row in rows[:-1]) / 19.0
    if inclusive_qty_mean <= 0 or prior_delivery_mean <= 0:
        return None
    q_ratio = avg_qty[-1] / inclusive_qty_mean
    d_ratio = float(current["delivery_pct"]) / prior_delivery_mean
    # Frozen, versioned coefficients independently verified in the 2026-07-14
    # audit and current-period screenshot validation addendum.
    raw_score = (
        Q_COEFFICIENT * q_ratio
        + D_COEFFICIENT * d_ratio
        + INTERACTION_COEFFICIENT * ((q_ratio * d_ratio) ** INTERACTION_EXPONENT)
        + INTERCEPT
    )
    turnover = current.get("turnover")
    avg_trade_value = None
    if turnover is not None:
        # NSE TURNOVER_LACS is lakh rupees; expose a rupee-per-trade estimate.
        avg_trade_value = float(turnover) * 100_000.0 / float(current["num_trades"])
    return {
        "as_of_date": current["trade_date"],
        "symbol": current["symbol"],
        "score": round(raw_score, 2),
        "avg_trade_qty": round(avg_qty[-1], 4),
        "avg_trade_qty_inclusive20": round(inclusive_qty_mean, 4),
        "avg_trade_qty_ratio20": round(q_ratio, 6),
        "avg_trade_value": round(avg_trade_value, 2) if avg_trade_value is not None else None,
        "delivery_pct": round(float(current["delivery_pct"]), 4),
        "delivery_pct_prior19": round(prior_delivery_mean, 4),
        "delivery_ratio19": round(d_ratio, 6),
        "source": current.get("source") or "unknown",
    }


def compute(conn, as_of: str) -> list[dict[str, Any]]:
    """Compute and persist the latest causal cross-section on or before as_of."""
    ensure_schema(conn)
    candidates: list[dict[str, Any]] = []
    classified_stocks = _classified_stock_symbols(conn, as_of)
    for symbol, rows in _raw_rows(conn, as_of).items():
        # NSE's EQ series also contains ETF and index-fund units. This powers a
        # Stocks view, so reuse the desk's canonical cheap ETF guard rather than
        # letting fund-unit trade-size spikes dominate stock rankings.
        if is_probable_etf(symbol) or (
            classified_stocks is not None and symbol not in classified_stocks
        ):
            continue
        item = _score(rows)
        # A cross-section must not silently mix suspended/stale symbols from
        # older sessions into the requested date's percentile distribution.
        if not item or item["as_of_date"] != as_of:
            continue
        item["_prior_session"] = rows[-2]["trade_date"]
        candidates.append(item)
    if not candidates:
        return []
    # The computed cross-section is authoritative for this formula/date. Clear
    # prior rows inside the caller's transaction so newly excluded instruments
    # (for example ETF units) cannot survive a recalculation as stale leaders.
    conn.execute(
        "DELETE FROM alpha_activity_signals WHERE as_of_date=? AND formula_version=?",
        (as_of, FORMULA_VERSION),
    )
    previous_rows = conn.execute(
        "SELECT signal.* FROM alpha_activity_signals signal JOIN ("
        " SELECT symbol,MAX(as_of_date) AS previous_date FROM alpha_activity_signals "
        " WHERE as_of_date<? AND formula_version=? GROUP BY symbol"
        ") previous ON previous.symbol=signal.symbol "
        "AND previous.previous_date=signal.as_of_date "
        "WHERE signal.formula_version=?",
        (as_of, FORMULA_VERSION, FORMULA_VERSION),
    ).fetchall()
    previous_by_symbol = {row["symbol"]: row for row in previous_rows}
    ordered = sorted(item["score"] for item in candidates)
    for item in candidates:
        item["percentile"] = round(
            100.0 * sum(v <= item["score"] for v in ordered) / len(ordered), 1
        )
        item["state"] = (
            "isolated_extreme"
            if item["score"] >= EXTREME_LEVEL
            else "abnormal"
            if item["score"] >= ABNORMAL_LEVEL
            else "baseline"
        )
        previous = previous_by_symbol.get(item["symbol"])
        continues_abnormal_run = bool(
            previous
            and previous["as_of_date"] == item["_prior_session"]
            and float(previous["score"] or 0) >= ABNORMAL_LEVEL
        )
        item["persistence_sessions"] = (
            (int(previous["persistence_sessions"] or 0) + 1 if continues_abnormal_run else 1)
            if item["score"] >= ABNORMAL_LEVEL
            else 0
        )
        if item["state"] == "abnormal" and item["persistence_sessions"] >= 2:
            item["state"] = "persistent_abnormal"
        item.pop("_prior_session", None)
        conn.execute(
            "INSERT INTO alpha_activity_signals ("
            "as_of_date,symbol,formula_version,score,percentile,state,persistence_sessions,"
            "avg_trade_qty,avg_trade_qty_inclusive20,avg_trade_qty_ratio20,avg_trade_value,"
            "delivery_pct,delivery_pct_prior19,delivery_ratio19,source,quality_status) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'ready') "
            "ON CONFLICT(as_of_date,symbol,formula_version) DO UPDATE SET "
            "score=excluded.score,percentile=excluded.percentile,state=excluded.state,"
            "persistence_sessions=excluded.persistence_sessions,avg_trade_qty=excluded.avg_trade_qty,"
            "avg_trade_qty_inclusive20=excluded.avg_trade_qty_inclusive20,"
            "avg_trade_qty_ratio20=excluded.avg_trade_qty_ratio20,avg_trade_value=excluded.avg_trade_value,"
            "delivery_pct=excluded.delivery_pct,delivery_pct_prior19=excluded.delivery_pct_prior19,"
            "delivery_ratio19=excluded.delivery_ratio19,source=excluded.source,quality_status='ready'",
            (
                item["as_of_date"],
                item["symbol"],
                FORMULA_VERSION,
                item["score"],
                item["percentile"],
                item["state"],
                item["persistence_sessions"],
                item["avg_trade_qty"],
                item["avg_trade_qty_inclusive20"],
                item["avg_trade_qty_ratio20"],
                item["avg_trade_value"],
                item["delivery_pct"],
                item["delivery_pct_prior19"],
                item["delivery_ratio19"],
                item["source"],
            ),
        )
    return candidates


def leaders(conn, as_of: str | None = None, limit: int = 20) -> dict[str, Any]:
    ensure_schema(conn)
    if as_of is None:
        row = conn.execute(
            "SELECT MAX(as_of_date) d FROM alpha_activity_signals WHERE formula_version=?",
            (FORMULA_VERSION,),
        ).fetchone()
        as_of = row["d"] if row else None
    if not as_of:
        return {
            "state": "warming",
            "as_of": None,
            "rows": [],
            "shadow_only": True,
            "note": SOURCE_NOTE,
        }
    rows = conn.execute(
        "SELECT * FROM alpha_activity_signals WHERE as_of_date=("
        "SELECT MAX(as_of_date) FROM alpha_activity_signals "
        "WHERE as_of_date<=? AND formula_version=?) "
        "AND formula_version=? ORDER BY score DESC,symbol LIMIT ?",
        (as_of, FORMULA_VERSION, FORMULA_VERSION, max(1, min(int(limit), 100))),
    ).fetchall()
    row_dicts = [dict(row) for row in rows]
    resolved_as_of = row_dicts[0]["as_of_date"] if row_dicts else as_of
    summary_row = conn.execute(
        "SELECT COUNT(*) AS universe,"
        " SUM(CASE WHEN score>=? THEN 1 ELSE 0 END) AS abnormal,"
        " SUM(CASE WHEN score>=? THEN 1 ELSE 0 END) AS extreme,"
        " SUM(CASE WHEN score>=? AND persistence_sessions>=2 THEN 1 ELSE 0 END) AS persistent"
        " FROM alpha_activity_signals WHERE as_of_date=? AND formula_version=?",
        (ABNORMAL_LEVEL, EXTREME_LEVEL, ABNORMAL_LEVEL, resolved_as_of, FORMULA_VERSION),
    ).fetchone()
    summary = {
        key: int(summary_row[key] or 0) for key in ("universe", "abnormal", "extreme", "persistent")
    }
    if row_dicts:
        symbols = [row["symbol"] for row in row_dicts]
        placeholders = ",".join("?" for _ in symbols)
        trail_rows = conn.execute(
            "WITH ranked AS ("
            " SELECT symbol,as_of_date,score,"
            " ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY as_of_date DESC) AS rn"
            " FROM alpha_activity_signals WHERE formula_version=? AND as_of_date<=?"
            f" AND symbol IN ({placeholders})"
            ") SELECT symbol,as_of_date,score FROM ranked WHERE rn<=10 "
            "ORDER BY symbol,as_of_date",
            (FORMULA_VERSION, row_dicts[0]["as_of_date"], *symbols),
        ).fetchall()
        trails: dict[str, list[float]] = defaultdict(list)
        for trail_row in trail_rows:
            trails[trail_row["symbol"]].append(float(trail_row["score"]))
        for row in row_dicts:
            trail = trails.get(row["symbol"], [])
            previous = trail[-2] if len(trail) >= 2 else None
            row["previous_score"] = previous
            row["score_change"] = (
                round(float(row["score"]) - previous, 2) if previous is not None else None
            )
            row["score_avg_4"] = round(sum(trail[-4:]) / len(trail[-4:]), 2) if trail else None
            row["score_avg_10"] = round(sum(trail) / len(trail), 2) if trail else None
            row["trail"] = trail
    return {
        "state": "ready" if rows else "warming",
        "as_of": resolved_as_of,
        "rows": row_dicts,
        "shadow_only": True,
        "summary": summary,
        "formula_version": FORMULA_VERSION,
        "thresholds": {"abnormal": ABNORMAL_LEVEL, "extreme": EXTREME_LEVEL},
        "note": SOURCE_NOTE,
    }


def symbol(conn, symbol_name: str, as_of: str | None = None, trail: int = 10) -> dict[str, Any]:
    ensure_schema(conn)
    params: list[Any] = [symbol_name.upper(), FORMULA_VERSION]
    where = "symbol=? AND formula_version=?"
    if as_of:
        where += " AND as_of_date<=?"
        params.append(as_of)
    params.append(max(1, min(int(trail), 30)))
    rows = conn.execute(
        f"SELECT * FROM alpha_activity_signals WHERE {where} ORDER BY as_of_date DESC LIMIT ?",
        params,
    ).fetchall()
    return {
        "state": "ready" if rows else "warming",
        "symbol": symbol_name.upper(),
        "latest": dict(rows[0]) if rows else None,
        "trail": [dict(row) for row in reversed(rows)],
        "shadow_only": True,
        "formula_version": FORMULA_VERSION,
        "note": SOURCE_NOTE,
    }
