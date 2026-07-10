# LENS: Episodic Pivot (EP) / Earnings-Theme

## Backbone parameters (TradeTM, exact — `INDIA_PLAYBOOK.md` §3.1)
- Growth screen: **~30%+ YoY AND QoQ growth in both EPS and sales** — soft benchmark, not a hard
  gate; ~80% of gap-ups don't actually clear this bar and should be treated as ordinary technical
  setups, not EP conviction plays. [TTM-B1, TTM-S9]
- **Day-0 entry = 5-min opening-range-high breakout** (NOT the gap-up price itself) — the
  first-5-minute ORB is the proxy trigger, stop = day's low (often the breakout-bar low). Skip if
  gap-up% + ORB% > 12% of prior close (circuit-risk skip, U5/backbone §1). Win rate 40-60%,
  initial stop 2-4%. [TTM-B2, TTM-S10]
- **Pullback entry (most common, highest R:R) = 10/21 EMA.** Every pullback to the 10/21 EMA is a
  pyramiding opportunity. [TTM-B3, TTM-S11]
- **Exit template = Magnitude, sell into weakness**: 21EMA close-break, or 50DMA if the stock
  hasn't extended far — NOT sell-into-strength except a 15%+ blow-off extension. EPs are <10% of
  trades but >35% of 2-yr returns — hold all-or-nothing on the strong ones. [TTM-B4, TTM-S36]

Source coverage: **STRONG**. Primary sources: `design/study/EP/Episodic Pivots_ A Complete Guide
for Indian Traders_text.txt` (blog, Anurag Venkatakrishnan/TradeTM), `design/study/EP/ep_qna_formatted.txt`
(live Q&A transcript), `design/study/EP/main.md` (digest of both). Cross-checked against
`design/study/Tradetm/On Bear Markets and Episodic Pivots Explained_text.txt` (same author,
TradeTM blog).

## 1. RECOGNITION markers (price/volume/chart, concrete)

- **Catalyst**: new information the market did not expect — primarily strong post-market-close
  earnings, or a non-earnings catalyst (new order wins, government policy change, sector
  tie-up). Two types per the guide: **Earnings EP** and **Non-Earnings EP**.
- Earnings screen (Stock Bee rule, cited in guide): **30%+ YoY AND QoQ growth in both revenue
  and EPS** — "not strict," used as a benchmark not a hard gate.
- **Must gap up or open strongly the next session** — "otherwise market not surprised." No gap,
  no EP.
