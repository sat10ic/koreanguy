# UniDesk terminal — handoff

Governed by `../plan/UNIFIED_DESK_UI_UX_MANUAL_V2.md` (repo-root `plan/`).
Companion to the backend build tracked in `../unidesk/` (GOAL.md/HANDOFF.md/
TASKS.md) — **separate wave tracking.** The V2 manual's own header already
states this app is a fixture prototype, not the shipped artifact (the
shipped nightly artifact is markdown: `unidesk/momentum/report.py` →
`data/market/reports/tonight_*.md`). Do not treat anything here as live
scan output.

## To continue

**2026-08-29 — Full V1→V2 redesign completed, audited, and visually verified.**

### What happened this session (in order)

1. Built a UI Phase 1 shell against the **V1** manual (`Downloads/
   UNIFIED_MOMENTUM_TRADING_DESK_UI_UX_PRODUCT_MANUAL.md`): nav shell, full
   Home screen, Setups/Stock/Watchlist/Flow/etc.
2. An Opus subagent audited that build (screenshots + source read). Findings:
   amber overloaded across 3 meanings, a scroll rail that clipped a card with
   no affordance, invisible tick guides, an off-canvas active-nav indicator,
   accessibility gaps (missing aria-labels, sub-40px hit targets), duplicated
   tone→color maps. Findings noted, not yet applied.
3. **Mid-session, the backend adopted V2 manuals** (`unidesk/DECISIONS.md`
   D13): the product pivoted from a live intraday cockpit to an **evening
   desk** — read tonight's report, drill in, decide. V1's Flow console,
   trigger queues, and live pulses are explicitly removed or deferred (V2
   §0, §10). This session's V1 build was **not** what got finished — it got
   replaced.
