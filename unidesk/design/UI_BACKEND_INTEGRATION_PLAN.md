# UI ⟷ backend integration cadence

Status: controlling plan for wiring `unidesk/` backend output into
`unidesk_terminal/`. Created 2026-08-30.

## Where things actually stand (verified, not assumed)

- The UI has **zero data wiring**. `grep -rl "fetch(\|axios\|useQuery"
  unidesk_terminal/src` returns nothing outside `fixtures.ts`. Every screen
  renders from one static file.
- `fixtures.ts` already distinguishes real from invented data with a
  `dataSource: "illustrative"` tag per record — this convention is correct and
  must survive into the real API.
- The backend's only shipped artifact is Markdown
  (`unidesk/momentum/report.py` → `data/market/reports/tonight_*.md`). There is
  no JSON output anywhere in the pipeline.
- `unidesk/contracts/*` already defines 12 frozen dataclasses (market,
  candidate, setup, geometry, flow, social, decision, research) with a stable
  `to_dict()` — this is the ready-made JSON boundary; nothing new needs
  inventing for serialization.
- This is a nightly EOD desk (D9/D10), not a live app. **The integration
  target is static JSON files the UI reads at load time, not a running
  server.** A server is only justified later if a live module (N7) demands it.

## The bridge: one JSON sibling per report, emitted by contracts

`report.py` already builds the typed objects it renders to Markdown. Add:

```
data/market/reports/tonight_<date>.json
```

— an array of the same `contracts.*` objects, via their existing `to_dict()`,
written alongside the Markdown in the same `nightly.py` run. No new data model.
No second source of truth: the JSON and the Markdown are two renders of the
same in-memory objects, generated in the same call.

> **CORRECTION (2026-08-30, Cline):** the premise "`report.py` builds the typed
> objects it renders" is **not what the code does**. `report.py` and
> `scan_universe()` work directly off `ScanResult`/`SymbolScan` (scan.py), a
> lighter dataclass pair, not the frozen `contracts.candidate`/`contracts.setup`
> objects (those require fields — `snapshot_id`, `geometry_snapshot_id`,
> `config_hash`, quality scores — that scan_universe never computes).
> `momentum/report_json.py` therefore builds its dicts directly from the same
> in-memory `ScanResult`/`SymbolScan` and reuses `contracts.base.to_dict()` only
> for datetime/enum serialization. Constructing fake contract instances just to
> call `to_dict()` would mean inventing data, which the honesty rules forbid.
> The "same in-memory objects, two renders, no re-derivation" goal holds; the
> mechanism is the scan dataclasses, not the frozen contracts.

**Rule, non-negotiable:** every JSON record carries the honesty-footer facts
that already exist in the Markdown — universe size, skip count, regime
built/not-built, adjustment status — as fields, not as prose the UI has to
parse. The UI must be able to render "not built yet" without scraping text.

## Cadence — one screen wired at a time, gated on real backend coverage

Wiring a screen before its backend data is real just moves the fixture
problem into the UI layer with a JSON label instead of a `.ts` label. Each
step below only starts once its "Backend must produce" column is true, checked
against `run_checks.py` / `TASKS.md`, not assumed.

| Order | Screen | Backend must produce | Status today |
|---|---|---|---|
| 1 | **Tonight** | `tonight_<date>.json` from N1 (universe scan + setups) | N1 done; JSON emission not built |
| 2 | **Candidates** | per-candidate `contracts.candidate` + `contracts.setup` objects, geometry/entry-quality scores | built (N1/W-E); needs the JSON emitter |
| 3 | **Stock** | point-in-time market state for one symbol (`get_market_state`) | **blocked on U-P0.3**, not built |
| 4 | **History** | outcome-labelled events from the research spine, adjustment-basis-checked | blocked on Opus's stage-1 conditions 3–4 (adjustment guard on archive attach) — do not wire until those land, or History will render the corrupted MAE/stop-hit values verbatim |
| 5 | **Research** | walk-forward / ablation results (N5) | **NO-GO per the stage-3 verdict below** — do not wire until N5 is lifted |
| 6 | **Settings** | config surfacing only (detector toggles, cost assumptions version) | mechanical once contracts are read-only-exposed |

Order 1–2 can start now (stage-1 work does not block it — it is a separate,
additive JSON emitter, not a change to research internals). Orders 3–6 are
each individually gated; do not wire ahead of the gate to "make more screens
real" — that reintroduces exactly the fixture-mislabeled-as-real risk the
`dataSource` convention exists to prevent.

## Every wired screen carries its own honesty footer

Per screen, once wired: an explicit banner reading real coverage from the JSON
— "233 sessions, regime BULL, adjustment basis: 4 confirmed CA, 194
unconfirmed excluded" — never a silent, confident-looking table. This is the
same discipline as TraderLog's `unresolved[]` and denominator rules; it is
what makes a swap from fixture to real data safe to do incrementally without
a big-bang cutover.

## What does NOT change

- `unidesk_terminal/` stays a separate Vite/React app; no framework change.
- No live server, no websocket, until N7 is owner-requested.
- Fixture data stays in the repo as a fallback/demo mode, clearly labelled,
  never silently substituted for missing real data.
