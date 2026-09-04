"""E-3 step 1 — the exact circuit-locked check.

The old heuristic flagged only high==low prints, so a name that traded all
day and closed PINNED at its band limit (MILKYMIST 2026-09-01: high 232.03 /
low 221.92 / close 232.03, exactly the +10% limit off 210.94) escaped. The
band-limit test recognises the close-at-limit print; the frozen test is
tightened to high==low==close so a mere close-on-its-high is never flagged.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from unidesk.contracts.market import DailyBar
from unidesk.momentum.data.market_store import VersionedDailyBar
from unidesk.momentum.universe.gates import circuit_locked

UTC = timezone.utc
DAY0 = datetime(2026, 9, 1, 18, 0, tzinfo=UTC)


def _bar(high, low, close, *, open_=None, volume=1000, i=0):
    session = (DAY0 + timedelta(days=i)).date()
    return VersionedDailyBar(
        bar=DailyBar(
            symbol="TEST", session=session,
            open=open_ if open_ is not None else close,
            high=high, low=low, close=close, volume=volume,
            data_version="test",
        ),
        available_at=DAY0 + timedelta(days=i + 1),
    )


def test_milkymist_0901_real_print_is_locked():
    """The acceptance case from the bhavcopy: prev 210.94, HIGH 232.03 /
    LOW 221.92 / CLOSE 232.03 — traded all day, closed pinned at the +10%
    band (target 232.034). The old high==low test missed this."""
    bars = [
        _bar(212.0, 209.5, 210.94, i=0),                    # prev session
        _bar(232.03, 221.92, 232.03, open_=230.79, volume=23_925_717, i=1),
    ]
    assert circuit_locked(bars) is True


def test_close_on_high_but_not_at_band_is_not_locked():
    # closed exactly on its high, ~+4.9% — a strong day, not a band print.
    bars = [_bar(104.9, 97.5, 104.9, open_=98.0, i=0),
            _bar(105.0, 99.0, 104.9, open_=100.0, i=1)]
    assert circuit_locked(bars) is False


def test_one_tick_below_the_limit_is_not_locked():
    # 104.95 is half a tick from the computed +5% target 105.00 — a normal
    # trade one tick under the band, deliberately NOT flagged (half-tick
    # tolerance).
    bars = [_bar(105.1, 99.0, 100.0, i=0),
            _bar(105.0, 100.0, 104.95, open_=100.0, i=1)]
    assert circuit_locked(bars) is False


def test_frozen_triple_equality_is_locked():
    bars = [_bar(50.2, 49.8, 50.0, i=0),
            _bar(47.6, 47.6, 47.6, open_=47.6, volume=120, i=1)]  # -4.8% print, frozen
    assert circuit_locked(bars) is True


def test_zero_volume_is_locked():
    bars = [_bar(50.2, 49.8, 50.0, i=0),
            _bar(50.0, 50.0, 50.0, open_=50.0, volume=0, i=1)]
    assert circuit_locked(bars) is True


def test_three_of_five_frozen_tail_is_locked():
    bars = [_bar(50.2, 49.8, 50.0, i=0)]
    bars += [_bar(47.6, 47.6, 47.6, i=i + 1) for i in range(3)]
    bars.append(_bar(48.0, 47.5, 47.8, i=4))
    assert circuit_locked(bars) is True


def test_downside_band_print_is_locked():
    # -10% limit: prev 100 -> target 90.00, close prints 89.95 (tick-rounded
    # band price 89.95 vs raw target 90.00 is within half a tick? No —
    # 89.95 is one tick away; the band print at 90.00 exact is the case).
    bars = [_bar(101.0, 99.5, 100.0, i=0),
            _bar(90.0, 90.0, 90.0, open_=90.0, volume=400, i=1)]
    assert circuit_locked(bars) is True
