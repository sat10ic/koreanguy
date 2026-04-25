import os
import sys
import time
import logging
import pandas as pd
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts import _db, _config
from fyers_apiv3 import fyersModel

def setup_logger():
    os.makedirs('logs', exist_ok=True)
    logger = logging.getLogger('fetch')
    logger.setLevel(logging.INFO)
    fh = logging.FileHandler('logs/fetch.log')
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    
    ch = logging.StreamHandler()
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    return logger

logger = setup_logger()
config = _config.load_config()

def get_fyers_client():
    client_id = os.environ.get("FYERS_CLIENT_ID")
    token_env = getattr(config.fyers, 'access_token_env', 'FYERS_TOKEN')
    token = os.environ.get(token_env)
    
    if not client_id or not token:
        # Fallback to SwingEdge settings
        swingedge_settings_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'SwingEdge', 'config', 'settings.json')
        if os.path.exists(swingedge_settings_path):
            try:
                import json
                with open(swingedge_settings_path, 'r') as f:
                    settings = json.load(f)
                    client_id = client_id or settings.get('fyers_app_id')
                    token = token or settings.get('fyers_access_token')
            except Exception as e:
                logger.warning(f"Failed to read SwingEdge settings: {e}")
                
    if not client_id or not token:
        logger.error(f"Missing {token_env} or FYERS_CLIENT_ID, and couldn't find them in SwingEdge settings.")
        sys.exit(2)
        
    fyers = fyersModel.FyersModel(client_id=client_id, is_async=False, token=token, log_path="")
    return fyers

def fetch_history_with_retry(fyers, data, retries=3):
    backoff = 2
    for attempt in range(retries):
        try:
            response = fyers.history(data=data)
            if response.get('s') == 'error':
                msg = response.get('message', '').lower()
                if 'limit' in msg or response.get('code') == 429:
                    logger.warning(f"Rate limit hit for {data['symbol']}. Retrying in {backoff}s...")
                    time.sleep(backoff)
                    backoff *= 2
                    continue
                elif 'token' in msg or 'expired' in msg or 'authenticate' in msg:
                    logger.warning("Fyers token expired or invalid. Attempting auto-refresh...")
                    from scripts.refresh_token import refresh_access_token, update_settings
                    
                    app_id = os.environ.get("FYERS_CLIENT_ID", "")
                    secret_id = os.environ.get("FYERS_SECRET_ID", "")
                    refresh_token_val = ""
                    swingedge_settings_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'SwingEdge', 'config', 'settings.json')
                    
                    if os.path.exists(swingedge_settings_path):
                        try:
                            import json
                            with open(swingedge_settings_path, 'r') as f:
                                settings = json.load(f)
                                app_id = app_id or settings.get('fyers_app_id', '')
                                secret_id = secret_id or settings.get('fyers_secret_id', '')
                                refresh_token_val = settings.get('fyers_refresh_token', '')
                        except:
                            pass
                    
                    if not app_id or not secret_id or not refresh_token_val:
                        logger.error("Missing app_id, secret_id, or refresh_token. Cannot auto-refresh. Run scripts/refresh_token.py.")
                        sys.exit(2)
                        
                    tokens = refresh_access_token(app_id, secret_id, refresh_token_val)
                    if tokens:
                        update_settings(tokens, swingedge_settings_path)
                        logger.info("Successfully auto-refreshed Fyers token.")
                        # Update the fyers client token for subsequent retries
                        fyers.token = tokens['access_token']
                        continue
                    else:
                        logger.error("Auto-refresh failed. Run scripts/refresh_token.py manually.")
                        sys.exit(2)
                else:
                    return response # e.g. 404/delisted
            return response
        except Exception as e:
            logger.error(f"Network error on {data['symbol']}: {e}")
            if attempt < retries - 1:
                time.sleep(backoff)
                backoff *= 2
            else:
                return None
    return None

def upsert_ohlcv(conn, records):
    cursor = conn.cursor()
    cursor.executemany('''
        INSERT INTO ohlcv (symbol, date, open, high, low, close, volume)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(symbol, date) DO UPDATE SET
            open=excluded.open,
            high=excluded.high,
            low=excluded.low,
            close=excluded.close,
            volume=excluded.volume
    ''', records)
    conn.commit()

