# BananaPatterns benchmark and event-data task definition

Attribution-ID: attr-unidesk-benchmark-event-tasks-gpt56sol-20260830-001

## Decision

Added two explicit recovery-plan slices:

1. An offline, held-out BananaPatterns comparison harness. It archives source
   bytes and provenance, uses an ISIN-first crosswalk, reports field-level
   agreement and disagreement, and prohibits vendor fields from production.
2. Versioned IPO listing facts and NSE result-event ingestion. Both require
   source and availability timestamps so IPO-age and EP studies cannot use
   hindsight.

## External repository assessment

- `gagandt/ipo-ai` is a strong implementation reference and possible
  one-time importer seed: it documents the NSE issue feed, equity-master gap
  recovery, raw caching, and a real warning against name-only matching. It is
  not adopted as a runtime dependency because it also uses third-party RHP
  extraction and its dataset is not itself a point-in-time authority.
- `thekrishnasoni/nse_earnings_tracker` is a narrow, useful reference for
  NSE-session handling and upcoming board-meeting discovery. Its future dates
  are calendar context only, not realised EP events.
- `manish70158/nse-earnings-analyzer` is unsuitable as a research authority:
  it pairs NSE discovery with Yahoo Finance estimates and fallback stock
  lists. Its data can inform exploratory UI work only after independent
  provenance checks.

## Limitations

No external repository was executed, vendored, or trusted as a production
source. The new plan remains unimplemented; it deliberately defers source
licensing, raw archival, and schema migration to their dedicated slices.
