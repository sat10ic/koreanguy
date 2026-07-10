"""WAVE K K4 — smoke tests for scanner/discovery.py (counterfactual-only bucket)."""
import sqlite3

from manas_os import db
from manas_os.scanner import discovery


def _mk_conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(db._SCHEMA.read_text(encoding="utf-8"))
    return conn


def _seed_symbol(conn, symbol, n=90, price=100.0):
    import datetime
    d = datetime.date(2026, 1, 1)
    prev_close = None
    for i in range(n):
        d2 = d + datetime.timedelta(days=i)
        p = price + i * 0.3
        conn.execute(
            "INSERT INTO daily_prices (symbol, series, trade_date, open, high, low, close, "
            "prev_close, volume, delivery_qty, delivery_pct) VALUES (?, 'EQ', ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (symbol, d2.isoformat(), p, p + 1, p - 1, p, prev_close, 500_000, 200_000, 40.0),
        )
        prev_close = p
    conn.commit()
    return d2.isoformat()


def test_build_bucket_empty_when_no_prices():
    conn = _mk_conn()
    assert discovery.build_bucket(conn, "2026-01-01") == []


def test_build_bucket_and_persist_roundtrip():
    conn = _mk_conn()
    scan_date = _seed_symbol(conn, "TESTCO", n=90)
    bucket = discovery.build_bucket(conn, scan_date)
    rows = discovery.persist_bucket(conn, scan_date, bucket)
    assert rows == len(bucket)
    persisted = conn.execute(
        "SELECT symbol, archetypes_json, metrics_json FROM discovery_bucket WHERE scan_date = ?",
        (scan_date,),
    ).fetchall()
    assert len(persisted) == rows


def test_run_never_raises_and_logs_pipeline_run():
    conn = _mk_conn()
    scan_date = _seed_symbol(conn, "RUNCO", n=90)
    result = discovery.run(conn, scan_date)
    assert result["status"] in ("ok", "skip")
    log = conn.execute(
        "SELECT status FROM pipeline_runs WHERE stage = ?", (discovery.STAGE,)
    ).fetchall()
    assert len(log) == 1


def test_run_skip_when_no_prices_on_or_before_date():
    conn = _mk_conn()
    result = discovery.run(conn, "2020-01-01")
    assert result["status"] == "skip"
    assert result["rows"] == 0


def _seed_reversal_symbol(conn, symbol, n=91):
    """K7: strong prior uptrend (180d high >= 1.5x the 252d low) then 5 red
    days on declining volume INTO a 15-40% correction off the 180d high,
    THEN one up day (the reversal trigger) -- current-price force is weak
    here by construction, so this symbol must NOT need current force to be
    tagged 'reversal'."""
    import datetime
    d = datetime.date(2026, 1, 1)
    prev_close = None
    price = 100.0
    d2_last = d
    for i in range(n - 6):
        d2 = d + datetime.timedelta(days=i)
        price = 100.0 + i * 1.2  # strong uptrend leg
        conn.execute(
            "INSERT INTO daily_prices (symbol, series, trade_date, open, high, low, close, "
            "prev_close, volume, delivery_qty, delivery_pct) VALUES (?, 'EQ', ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (symbol, d2.isoformat(), price, price + 1, price - 1, price, prev_close, 600_000, 200_000, 40.0),
        )
        prev_close = price
        d2_last = d2
    vol = 600_000
    for j in range(5):
        d2_last = d2_last + datetime.timedelta(days=1)
        price = price * 0.95
        vol = int(vol * 0.9)
        conn.execute(
            "INSERT INTO daily_prices (symbol, series, trade_date, open, high, low, close, "
            "prev_close, volume, delivery_qty, delivery_pct) VALUES (?, 'EQ', ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (symbol, d2_last.isoformat(), price, price + 1, price - 1, price, prev_close, vol, 200_000, 40.0),
        )
        prev_close = price
    # trigger 1: today's up day closes the 3-5 red-day run
    d2_last = d2_last + datetime.timedelta(days=1)
    price = price * 1.02
    conn.execute(
        "INSERT INTO daily_prices (symbol, series, trade_date, open, high, low, close, "
        "prev_close, volume, delivery_qty, delivery_pct) VALUES (?, 'EQ', ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (symbol, d2_last.isoformat(), price, price + 1, price - 1, price, prev_close, vol, 200_000, 40.0),
    )
    conn.commit()
    return d2_last.isoformat()


