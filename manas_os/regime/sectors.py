"""MARS — Moving Average Relative Strength, per sector vs a benchmark.

Adopted from the Pine "Moving Average Relative Strength" script (© finallynitin,
concept dman103) the user supplied. The math is rewritten here, not imported.

Definition (per the Pine source):
    sectorPct = (close − SMA50) / SMA50 × 100      # sector's distance from its MA
    indexPct  = (indexClose − indexSMA50) / indexSMA50 × 100
    MARS      = sectorPct − indexPct               # outperformance, in pp

State — a 6-way classification combining each side's above/below-MA with the
sign of MARS, exactly mirroring the Pine rules:

    Absolute Outperformance   : index below MA, sector above MA            (aop)
    Gross Outperformance       : both above MA, sector outperforms (MARS>0) (gop)
    Relative Outperformance   : both below MA, sector less bearish (MARS>0) (rop)
    Absolute Underperformance : index above MA, sector below MA            (aup)
    Gross Underperformance     : both below MA, sector more bearish... wait
                                 (both below, sector MORE bearish → MARS<0)  (gup)
    Relative Underperformance : both above MA, sector less bullish (MARS<0) (rup)

This module is pure: ``compute_mars`` takes bar lists and returns
``(mars_value, state)``. I/O (fetching history, writing rows) lives in
``mars_ingest``.
"""
from __future__ import annotations

from typing import Sequence

from manas_os.providers.base import DailyBar

# Canonical sector registry. Each entry ties together the two source vocabularies
# so ChartsMaze (which labels a sector "Auto") and MARS (which labels it
# "NIFTY AUTO") write to the SAME sector_metrics row instead of appearing as
# two separate populations. `key` is the storage key; `index` is the Fyers/
# NIFTY index name; `chartsmaze` lists the ChartsMaze CSV labels that merge in.
# Add a row here when a new sector appears in either source.
SECTORS: list[dict] = [
    {"key": "AUTO",                "index": "NIFTY AUTO",                "chartsmaze": ["Auto"]},
    {"key": "BANK",                "index": "NIFTY BANK",                "chartsmaze": ["Banks", "Banking"]},
    {"key": "FINANCIAL_SERVICES",  "index": "NIFTY FINANCIAL SERVICES",  "chartsmaze": ["Financial Services", "Financials"]},
    {"key": "FMCG",                "index": "NIFTY FMCG",                "chartsmaze": ["FMCG", "Consumer Food"]},
    {"key": "IT",                  "index": "NIFTY IT",                  "chartsmaze": ["Information Technology", "IT"]},
    {"key": "MEDIA",               "index": "NIFTY MEDIA",               "chartsmaze": ["Media Entertainment & Publication", "Media"]},
    {"key": "METAL",               "index": "NIFTY METAL",               "chartsmaze": ["Metals & Mining", "Metals"]},
    {"key": "PHARMA",              "index": "NIFTY PHARMA",              "chartsmaze": ["Healthcare", "Pharma", "Pharmaceuticals"]},
    {"key": "REALTY",              "index": "NIFTY REALTY",              "chartsmaze": ["Realty", "Real Estate"]},
    {"key": "ENERGY",              "index": "NIFTY ENERGY",              "chartsmaze": ["Power", "Energy"]},
    {"key": "INFRASTRUCTURE",      "index": "NIFTY INFRASTRUCTURE",      "chartsmaze": ["Construction", "Infrastructure"]},
    {"key": "PSU_BANK",            "index": "NIFTY PSU BANK",            "chartsmaze": ["PSU Bank"]},
    {"key": "PRIVATE_BANK",        "index": "NIFTY PRIVATE BANK",        "chartsmaze": ["Private Bank"]},
    {"key": "CONSUMER_DURABLES",   "index": "NIFTY CONSUMER DURABLES",   "chartsmaze": ["Consumer Durables"]},
    {"key": "OIL_GAS",             "index": "NIFTY OIL AND GAS",         "chartsmaze": ["Oil, Gas & Consumable fuels", "Oil & Gas", "Oil"]},
    {"key": "CAPITAL_GOODS",       "index": None,                        "chartsmaze": ["Capital Goods"]},
    {"key": "UTILITIES",           "index": None,                        "chartsmaze": ["Utilities"]},
    {"key": "SERVICES",            "index": None,                        "chartsmaze": ["Services"]},
    {"key": "CHEMICALS",           "index": None,                        "chartsmaze": ["Chemicals"]},
    {"key": "TEXTILES",            "index": None,                        "chartsmaze": ["Textiles"]},
    {"key": "CONSUMER_SERVICES",   "index": None,                        "chartsmaze": ["Consumer Services"]},
    {"key": "TELECOM",             "index": None,                        "chartsmaze": ["Telecommunication"]},
    {"key": "DIVERSIFIED",         "index": None,                        "chartsmaze": ["Diversified"]},
    {"key": "FOREST_MATERIALS",    "index": None,                        "chartsmaze": ["Forest Materials"]},
]

