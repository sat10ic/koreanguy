# Edge test — pre-registration (2026-07-31)

Written BEFORE any result was computed. The point of writing it first is that
every choice below — cohorts, metric, horizon, thresholds, what counts as a
pass — is fixed while I am still ignorant of which choice would flatter the
tool. Anything I change after seeing numbers gets recorded in §9 with the reason,
so the reader can discount it.

The question: **do the names this tool surfaces beat a fair baseline?**

Not "is the code correct", not "does the pipeline run". Those are already known
to be true and have never been the complaint.

---

## 1. Cohorts

| # | Cohort | Definition | What it is for |
|---|---|---|---|
| A | **PASSED** | candidates that cleared the full gate on scan date D | the product |
| B | **REFUSED** | candidates evaluated on D that failed at any gate | isolates the gate's *marginal* contribution — same pool, same day, only the gate differs |
| C | **RANDOM** | random draw from the tradeable universe on D, same count as A that day | the fairness baseline. If A does not beat C, the gate is decoration |
| D | **UNIVERSE** | every tradeable name on D | the market's own return; separates "edge" from "the tape went up" |

A-vs-C is the primary comparison. A-vs-B answers a different and weaker question
(the gate ranks within an already-screened pool) and is reported second.

Cohort C is drawn with a **fixed seed**, and the draw is repeated 200 times so
the baseline is a distribution, not one lucky sample. A single random draw is not
a control; it is an anecdote.

## 2. Entry price — the look-ahead that kills most backtests

Entry is the **open of the session AFTER the scan date**. Not the scan date's
close.

The scan runs on EOD data. You cannot buy at a close you only learn about once
the close has happened. Using D's close as the entry price silently grants a
free intraday move and is, in my experience, the single most common reason a
dead strategy backtests well.

Exit is the open of session D+11 (i.e. 10 full sessions held). No stops, no
trailing, no discretion — this measures the *signal*, not the trade management.
Trade management is a separate question and mixing them makes both unanswerable.

## 3. Primary metric (pre-committed, single)

> **Median 10-session excess return, cohort A minus cohort C, net of costs.**

Excess = the name's return minus the *same-day universe median return*. This
removes the tape: in a month where everything rose 8%, a cohort returning 8% has
no edge and the raw number would say otherwise.

Median, not mean — swing returns are fat-tailed and one 60% winner drags a mean
into looking like a system.

**Costs subtracted from every trade, both cohorts:** 0.40% round trip
(brokerage + STT + exchange + stamp + GST, plus slippage on a mid/small-cap
market order). Real costs are the reason a "+0.3% edge" is not an edge. If the
true figure is materially different from 0.40% I will state the sensitivity, not
quietly pick the flattering one.

## 4. Secondary metrics (exploratory — labelled as such, never used to claim a win)

- Hit rate: fraction with excess return > 0
- Median raw return (no excess adjustment)
- Same at 5 and 20 sessions
- Per-setup-family breakdown
- A vs B

These exist to describe. If the primary metric fails and a secondary one passes,
that is a **failure with a hypothesis attached**, not a pass. Stating this now
because after seeing results the temptation runs the other way.

## 5. Significance — block bootstrap, by date

Same-day picks are one bet, not N bets. Twenty names surfaced on the same day
share a market, often a sector, sometimes a theme. Treating 500 rows from 30
scan dates as 500 independent observations overstates significance by roughly
the square root of the clustering — it is how a coin-flip strategy earns a
p-value.

So: **resample whole scan dates with replacement** (10,000 iterations), recompute
the median difference on each resample, report the 5th–95th percentile interval.

**n is reported as the number of distinct scan dates, alongside the row count.**
30 dates is 30 observations no matter how many rows they carry.

## 6. Bias ledger — filled in from the three traces before any number is computed

| Bias | Control |
|---|---|
| Survivorship | universe for date D must come from data published on D. If it comes from a current symbol master, delisted names are invisible and every result is inflated — this is a **hard stop**, not a caveat |
| Look-ahead (features) | every gate query must bound on `<= D`. Any unbounded query found = that feature is excluded or the test is abandoned |
| Look-ahead (entry) | next-session open, per §2 |
| Price restatement | if `daily_prices` is retro-adjusted for splits/bonuses, the replay sees prices the scanner never saw. Quantify how many symbols are affected; exclude them if material |
| Selection at persistence | if only top-N candidates were ever written, cohort A is pre-selected and the A-vs-C comparison is invalid as stated. Would need reconstruction from the refusal ledger |
| Epoch contamination | restricted to rule-stable windows from the git/data overlay. Pooling across rule versions measures an average of strategies that no longer exist |
| Maturation | rows need ~20 sessions of forward data. Anything after ~2026-07-01 is unmeasurable today and is excluded, not partially counted |
| Same-day correlation | block bootstrap, §5 |
| Multiple comparisons | one pre-committed primary metric, §3 |
| Costs | 0.40% round trip, §3 |

## 7. Decision rule (pre-committed)

- **EDGE**: primary metric > 0 with the bootstrap interval excluding 0, on ≥30
  distinct scan dates. → keep the gate, proceed to tune it.
- **NO EDGE**: interval spans 0, or the median is negative. → the gate does not
  select. Keep the data pipeline and the journal; stop maintaining the gate.
- **UNMEASURABLE**: any hard stop in §6 fires, or fewer than 30 usable scan
  dates. → say so and say what would have to be rebuilt to answer. This is a
  legitimate outcome and will be reported as plainly as the other two.

I expect UNMEASURABLE is a real possibility given what the traces are checking.
Recording that expectation now so that if it happens it reads as a finding and
not as an excuse.

## 8. What this test does NOT answer

- Whether the *user's own discretionary* trades have edge (that is the journal,
  separate sample, different question)
- Whether trade management (stops, trails, exits) adds or destroys value
- Whether the LLM council helps — it gates what reaches the user via the sizer
  JOIN and needs its own A/B on the same substrate
- Whether PB-1 specifically works, unless its 50 frozen trades sit inside a
  usable epoch

## 9. Deviations log

*(Anything changed after results were seen goes here, with the reason. Empty at
time of writing.)*
