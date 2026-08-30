"""Experiment A/B verdict engine (build manual V2 N5; swing-edges spec §10.4,
§14 Experiments A & B).

Compares a candidate book against its pre-registered DUMB baseline on the
same sessions, net of costs, and emits the spec's verdict structure:
n, net expectancy per trade, profit factor, hold rate, and the pass/fail
gates. This module judges nothing by itself — the experiments it scores are
pre-registered in ``plan/SWING_EDGES_TECHNICAL_SPEC.md`` §12/§14 and its
kill criteria are the ones committed before testing (R-H).

A "book" is a list of trade outcomes sharing sessions: each trade is
(symbol, entry_session, net_bps). The baseline book must contain the SAME
sessions it was defined on — the runner aligns on entry session, comparing
like-for-like calendar exposure.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from unidesk.contracts.base import ContractError, require_float, require_str


@dataclass(frozen=True)
class Trade:
    symbol: str
    entry_session: str          # ISO date of the entry fill
    net_bps: float              # net-of-cost outcome for this book's rule


@dataclass(frozen=True)
class BookStats:
    n: int
    net_expectancy_bps: float   # mean net_bps per trade
    win_rate: float             # share of trades with net_bps > 0
    profit_factor: float        # gross wins / gross losses (net), inf-safe
    avg_win_bps: float
    avg_loss_bps: float


def book_stats(trades: Sequence[Trade]) -> BookStats:
    if not trades:
        raise ContractError("book_stats needs at least one trade")
    nets = [require_float(t.net_bps, "net_bps") for t in trades]
    wins = [n for n in nets if n > 0]
    losses = [n for n in nets if n <= 0]
    gross_win = sum(wins)
    gross_loss = abs(sum(losses))
    pf = float("inf") if gross_loss == 0 and gross_win > 0 else (
        float("inf") if gross_win == 0 and gross_loss == 0 else gross_win / gross_loss)
    return BookStats(
        n=len(nets),
        net_expectancy_bps=round(sum(nets) / len(nets), 4),
        win_rate=round(len(wins) / len(nets), 4),
        profit_factor=round(pf, 4) if pf != float("inf") else float("inf"),
        avg_win_bps=round(gross_win / len(wins), 4) if wins else 0.0,
        avg_loss_bps=round(sum(losses) / len(losses), 4) if losses else 0.0,
    )


@dataclass(frozen=True)
class EdgeVerdict:
    candidate_stats: BookStats
    baseline_stats: BookStats
    beats_baseline_net: bool
    verdict: str                # KEEP_CANDIDATE | BASELINE_WINS | INSUFFICIENT_N
    min_n: int
    notes: tuple


def compare_edge(
    candidate_book: Sequence[Trade],
    baseline_book: Sequence[Trade],
    *,
    label: str = "experiment",
    min_n: int = 30,
) -> EdgeVerdict:
    """Spec §10.4 gate: the candidate book is kept only if its NET expectancy
    beats the baseline's at adequate sample size (R-H/R-I). Both books must
    be defined by their own frozen rules; this function never merges them."""
    if not candidate_book or not baseline_book:
        raise ContractError("both books must be non-empty")
    cand = book_stats(candidate_book)
    base = book_stats(baseline_book)
    beats = cand.net_expectancy_bps > base.net_expectancy_bps
    n_ok = cand.n >= min_n
    if not n_ok:
        verdict = "INSUFFICIENT_N"
    elif beats:
        verdict = "KEEP_CANDIDATE"
    else:
        verdict = "BASELINE_WINS"
    notes = (f"{label}: candidate net {cand.net_expectancy_bps} bps/trade "
             f"vs baseline {base.net_expectancy_bps} bps/trade over "
             f"{cand.n}/{base.n} trades")
    return EdgeVerdict(candidate_stats=cand, baseline_stats=base,
                       beats_baseline_net=beats, verdict=verdict,
                       min_n=min_n, notes=(notes,))
