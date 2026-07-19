"""Shared fixtures for the installed ``manas_os`` package."""
import json
from datetime import date, timedelta

# Canonical as-of date for cascade-era fixtures (a real trading Tuesday).
AS_OF = "2026-06-30"


def trading_dates(n, end=AS_OF):
    """n real weekday date strings ending at `end` (ascending)."""
    out = []
    d = date.fromisoformat(end)
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d.isoformat())
        d -= timedelta(days=1)
    return list(reversed(out))


def insert_price_ramp(conn, symbol="ACME", n=210, start=100.0, step=0.1,
                      volume=500000, delivery=62.0, low_frac=None, end=AS_OF):
    """Seed a gently-rising EQ series satisfying the Manas 2.0 cascade:
    210 bars (200SMA computable), Lead EMA stack, nearness ~1.0, tight
    structural stop. `low_frac` (e.g. 0.80) makes lows deep for
    refuse-on-risk tests. Returns the last trade_date.

    A prior swing high is injected ~40 bars from the end so the structural
    measured-move target (risk/plan.structural_target) has a real overhead
    resistance level to race toward — the geometry of a genuine base
    breakout, where the entry clears a prior peak that then frames the
    measured move. Without it the ramp's most recent highs are always the
    highest and the structural target degrades to a synthetic ATR projection.
    """
    dates = trading_dates(n, end)
    rows = []
    swing_high_bar = n - 40          # ~40 sessions from the end
    swing_high_premium = (start + n * step) * 0.18  # ~18% above the final close
    for i, d in enumerate(dates, start=1):
        close = start + i * step
        low = close * low_frac if low_frac else close - 2
        high = close + 2
        if i == swing_high_bar:
            # a clean local maximum in a +-4 window — the textbook swing high
            high = close + swing_high_premium
        dlv = delivery(i) if callable(delivery) else delivery
        rows.append((symbol, d, "EQ", close - 1, high, low, close,
                     close - step, volume, 100, dlv, "test"))
    conn.executemany(
        "INSERT OR REPLACE INTO daily_prices (symbol, trade_date, series, open, high, low, "
        "close, prev_close, volume, delivery_qty, delivery_pct, source) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        rows,
    )
    conn.commit()
    return dates[-1]


def seed_regime(conn, scan_date=AS_OF, mode="RISK_ON"):
    conn.execute(
        "INSERT OR REPLACE INTO regime_snapshots (snapshot_date, market_mode) VALUES (?, ?)",
        (scan_date, mode),
    )
    conn.commit()


def seed_confluent_symbol(conn, symbol="ACME", scan_date=AS_OF):
    """Make `symbol` survive the confluence-first, quality-gated Setups feed.

    The rewired scanner (manas_os.scanner.candidates) only considers symbols
    that are (a) in the confluence pool -- >=MIN_CONFLUENCE distinct
    non-bearish screener_hits rows, (b) pass the universe_filter quality gate
    (price>=Rs30, avg 20d turnover>=Rs5cr, not ETF/circuit-locked), and (c) not
    ASM-flagged (symbol_quality.asm_stage IS NULL). Fixtures that only insert
    daily_prices (with the old tiny ~1000-4500 volume) no longer produce any
    candidates. This helper seeds the two extra tables so a plain price
    fixture becomes scanner-visible, without touching production logic.

    `scan_date` should match the trade_date the test scans as-of (rows are
    resolved most-recent <= as_of, so an exact match is simplest for tests).
    """
    conn.execute(
        "INSERT OR REPLACE INTO screener_hits "
        "(trade_date, symbol, screener, bearish, rs_rating, basic_industry) "
        "VALUES (?, ?, 'vcp', 0, 90, 'Pharmaceuticals')",
        (scan_date, symbol),
    )
    conn.execute(
        "INSERT OR REPLACE INTO screener_hits "
        "(trade_date, symbol, screener, bearish, rs_rating, basic_industry) "
        "VALUES (?, ?, 'momentum-scanner', 0, 90, 'Pharmaceuticals')",
        (scan_date, symbol),
    )
    conn.execute(
        "INSERT OR REPLACE INTO symbol_quality "
        "(trade_date, symbol, market_cap_cr, asm_stage, eps_qoq, eps_yoy, sales_yoy, "
        "opm_yoy, is_fno, exchange) "
        "VALUES (?, ?, 5000, NULL, 10, 40, 20, 5, 1, 'NSE')",
        (scan_date, symbol),
    )
    seed_regime(conn, scan_date)  # cascade regime gate: fixtures default RISK_ON
    conn.commit()


def seed_sizer_verdict(conn, symbol=None, scan_date=AS_OF, final_qty=25, multiplier=1.0,
                       reasoning="sized to risk cap"):
    """Seed an agent_verdicts 'sizer' row so `symbol`/`scan_date` resolves as
    actionable (P0 fix: /api/desk/signal-guide and POST /api/setups/decision
    both require a real sizer verdict with a positive final_qty before a
    candidate is actionable/TAKEN-able -- see app._plan_actionability).
    Without this, a plain scan_candidates row is 'sizing-unavailable', not
    'live-paper', and TAKEN is correctly refused with 409 NOT_ACTIONABLE."""
    if symbol is None:
        symbol = "ACME"
    conn.execute(
        "INSERT OR REPLACE INTO agent_verdicts "
        "(scan_date, symbol, agent, verdict, reasoning, lens_scores_json) "
        "VALUES (?, ?, 'sizer', 'TAKE', ?, ?)",
        (scan_date, symbol, reasoning, json.dumps({"multiplier": multiplier, "final_qty": final_qty})),
    )
    conn.commit()
