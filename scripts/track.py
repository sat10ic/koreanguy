import os
import sys
import json
import logging
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts import _db, _config, _grade_helper

def setup_logger():
    os.makedirs('logs', exist_ok=True)
    logger = logging.getLogger('track')
    logger.setLevel(logging.INFO)
    if logger.handlers:
        return logger
    fh = logging.FileHandler('logs/track.log')
    fmt = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    fh.setFormatter(fmt)
    logger.addHandler(fh)
    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    logger.addHandler(ch)
    return logger

logger = setup_logger()
config = _config.load_config()


def _get_today_bar(ohlcv_conn, symbol, today_date):
    q = "SELECT * FROM ohlcv WHERE symbol = ? AND date <= ? ORDER BY date DESC LIMIT 2"
    df = pd.read_sql_query(q, ohlcv_conn, params=(symbol, today_date))
    if df.empty:
        return None, None
    today = df.iloc[0]
    prev = df.iloc[1] if len(df) > 1 else None
    return today, prev


def _get_today_features(feat_conn, symbol, today_date):
    q = "SELECT * FROM features WHERE symbol = ? AND date = ?"
    df = pd.read_sql_query(q, feat_conn, params=(symbol, today_date))
    return df.iloc[0] if not df.empty else None


def _grade_today(feat_conn, ohlcv_conn, symbol, today_date):
    g = _grade_helper.calculate_grades_for_date(feat_conn, ohlcv_conn, today_date)
    r = g[g['symbol'] == symbol]
    return r.iloc[0]['grade'] if not r.empty else None


