"""Tests for the XP regime dial (manas_os.regime.xp)."""
import math

from manas_os.regime.xp import compute_xp, logit


def test_logit_midpoint_is_zero():
    assert abs(logit(50.0)) < 1e-9


def test_two_step_worked_example():
    """Hand-computed 2-step recursion, asserted to ~4 dp.

    Seeds: xp_prev=15.0, z_prev=20.0.

    Precise weights (0.592/0.471/0.198/0.334/0.067/0.077); term 5 = raw decliners.

    Step 1 inputs: up4=120, decliners=30, 10dma%=60, 20dma%=55
      z1 = 0.162*120 + 0.838*20 = 19.44 + 16.76 = 36.20
      log_xp1 = 0.592*ln(15) + 0.471*ln(36.20) + 0.198*logit(60) + 0.334
                - 0.067*ln(30) - 0.077*logit(55)
      => xp1 = 31.9625

    Step 2 inputs: up4=90, decliners=45, 10dma%=52, 20dma%=50 (uses xp1, z1)
      z2 = 0.162*90 + 0.838*36.20 = 44.9156
      => xp2 = 51.3096
    """
    xp1, z1 = compute_xp(120, 30, 60.0, 55.0, xp_prev=15.0, z_prev=20.0)
    assert round(z1, 4) == 36.2000
    assert round(xp1, 4) == 31.9625

    xp2, z2 = compute_xp(90, 45, 52.0, 50.0, xp_prev=xp1, z_prev=z1)
    assert round(z2, 4) == 44.9156
    assert round(xp2, 4) == 51.3096


def test_z_state_recursion_matches_formula():
    _, z = compute_xp(100, 10, 50.0, 50.0, xp_prev=10.0, z_prev=25.0)
    assert math.isclose(z, 0.162 * 100 + 0.838 * 25.0, rel_tol=0, abs_tol=1e-12)


def test_monotonic_in_up4():
    """Higher today_up4 => higher XP, all else equal."""
    xp_lo, _ = compute_xp(80, 40, 50.0, 50.0, xp_prev=15.0, z_prev=20.0)
    xp_hi, _ = compute_xp(160, 40, 50.0, 50.0, xp_prev=15.0, z_prev=20.0)
    assert xp_hi > xp_lo


def test_domain_guards_do_not_blow_up():
    """Zero counts and 0/100 percents must not raise (epsilon-guarded)."""
    xp, z = compute_xp(0, 0, 0.0, 100.0, xp_prev=0.0, z_prev=0.0)
    assert math.isfinite(xp) and math.isfinite(z)
