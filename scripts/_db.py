import sqlite3
import os

DB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')

def get_conn(db_name):
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(os.path.join(DB_DIR, db_name))
    conn.row_factory = sqlite3.Row
    return conn

def ohlcv_conn():
    return get_conn('ohlcv.db')

def features_conn():
    return get_conn('features.db')

def portfolio_conn():
    return get_conn('portfolio_state.db')

def init_schemas():
    # OHLCV Schema
    with ohlcv_conn() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS ohlcv (
                symbol TEXT,
                date DATE,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume INTEGER,
                PRIMARY KEY (symbol, date)
            )
        ''')
    
    # Features Schema
    with features_conn() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS features (
                symbol TEXT, date DATE,
                sma20 REAL, sma21 REAL, sma50 REAL, sma200 REAL,
                ema10 REAL, ema20 REAL, ema21 REAL, ema50 REAL,
                atr14 REAL, atr21 REAL, adv20 REAL, rsi14 REAL,
                high_126 REAL, low_126 REAL,
                ret_1d REAL, ret_5d REAL, ret_21d REAL,
                purple_dot INTEGER,
                purple_dot_count_30d INTEGER,
                PRIMARY KEY (symbol, date)
            )
        ''')
        # Idempotent migrations for newly-added metrics
        for col, typ in (
            ('adr14_pct', 'REAL'),
            ('adr20_pct', 'REAL'),
            ('vol_ratio_20', 'REAL'),
            ('buying_force_score', 'REAL'),
            ('bf_score_30d_max', 'REAL'),
        ):
            try:
                conn.execute(f'ALTER TABLE features ADD COLUMN {col} {typ}')
            except sqlite3.OperationalError:
                pass  # column already exists
        
    # Portfolio State Schema — spec §6.3
    with portfolio_conn() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                signal_date DATE NOT NULL,
                state TEXT NOT NULL,
                entry_date DATE,
                entry_price REAL,
                stop_price REAL,
                size_shares INTEGER,
                exit_date DATE,
                exit_price REAL,
                pnl_pct REAL,
                regime_at_entry TEXT,
                entry_grade TEXT,
                grade_decay_streak INTEGER DEFAULT 0,
                notes TEXT,
                UNIQUE (symbol, signal_date)
            )
        ''')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_positions_state ON positions(state)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_positions_symbol ON positions(symbol)')

if __name__ == '__main__':
    init_schemas()
    print("Databases initialized.")