def test_reversal_archetype_fires_without_current_force_via_180d_prior_strength():
    conn = _mk_conn()
    scan_date = _seed_reversal_symbol(conn, "REVCO", n=91)
    bucket = discovery.build_bucket(conn, scan_date)
    entry = next((e for e in bucket if e["symbol"] == "REVCO"), None)
    assert entry is not None, "reversal pick must be admitted without current-price force"
    assert "reversal" in entry["archetypes"]
    # current force (off TODAY's close, only just past the pullback) must be
    # weak -- proves the archetype fired via 180d prior strength, not
    # current-price buying force.
    assert entry["metrics"]["pct_up_from_65d_low"] < discovery.BUYING_FORCE_PCT_UP_65D_LOW


def test_recent_listing_waives_current_force_when_fresh():
    """A symbol with <90 sessions of history and strong velocity (purple
    dots) but no computable 65d-low force yet must still be tagged
    recent_listing -- K4.1 GROWW-class waiver."""
    conn = _mk_conn()
    import datetime
    # ANCHOR symbol starts well before FRESHIPO so FRESHIPO's own first row
    # is NOT the archive's global-first row (listing_status treats that as
    # "unknown"/pre-archive-start, not a genuine fresh listing).
    anchor_d = datetime.date(2020, 1, 1)
    anchor_prev = None
    for i in range(400):
        ad = anchor_d + datetime.timedelta(days=i)
        ap = 50.0 + i * 0.01
        conn.execute(
            "INSERT INTO daily_prices (symbol, series, trade_date, open, high, low, close, "
            "prev_close, volume, delivery_qty, delivery_pct) VALUES (?, 'EQ', ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("ANCHOR", ad.isoformat(), ap, ap + 1, ap - 1, ap, anchor_prev, 500_000, 200_000, 40.0),
        )
        anchor_prev = ap
    conn.commit()

    d = datetime.date(2026, 1, 1)
    prev_close = None
    price = 100.0
    d2 = d
    for i in range(40):
        d2 = d + datetime.timedelta(days=i)
        price = price * (1.06 if i % 3 == 0 else 1.0)
        conn.execute(
            "INSERT INTO daily_prices (symbol, series, trade_date, open, high, low, close, "
            "prev_close, volume, delivery_qty, delivery_pct) VALUES (?, 'EQ', ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("FRESHIPO", d2.isoformat(), price, price * 1.02, price * 0.98, price, prev_close,
             700_000, 300_000, 42.0),
        )
        prev_close = price
    conn.commit()
    scan_date = d2.isoformat()
    bucket = discovery.build_bucket(conn, scan_date)
    entry = next((e for e in bucket if e["symbol"] == "FRESHIPO"), None)
    assert entry is not None
    assert "recent_listing" in entry["archetypes"]
    assert entry["metrics"]["days_since_listing"] <= discovery.RECENT_LISTING_MAX_DAYS


