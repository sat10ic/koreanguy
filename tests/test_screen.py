import os
import sys
import pandas as pd
import pytest
from unittest.mock import MagicMock, patch

from scripts import screen

@pytest.fixture
def mock_config(monkeypatch):
    mock = MagicMock()
    mock.rs.weights = {'d1': 0.2, 'd5': 0.3, 'd21': 0.5}
    mock.universe.watchlist_file = 'watchlist.csv'
    monkeypatch.setattr(screen, 'config', mock)
    return mock

def test_get_grade():
    assert screen.get_grade(0.96) == "A+"
    assert screen.get_grade(0.90) == "A"
    assert screen.get_grade(0.80) == "A-"
    assert screen.get_grade(0.50) == "C"
    assert screen.get_grade(0.04) == "G"

@patch('scripts.screen.pd.read_sql_query')
@patch('scripts.screen.pd.read_csv')
@patch('os.path.exists')
def test_screen_logic(mock_exists, mock_read_csv, mock_read_sql, mock_config):
    # Setup mock data for 2 days
    def side_effect(query, conn):
        if "FROM features" in query:
            return pd.DataFrame({
                'symbol': ['TEST', 'TEST'],
                'date': ['2023-01-02', '2023-01-01'],
                'sma20': [100, 110],
                'sma50': [90, 90],
                'sma200': [80, 80],
                'atr14': [2, 2],
                'adv20': [1000, 1000],
                'high_126': [120, 120],
                'low_126': [80, 80],
                'ret_1d': [0.01, 0.01],
                'ret_5d': [0.05, 0.05],
                'ret_21d': [0.10, 0.10],
            })
        if "FROM ohlcv" in query:
            return pd.DataFrame({
                'symbol': ['TEST', 'TEST'],
                'date': ['2023-01-02', '2023-01-01'],
                'close': [105, 105], # Today 105 > SMA20(100) -> Reclaim if yesterday was below
            })
        return pd.DataFrame()
        
    mock_read_sql.side_effect = side_effect
    
    # Yesterday was above SMA20 (105 > 110 is False), wait...
    # Let's adjust mock so yesterday is below SMA20
    def side_effect_v2(query, conn):
        if "FROM features" in query:
            return pd.DataFrame({
                'symbol': ['TEST', 'TEST'],
                'date': ['2023-01-02', '2023-01-01'],
                'sma20': [100, 110], # SMA20 was 110 yesterday, 100 today
                'sma50': [90, 90],
                'sma200': [80, 80],
                'atr14': [2, 2],
                'adv20': [1000, 1000],
                'high_126': [120, 120],
                'low_126': [80, 80],
                'ret_1d': [0.01, 0.01],
                'ret_5d': [0.05, 0.05],
                'ret_21d': [0.10, 0.10],
            })
        if "FROM ohlcv" in query:
            return pd.DataFrame({
                'symbol': ['TEST', 'TEST'],
                'date': ['2023-01-02', '2023-01-01'],
                'close': [105, 105], # Close 105. Yesterday 105 <= 110 (True). Today 105 > 100 (True).
            })
        return pd.DataFrame()
    
    mock_read_sql.side_effect = side_effect_v2
    
    mock_exists.return_value = True
    mock_read_csv.return_value = pd.DataFrame({'symbol': ['TEST']})
    
    mock_feat_conn = MagicMock()
    mock_feat_conn.cursor().fetchall.return_value = [('2023-01-02',), ('2023-01-01',)]
    
    # Capture the output to avoid file creation in test
    with patch('pandas.DataFrame.to_csv'):
        df_result = screen.run_screen(mock_feat_conn, MagicMock())
        
        assert df_result.iloc[0]['setup_pass'] == 1
        assert df_result.iloc[0]['uptrend_pass'] == True
        assert df_result.iloc[0]['correction_pass'] == True
        assert df_result.iloc[0]['reclaim_pass'] == True
        assert df_result.iloc[0]['watchlist_member'] == 1
        assert df_result.iloc[0]['bucket'] == 'Bullish'
        assert df_result.iloc[0]['grade'] == 'A+' # Only 1 stock, rank_pct=1.0 -> A+
