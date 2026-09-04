# Manas AI Trading OS — Design Guidance (v1)

Front-end / UX system that formalizes the seeded light **"trading terminal"** into a rigorous, reusable language and applies it coherently across all five surfaces. Companion machine-readable tokens: **`design_guidelines.json`**. Living, rendered reference: **`Manas Trading OS.dc.html`** → the **Style Guide** tab (tokens, type scale, font comparison, every component spec, and the state matrix are all shown live).

> **Prime directive:** easy to operate, easy to control, not a messy mashup. One coherent visual language on every surface. The plain-English verdict beside every number *is* the beginner explainability — it does double duty as the product's personality.

---

## 1. Tokens

**Surfaces & ink** — warm-neutral, flat (no gradients/shadows):
`bg #f4f5f7` · `card #fff` · `raised #f7f8fa` · `ink #14161a` · `ink-2 #5b6472` · `ink-3 #8a93a0` · `ink-4 #9aa2ae` · hairlines `#e7e9ee / #eef0f3 / #f4f5f7`.

**Conditional-color bands — the core motif.** Color is *functional only*. Each band ships as `{fg-on-white, bg-tint, border, dot}`, all AA-checked (fg ≥ 4.5:1 on white; >7:1 on its tint):

| Band | Meaning | fg | bg | border | dot |
|---|---|---|---|---|---|
| green | bullish / pass / allowed | `#0f7a3d` | `#e6f6ec` | `#c2e6cf` | `#22c55e` |
| orange | extreme-bullish / burst / caution | `#9a5b00` | `#fdf0dd` | `#f1d7a6` | `#f6a609` |
| red | bearish / fail / off | `#b42318` | `#fdecea` | `#f4c9c4` | `#e5484d` |
| gray | neutral / no signal | `#5b6472` | `#f0f1f4` | `#e2e5ea` | `#9aa2ae` |
| blue | secondary highlight (XP, RMV) | `#175cd3` | `#e9f1fd` | `#c7dbf7` | `#4a90ff` |

**Posture** maps onto bands: `RISK_ON`→green, `SELECTIVE`→orange, `DEFENSIVE`→red, `NO_TRADE`→**ink-inverted** (`#14161a`/white — the hardest state), `DEGRADED`→gray (stale/auth only).

**Radii:** chip 5 · chip-lg 7 · button 8 · card 12 · card-lg 14. **Border:** `1px solid #e7e9ee`. **Spacing:** 8px base; steps 4/8/12/16/24/32; major gaps 12/16/24; max content width **1440px**.

---

## 2. Type scale

Mono-forward. **Ship JetBrains Mono** (widest weight range, excellent tabular figures, unambiguous `0O1lI`); Cascadia Code is the seed's lead and an acceptable alt, IBM Plex Mono reads warmer. A clean **sans** (`system-ui / Segoe UI`) is used *only* for the plain-English prose reads. Always `font-variant-numeric: tabular-nums` on numeric columns.

| Role | Family | Size / weight |
|---|---|---|
| Terminal chrome (pill labels, headers) | mono | 10–11px / 700, .06em, UPPER |
| Data table / chips | mono | 12px / 600, tabular |
| Headline number (XP dial, 46% bias, readiness) | mono | 20–28px / 700 |
| Section title | mono | 20px / 700, -.01em |
| Prose "READ" | sans | 12–13px / 1.45, `#3a414c` |

---

## 3. Component specs (anatomy)

