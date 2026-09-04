# HANDOFF scouting_wire_2026-08-24 -- COMPLETED

## Outcome

The fourth visual direction — **Scouting × Wire** (`design/REDESIGN_SCOUTING_WIRE.md`,
owner-approved 2026-08-24) — is built in full against the real API and database,
with the XP fix (C8) that the direction required landed first.

- **Token layer + shell.** `ui/src/styles/tokens.css` carries the binding dark
  token set (`--ground/--raised/--sunken/--edge/--hair/--ink` ladder/`--risk/
  --up/--down/--caution/--caution-bg`, radius 0, no shadows; hero 33 · value 15 ·
  body 12.5 · gloss 11.5 · meta 10.5 · kicker 9.5). One 1px `--edge` rule per
  region, no nested boxes; mono tabular numerics; sentence-case prose; uppercase
  kickers only. `App.jsx`: `NAV_TABS = [TODAY, LEDGER, TRADERS, IDEAS, LIBRARY,
  MARKET]`, route-only `STYLE` and `SYMBOL`, legacy `?tab=FEED/BREADTH` →
  `TODAY/MARKET` mapping, review badge on TODAY, MockBanner, ⌘K command bar
  (tabs/traders/symbols palette), `Stat` explained-stat component in `ui.jsx`.
- **TODAY** (was FEED): review queue above four computed bands — Money moved
  (`trade_event` + stated price), Names to watch, Background, Removed
  (non-empty only) — each with a why-line; rows of band label · handle ·
  verbatim post · payload-derived gloss · time; filters + load-more preserved.
- **LEDGER**: `PositionBars` remapped to an **ECharts custom series** shared
  time axis (signature element; lanes, add/stop markers, clip colour by state),
  outcome-in-words strip, `--caution` line for unstated, computed overlap
  sentence ("Fastzone and Manas were both in FCL at the same time."), sortable
  table + evidence/media containment beneath (W3c rules kept).
- **TRADERS**: one question at a time (Segmented: stop-kept default), ranked
  with `n` visible; §6 thresholds → dimmed bar + em dash "— too few", never a
  percentage; verbatim one-liner beneath; roster + profile + StripPlot/Dumbbell/
  StackedArea/CalendarGrid with labelled empty states.
