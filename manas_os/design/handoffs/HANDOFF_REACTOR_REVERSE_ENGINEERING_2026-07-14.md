# Reactor Reverse-Engineering Handoff

**Date:** 2026-07-14  
**Canonical audit:** `../REACTOR_SCALE_REVERSE_ENGINEERING_AUDIT_2026-07-14.md`  
**Source labels:** `C:\Users\satta\Downloads\DEMO SHEET - MARCH APRIL - Sheet1.csv`

## State

**Certain:** the bounded daily-bhavcopy formula search is complete and did not
recover the proprietary score exactly. The best full-panel candidate matches
6,572 of 53,280 cells (12.3348%) across 1,478 symbols and all 37 source dates.
Independent Decimal rounding and `math.fsum` verification passed.

**Certain:** 162 official NSE sessions from 2024-09-02 through 2025-04-29 are
validated in `data/bhavcopy`; the manifest reports 10 market-closed dates and zero
failures. Do not redownload them unless the manifest/hash validation fails.

**Likely:** the source formula or upstream footprint feed changed around
2025-03-20/26. Best period-specific exact shares are 2.0390% (early), 4.2398%
(transition), and 21.8029% (late). This is an inference, not a publisher disclosure.

**Unverified:** whether ADR in the publisher's phrase means precisely Average
Daily Range. The public site does not expand the acronym. Tested price-range ADR
terms add almost no explanatory value.

## Do not repeat

- Do not run another many-factor/black-box fit; it violates the recovery constraint
  and cannot establish formula fidelity.
- Do not call the current candidate "Reactor Scale" or "smart-money detection."
- Do not kill the live `run_manas_cli.py run-eod` process to force DB ingestion.
- Do not treat POC/VAH/VAL as score inputs; they are separate directional context.

## Next executable work

1. When the active EOD writer releases SQLite, run
   `output/reactor_scale_audit/ingest_official_bhavcopy_range.py` and verify coverage.
2. Exact-clone research resumes only if the publisher's component formula or the
   same order/tick-level footprint feed becomes available.
3. Otherwise, specify a separately named sat10ic EOD abnormal-activity analogue,
   keep it direction-neutral and shadow-test it against future path outcomes.

## Verification artifacts

- `output/reactor_scale_audit/exact_refine_nonlinear_results.json`
- `output/reactor_scale_audit/exact_refine_nonlinear_predictions.csv`
- `output/reactor_scale_audit/final_reactor_search_verification.json`
- `output/reactor_scale_audit/period_formula_search_results.json`
- `output/reactor_scale_audit/remaining_domain_search_results.json`
- `output/reactor_scale_audit/zscore_domain_search_results.json`
- `output/reactor_scale_audit/official_bhavcopy_manifest.json`

## Risks

- The missing variable may be a proprietary individual-order statistic unavailable
  in daily bhavcopy.
- The public source appears internally versioned, so even the original current
  formula may not reproduce the early demo-sheet block.
- Source-score similarity is not evidence of future tradable alpha.
