# Edge test — results (2026-07-31)

Protocol fixed in advance: `EDGE_TEST_PREREGISTRATION_2026-07-31.md`.
Code: `manas_os/backtest/gate_edge_test.py`. Nothing was written to the DB.

## Verdict

**NO EDGE — and worse than neutral. The gate is inverted.**

The names the gate PASSES underperform a random pick. The names it REFUSES
outperform the market. This is not "the filters need tuning"; the cascade is
selecting against the pool it draws from.

---

## The numbers

**Metric**: 10-session return, entry at the **next session's open**, minus that
day's universe median (so a rising tape is not mistaken for skill). CIs are a
block bootstrap resampling whole scan dates — 10,000 iterations — because names
surfaced on one day share a market and are not independent bets.

### Test 1 — what the gate refused (279 scan dates, 2025-03-19 → 2026-06-30)

| Gate that refused | rows | dates | median excess | 90% CI | hit rate |
|---|---|---|---|---|---|
| fresh-leg | 364 | 142 | **+2.33%** | [+0.99, +2.90] | 58.8% |
| risk | 1,961 | 213 | **+1.26%** | [+0.95, +1.63] | 58.5% |
| participation | 1,603 | 177 | **+1.10%** | [+0.72, +1.45] | 57.3% |
| regime | 60,506 | 279 | +0.54% | [+0.44, +0.64] | 54.0% |
| trend-template | 17,225 | 203 | +0.44% | [+0.32, +0.58] | 53.6% |
| tradability | 80,094 | 279 | +0.43% | [+0.30, +0.55] | 55.3% |
| **RANDOM control** | 11,160 | 279 | **+0.11%** | [+0.02, +0.21] | 50.9% |

Every gate's rejects beat a random name. The three *late* gates — the ones that
fire after a name has already survived the cascade, i.e. the most discriminating
ones — reject the best names of all.

### Test 2 — the product itself (55 dates, 2025-07-09 → 2026-07-13)

| Cohort | rows | dates | median excess | 90% CI | hit rate |
|---|---|---|---|---|---|
| **PASSED (what the tool shows you)** | 520 | 55 | **−0.31%** | [−0.64, +0.17] | **46.9%** |
| REFUSED, near-miss gates | 6,659 | 55 | +0.62% | [+0.32, +1.02] | 54.5% |
| REFUSED, all gates | 34,505 | 55 | +0.53% | [+0.33, +0.77] | 55.5% |
| RANDOM control | 2,200 | 55 | +0.12% | [−0.09, +0.38] | 51.1% |

PASSED and REFUSED-near-miss have **non-overlapping intervals** (+0.17 vs +0.32).
The difference is not noise.

---

## Attacks I ran on my own result

**"It's beta — the gate refuses volatile names and the window was a bull market."**
Refuted. Split by tape direction (was the universe median positive that day?),
the outperformance is present in *both*, and for the risk gate it is **larger on
down days**:

| Gate | up-tape median | down-tape median |
|---|---|---|
| risk | +0.82% | **+1.47%** |
| participation | +0.73% | +1.22% |
| fresh-leg | +2.88% | +1.55% |

**"A median hides the left tail, and the risk gate exists to prevent ruin."**
Partly valid, for exactly one gate:

| Gate | p10 | p50 | p90 | mean | share below −10% |
|---|---|---|---|---|---|
| risk | −6.23% | +1.26% | +12.00% | +2.12% | 3.5% |
| participation | −6.99% | +1.10% | +10.56% | +1.47% | 4.6% |
| fresh-leg | **−10.54%** | +2.33% | +16.30% | +2.04% | **10.7%** |
| tradability | −5.50% | +0.43% | +6.09% | +0.50% | 3.4% |

Only `fresh-leg` cuts a genuinely fatter tail (10.7% of its rejects fall >10%,
triple the baseline) — and even it has the highest median and p90. The **risk**
gate's rejects have the *same* downside as everything else and a much better
upside. The risk gate is not buying safety; it is refusing better trades.

**"The passed cohort is two July dates wearing a trench coat."**
Substantially true, and it is the main weakness here. 448 of 520 passed rows come
from 2026-07-10 and 2026-07-13 alone. Split into two near-independent samples:

| Sub-sample | rows | dates | median | 90% CI | hit rate |
|---|---|---|---|---|---|
| July 2026 only | 455 | 6 | −0.29% | [−0.57, +0.16] | 47.0% |
| Excluding July 2026 | 65 | 49 | −0.54% | [−1.56, +0.74] | 46.2% |

Same sign, sub-50% hit rate in both. Neither alone is conclusive; agreeing is
what makes the direction credible. **The PASSED result is directional, not
precise.** The REFUSED result is the strong one — 279 dates, 160k+ rows.

---

## Why this happens (hypothesis, not measured)

`fresh-leg` refuses names that are *extended* — already >8% above the 21EMA or
>15 bars into a leg. `risk` refuses names whose stop would be wide. Both are
proxies for "this name is moving fast", and momentum continuation is precisely
the effect a swing system is supposed to harvest. The cascade encodes a
mean-reversion prior while the setups it hunts are momentum setups.

Testable next: rank pool names by extension and by stop-width and check whether
forward return rises monotonically. If it does, these two gates should be
inverted or deleted, not tuned.

---

## What survives

The **discovery pool is not worthless.** Names the scanner surfaces at all show
+0.43–0.54% excess against a random +0.11%, on 279 dates, with non-overlapping
intervals. The confluence / near-52w-high / discovery layer carries modest real
information.

**It is the gate stacked on top that destroys it** — the pool is +0.5%, the
subset the gate passes is −0.31%.

Keep: the data pipeline, the discovery pool, the journal, the refusal ledger
(which turned out to be the most valuable table in the database — it is the only
reason this test was possible at all).

Kill or invert: the fail-fast cascade as a *gate*.

---

## Bias ledger — what was actually controlled

| Bias | Status |
|---|---|
| Survivorship | **Absent by construction.** The pool for date D comes from `daily_prices` rows dated D (`universe_filter.py:292`), and no production code deletes price rows — verified: delisted names still carry their historical sessions |
| Look-ahead, entry price | **Controlled.** Next session's open, never the scan-day close |
| Look-ahead, features | **Effectively clean.** `gates.py` touches no DB; two unbounded queries found (`candidates.py:701`, `eod_detectors.py:509`) both harvest names/dates only, no future prices |
| Price restatement | **Absent.** One production writer (`bhavcopy.py:144`), 5-day rolling window, no split/bonus adjustment layer anywhere |
| Market direction | **Controlled** via same-day universe-median excess, plus the up/down-tape split |
| Same-day correlation | **Controlled** via block bootstrap over dates; n reported as dates |
| Costs | Cancel in excess terms (both cohorts pay them). Absolute returns would be ~0.40% lower |
| Epoch contamination | **Present, and unavoidable for Test 2.** All seven decision-path files were created on/after 2026-07-06; no ≥10-day rule-stable matured window exists |
| Date concentration in PASSED | **Present.** 86% of passed rows from 2 dates. Reported above, not hidden |

## Deviation from the pre-registration (§9)

The pre-registered primary metric was PASSED vs RANDOM via a full scanner replay
over history. **That could not be run**: one `scan_candidates()` call takes over
10 minutes, so 370 sessions is weeks of compute. Substituted the `refusals`
table — 186,635 rows the scanner itself wrote at the time — which measures the
same question from the reject side, on far more data, and needed no replay.

The pre-registered primary comparison was still run, on the 55 dates where a
passed cohort exists. It failed. The decision rule fires **NO EDGE**.
