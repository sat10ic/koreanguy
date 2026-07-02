"""SwingEdge Lite — Dashboard Backend (FastAPI).

Reads pipeline outputs (SQLite + CSV + JSON) and exposes them to the React
dashboard. Also exposes endpoints to trigger the daily pipeline run.
"""
from __future__ import annotations

import json
import math
import os
import sys
import threading
from pathlib import Path
from typing import Any
from datetime import datetime

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, Body
from fastapi.middleware.cors import CORSMiddleware

# --- Load env --------------------------------------------------------------
# Default ROOT to the repo root (parent of this backend/ dir) so the server
# works locally without setting SWINGEDGE_ROOT. The /app container path was
# a hardcoded default that broke every local invocation — the backend would
# look in /app/output (nonexistent) and serve empty data silently. Container
# deployments still override via SWINGEDGE_ROOT=/app.
load_dotenv(Path(__file__).parent / ".env")
_DEFAULT_ROOT = Path(__file__).resolve().parent.parent
ROOT = Path(os.environ.get("SWINGEDGE_ROOT") or _DEFAULT_ROOT)

# Make the existing scripts importable
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from scripts import _db, _grade_helper, _config  # noqa: E402
from scripts import run_pipeline  # noqa: E402


# --- Helpers ---------------------------------------------------------------
OUTPUT_DIR = ROOT / "output"
DATA_DIR = ROOT / "data"

PIPELINE_STATUS: dict[str, Any] = {
    "running": False,
    "started_at": None,
    "finished_at": None,
    "stages": [],
    "error": None,
    "current_stage": None,
    "progress": {"done": 0, "total": 0, "symbol": "", "detail": ""},
}
PIPELINE_LOCK = threading.Lock()


