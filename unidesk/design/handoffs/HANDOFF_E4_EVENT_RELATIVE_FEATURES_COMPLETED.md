# Completion — E-4 event-relative feature core

**Date:** 2026-09-04  
**Scope:** isolated descriptive feature layer only; safe to build while B2-3
owns the research-event archive.

Attribution-ID: attr-unidesk-e4-event-relative-codex-20260904-001
Attribution-ID: attr-unidesk-e4-event-relative-codex-20260904-002

## Delivered

- Added `unidesk/momentum/features/event_relative.py` with calendar-based
  `sessions_since_event`, IPO listing-relative features, and EP gap-relative
  features.
- IPO values: listing-high/low distance, first-day range, base depth in
  listing-day ranges, and an explicitly optional issue-price distance.
- EP values: open-vs-prior-close gap, gap-day close location, survival above
  the gap low, RVOL-normalised post-gap path, circuit-lock count when the
  entire supplied history is known, and optional catalyst age.
- Every public callable is classified in the truncation-invariance registry.
  The feature pair has a dedicated as-of test: altering later bars cannot
  change the result as of an earlier session.

## Verification

Focused run (local project virtual environment):

```text
.venv-orderflow\Scripts\python.exe -m pytest unidesk\tests\test_event_relative.py unidesk\tests\test_truncation_invariance.py -q
31 passed, 34 skipped in 0.31s
```

## Deliberate containment

- Did **not** touch the in-flight E-1 listing-calendar files, E-2 announcement
  ingest, the B2-3 event archive, circuit/ranking gates, candidate ordering,
  or an Events UI.
- This is not a signal, detector, rank input, or validation claim.  Wiring it
  requires fact-backed `EventAnchor` records and owner approval after E-1/E-2.
- `days_locked_since_gap` stays `None` when any supplied post-gap lock status
  is unknown; absence does not become evidence.
- The full runner was subsequently exercised while B2-3 remained active:
  `unidesk/run_checks.py` reported all checks green (with its two existing
  honest `not_built_yet` stubs). No independent code review has occurred.