def run_track():
    portfolio_conn = _db.portfolio_conn()
    feat_conn = _db.features_conn()
    ohlcv_conn = _db.ohlcv_conn()

    candidates_path = 'output/candidates.csv'
    regime_path = 'output/regime_today.json'
    if not (os.path.exists(candidates_path) and os.path.exists(regime_path)):
        logger.error("Missing candidates.csv or regime_today.json")
        return

    cands = pd.read_csv(candidates_path)
    with open(regime_path) as f:
        regime_data = json.load(f)
    today_date = regime_data['date']
    regime = regime_data['regime']

    cur = portfolio_conn.cursor()

    # 1. Insert primary candidates as PENDING_CONFIRM (idempotent)
    if not cands.empty:
        primaries = cands[cands['tier'] == 'primary']
        for _, c in primaries.iterrows():
            cur.execute(
                "SELECT id FROM positions WHERE symbol = ? AND signal_date = ?",
                (c['symbol'], today_date),
            )
            if cur.fetchone():
                continue
            cur.execute(
                """INSERT INTO positions
                   (symbol, signal_date, state, stop_price, size_shares,
                    regime_at_entry, entry_grade, notes)
                   VALUES (?, ?, 'PENDING_CONFIRM', ?, ?, ?, ?, ?)""",
                (
                    c['symbol'], today_date,
                    float(c['suggested_stop']), int(c['size_shares']),
                    regime, c['grade'], str(c.get('notes', '')),
                ),
            )
            logger.info(f"PENDING_CONFIRM: {c['symbol']} @ stop {c['suggested_stop']}")

    # 2. Process PENDING_CONFIRM -> ACTIVE / DISCARDED (spec §6.1)
    pending = pd.read_sql_query(
        "SELECT * FROM positions WHERE state = 'PENDING_CONFIRM'", portfolio_conn,
    )
    for _, pos in pending.iterrows():
        if pos['signal_date'] == today_date:
            continue  # don't confirm same day
        bar, prev_bar = _get_today_bar(ohlcv_conn, pos['symbol'], today_date)
        feat = _get_today_features(feat_conn, pos['symbol'], today_date)
        if bar is None or prev_bar is None or feat is None:
            continue

        ema10 = feat['ema10']
        adv20 = feat['adv20']
        confirmed = (
            bar['close'] > prev_bar['close']
            and bar['volume'] >= (adv20 or 0)
            and bar['close'] > (ema10 or float('inf'))
        )
        if confirmed:
            cur.execute(
                """UPDATE positions SET state='ACTIVE', entry_date=?, entry_price=?
                   WHERE id=?""",
                (today_date, float(bar['close']), pos['id']),
            )
            logger.info(f"ACTIVE: {pos['symbol']} @ {bar['close']}")
        else:
            cur.execute(
                "UPDATE positions SET state='DISCARDED', exit_date=? WHERE id=?",
                (today_date, pos['id']),
            )
            logger.info(f"DISCARDED: {pos['symbol']} (confirmation failed)")

    # 3. Process ACTIVE positions for exits (spec §6.2)
    active = pd.read_sql_query(
        "SELECT * FROM positions WHERE state = 'ACTIVE'", portfolio_conn,
    )
    decay_levels = config.exit_flags.grade_decay_levels
    decay_days = config.exit_flags.grade_decay_days
    super_ext = config.exit_flags.super_extended_atr_multiple

    for _, pos in active.iterrows():
        bar, _ = _get_today_bar(ohlcv_conn, pos['symbol'], today_date)
        feat = _get_today_features(feat_conn, pos['symbol'], today_date)
        if bar is None or feat is None:
            continue

        # A. Stop hit (intraday low <= stop_price)
        if bar['low'] <= pos['stop_price']:
            pnl = (pos['stop_price'] - pos['entry_price']) / pos['entry_price']
            cur.execute(
                """UPDATE positions SET state='EXITED_STOP', exit_date=?,
                   exit_price=?, pnl_pct=? WHERE id=?""",
                (today_date, float(pos['stop_price']), float(pnl), pos['id']),
            )
            logger.info(f"EXITED_STOP: {pos['symbol']} pnl {pnl:.2%}")
            continue

        # B. Super-extended (close > sma50 + 7×atr14)
        if (
            pd.notna(feat['sma50']) and pd.notna(feat['atr14']) and
            bar['close'] > feat['sma50'] + super_ext * feat['atr14']
        ):
            pnl = (bar['close'] - pos['entry_price']) / pos['entry_price']
            cur.execute(
                """UPDATE positions SET state='EXITED_EXTENDED', exit_date=?,
                   exit_price=?, pnl_pct=? WHERE id=?""",
                (today_date, float(bar['close']), float(pnl), pos['id']),
            )
            logger.info(f"EXITED_EXTENDED: {pos['symbol']} pnl {pnl:.2%}")
            continue

        # C. Grade decay — drop >= decay_levels for decay_days consecutive sessions
        today_grade = _grade_today(feat_conn, ohlcv_conn, pos['symbol'], today_date)
        if today_grade and pos['entry_grade']:
            entry_ord = _grade_helper.get_grade_ordinal(pos['entry_grade'])
            today_ord = _grade_helper.get_grade_ordinal(today_grade)
            if (entry_ord - today_ord) >= decay_levels:
                streak = (pos['grade_decay_streak'] or 0) + 1
                if streak >= decay_days:
                    pnl = (bar['close'] - pos['entry_price']) / pos['entry_price']
                    cur.execute(
                        """UPDATE positions SET state='EXITED_DECAY', exit_date=?,
                           exit_price=?, pnl_pct=? WHERE id=?""",
                        (today_date, float(bar['close']), float(pnl), pos['id']),
                    )
                    logger.info(f"EXITED_DECAY: {pos['symbol']} pnl {pnl:.2%}")
                    continue
                else:
                    cur.execute(
                        "UPDATE positions SET grade_decay_streak=? WHERE id=?",
                        (streak, pos['id']),
                    )
            else:
                cur.execute(
                    "UPDATE positions SET grade_decay_streak=0 WHERE id=?",
                    (pos['id'],),
                )

    portfolio_conn.commit()

    state_counts = pd.read_sql_query(
        "SELECT state, COUNT(*) c FROM positions GROUP BY state", portfolio_conn,
    )
    logger.info("Tracker state: " + ", ".join(f"{r['state']}={r['c']}" for _, r in state_counts.iterrows()))


def main():
    _db.init_schemas()
    run_track()


if __name__ == '__main__':
    main()
