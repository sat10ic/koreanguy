"""Sunday review report - prints suggestions, never edits watchlist.csv. Spec 8.3."""
import io
import os
import sys
import pandas as pd

if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts import _db, _config, _grade_helper

config = _config.load_config()

BOLD = "\033[1m"; DIM = "\033[2m"; RESET = "\033[0m"
GREEN = "\033[32m"; RED = "\033[31m"; YELLOW = "\033[33m"


def header(t):
    print(f"\n{BOLD}{t}{RESET}")
    print("-" * len(t))


def load_watchlist():
    path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        getattr(config.universe, 'watchlist_file', 'watchlist.csv'),
    )
    if not os.path.exists(path):
        return set()
    return set(pd.read_csv(path)['symbol'].tolist())


def section_secondary_freq(hist_df, watchlist):
    header("1. Secondary signals — last 7 days (group by symbol)")
    if hist_df.empty:
        print(f"{DIM}No history yet.{RESET}")
        return
    last7_dates = sorted(hist_df['date'].unique())[-7:]
    recent = hist_df[hist_df['date'].isin(last7_dates)]
    sec = recent[recent['tier'] == 'secondary']
    if sec.empty:
        print(f"{DIM}No secondary signals in last 7 days.{RESET}")
        return
    counts = sec.groupby('symbol').size().sort_values(ascending=False)
    for sym, n in counts.items():
        marker = "★" if sym in watchlist else " "
        print(f"  {marker} {sym:12s}  {GREEN}{n}×{RESET}")


def section_inactive_watchlist(hist_df, watchlist, all_dates):
    header("2. Watchlist members with zero signals in last 30 days (drop candidates)")
    if not watchlist:
        print(f"{DIM}Empty watchlist.{RESET}")
        return
    last30 = sorted(all_dates)[-30:]
    recent = hist_df[hist_df['date'].isin(last30)] if not hist_df.empty else hist_df
    fired = set(recent['symbol'].tolist()) if not recent.empty else set()
    inactive = sorted(watchlist - fired)
    if not inactive:
        print(f"{DIM}All watchlist members have fired.{RESET}")
        return
    for sym in inactive:
        print(f"  {RED}↓{RESET} {sym}")


def section_purple_dot_hot(feat_conn, watchlist):
    header("3. Non-watchlist names with ≥ 2 Purple Dots in last 30 days (add candidates)")
    cur = feat_conn.cursor()
    cur.execute("SELECT MAX(date) FROM features")
    max_date = cur.fetchone()[0]
    if not max_date:
        print(f"{DIM}No feature data.{RESET}")
        return
    q = (
        "SELECT symbol, SUM(purple_dot) c FROM features "
        "WHERE date > date(?, '-30 days') "
        "AND symbol NOT IN ('_NIFTY50','_NF500EW') "
        "GROUP BY symbol HAVING c >= 2 ORDER BY c DESC"
    )
    df = pd.read_sql_query(q, feat_conn, params=(max_date,))
    hot = df[~df['symbol'].isin(watchlist)]
    if hot.empty:
        print(f"{DIM}None.{RESET}")
        return
    for _, r in hot.iterrows():
        print(f"  {GREEN}↑{RESET} {r['symbol']:12s}  PD×{int(r['c'])}")


def section_degrading(feat_conn, ohlcv_conn, watchlist):
    header("4. Watchlist names with grade ≤ C- for 5+ consecutive days (degrading)")
    cur = feat_conn.cursor()
    cur.execute("SELECT DISTINCT date FROM features ORDER BY date DESC LIMIT 5")
    dates = [r[0] for r in cur.fetchall()]
    if len(dates) < 5:
        print(f"{DIM}Need 5 trading days of data.{RESET}")
        return
    threshold = _grade_helper.get_grade_ordinal("C-")
    bad = []
    for sym in watchlist:
        run = 0
        for d in dates:
            g = _grade_helper.calculate_grades_for_date(feat_conn, ohlcv_conn, d)
            r = g[g['symbol'] == sym]
            if r.empty:
                break
            if _grade_helper.get_grade_ordinal(r.iloc[0]['grade']) <= threshold:
                run += 1
            else:
                break
        if run >= 5:
            bad.append((sym, run))
    if not bad:
        print(f"{DIM}None.{RESET}")
        return
    for sym, n in bad:
        print(f"  {YELLOW}!{RESET} {sym:12s}  {n} bad days")


def main():
    watchlist = load_watchlist()
    hist_path = 'output/candidates_history.csv'
    hist_df = pd.read_csv(hist_path) if os.path.exists(hist_path) else pd.DataFrame(columns=['date', 'symbol', 'tier'])

    feat_conn = _db.features_conn()
    ohlcv_conn = _db.ohlcv_conn()
    cur = feat_conn.cursor()
    cur.execute("SELECT DISTINCT date FROM features ORDER BY date DESC LIMIT 30")
    all_dates = [r[0] for r in cur.fetchall()]

    print(f"{BOLD}=== SwingEdge Lite - Watchlist Helper (Sunday Review) ==={RESET}")
    print(f"  Watchlist size: {len(watchlist)}")
    section_secondary_freq(hist_df, watchlist)
    section_inactive_watchlist(hist_df, watchlist, all_dates)
    section_purple_dot_hot(feat_conn, watchlist)
    section_degrading(feat_conn, ohlcv_conn, watchlist)
    print()
    print(f"{DIM}This script does not modify watchlist.csv. Edit manually after review.{RESET}")


if __name__ == '__main__':
    main()