# Sectors with a Fyers-fetchable index (index is not None). MARS iterates these.
SECTOR_INDICES: list[str] = [s["index"] for s in SECTORS if s["index"]]

# Human-friendly display label per canonical key (for the UI). Explicit (not
# auto-title-cased) so acronyms like IT/FMCG/PSU don't mangle to "It"/"Fmcg".
SECTOR_LABELS: dict[str, str] = {
    "AUTO": "Auto",
    "BANK": "Bank",
    "FINANCIAL_SERVICES": "Financial Services",
    "FMCG": "FMCG",
    "IT": "IT",
    "MEDIA": "Media",
    "METAL": "Metal",
    "PHARMA": "Pharma & Healthcare",
    "REALTY": "Realty",
    "ENERGY": "Energy",
    "INFRASTRUCTURE": "Infrastructure",
    "PSU_BANK": "PSU Bank",
    "PRIVATE_BANK": "Private Bank",
    "CONSUMER_DURABLES": "Consumer Durables",
    "OIL_GAS": "Oil & Gas",
    "CAPITAL_GOODS": "Capital Goods",
    "UTILITIES": "Utilities",
    "SERVICES": "Services",
    "CHEMICALS": "Chemicals",
    "TEXTILES": "Textiles",
    "CONSUMER_SERVICES": "Consumer Services",
    "TELECOM": "Telecom",
    "DIVERSIFIED": "Diversified",
    "FOREST_MATERIALS": "Forest Materials",
}

