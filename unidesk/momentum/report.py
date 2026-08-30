"""The Nightly Report renderer (N1; UI manual V2 §3).

Pure function: a :class:`~unidesk.momentum.scan.ScanResult` in, TONIGHT
markdown out. Honesty rules are structural: every candidate names its
numbers; gaps and skips are reported in the footer; the regime line says
``not built`` until R0 exists — a placeholder is never dressed up.
"""
from __future__ import annotations

from unidesk.momentum.detectors.momentum_burst import Detection
from unidesk.momentum.scan import ScanResult

_DETECTOR_TITLES = {
    "momentum_burst": "Momentum Burst",
    "episodic_pivot": "Episodic Pivot",
    "episodic_pivot_partial": "Episodic Pivot (partial inputs)",
    "ipo_base": "IPO Base",
    "inside_bar": "Inside Bar",
    "base_breakout": "Base Breakout",
    "pullback": "Pullback",
    "reversal_reclaim": "Reversal / Reclaim",
    "power_play": "Power Play",
}


def build_nightly_report(scan: ScanResult, *, regime_note: str = "not built yet (wave N2)") -> str:
    lines: list[str] = []
    date_str = scan.last_session or scan.as_of.date().isoformat()

    lines.append("# Tonight's Report")
    lines.append("")
    lines.append(f"**Session:** {date_str}  ·  **Regime:** {regime_note}")
    lines.append(f"**Universe:** {scan.scanned} scanned · "
                 f"{scan.skipped.get('insufficient_sessions', 0)} skipped (insufficient history) · "
                 f"{round(scan.pct_above_ema50, 1) if scan.pct_above_ema50 is not None else '—'}% above EMA50 · "
                 f"{scan.above_ema21}/{scan.scanned} above EMA21")
    lines.append("")

    lines.append("## Setups")
    lines.append("")
    by_detector: dict[str, list] = {}
    for s in scan.symbols:
        for name, (det, failures) in s.detectors.items():
            if det is Detection.VALID:
                by_detector.setdefault(name, []).append(s)
    if not by_detector:
        lines.append("_No candidates passed tonight. That is a result, not an error._")
        lines.append("")
    for name in sorted(by_detector):
        title = _DETECTOR_TITLES.get(name, name)
        lines.append(f"### {title} — {len(by_detector[name])} candidate(s)")
        lines.append("")
        lines.append("| Symbol | Close | ADR% | RS rank | RVOL | Contraction | Delivery ratio | Trend |")
        lines.append("|---|---|---|---|---|---|---|---|")
        for s in sorted(by_detector[name], key=lambda x: -(x.rs_rank or 0)):
            lines.append(
                f"| {s.symbol} | {s.close} | {s.adr_pct} | {s.rs_rank} | "
                f"{s.rvol} | {s.contraction} | {s.delivery_ratio} | {s.trend.value} |"
            )
        lines.append("")
        lines.append("_Rule outputs, not recommendations. Thresholds are config; see the parameter register._")
        lines.append("")

    lines.append("## Honesty footer")
    lines.append("")
    lines.append(f"- Regime classifier: {regime_note}.")
    lines.append(f"- Symbols skipped for insufficient history: "
                 f"{scan.skipped.get('insufficient_sessions', 0)}.")
    lines.append("- Detection inputs missing for some symbols (RS needs 21 sessions, "
                 "ADR/RVOL need 20 priors): such symbols are excluded from that detector, "
                 "not zero-filled.")
    n_adj = getattr(scan, "adjusted_symbols", 0) or 0
    n_act = getattr(scan, "actions_applied", 0) or 0
    if n_act:
        lines.append(
            f"- Data source: NSE bhavcopy (EQ series). Confirmed CA table applied "
            f"as a derived view at scan time ({n_act} actions, {n_adj} symbols). "
            "Raw prints stay in the store. Official NSE CA-with-ratios still open."
        )
    else:
        lines.append("- Data source: NSE bhavcopy (EQ series). Unadjusted prices — long-window "
                     "features are provisional until the corporate-action adjustment pass (N3).")
    lines.append("- All outputs are rule results for research review. They are not "
                 "recommendations, and nothing here places orders.")
    lines.append("")
    return "\n".join(lines)
