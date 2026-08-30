# Unified Momentum Desk — UI/UX Product Manual V2

**Status:** controlling product/UI manual — supersedes `UNIFIED_DESK_UI_UX_MANUAL.md` (V1, retained as reference)
**Adopted:** 2026-08-29 (unidesk DECISIONS D13)
**As-built (2026-08-29, D14–D17):** a fixture prototype lives in `unidesk_terminal/` — rebuilt same-day against this V2 spec (Tonight/Candidates/Stock/History/Research/Settings, per §2). It does **not** fulfill N8 / W-H. The shipped nightly artifact is markdown (`unidesk/momentum/report.py` → `data/market/reports/tonight_*.md`), not this screen spec. Data truth is Build Manual V2 §3 / §12. Regime, index series, and 18 PIT universe snapshots exist in parquet; the prototype's 3 real Momentum Burst candidates are transcribed verbatim from `tonight_2026-07-03.md`, everything else is tagged illustrative in the UI. Do not treat fixture cards as live scan output. Full state: `unidesk_terminal/HANDOFF.md`.
**Product shape:** an **evening desk** for a swing trader — read tonight's report, drill in, decide. Not a live intraday terminal.
**Precedence:** data truth comes from Build Manual V2; if UI wording risks misrepresenting data, the build manual wins.

---

## 0. What changed from V1

V1 designed a live trading cockpit: Flow console, trigger queues, real-time
pulses. That design served a product we no longer build first (D10). V2
designs the **evening ritual** instead:

```
after close → the desk builds tonight's report
          → you read it in ten minutes, calm, unhurried
          → you decide what goes on tomorrow's watch plan
```

The live module (if ever built) adds a confirmation overlay later — it does
not redefine the product.

V1's best ideas survive: the 3-Layer Quality Stack (Stock / Setup / Entry),
honest unknowns, beginner-vs-pro vocabulary, visual-first panels. V1's live
widgets (pulse matrix, trigger queue as "airport board", realtime pulses)
are removed or re-scoped to the evening review.

---

## 1. The product feeling

Not a broker terminal. Not an AI chat. A **quiet research desk at night**:

```text
part disciplined research workbook
part scout's morning report
part checklist-driven pre-flight
```

Emotional targets: calm, sharp, honest, in-control. Anti-targets: hype,
realtime anxiety, KPI soup, "AI says buy".

---

## 2. Navigation (V2)

```text
TONIGHT      the daily report — the product
CANDIDATES   scan results across all detectors, filterable
STOCK        one-symbol deep dive
HISTORY      past reports, past candidates, what happened next
RESEARCH     ablation, baselines, negative findings (pro)
SETTINGS     weights, gates, universe, data status
--- later phases ---
MARKET (breadth deep-dive) · WATCHLIST · TRADERS (social) · JOURNAL · LIVE (optional module)
```

The live module, if built, adds a **CONFIRM** overlay on STOCK — not a tab
of blinking screens.

---

## 3. TONIGHT — the primary screen

The nightly report, rendered. Fixed reading order, top to bottom:

```
┌────────────────────────────────────────────────────────────┐
│ HEADER   Wed 15 Jul · Regime: CHOP (12 sessions)           │
│          Universe: 1,014 gated · 2,760 ingested · 1 gap    │
├────────────────────────────────────────────────────────────┤
│ A. REGIME STRIP    BULL/BEAR/CHOP + breadth mini-bars      │
│                    (above 50/200 DMA, near highs/lows)     │
├────────────────────────────────────────────────────────────┤
│ B. TONIGHT'S SETUPS — candidate cards, grouped by setup    │
│    each card: symbol · setup name · the 3 named numbers    │
│    that passed · coverage · policy chip (ADVISORY)         │
├────────────────────────────────────────────────────────────┤
│ C. YESTERDAY'S CALLS — what happened to prior candidates   │
│    (measured outcomes; losses shown like wins)             │
├────────────────────────────────────────────────────────────┤
│ D. WATCHLIST DRIFT — quiet movement of tracked names       │
├────────────────────────────────────────────────────────────┤
│ E. HONESTY FOOTER — data gaps, missing delivery, skew,     │
│    unknowns — named, never hidden                          │
└────────────────────────────────────────────────────────────┘
```

**Candidate card (Setup section):** symbol, close, setup name, the 3-Layer
Quality Stack (Stock / Setup / Entry), lifecycle chip
(`forming · fresh breakout · climbing · played out` — BananaPatterns
vocabulary, D12), one-line "why", and the trigger/invalidation pair if the
setup defines them. Clicking opens STOCK.

