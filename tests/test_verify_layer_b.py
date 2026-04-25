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

@patch('scripts.verify.pd.read_csv')
@patch('scripts.verify.json.load')
@patch('scripts.verify.open')
@patch('scripts.verify._grade_helper.calculate_grades_for_date')
@patch('scripts.verify.pd.read_sql_query')
@patch('os.path.exists')
def test_layer_b_rising_rs_fails(mock_exists, mock_read_sql, mock_calculate_grades, mock_open, mock_json_load, mock_read_csv, mock_config):
    mock_exists.return_value = True
    # Today RS is 0.1
    mock_read_csv.return_value = pd.DataFrame({
        'symbol': ['TEST'], 'setup_pass': [1], 'bucket': ['Bullish'], 'grade': ['A'], 'rs_score': [0.1],
        'close': [100], 'atr14': [1], 'watchlist_member': [1], 'extended_red': [0], 'extended_yellow': [0]
    })
    mock_json_load.return_value = {'regime': 'RISK_ON', 'risk_pct_override': 0.0025}
    
    # Yesterday RS is 0.2 (higher than today -> FAIL)
    def side_effect_grades(feat_conn, ohlcv_conn, date):
        return pd.DataFrame({
            'symbol': ['TEST'], 'grade': ['A'], 'rs_score': [0.2], 'rank_pct': [0.9], 'bucket': ['Bullish']
        })
    mock_calculate_grades.side_effect = side_effect_grades
    
    mock_feat_conn = MagicMock()
    mock_feat_conn.cursor().fetchall.return_value = [('2023-01-05',), ('2023-01-04',), ('2023-01-03',), ('2023-01-02',), ('2023-01-01',)]
    
    with patch('scripts._db.features_conn', return_value=mock_feat_conn):
        with patch('pandas.DataFrame.to_csv'):
            df_result = verify.run_verify()
            assert len(df_result) == 0

@patch('scripts.verify.pd.read_csv')
@patch('scripts.verify.json.load')
@patch('scripts.verify.open')
@patch('scripts.verify._grade_helper.calculate_grades_for_date')
@patch('scripts.verify.pd.read_sql_query')
@patch('os.path.exists')
def test_layer_b_vol_containment_fails(mock_exists, mock_read_sql, mock_calculate_grades, mock_open, mock_json_load, mock_read_csv, mock_config):
    mock_exists.return_value = True
    # Today ATR is 5.0
    mock_read_csv.return_value = pd.DataFrame({
        'symbol': ['TEST'], 'setup_pass': [1], 'bucket': ['Bullish'], 'grade': ['A'], 'rs_score': [0.5],
        'close': [100], 'atr14': [5.0], 'watchlist_member': [1], 'extended_red': [0], 'extended_yellow': [0]
    })
    mock_json_load.return_value = {'regime': 'RISK_ON', 'risk_pct_override': 0.0025}
    
    # Yesterday RS is 0.1 (today is higher -> PASS RS)
    def side_effect_grades(feat_conn, ohlcv_conn, date):
        import pandas as pd
        return pd.DataFrame({
            'symbol': ['TEST'], 'grade': ['A'], 'rs_score': [0.1], 'rank_pct': [0.9], 'bucket': ['Bullish']
        })
    mock_calculate_grades.side_effect = side_effect_grades
    
    # Avg ATR in history is 1.0 (5.0 > 1.2 * 1.0 -> FAIL)
    def side_effect_sql(query, conn):
        import pandas as pd
        return pd.DataFrame({'atr14': [1.0, 1.0, 1.0, 1.0, 1.0], 'purple_dot': [0]*5})
    mock_read_sql.side_effect = side_effect_sql
    
    mock_feat_conn = MagicMock()
    mock_feat_conn.cursor().fetchall.return_value = [('2023-01-05',), ('2023-01-04',), ('2023-01-03',), ('2023-01-02',), ('2023-01-01',)]
    
    with patch('scripts._db.features_conn', return_value=mock_feat_conn):
        with patch('pandas.DataFrame.to_csv'):
            df_result = verify.run_verify()
            assert len(df_result) == 0

@patch('scripts.verify.pd.read_csv')
@patch('scripts.verify.json.load')
@patch('scripts.verify.open')
@patch('scripts.verify._grade_helper.calculate_grades_for_date')
@patch('scripts.verify.pd.read_sql_query')
@patch('os.path.exists')
def test_layer_b_yellow_extension_needs_purple_dot(mock_exists, mock_read_sql, mock_calculate_grades, mock_open, mock_json_load, mock_read_csv, mock_config):
    mock_exists.return_value = True
    # extended_yellow is 1
    mock_read_csv.return_value = pd.DataFrame({
        'symbol': ['TEST'], 'setup_pass': [1], 'bucket': ['Bullish'], 'grade': ['A'], 'rs_score': [0.5],
        'close': [100], 'atr14': [1.0], 'watchlist_member': [1], 'extended_red': [0], 'extended_yellow': [1]
    })
    mock_json_load.return_value = {'regime': 'RISK_ON', 'risk_pct_override': 0.0025}
    
    def side_effect_grades(feat_conn, ohlcv_conn, date):
        import pandas as pd
        return pd.DataFrame({'symbol': ['TEST'], 'grade': ['A'], 'rs_score': [0.1], 'rank_pct': [0.9], 'bucket': ['Bullish']})
    mock_calculate_grades.side_effect = side_effect_grades
    
    # Case 1: No purple dots -> FAIL
    def side_effect_sql(query, conn):
        import pandas as pd
        return pd.DataFrame({'atr14': [1.0]*5, 'purple_dot': [0]*5})
    mock_read_sql.side_effect = side_effect_sql
    
    mock_feat_conn = MagicMock()
    mock_feat_conn.cursor().fetchall.return_value = [('2023-01-05',), ('2023-01-04',), ('2023-01-03',), ('2023-01-02',), ('2023-01-01',)]
    
    with patch('scripts._db.features_conn', return_value=mock_feat_conn):
        with patch('pandas.DataFrame.to_csv'):
            df_result = verify.run_verify()
            assert len(df_result) == 0
            
        # Case 2: One purple dot -> PASS
        def side_effect_sql_v2(query, conn):
            import pandas as pd
            return pd.DataFrame({'atr14': [1.0]*5, 'purple_dot': [0, 1, 0, 0, 0]})
        mock_read_sql.side_effect = side_effect_sql_v2
        
        with patch('pandas.DataFrame.to_csv'):
            df_result = verify.run_verify()
            assert len(df_result) == 1
