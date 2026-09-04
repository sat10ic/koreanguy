"""Scratch driver for Round-4 EVIDENCE replays -- NOT part of the shipped
package (repo root scratch file per existing convention, e.g. _cohort_study.py).
Reuses the persisted candidates/outcomes cohort (n=55 @ horizon=10) and
manas_os.backtest.exit_variants to recompute managed outcomes under each
variant. Read-only against manas_os/data/manas.db.
"""
import sqlite3
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from manas_os.backtest import exit_variants as ev

DB = "manas_os/data/manas.db"
HORIZON = 10


def regime_for(conn, session_date):
    row = conn.execute(
        "SELECT market_mode FROM regime_snapshots WHERE snapshot_date <= ? "
        "ORDER BY snapshot_date DESC LIMIT 1",
        (session_date,),
    ).fetchone()
    return row[0] if row and row[0] else "UNKNOWN"


def setup_family(setup):
    return str(setup).strip().lower().replace(" ", "_").replace("-", "_")


def load_cohort(conn):
    """The SAME n=55 cohort as the E1 audit: candidates with a complete
    horizon=10 managed outcome today (i.e. a full T+10 window exists)."""
    rows = conn.execute(
        "SELECT c.candidate_date, c.symbol, c.setup, c.entry, c.stop "
        "FROM candidates c JOIN outcomes o "
        "ON c.candidate_date=o.candidate_date AND c.symbol=o.symbol AND c.setup=o.setup "
        "WHERE o.horizon=? AND o.managed_r IS NOT NULL",
        (HORIZON,),
    ).fetchall()
    return rows


def bars_from(conn, symbol, candidate_date, min_needed=40):
    rows = conn.execute(
        "SELECT trade_date, open, high, low, close FROM daily_prices "
        "WHERE symbol=? AND series='EQ' AND trade_date > ? AND open IS NOT NULL "
        "AND high IS NOT NULL AND low IS NOT NULL AND close IS NOT NULL "
        "ORDER BY trade_date ASC LIMIT ?",
        (symbol, candidate_date, min_needed),
    ).fetchall()
    return [
        {"trade_date": r[0], "open": r[1], "high": r[2], "low": r[3], "close": r[4]}
        for r in rows
    ]


def run_variant(conn, cohort, stop_multiplier, entry_mode):
    obs = []  # list of dict: family, regime, r, exit_reason, mfe, mae, hit1r, skipped
    skips = 0
    for cand_date, symbol, setup, entry, stop in cohort:
        if entry is None or stop is None:
            continue
        bars = bars_from(conn, symbol, cand_date)
        out = ev.walk_managed_exit(
            bars, float(entry), float(stop), HORIZON,
            stop_multiplier=stop_multiplier, entry_mode=entry_mode,
        )
        if out is None:
            continue  # incomplete window (shouldn't happen for this fixed cohort)
        if out.get("skipped"):
            skips += 1
            continue
        obs.append({
            "family": setup_family(setup),
            "regime": regime_for(conn, cand_date),
            "r": out["managed_r"],
            "exit_reason": out["exit_reason"],
            "mfe": out["managed_mfe_r"],
            "mae": out["managed_mae_r"],
            "hit_1r": out["hit_1r"],
        })
    return obs, skips


