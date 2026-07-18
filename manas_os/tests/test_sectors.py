"""Tests for the visible industry -> sector registry."""
import csv
from datetime import date
from pathlib import Path

from manas_os.regime import sectors

_CHARTSMAZE_ROOT = (
    Path(__file__).resolve().parents[2]
    / "legacy"
    / "SwingEdge"
    / "data"
    / "chartsmaze"
)


def _latest_industry_csv() -> Path:
    def is_date_dir(path: Path) -> bool:
        try:
            date.fromisoformat(path.name)
        except ValueError:
            return False
        return path.is_dir()

    dated = sorted(
        path for path in _CHARTSMAZE_ROOT.iterdir()
        if is_date_dir(path) and (path / "analytics" / "industry-analytics.csv").is_file()
    )
    assert dated, "no real ChartsMaze industry-analytics.csv fixture found"
    return dated[-1] / "analytics" / "industry-analytics.csv"


def _real_industries() -> set[str]:
    with _latest_industry_csv().open("r", encoding="utf-8-sig", newline="") as fh:
        return {row["Basic Industry"].strip() for row in csv.DictReader(fh) if row["Basic Industry"].strip()}


def test_industry_to_sector_covers_real_chartsmaze_industries():
    real = _real_industries()
    assert real
    assert real == set(sectors.INDUSTRY_TO_SECTOR)
    valid_keys = {row["key"] for row in sectors.SECTORS}
    assert all(sectors.INDUSTRY_TO_SECTOR[industry] in valid_keys for industry in real)
    assert set(sectors.INDUSTRY_TO_SECTOR.values()) <= valid_keys


def test_industries_for_sector_returns_sorted_industry_labels():
    industries = sectors.industries_for_sector("CAPITAL_GOODS")
    assert industries == sorted(industries)
    assert "Electrical - Power Equipment" in industries
    assert "Private Banks" not in industries

    private_bank_industries = sectors.industries_for_sector("private_bank")
    assert private_bank_industries == ["Private Banks"]
