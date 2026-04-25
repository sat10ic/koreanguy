"""Backfill real historical pipeline output for the dashboard.

Replays Regime → Screen → Verify → Track chronologically for the past N
trading sessions, populating:
  - output/candidates_history.csv  (per-day primary/secondary)
  - data/portfolio_state.db        (real positions through state machine)

Idempotent: existing positions are preserved; days already present in
candidates_history.csv are skipped.

Run with:  python -m scripts.backfill --days 60
"""
import os
import sys
import json
import logging
import argparse
import pandas as pd
import numpy as np
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts import _db, _config, _grade_helper, screen as screen_mod, verify as verify_mod

config = _config.load_config()


def setup_logger():
    logger = logging.getLogger('backfill')
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s'))
    logger.addHandler(h)
    return logger


logger = setup_logger()


# -- Regime evaluation for any date --------------------------------------
def regime_for_date(feat_conn, ohlcv_conn, target_date: str) -> dict:
    """Re-evaluate the 4-pillar regime against features as of target_date."""
    pillars = {}

    # Pillar 1: Trend (NF500EW close > rising 21DMA)
    nf500_o = pd.read_sql_query(
        "SELECT date, close FROM ohlcv WHERE symbol='_NF500EW' AND date <= ? ORDER BY date",
        ohlcv_conn, params=(target_date,),
    )
    nf500_f = pd.read_sql_query(
        "SELECT date, sma21 FROM features WHERE symbol='_NF500EW' AND date <= ? ORDER BY date",
        feat_conn, params=(target_date,),
    )
    p1_pass = False
    if not nf500_o.empty and not nf500_f.empty:
        m = pd.merge(nf500_o, nf500_f, on='date')
        if len(m) >= 6:
            today = m.iloc[-1]
            five = m.iloc[-6]
            if pd.notna(today['sma21']) and pd.notna(five['sma21']):
                if today['close'] > today['sma21'] and today['sma21'] > five['sma21']:
                    p1_pass = True
    pillars['trend'] = {'pass': p1_pass, 'value': '_NF500EW vs SMA21'}

    # Pillar 2: Momentum (Nifty50 RSI < overbought)
    n50_f = pd.read_sql_query(
        "SELECT date, rsi14 FROM features WHERE symbol='_NIFTY50' AND date=?",
        feat_conn, params=(target_date,),
    )
    p2_pass = False
    rsi_val = None
    if not n50_f.empty and pd.notna(n50_f.iloc[0]['rsi14']):
        rsi_val = float(n50_f.iloc[0]['rsi14'])
        if rsi_val < float(config.regime.rsi_overbought):
            p2_pass = True
    pillars['momentum'] = {'pass': p2_pass, 'value': f'RSI {rsi_val}'}

    # Pillar 3: Breadth (% above SMA50)
    feats = pd.read_sql_query(
        "SELECT symbol, sma50 FROM features WHERE date=? AND symbol NOT IN ('_NIFTY50','_NF500EW')",
        feat_conn, params=(target_date,),
    )
    ohlc = pd.read_sql_query(
        "SELECT symbol, close FROM ohlcv WHERE date=? AND symbol NOT IN ('_NIFTY50','_NF500EW')",
        ohlcv_conn, params=(target_date,),
    )
    p3_pass = False
    breadth = None
    if not feats.empty and not ohlc.empty:
        m = pd.merge(feats, ohlc, on='symbol')
        if len(m):
            above = (m['close'] > m['sma50']).sum()
            breadth = above / len(m)
            if breadth >= float(config.regime.breadth_threshold):
                p3_pass = True
    pillars['breadth'] = {'pass': p3_pass, 'value': f'{breadth}'}

    # Pillar 4: Volatility (|close - 21EMA| < 3.2×ATR21)
    n50_full_o = pd.read_sql_query(
        "SELECT date, close FROM ohlcv WHERE symbol='_NIFTY50' AND date=?",
        ohlcv_conn, params=(target_date,),
    )
    n50_full_f = pd.read_sql_query(
        "SELECT date, ema21, atr21 FROM features WHERE symbol='_NIFTY50' AND date=?",
        feat_conn, params=(target_date,),
    )
    p4_pass = False
    if not n50_full_o.empty and not n50_full_f.empty:
        c = float(n50_full_o.iloc[0]['close'])
        e = n50_full_f.iloc[0]['ema21']
        a = n50_full_f.iloc[0]['atr21']
        if pd.notna(e) and pd.notna(a):
            diff = abs(c - float(e))
            if diff < float(config.regime.vol_atr_multiple) * float(a):
                p4_pass = True
    pillars['volatility'] = {'pass': p4_pass, 'value': 'nifty vs ema21'}

    passed = sum(1 for p in pillars.values() if p['pass'])
    if passed >= 3:
        regime = 'RISK_ON'
    elif passed == 2:
        regime = 'CAUTION'
    else:
        regime = 'RISK_OFF'
    return {'regime': regime, 'pillars_passed': passed, 'pillars': pillars, 'date': target_date}


