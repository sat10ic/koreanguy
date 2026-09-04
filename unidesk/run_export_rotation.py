"""N-28 — RRG-lite data builder: relative rotation from sectoral indices.

Produces the data structure the Market screen's RRG chart consumes: per
sector, per session — RS_Ratio (x) and RS_Momentum (y), percentile-normalised
across all groups on that date (spec §20). The frontend renders; it never
computes.

    .venv-orderflow/Scripts/python.exe unidesk/run_export_rotation.py

Requires N-1 (canonical index_id) and N-2 (sectoral indices in store).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from unidesk.momentum.data.indices import load_index_rows, series_for  # noqa: E402
from unidesk.research.group_rs import jdk_rs_series, percentile_normalise  # noqa: E402

INDEX_PATH = REPO / "data" / "market" / "reference" / "indices.parquet"
OUT = REPO / "unidesk_terminal" / "src" / "data" / "rotation.json"
BENCHMARK = "NIFTY_500"

SECTORAL_IDS = [
    "NIFTY_AUTO", "NIFTY_BANK", "NIFTY_FIN_SERVICE", "NIFTY_FMCG", "NIFTY_IT",
    "NIFTY_MEDIA", "NIFTY_METAL", "NIFTY_PHARMA", "NIFTY_PVT_BANK",
    "NIFTY_PSU_BANK", "NIFTY_REALTY", "NIFTY_ENERGY", "NIFTY_INFRA",
    "NIFTY_COMMODITIES", "NIFTY_CONSUMPTION", "NIFTY_CPSE",
]
DISPLAY = {
    "NIFTY_AUTO": "Auto", "NIFTY_BANK": "Bank", "NIFTY_FIN_SERVICE": "Fin Service",
    "NIFTY_FMCG": "FMCG", "NIFTY_IT": "IT", "NIFTY_MEDIA": "Media",
    "NIFTY_METAL": "Metal", "NIFTY_PHARMA": "Pharma", "NIFTY_PVT_BANK": "Pvt Bank",
    "NIFTY_PSU_BANK": "PSU Bank", "NIFTY_REALTY": "Realty", "NIFTY_ENERGY": "Energy",
    "NIFTY_INFRA": "Infra", "NIFTY_COMMODITIES": "Commodities",
    "NIFTY_CONSUMPTION": "Consumption", "NIFTY_CPSE": "CPSE",
}


def main() -> int:
    rows = load_index_rows(INDEX_PATH)

    bench = series_for(rows, BENCHMARK)
    bench_closes = [c for _, c in bench]
    bench_dates = [d for d, _ in bench]

    series_by_sector: dict[str, list] = {}
    for sector_id in SECTORAL_IDS:
        pts = series_for(rows, sector_id)
        if len(pts) < 60:  # JdK warm-up
            print(f"[rotation] {sector_id}: {len(pts)} sessions < 60 — skipped")
            continue
        series_by_sector[sector_id] = [c for _, c in pts]

    if not series_by_sector:
        print("[rotation] no sectoral index with ≥60 sessions — build N-2 first")
        return 1

    # align dates to the benchmark (inner join on session)
    result: dict[str, list] = {"sectors": [], "session": "N/A"}
    for sector_id, closes in series_by_sector.items():
        name = DISPLAY.get(sector_id, sector_id)
        jdk = jdk_rs_series(closes, bench_closes[:len(closes)], m=20, k=20)
        valid = [(i, r, m) for i, (r, m) in enumerate(jdk) if r is not None and m is not None]
        if not valid:
            print(f"[rotation] {name}: no valid JdK points")
            continue
        result["sectors"].append({
            "id": sector_id, "name": name,
            "sessions": len(closes),
            "latest_ratio": valid[-1][1],
            "latest_momentum": valid[-1][2],
            "jdk": [{"i": i, "ratio": round(r, 3) if r else None,
                     "momentum": round(m, 2) if m else None} for i, r, m in valid],
        })
        print(f"[rotation] {name}: {len(valid)} JdK points, "
              f"latest ratio={valid[-1][1]:.2f} momentum={valid[-1][2]:.2f}")

    # percentile-normalise the latest point across all sectors
    ratios = [s["latest_ratio"] for s in result["sectors"]]
    momenta = [s["latest_momentum"] for s in result["sectors"]]
    for s in result["sectors"]:
        r_rank = (sorted(ratios).index(s["latest_ratio"]) / max(1, len(ratios) - 1)) * 100
        m_rank = (sorted(momenta).index(s["latest_momentum"]) / max(1, len(momenta) - 1)) * 100
        s["rs_ratio_pct"] = round(r_rank, 1)
        s["rs_momentum_pct"] = round(m_rank, 1)

    result["session"] = bench_dates[-1] if bench_dates else "N/A"
    OUT.write_text(json.dumps(result, indent=1, default=str, allow_nan=False).replace("NaN", "null"), encoding="utf-8")
    print(f"[rotation] -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
