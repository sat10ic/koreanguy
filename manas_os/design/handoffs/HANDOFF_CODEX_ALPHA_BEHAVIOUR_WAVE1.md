# sat10ic os — Alpha / Chart-Behaviour Wave 1 Handoff

Date: 2026-07-11  
Branch: `emergent`

## Governing correction

Indian swing alpha is implemented as **regime detection → cross-sectional ranking → risk context → chart-behaviour reasoning**. Forecast probabilities are secondary evidence. Deterministic gates remain the tradability/risk governor, but must not substitute for reading the chart. The durable constraint is in `design/ALPHA_LEARNING_CONSTRAINTS.md`.

## Delivered

- Native alpha schema and services for point-in-time feature snapshots, model/experiment registry, shadow predictions, immutable decision memory and analogue IDs.
- Causal 5/10/20/60-day residual momentum, cross-sectional ranks/z-scores, Bayesian shrinkage, competing-risk summaries and seeded block-bootstrap uncertainty.
- Behaviour-first chart context with EMA 10/21/50, slopes, RS/sector relative strength, ADR, contraction/range structure, volume relationships and compact recent OHLCV path.
- Debate prompt contract now evaluates EP/gap-and-go, flags, VCP, IPO base, long-base Stage 2, pocket pivots, pullbacks and reversals as competing hypotheses. It must state confirmation, invalidation, expected sequence/time and strongest contradiction.
- Tiered intraday storage/provider seam: 5-minute full universe, 1-minute active set, Fyers adapter, resumable windows, TradeTM session segments, provenance and completeness checks.
- Nightly alpha feature build before debate and immutable decision-memory capture after chair adjudication.
- Alpha APIs: overview, leaders, symbol evidence, experiments, models and memory.
- Round-4 light Alpha Lab and compact Debate Alpha Card with honest loading/warming/error states and plain-English descriptions.
- Fixed the legacy black document canvas visible outside the white Round-4 shell.

## Verification ledger

- Alpha/API/intraday/context/debate targeted suite: **42 passed**.
- Desk Vitest: **37 passed**.
- Desk production build: passed (existing bundle-size warning only).
- Full Python suite: **722 passed, 7 failed**. The same seven failures existed before this wave: six belong to already-dirty `alerts/live_fsm.py` / `test_live_fsm.py`; one real-database sector-downside model currently fails to beat its baseline. No alpha file is implicated.
- Browser QC at 1280×720: Alpha Lab renders real bhavcopy-backed ranking data; outer canvas is light; loading and lower-section scrolling work.
- `BETA` was investigated rather than removed: it has 286 complete sessions through 2026-07-10 and `source='bhavcopy'`.

## Deliberately still shadow / not complete

- The local daily panel is about 286 sessions, not the required 3–5 point-in-time years. It can build infrastructure and shadow ranks, not support promotion claims.
- Real Fyers intraday backfill has not been run; storage/provider machinery is ready but credentials, rate limits and completeness must be observed during the actual run.
- No model is promoted. Gradient ranking/survival training and any ranking tilt require leakage-safe walk-forward evidence, Indian costs/slippage, calibration/stability gates and at least 20 genuine live shadow sessions.
- Outcome resolution and Bayesian cohort updates need accumulated real decisions/outcomes; sparse EP/IPO/reversal cohorts must remain visibly shrunk and shadow-labelled.

## Next executable wave

1. Extend canonical NSE history to 3–5 years with symbol identity/delist/listing-age and point-in-time universe checks.
2. Run and QC tiered Fyers backfill; expose SSE progress and data-quality coverage in Alpha Lab.
3. Add setup-family/event outcome resolver (trigger availability, next-open slippage, MFE/MAE, +1R/+2R/stop timing, gaps).
4. Train a cross-sectional ranking objective and survival model only after the history gate; compare against simple RS/residual-momentum baselines.
5. Accumulate 20+ live shadow sessions, audit calibration/regime stability/subgroups, then consider a capped ranking tilt. Hard gates and position-risk math remain authoritative.

## Protected / unrelated work

Do not stage or overwrite the pre-existing dirty files `alerts/live_fsm.py`, `market_calendar.py`, `scanner/scanner_presets.py`, or `tests/test_live_fsm.py`. Protected risk/governor/replay files were not touched.
