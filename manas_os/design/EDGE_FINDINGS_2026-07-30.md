# Edge findings — 2026-07-30

Everything measured during the A1 component audit, plus the practitioner specs the
user supplied that day. **Read this before touching the setup/grading/ranking work.**
Every number here has its `n` and its date window; nothing is quoted from memory.

---

## 0. The one lesson that invalidated three of my own findings

**The code changes faster than outcomes mature, so almost nothing can be measured.**

Gate code changed on 07-11, 07-19, 07-21, 07-22 and 07-30. Forward returns need
10–20 sessions. Three separate times I measured a "defect" against code that had
already been replaced:

| I claimed | reality |
|---|---|
| 63,232 regime refusals prove the gate is a switch | that gate stopped emitting on **2026-07-09**; current code's string has **0 rows** |
| 60 winners refused for "no measured move" | fixed by the WAVE_L trail tier on **07-21**. Counts per date: 330/329/208 on 07-15/16/17 → 13/13/22 from 07-21 |
| 17 winners lost to stop-cap hair-misses | ADR-scaled cap landed **07-22**, after every case I cited |

**Rule going forward:** stamp a cascade version into every `refusals` and
`scan_candidates` row, and freeze thresholds for 50 trades before drawing any
conclusion. This is the user's own checklist rule ("run untouched for 50 straight
trades") and it is not merely discipline advice — it is the precondition for
measurement.

---

## 1. Recall — the tool misses the winners

Window 2026-07-13..07-21, mature forward data, liquid universe (≥₹5cr, no ETFs).
Winner = gained **≥10% within 10 sessions**.

```
331 winners existed.  The tool listed 40.   RECALL 12.1%
...while showing 139–281 names a night.
```

Not selective — it shows plenty, just not the ones that moved.

**Why, after regrouping the 436 refused winners** (reason strings embed rupee and
percent values, which fragments one cause into hundreds of unique strings — always
strip them before grouping):

```
130  trend-template   not in a confirmed uptrend (close/50SMA/200SMA)   30%
119  tradability      avg turnover below floor                          27%
 41  risk             no measured move
 31  risk             R:R below floor
 16  trend-template   insufficient history
```

**POLICY refusals — the regime deliberately disallowing a family — were 0%.**
Every missed winner died on a mechanical gate, not a deliberate decision.

Named examples: DIACABS +44%, HUHTAMAKI +38%, GSPCROP +36%, NILKAMAL +30%,
CYIENTDLM +29%. RAIN was refused 3× for "no measured move" on days it went
+6% to +8%. SKYGOLD was refused for a stop of **5.1% against a 5.0% cap**.

⚠️ Caveat: in a tape falling 61%→29% above-20DMA, many "winners" are counter-trend
snapbacks that `trend-template` is *designed* to refuse. Some of the 130 may be
correct. Needs a rising-tape window to separate defect from policy.

---

## 2. The rank carries no signal — this is the core defect

588 ranked candidates with forward data:

```
rank band        n    mean fwd%   win≥10%
top 10%         56      -1.43%       7%
10-25%          85      -0.36%       4%
25-50%         150      -1.13%       6%
50-75%         146      -1.73%       5%
bottom 25%     151      -1.21%       7%

top-10% minus bottom-25%:  -0.21pp   →  RANK IS NOISE
```

Top 5 by rank each night — what the user actually sees:

```
07-13  +2.87%  2 winners
07-14  -5.00%  0
07-15  -4.60%  0
07-16  -2.26%  0
07-17  -1.78%  0
```

**"The top calls are not doing well" is literally true.** For a user who trades 1–2
names a night, ranking quality — not gate membership — is the binding deficiency.

---

## 3. Precision — indistinguishable from random

Same dates, same entry/stop rules, our picks vs randomly chosen liquid stocks:

```
RANDOM liquid   n=1,181   mean -0.508R   win 21%
OUR TOOL        n=  550   mean -0.488R   win 22%
edge: +0.02R
```

The tape over that window: declines beat advances on 6 of 9 days (worst 69/328),
% above 20DMA halved 61%→29%. Everything long lost money.

**Do not read this as "the gates are worthless."** One falling tape, 7 sessions, is
one regime; −0.488 vs −0.508 distinguishes nothing in either direction. The safety
gates (ASM, circuit, pump, lottery) are tail-risk insurance whose value never shows
in mean R. But it does mean **chasing recall is premature** — with precision at
random, more recall just means more random names.

---

## 4. Entry and stop mechanics are NOT the problem

Replayed our own candidates under the Hindi-transcript trader's rules
(buy above previous-day high, 2–3% stop) vs ours (pivot entry, our stop):

```
OURS: pivot entry + our stop        n=550   -0.488R   22% win
prev-day-high + 3.0%                n=740   -0.516R   22%
prev-day-high + our stop            n=740   -0.528R   21%
prev-day-high + 2.5%                n=740   -0.605R   18%
pivot + 2.5%                        n=550   -0.606R   18%
prev-day-high + 2.0%                n=740   -0.728R   13%
```

