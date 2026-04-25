import os
import sys
import json
import pytest
from unittest.mock import MagicMock, patch

from scripts import regime

@pytest.fixture
def mock_config(monkeypatch):
    mock = MagicMock()
    mock.regime.breadth_threshold = 0.45
    mock.regime.rsi_overbought = 75
    mock.regime.vol_atr_multiple = 3.2
    mock.sizing.risk_pct_risk_on = 0.0025
    mock.sizing.risk_pct_caution = 0.00125
    mock.sizing.risk_pct_risk_off = 0
    monkeypatch.setattr(regime, 'config', mock)
    return mock

@patch('scripts.regime.pd.read_sql_query')
def test_all_pass_gives_risk_on(mock_read_sql, mock_config):
    # Setup mock data for all passing
    def side_effect(query, conn):
        import pandas as pd
        dates = [f'2023-01-0{i+1}' for i in range(6)]
        if "FROM features" in query and "symbol='_NF500EW'" in query:
            return pd.DataFrame({'date': dates, 'sma21': [90, 91, 92, 93, 94, 95]})
        if "FROM ohlcv" in query and "symbol='_NF500EW'" in query:
            return pd.DataFrame({'date': dates, 'close': [100]*6})
        if "FROM features" in query and "symbol='_NIFTY50'" in query:
            return pd.DataFrame({'date': ['2023-01-06'], 'rsi14': [50], 'ema21': [100], 'atr21': [10]})
        if "FROM ohlcv" in query and "symbol='_NIFTY50'" in query:
            return pd.DataFrame({'date': ['2023-01-06'], 'close': [102]})
        if "JOIN ohlcv" in query:
            return pd.DataFrame({'symbol': ['A', 'B'], 'close': [100, 100], 'sma50': [90, 90]}) # 100% breadth
        return pd.DataFrame()
        
    mock_read_sql.side_effect = side_effect
    
    mock_conn = MagicMock()
    mock_conn.cursor().fetchone.return_value = ('2023-01-06',)
    
    result = regime.evaluate_regime(mock_conn)
    assert result['pillars_passed'] == 4
    assert result['regime'] == 'RISK_ON'

@patch('scripts.regime.pd.read_sql_query')
def test_two_pass_gives_caution(mock_read_sql, mock_config):
    def side_effect(query, conn):
        import pandas as pd
        dates = [f'2023-01-0{i+1}' for i in range(6)]
        if "FROM features" in query and "symbol='_NF500EW'" in query:
            return pd.DataFrame({'date': dates, 'sma21': [90, 91, 92, 93, 94, 95]})
        if "FROM ohlcv" in query and "symbol='_NF500EW'" in query:
            return pd.DataFrame({'date': dates, 'close': [90]*6})
        if "FROM features" in query and "symbol='_NIFTY50'" in query:
            return pd.DataFrame({'date': ['2023-01-06'], 'rsi14': [50], 'ema21': [100], 'atr21': [10]})
        if "FROM ohlcv" in query and "symbol='_NIFTY50'" in query:
            return pd.DataFrame({'date': ['2023-01-06'], 'close': [140]})
        if "JOIN ohlcv" in query:
            return pd.DataFrame({'symbol': ['A', 'B'], 'close': [100, 100], 'sma50': [90, 90]})
        return pd.DataFrame()
        
    mock_read_sql.side_effect = side_effect
    mock_conn = MagicMock()
    mock_conn.cursor().fetchone.return_value = ('2023-01-06',)
    
    result = regime.evaluate_regime(mock_conn)
    assert result['pillars_passed'] == 2
    assert result['regime'] == 'CAUTION'

@patch('scripts.regime.pd.read_sql_query')
def test_zero_pass_gives_risk_off(mock_read_sql, mock_config):
    def side_effect(query, conn):
        import pandas as pd
        dates = [f'2023-01-0{i+1}' for i in range(6)]
        if "FROM features" in query and "symbol='_NF500EW'" in query:
            return pd.DataFrame({'date': dates, 'sma21': [90, 91, 92, 93, 94, 95]})
        if "FROM ohlcv" in query and "symbol='_NF500EW'" in query:
            return pd.DataFrame({'date': dates, 'close': [90]*6})
        if "FROM features" in query and "symbol='_NIFTY50'" in query:
            return pd.DataFrame({'date': ['2023-01-06'], 'rsi14': [80], 'ema21': [100], 'atr21': [10]})
        if "FROM ohlcv" in query and "symbol='_NIFTY50'" in query:
            return pd.DataFrame({'date': ['2023-01-06'], 'close': [140]})
        if "JOIN ohlcv" in query:
            return pd.DataFrame({'symbol': ['A', 'B'], 'close': [80, 80], 'sma50': [90, 90]})
        return pd.DataFrame()
        
    mock_read_sql.side_effect = side_effect
    mock_conn = MagicMock()
    mock_conn.cursor().fetchone.return_value = ('2023-01-06',)
    
    result = regime.evaluate_regime(mock_conn)
    assert result['pillars_passed'] == 0
    assert result['regime'] == 'RISK_OFF'

@patch('scripts.regime.pd.read_sql_query')
def test_boundary_three_pass(mock_read_sql, mock_config):
    def side_effect(query, conn):
        import pandas as pd
        dates = [f'2023-01-0{i+1}' for i in range(6)]
        if "FROM features" in query and "symbol='_NF500EW'" in query:
            return pd.DataFrame({'date': dates, 'sma21': [90, 91, 92, 93, 94, 95]})
        if "FROM ohlcv" in query and "symbol='_NF500EW'" in query:
            return pd.DataFrame({'date': dates, 'close': [100]*6})
        if "FROM features" in query and "symbol='_NIFTY50'" in query:
            return pd.DataFrame({'date': ['2023-01-06'], 'rsi14': [50], 'ema21': [100], 'atr21': [10]})
        if "FROM ohlcv" in query and "symbol='_NIFTY50'" in query:
            return pd.DataFrame({'date': ['2023-01-06'], 'close': [102]})
        if "JOIN ohlcv" in query:
            # Fails Breadth (0%)
            return pd.DataFrame({'symbol': ['A', 'B'], 'close': [80, 80], 'sma50': [90, 90]})
        return pd.DataFrame()
        
    mock_read_sql.side_effect = side_effect
    mock_conn = MagicMock()
    mock_conn.cursor().fetchone.return_value = ('2023-01-06',)
    
    result = regime.evaluate_regime(mock_conn)
    assert result['pillars_passed'] == 3
    assert result['regime'] == 'RISK_ON'

@patch('scripts.regime.pd.read_sql_query')
def test_missing_data_gracefully(mock_read_sql, mock_config):
    def side_effect(query, conn):
        import pandas as pd
        # Return empty dataframes to simulate missing data
        return pd.DataFrame()
        
    mock_read_sql.side_effect = side_effect
    mock_conn = MagicMock()
    mock_conn.cursor().fetchone.return_value = ('2023-01-01',)
    
    result = regime.evaluate_regime(mock_conn)
    assert result['pillars_passed'] == 0
    assert result['regime'] == 'RISK_OFF'