def _read_json(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def _read_csv_records(path: Path) -> list[dict]:
    if not path.exists():
        return []
    try:
        df = pd.read_csv(path)
        df = df.where(pd.notnull(df), None)
        return df.to_dict(orient="records")
    except Exception:
        return []


def _safe_float(x):
    try:
        if x is None or pd.isna(x):
            return None
        f = float(x)
        if math.isinf(f):
            return None
        return f
    except Exception:
        return None


def _safe_int(x):
    try:
        if x is None or pd.isna(x):
            return None
        return int(x)
    except Exception:
        return None


def _scrub(df: pd.DataFrame) -> pd.DataFrame:
    """Coerce NaN AND ±Inf to None reliably across mixed-dtype frames."""
    if df is None or df.empty:
        return df
    # First, replace ±Inf with NaN so subsequent .where() catches them
    df = df.replace([np.inf, -np.inf], np.nan)
    return df.astype(object).where(pd.notnull(df), None)


def _scrub_rows(rows: list[dict]) -> list[dict]:
    """Final per-row scrub: replace NaN AND Inf floats with None."""
    for r in rows:
        for k, v in list(r.items()):
            if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
                r[k] = None
    return rows


# --- FastAPI ---------------------------------------------------------------
app = FastAPI(title="SwingEdge Lite Dashboard API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "ts": datetime.utcnow().isoformat(),
        "root": str(ROOT),
        "data_dir_exists": DATA_DIR.exists(),
        "output_dir_exists": OUTPUT_DIR.exists(),
    }


# ---- Regime ---------------------------------------------------------------
@app.get("/api/regime")
def get_regime():
    data = _read_json(OUTPUT_DIR / "regime_today.json")
    if not data:
        return {"available": False}
    return {"available": True, **data}


# ---- Universe summary -----------------------------------------------------
@app.get("/api/universe/summary")
def get_universe_summary():
    """Return bullish/bearish split, purple-dot count, sector breakdown."""
    screen_path = OUTPUT_DIR / "screen_today.csv"
    if not screen_path.exists():
        return {"available": False}

    df = pd.read_csv(screen_path)
    bullish = int((df["bucket"] == "Bullish").sum())
    bearish = int((df["bucket"] == "Bearish").sum())
    pd_today = int(df.get("purple_dot", pd.Series([0])).sum())
    extended_yellow = int(df.get("extended_yellow", pd.Series([0])).sum())
    extended_red = int(df.get("extended_red", pd.Series([0])).sum())
    setups = int(df.get("setup_pass", pd.Series([0])).sum())

    # Sector/Industry/Basic-Industry breakdowns — join with universe.csv
    universe = pd.read_csv(ROOT / "universe.csv").drop_duplicates(subset=["symbol"])
    keep_cols = [c for c in ["symbol", "sector", "industry", "basic_industry", "name"] if c in universe.columns]
    merged = df.merge(universe[keep_cols], on="symbol", how="left")

    def _breakdown(group_col: str) -> list[dict]:
        if group_col not in merged.columns:
            return []
        out = []
        for k, g in merged.groupby(group_col):
            out.append({
                group_col: k,
                "count": int(len(g)),
                "bullish": int((g["bucket"] == "Bullish").sum()),
                "purple_dots": int(g.get("purple_dot", pd.Series([0])).sum()),
                "avg_rs_score": _safe_float(g["rs_score"].mean()) if "rs_score" in g else None,
            })
        out.sort(key=lambda r: r["count"], reverse=True)
        return out

    sector_stats = _breakdown("sector")
    industry_stats = _breakdown("industry")
    basic_industry_stats = _breakdown("basic_industry")

    return {
        "available": True,
        "total": int(len(df)),
        "bullish": bullish,
        "bearish": bearish,
        "purple_dots_today": pd_today,
        "extended_yellow": extended_yellow,
        "extended_red": extended_red,
        "setup_pass_count": setups,
        "sectors": sector_stats,
        "industries": industry_stats,
        "basic_industries": basic_industry_stats,
    }


# ---- Screen (full graded universe) ----------------------------------------
@app.get("/api/screen")
def get_screen(
    grade: str | None = None,
    bucket: str | None = None,
    setup_only: bool = False,
    purple_dot_only: bool = False,
    extended_only: bool = False,
    watchlist_only: bool = False,
    sector: str | None = None,
    industry: str | None = None,
    basic_industry: str | None = None,
    sort_by: str = "rs_score",
    sort_desc: bool = True,
    limit: int = 600,
):
    path = OUTPUT_DIR / "screen_today.csv"
    if not path.exists():
        return {"available": False, "rows": []}
    df = pd.read_csv(path)

    universe = pd.read_csv(ROOT / "universe.csv").drop_duplicates(subset=["symbol"])
    keep = [c for c in ["symbol", "name", "sector", "industry", "basic_industry"] if c in universe.columns]
    df = df.merge(universe[keep], on="symbol", how="left")

    if grade:
        df = df[df["grade"] == grade]
    if bucket:
        df = df[df["bucket"] == bucket]
    if setup_only:
        df = df[df["setup_pass"] == 1]
    if purple_dot_only:
        df = df[df["purple_dot"] == 1]
    if extended_only:
        # Extended = either yellow (5×ATR from sma50) or red (7×ATR)
        ext_y = df.get("extended_yellow", pd.Series([0] * len(df))).fillna(0).astype(int)
        ext_r = df.get("extended_red", pd.Series([0] * len(df))).fillna(0).astype(int)
        df = df[(ext_y == 1) | (ext_r == 1)]
    if watchlist_only:
        df = df[df["watchlist_member"] == 1]
    if sector and "sector" in df.columns:
        df = df[df["sector"] == sector]
    if industry and "industry" in df.columns:
        df = df[df["industry"] == industry]
    if basic_industry and "basic_industry" in df.columns:
        df = df[df["basic_industry"] == basic_industry]

    if sort_by in df.columns:
        df = df.sort_values(sort_by, ascending=not sort_desc, na_position="last")

    df = df.head(limit)
    df = _scrub(df)
    rows = _scrub_rows(df.to_dict(orient="records"))
    return {"available": True, "rows": rows}


# ---- RS grid (compact view for heatmap) -----------------------------------
@app.get("/api/rs_grid")
def get_rs_grid():
    path = OUTPUT_DIR / "screen_today.csv"
    if not path.exists():
        return {"available": False, "grades": {}}
    df = pd.read_csv(path)
    universe = pd.read_csv(ROOT / "universe.csv").drop_duplicates(subset=["symbol"])
    df = df.merge(universe[["symbol", "sector"]], on="symbol", how="left")
    # Replace ±Inf with NaN, then NaN with None at top level so string cells
    # (sector / bucket) don't leak NaN floats into the JSON response.
    df = df.replace([np.inf, -np.inf], np.nan)
    df = df.astype(object).where(pd.notnull(df), None)

    grade_order = ["A+", "A", "A-", "B+", "B", "B-", "C+", "C", "C-",
                   "D+", "D", "D-", "E+", "E", "F", "G"]
    out = {g: [] for g in grade_order}
    for _, r in df.iterrows():
        g = r.get("grade") or "G"
        if g not in out:
            out[g] = []
        sector = r.get("sector")
        bucket = r.get("bucket")
        out[g].append({
            "symbol": r["symbol"],
            "sector": None if (isinstance(sector, float) and pd.isna(sector)) else sector,
            "rs_score": _safe_float(r.get("rs_score")),
            "close": _safe_float(r.get("close")),
            "ret_5d": _safe_float(r.get("ret_5d")),
            "ret_21d": _safe_float(r.get("ret_21d")),
            "purple_dot": _safe_int(r.get("purple_dot")),
            "watchlist_member": _safe_int(r.get("watchlist_member")),
            "extended_yellow": _safe_int(r.get("extended_yellow")),
            "extended_red": _safe_int(r.get("extended_red")),
            "bucket": None if (isinstance(bucket, float) and pd.isna(bucket)) else bucket,
        })
    # Sort each band by rs_score desc
    for g in out:
        out[g].sort(key=lambda x: x.get("rs_score") or 0, reverse=True)

    counts = {g: len(out[g]) for g in grade_order}
    return {"available": True, "grades": out, "counts": counts, "order": grade_order}


# ---- Candidates (primary + secondary) -------------------------------------
@app.get("/api/candidates")
def get_candidates():
    path = OUTPUT_DIR / "candidates.csv"
    rows = _read_csv_records(path)
    if not rows:
        return {"available": False, "primary": [], "secondary": []}
    universe = pd.read_csv(ROOT / "universe.csv").drop_duplicates(subset=["symbol"])
    sector_map = dict(zip(universe["symbol"], universe["sector"]))
    name_map = dict(zip(universe["symbol"], universe["name"]))
    for r in rows:
        r["sector"] = sector_map.get(r.get("symbol"))
        r["name"] = name_map.get(r.get("symbol"))
    primary = [r for r in rows if str(r.get("tier", "")).lower() == "primary"]
    secondary = [r for r in rows if str(r.get("tier", "")).lower() == "secondary"]
    return {"available": True, "primary": primary, "secondary": secondary}


# ---- Method-based detectors (Based + Afzal) ------------------------------
def _scrub_nans(obj):
    """Recursively replace pandas/numpy NaN values with None so the
    response can be JSON-serialised."""
    if isinstance(obj, dict):
        return {k: _scrub_nans(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_scrub_nans(v) for v in obj]
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    return obj


def _bucket_method_rows(filename: str, bucket_field: str = "bucket") -> dict:
    """Read a method's CSV and return rows grouped by bucket label, plus
    a flat list. Adds sector/name from universe for the UI.
    """
    path = OUTPUT_DIR / filename
    rows = _read_csv_records(path)
    if not rows:
        return {"available": False, "rows": [], "buckets": {}}
    try:
        universe = pd.read_csv(ROOT / "universe.csv").drop_duplicates(subset=["symbol"])
        universe = universe.where(pd.notnull(universe), None)
        sector_map = dict(zip(universe["symbol"], universe["sector"]))
        name_map = dict(zip(universe["symbol"], universe["name"]))
        for r in rows:
            r["sector"] = sector_map.get(r.get("symbol"))
            r["name"] = name_map.get(r.get("symbol"))
    except Exception:
        pass
    buckets: dict[str, list] = {}
    for r in rows:
        b = r.get(bucket_field) or "Unknown"
        buckets.setdefault(b, []).append(r)
    return _scrub_nans({"available": True, "rows": rows, "buckets": buckets})


@app.get("/api/methods/breakout")
def get_method_breakout():
    """Breakout detector (Setup B) output — Triggered / Forming / Watching."""
    return _bucket_method_rows("breakout_today.csv")


@app.get("/api/methods/pullback")
def get_method_pullback():
    """Pullback detector (Setup C) output — Reclaim / Near / Watching."""
    return _bucket_method_rows("pullback_today.csv")


@app.get("/api/methods/ep")
def get_method_ep():
    """EP detector (Setup A: Episodic Pivot / Strong Start) — Triggered / Forming / Watching."""
    return _bucket_method_rows("ep_today.csv")


# Legacy aliases (point to new per REPLAN rename)
@app.get("/api/methods/based")
def get_method_based():
    return get_method_breakout()


@app.get("/api/methods/afzal")
def get_method_afzal():
    return get_method_pullback()


@app.get("/api/methods/squeeze")
def get_method_squeeze():
    return get_method_ep()


@app.get("/api/movers")
def get_movers(limit: int = 20):
    """Pure catalyst screen — what actually moved today, no setup filter."""
    from scripts import detect_movers
    return _scrub_nans(detect_movers.build_movers(limit=limit))


@app.get("/api/picks/history_stats")
def get_picks_history_stats(lookback_days: int = 60):
    """Forward-return aggregations per source. Real evidence about whether
    the deterministic filters are picking winners over time."""
    from scripts import track_picks
    return track_picks.aggregate_stats(lookback_days=lookback_days)


@app.get("/api/picks/benchmark")
def get_picks_benchmark():
    """Today's avg return for top-picks vs nifty50 vs full-universe.
    Lets the user see if a bad day for picks is also a bad day for the
    market, vs systematic underperformance."""
    out = {"available": False, "date": None}
    try:
        with _db.features_conn() as fc:
            cur = fc.cursor()
            cur.execute("SELECT MAX(date) FROM features")
            target_date = cur.fetchone()[0]
        if not target_date:
            return out
        out["date"] = target_date

        with _db.ohlcv_conn() as oc:
            uni_df = pd.read_sql_query(
                "SELECT symbol, close FROM ohlcv WHERE date = ? AND symbol NOT LIKE '\\_%' ESCAPE '\\'",
                oc, params=(target_date,),
            )
            uni_df_prev = pd.read_sql_query(
                "SELECT symbol, close FROM ohlcv WHERE date < ? AND symbol NOT LIKE '\\_%' ESCAPE '\\' "
                "ORDER BY date DESC LIMIT 10000",
                oc, params=(target_date,),
            )
            nifty_df = pd.read_sql_query(
                "SELECT date, close FROM ohlcv WHERE symbol='_NIFTY50' ORDER BY date DESC LIMIT 2",
                oc,
            )

        if uni_df.empty:
            return out
        # Build prev_close map (latest close per symbol BEFORE target_date)
        prev_close = uni_df_prev.drop_duplicates(subset=["symbol"]).set_index("symbol")["close"].to_dict()
        uni_df = uni_df.assign(prev=uni_df["symbol"].map(prev_close))
        uni_df = uni_df.dropna(subset=["prev"])
        uni_df["ret_1d"] = (uni_df["close"] - uni_df["prev"]) / uni_df["prev"]
        out["universe_avg_pct"] = round(float(uni_df["ret_1d"].mean()), 4)
        out["universe_median_pct"] = round(float(uni_df["ret_1d"].median()), 4)

        # Top quartile (top 25% gainers' avg)
        top_q = uni_df.nlargest(int(len(uni_df) * 0.25) or 1, "ret_1d")
        out["universe_top_quartile_pct"] = round(float(top_q["ret_1d"].mean()), 4)

        # Top picks avg
        try:
            from scripts import top_picks as _tp
            tp = _tp.build_top_picks(limit=5)
            pick_syms = [p["symbol"] for p in (tp.get("picks") or [])]
            picks_df = uni_df[uni_df["symbol"].isin(pick_syms)]
            if not picks_df.empty:
                out["top_picks_avg_pct"] = round(float(picks_df["ret_1d"].mean()), 4)
                out["top_picks_count"] = int(len(picks_df))
        except Exception:
            pass

        # Nifty
        if not nifty_df.empty and len(nifty_df) >= 2:
            n_today = float(nifty_df.iloc[0]["close"])
            n_prev = float(nifty_df.iloc[1]["close"])
            out["nifty_pct"] = round((n_today - n_prev) / n_prev, 4)

        out["available"] = True
        return out
    except Exception as e:
        out["error"] = str(e)
        return out


@app.get("/api/ai/morning_brief")
def get_morning_brief(refresh: int = 0):
    from scripts import analyst
    return analyst.build_morning_brief(force=bool(refresh))


@app.get("/api/ai/top_picks_narrative")
def get_top_picks_narrative(refresh: int = 0):
    from scripts import analyst
    return analyst.build_top_picks_narrative(force=bool(refresh))


@app.get("/api/ai/symbol/{sym}")
def get_symbol_narrative(sym: str, refresh: int = 0):
    from scripts import analyst
    return analyst.summarize_symbol(sym, force=bool(refresh))


@app.get("/api/ai/positions_narrative")
def get_positions_narrative(refresh: int = 0):
    from scripts import analyst
    return analyst.build_positions_narrative(force=bool(refresh))


@app.get("/api/ai/confidence/{sym}")
def get_confidence(sym: str):
    """Pure deterministic confidence score (0-100) for a symbol with
    component breakdown. No LLM."""
    from scripts import analyst
    sym_u = sym.upper()
    feat_row = None
    try:
        with _db.features_conn() as fc:
            df = pd.read_sql_query(
                "SELECT * FROM features WHERE symbol=? ORDER BY date DESC LIMIT 1",
                fc, params=(sym_u,),
            )
        if not df.empty:
            feat_row = df.iloc[0].to_dict()
    except Exception:
        pass

    ep_row = breakout_row = pullback_row = None
    for label, path, target in (
        ("ep", OUTPUT_DIR / "ep_today.csv", "ep"),
        ("breakout", OUTPUT_DIR / "breakout_today.csv", "breakout"),
        ("pullback", OUTPUT_DIR / "pullback_today.csv", "pullback"),
    ):
        if path.exists():
            try:
                d = pd.read_csv(path)
                hit = d[d["symbol"] == sym_u]
                if not hit.empty:
                    if target == "ep":
                        ep_row = hit.iloc[0].to_dict()
                    elif target == "breakout":
                        breakout_row = hit.iloc[0].to_dict()
                    else:
                        pullback_row = hit.iloc[0].to_dict()
            except Exception:
                pass

    return analyst.compute_confidence(
        sym_u, feat_row=feat_row,
        ep_row=ep_row, breakout_row=breakout_row, pullback_row=pullback_row,
    )


@app.post("/api/assistant/ask")
def assistant_ask(payload: dict = Body(...)):
    """DeepSeek-backed Q&A. Strict fact-sheet narration with hallucination
    guard + forbidden-phrase filter. Returns plain prose + diagnostic
    metadata (model, reason, fact_sheet for transparency)."""
    question = (payload or {}).get("question", "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="question required")
    from scripts import analyst
    out = analyst.ask(question)
    return out


@app.get("/api/methods/top_picks")
def get_methods_top_picks(limit: int = 5):
    """Top-N picks today, scored across EP + Breakout + Pullback. Deterministic
    unified prioritizer (RS + tightness + sector + setup); reasons list explains.
    """
    from scripts import top_picks
    out = top_picks.build_top_picks(limit=limit)
    return _scrub_nans(out)


@app.get("/api/methods/overlap")
def get_methods_overlap():
    """Symbols appearing in multiple setups today (EP + Breakout + Pullback overlap)."""
    ep = _bucket_method_rows("ep_today.csv")
    bo = _bucket_method_rows("breakout_today.csv")
    pb = _bucket_method_rows("pullback_today.csv")
    ep_syms = {r.get("symbol") for r in ep.get("rows", []) if r.get("symbol")}
    bo_syms = {r.get("symbol") for r in bo.get("rows", []) if r.get("symbol")}
    pb_syms = {r.get("symbol") for r in pb.get("rows", []) if r.get("symbol")}
    # overlap = symbols in 2+ of the sets
    all_syms = ep_syms | bo_syms | pb_syms
    overlap = []
    for sym in sorted(all_syms):
        cnt = sum([sym in ep_syms, sym in bo_syms, sym in pb_syms])
        if cnt >= 2:
            overlap.append(sym)
    out = []
    ep_index = {r["symbol"]: r for r in ep.get("rows", []) if r.get("symbol")}
    bo_index = {r["symbol"]: r for r in bo.get("rows", []) if r.get("symbol")}
    pb_index = {r["symbol"]: r for r in pb.get("rows", []) if r.get("symbol")}
    for sym in overlap:
        out.append({
            "symbol": sym,
            "ep_bucket": ep_index.get(sym, {}).get("bucket"),
            "breakout_bucket": bo_index.get(sym, {}).get("bucket"),
            "pullback_bucket": pb_index.get(sym, {}).get("bucket"),
            "ep": ep_index.get(sym),
            "breakout": bo_index.get(sym),
            "pullback": pb_index.get(sym),
        })
    return {"available": True, "count": len(out), "overlap": out}


# Legacy alias
@app.get("/api/methods/both")
def get_methods_both():
    return get_methods_overlap()


# ---- Candidates history ---------------------------------------------------
@app.get("/api/candidates/history")
def get_candidates_history(days: int = 30):
    path = OUTPUT_DIR / "candidates_history.csv"
    if not path.exists():
        return {"available": False, "rows": []}
    df = pd.read_csv(path)
    if "date" not in df.columns:
        return {"available": False, "rows": []}
    by_day = df.groupby(["date", "tier"]).size().unstack(fill_value=0).reset_index()
    by_day = by_day.sort_values("date").tail(days)
    by_day = by_day.where(pd.notnull(by_day), 0)
    return {"available": True, "rows": by_day.to_dict(orient="records")}


# ---- Positions (tracker) --------------------------------------------------
@app.get("/api/positions")
def get_positions(state: str | None = None, limit: int = 200):
    try:
        with _db.portfolio_conn() as conn:
            df = pd.read_sql_query(
                "SELECT * FROM positions ORDER BY signal_date DESC, id DESC", conn,
            )
    except Exception:
        return {"available": False, "rows": []}
    if df.empty:
        return {"available": True, "rows": [], "summary": {}, "stats": {}}

    if state:
        df = df[df["state"] == state]
    df = df.head(limit)

    # Enrich ACTIVE positions with current price + distance to stop
    screen_path = OUTPUT_DIR / "screen_today.csv"
    cur_price_map: dict[str, float] = {}
    if screen_path.exists():
        s = pd.read_csv(screen_path)
        cur_price_map = dict(zip(s["symbol"], s["close"]))

    out = []
    for _, r in df.iterrows():
        d = r.to_dict()
        d.pop("_id", None)
        cur_price = cur_price_map.get(d.get("symbol"))
        d["current_price"] = _safe_float(cur_price)
        if d.get("state") == "ACTIVE" and d.get("entry_price") and cur_price:
            d["live_pnl_pct"] = (cur_price - d["entry_price"]) / d["entry_price"]
            if d.get("stop_price"):
                d["distance_to_stop_pct"] = (cur_price - d["stop_price"]) / cur_price
        for k, v in list(d.items()):
            if isinstance(v, float) and pd.isna(v):
                d[k] = None
        out.append(d)

    # Summary across all states
    with _db.portfolio_conn() as conn:
        sdf = pd.read_sql_query("SELECT state, COUNT(*) c FROM positions GROUP BY state", conn)
    summary = {row["state"]: int(row["c"]) for _, row in sdf.iterrows()}

    # Hit rate / R-multiple over EXITED_*
    with _db.portfolio_conn() as conn:
        exited = pd.read_sql_query(
            "SELECT * FROM positions WHERE state LIKE 'EXITED_%' AND pnl_pct IS NOT NULL", conn,
        )
    stats = {}
    if not exited.empty:
        wins = int((exited["pnl_pct"] > 0).sum())
        total = int(len(exited))
        stats = {
            "total_exited": total,
            "wins": wins,
            "losses": total - wins,
            "hit_rate": round(wins / total, 4) if total else 0,
            "avg_pnl_pct": round(float(exited["pnl_pct"].mean()), 4),
            "best_pnl_pct": round(float(exited["pnl_pct"].max()), 4),
            "worst_pnl_pct": round(float(exited["pnl_pct"].min()), 4),
        }
        # MAE/MFE roll-ups (only over rows that have them populated)
        mae_rows = exited.dropna(subset=["mae_pct"]) if "mae_pct" in exited.columns else pd.DataFrame()
        if not mae_rows.empty:
            stats["avg_mae_pct"] = round(float(mae_rows["mae_pct"].mean()), 4)
            stats["avg_mfe_pct"] = round(float(mae_rows["mfe_pct"].mean()), 4)
            if "mae_r" in mae_rows.columns:
                rr = mae_rows.dropna(subset=["mae_r"])
                if not rr.empty:
                    stats["avg_mae_r"] = round(float(rr["mae_r"].mean()), 2)
                    stats["avg_mfe_r"] = round(float(rr["mfe_r"].mean()), 2)
            # Stop-calibration: of stopped trades, what fraction had MAE<=-3%
            # before they hit stop? If high, the actual stop is too loose.
            stopped = mae_rows[mae_rows["state"] == "EXITED_STOP"]
            if not stopped.empty:
                shallow = int((stopped["mae_pct"] >= -0.03).sum())
                stats["shallow_stop_fraction"] = round(shallow / len(stopped), 3)

    return {"available": True, "rows": out, "summary": summary, "stats": stats}


# ---- Position manual management -------------------------------------------
def _compute_pnl_pct(entry: float | None, exit_p: float | None) -> float | None:
    if entry is None or exit_p is None or entry == 0:
        return None
    try:
        return round((exit_p - entry) / entry, 6)
    except Exception:
        return None


@app.post("/api/positions/add")
def position_add(payload: dict):
    """Manually create a position. Required: symbol, entry_price, stop_price.
    Optional: signal_date (default=today), entry_date (default=today),
    size_shares, state (default ACTIVE), regime_at_entry, entry_grade, notes.
    """
    p = payload or {}
    sym = (p.get("symbol") or "").strip().upper()
    if not sym:
        raise HTTPException(400, "symbol required")
    try:
        entry_price = float(p["entry_price"]) if p.get("entry_price") is not None else None
        stop_price = float(p["stop_price"]) if p.get("stop_price") is not None else None
    except Exception:
        raise HTTPException(400, "entry_price and stop_price must be numbers")
    if entry_price is None or stop_price is None:
        raise HTTPException(400, "entry_price and stop_price required")
    if stop_price >= entry_price:
        raise HTTPException(400, "stop_price must be below entry_price for a long")

    today = datetime.utcnow().strftime("%Y-%m-%d")
    state = (p.get("state") or "ACTIVE").upper()
    allowed_states = {"PENDING_CONFIRM", "ACTIVE", "EXITED_STOP",
                      "EXITED_EXTENDED", "EXITED_DECAY", "EXITED_MANUAL", "DISCARDED"}
    if state not in allowed_states:
        raise HTTPException(400, f"state must be one of {sorted(allowed_states)}")

    size_shares = None
    if p.get("size_shares") is not None:
        try:
            size_shares = int(p["size_shares"])
        except Exception:
            raise HTTPException(400, "size_shares must be an integer")

    try:
        with _db.portfolio_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO positions
                   (symbol, signal_date, state, entry_date, entry_price, stop_price,
                    size_shares, regime_at_entry, entry_grade, notes)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    sym,
                    p.get("signal_date") or today,
                    state,
                    p.get("entry_date") or today,
                    entry_price,
                    stop_price,
                    size_shares,
                    p.get("regime_at_entry"),
                    p.get("entry_grade"),
                    p.get("notes") or "manual entry",
                ),
            )
            conn.commit()
            new_id = cur.lastrowid
        return {"ok": True, "id": new_id, "symbol": sym, "state": state}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"failed to add position: {e}")