- Pivot entry is **more** selective than previous-day-high (550 vs 740 triggers) and
  performs **better**. His "never buy the pivot" rule did not transfer.
- Tighter stops are monotonically **worse** — these names are choppy, tight stops
  just get hit. More room = better.
- Our actual stop widths: median **3.45%** (11% ≤2%, 24% 2–3%, 55% 3–5%, 10% 5–8%).
  Not the "4–6%" I had assumed — that was the *cap*, not the actual.

---

## 5. Per-setup stats — the table that had never existed

T+10 outcomes joined to candidates. **All 328 rows are PRE-M3** (current-code cells
have no n≥5 yet — forward data has not matured).

```
setup_type                n   win%  avgWin  avgLoss  expect  holdD
pocket_pivot             30    33%   +5.94    -1.03   +1.30    9.7   ← only positive
persistent_momentum      19    11%   +4.64    -1.35   -0.72    4.9
near_pivot               91     5%   +1.31    -1.12   -0.99    5.1
ipo_base                 50     2%   +0.00    -1.20   -1.18    3.9
pullback                 34     0%   +0.00    -1.22   -1.22    2.6
recent_listing            7     0%   +0.00    -1.22   -1.22    3.0
watchlist_timing         90     1%   +0.27    -1.72   -1.70    3.5
ALL                     328     6%                    -1.04
```

`pocket_pivot` shows a textbook momentum profile — low win rate, fat right tail,
longest hold. **n=30 on dead code: a hypothesis, not a decision.**

`watchlist_timing` is the largest producer (639 candidates) and the worst performer
(1% win, −1.70R).

**Half the "setup types" are states, not patterns** — `watchlist_timing`,
`near_pivot`, `recent_listing` describe where a stock sits, not what it is doing.
That is part of why nothing sorts. `vcp` has fired **once ever** (07-30): nominally
detected, effectively absent.

---

## 6. The A+ spec (user, 2026-07-30) — the target definition

> "You don't lose money because your system is bad. You lose money because you trade
> B- and C setups."

1. **Strong Leader** — top 10–20% of market over 3–6M, usually a trending sector.
   Screens: 3-month high · 30% move in 2–3 months · 52WH
2. **Tight Structure** — a SEQUENCE: fast uptrend → pullback base → tight → range
   expansion (entry). Base patterns (flag/VCP/CPH), then NR5/NR7/inside bars,
   volatility AND volume drying up
3. **Clean Risk** — stop close and logical. **4% max.** "If you need a 7–8% stop, it
   is not A+"
4. **Freshness** — near 11/21 EMA, near demand, near breakout. Never extended/chased
5. **Market Tailwind** — indices above 21 EMA, breadth expanding, **leaders breaking
   out**. "If the market is chopping, your A+ becomes B-"

### The structural finding

`candidates.py:1417` — `grade_cap = "B" if (objections or ...)`. **Any objection caps
the grade at B**, and ~87% of passers carry the `regime_family` objection in any
non-RISK_ON tape. **A+ is unreachable outside a risk-on market — 100% of 1,734
candidates are grade B.**

By condition 5, that degradation is *correct*. The defect is what happens next: the
tool concludes nothing is A+ **and then lists 281 B's anyway.** It manufactures
exactly the boredom-trading the spec warns about. It should show **zero**.

### Gaps against the spec
- **The sequence in #2** — we snapshot; the spec requires a path over time. Needs a
  per-symbol radar/tracking layer the tool has never had.
- **"Leaders breaking out" in #5** — see §8.
- Our stop caps (6% / 7.5% / 8%) are **looser** than the A+ bar of 4%. He uses stop
  width as a *quality grade*; we use it only as a refusal cap.

---

## 7. The 14 setups to track (user list) — coverage today

```
YES  Flat base / consolidation box     VCP (1 hit ever)     Episodic Pivot
     MA pullback (10/20/50)            Inside bar continuation
     Undercut & rally                  Oversold bounce (RSI2/14)

NO   High Tight Flag          (scratch detector exists: scratchpad/htf_scan.py,
                               41 hits on 07-24, 12 at the US ≥90% pole bar)
     Darvas Box               52-week high breakout     Fibonacci retracement
     Trend-line breakout      Inverse head & shoulders  Falling wedge
```

Each needs: win rate, avg win, avg loss, holding period, expectancy — as a **nightly
artifact**, epoch-stamped. Cheapest to add first: HTF (detector written), 52-week-high
breakout, Darvas box.

---

## 8. "Leaders breaking out" — three independent sources, one missing metric

- **Leif Soreide**: check whether anything on your weekly watchlist actually broke out;
  if the right side looks weak and rolls over, stop trading
- **The Hindi-transcript trader**: market read comes from *his own watchlist* and his
  *last 3–5 trades* — if 3–4 broke out and came straight back, conditions aren't tradeable
- **The A+ spec, condition 5**: "leaders breaking out"

None of them uses a breadth dial. All three read the tape from **their own shortlist's
follow-through**. We have ~40 sessions of scan history and this metric does not exist.
Probably the single highest-value missing measurement in the tool.