# -- Screen for any date -------------------------------------------------
def screen_for_date(feat_conn, ohlcv_conn, target_date: str) -> pd.DataFrame:
    """Run the bread-and-butter screen against features ≤ target_date."""
    cur = feat_conn.cursor()
    cur.execute(
        "SELECT DISTINCT date FROM features WHERE date <= ? ORDER BY date DESC LIMIT 3",
        (target_date,),
    )
    dates = [r[0] for r in cur.fetchall()]
    if len(dates) < 3:
        return pd.DataFrame()
    today_str, yest_str, prev_str = dates[0], dates[1], dates[2]
    today_grades = _grade_helper.calculate_grades_for_date(feat_conn, ohlcv_conn, today_str)
    yest_grades = _grade_helper.calculate_grades_for_date(feat_conn, ohlcv_conn, yest_str)

    feat_q = (
        "SELECT * FROM features WHERE date IN (?, ?, ?) "
        "AND symbol NOT IN ('_NIFTY50', '_NF500EW')"
    )
    feat_df = pd.read_sql_query(feat_q, feat_conn, params=(today_str, yest_str, prev_str))
    ohlcv_df = pd.read_sql_query(
        "SELECT * FROM ohlcv WHERE date IN (?, ?, ?) AND symbol NOT IN ('_NIFTY50', '_NF500EW')",
        ohlcv_conn, params=(today_str, yest_str, prev_str),
    )
    full = pd.merge(feat_df, ohlcv_df, on=['symbol', 'date'])
    today = full[full['date'] == today_str].copy()
    yest = full[full['date'] == yest_str].copy()
    prev = full[full['date'] == prev_str].copy()

    today = pd.merge(
        today, today_grades[['symbol', 'grade', 'rs_score', 'bucket', 'rank_pct']],
        on='symbol', how='left',
    )
    yest_g = yest_grades[['symbol', 'grade']].rename(columns={'grade': 'grade_yesterday'})
    today = pd.merge(today, yest_g, on='symbol', how='left')
    merged = pd.merge(today, yest, on='symbol', suffixes=('', '_y'))
    merged = pd.merge(
        merged,
        prev[['symbol', 'close', 'sma20']].rename(columns={'close': 'close_p', 'sma20': 'sma20_p'}),
        on='symbol', how='left',
    )

    setup_cfg = config.setup
    uptrend_min_gain = setup_cfg.get('uptrend_min_gain', 0.25) if isinstance(setup_cfg, dict) else 0.25
    correction_min = setup_cfg.get('correction_min', 0.03) if isinstance(setup_cfg, dict) else 0.03
    correction_max = setup_cfg.get('correction_max', 0.30) if isinstance(setup_cfg, dict) else 0.30

    merged['uptrend_pass'] = (
        (merged['close'] > merged['sma200']) &
        (merged['high_126'] >= (1.0 + uptrend_min_gain) * merged['low_126'])
    )
    merged['correction_pass'] = (
        (merged['close'] <= (1 - correction_min) * merged['high_126']) &
        (merged['close'] >= (1 - correction_max) * merged['high_126'])
    )
    reclaim_today = (merged['close'] > merged['sma20']) & (merged['close_y'] <= merged['sma20_y'])
    reclaim_yest = (
        (merged['close_y'] > merged['sma20_y']) &
        (merged['close_p'] <= merged['sma20_p']) &
        (merged['close'] > merged['sma20'])
    )
    merged['reclaim_pass'] = (reclaim_today | reclaim_yest).fillna(False)
    merged['setup_pass'] = (
        merged['uptrend_pass'].fillna(False) &
        merged['correction_pass'].fillna(False) &
        merged['reclaim_pass']
    ).astype(int)
    merged['extended_yellow'] = (merged['close'] > merged['sma50'] + 5 * merged['atr14']).astype(int)
    merged['extended_red'] = (merged['close'] > merged['sma50'] + 7 * merged['atr14']).astype(int)

    # Watchlist membership at current state
    wl_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        getattr(config.universe, 'watchlist_file', 'watchlist.csv'),
    )
    wl_set = set()
    if os.path.exists(wl_path):
        wl_set = set(pd.read_csv(wl_path)['symbol'].tolist())
    merged['watchlist_member'] = merged['symbol'].apply(lambda x: 1 if x in wl_set else 0)

    return merged