# Hand-classified ChartsMaze Basic Industry -> canonical sector key map.
# Keep this visible and explicit: no runtime guessing, and every real
# industry-analytics.csv label must be covered by tests.
INDUSTRY_TO_SECTOR: dict[str, str] = {
    "Advertising": "MEDIA",
    "Aerospace & Defense": "CAPITAL_GOODS",
    "Agro chemicals": "CHEMICALS",
    "Agro Products": "FMCG",
    "Airlines": "SERVICES",
    "Amusement Parks/ Other Recreation": "CONSUMER_SERVICES",
    "Apparels": "TEXTILES",
    "Asset Management": "FINANCIAL_SERVICES",
    "Auto Ancilaries": "AUTO",
    "Auto Dealer": "AUTO",
    "Auto Manufacturers": "AUTO",
    "Biotechnology": "PHARMA",
    "Breweries & Distilleries": "FMCG",
    "Cables - Electricals": "CAPITAL_GOODS",
    "Cement": "INFRASTRUCTURE",
    "Chemicals Specialty": "CHEMICALS",
    "Chemicals-Basic": "CHEMICALS",
    "Chemicals-Plastics": "CHEMICALS",
    "Civil Construction": "INFRASTRUCTURE",
    "Coal Products": "OIL_GAS",
    "Computer Hardware": "IT",
    "Computer-Networking": "IT",
    "Construction Products Miscallaneous": "INFRASTRUCTURE",
    "Construction Residential & Commercial": "REALTY",
    "Consulting Services": "SERVICES",
    "Credit Rating Agencies": "FINANCIAL_SERVICES",
    "Dairy Products": "FMCG",
    "Diversified Commercial Services": "SERVICES",
    "Diversified Operations": "DIVERSIFIED",
    "Diversified Retail": "CONSUMER_SERVICES",
    "E- Commerce": "CONSUMER_SERVICES",
    "Edible Oils & Solvent Extraction": "FMCG",
    "Education Services": "CONSUMER_SERVICES",
    "Electrical - Power Equipment": "CAPITAL_GOODS",
    "Electrical Miscallaneous": "CAPITAL_GOODS",
    "Electronic Media": "MEDIA",
    "EMS": "CAPITAL_GOODS",
    "Energy-Alternative": "ENERGY",
    "Fertilizers": "CHEMICALS",
    "Film Production & Distribution": "MEDIA",
    "Finance & Investment": "FINANCIAL_SERVICES",
    "Financial Services-Specialty": "FINANCIAL_SERVICES",
    "Food Products": "FMCG",
    "Footwear": "CONSUMER_DURABLES",
    "Gas Distribution": "OIL_GAS",
    "General Insurance": "FINANCIAL_SERVICES",
    "Glass": "CONSUMER_DURABLES",
    "Healthcare Research Analytics & Technology": "PHARMA",
    "Holding Company": "FINANCIAL_SERVICES",
    "Home Furnishing": "CONSUMER_DURABLES",
    "Hospitals": "PHARMA",
    "Hotels": "CONSUMER_SERVICES",
    "Household Appliances": "CONSUMER_DURABLES",
    "Housing Finance": "FINANCIAL_SERVICES",
    "Industrial Products & Manufacturing": "CAPITAL_GOODS",
    "Investment Banking & Broking": "FINANCIAL_SERVICES",
    "Iron & Steel": "METAL",
    "Jewellery": "CONSUMER_DURABLES",
    "Leisure Products": "CONSUMER_DURABLES",
    "Life Insurance": "FINANCIAL_SERVICES",
    "Logistics": "SERVICES",
    "Lubricants": "OIL_GAS",
    "Media & Entertainment": "MEDIA",
    "Medical Diagnostics": "PHARMA",
    "Medical Equipment & Supplies": "PHARMA",
    "Medical-Diversified": "PHARMA",
    "Metal Fabrication": "METAL",
    "Mining/Minerals": "METAL",
    "NBFC": "FINANCIAL_SERVICES",
    "Oil & Gas Drilling": "OIL_GAS",
    "Oil & Gas-Field Services": "OIL_GAS",
    "Oil & Gas-Integrated": "OIL_GAS",
    "Oil & Gas-Refining & Marketing": "OIL_GAS",
    "Oil Exploration & Production": "OIL_GAS",
    "Other Beverages": "FMCG",
    "Other Telecom Services": "TELECOM",
    "Packaging": "FOREST_MATERIALS",
    "Paints": "CONSUMER_DURABLES",
    "Paper & Paper Products": "FOREST_MATERIALS",
    "Personal Care": "FMCG",
    "Petrochemicals": "OIL_GAS",
    "Pharmaceuticals": "PHARMA",
    "Power Generation & Distribution": "ENERGY",
    "Print Media": "MEDIA",
    "Private Banks": "PRIVATE_BANK",
    "PSU Banks": "PSU_BANK",
    "Pumps": "CAPITAL_GOODS",
    "Railways": "CAPITAL_GOODS",
    "Real Estate": "REALTY",
    "Restaurants": "CONSUMER_SERVICES",
    "Retail-Department Stores": "CONSUMER_SERVICES",
    "Ship building & Allied services": "CAPITAL_GOODS",
    "Software Products": "IT",
    "Software Services": "IT",
    "Speciality Retail": "CONSUMER_SERVICES",
    "Stationary": "CONSUMER_DURABLES",
    "Sugar": "FMCG",
    "Tea & Coffee": "FMCG",
    "Telecom - Cellular & Fixed line services": "TELECOM",
    "Telecom - Equipment & Accessories": "TELECOM",
    "Telecom - Infrastructure": "TELECOM",
    "Textiles": "TEXTILES",
    "Tobacco": "FMCG",
    "Tour & Travel services": "CONSUMER_SERVICES",
    "Trading - Metals": "METAL",
    "Transformers": "CAPITAL_GOODS",
    "TV Broadcasting & Software": "MEDIA",
    "Tyres & Rubber Products": "AUTO",
    "Waste Management": "SERVICES",
    "Water Supply & Management": "UTILITIES",
    "Web Services": "IT",
    "Wood Products": "FOREST_MATERIALS",
}


def industries_for_sector(sector_key: str) -> list[str]:
    """Industry labels mapped to a canonical sector key, sorted for display."""
    key = canonical_sector_key(sector_key, "chartsmaze")
    return sorted(
        industry for industry, mapped_key in INDUSTRY_TO_SECTOR.items()
        if mapped_key == key
    )


def display_label(key: str) -> str:
    """Pretty label for a canonical key, e.g. CAPITAL_GOODS → 'Capital Goods'."""
    if not key:
        return key
    return SECTOR_LABELS.get(key) or key.replace("_", " ").title()

# Lookup tables built once from SECTORS.
_BY_INDEX: dict[str, str] = {s["index"]: s["key"] for s in SECTORS if s["index"]}
_BY_CHARTSMAZE: dict[str, str] = {}
for _s in SECTORS:
    for _label in _s["chartsmaze"]:
        _BY_CHARTSMAZE[_label.strip().lower()] = _s["key"]


