"""JSON sibling of the nightly Markdown report (N1; UI_BACKEND_INTEGRATION_
PLAN.md wave 1 -- the "UI backend integration" TASKS.md item, also tracked
under N8 Terminal UI).

Corrected premise, verified before writing this file: the integration plan
says report.py "already builds the typed objects it renders to Markdown ...
contracts.*.to_dict()". That is not what the code does -- `report.py` and
`scan_universe()` work directly off `ScanResult`/`SymbolScan`
(`unidesk/momentum/scan.py`), a lighter dataclass pair, not the frozen
`contracts.candidate`/`contracts.setup` objects (those require fields --
`snapshot_id`, `geometry_snapshot_id`, `config_hash`, quality scores -- that
scan_universe never computes). Constructing fake contract instances just to
call their `to_dict()` would mean inventing data, which the honesty rules
this module exists to serve explicitly forbid. Instead this module builds
its dict directly from the same `ScanResult`/`SymbolScan` instance
`build_nightly_report` renders, reusing `contracts.base.to_dict()` only for
its datetime/enum serialization helpers. Same in-memory objects, two
renders, no re-derivation, no drift, no invented fields.
"""
from __future__ import annotations

from typing import Any, Optional

from unidesk.contracts.base import to_dict as _to_dict
from unidesk.momentum.detectors.momentum_burst import Detection
from unidesk.momentum.detectors.trust import detector_trust, detector_trust_map
from unidesk.momentum.features.breadth import (
    bo_bd_ratio, net_nh_nl, up_down_close_pct, volatility_ratio, volume_ratio,
)
from unidesk.momentum.report import _DETECTOR_TITLES
from unidesk.momentum.scan import ScanResult, SymbolScan

# Raw scan fields report.py's Markdown table already prints per candidate.
# Stock-quality (0-100) is now real, added separately below as
# "stock_quality" -- still no trigger/invalidation prices or entry-quality
# score (those need a real trigger/hurdle/invalidation geometry no detector
# in this pipeline computes yet; see momentum/scoring/entry_quality.py's
# module docstring) and no company/sector names. A UI screen that needs
# those must keep using its labelled illustrative fallback.
_CANDIDATE_FIELDS = (
    "symbol", "close", "adr_pct", "rs_rank", "rvol",
    "contraction", "delivery_ratio", "trigger", "invalidation", "rr",
)


def _quality_snapshot_dict(sq) -> Optional[dict]:
    """Shared serializer for setup/entry quality snapshots (score,
    coverage, unknowns — R12-named reasons, never fabricated)."""
    if sq is None:
        return None
    return {
        "score": sq.score,
        "coverage": sq.coverage,
        "unknowns": list(sq.unknowns),
        "feature_version": sq.feature_version,
        "config_hash": sq.config_hash,
    }


def _stock_quality_dict(sq) -> Optional[dict]:
    if sq is None:
        return None
    return {
        "score": sq.score,
        "coverage": sq.coverage,
        "unknowns": list(sq.unknowns),
        "hard_gates": list(sq.hard_gates),
        "feature_version": sq.feature_version,
        "config_hash": sq.config_hash,
    }


def _candidate_dict(s: SymbolScan) -> dict:
    d: dict[str, Any] = {f: getattr(s, f) for f in _CANDIDATE_FIELDS}
    d["trend"] = s.trend.value
    d["sessions"] = s.sessions
    d["adjusted"] = s.adjusted
    # P1.9, wired into the scan for the first time (previously zero
    # production call sites): additive field, None when the score itself
    # is None (insufficient coverage) or when the scan predates this wiring.
    d["stock_quality"] = _stock_quality_dict(s.stock_quality)
    # P2.4 / P2.8 — the audit's named blocker on these ("no trigger/stop
    # geometry exists anywhere — R12 forbids inventing it") was cleared by
    # Stage 3's per-candidate trade geometry; both snapshots are now
    # computed at scan time and emitted here. UI maps each to the
    # corresponding Quality-Stack slot (Stock/Setup/Entry).
    d["setup_quality"] = _quality_snapshot_dict(getattr(s, "setup_quality", None))
    d["entry_quality"] = _quality_snapshot_dict(getattr(s, "entry_quality", None))
    d["activity_score"] = s.activity_score
    d["geometry_notes"] = list(s.geometry_notes) if s.geometry_notes else None
    return d