@app.post("/api/positions/{pid}/update")
def position_update(pid: int, payload: dict | None = None):
    """Edit an existing position. Allowed fields: stop_price (trail), size_shares,
    notes, entry_grade, regime_at_entry, state.
    """
    p = payload or {}
    sets = []
    vals: list[Any] = []
    field_map = {
        "stop_price": float,
        "size_shares": int,
        "notes": str,
        "entry_grade": str,
        "regime_at_entry": str,
        "state": str,
    }
    for k, cast in field_map.items():
        if k in p and p[k] is not None:
            try:
                v = cast(p[k]) if cast is not str else str(p[k])
                if k == "state":
                    v = v.upper()
                sets.append(f"{k}=?")
                vals.append(v)
            except Exception:
                raise HTTPException(400, f"invalid {k}")
    if not sets:
        raise HTTPException(400, "no editable fields supplied")
    vals.append(pid)
    try:
        with _db.portfolio_conn() as conn:
            cur = conn.cursor()
            cur.execute(f"UPDATE positions SET {', '.join(sets)} WHERE id=?", vals)
            if cur.rowcount == 0:
                raise HTTPException(404, f"position id {pid} not found")
            conn.commit()
        return {"ok": True, "id": pid, "updated_fields": list(p.keys())}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"failed to update position: {e}")


