"""NSE-direct daily bulk/block deal feed, independent of ChartsMaze."""
from __future__ import annotations

import csv
import io
import json
import time
from typing import Any, Callable

import requests

STAGE = "ingest_nse_deals"
SOURCE = "nse_daily_reports"
URLS = {
    "nse_bulk_deal": "https://nsearchives.nseindia.com/content/equities/bulk.csv",
    "nse_block_deal": "https://nsearchives.nseindia.com/content/equities/block.csv",
}
HEADERS = {"User-Agent": "Mozilla/5.0", "Accept": "text/csv,*/*", "Referer": "https://www.nseindia.com/all-reports"}


def _norm(value: Any) -> str:
    return " ".join(str(value or "").strip().lstrip("\ufeff").lower().replace("/", " ").split())


def _first(row: dict[str, Any], names: tuple[str, ...]) -> Any:
    normalized = {_norm(key): value for key, value in row.items()}
    for name in names:
        if name in normalized:
            return normalized[name]
    return None


def _date(raw: Any, fallback: str) -> str:
    text = str(raw or "").strip().replace("/", "-")
    parts = text.split("-")
    if len(parts) == 3:
        if len(parts[0]) == 4:
            return f"{int(parts[0]):04d}-{int(parts[1]):02d}-{int(parts[2]):02d}"
        return f"{int(parts[2]):04d}-{int(parts[1]):02d}-{int(parts[0]):02d}"
    return fallback


def parse_csv(text: str, kind: str, run_date: str) -> list[dict[str, Any]]:
    out = []
    for raw in csv.DictReader(io.StringIO(text.lstrip("\ufeff"))):
        symbol = str(_first(raw, ("symbol", "stock symbol")) or "").strip().upper()
        if not symbol:
            continue
        detail = {str(key).strip().lstrip("\ufeff"): value for key, value in raw.items()}
        # Canonical aliases keep the existing deal-value calculation working.
        detail["quantity"] = _first(raw, ("quantity traded", "quantity", "qty"))
        detail["price"] = _first(raw, ("trade price wavg", "trade price", "price", "wavg price"))
        detail["source"] = SOURCE
        out.append({
            "trade_date": _date(_first(raw, ("date", "trade date")), run_date),
            "symbol": symbol, "kind": kind, "detail": detail,
        })
    return out


def fetch_csv(url: str, timeout: int = 15) -> str:
    response = requests.get(url, headers=HEADERS, timeout=timeout)
    response.raise_for_status()
    return response.text


def run(conn, run_date: str, *, fetcher: Callable[[str], str] | None = None) -> int:
    started = time.monotonic()
    get = fetcher or fetch_csv
    rows = []
    errors = []
    for kind, url in URLS.items():
        try:
            rows.extend(parse_csv(get(url), kind, run_date))
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{kind}: {type(exc).__name__}: {exc}")
    for row in rows:
        conn.execute(
            "INSERT INTO disclosures(trade_date,symbol,kind,detail_json) VALUES(?,?,?,?) "
            "ON CONFLICT(trade_date,symbol,kind) DO UPDATE SET detail_json=excluded.detail_json",
            (row["trade_date"], row["symbol"], row["kind"], json.dumps(row["detail"], sort_keys=True)),
        )
    status = "ok" if rows else "skip"
    detail = f"NSE direct deals rows={len(rows)}" + (f"; {' | '.join(errors)}" if errors else "")
    conn.execute(
        "INSERT INTO pipeline_runs(run_date,stage,source,status,rows_affected,duration_s,detail) "
        "VALUES(?,?,?,?,?,?,?)",
        (run_date, STAGE, SOURCE, status, len(rows), time.monotonic() - started, detail),
    )
    conn.commit()
    return len(rows)
