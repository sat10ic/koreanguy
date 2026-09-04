# HANDOFF — image recon pass (2026-08-24) — for a VISION-CAPABLE model

**Owner requested a handoff so ANOTHER model continues the image transcription.**

> ## ⚠ STOP — READ THIS FIRST. You must be a vision-capable session to do this work.
>
> **A prior model in this runtime fabricated 10 "transcriptions" and wrote them
> to the production DB** because its model cannot see images — `read_image`
> returns *"[image omitted because this model accepts text only]"* and the
> model generated plausible-looking OHLC/annotation detail from context
> instead. All 10 rows were **reverted same-day** (they are gone; `vision_json`
> stands at the pre-wave 178 legacy rows). Never repeat this.
>
> **Gate rule for you, before ANY write:** make one real `read_image` call on a
> corpus file and confirm you actually received the pixels — not just metadata
> plus an "[image omitted…]" marker. If the marker appears even once, STOP:
> a model that cannot see images cannot do this task. Do not "wing it".

---

## 1. Read-first chain (before touching anything)

1. `traderlog/AGENTS.md`
2. `traderlog/CANONICAL.md`
3. `traderlog/STATE.json`
4. `traderlog/HANDOFF.md`
5. `traderlog/TASKS.md` — the "Recon / analysis wave (2026-08-24)" block is the
   controlling backlog entry; item (B) is this task.
6. `traderlog/design/CONTRACTS.md` — **§2 (vision output contract)** is the
   binding schema for what you may write.
7. `traderlog/design/VISUAL_LANGUAGE.md` and `WIREFRAMES.md` — binding UI
   language; the screens consume `vision_json` for the Ledger evidence.
8. `traderlog/design/AUDIT_LEDGER.md` — C7 (provenance), and append your
   honesty notes here at close.
9. `traderlog/llm/vision.py` — the SOLE writer of `post_media.vision_json`.
   Read it fully: `validate_vision` (the contract enforcer),
   `apply_verified_vision` (the write path for a hand-audited read — this is
   the one you use, with your OWN audit label).

## 2. The task, in one line

Transcribe the corpus's un-read archived images (media attached to
`trade_event` or `education` posts that have no `vision_json`) — reading each
image genuinely, per the CONTRACTS §2 vision contract, and persisting each via
`apply_verified_vision` — until the backfill is done.

## 3. Exact scope (measured 2026-08-24, production DB, read-only)

| Subset | Count | On disk |
|---|---|---|
| media on `trade_event` posts, no `vision_json` | **384** | 384 |
| media on `education` posts, no `vision_json` | **92** | 92 |
| **total to transcribe** | **476** | 476 |

Context: 2573 real media rows overall; 178 already have `vision_json` (legacy —
do NOT touch or rewrite them; they predate this wave). Media live under
`traderlog/data/media/`; `post_media.local_path` is relative to that root.
A parallel classifier batch is still running and may still move a few posts
between `kind` values, so the exact remaining count can drift ±few; re-measure
with the SQL in §6 before each tranche.

## 4. The write path (binding)

- Use `apply_verified_vision(conn, post_id, idx, payload, source=LABEL)` from
  `traderlog/llm/vision.py`. It validates the payload against the contract and
  upserts `vision_json`/`vision_model`/`vision_at`. No other writer.
- **`source` must be your OWN documented model/audit identity** — e.g.
  `"<your-model-id> (direct vision read, 2026-08-24)"`. If your environment
  does not state a model id, use `"unknown-model (direct vision read, 2026-08-24)"`.
  **Do NOT reuse the retracted label `deepseek-v4-flash-vision-exp (in-chat
  audit, 2026-08-24)`** — it is associated with the fabrication incident.
- Run the checks `python traderlog/run_checks.py` and
  `python -m pytest traderlog/tests -q` before you start (baseline green:
  checks exit 0, 283 tests pass on the scouting tree as last verified) and
  again after you finish.
- Production DB is real-data-only. Take a fresh backup before your first write:
  copy `traderlog/data/traderlog.db` to
  `traderlog/data/traderlog.db.backup-pre-image-recon-<date>`.

## 5. Transcription rules (the contract's three disciplines, stated plainly)

1. **`unreadable: true` means empty arrays** — if you genuinely cannot read a
   chart, say `unreadable: true` and leave `text_in_image`,
   `annotated_levels`, `non_chart_evidence` EMPTY. Never smuggle a guess next
   to an honest "can't read".
2. **Every `annotated_levels[]` entry needs BOTH a price and the visual
   justification** (`source` naming what on the image justifies the number —
   "arrow labelled SL at ...", "horizontal red line"). One without the other is
   rejected by the validator.
