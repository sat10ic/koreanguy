# HANDOFF — Tonight/Candidates screens wired to real scan data — COMPLETED

Date: 2026-08-30. Executed by a Sonnet subagent scoped to `unidesk_terminal/`
only (the concurrent `unidesk/research/` archive-attach slice held write
scope there); logged into the shared ledger by the orchestrating session
per the executing agent's own "FOR THE ORCHESTRATOR TO LOG" section, after
independently verifying the commit.

Attribution-ID: attr-unidesk-ui-tonight-candidates-wired-claude-sonnet5-20260830-001

## What was built (orchestrator-verified against the actual commit)

Commit `6cd84a67`, 13 files, all under `unidesk_terminal/`
(`git show --stat 6cd84a67` confirmed no file outside that directory).

- `src/data/tonight.ts` (new) maps the real
  `data/market/reports/tonight_2026-08-28.json` (268 real candidates across
  8 detectors) onto the shared `Candidate` type, bundled at build time as a
  static Vite JSON import (`src/data/tonight_2026-08-28.json`) — no server,
  no fetch, matching the EOD-nightly nature of this product.
- `Tonight.tsx` and `Candidates.tsx` now render real candidates alongside
  the existing illustrative fixtures, distinguished by a "REAL SCAN" badge
  and a "RAW SCAN SIGNALS — NO QUALITY SCORE COMPUTED" card path for fields
  the scan doesn't supply (quality scores, trigger/invalidation prices,
  narrative, lifecycle, company/sector) — never blended with fixture
  numbers for those fields.
- Header stats (universe scanned 2,710, skipped 287) and the honesty
  footer now read live from `honesty_footer` in the JSON, not fixture
  strings.
- Regime strip honestly shows "Regime not built yet" (from
  `honesty_footer.regime_built: false`), demoting the old fixture BULL
  regime display to a dashed "illustrative preview" beneath it.
- Yesterday's Calls / Watchlist Drift sections — no real backend for
  either exists yet — newly tagged illustrative (were untagged before).
- Bug found and fixed during the agent's own Playwright verification: a
  duplicate-React-key collision (one symbol can appear under multiple
  setup detectors) — fixed with composite `symbol-setupType-dataSource`
  keys.
- `Stock.tsx`/`History.tsx`/`Research.tsx`/`Settings.tsx` left untouched
  per the integration plan's gating.

## Verification (orchestrator-independent, plus the agent's own)

```text
git show --stat 6cd84a67   -> 13 files, all under unidesk_terminal/, confirmed
git status --porcelain unidesk_terminal   -> clean after the commit
```

Agent's own reported build/lint (not independently re-run by the
orchestrator this pass, since the app has no test suite beyond these two
commands and the diff was read directly instead):

```text
npm run build -> tsc -b && vite build: clean, 2433 modules, ~1s
npm run lint  -> oxlint: clean (1 pre-existing unrelated warning)
```

Manually verified by the agent via the Playwright/Chrome browser pane on
`/tonight`, `/candidates`, `/stock/BIL` (real-scan symbol with no fixture
match, graceful fallback), `/stock/BANKA` (fixture symbol, unaffected) —
zero console/page errors after the duplicate-key fix.

## Important context this slice does NOT account for

A concurrent audit (`a91a9fbb05b9b7926`, completed the same session) found
that several of the 8 detectors now visible in this UI have real
trading-logic defects — most notably `base_breakout`, which has no
condition testing for an actual breakout and whose `room_adr` rule is
inverted (rejects genuine breakouts, selects laggards). The UI's "RAW SCAN
SIGNALS — NO QUALITY SCORE COMPUTED" framing and "Rule outputs, not
recommendations" disclaimer (inherited from `report_json.py`) are honest
about these being unscored rule output, not validated signals -- but
neither the UI nor this slice adds any detector-specific warning. A future
slice should consider surfacing per-detector trust status (e.g. flagging
`base_breakout` and `reversal_reclaim` specifically) once the audit's
findings are triaged and fixed, rather than relying solely on the generic
disclaimer.

## Still open / next slice

- Multi-date report picker: `tonight.ts` currently hardcodes
  `tonight_2026-08-28.json`. A future session should either automate
  copying the newest report in, or add a picker once a second dated report
  exists.
- `Stock.tsx` wiring to real per-symbol data remains blocked on U-P0.3,
  unchanged.
- Per-detector trust/warning surfacing, per the audit finding above.

## Files

`unidesk_terminal/src/data/tonight.ts` (new),
`unidesk_terminal/src/data/tonight_2026-08-28.json` (new),
`unidesk_terminal/src/data/fixtures.ts`,
`unidesk_terminal/src/lib/status.ts`,
`unidesk_terminal/src/screens/Tonight.tsx`,
`unidesk_terminal/src/screens/Candidates.tsx`,
`unidesk_terminal/src/components/widgets/{CandidateCard,RegimeStrip,CandidateScatter,DecisionCard,SetupEvidencePanel,StockChart}.tsx`,
`unidesk_terminal/tsconfig.app.json`.