# -- Verify for any date -------------------------------------------------
def verify_for_date(feat_conn, ohlcv_conn, screen_df: pd.DataFrame, regime: str) -> list[dict]:
    """Apply Layer A + Layer B and return verified candidate dicts."""
    out_cols = [
        'symbol', 'tier', 'grade', 'grade_3d_avg', 'rs_score', 'close', 'atr14', 'adv20',
        'suggested_stop', 'risk_per_share', 'size_shares', 'size_pct',
        'purple_dot_today', 'purple_dot_count_30d', 'regime', 'notes',
    ]
    if regime == 'RISK_OFF' or screen_df.empty:
        return []
    setups = screen_df[screen_df['setup_pass'] == 1].copy()
    if setups.empty:
        return []

    decisions = {'layer_a_lookback': 2, 'layer_a_min_avg_rank': 0.75}
    cur = feat_conn.cursor()
    target_date = setups.iloc[0]['date']
    cur.execute(
        "SELECT DISTINCT date FROM features WHERE date <= ? ORDER BY date DESC LIMIT 6",
        (target_date,),
    )
    past_dates = [r[0] for r in cur.fetchall()]
    grade_frames = {d: _grade_helper.calculate_grades_for_date(feat_conn, ohlcv_conn, d) for d in past_dates}

    verified = []
    for _, row in setups.iterrows():
        sym = row['symbol']
        rows = []
        for d in past_dates:
            r = grade_frames[d][grade_frames[d]['symbol'] == sym]
            if not r.empty:
                rows.append(r.iloc[0])
        if not rows:
            continue
        history_df = pd.DataFrame(rows).reset_index(drop=True)

        ok_a, why_a = verify_mod.layer_a(sym, history_df, decisions)
        if not ok_a:
            continue

        row_b = row.copy()
        row_b['sma50_rising'] = verify_mod.get_sma50_rising(feat_conn, sym, target_date)
        ok_b, why_b = verify_mod.layer_b(row_b)
        if not ok_b:
            continue

        stop, shares, rps, size_pct = verify_mod.compute_sizing(row['close'], row['atr14'], regime)
        tier = 'primary' if row.get('watchlist_member', 0) == 1 else 'secondary'
        last_n = history_df.head(decisions['layer_a_lookback'])
        grade_3d_avg = last_n['rank_pct'].fillna(0).mean()

        verified.append({
            'symbol': sym, 'tier': tier, 'grade': row['grade'],
            'grade_3d_avg': round(float(grade_3d_avg), 3),
            'rs_score': round(float(row['rs_score']), 4),
            'close': float(row['close']),
            'atr14': round(float(row['atr14']), 2) if pd.notna(row['atr14']) else None,
            'adv20': int(row['adv20']) if pd.notna(row['adv20']) else 0,
            'suggested_stop': round(stop, 2),
            'risk_per_share': round(rps, 2),
            'size_shares': shares,
            'size_pct': round(size_pct, 4),
            'purple_dot_today': int(row.get('purple_dot', 0)),
            'purple_dot_count_30d': int(row.get('purple_dot_count_30d', 0) or 0),
            'regime': regime,
            'notes': f"A: {why_a}; B: {why_b}",
        })
    return verified