def _episode_dict(episode) -> dict:
    return {
        "episode_id": episode.episode_id,
        "symbol": episode.symbol,
        "as_of": episode.as_of.isoformat(),
        "known_at": episode.known_at.isoformat(),
        "method_version": episode.method_version,
        "adjustment_basis_hash": episode.adjustment_basis_hash,
        "base_start": episode.base_start.isoformat(),
        "base_end": episode.base_end.isoformat(),
        "base_sessions": episode.base_sessions,
        "base_weeks": episode.base_weeks,
        "pivot": episode.pivot,
        "floor": episode.floor,
        "depth_pct": episode.depth_pct,
        "coil_ratio": episode.coil_ratio,
        "dry_ratio": episode.dry_ratio,
        "dry_depth_ratio": episode.dry_depth_ratio,
        "rs_rank": episode.rs_rank,
        "verdict": episode.verdict.value,
        "notes": list(episode.notes),
        "annotations": [
            {
                "kind": annotation.kind.value,
                "occurred_at": annotation.occurred_at.isoformat(),
                "known_at": annotation.known_at.isoformat(),
            }
            for annotation in episode.annotations
        ],
        "pullback_depths": list(episode.pullback_depths),
        "atrp_percentile": episode.atrp_percentile,
        "delivery_bottom_quintile": episode.delivery_bottom_quintile,
        "rs_made_20d_low": episode.rs_made_20d_low,
        "vcp_match": _vcp_match(episode),
    }


def _vcp_match(episode) -> Optional[dict]:
    """VCP (Volatility Contraction Pattern, Minervini) preset match from the
    clean-room base episode. Pure — reuses match_base_preset over the
    episode's own fields. The VCP screen checks: minimum base duration (3
    weeks), maximum base depth (35%), coil/tightness (volatility contraction
    <= 0.9), volume dry-up (quiet trading <= 0.9), and relative strength
    (>= 70). These are the published Minervini VCP criteria, not a proprietary
    derivative. Blue-sky/multi-year/IPO presets are flagged as
    ``requires_*`` failures rather than guessing — the clean-room detector
    has no 52-week context for those."""
    from unidesk.momentum.detectors.base_episode import (
        BasePreset, match_base_preset,
    )
    try:
        result = match_base_preset(episode, BasePreset.VCP)
        return {
            "preset": "vcp",
            "included": result.included,
            "failed_rules": list(result.failed_rules),
        }
    except Exception:
        return None
def _breadth_analytics(scan: ScanResult) -> dict:
    """Derived breadth analytics from scan counters. Pure functions over the
    counts dict; breakouts/breakdowns are None because the scan loop doesn't
    run the full detector pipeline per symbol (that would double the scan
    time for a single derived ratio)."""
    counts = {
        "total_universe": scan.scanned,
        "new_52wk_high": scan.new_52wk_high,
        "new_52wk_low": scan.new_52wk_low,
        "range_expansion": scan.range_expansion,
        "range_contraction": scan.range_contraction,
        "high_vol": scan.high_vol,
        "low_vol": scan.low_vol,
        "close_upper_half": scan.close_upper_half,
        "close_lower_half": scan.close_lower_half,
        # breakouts / breakdowns not collected in scan loop
    }
    return {
        "net_nh_nl": net_nh_nl(counts),
        "volatility_ratio": volatility_ratio(counts),
        "volume_ratio": volume_ratio(counts),
        "up_down_close_pct": up_down_close_pct(counts),
        "bo_bd_ratio": None,  # needs breakout detector pass in loop
    }


