import os
import sys
import sqlite3
import pytest
import pandas as pd
from unittest.mock import MagicMock

from scripts import indicators, _db

@pytest.fixture
def mock_config(monkeypatch):
    mock = MagicMock()
    mock.purple_dot.pct_move_threshold = 0.05
    mock.purple_dot.volume_threshold_smallcap = 1000
    mock.purple_dot.volume_threshold_midcap = 5000
    mock.purple_dot.volume_threshold_default = 10000
    monkeypatch.setattr(indicators, 'config', mock)
    return mock

def test_get_volume_threshold(mock_config):
    assert indicators.get_volume_threshold(1000) == 1000  # smallcap
    assert indicators.get_volume_threshold(5000) == 5000  # midcap
    assert indicators.get_volume_threshold(15000) == 10000 # default
    assert indicators.get_volume_threshold(float('nan')) == 10000 # default

def test_compute_indicators_for_symbol(mock_config):
    # Create 200 days of fake OHLCV data
    # Normal days: open=100, close=100, high=105, low=95, volume=500
    dates = pd.date_range('2023-01-01', periods=200, freq='D')
    df = pd.DataFrame({
        'symbol': 'TEST',
        'date': dates.strftime('%Y-%m-%d'),
        'open': 100.0,
        'high': 105.0,
        'low': 95.0,
        'close': 100.0,
        'volume': 500
    })
    
    # Let's make the last day a Purple Dot
    # To be a purple dot: close > open, ret_1d >= 5%, volume >= threshold
    # Since previous close is 100, we need today's close >= 105
    df.loc[199, 'open'] = 100.0
    df.loc[199, 'close'] = 106.0
    df.loc[199, 'high'] = 110.0
    df.loc[199, 'low'] = 99.0
    df.loc[199, 'volume'] = 2000  # >= 1000 smallcap threshold
    
    # Calculate for smallcap (mcap = 1000 -> vol thresh = 1000)
    feat_df = indicators.compute_indicators_for_symbol(df, mcap=1000)
    
    # Assert ret_1d for last day is 0.06
    assert abs(feat_df.iloc[-1]['ret_1d'] - 0.06) < 1e-5
    
    # Assert purple dot is 1 for the last day
    assert feat_df.iloc[-1]['purple_dot'] == 1
    assert feat_df.iloc[-2]['purple_dot'] == 0
    
    # Assert rolling 30d sum works
    assert feat_df.iloc[-1]['purple_dot_count_30d'] == 1
    
    # Check SMA
    # Last SMA20: 19 days of 100, 1 day of 106 -> mean is 100.3
    assert abs(feat_df.iloc[-1]['sma20'] - 100.3) < 1e-5
    
    # Check high_126
    # It should be 110 (the high of the last day)
    assert feat_df.iloc[-1]['high_126'] == 110.0

def test_compute_indicators_fails_volume_threshold(mock_config):
    dates = pd.date_range('2023-01-01', periods=200, freq='D')
    df = pd.DataFrame({
        'symbol': 'TEST',
        'date': dates.strftime('%Y-%m-%d'),
        'open': 100.0,
        'high': 105.0,
        'low': 95.0,
        'close': 100.0,
        'volume': 500
    })
    df.loc[199, 'close'] = 106.0
    df.loc[199, 'volume'] = 2000
    
    # Calculate for midcap (mcap = 5000 -> vol thresh = 5000)
    feat_df = indicators.compute_indicators_for_symbol(df, mcap=5000)
    
    # Volume 2000 is < 5000 midcap threshold, so no purple dot
    assert feat_df.iloc[-1]['purple_dot'] == 0
