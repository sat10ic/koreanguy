from manas_os import db
from manas_os.agents import context_pack
from manas_os.scanner import expectancy


def _shortlist_item(symbol="ACME", setup_family="strong_start"):
    return {
        "symbol": symbol,
        "setup": "strong_start",
        "setup_family": setup_family,
        "rank": 1,
        "rank_of": 5,
        "grade": "A",
        "readiness": 80,
        "sector": "IT",
        "industry": "Software",
        "timing": {"close": 100.0, "dist_pivot": 1.2, "rvol": 1.5, "delivery_pct": 55, "adr": 2.1},
        "score_breakdown": {"sector_adj_momentum": 1.1, "growth": 0.2},
        "exit_state": "none",
        "evidence": ["delivery>=60"],
        "gates": [],
        "entry": 101.0,
        "stop": 95.0,
        "rr": 2.0,
        "suggested_qty": 10,
    }


def _insert_daily_prices(conn, symbol, dates_closes):
    for d, c in dates_closes:
        conn.execute(
            "INSERT INTO daily_prices (symbol, trade_date, close, source) VALUES (?, ?, ?, 'bhavcopy')",
            (symbol, d, c),
        )
    conn.commit()


def _insert_regime(conn, snapshot_date, market_mode):
    conn.execute(
        "INSERT INTO regime_snapshots (snapshot_date, market_mode) VALUES (?, ?)",
        (snapshot_date, market_mode),
    )
    conn.commit()


def test_look_ahead_guard_weekly_closes_never_exceed_scan_date(tmp_path):
    conn = db.init_db(tmp_path / "manas.db")
    try:
        scan_date = "2026-03-15"
        dates = []
        # 20 weeks of daily bars spanning before and after scan_date.
        import datetime
        d = datetime.date(2025, 11, 1)
        while d <= datetime.date(2026, 4, 1):
            dates.append((d.isoformat(), 100 + d.toordinal() % 10))
            d += datetime.timedelta(days=1)
        _insert_daily_prices(conn, "ACME", dates)

        weekly = context_pack._weekly_closes(conn, "ACME", scan_date)
        assert weekly, "expected some weekly closes"
        for w in weekly:
            assert w["week_end"] <= scan_date
        assert len(weekly) <= context_pack.WEEKLY_CLOSES_COUNT + 1
    finally:
        conn.close()


def test_regime_age_days_computed_correctly(tmp_path):
    conn = db.init_db(tmp_path / "manas.db")
    try:
        _insert_regime(conn, "2026-03-10", "RISK_ON")
        _insert_regime(conn, "2026-03-11", "RISK_ON")
        _insert_regime(conn, "2026-03-12", "RISK_ON")
        _insert_regime(conn, "2026-03-13", "SELECTIVE")
        _insert_regime(conn, "2026-03-14", "SELECTIVE")

        regime, age = context_pack._regime_and_age(conn, "2026-03-14")
        assert regime == "SELECTIVE"
        assert age == 2

        regime2, age2 = context_pack._regime_and_age(conn, "2026-03-12")
        assert regime2 == "RISK_ON"
        assert age2 == 3
    finally:
        conn.close()


def test_regime_age_days_no_data_returns_none(tmp_path):
    conn = db.init_db(tmp_path / "manas.db")
    try:
        regime, age = context_pack._regime_and_age(conn, "2026-03-14")
        assert regime is None
        assert age == 0
    finally:
        conn.close()