def compute_ew_index(conn):
    logger.info("Computing _NF500EW index...")
    df = pd.read_sql_query("SELECT symbol, date, close FROM ohlcv WHERE symbol NOT IN ('_NIFTY50', '_NF500EW')", conn)
    if df.empty:
        return
    
    df['date'] = pd.to_datetime(df['date'])
    pivoted = df.pivot(index='date', columns='symbol', values='close')
    pivoted = pivoted.sort_index()
    
    returns = pivoted.pct_change()
    ew_returns = returns.mean(axis=1)
    
    ew_index = (1 + ew_returns.fillna(0)).cumprod() * 1000
    
    records = []
    for date, val in ew_index.items():
        date_str = date.strftime('%Y-%m-%d')
        records.append(('_NF500EW', date_str, float(val), float(val), float(val), float(val), 0))
    
    upsert_ohlcv(conn, records)
    logger.info("Successfully updated _NF500EW.")

def get_last_date(conn, symbol):
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(date) FROM ohlcv WHERE symbol=?", (symbol,))
    row = cursor.fetchone()
    return row[0] if row and row[0] else None

def main():
    _db.init_schemas()
    
    # Load universe
    universe_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), getattr(config.universe, 'file', 'universe.csv'))
    if not os.path.exists(universe_path):
        logger.error(f"Universe file {universe_path} not found.")
        sys.exit(1)
        
    universe_df = pd.read_csv(universe_path)
    symbols = universe_df['symbol'].tolist()
    
    symbols_to_fetch = symbols + ['_NIFTY50']
    
    fyers = get_fyers_client()
    conn = _db.ohlcv_conn()
    
    failures = []
    success_count = 0
    total = len(symbols_to_fetch)
    
    today = datetime.now()
    batch_delay = getattr(config.fetch, 'batch_delay_ms', 200) / 1000.0
    backfill_days = getattr(config.fetch, 'backfill_days', 504)
    
    for sym in symbols_to_fetch:
        fyers_sym = "NSE:NIFTY50-INDEX" if sym == '_NIFTY50' else f"NSE:{sym}-EQ"
        
        last_date_str = get_last_date(conn, sym)
        if last_date_str:
            last_date = datetime.strptime(last_date_str, '%Y-%m-%d')
            start_date = last_date + timedelta(days=1)
        else:
            start_date = today - timedelta(days=int(backfill_days * 1.45))
        
        if start_date > today:
            success_count += 1
            continue
            
        candles = []
        current_start = start_date
        fetch_success = True
        
        while current_start <= today:
            current_end = min(current_start + timedelta(days=364), today)
            data = {
                "symbol": fyers_sym,
                "resolution": "1D",
                "date_format": "1",
                "range_from": current_start.strftime('%Y-%m-%d'),
                "range_to": current_end.strftime('%Y-%m-%d'),
                "cont_flag": "1"
            }
            
            resp = fetch_history_with_retry(fyers, data)
            
            if not resp:
                logger.warning(f"Failed to fetch {sym} due to network error.")
                fetch_success = False
                break
                
            if resp.get('s') == 'error':
                msg = resp.get('message', '').lower()
                logger.warning(f"Skipping {sym}: {msg}")
                fetch_success = False
                break
                
            chunk_candles = resp.get('candles', [])
            if chunk_candles:
                candles.extend(chunk_candles)
                
            current_start = current_end + timedelta(days=1)
            time.sleep(batch_delay)
            
        if not fetch_success:
            failures.append(sym)
            continue
            
        if candles:
            records = []
            for c in candles:
                dt = datetime.fromtimestamp(c[0]).strftime('%Y-%m-%d')
                records.append((sym, dt, c[1], c[2], c[3], c[4], c[5]))
            upsert_ohlcv(conn, records)
        
        success_count += 1
        
    compute_ew_index(conn)
    
    success_pct = success_count / total
    logger.info(f"Fetched {success_count}/{total} symbols through {today.strftime('%Y-%m-%d')}. Failures: {', '.join(failures) if failures else 'None'}")
    
    if success_pct < 0.95:
        logger.error(f"Fetch completed but success rate {success_pct:.1%} is below 95%. Exiting with error code 1.")
        sys.exit(1)

if __name__ == '__main__':
    main()
