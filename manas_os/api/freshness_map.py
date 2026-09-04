"""One honest source-of-truth for data coverage and producing-stage health."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Source:
    key: str
    label: str
    table: str
    date_column: str
    stage: str
    chartsmaze: bool = False
    where: str | None = None


SOURCES = (
    Source("prices", "NSE prices + delivery", "daily_prices", "trade_date", "ingest_bhavcopy"),
    Source("universe", "Tradeable universe", "universe", "as_of_date", "classify_universe"),
    Source("breadth", "Market breadth", "breadth_daily", "trade_date", "breadth_counts"),
    Source("regime", "Market regime", "regime_snapshots", "snapshot_date", "regime_snapshot"),
    Source("scans", "Setup candidates", "scan_candidates", "scan_date", "scan_candidates"),
    Source("features", "Technical features", "features_daily", "trade_date", "indicators"),
    Source("alpha", "Alpha research", "alpha_feature_snapshots", "as_of_date", "alpha_features"),
    Source("fundamentals", "Quarterly fundamentals", "symbol_fundamentals", "as_of", "ingest_fundamentals"),
    Source("flows", "FII / DII flows", "fii_dii_daily", "trade_date", "ingest_fii_dii"),
    Source("screeners", "ChartsMaze screeners", "screener_hits", "trade_date", "ingest_chartsmaze_scanners", True),
    Source("disclosures", "ChartsMaze disclosures", "disclosures", "trade_date", "ingest_disclosures", True,
           "kind NOT IN ('nse_bulk_deal','nse_block_deal')"),
    Source("deals", "NSE bulk / block deals", "disclosures", "trade_date", "ingest_nse_deals", False,
           "kind IN ('nse_bulk_deal','nse_block_deal')"),
    Source("sectors", "ChartsMaze sector RS", "sector_metrics", "snapshot_date", "ingest_chartsmaze", True),
    Source("industries", "ChartsMaze industries", "industry_metrics", "snapshot_date", "ingest_chartsmaze", True),
    Source("debate", "Agent council", "agent_verdicts", "scan_date", "agents_debate"),
)


def _max_date(conn, source: Source) -> str | None:
    try:
        where = f" WHERE {source.where}" if source.where else ""
        row = conn.execute(f"SELECT MAX({source.date_column}) FROM {source.table}{where}").fetchone()
        return row[0] if row and row[0] else None
    except Exception:
        return None


def _latest_stage(conn, stage: str) -> dict[str, Any] | None:
    try:
        row = conn.execute(
            "SELECT run_date,status,detail,ran_at FROM pipeline_runs "
            "WHERE stage=? ORDER BY run_id DESC LIMIT 1", (stage,),
        ).fetchone()
        if row:
            return dict(row)
        step = conn.execute(
            "SELECT j.run_date,s.status,COALESCE(s.error,s.detail) AS detail,s.finished_at AS ran_at "
            "FROM job_steps s JOIN jobs j ON j.job_id=s.job_id WHERE s.name=? "
            "ORDER BY s.step_id DESC LIMIT 1", (stage,),
        ).fetchone()
        return dict(step) if step else None
    except Exception:
        return None


def _session_lag(conn, until: str | None, latest_price: str | None) -> int | None:
    if not latest_price or not until:
        return None
    if until >= latest_price:
        return 0
    try:
        return int(conn.execute(
            "SELECT COUNT(DISTINCT trade_date) FROM daily_prices "
            "WHERE series='EQ' AND trade_date>? AND trade_date<=?", (until, latest_price),
        ).fetchone()[0])
    except Exception:
        return None


def _chartsmaze_fetch_state(conn) -> dict[str, Any] | None:
    """Latest fetch_chartsmaze outcome, classified -- best-effort, never raises.

    Import is local to avoid a module-load-time dependency from api/ onto
    sources/ (sources/ never imports api/, so this is one-directional and
    safe, but keeping it lazy matches how the rest of this file treats
    optional lookups).
    """
    try:
        from manas_os.sources import chartsmaze
        return chartsmaze.fetch_failure_reason(conn)
    except Exception:
        return None


def _action(source: Source, until: str | None, status: str | None, detail: str | None,
            auth_expired: bool = False) -> str:
    if auth_expired:
        return (
            "ChartsMaze login expired — this source cannot update until you log back in. "
            "Run: cd chartsmaze_extractor && python login.py (completes the OTP flow)."
        )
    if source.chartsmaze and detail and (
        "chartsmaze root missing" in detail.lower() or "no chartsmaze dump for" in detail.lower()
    ):
        return (
            "The ChartsMaze scraper hasn't produced files for these dates. Run the ChartsMaze "
            f"extractor (login-gated) — screeners/sector-RS stay at {until or 'no date'} until it does."
        )
    if status in {"skip", "skipped", "fail", "failed", "error"}:
        return f"Re-run {source.stage} after fixing the reported source error."
    return "No action needed." if until else f"Run the EOD update stage {source.stage}."


def coverage(conn) -> dict[str, Any]:
    price_source = SOURCES[0]
    latest_price = _max_date(conn, price_source)
    # One lookup, reused across every ChartsMaze-tagged source below -- the
    # auth-expired state is a property of the scraper login, not of any one
    # downstream table, so it must not be re-derived per source.
    fetch_state = _chartsmaze_fetch_state(conn)
    fetch_auth_expired = bool(fetch_state and fetch_state.get("reason_code") == "auth_expired")
    rows = []
    for source in SOURCES:
        until = _max_date(conn, source)
        stage = _latest_stage(conn, source.stage) or {}
        status = stage.get("status")
        detail = stage.get("detail")
        lag = _session_lag(conn, until, latest_price)
        auth_expired = source.chartsmaze and fetch_auth_expired
        failed = status in {"skip", "skipped", "fail", "failed", "error"}
        color = "red" if auth_expired or failed or lag is None or lag >= 2 else ("amber" if lag == 1 else "green")
        rows.append({
            "key": source.key, "label": source.label, "until": until,
            "lag_sessions": lag, "health": color, "stage": source.stage,
            "last_status": status or "unknown", "reason": detail,
            "diagnostic": f"{source.stage}: {status or 'unknown'} — {detail}" if detail else None,
            "last_run_at": stage.get("ran_at"),
            "what_to_do": _action(source, until, status, detail, auth_expired),
            "affected": source.chartsmaze,
            "auth_expired": auth_expired,
        })
    return {"as_of_query": latest_price, "latest_price_date": latest_price, "sources": rows}
