# UI BUILD DIRECTION — Round-4 LIGHT debate design → production desk

Written 2026-07-11 (Fable director pass). Executable by a Sonnet coder + QC reviewer.

**Design of record:** `manas_os/design/bakeoff/round4/debate_merged_light.html`.
This LOCKED mockup **supersedes UI_OVERHAUL_HANDOFF.md §4's palette/type paragraph**
(dark charcoal + Barlow Condensed is dead; warm off-white + Fraunces/Public Sans/IBM Plex
Mono is the law). Everything else in the handoff still binds: §4 composition rules
(one dominant question per screen, verdict before metrics, no card farms, motion marks a
real change once), §5 DEBATE surface spec, §6 one-writer-at-a-time waves, §7 QC loop,
and CODEX_HANDOFF §0 mission (honest 0-live, deterministic risk sovereign, beginner-legible,
no synthetic data in production).

**Scope discipline:** this is a per-screen migration, NOT a reskin. The old 84 KB
`desk/src/App.css` and the dark `tokens.css` stay untouched and keep serving the
unmigrated tabs (MARKET, SCANNERS, SHORTLIST, POSITIONS, JOURNAL, PLAN). Only the app
SHELL (Wave 1) and DEBATE (Wave 2) move to the new system. Nothing in the old
stylesheet is deleted until UI-7 close-out.

---

## 1. TOKEN STRATEGY — `desk/src/styles/tokens.v5.css`

A NEW file, loaded **after** the existing `tokens.css` in `main.jsx`. It does NOT
redefine the old `--bg/--ink/--accent` names (that would blind-reskin every tab).
All v5 tokens are net-new names, plus one scoping class.