def test_groww_fixture_recent_listing_leg_force_gets_bucket_tag():
    """GROWW repro shape: 159-session recent listing, qualifying prior-leg
    force, strong velocity, but current close is below the 30% force gate.
    It must still enter as recent_listing under the K4.1 waiver."""
    conn = _mk_conn()
    import datetime

    anchor_d = datetime.date(2020, 1, 1)
    anchor_prev = None
    for i in range(400):
        ad = anchor_d + datetime.timedelta(days=i)
        ap = 50.0 + i * 0.01
        conn.execute(
            "INSERT INTO daily_prices (symbol, series, trade_date, open, high, low, close, "
            "prev_close, volume, delivery_qty, delivery_pct) VALUES (?, 'EQ', ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("ANCHOR", ad.isoformat(), ap, ap + 1, ap - 1, ap, anchor_prev, 500_000, 200_000, 40.0),
        )
        anchor_prev = ap

    start = datetime.date(2026, 1, 1)
    fast_prev = None
    for i in range(159):
        d = start + datetime.timedelta(days=i)
        close = 50.0 + i * 2.0
        conn.execute(
            "INSERT INTO daily_prices (symbol, series, trade_date, open, high, low, close, "
            "prev_close, volume, delivery_qty, delivery_pct) VALUES (?, 'EQ', ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("FASTCO", d.isoformat(), close, close + 2, close - 2, close, fast_prev,
             700_000, 300_000, 42.0),
        )
        fast_prev = close

    prev_close = None
    scan_date = None
    for i in range(159):
        d = start + datetime.timedelta(days=i)
        close = 112.0
        high = 114.0
        low = 110.0
        if i >= 94:
            low = 100.0
            close = 128.7
            high = 130.0
        if i == 120:
            high = 147.4
            close = 143.0
        if i in (105, 118, 132, 146):
            close = 106.0 if prev_close is None else prev_close * 1.06
            high = close * 1.02
            low = close * 0.98
        if i == 158:
            close = 128.7
            high = 130.0
            low = 126.0
        conn.execute(
            "INSERT INTO daily_prices (symbol, series, trade_date, open, high, low, close, "
            "prev_close, volume, delivery_qty, delivery_pct) VALUES (?, 'EQ', ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("GROWW", d.isoformat(), close, high, low, close, prev_close, 700_000, 300_000, 42.0),
        )
        prev_close = close
        scan_date = d.isoformat()
    conn.commit()

    bucket = discovery.build_bucket(conn, scan_date)
    entry = next((e for e in bucket if e["symbol"] == "GROWW"), None)
    assert entry is not None
    assert "recent_listing" in entry["archetypes"]
    assert entry["metrics"]["days_since_listing"] == 159
    assert entry["metrics"]["pct_up_from_65d_low"] < discovery.BUYING_FORCE_PCT_UP_65D_LOW
    assert round(entry["metrics"]["leg_force_from_65d_low"], 1) == 47.4


def test_size_control_caps_each_archetype_and_ranks_by_velocity_score():
    entries = []
    for i in range(20):
        entries.append({
            "symbol": f"S{i}",
            "archetypes": ["vcp_coil"],
            "metrics": {"adr20_pctile": float(i), "purple_dot_count_60d": 0,
                        "momentum_63d_pctile": 0.0},
        })
    capped = discovery._apply_size_control(entries)
    assert len(capped) == discovery.CAP_PER_ARCHETYPE
    kept_symbols = {e["symbol"] for e in capped}
    assert kept_symbols == {f"S{i}" for i in range(20 - discovery.CAP_PER_ARCHETYPE, 20)}


def test_size_control_keeps_symbol_if_it_survives_cap_in_any_archetype():
    # crowded out of vcp_coil, but sole member of reversal -> survives there
    multi = {
        "symbol": "MULTI", "archetypes": ["vcp_coil", "reversal"],
        "metrics": {"adr20_pctile": 0.0, "purple_dot_count_60d": 0, "momentum_63d_pctile": 0.0},
    }
    high_score_single_archetype = [
        {"symbol": f"H{i}", "archetypes": ["vcp_coil"],
         "metrics": {"adr20_pctile": 100.0, "purple_dot_count_60d": 5, "momentum_63d_pctile": 100.0}}
        for i in range(discovery.CAP_PER_ARCHETYPE)
    ]
    bucket = high_score_single_archetype + [multi]
    capped = discovery._apply_size_control(bucket)
    assert "MULTI" in {e["symbol"] for e in capped}


