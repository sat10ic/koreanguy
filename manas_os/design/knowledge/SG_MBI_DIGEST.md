# Stocksgeeks — Market Breadth Indicator (MBI) — Digest (2026-07-17)

Source: `C:\Users\satta\Downloads\book\stocksgeeks\MBI_transcript.md` (485 lines;
Hinglish/Hindi, ASR-transcribed, garbled in places). Line numbers are the transcript's
own. File read in full (confirmed via its own sign-off at line 485).

## Column definitions (raw breadth table)
- **52-week-high / 52-week-low columns** (lines 27-29): count of stocks making a new
  52wk high / low that day. This column turns RED whenever new-lows > new-highs — "काइंड
  ऑफ लाइक अ बेरिश सिग्नल."
- **4.5%+ / 4.5%- columns** (lines 29-33): count/percent of stocks up or down ≥4.5% that
  day — a "burst" gauge in both directions, distinct from a plain advance/decline ratio
  because it captures MAGNITUDE, not just direction.
- **10dma / 20dma / 50dma / 200dma "above" columns** (lines 33-39): count of stocks above
  each moving average.
- **Oversold column-coloring** (raw %, separate from the ratio-day-color system below;
  lines 35-39): 10+ column → GREEN when <15%, ORANGE when <10%; 20+ column → GREEN when
  <20%, ORANGE when <15%; 50+ and 200+ columns → GREEN when <25%, ORANGE when <20%. Used
  ONLY to play oversold bounces — occurs "साल में ज्यादा से ज्यादा 10" times a year, fewer
  (~3-4) in a genuine bull run (lines 39-41).

## Ratio / day-color system (the actionable dial)
Distinct from the raw oversold coloring above — this is what decides GREEN/RED/WHITE
"day color" for trading (lines 43-67):
- **20-day ratio** = `(20+ column) / (20- column) * 100`. GREEN when the number is above
  ~75 ("मैं प्रॉफिट करता हूं"), RED below 50 ("मैं लॉस करता हूं"), WHITE in between
  (lines 45-47).
