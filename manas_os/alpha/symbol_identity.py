"""Point-in-time symbol identity + universe reconstruction, derived only from
``daily_prices`` (no external listing feed — additive, read-only over the
existing canonical price panel).

Two different things live here, deliberately kept separate:

- ``build_symbol_identity`` / the ``symbol_identity`` table: a GLOBAL summary
  (first/last seen, session count, gap stats, a trailing-gap-based delisted
  flag) computed over the *whole* panel. Useful for reference/UI/diagnostics.
  It is NOT point-in-time safe by itself — a symbol's ``last_seen`` reflects
  data that may be in the future relative to some historical ``as_of_date``.
- ``universe_on(conn, as_of_date)``: the point-in-time-safe helper. It
  re-derives first/last-seen *only* from rows with ``trade_date <= as_of_date``
  every time it is called, so it never leaks knowledge of a symbol's future
  trading history. This is the one alpha/backtest code should call.

Both treat "delisted/suspended" the same way: a symbol is presumed
delisted/suspended once its trailing gap since it last traded exceeds
``DELIST_GAP_SESSIONS`` trading sessions *within the panel's own observed
calendar* (distinct trade_date values already in daily_prices — no external
NSE holiday calendar dependency).
"""
from __future__ import annotations

import time

from .schema import ensure_schema

DELIST_GAP_SESSIONS = 30


def _log(conn, run_date: str, status: str, rows: int, started: float, detail: str) -> None:
    conn.execute(
        "INSERT INTO pipeline_runs (run_date,stage,source,status,rows_affected,duration_s,detail) "
        "VALUES (?,?,?,?,?,?,?)",
        (run_date, "alpha_symbol_identity", "alpha_shadow", status, rows, round(time.monotonic() - started, 3), detail),
    )


def build_symbol_identity(conn) -> int:
    """(Re)build the global ``symbol_identity`` summary table. Idempotent:
    fully replaces existing rows from the current ``daily_prices`` panel.

    ``trailing_gap_sessions`` is measured in the panel's own trading calendar
    (distinct trade_date count between a symbol's last_seen and the panel's
    global max trade_date). ``delisted=1`` when that gap exceeds
    ``DELIST_GAP_SESSIONS``. ``max_gap_sessions`` is the largest internal gap
    between two consecutive observed sessions for that symbol (diagnostic —
    flags suspensions mid-history, not just at the end).
    """
    ensure_schema(conn)
    global_max = conn.execute("SELECT MAX(trade_date) FROM daily_prices").fetchone()[0]
    if global_max is None:
        conn.execute("DELETE FROM symbol_identity")
        conn.commit()
        return 0

    calendar = [r[0] for r in conn.execute(
        "SELECT DISTINCT trade_date FROM daily_prices ORDER BY trade_date"
    ).fetchall()]
    cal_index = {d: i for i, d in enumerate(calendar)}
    panel_end_idx = cal_index[global_max]

    rows = conn.execute(
        "SELECT symbol, MIN(trade_date) AS first_seen, MAX(trade_date) AS last_seen, "
        "COUNT(DISTINCT trade_date) AS session_count "
        "FROM daily_prices GROUP BY symbol"
    ).fetchall()

    # Per-symbol trade dates, for internal max-gap diagnostics.
    sym_dates: dict[str, list[str]] = {}
    for r in conn.execute("SELECT DISTINCT symbol, trade_date FROM daily_prices ORDER BY symbol, trade_date"):
        sym_dates.setdefault(r["symbol"], []).append(r["trade_date"])

    out = []
    for r in rows:
        symbol, first_seen, last_seen, session_count = (
            r["symbol"], r["first_seen"], r["last_seen"], r["session_count"],
        )
        last_idx = cal_index.get(last_seen)
        trailing_gap = panel_end_idx - last_idx if last_idx is not None else 0
        delisted = 1 if trailing_gap > DELIST_GAP_SESSIONS else 0

        dates = sym_dates.get(symbol, [])
        max_gap = 0
        for a, b in zip(dates, dates[1:]):
            ia, ib = cal_index.get(a), cal_index.get(b)
            if ia is not None and ib is not None:
                max_gap = max(max_gap, ib - ia - 1)

        out.append((symbol, first_seen, last_seen, session_count, max_gap, trailing_gap, delisted))

    conn.execute("DELETE FROM symbol_identity")
    conn.executemany(
        "INSERT INTO symbol_identity "
        "(symbol, first_seen, last_seen, session_count, max_gap_sessions, trailing_gap_sessions, delisted) "
        "VALUES (?,?,?,?,?,?,?)",
        out,
    )
    conn.commit()
    return len(out)


def listing_age_sessions(conn, symbol: str, as_of_date: str) -> int | None:
    """Sessions the symbol has traded, counted only through ``as_of_date``.

    Point-in-time safe: only reads rows with trade_date <= as_of_date.
    Returns None if the symbol has no observed session at/before as_of_date.
    """
    row = conn.execute(
        "SELECT COUNT(DISTINCT trade_date) AS n FROM daily_prices "
        "WHERE symbol = ? AND trade_date <= ?",
        (symbol, as_of_date),
    ).fetchone()
    n = row["n"] if row else 0
    return n or None


def universe_on(conn, as_of_date: str) -> list[str]:
    """Point-in-time tradeable universe as of ``as_of_date``.

    Guardrail: every query here is scoped to ``trade_date <= as_of_date`` —
    it never reads a symbol's future trading history, so it is safe to call
    from inside a walk-forward backtest without look-ahead leakage.

    A symbol is included when its most recent observed session at/before
    ``as_of_date`` is within ``DELIST_GAP_SESSIONS`` sessions (measured in
    the panel's own as-of-date-scoped trading calendar) of the latest
    session observed at/before ``as_of_date`` — i.e. it was still trading
    recently as of that date, not presumed delisted/suspended.
    """
    calendar = [r[0] for r in conn.execute(
        "SELECT DISTINCT trade_date FROM daily_prices WHERE trade_date <= ? ORDER BY trade_date",
        (as_of_date,),
    ).fetchall()]
    if not calendar:
        return []
    cal_index = {d: i for i, d in enumerate(calendar)}
    panel_end_idx = len(calendar) - 1

    rows = conn.execute(
        "SELECT symbol, MAX(trade_date) AS last_seen FROM daily_prices "
        "WHERE trade_date <= ? GROUP BY symbol",
        (as_of_date,),
    ).fetchall()

    out = []
    for r in rows:
        idx = cal_index.get(r["last_seen"])
        if idx is None:
            continue
        if panel_end_idx - idx <= DELIST_GAP_SESSIONS:
            out.append(r["symbol"])
    return sorted(out)


def run(conn, run_date: str) -> dict:
    """Nightly refresh stage: rebuild the global symbol_identity summary.

    Failure-safe like the other alpha stages — a research-fabric refresh must
    never break run-eod.
    """
    started = time.monotonic()
    try:
        n = build_symbol_identity(conn)
        status = "ok" if n else "skip"
        detail = f"symbol_identity rows={n}"
        _log(conn, run_date, status, n, started, detail)
        conn.commit()
        return {"status": status, "rows": n, "detail": detail}
    except Exception as exc:  # noqa: BLE001 - research must not break run-eod
        _log(conn, run_date, "skip", 0, started, f"error: {exc}")
        conn.commit()
        return {"status": "skip", "rows": 0, "detail": str(exc)}
