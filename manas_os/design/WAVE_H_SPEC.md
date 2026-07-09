# WAVE H — Tier-1 ChartsMaze independence (user-approved 2026-07-10)

Goal: every price/volume-derived ChartsMaze screener computed IN-HOUSE from bhavcopy +
our indicator engine, so the signal-critical path no longer depends on the daily scrape.
ChartsMaze extractor remains ONLY for Tier-3 (disclosures, fundamentals, order wins,
results calendar) + the frozen industry taxonomy.

Method (no blind guessing): we hold months of their daily outputs (hit lists + full
column values) AND the same days' bhavcopy. Replicate → replay → diff → tune → freeze.

## H1 — Calibration harness (build first, everything else is judged by it)
- New manas_os/screeners/calibrate.py: for a screener S and date D, compute our hit set
  from local data, load their hit set from the archived CSV, emit
  {date, screener, ours_n, theirs_n, jaccard, only_ours[], only_theirs[]}.
  CLI: `python -m manas_os.screeners.calibrate --screener vcp --start .. --end ..`.
- Value-level mode: for numeric columns present in their schema (RS Rating, ADR%, etc.)
  emit per-stock abs error distribution.
- ACCEPTANCE BAR per screener: median daily Jaccard >= 0.90 over >=15 sessions, and
  only_theirs misses explained (e.g. their universe includes SME board we exclude).
  Result logged per screener in manas_os/design/LEARNINGS.md before the in-house version
  becomes a producer.

## H2 — Screener ports (batch order; standard formulas first, tune via H1)
1. Volume Spike / Highest Volume / Volume Footprint (pure ranks) — easiest, validates harness.
2. Gap Up / Gap Filling / Top Gainers.
3. Inside Bar D/W, Tight Setup D/W (we already have tightness/RMV), Horizontal Resistance.
4. Shakeout 10/21/50/200 EMA (4 variants), Momentum Scanner.
5. VCP, Flag & Pennants, RS High Before Price High.
6. RS Rating (IBD-style weighted 3/6/12m return percentile across universe) — value-level
   calibration against their column, not just membership.
7. IPO Setups, Circuit Revision (screener form), Shorting Scanner, Past Winners.
- Each port: one module in manas_os/screeners/, pure function over bars/universe frames,
  fixture unit tests + H1 calibration report. One writer: once accepted, the in-house
  screener REPLACES the ChartsMaze hit ingestion for that screener (no dual producers).

## H3 — Cutover
- screener_hits gains source column ('inhouse'|'chartsmaze'); pipeline computes in-house
  Tier-1 nightly BEFORE ingest_chartsmaze; chartsmaze ingestion keeps only Tier-3 groups.
- Taxonomy freeze: industry->sector mapping copied into our repo as data (quarterly manual
  review note), no longer read from daily dumps.
- DONE-TEST: pipeline runs green with chartsmaze screeners group disabled; desk shows
  identical (calibrated) screener chips.

User support (optional accelerator): paste/screenshot ChartsMaze's own screener criteria
text pages — converts reverse-engineering into verification. Not blocking.
