"""Phase 1 core: risk/plan.py, scanner/gates.py, regime/governor.py (plan T1.1-T1.3)."""
from manas_os.risk import plan as rp
from manas_os.scanner import gates as g
from manas_os.regime.governor import governor


def _bar(i, close, low=None, high=None, volume=1000, delivery=50.0):
    return {"date": f"d{i}", "open": close, "high": high if high is not None else close + 1,
            "low": low if low is not None else close - 1, "close": close,
            "prev_close": close - 1, "volume": volume, "delivery_pct": delivery}


def _uptrend(n=260, start=100.0, step=0.3, **kw):
    return [_bar(i, start + i * step, **kw) for i in range(n)]


# ---------------- risk/plan.py ----------------

def test_choose_stop_picks_tightest_valid():
    bars = _uptrend(30)
    entry = bars[-1]["close"] + 1
    chosen = rp.choose_stop(bars, "momentum", entry)
    assert chosen is not None
    assert chosen["stop"] < entry
    assert chosen["stop_pct"] >= rp.STOP_FLOOR


def test_validate_refuses_wide_stop_27pct():
    r = rp.validate(entry=100, stop=73, measured_move=140, regime="RISK_ON",
                    account_capital=1_000_000)
    assert not r["pass"]
    assert any("exceeds" in x for x in r["reasons"])


def test_validate_refuses_rr_below_floor():
    r = rp.validate(entry=100, stop=95, measured_move=104, regime="RISK_ON",
                    account_capital=1_000_000)
    assert not r["pass"]
    assert any("R:R" in x for x in r["reasons"])


def test_validate_aggressive_profile_qty_math():
    # aggressive RISK_ON base 0.75%: 1_000_000*0.0075 = 7500 rupee risk; stop dist 5 -> 1500 qty
    r = rp.validate(entry=100, stop=95, measured_move=110, regime="RISK_ON",
                    profile="aggressive", account_capital=1_000_000)
    assert r["pass"]
    assert r["qty"] == 1500
    assert r["rr"] == 2.0


def test_validate_sector_third_position_halves_size():
    open_pos = [{"sector": "PHARMA", "risk_pct": 0.5}, ]
    r = rp.validate(entry=100, stop=95, measured_move=110, regime="RISK_ON",
                    sector="PHARMA", open_positions=open_pos,
                    profile="aggressive", account_capital=1_000_000)
    assert r["pass"] and r["half_size_applied"]
    two = [{"sector": "PHARMA", "risk_pct": 0.5}, {"sector": "PHARMA", "risk_pct": 0.5}]
    r2 = rp.validate(entry=100, stop=95, measured_move=110, regime="RISK_ON",
                     sector="PHARMA", open_positions=two,
                     profile="aggressive", account_capital=1_000_000)
    assert not r2["pass"]  # 3rd position in sector refused


def test_validate_no_trade_regime_refuses():
    r = rp.validate(entry=100, stop=95, measured_move=110, regime="NO_TRADE",
                    account_capital=1_000_000)
    assert not r["pass"]


def test_validate_circuit_band_refusal():
    r = rp.validate(entry=100, stop=97, measured_move=110, regime="RISK_ON",
                    circuit_band_pct=5.0, account_capital=1_000_000)
    assert not r["pass"]
    assert any("circuit band" in x for x in r["reasons"])


def test_exceptional_family_gets_7_5_cap():
    r = rp.validate(entry=100, stop=93, measured_move=115, regime="DEFENSIVE",
                    setup_family="ep", account_capital=1_000_000)
    # 7% stop passes only via the exceptional cap (DEFENSIVE cap is 4%)
    assert r["stop_cap_applied"] == 7.5
    assert r["pass"]


# ---------------- scanner/gates.py ----------------

def test_gate_regime_blocks_momentum_in_defensive():
    assert not g.gate_regime("momentum", "DEFENSIVE")["pass"]
    assert g.gate_regime("catalyst", "DEFENSIVE")["pass"]
    assert not g.gate_regime("catalyst", "NO_TRADE")["pass"]


def test_gate_tradability_lottery_exclusion():
    bars = _uptrend(30)
    bars[-5] = _bar(995, bars[-6]["close"] * 1.22)  # +22% day
    r = g.gate_tradability(bars, "PUMPY", {"market_cap_cr": 800}, None)
    assert not r["pass"] and "lottery" in r["reason"]


def test_gate_tradability_asm_refused():
    r = g.gate_tradability(_uptrend(30), "X", {"asm_stage": "LTASM-I"}, None)
    assert not r["pass"] and "ASM" in r["reason"]


def test_gate_trend_template_requires_lead_stack_and_nearness():
    up = _uptrend(260)
    r = g.gate_trend_template(up, "momentum", rs_rating=90.0)
    assert r["pass"], r["reason"]
    down = [_bar(i, 200 - i * 0.3) for i in range(260)]
    assert not g.gate_trend_template(down, "momentum", 90.0)["pass"]
    assert not g.gate_trend_template(up, "momentum", 60.0)["pass"]  # RS floor 80


def test_gate_fresh_leg_refuses_extension():
    bars = _uptrend(60)
    bars[-1] = _bar(999, bars[-2]["close"] * 1.12)  # spike far above 21EMA
    r = g.gate_fresh_leg(bars, pivot=None, breakout_age=None)
    assert not r["pass"] and "extended" in r["reason"]


def test_gate_fresh_leg_pass_and_states():
    bars = _uptrend(60, step=0.05)
    r = g.gate_fresh_leg(bars, pivot=bars[-1]["close"] * 0.99, breakout_age=3)
    assert r["pass"]


def test_gate_participation_negative_delivery_z_refused():
    bars = _uptrend(60, delivery=60.0)
    bars[-1]["delivery_pct"] = 20.0  # collapse vs its own norm
    r = g.gate_participation(bars)
    assert not r["pass"] and "BELOW" in r["reason"]


def test_run_cascade_fail_fast_records_gate():
    bars = _uptrend(260)
    ctx = {"bars": bars, "symbol": "T", "setup_family": "momentum",
           "market_mode": "DEFENSIVE", "quality": {}, "rs_rating": 90.0,
           "plan_result": {"pass": True}}
    out = g.run_cascade(ctx)
    assert not out["passed"] and out["failed_at"] == "regime"


def test_run_cascade_full_pass():
    bars = _uptrend(260, step=0.05)
    plan = rp.validate(entry=bars[-1]["close"], stop=bars[-1]["close"] * 0.96,
                       measured_move=bars[-1]["close"] * 1.10, regime="RISK_ON",
                       account_capital=1_000_000)
    ctx = {"bars": bars, "symbol": "T", "setup_family": "momentum",
           "market_mode": "RISK_ON", "quality": {"market_cap_cr": 5000},
           "rs_rating": 90.0, "plan_result": plan}
    out = g.run_cascade(ctx)
    assert out["passed"], out
    assert len(out["gates"]) == 6


# ---------------- regime/governor.py ----------------

def test_governor_locked_table():
    gv = governor("SELECTIVE", profile="aggressive")
    assert gv["max_cards"] == 4
    assert gv["risk_band"] == {"base_pct": 0.50, "hard_max_pct": 0.75}
    assert gv["open_risk_cap_pct"] == 2.0
    assert gv["push_allowed"] is True
    nt = governor("NO_TRADE")
    assert nt["max_cards"] == 0 and nt["push_allowed"] is False and nt["message"]


def test_governor_unknown_mode_degrades_to_no_trade():
    assert governor("GARBAGE")["market_mode"] == "NO_TRADE"
    assert governor(None)["max_cards"] == 0