4. **Full redesign to V2**, incorporating the still-relevant audit findings
   inline (not re-run as a separate pass — the V1 widgets most of the
   findings applied to no longer exist):
   - Deleted all V1-only screens/widgets: `Home.tsx`, `Setups.tsx`,
     `SectorHeatmap.tsx`, `OpportunityCard.tsx`, `TriggerRing.tsx`,
     `RoomMeter.tsx`, `RRLadder.tsx`, `ExtensionMeter.tsx`,
     `CorrectionTypeWidget.tsx`, `EvidenceRail.tsx`, `FlowPulseMatrix.tsx`,
     `MomentumPanel.tsx`, `StubScreen.tsx`.
   - New nav (V2 §2): **Tonight / Candidates / Stock / History / Research /
     Settings**. Market/Watchlist/Traders/Journal/Flow are gone from the
     rail — V2 defers or removes them (§10), not worth dead nav entries.
   - New screens: `Tonight.tsx` (the primary product — header, Regime Strip,
     candidates grouped by setup, Yesterday's Calls, Watchlist Drift,
     Honesty Footer), `Candidates.tsx` (filters + scatter + dense cards),
     `Stock.tsx` (rewritten — header, chart, Decision panel, Setup Evidence,
     History strip; no live/social panels, per V2 §5), `History.tsx` (new —
     losses shown exactly like wins), `Research.tsx` (new — ablation ladder,
     leakage suite status, negative findings board), `Settings.tsx` (new —
     mode toggle, data status, honest "no config UI yet" for weights/gates).
   - New widgets: `CandidateCard`, `RegimeStrip`, `HonestyFooter`,
     `YesterdaysCalls`, `SetupEvidencePanel`, `ContributorBars`, `ScrollRail`
     (only fades when the rail actually overflows — checked with a resize
     observer, not assumed).
   - Fixed the audit's amber-overload finding at the root: added a `score-mid`
     cool-blue token + `info` Chip tone, so "warning," "brand accent," and
     "average score"/"fresh breakout" no longer share one hue.
   - Fixed the audit's off-canvas active-rail-indicator bug, missing
     aria-labels (search input, alert bell, mode toggle `role="group"` +
     `aria-pressed`), and bell hit-target (28px → 40px).
   - `lib/ModeContext.tsx` — lifted Beginner/Pro state to a proper React
     context (it was local `useState` inside `AppShell`, which reset on every
     route change — a real bug, not from the audit, caught while wiring
     V2's mode-dependent labels).
5. **Grounded fixtures in the one real report that exists**
   (`data/market/reports/tonight_2026-07-03.md`): the 3 Momentum Burst
   candidates (BANKA/VLEGOV/FILATEX) are verbatim real numbers; the honesty
   footer is verbatim; the universe stats are verbatim. Regime (BULL, 12
   sessions) is real too but pulled forward from N2's classifier output
   ahead of `report.py` being re-run to include it — flagged with a `title`
   tooltip, not silently presented as if `report.py` produced it. Everything
   else (other 7 setup types, Yesterday's Calls, Watchlist Drift) is
   `dataSource: "illustrative"` and renders with a dashed border + visible
   label — see `data/fixtures.ts` header comment for the full inventory.
6. **Visually verified with Playwright** (Chrome extension was not connected
   this session — see `scripts/shot.mjs`, `MSYS_NO_PATHCONV=1 node
   scripts/shot.mjs <outDir> / /candidates /stock/BANKA /history /research
   /settings`). Screenshotted every screen at 1920×1080, read the actual
   images, and fixed two real bugs found by looking:
   - The synthetic OHLC generator's random walk didn't reliably end at the
     candidate's real close, so trigger/invalidation price lines could fall
     outside the chart's visible range. Fixed in `lib/ohlc.ts` — the series
     is now rescaled so the last close exactly matches.
   - Pro mode didn't reach the Decision panel (`DecisionCard` wasn't reading
     `useMode()`) — caught by actually clicking the Pro toggle via Playwright
     and screenshotting, not by inspecting code. `QualityStack` now reads
     mode from context itself by default, so this class of bug can't recur.
   - Also fixed: the amber lifecycle-tone collision (see above) was visible
     in the first post-redesign screenshot and got fixed same-session.

### Verification

```text
npx tsc -b            -> clean
npm run build          -> clean (vite build, ~800KB bundle, one size warning — not fixed, see system.md)
curl :5183/            -> 200, no console/page errors on any of the 6 screens (Playwright pageerror/console listeners, zero hits)
```

### Honest partials / not done this session

- **Base-box (VCP geometry) chart overlay** (manual V2 §5.2) — not
  implemented. Chart has candles/EMA21/EMA50/AVWAP/trigger/invalidation only.
- **Beginner/Pro mode** now correctly propagates everywhere QualityStack is
  used, but nothing else in the app has a pro-only "deeper detail" reveal
  yet (V2 §8: "Pro mode shows the internal terms, contributors, weights,
  and config hash") — only the vocabulary swap is wired, not the extra
  density.
- **Settings** has no actual config-editing UI (honestly disclosed in the
  screen itself) — weights/gates are still edited by changing call-site
  values in `unidesk/momentum` directly.
- **Research** screen's ablation ladder, leakage-suite pass/fail, and
  negative-findings entries are illustrative placeholders in the right
  *shape* (per V2 §7) but not read from any real backend artifact — there
  isn't one yet (ablation needs weeks of recorded live outcomes, GOAL.md
  hard stop #5).
- No tests. No route-level code-splitting (798KB single bundle — flagged by
  Vite's own build warning, not a blocker for a prototype).

### Next slice (suggested)

Wire STOCK's chart to real bhavcopy history for the 3 real candidates
(BANKA/VLEGOV/FILATEX) instead of the seeded-random `lib/ohlc.ts` generator
— the real 646k-bar archive already exists at `data/bhavcopy/` per
`unidesk/GOAL.md`'s N3 entry; reading it requires either a small static
JSON export step or a local API, which doesn't exist yet for this app.