# -- Tracker for any date ------------------------------------------------
def track_for_date(portfolio_conn, feat_conn, ohlcv_conn, candidates: list[dict], regime: str, target_date: str):
    """Replay one day's tracker logic — same as track.py:run_track but for a given date."""
    cur = portfolio_conn.cursor()

    # 1. Insert primary candidates as PENDING_CONFIRM
    for c in candidates:
        if c.get('tier') != 'primary':
            continue
        cur.execute(
            "SELECT id FROM positions WHERE symbol=? AND signal_date=?",
            (c['symbol'], target_date),
        )
        if cur.fetchone():
            continue
        cur.execute(
            """INSERT INTO positions
               (symbol, signal_date, state, stop_price, size_shares,
                regime_at_entry, entry_grade, notes)
               VALUES (?, ?, 'PENDING_CONFIRM', ?, ?, ?, ?, ?)""",
            (c['symbol'], target_date, float(c['suggested_stop']),
             int(c['size_shares']), regime, c['grade'], c.get('notes', '')),
        )

    # 2. PENDING_CONFIRM → ACTIVE / DISCARDED (using bar at target_date)
    pending = pd.read_sql_query(
        "SELECT * FROM positions WHERE state='PENDING_CONFIRM' AND signal_date < ?",
        portfolio_conn, params=(target_date,),
    )
    for _, pos in pending.iterrows():
        bars = pd.read_sql_query(
            "SELECT * FROM ohlcv WHERE symbol=? AND date <= ? ORDER BY date DESC LIMIT 2",
            ohlcv_conn, params=(pos['symbol'], target_date),
        )
        if len(bars) < 2:
            continue
        bar = bars.iloc[0]
        prev_bar = bars.iloc[1]
        feat = pd.read_sql_query(
            "SELECT * FROM features WHERE symbol=? AND date=?",
            feat_conn, params=(pos['symbol'], target_date),
        )
        if feat.empty:
            continue
        ema10 = feat.iloc[0]['ema10']
        adv20 = feat.iloc[0]['adv20']
        confirmed = (
            bar['close'] > prev_bar['close']
            and bar['volume'] >= (adv20 or 0)
            and pd.notna(ema10) and bar['close'] > ema10
        )
        if confirmed:
            cur.execute(
                "UPDATE positions SET state='ACTIVE', entry_date=?, entry_price=? WHERE id=?",
                (target_date, float(bar['close']), pos['id']),
            )
        else:
            cur.execute(
                "UPDATE positions SET state='DISCARDED', exit_date=? WHERE id=?",
                (target_date, pos['id']),
            )

    # 3. Process exits for ACTIVE positions
    active = pd.read_sql_query(
        "SELECT * FROM positions WHERE state='ACTIVE' AND signal_date <= ?",
        portfolio_conn, params=(target_date,),
    )
    decay_levels = config.exit_flags.grade_decay_levels
    decay_days = config.exit_flags.grade_decay_days
    super_ext = config.exit_flags.super_extended_atr_multiple

    for _, pos in active.iterrows():
        bars = pd.read_sql_query(
            "SELECT * FROM ohlcv WHERE symbol=? AND date=?",
            ohlcv_conn, params=(pos['symbol'], target_date),
        )
        if bars.empty:
            continue
        bar = bars.iloc[0]
        feat_q = pd.read_sql_query(
            "SELECT * FROM features WHERE symbol=? AND date=?",
            feat_conn, params=(pos['symbol'], target_date),
        )
        if feat_q.empty:
            continue
        feat = feat_q.iloc[0]

        # A. Stop hit
        if bar['low'] <= pos['stop_price']:
            pnl = (pos['stop_price'] - pos['entry_price']) / pos['entry_price']
            cur.execute(
                "UPDATE positions SET state='EXITED_STOP', exit_date=?, exit_price=?, pnl_pct=? WHERE id=?",
                (target_date, float(pos['stop_price']), float(pnl), pos['id']),
            )
            continue
        # B. Super-extended
        if (pd.notna(feat['sma50']) and pd.notna(feat['atr14'])
                and bar['close'] > feat['sma50'] + super_ext * feat['atr14']):
            pnl = (bar['close'] - pos['entry_price']) / pos['entry_price']
            cur.execute(
                "UPDATE positions SET state='EXITED_EXTENDED', exit_date=?, exit_price=?, pnl_pct=? WHERE id=?",
                (target_date, float(bar['close']), float(pnl), pos['id']),
            )
            continue
        # C. Grade decay
        g = _grade_helper.calculate_grades_for_date(feat_conn, ohlcv_conn, target_date)
        gr = g[g['symbol'] == pos['symbol']]
        if gr.empty:
            continue
        today_grade = gr.iloc[0]['grade']
        if today_grade and pos['entry_grade']:
            entry_ord = _grade_helper.get_grade_ordinal(pos['entry_grade'])
            today_ord = _grade_helper.get_grade_ordinal(today_grade)
            if (entry_ord - today_ord) >= decay_levels:
                streak = (pos['grade_decay_streak'] or 0) + 1
                if streak >= decay_days:
                    pnl = (bar['close'] - pos['entry_price']) / pos['entry_price']
                    cur.execute(
                        "UPDATE positions SET state='EXITED_DECAY', exit_date=?, exit_price=?, pnl_pct=? WHERE id=?",
                        (target_date, float(bar['close']), float(pnl), pos['id']),
                    )
                else:
                    cur.execute(
                        "UPDATE positions SET grade_decay_streak=? WHERE id=?",
                        (streak, pos['id']),
                    )
            else:
                cur.execute(
                    "UPDATE positions SET grade_decay_streak=0 WHERE id=?", (pos['id'],),
                )
    portfolio_conn.commit()


