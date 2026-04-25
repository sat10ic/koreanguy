import os
import sys
import json
import logging
import pandas as pd
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts import _db, _config

def setup_logger():
    os.makedirs('logs', exist_ok=True)
    logger = logging.getLogger('regime')
    logger.setLevel(logging.INFO)
    fh = logging.FileHandler('logs/regime.log')
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    
    ch = logging.StreamHandler()
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    return logger

logger = setup_logger()
config = _config.load_config()

def evaluate_regime(conn):
    # Fetch latest date from features
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(date) FROM features")
    row = cursor.fetchone()
    if not row or not row[0]:
        logger.error("No data found in features.db. Run indicators.py first.")
        return None
        
    latest_date = row[0]
    
    # Pillar 1: Trend (_NF500EW close > SMA21 and SMA21 rising)
    p1_pass = False
    p1_val = "Missing Data"
    
    # We need _NF500EW history to check if SMA21 is rising
    nf500_df = pd.read_sql_query("SELECT * FROM features WHERE symbol='_NF500EW' ORDER BY date ASC", conn)
    nf500_ohlcv = pd.read_sql_query("SELECT * FROM ohlcv WHERE symbol='_NF500EW' ORDER BY date ASC", _db.ohlcv_conn())
    
    # Merge them just in case close price is needed
    if not nf500_df.empty and not nf500_ohlcv.empty:
        nf500 = pd.merge(nf500_df, nf500_ohlcv[['date', 'close']], on='date')
        if len(nf500) >= 6:
            today_row = nf500.iloc[-1]
            five_days_ago_row = nf500.iloc[-6]
            
            if pd.notna(today_row.get('sma21')) and pd.notna(five_days_ago_row.get('sma21')):
                sma21_today = today_row['sma21']
                sma21_prev = five_days_ago_row['sma21']
                close_today = today_row['close']
                
                if close_today > sma21_today and sma21_today > sma21_prev:
                    p1_pass = True
                
                p1_val = f"Close: {close_today:.2f}, SMA21: {sma21_today:.2f} (prev: {sma21_prev:.2f})"
    
    # Pillar 2: Not Overbought (Nifty 50 RSI14 < config)
    p2_pass = False
    p2_val = "Missing Data"
    
    nifty50_df = pd.read_sql_query("SELECT * FROM features WHERE symbol='_NIFTY50' ORDER BY date ASC", conn)
    nifty50_ohlcv = pd.read_sql_query("SELECT * FROM ohlcv WHERE symbol='_NIFTY50' ORDER BY date ASC", _db.ohlcv_conn())
    
    if not nifty50_df.empty and not nifty50_ohlcv.empty:
        nifty50 = pd.merge(nifty50_df, nifty50_ohlcv[['date', 'close']], on='date')
        today_nifty = nifty50.iloc[-1]
        
        rsi14 = today_nifty.get('rsi14')
        if pd.notna(rsi14):
            overbought_thresh = config.regime.rsi_overbought
            if rsi14 < overbought_thresh:
                p2_pass = True
            p2_val = f"RSI: {rsi14:.2f} (threshold: {overbought_thresh})"
            
    # Pillar 3: Breadth
    p3_pass = False
    p3_val = "Missing Data"
    
    # Query all universe stocks (exclude _NIFTY50, _NF500EW) for the latest date
    f_df = pd.read_sql_query(f"SELECT symbol, sma50 FROM features WHERE date='{latest_date}' AND symbol NOT IN ('_NIFTY50', '_NF500EW')", conn)
    o_df = pd.read_sql_query(f"SELECT symbol, close FROM ohlcv WHERE date='{latest_date}' AND symbol NOT IN ('_NIFTY50', '_NF500EW')", _db.ohlcv_conn())
    
    if not f_df.empty and not o_df.empty:
        breadth_df = pd.merge(f_df, o_df, on='symbol')
        total_stocks = len(breadth_df)
        above_sma50 = len(breadth_df[breadth_df['close'] > breadth_df['sma50']])
        breadth_pct = above_sma50 / total_stocks if total_stocks > 0 else 0
        
        breadth_thresh = config.regime.breadth_threshold
        if breadth_pct >= breadth_thresh:
            p3_pass = True
        
        p3_val = f"Breadth: {breadth_pct*100:.1f}% (threshold: {breadth_thresh*100}%)"
        
    # Pillar 4: Volatility
    p4_pass = False
    p4_val = "Missing Data"
    
    if not nifty50_df.empty and not nifty50_ohlcv.empty:
        today_nifty = nifty50.iloc[-1]
        close = today_nifty.get('close')
        ema21 = today_nifty.get('ema21')
        atr21 = today_nifty.get('atr21')
        
        if pd.notna(close) and pd.notna(ema21) and pd.notna(atr21):
            diff = abs(close - ema21)
            limit = config.regime.vol_atr_multiple * atr21
            
            if diff < limit:
                p4_pass = True
                
            p4_val = f"Diff: {diff:.2f}, Limit: {limit:.2f}"
            
    # State Assignment
    pillars_passed = sum([p1_pass, p2_pass, p3_pass, p4_pass])
    if pillars_passed >= 3:
        regime_state = "RISK_ON"
        risk_pct = config.sizing.risk_pct_risk_on
    elif pillars_passed == 2:
        regime_state = "CAUTION"
        risk_pct = config.sizing.risk_pct_caution
    else:
        regime_state = "RISK_OFF"
        risk_pct = config.sizing.risk_pct_risk_off
        
    result = {
        "regime": regime_state,
        "pillars_passed": pillars_passed,
        "date": latest_date,
        "risk_pct_override": risk_pct,
        "pillars": {
            "trend": {
                "pass": p1_pass,
                "value": p1_val
            },
            "momentum": {
                "pass": p2_pass,
                "value": p2_val
            },
            "breadth": {
                "pass": p3_pass,
                "value": p3_val
            },
            "volatility": {
                "pass": p4_pass,
                "value": p4_val
            }
        }
    }
    
    return result

def main():
    feat_conn = _db.features_conn()
    result = evaluate_regime(feat_conn)
    
    if result:
        os.makedirs('output', exist_ok=True)
        out_path = 'output/regime_today.json'
        with open(out_path, 'w') as f:
            json.dump(result, f, indent=2)
        logger.info(f"Regime evaluated for {result['date']}: {result['regime']} ({result['pillars_passed']}/4 pillars). Wrote to {out_path}.")
    else:
        logger.error("Failed to evaluate regime.")

if __name__ == '__main__':
    main()
