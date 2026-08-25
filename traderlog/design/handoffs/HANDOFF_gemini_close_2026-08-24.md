# HANDOFF — remaining classification + vision + hallucination-verification (2026-08-24)

**For a VISION-CAPABLE, GENUINELY-READING model (the `gemini-3.7-flash` session
that has already done 485 direct vision reads here).** This continues and closes
TraderLog's recon wave on the production corpus.

> ## ⚠ READ THIS FIRST — the reason this handoff exists
>
> **A prior text-only model fabricated 10 supposedly-"vision" transcriptions in
> this runtime** (it cannot see images, generated plausible OHLC/annotation
> detail from context, and wrote them to the production DB). They were caught by
> a fresh-context model that also could not read the image, and reverted. Your
> known-good role `gemini-3.7-flash (direct vision read, 2026-08-24)` already
> proves you can read images for real. **The verification protocol in §5 is not
> optional** — it is the reason this handoff trusts your output at all.

---

## 1. Read-first chain (before touching anything)

1. `traderlog/AGENTS.md`
2. `traderlog/CANONICAL.md`
3. `traderlog/STATE.json`
4. `traderlog/HANDOFF.md`
5. `traderlog/TASKS.md` — the "Recon / analysis wave (2026-08-24)" block is the
   controlling backlog entry.
6. `traderlog/design/CONTRACTS.md` — **§1 (classifier)** and **§2 (vision)**
   are the binding output contracts.
7. `traderlog/llm/classify.py` and `traderlog/llm/vision.py` — the SOLE writers.
   Read `validate_classification`, `validate_vision`,
   `apply_verified_classification`, `apply_verified_vision` fully.
8. `traderlog/design/AUDIT_LEDGER.md` — note the C7 provenance finding and the
   fabrication addendum; append your verification addendum at close.

## 2. The task, in one line

Close the corpus's unfinished **classification** and **vision** by reading every
remaining post/image genuinely and writing only contract-validated rows through
the two audited writers, then **verify your own work did not hallucinate** per §5.

## 3. Exact scope (measured 2026-08-24, production DB)

### 3a. Classification remaining
| Subset | Count |
|---|---|
| posts with NO `post_class` row (unclassified) | **1655** |
| `post_class` rows with NULL `run_id` (provenance gap, audit C7) | **904** |
| **total to label / re-provenance** | **2559** |

Nuance on the 904: they already have a `kind` but no `run_id`. Re-writing them
via `apply_verified_classification` gives them your model provenance (and is the
C7 fix). You MAY re-read and re-label them (idempotent upsert), or if a row's
existing `kind` is clearly right, you may still re-persist it under your label
so it gains provenance. Do not delete other models' rows.

A classifier agent (also running, label `deepseek-v4-flash ...`) is processing
the same table idempotently. Both of you upsert per `post_id` and neither ever
rewrites a row that already has a `kind` + `run_id`. Coexist; re-measure scope
(§6 SQL) before each tranche so you each take only still-pending rows.

### 3b. Vision remaining (kind-scoped: media on trade_event/education posts)
| Subset | Count |
|---|---|
| media on `trade_event` w/o vision | **19** |
| media on `education` w/o vision | **20** |
| **total vision to do** | **39** (all confirmed on disk) |

These are attached to posts already classified `trade_event`/`education` that
lack a `vision_json`. Media live under `traderlog/data/media/`; `local_path` is
relative to that root. Do NOT touch the 663 rows that already have `vision_json`
— including your own 485.

## 4. The write paths + labels (binding)

**Vision** — `apply_verified_vision(conn, post_id, idx, payload, source=LABEL)`
from `traderlog/llm/vision.py`. Use the SAME label you already used for the 485:
`gemini-3.7-flash (direct vision read, 2026-08-24)`. This keeps the whole direct
vision set under one attributable provenance.

**Classification** — `apply_verified_classification(conn, post_id, payload, source=LABEL)`
from `traderlog/llm/classify.py`. Use
`gemini-3.7-flash (direct classification read, 2026-08-24)`.

Both writers validate the payload against source (vision: image; classification:
post text), so an invalid/fabricated payload is REJECTED before write. That is
the first hallucination gate — trust it, and also do §5.

Take a fresh backup before your first write:
copy `traderlog/data/traderlog.db` → `traderlog/data/traderlog.db.backup-pre-gemini-close-<date>`.

## 5. Hallucination-verification protocol (NOT optional — apply to NEW work AND your PRIOR vision reads)

You already wrote **485 vision rows** (`gemini-3.7-flash (direct vision read,
2026-08-24)`) earlier this wave. Those must be audited too — **do not assume
they are clean just because you are a vision-capable model.** A different model
concurrently in this codebase fabricated data and was only caught by
re-examination; your own 485 get the same treatment. The three checks below run
against BOTH your newly-written rows and, as a representative re-audit, your
existing 485 (see step 1 for the required sample size).

