"""regime_daily orchestration — wires adopted/xp.py + adopted/mbi.py to the DB.

Original TraderLog code, written 2026-08-23 for W4. Not copied from a single
manas_os source; it is the glue the two adopted reverse-engineering modules
need to populate ``regime_daily`` in strict date order. See CANONICAL.md §5,
DECISIONS.md 2026-08-23 "Adopt the XP and MBI scores, but not the regime
governor", and ``adopted/xp.py`` for the gap-handling rationale this module
depends on.

XP is a recursion: ``backfill`` MUST process ``breadth_daily`` dates in
strict ascending order (never sparsely, never in parallel) or the recursion
chain is meaningless. ``run(conn, one_date)`` exists for a single date but a
caller feeding it dates out of order will silently get a wrong recursion —
this module cannot detect that from a single call, only ``backfill`` can
guarantee order.
"""
from __future__ import annotations

import time

from traderlog.adopted import mbi as mbi_mod
from traderlog.adopted.xp import DEFAULT_GAP_THRESHOLD_DAYS, xp_for_date
from traderlog.db import now_iso

STAGE = "adopted.regime_daily"


def compute_regime_row(
    conn, trade_date: str, seeds: dict | None = None,
    gap_threshold_days: int = DEFAULT_GAP_THRESHOLD_DAYS,
) -> dict | None:
    """Build the full regime_daily row for trade_date, or None if no breadth_daily row.

    Callers of ``backfill`` never need this directly; it is exposed for tests
    and for a single-date recompute (which is exactly the determinism
    done-test: recompute a known date twice, using the DB's own persisted
    prior row both times, and get the identical value).
    """
    row = conn.execute(
        "SELECT * FROM breadth_daily WHERE trade_date = ?", (trade_date,)
    ).fetchone()
    if row is None:
        return None
    row = dict(row)

    xp_value, xp_z_state, reseeded = xp_for_date(
        conn, trade_date, seeds=seeds, gap_threshold_days=gap_threshold_days
    )
    mbi = mbi_mod.compute_mbi(row)

    return {
        "trade_date": trade_date,
        "xp_value": xp_value,
        "xp_z_state": xp_z_state,
        "xp_band": mbi_mod.xp_band(xp_value),
        "r10": mbi["r10"],
        "r20": mbi["r20"],
        "r50": mbi["r50"],
        "r4p5": mbi["r4p5"],
        "band_r10": mbi["bands"]["r10"],
        "band_r20": mbi["bands"]["r20"],
        "band_r50": mbi["bands"]["r50"],
        "band_r4p5": mbi["bands"]["r4p5"],
        "mbi_day_color": mbi["mbi_day_color"],
        "mbi_score": mbi["score"],
        "warning_day": int(bool(mbi["warning_day"])),
        "source_date": trade_date,
        "reseeded": reseeded,  # not a column; consumed by run()/backfill() for logging only
    }


def _upsert(conn, r: dict) -> None:
    conn.execute(
        "INSERT INTO regime_daily (trade_date, xp_value, xp_z_state, xp_band, "
        "r10, r20, r50, r4p5, band_r10, band_r20, band_r50, band_r4p5, "
        "mbi_day_color, mbi_score, warning_day, source_date, ingested_at) "
        "VALUES (:trade_date, :xp_value, :xp_z_state, :xp_band, "
        ":r10, :r20, :r50, :r4p5, :band_r10, :band_r20, :band_r50, :band_r4p5, "
        ":mbi_day_color, :mbi_score, :warning_day, :source_date, :ingested_at) "
        "ON CONFLICT(trade_date) DO UPDATE SET "
        "xp_value=excluded.xp_value, xp_z_state=excluded.xp_z_state, xp_band=excluded.xp_band, "
        "r10=excluded.r10, r20=excluded.r20, r50=excluded.r50, r4p5=excluded.r4p5, "
        "band_r10=excluded.band_r10, band_r20=excluded.band_r20, "
        "band_r50=excluded.band_r50, band_r4p5=excluded.band_r4p5, "
        "mbi_day_color=excluded.mbi_day_color, mbi_score=excluded.mbi_score, "
        "warning_day=excluded.warning_day, source_date=excluded.source_date, "
        "ingested_at=excluded.ingested_at",
        {**{k: v for k, v in r.items() if k != "reseeded"}, "ingested_at": now_iso()},
    )


def _log_run(conn, run_date: str, status: str, rows: int, dur: float, detail: str) -> None:
    conn.execute(
        "INSERT INTO pipeline_runs (stage, run_date, status, rows, duration_ms, detail, ts) "
        "VALUES (?,?,?,?,?,?,?)",
        (STAGE, run_date, status, rows, int(dur * 1000), detail, now_iso()),
    )


def run(
    conn, run_date: str, seeds: dict | None = None,
    gap_threshold_days: int = DEFAULT_GAP_THRESHOLD_DAYS,
) -> dict:
    """Compute + persist one regime_daily row. Never raises.

    Caller is responsible for ascending-date ordering when backfilling — see
    ``backfill``.
    """
    started = time.monotonic()
    try:
        row = compute_regime_row(conn, run_date, seeds=seeds, gap_threshold_days=gap_threshold_days)
        if row is None:
            detail = f"no breadth_daily row for {run_date}"
            _log_run(conn, run_date, "skip", 0, time.monotonic() - started, detail)
            conn.commit()
            return {"status": "skip", "rows": 0, "detail": detail}
        _upsert(conn, row)
        detail = (
            f"xp={row['xp_value']:.2f} band={row['xp_band']} "
            f"mbi={row['mbi_day_color']} score={row['mbi_score']}"
            + (" RESEEDED (chain break)" if row["reseeded"] else "")
        )
        _log_run(conn, run_date, "ok", 1, time.monotonic() - started, detail)
        conn.commit()
        return {"status": "ok", "rows": 1, "detail": detail, "reseeded": row["reseeded"]}
    except Exception as exc:  # noqa: BLE001
        _log_run(conn, run_date, "fail", 0, time.monotonic() - started, f"{type(exc).__name__}: {exc}")
        conn.commit()
        return {"status": "fail", "rows": 0, "detail": str(exc)}


def backfill(
    conn, dates: list[str] | None = None, seeds: dict | None = None,
    gap_threshold_days: int = DEFAULT_GAP_THRESHOLD_DAYS,
) -> dict:
    """Populate regime_daily for every breadth_daily date, in strict ascending order.

    Returns {"dates": n, "ok": n, "skipped": n, "failed": [dates], "reseed_points": [dates]}.
    """
    if dates is None:
        dates = [
            r[0] for r in conn.execute(
                "SELECT trade_date FROM breadth_daily ORDER BY trade_date ASC"
            ).fetchall()
        ]
    else:
        dates = sorted(dates)

    ok = skipped = 0
    failed: list[str] = []
    reseed_points: list[str] = []
    for d in dates:
        result = run(conn, d, seeds=seeds, gap_threshold_days=gap_threshold_days)
        if result["status"] == "ok":
            ok += 1
            if result.get("reseeded"):
                reseed_points.append(d)
        elif result["status"] == "skip":
            skipped += 1
        else:
            failed.append(d)
    return {
        "dates": len(dates), "ok": ok, "skipped": skipped,
        "failed": failed, "reseed_points": reseed_points,
    }
