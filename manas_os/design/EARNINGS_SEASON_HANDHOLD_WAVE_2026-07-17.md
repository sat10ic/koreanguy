# EARNINGS-SEASON WAVE — EP / Strong-Start / IPO-base hand-holding (2026-07-17)

User ask (verbatim intent): earnings season starting; get dates + results from online sources,
link to Stockbee/TradeTM EP methodology, and make the WHOLE process hand-held — same for Arora
strong-start/busted setups and IPO-base breakouts. Explainer copy bar raised: current drafts
"very poor and bland" → apply ux-writing-skill discipline (see memory feedback-explainer-copy-bar).

## What already exists (verified on disk 2026-07-17 — do NOT rebuild)
- ChartsMaze daily dump: `earnings-gap-up.csv` + `positive-earnings-reaction.csv` — both ALREADY
  ingested (`sources/chartsmaze_scanners.py` L49/L58) = day-of EP reaction feeds.
- `sources/disclosures.py` — corporate announcements (results filings land here), bulk/block/insider.
- `sources/fundamentals.py` — quarterly `symbol_fundamentals` via yfinance: eps, revenue,
  eps_yoy/qoq, sales_yoy, opm → surprise/acceleration computable.
- Detectors: EP (`engine/eod_detectors.py`, neglected-base per spec), ipo_base (mini-coil+TVCP),
  busted_reversal family, launch_pad; Focus Center EP/IPO lens; guided flow `/api/flow/today`;
  live FSM stage-1 (paper) for strong-start; journal→outcomes→expectancy loop.
- Auto-advance update (2026-07-17 fix): pipeline catches up all pending sessions per click.

## The ONE missing data piece: forward earnings calendar
We know reactions after the fact; we don't know WHO REPORTS TOMORROW. Build
`sources/earnings_calendar.py`:
- **Primary: BSE board-meetings API** (api.bseindia.com, no cookie wall; purpose filter
  "Results"). Map BSE scrip→NSE symbol via existing symbol master.
- **Secondary: NSE event-calendar** (nseindia.com/api/event-calendar; needs NSE cookie dance —
  reuse/extend the Playwright session the chartsmaze extractor already maintains if raw requests
  are blocked).
- Table `earnings_calendar(symbol, meeting_date, purpose, source, fetched_at)` point-in-time;
  stage registered in the pipeline (fetch leg + ingest leg). Idempotent upsert.
- API `GET /api/earnings/upcoming?days=7` → {date → [symbols in universe, with float/ADR/RS/
  base-state chips]}. Honest empty state when the fetch failed.

## The hand-held loops (workflow packaging, guided-flow steps)
### EP (Stockbee/TradeTM)
1. **Evening before**: flow step "Earnings tomorrow: N universe names" → EP-PREP list, each with
   one trader-voice line (float, ADR, RS, base posture, last-quarter reaction).
2. **Day of, EOD**: EP detector on actual reaction (gap+RVOL+delivery_z+neglected-base) joined
   with the calendar (reported today = catalyst confirmed, not rumor) + surprise numbers from
   fundamentals → full plan card (entry/stop/qty from risk engine, one-writer).
3. **Live (when armed)**: EP-PREP names feed the strong-start monitor at open; 9:15-9:45 confirm
   → alert. Paper until live-loop graduation criteria met (unchanged).
4. **Learning**: TAKEN/SKIPPED → outcomes → expectancy cell ep×regime (exists; now fed daily).

### Strong-start / busted (Arora)
- Pre-open watchlist = EOD candidates + EP-PREP; live FSM confirms strong start (gap holds,
  above OR-low/VWAP, RVOL) → guided step with the exact plan. Busted setup = failed-breakout
  reversal teaching card (India cash: exit/avoid coaching, not shorting).

### IPO base
- Detector exists; hand-holding = stage narration on the card ("day 7 in a 4% range under 512
  pivot — the wait IS the setup") + armed trigger + explicit WAIT state.

## Copy bar (applies to ALL of the above + existing cards)
Framework: ux-writing-skill (purposeful/concise/conversational/clear; tone mapped to state;
before/after test) + practitioner-tweet voice (situation → honest con → what to watch/do).
- Grounded: every number from the card's computed fields; no invented stats.
- Trader voice: "Reported 42% EPS growth this morning, gapped 7% on 4x volume and held it.
  Circuit band is 10% — size for a fast exit." NOT "this shows a positive earnings reaction".
- Honest con mandatory per card (circuit, extension, thin delivery, late leg).
- One shared `engine/read_builder.py` (or extend existing read/copy layer) with per-setup
  templates; ban-list lint in desk_gate for bland stems ("this shows", "consider", "may
  indicate").

## Sequencing (after the auto-advance catch-up verifies + commits)
1. `sources/earnings_calendar.py` + table + stage + `/api/earnings/upcoming` (backend, tests).
2. EP-PREP flow step + evening watchlist (backend flow + desk rail).
3. Copy layer rewrite to the bar (desk-wide, gate-linted).
4. Live strong-start arm of EP-PREP (rides P4 live loop, paper first).
Validation: this earnings season IS the test window — every EP the calendar caught vs missed
logged to LEARNINGS; practitioner-pick probes (NUVOCO-class EP days) must surface or name the
specific refusing gate.
