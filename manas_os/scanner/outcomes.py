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
    # E1-FIX (2026-07-10): stop-exit modeling for the PASSED cohort. The
    # original forward_r graded an UNMANAGED T+horizon close-to-close hold in
    # R units, which is mechanically capable of reading far worse than -1R
    # (e.g. -2.49R average) even though every plan carries a stop -- a
    # stop-honored trade cannot lose more than -1R (+ slippage) in reality.
    # These additive columns model an actually-managed exit: walk forward
    # bars from a HONEST entry (next session's open after candidate_date,
    # not the same-day/pivot price), exit at the stop the first day price
    # trades through it (low <= stop), else hold to the T+horizon close.
    for name, ddl in {
        "entry_fill": "REAL",       # next-session open used as the actual fill
        "exit_date": "TEXT",
        "exit_price": "REAL",
        "exit_reason": "TEXT",       # 'stop' | 'gap_through_stop' | 'horizon_close'
        "managed_r": "REAL",         # stop-exit-modeled R (additive; forward_r unchanged)
        "managed_mfe_r": "REAL",     # MFE/MAE over the SAME managed window (fill -> exit/horizon)
        "managed_mae_r": "REAL",
        "hit_1r": "INTEGER",         # did +1R print before the stop, within the window
        "hit_2r": "INTEGER",
    }.items():
        if name not in outcomes_have:
            conn.execute(f"ALTER TABLE outcomes ADD COLUMN {name} {ddl}")
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


STOP_SLIPPAGE_PCT = 0.002  # 0.2% haircut on a stop fill (real fills rarely print exactly at the stop)