**Scoping rule:** v5 visuals apply only inside `.v5` (set on the shell wrapper in
Wave 1 and on DebateTab's root in Wave 2). Old tabs render inside the v5 shell but
their body markup keeps old classes → old App.css rules still win for them because
v5 styles are written against v5 class names (`.v5-*` prefix), never against old
selectors. No `!important`, no selector wars.

### Exact token set (values verbatim from the mockup's `:root`)

```css
.v5, :root {
  /* canvas / surface steps (warm off-white "newsprint" ramp) */
  --v5-canvas:    #f7f6f2;   /* page bg  (mockup --bg) */
  --v5-canvas-1:  #f2f0e9;   /* sunken   (--bg-1) */
  --v5-panel:     #fffdf9;   /* raised   (--panel) */
  --v5-panel-2:   #f3f1ea;   /* inset chip bg (--panel-2) */
  --v5-panel-3:   #ece9df;   /* deepest inset / tape bg (--panel-3) */

  /* hairlines */
  --v5-line:      #e2ddd0;
  --v5-line-soft: #ebe7db;

  /* ink ramp */
  --v5-ink:       #17181b;
  --v5-ink-dim:   #43464e;
  --v5-ink-mute:  #6b6f78;
  --v5-ink-faint: #9a9da5;   /* decorative ONLY — never essential copy (handoff §4) */

  /* accents */
  --v5-teal:       #0d6c6c;  /* analysis / system (mockup --cyan) */
  --v5-teal-ink:   #0a5555;  /* teal on light bg for TEXT (AA-safe, see §5) */
  --v5-teal-dim:   #d8ece9;  /* teal wash bg */
  --v5-amber:      #8a5a12;  /* caution — text-safe ochre (--amber) */
  --v5-amber-ink:  #6e470d;
  --v5-amber-bright:#b8801a; /* graphics/borders only, NOT body text */
  --v5-amber-glow: rgba(184,127,26,0.12);
  --v5-green:      #14713f;  /* literal TAKE / up */
  --v5-green-dim:  #dcefe1;
  --v5-red:        #ad2c34;  /* literal SKIP / down / refusal */
  --v5-red-dim:    #f6dfe0;

  /* type */
  --v5-disp: 'Fraunces', Georgia, serif;              /* display, verdicts, big numbers */
  --v5-sans: 'Public Sans', -apple-system, sans-serif;/* UI + prose */
  --v5-mono: 'IBM Plex Mono', ui-monospace, monospace;/* NUMBERS ONLY + tiny code tags */

  /* type scale (from mockup usage) */
  --v5-fs-hero: 30px;  /* foot-stat .n */
  --v5-fs-disp: 21px;  /* brand mark, prices */
  --v5-fs-val:  17px;  /* lens values, funnel numbers */
  --v5-fs-body: 11.5px;/* table body */
  --v5-fs-ui:   10.5px;/* chips, notes */
  --v5-fs-label:9.5px; /* uppercase section/col labels */
  --v5-fs-micro:9px;   /* table headers, tags */

  /* radius scale */
  --v5-r-xs: 3px;  /* tags */
  --v5-r-sm: 5px;  /* chips */
  --v5-r-md: 7px;  /* inset cells */
  --v5-r-lg: 10px; /* panels */
  --v5-r-xl: 12px; /* hero blocks (GROWW) */

  /* shadow + motion */
  --v5-shadow-panel: 0 1px 2px rgba(23,24,27,0.03);
  --v5-shadow-hero:  0 16px 44px -24px rgba(23,24,27,0.18);
  --v5-motion-fast: 120ms ease;      /* hovers */
  --v5-motion-tape: 52s linear;      /* ticker loop */
  /* NEVER animate: P&L, stop, target, qty, verdict (handoff §4) */
}
```

Also in tokens.v5.css: `.v5 .mono-num { font-family:var(--v5-mono); font-variant-numeric:tabular-nums; font-feature-settings:"tnum" 1; }`, the mockup's body radial-gradient wash (applied to `.v5-shell`, not `body`), selection color, and thin scrollbar rules scoped to `.v5`.

### Fonts — @fontsource, NOT CDN (offline desk, no Google requests)

```
npm i @fontsource-variable/fraunces @fontsource/public-sans @fontsource/ibm-plex-mono
```
Import in `main.jsx` (weights actually used): Fraunces variable (covers 300–900 +
italic axis if the variable italic package is added — mockup uses italic display in
`.sec-label`); Public Sans 400/500/600/700/800; IBM Plex Mono 400/500/600/700.
Acceptance: DevTools Network shows zero requests to fonts.googleapis/gstatic.

---

## 2. PRIMITIVES — build once, `desk/src/components/v5/`

One file each, plain CSS in a colocated `primitives.v5.css` (v5-prefixed classes).
Copy geometry/colors from the mockup CSS blocks named below. "Shared" = used by the
shell or expected by ≥2 tabs when later screens migrate.

| Primitive | Mockup source | Shared? | Notes |
|---|---|---|---|
| `StatusChip` | `.status-chip` (+ green/amber dot variants) | **App-wide (shell)** | props: label, value, tone(green/amber/neutral), `qual` italic variant, title tooltip |
| `CommandStrip` | `.cmd-topbar` | **App-wide (shell)** | brand mark + name/sub, middle StatusChips (Day/Regime/HMM/VIX), right mono stats (XP/Universe/Debated). Context-grid intentionally omitted (mockup removed it as dedup) |
| `TickerTape` | `.tape-outer/.tape-track/.tape-item` | **App-wide (shell)** | duplicated-track infinite loop, edge fades; `prefers-reduced-motion: reduce` → static row, no animation |
| `SectionLabel` | `.sec-label` | **App-wide** | italic Fraunces text + gradient rule + optional count pill |
| `Panel` / `PanelHeader` | `.panel/.panel-hd/.panel-bd` | **App-wide** | title + right-aligned italic mono `cite` slot (source provenance) |
| `VerdictChip` | `.verdict-chip` take/skip | **App-wide** (Debate, Shortlist, Positions later) | optional `*` struck marker + embedded ConvictionDots |
| `ConvictionDots` | `.conv-dots` | Shared | 4 dots, `currentColor` on/off — exists in DebateTab today; port, don't duplicate |
| `VoteBar` | `.vote-bar/.vote-seg/.vote-lbl` | Debate | muted green/rose segments (#8fcaa5/#e0a3a7) + `2T/2S` mono label |
| `MLBar` | `.ml-bar-track/.ml-bar-fill` | Debate | 44px teal micro-bar + pct; renders `—` when null |
| `Sparkline` | table `<svg class="spark">` polyline | Shared (Debate, Shortlist later) | pure SVG from a real closes array; green/red by first-vs-last; **no synthetic series** — omit/`—` when `spark` absent |
| `ReturnCell` | `retCell()` in mockup script | Shared | signed %, green/red, mono tabular; `—` (ink-faint, but with `title` explanation) when null |
| `GatePassTag` | `.status-tag` gatepass/nearmiss | Debate | GATE-PASS · PAPER / NEAR-MISS + 9px gate-note line |
| `GateCell` grid | `.gate-grid/.gate-cell` | Debate | PASS/WAIVED state + amber objection note |
| `FunnelPanel` | `.funnel-wrap/.fs-row/.fs-drop` | Debate (Market later) | **No ECharts.** Rebuild as SVG/CSS trapezoid stack (5 fixed bands, widths ∝ value) + stat rows + drop chips. Zero new chart deps |
| `LensLane` | `.lens-wrap/.lens-grid/.lens` | Debate | 4-up mechanism lens cells: label, verdict value, micro progress bar, description; honest "— N/A / not triggered" state |
| `LaneCard` | `.lane-card` momentum/basepattern/ipobase | Debate | 3px left accent border per family + count + symbol summary |
| `SizerStamp` | `.sizer-stamp` | Debate (TradePlan later) | red-ringed ✕ + "SIZER REFUSED — DETERMINISTIC RISK IS FINAL AUTHORITY" + 0×/0/0 metrics. Values come ONLY from payload |
| `StruckNote` | `.struck-note` | Debate | teal-edged chair-strike quote block |
| `CallBanner` | `.call-banner` | Debate (Market later) | stance cell + headline + arrow bullets + mono cite tags — renders `tonights_call` |

Gauges (`.regime-ring`, breadth gauges): the ring is a plain SVG stroke-dasharray —
implement as `RingGauge` (no ECharts). Breadth mini-gauges are Wave-2-optional; if the
debate payload lacks breadth ratios, the panel renders what the payload has — do not
fetch new endpoints just to fill decoration.

---

## 3. WAVE PLAN (each wave = one Sonnet coder run, one commit, QC before the next)

### Wave 1 — tokens + fonts + primitives + new LIGHT shell (real VIX). App still boots; tab bodies unchanged.

**Files**
- NEW `desk/src/styles/tokens.v5.css` (§1), `desk/src/components/v5/` (CommandStrip,
  StatusChip, TickerTape, SectionLabel, Panel, VerdictChip, ConvictionDots port,
  Sparkline, ReturnCell — the shell set + the leaf primitives Wave 2 needs)
- `desk/package.json` (+3 @fontsource deps), `desk/src/main.jsx` (font + css imports)
- `desk/src/App.jsx`: replace the current header block with `<div className="v5 v5-shell">`
  wrapping CommandStrip + TickerTape + existing tab nav (restyled v5) + existing tab
  bodies untouched. Preserve: tab state, date picker, symbolSearch, freshness stamp
  (`computeFreshnessStamp`), offline/stale banners (`computeOfflineBanner/computeStaleBanner`)
  — these move INTO the CommandStrip/right meta, they do not disappear.
  The two `App.*.test.js` suites cover the stamp/banner — keep them green.
- `desk/src/api.js`: no new endpoints needed; App.jsx additionally calls existing
  `fetchMarket(date)` once for the strip's VIX chip (see §4a).

**Command strip content mapping (all real):**
Day = run-card day color; Regime = `regime.market_mode`; HMM = regime HMM
warm-up if present in run card, else chip hidden; VIX = §4a; right stats
XP/Universe/Debated from run card + funnel. Ticker tape items = debate symbols
(chair verdict tag, %65dL, ADR20, conv) from `fetchDebate(date)` — if debate is
unavailable for the date, tape collapses to a single honest "no debate for {date}" item.

**Acceptance**
1. `npm run build` + all existing vitest suites green.
2. Every tab still renders on real 2026-07-10 data (screenshot each at 1470×900) —
   old tab bodies visually unchanged except the shell around them.
3. Shell chips cross-checked against `/api/desk/run-card` + `/api/desk/market` JSON
   (value-for-value, qc-ledger entry).
4. Zero external font/CDN requests; `prefers-reduced-motion` stops the tape.
5. VIX absent → chip shows "—" with a title explaining why (never a made-up "Normal").

### Wave 2 — DebateTab rebuilt to round-4 on REAL `/api/desk/debate`.

**Backend first (small, same wave):** §4b returns+spark fields, §4c chair
reconciliation. Then:

**Files**
- `manas_os/api/app.py` (`desk_debate`: returns/spark per symbol; chair struck fields)
- `manas_os/agents/chair.py` (persist pre-strike verdict + strike reason in lens JSON)
- `desk/src/DebateTab.jsx`: rebuilt to the round-4 composition, top→bottom:
  1. SectionLabel "Market Context" → regime panel (RingGauge + four-phase + HMM line +
     MBI chips) + breadth panel + FunnelPanel (real funnel block from payload)
  2. Governor / Portfolio-heat / Panel-coverage row (run-card governor + heat)
  3. LaneCard row (mechanism lanes, counts derived from payload families)
  4. CallBanner (tonight's call from run card)
  5. **Debated-names table** — the round-4 17-column table: Rank · Symbol(+family,
     src tag) · Family · 30d Sparkline · EOD · 3D · 7D · 1M · 3M · ADR20 · Off-65d-Low ·
     Purple Dots · Stock HMM · ML P(up) · VoteBar · Chair VerdictChip · GatePassTag+note.
     Row tint for gate-pass; hero-tinted clickable row for the gate-passed name
     scrolls to its deep-dive block. Wide table lives in its own `overflow-x:auto`.
  6. Deep-dive block for each gate-passed symbol (GROWW pattern): head (name/family/
     rank/price) + 3-col body (real chart via existing `ChartImg`/chart-data — NOT the
     mockup's synthetic candles; GateCell grid; model vote rows + grade note) +
     StruckNote (when chair.struck) + SizerStamp (when sizer refused/zeroed)
  7. LensLane strip + citation chips (from payload lens/citations where present;
     omit lanes the payload can't back — no fabricated lens verdicts)
  8. Foot stats (live/paper/near-miss/pool/debated — reuse payload's summary counts)
     + model ledger footer (models list from payload)
- Keep existing DebateTab logic components that survive (CitedText, GateDotsRow → GateCell,
  BaseRateChip, MlChip→MLBar, StockHmmChip, HowToTradeThis, ModelDebateBlock content) —
  port their DATA logic, restyle to v5; delete their old-styled duplicates same wave
  (pipeline-hygiene: no two live versions of the same block).

**Acceptance**
1. Screenshot-vs-mockup review, element-for-element (wireframe-fidelity bar): every
   round-4 section present or explicitly waived in the QC ledger with a reason.
2. Every rendered number traced to `/api/desk/debate`, `/api/desk/run-card`, or
   `/api/desk/market` JSON — value-for-value ledger (Fable-review-entirety bar:
   ALL 13 rows × all columns, not a sample).
3. Nulls render as "—", never invented (short-history returns, missing ML, RELIANCE
   1-model no-chair row).
4. Zero-size truth: for a struck/refused symbol, no element anywhere implies a live
   take; SizerStamp shows 0×/0/0 from payload.
5. Old DebateTab classes removed from App.css only if they become dead; otherwise left
   (deletion is UI-7's job).
6. Existing tests green + new vitest unit for the returns helper (§4b) and the struck
   derivation (§4c).

---

## 4. THE 3 DATA ITEMS — honest handling

### a. Real VIX (header chip)
`/api/desk/market` already returns top-level `vix` (e.g. `{value: 12.25, band: ...}`
via `_extract_vix`, see `api/app.py` ~5522–5560). Wave 1: App.jsx fetches market once
per date and passes `vix` to CommandStrip. Render `VIX 12.25` (mono) with band tone;
when `vix` is null / market unavailable / offline-fallback, render `—` with
`title="India VIX not available for this date"`. **Never** ship the mockup's
"Normal (qual.)" placeholder — that was a bakeoff honesty note, not a product state.
Note: `api.js` fallbackMarket hardcodes `vix:{value:13.4}` — offline fallback already
tags `offline_fallback:true`; the chip must show the offline banner state, not present
13.4 as live.

### b. Multi-period returns (EOD/3D/7D/1M/3M) + 30d sparkline per debated symbol
NOT in today's debate payload. The mockup synthesizes them (its own comment says
"production wires real daily_prices returns"). Direction — **backend, one helper**:

- In `api/app.py`, add `_symbol_returns(conn, symbol, on_or_before)` modeled directly
  on `_index_returns` (line ~217) but over `daily_prices`: fetch last 66 closes
  `WHERE symbol=? AND trade_date<=? ORDER BY trade_date DESC LIMIT 66`, compute
  trading-row offsets `{eod:1, d3:3, d7:7, m1:21, m3:63}` (same 21/63 convention as
  `_index_returns`); any offset beyond available history → `null`.
- In `desk_debate` (per-symbol loop, ~4430–4660): add to each symbol dict
  `"returns": {eod,d3,d7,m1,m3}` and `"spark": [last 30 closes ascending]`
  (30 real closes; fewer if history is short; `[]` → frontend omits sparkline).
  One batched query for all debated symbols (≤13) is fine — no N+1 concern at this n,
  but prefer a single `WHERE symbol IN (...)` fetch.
- Frontend: ReturnCell renders each, `—` when null; Sparkline colored by
  first-vs-last of the REAL series. The mockup's rule "returns derived from the same
  path as the sparkline" is automatically satisfied because both come from the same
  daily_prices rows.
- No fixture/synthetic fallback in production. Offline fallback run-card has no
  debate returns → cells show "—" under the offline banner.

### c. GROWW chair-verdict inconsistency — one truth
**Observed:** `bakeoff/debate_data.json` chair(GROWW)=SKIP/struck;
`bakeoff/runcard_data.json` chair(GROWW)=TAKE c3 and sizer=SKIP/refused.
**Root cause (verified in code):** `agents/sizer.py` only sizes chair
`verdict='TAKE'` rows (line ~76) — so a sizer refusal row for GROWW proves chair was
TAKE **at sizer time**; `agents/chair.py::_persist` upserts the FINAL post-strike
verdict (`"SKIP" if struck else base_verdict`) into `agent_verdicts`, so a strike
applied on a rerun (or a re-run of the chair after sizing) rewrites the chair row to
SKIP while the sizer row keeps telling the pre-strike story. Both readers
(`desk_debate` and `run_card._chair`) read the same table — the runcard JSON was
simply snapshotted before the strike landed. `desk_debate` additionally detects
`struck` by **string-matching "struck" in reasoning** (app.py ~4612) — fragile.

**Authoritative source:** `agent_verdicts` as it stands post-strike (the
runcard/sizer chain's DB ledger), with the strike made a first-class recorded
transition rather than a prose hint:

1. `agents/chair.py::_persist`: add to `lens_scores_json`:
   `"base_verdict": item["base_verdict"], "struck": bool(reason), "strike_reason": reason`.
2. `api/app.py::desk_debate` chair block: derive
   `struck = chair_lens.get("struck")` (fall back to the current string match only
   for pre-migration rows), and expose `"pre_strike_verdict"` + `"strike_reason"` so
   the UI can render the true story: *models 4T/0S → chair TAKE c3 → risk-gate
   STRUCK → SKIP → sizer REFUSED 0 qty* — exactly the round-4 StruckNote narrative.
3. `agents/run_card.py`: no schema change (it re-reads agent_verdicts), but pipeline
   ordering must guarantee chair-strike completes before both sizer and run-card
   build; add a build-time consistency check: any symbol with a sizer row must have
   chair verdict TAKE **or** `lens.struck=true` — log a run-card `errors` entry
   otherwise instead of silently disagreeing.
4. UI rule: DebateTab renders chair from the debate payload ONLY; the run-card
   headline counts ("chair took N") stay run-card-owned; a struck name counts in
   NEITHER live nor chair-take counts (already true in `desk_debate`'s
   live/paper/near-miss derivation).

No backfill rewrite of historical rows — old rows keep the string-match fallback.

---

## 5. RISKS + GUARDRAILS

- **One writer for risk.** UI never computes or invents stop/qty/multiplier/rupee
  risk. SizerStamp, plan numbers, heat bar are payload passthrough. Any formatting
  helper must be display-only (sign, %, ₹ formatting).
- **Deterministic risk is final authority, visually.** A refused/zeroed symbol can
  never co-render with a take-style CTA (handoff UI-5 done-test). GatePassTag for a
  refused gate-pass is "GATE-PASS · PAPER", never plain "GATE-PASS".
- **Honest 0-live.** Foot stats and the headline strip come from the same symbol list
  the table renders (`desk_debate` already computes them together — keep it that way).
- **Don't break existing routes/tabs.** v5 is additive + scoped (`.v5-*` classes, new
  token names). No edits to old App.css selectors in Waves 1–2. All existing vitest
  suites must stay green each wave; each wave is one commit (pipeline-hygiene).
- **No new chart deps.** No ECharts/lightweight-charts additions for the funnel,
  gauges, or sparklines — plain SVG. The GROWW candle chart uses the EXISTING
  chart-data/ChartImg path, not mockup synthetics.
- **No synthetic data in production, ever.** Every mockup element whose data was
  seeded (lane spark-bars, table sparklines, candle shapes) is either wired to real
  payload fields (§4b) or rendered as an honest empty/`—` state. If a decorative
  element has no real series, drop the decoration.
- **A11y AA on the light theme.** Contrast on `#f7f6f2` / `#fffdf9`:
  `--v5-ink/-dim/-mute` all pass AA; `--v5-teal #0d6c6c` ≈ 5.9:1 and
  `--v5-teal-ink #0a5555` ≈ 7.3:1 — both AA for normal text; `--v5-amber #8a5a12`
  ≈ 6.3:1 / `--v5-amber-ink #6e470d` ≈ 7.8:1 — AA; `--v5-green #14713f` ≈ 5.9:1 and
  `--v5-red #ad2c34` ≈ 6.4:1 — AA at chip sizes. **`--v5-amber-bright #b8801a`
  (~2.9:1) and `--v5-ink-faint #9a9da5` (~2.6:1) are graphics/decoration only — never
  body text**; where the mockup uses them on text (bar labels, cite italics ≤9px),
  bump to `--v5-amber`/`--v5-ink-mute`. QC gate: run a contrast pass over every
  text/background pair in the Wave-2 screenshot set; also verify verdict/return
  semantics are never color-only (chips carry text; returns carry sign).
- **Mockup fidelity boundaries.** `min-width:1470px` from the mockup is a bakeoff
  artifact — the shell keeps the desk's existing responsive behavior; the wide debate
  table scrolls in its own container. Ticker tape and pulse dot honor
  `prefers-reduced-motion`.
- **QC ledger.** Each wave appends a dated entry (files touched, screenshot paths,
  number cross-check results, waived mockup elements + reasons) to
  `UI_OVERHAUL_HANDOFF.md` §9 ledger or a sibling ledger file — re-audits are
  delta-scoped from there.
