# Benchmark and event-data risk foundations

Attribution-ID: attr-unidesk-benchmark-event-foundations-gpt56sol-20260830-001

## Completed

- Added immutable BananaPatterns public-snapshot evidence archival. The stored
  raw bytes, SHA-256, source date, retrieval timestamp, and manifest mark the
  asset as `offline_comparison_only`.
- Added fail-closed IPO listing and realised earnings-result source contracts.
  They require normalized identity, HTTPS source URL, SHA-256 evidence hash,
  and point-in-time availability/retrieval ordering. An earnings result is
  available exactly at dissemination, not at fiscal period end or a future
  board-meeting date.

## Verification

`py -m pytest unidesk/tests/test_bananapatterns_validation.py unidesk/tests/test_market_events.py unidesk/tests/test_detector_registry.py unidesk/tests/test_report_json.py -q`

Result: 21 passed.

`py unidesk/run_checks.py` passed.

## Still open

The contracts and evidence archive do not yet fetch NSE data, implement the
ISIN crosswalk/held-out comparator, persist event rows, or generate EP/IPO
signals. No third-party repository is imported or executed.