---

## 9. Breadth study (user-supplied chart) — indicts our breadth stack

838 logged breakout trades, Oct 2019–Nov 2022, 31 breadth rules tested, 10 cleared
their 95% range. Baseline "plain price filter" +1.27R.

**Helped** (all NH−NL family bar two):
`10-day sum of NH−NL above zero +1.72R` · `Caruso 3 days net new highs +1.68R` ·
`cumulative NH−NL above 20d avg +1.68R` · `Elder NH ratio 10d-avg >50% +1.64R` ·
`Stockbee up50/down50 monthly +1.58R` · `Elder 5-day sum >0 +1.30R` ·
`10-day up/down share volume >1 +1.12R` · `A/D line rising over 20d +0.88R`

**Hurt:** `Stockbee 10-day 4% ratio below 0.5 −1.60R` · `$MMTW oversold <20% −1.57R`

**Cannot be called (ranges cross zero) — the entire "% above a moving average" family:**
T2108, % above 50-day, $MMTW, % above 200-day.

**That family is exactly what our MBI and 8 breadth panels are built on.** The family
that works — **NH−NL** — is one of our permanently "NEEDS INGEST" empty panels.

Its own footnote: one trade population, one era, ~31 variants — "the best-looking
result in a sweep this size is usually the luckiest one." Treat +1.72R as a
direction, not a number.

---

## 10. Market Quadrant visual (finallynitin) — the target presentation

Four stacked rows over a NIFTYMIDSML400 candle chart, each with a plain-English verdict:

| row | input | our status |
|---|---|---|
| **MOMENTUM** | Homma MSwing per index | portable (one of the 6 Pine ports) |
| **SWING** | % above 10-day SMA + Stocksgeeks MBI | have (`breadth_daily.pct_above_10dma`) |
| **TREND** | 52-week **Net New Highs** + % above 50SMA | **NH−NL = the missing piece** |
| **BIAS** | % above 200-day SMA | have |
| centre | candles + 4.5R/XP table | have (`regime_snapshots`) |

Four of five rows buildable today. Verdicts read like "SWING is DOWN — less than half
of stocks are above their 10MA", not like a metric dump.

---

## 11. The user's process checklist, scored

| rule | tool | verdict |
|---|---|---|
| ONE core setup | 5 families running | **violated** |
| ONE market filter | XP + MBI + 8 breadth panels + governor + quadrant | **violated** |
| RS + strong uptrend only | trend-template + RS floor 80 | honored (possibly too hard) |
| Risk 1–2% per trade | bands 0.35–1.0% | **below range** — 0.35% of ₹1.5L is ₹525, the micro-size leak encoded |
| Never average down | no averaging logic | n/a |
| Book partials, trail rest ("biggest concern") | +1R → breakeven + book ⅓, 3 trail modes | **honored** |
| Concentrated watchlist, max 5 | 139–281 shown per night | **violated** |
| One-pager process | 30 thresholds, 38 stages, 29 panels | **violated** — by his own test, we don't understand it |
| 50 trades untouched | changed 07-19, 07-21, 07-22, 07-30 | **violated** — and this is why nothing measures (§0) |
| Journal everything | 420 trades | **honored** — best asset |

---

## 12. What was actually changed on 2026-07-30

Committed `4f0533a5`: liquidity floor **₹5cr → ₹2cr** in
`engine/universe_filter.py::GateConfig`. Cost 119 of 436 missed winners (27%). Sized
for an institution — at a 1%-of-turnover impact cap, ₹5cr supports a ₹5,00,000
position against his ₹15,000. Stopped at 2.0 not 1.0 because the outcome sim is
close-to-close and cannot see spread (sub-2cr names carry 0.3–1% spreads = 0.05–0.15R
on ₹15k). Going lower needs live Fyers depth data, not an argument.

**Rejected after review:** the "no measured move" fix (already shipped 07-21), the
stop-cap tolerance band (ADR cap already is the principled form, shipped 07-22), and
a `>=` cap bug (does not exist — `plan.py:385` is `if stop_pct > cap`; JINDWORLD's
"5.0% exceeds 5.0%" is `.1f` display rounding).

**Not reconciled:** `alpha/features.py` still hardcodes `min_avg_turnover_cr=5.0` for
its own eligibility universe — now diverges from the default.

---

## 13. Open proposals, not yet approved

1. **FREEZE the gates** and version-stamp every refusal/candidate row. No threshold
   changes for 50 trades — including mine. Precondition for every other measurement.
2. **Make A+ mean the five conditions**, and show **nothing** when nothing qualifies.
   Collapses the list to 0–5 by construction. Large behavioural change; needs sign-off.
3. **Cut to one market filter**, candidate NH−NL (§9).
4. **Build "leaders breaking out"** from our own scan history (§8).
5. **Register all 14 setups** with nightly epoch-stamped stats (§7).
6. **Shadow ranker** trained on outcomes (6,669 rows) + journal (420 trades),
   ordering survivors only, never gating. Baseline to beat: −0.21pp, i.e. zero.
