"""Tests for the visible industry -> sector registry."""
from pathlib import Path

import csv

from manas_os.regime import sectors

_REAL_INDUSTRY_CSV = (
    Path(__file__).resolve().parents[2]
    / "legacy"
    / "SwingEdge"
    / "data"
    / "chartsmaze"
    / "2026-07-04"
    / "analytics"
    / "industry-analytics.csv"
)


def _real_industries() -> set[str]:
    with _REAL_INDUSTRY_CSV.open("r", encoding="utf-8-sig", newline="") as fh:
        return {row["Basic Industry"].strip() for row in csv.DictReader(fh) if row["Basic Industry"].strip()}


def test_industry_to_sector_covers_real_chartsmaze_industries():
    real = _real_industries()
    assert real
    assert real <= set(sectors.INDUSTRY_TO_SECTOR)
    valid_keys = {row["key"] for row in sectors.SECTORS}
    assert set(sectors.INDUSTRY_TO_SECTOR.values()) <= valid_keys


def test_industries_for_sector_returns_sorted_industry_labels():
    industries = sectors.industries_for_sector("CAPITAL_GOODS")
    assert industries == sorted(industries)
    assert "Electrical - Power Equipment" in industries
    assert "Private Banks" not in industries

    private_bank_industries = sectors.industries_for_sector("private_bank")
    assert private_bank_industries == ["Private Banks"]
