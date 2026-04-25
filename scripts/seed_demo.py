"""Seed demo data for the dashboard.

Creates a few realistic historical positions in portfolio_state.db and a few
entries in candidates_history.csv, so the dashboard demonstrates its full UX
even when today's verify layer produces 0 candidates (which is normal — the
spec is strict by design).

Idempotent: existing positions/history rows are preserved; demo rows are tagged
in `notes` and re-seeded only if missing. Run with:

    python -m scripts.seed_demo

This file ONLY runs on explicit invocation. The daily pipeline never calls it.
"""
import os
import sys
import sqlite3
import pandas as pd
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts import _db


DEMO_TAG = "DEMO_SEED"


def seed_positions():
    _db.init_schemas()
    conn = _db.portfolio_conn()
    cur = conn.cursor()
    # Skip if any DEMO_SEED row already there
    cur.execute("SELECT COUNT(*) FROM positions WHERE notes LIKE ?", (f"%{DEMO_TAG}%",))
    if cur.fetchone()[0] > 0:
        print("demo positions already seeded — skipping")
        return

    # Pull 6 high-grade symbols from latest screen output
    screen_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'output', 'screen_today.csv')
    if not os.path.exists(screen_path):
        print("no screen output — run pipeline first")
        return
    df = pd.read_csv(screen_path)
    df = df[df["bucket"] == "Bullish"].sort_values("rs_score", ascending=False)
    if df.empty:
        print("no bullish stocks — abort")
        return
    picks = df.head(8).to_dict("records")

    # Today's date from any feature row
    feat_conn = _db.features_conn()
    today_row = feat_conn.execute("SELECT MAX(date) FROM features").fetchone()
    today = today_row[0]

    today_dt = datetime.strptime(today, "%Y-%m-%d")

    # 2 ACTIVE (entered 7 and 14 days ago — still open)
    # 1 PENDING_CONFIRM (today)
    # 1 EXITED_EXTENDED (entered 30 days ago, exited 3 days ago at +18%)
    # 1 EXITED_STOP (entered 25 days ago, stopped out 18 days ago at -2.5%)
    # 1 EXITED_DECAY (entered 20 days ago, decayed 5 days ago at -1.0%)
    seeds = []

    if len(picks) > 0:
        s = picks[0]
        ed = (today_dt - timedelta(days=14)).strftime("%Y-%m-%d")
        sd = (today_dt - timedelta(days=15)).strftime("%Y-%m-%d")
        # Entry slightly below current → P&L is positive
        ep = float(s["close"]) * 0.92
        seeds.append((
            s["symbol"], sd, "ACTIVE", ed, ep, ep * 0.975, 25,
            None, None, None, "RISK_ON", s["grade"], 0,
            f"{DEMO_TAG} confirmed entry on day after signal",
        ))
    if len(picks) > 1:
        s = picks[1]
        ed = (today_dt - timedelta(days=7)).strftime("%Y-%m-%d")
        sd = (today_dt - timedelta(days=8)).strftime("%Y-%m-%d")
        ep = float(s["close"]) * 0.96
        seeds.append((
            s["symbol"], sd, "ACTIVE", ed, ep, ep * 0.975, 30,
            None, None, None, "RISK_ON", s["grade"], 0,
            f"{DEMO_TAG} active position",
        ))
    if len(picks) > 2:
        s = picks[2]
        sd = today
        seeds.append((
            s["symbol"], sd, "PENDING_CONFIRM", None, None,
            float(s["close"]) * 0.975, 20,
            None, None, None, "RISK_ON", s["grade"], 0,
            f"{DEMO_TAG} fresh signal awaiting day-2 confirmation",
        ))
    if len(picks) > 3:
        s = picks[3]
        sd = (today_dt - timedelta(days=30)).strftime("%Y-%m-%d")
        ed = (today_dt - timedelta(days=29)).strftime("%Y-%m-%d")
        xd = (today_dt - timedelta(days=3)).strftime("%Y-%m-%d")
        ep = float(s["close"]) * 0.85
        xp = ep * 1.18
        seeds.append((
            s["symbol"], sd, "EXITED_EXTENDED", ed, ep, ep * 0.975, 18,
            xd, xp, (xp - ep) / ep, "RISK_ON", s["grade"], 0,
            f"{DEMO_TAG} super-extended exit",
        ))
    if len(picks) > 4:
        s = picks[4]
        sd = (today_dt - timedelta(days=25)).strftime("%Y-%m-%d")
        ed = (today_dt - timedelta(days=24)).strftime("%Y-%m-%d")
        xd = (today_dt - timedelta(days=18)).strftime("%Y-%m-%d")
        ep = float(s["close"]) * 1.04
        xp = ep * 0.975
        seeds.append((
            s["symbol"], sd, "EXITED_STOP", ed, ep, xp, 22,
            xd, xp, (xp - ep) / ep, "CAUTION", s["grade"], 0,
            f"{DEMO_TAG} stopped out",
        ))
    if len(picks) > 5:
        s = picks[5]
        sd = (today_dt - timedelta(days=20)).strftime("%Y-%m-%d")
        ed = (today_dt - timedelta(days=19)).strftime("%Y-%m-%d")
        xd = (today_dt - timedelta(days=5)).strftime("%Y-%m-%d")
        ep = float(s["close"]) * 1.02
        xp = ep * 0.99
        seeds.append((
            s["symbol"], sd, "EXITED_DECAY", ed, ep, ep * 0.975, 28,
            xd, xp, (xp - ep) / ep, "RISK_ON", s["grade"], 2,
            f"{DEMO_TAG} grade decay exit",
        ))
    if len(picks) > 6:
        s = picks[6]
        sd = (today_dt - timedelta(days=4)).strftime("%Y-%m-%d")
        ed = (today_dt - timedelta(days=3)).strftime("%Y-%m-%d")
        ep = float(s["close"]) * 0.98
        seeds.append((
            s["symbol"], sd, "ACTIVE", ed, ep, ep * 0.975, 35,
            None, None, None, "RISK_ON", s["grade"], 0,
            f"{DEMO_TAG} fresh active",
        ))
    if len(picks) > 7:
        s = picks[7]
        sd = (today_dt - timedelta(days=10)).strftime("%Y-%m-%d")
        ed = (today_dt - timedelta(days=9)).strftime("%Y-%m-%d")
        xd = (today_dt - timedelta(days=2)).strftime("%Y-%m-%d")
        ep = float(s["close"]) * 0.88
        xp = ep * 1.22
        seeds.append((
            s["symbol"], sd, "EXITED_EXTENDED", ed, ep, ep * 0.975, 22,
            xd, xp, (xp - ep) / ep, "RISK_ON", s["grade"], 0,
            f"{DEMO_TAG} second extended exit",
        ))

    cur.executemany(
        """INSERT OR IGNORE INTO positions
           (symbol, signal_date, state, entry_date, entry_price, stop_price,
            size_shares, exit_date, exit_price, pnl_pct, regime_at_entry,
            entry_grade, grade_decay_streak, notes)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        seeds,
    )
    conn.commit()
    print(f"seeded {len(seeds)} demo positions")


def seed_history():
    """Add a few sessions of candidate-count history to candidates_history.csv."""
    out = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'output', 'candidates_history.csv')
    if os.path.exists(out):
        df = pd.read_csv(out)
        if not df.empty and len(df) > 30:
            print("history already populated")
            return
    # Generate 30 days of synthetic primary/secondary counts
    today = datetime.now()
    rows = []
    import random
    random.seed(7)
    for i in range(30, 0, -1):
        d = (today - timedelta(days=i)).strftime("%Y-%m-%d")
        primary = max(0, int(random.gauss(2.4, 1.6)))
        secondary = max(0, int(random.gauss(5.5, 3.0)))
        # Generate that many fake rows
        for _ in range(primary):
            rows.append({"date": d, "tier": "primary", "symbol": "DEMO"})
        for _ in range(secondary):
            rows.append({"date": d, "tier": "secondary", "symbol": "DEMO"})
    pd.DataFrame(rows).to_csv(out, mode="a", header=not os.path.exists(out), index=False)
    print(f"appended {len(rows)} history rows to {out}")


def main():
    seed_positions()
    seed_history()


if __name__ == "__main__":
    main()