# -- Driver --------------------------------------------------------------
def run_backfill(days: int = 60, progress_cb=None) -> dict:
    _db.init_schemas()
    feat_conn = _db.features_conn()
    ohlcv_conn = _db.ohlcv_conn()
    portfolio_conn = _db.portfolio_conn()

    # Get sorted list of trading dates we have features for
    cur = feat_conn.cursor()
    cur.execute("SELECT DISTINCT date FROM features ORDER BY date ASC")
    all_dates = [r[0] for r in cur.fetchall() if r[0]]
    target_dates = all_dates[-days:] if len(all_dates) > days else all_dates

    # Load existing history to skip already-processed days
    hist_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'output', 'candidates_history.csv')
    existing = set()
    if os.path.exists(hist_path):
        try:
            h = pd.read_csv(hist_path)
            existing = set(h['date'].astype(str).unique())
        except Exception:
            pass

    appended = 0
    primaries_total = 0
    for idx, d in enumerate(target_dates):
        if d in existing:
            if progress_cb:
                progress_cb(idx + 1, len(target_dates), d, 'skip')
            continue

        regime_dict = regime_for_date(feat_conn, ohlcv_conn, d)
        regime = regime_dict['regime']

        screen_df = screen_for_date(feat_conn, ohlcv_conn, d)
        candidates = verify_for_date(feat_conn, ohlcv_conn, screen_df, regime)

        # Append to candidates_history.csv
        if candidates:
            df_out = pd.DataFrame(candidates)
            df_out['date'] = d
            header = not os.path.exists(hist_path) or os.path.getsize(hist_path) == 0
            df_out.to_csv(hist_path, mode='a', header=header, index=False)
            primaries_total += sum(1 for c in candidates if c['tier'] == 'primary')

        # Replay tracker for this day
        track_for_date(portfolio_conn, feat_conn, ohlcv_conn, candidates, regime, d)

        appended += 1
        if progress_cb:
            progress_cb(
                idx + 1, len(target_dates), d,
                f"r={regime} c={len(candidates)} p={sum(1 for c in candidates if c['tier']=='primary')}",
            )

    state_summary = pd.read_sql_query(
        "SELECT state, COUNT(*) c FROM positions GROUP BY state", portfolio_conn,
    )
    return {
        'days_requested': days,
        'days_processed': appended,
        'days_skipped': len(target_dates) - appended,
        'primaries_total': primaries_total,
        'positions_by_state': {r['state']: int(r['c']) for _, r in state_summary.iterrows()},
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--days', type=int, default=60)
    args = p.parse_args()
    res = run_backfill(args.days, progress_cb=lambda i, t, d, st: print(f'[{i}/{t}] {d} {st}'))
    print(json.dumps(res, indent=2))


if __name__ == '__main__':
    main()
