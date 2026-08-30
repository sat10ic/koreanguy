"""Corporate-action adjustment (build manual V2, wave N3; rule R-A).

Honest v1, two halves:

1. **Detection proposes.** A bar-shape heuristic flags candidate splits —
   a large overnight gap down with sustained repricing and continued volume,
   where the implied factor is close to a clean fraction (1/2, 1/5, 1/10).
   Candidates go to a REVIEW QUEUE. Detection never auto-adjusts: a wrong
   back-adjustment silently corrupts every historical feature (the manual's
   own warning), so a confirmed actions table is required for application.
   Announcement text (Chartsmaze dumps) corroborates record dates but does
   NOT carry ratios — an announcement alone is not a confirmed factor.
2. **Adjustment applies.** ``adjust_series`` takes a CONFIRMED action list
   (symbol, ex-date, factor = old/new) and returns the back-adjusted OHLC
   and volume series (bars strictly before the ex-date are multiplied by
   the factor). Raw series are preserved by the caller; adjusted is a
   derived view.
"""
from __future__ import annotations

import csv
import hashlib
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Optional, Sequence

from unidesk.contracts.base import ContractError, require_float, require_str

DEFAULT_CONFIRMED_CSV = (
    Path(__file__).resolve().parents[2] / "config" / "confirmed_actions.csv"
)
ADJUSTED_VERSION = "ca-adjusted-v1"


def confirmed_actions_content_hash(path: Optional[Path] = None) -> str:
    """SHA-256 (first 16 hex chars) of the confirmed-actions CSV's actual
    BYTES -- not its path or mtime (directive-1c/d). Two scans run against
    different confirmed-actions content must never collapse to the same
    adjustment-basis hash; a missing file hashes the empty string, which is
    itself a distinct, stable basis (never silently equal to "some content")."""
    csv_path = Path(path or DEFAULT_CONFIRMED_CSV)
    content = csv_path.read_bytes() if csv_path.exists() else b""
    return hashlib.sha256(content).hexdigest()[:16]

CLEAN_FACTORS = (1.0, 1 / 2, 1 / 5, 1 / 10, 2 / 5, 4 / 5, 2 / 3, 1 / 4)


@dataclass(frozen=True)
class ConfirmedAction:
    symbol: str
    ex_date: date
    factor: float          # old/new price ratio, applied to bars BEFORE ex-date
    source: str            # e.g. "confirmed feed" / "review queue (human-confirmed)"


@dataclass(frozen=True)
class SplitCandidate:
    symbol: str
    session: date          # the gap day
    prev_close: float
    open: float
    implied_factor: float  # open / prev_close
    nearest_clean: float
    clean_distance_pct: float
    gap_index: Optional[int] = None  # index ``i`` into the input series that
    # produced this candidate (the gap day). Carried out of
    # ``detect_split_candidates`` so ``detect_split_candidates_bars`` can
    # re-locate the correct bar directly, instead of re-deriving it by
    # value via ``closes.index(cand.prev_close)`` -- which silently returns
    # the FIRST matching close on flat/repeating pre-gap prices (common in
    # illiquid names) and mis-dates the candidate. Defaults to None so
    # existing ``SplitCandidate(...)`` construction elsewhere is unaffected.


def detect_split_candidates(
    closes: Sequence[float],
    opens: Sequence[float],
    volumes: Sequence[float],
    *,
    min_gap_pct: float = 20.0,
    clean_tolerance_pct: float = 3.0,
    min_post_volume: float = 0.1,
) -> list[SplitCandidate]:
    """Flag candidate split sessions. All series chronological; index ``i``
    is the gap day (compared against ``i-1``). A candidate needs:
    open[i] <= close[i-1] * (1 - min_gap_pct/100), continued volume at least
    ``min_post_volume`` × the prior day (a real session traded), and an
    implied factor within ``clean_tolerance_pct`` of a clean fraction.
    Deliberately conservative: it prefers misses over false adjustments."""
    if not (len(closes) == len(opens) == len(volumes)):
        raise ContractError("closes, opens, volumes must have equal length")
    out: list[SplitCandidate] = []
    for i in range(1, len(closes)):
        prev_close = require_float(closes[i - 1], f"closes[{i-1}]")
        open_ = require_float(opens[i], f"opens[{i}]")
        vol_i = require_float(volumes[i], f"volumes[{i}]")
        vol_prev = require_float(volumes[i - 1], f"volumes[{i-1}]")
        if prev_close <= 0 or open_ <= 0:
            continue
        gap = (open_ / prev_close - 1.0) * 100.0
        if gap > -min_gap_pct:
            continue
        if vol_prev > 0 and vol_i < vol_prev * min_post_volume:
            continue
        implied = open_ / prev_close
        nearest = min(CLEAN_FACTORS, key=lambda f: abs(f - implied))
        distance = abs(nearest - implied) / nearest * 100.0
        if distance <= clean_tolerance_pct:
            out.append(SplitCandidate(
                symbol="", session=date(1970, 1, 1),
                prev_close=prev_close, open=open_,
                implied_factor=round(implied, 6),
                nearest_clean=nearest,
                clean_distance_pct=round(distance, 3),
                gap_index=i,
            ))
    return out


