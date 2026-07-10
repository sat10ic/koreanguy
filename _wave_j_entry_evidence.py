"""Scratch driver for WAVE_J J3 EVIDENCE replays -- NOT part of the shipped
package (repo-root scratch, mirrors _gate_recal_evidence.py). Reuses the
persisted candidates/outcomes cohort (n=55 @ horizon=10) and composes
manas_os.backtest.entry_variants counterfactual entry-quality refusals
(H1/H2/H3/H4/H5/H6) over it, re-walking managed exits via
manas_os.backtest.exit_variants. Read-only against manas_os/data/manas.db.
Prints all tables; persists nothing (WAVE_J_SPEC.md J3).
"""
import sqlite3
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from manas_os.backtest import entry_variants as env
from manas_os.backtest import exit_variants as ev

DB = "manas_os/data/manas.db"
HORIZON = 10
INDICATOR_BAR_LIMIT = 420
INDEX_SYMBOL = "NIFTYMIDSML400"  # WAVE_J_SPEC H5; same benchmark as
                                  # scanner/candidates.py _index_return_63d and
                                  # agents/context_pack.py MSWING_INDEX_SYMBOLS

VARIANTS = [
    ("baseline", set()),
    ("H1", {"H1"}),
    ("H2", {"H2"}),
    ("H3", {"H3"}),
    ("H1+H2", {"H1", "H2"}),
    ("H1+H2+H3", {"H1", "H2", "H3"}),
    ("H1+H2+H3+H4", {"H1", "H2", "H3", "H4"}),
    ("H1+H2+H3+H4+H5", {"H1", "H2", "H3", "H4", "H5"}),
    ("H1+H2+H3+H4+H5+H6", {"H1", "H2", "H3", "H4", "H5", "H6"}),
]

SUBWINDOWS = [
    ("2025-03..2025-12", "2025-03-01", "2025-12-31"),
    ("2026-01..2026-07", "2026-01-01", "2026-07-31"),
]


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
    """The SAME n=55 cohort as E1/gate-recal: candidates with a complete
    horizon=10 managed outcome today (i.e. a full T+10 window exists)."""
    rows = conn.execute(
        "SELECT c.candidate_date, c.symbol, c.setup, c.entry, c.stop "
        "FROM candidates c JOIN outcomes o "
        "ON c.candidate_date=o.candidate_date AND c.symbol=o.symbol AND c.setup=o.setup "
        "WHERE o.horizon=? AND o.managed_r IS NOT NULL",
        (HORIZON,),
    ).fetchall()
    return rows


def trigger_bars_for(conn, symbol, candidate_date):
    """Bars strictly AT/BEFORE candidate_date (the trigger/signal day is the
    last element) -- oldest-first, mirroring agents/context_pack.py's own
    DESC-then-reverse convention and bar limit. Used ONLY by entry_quality
    refusals (no look-ahead)."""
    rows = conn.execute(
        "SELECT trade_date, open, high, low, close FROM daily_prices "
        "WHERE symbol=? AND series='EQ' AND trade_date <= ? AND open IS NOT NULL "
        "AND high IS NOT NULL AND low IS NOT NULL AND close IS NOT NULL "
        "ORDER BY trade_date DESC LIMIT ?",
        (symbol, candidate_date, INDICATOR_BAR_LIMIT),
    ).fetchall()
    rows = list(reversed(rows))
    return [
        {"trade_date": r[0], "open": r[1], "high": r[2], "low": r[3], "close": r[4]}
        for r in rows
    ]


def index_bars_for(conn, candidate_date):
    """H5 mswing benchmark bars (close-only is sufficient -- mi.mswing only
    reads _closes()). At/before candidate_date, oldest-first."""
    rows = conn.execute(
        "SELECT trade_date, close FROM sector_index_prices "
        "WHERE symbol=? AND trade_date<=? AND close IS NOT NULL "
        "ORDER BY trade_date DESC LIMIT ?",
        (INDEX_SYMBOL, candidate_date, INDICATOR_BAR_LIMIT),
    ).fetchall()
    rows = list(reversed(rows))
    return [{"trade_date": r[0], "close": r[1]} for r in rows]


def future_bars_for(conn, symbol, candidate_date, min_needed=40):
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