- **IDEAS + LIBRARY**: symbol grouping with inline-SVG mention heat strips,
  verbatim quotes, follow-through ("nobody has bought it" when true), protected
  footnote; Library quote-hero + `--raised` practice block with the 10-trade
  minimum ("Not enough to say yet — only N trades link to this. We won't score
  it until 10.").
- **MARKET** (was BREADTH): deliberately quiet, **zero `--risk`**, hero XP with
  band meaning + age, worded ribbon legend, cumulative A/D (ECharts) from
  additive `advances/declines`, stances + agreement with protected footnote.
  **No §8 caution block** — XP is fixed this wave.
- **Market prerequisite — C8 fix landed and production-recomputed**: percent
  inputs restored (retracted C6 conversion removed), reseed z-state seeds from
  observed `up_4pct`, `regime_daily.backfill(warmup_sessions=20)` discards the
  series-start transient. Production: 431 rows, 0 cap hits, 0 EXTREME, max
  81.31, LOW 349/BUILDING 67/STRONG 15, latest-5 parity True; pre-change backup
  `data/traderlog.db.backup-pre-xpfix-20260824`. See `AUDIT_LEDGER.md` C8/I12/
  G12 addenda.
- **SYMBOL landing page + API**: new `GET /api/symbol/{symbol}`
  (`validated` = rows in bhavcopy `daily_prices`; named empty states when not
  validated), candles via **lightweight-charts** ^4.2.3 (new dependency),
  corpus context (positions, mentions); `/api/breadth` history +`advances/
  declines`; `/api/traders` +`stop_stated_pct/stop_honored_pct`; `api.js`
  `fetchSymbol`; `CONTRACTS.md` §8 updated in the same change.
- **Tests**: `test_pc_layout.py` + `test_browser_review.py` rewritten to the
  new DOM (grid, containment, review flows, ⌘K, bands — with the 1709px-media
  containment regression kept); one browser test in `test_feed_pagination.py`
  updated; new `tests/test_scouting_wire.py` (8 tests: band order/lifecycle,
  banding rules, accent scoping, Rule-1 gloss, symbol page, traders thresholds,
  ⌘K, market hero/ribbon/no-caution).

## Honest partials

- The Removed band waits for a real production deletion (0 rows today; lifecycle
  covered by a disposable-DB test).
- Today's trader-record glosses wait for `trader_style` ≥ 10 closed positions
  (W6); `trader_style` empty today → TRADERS honestly renders "— too few".
- First persisted XP session (2024-09-30) reads 30.9 BUILDING — cosmetic carry
  from the discarded warm-up chain (AUDIT_LEDGER I12).
- The play-type `StackedArea` on TRADERS renders its labelled empty state until
  the feed payload carries `play_type` (out of scope; honest state today).
- Screenshots are structural evidence (headless); pixel-level appearance is for
  the owner's eyes in `output/playwright/scouting-wire/`.

## Verification (orchestrator, personally re-run)

```text
python traderlog/run_checks.py          -> exit 0 (db/ingest/parse/golden/
   attribution/derive/ui pass; telegram dry_run); STATE.json updated
python -m pytest traderlog/tests -q     -> 283 passed, 2 warnings (0 failed)
npm run build (traderlog/ui)            -> clean (vite 5.4, 1264 modules)
live 1920x1080 probe, production API    -> PASS on TODAY/LEDGER/TRADERS/IDEAS/
   LIBRARY/MARKET/STYLE/SYMBOL: grid 1680@x=120, docScrollW 1920, 0 panel
   overflow, 0 console/page errors, 0 >=400 responses; bands ordered
   [money, watch, background]; risk mark only on money rows; MARKET 0 risk-
   colored elements, no caution text, hero age present; Symbol page renders
   candles for 20MICRONS; Ctrl+K palette opens, filters, navigates to MARKET
XP recompute (production, after backup)  -> 431 rows, at_cap 0, EXTREME 0,
   max 81.31, reseed_points ['2025-06-20'], latest-5 parity True
```

## Attribution

Attribution-ID: attr-scouting-s1-executor-20260824-001

Attribution-ID: attr-scouting-s2-executor-20260824-001

Attribution-ID: attr-scouting-s3-executor-20260824-001

Attribution-ID: attr-scouting-s4-executor-20260824-001

Attribution-ID: attr-scouting-s5-executor-20260824-001

Attribution-ID: attr-scouting-s6-executor-20260824-001

Attribution-ID: attr-scouting-s7-executor-20260824-001

Attribution-ID: attr-scouting-s8-executor-20260824-001

Attribution-ID: attr-scouting-s9-executor-20260824-001

Attribution-ID: attr-scouting-s10-executor-20260824-001

Attribution-ID: attr-scouting-orchestrator-flash-20260824-001

## Files changed

- `adopted/xp.py`, `adopted/regime_daily.py` — C8: percent convention, observed-z
  reseed, warm-up; comments corrected across `db/schema.sql`,
  `adopted/universe_breadth.py`, `config.example.yaml`.
- `api/app.py` — `/api/symbol/{symbol}`; breadth advances/declines; traders stop
  fields. `design/CONTRACTS.md` §8.
- `ui/src/styles/tokens.css`, `app.css` — scouting tokens + shell.
- `ui/src/App.jsx` — nav renames, ⌘K, SYMBOL route. `ui/src/components/ui.jsx`
  (Stat + restyle), `ui/src/components/CommandBar.jsx` (new),
  `ui/src/components/charts.jsx` (renderer remap + StackedArea + CalendarGrid).
- `ui/src/screens/Today.jsx` (replaces Feed.jsx), `screens/Ledger.jsx`,
  `screens/Traders.jsx`, `screens/Ideas.jsx`, `screens/Library.jsx`,
  `screens/Market.jsx` (replaces Breadth.jsx), `screens/Symbol.jsx` (new),
  `screens/Style.jsx` + per-screen `styles/*.css` (today/ledger/traders/ideas/
  library/market/symbol).
- `ui/package.json` + lock — lightweight-charts ^4.2.3. `ui/src/api.js`.
- `tests/test_pc_layout.py`, `tests/test_browser_review.py`,
  `tests/test_feed_pagination.py` (one browser test), `tests/test_scouting_wire.py` (new),
  `tests/test_api_filters.py`, `tests/test_adopted_xp_mbi.py`,
  `tests/test_adopted_regime_daily.py`.
- Docs: `design/REDESIGN_SCOUTING_WIRE.md` (spec, unchanged), `VISUAL_LANGUAGE.md`
  (supersession banner), `WIREFRAMES.md` (rewritten), `DECISIONS.md`,
  `AUDIT_LEDGER.md`, `TASKS.md`, `HANDOFF.md`, `STATE.json` (via checks),
  `design/MODEL_WORK_LOG.jsonl`.
- `data/traderlog.db` — regime_daily recomputed (pre-change backup
  `data/traderlog.db.backup-pre-xpfix-20260824`).

Nothing committed — the maintainer QCs and commits.