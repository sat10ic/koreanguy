# LENS: Post-Earnings Announcement Drift (PEAD)

Source coverage: **STRONG** (revised — the original MISSING verdict searched only
`design/study/*` and `manas_os/docs/Tradetm/*`; the `design/Feedback/*` research briefs, not
searched in that pass, contain a full PEAD literature review plus a rules-first mechanism spec,
and `design/LEARNINGS.md` T2.2 adds this project's own empirical backtest on top). Primary
sources: `Feedback/Manas 2.0 EDGE RESEARCH - global edges unsaturated in India.md` (Edge A —
the mechanism spec), `Feedback/manas 2.0 - gpt 2.0.md` (Indian academic evidence, Part B),
`Feedback/manas v2 claude.md` (Part B.1/B.2 evidence ranking), `Feedback/Manas 2.0 USIC champion
setups translated for India.md` (Tanmay Khandelwal cross-validation), `Feedback/manas 2.0 - gpt
3.0.md` and `Feedback/Manas 2.0 GLM response.md` (roadmap framing) — plus `LEARNINGS.md`'s own
T2.2 backtest, which is this system's empirical result, not textbook theory, and is kept in its
own section below rather than blended with the literature claims.

**Do not conflate with EP (`LENS_EP.md`).** EP is a gap/narrative-shift catalyst traded for
immediate follow-through (Day 0 ORB, Day 1+ EMA pullback). PEAD is the underlying academic
phenomenon EP is built to harvest — continued abnormal drift over a period of days-to-months
following an earnings surprise, driven by slow information diffusion rather than an immediate
gap trigger. `manas v2 claude.md` explicitly treats "EP done properly" as the PEAD mechanism
operationalized with EP's catalyst + gate discipline (`Feedback/manas v2 claude.md` — Part C.1,
point 2). The two lenses should be debated as one family with EP supplying entry mechanics and
PEAD supplying the underreaction thesis and the survival/expectancy discipline.

## 1. RECOGNITION markers (price/volume/chart, concrete)

