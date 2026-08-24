# TraderLog — Design Overhaul Plan (v2, grounded in the real product)

## Intent

A complete visual + structural overhaul of **TraderLog** — an evidence-reconstruction research tool that tracks a roster of Indian fin-Twitter traders, ingests their posts, rebuilds positions from threads, and measures *stated vs actual* behavior. The overhaul must respect the product's real information architecture, content model, documented design rules, and existing chart primitives. It must NOT impose a foreign template over a system that is already deliberately designed.

---

## Diagnosis — what TraderLog actually is (from the real screens)

This is not a "trading journal dashboard." It is a **research/evidence desk**. The entire product is built on one philosophical spine, visible in every screen's copy:

> "Results are what the trader *said* — never computed from market data."
> "Stated vs measured." "Evidence desks." "Unresolved flags." "Confidence floors."

### The six real product screens (+ one dev screen)

- **Feed** — the thread workspace. Posts newest-first, grouped into threads; event strips (entry / add / stop-move / exit); unresolved disclosure (count then full strings on expand); deleted-post warnings kept on purpose (anti-bias); an evidence "why?" expansion; a **Review queue** (attach / deny ambiguous items, one decision at a time); secondary rail = filters + traders-on-desk + a quiet desk ledger.
- **Traders** — sortable roster table (handle / tier / posts / open / closed / hold / win / preach / last seen) + a per-trader **profile**: stated win rate as THE one dominant number, stop-discipline **dumbbell** (stated vs honoured), hold-days **strip plot**, sector-tilt **stacked strip**, open positions.
- **Ledger** — reconstructed positions. Filter row (trader / status / symbol / conf / unresolved toggle), the **PositionBars** shared-time-axis chart, a sortable data table (trader / symbol / entry / adds / stop / exit / net / days / cf), expandable detail with event **timeline**, evidence dict, archived media.
- **Breadth** — market internals: XP value + band (dominant number), MBI day colour + score + warning flag, the r10/r20/r50/r4.5 ratios with bands, MBI **ribbon** history, XP trend **BandLine**, trader stances vs actual breadth, agreement bars with `n` shown.
- **Ideas** — **ticker leaderboard** (entered / holding / exited / mentioned per symbol, grouped by symbol not trader), by-symbol idea groups with **verbatim quotes**, themes bars.
- **Library** — educational quotes by topic (**verbatim** — paraphrase drift would corrupt the measure), each item followed by **practice-vs-preach**: followed / violated / n-a counts, score bar, violations list with evidence.
- **Style** — a **dev-only reference sheet** (not a product tab) that renders every chart + control primitive against inline sample data. It is the design-system ledger the team copies from.

### Existing design rules already encoded in the code (preserve, never regress)

1. **A denominator beside every percentage** (§1) — "63% of 183" not bare "63%".
2. **One dominant number per screen**, sized by weight, **never a dial or gauge** (§4).
3. **Sortable column headers** with a caret; real disclosure carets (keyboard-operable), never bare row clicks (§3).
4. **Chips differ by fill weight, never hue**; sentence-case tags, not shouts.
5. **Evidence is always visible**, never behind a toggle — it is why the table can be trusted.
6. **Unstated ≠ zero**: em dash "—" for missing, never "—%" and never "0%".
7. **Empty states are truthful**: a one-line "future block" explaining what is unavailable and what will provide it — never a framed empty chart.
8. **Deleted posts are kept** — traders delete losers; dropping them would bias every metric.
9. **No invented metrics.** Everything is derived client-side from real payloads, or explicitly future-wave.
10. Custom chart primitives are the product's voice: **PositionBars, Dumbbell, StripPlot, BandLine, Ribbon, StackedStrip, SmallMultiples** — all with labelled, accessible empty frames.

### Why the first attempt was wrong

My earlier `traderlog-overhaul.html` invented a US-equities P&L dashboard (SPY/QQQ tickers, "equity curve", KPI tiles, New trade dialog). TraderLog has **no such thing**: it is ₹-denominated, Indian symbols (DIXON, BEL, KPITTECH, COFORGE-style), thread-based, evidence-chained, and philosophically opposed to fabricated metrics. The correct overhaul upgrades the craft of the existing system — it does not replace the system.

---

## Visual direction — LOCKED: "The Evidence Desk"

