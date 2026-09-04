"""FII/DII daily cash-provisional ingest → fii_dii_daily.

F7 (design/AGENTIC_BUILD_SPEC.md). NSE's own fiidiiTradeReact API and reports
pages sit behind Akamai bot detection and return 403 to every non-browser
client tried from this machine (urllib and curl alike, with full browser
headers) — not workable as an unattended source. groww.in/fii-dii-data is a
plain server-rendered Next.js page: the daily FII/DII cash figures (in Rs.
crore) are embedded verbatim in a `__NEXT_DATA__` JSON blob, no auth, no
bot-wall, confirmed reachable with a stock ``requests`` GET + a normal
desktop User-Agent. That JSON is `props.pageProps.initialData`, a list of
``{date, fii: {grossBuy, grossSell, netBuySell}, dii: {...}}`` rows (most
recent trading days, descending).

Failure-safe: any network/parse error is caught, logged as a `skip` (not
`fail`) pipeline_runs row, and the stage returns 0 — it never raises, so a
dead network or a page-layout change never breaks `run-eod`.
"""
from __future__ import annotations

import json
import re
import time

import requests

_SOURCE = "groww_fii_dii"
_STAGE = "ingest_fii_dii"
_URL = "https://groww.in/fii-dii-data"
_TIMEOUT = 15
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

_NEXT_DATA_RE = re.compile(
    r'id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.DOTALL
)


def _num(value) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_groww_html(html: str) -> list[dict]:
    """Extract FII/DII daily rows from the groww.in page HTML. Pure, no I/O.

    Returns a list of dicts shaped for fii_dii_daily, most-recent-first as
    served (caller does not need to re-sort for upsert since it's PK'd on
    trade_date). Raises ValueError if the expected JSON blob isn't found or
    doesn't parse — caller decides how to handle that.
    """
    m = _NEXT_DATA_RE.search(html)
    if not m:
        raise ValueError("__NEXT_DATA__ script tag not found")
    payload = json.loads(m.group(1))
    rows = (
        payload.get("props", {})
        .get("pageProps", {})
        .get("initialData", [])
    )
    if not isinstance(rows, list) or not rows:
        raise ValueError("initialData empty or not a list")

    out: list[dict] = []
    for r in rows:
        trade_date = r.get("date")
        fii = r.get("fii") or {}
        dii = r.get("dii") or {}
        if not trade_date:
            continue
        out.append({
            "trade_date": trade_date,
            "fii_buy": _num(fii.get("grossBuy")),
            "fii_sell": _num(fii.get("grossSell")),
            "fii_net": _num(fii.get("netBuySell")),
            "dii_buy": _num(dii.get("grossBuy")),
            "dii_sell": _num(dii.get("grossSell")),
            "dii_net": _num(dii.get("netBuySell")),
            "source": _SOURCE,
        })
    return out


def fetch_rows() -> list[dict]:
    """Network fetch + parse. Raises on any failure — caller (run) catches it."""
    resp = requests.get(_URL, headers=_HEADERS, timeout=_TIMEOUT)
    resp.raise_for_status()
    return parse_groww_html(resp.text)


def _upsert(conn, records: list[dict]) -> int:
    sql = (
        "INSERT INTO fii_dii_daily "
        "(trade_date, fii_buy, fii_sell, fii_net, dii_buy, dii_sell, dii_net, source) "
        "VALUES (:trade_date, :fii_buy, :fii_sell, :fii_net, :dii_buy, :dii_sell, :dii_net, :source) "
        "ON CONFLICT(trade_date) DO UPDATE SET "
        "fii_buy=excluded.fii_buy, fii_sell=excluded.fii_sell, fii_net=excluded.fii_net, "
        "dii_buy=excluded.dii_buy, dii_sell=excluded.dii_sell, dii_net=excluded.dii_net, "
        "source=excluded.source"
    )
    conn.executemany(sql, records)
    return len(records)


def _log_run(conn, run_date, status, rows, duration, detail) -> None:
    conn.execute(
        "INSERT INTO pipeline_runs (run_date, stage, source, status, "
        "rows_affected, duration_s, detail) VALUES (?,?,?,?,?,?,?)",
        (run_date, _STAGE, _SOURCE, status, rows, duration, detail),
    )


def run(conn, run_date: str, fetcher=fetch_rows) -> int:
    """Fetch latest FII/DII cash-provisional rows and upsert (idempotent).

    Never raises: any fetch/parse error is a `skip`, not a `fail` — this
    stage must not break run-eod on a dead network or an upstream layout
    change. ``fetcher`` is injectable for tests (no network in tests).
    """
    started = time.monotonic()
    try:
        records = fetcher()
    except Exception as exc:  # noqa: BLE001
        _log_run(conn, run_date, "skip", 0, time.monotonic() - started,
                 f"fetch failed: {type(exc).__name__}: {exc}")
        conn.commit()
        return 0

    if not records:
        _log_run(conn, run_date, "skip", 0, time.monotonic() - started,
                 "no rows parsed")
        conn.commit()
        return 0

    try:
        rows = _upsert(conn, records)
        _log_run(conn, run_date, "ok", rows, time.monotonic() - started,
                 f"{rows} rows (latest={records[0]['trade_date']})")
        conn.commit()
        return rows
    except Exception as exc:  # noqa: BLE001
        _log_run(conn, run_date, "skip", 0, time.monotonic() - started,
                 f"upsert failed: {type(exc).__name__}: {exc}")
        conn.commit()
        return 0