- **Global anomaly base rate**: PEAD is "one of the most replicated anomalies in finance" — prices
  drift in the direction of an earnings surprise for roughly 5-60 sessions after the announcement
  because information diffuses slowly (`Feedback/Manas 2.0 EDGE RESEARCH...md` — Edge A, "The
  global evidence").
- **India academic evidence, Nifty 500 2002-2017**: a long-short strategy sorted on standardized
  unexpected earnings (SUE) produced **~6% spread return over 64 days** between highest- and
  lowest-SUE portfolios, robust after controlling for beta, size, value, illiquidity, and
  idiosyncratic volatility (`Feedback/manas 2.0 - gpt 2.0.md` — Executive Summary and "PEAD and
  earnings drift" table row). Earlier India work (469 firms) found significant post-event
  abnormal returns in **35 of 37 quarters** (`Feedback/manas 2.0 - gpt 2.0.md` — same table row).
- **Narrower drift estimate cited elsewhere**: Indian studies find meaningful drift of roughly
  **~4.8-6%** after earnings surprises, concentrated in under-covered small/mid caps
  (`Feedback/manas v2 claude.md` — line ~159-161, and again at B.2 "Episodic Pivots (EP) / PEAD").
- **Rules-first mechanism (the buildable spec)** — a name qualifies when ALL hold
  (`Feedback/Manas 2.0 EDGE RESEARCH...md` — Edge A, "Mechanism (rules-first)"):
  - `earnings_power` detector fires: 30%+ QoQ+YoY EPS and sales growth, plus a gap-up.
  - `500 ≤ market_cap_cr ≤ 8000` (the "under-covered zone" — above this is too well-followed,
    below is pump territory).
  - Gap fills < 40% intraday (a quality gap, not distribution).
  - Delivery_z ≥ +1.0 on the gap day (sustained accumulation, not a quick flip).
  - Not flagged by the MAX-effect / lottery-stock exclusion (`Feedback/Manas 2.0 EDGE
    RESEARCH...md` — Edge C).
- **Live-adaptation filter**: skip names where the post-result day closes in the bottom quartile
  of its day range despite a nominal beat — that pattern "usually signals guidance or quality
  issues" (`Feedback/manas 2.0 - gpt 2.0.md` — "PEAD and earnings drift" table row).
- **Independent practitioner cross-validation**: Tanmay Khandelwal (USIC 2023, +129%, $1M+
  division) states his edge verbatim as finding stocks with the best **earnings momentum**, not
  the best price momentum — cited as independent real-world confirmation of the PEAD thesis, run
  on US mid-caps and translated to India as the same under-covered-zone logic (`Feedback/Manas
  2.0 USIC champion setups translated for India.md` — "Tanmay Khandelwal" section).

## 2. CONTEXT requirements (regime/sector/liquidity)

- **Why it's structurally durable in India** (three named moats, not just "unsaturated because
  new"): (1) a retail-dominated market with slow diffusion — institutions can't deploy into
  ₹500-5000cr names fast enough to close the gap; (2) **no consensus-estimates data for
  small/mid-caps is itself the signal** — if the tool doesn't have analyst forecasts, neither
  does the broad market, so the "surprise" in a gap-up is genuinely novel information; (3)
  operator/pump noise in the small-cap space causes most screens to avoid the space entirely,
  leaving genuine fundamental-drift names under-followed even by screens that could find them
  (`Feedback/Manas 2.0 EDGE RESEARCH...md` — Edge A, "Why it's unsaturated in India").
- **Market-cap band is the core context gate**: 500-8000cr, per the mechanism spec above — outside
  this band the edge is either arbed away (large-cap) or dominated by pump risk (micro-cap).
- **Size/costs**: for long-only application, use only the positive-surprise sleeve; size single-name
  risk so 1 ATR ≈ 35-50bps of portfolio loss; avoid illiquid small names around result day if
  impact cost is high; consider scaling in over 2-3 days rather than buying the full opening gap
  (`Feedback/manas 2.0 - gpt 2.0.md` — "PEAD and earnings drift" table row, sizing column).
- **Evidence-tier ranking**: PEAD is ranked the **2nd-strongest** evidence-graded setup in the
  India survey, behind only cross-sectional momentum (which is index-proven via the Nifty 500/
  Midcap150 Momentum 50 factor indices) — ahead of 52-week-high breakouts, pullback/VCP entries,
  mean reversion, IPO bases, and high-tight flags (`Feedback/manas v2 claude.md` — Part B.1
  evidence-quality ranking, and B.3 comparative synthesis: "Strongest, most defensible in India
  recently: cross-sectional momentum ... and PEAD").
- **India-specific execution complication**: circuit limits lock catalyst gaps, compressing entry
  into the pre-open + first 15 minutes; the drift window (T+5/T+10/T+20) is exactly what the
  journal/outcomes loop measures (`Feedback/manas v2 claude.md` — B.2 "Episodic Pivots (EP) /
  PEAD", "India complications").
- **Roadmap priority**: multiple briefs independently rank the PEAD/order-win drift module as the
  single highest-value backtest and build priority on the existing data stack (`Feedback/manas
  2.0 - gpt 3.0.md` — priority table rows; `Feedback/Manas 2.0 GLM response.md` — roadmap row 7).

## 3. DISQUALIFIERS

- Market cap outside the 500-8000cr under-covered band (too-followed above, pump-risk below)
  (`Feedback/Manas 2.0 EDGE RESEARCH...md` — Edge A mechanism).
- Gap fills ≥ 40% intraday — a distribution gap, not a quality gap (same source).
- Delivery_z < +1.0 on the gap day — a quick flip, not sustained accumulation (same source).
- Flagged by the MAX-effect/lottery-stock exclusion — this is named explicitly as PEAD's "natural
  pair": "PEAD says yes to drift names, MAX says no to lottery names" (`Feedback/Manas 2.0 EDGE
  RESEARCH...md` — Edge C, closing line).
- Post-result day closes in the bottom quartile of its day range despite a nominal beat — signals
  guidance/quality issues, not genuine surprise (`Feedback/manas 2.0 - gpt 2.0.md`).
- **Beyond these, no additional named disqualifiers (specific stop-loss rule, minimum liquidity
  floor beyond the mcap band, holding-period cutoff rule) are stated in the Feedback sources for
  the PEAD lens as such — do not invent one.** The T+5/10/20 window is described as a measurement
  horizon, not a hard exit rule, in these sources.

## 4. GOOD vs BAD example (in words)

**No named single-stock GOOD/BAD walkthrough example is given for PEAD specifically** in the
Feedback docs (unlike EP's Ola/Netweb/Angel examples) — the India evidence here is presented as
portfolio-level academic backtest statistics (SUE deciles, 64-day holds) and a rules-first
mechanism spec, not as narrated single-name case studies. Marking this **NEEDS SOURCE** rather
than substituting an invented example.

## 5. Exit / failure notes

- Academic holding period used in the underlying Indian study: **hold up to 64 days** after the
  announcement for the long-short SUE-decile portfolio (`Feedback/manas 2.0 - gpt 2.0.md` — "PEAD
  and earnings drift" table row). This is a backtest holding convention, not a stated stop/trail
  rule for a single-name discretionary trade.
- No PEAD-specific trail, partial-profit, or stop-loss mechanic is stated in the Feedback sources
  — mark any such rule NEEDS SOURCE if it surfaces in a debate transcript. For single-name
  discretionary exit mechanics, the debate should fall back to whatever EP (`LENS_EP.md` §5)
  or general risk-management rules the tool already uses, not invent PEAD-specific ones.

## 6. Measured on our data — `LEARNINGS.md` T2.2 (empirical, distinct from literature claims above)

This section is this project's own backtest finding (2026-07-06, 1,209 price-only gap events,
2025-04..2026-06 window, forward from event close) and is kept separate from the general/global
PEAD literature above because it produced a materially different, more cautious verdict when
tested on *price-only* gaps without the catalyst leg (`LEARNINGS.md` — "2026-07-06 — T2.2
PEAD/gap-drift study"):

- **Liquidity gradient is the finding, and it is monotonic**: illiquid names (<5cr turnover, 67%
  of all 1,209 events!) showed **-2.50% T+10 / -4.50% T+20** — i.e. NEGATIVE forward returns.
  5-25cr turnover: -0.49%. 25-100cr: +0.24%. **>100cr turnover: +1.73% T+10, 40.5% hit rate** —
  the only bucket with a clearly positive edge.
- **Illiquid gap-ups are exit-liquidity traps**; genuine follow-through drift lives only in liquid
  names, the opposite of where most of the raw event population (67%) sits.
- **Bigger gaps are not better**: gaps >10% showed a **median -2.12%** return — gap size alone is
  not a quality signal.
- **Micro-cap bucket showed -8.65% / -11.63%** (T+10/T+20) — stated in `LEARNINGS.md` explicitly
  as validation for the MAX/lottery + pump exclusions, i.e. this number is **a warning that
  micro-caps are dangerous on a naive price-only gap screen, not a rule to trade on or a
  contradiction of the exclusion logic.**
- **VERDICT**: the naive small-cap-PEAD thesis is **NOT confirmed for price-only gaps** — the
  **catalyst leg (30% EPS+sales growth) is load-bearing, not optional**. Catalyst-conditioned
  drift (i.e. the actual Edge A mechanism from the Feedback research, which requires the
  earnings-growth screen) is untestable historically on this system's data because growth data
  exists only for dump dates; the journal/outcomes loop is expected to build that sample live
  going forward.
- **Resulting actions** (per `LEARNINGS.md`): (1) EP must keep all legs and never relax to
  price-only gaps; (2) the turnover floor of Rs 5cr is re-validated as a hard cutoff; (3) a
  liquidity-tier boost inside EP ranking (liquid EP ranked above thin EP) is queued as a future
  change, subject to the project's one-change-per-quarter discipline.
- **How to read this against §1's literature numbers**: the 6%/64-day and 4.8-6% India academic
  findings above are unconditional/price-and-fundamentals-blended results from published studies;
  this project's own T2.2 test isolated the *price-only* gap signal and found it insufficient by
  itself — confirming the literature's own emphasis on genuine earnings surprise (not just a gap)
  as the active ingredient, while adding a liquidity-tier finding not present in the literature
  sources reviewed above.
