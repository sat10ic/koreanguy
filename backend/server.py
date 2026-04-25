"""SwingEdge Lite — Dashboard Backend (FastAPI).

Reads pipeline outputs (SQLite + CSV + JSON) and exposes them to the React
dashboard. Also exposes endpoints to trigger the daily pipeline run.
"""
from __future__ import annotations

import json
import os
import sys
import threading
from pathlib import Path
from typing import Any
from datetime import datetime

import pandas as pd
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

# --- Load env --------------------------------------------------------------
ROOT = Path(os.environ.get("SWINGEDGE_ROOT", "/app"))
load_dotenv(Path(__file__).parent / ".env")
ROOT = Path(os.environ.get("SWINGEDGE_ROOT", "/app"))

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
        return float(x)
    except Exception:
        return None


def _safe_int(x):
    try:
        if x is None or pd.isna(x):
            return None
        return int(x)
    except Exception:
        return None


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

    # Sector breakdown — join with universe.csv for sector
    universe = pd.read_csv(ROOT / "universe.csv").drop_duplicates(subset=["symbol"])
    merged = df.merge(universe[["symbol", "sector", "industry", "name"]], on="symbol", how="left")
    sector_stats = []
    if "sector" in merged.columns:
        for sec, g in merged.groupby("sector"):
            sector_stats.append({
                "sector": sec,
                "count": int(len(g)),
                "bullish": int((g["bucket"] == "Bullish").sum()),
                "purple_dots": int(g.get("purple_dot", pd.Series([0])).sum()),
                "avg_rs_score": _safe_float(g["rs_score"].mean()) if "rs_score" in g else None,
            })
        sector_stats.sort(key=lambda r: r["count"], reverse=True)

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
    }


# ---- Screen (full graded universe) ----------------------------------------
@app.get("/api/screen")
def get_screen(
    grade: str | None = None,
    bucket: str | None = None,
    setup_only: bool = False,
    purple_dot_only: bool = False,
    watchlist_only: bool = False,
    sort_by: str = "rs_score",
    sort_desc: bool = True,
    limit: int = 600,
):
    path = OUTPUT_DIR / "screen_today.csv"
    if not path.exists():
        return {"available": False, "rows": []}
    df = pd.read_csv(path)

    universe = pd.read_csv(ROOT / "universe.csv").drop_duplicates(subset=["symbol"])
    df = df.merge(universe[["symbol", "name", "sector", "industry"]], on="symbol", how="left")

    if grade:
        df = df[df["grade"] == grade]
    if bucket:
        df = df[df["bucket"] == bucket]
    if setup_only:
        df = df[df["setup_pass"] == 1]
    if purple_dot_only:
        df = df[df["purple_dot"] == 1]
    if watchlist_only:
        df = df[df["watchlist_member"] == 1]

    if sort_by in df.columns:
        df = df.sort_values(sort_by, ascending=not sort_desc, na_position="last")

    df = df.head(limit)
    df = df.where(pd.notnull(df), None)
    return {"available": True, "rows": df.to_dict(orient="records")}


# ---- RS grid (compact view for heatmap) -----------------------------------
@app.get("/api/rs_grid")
def get_rs_grid():
    path = OUTPUT_DIR / "screen_today.csv"
    if not path.exists():
        return {"available": False, "grades": {}}
    df = pd.read_csv(path)
    universe = pd.read_csv(ROOT / "universe.csv").drop_duplicates(subset=["symbol"])
    df = df.merge(universe[["symbol", "sector"]], on="symbol", how="left")
    df = df.where(pd.notnull(df), None)

    grade_order = ["A+", "A", "A-", "B+", "B", "B-", "C+", "C", "C-",
                   "D+", "D", "D-", "E+", "E", "F", "G"]
    out = {g: [] for g in grade_order}
    for _, r in df.iterrows():
        g = r.get("grade", "G") or "G"
        if g not in out:
            out[g] = []
        out[g].append({
            "symbol": r["symbol"],
            "sector": r.get("sector"),
            "rs_score": _safe_float(r.get("rs_score")),
            "close": _safe_float(r.get("close")),
            "ret_5d": _safe_float(r.get("ret_5d")),
            "ret_21d": _safe_float(r.get("ret_21d")),
            "purple_dot": _safe_int(r.get("purple_dot")),
            "watchlist_member": _safe_int(r.get("watchlist_member")),
            "extended_yellow": _safe_int(r.get("extended_yellow")),
            "extended_red": _safe_int(r.get("extended_red")),
            "bucket": r.get("bucket"),
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
        return {"available": True, "rows": [], "summary": {}}

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

    return {"available": True, "rows": out, "summary": summary, "stats": stats}


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
        df = df.merge(
            s[["symbol", "grade", "rs_score", "close", "purple_dot",
               "purple_dot_count_30d", "extended_yellow", "extended_red", "bucket"]],
            on="symbol", how="left",
        )
    # Robust NaN -> None coercion (handles float-dtype NaN that survives df.where)
    df = df.astype(object).where(pd.notnull(df), None)

    # 5-day grade history
    history: dict[str, list[str]] = {}
    try:
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
    # Validate symbol exists in universe (avoids stale watchlist rows breaking GET)
    universe = pd.read_csv(ROOT / "universe.csv").drop_duplicates(subset=["symbol"])
    if sym not in set(universe["symbol"].tolist()):
        raise HTTPException(400, f"unknown symbol '{sym}' — not in NIFTY 500 universe")
    path = ROOT / "watchlist.csv"
    df = pd.read_csv(path) if path.exists() else pd.DataFrame(columns=["symbol", "date_added", "source_reason"])
    if sym in set(df["symbol"].tolist()):
        return {"ok": True, "msg": "already in watchlist"}
    new = pd.DataFrame([{
        "symbol": sym,
        "date_added": datetime.utcnow().strftime("%Y-%m-%d"),
        "source_reason": (payload or {}).get("reason", "manual"),
    }])
    df = pd.concat([df, new], ignore_index=True)
    df.to_csv(path, index=False)
    return {"ok": True, "added": sym}


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


# ---- SVRO arms (Phase-2 prep) --------------------------------------------
@app.get("/api/svro/arms")
def svro_arms():
    data = _read_json(OUTPUT_DIR / "svro_arm_today.json")
    if not data:
        return {"available": False}
    return {"available": True, **data}


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
            "rsi14, ret_1d, ret_5d, ret_21d, purple_dot, purple_dot_count_30d "
            "FROM features WHERE symbol=? ORDER BY date DESC LIMIT ?",
            feat_conn, params=(sym, days),
        )
    except Exception as e:
        return {"available": False, "error": str(e)}
    if df_o.empty:
        return {"available": False}
    df = df_o.merge(df_f, on="date", how="left").sort_values("date")
    df = df.where(pd.notnull(df), None)
    universe = pd.read_csv(ROOT / "universe.csv").drop_duplicates(subset=["symbol"])
    info = universe[universe["symbol"] == sym]
    meta = info.iloc[0].to_dict() if not info.empty else {"symbol": sym}
    for k, v in list(meta.items()):
        if isinstance(v, float) and pd.isna(v):
            meta[k] = None
    return {"available": True, "meta": meta, "bars": df.to_dict(orient="records")}


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
    return {
        "available": True,
        "rows": df.to_dict(orient="records"),
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