**Report first-read test:** a new reader finds the day's candidates and the
market mood in under a minute, without jargon.

---

## 4. CANDIDATES — the Scout's full output

Filter chips (setup type, sector, lifecycle, quality band), sort by
score/coverage/recency. Same candidate cards as TONIGHT, denser. The
candidate scatter (entry quality × stock quality, bubble = setup quality,
colour = lifecycle) lives here — it is the "map of opportunity" and the
product's signature visual after the Quality Stack.

---

## 5. STOCK — the deep dive

Panels, in reading order:

1. **Header** — price, sector/industry, lifecycle chip, policy chip, feed status.
2. **Chart** — candles, volume, EMA21/50 (+200 when history allows), AVWAP
   anchors, trigger/invalidation lines, base boxes (VCP-style geometry when
   the detector drew one). Restrained: no indicator wall.
3. **Decision panel** — the 3-Layer Stack, entry-quality contributors
   (each bar decomposable), regime context, circuit/exit-risk chips.
4. **Setup evidence** — which detectors fired, which rules passed/failed,
   with the named numbers (e.g. "contraction 0.73 ≤ 0.80 ✓").
5. **History strip** — this symbol's past candidates and their measured outcomes.

Every number decomposes to its contributor; every unknown is named
(`DELIV_PER missing 3 sessions`, `no sector membership`). Nothing decorated.

---

## 6. HISTORY — accountability as a feature

Past nightly reports, past candidate cards joined to measured outcomes
(MFE/MAE/R, breakout held/failed — from `research/labels.py`). Contains the
losses, visibly. This screen exists so the desk can never curate its own
highlights.

---

## 7. RESEARCH (pro)

Ablation ladder status (which model is winning), baseline comparisons per
the swing-edges spec, parameter register state, leakage-suite status, and
the **Negative Findings board** — retired features with their death
certificates, visibly displayed. Per manual R-H: a killed feature is
documented, not deleted.

---

## 8. Vocabulary (beginner → pro)

| Internal | Beginner label |
|---|---|
| Stock Quality | Stock Strength |
| Setup Quality / detection | Setup |
| Entry Quality | Entry Timing |
| Liquidity gate / circuit risk | Exit Risk |
| Regime (R0) | Market Mood |
| Lifecycle stage | Stage (Forming / Fresh / Climbing / Played out) |
| Contract / rule failure | Why it didn't qualify |
| Outcome labels | What happened next |

Pro mode shows the internal terms, contributors, weights, and config hash.
One app structure, two vocabularies — never two apps.

---

## 9. Interaction & honesty rules (carried from V1, still binding)

* Single-click progression: TONIGHT → CANDIDATES → STOCK → back.
* Selection persists across tabs.
* Unknown is visibly unknown; stale carries its timestamp; zero is shown as zero.
* No alert may contain a number code didn't compute.
* Colour never carries meaning alone — icon + text + shape always accompany it.
* Every screen answers ONE primary question in one scan.

---

## 10. Screens not built (and why)

| V1 screen | V2 disposition |
|---|---|
| FLOW console (live) | removed — belongs to the optional live module (Build V2 §8); if built, a CONFIRM overlay on STOCK, not a tab |
| TRADERS (social) | deferred with U-P4 (TraderLog Lite) — owner decision pending |
| JOURNAL | Phase 8 per build manual — deferred |
| MARKET | folded into the Regime Strip + a later deep-dive when breadth history accumulates |

---

## 11. Acceptance (per screen, condensed)

* TONIGHT: readable in one minute; candidates + regime + yesterday's outcomes visible; honesty footer present.
* CANDIDATES: filters don't overwhelm; every card names its numbers.
* STOCK: every score decomposes; every unknown named; chart uncluttered.
* HISTORY: losses as visible as wins; outcomes joined to past calls.
* RESEARCH: ablation ladder and negative findings on display.
* ALL: works in Beginner and Pro; no stale value masquerades as live; the report could be printed and still make sense.

---

## 12. Build order

1. Report renderer (markdown → the TONIGHT layout) — first, because the
   report is the product even before any UI exists.
2. CANDIDATES + STOCK read-only views over the report/candidate store.
3. HISTORY + outcome joins.
4. RESEARCH views; SETTINGS (weights/gates as config UI).
5. Polish, keyboard, saved views — last.
```
