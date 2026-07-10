# LENS: IPO Base

## Backbone parameters (TradeTM + Stocksgeeks, exact — `INDIA_PLAYBOOK.md` §3.5)
- **First inside bar = highest-probability trigger** near the IPO-day level; **double inside bar
  = immediate trade** (~80% of moves start the very next day — don't delay entry waiting for a
  third confirmation bar). Right-side triggers generally: inside bar / mini-coil. [SG-IPO-First-
  Inside-Bar, SG-Inside-Bar-Double]
- **J-curve / bar-by-bar reversal anticipation (backbone, codeable):** an IPO base is *designed*
  to look non-optimistic on the surface; the base is read bar-by-bar, not pattern-by-pattern.
  - **Overlap+contraction reversal signal:** 3+ consecutive bars with **>50% overlap** of the
    prior bar's range, **contracting range**, and closes migrating inside the range = supply
    absorption → reversal imminent — anticipate the turn from this signal rather than waiting for
    a breakout candle. [TTM-H-I3, TTM-H-I1]
  - **J-curve entry pattern:** 3+ bars consolidating *down* (the "J" dip), then 1 bar of upside
    expansion smaller than the consolidation width = a valid entry trigger, not a failed base —
    this is the base's designed non-optimistic look resolving upward. [TTM-H-I6]
  - **IPO stop width:** 4% is TIGHT here, not wide — you are buying the rock-bottom of a completed
    reversal; use a wider default (4-6%) than velocity/absolute setups (1-2%). [TTM-H-I2]
- **Fire-power ↔ entry quality (scale sizing by entry precision):** a loose/late entry needs a
  20%+ move to go risk-free; a tight, early (bar-by-bar-anticipated) entry needs only 2-3%. Flag
  any entry requiring >15% upside-to-risk-free as suboptimal fire-power and size down accordingly.
  [TTM-H-I5]
- IPOs are high-momentum, low-price-history → weight regime/breadth (MBI, EP frequency) into
  confidence, not chart quality alone. [TTM-H-I4]

Source coverage: **STRONG** for pattern/entry mechanics, **THIN** for exit/context rules (the
transcript is entry-focused). Sole source: `design/study/IPO/IPO_trading_transcript.md`
("IPO Trading Setups — Transcript (Part 2)", ~218KB teaching transcript), digested faithfully in
`design/study/IPO/main.md`. No second source exists in the study folder for cross-check — treat
single-sourcing as a caveat when weighing this lens against EP/Strong Start.

## 1. RECOGNITION markers (price/volume/chart, concrete)

- IPO bases are **small — days to a few weeks** — so individual candle behavior and simple
  structures carry more analytical weight than volume or fundamentals in the early base.
- **VCP (Volatility Contraction Pattern) foundation applies**: price range squeezes progressively
  smaller; higher lows while highs are tested/held = net buying ("institution defending the low").
  Progressive tightening example cited: **8pt → 5pt → 2pt range**.
  - Higher low = strength (institutions not letting it fall).
  - Lower low = weakness.
  - Flat high + higher low = positive tilt.
  - Lower high + higher low, or flat low = weaker read.