def detect_split_candidates_bars(bars, *, min_gap_pct: float = 20.0,
                                 clean_tolerance_pct: float = 3.0,
                                 min_post_volume: float = 0.1) -> list[SplitCandidate]:
    """Convenience wrapper over a chronological VersionedDailyBar list for
    ONE symbol (attribute access)."""
    closes = [b.bar.close for b in bars]
    opens = [b.bar.open for b in bars]
    volumes = [b.bar.volume for b in bars]
    found = detect_split_candidates(closes, opens, volumes,
                                    min_gap_pct=min_gap_pct,
                                    clean_tolerance_pct=clean_tolerance_pct,
                                    min_post_volume=min_post_volume)
    out = []
    for cand in found:
        # Use the gap-day index carried out of the detector directly --
        # NOT closes.index(cand.prev_close), which returns the FIRST bar
        # matching that close value and mis-dates the candidate whenever
        # pre-gap closes are flat or repeat (common in illiquid names).
        idx = cand.gap_index
        session = bars[idx].bar.session
        out.append(SplitCandidate(
            symbol=bars[idx].bar.symbol, session=session,
            prev_close=cand.prev_close, open=cand.open,
            implied_factor=cand.implied_factor,
            nearest_clean=cand.nearest_clean,
            clean_distance_pct=cand.clean_distance_pct,
            gap_index=idx,
        ))
    return out


def adjust_series(
    values: Sequence[float],
    sessions: Sequence[date],
    symbol: str,
    actions: Sequence[ConfirmedAction],
) -> list[float]:
    """Back-adjust a series for confirmed splits/bonuses of ONE symbol.

    For each action (sorted by ex_date descending), every bar STRICTLY
    BEFORE the ex-date is multiplied by that action's factor. Multiple
    actions compound correctly. Volume should be divided by the same
    factor by the caller (``adjust_volume``) — prices and volumes adjust
    in opposite directions."""
    if len(values) != len(sessions):
        raise ContractError("values and sessions must have equal length")
    mine = sorted(
        (a for a in actions if a.symbol == symbol),
        key=lambda a: a.ex_date, reverse=True,
    )
    out = []
    for v, s in zip(values, sessions):
        factor = 1.0
        for a in mine:
            if s < a.ex_date:
                factor *= a.factor
        out.append(require_float(v, "values[]") * factor)
    return out


def adjust_volume(volumes: Sequence[float], sessions: Sequence[date],
                  symbol: str, actions: Sequence[ConfirmedAction]) -> list[float]:
    """Volume adjusts inversely to price: pre-split bars divide by factor."""
    if len(volumes) != len(sessions):
        raise ContractError("volumes and sessions must have equal length")
    mine = sorted((a for a in actions if a.symbol == symbol),
                  key=lambda a: a.ex_date, reverse=True)
    out = []
    for v, s in zip(volumes, sessions):
        v = require_float(v, "volumes[]")
        factor = 1.0
        for a in mine:
            if s < a.ex_date:
                factor *= a.factor
        out.append(v / factor if factor > 0 else v)
    return out


def load_confirmed_actions(path: Optional[Path] = None) -> list[ConfirmedAction]:
    """Load the confirmed-actions table. Missing file → empty (scan stays raw)."""
    csv_path = Path(path or DEFAULT_CONFIRMED_CSV)
    if not csv_path.exists():
        return []
    out: list[ConfirmedAction] = []
    with open(csv_path, "r", encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            symbol = require_str((row.get("symbol") or "").strip().upper(), "symbol")
            raw_date = (row.get("ex_date") or "").strip()
            try:
                ex_date = datetime.strptime(raw_date, "%Y-%m-%d").date()
            except ValueError as exc:
                raise ContractError(f"{symbol}: bad ex_date {raw_date!r}") from exc
            try:
                factor = require_float(float((row.get("factor") or "").strip()), "factor")
            except (TypeError, ValueError) as exc:
                raise ContractError(
                    f"{symbol}: factor must be a number, got {row.get('factor')!r}"
                ) from exc
            source = require_str((row.get("source") or "").strip(), "source")
            if factor <= 0:
                raise ContractError(f"{symbol}: factor must be > 0")
            out.append(ConfirmedAction(symbol, ex_date, factor, source))
    return out


def persist_confirmed_actions(actions: Sequence[ConfirmedAction], path: Path) -> Path:
    """Write the confirmed table as parquet (research copy). Raw CSV stays the seed."""
    import pyarrow as pa
    import pyarrow.parquet as pq

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = [
        {
            "symbol": a.symbol,
            "ex_date": a.ex_date.isoformat(),
            "factor": a.factor,
            "source": a.source,
        }
        for a in actions
    ]
    schema = pa.schema([
        ("symbol", pa.string()),
        ("ex_date", pa.string()),
        ("factor", pa.float64()),
        ("source", pa.string()),
    ])
    pq.write_table(pa.Table.from_pylist(rows, schema=schema), path)
    return path


def actions_for_symbol(actions: Sequence[ConfirmedAction], symbol: str) -> tuple[ConfirmedAction, ...]:
    return tuple(a for a in actions if a.symbol == symbol)


def adjust_ohlcv(
    *,
    opens: Sequence[float],
    highs: Sequence[float],
    lows: Sequence[float],
    closes: Sequence[float],
    volumes: Sequence[float],
    sessions: Sequence[date],
    symbol: str,
    actions: Sequence[ConfirmedAction],
) -> dict:
    """Derived OHLC+volume for one symbol. Raw lists are not mutated."""
    mine = actions_for_symbol(actions, symbol)
    if not mine:
        return {
            "open": list(opens),
            "high": list(highs),
            "low": list(lows),
            "close": list(closes),
            "volume": list(volumes),
            "adjusted": False,
        }
    return {
        "open": adjust_series(opens, sessions, symbol, mine),
        "high": adjust_series(highs, sessions, symbol, mine),
        "low": adjust_series(lows, sessions, symbol, mine),
        "close": adjust_series(closes, sessions, symbol, mine),
        "volume": adjust_volume(volumes, sessions, symbol, mine),
        "adjusted": True,
    }
