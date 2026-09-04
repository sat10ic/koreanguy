# VISION BACKFILL SPEC — standing post-classify pass

**Status:** standing procedure, owner-directed 2026-08-25. Executor: the
`gemini-3.7-flash` vision-capable session (proven: 531 direct reads this corpus,
0 validator rejections). This stage exists because classification *grows* the
vision target set — labeling a post `trade_event`/`education` pulls its media
into vision scope — so every classify wave leaves a measurable vision debt.

---

## 1. Trigger

Run this stage whenever a classification wave completes (provider batch, agentic
in-chat run, or manual backfill) AND the scope query below returns > 0 rows.
Also run when new captures are imported and classified.

## 2. Scope (the only source of truth)

```sql
SELECT m.post_id, m.idx, m.local_path, c.kind
  FROM post_media m
  JOIN post_class c ON c.post_id = m.post_id
 WHERE m.is_mock=0
   AND c.kind IN ('trade_event','education')
   AND (m.vision_json IS NULL OR m.vision_json='')
 ORDER BY c.kind DESC, m.post_id, m.idx
```

Measured history of this backlog: 476 → 39 → 565 (scope grows by design).
Re-measure before each tranche; never trust a stale count.

## 3. Executor + write path

- Executor: **a genuinely vision-capable session** (currently `gemini-3.7-flash`).
  Gate rule: one real image read confirming pixels received; if output shows
  *"[image omitted because this model accepts text only]"* or any refusal —
  STOP. A text-only model must never write here (fabrication precedent:
  10 reverted rows, 2026-08-24).
- Write path (sole writer): `apply_verified_vision(conn, post_id, idx, payload,
  source=LABEL)` from `llm/vision.py`.
- Standing label: `gemini-3.7-flash (direct vision read, 2026-08-24)` — keep the
  whole direct-vision set under ONE attributable identity. A new executor model
  uses its own documented id + `(direct vision read, <date>)`.
- Backup before first write per pass:
  `traderlog/data/traderlog.db.backup-pre-vision-<date>`.

## 4. Fidelity rules (CONTRACTS §2 — unchanged)

- Transcribe only what is visibly written; `unreadable: true` ⇒ empty arrays.
- `annotated_levels[]`: price + visual justification, both required.
- Index/study/book/comparison charts → `chart_symbol: null`, `image_kind`
  `"chart"` only for literal tradeable charts, else `"other"`.
- Chart-vs-post-text contradictions: copy the chart faithfully; reconciler weighs.
- Never infer a number not written on the image.

## 5. Verification protocol (every pass, no exceptions)

1. **Self-audit** — every ~25 rows re-open 5; stored JSON must match pixels.
2. **Prior-work re-audit** — ≥49 previously-written own rows (every 10th, or 40
   random + 10 lowest-confidence); correct mismatches; report counts.
3. **Fresh-context adversarial diff** — 10 rows (new + prior mix) independently
   transcribed by a separate memoryless model; material disagreements fixed and
   reported.

## 6. Coordination

- Concurrent classify/reconcile agents are safe: different tables, idempotent
  writers keyed per row. Re-measure scope each tranche.
- Do NOT touch positions/review_queue/post_class during this pass.
- $0 cost expected — the executor IS the model; no provider calls.

## 7. Done-test + bookkeeping

- Scope query returns 0, OR remaining rows carry per-row reasons (e.g. unreadable).
- `run_checks.py` exit 0; full pytest green.
- Report: rows written, image_kind distribution, levels/unreadable counts,
  audit findings + corrections, spend ($0), exact model id + label.
- Append ADDENDA to `design/AUDIT_LEDGER.md`; update TASKS.md recon-wave item;
  MODEL_WORK_LOG record with your attribution.

## 8. Retirement condition (future automation)

This manual stage retires when `llm/provider.py`'s `vision` tier has a working,
rate-viable backend and a batch orchestration over `vision_pass()` exists
(TASKS W2 orchestration). Until then, this spec IS the vision pipeline.
