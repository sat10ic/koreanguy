"""Reference-data ingestion tests (synthetic fixtures mirroring the real
dump headers, including the UTF-8 BOM the real files carry)."""
from datetime import date

import pytest

from unidesk.contracts.base import ContractError
from unidesk.momentum.data.reference_ingest import (
    SOURCE_TIER_CHARTSMAZE, SOURCE_TIER_NEXUS,
    fill_industry_mapping_from_nexus, load_industry_mapping, load_industry_sources,
    load_sector_rollup, overlay_industry_rows, parse_industry_mapping,
    parse_industry_sector, parse_nexus_industry_map, parse_results_calendar,
    persist_reference, sector_of,
)

BOM = "﻿"

STOCKS = BOM + "ticker,industry,rs\nM&M,Automobile,88\nTRENT,Retail,94\nbad symbol,Retail,10\n"
INDUSTRIES = BOM + "name,sector,pct\nAutomobile,Auto & Ancillary,50.0%\nRetail,Retailing,60.0%\n"
RESULTS = (
    "Stock Name,Quarterly Results Date,QoQ % EPS Latest,YoY % EPS Latest,"
    "QoQ % Sales Latest,YoY % Sales Latest,QoQ % OPM Latest,YoY % OPM Latest\n"
    "M&M,13/07/2026,11.3,94.3,4.6,24.9,4.2,62.7\n"
    "TRENT,15/07/2026,3,,,1.8,\n"
    "BADROW,32/13/2026,1,1,1,1,1,1\n"
)


def write(tmp_path, name, content):
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return p


def test_industry_mapping_strips_bom_and_normalizes(tmp_path):
    rows, stats = parse_industry_mapping(write(tmp_path, "stocks.csv", STOCKS))
    assert stats["skipped"] == 1                      # 'bad symbol' has a space
    by_sym = {r["symbol"]: r["industry"] for r in rows}
    assert by_sym["M&M"] == "Automobile"
    assert by_sym["TRENT"] == "Retail"


def test_industry_sector_rollup(tmp_path):
    mapping = parse_industry_sector(write(tmp_path, "ind.csv", INDUSTRIES))
    assert mapping["Automobile"] == "Auto & Ancillary"


def test_sector_of_composes_and_falls_back_to_industry(tmp_path):
    rows, _ = parse_industry_mapping(write(tmp_path, "s.csv", STOCKS))
    rollup = parse_industry_sector(write(tmp_path, "i.csv", INDUSTRIES))
    sector = sector_of(rows, rollup)
    assert sector["M&M"] == "Auto & Ancillary"        # via rollup
    assert sector["TRENT"] == "Retailing"             # rollup wins over raw industry


def test_results_calendar_parses_dates_and_blank_growth(tmp_path):
    rows, stats = parse_results_calendar(write(tmp_path, "rc.csv", RESULTS))
    assert stats["skipped"] == 1                      # impossible date
    mm = next(r for r in rows if r["symbol"] == "M&M")
    assert mm["results_date"] == "2026-07-13"
    assert mm["eps_yoy_pct"] == 94.3
    tr = next(r for r in rows if r["symbol"] == "TRENT")
    assert tr["eps_yoy_pct"] is None                  # blank stays None (R12)


def test_persist_and_reload_round_trip(tmp_path):
    rows, _ = parse_industry_mapping(write(tmp_path, "s.csv", STOCKS))
    rollup = parse_industry_sector(write(tmp_path, "i.csv", INDUSTRIES))
    results, _ = parse_results_calendar(write(tmp_path, "rc.csv", RESULTS))
    ref = persist_reference(tmp_path, industry_rows=rows,
                            industry_sector=rollup, results_rows=results)
    assert (ref / "industry_mapping.parquet").exists()
    assert load_industry_mapping(tmp_path)["M&M"] == "Automobile"
    assert load_sector_rollup(tmp_path)["Retail"] == "Retailing"
    assert load_industry_sources(tmp_path)["M&M"] == SOURCE_TIER_CHARTSMAZE


NEXUS = (
    "symbol,industry,in_our_universe\n"
    "M&M,Diversified Companies,1\n"
    "NEWCO,Pharmaceuticals Companies,0\n"
    "AAYUSHBULL,\"Gems, Jewellery And Watches Companies\",0\n"
    "BAD SYM,Textiles Companies,1\n"
    ",Empty Symbol Companies,1\n"
)


def test_parse_nexus_skips_bad_symbols_and_keeps_quoted_industry(tmp_path):
    rows, stats = parse_nexus_industry_map(write(tmp_path, "nexus.csv", NEXUS))
    assert stats["skipped"] == 2
    by = {r["symbol"]: r for r in rows}
    assert by["M&M"]["industry"] == "Diversified Companies"
    assert by["NEWCO"]["industry"] == "Pharmaceuticals Companies"
    assert by["AAYUSHBULL"]["industry"] == "Gems, Jewellery And Watches Companies"
    assert by["NEWCO"]["source_tier"] == SOURCE_TIER_NEXUS
    assert "BAD SYM" not in by


def test_overlay_chartsmaze_wins_nexus_fills_gaps():
    primary = [
        {"symbol": "M&M", "industry": "Automobile", "source_tier": SOURCE_TIER_CHARTSMAZE},
        {"symbol": "TRENT", "industry": "Retail", "source_tier": SOURCE_TIER_CHARTSMAZE},
    ]
    fill = [
        {"symbol": "M&M", "industry": "Diversified Companies", "source_tier": SOURCE_TIER_NEXUS},
        {"symbol": "NEWCO", "industry": "Pharmaceuticals Companies", "source_tier": SOURCE_TIER_NEXUS},
    ]
    merged, stats = overlay_industry_rows(primary, fill)
    by = {r["symbol"]: r for r in merged}
    assert by["M&M"]["industry"] == "Automobile"
    assert by["M&M"]["source_tier"] == SOURCE_TIER_CHARTSMAZE
    assert by["NEWCO"]["industry"] == "Pharmaceuticals Companies"
    assert by["NEWCO"]["source_tier"] == SOURCE_TIER_NEXUS
    assert stats["filled"] == 1
    assert stats["blocked_overlap"] == 1
    assert stats["total"] == 3


def test_nexus_fill_refuses_to_invent_primary_table(tmp_path):
    with pytest.raises(ContractError, match="missing"):
        fill_industry_mapping_from_nexus(tmp_path, tmp_path / "nope.csv")


def test_nexus_fill_rewrites_parquet_without_clobber(tmp_path):
    rows, _ = parse_industry_mapping(write(tmp_path, "s.csv", STOCKS))
    persist_reference(
        tmp_path, industry_rows=rows, industry_sector={}, results_rows=[],
    )
    stats = fill_industry_mapping_from_nexus(
        tmp_path, write(tmp_path, "nexus.csv", NEXUS),
    )
    mapping = load_industry_mapping(tmp_path)
    sources = load_industry_sources(tmp_path)
    assert mapping["M&M"] == "Automobile"
    assert sources["M&M"] == SOURCE_TIER_CHARTSMAZE
    assert mapping["NEWCO"] == "Pharmaceuticals Companies"
    assert sources["NEWCO"] == SOURCE_TIER_NEXUS
    assert stats["filled"] == 2  # NEWCO + AAYUSHBULL; M&M blocked