@app.post("/api/positions/{pid}/exit")
def position_exit(pid: int, payload: dict | None = None):
    """Close a position. Required: exit_price. Optional: exit_date (today),
    state (default EXITED_MANUAL — also accepts EXITED_STOP / EXITED_EXTENDED /
    EXITED_DECAY), notes.
    """
    p = payload or {}
    if p.get("exit_price") is None:
        raise HTTPException(400, "exit_price required")
    try:
        exit_price = float(p["exit_price"])
    except Exception:
        raise HTTPException(400, "exit_price must be a number")
    state = (p.get("state") or "EXITED_MANUAL").upper()
    allowed_exit_states = {"EXITED_STOP", "EXITED_EXTENDED", "EXITED_DECAY", "EXITED_MANUAL"}
    if state not in allowed_exit_states:
        raise HTTPException(400, f"state must be one of {sorted(allowed_exit_states)}")
    today = datetime.utcnow().strftime("%Y-%m-%d")

    try:
        with _db.portfolio_conn() as conn:
            cur = conn.cursor()
            row = cur.execute(
                "SELECT entry_price, notes FROM positions WHERE id=?", (pid,),
            ).fetchone()
            if not row:
                raise HTTPException(404, f"position id {pid} not found")
            entry_price = row[0]
            existing_notes = row[1] or ""
            pnl = _compute_pnl_pct(entry_price, exit_price)
            new_notes = p.get("notes")
            final_notes = (existing_notes + " | " + new_notes).strip(" |") if new_notes else existing_notes
            cur.execute(
                """UPDATE positions
                   SET state=?, exit_date=?, exit_price=?, pnl_pct=?, notes=?
                   WHERE id=?""",
                (state, p.get("exit_date") or today, exit_price, pnl, final_notes, pid),
            )
            conn.commit()
        return {"ok": True, "id": pid, "state": state, "pnl_pct": pnl}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"failed to exit position: {e}")


@app.post("/api/positions/{pid}/delete")
def position_delete(pid: int):
    """Hard-delete a position row."""
    try:
        with _db.portfolio_conn() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM positions WHERE id=?", (pid,))
            if cur.rowcount == 0:
                raise HTTPException(404, f"position id {pid} not found")
            conn.commit()
        return {"ok": True, "deleted_id": pid}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"failed to delete position: {e}")


