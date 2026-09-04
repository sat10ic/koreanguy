"""Historical replay of the canonical point-in-time factor-IC contract."""
from __future__ import annotations

import math
from collections import defaultdict
from typing import Iterable

from manas_os.scanner import gates as scanner_gates

from . import factor_health
from .schema import ensure_schema


FEATURE_FACTORS = (
    (factor_health.FACTOR_ID, "momentum_percentile", factor_health.FACTOR_VERSION),
    ("momentum_zscore", "momentum_zscore", None),
    ("market_residual_5", "market_residual_5", None),
    ("market_residual_10", "market_residual_10", None),
    ("market_residual_20", "market_residual_20", None),
    ("market_residual_60", "market_residual_60", None),
    ("sector_residual_5", "sector_residual_5", None),
    ("sector_residual_10", "sector_residual_10", None),
    ("sector_residual_20", "sector_residual_20", None),
    ("sector_residual_60", "sector_residual_60", None),
)
ACTIVITY_FACTOR_ID = "activity_footprint_score"
DELIVERY_FACTOR_ID = "delivery_z"
DELIVERY_FACTOR_VERSION = "scanner_delivery_z_50_v1"


def _table_columns(conn, table: str) -> set[str]:
    if not conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone():
        return set()
    return {str(row[1]) for row in conn.execute(f"PRAGMA table_info({table})")}


def _price_panel(conn) -> tuple[dict[str, list[tuple[str, float]]], list[str]]:
    rows = conn.execute(
        "SELECT symbol,trade_date,close FROM daily_prices "
        "WHERE series='EQ' AND close IS NOT NULL ORDER BY symbol,trade_date"
    ).fetchall()
    by_symbol: dict[str, list[tuple[str, float]]] = defaultdict(list)
    sessions: set[str] = set()
    for row in rows:
        day = str(row["trade_date"])
        by_symbol[str(row["symbol"])].append((day, float(row["close"])))
        sessions.add(day)
    return dict(by_symbol), sorted(sessions)


def _feature_cross_sections(
    conn, evaluation_date: str
) -> tuple[list[tuple[str, str, list[tuple[str, float]]]], int]:
    columns = _table_columns(conn, "alpha_feature_snapshots")
    output: list[tuple[str, str, list[tuple[str, float]]]] = []
    missing = 0
    for factor_id, column, fixed_version in FEATURE_FACTORS:
        if column not in columns:
            missing += 1
            continue
        rows = conn.execute(
            f"SELECT symbol,feature_version,{column} AS factor_value "
            "FROM alpha_feature_snapshots WHERE as_of_date=? "
            f"AND {column} IS NOT NULL ORDER BY feature_version,symbol",
            (evaluation_date,),
        ).fetchall()
        grouped: dict[str, list[tuple[str, float]]] = defaultdict(list)
        for row in rows:
            value = float(row["factor_value"])
            if math.isfinite(value):
                version = fixed_version or str(row["feature_version"])
                grouped[version].append((str(row["symbol"]), value))
        if not grouped:
            missing += 1
            continue
        output.extend((factor_id, version, values) for version, values in grouped.items())
    return output, missing


def _activity_cross_sections(
    conn, evaluation_date: str
) -> tuple[list[tuple[str, str, list[tuple[str, float]]]], int]:
    columns = _table_columns(conn, "alpha_activity_signals")
    if not {"symbol", "formula_version", "score", "as_of_date"}.issubset(columns):
        return [], 1
    rows = conn.execute(
        "SELECT symbol,formula_version,score FROM alpha_activity_signals "
        "WHERE as_of_date=? AND score IS NOT NULL ORDER BY formula_version,symbol",
        (evaluation_date,),
    ).fetchall()
    grouped: dict[str, list[tuple[str, float]]] = defaultdict(list)
    for row in rows:
        value = float(row["score"])
        if math.isfinite(value):
            grouped[str(row["formula_version"])].append((str(row["symbol"]), value))
    if not grouped:
        return [], 1
    return [
        (ACTIVITY_FACTOR_ID, version, values) for version, values in grouped.items()
    ], 0


def _delivery_cross_section(
    conn, evaluation_date: str
) -> tuple[list[tuple[str, str, list[tuple[str, float]]]], int]:
    columns = _table_columns(conn, "daily_prices")
    if "delivery_pct" not in columns:
        return [], 1
    rows = conn.execute(
        "SELECT symbol,trade_date,delivery_pct FROM daily_prices WHERE series='EQ' "
        "AND trade_date<=? AND delivery_pct IS NOT NULL ORDER BY symbol,trade_date",
        (evaluation_date,),
    ).fetchall()
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        grouped[str(row["symbol"])].append(dict(row))
    zscores: list[tuple[str, float]] = []
    for symbol, bars in grouped.items():
        if str(bars[-1]["trade_date"]) != evaluation_date:
            continue
        value = scanner_gates.delivery_z(bars)
        if value is not None and math.isfinite(value):
            zscores.append((symbol, float(value)))
    if len(zscores) < 3:
        return [], 1
    return [(DELIVERY_FACTOR_ID, DELIVERY_FACTOR_VERSION, zscores)], 0