def summarize(obs, label):
    lines = [f"\n=== {label} (n={len(obs)}) ==="]
    if not obs:
        lines.append("(no observations)")
        return "\n".join(lines)
    by_family = defaultdict(list)
    for o in obs:
        by_family[o["family"]].append(o)
    header = f"{'family':<18} {'n':>4} {'stopout%':>9} {'avgR':>7} {'medR':>7} {'avgMFE':>7} {'avgMAE':>7} {'hit1r%':>7}"
    lines.append(header)
    lines.append("-" * len(header))
    for fam, rows in sorted(by_family.items()):
        n = len(rows)
        stopout = sum(1 for r in rows if r["exit_reason"] in ("stop", "gap_through_stop")) / n * 100
        avgr = sum(r["r"] for r in rows) / n
        medr = st.median(r["r"] for r in rows)
        avgmfe = sum(r["mfe"] for r in rows) / n
        avgmae = sum(r["mae"] for r in rows) / n
        hit1r = sum(r["hit_1r"] for r in rows) / n * 100
        lines.append(f"{fam:<18} {n:>4} {stopout:>8.1f}% {avgr:>7.2f} {medr:>7.2f} {avgmfe:>7.2f} {avgmae:>7.2f} {hit1r:>6.1f}%")
    n = len(obs)
    stopout = sum(1 for r in obs if r["exit_reason"] in ("stop", "gap_through_stop")) / n * 100
    avgr = sum(r["r"] for r in obs) / n
    medr = st.median(r["r"] for r in obs)
    avgmfe = sum(r["mfe"] for r in obs) / n
    avgmae = sum(r["mae"] for r in obs) / n
    hit1r = sum(r["hit_1r"] for r in obs) / n * 100
    lines.append("-" * len(header))
    lines.append(f"{'ALL':<18} {n:>4} {stopout:>8.1f}% {avgr:>7.2f} {medr:>7.2f} {avgmfe:>7.2f} {avgmae:>7.2f} {hit1r:>6.1f}%")
    return "\n".join(lines)


def summarize_by_regime(obs, label):
    lines = [f"\n=== {label} by regime ==="]
    by_regime = defaultdict(list)
    for o in obs:
        by_regime[o["regime"]].append(o)
    header = f"{'regime':<12} {'n':>4} {'stopout%':>9} {'avgR':>7} {'medR':>7} {'avgMFE':>7} {'avgMAE':>7} {'hit1r%':>7}"
    lines.append(header)
    lines.append("-" * len(header))
    for regime, rows in sorted(by_regime.items()):
        n = len(rows)
        stopout = sum(1 for r in rows if r["exit_reason"] in ("stop", "gap_through_stop")) / n * 100
        avgr = sum(r["r"] for r in rows) / n
        medr = st.median(r["r"] for r in rows)
        avgmfe = sum(r["mfe"] for r in rows) / n
        avgmae = sum(r["mae"] for r in rows) / n
        hit1r = sum(r["hit_1r"] for r in rows) / n * 100
        lines.append(f"{regime:<12} {n:>4} {stopout:>8.1f}% {avgr:>7.2f} {medr:>7.2f} {avgmfe:>7.2f} {avgmae:>7.2f} {hit1r:>6.1f}%")
    return "\n".join(lines)


def main():
    conn = sqlite3.connect(DB)
    cohort = load_cohort(conn)
    print(f"cohort n={len(cohort)}")

    out = []
    obs_by_mult = {}
    for mult in (1.0, 1.5, 2.0):
        obs, skips = run_variant(conn, cohort, stop_multiplier=mult, entry_mode="next_open")
        obs_by_mult[mult] = obs
        out.append(summarize(obs, f"E-A stop_mult={mult} entry=next_open"))
    print("\n".join(out))

    obs_next = obs_by_mult[1.0]
    obs_buystop, skips_buystop = run_variant(conn, cohort, stop_multiplier=1.0, entry_mode="buy_stop")
    print(summarize(obs_next, "E-B entry=next_open (baseline, same as E-A x1.0)"))
    print(summarize(obs_buystop, f"E-B entry=buy_stop (skipped={skips_buystop})"))

    for mult in (1.5, 2.0):
        obs_c, skips_c = run_variant(conn, cohort, stop_multiplier=mult, entry_mode="buy_stop")
        print(summarize(obs_c, f"E-C stop_mult={mult} entry=buy_stop (skipped={skips_c})"))

    print(summarize_by_regime(obs_next, "baseline (x1.0/next_open)"))
    print(summarize_by_regime(obs_by_mult[2.0], "E-A x2.0/next_open"))
    print(summarize_by_regime(obs_buystop, "E-B buy_stop/x1.0"))


if __name__ == "__main__":
    main()