# ---- Watchlist ------------------------------------------------------------
@app.get("/api/watchlist")
def get_watchlist():
    path = ROOT / "watchlist.csv"
    if not path.exists():
        return {"available": False, "rows": []}
    df = pd.read_csv(path)
    universe = pd.read_csv(ROOT / "universe.csv").drop_duplicates(subset=["symbol"])

    # Enrich with screen data + grade history
    screen_path = OUTPUT_DIR / "screen_today.csv"
    s = pd.read_csv(screen_path) if screen_path.exists() else pd.DataFrame()
    df = df.merge(universe[["symbol", "name", "sector", "industry"]], on="symbol", how="left")
    if not s.empty:
        screen_cols = [c for c in [
            "symbol", "grade", "rs_score", "close", "purple_dot",
            "purple_dot_count_30d", "extended_yellow", "extended_red", "bucket",
            "adr14_pct", "vol_ratio_20", "bf_score_30d_max",
            "sector_rs_pct",
        ] if c in s.columns]
        df = df.merge(s[screen_cols], on="symbol", how="left")
    else:
        # Initialize columns so the fallback merge below works uniformly
        for col in ["grade", "rs_score", "close", "purple_dot",
                    "purple_dot_count_30d", "extended_yellow", "extended_red", "bucket",
                    "adr14_pct", "vol_ratio_20", "bf_score_30d_max", "sector_rs_pct"]:
            df[col] = None

    # Always-on enrichment from the grader: screen_today.csv sometimes
    # leaves rs_score as NaN for symbols outside the gate-passers, even if
    # they're in the screen output (e.g. watchlist members in S1A). The
    # grader is the canonical RS source — pull it here for every watchlist
    # row that lacks one.
    try:
        feat_conn = _db.features_conn()
        ohlcv_conn = _db.ohlcv_conn()
        cur = feat_conn.cursor()
        cur.execute("SELECT MAX(date) FROM features")
        latest_date = cur.fetchone()[0]
        if latest_date:
            grade_today_df = _grade_helper.calculate_grades_for_date(
                feat_conn, ohlcv_conn, latest_date,
            )
            if grade_today_df is not None and not grade_today_df.empty:
                grade_idx = grade_today_df.set_index("symbol")
                for sym in df["symbol"].tolist():
                    if sym not in grade_idx.index:
                        continue
                    g_row = grade_idx.loc[sym]
                    mask = df["symbol"] == sym
                    cur_rs = df.loc[mask, "rs_score"].iloc[0] if "rs_score" in df.columns else None
                    if cur_rs is None or pd.isna(cur_rs):
                        df.loc[mask, "rs_score"] = _safe_float(g_row.get("rs_score"))
                    cur_grade = df.loc[mask, "grade"].iloc[0] if "grade" in df.columns else None
                    if not cur_grade or (isinstance(cur_grade, float) and pd.isna(cur_grade)):
                        df.loc[mask, "grade"] = g_row.get("grade")
    except Exception as e:
        print(f"[watchlist grader enrich] {e}")

    # Fallback: for symbols missing from screen_today, pull latest features row
    # so newly-added watchlist symbols show price/RS/grade as soon as backfill done.
    try:
        missing_syms = [
            s_ for s_ in df["symbol"].tolist()
            if s_ and (s.empty or s_ not in set(s["symbol"].tolist()))
        ]
        if missing_syms:
            feat_conn = _db.features_conn()
            ohlcv_conn = _db.ohlcv_conn()
            # Cache today's grade calculation once for all missing symbols —
            # rs_score isn't a column on `features`, it's computed by the
            # grader. Without this watchlist symbols outside screen show "—".
            grade_today_df = None
            try:
                cur = feat_conn.cursor()
                cur.execute("SELECT MAX(date) FROM features")
                latest_date = cur.fetchone()[0]
                if latest_date:
                    grade_today_df = _grade_helper.calculate_grades_for_date(
                        feat_conn, ohlcv_conn, latest_date,
                    )
            except Exception as e:
                print(f"[watchlist grade cache] {e}")
            for sym in missing_syms:
                try:
                    last = pd.read_sql_query(
                        "SELECT * FROM features WHERE symbol=? ORDER BY date DESC LIMIT 1",
                        feat_conn, params=(sym,),
                    )
                    if last.empty:
                        continue
                    last_row = last.iloc[0]
                    last_close = pd.read_sql_query(
                        "SELECT close FROM ohlcv WHERE symbol=? ORDER BY date DESC LIMIT 1",
                        ohlcv_conn, params=(sym,),
                    )
                    close_val = float(last_close.iloc[0]["close"]) if not last_close.empty else None
                    sma50 = last_row.get("sma50")
                    bucket = None
                    if close_val and sma50 and not pd.isna(sma50):
                        bucket = "Bullish" if close_val > sma50 else "Bearish"
                    # Pull rs_score + grade from the grader output for today.
                    rs_score = None
                    grade = None
                    sector_rs_pct = None
                    if grade_today_df is not None and not grade_today_df.empty:
                        gr = grade_today_df[grade_today_df["symbol"] == sym]
                        if not gr.empty:
                            rs_score = _safe_float(gr.iloc[0].get("rs_score"))
                            grade = gr.iloc[0].get("grade")
                            sector_rs_pct = _safe_float(gr.iloc[0].get("sector_rs_pct"))
                    mask = df["symbol"] == sym
                    df.loc[mask, "close"] = close_val
                    df.loc[mask, "rs_score"] = rs_score
                    df.loc[mask, "grade"] = grade
                    df.loc[mask, "sector_rs_pct"] = sector_rs_pct
                    df.loc[mask, "purple_dot"] = _safe_int(last_row.get("purple_dot"))
                    df.loc[mask, "purple_dot_count_30d"] = _safe_int(last_row.get("purple_dot_count_30d"))
                    df.loc[mask, "adr14_pct"] = _safe_float(last_row.get("adr14_pct"))
                    df.loc[mask, "vol_ratio_20"] = _safe_float(last_row.get("vol_ratio_20"))
                    df.loc[mask, "bf_score_30d_max"] = _safe_float(last_row.get("bf_score_30d_max"))
                    df.loc[mask, "bucket"] = bucket
                except Exception as e:
                    print(f"[watchlist enrich fallback] {sym}: {e}")
    except Exception as e:
        print(f"[watchlist features fallback] {e}")

    # Robust NaN -> None coercion (handles float-dtype NaN that survives df.where)
    df = df.astype(object).where(pd.notnull(df), None)

    # 5-day grade history (clear cache first since universe may have changed)
    history: dict[str, list[str]] = {}
    try:
        _grade_helper.clear_cache()
        feat_conn = _db.features_conn()
        ohlcv_conn = _db.ohlcv_conn()
        cur = feat_conn.cursor()
        cur.execute("SELECT DISTINCT date FROM features ORDER BY date DESC LIMIT 5")
        dates = [r[0] for r in cur.fetchall()]
        for d in reversed(dates):
            grades = _grade_helper.calculate_grades_for_date(feat_conn, ohlcv_conn, d)
            for sym in df["symbol"].tolist():
                row = grades[grades["symbol"] == sym]
                history.setdefault(sym, []).append(row.iloc[0]["grade"] if not row.empty else None)
    except Exception:
        pass

    rows = df.to_dict(orient="records")
    for r in rows:
        # Final pass: coerce any lingering NaN floats to None
        for k, v in list(r.items()):
            if isinstance(v, float) and (v != v):  # NaN check
                r[k] = None
        r["grade_history_5d"] = history.get(r.get("symbol"), [])
    return {"available": True, "rows": rows}


