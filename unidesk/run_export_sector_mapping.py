"""Export the symbol → sector/industry mapping for the UI (spec §13/§14).

Source: data/market/reference/industry_mapping.parquet +
industry_sector.parquet — Chartsmaze VENDOR labels (source_tier=CHARTSMAZE),
not NSE official. The UI must disclose that provenance wherever shown.

Output: unidesk_terminal/src/data/sector_mapping.json
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[1]
REF = REPO / "data" / "market" / "reference"
OUT = REPO / "unidesk_terminal" / "src" / "data" / "sector_mapping.json"

if __name__ == "__main__":
    ind = pd.read_parquet(REF / "industry_mapping.parquet")
    sec = pd.read_parquet(REF / "industry_sector.parquet")
    ind2sec = dict(zip(sec["industry"], sec["sector"]))
    mapping = {}
    for row in ind.itertuples(index=False):
        mapping[row.symbol] = {
            "industry": row.industry,
            "sector": ind2sec.get(row.industry, "Unclassified"),
        }
    payload = {
        "source": "data/market/reference/industry_mapping.parquet + industry_sector.parquet (source_tier=CHARTSMAZE, vendor labels - not NSE official)",
        "generator": "unidesk/run_export_sector_mapping.py",
        "count": len(mapping),
        "symbols": mapping,
    }
    OUT.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
    print(f"[export] {len(mapping)} symbol sector mappings -> {OUT}")