def test_size_control_no_blanket_multi_archetype_immunity():
    """K7 fix: a multi-archetype name that fails the cap in EVERY archetype
    it carries is dropped -- the old blanket immunity for any 2+-tag name
    was unbounded and drove buckets to 315-470/day."""
    weakest = {
        "symbol": "MULTI_WEAK",
        "archetypes": ["vcp_coil", "d2_episodic"],
        "metrics": {"adr20_pctile": 0.0, "purple_dot_count_60d": 0,
                    "momentum_63d_pctile": 0.0, "leg_force_from_65d_low": 0.0},
    }
    crowded = []
    for archetype in ("vcp_coil", "d2_episodic"):
        for i in range(discovery.CAP_PER_ARCHETYPE + 5):
            crowded.append({
                "symbol": f"{archetype}_{i}",
                "archetypes": [archetype],
                "metrics": {"adr20_pctile": 100.0 - i * 0.1, "purple_dot_count_60d": 5,
                            "momentum_63d_pctile": 100.0, "leg_force_from_65d_low": 60.0},
            })
    capped = discovery._apply_size_control(crowded + [weakest])
    assert "MULTI_WEAK" not in {e["symbol"] for e in capped}


def test_size_control_reversal_ranked_by_tightness_proximity():
    """K7 fix: within the reversal archetype, ranking is ascending prev-day
    tightness percentile (proximity-to-trigger), NOT the momentum-weighted
    velocity score -- reversal members sit at momentum bottoms by
    construction (BSOFT 12-Jun-2026: momentum pctile 5, tightness 15)."""
    tight_bottom = {
        "symbol": "BSOFTLIKE", "archetypes": ["reversal"],
        "metrics": {"adr20_pctile": 10.0, "purple_dot_count_60d": 0,
                    "momentum_63d_pctile": 5.0, "prev_day_tightness_pctile": 15.0},
    }
    crowd = [{
        "symbol": f"R{i}", "archetypes": ["reversal"],
        "metrics": {"adr20_pctile": 99.0, "purple_dot_count_60d": 9,
                    "momentum_63d_pctile": 99.0, "prev_day_tightness_pctile": 60.0},
    } for i in range(discovery.CAP_PER_ARCHETYPE)]
    capped = discovery._apply_size_control(crowd + [tight_bottom])
    assert "BSOFTLIKE" in {e["symbol"] for e in capped}


def test_size_control_pullback_ranked_by_leg_force_desc():
    """K8 D4: pullback_to_rising_ma ranks by DESCENDING prior-leg force
    (leg_force_from_65d_low) -- replaces K7's ma-proximity ranker, which
    barely separated the crowd (every label pick sits <=2.1% from its MA).
    A strong-prior-leg name must survive the cap even with weak liveness,
    against a crowd of high-liveness/high-momentum names with a weaker leg."""
    strong_leg = {
        "symbol": "STRONGLEG", "archetypes": ["pullback_to_rising_ma"],
        "metrics": {"adr20_pctile": 0.0, "purple_dot_count_60d": 0,
                    "momentum_63d_pctile": 0.0, "ma_distance_pct": 2.5,
                    "leg_force_from_65d_low": 45.0},
    }
    crowd = [{
        "symbol": f"P{i}", "archetypes": ["pullback_to_rising_ma"],
        "metrics": {"adr20_pctile": 99.0, "purple_dot_count_60d": 9,
                    "momentum_63d_pctile": 99.0, "ma_distance_pct": 0.4,
                    "leg_force_from_65d_low": 10.0},
    } for i in range(discovery.CAP_PER_ARCHETYPE)]
    capped = discovery._apply_size_control(crowd + [strong_leg])
    assert "STRONGLEG" in {e["symbol"] for e in capped}


def test_size_control_caps_wide_archetype_at_cap_not_beyond():
    """K7 fix: a wide-firing archetype (100 raw hits, single-archetype, none
    multi-tagged) must be capped at exactly CAP_PER_ARCHETYPE -- the old
    "top quartile is immune from the cap" clause let this kind of archetype
    balloon to 25+ names (25% of 100), which is exactly the 200-350/day
    bucket-size blowup K7 fixed."""
    entries = []
    for i in range(100):
        entries.append({
            "symbol": f"Q{i}",
            "archetypes": ["persistent_momentum"],
            "metrics": {"adr20_pctile": float(100 - i), "purple_dot_count_60d": 0,
                        "momentum_63d_pctile": 0.0, "leg_force_from_65d_low": 0.0},
        })
    capped = discovery._apply_size_control(entries)
    kept_symbols = {e["symbol"] for e in capped}
    assert len(kept_symbols) == discovery.CAP_PER_ARCHETYPE
    # highest-velocity-score names (lowest index, per fixture ranking) survive
    assert f"Q{discovery.CAP_PER_ARCHETYPE - 1}" in kept_symbols
    assert f"Q{discovery.CAP_PER_ARCHETYPE}" not in kept_symbols