- **Right-side completion triggers** (what to look for on the final contraction, i.e. the entry
  trigger candle/structure):
  - **Inside bar** (one candle fully inside the prior candle's range).
  - **Mini coil** (multiple candles inside one prior candle's range).
  - Coil / tight range generally.
- **Named pattern set** used repeatedly across the transcript's chart walkthroughs:
  1. **Crowbar** — strong candle, then 2-3 small sideways candles, then resumption ("bar with a
     crowbar on top" — price does not fully retrace to the EMA before ripping again).
  2. **Hook** — price pulls back to the EMA after breakout, retests, resumes ("price catches up
     to EMA").
  3. **Fast Flag** — breakout, then sideways for a few days (price doesn't fully return to EMA),
     resumes ("EMA catches up to price").
  4. **Inverted Head & Shoulders** (including on a trendline) — common in small IPO bases; the
     speaker explicitly warns real-time versions have uneven shoulders/heads, "use visual
     imagination," don't demand textbook symmetry.
  5. **VCP / T-VCP / Tight Squeeze** — as above.
  6. **Inside Bar / Mini Coil / Double Inside Bar** — the primary right-side triggers.
  7. **Sideways/Range after breakout** — trade the range break or a coil forming inside it.
- **Demand/strength signals** (used across chart examples to validate a base before entry):
  - Long-tail candles (small body, long lower wick) = demand pulling price up from below.
  - Bottom spring + outside bar (a down day followed by a bar that engulfs the prior close).
  - Multiple higher lows.
  - Strong up candle with **limited retracement — ideally under 50% of that candle's range held**
    ("50% retracement rule on strong candles").
  - A single "dirty" (bad) candle during broad market weakness with **no follow-through lower** =
    shakeout, not real damage — treated as buyable if the prior low holds.
- **Multi-timeframe confirmation rule**: Daily > 75-min > 15-min in importance. Always confirm
  the higher timeframe shows strength/readiness before acting on a 15-min trigger. For most
  traders: stick to 15-min and above ("1-min increases frequency and whipsaw dramatically").
- **BSC-to-NSC migrations** (exchange/segment moves) are treated identically to true IPOs
  behaviorally — a setup is tradable on the new listing chart even if the old listing shows none.

## 2. CONTEXT requirements (regime/sector/liquidity)

- Volume is explicitly **secondary on very fresh bases** — "you can't do volume analysis freshly."
  It becomes progressively more important as the base ages/enlarges (see below).
- **As the base grows** (2+ months), the weighting shifts: less reliance on individual candle
  size, more on **volume dry-up on down days, symmetry, proper "boxes," and multiple tests of a
  resistance level turning into support**.
- Theme/sector narrative "helps but is not required" for a valid IPO setup per the transcript —
  weaker context requirement than EP, where narrative is central.
- IPO + EP combination is explicitly endorsed in the closing Q&A: institutions being active in
  IPOs can raise odds further when broader market breadth (MBE) is favorable — no prohibition on
  stacking the two lenses on the same name.
- Speaker's stated bias: prefers buying at "higher" areas within the base when possible, to avoid
  the opportunity cost/time-decay of buying too low and waiting through chop.

## 3. DISQUALIFIERS

- **Gap + opening-range extension too large on day 1** — same "no quick risk-free entry"
  disqualifier logic used elsewhere in these sources; flagged explicitly for IPO setups.
- **Excessive retracement on the key strong candle (>50%)** — breaks the demand read, disqualifies
  the setup as currently structured.
- **Low-liquidity chop** — explicitly called out as producing more whipsaws on lower timeframes;
  avoid trading tight patterns on illiquid names on 15-min/1-min charts.
- **No follow-through after breakout, or after a "good" candle** — if the market doesn't confirm
  the candle's implied strength in the next bars, the setup is not validated; do not hold the
  read on hope.
- Perfect textbook pattern symmetry is NOT required and is not itself a qualifier — but the
  speaker still requires the underlying demand evidence (higher lows, tails, limited retracement)
  to be present; a "pattern-shaped" chart with no demand evidence is not a real signal on its own.

## 4. GOOD vs BAD example (in words)

**GOOD** — Honasa-style read (per transcript synthesis): multiple long-tail candles (repeated
demand evidence), mini coils forming, an inverted structure visible on the 75-min chart "despite
chop" on the daily — the lower-timeframe read confirms the higher-timeframe demand signals even
though the daily alone looked messy.

**GOOD** — Jyoti CNC-style read: a clean hook pattern on the higher timeframe, with the **first
inside bar** after the pullback used as the actual entry trigger — textbook sequencing of
"identify structure on daily → drop to lower TF for the tight-stop trigger."

**BAD / SKIPPED (by the speaker's own standard)** — Swiggy-style case: a "beautiful VCP" existed
on the lower timeframe, but the speaker skipped it that day, citing better alternatives elsewhere
or a preference to buy at a higher confirmed level rather than force an entry on the lowest
theoretical point of the base. Illustrates that pattern presence alone doesn't force a trade —
selectivity/comparative ranking across the day's candidates still applies.

**BAD (implicit, general)** — any base showing a strong candle whose gains get erased beyond the
50% retracement line, or a breakout that stalls with no follow-through bar — both explicitly
named as reasons to stand aside.

## 5. Exit / failure notes — **NEEDS SOURCE**

The transcript is almost entirely entry-focused. Only two exit-adjacent statements are explicit:
- Stops are kept tight on fresh listings: **daily-TF stop ~3-4%; 75-min or 15-min entries can get
  1.5-2%** stops, "tries not to exceed ~4% or so on very new names."
- Trailing/booking style is only loosely mentioned: "some hold to 20-40% on strong movers; half
  out at 15-20% is a common suggestion" — stated as a general practice note, not a rule specific
  to IPO bases, and not elaborated with mechanics (no EMA/DMA trail rule given, unlike Strong
  Start's 20-DMA/10-DMA trail or EP's 21-EMA/50-DMA trail).
- No management-of-losing-position guidance, no partial-profit trigger levels, no explicit
  invalidation-of-thesis criteria are given in this source. Any exit rules used operationally for
  this lens beyond the stop-tightness note above should be flagged as "NEEDS SOURCE" and either
  borrowed explicitly (and labeled as borrowed) from the Strong Start or EP lenses, or left to the
  debate agent's general judgment rather than presented as Arora/IPO-transcript doctrine.
