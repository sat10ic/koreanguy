"""Forward-return outcome plumbing for persisted setup candidates.

This is deliberately narrow: copy scanner candidates into the durable
`candidates` table, then backfill T+5/T+10/T+20 returns from daily_prices.
No weekly retro engine, no learnings file.
"""
from __future__ import annotations

from typing import Any
import json
import time

STAGE = "candidate_outcomes"
SOURCE = "scan_candidates+daily_prices"
HORIZONS = (5, 10, 20)


def ensure_schema(conn) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS candidates ("
        "candidate_date TEXT NOT NULL, symbol TEXT NOT NULL, setup TEXT NOT NULL, "
        "readiness REAL, grade TEXT, entry REAL, stop REAL, sector TEXT, industry TEXT, "
        "rr REAL, suggested_qty INTEGER, "
        "source_payload_json TEXT, created_at TEXT DEFAULT (datetime('now')), "
        "PRIMARY KEY (candidate_date, symbol, setup))"
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_candidates_date ON candidates(candidate_date)")
    have = {r[1] for r in conn.execute("PRAGMA table_info(candidates)")}
    for name, ddl in {"rr": "REAL", "suggested_qty": "INTEGER"}.items():
        if name not in have:
            conn.execute(f"ALTER TABLE candidates ADD COLUMN {name} {ddl}")
    conn.execute(
        "CREATE TABLE IF NOT EXISTS outcomes ("
        "candidate_date TEXT NOT NULL, symbol TEXT NOT NULL, setup TEXT NOT NULL, "
        "horizon INTEGER NOT NULL, as_of_date TEXT, forward_return_pct REAL, "
        "forward_r REAL, status TEXT NOT NULL DEFAULT 'pending', "
        "updated_at TEXT DEFAULT (datetime('now')), "
        "PRIMARY KEY (candidate_date, symbol, setup, horizon), "
        "FOREIGN KEY (candidate_date, symbol, setup) REFERENCES "
        "candidates(candidate_date, symbol, setup) ON DELETE CASCADE)"
    )
    # W1.4: per-candidate MFE/MAE in R (max favorable / adverse excursion over
    # the horizon, vs the plan stop). Additive columns; backfilled for every
    # completed row. Unblocks the Journal MFE/MAE scatter.
    outcomes_have = {r[1] for r in conn.execute("PRAGMA table_info(outcomes)")}
    for name in ("mfe_r", "mae_r"):
        if name not in outcomes_have:
            conn.execute(f"ALTER TABLE outcomes ADD COLUMN {name} REAL")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_outcomes_status ON outcomes(status, horizon)")


def ensure_setup_decisions_schema(conn) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS setup_decisions ("
        "scan_date TEXT, symbol TEXT, decision TEXT, skip_reason TEXT, "
        "entry_price REAL, qty INTEGER, snapshot_json TEXT, "
        "created_at TEXT DEFAULT (datetime('now')), "
        "PRIMARY KEY(scan_date, symbol))"
    )


def persist_candidate_snapshot(conn, candidate_date: str, candidate: dict[str, Any]) -> None:
    """Mirror one visible setup candidate into the durable outcomes seed table."""
    ensure_schema(conn)
    payload = {
        k: v
        for k, v in candidate.items()
        if k not in {"source_payload_json"}
    }
    conn.execute(
        "INSERT INTO candidates (candidate_date, symbol, setup, readiness, grade, entry, "
        "stop, sector, industry, rr, suggested_qty, source_payload_json) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
        "ON CONFLICT(candidate_date, symbol, setup) DO UPDATE SET "
        "readiness=excluded.readiness, grade=excluded.grade, entry=excluded.entry, "
        "stop=excluded.stop, sector=excluded.sector, industry=excluded.industry, "
        "rr=excluded.rr, suggested_qty=excluded.suggested_qty, "
        "source_payload_json=excluded.source_payload_json",
        (
            candidate_date,
            str(candidate["symbol"]).upper(),
            candidate["setup"],
            candidate.get("readiness"),
            candidate.get("grade"),
            candidate.get("entry"),
            candidate.get("stop"),
            candidate.get("sector"),
            candidate.get("industry"),
            candidate.get("rr"),
            candidate.get("suggested_qty"),
            json.dumps(payload, sort_keys=True),
        ),
    )
    for horizon in HORIZONS:
        conn.execute(
            "INSERT OR IGNORE INTO outcomes "
            "(candidate_date, symbol, setup, horizon, status) VALUES (?, ?, ?, ?, 'pending')",
            (candidate_date, str(candidate["symbol"]).upper(), candidate["setup"], horizon),
        )


def _candidate_day_close(conn, symbol: str, candidate_date: str) -> float | None:
    row = conn.execute(
        "SELECT close FROM daily_prices WHERE symbol = ? AND series = 'EQ' "
        "AND trade_date <= ? ORDER BY trade_date DESC LIMIT 1",
        (symbol, candidate_date),
    ).fetchone()
    return None if not row or row["close"] is None else float(row["close"])


def _horizon_close(conn, symbol: str, candidate_date: str, horizon: int) -> tuple[str, float] | None:
    row = conn.execute(
        "SELECT trade_date, close FROM daily_prices WHERE symbol = ? AND series = 'EQ' "
        "AND trade_date > ? AND close IS NOT NULL ORDER BY trade_date ASC LIMIT 1 OFFSET ?",
        (symbol, candidate_date, horizon - 1),
    ).fetchone()
    if not row:
        return None
    return row["trade_date"], float(row["close"])


def _horizon_excursion_r(
    conn, symbol: str, candidate_date: str, horizon: int, entry: float, risk: float
) -> tuple[float | None, float | None]:
    """Max favorable / adverse excursion in R over the horizon window
    (the `horizon` sessions after candidate_date). MFE = (max high - entry)/risk;
    MAE = (min low - entry)/risk (negative when the low is below entry). Returns
    (mfe_r, mae_r), both None when there isn't a full window of bars."""
    rows = conn.execute(
        "SELECT high, low FROM daily_prices WHERE symbol = ? AND series = 'EQ' "
        "AND trade_date > ? AND high IS NOT NULL AND low IS NOT NULL "
        "ORDER BY trade_date ASC LIMIT ?",
        (symbol, candidate_date, horizon),
    ).fetchall()
    if len(rows) < horizon or risk <= 0:
        return None, None
    highs = [float(r["high"]) for r in rows]
    lows = [float(r["low"]) for r in rows]
    mfe_r = round((max(highs) - entry) / risk, 2)
    mae_r = round((min(lows) - entry) / risk, 2)
    return mfe_r, mae_r


def backfill_forward_returns(conn, through_date: str | None = None) -> int:
    """Fill all currently-computable T+N outcomes.

    `through_date` bounds candidates considered by date only; the horizon still
    requires enough daily_prices rows after each candidate date.
    """
    ensure_schema(conn)
    where = "WHERE candidate_date <= ?" if through_date else ""
    params: tuple[Any, ...] = (through_date,) if through_date else ()
    rows = conn.execute(
        "SELECT candidate_date, symbol, setup, entry, stop FROM candidates "
        f"{where} ORDER BY candidate_date, symbol, setup",
        params,
    ).fetchall()
    written = 0
    for c in rows:
        base = c["entry"] if c["entry"] is not None else _candidate_day_close(conn, c["symbol"], c["candidate_date"])
        stop = c["stop"]
        risk = (float(base) - float(stop)) if base is not None and stop is not None else None
        for horizon in HORIZONS:
            target = _horizon_close(conn, c["symbol"], c["candidate_date"], horizon)
            if base is None or target is None:
                status = "pending"
                as_of_date = None
                fwd_pct = None
                fwd_r = None
                mfe_r = None
                mae_r = None
            else:
                as_of_date, close = target
                fwd_pct = round((close - float(base)) / float(base) * 100.0, 2)
                fwd_r = round((close - float(base)) / risk, 2) if risk and risk > 0 else None
                # W1.4: MFE/MAE in R over the same horizon window.
                if risk and risk > 0:
                    mfe_r, mae_r = _horizon_excursion_r(
                        conn, c["symbol"], c["candidate_date"], horizon, float(base), risk
                    )
                else:
                    mfe_r, mae_r = None, None
                status = "complete"
            conn.execute(
                "INSERT INTO outcomes (candidate_date, symbol, setup, horizon, as_of_date, "
                "forward_return_pct, forward_r, mfe_r, mae_r, status, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now')) "
                "ON CONFLICT(candidate_date, symbol, setup, horizon) DO UPDATE SET "
                "as_of_date=excluded.as_of_date, "
                "forward_return_pct=excluded.forward_return_pct, "
                "forward_r=excluded.forward_r, "
                "mfe_r=excluded.mfe_r, mae_r=excluded.mae_r, "
                "status=excluded.status, "
                "updated_at=datetime('now')",
                (c["candidate_date"], c["symbol"], c["setup"], horizon, as_of_date, fwd_pct, fwd_r, mfe_r, mae_r, status),
            )
            written += 1
    return written


def run(conn, run_date: str) -> dict[str, Any]:
    started = time.monotonic()
    try:
        written = backfill_forward_returns(conn, through_date=run_date)
        complete = conn.execute("SELECT COUNT(*) FROM outcomes WHERE status = 'complete'").fetchone()[0]
        conn.execute(
            "INSERT INTO pipeline_runs (run_date, stage, source, status, rows_affected, "
            "duration_s, detail) VALUES (?, ?, ?, 'ok', ?, ?, ?)",
            (
                run_date,
                STAGE,
                SOURCE,
                written,
                round(time.monotonic() - started, 3),
                f"outcomes_checked={written} complete={complete}",
            ),
        )
        conn.commit()
        return {"status": "ok", "rows": written, "complete": complete}
    except Exception as exc:  # noqa: BLE001
        conn.execute(
            "INSERT INTO pipeline_runs (run_date, stage, source, status, rows_affected, "
            "duration_s, detail) VALUES (?, ?, ?, 'fail', 0, ?, ?)",
            (run_date, STAGE, SOURCE, round(time.monotonic() - started, 3), str(exc)),
        )
        conn.commit()
        return {"status": "fail", "rows": 0, "detail": str(exc)}