def test_size_control_small_archetype_keeps_all_members_below_cap():
    """A small archetype (raw count < CAP_PER_ARCHETYPE) keeps every member
    -- the cap only trims, it never pads a small archetype out."""
    entries = [{
        "symbol": f"S{i}", "archetypes": ["vcp_coil"],
        "metrics": {"adr20_pctile": float(10 - i), "purple_dot_count_60d": 0,
                    "momentum_63d_pctile": 0.0, "leg_force_from_65d_low": 0.0},
    } for i in range(5)]
    capped = discovery._apply_size_control(entries)
    assert {e["symbol"] for e in capped} == {f"S{i}" for i in range(5)}


# --- WAVE K8: D1/D2/D3 quality guards on _pullback_to_rising_ma ----------

def _rising_bar(date, o, h, l, c, v, prev):
    return {"date": date, "open": o, "high": h, "low": l, "close": c, "prev_close": prev, "volume": v}


def _pullback_bars(pullback):
    """45-bar rising leg (100 -> 145) + a 10-bar pullback window built from
    (price, volume) pairs. Returns (bars, leg_high)."""
    bars = []
    prev = None
    price = 100.0
    for i in range(45):
        price += 1.0
        bars.append(_rising_bar(f"d{i}", price - 1, price + 0.5, price - 1.5, price, 300_000, prev))
        prev = price
    leg_high = price
    for i, (p, v) in enumerate(pullback):
        bars.append(_rising_bar(f"pb{i}", prev, p + 0.3, p - 0.3, p, v, prev))
        prev = p
    return bars, leg_high


# A clean Arora-style pullback: undercuts the rising MA, recovers, tight/
# non-increasing ranges toward the end, up-volume dominant, no heavy-volume
# red day, >=3-of-5 recent down closes, ends close to the rising MA.
_CLEAN_PULLBACK = list(zip(
    [143.6, 144.2, 144.5, 143.0, 143.3, 143.0, 141.5, 140.0, 138.5, 137.5],
    [400_000, 400_000, 400_000, 120_000, 400_000, 120_000, 120_000, 120_000, 120_000, 120_000],
))


def test_pullback_to_rising_ma_admits_clean_arora_pullback():
    """K8 D1-D3 baseline: a genuine undercut-and-recover pullback with dried-
    up (up-dominant) volume and no heavy red day still clears the archetype
    -- the guards shrink the crowd without killing the real picks."""
    bars, leg_high = _pullback_bars(_CLEAN_PULLBACK)
    closes = [b["close"] for b in bars]
    depth = (leg_high - closes[-1]) / leg_high * 100.0
    assert discovery._pullback_to_rising_ma(bars, depth) is True


def test_pullback_to_rising_ma_rejects_heavy_red_day_D1():
    """K8 D1: injecting a single heavy-volume (>500k), >=5%-down day into an
    otherwise-clean pullback window flips admission to False -- the
    institutional-distribution-day gate (groww2/groww4)."""
    bars, leg_high = _pullback_bars(_CLEAN_PULLBACK)
    idx = len(bars) - 3
    prev_close = bars[idx - 1]["close"]
    heavy_close = prev_close * 0.93  # -7%, well past the -5% floor
    bars[idx] = _rising_bar("heavy", prev_close, prev_close + 0.3,
                             heavy_close - 0.3, heavy_close, 700_000, prev_close)
    prev = heavy_close
    for j in range(idx + 1, len(bars)):
        bars[j] = dict(bars[j])
        bars[j]["prev_close"] = prev
        prev = bars[j]["close"]
    closes = [b["close"] for b in bars]
    depth = (leg_high - closes[-1]) / leg_high * 100.0
    assert discovery._pullback_to_rising_ma(bars, depth) is False