- **50-day ratio** = `(50+ column) / (50- column) * 100`. GREEN ≥85 ("85 के ऊपर ये ग्रीन
  हो जाएगा"), RED <60 ("60 के नीचे जाएगा रेड हो जाएगा"), WHITE in between (line 51).
- **4.5R ratio** = `(4.5%+ column) / (4.5%- column) * 100`. This is called **"दिस रेशो इज
  द मोस्ट इंपोर्टेंट थिंग इन माय ओपिनियन"** (line 55). Bands: RED <50, WHITE 50-200,
  GREEN 200-400, ORANGE >400 (line 59) — "हर चार स्टॉक्स जो 4.5% ऊपर उसके सामने सिर्फ एक
  स्टॉक 4.5% नीचे" at the ORANGE threshold.
- **Composite day color** (lines 61-67): 6 columns (10/20/50/200-day ratios + 52wk-hi/lo +
  4.5R) each score -1 (red) / 0 (white) / +1 (green-or-orange); sum ≥ **+3** → day is
  GREEN; sum ≤ **-3** → RED; otherwise WHITE and **the previous color-day's trend simply
  carries forward** — "जो प्रीवियस कलर डे है ... उसी का ट्रेंड कंटिन्यू रह रहा है." A
  BLACK highlight marks a color FLIP (cosmetic only, line 69-71).
- **Warning day** (lines 73-79): **3 or more of the 6 columns are RED**, regardless of
  whether the overall day itself is red — "छ में से तीन या उससे ज्यादा कॉलम रेड हो गए ...
  सीधा-सीधा वार्निंग डे होगा." Re-entry rule after a warning day: wait until EITHER (a)
  price closes above the warning-day's high, OR (b) the 4.5R number prints >400 on any
  day BEFORE the color actually turns red. If neither condition fires before red hits,
  you must wait for the next full green flip.

## EM dial / EM>15 / EM>12 gate — searched for, NOT found in this corpus
**Unverified / likely-inference, flagged honestly:** the literal indicator name "EM" and
an ">15" / ">12" gate (as cited in our own `STOCKSGEEKS_COMBINATION_2026-07-17.md`
summary — "99% I trade only when EM > 15") does **not appear verbatim** anywhere in this
MBI transcript, nor in the IPO, Trading-Systems-Part-3, or Umang-intraday transcripts read
alongside it for this digest wave. What IS present, heavily quantified, and functionally
similar is the **4.5R ratio** above (with its 50/200/400 bands) plus the day-color/
warning-day system — the same speaker, across multiple videos in this corpus, repeatedly
uses the 4.5R number as his single most important "should I be aggressive today" dial
(also seen driving intraday deployment speed in the Umang-intraday digest). **Likely** (not
Certain): "EM" is this same practitioner's colloquial/private name for the 4.5R dial, or a
close variant of it, spoken in a video outside this 4-file batch. Do not treat this as a
confirmed identity — an explicit "EM" source quote should be tracked down before any
downstream doc states EM = 4.5R as fact.
**Citation correction (caught on re-check, not a fabrication but an initial mis-attribution
to fix before this digest gets used downstream):** the literal string "ईएम" (EM) DOES
appear once in this 4-file batch, but it is spoken in the *Q&A tail of the IPO transcript*
(`IPO_trading_transcript.md:473-475`), not in this MBI transcript: **"ईएम वाला जो कॉलम है
वो मैं बताना नहीं चाह रहा हूं थोड़ा प्राइवेट इंडिकेटर है ... अ गुड मैजिशियन नॉट टेल ऑल
जिज ट्रिक्स."** He is answering a question about "the EM indicator" as a column he
deliberately keeps private. This raises confidence that EM is a real, named, but
intentionally-undisclosed column in his sheet — separate from the six scored above, and
almost certainly the same object referenced by our combination doc's "EM>15" quote — but
its formula is **not disclosed in either the IPO or the MBI transcript**; treat as OPEN
QUESTION, not solvable from source. (Flagging the mis-attribution explicitly rather than
silently correcting it, per this project's source-fidelity discipline.)

## Position-taking rules tied to MBI (lines 89-133)
- Standard ramp: on the EOD the breadth turns GREEN, build ~10% size that evening; if
  early follow-through works, add up to ~80% of capital within 1-2 days ("इनिशियल फेज में
  बहुत अच्छे-अच्छे मूव्स आ जाते हैं").
- Combine MBI-green with price-action (Wyckoff-style "wallace/wallis feedback") for best
  results — MBI alone is faster/less-lagging than pure PA feedback ("मेरा एमबीई पहले
  सिग्नल देता है ... मेरा वाइस हमेशा बाद में परफॉर्म करता है").
- Anticipation entries at the exact pivot are explicitly allowed ONLY when MBI is green —
  "जभी भी एबी रेड है आप एंटीसिपेशन एंट्रीज नहीं ले सकते" — when MBI is red, the same pivot
  usually gets missed entirely (dips just short) (lines 111-117).
- Portfolio-level rule (lines 119-121): trade only while a hard **3% max drawdown/risk**
  cap holds; stop entirely once hit ("जैसे ही 3% ड्रॉडाउन हो जाता है मैं ट्रेडिंग बंद कर
  देता हूं"). Three conditions gate size-up together: MBI green + high 4.5R + working
  price-action feedback (line 121).

## Reversal / oversold-bounce rules (bear-market context, lines 175-201)
- Each successive oversold bounce needs to be MORE oversold than the last one to be
  playable — "अगली बार जो ओवरसोल्ड होगा वो प्रीवियस ओवरसोल्ड जोन से ज्यादा ओवरसोल्ड होना
  चाहिए." Max ~2-3 bounces playable before diminishing returns ("तीसरे बाउंस के बाद
  दिक्कत होने लगती है").
- Requires a **"पैनिक डे"**: a red candle >~7% the day before the bounce ("% के ऊपर की
  रेड कैंडल इज अ वेरी गुड कैंडल").
- Prefer the **3rd day** of selling, not day 1 or 2 — bulls need to exhaust first.
- Final condition: an intraday undercut of the prior low before the bounce (shakes out
  late buyers) — "अंडरकट ऑफ प्रीवियस लो." All four conditions rarely align together;
  3-of-4 is treated as tradeable.

## DELTA vs `manas_os/regime/` (breadth_analytics.py, xp.py, snapshot.py, governor.py)
Read: `regime/snapshot.py:1-280`, `regime/xp.py:1-80`, `regime/governor.py`,
`regime/breadth_analytics.py:1-80`.
- **Strong, precise MATCH**: `snapshot.py`'s `compute_mbi()` implements exactly the
  ratio-band system above — `RATIO_GREEN_MIN=75.0`, `RATIO_WHITE_MIN=50.0` (the 20-day
  ratio bands, line 22-23) match the transcript's 75/50 numbers exactly; `R50_GREEN_MIN=
  85.0`, `R50_WHITE_MIN=60.0` (line 24-25) match the transcript's 85/60 exactly;
  `R4_RED_MAX=50.0`, `R4_GREEN_MIN=200.0`, `R4_ORANGE_MIN=400.0` (line 26-28) match the
  4.5R bands (RED<50, GREEN 200-400, ORANGE>400) exactly. This is a confirmed, precise
  fidelity win — worth stating plainly rather than as a gap.
- **GAP — warning-day math is quietly stricter than the source**: the transcript's warning
  day is "3 or more of **6** columns red." `compute_mbi()` only scores **4** bands (r10,
  r20, r50, r4p5 — no 200dma ratio, no 52wk-hi/lo column), then sets
  `warning_day = red_count >= 3` (`snapshot.py:159`). With only 4 total bands, 3-red is a
  much stricter bar than the source's 3-of-6 — this silently changes how often warning
  days fire relative to the practitioner's own system. Concrete, actionable gap.
- **GAP — no day-color carry-forward**: the transcript's WHITE-day rule explicitly carries
  forward yesterday's GREEN/RED trend when no new trigger fires (line 65-67).
  `compute_mbi()` is a pure per-row function with no memory of the prior day — every WHITE
  day displays as WHITE, never as "still trending green/red from before."
- **GAP — no re-entry-after-warning-day state machine**: the source's explicit
  "wait for warning-day-high-cross OR 4.5R>400" rule is not implemented anywhere seen in
  `governor.py` or `snapshot.py` (which read today's `market_mode` fresh, with no
  warning-day-specific carry state).
- **MISSING feature (not a mismatch, an absent feature)**: the raw oversold column-coloring
  system (10/20/50/200dma% at 15/10, 20/15, 25/20 thresholds) used for bottom-fishing is
  not implemented anywhere in `regime/` — this is a DIFFERENT mechanism from the
  already-implemented ratio bands, not a duplicate of it.
- **EM stub confirms the combination-doc's gap**: `snapshot.py` emits
  `"em_value": None, "em_source": "proxy_not_yet_computed"` (lines 479-481, 633-635,
  786) — i.e., the codebase already anticipated an EM dial and explicitly parked it as
  unimplemented. Given the corpus evidence above (EM is real but privately undisclosed by
  the speaker), the most defensible interim proxy is the already-implemented **r4p5** (the
  4.5R ratio) — NOT a new invented number — pending any future confirmed EM quote.
- **Modeling caution**: `regime/xp.py`'s XP dial (a log-space recursion over
  `z_state`/MA-participation/decliners — see its own docstring, lines 1-19) is a
  **manas_os-original construction**, not sourced from any stocksgeeks transcript in this
  batch, under this name or formula. The combination doc's suggestion to "calibrate an XP
  threshold band equivalent to his EM 12/15" is comparing two structurally different
  formulas (XP's multi-term log recursion vs. a simple up/down count ratio) — worth
  flagging as a modeling caution before doing that calibration, not a drop-in mapping.

## OPEN QUESTIONS (not answered in this transcript)
1. The EM column's actual formula is explicitly undisclosed by the speaker — cannot be
   reverse-engineered from this source; needs either a different stocksgeeks video or
   independent statistical inference from his stated wins/losses.
2. No exact universe size or exchange scope is given for "total stock universe" — the
   1000-stock example (line 25-27) is illustrative, not necessarily NIFTY500/MIDSMALL400
   (that specific benchmark choice appears in the Trading-Systems-Part-3 digest instead).
3. No numeric SL/target rules are given in this video specifically for MBI-gated entries —
   sizing/drawdown rules (3% cap) are the only quantified risk control here.
