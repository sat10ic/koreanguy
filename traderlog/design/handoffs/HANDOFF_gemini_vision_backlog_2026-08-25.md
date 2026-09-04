# HANDOFF — Gemini vision backlog pass #2 (2026-08-25)

**For: `gemini-3.7-flash` session (you already completed 531 direct vision reads
under the label below, plus 1707 classifications — this pass finishes what your
own classification wave created).**

> ## Gate rule (same as last time — hard stop)
>
> Before ANY write, make one real `read_image` call on a corpus file and confirm
> you received actual pixels. If output ends with *"[image omitted because this
> model accepts text only]"* or any refusal — **STOP**. A model that cannot see
> images must not write transcriptions here: a prior runtime fabricated 10 rows
> that way and they had to be reverted.

---

## 1. Read-first chain

1. `traderlog/AGENTS.md` (note: "owner-directed manual backfills stay manual" —
   you ARE the executing model; use the audited `apply_verified_*` writers)
2. `traderlog/design/CONTRACTS.md` §2 — vision output contract
3. `traderlog/llm/vision.py` — sole writer; read `validate_vision` +
   `apply_verified_vision` fully
4. `traderlog/design/handoffs/HANDOFF_gemini_close_2026-08-24.md` — your prior
   brief; §5 verification protocol and §8 traps carry over verbatim
5. `traderlog/TASKS.md` — recon wave block

## 2. Task in one line

Transcribe the **565 newly-in-scope images** (346 trade_event + 219 education,
all confirmed on disk) that your own classification wave pulled into vision
scope — then run the full hallucination-verification protocol from your prior
brief (§5), including re-audits of both this pass AND a sample of your prior 531.

## 3. Scope (measured 2026-08-25, production DB)

| Kind | Missing vision | On disk |
|---|---|---|
| trade_event | 346 | 346 |
| education | 219 | 219 |
| **Total** | **565** | **565** |

Context: classification is now 100% complete (3395/3395) — no classification
work remains unless NEW captures are imported after your start; if so, apply
`apply_verified_classification` with label
`gemini-3.7-flash (direct classification read, 2026-08-24)` to genuinely-read
posts only.

Media live under `traderlog/data/media/`; `post_media.local_path` is relative.
Scope SQL:
```sql
SELECT m.post_id, m.idx, m.local_path FROM post_media m
  JOIN post_class c ON c.post_id = m.post_id
 WHERE m.is_mock=0 AND c.kind IN ('trade_event','education')
   AND (m.vision_json IS NULL OR m.vision_json='')
 ORDER BY c.kind DESC, m.post_id, m.idx
```
Re-measure before each tranche — an agentic reconcile agent may concurrently be
writing `positions`/`position_events` (different tables; no conflict), but do
not touch positions/review_queue yourself.

## 4. Write path + label (binding)

`apply_verified_vision(conn, post_id, idx, payload,
source="gemini-3.7-flash (direct vision read, 2026-08-24)")` — same label as
your prior 531 so the entire direct-vision set stays under one provenance.
Backup before first write:
copy `traderlog/data/traderlog.db` →
`traderlog/data/traderlog.db.backup-pre-gemini-pass2-<date>`.

## 5. Fidelity rules (contract + corpus discipline)

- Transcribe only what is visibly written. `unreadable: true` ⇒ empty arrays.
- Every `annotated_levels[]` entry: price + visual `source` justification;
  otherwise the observation goes to `structure_note`.
- Index/study/comparison/book pages → `chart_symbol: null`, correct
  `timeframe`, `image_kind: "chart"` only for literal tradeable charts, else
  `"other"`.
- Post text may contradict the chart — copy the chart faithfully anyway; the
  reconciler weighs them.
- Never infer a number not written on the image. Estimating arrow positions is
  `structure_note` material, not levels.

## 6. Hallucination-verification protocol (carry-over, NOT optional)

1. **Self-audit**: every ~25 new rows, re-open 5 and confirm stored JSON matches
   the pixels (every digit).
2. **Prior-work re-audit**: re-audit ≥49 of your existing 531 (every 10th) OR
   40 random + 10 lowest-confidence — whichever is larger. Fix mismatches; report counts.
3. **Fresh-context adversarial check**: hand 10 rows (mix of new + prior) to a
   separate memoryless model with only file paths/post texts; diff outcomes;
   correct any material disagreement.

## 7. Done-test / report

- All 565 written (or honestly reported remainder with per-row reasons);
  `vision_json` nonempty = 709 + your new total.
- §6 audit numbers: self-audit count/mismatches/fixes; prior-531 sample size and
  corrections; fresh-context diff outcome.
- `python traderlog/run_checks.py` exit 0; `python -m pytest traderlog/tests -q`
  green.
- Update `TASKS.md` recon-wave item (B) with final coverage; append an
  ADDENDA row to `design/AUDIT_LEDGER.md`. Do NOT commit.
- Report your exact model id + label for MODEL_WORK_LOG attribution.

## 8. Traps (carry-over)

- `[image omitted…]` = hard stop, never a prompt to improvise.
- Do not touch positions/review_queue (concurrent reconcile agent owns those
  writes this wave). Do not rewrite other models' vision/classification rows.
- `seed_mock.py` never on production. No `manas_os/` access. Scratch scripts
  deleted when done.