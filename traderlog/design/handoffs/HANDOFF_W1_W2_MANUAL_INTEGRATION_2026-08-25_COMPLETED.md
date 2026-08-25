# W1/W2 manual classification integration — completed 2026-08-25

## Outcome

- Manually reviewed and persisted classifications for the 35-post recent capture.
- Manually classified the 28 remaining historical gaps. Production coverage is
  3,395 classified posts of 3,395 captured posts.
- Reconciled BALAMINES, BLUEJET, AEGISLOG, RATEGAIN and MOLBIO only where the
  source posts supported durable links. Ambiguous replies remain unlinked.
- Rebuilt `watch_ideas` transactionally from the completed corpus: 546 rows.
- No TraderLog provider-backed LLM classification or reconciliation calls were
  used.

## Verification

- 23 real positions and 23 cited events; zero open reconciliation reviews.
- No missing event sources or null event timestamps.
- SQLite integrity check: `ok`.
- `python traderlog/run_checks.py`: all required checks pass; ingest freshness
  remains a warning because only 9 of 17 traders were present in the recent
  capture.

## Attribution

Attribution-ID: attr-w1-recent-historical-manual-classification-reconciliation-executor-gpt-5-6-terra-20260825-001

Attribution-ID: attr-w1-w2-classification-integration-orchestrator-exact-model-unavailable-20260825-001

## Remaining risk

The Gemini vision outputs saved under `_gemini_tranches` are already integrated,
but vision coverage is not corpus-complete: 709 media rows have `vision_json`;
565 image rows attached to `trade_event` or `education` posts do not. Legacy
`themes` and `edu_items` also have no production materializer; the planned
Playbook replacement should consume classified evidence directly.
