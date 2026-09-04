import os
import sys
import json
import logging
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts import _db, _config, _grade_helper

def setup_logger():
    os.makedirs('logs', exist_ok=True)
    logger = logging.getLogger('verify')
    logger.setLevel(logging.INFO)
    if logger.handlers:
        return logger
    fh = logging.FileHandler('logs/verify.log')
    fmt = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    fh.setFormatter(fmt)
    logger.addHandler(fh)
    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    logger.addHandler(ch)
    return logger

logger = setup_logger()
config = _config.load_config()


def compute_sizing(close, atr14, regime):
    """Per spec §5.5"""
    sz = config.sizing
    raw_stop_dist = max(0.02 * close, 0.5 * atr14) if atr14 and atr14 > 0 else 0.02 * close
    raw_stop_price = close - raw_stop_dist
    stop_pct = (close - raw_stop_price) / close
    stop_pct = min(stop_pct, sz.max_stop_pct)
    stop_pct = max(stop_pct, sz.min_stop_pct)
    suggested_stop = close * (1 - stop_pct)
    risk_per_share = close - suggested_stop

    risk_pct_map = {
        'RISK_ON': sz.risk_pct_risk_on,
        'CAUTION': sz.risk_pct_caution,
        'RISK_OFF': sz.risk_pct_risk_off,
    }
    risk_pct = risk_pct_map.get(regime, 0)
    portfolio_value = sz.portfolio_value
    risk_budget = portfolio_value * risk_pct
    if risk_per_share <= 0 or risk_budget <= 0:
        return suggested_stop, 0, risk_per_share, 0.0

    size_shares = int(risk_budget // risk_per_share)
    max_notional = portfolio_value * sz.max_allocation_pct
    cap_shares = int(max_notional // close) if close > 0 else 0
    size_shares = min(size_shares, cap_shares)
    size_pct = (size_shares * close) / portfolio_value if portfolio_value else 0
    return suggested_stop, size_shares, risk_per_share, size_pct


def layer_a(symbol, history_df, decisions):
    """Layer A — grade stability.

    Reads config.verify_layer_a. The intent (don't buy a one-day wonder) is
    sound, but the original hardcoded rule — all-A-tier for 2-3 consecutive
    days — was nearly unachievable after a working screen + hybrid grader,
    yielding 0 candidates. The achievable formulation:

      1. today's grade must meet min_grade_each_day (default A-)
      2. avg rank_pct over the lookback window must meet min_avg_rs (config
         value is in 0-100 percentile space; we convert)
      3. no severe downgrade streak (>= max_downgrades_in_5d consecutive
         steps down in the last 5 sessions)
      4. today's bucket must be Bullish (close > sma50)

    'all-tier-A-every-day' is available via require_all_atier (default false)
    for users who want the strict original behaviour.
    """
    lookback = decisions['layer_a_lookback']
    min_rank = decisions['layer_a_min_avg_rank']
    min_grade = decisions.get('layer_a_min_grade', 'A-')
    max_downgrades = decisions.get('layer_a_max_downgrades', 1)
    require_all = decisions.get('layer_a_require_all_atier', False)
    accept_grades = _grade_helper.GRADE_ORDER[:_grade_helper.GRADE_ORDER.index(min_grade) + 1] \
        if min_grade in _grade_helper.GRADE_ORDER else {"A+", "A", "A-"}

    if history_df.empty:
        return False, "no grade history"
    today_grade = history_df.iloc[0]['grade']
    last_n = history_df.head(lookback)
    if len(last_n) < min(lookback, 2):
        return False, "insufficient history"

    if require_all:
        if not all(g in accept_grades for g in last_n['grade']):
            return False, f"grades not all >={min_grade} in last {lookback}d"
    else:
        # Achievable: today must clear the floor; recent days just mustn't collapse.
        if today_grade not in accept_grades:
            return False, f"today {today_grade} < min_grade {min_grade}"

    avg_rank = last_n['rank_pct'].fillna(0).mean()
    if avg_rank < min_rank:
        return False, f"avg rank_pct {avg_rank:.2f} < {min_rank}"

    # Downgrade streak check (relaxed: allow up to max_downgrades consecutive
    # steps down before rejecting; original was 0 — any single step failed).
    last_5 = history_df.head(5)
    if len(last_5) >= 2:
        ords = [_grade_helper.get_grade_ordinal(g) for g in last_5['grade']]
        streak = 0
        max_streak = 0
        for i in range(len(ords) - 1):
            if ords[i] < ords[i + 1]:
                streak += 1
                max_streak = max(max_streak, streak)
            else:
                streak = 0
        if max_streak > max_downgrades:
            return False, f"downgrade streak {max_streak} > {max_downgrades} in last 5d"

    if last_n.iloc[0].get('bucket') != 'Bullish':
        return False, "not in Bullish bucket"
    return True, f"stable {today_grade}, avg_rank {avg_rank:.2f}"


def layer_b(row, decisions=None):
    """Layer B — chart structure. Reads config.verify_layer_b for the
    extension threshold (was hardcoded 5xATR via the extended_yellow flag)."""
    decisions = decisions or {}
    reasons = []
    ema10, ema20, ema50 = row.get('ema10'), row.get('ema20'), row.get('ema50')
    if pd.isna(ema10) or pd.isna(ema20) or pd.isna(ema50):
        return False, "missing EMA data"

    require_stack = decisions.get('layer_b_require_ema_stack', True)
    if require_stack and not (ema10 >= ema20 >= ema50):
        return False, f"EMA stack inverted ({ema10:.1f}/{ema20:.1f}/{ema50:.1f})"
    reasons.append("EMA stacked")

    require_stage2 = decisions.get('layer_b_require_stage2', True)
    if require_stage2:
        if row.get('sma50_rising', False):
            reasons.append("Stage 2")
        else:
            return False, "SMA50 not rising"

    # Extension check — now config-driven instead of the hardcoded extended_yellow
    # flag (which baked in 5xATR). Compute directly from row values so the
    # threshold in verify_layer_b.max_atr_extension_from_sma50 is honoured.
    max_ext = decisions.get('layer_b_max_atr_extension', 5.0)
    close = row.get('close')
    sma50 = row.get('sma50')
    atr14 = row.get('atr14')
    if (not pd.isna(close)) and (not pd.isna(sma50)) and (not pd.isna(atr14)) and atr14 > 0:
        ext_multiple = (close - sma50) / atr14
        if ext_multiple > max_ext:
            return False, f"extended ({ext_multiple:.1f}xATR from SMA50 > {max_ext})"
    reasons.append(f"not extended")

    require_vol = decisions.get('layer_b_require_volume_above_adv', True)
    vol = row.get('volume', 0)
    adv20 = row.get('adv20', 0)
    if require_vol and (not adv20 or vol < adv20):
        return False, f"volume {vol:.0f} < adv20 {adv20:.0f}"
    reasons.append(f"vol {vol/adv20:.2f}xadv20" if adv20 else "vol n/a")

    return True, "; ".join(reasons)


def get_sma50_rising(feat_conn, symbol, today_date):
    """Stage 2 check — today's sma50 > sma50 from 10 sessions ago."""
    q = (
        "SELECT date, sma50 FROM features WHERE symbol = ? "
        "AND date <= ? ORDER BY date DESC LIMIT 11"
    )
    df = pd.read_sql_query(q, feat_conn, params=(symbol, today_date))
    if len(df) < 11:
        return False
    today_sma50 = df.iloc[0]['sma50']
    past_sma50 = df.iloc[10]['sma50']
    if pd.isna(today_sma50) or pd.isna(past_sma50):
        return False
    return today_sma50 > past_sma50


def run_verify():
    screen_path = 'output/screen_today.csv'
    regime_path = 'output/regime_today.json'
    if not (os.path.exists(screen_path) and os.path.exists(regime_path)):
        logger.error("Missing screen or regime output. Aborting.")
        return

    screen_df = pd.read_csv(screen_path)
    with open(regime_path) as f:
        regime_data = json.load(f)
    regime = regime_data['regime']

    out_cols = [
        'symbol', 'tier', 'grade', 'grade_3d_avg', 'rs_score', 'close', 'atr14', 'adv20',
        'suggested_stop', 'risk_per_share', 'size_shares', 'size_pct',
        'purple_dot_today', 'purple_dot_count_30d', 'regime', 'notes',
    ]
    out_path = 'output/candidates.csv'

    if regime == 'RISK_OFF':
        pd.DataFrame(columns=out_cols).to_csv(out_path, index=False)
        logger.info("Regime RISK_OFF — wrote empty candidates.csv")
        _write_svro_arm([], regime_data)
        return

    setups = screen_df[screen_df['setup_pass'] == 1].copy()
    if setups.empty:
        pd.DataFrame(columns=out_cols).to_csv(out_path, index=False)
        logger.info("No setup_pass rows. Empty candidates.csv.")
        _write_svro_arm([], regime_data)
        return

    # Layer decisions — read from config (verify_layer_a / verify_layer_b)
    # instead of hardcoded inline values. This was the dead-config trap:
    # config.yaml had verify_layer_a values that were NEVER read, while the
    # code used a hardcoded dict. Now config is authoritative.
    vla = getattr(config, 'verify_layer_a', None)
    vla = vla if isinstance(vla, dict) else {}
    # min_avg_rs_3d is in 0-100 percentile space in config; rank_pct is 0-1.
    cfg_min_rank_100 = vla.get('min_avg_rs_3d', 75)
    decisions = {
        'layer_a_lookback': int(vla.get('lookback_days_grade_stability', 3)),
        'layer_a_min_avg_rank': float(cfg_min_rank_100) / 100.0,
        'layer_a_min_grade': vla.get('min_grade_each_day', 'A-'),
        'layer_a_max_downgrades': int(vla.get('max_downgrades_in_5d', 1)),
        'layer_a_require_all_atier': bool(vla.get('require_all_atier', False)),
    }
    vlb = getattr(config, 'verify_layer_b', None)
    vlb = vlb if isinstance(vlb, dict) else {}
    decisions.update({
        'layer_b_require_ema_stack': bool(vlb.get('require_ema_stack', True)),
        'layer_b_require_stage2': bool(vlb.get('require_stage2', True)),
        'layer_b_max_atr_extension': float(vlb.get('max_atr_extension_from_sma50', 5.0)),
        'layer_b_require_volume_above_adv': bool(vlb.get('require_volume_above_adv', True)),
    })

    feat_conn = _db.features_conn()
    ohlcv_conn = _db.ohlcv_conn()

    cur = feat_conn.cursor()
    cur.execute("SELECT DISTINCT date FROM features ORDER BY date DESC LIMIT 6")
    past_dates = [r[0] for r in cur.fetchall()]
    grade_frames = {d: _grade_helper.calculate_grades_for_date(feat_conn, ohlcv_conn, d) for d in past_dates}

    verified = []
    rejection_log = []

    for _, row in setups.iterrows():
        sym = row['symbol']
        rows = []
        for d in past_dates:
            gf = grade_frames[d]
            r = gf[gf['symbol'] == sym]
            if not r.empty:
                rows.append(r.iloc[0])
        if not rows:
            rejection_log.append((sym, 'no grade history'))
            continue
        history_df = pd.DataFrame(rows).reset_index(drop=True)

        ok_a, why_a = layer_a(sym, history_df, decisions)
        if not ok_a:
            rejection_log.append((sym, f"A: {why_a}"))
            continue

        row_b = row.copy()
        row_b['sma50_rising'] = get_sma50_rising(feat_conn, sym, row['date'])
        ok_b, why_b = layer_b(row_b, decisions)
        if not ok_b:
            rejection_log.append((sym, f"B: {why_b}"))
            continue

        stop, shares, rps, size_pct = compute_sizing(row['close'], row['atr14'], regime)
        tier = 'primary' if row.get('watchlist_member', 0) == 1 else 'secondary'
        last_n = history_df.head(decisions['layer_a_lookback'])
        grade_3d_avg = last_n['rank_pct'].fillna(0).mean()

        verified.append({
            'symbol': sym,
            'tier': tier,
            'grade': row['grade'],
            'grade_3d_avg': round(grade_3d_avg, 3),
            'rs_score': round(row['rs_score'], 4),
            'close': row['close'],
            'atr14': round(row['atr14'], 2) if pd.notna(row['atr14']) else None,
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

    df = pd.DataFrame(verified, columns=out_cols)
    df['tier_sort'] = df['tier'].map({'primary': 0, 'secondary': 1}).fillna(2)
    df['grade_sort'] = df['grade'].map(_grade_helper.GRADE_ORDINAL).fillna(-1)
    df = df.sort_values(['tier_sort', 'grade_sort', 'rs_score'], ascending=[True, False, False])
    df.drop(columns=['tier_sort', 'grade_sort'], errors='ignore').to_csv(out_path, index=False)

    _append_history(df, regime_data['date'])
    _write_svro_arm(verified, regime_data)

    logger.info(
        f"Verify: {len(setups)} setups -> {len(verified)} verified "
        f"({len(df[df['tier']=='primary'])} primary). Rejections: {len(rejection_log)}"
    )
    if rejection_log[:5]:
        logger.info("Sample rejections: " + "; ".join(f"{s}:{r}" for s, r in rejection_log[:5]))


def _append_history(df, date_str):
    hist_path = 'output/candidates_history.csv'
    if df.empty:
        return
    df_out = df.copy()
    df_out['date'] = date_str
    header = not os.path.exists(hist_path)
    df_out.to_csv(hist_path, mode='a', header=header, index=False)


def _write_svro_arm(verified_list, regime_data):
    """Build tomorrow's SVRO arm list (Phase 2 prep).

    Disabled by default — gated by `methods.svro_enabled` in config.yaml.
    The Based/Afzal detectors now own the EOD candidate stream; SVRO is
    archived as a future intraday confirmation hook. See FUTURE.md.
    """
    methods_cfg = getattr(config, 'methods', None)
    svro_enabled = bool(getattr(methods_cfg, 'svro_enabled', False)) if methods_cfg else False
    if not svro_enabled:
        return
    arm_path = 'output/svro_arm_today.json'
    arms = []
    for r in verified_list:
        if r['tier'] != 'primary':
            continue
        close = r['close']
        atr = r['atr14'] or 0
        arms.append({
            'symbol': r['symbol'],
            'reference_close': close,
            'atr14': atr,
            'or_ceiling': round(close + 0.5 * atr, 2),
            'or_floor': round(close - 0.5 * atr, 2),
            'volume_floor_5min': int((r['adv20'] or 0) / 75),
            'liquidity_gate_0920': int((r['adv20'] or 0) / 30),
            'suggested_stop': r['suggested_stop'],
            'size_shares': r['size_shares'],
            'grade': r['grade'],
            'svro_prior_score': round(
                0.4 * min(r['purple_dot_count_30d'] / 5.0, 1.0) +
                0.3 * r['grade_3d_avg'] +
                0.3 * min(r['rs_score'] * 5, 1.0), 3),
        })
    arms.sort(key=lambda x: x['svro_prior_score'], reverse=True)
    payload = {
        'date': regime_data['date'],
        'regime': regime_data['regime'],
        'risk_pct_override': regime_data.get('risk_pct_override', 0),
        'arms': arms,
    }
    with open(arm_path, 'w') as f:
        json.dump(payload, f, indent=2)


def main():
    run_verify()


if __name__ == '__main__':
    main()
