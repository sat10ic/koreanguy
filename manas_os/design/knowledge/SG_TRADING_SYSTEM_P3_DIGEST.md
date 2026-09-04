# Stocksgeeks — Trading Systems Part 3 — Digest (2026-07-17)

Source: `C:\Users\satta\Downloads\book\stocksgeeks\Trading_Systems_Part3_transcript.md`
(789 lines; Hinglish/Hindi in Devanagari + Latin script, ASR-transcribed — garbled in
places, noted honestly below rather than smoothed over). Line numbers cited are the
transcript's own line numbers (odd lines = content, even lines = blank paragraph
separators). **Correction note:** an earlier pass mis-measured this file at 395 lines
(a `Get-Content` encoding artifact) and nearly missed lines 396-789 — the back half of
the video (readiness/X-factor/market-health section, the full Mazagon Dock deep-dive,
and the intraday "spurt" teach-in) is included here after re-reading the full file.

## Thrust Power
QUOTE (line 207-211): "थ्रस्ट पावर क्या होता है एक स्टॉक की [एबिलिटी] कि वो कितनी बड़ी
कैंडल बना सकता है ... जितनी बड़ी थ्रस्ट पावर उतना अच्छा एक स्टॉक की एबिलिटी कि वो बड़ी
कैंडल बना सकता है अप साइड में." = a stock's ability to print large candles. No exact %/day
count threshold is stated in this transcript. Judged relative/comparative: given a choice
between two running stocks, prefer the higher-thrust one because it lets you build size
without an oversized single-name % (line 217-221: "आपका स्टॉप लॉस ज्यादा छोटा आ रहा है तो
आपको साइज बढ़ाना पड़ेगा ... एक स्टॉक में 50-60% साइज ... बनता नहीं है").
- ADR gotcha (line 221-224): ADR alone can UNDER-report thrust for a stock that gapped
  straight up without basing — worked example GMDC, ADR "2.8 जो कम माना जाता है", yet gave
  a "150-200% पैराबोलिक" move with 4/17/8/13/12% single-day candles; **"एडीआर आपको पूरी
  चीज नहीं दिखाएगा"**.
- Combine with sector for best effect (line 227-229): "अगर सेक्टर प्लस हाई थ्रस्ट पावर
  स्टॉक मिल जाए मजा आ जाता है."
- Sizing consequence: "मैं ऐसे स्टॉक्स को अंधा साइज करता हूं" (line 289) — high-thrust names
  get "blind size."

## Linearity
QUOTE (line 181-183): a stock's post-breakout move is "लीनियर" to the extent it respects
the 20 EMA — "लीनियर मींस सिंपली रिस्पेक्ट करता हुआ 20 [ईए] को." Worked examples: a stock
gave ~450% never closing below 20EMA once; PSU-bank leaders in a 2023-24 bull run gave
75-80% "एकदम लीनियर"; a "पावर स्टॉक" example gave 900% peak / 346% realized with only ONE
20EMA close-violation after a 300%+ run (still graded acceptable) (lines 183-199).
Rationale (line 187-191): choppy (non-linear) stocks force repeated stop-outs and
re-entries — "बारबार एंट्री लेना इज नॉट एज इजी" — burning time-value-of-money; linear
stocks let you "राइड" one entry through the whole move. **No numeric violation-count
cutoff is given** — Assumption territory for engineering (see below).

## Pivot Cutter
QUOTE (line 231-234): a stock's HABIT of giving only a barely-tight breakout, stopping
you out, retightening, breaking out again, stopping out again — "थोड़ा सा ब्रेकआउट देंगे
एसएल खा जाएंगे फिर से टाइट होंगे फिर से ब्रेक आउट देंगे फिर से एसल खा जाएंगे ... ये ना
बारबार आके पिट्स काटते हैं." This is a **stock-level history trait**, checked via the
ticker's own past behavior (line 243: "इसकी हिस्ट्री देख कर के ऐसे स्टॉक्स को अवॉइड कर
दिया करो"), not a single-setup flaw. Named negative example: RK Forgings ("आर के फोर्स") —
gave one big lifetime move, then years of "एक्स्ट्रा टाइटनेस" traps (lines 239-243).
Sharda Energy example (line 279-284): cut traders 2-3 times before finally working —
"चौथी ट्रेड में बोल रहे हो कि मैं मेरा ट्रेड सक्सेसफुल हो गया ... इट इज नॉट वर्थ इट." Cost
framed as opportunity cost (time + R wasted vs. a cleaner name), not a hard rule count.

## Cleanliness of Base
Three concrete, directly-quotable tests (lines 245-259):
1. **Lows defended going up** — current low inside the base must stay above the previous
   low; one violation (forming a small inverted-shoulder dip) is tolerable, REPEATED
   violations are not ("ये बारबार नहीं होना चाहिए").
2. **Up-day % > down-day %, shrinking down-days toward the right** — "जो बड़ी अप कैंडल्स
   हैं उनका ... परसेंटेज चेंज ... ज्यादा होना चाहिए ... जो डाउन कैंडल ... कम होना चाहिए,
   जितने कम 4-5%."
3. **Wicks** — fewer/smaller upper wicks preferred; a rejection wick near resistance
   FOLLOWED by a down close is an explicit violation ("अगर वह नीचे जा रहा है देन इट इज अ
   वायलेशन"); sideways after rejection is tolerable.
"अर्जेंसी" (urgency): a clean stock lifts off fast and doesn't dawdle — "जितना टाइम पास
करेगा उतना बेकार स्टॉक है" (line 269). Worked negative example (Bajaj-something, lines
259-263) and a named "chchoppy" contrast pair are walked candle-by-candle. Same two rules
(cleanliness + don't buy too far above MA) are called out again for INTRADAY at lines
459-463 as the two biggest win-rate differentiators.

## Readiness of Setup — Pattern Taxonomy
Named patterns (lines 293-335, cross-corroborated in the IPO digest): TVCP (successive
contractions), Inverted-Head-&-Shoulders, IHS-on-trendline, Crow bar, Hook, Fast flag —
plus two explicitly de-prioritized styles: multi-hit-resistance and
fake-out/shake-out/reset (bear-market-only, low win-rate, "मैं इतना फैन नहीं इन सेटप का").
**Pivot Level ("cheat" areas)** — exact quote (line 317-321): divide the whole base into
three regions (top / middle / bottom — transcript literally says "टॉप हाफ ... मिडिल हाफ
... बॉटम हाफ," an ASR/loose-speech artifact for "third," not actually "half" x3). Want the
pivot in the TOP region ("हाई पिट"); MID region ("मिड पिट") acceptable; BOTTOM region ("लो
पिट") must be avoided completely: **"लो पीव्स को कंपलीटली अवॉइड करना है, जितना लो पीव्स को
अवॉइड करो उतना अच्छा."** The word "cheat" appears exactly ONCE, offered and then declined:
"लो पिट को ... चीट भी बोल सकते हो, मैं थोड़ा सिंपल लैंग्वेज यूज करता हूं" — **the compound
term "ultra-cheat" used in our own combination summary does NOT appear verbatim anywhere
in this transcript.**
**Volume dry-up on the final right side** is required (lines 321-329): if volume is still
high/rising into the pivot, supply isn't absorbed — avoid. "Too tight" is explicitly a
warning sign, not a virtue (lines 325-335, missed-trade examples: Avanti Feed, Gabriel —
speaker waited for "perfect" tightness that never came and the stock ran without him).

## Area of Interest / Up-base vs Down-base
Definition (lines 47-49, Weinstein-inspired but simplified): compare the CURRENT
consolidation to the PRIOR WEEKLY consolidation. Current base ABOVE the prior weekly base
= **"अप बेस"** (tradeable/preferred). Current base BELOW the prior weekly base = **"डाउन
बेस"** (avoid by default — "overhead supply"). The very first base after listing gets no
up/down label ("इसको काउंट जीरो ही करेंगे").
Down-base nuance (less-bad exceptions, lines 53-63, 87): a LARGE prior weekly base (e.g.
"6 महीने") with the current base far below it = heaviest overhead supply, avoid hardest
(Corona-crash example); a SMALL prior weekly base (e.g. "1-1.5 महीने") without a
huge-volume fall = lighter supply, tradeable if other factors align; down-bases still
close to the 52-week high are more tradeable than ones "40-50% गिर चुका है." Tactic: the
speaker personally trades down-bases **intraday only**, never holds them for swing (lines
65-67).
Relative Strength (lines 113-137) rides alongside this: matters MOST when the market
itself is falling (divergence vs. benchmark — NIFTY500 for large caps, NIFTY
MIDSMALL400 preferred personally for small/mid); in a rising market RS barely matters —
"कोई भी 20-25% ऑफ हाई स्कैनर" suffices.

## HVE / HVY (resolved — precise definition found)
Exact quote (line 411): **"एचवी क्यू ... मतलब हाईएस्ट वॉल्यूम इन अ क्वार्टर, एचवी वाय
मतलब हाईएस्ट वॉल्यूम इन ईयर, एचवी यानी हाईएस्ट वॉल्यूम एवर."** → HVQ = Highest Volume in a
Quarter; HVY = Highest Volume in a Year; HV (bare) = Highest Volume Ever. This is very
likely what our combination doc's "HVE/HVY" shorthand refers to (HVE ≈ the bare "HV
Ever" reading), though the doc's exact letter "HVE" is not itself spoken — flagged as
Likely, not Certain, on the HVE↔"HV Ever" mapping.
Where it should appear (line 411-413): inside the base OR inside the flag POLE itself —
signals a big player entered. Where it should NOT (same lines, plus IOB example
413-415): AFTER a stock has already rallied 40-60%+ — an HV print there is a possible
**topping** signal, not accumulation. Worked negative example: IOB's all-time-highest-
volume bar printed AT its all-time high, and the stock never regained that level after.
Used repeatedly as a scoring input in the Mazagon Dock deep-dive (below) — presence of an
HVQ near the base/pole earns points toward Volume-Activity/X-Factor; its ABSENCE through
a long consolidation is an explicit reason to stay out even when peers look similar (lines
767-773: "मुझे कोई एचवी क्य भी नहीं दिखा है ... जब तक स्ट्रंग [वॉल्यूम] नहीं आती").
**Garble/deferral note:** line 275 and 411 both pair "HV" with "AVWAP" ("एचवी एवीवा", "एक्स
फैक्टर एवीवा") and the speaker explicitly defers full AVWAP-anchoring mechanics to a later
video not in our corpus ("हम और डिस्कस करेंगे एक्स फक्टर में") — **how the AVWAP anchor
itself is drawn/placed is an OPEN QUESTION, not answered here.**

## X-Factor (sector, IPO, EP, RS, volume) and Market Health
X-factor needs "कुछ ना कुछ" out of: sectoral strength, IPO, EP/gap, high RS, strong-pocket
volume (line 337). Sector strength operationalized (lines 337-345): many stocks near
52wk-high within 15-20% band; multiple QUALIFYING setups from the same sector; multiple
BREAKOUTS from the same sector (stronger signal than setups alone); or one dominant
volume/HV signal even with nothing else. EP defined (line 383-407) as a strong
earnings/news reaction — gap, strong-reaction, or gradual "hidden EP" bottom formation —
loses its "extra point" once the stock is already 100%+ off that reaction (must then be
traded as a plain base on its own thrust/linearity merits).
Market health/MBI is called "सबसे इंपॉर्टेंट फैक्टर" (line 415-419) — mainly followed via
the 4.5R column plus MBI day-color (both already covered in the MBI digest); "quality of
setups" is judged as 7-8 of ~10-11 total factors passing; when quality setups appear
MULTIPLE and their breakouts get FOLLOW-THROUGH across the market, that is "peak market
condition" → **"अंधा साइज करना चाहिए"** (blind-size, market-wide version of the stock-level
rule above) (lines 419-429, 463-479).

## Deep-Dive Case Study (Mazagon Dock / "Masdoc")
A full IPO-to-multi-hundred-percent swing walk-through (lines 609-777) scoring each entry
point against: volume activity, thrust power, linearity, area-of-interest, pivot level,
EP/IPO/gap, sector, pattern, cleanliness, pivot-cutter — used as the worked template for
"quality of setup = N of ~10-11 factors passing." Key generalizable notes: (a) a stock can
show good thrust/linearity from its OWN history even while other factors (sector, pattern)
are unclear early on; (b) once genuinely large HV volume + thrust + linearity align, the
speaker states refusing the trade is a "sin" ("पाप") for an equity trader — a rare
absolute statement in an otherwise "no factor is absolute" video; (c) MDOC's own
character — long, flat-looking LEFT side of every base, then sudden RIGHT-side ignition —
is itself flagged as ticker-specific behavior to remember, not a general rule.

## Sizing / SL Management — What Is and Isn't Directly Stated
Directly stated: "blind size" high-thrust/clean/peak-market setups (lines 289, 467); for
intraday spurts, reward:risk is prioritized over win-rate — don't book fixed 2R/3R, let it
run (lines 495-497, 505-509). **NOT found verbatim in this transcript:** the "dirty bases
get faster SL, cleaner bases get more room" framing used in our own combination summary —
the closest actual statements are about ENTRY acceptance (avoid dirty bases outright), not
a differential-SL-distance rule. Flag this line item as **not directly quotable from Part
3** — likely paraphrased/inferred by the combination doc's author, or sourced from a
different stocksgeeks video outside this batch.

## ENGINEERING TRANSLATION

| Factor | Formula candidate (daily OHLCV + delivery%) | Marker |
|---|---|---|
| Thrust Power | Count of trailing-252d days with `\|%chg\| >= k * ADR20` (k~1.5-2), or 95th-pct of daily-gain distribution | **Likely** formula shape (Certain on the underlying "big-candle ability" concept; k and window are Assumption — no exact cutoff stated in this file) |
| Linearity | `% of days closing >= 20EMA` over the length of an active leg; or count of 20EMA-close-violations per leg | **Likely** (Certain that 20EMA-respect is the metric; Assumption on the tolerance/violation-count cutoff — transcript narrates tolerance qualitatively only) |
| Pivot Cutter | Trailing-N-month count of (tight-base → breakout → re-stop-within-K-days) cycles per ticker | **Likely** shape; **Assumption** on N, K, and the repeat-count that flips a name to "pivot cutter" (none given) |
| Cleanliness of Base | Composite: (a) count of lower-low violations inside base, (b) avg(up-day %)/avg(down-day %) ratio with a rightward-shrinking down-day rule, (c) upper-wick ratio, (d) right-side volume trend (should fall) | **Certain** on the 3 named sub-rules (lines 245-259); **Assumption** on weights/composite scoring |
| HVQ/HVY/HV | `vol[t] == max(vol[t-63:t+1])` (HVQ, ~1 quarter); `max(vol[t-252:t+1])` (HVY); `max(all history)` (HV); gate: positive only if inside base/pole AND prior rally-from-low < ~40% (else flag as topping risk) | **Certain** on the 3 window definitions (line 411 is an exact quote); **Assumption** on the ~40% rally-gate cutoff (transcript gives an illustrative "40-50-60%" range, not a hard number) |
| Area of Interest (Up/Down base) | Compare current price-band consolidation to the last WEEKLY swing base's price band; above = up-base, below = down-base | **Certain** on the relative definition; **Assumption** on exact "how far below counts as down" and "how large a prior base = heavy supply" (only qualitative examples given) |
| Pivot Level (cheat tiers) | `tier = (pivot_price - base_low) / (base_high - base_low)`; top third preferred, bottom third hard-avoid | **Certain** on the 3-region split and top/bottom ranking; **Assumption** that thirds are exactly equal (transcript's "half x3" phrasing is an ASR artifact, not a stated ratio) |
| Sizing by quality | Position-size multiplier scaled to a composite quality score (thrust + linearity + cleanliness + market 4.5R regime) | **Assumption** — no formula given in-source; the "faster SL on dirty bases" framing itself is not directly quotable here (see above) |

## OPEN QUESTIONS (not answered in this transcript)
1. How is the AVWAP anchor point chosen/drawn when paired with an HVQ/HVY bar? Explicitly
   deferred to a future "X-factor" video not in our corpus (line 275, 411).
2. No exact numeric threshold for "how many pivot-cuts = a pivot cutter," nor for "how
   many 20EMA violations still count as linear."
3. "Flag count" / "tilted flag" as named, countable concepts (referenced in our own
   combination summary's avoid-list, e.g. THERMAX/RUBICON) do **not** appear anywhere in
   this transcript — likely sourced from a separate scanning-session video outside this
   batch.
4. The "dirty base → faster SL, clean base → more room" sizing rule is not directly
   quotable here (see Sizing section) — needs a source citation or should be marked as an
   inference in downstream docs.
5. No numeric liquidity/value-traded gate is given in THIS video for swing "cleanliness"
   trades (a value-traded gate does appear, quantified, in the Umang intraday digest — not
   a substitute, just the closest cross-reference).

---
ORCHESTRATOR FIDELITY NOTE (2026-07-17): source transcripts are Hinglish in Devanagari script; quoted lines in these 4 SG digests are TRANSLATIONS/transliterations, not verbatim-greppable text. Spot-verified: HVQ concept present in source (Devanagari 'highest volume in quarter' @char66109, 190x 'volume'); snapshot.py warning-day 4-of-6-columns discrepancy VERIFIED against code (red_count over r10/r20/r50/r4p5 only). Verify any load-bearing threshold against the Devanagari source before coding it.
