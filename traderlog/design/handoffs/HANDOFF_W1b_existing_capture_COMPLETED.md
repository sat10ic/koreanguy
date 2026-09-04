# HANDOFF W1b existing capture -- COMPLETED

## Outcome

Implemented a strict, idempotent archive-first importer for the already-captured
`@iManasArora` and `@Fastzonetrader` provisional Chrome DOM corpus. It accepts
only those exact handles, excludes pinned and empty/no-media records, and never
creates a thread relationship unless the capture contains permalink ancestry
that proves it. All other imported records retain their source payload and an
explicit `relationship_status: unresolved` provenance marker.

The explicit CLI requires both `--handles` and either `--dry-run` or `--apply`,
as well as an explicit database path. Dry-run opens that database read-only and
does not download media, archive evidence, or write the database.

## Attribution

Attribution-ID: attr-w1b-provisional-gpt5-executor-20260823-001
Attribution-ID: attr-w1b-corpus-gpt5-orchestrator-20260823-001
Attribution-ID: attr-w1b-corpus-gpt5-reviewer-20260823-001

## Files changed

- `ingest/provisional_import.py` -- strict selected-handle validation, archive-first import, relationship proof rules, failure isolation, and dry-run reporting.
- `run_import_provisional.py` -- explicit operator-only dry-run/apply command.
- `tests/test_provisional_import.py` -- disposable-DB coverage for source identity, handle rejection, eligibility, relationship handling, media validation, archive ordering, isolation, and idempotence.
- `design/MODEL_WORK_LOG.jsonl` -- executor attribution record.

## Verification

```text
python traderlog/run_checks.py
  exit 0; no failures (derive remains stale_9d)

pytest traderlog/tests/test_provisional_import.py -q
  12 passed

python traderlog/run_import_provisional.py --dry-run --handles iManasArora Fastzonetrader --db traderlog/data/traderlog.db
  {"eligible": 197, "excluded": 21, "excluded_empty": 19,
   "excluded_pinned": 2, "existing": 7, "failed": {}, "media_items": 110,
   "new": 190, "new_media_items": 106, "selected": 218}

pytest traderlog/tests -q
  246 passed, 2 existing dependency deprecation warnings
```

## Honest partials

- The executor did not run the production import. Root subsequently applied the
  same explicit importer after creating and integrity-checking
  `data/traderlog.db.backup-pre-w1b-20260823`.
- Only one saved Manas record contains complete permalink ancestry. The importer
  deliberately stores the remaining eligible records with null
  `conversation_id`/`in_reply_to`; no reply ancestry was invented.
- Six selected records did not capture an `is_pinned` field. They are treated
  as not marked pinned; their original record is preserved verbatim in raw
  provenance for audit.

## Root production application and independent verification

```text
python traderlog/run_import_provisional.py --apply --handles iManasArora Fastzonetrader --db traderlog/data/traderlog.db
  190 new posts; 106 new media; 0 failures

Independent SQLite/filesystem verification
  202 real posts total: Manas 84, Fastzone 113, VCPSwing 3, Trading Hustler 2
  115 real media rows
  0 mock posts; 0 mock media
  0 missing/malformed raw archives
  0 missing media files; 0 SHA-256 mismatches
  PRAGMA integrity_check = ok
```

This completes exposure of the approved saved corpus. It does not complete the
separate seven-day live-observation criterion, infer missing reply links,
classify the new posts, or resume X collection.
