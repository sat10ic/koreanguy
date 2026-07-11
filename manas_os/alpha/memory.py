"""Immutable decision memory and strictly point-in-time analogue recall."""
from __future__ import annotations

import json
import math
from datetime import datetime
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


def recall_analogues(conn, *, as_of: str, symbol: str | None = None,
                     setup_family: str | None = None, regime: str | None = None,
                     sector: str | None = None, theme: str | None = None,
                     execution_lens: str | None = None, limit: int = 3) -> list[dict]:
    """Recall only decisions and resolved outcomes that existed by ``as_of``."""
    ensure_schema(conn)
    rows = conn.execute("""SELECT d.*,r.outcome_available_at resolved_at,r.outcome_json resolved_outcome
      FROM decision_memories d LEFT JOIN decision_memory_outcomes r ON r.memory_id=d.memory_id
      WHERE d.decision_time < ? ORDER BY d.decision_time DESC""", (as_of,)).fetchall()
    query = {"symbol": symbol.upper() if symbol else None, "setup_family": setup_family,
             "regime": regime, "sector": sector, "theme": theme, "execution_lens": execution_lens}
    as_dt = datetime.fromisoformat(as_of.replace("Z", "+00:00"))
    scored = []
    for row in rows:
        fields = [k for k, v in query.items() if v is not None]
        similarity = sum(row[k] == query[k] for k in fields) / len(fields) if fields else 0.5
        then = datetime.fromisoformat(row["decision_time"].replace("Z", "+00:00"))
        days = max(0.0, (as_dt - then).total_seconds() / 86400)
        recency = math.exp(-days / 180.0)
        quality = float(row["data_quality"] if row["data_quality"] is not None else 0.5)
        visible_outcome = row["resolved_outcome"] if row["resolved_at"] and row["resolved_at"] <= as_of else None
        outcome_weight = 1.0 if visible_outcome else 0.7
        score = similarity * 0.6 + recency * 0.2 + quality * 0.1 + outcome_weight * 0.1
        item = dict(row); item["evidence"] = json.loads(item.pop("evidence_json"));
        item.pop("outcome_json", None)
        item["outcome"] = json.loads(visible_outcome) if visible_outcome else None
        item.update({"similarity": similarity, "recency_weight": recency,
                     "quality_weight": quality, "outcome_weight": outcome_weight,
                     "combined_score": score})
        scored.append(item)
    return sorted(scored, key=lambda x: (-x["combined_score"], x["memory_id"]))[:limit]