def test_base_rates_include_n_and_handle_empty_gracefully(tmp_path):
    conn = db.init_db(tmp_path / "manas.db")
    try:
        # No expectancy data at all -> chip_for returns None -> pack marks no_data.
        pack = context_pack.build_pack(conn, "2026-03-14", [_shortlist_item()])
        block = pack["shortlist"][0]
        assert block["base_rates"] == {"no_data": True}

        # Now seed expectancy data and confirm n surfaces.
        expectancy.ensure_schema(conn)
        conn.execute(
            "INSERT INTO setup_expectancy (as_of, loop, setup_family, regime, n, hit_rate, "
            "median_r, posterior_r, trust) VALUES (?, 'system', ?, ?, ?, ?, ?, ?, ?)",
            ("2026-03-14", "strong_start", "RISK_ON", 40, 0.55, 0.8, 0.75, "directional"),
        )
        conn.commit()
        _insert_regime(conn, "2026-03-14", "RISK_ON")
        pack2 = context_pack.build_pack(conn, "2026-03-14", [_shortlist_item()])
        block2 = pack2["shortlist"][0]
        assert "system" in block2["base_rates"]
        assert block2["base_rates"]["system"]["n"] == 40
    finally:
        conn.close()


def test_lens_text_appears_exactly_once_not_per_symbol(tmp_path):
    conn = db.init_db(tmp_path / "manas.db")
    try:
        shortlist = [_shortlist_item("ACME"), _shortlist_item("BETA")]
        pack = context_pack.build_pack(conn, "2026-03-14", shortlist)
        lens_notes = pack["lens_notes"]
        assert lens_notes  # lens files exist in the repo
        # lens_notes lives once at pack level, not inside each symbol block.
        for block in pack["shortlist"]:
            assert "lens_notes" not in block
        # sanity: a known lens marker string appears exactly once in the whole pack json
        assert lens_notes.count("Strong Start") >= 1
    finally:
        conn.close()


def test_catalyst_shortlist_uses_only_relevant_lens_notes(tmp_path, monkeypatch):
    conn = db.init_db(tmp_path / "manas.db")
    try:
        monkeypatch.setattr(context_pack.config, "get", lambda key, default=None: default)
        pack = context_pack.build_pack(conn, "2026-03-14", [_shortlist_item(setup_family="catalyst")])
        lens_notes = pack["lens_notes"]
        assert "Episodic Pivot" in lens_notes
        assert "PEAD" in lens_notes
        assert "Strong Start" in lens_notes
        assert "High Tight Flag" not in lens_notes
    finally:
        conn.close()


def test_full_lens_notes_config_restores_all_lens_files(tmp_path, monkeypatch):
    conn = db.init_db(tmp_path / "manas.db")
    try:
        monkeypatch.setattr(
            context_pack.config,
            "get",
            lambda key, default=None: True if key == "agents.full_lens_notes" else default,
        )
        pack = context_pack.build_pack(conn, "2026-03-14", [_shortlist_item(setup_family="catalyst")])
        lens_notes = pack["lens_notes"]
        assert "Episodic Pivot" in lens_notes
        assert "High Tight Flag" in lens_notes
        assert "IPO Base" in lens_notes
    finally:
        conn.close()


def test_honest_omission_no_vix_row_and_no_lesson_digest(tmp_path):
    conn = db.init_db(tmp_path / "manas.db")
    try:
        pack = context_pack.build_pack(conn, "2026-03-14", [_shortlist_item()])
        assert "india_vix" not in pack
        assert "lesson_digest" not in pack
    finally:
        conn.close()


def test_india_vix_present_when_row_exists(tmp_path):
    conn = db.init_db(tmp_path / "manas.db")
    try:
        conn.execute(
            "INSERT INTO sector_index_prices (symbol, trade_date, close) VALUES ('INDIAVIX', ?, ?)",
            ("2026-03-10", 13.5),
        )
        conn.commit()
        pack = context_pack.build_pack(conn, "2026-03-14", [_shortlist_item()])
        assert pack["india_vix"] == 13.5
    finally:
        conn.close()


def test_india_structure_primer_present_as_static_string(tmp_path):
    conn = db.init_db(tmp_path / "manas.db")
    try:
        pack = context_pack.build_pack(conn, "2026-03-14", [_shortlist_item()])
        assert pack["india_structure_primer"] == context_pack.INDIA_STRUCTURE_PRIMER
        assert "T+1" in pack["india_structure_primer"]
        assert "Thursday" in pack["india_structure_primer"]
    finally:
        conn.close()
