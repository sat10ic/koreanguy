"""N-51 — setup-family review horizons, versioned and configurable."""
from __future__ import annotations

from unidesk.research.horizons import HORIZONS, HORIZON_VERSION, all_horizons, horizon_for


def test_horizons_versioned():
    assert HORIZON_VERSION == "horizons-v1-ep3-base10-ipo15"


def test_ep_horizon_is_short():
    assert horizon_for("episodic_pivot") == 3


def test_ipo_horizon_is_long():
    assert horizon_for("ipo_base") == 15


def test_unknown_detector_gets_default():
    assert horizon_for("nonexistent") == horizon_for("_default")


def test_all_horizons_returns_copy():
    h = all_horizons()
    h["test"] = 999
    assert "test" not in all_horizons()
