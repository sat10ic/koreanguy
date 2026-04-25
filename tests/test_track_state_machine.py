import os
import sys
import sqlite3
import pandas as pd
import json
import pytest
from unittest.mock import MagicMock, patch

from scripts import track, _db

@pytest.fixture
def mock_db_path(tmp_path):
    db_file = tmp_path / "portfolio_state.db"
    conn = sqlite3.connect(db_file)
    conn.execute("""
        CREATE TABLE portfolio_state (
            symbol TEXT,
            entry_date TEXT,
            entry_price REAL,
            stop_loss REAL,
            size_shares INTEGER,
            state TEXT,
            exit_price REAL,
            exit_date TEXT,
            pnl_pct REAL,
            days_held INTEGER
        )
    """)
    conn.commit()
    return str(db_file)

@patch('scripts.track.os.path.exists')
@patch('scripts.track.pd.read_csv')
@patch('scripts.track.open')
@patch('scripts.track.json.load')
def test_regime_exit_all(mock_json_load, mock_open, mock_read_csv, mock_exists, mock_db_path):
    # Setup: 1 open position, Regime is RISK_OFF
    conn = sqlite3.connect(mock_db_path)
    conn.execute("INSERT INTO portfolio_state (symbol, entry_price, state, days_held) VALUES ('TEST', 100, 'OPEN', 5)")
    conn.commit()
    
    mock_exists.return_value = True
    mock_read_csv.side_effect = [
        pd.DataFrame({'symbol': ['TEST'], 'close': [90], 'extended_red': [0]}), # screen_df
        pd.DataFrame() # candidates_df
    ]
    mock_json_load.return_value = {'regime': 'RISK_OFF', 'date': '2023-01-01'}
    
    with patch('scripts._db.portfolio_conn', return_value=conn):
        track.run_track()
        
        # Verify exit
        res = pd.read_sql_query("SELECT * FROM portfolio_state", conn)
        assert res.iloc[0]['state'] == 'EXITED_REGIME'
        assert float(res.iloc[0]['exit_price']) == 90.0

@patch('scripts.track.os.path.exists')
@patch('scripts.track.pd.read_csv')
@patch('scripts.track.open')
@patch('scripts.track.json.load')
def test_stop_loss_exit(mock_json_load, mock_open, mock_read_csv, mock_exists, mock_db_path):
    conn = sqlite3.connect(mock_db_path)
    conn.execute("INSERT INTO portfolio_state (symbol, entry_price, stop_loss, state, days_held) VALUES ('TEST', 100, 95, 'OPEN', 5)")
    conn.commit()
    
    mock_exists.return_value = True
    mock_read_csv.side_effect = [
        pd.DataFrame({'symbol': ['TEST'], 'close': [94], 'extended_red': [0]}), # screen_df (below stop 95)
        pd.DataFrame()
    ]
    mock_json_load.return_value = {'regime': 'RISK_ON', 'date': '2023-01-01'}
    
    with patch('scripts._db.portfolio_conn', return_value=conn):
        track.run_track()
        res = pd.read_sql_query("SELECT * FROM portfolio_state", conn)
        assert res.iloc[0]['state'] == 'EXITED_STOP'

@patch('scripts.track.os.path.exists')
@patch('scripts.track.pd.read_csv')
@patch('scripts.track.open')
@patch('scripts.track.json.load')
def test_time_decay_exit(mock_json_load, mock_open, mock_read_csv, mock_exists, mock_db_path):
    conn = sqlite3.connect(mock_db_path)
    # Held 10 days, price 101 (only 1% gain -> FAIL)
    conn.execute("INSERT INTO portfolio_state (symbol, entry_price, stop_loss, state, days_held) VALUES ('TEST', 100, 90, 'OPEN', 10)")
    conn.commit()
    
    mock_exists.return_value = True
    mock_read_csv.side_effect = [
        pd.DataFrame({'symbol': ['TEST'], 'close': [101], 'extended_red': [0]}), 
        pd.DataFrame()
    ]
    mock_json_load.return_value = {'regime': 'RISK_ON', 'date': '2023-01-01'}
    
    with patch('scripts._db.portfolio_conn', return_value=conn):
        track.run_track()
        res = pd.read_sql_query("SELECT * FROM portfolio_state", conn)
        assert res.iloc[0]['state'] == 'EXITED_DECAY'

@patch('scripts.track.os.path.exists')
@patch('scripts.track.pd.read_csv')
@patch('scripts.track.open')
@patch('scripts.track.json.load')
def test_new_entry(mock_json_load, mock_open, mock_read_csv, mock_exists, mock_db_path):
    conn = sqlite3.connect(mock_db_path)
    # Empty portfolio
    conn.commit()
    
    mock_exists.return_value = True
    mock_read_csv.side_effect = [
        pd.DataFrame(), # screen_df (no open positions to update)
        pd.DataFrame({
            'symbol': ['NEW'], 'close': [50], 'suggested_stop': [48], 'size_shares': [100]
        }) # candidates_df
    ]
    mock_json_load.return_value = {'regime': 'RISK_ON', 'date': '2023-01-01'}
    
    with patch('scripts._db.portfolio_conn', return_value=conn):
        track.run_track()
        res = pd.read_sql_query("SELECT * FROM portfolio_state WHERE state='OPEN'", conn)
        assert len(res) == 1
        assert res.iloc[0]['symbol'] == 'NEW'
        assert res.iloc[0]['entry_price'] == 50