@app.post("/api/watchlist/add")
def watchlist_add(payload: dict):
    sym = (payload or {}).get("symbol", "").strip().upper()
    if not sym:
        raise HTTPException(400, "symbol required")
    universe_path = ROOT / "universe.csv"
    universe = pd.read_csv(universe_path).drop_duplicates(subset=["symbol"])
    universe_syms = set(universe["symbol"].tolist())

    auto_added_to_universe = False
    if sym not in universe_syms:
        # Auto-extend: validate via yfinance, then append to universe.csv
        import yfinance as yf
        meta_name = (payload or {}).get("name") or sym
        meta_sector = (payload or {}).get("sector") or "Uncategorised"
        meta_industry = (payload or {}).get("industry") or "Uncategorised"
        meta_basic = (payload or {}).get("basic_industry") or meta_industry
        meta_mcap = (payload or {}).get("market_cap_cr")
        try:
            tk = yf.Ticker(f"{sym}.NS")
            df_test = tk.history(period="10d", auto_adjust=False)
            if df_test is None or df_test.empty:
                raise HTTPException(400, f"unknown symbol '{sym}' — yfinance returned no data for {sym}.NS")
            # Pull sector/industry/longName/market_cap from .info — graceful on failure
            try:
                info = tk.info or {}
                if not (payload or {}).get("name"):
                    meta_name = info.get("longName") or info.get("shortName") or sym
                if not (payload or {}).get("sector"):
                    meta_sector = info.get("sector") or "Uncategorised"
                if not (payload or {}).get("industry"):
                    meta_industry = info.get("industry") or "Uncategorised"
                if not (payload or {}).get("basic_industry"):
                    meta_basic = info.get("industry") or meta_industry
                if meta_mcap is None and info.get("marketCap"):
                    try:
                        # yfinance returns market cap in INR for .NS tickers — convert to crores
                        meta_mcap = round(float(info["marketCap"]) / 1e7, 2)
                    except Exception:
                        pass
            except Exception as e:
                print(f"[watchlist_add info] {sym}: {e}")
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(400, f"failed to validate '{sym}' on yfinance: {e}")

        new_row = {
            "symbol": sym,
            "name": meta_name,
            "sector": meta_sector,
            "industry": meta_industry,
            "market_cap_cr": meta_mcap,
            "basic_industry": meta_basic,
        }
        universe = pd.concat([universe, pd.DataFrame([new_row])], ignore_index=True)
        ordered = [c for c in ["symbol", "name", "sector", "industry", "market_cap_cr", "basic_industry"] if c in universe.columns]
        universe = universe[ordered]
        universe.to_csv(universe_path, index=False)
        auto_added_to_universe = True

        def _backfill_one():
            try:
                from scripts import fetch_yf, indicators, _db
                from datetime import datetime as _dt, timedelta as _td
                conn = _db.ohlcv_conn()
                today = _dt.now()
                start = today - _td(days=380)
                df_o = fetch_yf.fetch_one(sym, start, today)
                if df_o is None or df_o.empty:
                    return
                records = []
                for ts, row in df_o.iterrows():
                    try:
                        records.append((
                            sym, ts.strftime("%Y-%m-%d"),
                            float(row["Open"]), float(row["High"]), float(row["Low"]),
                            float(row["Close"]),
                            int(row["Volume"]) if pd.notna(row["Volume"]) else 0,
                        ))
                    except Exception:
                        continue
                fetch_yf.upsert_ohlcv(conn, records)
                ohlcv_conn = _db.ohlcv_conn()
                feat_conn = _db.features_conn()
                df_full = pd.read_sql_query(
                    "SELECT * FROM ohlcv WHERE symbol=? ORDER BY date ASC",
                    ohlcv_conn, params=(sym,),
                )
                if not df_full.empty:
                    feat_df = indicators.compute_indicators_for_symbol(df_full, float("nan"))
                    if not feat_df.empty:
                        indicators.upsert_features(feat_conn, feat_df)
            except Exception as e:
                print(f"[watchlist_add backfill] {sym}: {e}")

        threading.Thread(target=_backfill_one, daemon=True).start()

    path = ROOT / "watchlist.csv"
    df = pd.read_csv(path) if path.exists() else pd.DataFrame(columns=["symbol", "date_added", "source_reason"])
    if sym in set(df["symbol"].tolist()):
        return {"ok": True, "msg": "already in watchlist", "auto_added_to_universe": auto_added_to_universe}
    new = pd.DataFrame([{
        "symbol": sym,
        "date_added": datetime.utcnow().strftime("%Y-%m-%d"),
        "source_reason": (payload or {}).get("reason", "manual"),
    }])
    df = pd.concat([df, new], ignore_index=True)
    df.to_csv(path, index=False)
    return {"ok": True, "added": sym, "auto_added_to_universe": auto_added_to_universe}


@app.post("/api/watchlist/remove")
def watchlist_remove(payload: dict):
    sym = (payload or {}).get("symbol", "").strip().upper()
    if not sym:
        raise HTTPException(400, "symbol required")
    path = ROOT / "watchlist.csv"
    if not path.exists():
        return {"ok": True}
    df = pd.read_csv(path)
    df = df[df["symbol"] != sym]
    df.to_csv(path, index=False)
    return {"ok": True, "removed": sym}


@app.post("/api/watchlist/refresh_meta")
def watchlist_refresh_meta(payload: dict | None = None):
    """Re-fetch sector/industry/name from yfinance for watchlist symbols whose
    universe row is currently 'Uncategorised'. Idempotent — safe to call any
    time. Pass {"symbol": "X"} to refresh just one, otherwise refreshes all
    Uncategorised watchlist members.
    """
    payload = payload or {}
    target_sym = (payload.get("symbol") or "").strip().upper() or None

    universe_path = ROOT / "universe.csv"
    universe = pd.read_csv(universe_path).drop_duplicates(subset=["symbol"])
    wl_path = ROOT / "watchlist.csv"
    if not wl_path.exists():
        return {"ok": True, "updated": []}
    wl = pd.read_csv(wl_path)

    candidates = wl["symbol"].tolist()
    if target_sym:
        candidates = [s for s in candidates if s == target_sym]

    updated = []
    import yfinance as yf
    for sym in candidates:
        urow = universe[universe["symbol"] == sym]
        if urow.empty:
            continue
        cur_sector = str(urow.iloc[0].get("sector") or "")
        cur_industry = str(urow.iloc[0].get("industry") or "")
        if not target_sym and cur_sector and cur_sector != "Uncategorised" and cur_industry and cur_industry != "Uncategorised":
            continue
        try:
            tk = yf.Ticker(f"{sym}.NS")
            info = tk.info or {}
            new_name = info.get("longName") or info.get("shortName") or urow.iloc[0].get("name") or sym
            new_sector = info.get("sector") or cur_sector or "Uncategorised"
            new_industry = info.get("industry") or cur_industry or "Uncategorised"
            new_basic = info.get("industry") or new_industry
            new_mcap = urow.iloc[0].get("market_cap_cr")
            if info.get("marketCap"):
                try:
                    new_mcap = round(float(info["marketCap"]) / 1e7, 2)
                except Exception:
                    pass
            mask = universe["symbol"] == sym
            universe.loc[mask, "name"] = new_name
            universe.loc[mask, "sector"] = new_sector
            universe.loc[mask, "industry"] = new_industry
            if "basic_industry" in universe.columns:
                universe.loc[mask, "basic_industry"] = new_basic
            if "market_cap_cr" in universe.columns and new_mcap is not None:
                universe.loc[mask, "market_cap_cr"] = new_mcap
            updated.append({"symbol": sym, "sector": new_sector, "industry": new_industry, "name": new_name})
        except Exception as e:
            print(f"[refresh_meta] {sym}: {e}")

    if updated:
        ordered = [c for c in ["symbol", "name", "sector", "industry", "market_cap_cr", "basic_industry"] if c in universe.columns]
        universe = universe[ordered]
        universe.to_csv(universe_path, index=False)
    return {"ok": True, "updated": updated}


