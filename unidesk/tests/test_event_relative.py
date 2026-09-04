from datetime import date

import pytest

from unidesk.contracts.base import ContractError
from unidesk.momentum.data.calendar import from_sessions
from unidesk.momentum.features.event_relative import (
    ep_event_features,
    ipo_event_features,
    sessions_since_event,
)


SESSIONS = [date(2026, 1, day) for day in (2, 5, 6, 7, 8)]
CALENDAR = from_sessions(SESSIONS)
OPENS = [100.0, 104.0, 111.0, 109.0, 115.0]
HIGHS = [105.0, 110.0, 115.0, 116.0, 120.0]
LOWS = [99.0, 102.0, 108.0, 107.0, 112.0]
CLOSES = [103.0, 109.0, 110.0, 114.0, 118.0]


def test_sessions_since_event_uses_observed_sessions_not_calendar_days():
    assert sessions_since_event(CALENDAR, SESSIONS[0], SESSIONS[4]) == 4
    with pytest.raises(ContractError, match="absent"):
        sessions_since_event(CALENDAR, SESSIONS[0], date(2026, 1, 3))


def test_ipo_features_are_listing_relative_and_optional_issue_price_is_honest():
    result = ipo_event_features(
        CALENDAR, anchor_session=SESSIONS[1], as_of=SESSIONS[4],
        highs=HIGHS, lows=LOWS, closes=CLOSES, issue_price=95.0,
    )
    assert result.sessions_since_event == 3
    assert result.first_day_range_pct == pytest.approx((110.0 - 102.0) / 102.0 * 100.0)
    assert result.pct_from_listing_high == pytest.approx((118.0 / 110.0 - 1.0) * 100.0)
    assert result.pct_from_listing_low == pytest.approx((118.0 / 102.0 - 1.0) * 100.0)
    assert result.base_vs_listing_range == pytest.approx((110.0 - 102.0) / (110.0 - 102.0))
    assert result.pct_from_issue_price == pytest.approx((118.0 / 95.0 - 1.0) * 100.0)
    assert ipo_event_features(
        CALENDAR, anchor_session=SESSIONS[1], as_of=SESSIONS[1],
        highs=HIGHS, lows=LOWS, closes=CLOSES,
    ).pct_from_issue_price is None


def test_ipo_features_do_not_read_future_bars():
    baseline = ipo_event_features(
        CALENDAR, anchor_session=SESSIONS[1], as_of=SESSIONS[3],
        highs=HIGHS, lows=LOWS, closes=CLOSES,
    )
    changed_future = ipo_event_features(
        CALENDAR, anchor_session=SESSIONS[1], as_of=SESSIONS[3],
        highs=HIGHS[:-1] + [999.0], lows=LOWS[:-1] + [1.0], closes=CLOSES[:-1] + [900.0],
    )
    assert changed_future == baseline


def test_ep_features_capture_gap_survival_volume_path_and_known_circuit_history():
    result = ep_event_features(
        CALENDAR, anchor_session=SESSIONS[2], as_of=SESSIONS[4],
        opens=OPENS, highs=HIGHS, lows=LOWS, closes=CLOSES,
        rvols=[None, None, 4.0, 2.0, 1.0],
        locked_sessions=[False, False, True, False, True],
        catalyst_type="results", catalyst_session=SESSIONS[2],
    )
    assert result.sessions_since_event == 2
    assert result.gap_pct == pytest.approx((111.0 / 109.0 - 1.0) * 100.0)
    assert result.gap_day_close_location == pytest.approx((110.0 - 108.0) / (115.0 - 108.0))
    assert result.held_above_gap_low is True
    assert result.volume_decay_since_gap == pytest.approx((1.0, 0.5, 0.25))
    assert result.days_locked_since_gap == 2
    assert result.catalyst_type == "results"
    assert result.days_since_catalyst == 2


def test_ep_features_fail_closed_for_partial_circuit_history_and_bad_catalyst_pairing():
    result = ep_event_features(
        CALENDAR, anchor_session=SESSIONS[2], as_of=SESSIONS[3],
        opens=OPENS, highs=HIGHS, lows=LOWS, closes=CLOSES,
        locked_sessions=[False, False, True, None, False],
    )
    assert result.days_locked_since_gap is None
    assert result.volume_decay_since_gap == (None, None)
    with pytest.raises(ContractError, match="requires catalyst_session"):
        ep_event_features(
            CALENDAR, anchor_session=SESSIONS[2], as_of=SESSIONS[3],
            opens=OPENS, highs=HIGHS, lows=LOWS, closes=CLOSES,
            catalyst_type="results",
        )


def test_ep_features_do_not_read_future_bars():
    baseline = ep_event_features(
        CALENDAR, anchor_session=SESSIONS[2], as_of=SESSIONS[3],
        opens=OPENS, highs=HIGHS, lows=LOWS, closes=CLOSES,
        rvols=[None, None, 4.0, 2.0, 1.0],
    )
    changed_future = ep_event_features(
        CALENDAR, anchor_session=SESSIONS[2], as_of=SESSIONS[3],
        opens=OPENS[:-1] + [1.0], highs=HIGHS[:-1] + [999.0],
        lows=LOWS[:-1] + [1.0], closes=CLOSES[:-1] + [999.0],
        rvols=[None, None, 4.0, 2.0, 99.0],
    )
    assert changed_future == baseline
