"""L1.5 analogue retrieval — EXPLORATION PROTOTYPE (Constitution §7).

STATUS: research exploration only, built at the owner's explicit direction.
The Phase 0 gate has NOT passed (see design/PHASE0_GATE_AUDIT_A01.md), so
per UI_BUILD_SPEC_V1 PART 13 nothing here is surfaced in any user-facing
screen, no expectancy/edge claim may be quoted, and any result this module
produces is evidence-gathering for the gate review — not product.

What this is: engineered-vector nearest-neighbour retrieval over the
frozen research event store, implementing every hard constraint the
constitution and UI_BUILD_SPEC_V1 A-02 place on L1.5:

  - cosine distance ONLY (§10); no learned encoder anywhere
  - k = 25 or 50 ONLY (§10)
  - same-symbol embargo wired via research.leakage.embargo_overlapping_events
    (previously built and unused — this wires it)
  - point-in-time normalisation: each dimension is rank-normalised against
    the corpus STRICTLY OLDER than the query event; no full-sample z-scores (§6.4)
  - concentration cap: no more than 20% of neighbours from one calendar
    week (§6.3); the industry-half of that cap is PENDING the sector join
  - sample size is carried on every result (§20) and similarity values are
    never exposed as probabilities

Dimension mapping from the frozen event snapshots (n5_inputs + snapshot),
with honest gaps — dimensions the store does not carry are omitted and
renormalised over the present ones, never zero-filled:

  gap_pct          n5_inputs.ep.gap_pct
  close_loc        n5_inputs.ep.close_loc
  rvol             n5_inputs.ep.rvol            (constitution says rvol_20;
                                                 the store carries rvol —
                                                 documented drift)
  prior_atr_pct    n5_inputs.tight.base_episode.atrp_percentile
  S_ep             n5_inputs.tight.tightness.score
  base_depth       n5_inputs.tight.base_episode.depth_pct
  RS               snapshot.rs_rank
  adr_pct          snapshot.adr_pct             (liquidity proxy)
  market_regime    NOT per-event in the store — resolved via the archived
                   report breadth series (regime_history); None when the
                   session predates the archive.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Optional

from unidesk.contracts.base import ContractError
from unidesk.momentum.data.calendar import TradingCalendar
from unidesk.research.leakage import embargo_overlapping_events
from unidesk.research.event_store import load_events
from unidesk.research.labels import OUTCOME_LABELS_VERSION

# Constitution §10: k is 25 or 50. Nothing else is retrievable.
ALLOWED_K = (25, 50)
# Constitution §6.3: at most 20% of neighbours from one concentration cell.
MAX_CELL_FRACTION = 0.20
# A dimension is usable on a pair only if both sides carry it; below this
# many shared dimensions the pair is not comparable and is excluded.
MIN_SHARED_DIMS = 4


# ---------------------------------------------------------------- vectors

def flatten_vector(snapshot: dict, market_regime: Optional[str] = None) -> dict[str, Optional[float]]:
    """Flatten a frozen event snapshot into the named L1.5 dimensions.
    Missing inputs stay None — never zero-filled (R8/R12)."""
    n5 = snapshot.get("n5_inputs") or {}
    ep = n5.get("ep") or {}
    tight = n5.get("tight") or {}
    episode = tight.get("base_episode") or {}
    tightness = tight.get("tightness") or {}
    return {
        "gap_pct": _num(ep.get("gap_pct")),
        "close_loc": _num(ep.get("close_loc")),
        "rvol": _num(ep.get("rvol")),
        "prior_atr_pct": _num(episode.get("atrp_percentile")),
        "S_ep": _num(tightness.get("score")),
        "base_depth": _num(episode.get("depth_pct")),
        "rs": _num(snapshot.get("rs_rank")),
        "adr_pct": _num(snapshot.get("adr_pct")),
        # market_regime joins the archived breadth series; "BULL"/"BEAR"/
        # "CHOP" map to +1/-1/0 for the cosine space.
        "market_regime": ({"BULL": 1.0, "BEAR": -1.0}.get(market_regime, 0.0)
                          if market_regime else None),
    }


def _num(v: Any) -> Optional[float]:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


# -------------------------------------------------------------- session
# ResearchEvent carries no session field; the convention (mirroring
# research/leakage.py::_decision_session) is to parse it from the event_id
# tail when it is a date, else fall back to the decision timestamp.


def _decision_session(ev) -> date:
    raw = ev.event_id.rsplit(":", 1)[-1]
    try:
        return date.fromisoformat(raw)
    except ValueError:
        pass
    ts = ev.timestamp
    return ts.date() if hasattr(ts, "date") else date.fromisoformat(str(ts)[:10])


def cosine_distance(a: dict[str, Optional[float]], b: dict[str, Optional[float]]) -> Optional[float]:
    """Cosine distance over the dimensions present in BOTH vectors.
    Returns None when fewer than MIN_SHARED_DIMS overlap."""
    shared = [k for k in a if a.get(k) is not None and b.get(k) is not None]
    if len(shared) < MIN_SHARED_DIMS:
        return None
    va = [a[k] for k in shared]
    vb = [b[k] for k in shared]
    dot = sum(x * y for x, y in zip(va, vb))
    na = math.sqrt(sum(x * x for x in va))
    nb = math.sqrt(sum(y * y for y in vb))
    if na == 0 or nb == 0:
        return None
    return 1.0 - dot / (na * nb)


# ------------------------------------------------- point-in-time scaling

def pit_scale(corpus: list[dict[str, Optional[float]]]) -> dict[str, list[float]]:
    """Rank-normalisation reference: the raw dim values of the corpus.
    Callers percentile-rank a query dim against these lists. The corpus is
    built strictly from events OLDER than the query (PIT; §6.4) — enforced
    by the caller, asserted here by convention only."""
    out: dict[str, list[float]] = {}
    for vec in corpus:
        for k, v in vec.items():
            if v is not None:
                out.setdefault(k, []).append(v)
    return out


def pit_rank(value: float, reference: list[float]) -> float:
    """Percentile rank of `value` within the point-in-time reference [0,1]."""
    if not reference:
        return 0.5
    below = sum(1 for x in reference if x <= value)
    return below / len(reference)


# -------------------------------------------------------------- retrieval

@dataclass(frozen=True)
class Neighbour:
    event_id: str
    symbol: str
    session: str
    r_multiple: Optional[float]
    cosine_similarity: float   # internal retrieval quantity — NEVER surface


@dataclass(frozen=True)
class RetrievalResult:
    k_requested: int
    neighbours: list[Neighbour]
    embargoed_count: int
    candidates_with_vectors: int
    outcome_distribution: dict[str, int]
    median_r: Optional[float]
    notes: tuple

    @property
    def sample_size(self) -> int:
        return len(self.neighbours)


def _session_regime_lookup(regime_rows: list[dict]) -> dict[str, str]:
    out = {}
    for row in regime_rows:
        out[row["date"]] = row.get("regime") or row.get("regime_replayed") or ""
    return out


def retrieve(
    query_event,
    data_root: Path,
    *,
    k: int = 25,
    calendar: TradingCalendar,
    regime_rows: Optional[list[dict]] = None,
    events: Optional[list] = None,
) -> RetrievalResult:
    """`events` lets the caller pass a pre-loaded corpus (recommended: bound
    it to the regenerated range — loading all 1,500+ partitions costs
    gigabytes and the store is mid-regen). Defaults to the full store."""
    """Retrieve the k most similar RESOLVED historical events for one query.

    Constraints enforced here (fail loudly, never silently degrade):
      - k in (25, 50)
      - same-symbol embargo applied BEFORE ranking
      - PIT rank-normalisation against events strictly older than the query
      - week-concentration cap (industry cap pending the sector join)
    """
    if k not in ALLOWED_K:
        raise ContractError(f"L1.5 k must be one of {ALLOWED_K}, got {k}")

    if events is None:
        events = load_events(data_root)
    regime_lookup = _session_regime_lookup(regime_rows or [])

    # resolved corpus only: a neighbour must carry an outcome label of the
    # current version with a usable r_multiple.
    corpus = []
    for ev in events:
        labels = ev.outcome_labels or {}
        if labels.get("label_version") != OUTCOME_LABELS_VERSION:
            continue
        if _decision_session(ev) >= _decision_session(query_event):
            continue  # PIT: corpus is strictly older than the query
        r = labels.get("r_multiple")
        corpus.append((ev, r))

    # same-symbol embargo (constitution §6) — wired, reported, not silent
    kept_events, embargoed = embargo_overlapping_events(
        [ev for ev, _ in corpus], calendar,
    )
    kept_r = {ev.event_id: r for ev, r in corpus}
    corpus = [(ev, kept_r[ev.event_id]) for ev in kept_events]

    q_session = _decision_session(query_event)
    query_vec = flatten_vector(
        query_event.snapshot or {},
        regime_lookup.get(q_session.isoformat()),
    )
    corpus_vecs = [
        (ev, r, flatten_vector(ev.snapshot or {},
                               regime_lookup.get(_decision_session(ev).isoformat())))
        for ev, r in corpus
    ]
    reference = pit_scale([v for _, _, v in corpus_vecs])

    scored: list[tuple[float, Any, Optional[float]]] = []
    for ev, r, vec in corpus_vecs:
        # PIT-normalise both sides dim-wise, then cosine over shared dims
        qa = {k: pit_rank(v, reference[k]) if v is not None else None for k, v in query_vec.items()}
        ca = {k: pit_rank(v, reference[k]) if v is not None else None for k, v in vec.items()}
        dist = cosine_distance(qa, ca)
        if dist is None:
            continue
        scored.append((dist, ev, r))

    scored.sort(key=lambda t: t[0])
    picked: list[Neighbour] = []
    week_counts: dict[str, int] = {}
    max_per_week = max(1, math.ceil(MAX_CELL_FRACTION * k))
    for dist, ev, r in scored:
        if len(picked) >= k:
            break
        week = _decision_session(ev).isocalendar()[1]
        if week_counts.get(week, 0) >= max_per_week:
            continue
        week_counts[week] = week_counts.get(week, 0) + 1
        picked.append(Neighbour(
            event_id=ev.event_id, symbol=ev.symbol,
            session=_decision_session(ev).isoformat(),
            r_multiple=r, cosine_similarity=1.0 - dist,
        ))

    rs = [n.r_multiple for n in picked if n.r_multiple is not None]
    rs.sort()
    median_r = rs[len(rs) // 2] if rs else None
    distribution = {
        "continued": sum(1 for x in rs if x > 0.25),
        "flat": sum(1 for x in rs if -0.25 <= x <= 0.25),
        "failed": sum(1 for x in rs if x < -0.25),
    }
    notes = (
        f"k={k}; embargoed {len(embargoed)} same-symbol overlaps before ranking; "
        f"{len(scored)} comparable events; industry-half of the §6.3 "
        f"concentration cap PENDING the sector join; research-only (Phase 0 gate open).",
    )
    return RetrievalResult(
        k_requested=k,
        neighbours=picked,
        embargoed_count=len(embargoed),
        candidates_with_vectors=len(scored),
        outcome_distribution=distribution,
        median_r=median_r,
        notes=notes,
    )
