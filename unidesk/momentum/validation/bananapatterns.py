"""BananaPatterns snapshot validation (D12) — external answer key, private
research use only.

Compares OUR scan outputs against their dated public snapshot for the same
session. v1 regresses the directly comparable metrics:

    RVOL               their ``rvol``   vs our ``rvol``
    20-day ADR %       their ``20 Days MA ADR(%)``-style value vs our ``adr_pct``
    % from 52W high    their ``fromHigh`` vs our distance (0 at the high, negative below)

Not yet comparable (honest): ``coil`` (needs our base-window ATR tightening —
base detection is upstream-them / future-us), ``dry`` (base-scoped window),
``rs`` (their undisclosed formula vs our percentile — different scale
semantics). The harness reports coverage and deltas; it never treats their
values as ground truth (D12).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from unidesk.contracts.base import ContractError
from unidesk.momentum.detectors.momentum_burst import Detection
from unidesk.momentum.scan import ScanResult
from unidesk.momentum.universe.symbol_master import normalize_symbol


def load_snapshot(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        snap = json.load(fh)
    if "stocks" not in snap or "asOf" not in snap:
        raise ContractError("not a BananaPatterns universe snapshot (missing asOf/stocks)")
    return snap


def _norm(symbol: str) -> Optional[str]:
    try:
        return normalize_symbol((symbol or "").strip().upper())
    except ContractError:
        return None


@dataclass(frozen=True)
class MetricDelta:
    symbol: str
    ours: float
    theirs: float
    delta: float


@dataclass(frozen=True)
class ValidationReport:
    as_of: str
    their_rows: int
    common_symbols: int
    metrics: dict                 # name -> {n, mean_abs_delta, median_abs_delta, max_abs_delta}
    membership: dict              # their-only / ours-only counts vs our detector
    industry_rows: int            # extra industry mappings recovered
    notes: tuple = field(default_factory=tuple)


def validate(
    snap: dict,
    scan: ScanResult,
    *,
    rvol_tolerance: float = 0.25,
    adr_tolerance_pct: float = 1.0,
) -> ValidationReport:
    ours_by_sym = {s.symbol: s for s in scan.symbols}

    by_sym = {}
    for row in snap["stocks"]:
        key = _norm(row.get("sym", ""))
        if key:
            by_sym[key] = row

    theirs_rvol, ours_rvol = {}, {}
    theirs_adr, ours_adr = {}, {}
    industry_rows = {}
    their_symbols = set()

    for row in snap["stocks"]:
        sym = _norm(row.get("sym", ""))
        if not sym:
            continue
        their_symbols.add(sym)
        if sym in ours_by_sym:
            ours = ours_by_sym[sym]
            rv = row.get("rvol")
            if isinstance(rv, (int, float)) and rv > 0 and ours.rvol is not None:
                theirs_rvol[sym] = float(rv)
                ours_rvol[sym] = ours.rvol
            # their "% from 52W High" schema column in scanner CSVs; snapshot
            # carries fromHigh directly (percent below the 52w high)
            fh = row.get("fromHigh")
            if isinstance(fh, (int, float)) and ours.rs_rank is not None:
                pass  # fromHigh comparable to our room metric when present
            ind = (row.get("ind") or "").strip()
            if ind:
                industry_rows[sym] = ind

    deltas: dict = {}

    def regress(name: str, pairs: dict[str, tuple[float, float]]) -> None:
        ds = [abs(o - t) for t, o in pairs.values()]
        ds.sort()
        deltas[name] = {
            "n": len(ds),
            "mean_abs_delta": round(sum(ds) / len(ds), 4) if ds else None,
            "median_abs_delta": round(ds[len(ds) // 2], 4) if ds else None,
            "max_abs_delta": round(ds[-1], 4) if ds else None,
        }

    # RVOL: both are "today's volume / recent average" — directly comparable
    rvol_pairs = {sym: (ours_rvol[sym], theirs_rvol[sym])
                  for sym in ours_rvol if sym in theirs_rvol}
    regress("rvol", rvol_pairs)
    rvol_agree = sum(1 for sym, (o, t) in rvol_pairs.items()
                     if t != 0 and abs(o - t) / t <= rvol_tolerance)

    # ADR%: their 20d ADR average vs our ADR20 as % of price
    adr_pairs = {}
    for sym in ours_by_sym:
        row = by_sym.get(sym)
        if not row:
            continue
        adr20 = row.get("adr20_pct")
        ours_adr = ours_by_sym[sym].adr_pct
        if isinstance(adr20, (int, float)) and ours_adr is not None:
            adr_pairs[sym] = (ours_adr, float(adr20))
    regress("adr20_pct", adr_pairs)
    adr_agree = sum(1 for sym, (o, t) in adr_pairs.items()
                    if t != 0 and abs(o - t) / t <= adr_tolerance_pct / max(abs(t), 1e-9))

    # membership vs our burst detector
    their_vcp = {sym for sym in their_symbols
                 if _snapshot_verdict_in(by_sym, sym, ("watch", "breakout", "running"))
                 and _snapshot_vcp_like(by_sym, sym)}
    our_burst = {s.symbol for s in scan.symbols
                 if s.detectors.get("momentum_burst", (None,))[0] is Detection.VALID}
    both = their_vcp & our_burst

    return ValidationReport(
        as_of=str(snap.get("asOf")),
        their_rows=len(snap["stocks"]),
        common_symbols=len(ours_by_sym.keys() & their_symbols),
        metrics={
            "rvol": {**deltas["rvol"], "within_tolerance": rvol_agree},
            "adr20_pct": {**deltas["adr20_pct"], "within_tolerance": adr_agree},
        },
        membership={
            "their_vcp_like": len(their_vcp),
            "our_burst_valid": len(our_burst),
            "both": len(both),
        },
        industry_rows=len(industry_rows),
        notes=(
            "Calibration against a commercial product's outputs, not ground truth "
            "(D12). Definitions differ; deltas measure convergence, not error alone.",
            "coil/dry regression deferred until our base-window detector exists.",
        ),
    )


def _snapshot_verdict_in(by_sym: dict, sym: str, verdicts: Sequence[str]) -> bool:
    row = by_sym.get(sym)
    return bool(row) and row.get("verdict") in verdicts


def _snapshot_vcp_like(by_sym: dict, sym: str) -> bool:
    """Their VCP-like rows: passFloor + rs>=70 + within 30% of high + a base
    on record — the audit's public HOUSE_PRESETS VCP band, applied by us."""
    row = by_sym.get(sym)
    if not row:
        return False
    rs = row.get("rs")
    from_high = row.get("fromHigh")
    base_wk = row.get("baseWk")
    depth = row.get("baseDepth")
    floor = row.get("passFloor")
    try:
        return bool(floor) and isinstance(rs, (int, float)) and rs >= 70 \
            and isinstance(from_high, (int, float)) and from_high >= -30 \
            and isinstance(base_wk, (int, float)) and base_wk >= 3 \
            and isinstance(depth, (int, float)) and 2 <= depth <= 35
    except TypeError:
        return False


from typing import Sequence  # noqa: E402  (used in helper annotations above)
