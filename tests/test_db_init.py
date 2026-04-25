import os
import sqlite3
import pytest

# Monkeypatch the DB_DIR in _db so it uses a tmp_path
from scripts import _db

def test_init_schemas(tmp_path, monkeypatch):
    monkeypatch.setattr(_db, 'DB_DIR', str(tmp_path))
    
    _db.init_schemas()
    
    # Check OHLCV
    conn = sqlite3.connect(os.path.join(tmp_path, 'ohlcv.db'))
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ohlcv';")
    assert cursor.fetchone() is not None
    cursor.execute("PRAGMA table_info(ohlcv);")
    cols = [row[1] for row in cursor.fetchall()]
    assert set(cols) == {'symbol', 'date', 'open', 'high', 'low', 'close', 'volume'}
    
    # Check Features
    conn = sqlite3.connect(os.path.join(tmp_path, 'features.db'))
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='features';")
    assert cursor.fetchone() is not None
    cursor.execute("PRAGMA table_info(features);")
    cols = [row[1] for row in cursor.fetchall()]
    assert 'purple_dot' in cols
    assert 'sma20' in cols
    
    # Check Portfolio
    conn = sqlite3.connect(os.path.join(tmp_path, 'portfolio_state.db'))
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='positions';")
    assert cursor.fetchone() is not None
    cursor.execute("PRAGMA table_info(positions);")
    cols = [row[1] for row in cursor.fetchall()]
    assert 'state' in cols
    assert 'pnl_pct' in cols