**Creative-director call.** TraderLog's identity is a dense, monochrome research terminal (black-square/white-"T" brand mark, ₹ figures, mono numerics, tabular data tables). The overhaul direction is **dark-chrome editorial-utility**: the density and precision of a research terminal, with the typographic discipline of a financial desk, hairline rules, no shadows, no rounded cards, and one restrained signal accent.

- **Palette:** derived in `oklch` from the direction posture — near-black `--bg`, elevated panel surfaces, ink-on-paper text hierarchy, hairline `--border`, one domain-appropriate accent (used ≤2×/screen); green/red reserved exclusively for state (MBI GREEN/RED, P&L).
- **Type:** serif display (Iowan Old Style / Charter / Georgia) for masthead + section heads; sans body; **mono `tabular-nums` for every figure**, timestamps, and kickers — the product already leads with mono numerics.
- **Posture:** hairline rules + whitespace do the layout; no shadows except modals; one decisive chart per panel; mono uppercase kickers; a date line in the masthead (a research desk is dated).
- **Charts:** the existing primitives stay and get a craft pass — filled encoding, labelled axes, accessible empty frames, consistent stroke/rule language.

### Anti-slop guarantees

No purple gradients · no Inter · no grey-out hovers · no "colored vertical bar + rounded card" callouts · one accent ≤2×/screen · filled chart encoding · every hover/focus/active state contrast-paired · stated-vs-measured copy never fabricated · denominators beside every %.

---

## Screen plan (real content model, confirmed from source)

| Screen | What it shows (real) | Overhaul moves |
|---|---|---|
| **Feed** | Threads, event strips, unresolved, deleted-post warnings, evidence "why?", review queue, filters rail, traders-on-desk, desk ledger | Two-column evidence desk: thread workspace primary, rail secondary; serif-led thread copy; mono event strips; review queue styled as a flagged desk; hairlines throughout |
| **Traders** | Sortable roster + profile (win-rate dominant number, dumbbell, strip plot, stacked strip, open positions) | Roster as a ruled league table; profile lead with the one dominant number; charts in consistent frame language |
| **Ledger** | Filters, PositionBars timeline, sortable positions table, expandable detail (timeline, evidence, media) | PositionBars as the lead graphic with dated interior events; table with column rules; detail as a side panel with evidence desk |
| **Breadth** | XP dominant number + band, MBI day colour/score/warning, r10/20/50/4.5 ratios, ribbon history, XP trend, stances, agreement | XP as the screen's single dominant figure; ribbon as the calendar; stance-vs-breadth comparison styled as a desk ledger |
| **Ideas** | Ticker leaderboard (entered/holding/exited/mentioned), by-symbol groups with verbatim quotes, themes | Leaderboard as a rules-based table with counts in mono; idea groups as filed evidence cards; verbatim quotes preserved |
| **Library** | Verbatim education quotes by topic + practice-vs-preach per item | Topic tabs as index; quote as the unit of content; practice ledger styled consistently |
| **Style (dev)** | Primitive reference sheet | Kept as the system's reference ledger; restyled to match the new tokens |

**Deliverable form (locked):** single self-contained HTML redesign prototype in Design Files, with working interactions (nav, filters, sort, disclosure, review attach/deny) and honest, clearly-labelled demo data. It renders the REAL TraderLog screens — not an invented dashboard.

---

## Open items (blockers)

- [ ] **Tokens + components + design docs still unreadable** — `tokens.css`, `app.css`, `thread.css`, `components/ui.jsx`, `components/charts.jsx`, `design/VISUAL_LANGUAGE.md`, `design/WIREFRAMES.md`. These define the current visual system and chart API. Reads of the `Downloads\koreanguy\traderlog` path keep being denied; the screens were pasted, but these were not.
- [ ] **Direction branch confirm** — dark-chrome "Evidence Desk" (recommended) vs light-paper variant of the same system.
- [ ] **Scope of first pass** — Ledger-first (recommended) vs all six product screens.

---

## Next step

Paste the missing reference files (tokens.css + app.css + thread.css, then ui.jsx + charts.jsx) so I bind the real tokens and chart primitives — or confirm I should derive the system myself in `oklch` while preserving the documented rules. Then rebuild Ledger-first in the "Evidence Desk" system and verify against the checklist.