@app.post("/api/watchlist/add_bulk")
def watchlist_add_bulk(payload: dict):
    """Add multiple symbols at once. Body: {symbols: ["LENSKART","ATHERENERGY"]}.
    Calls the same validation/backfill logic as /add for each. Returns
    per-symbol status (added / already-in / failed) so the UI can show a
    summary toast.
    """
    raw = (payload or {}).get("symbols") or []
    if isinstance(raw, str):
        raw = [s.strip() for s in raw.replace(",", "\n").split("\n")]
    syms = [s.strip().upper() for s in raw if s and s.strip()]
    if not syms:
        raise HTTPException(400, "symbols list required")
    results = []
    for sym in syms:
        try:
            res = watchlist_add({"symbol": sym, "reason": "bulk_add"})
            results.append({"symbol": sym, "ok": True, **{k: v for k, v in res.items() if k != "ok"}})
        except HTTPException as e:
            results.append({"symbol": sym, "ok": False, "error": e.detail})
        except Exception as e:
            results.append({"symbol": sym, "ok": False, "error": str(e)})
    n_ok = sum(1 for r in results if r["ok"])
    return {"ok": True, "added": n_ok, "total": len(results), "results": results}


# Curated list of post-2024 NSE IPOs. Used by the "Add IPO basket"
# button in the watchlist UI. yfinance validation in /add_bulk will
# silently skip any ticker that has changed/delisted — the per-symbol
# error surfaces in the UI summary toast.
RECENT_IPOS = [
    "ATHERENERGY",   # Ather Energy (Apr 2025)
    "LENSKART",      # Lenskart Solutions (Nov 2025)
    "HYUNDAI",       # Hyundai Motor India (Oct 2024)
    "SWIGGY",        # Swiggy (Nov 2024)
    "OLAELEC",       # Ola Electric (Aug 2024)
    "FIRSTCRY",      # Brainbees / FirstCry (Aug 2024)
    "WAAREEENER",    # Waaree Energies (Nov 2024)
    "NTPCGREEN",     # NTPC Green Energy (Nov 2024)
    "NIVABUPA",      # Niva Bupa Health Insurance (Nov 2024)
    "BAJAJHFL",      # Bajaj Housing Finance (Sep 2024)
    "AWFIS",         # Awfis Space Solutions (May 2024)
    "GODIGIT",       # Go Digit General Insurance (May 2024)
    "PREMIERENE",    # Premier Energies (Sep 2024)
    "INVENTURUS",    # Inventurus Knowledge Solutions (Dec 2024)
    "ZAGGLE",        # Zaggle Prepaid (Sep 2023)
]


@app.get("/api/watchlist/ipo_basket")
def watchlist_ipo_basket():
    """Return the curated list of recent NSE IPOs. Frontend's
    'Add IPO Basket' button POSTs the chosen symbols to /add_bulk.
    """
    return {"ok": True, "symbols": RECENT_IPOS, "count": len(RECENT_IPOS)}


# ---- SVRO arms (deprecated — feature-flagged) ----------------------------
# SVRO has been retired in favour of the Based + Afzal methods. The endpoint
# remains so existing UI fetches don't 404, but it returns available:false
# unless `methods.svro_enabled` is true in config.yaml.
@app.get("/api/svro/arms")
def svro_arms():
    cfg = _config.load_config()
    methods_cfg = getattr(cfg, "methods", None)
    enabled = bool(getattr(methods_cfg, "svro_enabled", False)) if methods_cfg else False
    if not enabled:
        return {"available": False, "deprecated": True, "replaced_by": ["based", "afzal"]}
    data = _read_json(OUTPUT_DIR / "svro_arm_today.json")
    if not data:
        return {"available": False}
    return {"available": True, **data}


# ---- Daily position digest -----------------------------------------------
@app.get("/api/positions/daily_digest")
def positions_daily_digest_preview(date: str | None = None):
    """Preview the daily position digest (deterministic). No Telegram send."""
    from scripts import position_digest
    out = position_digest.send_digest(send=False, today_date=date)
    return _scrub_nans({
        "available": True,
        "date": out.get("date"),
        "regime": out.get("regime"),
        "positions": out.get("positions"),
        "exits_today": out.get("exits_today"),
        "pending_count": out.get("pending_count"),
        "based": out.get("based"),
        "afzal": out.get("afzal"),
        "telegram_text": out.get("_text"),
    })


@app.post("/api/positions/daily_digest")
def positions_daily_digest_send(body: dict | None = Body(default=None)):
    """Send the daily position digest to Telegram. Body may contain
    {"date": "YYYY-MM-DD"} to override; otherwise uses latest features date.
    """
    from scripts import position_digest
    date = (body or {}).get("date") if isinstance(body, dict) else None
    out = position_digest.send_digest(send=True, today_date=date)
    return {
        "ok": True,
        "sent": bool(out.get("_sent")),
        "date": out.get("date"),
        "preview": out.get("_text"),
    }


# ---- OpenClaw / signals + fills + skips ----------------------------------
# Contract documented in docs/openclaw_skill.md. These endpoints power the
# OpenClaw skill bridge: signals out, acks back, fills/skips logged.

@app.get("/api/signals/outbound")
def signals_outbound(limit: int = 50):
    """Return un-acked signals from `signals` table, oldest first.

    OpenClaw polls this and acks each via /api/signals/ack/<uuid>.
    """
    conn = _db.portfolio_conn()
    rows = pd.read_sql_query(
        "SELECT uuid, created_at, method, symbol, kind, bucket, payload "
        "FROM signals WHERE acked_at IS NULL ORDER BY created_at ASC LIMIT ?",
        conn, params=(limit,),
    )
    out = []
    for _, r in rows.iterrows():
        try:
            payload = json.loads(r["payload"]) if r["payload"] else {}
        except Exception:
            payload = {}
        out.append({
            "uuid": r["uuid"],
            "created_at": r["created_at"],
            "method": r["method"],
            "symbol": r["symbol"],
            "kind": r["kind"],
            "bucket": r["bucket"],
            "payload": payload,
        })
    return {"signals": out, "count": len(out)}


@app.post("/api/signals/ack/{uuid}")
def signals_ack(uuid: str, body: dict | None = Body(default=None)):
    """Mark a signal as delivered. Idempotent — re-acking is a no-op."""
    delivered_to = (body or {}).get("delivered_to") if isinstance(body, dict) else None
    conn = _db.portfolio_conn()
    cur = conn.cursor()
    cur.execute(
        "UPDATE signals SET acked_at=CURRENT_TIMESTAMP, delivered_to=COALESCE(?, delivered_to) "
        "WHERE uuid=? AND acked_at IS NULL",
        (delivered_to, uuid),
    )
    conn.commit()
    if cur.rowcount == 0:
        return {"ok": True, "already_acked": True}
    return {"ok": True, "uuid": uuid, "delivered_to": delivered_to}


