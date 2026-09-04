"""Immutable decision memory and strictly point-in-time analogue recall."""
from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from uuid import uuid4

from .schema import ensure_schema


def record_decision(conn, *, decision_time: str, symbol: str, decision: str,
                    evidence: dict, memory_id: str | None = None, **context) -> str:
    ensure_schema(conn)
    memory_id = memory_id or uuid4().hex
    conn.execute("""INSERT INTO decision_memories
      (memory_id,decision_time,symbol,decision,setup_family,regime,sector,theme,execution_lens,
       evidence_json,proposed_path_json,data_quality) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
      (memory_id, decision_time, symbol.upper(), decision, context.get("setup_family"),
       context.get("regime"), context.get("sector"), context.get("theme"),
       context.get("execution_lens"), json.dumps(evidence, sort_keys=True),
       json.dumps(context.get("proposed_path"), sort_keys=True) if context.get("proposed_path") is not None else None,
       context.get("data_quality")))
    conn.commit()
    return memory_id


def resolve_outcome(conn, *, memory_id: str, outcome_available_at: str, outcome: dict) -> None:
    """Append the one immutable resolution for a decision."""
    ensure_schema(conn)
    decision = conn.execute("SELECT decision_time FROM decision_memories WHERE memory_id=?", (memory_id,)).fetchone()
    if not decision:
        raise ValueError("unknown memory_id")
    if outcome_available_at < decision["decision_time"]:
        raise ValueError("outcome cannot predate decision")
    conn.execute("INSERT INTO decision_memory_outcomes(memory_id,outcome_available_at,outcome_json) VALUES(?,?,?)",
                 (memory_id, outcome_available_at, json.dumps(outcome, sort_keys=True)))
    conn.commit()


def _sigmoid(x: float) -> float:
    # numerically stable-ish
    if x >= 0:
        z = math.exp(-x)
        return 1.0 / (1.0 + z)
    z = math.exp(x)
    return z / (1.0 + z)


def _outcome_quality_Q(outcome: dict | None, *, pending_neutral: float = 0.5) -> tuple[float, str]:
    """Q = sigmoid(realized R-multiple). PENDING/missing → neutral shrunk Q."""
    if not outcome:
        return pending_neutral, "PENDING_OR_MISSING"
    status = str(outcome.get("status") or outcome.get("resolution") or "").upper()
    if status in {"PENDING", "UNRESOLVABLE"}:
        return pending_neutral, status or "PENDING"
    r_mult = outcome.get("r_multiple")
    if r_mult is None:
        r_mult = outcome.get("realized_r")
    if r_mult is None:
        return pending_neutral, "NO_R_MULTIPLE"
    try:
        q = _sigmoid(float(r_mult))
    except (TypeError, ValueError):
        return pending_neutral, "BAD_R"
    return q, "RESOLVED"


def _gaussian_sim(a: dict, b: dict, keys: list[str], sigma: float = 1.0) -> float:
    """Gaussian kernel over shared numeric evidence features; categorical exact-match."""
    if not keys:
        return 0.5
    parts = []
    for k in keys:
        va, vb = a.get(k), b.get(k)
        if va is None or vb is None:
            continue
        if isinstance(va, (int, float)) and isinstance(vb, (int, float)):
            parts.append(math.exp(-((float(va) - float(vb)) ** 2) / (2 * sigma * sigma)))
        else:
            parts.append(1.0 if va == vb else 0.0)
    return sum(parts) / len(parts) if parts else 0.5


def _parse_memory_time(value: str) -> datetime:
    """Parse legacy naive and current ISO timestamps onto one UTC timeline."""
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def recall_analogues(conn, *, as_of: str, symbol: str | None = None,
                     setup_family: str | None = None, regime: str | None = None,
                     sector: str | None = None, theme: str | None = None,
                     execution_lens: str | None = None, limit: int = 3,
                     query_features: dict | None = None,
                     proposed_direction: str | None = None) -> list[dict]:
    """Recall only decisions/outcomes visible by ``as_of``.

    Score = Q · Sim · Rec · Conf (multiplicative):
      Q   = sigmoid(R-multiple) or neutral for PENDING/UNRESOLVABLE
      Sim = Gaussian/categorical kernel over decision-time fields + query_features
      Rec = power-law decay on age in days: (1+days)^(-0.5)
      Conf = sample-size shrinkage n/(n+k) on local cohort size
    Also sets anti_resonance when top-k outcomes oppose proposed_direction.
    """
    ensure_schema(conn)
    rows = conn.execute("""SELECT d.*,r.outcome_available_at resolved_at,r.outcome_json resolved_outcome
      FROM decision_memories d LEFT JOIN decision_memory_outcomes r ON r.memory_id=d.memory_id
      WHERE d.decision_time < ? ORDER BY d.decision_time DESC""", (as_of,)).fetchall()
    query = {"symbol": symbol.upper() if symbol else None, "setup_family": setup_family,
             "regime": regime, "sector": sector, "theme": theme, "execution_lens": execution_lens}
    query_features = query_features or {}
    as_dt = _parse_memory_time(as_of)
    # Cohort size for Conf: count rows matching family+regime among visible
    cohort_n = sum(
        1 for row in rows
        if (setup_family is None or row["setup_family"] == setup_family)
        and (regime is None or row["regime"] == regime)
    )
    conf = cohort_n / (cohort_n + 10.0)  # shrinkage k=10

    scored = []
    for row in rows:
        fields = [k for k, v in query.items() if v is not None]
        cat_sim = sum(row[k] == query[k] for k in fields) / len(fields) if fields else 0.5
        evidence = json.loads(row["evidence_json"] or "{}")
        feat_sim = _gaussian_sim(evidence, query_features, list(query_features.keys())) if query_features else cat_sim
        similarity = 0.5 * cat_sim + 0.5 * feat_sim if query_features else cat_sim

        then = _parse_memory_time(row["decision_time"])
        days = max(0.0, (as_dt - then).total_seconds() / 86400)
        recency = (1.0 + days) ** (-0.5)  # power-law

        visible_outcome_raw = row["resolved_outcome"] if row["resolved_at"] and row["resolved_at"] <= as_of else None
        outcome = json.loads(visible_outcome_raw) if visible_outcome_raw else None
        q, q_label = _outcome_quality_Q(outcome)

        score = max(1e-12, q) * max(1e-12, similarity) * max(1e-12, recency) * max(1e-12, conf)
        item = dict(row)
        item["evidence"] = evidence
        item.pop("evidence_json", None)
        item.pop("outcome_json", None)
        item["outcome"] = outcome
        item.update({
            "Q": q, "Q_label": q_label,
            "similarity": similarity, "recency_weight": recency,
            "confidence_weight": conf, "cohort_n": cohort_n,
            "combined_score": score,
        })
        scored.append(item)

    top = sorted(scored, key=lambda x: (-x["combined_score"], x["memory_id"]))[:limit]

    # Anti-resonance: do top-k outcomes oppose proposed_direction?
    anti = {"active": False, "opposing": [], "note": None}
    if proposed_direction and top:
        want = proposed_direction.upper()
        opposing = []
        for it in top:
            oc = it.get("outcome") or {}
            direction = str(oc.get("direction") or oc.get("path_bias") or "").upper()
            r_mult = oc.get("r_multiple", oc.get("realized_r"))
            try:
                r_mult_f = float(r_mult) if r_mult is not None else None
            except (TypeError, ValueError):
                r_mult_f = None
            # TAKE long opposed by negative R; or explicit opposite direction label
            if want in {"LONG", "TAKE", "BULL"} and r_mult_f is not None and r_mult_f < 0:
                opposing.append(it["memory_id"])
            elif want in {"SHORT", "BEAR"} and r_mult_f is not None and r_mult_f > 0:
                opposing.append(it["memory_id"])
            elif direction and direction not in {want, ""} and direction in {"LONG", "SHORT", "BULL", "BEAR"}:
                opposing.append(it["memory_id"])
        if opposing:
            anti = {
                "active": True,
                "opposing": opposing,
                "note": "top-k analogues' outcomes oppose proposed direction — strongest contradiction",
            }
    for it in top:
        it["anti_resonance"] = anti
    return top
