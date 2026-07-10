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


def _seed_reversal_symbol(conn, symbol, n=90):
    """K4.1: strong prior uptrend (leg force >=30% off the low) then 5 red
    days on declining volume INTO a correction <=30% off the leg high --
    current-price force is weak here by construction, so this symbol must
    NOT need current force to be tagged 'reversal'."""
    import datetime
    d = datetime.date(2026, 1, 1)
    prev_close = None
    price = 100.0
    d2_last = d
    for i in range(n - 5):
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
    conn.commit()
    return d2_last.isoformat()


def test_reversal_archetype_fires_without_current_force_via_leg_force():
    conn = _mk_conn()
    scan_date = _seed_reversal_symbol(conn, "REVCO", n=90)
    bucket = discovery.build_bucket(conn, scan_date)
    entry = next((e for e in bucket if e["symbol"] == "REVCO"), None)
    assert entry is not None, "reversal pick must be admitted without current-price force"
    assert "reversal" in entry["archetypes"]
    # current force (off TODAY's close, deep in the pullback) must be weak --
    # proves the archetype fired via leg_force, not current_force
    assert entry["metrics"]["pct_up_from_65d_low"] < discovery.BUYING_FORCE_PCT_UP_65D_LOW
    assert entry["metrics"]["leg_force_from_65d_low"] >= discovery.BUYING_FORCE_PCT_UP_65D_LOW


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
    assert entry["metrics"]["days_since_listing"] < discovery.FORCE_WAIVER_MAX_DAYS


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
    low_score_but_multi_archetype = {
        "symbol": "MULTI", "archetypes": ["vcp_coil", "reversal"],
        "metrics": {"adr20_pctile": 0.0, "purple_dot_count_60d": 0, "momentum_63d_pctile": 0.0},
    }
    high_score_single_archetype = [
        {"symbol": f"H{i}", "archetypes": ["vcp_coil"],
         "metrics": {"adr20_pctile": 100.0, "purple_dot_count_60d": 5, "momentum_63d_pctile": 100.0}}
        for i in range(discovery.CAP_PER_ARCHETYPE)
    ]
    bucket = high_score_single_archetype + [low_score_but_multi_archetype]
    capped = discovery._apply_size_control(bucket)
    assert "MULTI" in {e["symbol"] for e in capped}