def load_all(conn, cohort):
    """Pre-fetch bars once per (symbol, date) -- reused across all variants."""
    cache = {}
    for cand_date, symbol, setup, entry, stop in cohort:
        if entry is None or stop is None:
            continue
        trig = trigger_bars_for(conn, symbol, cand_date)
        idx = index_bars_for(conn, cand_date)
        fut = future_bars_for(conn, symbol, cand_date)
        cache[(cand_date, symbol, setup)] = {
            "entry": float(entry), "stop": float(stop),
            "trigger_bars": trig, "index_bars": idx, "future_bars": fut,
            "regime": regime_for(conn, cand_date),
            "family": setup_family(setup),
        }
    return cache


H5_MIN_INDEX_BARS = 51  # mi.mswing needs a 50-session momentum lookback


def run_variant(cache, hypotheses):
    """Returns (obs, removed, excluded_no_data) where obs = eligible trades'
    outcomes; removed = refused candidates w/ their standalone (unrefused)
    stats for the paired removed-cohort test; excluded_no_data = candidates
    skipped because H5 was requested but index history doesn't reach back
    far enough (data-coverage gap, NOT a refusal -- WAVE_J_SPEC #4 honesty)."""
    obs = []
    removed = []
    excluded_no_data = []
    for key, c in cache.items():
        cand_date, symbol, setup = key
        if "H5" in hypotheses and len(c["index_bars"]) < H5_MIN_INDEX_BARS:
            excluded_no_data.append((key, c))
            continue
        result = env.run_variant(
            c["trigger_bars"], c["index_bars"], c["future_bars"],
            c["entry"], c["stop"], HORIZON,
            hypotheses=hypotheses,
        )
        # Standalone (baseline, no refusals) outcome for the paired test --
        # ALWAYS computed so a refused name's own would-have-been R is known.
        standalone = ev.walk_managed_exit(
            c["future_bars"], c["entry"], c["stop"], HORIZON,
            stop_multiplier=1.0, entry_mode="next_open",
        )
        if not result["eligible"]:
            removed.append({
                "key": key, "family": c["family"], "regime": c["regime"],
                "failed": result["failed"],
                "standalone_r": standalone["managed_r"] if standalone and not standalone.get("skipped") else None,
            })
            continue
        outcome = result["outcome"]
        if outcome is None or outcome.get("skipped"):
            removed.append({
                "key": key, "family": c["family"], "regime": c["regime"],
                "failed": "H3_no_confirm" if outcome and outcome.get("skipped") else "incomplete_window",
                "standalone_r": standalone["managed_r"] if standalone and not standalone.get("skipped") else None,
            })
            continue
        obs.append({
            "key": key, "family": c["family"], "regime": c["regime"],
            "r": outcome["managed_r"], "exit_reason": outcome["exit_reason"],
            "mfe": outcome["managed_mfe_r"], "mae": outcome["managed_mae_r"],
            "hit_1r": outcome["hit_1r"],
        })
    return obs, removed, excluded_no_data


def _stats_row(rows):
    n = len(rows)
    if n == 0:
        return None
    stopout = sum(1 for r in rows if r["exit_reason"] in ("stop", "gap_through_stop")) / n * 100
    avgr = sum(r["r"] for r in rows) / n
    medr = st.median(r["r"] for r in rows)
    avgmfe = sum(r["mfe"] for r in rows) / n
    hit1r = sum(r["hit_1r"] for r in rows) / n * 100
    return {"n": n, "stopout": stopout, "avgr": avgr, "medr": medr, "avgmfe": avgmfe, "hit1r": hit1r}


def _fmt_row(label, s):
    if s is None:
        return f"{label:<28} {'0':>4}  (no observations)"
    flag = "" if s["n"] >= 30 else (" [directional 20-29]" if s["n"] >= 20 else " [THIN <20]")
    return (f"{label:<28} {s['n']:>4} {s['stopout']:>8.1f}% {s['avgr']:>7.2f} "
            f"{s['medr']:>7.2f} {s['avgmfe']:>7.2f} {s['hit1r']:>6.1f}%{flag}")


