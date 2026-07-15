"""Point-in-time IC/Rank-IC evaluation for the first India-native factor.

The initial family is the already-persisted 20-session residual-momentum rank.
Evaluation only occurs once the complete forward 5/10/20-session outcome exists.
"""
from __future__ import annotations

import math
from collections import defaultdict
from typing import Iterable

from .schema import ensure_schema


FACTOR_ID = "residual_momentum_20"
FACTOR_VERSION = "alpha_features_v1"
DEFINITION_VERSION = "sat10ic_ic_v1"
HORIZONS = (5, 10, 20)


def _pearson(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) < 3 or len(xs) != len(ys):
        return None
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    den = math.sqrt(sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys))
    return None if den == 0 else num / den


def _ranks(values: list[float]) -> list[float]:
    ordered = sorted(enumerate(values), key=lambda item: item[1])
    out = [0.0] * len(values)
    index = 0
    while index < len(ordered):
        end = index + 1
        while end < len(ordered) and ordered[end][1] == ordered[index][1]:
            end += 1
        rank = (index + 1 + end) / 2.0
        for original, _value in ordered[index:end]:
            out[original] = rank
        index = end
    return out


def evaluate(conn, as_of: str) -> int:
    ensure_schema(conn)
    snapshots = conn.execute(
        "SELECT as_of_date,symbol,momentum_percentile FROM alpha_feature_snapshots "
        "WHERE as_of_date<=? AND momentum_percentile IS NOT NULL ORDER BY as_of_date,symbol",
        (as_of,),
    ).fetchall()
    if not snapshots:
        return 0
    symbols = sorted({row["symbol"] for row in snapshots})
    placeholders = ",".join("?" for _ in symbols)
    prices = conn.execute(
        f"SELECT symbol,trade_date,close FROM daily_prices WHERE series='EQ' "
        f"AND symbol IN ({placeholders}) AND trade_date<=? AND close IS NOT NULL "
        "ORDER BY symbol,trade_date",
        (*symbols, as_of),
    ).fetchall()
    by_symbol: dict[str, list[tuple[str, float]]] = defaultdict(list)
    for row in prices:
        by_symbol[row["symbol"]].append((row["trade_date"], float(row["close"])))
    lookup = {symbol: {day: index for index, (day, _close) in enumerate(series)} for symbol, series in by_symbol.items()}
    by_date: dict[str, list] = defaultdict(list)
    for row in snapshots:
        by_date[row["as_of_date"]].append(row)

    written = 0
    for evaluation_date, rows in by_date.items():
        for horizon in HORIZONS:
            factors: list[float] = []
            returns: list[float] = []
            outcome_dates: list[str] = []
            for row in rows:
                series = by_symbol.get(row["symbol"])
                index = lookup.get(row["symbol"], {}).get(evaluation_date)
                if not series or index is None or index + horizon >= len(series):
                    continue
                start = series[index][1]
                end_date, end = series[index + horizon]
                if start <= 0:
                    continue
                factors.append(float(row["momentum_percentile"]))
                returns.append(end / start - 1.0)
                outcome_dates.append(end_date)
            ic = _pearson(factors, returns)
            rank_ic = _pearson(_ranks(factors), _ranks(returns)) if factors else None
            if ic is None or rank_ic is None:
                continue
            future_available_at = max(outcome_dates)
            regime = conn.execute(
                "SELECT market_mode FROM regime_snapshots WHERE snapshot_date<=? "
                "ORDER BY snapshot_date DESC LIMIT 1", (evaluation_date,),
            ).fetchone()
            conn.execute(
                "INSERT INTO alpha_factor_evaluations (factor_id,factor_version,evaluation_date,"
                "horizon_sessions,pearson_ic,spearman_rank_ic,universe_denominator,regime,"
                "future_available_at,definition_version) VALUES (?,?,?,?,?,?,?,?,?,?) "
                "ON CONFLICT(factor_id,factor_version,evaluation_date,horizon_sessions) DO UPDATE SET "
                "pearson_ic=excluded.pearson_ic,spearman_rank_ic=excluded.spearman_rank_ic,"
                "universe_denominator=excluded.universe_denominator,regime=excluded.regime,"
                "future_available_at=excluded.future_available_at,definition_version=excluded.definition_version",
                (FACTOR_ID, FACTOR_VERSION, evaluation_date, horizon, ic, rank_ic, len(factors),
                 regime["market_mode"] if regime else None, future_available_at, DEFINITION_VERSION),
            )
            written += 1
    _refresh_health(conn)
    return written


def _refresh_health(conn) -> None:
    for horizon in HORIZONS:
        rows = conn.execute(
            "SELECT evaluation_date,pearson_ic,spearman_rank_ic,universe_denominator "
            "FROM alpha_factor_evaluations WHERE factor_id=? AND factor_version=? "
            "AND horizon_sessions=? ORDER BY evaluation_date",
            (FACTOR_ID, FACTOR_VERSION, horizon),
        ).fetchall()
        if not rows:
            continue
        ics = [float(row["pearson_ic"]) for row in rows]
        rank_ics = [float(row["spearman_rank_ic"]) for row in rows]
        mean_ic = sum(ics) / len(ics)
        variance = sum((value - mean_ic) ** 2 for value in ics) / len(ics)
        std = math.sqrt(variance)
        conn.execute(
            "INSERT INTO alpha_factor_health (factor_id,factor_version,horizon_sessions,mean_ic,ic_std,"
            "icir_sat10ic,mean_rank_ic,sign_consistency,evaluation_count,sample_size,last_evaluation_date,"
            "definition_version) VALUES (?,?,?,?,?,?,?,?,?,?,?,?) "
            "ON CONFLICT(factor_id,factor_version,horizon_sessions) DO UPDATE SET "
            "mean_ic=excluded.mean_ic,ic_std=excluded.ic_std,icir_sat10ic=excluded.icir_sat10ic,"
            "mean_rank_ic=excluded.mean_rank_ic,sign_consistency=excluded.sign_consistency,"
            "evaluation_count=excluded.evaluation_count,sample_size=excluded.sample_size,"
            "last_evaluation_date=excluded.last_evaluation_date,definition_version=excluded.definition_version,"
            "updated_at=datetime('now')",
            (FACTOR_ID, FACTOR_VERSION, horizon, mean_ic, std, None if std == 0 else mean_ic / std,
             sum(rank_ics) / len(rank_ics), sum(1 for value in ics if value > 0) / len(ics), len(rows),
             sum(int(row["universe_denominator"]) for row in rows), rows[-1]["evaluation_date"], DEFINITION_VERSION),
        )


def health(conn) -> dict:
    ensure_schema(conn)
    rows = [dict(row) for row in conn.execute(
        "SELECT * FROM alpha_factor_health ORDER BY factor_id,horizon_sessions"
    ).fetchall()]
    return {"state": "ready" if rows else "warming", "rows": rows, "shadow_only": True,
            "note": "IC relates a point-in-time rank to later returns; it is research health, not a stock forecast."}
