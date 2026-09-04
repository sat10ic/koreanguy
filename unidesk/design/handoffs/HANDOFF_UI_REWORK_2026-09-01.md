# HANDOFF — UI rework per momentum_trading_os_detailed_design_spec.md

**Date:** 2026-09-01
**Executor:** GLM-5.3-Flash via ZCode
**Spec:** momentum_trading_os_detailed_design_spec.md (owner-supplied design direction)
Attribution-ID: attr-unidesk-ui-rework-glm53flash-20260901-001

## Scope executed (spec §39 phases)

- **Phase 1 — design system / shell.** Tokens migrated to spec palette
  (§5.1: #0A0B0D base, #42C987/#EF6A67/#D5A84E/#6A9DF8 semantics, amber kept
  as the single structural accent); type steps 12/13/20 added; radius
  6/7/9/12; motion durations (§32); focus-visible outline (§33). Sidebar
  rebuilt: 208px expanded / 64px collapsed, text labels primary, persisted
  collapse; Stock removed from primary nav (contextual per §3.1); Market
  added. TopBar rebuilt at 56px: breadcrumb, session date (single source,
  §4.3), session picker, search, Beginner/Pro, stale marker (§29.4).
  New shared components: SectionHeader (§7.1), MetricRow (§7.3),
  MiniCandles (§7.5 — real bars + trigger line, no axes).
- **Phase 2 — Tonight.** Sticky subnav with anchored subsections (§3.2
  preferred). Market State hero 8 cols + Playbook 4 cols (§9.3); hero shows
  regime, explanation, position strip, 20-session breadth micro-bars from
  real archived reports; participation table with per-metric universe
  tooltips and the one real 1D delta (§9.6 critical-validation rule);
  Opportunity Funnel with every step defined from real footer counts
  (§9.7); breadth analytics with sign-derived interpretation words;
  leadership concentration honestly absent (sector/theme universe data not
  emitted — §0.1). Setup feed: real mini-candle thumbnails, "N actionable ·
  M extended" subtitles, non-rankable detectors flagged, collapsed
  empty sections (§10.8). Prior Calls compact strip. Trigger Proximity in
  "prev → now" drift form (§12.3) with approaching/extending tags.
- **Phase 3 — Stock.** ContextRibbon (MARKET / SECTOR / THIS STOCK — §7.8,
  §17.8, sector from vendor mapping with provenance); Beginner verdict with
  WHY score-bands and the three entry questions (§17.6); Pro raw-metrics
  groups as strict superset (§17.7).
- **Phase 4 — Candidates.** Row A: Opportunity Landscape 8 cols + Research
  Lens 4 cols (§15.2, §16 — regime priorities rendered as UI emphasis
  chips, labelled "not a score, not validated weighting"); Row B ranked
  table (unchanged data contract).
- **Market screen (§13, honest partial).** Breadth history line (42 real
  archived sessions) + regime dots; rule-derived Market Character
  (documented thresholds, labelled heuristic, §13.3); Candidates-by-sector
  table from the Chartsmaze vendor mapping (real join, provenance
  disclosed, scope limited to tonight's candidates — market-wide sector
  breadth needs universe-level emission and is NOT faked, §13.4 gap named).
- History/Desk/Research/Settings inherit the new shell/tokens (charter
  framing, X-02/X-05 wording unchanged).

## Not built (data does not exist — §0.1)

- Sectors/Themes screens (§14): full sector breadth/RS/theme model needs
  universe-level sector joins in the nightly.
- Watchlist buckets FOCUS/BACKUP/DEVELOPING (§18) and Portfolio heat/exposure
  (§19): no watchlist store; register/positions exist on Desk only.
- Catalyst layer (§21), ASM/GSM panel (§20), RS-trend sparkline column
  (§15.5): fields not emitted (ADR IS shown; ASM/GSM/earnings absent).
- Tradeability panel inputs beyond circuit/liquidity gates already disclosed.

## Verification

- `npm run build` green after each phase; browser-verified Tonight, Market,
  Candidates, Stock, Desk at 1440×900 against the spec §38 must-not-happen
  list; zero console errors.
- No data-truth regressions: all display values still trace to
  tonight_<date>.json / stock_history / outcomes / broker namespace.
