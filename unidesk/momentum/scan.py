"""Universe scan (N1): per-symbol feature computation + detector runs at one
point-in-time instant.

This is the Scout's engine room: given the store and an ``as_of``, it
produces one :class:`SymbolScan` per eligible symbol — every value named,
every gap carried as None + reason. Detectors are pure rule consumers;
thresholds are parameters (R14). The regime classifier is NOT here (N2);
its placeholder reason is carried honestly in the report.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Sequence

from unidesk.contracts.base import ContractError, ensure_utc
from unidesk.momentum.data.corp_actions import (
    ConfirmedAction, adjust_ohlcv, confirmed_actions_content_hash,
)
from unidesk.momentum.data.market_store import InMemoryMarketStore
from unidesk.momentum.detectors.inputs import compute_setup_inputs
from unidesk.momentum.detectors.base_episode import BaseEpisode, base_episode_from_bars
from unidesk.momentum.detectors.base_pattern import DailyBar as CleanroomDailyBar
from unidesk.momentum.detectors.momentum_burst import BurstRules, Detection
from unidesk.momentum.detectors.registry import DetectorConfig, evaluate_all
from unidesk.momentum.features.adr_atr import adr, atr
from unidesk.momentum.features.participation import rvol
from unidesk.momentum.features.rs import percentile_rank, window_return
from unidesk.momentum.features.trend import TrendState, ema, ema_rising, trend_state

MIN_SESSIONS_DEFAULT = 61   # 20 prior + 20 window + 20 EMA + 1: honest floor
CONTRACTION_RECENT_N = 5
CONTRACTION_PRIOR_N = 20


@dataclass
class SymbolScan:
    symbol: str
    sessions: int
    close: float
    ema21: Optional[float]
    ema50: Optional[float]
    rising21: Optional[bool]
    trend: TrendState
    adr_pct: Optional[float]
    atr_pct: Optional[float]
    rvol: Optional[float]
    delivery_ratio: Optional[float]
    rs_rank: Optional[float]
    contraction: Optional[float]
    detectors: dict = field(default_factory=dict)   # name -> (Detection, failures)
    setup_inputs: dict = field(default_factory=dict)  # frozen detector inputs
    adjusted: bool = False   # True iff this symbol's OHLCV was CA-adjusted (directive-1c)
    base_episode: Optional[BaseEpisode] = None

    @property
    def detection_names(self) -> tuple:
        return tuple(name for name, (det, _f) in self.detectors.items() if det is Detection.VALID)


@dataclass
class ScanResult:
    as_of: datetime
    scanned: int
    skipped: dict                  # reason -> count
    symbols: list                  # list[SymbolScan], sorted by symbol
    universe_returns: dict         # symbol -> 20d return (%), for RS
    above_ema21: int
    above_ema50: int
    last_session: Optional[str] = None  # ISO date of the latest observed session
    adjusted_symbols: int = 0
    actions_applied: int = 0

    @property
    def pct_above_ema50(self) -> Optional[float]:
        return 100.0 * self.above_ema50 / self.scanned if self.scanned else None


def scan_universe(
    store: InMemoryMarketStore,
    as_of: datetime,
    *,
    min_sessions: int = MIN_SESSIONS_DEFAULT,
    ema_span: int = 21,
    ema_long_span: int = 50,
    rvol_span: int = 20,
    adr_span: int = 20,
    run_detectors: bool = True,
    burst_rules: Optional[BurstRules] = None,
    detector_config: Optional[DetectorConfig] = None,
    actions: Optional[Sequence[ConfirmedAction]] = None,
) -> ScanResult:
    as_of = ensure_utc(as_of, "as_of")
    action_list: tuple[ConfirmedAction, ...] = tuple(actions or ())
    by_symbol: dict[str, list] = {}
    for item in store._daily:
        if item.available_at <= as_of:
            by_symbol.setdefault(item.bar.symbol, []).append(item)
    for sym in by_symbol:
        by_symbol[sym].sort(key=lambda b: b.bar.session)

    # universe 20d returns for RS ranking (point-in-time; CA-adjusted when confirmed)
    universe_returns: dict = {}
    series_by_symbol: dict[str, dict] = {}
    for sym, bars in by_symbol.items():
        sessions = [b.bar.session for b in bars]
        adj = adjust_ohlcv(
            opens=[b.bar.open for b in bars],
            highs=[b.bar.high for b in bars],
            lows=[b.bar.low for b in bars],
            closes=[b.bar.close for b in bars],
            volumes=[float(b.bar.volume) for b in bars],
            sessions=sessions, symbol=sym, actions=action_list,
        )
        series_by_symbol[sym] = adj
        closes = adj["close"]
        if len(closes) >= 21:
            wr = window_return(closes, 20)[-1]
            if wr is not None:
                universe_returns[sym] = wr

    scans: list[SymbolScan] = []
    skipped = {"insufficient_sessions": 0}
    above21 = above50 = 0
    adjusted_symbols = 0
    all_returns = list(universe_returns.values())

    for sym in sorted(by_symbol):
        bars = by_symbol[sym]
        if len(bars) < min_sessions:
            skipped["insufficient_sessions"] += 1
            continue
        dvp = [b.bar.delivery_percentage for b in bars]
        adj = series_by_symbol[sym]
        if adj["adjusted"]:
            adjusted_symbols += 1
        opens, highs, lows, closes, vols = (
            adj["open"], adj["high"], adj["low"], adj["close"], adj["volume"],
        )
        try:
            e21 = ema(closes, ema_span)
            e50 = ema(closes, ema_long_span)
            a = adr(highs, lows, adr_span)
            at = atr(highs, lows, closes, 14)
            rv = rvol(vols, rvol_span)
            close = closes[-1]
            rising = ema_rising(e21, len(e21) - 1)
            adr_pct = a[-1] / close * 100.0 if a[-1] else None
            atr_pct = at[-1] / close * 100.0 if at[-1] else None
            state = trend_state(close, e21[-1], e50[-1], bool(rising))
            if e50[-1] is not None and close > e50[-1]:
                above50 += 1
            if e21[-1] is not None and close > e21[-1]:
                above21 += 1

            rs_rank = (
                percentile_rank(all_returns, universe_returns[sym])
                if sym in universe_returns else None
            )
            from unidesk.momentum.primitives.contraction import range_contraction_ratio
            cr = range_contraction_ratio(highs, lows, CONTRACTION_RECENT_N, CONTRACTION_PRIOR_N)
            dvr = delivery_volume_ratio_safe(vols, dvp, rvol_span)

            scan = SymbolScan(
                symbol=sym, sessions=len(bars), close=close,
                ema21=e21[-1], ema50=e50[-1], rising21=rising, trend=state,
                adr_pct=round(adr_pct, 3) if adr_pct is not None else None,
                atr_pct=round(atr_pct, 3) if atr_pct is not None else None,
                rvol=round(rv[-1], 3) if rv[-1] is not None else None,
                delivery_ratio=round(dvr, 3) if dvr is not None else None,
                rs_rank=round(rs_rank, 1) if rs_rank is not None else None,
                contraction=round(cr, 3) if cr is not None else None,
                adjusted=bool(adj["adjusted"]),
            )
            # A BaseEpisode is a separate clean-room object, never a substitute
            # for the eight legacy detector verdicts.  Its adjustment basis is
            # retained so a later chart or screen can disclose its provenance.
            episode_rs = (
                int(round(rs_rank)) if rs_rank is not None and 1 <= rs_rank <= 99 else None
            )
            cleanroom_bars = [
                CleanroomDailyBar(
                    day=bars[index].bar.session, open=opens[index], high=highs[index],
                    low=lows[index], close=closes[index], volume=vols[index],
                )
                for index in range(len(bars))
            ]
            scan.base_episode = base_episode_from_bars(
                symbol=sym, bars=cleanroom_bars, rs_rank=episode_rs,
                adjustment_basis_hash=f"confirmed-actions:{confirmed_actions_content_hash()}",
            )
            if run_detectors:
                cfg = detector_config or DetectorConfig(
                    burst_rules=burst_rules or BurstRules(),
                )
                extras = compute_setup_inputs(
                    opens=opens,
                    highs=highs, lows=lows, closes=closes, volumes=vols,
                    delivery_pcts=dvp, rs_rank=rs_rank,
                )
                scan.setup_inputs = extras
                scan.detectors = evaluate_all(extras, config=cfg)
            scans.append(scan)
        except ContractError:
            skipped["insufficient_sessions"] += 1

    last_session = max(
        (bars[-1].bar.session for bars in by_symbol.values() if bars),
        default=None,
    )
    return ScanResult(
        as_of=as_of, scanned=len(scans), skipped=skipped, symbols=scans,
        universe_returns=universe_returns, above_ema21=above21, above_ema50=above50,
        last_session=last_session.isoformat() if last_session else None,
        adjusted_symbols=adjusted_symbols,
        actions_applied=len(action_list),
    )


def delivery_volume_ratio_safe(vols: list, dvp: list, span: int) -> Optional[float]:
    from unidesk.momentum.features.participation import delivery_volume_ratio
    try:
        out = delivery_volume_ratio(vols, dvp, span)
        return out[-1] if out else None
    except ContractError:
        return None


def run_symbol_detectors(scan: SymbolScan,
                         *,
                         config: Optional[DetectorConfig] = None) -> dict:
    """Replay detectors over a scan's frozen ``setup_inputs``.

    Prefer the inputs captured at scan time; fall back to the named
    SymbolScan fields for older call sites that never computed extras.
    """
    inputs = dict(scan.setup_inputs or {})
    inputs.setdefault("adr_pct", scan.adr_pct)
    inputs.setdefault("rs_rank", scan.rs_rank)
    inputs.setdefault("rvol", scan.rvol)
    inputs.setdefault("contraction_ratio", scan.contraction)
    inputs.setdefault("delivery_ratio", scan.delivery_ratio)
    inputs.setdefault("breakout_rvol", scan.rvol)
    inputs.setdefault("volume_expansion", scan.rvol)
    inputs.setdefault("avwap_extension_adr", None)
    return evaluate_all(inputs, config=config)
