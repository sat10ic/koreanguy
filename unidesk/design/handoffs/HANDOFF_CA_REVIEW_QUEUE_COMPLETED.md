# HANDOFF — N3 CA-ratio review-queue artifact — COMPLETED

Date: 2026-08-30. Orchestrator-executed directly.

Attribution-ID: attr-unidesk-ca-review-queue-claude-sonnet5-20260830-001

## What this closes

N3's "STILL OPEN" list has carried "remaining 194 detector candidates
unconfirmed" since directive-1e, but nothing actually produced a queue an
owner could review. **Producing the queue is not owner-gated — only the
ratio source is** (do not infer a real split factor from the price gap
itself). This slice closes exactly that gap: a script that runs the
existing, already-tested detector across the full archive and writes the
unconfirmed backlog to a small, committed, owner-facing CSV.

## What was built

`unidesk/run_ca_review_queue.py`: ingests `data/bhavcopy/` into an
`InMemoryMarketStore`, runs `momentum.data.splits.scan_store_for_splits`
(the existing conservative bar-shape detector — unchanged, not touched
here), loads `config/confirmed_actions.csv`, and calls the existing
`unconfirmed_candidate_sessions` to drop any candidate whose
`(symbol, ex_date)` already has a confirmed factor. Writes
`unidesk/config/ca_review_queue.csv` — one row per unconfirmed candidate:
`symbol, session, prev_close, open, implied_factor, nearest_clean,
clean_distance_pct`. No ratio is ever written or inferred here — that
column set is exactly what the detector observed, nothing derived beyond
it. Sorted by symbol then session for reviewability.

## Verification (real run, not a fixture)

```text
python unidesk/run_ca_review_queue.py
-> [ca-review-queue] 190 unconfirmed candidates written to .../unidesk/config/ca_review_queue.csv
```

190 reconciles exactly with N3's documented "194 open-gap candidates"
figure minus the 4 since-confirmed actions
(ANANDRATHI/BEML/AGIIL/ANUHPHR) — this is the same detector, same
backlog, just filtered through the confirmed table for the first time.
Spot-checked: `ANANDRATHI` appears in the output on a *different* gap date
(2025-03-05) than its confirmed one (2026-06-03) — the guard correctly
matches on `(symbol, ex_date)`, not on symbol alone, so a symbol can have
both a confirmed split and a still-open, unrelated candidate.

No new unit test was added: `unconfirmed_candidate_sessions` (the one
piece of logic this script depends on beyond already-exercised primitives)
already has dedicated coverage in `test_unconfirmed_ca_guard.py`; this
script is a thin, mechanically-verified wrapper, not new logic.

## Files

`unidesk/run_ca_review_queue.py` (new), `unidesk/config/ca_review_queue.csv`
(new, generated — committed because it is small and owner-facing, unlike
the generated event store under `data/market/`, which stays gitignored).

## Still open

The ratio SOURCE remains genuinely owner-gated: someone with access to an
authoritative NSE/BSE corporate-action feed (or the owner directly) must
confirm each row's real factor and move it into
`config/confirmed_actions.csv`. This script produces no recommendation on
what that factor is — `nearest_clean` is the closest of a small set of
common fractions to the *observed* gap, offered only as a sorting/triage
aid, explicitly not a confirmed value.
