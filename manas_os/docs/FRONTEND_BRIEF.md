# Manas AI Trading OS — Front-End Design Brief

**For:** design ideation (Claude Design). **Return:** a design-guidance MD (tokens, type scale,
component specs, layout grid, state matrix, responsive rules) + a `design_guidelines.json`.
**Scope:** front-end / UX only. The backend, data pipeline, and formulas are already built —
this brief is about how the product should *look, read, and feel*, not how data is produced.

---

## 1. What this is, and who it's for

**Manas AI Trading OS** is a **single-user, beginner-friendly decision cockpit for NSE (Indian
cash-market) swing trading.** It does **not** pick stocks and does **not** place orders. It helps
one retail trader answer four questions each evening/morning, always with visible evidence:

1. **Should I be aggressive today?** → the Market Regime page.
2. **Which valid setup deserves capital?** → the Scanner / Focus list.
3. **How much should I risk?** → stop-loss + position size, shown on each candidate.
4. **Am I following my process?** → the Journal.

**The user:** a retail swing trader, relatively new, ~30–45 minutes of process time a day, on a
Windows laptop. Not a data scientist. Wants to *learn the method while using the tool*. Easily
overwhelmed by dense pro terminals — but does not want a toy. The product must be **legible to a
beginner yet respected by an experienced trader.**

**The prime directive (everything below serves this):** *easy to operate, easy to control, and not
a messy mashup.* One coherent visual language across every surface.

---

## 2. Design north star (already seeded — build on this, don't reinvent)

The user chose the aesthetic from two references and we prototyped it. **The house style is a
light "trading terminal": monospace, high-contrast, calm, with a plain-English read beside every
number.** The look must be extrapolated consistently to every page.