def _managed_exit(
    conn, symbol: str, candidate_date: str, horizon: int,
    plan_entry: float | None, stop: float | None,
) -> dict[str, Any] | None:
    """Model an actually-managed exit for the PASSED cohort (E1-FIX 2026-07-10).

    Honest fill: the candidate is a signal generated ON candidate_date, so the
    fill is the NEXT session's open (not same-day/pivot price, which is what
    the original `forward_r` implicitly assumed and cannot have been filled at
    in a live system).

    R unit: BOTH the risk-per-share denominator AND the reference price in
    the R numerator are the PLANNED entry/stop from the candidate's own plan
    -- not re-derived from the actual fill. This is deliberate: R is measured
    against what the plan set out to risk, so a name that gaps through its
    planned stop before the fill even happens is a real, honest outcome (it
    prints far worse than -1R) rather than being silently dropped OR having
    the gap cost hidden by resetting the reference price to the bad fill
    (which would make an entry that gapped 20% down and went nowhere read as
    ~breakeven -- technically true of the realized P&L from that fill, but it
    launders the entry-gap cost the gate's plan never priced in). The actual
    fill (next session's open) is recorded separately in `entry_fill` purely
    as a diagnostic of realized slippage from plan.

    Walks forward `horizon` sessions from the fill bar. Each day, the STOP
    check is applied before the favorable-excursion check (a conservative,
    documented convention -- without intraday sequencing we cannot know
    whether the stop or a favorable print came first within a single bar, so
    the stop is assumed to have triggered first):
      - gap-through-stop: the day's open is already <= stop -> exit at that
        open (haircut further by STOP_SLIPPAGE_PCT), recorded honestly even
        when it prints worse than -1R.
      - low <= stop (no gap): exit at stop * (1 - STOP_SLIPPAGE_PCT).
      - neither: track running MFE/MAE in R and hit_1r/hit_2r, continue.
    If the stop is never touched within the window, exits at the T+horizon
    close ("horizon_close").

    Returns None when there isn't a full window of bars yet (still pending)
    or the plan itself is invalid (missing entry/stop, or stop >= entry).
    """
    if stop is None or plan_entry is None:
        return None
    risk = float(plan_entry) - float(stop)
    if risk <= 0:
        return None  # stop above entry -- not a valid long risk plan; skip managed modeling
    entry_row = conn.execute(
        "SELECT trade_date, open FROM daily_prices WHERE symbol = ? AND series = 'EQ' "
        "AND trade_date > ? AND open IS NOT NULL ORDER BY trade_date ASC LIMIT 1",
        (symbol, candidate_date),
    ).fetchone()
    if not entry_row:
        return None
    entry_date, fill = entry_row["trade_date"], float(entry_row["open"])
    plan_entry_f = float(plan_entry)

    bars = conn.execute(
        "SELECT trade_date, open, high, low, close FROM daily_prices WHERE symbol = ? "
        "AND series = 'EQ' AND trade_date >= ? AND open IS NOT NULL AND high IS NOT NULL "
        "AND low IS NOT NULL AND close IS NOT NULL ORDER BY trade_date ASC LIMIT ?",
        (symbol, entry_date, horizon),
    ).fetchall()
    if len(bars) < horizon:
        return None  # window not complete yet

    stop_f = float(stop)
    running_mfe_r: float | None = None
    running_mae_r: float | None = None
    hit_1r = False
    hit_2r = False
    for bar in bars:
        o, h, low, c = float(bar["open"]), float(bar["high"]), float(bar["low"]), float(bar["close"])
        if o <= stop_f:
            exit_price = o * (1.0 - STOP_SLIPPAGE_PCT)
            r = (exit_price - plan_entry_f) / risk
            running_mae_r = r if running_mae_r is None else min(running_mae_r, r)
            return {
                "entry_fill": round(fill, 2), "entry_date": entry_date,
                "exit_date": bar["trade_date"], "exit_price": round(exit_price, 2),
                "exit_reason": "gap_through_stop", "managed_r": round(r, 3),
                "managed_mfe_r": round(running_mfe_r, 3) if running_mfe_r is not None else round(r, 3),
                "managed_mae_r": round(running_mae_r, 3),
                "hit_1r": int(hit_1r), "hit_2r": int(hit_2r),
            }
        if low <= stop_f:
            exit_price = stop_f * (1.0 - STOP_SLIPPAGE_PCT)
            r = (exit_price - plan_entry_f) / risk
            bar_mae_r = (low - plan_entry_f) / risk
            running_mae_r = bar_mae_r if running_mae_r is None else min(running_mae_r, bar_mae_r)
            return {
                "entry_fill": round(fill, 2), "entry_date": entry_date,
                "exit_date": bar["trade_date"], "exit_price": round(exit_price, 2),
                "exit_reason": "stop", "managed_r": round(r, 3),
                "managed_mfe_r": round(running_mfe_r, 3) if running_mfe_r is not None else round(r, 3),
                "managed_mae_r": round(running_mae_r, 3),
                "hit_1r": int(hit_1r), "hit_2r": int(hit_2r),
            }
        bar_mfe_r = (h - plan_entry_f) / risk
        bar_mae_r = (low - plan_entry_f) / risk
        running_mfe_r = bar_mfe_r if running_mfe_r is None else max(running_mfe_r, bar_mfe_r)
        running_mae_r = bar_mae_r if running_mae_r is None else min(running_mae_r, bar_mae_r)
        if bar_mfe_r >= 1.0:
            hit_1r = True
        if bar_mfe_r >= 2.0:
            hit_2r = True

    last = bars[-1]
    close = float(last["close"])
    r = (close - plan_entry_f) / risk
    return {
        "entry_fill": round(fill, 2), "entry_date": entry_date,
        "exit_date": last["trade_date"], "exit_price": round(close, 2),
        "exit_reason": "horizon_close", "managed_r": round(r, 3),
        "managed_mfe_r": round(running_mfe_r, 3) if running_mfe_r is not None else round(r, 3),
        "managed_mae_r": round(running_mae_r, 3) if running_mae_r is not None else round(r, 3),
        "hit_1r": int(hit_1r), "hit_2r": int(hit_2r),
    }


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
            # E1-FIX: stop-exit-managed exit modeling, additive to the legacy
            # unmanaged forward_r above. None while the window is incomplete.
            managed = _managed_exit(conn, c["symbol"], c["candidate_date"], horizon, base, stop)
            conn.execute(
                "INSERT INTO outcomes (candidate_date, symbol, setup, horizon, as_of_date, "
                "forward_return_pct, forward_r, mfe_r, mae_r, status, updated_at, "
                "entry_fill, exit_date, exit_price, exit_reason, managed_r, "
                "managed_mfe_r, managed_mae_r, hit_1r, hit_2r) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), ?, ?, ?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(candidate_date, symbol, setup, horizon) DO UPDATE SET "
                "as_of_date=excluded.as_of_date, "
                "forward_return_pct=excluded.forward_return_pct, "
                "forward_r=excluded.forward_r, "
                "mfe_r=excluded.mfe_r, mae_r=excluded.mae_r, "
                "status=excluded.status, "
                "updated_at=datetime('now'), "
                "entry_fill=excluded.entry_fill, exit_date=excluded.exit_date, "
                "exit_price=excluded.exit_price, exit_reason=excluded.exit_reason, "
                "managed_r=excluded.managed_r, managed_mfe_r=excluded.managed_mfe_r, "
                "managed_mae_r=excluded.managed_mae_r, hit_1r=excluded.hit_1r, hit_2r=excluded.hit_2r",
                (
                    c["candidate_date"], c["symbol"], c["setup"], horizon, as_of_date, fwd_pct, fwd_r, mfe_r, mae_r, status,
                    managed["entry_fill"] if managed else None,
                    managed["exit_date"] if managed else None,
                    managed["exit_price"] if managed else None,
                    managed["exit_reason"] if managed else None,
                    managed["managed_r"] if managed else None,
                    managed["managed_mfe_r"] if managed else None,
                    managed["managed_mae_r"] if managed else None,
                    managed["hit_1r"] if managed else None,
                    managed["hit_2r"] if managed else None,
                ),
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