- **Pill label + status dot** — ink pill, 10–11px uppercase mono, .06em, 6px dot = live state. Section identity on every card.
- **Conditional data cell** — tabular value inside a tinted chip; band chosen by threshold (breadth %: ≥65 green / 48–64 gray / <48 red · 4.5R: ≥150 orange / 100–149 green / 60–99 gray / <60 red · signed: >0 green / <0 red).
- **Verdict / annotation layer** — the systematic slot: a mono verdict chip (`SWING UP`) + a sans **READ** line under a dashed divider. Every data block gets exactly one; never omit, never decorate. This is how the "plain-English read beside every number" scales beyond the quadrant page.
- **Quadrant card** — 3px colored left-rail, pill label, state, one-sentence question, 0–100 confidence bar, 2–3 metric chips, READ line.
- **Top decision strip** — two directions provided (see §6).
- **Candidate card** — symbol, setup, Trade Readiness score (0–100) + grade (A+→C), mini chart w/ pivot line, **evidence chips** (named filters that fired), trade-plan box, 2-tap log-to-journal. **No buy button.**
- **Heatmap strip** — 132px row label + run of solid `band.dot` cells (green→red) over sessions.
- **Preset chart frame** — preset tabs → heat strips → candles (72%) → volume (28%) → price lines → side badges → risk box. Switching presets **never** mixes overlays.
- **Banner** — pulsing dot + bold title + sans explanation + action button; full-width, band-tinted; impossible to miss.
- **InfoDot (ⓘ)** — on any jargon term/column header → 1-line plain-English definition (~40 glossary terms).
- **Beginner ⇄ Expert toggle** — global segmented ink control; flips label style + reveals/hides raw columns app-wide.

---

## 4. Layout & nav

**Top tab bar** for the 5 destinations (recommended over a left rail: fewer chrome pixels, clearer for beginners, and 5 items never sprawl). Global header (56px): app mark · **posture badge** (always visible) · **data-freshness** (date + green/amber/red dot) · Beginner⇄Expert · Fyers chip.

**Regime grid rhythm (flagship):** strip (12) → quadrant (12) → universe (8) + action badges (4) → sector heatmap (8) + setup availability (4). Other surfaces reuse the same card/rail/verdict vocabulary at their own densities.

**Responsive (desktop-first):** ≥1600 → 32px pad; 1366–1600 → 24px pad; ≤1024 → quadrant collapses to 2×2 and side panels stack; ≤768 → single column, strip becomes two chip rows, universe → horizontal scroll/accordion, sector → accordion (top 8).

---

## 5. State matrix (beginner-safety)

Toggle the header **STATE** selector to see each live. Every data surface designs all five:

- **Normal** — fresh + populated; confident posture.
- **Empty** — a valid "nothing today": *"0 setups tonight — market is SELECTIVE, sit tight."* Intentional, never blank.
- **Stale** — loud red banner **and** affected numbers de-emphasized (opacity .55 + grayscale) **and** posture hard-degrades to gray. Never a confident green regime on old data.
- **Auth-needed** — Fyers token expired (~6am daily) → orange reconnect banner + live surfaces marked stale (WebSocket source shows FAIL).
- **Loading** — calm monospace shimmer skeletons; no layout shift on arrival.

---

## 6. Open questions — resolved

1. **Light or dark?** → **Light only** for v1 (the chosen reference). Tokens are semantically named so a future dark "control-room" can reuse the band/posture layer without re-authoring meaning.
2. **Primary font?** → **JetBrains Mono**, bundled. (Comparison rendered in the Style Guide.)
3. **Nav?** → **Top tab bar.**
4. **Beginner density?** → **Moderate.** Plain-English leads, but key numbers (XP, %>DMA, 4.5R) stay visible; ≤3 raw indicators per card before expansion. Expert adds 20R/50R/ADR/RS columns app-wide.
5. **Verdict layer rendering?** → A **fixed slot**: mono verdict chip + sans READ line under every data block (not a separate column, not free-floating) — so it scales identically across quadrant, universe, chart, and candidate surfaces.

---

## 7. Two directions to compare (Regime top strip + quadrant)

Toggle **DIR A / DIR B** on the Regime page.

- **Direction A — Instrument.** An 8-card metric strip + four equal quadrant cards. Densest, most terminal-like; fastest 3-second scan for an experienced eye.
- **Direction B — Briefing.** One wide posture banner leading with the plain-English sentence + supporting chips, and a 2×2 question-led quadrant with numbers subordinate. More beginner-forward and editorial.

Recommendation: ship **A** as the default power view and offer **B** as the Beginner-mode default — same tokens, same data, different emphasis.

---

## 8. Non-goals (do not design)

No order/buy/sell buttons anywhere (plans only, executed manually off-platform) · no black-box scores (every number traces to named filters) · single-user/private (no social/sharing) · no decorative color, gradients, shadows, or motion · not a free-form charting platform (presets over indicator assembly).
