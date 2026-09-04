# Visualization brainstorm + the "too deterministic?" question

Status: BRAINSTORM — nothing here is committed scope. Ideas are ranked within each section.
Every chart must obey the existing law: the number it draws must already exist in an API
payload (no client-side metric derivation), ECharts for panels, design tokens only.

---

## Part 1 — Visualization ideas (grounded in data the tool already persists)

### Tier 1 — directly answers a question the user actually has

**1. Near-miss verdict chart (the most important chart the tool doesn't have)**
Line/band chart: forward T+10 median R of the PASSED cohort vs the REFUSED-near-miss cohort,
rolling as sessions accumulate. Data: `refusals` + `outcomes` (both exist).
This is the "is the gate right?" chart — and today the answer is uncomfortable (refused
outperformed passed on the last measured window). Making this visible turns the tool's biggest
open question into a monitored dashboard instead of a buried LEARNINGS caveat. If the refused
line stays above the passed line for a quarter, the thresholds get a documented calibration
pass. This chart is the honest answer to "are we missing good calls" — measured, not felt.

**2. Gate proximity map (per refused name)**
For each near-miss: a compact bullet/radar showing distance-to-pass on each of the 6 gates
(e.g. extension 8.9% vs 8.0% cap → 0.9pp over; delivery_z -0.3 vs 0 floor → 0.3 under).
Data: `refusals.evidence_json` already stores the numbers. Beginner reading: "this name missed
by a hair on ONE gate" vs "this failed everything." Feeds directly into the Part-2 discussion —
a hair-miss on one gate is exactly the case where rigid thresholds bite.

**3. "What would it take" chip**
Text companion to #2: the single minimal change that would flip a refusal to a pass
("needs delivery_z +0.4" / "needs 2 more days of base"). Pure arithmetic against the LOCKED
thresholds — deterministic, explainable, and it teaches the user what the gate actually wants.

**4. Trade lifecycle river (per open position)**
X = sessions since entry, Y = open R. Background bands colored by exit-engine phase
(INITIATION / TREND / EXTENSION), trail-stop line overlaid, +1R book-⅓ event marked.
Data: `journal_trades` + bars + `trail_plan()` outputs. This is the Position Coach made visual —
the beginner SEES why "hold through the wobble" was right last time.

**5. Regime ribbon with outcomes overlaid**
Calendar strip of `market_mode` per session (colored ribbon), journal trade entries/exits
plotted on top with R-result color. Answers: "do I actually make money in the regimes the
governor lets me trade?" Data: `regime_snapshots` + `journal_trades`.

### Tier 2 — strong, build after Tier 1

**6. Refusal funnel over time** — stacked area of `by_gate` refusal counts across sessions.
Shows the gate breathing with the regime (tradability dominates always; fresh-leg spikes in
extended markets). Data: `refusals` grouped by date.

**7. Confluence-family UpSet chart** — which FAMILY COMBINATIONS (base+momentum,
catalyst+accumulation…) produce the best forward R. UpSet beats Venn for 4 sets. Data:
`source_payload_json.setup_family` + screener families + `outcomes`. This is also the
empirical check on the "≥2 families" LOCKED threshold.

**8. Stop-vs-ADR outcome scatter** — every historical card: x = stop% / ADR%, y = realized R,
colored by hit/miss. Validates (or kills) the 0.75×ADR warning chip with data.

**9. Expectancy matrix evolution** — small-multiples of the family×regime heatmap by quarter,
so the user watches cells earn trust (grey → n≥20 → colored) over time. The moat, animated.

**10. Breadth weather calendar** — GitHub-contribution-style year grid of MBI day colors +
warning days. One glance = "what kind of year is this." Data: `regime_snapshots`.

### Tier 3 — nice-to-have / expert-only

**11. Position heat sunburst** — capital → sector → position → open risk share (expert Watchlist).
**12. Delivery-z strip under ChartDrawer candles** — histogram pane, z>+1.5 highlighted.
**13. Slippage tracker** — planned entry (card) vs actual fill (journal) distribution; teaches
the user their own execution cost. Data exists once decisions carry entry_price.
**14. Sector-rotation quadrant** — already planned (T3.2 expert accordion); listed for
completeness so this file is the one viz backlog.

---

## Part 2 — "Isn't the tool too deterministic? Wouldn't an LLM orchestrator be better?"

The worry is legitimate and the tool ALREADY has evidence for it: on the last measured replay
window the refused near-miss cohort OUTPERFORMED the passed cohort at T+10. Rigid thresholds
demonstrably left money on the table in that window. So the question deserves a real answer,
not a doctrine recital.

### Why the gate stays deterministic anyway

1. **The 3/10 review was precisely about non-explainable numbers.** An LLM that "adjudges
   multiple parameters with its own logic" is a black-box score with better vocabulary. Same
   inputs → different outputs run-to-run; no named reason a beginner can learn from; no way to
   replay it over history to prove it has edge. Every mechanism that earned back trust this
   rebuild (refusal ledger, replay harness, expectancy loop) requires reproducibility.
2. **The edge loop is built ON determinism.** Expectancy cells, probation rules, threshold
   calibration — all of it assumes the same rule fires the same way every time. An LLM gate
   can't accumulate a sample because it isn't the same gate twice.
3. **"Misses good calls" is a calibration problem, not an architecture problem.** The gate has
   ~6 numeric thresholds. If the near-miss cohort keeps outperforming, the documented response
   is a quarterly, one-at-a-time, LEARNINGS-logged loosening (extension 8%→9%? RS 80→75?) —
   tested by replay before it ships. That's how a rigid system learns without becoming a mood.

### Where an LLM genuinely fits (proposes — never disposes)

The plan's "theatre" list bans LLM *confidence scores*, not LLM *language*. Roles that add
real value without breaking one-writer/no-black-box:

- **L1. Card narrator** — turn a card's evidence JSON into three plain-English sentences for
  beginner mode ("Strong delivery into a quiet base; sector is leading; the stop is tight
  because the trigger bar is small"). Numbers stay the gate's; words are the LLM's. Advisory
  label, zero effect on rank/grade.
- **L2. Near-miss devil's advocate** — nightly, the LLM reads the top-10 near-misses and
  argues the OTHER side ("refused on delivery_z -0.1σ, but disclosure feed shows a large order
  win yesterday — worth a watchlist add"). Output = a tagged watchlist suggestion the user
  accepts/rejects with one tap. The acceptance rate is itself loggable — the LLM earns trust
  the same way a setup family does: n and hit-rate, in a ledger.
- **L3. Weekly journal reviewer** — synthesize the week's trades + skips + mistake tags into a
  short written review ("both your early exits were in INITIATION phase — the coach said HOLD
  both times"). The Mental-Game-of-Trading loop, automated.
- **L4. Disclosure reader** — parse corporate announcements/order-win feeds into one-line
  catalyst chips on EP cards ("₹450cr order win, ~8% of revenue"). Extraction, not judgment.
- **L5. Threshold-change analyst** — quarterly: LLM reads LEARNINGS + replay outputs and
  DRAFTS the calibration memo (which threshold, what evidence, expected effect) for the human
  to approve and replay-test. It orchestrates the *review*, not the *trade*.

Rule of thumb that keeps all five safe: **the LLM may generate text, suggestions, and drafts;
it may never generate a number that ranks, sizes, gates, or exits.** Everything it proposes
lands in a ledger with its own n/hit-rate, so even the LLM's judgment gets the expectancy
treatment. If its near-miss picks (L2) beat the gate over a real sample — THAT, not intuition,
is the evidence to widen the gate.

### Suggested build order if any of this gets picked up
1. Viz #1 (near-miss verdict chart) — it's the empirical referee for this whole debate.
2. Viz #2+#3 (gate proximity + what-would-it-take) — cheap, teaches the user the gate.
3. L2 (devil's advocate, with acceptance ledger) — the first LLM role, because it's the one
   whose value is directly measurable against the gate it challenges.

---

## Part 3 — Making the tool "organic" without making it a mood

The real question behind "too deterministic": can the tool ADAPT, not just repeat? Yes — the
principle is **adaptivity in the parameters (slow, evidenced, logged), determinism in the
decision (fast, reproducible)**. Organic ≠ non-deterministic; organic = feedback-coupled.
Ranked options, least→most radical:

**A1. The calibration loop that's already designed (just run it).** Quarterly threshold review
driven by the near-miss cohort + replay A/B, human-approved, LEARNINGS-logged. The gate already
"learns" — at quarterly cadence, with evidence. Cheapest organic mechanism; currently unused.

**A2. Percentile thresholds instead of constants.** Replace fixed numbers with data-anchored
percentiles recomputed at each quarterly review: e.g. extension cap = the historical extension
level beyond which forward T+10 median R went negative (per regime), not a hand-picked 8%.
Frozen between reviews → still reproducible; but the NUMBER comes from the market, not from a
doc. This is the single best answer to "rigid measures miss good calls" — the measure itself
is fitted to what actually worked.

**A3. Regime/volatility-conditional parameters.** One threshold table per volatility state
(index ATR percentile tercile). A 6% extension means something different in a quiet tape vs a
wild one. Still a lookup table — just a smarter key. Costs one extra dimension of replay
validation (n per cell shrinks — trust ladder applies).

**A4. Learned RANK, ruled GATE.** Keep the binary gate exactly as-is, but let the ordinal
ranking among survivors use a fitted model (logistic regression on the gate-evidence fields →
P(T+10 ≥ +1R)). Logistic, not a neural net: coefficients are inspectable ("delivery_z carries
3x the weight of confluence"), so no-black-box survives. The gate decides WHO enters the feed;
the model only orders them. Needs n≥150+ outcomes before it beats the current heuristic
tiebreak — the trust ladder already defines when it's allowed.

**A5. Override ledger (human-as-sensor).** Let the user override a refusal — one tap, mandatory
reason, half size — and track overrides as their own expectancy cohort. If the user's overrides
systematically beat the gate, that's measured evidence the gate is too tight (and of exactly
where); if they lose, the tool shows the user their own numbers. The beginner's intuition gets
the same treatment as any setup family: earn trust with n.

**A6. LLM roles (Part 2 above).** L1-L5, with L2 (devil's advocate + acceptance ledger) first.

Anti-patterns, restated once: per-trade threshold nudging (gate becomes un-backtestable),
online learning that updates weights daily (curve-fits noise; n per regime is tiny), LLM
generating any gating/sizing number (3/10 review, again). Every adaptive mechanism above keeps
one property: **at any moment, the tool can answer "why did you refuse this?" with a named rule
and a number — and "why is the rule set this way?" with a dated LEARNINGS entry and a replay.**
