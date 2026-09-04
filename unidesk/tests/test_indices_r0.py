"""Index-close parser (nse-archives ind_close_all) and R0 midcap gate."""
from datetime import date, timedelta

import pytest

from unidesk.momentum.data.indices import above_sma, parse_ind_close_all_rows, series_for
from unidesk.momentum.regime import Regime, RegimeClassifier


def test_parse_keeps_r0_set_and_sectoral():
    """Rotation R-0.2: sectoral indices (Nifty Auto etc.) are now kept
    alongside the R0 broad set — sector RS is measured from the exchange's
    own index (HANDOFF_2026-09-04_MARKET_ROTATION §3.1)."""
    rows = [
        {"Index Name": "Nifty 50", "Index Date": "14-08-2026",
         "Open Index Value": 25000, "High Index Value": 25100,
         "Low Index Value": 24900, "Closing Index Value": 25050},
        {"Index Name": "Nifty Midcap 150", "Index Date": "14-08-2026",
         "Closing Index Value": "19500.5"},
        {"Index Name": "India VIX", "Index Date": "14-08-2026",
         "Closing Index Value": "12.4"},
        {"Index Name": "Nifty Auto", "Index Date": "14-08-2026",
         "Closing Index Value": "99"},
        {"Index Name": "Nifty IT", "Index Date": "14-08-2026",
         "Closing Index Value": "35000"},
        {"Index Name": "Nifty 50", "Index Date": "14-08-2026",
         "Closing Index Value": "-"},
    ]
    out = parse_ind_close_all_rows(rows, source_file="ind_close_all_14082026.csv")
    ids = {r["index_id"] for r in out}
    assert "NIFTY_AUTO" in ids and "NIFTY_IT" in ids
    # the malformed "-" close for the duplicate Nifty 50 row is dropped (R12)
    assert ids == {"NIFTY_50", "NIFTY_MIDCAP_150", "INDIA_VIX", "NIFTY_AUTO", "NIFTY_IT"}
    by = {r["index_id"]: r for r in out}
    assert by["NIFTY_50"]["close"] == 25050
    assert by["NIFTY_50"]["source_tier"] == "NSE_ARCHIVES_IND_CLOSE_ALL"
    assert by["INDIA_VIX"]["close"] == 12.4
    assert by["NIFTY_AUTO"]["close"] == 99.0
    assert by["NIFTY_IT"]["close"] == 35000.0


def test_above_sma_warmup_then_true():
    points = []
    d0 = date(2026, 1, 2)
    for i in range(55):
        points.append((d0 + timedelta(days=i), 100.0 + i))  # rising
    assert above_sma(points, d0 + timedelta(days=20), span=50) is None
    assert above_sma(points, d0 + timedelta(days=54), span=50) is True
    falling = [(d0 + timedelta(days=i), 200.0 - i) for i in range(55)]
    assert above_sma(falling, d0 + timedelta(days=54), span=50) is False


def test_r0_midcap_disagreement_forces_chop():
    clf = RegimeClassifier()
    # breadth BULL but midcap below SMA50 → CHOP
    row = clf.update(date(2026, 6, 1), 0.70, midcap_above_sma50=False)
    assert row.regime is Regime.CHOP
    assert row.source == "breadth_and_midcap150_sma50"
    # breadth BULL and midcap above → BULL
    clf2 = RegimeClassifier()
    row2 = clf2.update(date(2026, 6, 1), 0.70, midcap_above_sma50=True)
    assert row2.regime is Regime.BULL
    # missing midcap stays breadth_only
    clf3 = RegimeClassifier()
    row3 = clf3.update(date(2026, 6, 1), 0.70)
    assert row3.regime is Regime.BULL
    assert row3.source == "breadth_only"


def test_harvested_parquet_has_r0_set():
    from pathlib import Path
    from unidesk.momentum.data.indices import load_index_rows, series_for, above_sma
    path = Path(__file__).resolve().parents[2] / "data" / "market" / "reference" / "indices.parquet"
    if not path.exists():
        pytest.skip("index harvest not present")
    rows = load_index_rows(path)
    ids = {r["index_id"] for r in rows}
    assert {"NIFTY_50", "NIFTY_MIDCAP_150", "NIFTY_500", "INDIA_VIX", "NIFTY_SMALLCAP_250"} <= ids
    mid = series_for(rows, "NIFTY_MIDCAP_150")
    assert len(mid) >= 50
    assert above_sma(mid, mid[-1][0], 50) is not None


def test_series_for_sorts():
    rows = parse_ind_close_all_rows([
        {"Index Name": "Nifty 50", "Index Date": "15-08-2026", "Closing Index Value": 2},
        {"Index Name": "Nifty 50", "Index Date": "14-08-2026", "Closing Index Value": 1},
    ])
    pts = series_for(rows, "NIFTY_50")
    assert [d.isoformat() for d, _ in pts] == ["2026-08-14", "2026-08-15"]


def test_canonicalise_merges_tier_duplicates_and_normalises_names():
    """Rotation R-0.1: legacy MANAS spellings and NSE_ARCHIVES spellings
    describe the same indices — after canonicalisation, one row per
    (session, index_id), and the name is the canonical display spelling."""
    from unidesk.momentum.data.indices import canonicalise_index_rows

    rows = [
        {"session": "2026-08-20", "index_id": "NIFTY_50", "index_name": "NIFTY 50",
         "close": 100.0, "source_tier": "MANAS_SECTOR_INDEX_PRICES"},
        {"session": "2026-08-20", "index_id": "NIFTY_50", "index_name": "Nifty 50",
         "close": 100.0, "source_tier": "NSE_ARCHIVES_IND_CLOSE_ALL"},
        {"session": "2026-08-21", "index_id": "NIFTY_50", "index_name": "Nifty 50",
         "close": 101.0, "source_tier": "NSE_ARCHIVES_IND_CLOSE_ALL"},
    ]
    out, stats = canonicalise_index_rows(rows)
    assert stats["tier_dupes_dropped"] == 1
    assert len(out) == 2
    assert all(r["index_name"] == "Nifty 50" for r in out)
    seen = {(r["session"], r["index_id"]) for r in out}
    assert len(seen) == 2


def test_canonicalise_never_leaves_duplicates():
    """The invariant the rotation screen depends on: a session never carries
    two rows for one canonical index — even for unknown names."""
    from unidesk.momentum.data.indices import canonicalise_index_rows

    rows = [
        {"session": "2026-08-20", "index_id": "X", "index_name": "NIFTY 50", "close": 1.0},
        {"session": "2026-08-20", "index_id": "X", "index_name": "NIFTY 50", "close": 1.0},
    ]
    out, _ = canonicalise_index_rows(rows)
    assert len({(r["session"], r["index_id"]) for r in out}) == len(out)
