# UX Craft Re-audit and Repair Ledger — 2026-07-13

Verdict: **PARTIAL PASS — named repairs verified; remaining defects explicitly open.**

This ledger supersedes treating `UX_CRAFT_AUDIT_2026-07-12.md` as a completion record. That file is a defect inventory with a CONDITIONAL verdict.

## User-named audit items

| ID | Current status | Evidence checked | Remaining work |
|---|---|---|---|
| #31 reduced motion | PASS | Guards exist in App, Market, Scanners, Shortlist, Debate, Alpha, Positions, Journal/Ledger, Trade Plan, live-work, primitives and token CSS. | New CSS must retain the guard. |
| #19 Debate pipeline note | PASS | `DebateTab.jsx` renders `card.errors` in clickable `<details>` with traceable messages. | Browser fixture with a real error remains useful. |
| #23 Positions origin thesis | PASS | Existing thesis links to symbol/date debate; navigation callback is wired. | None found. |
| #49 no-thesis dead end | PASS | Manual/pre-log position explains why no thesis exists and provides “Run debate”. | None found. |
| #25 Journal manual write | PARTIAL | Manual trade add, numeric inline edit and delete are implemented and API-backed. | Manual lesson entry is still missing; filesystem lessons are read-only. |
| #28 keyboard shortcuts | PASS | Global keydown handles `/`, `?`, Escape and `g` destination chords; help lists shortcuts. | Browser smoke test still required for every chord. |

## Repairs in this wave

- Restored Strong Start discoverability: nav now reads `SHORTLIST / SS`; Strong Start renders immediately below Curator delta instead of after every shortlist row.
- Switched all four debate seats from paid models to explicit current OpenRouter `:free` models. Vision uses a free multimodal endpoint. `config.yaml` remains local/uncommitted by policy.
- Recovered canonical ChartsMaze historical industry data from the already-downloaded `industry-graphical-view.csv` static asset.
- Added `chartsmaze_industry_history` with raw cumulative values and source-file provenance.
- Imported 27,776 observations: 112 industries, 2025-07-10 through 2026-07-10.
- Multi-horizon theme returns/RS now derive from preserved daily history at 3D/1W/1M/3M/6M.
- Added chart-drawer comparison pane: stock vs recorded ChartsMaze industry vs Nifty MidSmallcap 400, all rebased to 100 on the first observation.
- Browser QC found and repaired two hidden ChartDrawer regressions: the v5 token resolver read the wrong DOM root, and the drawer's structural CSS had been deleted. A third bug passed color functions instead of color strings to Lightweight Charts; repaired and re-rendered.

## Panel audit

### Scanners / Strong Start

- Strong Start exists and has two populated names on the audited 2026-07-10 payload.
- The mechanism was below a very long shortlist and therefore effectively undiscoverable; repaired.
- Open: Scanner result density/filtering and beginner glyph-label cleanup from the original audit remain.

### Debate

- Pipeline notes, list relationship legend and behaviour-first Alpha facts are present.
- Free-model configuration repaired.
- Open: long-page navigation/collapse and voter-denominator explanation remain material UX debt.

### Journal

- Manual trade add/edit/delete are present.
- Open: manual lesson writing and clearer operational-vs-directional explanation remain.

### Alpha

- Row actions, relationship badges, structured research bench and honest model states are present.
- Open: the current data remains shadow evidence; no model is promoted.

### Market lower section

- Broader indices, sector heatmap, ChartsMaze sectors/themes, RS/returns, movers, deals and FII/DII data are present.
- Open: the nested legacy MarketTab remains denser and less typographically consistent than the Round-4 shell; it needs a dedicated v5 component decomposition rather than further CSS accretion.

## Verification

- Targeted Python: 86 passed.
- Desk Vitest: 37 passed.
- Desk production build: passed; existing large-chunk warning remains.
- Live comparison payload for UNIPARTS: 250 stock points, 248 theme points, 234 broad-index points; industry resolved to `Industrial Products & Manufacturing`.
- Browser: Strong Start is above the long shortlist; ChartDrawer opens as a modal and the `vs theme / index` pane renders. ADANIGREEN correctly labels its theme unavailable because its stored shortlist record has no industry mapping.
- Direct live database import count and importer result agree on 27,776 historical rows.

## Explicitly not certified

- Full 7-tab × beginner/expert × normal/empty/stale screenshot matrix was not completed in this wave.
- Manual lesson creation.
- Scanner filters/sorting and all beginner copy/glyph cleanup.
- Debate internal navigation and voter-denominator redesign.
- Full v5 decomposition of lower Market movers/FII-DII surfaces.
