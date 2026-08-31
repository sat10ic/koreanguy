"""Universe scan (N1): per-symbol feature computation + detector runs at one
point-in-time instant.

This is the Scout's engine room: given the store and an ``as_of``, it
produces one :class:`SymbolScan` per eligible symbol — every value named,
every gap carried as None + reason. Detectors are pure rule consumers;
thresholds are parameters (R14). The regime classifier is NOT here (N2);
its placeholder reason is carried honestly in the report.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Mapping, Optional, Sequence

from unidesk.contracts.base import ContractError, ensure_utc
from unidesk.momentum.data.corp_actions import (
    ConfirmedAction, adjust_ohlcv, confirmed_actions_content_hash, detect_split_candidates_bars,
)
from unidesk.momentum.data.market_store import InMemoryMarketStore
from unidesk.momentum.detectors.inputs import compute_setup_inputs
from unidesk.momentum.detectors.base_episode import BaseEpisode, base_episode_from_bars
from unidesk.momentum.detectors.base_pattern import DailyBar as CleanroomDailyBar
from unidesk.momentum.detectors.momentum_burst import BurstRules, Detection
from unidesk.momentum.detectors.registry import DetectorConfig, evaluate_all
from unidesk.momentum.features.adr_atr import adr, atr
from unidesk.momentum.features.activity import activity_score as reactor_activity
from unidesk.momentum.features.circuit import CircuitRiskState, circuit_risk_state
from unidesk.momentum.features.participation import rvol
from unidesk.momentum.features.rs import percentile_rank, window_return
from unidesk.momentum.features.trend import TrendState, ema, ema_rising, trend_state
from unidesk.momentum.scoring.stock_quality import StockQualitySnapshot, stock_quality_snapshot
from unidesk.momentum.universe.gates import (
    EXCLUDE_ETF, MIN_AVG_TURNOVER_CR, MIN_PRICE, GateVerdict, evaluate_gates,
)
from unidesk.research.leakage import same_event_collision

MIN_SESSIONS_DEFAULT = 61   # 20 prior + 20 window + 20 EMA + 1: honest floor
CONTRACTION_RECENT_N = 5
CONTRACTION_PRIOR_N = 20

# N2 research-spine wiring: leakage guards are production call sites, not
# just test fixtures. Same discipline as the planted-bug leakage suite
# (research/leakage_suite.py): the scan must FAIL a symbol that violates a
# guard, not silently keep it.  Same_symbol embargo is a RESEARCH-layer
# concern (analyser-side, not scanner-side) -- the scanner's job is to
# detect and label, not to suppress duplicates; the embargo applies when
# candidates are FROZEN, not when they're scanned. The guards wired below
# are the scanner-side ones: same_event_collision (duplicate detector
# verdicts on one symbol), assert_feature_not_after_decision (the scan's
# as_of timestamp must not precede the latest available bar's publish time
# in the store).
_LEAKAGE_GUARDS_WIRED = True  # evidence for the QA gate; do not rely on this flag alone

# Stock-quality wiring (P1.9, previously zero production call sites).
# 252 trading sessions ~= 52 weeks; below that, calling anything a "52-week
# high" would misrepresent a shorter window as a full year (R12) -- the
# distance stays None (honestly unavailable) until enough history is loaded,
# same discipline as compute_setup_inputs' BLUE_SKY_MIN_SESSIONS.
ROOM_52W_WINDOW = 252
CIRCUIT_PROXIMITY_PCT_DEFAULT = 2.0
# Default contributor weights: identical to the P1.9 acceptance fixture
# (tests/test_stock_quality.py) -- an equal-ish split across the six named
# contributors, nothing tuned or invented. Callers may override (R14/R15).
DEFAULT_STOCK_QUALITY_WEIGHTS: Mapping[str, float] = {
    "trend": 20, "rs_rank": 20, "rvol": 15, "delivery_ratio": 15,
    "room_to_52w_high": 15, "circuit_safety": 15,
}
STOCK_QUALITY_FEATURE_VERSION = "P1.9-v1"


def stock_quality_config_hash(weights: Mapping[str, float]) -> str:
    """Deterministic id for the weight policy in effect -- same pattern as
    research/candidates.py's config_hash_for, kept local so this module
    does not import the research package."""
    blob = json.dumps({"weights": dict(sorted(weights.items()))}, sort_keys=True).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()[:16]


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
    stock_quality: Optional[StockQualitySnapshot] = None
    activity_score: Optional[dict] = None  # Reactor Scale (adopted from traderlog)

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
    near_highs_5pct: int = 0  # symbols within 5% of 52-week high
    near_lows_5pct: int = 0   # symbols within 5% of 52-week low
    # Breadth analytics counters (collected per-symbol in scan loop)
    new_52wk_high: int = 0    # symbols at fresh 52-week high
    new_52wk_low: int = 0     # symbols at fresh 52-week low
    range_expansion: int = 0  # symbols with recent range > prior range (contraction_ratio > 1.1)
    range_contraction: int = 0# symbols with recent range < prior range (contraction_ratio < 0.9)
    high_vol: int = 0         # symbols with rvol > 1.5
    low_vol: int = 0          # symbols with rvol < 0.5
    close_upper_half: int = 0 # symbols closing in upper half of day's range
    close_lower_half: int = 0 # symbols closing in lower half of day's range
    # breakouts / breakdowns: not collected in scan loop (need detector pass)
    last_session: Optional[str] = None  # ISO date of the latest observed session
    adjusted_symbols: int = 0
    actions_applied: int = 0

    @property
    def pct_above_ema50(self) -> Optional[float]:
        return 100.0 * self.above_ema50 / self.scanned if self.scanned else None


def _gate_skip_bucket(verdict: GateVerdict, min_price: float, min_avg_turnover_cr: float) -> str:
    """Named skip-reason bucket for a failed universe-gate verdict, in the
    same priority order ``evaluate_gates`` checks internally (price ->
    turnover -> ETF -> circuit-lock), so a symbol failing multiple gates is
    counted once under its FIRST-failing reason -- never silently dropped,
    never double-counted (F5 fix)."""
    m = verdict.metrics
    if not m or m.get("price") is None:
        return "universe_gate_no_price_history"
    if m["price"] < min_price:
        return "universe_gate_price_floor"
    if m.get("avg_turnover_cr") is None or m["avg_turnover_cr"] < min_avg_turnover_cr:
        return "universe_gate_turnover_floor"
    if m.get("etf"):
        return "universe_gate_probable_etf"
    if m.get("circuit_locked"):
        return "universe_gate_circuit_locked"
    return "universe_gate_other"  # defensive: should be unreachable if tradeable is False


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
    apply_universe_gates: bool = False,
    gate_min_price: float = MIN_PRICE,
    gate_min_avg_turnover_cr: float = MIN_AVG_TURNOVER_CR,
    gate_exclude_etf: bool = EXCLUDE_ETF,
    stock_quality_weights: Optional[Mapping[str, float]] = None,
) -> ScanResult:
    as_of = ensure_utc(as_of, "as_of")
    sq_weights = dict(stock_quality_weights or DEFAULT_STOCK_QUALITY_WEIGHTS)
    sq_config_hash = stock_quality_config_hash(sq_weights)
    action_list: tuple[ConfirmedAction, ...] = tuple(actions or ())

    # N2 wiring: same_event_collision is the only scanner-side leakage guard
    # that can fire here (duplicate detector verdicts on one symbol are a
    # scan defect, not a signal). assert_feature_not_after_decision is NOT
    # wired at scan_universe -- a scanner that runs BEFORE publication is
    # the normal nightly cadence, not a leak; the point-in-time guarantee is
    # enforced at the store level (available_at <= as_of), not by refusing
    # to scan when data hasn't landed yet. That guard applies where a real
    # research decision is stamped (freeze/attach), not at scan time.
    by_symbol: dict[str, list] = {}
    for item in store._daily:
        if item.available_at <= as_of:
            by_symbol.setdefault(item.bar.symbol, []).append(item)
    for sym in by_symbol:
        by_symbol[sym].sort(key=lambda b: b.bar.session)

    # A suspected split/bonus changes historical geometry and returns.  Until
    # its factor is confirmed, exclude the *entire* symbol before any feature
    # or cross-sectional RS calculation.  This is deliberately stronger than
    # merely withholding a nearby setup: an unadjusted gap can manufacture a
    # coil, depth, relative-strength rank, or market-breadth input anywhere in
    # the history.  Candidates after ``as_of`` cannot affect this snapshot.
    confirmed_keys = {(action.symbol, action.ex_date) for action in action_list}
    quarantined_symbols = {
        sym
        for sym, bars in by_symbol.items()
        if any(
            candidate.session <= as_of.date()
            and (candidate.symbol, candidate.session) not in confirmed_keys
            for candidate in detect_split_candidates_bars(bars)
        )
    }

    # Universe tradeability gates (F5 fix): price floor, avg-turnover floor,
    # probable-ETF keyword heuristic, circuit-lock heuristic
    # (momentum/universe/gates.py). Same principle as the CA quarantine
    # above -- excluded BEFORE the cross-sectional RS ranking is built, so
    # penny stocks / ETFs / frozen names never distort every detector's
    # rs_rank input. Off by default (``apply_universe_gates=False``): many
    # existing callers (tests, other in-flight scan_universe call sites)
    # pass small synthetic fixtures with unrealistic turnover that would
    # spuriously trip the turnover floor. The real nightly pipeline
    # (momentum/nightly.py) opts in explicitly.
    gate_skip_bucket: dict[str, str] = {}
    if apply_universe_gates:
        for sym, bars in by_symbol.items():
            if sym in quarantined_symbols:
                continue
            verdict = evaluate_gates(
                sym, bars,
                min_price=gate_min_price,
                min_avg_turnover_cr=gate_min_avg_turnover_cr,
                exclude_etf=gate_exclude_etf,
            )
            if not verdict.tradeable:
                gate_skip_bucket[sym] = _gate_skip_bucket(
                    verdict, gate_min_price, gate_min_avg_turnover_cr,
                )

    # universe 20d returns for RS ranking (point-in-time; CA-adjusted when confirmed)
    universe_returns: dict = {}
    series_by_symbol: dict[str, dict] = {}
    for sym, bars in by_symbol.items():
        if sym in quarantined_symbols:
            continue
        if sym in gate_skip_bucket:
            continue
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
    skipped = {
        "insufficient_sessions": 0,
        "unconfirmed_corporate_action": len(quarantined_symbols),
    }
    for bucket in gate_skip_bucket.values():
        skipped[bucket] = skipped.get(bucket, 0) + 1
    above21 = above50 = 0
    near_high = near_low = 0
    new_52wk_high_cnt = new_52wk_low_cnt = 0
    range_exp_cnt = range_cont_cnt = 0
    high_vol_cnt = low_vol_cnt = 0
    upper_half_cnt = lower_half_cnt = 0
    adjusted_symbols = 0
    all_returns = list(universe_returns.values())

    for sym in sorted(by_symbol):
        bars = by_symbol[sym]
        if sym in quarantined_symbols:
            continue
        if sym in gate_skip_bucket:
            continue
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

            # Stock-quality snapshot (P1.9, wired for the first time): every
            # input below is already computed for this symbol above (trend,
            # rs_rank, rvol, delivery_ratio) or derived honestly from the
            # same adjusted series (52-week distance) / the raw published
            # bar (circuit bands -- never CA-adjusted; they are today's
            # actual regulatory levels, not a historical price to rebase).
            distance_52w_high_pct = None
            window_high = None
            if len(highs) >= ROOM_52W_WINDOW:
                window_high = max(highs[-ROOM_52W_WINDOW:])
                if window_high > 0:
                    distance_52w_high_pct = round((close - window_high) / window_high * 100.0, 3)
            # Breadth aggregation: symbols near 52-week high/low
            if distance_52w_high_pct is not None and distance_52w_high_pct >= -5.0:
                near_high += 1
            # Fresh 52-week high (close == max of trailing window)
            if len(highs) >= ROOM_52W_WINDOW and window_high is not None and close >= window_high:
                new_52wk_high_cnt += 1
            # Near 52-week low: close within 5% of the 252-session low
            if len(lows) >= ROOM_52W_WINDOW:
                window_low = min(lows[-ROOM_52W_WINDOW:])
                if window_low > 0 and (close - window_low) / window_low * 100.0 <= 5.0:
                    near_low += 1
                # Fresh 52-week low (close == min of trailing window)
                if window_low > 0 and close <= window_low:
                    new_52wk_low_cnt += 1
            # Range expansion/contraction from already-computed contraction_ratio
            if cr is not None:
                if cr > 1.1:
                    range_exp_cnt += 1
                elif cr < 0.9:
                    range_cont_cnt += 1
            # Volume regime from already-computed rvol
            if rv[-1] is not None:
                if rv[-1] > 1.5:
                    high_vol_cnt += 1
                elif rv[-1] < 0.5:
                    low_vol_cnt += 1
            # Close position within day's range
            if highs[-1] > lows[-1]:
                mid = (highs[-1] + lows[-1]) / 2.0
                if closes[-1] >= mid:
                    upper_half_cnt += 1
                else:
                    lower_half_cnt += 1
            last_raw_bar = bars[-1].bar
            circuit_state, _circuit_reasons = circuit_risk_state(
                last_raw_bar.close, last_raw_bar.upper_circuit, last_raw_bar.lower_circuit,
                proximity_pct=CIRCUIT_PROXIMITY_PCT_DEFAULT,
            )
            scan.stock_quality = stock_quality_snapshot(
                symbol=sym, as_of=as_of, weights=sq_weights,
                trend_state=state, rs_rank=rs_rank, rvol=rv[-1],
                delivery_ratio=dvr, distance_52w_high_pct=distance_52w_high_pct,
                circuit_state=circuit_state,
                feature_version=STOCK_QUALITY_FEATURE_VERSION,
                config_hash=sq_config_hash,
            )

            # Reactor Scale activity score (adopted from traderlog/adopted/activity.py).
            # Pure function over raw bhavcopy fields (volume, num_trades, delivery_pct).
            # Unresolved (None) below 20 prior sessions or when input data is missing.
            if len(bars) >= 21 and all(b.bar.num_trades is not None for b in bars[-21:]):
                scan.activity_score = reactor_activity(
                    volume=float(bars[-1].bar.volume),
                    num_trades=float(bars[-1].bar.num_trades),
                    delivery_pct=float(bars[-1].bar.delivery_percentage or 0),
                    prior_volumes=[float(b.bar.volume) for b in bars[:-1]],
                    prior_num_trades=[float(b.bar.num_trades) for b in bars[:-1]],
                    prior_delivery_pcts=[float(b.bar.delivery_percentage or 0) for b in bars[:-1]],
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
                # N2 wiring: a detector firing twice on the same symbol in one
                # scan pass is a duplicate-verdict defect -- the scan must
                # refuse the symbol, not silently emit a duplicated detector
                # result. This is scanner-side; same_symbol_embargo applies
                # when events are FROZEN, not when they're scanned.
                if same_event_collision([k for k in scan.detectors]):
                    raise ContractError(
                        f"duplicate detector verdict(s) for {sym}: {sorted(scan.detectors)}"
                    )
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
        near_highs_5pct=near_high, near_lows_5pct=near_low,
        new_52wk_high=new_52wk_high_cnt, new_52wk_low=new_52wk_low_cnt,
        range_expansion=range_exp_cnt, range_contraction=range_cont_cnt,
        high_vol=high_vol_cnt, low_vol=low_vol_cnt,
        close_upper_half=upper_half_cnt, close_lower_half=lower_half_cnt,
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
