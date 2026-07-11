"""Point-in-time daily alpha features derived only from bars known by ``as_of``."""
from __future__ import annotations

import json
import math
from collections import defaultdict

from .schema import ensure_schema

HORIZONS = (5, 10, 20, 60)


def _return(closes: list[float], horizon: int) -> float | None:
    if len(closes) <= horizon or closes[-horizon - 1] <= 0:
        return None
    return closes[-1] / closes[-horizon - 1] - 1.0


def _mean(values: list[float | None]) -> float | None:
    clean = [v for v in values if v is not None]
    return sum(clean) / len(clean) if clean else None


def compute_daily_features(
    conn, as_of_date: str, *, feature_version: str = "daily-v1", universe: str = "NSE_EQ"
) -> list[dict]:
    """Compute and persist a causal cross-section ending at ``as_of_date``.

    The market proxy is the equal-weight return of the eligible cross-section.
    Sector residuals are emitted only when point-in-time ``universe`` sector data
    exists; otherwise they remain null rather than being guessed.
    """
    ensure_schema(conn)
    rows = conn.execute(
        "SELECT symbol, trade_date, close FROM daily_prices "
        "WHERE series='EQ' AND trade_date <= ? AND close IS NOT NULL "
        "ORDER BY symbol, trade_date", (as_of_date,),
    ).fetchall()
    by_symbol: dict[str, list[tuple[str, float]]] = defaultdict(list)
    for row in rows:
        by_symbol[row["symbol"]].append((row["trade_date"], float(row["close"])))
    if not by_symbol:
        return []
    source_max = max(points[-1][0] for points in by_symbol.values())
    sectors: dict[str, str] = {}
    eligible_symbols: set[str] | None = None
    if conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='universe'").fetchone():
        universe_rows = list(conn.execute(
            "SELECT u.symbol,u.sector,u.is_tradeable FROM universe u JOIN (SELECT symbol,MAX(as_of_date) d FROM universe "
            "WHERE as_of_date<=? GROUP BY symbol) x ON x.symbol=u.symbol AND x.d=u.as_of_date",
            (as_of_date,),
        ))
        sectors = {r["symbol"]: r["sector"] for r in universe_rows if r["sector"]}
        if universe_rows:
            eligible_symbols = {r["symbol"] for r in universe_rows if int(r["is_tradeable"] or 0) == 1}
    if eligible_symbols is None:
        # Reuse the canonical liquidity/ETF universe gate when the persisted
        # point-in-time universe table has not been built yet. This is universe
        # eligibility only; it does not import setup gates or change risk law.
        try:
            from manas_os.engine.universe_filter import GateConfig, filter_universe

            eligible_symbols = set(filter_universe(
                conn, as_of_date,
                cfg=GateConfig(min_price=30.0, min_avg_turnover_cr=5.0, exclude_etf=True),
            )["tradeable"])
        except Exception:  # noqa: BLE001 - honest fallback for minimal fixtures.
            eligible_symbols = None
    raw: list[dict] = []
    for symbol, points in by_symbol.items():
        if eligible_symbols is not None and symbol not in eligible_symbols:
            continue
        dates = [p[0] for p in points]
        closes = [p[1] for p in points]
        if dates[-1] != source_max:
            continue  # excludes stale/suspended names from today's denominator
        returns = {h: _return(closes, h) for h in HORIZONS}
        raw.append({"symbol": symbol, "sector": sectors.get(symbol), "returns": returns})
    denominator = len(raw)
    market = {h: _mean([r["returns"][h] for r in raw]) for h in HORIZONS}
    sector_buckets: dict[str, list[dict]] = defaultdict(list)
    for row in raw:
        if row["sector"]:
            sector_buckets[row["sector"]].append(row)
    sector_means = {
        sector: {h: _mean([r["returns"][h] for r in group]) for h in HORIZONS}
        for sector, group in sector_buckets.items()
    }
    scores = [r["returns"][20] for r in raw if r["returns"][20] is not None]
    mu = _mean(scores)
    sigma = math.sqrt(sum((v - mu) ** 2 for v in scores) / len(scores)) if scores and mu is not None else 0.0
    ordered = sorted(scores)
    output: list[dict] = []
    # The snapshot is a complete cross-section for this version/date. Remove
    # rows that belonged to an older eligibility denominator before rebuilding.
    conn.execute(
        "DELETE FROM alpha_feature_snapshots WHERE as_of_date=? AND feature_version=?",
        (as_of_date, feature_version),
    )
    for row in raw:
        r20 = row["returns"][20]
        z = ((r20 - mu) / sigma) if r20 is not None and mu is not None and sigma > 0 else None
        pct = None
        if r20 is not None and ordered:
            below = sum(v < r20 for v in ordered)
            equal = sum(v == r20 for v in ordered)
            pct = (below + 0.5 * equal) / len(ordered) * 100.0
        market_res = {h: (row["returns"][h] - market[h]) if row["returns"][h] is not None and market[h] is not None else None for h in HORIZONS}
        sm = sector_means.get(row["sector"], {})
        sector_res = {h: (row["returns"][h] - sm[h]) if row["returns"][h] is not None and sm.get(h) is not None else None for h in HORIZONS}
        payload = {"returns": row["returns"], "market_residual": market_res, "sector_residual": sector_res,
                   "momentum_zscore": z, "momentum_percentile": pct}
        vals = [as_of_date, row["symbol"], feature_version, row["sector"], universe, source_max,
                denominator, 0]
        vals += [row["returns"][h] for h in HORIZONS]
        vals += [market_res[h] for h in HORIZONS]
        vals += [sector_res[h] for h in HORIZONS]
        vals += [z, pct, json.dumps(payload, sort_keys=True)]
        conn.execute("""INSERT INTO alpha_feature_snapshots (
          as_of_date,symbol,feature_version,sector,universe,source_max_date,source_denominator,freshness_sessions,
          ret_5,ret_10,ret_20,ret_60,market_residual_5,market_residual_10,market_residual_20,market_residual_60,
          sector_residual_5,sector_residual_10,sector_residual_20,sector_residual_60,momentum_zscore,momentum_percentile,features_json)
          VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
          ON CONFLICT(as_of_date,symbol,feature_version) DO UPDATE SET
          sector=excluded.sector,universe=excluded.universe,source_max_date=excluded.source_max_date,
          source_denominator=excluded.source_denominator,freshness_sessions=excluded.freshness_sessions,
          ret_5=excluded.ret_5,ret_10=excluded.ret_10,ret_20=excluded.ret_20,ret_60=excluded.ret_60,
          market_residual_5=excluded.market_residual_5,market_residual_10=excluded.market_residual_10,
          market_residual_20=excluded.market_residual_20,market_residual_60=excluded.market_residual_60,
          sector_residual_5=excluded.sector_residual_5,sector_residual_10=excluded.sector_residual_10,
          sector_residual_20=excluded.sector_residual_20,sector_residual_60=excluded.sector_residual_60,
          momentum_zscore=excluded.momentum_zscore,momentum_percentile=excluded.momentum_percentile,
          features_json=excluded.features_json""", vals)
        output.append({"symbol": row["symbol"], **payload, "source_denominator": denominator, "source_max_date": source_max})
    conn.commit()
    return output