def canonical_sector_key(label: str, source: str) -> str:
    """Normalize any sector label to its canonical storage key.

    `source` ∈ {'chartsmaze', 'index'}. Returns the canonical key, or the
    uppercased input when no mapping exists (so unmapped sectors still surface
    rather than vanishing — they show as their own row, which signals the map
    needs a new entry).
    """
    if not label:
        return label
    norm = label.strip().lower()
    if source == "index":
        # NIFTY index names map directly.
        return _BY_INDEX.get(label.strip()) or _BY_INDEX.get(label.strip().upper()) or label.strip().upper()
    # ChartsMaze label — case-insensitive match.
    return _BY_CHARTSMAZE.get(norm) or label.strip().upper()


# Benchmark the Pine script defaults to. Override via config `regime.mars_benchmark`.
BENCHMARK = "NIFTYMIDSML400"

MA_LENGTH = 50  # SMA window; matches the Pine default malength=50.

# The 6 states + their plain-English read (the verdict-beside-number layer).
STATE_LABELS: dict[str, str] = {
    "ABSOLUTE_OUT":   "index bearish but sector bullish",
    "GROSS_OUT":      "both bullish, sector outperforming",
    "RELATIVE_OUT":   "both bearish, sector less bearish",
    "ABSOLUTE_UNDER": "index bullish but sector bearish",
    "GROSS_UNDER":    "both bearish, sector more bearish",
    "RELATIVE_UNDER": "both bullish, sector less bullish",
}


def sma(values: Sequence[float], length: int) -> float | None:
    """Simple moving average of the last `length` values. None if too short."""
    if len(values) < length:
        return None
    return sum(values[-length:]) / length


def _pct_above_ma(close: float, ma: float | None) -> float | None:
    """(close − ma) / ma × 100. None if ma is missing/zero."""
    if ma is None or ma == 0:
        return None
    return (close - ma) / ma * 100.0


def classify_state(
    mars_value: float,
    sector_above_ma: bool,
    index_above_ma: bool,
) -> str:
    """One of the 6 MARS states. Implements the Pine 6-rule table verbatim."""
    positive = mars_value > 0
    # Pine rule order (from the source): rop / gop / aop / rup / gup / aup.
    if positive and not sector_above_ma and not index_above_ma:
        return "RELATIVE_OUT"      # rop — both bearish, sector less bearish
    if positive and sector_above_ma and index_above_ma:
        return "GROSS_OUT"         # gop — both bullish, sector more bullish
    if positive and not index_above_ma and sector_above_ma:
        return "ABSOLUTE_OUT"      # aop — index bearish, sector bullish
    if not positive and sector_above_ma and index_above_ma:
        return "RELATIVE_UNDER"    # rup — both bullish, sector less bullish
    if not positive and not sector_above_ma and not index_above_ma:
        return "GROSS_UNDER"       # gup — both bearish, sector more bearish
    if not positive and index_above_ma and not sector_above_ma:
        return "ABSOLUTE_UNDER"    # aup — index bullish, sector bearish
    # mars_value == 0 lands here; call it neutral relative under.
    return "RELATIVE_UNDER"


def compute_mars(
    sector_bars: Sequence[DailyBar],
    index_bars: Sequence[DailyBar],
    ma_length: int = MA_LENGTH,
) -> tuple[float | None, str | None]:
    """MARS for the latest bar. Returns (mars_value, state); (None, None) if
    either series is too short for an SMA50.

    Pure: no I/O. Both bar lists are oldest-first; only the trailing close and
    the SMA of the closes are used. The two series need not be the same length,
    but each must have ≥ ``ma_length`` bars.
    """
    if len(sector_bars) < ma_length or len(index_bars) < ma_length:
        return None, None

    sector_close = sector_bars[-1].close
    index_close = index_bars[-1].close
    sector_ma = sma([b.close for b in sector_bars], ma_length)
    index_ma = sma([b.close for b in index_bars], ma_length)

    sector_pct = _pct_above_ma(sector_close, sector_ma)
    index_pct = _pct_above_ma(index_close, index_ma)
    if sector_pct is None or index_pct is None:
        return None, None

    mars_value = sector_pct - index_pct
    state = classify_state(
        mars_value,
        sector_above_ma=sector_close > sector_ma,
        index_above_ma=index_close > index_ma,
    )
    return round(mars_value, 4), state