- Entry execution window is narrow and specific: **9:07-9:30 AM** premarket/pre-open tiling of
  charts, sorted by gap-up % between **9:00-9:15 AM** (Bear Markets blog). On the gap day itself
  (Day 0): **5-minute opening-range breakout (ORB) high** is the trigger, stop = the day's low
  (often the breakout bar's low).
- Skip the gap-day entry if **gap + opening-range-high extension exceeds ~12%** — circuit-limit
  risk removes the ability to get a quick risk-free stop.
- Deep-dive stats cited (1688 gap-ups, 2017-2022): **<45% of EPs trigger on the gap day**; those
  that do, "often give immediate risk-free entries" enabling pyramiding. Observed win rate on
  gap-day entries: **40-60%**, initial stops **2-4%**. [TTM-B4, TTM-S36]
- **Follow-through, not Day 0, is the real test**: "EP success is NOT based on your ORB entry.
  It is based on the follow through." Many Day 0 gaps fail or pull back hard on Day 1 — true
  confirmation is Day 1-2+.
- **Pullback entry** (most common per guide): to the **10 or 21 EMA**. High R:R, used especially
  when the earnings reaction was strong but the numbers themselves "not great." Entry near
  prior-day high on a strong start after the pullback. "Every pullback to the 10/21 EMA is a
  pyramiding opportunity."
- **Late/follow-through play**: entering after management commentary (capex plans, utilization,
  future guidance) validates the narrative days later even if Day 0 faded (Ola example: faded
  after results, resumed on later capex/utilization commentary). Not every delayed entry is
  valid — must be justified by fresh information, not just "it's still going up."

## 2. CONTEXT requirements (regime/sector/liquidity)

- **Stock must be "neglected"** before the catalyst: a dead/range-bound stock or one in a base/
  downtrend — "no one is putting money... a dead stock." A stock already up 100%+ in six months
  is explicitly NOT neglected (QnA, direct counter-example).
- Market-cap filter cited in the guide: **> ~300 Cr**.
- Low float + neglected = larger magnitude moves; consolidation bases outperform pure downtrends
  as the "neglected" precursor.
- **Environment matters more for EP than for pure technical setups**: in the Bear Markets blog,
  EP + EP-pullbacks are named a "First-Order Opportunity" that shows "resilience regardless of
  market conditions" — one of the few setups that keeps working in bad tape. In one quarter
  described, "the only stocks that actually worked ... were the earnings moves."
- Catalyst strength buys resilience: "if the catalyst is strong enough it is a lot more resilient
  to any market fluctuation" (QnA) — government policy or major tie-up (e.g. Nvidia) news
  survives broad weakness better than a plain earnings beat.
- **IPO + EP special case**: fresh listings are under-tracked, so IPO + base breakout + strong
  result is called a "purple spot" — fewer existing holders means confirmation triggers cleaner
  follow-through (Netweb example: initial gap faded, later Nvidia tie-up commentary created the
  real move).
- Late-hour results (9-10pm) reduce next-morning smart-money reaction speed (QnA).
- Prioritization when several EPs break out together: simplest rule given is **enter in sequence
  of their breakouts** — described as a rare ("tail-end") situation in practice.

## 3. DISQUALIFIERS

- No gap / no strong open next session — "otherwise market not surprised."
- Gap + opening-range extension > ~12% on Day 0 — skip, no risk-free room left.
- Stock already up 100%+ in the past six months — not neglected, doesn't qualify as EP regardless
  of the catalyst.
- Results "not strong enough" (per QnA, this is the case ~80% of the time) — treat as ordinary
  technical setup, not a true EP; don't force conviction language onto a marginal beat.
- Late entry with no fresh justifying information — chasing a delayed move on story alone,
  without new management commentary or price confirmation, is flagged as unsound ("does not mean
  every delayed DP... is going to be good").
- Reverse EP (bad news causing a pivot down) is explicitly out of scope of these sources — the
  guide says "search for yourself," no framework given here.

## 4. GOOD vs BAD example (in words)

**GOOD** — Ola-style pattern (QnA): result during market hours triggers upper circuit same day
(Day 0), then fades. Days later, management commentary (production ramp, capex, utilization)
gives fresh information — the real move resumes on that follow-through data, not on the original
number alone. Lesson drawn: wait for management commentary validating the narrative, not just
the headline beat.

**GOOD** — Netweb (IPO + EP): initial post-listing gap on results failed to hold. Later Nvidia
tie-up commentary created the genuine gap-up/re-rating context. Because it was a fresh IPO with
few existing holders, the follow-through was cleaner once the real catalyst (the tie-up, not the
original result) landed.

**BAD** — Angel-style failure (QnA): strong Day 0 reaction, made "risk-free" quickly, then pulled
back hard when a negative development (credit access issues) surfaced days later — cited directly
as a caution that "there are so many stock outs which happen after making your risk free," i.e.
Day 0 strength alone does not guarantee follow-through; the position must still be monitored and
exited on trail breach.

**BAD (implicit)** — any stock that gapped up on merely-average numbers (the ~80% case) treated
as a headline EP conviction play rather than the ordinary technical setup it actually is.

## 5. Exit / failure notes

- **"EP is a primary case for selling in weakness"** — this is the core exit philosophy stated
  directly in the digest/guide.
- Trail: exit if the **21 EMA is breached on a closing basis** (bar closes below the broken EMA),
  or use the **50 DMA** if the stock hasn't extended too far from it.
- Preferred stance on strong ones: **"hold all or nothing"** — the deep-dive data favored full
  holds over partial trims on the strongest EPs.
- Selling into strength is reserved only for (a) temporary extensions of roughly **~15% from the
  10 EMA**, or (b) deliberately trimming to protect mental capital with intent to buy back — not
  a standard profit-taking rule.
- Pyramiding continues on every pullback to the 10/21 EMA as long as the trend/thesis holds.
- Base rate context to carry into the debate: guide claims **10-20 strong EPs/year**, historically
  **<10% of trades but >35% of returns** (from the 1688-gap-up 2017-2022 deep dive) — useful for
  calibrating conviction sizing language, not a hard rule. [TTM-B4, TTM-S36]
