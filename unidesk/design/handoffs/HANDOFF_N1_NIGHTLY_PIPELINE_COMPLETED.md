# HANDOFF N1 Nightly pipeline — COMPLETED (v1)

Date: 2026-08-29.

Attribution-ID: attr-unidesk-n1-nightly-glm53flash-20260829-001

## Outcome

The EOD nightly pipeline runs end-to-end on real data:

- `unidesk/momentum/scan.py` — point-in-time universe scan: per-symbol
  features (EMA21/50, trend state, ADR%/ATR%, RVOL, delivery ratio,
  RS rank, contraction), detector runs, publication-time filtering,
  coverage/breadth stats.
- `unidesk/momentum/report.py` — the TONIGHT report renderer: header with
  session + breadth, setups grouped by detector with named values,
  honesty footer (regime placeholder, skip counts, unadjusted-price
  caveat, advisory disclaimer).
- `unidesk/momentum/nightly.py` — CLI orchestrator
  (`-m unidesk.momentum.nightly`, download→ingest→scan→report).

**Real run:** 646k-bar backlog, latest session 2026-07-03 — 2,563 symbols
scanned, 65.9% above EMA50, 3 Momentum-Burst candidates (BANKA, VLEGOV,
FILATEX — each with ADR%/RS-rank/RVOL/contraction/delivery named), report
at `data/market/reports/tonight_2026-07-03.md`.

Bugs found and fixed by tests during the slice: a contraction primitive
raised on unfillable windows instead of returning warm-up None (fixed in
the primitive; semantics now consistent module-wide); ScanResult gained
`last_session`; report rounding; a test's wrong mid-rank expectation.

## Files changed

- `unidesk/momentum/scan.py`, `unidesk/momentum/report.py`, `unidesk/momentum/nightly.py` (new)
- `unidesk/momentum/primitives/contraction.py` (warm-up semantics fix)
- `unidesk/tests/test_nightly_scan_report.py` (new, 5 tests), `unidesk/tests/test_setup_primitives.py` (1 test updated)
- `unidesk/TASKS.md`, `unidesk/GOAL.md`, this handoff

## Verification

```text
.venv-orderflow/Scripts/python.exe -m pytest orderflow/tests unidesk/tests -q -> 209 passed
.venv-orderflow/Scripts/python.exe unidesk/run_checks.py -> exit 0
Real run: python -m unidesk.momentum.nightly --no-download
  -> tonight_2026-07-03.md, 2563 symbols, 3 burst candidates
```

## Honest partials

- The download step is wired (subprocess to the owner's public downloader)
  but has never run against the live mirror — first evening run is the test.
- The store re-ingests all files per run (~73 s). A persistent cache is an
  optimization deferred to N4.
- Regime classifier (R0) is a placeholder in the report until N2.
- No yesterday's-outcomes section yet — needs the candidate store (N4).

## Addendum (2026-08-29) — D12 validation finding recorded against this report

The D12 external-validation slice (BananaPatterns snapshot regression) was
logged with this report as its completion_report before a dedicated report
existed. Finding: the public snapshot anonymizes most symbols (25/4,673
matched NSE tickers) — per-stock regression is infeasible unauthenticated;
task parked (TASKS.md), harness retained at
`unidesk/momentum/validation/bananapatterns.py`.

Attribution-ID: attr-unidesk-d12-validation-glm53flash-20260829-001
Attribution-ID: attr-unidesk-d12-report-correction-glm53flash-20260829-001
Attribution-ID: attr-unidesk-n2-fix-unknown-trend-glm53flash-20260830-001