def build_nightly_json(scan: ScanResult, *, regime_note: str = "not built yet (wave N2)") -> dict:
    """Build the JSON sibling of ``build_nightly_report`` for the SAME
    ``ScanResult``. Structural mirror of report.py's Markdown sections
    (same detector grouping, same per-candidate fields, same sort order),
    with the honesty-footer facts as first-class typed keys instead of
    prose a UI would have to parse back out.
    """
    date_str = scan.last_session or scan.as_of.date().isoformat()

    by_detector: dict[str, list[SymbolScan]] = {}
    for s in scan.symbols:
        for name, (det, _failures) in s.detectors.items():
            if det is Detection.VALID:
                by_detector.setdefault(name, []).append(s)

    setups: list[dict] = []
    candidates: list[dict] = []
    for name in sorted(by_detector):
        title = _DETECTOR_TITLES.get(name, name)
        group = sorted(by_detector[name], key=lambda x: -(x.rs_rank or 0))
        group_dicts = [_candidate_dict(s) for s in group]
        setups.append({
            "detector": name,
            "title": title,
            "trust": detector_trust(name),
            "candidate_count": len(group_dicts),
            "candidates": group_dicts,
        })
        for cd in group_dicts:
            candidates.append({
                **cd, "detector": name, "setup_title": title,
                "trust": detector_trust(name),
            })

    n_skip = scan.skipped.get("insufficient_sessions", 0)
    gate_skips = {k: v for k, v in scan.skipped.items() if k.startswith("universe_gate_")}
    n_adj = getattr(scan, "adjusted_symbols", 0) or 0
    n_act = getattr(scan, "actions_applied", 0) or 0
    # Same test the Markdown branch uses implicitly (report.py:74, `if n_act:`)
    # -- restated here as an explicit boolean field instead of leaving the
    # UI to infer adjustment status by parsing prose.
    regime_built = not regime_note.strip().lower().startswith("not built")

    if n_act:
        adjustment_note = (
            f"Data source: NSE bhavcopy (EQ series). Confirmed CA table applied "
            f"as a derived view at scan time ({n_act} actions, {n_adj} symbols). "
            "Raw prints stay in the store. Official NSE CA-with-ratios still open."
        )
        adjustment_status = "confirmed_ca_applied"
    else:
        adjustment_note = (
            "Data source: NSE bhavcopy (EQ series). Unadjusted prices — "
            "long-window features are provisional until the corporate-action "
            "adjustment pass (N3)."
        )
        adjustment_status = "unadjusted_provisional"

    honesty_footer = {
        "regime_note": regime_note,
        "regime_built": regime_built,
        "universe_scanned": scan.scanned,
        "universe_skipped_insufficient_history": n_skip,
        "universe_gate_skips": gate_skips,
        "universe_gate_skips_total": sum(gate_skips.values()),
        "pct_above_ema50": (
            round(scan.pct_above_ema50, 1) if scan.pct_above_ema50 is not None else None
        ),
        "above_ema21": scan.above_ema21,
        "above_ema21_of": scan.scanned,
        "detection_inputs_policy": (
            "Detection inputs missing for some symbols (RS needs 21 sessions, "
            "ADR/RVOL need 20 priors): such symbols are excluded from that "
            "detector, not zero-filled."
        ),
        "adjustment_status": adjustment_status,
        "actions_applied": n_act,
        "adjusted_symbols": n_adj,
        "adjustment_note": adjustment_note,
        "disclaimer": (
            "All outputs are rule results for research review. They are not "
            "recommendations, and nothing here places orders."
        ),
        "breadth": {
            "near_highs_5pct": scan.near_highs_5pct,
            "near_lows_5pct": scan.near_lows_5pct,
            "near_highs_pct": round(scan.near_highs_5pct / scan.scanned * 100, 1) if scan.scanned else None,
            "near_lows_pct": round(scan.near_lows_5pct / scan.scanned * 100, 1) if scan.scanned else None,
            "analytics": _breadth_analytics(scan) if scan.scanned else None,
        },
    }

    return {
        "schema_version": 1,
        "session_date": date_str,
        "as_of": _to_dict(scan.as_of),
        "honesty_footer": honesty_footer,
        "detector_trust": detector_trust_map(),
        "base_episodes": [
            _episode_dict(symbol.base_episode)
            for symbol in scan.symbols if symbol.base_episode is not None
        ],
        "setups": setups,
        "candidates": candidates,
    }