**Reference A — "Market Quadrant" (primary aesthetic):** a light, clean, annotated dashboard.
Black pill labels with colored status dots; compact monospace data tables with conditional cell
coloring (green / orange / red / gray / blue bands); breadth histogram panes; and a hand-written
plain-English callout next to each block ("SWING is UP — more than half of stocks are above their
10MA"; "MBI weakly green, XP<15"; "BIAS is BEARISH — ~46% above 200-day SMA"). This annotation
layer is not decoration — **the plain-English verdict beside each metric IS the beginner
explainability**, and it does double duty as the design's personality.

**Reference B — "SuperTraderEdge / MonAlert" (functional patterns for the chart/scanner):** a
charting workspace with **heatmap strips** stacked above a candlestick chart (e.g. "Minervini
Pressure", "Buy Risk", "TPR" — each a row of green→red cells over time), plus a left rail of
**Confirmations** and **Caution** lists (per-stock rows with a one-line reason). Take these
*patterns*, rendered in Reference A's visual language.

**The prototype we built (the seed to formalize):**
- Type: **monospace-forward.** Primary font stack led by **Cascadia Code / Cascadia Mono**, then
  **JetBrains Mono / IBM Plex Mono**, then `ui-monospace, Consolas, monospace`. Tabular figures
  (`font-variant-numeric: tabular-nums`) so numeric columns align. A clean **sans** (Inter /
  Segoe UI Variable / system-ui) is used *only* for the longer plain-English prose reads.
  (In the shipped app the chosen font is bundled, so it's machine-independent.)
- Surfaces: light background (`#f4f5f7`), white cards (`#fff`), near-black ink (`#14161a`),
  1px hairline borders (`#e7e9ee`), ~10–14px rounded corners, flat (no gradients/shadows).
- **Status dots + black pill labels** for section identity; a colored **left rail** on each card.
- **Conditional-color data cells** — the core motif — using functional color bands:
  green (bullish/pass), orange (extreme-bullish/burst), red (bearish/fail), gray (neutral),
  blue (secondary highlight, e.g. the XP column). Color is **functional only**, never decorative.
- **A plain-English verdict** ("SWING UP", "BIAS BEARISH") + one explanatory sentence beside
  every data block.

> Claude Design's job is to **formalize this seed into a rigorous system** (exact tokens, scale,
> spacing rhythm, component anatomy, dark-variant question, responsive behavior) and apply it
> coherently across all surfaces below — not to invent a different aesthetic.

---

## 3. Design principles (constraints the visual system must honor)

1. **Explainable, never a black box.** Every score/verdict shows the named filters behind it
   (evidence chips), and any metric is hover-to-define. No bare "AI conviction: 87%".
2. **Beginner-first, expert-toggle.** Default view uses plain-English labels and hides raw
   internals; a global **Beginner ⇄ Expert** switch reveals raw columns (RS, RVOL, bucket, ADR…)
   for power users. Same data, two densities.
3. **Rules first, calm surface.** The tool guides behavior — it must not feel like it's urging
   trades. Restraint over dopamine. No blinking, no hype.
4. **Dense but scannable.** Pro-grade information density is welcome *if* hierarchy and the
   monospace grid keep it readable in a 3-second glance (the top strip especially).
5. **One language everywhere.** Pill labels, status dots, conditional tables, and the
   verdict-beside-number pattern repeat on every page so the app feels like one instrument.
6. **Beginner-safety is visible.** Stale data, expired broker auth, and empty states are
   first-class, loud, and unmistakable (see §7) — silent staleness is the worst failure.

---

## 4. Global shell

- **Navigation:** a small number of top-level destinations — **Regime · Focus (Scanner) ·
  Chart · Journal · Health.** (5 max; the tool is meant to be easy to operate — avoid tab
  sprawl.) Design the nav pattern (top tabs vs. left rail) as part of the guidance.
- **Global header:** app mark, the current **market posture badge** (RISK_ON / SELECTIVE /
  DEFENSIVE / NO_TRADE) always visible, a **data-freshness indicator** (last update date +
  green/amber/red), the **Beginner ⇄ Expert** toggle, and a Fyers-connection status chip.
- **Glossary tooltips (InfoDot):** an "ⓘ" affordance on any jargon term/column header opens a
  one-line plain-English definition. ~40 terms (EM, XP, MBI, 4.5R, RVOL, RMV, RS, ADR, stage,
  persistency, pocket pivot, Strong Start, etc.).
- **Banners:** persistent, prominent banners for (a) **stale data** ("Market data hasn't updated
  since <date>"), (b) **Fyers auth needed** ("Reconnect broker to refresh live data" — the token
  expires ~6am daily), (c) optional info. These must be impossible to miss.

---

## 5. Surfaces (pages)

For each page: its purpose, the decision it answers, the key content/components, and the domain
vocabulary the design must accommodate.

### 5.1 Market Regime page — THE FLAGSHIP (open here every day)
**Answers:** "How aggressive am I allowed to be today, and why?"

- **Top Decision Strip** (the 3-second read): market posture badge; the **XP dial** (headline
  breadth-energy number, e.g. "12 — low energy"); **MBI day color** (green/white/red) +
  **warning-day** flag; allowed **risk-per-trade band**; **preferred** vs **avoid** setup chips.
- **Market Quadrant** — four cards, each a plain-language question + a state + a small data table
  + a one-sentence verdict:
  - **MOMENTUM** — "Is thrust expanding?" — inputs: Homma **MSwing** per index (Microcap/Smallcap/
    Nifty Next 50/Midcap/Nifty50). State: UP / NEUTRAL / DOWN (+ direction arrow, e.g. "+↓").
  - **SWING** — "Can short-term longs work?" — inputs: **% of stocks above 10-day SMA** (+20-day)
    and the **MBI** table (**4.5R** burst ratio + **XP**). Includes a **Swing Confidence** score.
  - **TREND** — "Are intermediate trends healthy?" — inputs: **52-week Net New Highs (NNH)** and
    **% above 50-day SMA** (+200-day).
  - **BIAS** — "Is long-term health supportive?" — input: **% above 200-day SMA** (shown as a big
    number + bar).
- **Universe-health table** — breadth per universe bucket (Nifty 50 / 500 / Midsmall 400 /
  Smallcap 250 / Microcap 250): %>10/20/50/200 DMA, 4.5R, new highs/lows, a status label.
- **Sector heatmap** — sector RS + breadth + setup-density, with a FOCUS / WATCH / AVOID action.
- **Setup-availability panel** — count of tradable setups per family (Strong Start, EP, VCP,
  Pullback…) with a permission state (ALLOWED / SELECTIVE / HALF-SIZE / OFF) and a one-line reason.
- **Action badges** — New longs (ALLOWED/SELECTIVE/REDUCED/OFF), add-ons, avoid-late-breakouts,
  favor-tight-setups, event-risk.

*(A prototype of the top strip + quadrant already exists in this exact style — treat it as the
reference build, then formalize + extend to the tables/heatmap/panels below.)*

### 5.2 Focus / Scanner page
**Answers:** "Which specific names are in play, and which to be careful about?"

- Two lists in the Reference-B pattern: **Confirmations** (candidates that passed) and **Caution**
  (extended / thin-data / flagged) — each row: ticker, setup type, a **Trade Readiness** grade
  (A+→C), % from 52-week high, price + day change, and a one-line reason.
- **Candidate card** (on select): symbol, setup family, **Trade Readiness score (0–100) + grade +
  evidence chips** (the named filters that fired: "prior-day tightness 88", "sector rank 3/28",
  "RVOL strong", "stop 2.1%"), a **mini price chart** with the setup marked, and a **trade-plan
  box** (entry zone, stop + stop-type, risk %, position size/qty, max ₹ loss, do-not-chase price).
  A **2-tap "log to journal"** action. **No buy button** — plan only, executed manually elsewhere.
- Filters: sector, setup type, grade, market-cap, extension. Beginner mode hides raw-number
  filters behind the plain-English ones.

### 5.3 Chart page (preset-driven)
**Answers:** "How do I read/execute this one setup?"

- A **candlestick chart** (daily + intraday) with **preset overlays** — the user picks a preset,
  not individual indicators. MVP presets: **Beginner-default** (MAs + volume), **VCP / Tight
  Base** (compression/**RMV** pane + pocket-pivot/VDU markers + pivot band), **Strong Start**
  (intraday: prev-close/prev-high lines, opening range, VWAP, RVOL panel). Each preset = a fixed,
  named set of overlays/panes — switching presets must **never** mix overlays from another.
- **Heatmap strips** above the chart (Reference B): e.g. **Minervini Pressure**, **Buy-Risk**,
  **Trend-Template**, each a horizontal row of green→red cells over recent sessions.
- **Side badges** (per-preset): compression/RMV, pocket-pivot count, persistency ("34 days above
  21 EMA"), stage, RVOL, regime support — each hover-defined.
- A **trade-plan / risk box** mirroring the candidate card. In-trade: entry/stop/trail/partials
  lines + open-risk + current R.

### 5.4 Journal / Review page
**Answers:** "Am I following my process, and what's working?"

- **Trade log** table (conditional-colored): date, ticker, setup, grade-at-entry, R-multiple,
  outcome. Sortable/filterable.
- **Fast entry** (≤2 min, mostly auto-filled from the candidate): entry/stop/size prefill,
  optional emotional-state tap, screenshot drop.
- **Mistake tags** (chips): chased-3rd-green-day, bought-extended, ignored-regime, stop-too-wide,
  moved-stop, no-setup, overtraded, etc.
- **Review dashboards:** win rate + expectancy + avg-R by setup, rule-adherence, an
  emotional-state × R crosstab, capture ratio, MAE/MFE distribution. Read-only, plain-English.

### 5.5 Pipeline Health page
**Answers:** "Is the data fresh and did tonight's run work?"
- Per-source ingest status + timestamps, last successful run per stage, any failures, and the
  overall freshness state that drives the global banner.

---

## 6. Domain vocabulary the design must accommodate

So the layout budgets space for the real content (glossary-worthy terms):
EM, **XP** (breadth-energy dial), **MBI** (market breadth indicator), **4.5R / 20R / 50R** (breadth
ratios), **day color**, **warning day**, **Momentum/Swing/Trend/Bias** quadrants, **MSwing**
(Homma), % above 10/20/50/200 DMA, **NNH** (net new highs), **RS** (relative strength), **ADR**,
**RVOL**, **VCP**, **RMV** (compression), **Persistency**, **Pocket Pivot / VDU**, **Burst Power**,
**Strong Start**, **EP** (episodic pivot), **Pullback**, **Trade Readiness** (score + A+→C grade),
**evidence chips**, **regime gating**, **setup permission**, stop / position size / gap-risk,
**R-multiple**, **MAE / MFE**, **mistake tags**.

---

## 7. State matrix (design ALL of these — beginner-safety lives here)

Every data surface needs explicit designs for:
- **Normal** — fresh data, populated.
- **Empty** — a valid "nothing today" (e.g. 0 candidates most nights) — must feel intentional
  ("0 setups tonight — market is SELECTIVE, sit tight"), never look broken or blank.
- **Stale** — inputs older than the last trading day → a loud banner **and** the affected numbers
  visibly de-emphasized; the regime posture must *hard-degrade* (never show a confident green
  regime on old data).
- **Auth-needed** — Fyers token expired → prominent reconnect banner + live surfaces marked stale.
- **Loading / skeleton** — calm, monospace-friendly skeletons.

---

## 8. Interaction patterns
- **Hover/tap any metric or column header → glossary definition** (InfoDot).
- **Beginner ⇄ Expert toggle** flips label style + reveals/hides raw columns app-wide.
- **Click a candidate → drawer/panel** with full readiness evidence + trade plan.
- **Preset switch on the chart** is instant and never mixes overlays.
- **2-tap journal entry** from a candidate.
- Keyboard-navigable; ARIA labels on badges/cards; WCAG AA contrast on the conditional colors
  (the green/red bands must pass on white).

---

## 9. Hard constraints / non-goals (do not design these)
- **No order/buy/sell buttons anywhere.** Execution is manual, off-platform. Plans only.
- **No black-box scores** — every number is traceable to named filters.
- **Single-user, private.** No social, sharing, multi-account, or "tips channel" surfaces.
- **No decorative color, gradients, shadows, or motion-for-motion's-sake.**
- Not a general charting platform — presets over free-form indicator assembly.

---

## 10. What we'd like back (the design-guidance MD + design_guidelines.json)
1. **Design tokens** — finalized palette (incl. the exact conditional-color bands for
   green/orange/red/gray/blue on white, contrast-checked), the mono + sans font stacks and which
   to ship-bundle, spacing scale, radii, border/hairline treatment.
2. **Type scale** — sizes/weights/tracking for: terminal chrome (mono, uppercase labels), data
   tables (tabular mono), headline numbers (the XP dial, the 46% bias), and prose reads (sans).
3. **Component specs** — anatomy for: pill label + status dot, conditional data table + cell,
   the quadrant card, the top decision strip, candidate card + evidence chips, heatmap strip,
   preset chart frame, banner, InfoDot tooltip, Beginner/Expert toggle.
4. **Layout** — the grid/rhythm for the Regime page (flagship) and how it flexes to the other
   surfaces; nav pattern recommendation.
5. **State designs** — the §7 matrix per surface.
6. **Responsive** — the app is desktop-first (laptop) but should degrade gracefully to a narrow
   window / tablet; specify breakpoints and what collapses.

## 11. Open design questions to resolve
- **Light only, or also a dark variant?** The chosen reference is light; an earlier direction was
  a dark "control-room." Recommend one, and if both, how they share tokens.
- **Primary font:** Cascadia vs JetBrains Mono (or another modern terminal mono) — pick one to
  bundle, with rationale.
- **Nav:** top tabs vs. left rail for 5 destinations, given desktop-first + beginner clarity.
- **Density default:** how much does Beginner mode hide, exactly, without feeling patronizing?
- **The verdict/annotation layer:** how to render the "plain-English read beside every number"
  systematically (fixed column? callout? inline?) so it scales beyond the quadrant page.