@app.post("/api/fills")
def post_fill(body: dict = Body(...)):
    """Record a confirmed trade fill. If a matching PENDING_CONFIRM
    position exists, transitions it to ACTIVE; otherwise creates a new
    manually-tracked position so the position is never lost.
    """
    sym = (body.get("symbol") or "").upper().strip()
    if not sym:
        raise HTTPException(400, "symbol required")
    method = (body.get("method") or "").lower().strip() or None
    price = float(body.get("price", 0) or 0)
    size = int(body.get("size_shares", 0) or 0)
    side = (body.get("side") or "BUY").upper()
    source = body.get("source") or "manual"
    notes = body.get("notes")
    if price <= 0 or size <= 0:
        raise HTTPException(400, "price and size_shares must be positive")

    conn = _db.portfolio_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO fills (symbol, method, price, size_shares, side, source, notes) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (sym, method, price, size, side, source, notes),
    )
    fill_id = cur.lastrowid

    position_id = None
    if side == "BUY":
        # Resolve a PENDING_CONFIRM row for this method+symbol (most recent)
        cur.execute(
            "SELECT id FROM positions WHERE symbol=? AND state='PENDING_CONFIRM' "
            "AND (method=? OR ?='') ORDER BY signal_date DESC LIMIT 1",
            (sym, method or '', method or ''),
        )
        row = cur.fetchone()
        if row:
            position_id = row[0]
            today = pd.Timestamp.now().date().isoformat()
            cur.execute(
                "UPDATE positions SET state='ACTIVE', entry_date=?, entry_price=?, "
                "size_shares=? WHERE id=?",
                (today, price, size, position_id),
            )
        else:
            today = pd.Timestamp.now().date().isoformat()
            cur.execute(
                "INSERT INTO positions (symbol, signal_date, state, method, "
                "entry_date, entry_price, size_shares, notes) "
                "VALUES (?, ?, 'ACTIVE', ?, ?, ?, ?, ?)",
                (sym, today, method, today, price, size, 'Manual fill via OpenClaw'),
            )
            position_id = cur.lastrowid
    elif side in ("SELL_PARTIAL", "SELL_EXIT"):
        cur.execute(
            "SELECT id, entry_price, size_shares FROM positions WHERE symbol=? "
            "AND state='ACTIVE' AND (method=? OR ?='') ORDER BY signal_date DESC LIMIT 1",
            (sym, method or '', method or ''),
        )
        row = cur.fetchone()
        if row:
            position_id, entry_price, cur_size = row
            if side == "SELL_EXIT":
                pnl = (price - float(entry_price)) / float(entry_price) if entry_price else None
                today = pd.Timestamp.now().date().isoformat()
                cur.execute(
                    "UPDATE positions SET state='EXITED_MANUAL', exit_date=?, "
                    "exit_price=?, pnl_pct=? WHERE id=?",
                    (today, price, pnl, position_id),
                )
            else:  # SELL_PARTIAL — reduce size_shares
                new_size = max(0, int(cur_size or 0) - size)
                cur.execute(
                    "UPDATE positions SET size_shares=? WHERE id=?",
                    (new_size, position_id),
                )

    if position_id is not None:
        cur.execute("UPDATE fills SET position_id=? WHERE id=?", (position_id, fill_id))
    conn.commit()
    return {"ok": True, "fill_id": fill_id, "position_id": position_id}


@app.get("/api/fills")
def list_fills(limit: int = 100):
    conn = _db.portfolio_conn()
    df = pd.read_sql_query(
        "SELECT * FROM fills ORDER BY ts DESC LIMIT ?", conn, params=(limit,),
    )
    return {"rows": _scrub_nans(df.to_dict(orient="records"))}


@app.post("/api/skips")
def post_skip(body: dict = Body(...)):
    sym = (body.get("symbol") or "").upper().strip()
    if not sym:
        raise HTTPException(400, "symbol required")
    method = (body.get("method") or "").lower().strip() or None
    reason = body.get("reason") or ""
    source = body.get("source") or "manual"
    conn = _db.portfolio_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO skips (symbol, method, reason, source) VALUES (?, ?, ?, ?)",
        (sym, method, reason, source),
    )
    conn.commit()
    return {"ok": True, "skip_id": cur.lastrowid}


# ---- Symbol detail (chart-ready OHLCV + features) ------------------------
@app.get("/api/symbol/{symbol}")
def symbol_detail(symbol: str, days: int = 180):
    sym = symbol.upper()
    try:
        ohlcv_conn = _db.ohlcv_conn()
        feat_conn = _db.features_conn()
        df_o = pd.read_sql_query(
            "SELECT date, open, high, low, close, volume FROM ohlcv WHERE symbol=? ORDER BY date DESC LIMIT ?",
            ohlcv_conn, params=(sym, days),
        )
        df_f = pd.read_sql_query(
            "SELECT date, sma20, sma50, sma200, ema10, ema20, ema50, atr14, adv20, "
            "rsi14, ret_1d, ret_5d, ret_21d, purple_dot, purple_dot_count_30d, "
            "adr14_pct, adr20_pct, vol_ratio_20, "
            "buying_force_score, bf_score_30d_max, "
            "stage, trp_pct, inside_bar, range_contraction, "
            "high_252, low_252, minervini_pass "
            "FROM features WHERE symbol=? ORDER BY date DESC LIMIT ?",
            feat_conn, params=(sym, days),
        )
    except Exception as e:
        return {"available": False, "error": str(e)}
    if df_o.empty:
        return {"available": False}
    df = df_o.merge(df_f, on="date", how="left").sort_values("date")
    df = _scrub(df)
    universe = pd.read_csv(ROOT / "universe.csv").drop_duplicates(subset=["symbol"])
    info = universe[universe["symbol"] == sym]
    meta = info.iloc[0].to_dict() if not info.empty else {"symbol": sym}
    for k, v in list(meta.items()):
        if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            meta[k] = None
    bars = _scrub_rows(df.to_dict(orient="records"))
    return {"available": True, "meta": meta, "bars": bars}


# ---- Pipeline control -----------------------------------------------------
@app.get("/api/pipeline/status")
def pipeline_status():
    return PIPELINE_STATUS


@app.post("/api/pipeline/run")
def pipeline_run(payload: dict | None = None):
    payload = payload or {}
    max_symbols = payload.get("max_symbols")
    if PIPELINE_STATUS.get("running"):
        return {"ok": False, "msg": "pipeline already running", "status": PIPELINE_STATUS}

    def _runner():
        with PIPELINE_LOCK:
            run_pipeline.run_full_pipeline(PIPELINE_STATUS, max_symbols=max_symbols)

    t = threading.Thread(target=_runner, daemon=True)
    t.start()
    return {"ok": True, "msg": "pipeline started", "status": PIPELINE_STATUS}


# ---- Universe metadata ----------------------------------------------------
@app.get("/api/universe")
def get_universe():
    path = ROOT / "universe.csv"
    if not path.exists():
        return {"available": False, "rows": []}
    df = pd.read_csv(path).drop_duplicates(subset=["symbol"])
    sectors = sorted([s for s in df["sector"].dropna().unique().tolist()])
    df = df.astype(object).where(pd.notnull(df), None)
    rows = df.to_dict(orient="records")
    for r in rows:
        for k, v in list(r.items()):
            if isinstance(v, float) and (v != v):
                r[k] = None
    return {
        "available": True,
        "rows": rows,
        "total": int(len(df)),
        "sectors": sectors,
    }


# ---- Config view ----------------------------------------------------------
@app.get("/api/config")
def get_config():
    cfg = _config.load_config()
    # Strip any secrets / credentials
    safe = json.loads(json.dumps(cfg))
    if "fyers" in safe:
        safe["fyers"] = {k: ("***" if "token" in k.lower() else v) for k, v in safe["fyers"].items()}
    if "telegram" in safe:
        safe["telegram"] = {k: ("***" if k != "chat_id" else v) for k, v in safe["telegram"].items()}
    return safe


# ---- Pipeline backfill (real history replay) -----------------------------
@app.post("/api/pipeline/backfill")
def pipeline_backfill(payload: dict | None = None):
    """Replay regime/screen/verify/track for the past N days to seed real
    historical positions + candidates_history.csv. Idempotent."""
    payload = payload or {}
    days = int(payload.get("days", 60))
    if PIPELINE_STATUS.get("running"):
        return {"ok": False, "msg": "pipeline running — try later"}

    def _runner():
        from scripts import backfill as bf
        PIPELINE_STATUS.update({
            "running": True, "current_stage": "backfill",
            "started_at": datetime.utcnow().isoformat(),
            "finished_at": None, "error": None,
            "progress": {"done": 0, "total": days, "symbol": "", "detail": ""},
            "stages": [],
        })
        try:
            def _pcb(i, t, d, st):
                PIPELINE_STATUS["progress"] = {"done": i, "total": t, "symbol": d, "detail": st}
            res = bf.run_backfill(days, progress_cb=_pcb)
            PIPELINE_STATUS["stages"].append({
                "name": "backfill", "ok": True,
                "ts": datetime.utcnow().isoformat(), "detail": res,
            })
        except Exception as e:
            PIPELINE_STATUS["error"] = str(e)
        finally:
            PIPELINE_STATUS["running"] = False
            PIPELINE_STATUS["current_stage"] = None
            PIPELINE_STATUS["finished_at"] = datetime.utcnow().isoformat()

    threading.Thread(target=_runner, daemon=True).start()
    return {"ok": True, "msg": f"backfill started for {days} days"}
