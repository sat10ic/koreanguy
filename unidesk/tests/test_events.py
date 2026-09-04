"""Chartsmaze event-table parsers (IPO, circuit, CA taxonomy, vendor breadth)."""
from datetime import date

import pytest

from unidesk.momentum.data.events import (
    circuit_band_as_of, classify_announcement, parse_circuit_revisions,
    parse_corporate_announcements, parse_ipo_listings, parse_vendor_breadth,
)

BOM = "\ufeff"


def test_classify_announcement_is_conservative():
    assert classify_announcement("Dividend", "Final Dividend of Rs. 9.50") == "DIVIDEND"
    assert classify_announcement("Updates", "Letter of offer for the buyback") == "BUYBACK"
    assert classify_announcement("Record Date", "stock split of equity shares") == "SPLIT"
    assert classify_announcement("Record Date", "bonus issue of shares") == "BONUS"
    assert classify_announcement("General Updates", "rights issue of equity") == "RIGHTS"
    assert classify_announcement("Trading Window", "insider trading window") == "OTHER"
    # company-name-like tokens must not classify from Subject alone
    assert classify_announcement("Trading Window", "") == "OTHER"


def test_ipo_listings_and_circuit_revisions(tmp_path):
    ipo = tmp_path / "ipo.csv"
    ipo.write_text(
        BOM + "Stock Name,Listing Date,Basic Industry\n"
        "AGL,03/07/2026,Logistics\n"
        "BAD ROW,not-a-date,X\n",
        encoding="utf-8",
    )
    rows, stats = parse_ipo_listings(ipo)
    assert stats["kept"] == 1 and stats["skipped"] == 1
    assert rows[0]["symbol"] == "AGL"
    assert rows[0]["listing_date"] == "2026-07-03"
    assert rows[0]["source_tier"] == "SECONDARY_REPAIR"

    circ = tmp_path / "circ.csv"
    circ.write_text(
        BOM + "Effective Date,Stock Name,From,To\n"
        "01/06/2026,TRENT,20,10\n"
        "15/06/2026,TRENT,10,5\n"
        "01/06/2026,M&M,5,20\n",
        encoding="utf-8",
    )
    revs, cstats = parse_circuit_revisions(circ)
    assert cstats["kept"] == 3
    assert circuit_band_as_of(revs, "TRENT", date(2026, 6, 1)) == 10.0
    assert circuit_band_as_of(revs, "TRENT", date(2026, 6, 15)) == 5.0
    assert circuit_band_as_of(revs, "TRENT", date(2026, 5, 31)) is None
    assert circuit_band_as_of(revs, "M&M", date(2026, 6, 20)) == 20.0


def test_corporate_announcements_never_auto_adjustable(tmp_path):
    p = tmp_path / "ca.csv"
    p.write_text(
        BOM + "Stock Name,Date,Subject,Details,Attachments\n"
        "GMDCLTD,14/05/2026,Dividend,recommended Final Dividend of Rs. 9.50,\n"
        "KRISHANA,24/06/2026,Record Date,stock split of equity shares,\n"
        ",01/01/2026,Updates,missing symbol,\n",
        encoding="utf-8",
    )
    rows, stats = parse_corporate_announcements(p)
    assert stats["kept"] == 2 and stats["skipped"] == 1
    by = {r["ca_type"]: r for r in rows}
    assert by["DIVIDEND"]["auto_adjustable"] is False
    assert by["SPLIT"]["symbol"] == "KRISHANA"
    assert stats["by_type"]["DIVIDEND"] == 1


def test_real_chartsmaze_dumps_smoke():
    from pathlib import Path
    root = Path(__file__).resolve().parents[2] / "SwingEdge" / "data" / "chartsmaze"
    ipo = root / "2026-07-04" / "scanners" / "past-IPO-listings.csv"
    circ = root / "circuit-limit-revision-history-master.csv"
    ca = root / "corporate-announcements-master.csv"
    breadth = root / "2026-07-04" / "analytics" / "market-breadth.csv"
    if not ipo.exists():
        pytest.skip("chartsmaze dump not present")
    ipo_rows, ipo_stats = parse_ipo_listings(ipo)
    assert ipo_stats["kept"] >= 50
    circ_rows, circ_stats = parse_circuit_revisions(circ)
    assert circ_stats["kept"] >= 20
    assert circuit_band_as_of(circ_rows, circ_rows[0]["symbol"],
                              date.fromisoformat(circ_rows[0]["effective_date"])) is not None
    ca_rows, ca_stats = parse_corporate_announcements(ca)
    assert ca_stats["kept"] >= 1000
    assert ca_stats["by_type"].get("DIVIDEND", 0) >= 1
    assert all(r["auto_adjustable"] is False for r in ca_rows)
    b_rows, b_stats = parse_vendor_breadth(breadth)
    assert b_stats["kept"] >= 50
    assert 0.0 < b_rows[-1]["pct_above_50"] < 1.0


def test_vendor_breadth_wide_csv(tmp_path):
    p = tmp_path / "breadth.csv"
    p.write_text(
        BOM + "Type of Info,2026-06-30,2026-07-01,2026-07-03\n"
        "Up by 4% Today,10,11,12\n"
        "Above 50MA %,56.0,60.5,64.0\n"
        "Above 200MA %,40.0,41.0,42.0\n",
        encoding="utf-8",
    )
    rows, stats = parse_vendor_breadth(p)
    assert stats["kept"] == 3
    by = {r["session"]: r for r in rows}
    assert by["2026-06-30"]["pct_above_50"] == pytest.approx(0.56)
    assert by["2026-07-03"]["pct_above_200"] == pytest.approx(0.42)