def _regime_on(conn, evaluation_date: str) -> str | None:
    columns = _table_columns(conn, "regime_snapshots")
    if not {"snapshot_date", "market_mode"}.issubset(columns):
        return None
    row = conn.execute(
        "SELECT market_mode FROM regime_snapshots WHERE snapshot_date<=? "
        "ORDER BY snapshot_date DESC LIMIT 1",
        (evaluation_date,),
    ).fetchone()
    return str(row["market_mode"]) if row and row["market_mode"] is not None else None


def _forward_cross_section(
    values: Iterable[tuple[str, float]],
    evaluation_date: str,
    horizon: int,
    prices: dict[str, list[tuple[str, float]]],
    lookups: dict[str, dict[str, int]],
) -> tuple[list[float], list[float], list[str]]:
    factors: list[float] = []
    returns: list[float] = []
    outcome_dates: list[str] = []
    for symbol, factor_value in values:
        series = prices.get(symbol)
        index = lookups.get(symbol, {}).get(evaluation_date)
        if not series or index is None or index + horizon >= len(series):
            continue
        start = series[index][1]
        outcome_date, end = series[index + horizon]
        if start <= 0 or outcome_date <= evaluation_date:
            continue
        forward_return = end / start - 1.0
        if not math.isfinite(forward_return):
            continue
        factors.append(factor_value)
        returns.append(forward_return)
        outcome_dates.append(outcome_date)
    return factors, returns, outcome_dates


def backfill_factor_evaluations(
    conn,
    start_date: str,
    end_date: str,
    horizons: tuple[int, ...] = (5, 10, 20),
) -> dict[str, int | str]:
    """Replay causal factor cross-sections and their strictly later returns."""
    if start_date > end_date:
        raise ValueError("start_date must be on or before end_date")
    normalized_horizons = tuple(dict.fromkeys(int(value) for value in horizons))
    if not normalized_horizons:
        raise ValueError("at least one horizon is required")
    unsupported = set(normalized_horizons) - set(factor_health.HORIZONS)
    if unsupported:
        raise ValueError(f"unsupported horizons: {sorted(unsupported)}")

    ensure_schema(conn)
    prices, all_sessions = _price_panel(conn)
    evaluation_dates = [day for day in all_sessions if start_date <= day <= end_date]
    session_index = {day: index for index, day in enumerate(all_sessions)}
    lookups = {
        symbol: {day: index for index, (day, _close) in enumerate(series)}
        for symbol, series in prices.items()
    }
    written = 0
    dates_processed = 0
    dates_skipped_future = 0
    factors_skipped = 0
    written_factor_keys: set[tuple[str, str]] = set()

    for evaluation_date in evaluation_dates:
        index = session_index[evaluation_date]
        available_horizons = tuple(
            horizon
            for horizon in normalized_horizons
            if index + horizon < len(all_sessions)
        )
        if not available_horizons:
            dates_skipped_future += 1
            print(f"alpha-backfill {evaluation_date}: skipped - insufficient future data")
            continue

        feature_sections, feature_missing = _feature_cross_sections(conn, evaluation_date)
        activity_sections, activity_missing = _activity_cross_sections(conn, evaluation_date)
        delivery_sections, delivery_missing = _delivery_cross_section(conn, evaluation_date)
        cross_sections = feature_sections + activity_sections + delivery_sections
        date_missing = feature_missing + activity_missing + delivery_missing
        date_written = 0
        regime = _regime_on(conn, evaluation_date)
        for factor_id, factor_version, values in cross_sections:
            for horizon in available_horizons:
                factors, returns, outcome_dates = _forward_cross_section(
                    values,
                    evaluation_date,
                    horizon,
                    prices,
                    lookups,
                )
                ic, rank_ic = factor_health.information_coefficients(factors, returns)
                if ic is None or rank_ic is None:
                    date_missing += 1
                    continue
                factor_health.write_evaluation(
                    conn,
                    factor_id=factor_id,
                    factor_version=factor_version,
                    evaluation_date=evaluation_date,
                    horizon_sessions=horizon,
                    pearson_ic=ic,
                    spearman_rank_ic=rank_ic,
                    universe_denominator=len(factors),
                    regime=regime,
                    future_available_at=max(outcome_dates),
                )
                written_factor_keys.add((factor_id, factor_version))
                written += 1
                date_written += 1
        dates_processed += 1
        factors_skipped += date_missing
        print(
            f"alpha-backfill {evaluation_date}: evaluations={date_written} "
            f"factors_skipped_missing_inputs={date_missing}"
        )

    if written_factor_keys:
        factor_health.refresh_factor_health(conn, factor_keys=written_factor_keys)
    conn.commit()
    return {
        "status": "ok",
        "dates_considered": len(evaluation_dates),
        "dates_processed": dates_processed,
        "dates_skipped_insufficient_future": dates_skipped_future,
        "factors_skipped_missing_inputs": factors_skipped,
        "evaluations_written": written,
    }