def summarize_family_regime(obs, label):
    lines = [f"\n=== {label} (n={len(obs)}) : family x regime ==="]
    header = f"{'family x regime':<28} {'n':>4} {'stopout%':>9} {'avgR':>7} {'medR':>7} {'avgMFE':>7} {'hit1r%':>7}"
    lines.append(header)
    lines.append("-" * len(header))
    by_cell = defaultdict(list)
    for o in obs:
        by_cell[(o["family"], o["regime"])].append(o)
    for (fam, regime), rows in sorted(by_cell.items()):
        s = _stats_row(rows)
        lines.append(_fmt_row(f"{fam}/{regime}", s))
    lines.append("-" * len(header))
    lines.append(_fmt_row("ALL", _stats_row(obs)))
    return "\n".join(lines)


def summarize_removed(removed, label):
    lines = [f"\n=== {label}: removed cohort (n={len(removed)}) ==="]
    if not removed:
        lines.append("(nothing removed)")
        return "\n".join(lines)
    by_reason = defaultdict(list)
    for r in removed:
        by_reason[r["failed"]].append(r)
    for reason, rows in sorted(by_reason.items()):
        names = ", ".join(f"{k[1]}@{k[0]}" for k in (r["key"] for r in rows))
        vals = [r["standalone_r"] for r in rows if r["standalone_r"] is not None]
        avg = sum(vals) / len(vals) if vals else None
        med = st.median(vals) if vals else None
        lines.append(f"  [{reason}] n={len(rows)} standalone avgR={avg} medR={med}")
        lines.append(f"    names: {names}")
    return "\n".join(lines)


def paired_test(kept_obs, removed, label):
    """WAVE_J_SPEC §3.4(3): kept cohort median managed R vs current-passed
    (unrefused, i.e. baseline-standalone) cohort median >= +0.5R, AND removed
    cohort's OWN standalone R <= kept cohort's median (refusal removes worse
    names, not random thinning)."""
    kept_med = st.median(o["r"] for o in kept_obs) if kept_obs else None
    removed_vals = [r["standalone_r"] for r in removed if r["standalone_r"] is not None]
    removed_med = st.median(removed_vals) if removed_vals else None
    return (
        f"{label}: kept medR={kept_med} (n={len(kept_obs)}) vs removed standalone "
        f"medR={removed_med} (n={len(removed_vals)}) -- "
        f"removed<=kept: {removed_med is not None and kept_med is not None and removed_med <= kept_med}"
    )


def main():
    conn = sqlite3.connect(DB)
    cohort = load_cohort(conn)
    print(f"cohort n={len(cohort)}")
    cache = load_all(conn, cohort)
    print(f"cache built n={len(cache)} (entry/stop present)")

    baseline_obs, baseline_removed, _ = run_variant(cache, set())
    baseline_med = st.median(o["r"] for o in baseline_obs) if baseline_obs else None
    print(f"\nbaseline (no refusals) medR={baseline_med} n={len(baseline_obs)}")

    all_results = {}
    for label, hyps in VARIANTS:
        obs, removed, excluded = run_variant(cache, hyps)
        all_results[label] = (obs, removed, excluded)
        print(summarize_family_regime(obs, label))
        print(summarize_removed(removed, label))
        if excluded:
            print(f"  [H5 data-gap exclusions, NOT refusals] n={len(excluded)}: "
                  f"{[k[1] + '@' + k[0] for k in (e[0] for e in excluded)]}")
        print(paired_test(obs, removed, label))

    # Two-sub-window replication (WAVE_J_SPEC §3.4(4))
    print("\n\n======== TWO-SUB-WINDOW REPLICATION ========")
    for label, hyps in VARIANTS:
        obs, removed, excluded = all_results[label]
        print(f"\n--- {label} ---")
        sub_meds = []
        for sub_label, lo, hi in SUBWINDOWS:
            sub_obs = [o for o in obs if lo <= o["key"][0] <= hi]
            s = _stats_row(sub_obs)
            print(f"  {sub_label}: " + (_fmt_row("", s).strip() if s else "n=0 (no observations)"))
            sub_meds.append(s["medr"] if s else None)
        both_nonneg = all(m is not None and m >= 0 for m in sub_meds)
        same_sign = (len(sub_meds) == 2 and sub_meds[0] is not None and sub_meds[1] is not None
                     and (sub_meds[0] >= 0) == (sub_meds[1] >= 0))
        print(f"  both windows >=0: {both_nonneg}; same sign: {same_sign}")

    conn.close()


if __name__ == "__main__":
    main()
