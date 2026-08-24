# TraderLog — Final Design Spec

**Status:** FINAL · closed for handoff · demo data, prototype fidelity
**Artifact:** `traderlog-evidence-desk.html`
**Design system:** "Quiet Editorial Terminal" — bound verbatim to `ui/src/styles/tokens.css`

---

## 1. The design in one line

TraderLog is an evidence desk, not a dashboard: every position is reconstructed
from a trader's thread, every number is chained to the post that justifies it,
and the interface reads as a calm, dense, warm-paper instrument — hairline
structure, zero radius, one restrained blue accent, serif display over sans
body with mono tabular numerics.

## 2. Token system (verbatim from tokens.css)

| Role | Value |
|---|---|
| `--canvas` | `#f7f6f4` warm-neutral paper |
| `--surface` | `#fdfdfc` panel |
| `--ink` | `#1a1a1a` soft near-black (never pure #000) |
| `--info` | `#1f4a8a` — the ONE accent (interaction, active, focus) |
| `--ok` / `--bad` / `--warn` | `#2f7d4f` / `#b3402c` / `#8a6d00` — state only |
| Radius | `0` everywhere |
| Structure | ONE 1px border per region; interior hairlines `--rule #cecbc0` |
| Shadow | only the 1px hard press offset |
| Type | Inter sans (display+body), mono ui-monospace for all numerics |
| Motion | none — state changes are instant |

**Rules that must not regress:** denominators beside every percentage ·
unstated ≠ zero (em dash, never "0%") · chips differ by fill weight not hue ·
one accent used at most twice per screen · charts use filled encoding ·
evidence always visible · deleted posts kept (anti-bias).

## 3. Screens (7 tabs)

1. **Ledger** — PositionBars shared-time-axis lead, sortable/filterable positions
   table, side strips (closed results, holding days, net by symbol), expandable
   detail with event timeline + evidence dict.
2. **Feed** — thread spine, event strips, deleted-post warnings, review queue
   (attach/deny with decision-pending lock), desk rail with cadence + posts-by-trader.
3. **Traders** — roster small-multiples, profile lead (one dominant number),
   stop-discipline dumbbell, hold-days strip, sector stacked strip.
4. **Breadth** — XP dominant number, MBI ribbon, XP BandLine, cumulative
   advance–decline line, stance-vs-breadth table.
5. **Ideas** — ticker leaderboard with position-split bars, by-symbol verbatim
   mentions, theme mix.
6. **Library** — verbatim quotes by topic, practise-vs-preach with n, small-multiples.
7. **Visuals** — 14 chart-vocabulary specimens including a seeded generative
   "Tape" study (p5 canvas + SVG fallback, reseed control).

## 4. Working interactions

- Tab navigation (persisted in `localStorage`)
- Ledger filters (trader / status / symbol / conf / unresolved toggle)
- **Sortable column headers** (caret indicator)
- Position detail expand/collapse (keyboard-accessible disclosure)
- Review queue attach/deny with one-decision-at-a-time lock
- Ticker-row → Ledger cross-navigation (pre-filtered by symbol)
- Generative tape reseed (seeded PRNG, reproducible render)

## 5. Accessibility baseline

`:focus-visible` ring on every focusable element · `aria-expanded` +
`aria-label` on disclosure controls · `role="img"` + aria-label on charts ·
labelled form controls · 28px min click targets with enlarged hit areas ·
`prefers-reduced-motion` respected · contrast: ink on paper 13:1+, state inks
≥4.5:1 · 920px mobile reflow (tabs wrap, no horizontal overflow).

## 6. Demo-data honesty

All figures are sample rows modelled on the real API payloads (₹-denominated,
Indian symbols). A demo banner marks this on every load. No metrics are
invented to look real — the shapes match production, the values do not.

## 7. Handoff notes

- The HTML is self-contained (single file, inline CSS/JS, p5 from CDN with a
  static SVG fallback so it renders anywhere).
- The real React source (`ui/src/…`) is untouched; this prototype is the
  design contract for a rebuild.
- If implementation time matters most, Ledger + Feed carry the system's voice;
  Visuals is the token/chart reference sheet.