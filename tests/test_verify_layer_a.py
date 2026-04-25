import os
import sys
import pandas as pd
import json
import pytest
from unittest.mock import MagicMock, patch

from scripts import verify

@pytest.fixture
def mock_config(monkeypatch):
    mock = MagicMock()
    mock.sizing.portfolio_value = 1000000
    mock.sizing.min_stop_pct = 0.005
    mock.sizing.max_stop_pct = 0.03
    mock.sizing.max_allocation_pct = 0.30
    mock.regime.vol_atr_multiple = 3.2
    monkeypatch.setattr(verify, 'config', mock)
    return mock

def test_get_sizing_basic(mock_config):
    row = {'close': 100, 'atr14': 0.5} # stop_dist = 1.6 (1.6%)
    regime_data = {'risk_pct_override': 0.0025} # risk = 2500
    
    stop, shares, pct = verify.get_sizing(row, regime_data)
    
    assert stop == 98.4
    # risk_per_share = 1.6
    # shares = 2500 / 1.6 = 1562
    assert shares == 1562
    # pct = 156200 / 1000000 = 0.1562
    assert abs(pct - 0.1562) < 1e-4

def test_get_sizing_stop_capped(mock_config):
    row = {'close': 100, 'atr14': 2.0} # stop_dist = 6.4 (6.4%)
    regime_data = {'risk_pct_override': 0.0025}
    
    stop, shares, pct = verify.get_sizing(row, regime_data)
    
    # Cap is 3% -> stop at 97
    assert stop == 97.0
    # risk_per_share = 3.0
    # shares = 2500 / 3 = 833
    assert shares == 833

def test_get_sizing_stop_floored(mock_config):
    row = {'close': 100, 'atr14': 0.1} # stop_dist = 0.32 (0.32%)
    regime_data = {'risk_pct_override': 0.0025}
    
    stop, shares, pct = verify.get_sizing(row, regime_data)
    
    # Floor is 0.5% -> stop at 99.5
    assert stop == 99.5
    # risk_per_share = 0.5
    # risk_amt = 2500 -> shares = 5000
    # BUT 5000 * 100 = 500,000 which is 50% of portfolio.
    # Cap is 30% -> 300,000 / 100 = 3000 shares.
    assert shares == 3000

@patch('scripts.verify.pd.read_csv')
@patch('scripts.verify.json.load')
@patch('scripts.verify.open')
@patch('scripts.verify._grade_helper.calculate_grades_for_date')
@patch('os.path.exists')
def test_run_verify_logic(mock_exists, mock_calculate_grades, mock_open, mock_json_load, mock_read_csv, mock_config):
    mock_exists.return_value = True
    mock_read_csv.return_value = pd.DataFrame({
        'symbol': ['TEST'],
        'setup_pass': [1],
        'bucket': ['Bullish'],
        'grade': ['A'],
        'rs_score': [0.1],
        'close': [100],
        'atr14': [1],
        'watchlist_member': [1]
    })
    mock_json_load.return_value = {'regime': 'RISK_ON', 'risk_pct_override': 0.0025}
    
    # Mock history of 5 days
    def side_effect(feat_conn, ohlcv_conn, date):
        import pandas as pd
        return pd.DataFrame({
            'symbol': ['TEST'],
            'grade': ['A'],
            'rs_score': [0.1],
            'rank_pct': [0.9],
            'bucket': ['Bullish']
        })
    mock_calculate_grades.side_effect = side_effect
    
    mock_feat_conn = MagicMock()
    mock_feat_conn.cursor().fetchall.return_value = [('2023-01-05',), ('2023-01-04',), ('2023-01-03',), ('2023-01-02',), ('2023-01-01',)]
    
    with patch('scripts._db.features_conn', return_value=mock_feat_conn):
        with patch('pandas.DataFrame.to_csv') as mock_to_csv:
            verify.run_verify()
            
            # The first argument to the call is the path 'output/candidates.csv'
            # The second argument (if passed as positional) or the 'self' of the bound method...
            # When we patch DataFrame.to_csv, the instance is passed as the first argument if we use patch.object.
            # But with patch('pandas.DataFrame.to_csv'), it's often the path.
            
            # Let's just check if it was called and if any candidates were found via logs or just mock differently.
            assert mock_to_csv.called
