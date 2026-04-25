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
        df = df.merge(
            s[["symbol", "grade", "rs_score", "close", "purple_dot",
               "purple_dot_count_30d", "extended_yellow", "extended_red", "bucket"]],
            on="symbol", how="left",
        )
    else:
        # Initialize columns so the fallback merge below works uniformly
        for col in ["grade", "rs_score", "close", "purple_dot",
                    "purple_dot_count_30d", "extended_yellow", "extended_red", "bucket"]:
            df[col] = None

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
                    mask = df["symbol"] == sym
                    df.loc[mask, "close"] = close_val
                    df.loc[mask, "rs_score"] = _safe_float(last_row.get("rs_score"))
                    df.loc[mask, "purple_dot"] = _safe_int(last_row.get("purple_dot"))
                    df.loc[mask, "purple_dot_count_30d"] = _safe_int(last_row.get("purple_dot_count_30d"))
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
