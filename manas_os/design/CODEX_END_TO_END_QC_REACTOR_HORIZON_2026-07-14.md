# sat10ic os end-to-end QC — Reactor analogue, Horizon and Gemini review

Date: 2026-07-14  
Reviewer/repair owner: Codex  
Verdict: **CONDITIONAL PASS for local research and shadow use.** The desk, API,
scanner cards and beginner journey are operational. No new alpha model is
promoted and no automated execution authority was added.

## Evidence-backed outcome

- **Certain:** full Python suite: `794 passed, 9 skipped`.
- **Certain:** desk unit suite: `37 passed`.
- **Certain:** production desk build completed.
- **Certain:** Playwright beginner/expert journey: `2 passed`; MARKET, SCANNERS,
  SHORTLIST, DEBATE, POSITIONS, JOURNAL and Alpha Lab rendered without console
  errors.
- **Certain:** scanner preset endpoint returns 20 cards, 18 populated counts in
  422 ms on the final live check (`2026-07-13`).
- **Certain:** Alpha endpoints return in roughly 0.01–0.11 seconds after the
  one-time schema lock repair.
- **Certain:** desk hard-code and contrast gates pass.
- **Certain:** the locked-files gate intentionally reports the reviewed changes
  to `risk/plan.py`, `regime/governor.py`, `scanner/candidates.py` and
  `scanner/gates.py`. This is not bypassed or labelled green.

## Critical defects found and repaired

### API and runtime

- Repaired invalid syntax in the debate context pack.
- Restored post-chair visual QC and separated Gemini's pre-debate chart observer
  into `agents/observer.py`; the two agents no longer overwrite one contract.
- Removed duplicate debate calls, invalid indentation and shared SQLite use
  across worker threads.
- Reused caller-owned database connections through risk/governor paths.
- Fixed `sqlite3.Row.get(...)` crashes in the live alert state machine.
- Fixed the Alpha schema readiness cache: a replaced test database or reused
  in-memory connection identity can no longer skip required tables.

### Beginner workflow and risk boundary

- Restored the compatible six-step daily flow: Data → Regime → Positions →
  Setups → Order Ticket → Done.
- Kept Gemini's clickable action/target fields, including direct Trade Plan and
  Friday Journal routing.
- Candidate research remains visible before profile onboarding by using an
  explicit conservative LEARNING research sizing context.
- Actual risk validation still refuses an incomplete trader profile. Research
  fallback therefore does not become live/manual quantity authority.
- Removed the invented `days_tracked > 0` Strong Start gate.

### Scanner cards

- Removed 18 parallel request-time count jobs from `ScannersTab`.
- Added one batch count path over persisted discovery and ChartsMaze artefacts.
- Archetype card counts never trigger a hidden full-universe discovery rebuild.
- Arora baseline and Today's Movers counts now use bounded market-session SQL,
  not a window sort over the complete 1.25M-row history.
- Missing nightly archetype data reports unavailable rather than pretending
  there were zero opportunities.

## Reactor abnormal-activity analogue

Implemented as an explicitly named **EOD abnormal-activity analogue**, not the
publisher's proprietary Reactor Scale and not proof of institutional identity.

- Official NSE bhavcopy inputs only.
- Direction unresolved by design.
- Shadow/research use only; it cannot change tradability, risk or quantity.
- Cross-sectional stale/suspended rows are excluded.
- Persistence streaks reset across missing-session gaps.
- APIs: `/api/alpha/activity` and `/api/alpha/activity/{symbol}`.
- Wired into Alpha Lab, Debate Alpha Card and the debate evidence context.
- Current approximation formula:
  `1.1048768252*q + 1.0099667732*d + 1.1730986222*(q*d)^0.825 - 0.14`.

**Unverified:** exact parity with the supplied CSV remains impossible without
the publisher formula or equivalent tick/order-flow footprint input. This is
labelled honestly in the UI and research documentation.

## Horizon integration

Added the useful governance/research layer without allowing it to override the
trading governor:

- immutable experiment and failure memory;
- trial lineage and repeated-hypothesis accounting;
- factor IC/RankIC health and ablation records;
- performance cones and plateau records;
- HMM transition persistence and asymmetry evidence;
- Alpha Lab research-quality views and APIs.

**Unverified/not implemented:** exact Deflated Sharpe Ratio. The supplied source
contains the required formula as an image, so inventing a textual formula would
violate source fidelity.

## Data state verified

- 424 distinct official bhavcopy sessions: 2024-09-02 through 2026-07-13.
- 1,256,174 total daily-price rows; 925,615 EQ rows.
- Zero EQ rows missing trade count.
- 30 recent abnormal-activity sessions computed: 71,389 signals; 2,341 symbols
  on 2026-07-13.
- `--all-local` ingestion checks the date inside each file rather than trusting
  a holiday/mirror filename.

## Model-promotion finding

The sector-downside shadow model no longer beats its sector base-rate baseline
after the history extension (Brier model about 0.1783 versus baseline about
0.1727). This is a healthy gate failure: the model remains not-for-display.
The old integration test was corrected so it verifies the current promotion
verdict instead of demanding retrospective retuning.

## Remaining risks

- The git worktree contains extensive pre-existing Gemini/user changes and
  deleted study material. They were preserved; no reset or blanket cleanup was
  performed.
- Fyers intraday backfill remains dependent on external authentication.
- The production bundle is about 605 kB minified; code splitting is advisable
  but not a correctness blocker.
- `pytest` completes successfully but Windows emits a benign temp-directory
  cleanup `PermissionError` after the test summary.
- FastAPI's `on_event` API and three SHAP colormap calls emit deprecation
  warnings.
- Locked risk/governor/scanner files require maintainer review before commit.
