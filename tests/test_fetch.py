import os
import sys
import sqlite3
import pytest
from unittest.mock import patch, MagicMock

from scripts import fetch, _db

@pytest.fixture
def test_conn(tmp_path, monkeypatch):
    monkeypatch.setattr(_db, 'DB_DIR', str(tmp_path))
    
    universe_path = os.path.join(tmp_path, 'universe.csv')
    with open(universe_path, 'w') as f:
        f.write("symbol,name,sector,industry,market_cap_cr\n")
        f.write("ZOMATO,Zomato,Tech,Internet,100000\n")
        
    # patch config
    mock_config = MagicMock()
    mock_config.universe.file = universe_path
    mock_config.fetch.batch_delay_ms = 0
    mock_config.fetch.backfill_days = 504
    monkeypatch.setattr(fetch, 'config', mock_config)
    
    _db.init_schemas()
    return _db.ohlcv_conn()

def test_fresh_backfill(test_conn, monkeypatch):
    mock_fyers = MagicMock()
    # Mocking a list of 504 candles
    mock_fyers.history.return_value = {
        's': 'ok',
        'candles': [[1609459200 + i*86400, 100, 105, 95, 102, 1000] for i in range(504)]
    }
    
    monkeypatch.setattr(fetch, 'get_fyers_client', lambda: mock_fyers)
    
    # Run fetch
    fetch.main()
    
    cursor = test_conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM ohlcv WHERE symbol='ZOMATO'")
    assert cursor.fetchone()[0] == 504
    
    cursor.execute("SELECT COUNT(*) FROM ohlcv WHERE symbol='_NIFTY50'")
    assert cursor.fetchone()[0] == 504
    
    cursor.execute("SELECT COUNT(*) FROM ohlcv WHERE symbol='_NF500EW'")
    assert cursor.fetchone()[0] == 504

def test_incremental(test_conn, monkeypatch):
    cursor = test_conn.cursor()
    cursor.execute("INSERT INTO ohlcv (symbol, date, close) VALUES ('ZOMATO', '2025-01-01', 100)")
    cursor.execute("INSERT INTO ohlcv (symbol, date, close) VALUES ('_NIFTY50', '2025-01-01', 100)")
    test_conn.commit()
    
    mock_fyers = MagicMock()
    mock_fyers.history.return_value = {
        's': 'ok',
        'candles': [[1609459200, 100, 105, 95, 102, 1000]]
    }
    monkeypatch.setattr(fetch, 'get_fyers_client', lambda: mock_fyers)
    
    fetch.main()
    
    cursor.execute("SELECT COUNT(*) FROM ohlcv WHERE symbol='ZOMATO'")
    assert cursor.fetchone()[0] == 2

def test_skip_delisted(test_conn, monkeypatch):
    mock_fyers = MagicMock()
    def mock_history(data):
        if 'ZOMATO' in data['symbol']:
            return {'s': 'error', 'message': 'Invalid symbol'}
        return {'s': 'ok', 'candles': [[1609459200, 100, 105, 95, 102, 1000]]}
    mock_fyers.history.side_effect = mock_history
    monkeypatch.setattr(fetch, 'get_fyers_client', lambda: mock_fyers)
    
    # It should not exit immediately, but at the end it exits 1 because success rate < 95%
    with pytest.raises(SystemExit) as exc:
        fetch.main()
    assert exc.value.code == 1

def test_token_expired(test_conn, monkeypatch):
    mock_fyers = MagicMock()
    mock_fyers.history.return_value = {'s': 'error', 'message': 'Token expired'}
    monkeypatch.setattr(fetch, 'get_fyers_client', lambda: mock_fyers)
    
    with pytest.raises(SystemExit) as exc:
        fetch.main()
    assert exc.value.code == 2