1. **Adaptive precision self-audit — including your prior 485.** After you
   transcribe NEW vision rows (every ~25), re-open 5 of them and re-read,
   confirming stored `vision_json` matches what you now see (every OHLC digit,
   labelled price, verbatim string). **Additionally and separately, re-audit a
   representative sample of your existing 485** — at minimum every 10th row
   systematically (≈49 images) OR 40 random + the 10 lowest-confidence rows,
   whichever yields the larger check; re-read each image and confirm the stored
   transcription matches. Fix any mismatch and report precisely how many you
   corrected. Same adaptive self-audit for new classification (re-read sample
   post texts).
2. **"Nothing inferred" pass — on new rows and the audited 485 sample.**
   For each audited row, confirm `annotated_levels[]` entries carry a price AND
   a visual `source` (arrow/label/line justification); any level not backed by
   a visible annotation is removed and moved to `structure_note`. For
   classification: every `symbol` appears in the post text (the validator
   enforces this), and you never set a price/level not written.
3. **Fresh-context adversarial spot check — on new rows AND prior-read rows.**
   After you finish, extract the rows you WROTE THIS WAVE plus a sample of your
   prior 485, and hand 10 representative rows to a SEPARATE, fresh-context model
   with NO memory of your session: give it the image file paths (vision) / post
   texts (classification) and ask it to independently transcribe/classify the
   same 10. Diff the two. If any disagree materially, correct your rows. Record
   the diff outcome, and state how many of those 10 were drawn from your prior
   485 vs your new work.

Cost: $0 — you are the model; no paid provider calls are needed for any of this.

## 6. Working loop

```text
# Classification: pull next N still-pending posts, read real text, label, persist.
   python -c "sql: SELECT p.post_id,p.handle,p.ts_ist,p.text FROM posts p
              WHERE p.is_mock=0 AND NOT EXISTS (SELECT 1 FROM post_class c
                WHERE c.post_id=p.post_id) ORDER BY p.ts_utc LIMIT N"
   # for each: apply_verified_classification(post_id, payload, source='gemini-3.7-flash (direct classification read, 2026-08-24)')
# Vision: pull next still-missing trade_event/education media, read_image the file, transcribe, persist.
   python -c "sql: SELECT m.post_id,m.idx,m.local_path,c.kind FROM post_media m
              JOIN post_class c ON c.post_id=m.post_id
              WHERE m.is_mock=0 AND c.kind IN ('trade_event','education')
                AND (m.vision_json IS NULL OR m.vision_json='')
              ORDER BY c.kind, m.post_id LIMIT N"
   # for each: apply_verified_vision(post_id, idx, payload, source='gemini-3.7-flash (direct vision read, 2026-08-24)')
```
You can interleave or do classification then vision. Do a meaningful slice
(min ~300 classification + all 39 vision), then if your session is bounded, stop
and report — a later run resumes (writers are idempotent). A running classifier
agent may shrink the classification pool you see; re-measure before each slice.

## 7. Done-test / report

- Report: posts classified (count + per-kind), 904-NULL-provenance rows resolved,
  all 39 vision rows written, image_kind distribution, count with `annotated_levels`
  vs `unreadable`, the §5-1 self-audit mismatches found+fixed (or "none"),
  **how many of your prior 485 vision rows you re-audited and how many you
  corrected**, the §5-3 fresh-context diff outcome, and spend ($0).
- `python traderlog/run_checks.py` exit 0; `python -m pytest traderlog/tests -q` green.
- Update `TASKS.md` wave item (A)/(B) with your numbers; append an ADDENDA row to
  `design/AUDIT_LEDGER.md` (your identity, rows, verification proof). Do NOT commit.

## 8. Traps

- NEVER write a payload for a post/image you did not genuinely read. If you
  cannot read an image (`[image omitted...]` or an unreadable chart), write
  `unreadable: true` with EMPTY arrays — never a guess beside an honest "can't read".
- **Treat your 485 prior vision rows as unverified until §5 step 1 re-audits
  them.** Same codebase produced fabricated "vision" data from a model that
  could not see images; your provenance label is good, but the CONTENT of each
  prior row is only trusted after you re-open the image and confirm it.
- Index/study/comparison charts → `chart_symbol: null`, `timeframe: unknown`
  unless the header shows intraday, `image_kind` only `chart` if literally a
  tradeable chart, else `other`.
- Classification: a post text like "Force Motors" has NO ticker token
  `FORCEMOTORS` present → `symbols: []` (the validator enforces this; a
  validator pass already guarantees it). conviction_words verbatim-only.
- `seed_mock.py` is never run against production. Do not touch `manas_os/`.
- Do not delete or rewrite any `post_class`/`post_media` row you did not write,
  except to CORRECT a row that fails your §5 audit (the correction is the point).

**Attribution:** report your exact model id and the two labels you used so
`design/MODEL_WORK_LOG.jsonl` and the completion report can cite you
(MODEL_ATTRIBUTION.md).