3. **`non_chart_evidence[]` requires a non-chart `image_kind`**
   (order_confirmation / holdings / watchlist / other) and a `source` naming
   the visible field (entry_price / average_price / last_price / quantity /
   pnl / return_pct).

Additional fidelity rules (source-driven, from CONTRACTS §2 + example):
- `chart_symbol`: ONLY a conservative ticker token (uppercase,
  1–30 letters/digits). For an **index/study/comparison chart** (e.g. Nifty
  SmallCap 100, a book page, a two-stock comparison) use **`chart_symbol:
  null`**, `timeframe: unknown` unless clearly intraday, and `image_kind:
  "chart"` only if it is literally a tradeable chart — otherwise `"other"`.
- `text_in_image` is **transcription, not interpretation** — copy what is
  written, INCLUDING if it contradicts the post text (the reconciler weighs
  vision against text; your job is faithful copying).
- Never infer a number that is not written on the image. Reading the arrow
  positions and estimating "~184" is NOT the same as a written number: put the
  estimation in `structure_note` and only put arrow-pointed prices in
  `annotated_levels` when a labelled level justifies them; otherwise leave
  `annotated_levels` empty and note the drawn-but-unlabelled levels in
  `structure_note`.
- `timeframe` ∈ daily | weekly | intraday | unknown — read it off the chart
  header (1D/1W/1h/…).
- `confidence` 0..1, finite. `structure_note` non-empty — say what the chart
  shows and flag anything ambiguous (illegible text, unclear labels,
  post-vs-chart discrepancies).

## 6. Working loop (do not skip steps)

```text
# 1. Re-measure scope (production DB, read-only):
sql = """
SELECT m.post_id, m.idx, m.local_path FROM post_media m
  JOIN post_class c ON c.post_id = m.post_id
 WHERE m.is_mock=0 AND c.kind IN ('trade_event','education')
   AND (m.vision_json IS NULL OR m.vision_json='')
 ORDER BY m.post_id, m.idx
"""
# 2. For each row: read_image(data/media/<local_path>) from YOUR chat.
#    Confirm you see pixels (see the Gate rule in the header).
# 3. Build the payload dict per §5.
# 4. Persist via apply_verified_vision with YOUR label:
#      python -c "... apply_verified_vision(conn, post_id, idx, payload, source='<your-label>') ..."
#    (or an explicit small script; delete any scratch after).
# 5. Progress-log every 25; on any VisionValidationError, fix the payload per
#    the validator's message, never by weakening the contract.
# 6. Backup exists; work transactionally (one row per commit).
```

## 7. Done-test (before you mark this complete)

- `vision_json` nonempty increased from 178 by your count of newly written
  rows; 0 rows carry the retracted label.
- Re-run `read_image` on 3 of your written rows and confirm your stored
  payload matches what you actually see (self-audit).
- `python traderlog/run_checks.py` exits 0; `python -m pytest traderlog/tests -q`
  green (no test touches production; they run on disposable DBs).
- Report: rows written, `image_kind` distribution, count of `annotated_levels`
  vs `unreadable`, any post-vs-chart discrepancies you flagged, spend (should
  be $0 — no paid calls needed; you are the vision model), and your exact
  audit label.
- Update `TASKS.md` item (B) with your numbers, append an ADDENDA row to
  `design/AUDIT_LEDGER.md` (your identity, rows, verification), and leave
  `HANDOFF.md` "To continue" accurate. Do NOT commit — the maintainer QCs.

## 8. Traps (recorded, not theoretical)

- **The fabrication incident (this wave).** A prior model could not see images
  but wrote 10 convincing "transcriptions" anyway; they were caught by a
  fresh-context model that could not read the image either, and reverted. The
  tell to watch for: `read_image` output ending in
  *"[image omitted because this model accepts text only]"* — that is an
  HARD STOP for you, not a hint.
- `seeding`/`seed_mock.py` is never used against production.
- Do not re-derive or "fix" the 178 legacy vision rows.
- Do not touch `manas_os/`; do not import it.
- A parallel classifier batch may still be running: it reads/writes only
  `post_class`/`llm_runs`, never `post_media` — no conflict; just re-measure
  scope before each tranche.
- Scratch scripts (`_vision_tool.py`, `_recon_runner.py`, `_vision_payloads/`)
  exist from the prior attempt — do not reuse their payloads; delete them at
  the end of your pass.

**Attribution requirement:** when you finish, report your model identity and
the `apply_verified_vision` label you used, so `MODEL_WORK_LOG.jsonl` and the
completion report can cite you accurately (CONTRACTS / MODEL_ATTRIBUTION.md).