"""B2-8 — per-symbol refusal reasons: the map the nightly now emits must

* name the PRIMARY refusal and every ADDITIONAL applicable reason
  (a symbol failing both a universe gate and the history floor lists both —
  the MILKYMIST class), and
* stay consistent with the aggregate bucket counts (a refused symbol's
  primary reason tallies back to its bucket; totals never double-count).

Synthetic store only — no corpus ingest; this is logic coverage, and the
regenerated-report acceptance (MILKYMIST in tonight_*.json) is checked
against the real nightly separately.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from unidesk.contracts.market import DailyBar
from unidesk.momentum.data.market_store import InMemoryMarketStore, VersionedDailyBar
from unidesk.momentum.scan import scan_universe

UTC = timezone.utc
DAY0 = datetime(2026, 6, 1, 18, 0, tzinfo=UTC)


def _add_session(store, symbol, i, close, vol):
    session = (DAY0 + timedelta(days=i)).date()
    bar = DailyBar(
        symbol=symbol, session=session,
        open=close, high=close + 0.5, low=close - 0.5,
        close=close, volume=int(vol), data_version="test",
    )
    store.add_daily_bar(VersionedDailyBar(bar=bar, available_at=DAY0 + timedelta(days=i + 1)))
    return session


def _fill(store, symbol, n, close, vol):
    for i in range(n):
        _add_session(store, symbol, i, close, vol)


def _scan(store):
    # as_of must be past every bar's available_at stamp, or the store yields
    # nothing and the gates never run (the scan is point-in-time by design).
    as_of = DAY0 + timedelta(days=200)
    return scan_universe(store, as_of, apply_universe_gates=True, min_sessions=61)


def _build() -> InMemoryMarketStore:
    store = InMemoryMarketStore()
    # passes everything: healthy price, ~₹5cr/day turnover, 100 sessions
    _fill(store, "HEALTHY", 100, close=500.0, vol=100_000)
    # price below ₹30 floor AND turnover under ₹2cr, but enough history:
    # primary = price floor, "also" must carry the turnover floor
    _fill(store, "POORCO", 100, close=10.0, vol=5_000)
    # plenty of turnover but only 30 sessions: primary = insufficient_sessions
    _fill(store, "SHORTCO", 30, close=500.0, vol=100_000)
    return store


def test_refusal_map_names_primary_and_all_applicable_reasons():
    scan = _scan(_build())
    ref = scan.symbol_refusals

    assert "HEALTHY" not in ref, "a symbol that passes every gate must not be refused"

    poor = ref["POORCO"]
    assert poor["reason"] == "universe_gate_price_floor"
    assert "universe_gate_turnover_floor" in poor.get("also", []), (
        "a symbol failing two gates must list both, not just the first"
    )
    assert poor["price"] == 10.0 and poor["floor"] == 30.0

    short = ref["SHORTCO"]
    assert short["reason"] == "insufficient_sessions"
    assert short["sessions"] == 30 and short["required"] == 61


def test_aggregate_counts_match_per_symbol_primaries():
    scan = _scan(_build())
    ref = scan.symbol_refusals
    primaries: dict[str, int] = {}
    for entry in ref.values():
        primaries[entry["reason"]] = primaries.get(entry["reason"], 0) + 1
    for reason, n in primaries.items():
        if reason.startswith("universe_gate_"):
            assert scan.skipped.get(reason) == n, reason
        elif reason == "insufficient_sessions":
            assert scan.skipped.get("insufficient_sessions") == n
    # no double counting: total refusals == total symbols refused under any reason
    assert len(ref) == sum(
        v for k, v in scan.skipped.items()
        if k.startswith("universe_gate_") or k == "insufficient_sessions"
    )
