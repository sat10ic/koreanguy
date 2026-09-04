# Stocksgeeks (via Traderlion/Umang) — Intraday Method — Digest (2026-07-17)

Source: `C:\Users\satta\Downloads\koreanguy\trading-brain\raw\Traderlion\uman stocksgeeks
intraday.txt` — a **single physical line**, 240,068 bytes as stored on disk. Handling
note: the file is valid UTF-8 (verified by direct byte-decode); an initial attempt to
split it via PowerShell `Get-Content -Raw` (no explicit encoding) produced mojibake
(double-encoded Devanagari) — that attempt was discarded and the file was re-split using
`[System.IO.File]::ReadAllBytes` + explicit `UTF8Encoding` (94,996 characters once
correctly decoded), into 8 sequential chunks read in full. Format: an interview
transcript between the speaker ("उमंग") and an interviewer ("अंकुर भाई"), Hinglish/Hindi
ASR, garbled in places — noted honestly below.

## Core taxonomy: Swing / Recursion / Spurt
The speaker files every trade into exactly one of three buckets (chunk 7): **Swing**
(normal daily-timeframe holds), **Recursion** ("रिकर्शन" — a daily/swing-quality setup
executed across mixed timeframes intraday for a faster/cheaper entry — explicitly NOT
taught in this video, deferred), and **Spurt** ("स्पर्ट" — pure momentum-burst intraday,
the subject of this whole interview). Recursion is called "much easier to trade than
spurt" (chunk 7) — spurt is explicitly the harder skill.

## Stock exclusion filters (before any setup is considered)
- No F&O stocks with low ADR — worked example ITI (ADR very high, repeatedly
  10-14% single-day moves) vs. a contrasting low-thrust name whose "5% candle" is really
  only 2-3% once the gap-up portion is subtracted (chunk 1).
- **ADR ≥ 3%** (chunk 1, direct answer to interviewer's clarifying question: "दैट्स अबव
  3%... 3% एडीआर").
- **Value traded (1-min chart) ≥ 0.5 Cr** ("आई नीड एटलीस्ट 0.5 सीआर"), with an explicit
  **opening exception** — liquidity often appears fast right at 9:15 so the floor is
  relaxed in the first few minutes (chunk 1).
- Avoid mega-caps even when technically F&O-eligible (Reliance, SBI named explicitly) —
  "participation is too high," bases get "बहुत स्ट्रेच्ड," big candles don't form (chunk
  1). Large-cap ADR numbers can look fine (e.g. "4.55") while candles still don't move —
  size/weightage suppresses realized thrust regardless of the raw ADR reading.

## Three time-of-day zones (explicit, drawn as a 3-part day)
1. **Opening (~9:15-10:15/10:30)**: most liquidity, most volatility, most new moves start
   here — requires SPEED (rescanning "एवरी 5 मिनट्स आफ्टर 9:20").
2. **Middle market (~10:30-13:00/13:30)**: LEAST liquid zone, hardest to trade,
   especially in a choppy/bear tape — gated by the same 4.5R number from the MBI system
   (see below); speaker personally trades this zone least of the three ("मैं सबसे कम इस
   एरिया में ट्रेड करता हूं").
3. **End of day (~13:30-15:30)**: volatility and liquidity both return; small, fresh
   bases form and anticipation entries work again.

## Setup shapes — Opening
Three canonical VWAP-relative shapes, all requiring a prior up-move ("अपमूव") first:
(a) price dips to/below VWAP then reclaims immediately; (b) price tests VWAP once or
twice then breaks; (c) a small base forms directly on 10/20 EMA without ever touching
VWAP, breaking via a 2T/3T VCP. All three must sit above BOTH the prior move and VWAP —
an **"up-base"** requirement mirrored from the daily-timeframe Area-of-Interest concept.

## Setup shapes — Middle market (ranked)
A prior "leg" (up-move) is a hard prerequisite — "अगर लेग नहीं आया तो मैं छोड़ देता हूं" —
no leg, no trade, regardless of how tight the base looks. Three base types, ranked:
1. **Clean up-base fully above VWAP** — his actual tradeable model; anticipation entries
   allowed.
2. **Base that dips briefly below VWAP then reclaims** — lower probability; requires
   volume CONFIRMATION before entry (not anticipation); traded "as little as possible."
3. **Base that stays below VWAP** — explicitly **"not my setup"**, almost never traded:
   "मेरे कभी भी आप विनर्स देखोगे ... मैं यहां पे एंट्री कभी नहीं करता हूं।"
Win-rate collapses hard after 10 AM regardless of shape if the market-wide 4.5R number is
weak (chunk 3): "इधर विन रेट बहुत हाई रहता है ... इधर विन रेट कम हो जाता है 10:00 बजे के
बाद, अनलेस जो 4.5 आवर है वो 800-900 चला गया."

## Market-condition filter (live, intraday-recomputed)
Uses the **same 4.5R ratio** from the MBI system (see the MBI digest for the full
definition) as an intraday-recomputed live gate, distinct from its EOD/daily use:
"अगर मुझे दिखता है 4.5 आर नंबर इतना अच्छा नहीं है तो मैं 10:20 को ही ब्रेक करेगा तो भी
निकल जाऊंगा" (chunk 2). Worked live-session example: "आज का 4.5 आर नंबर 20 का है। 20 इज़
पैथेटिक। मैं 400 बोल रहा हूं, 20 आ रहा है" (chunk 8) — on such a day he explicitly avoids
trading or shrinks size sharply, sometimes closing the screen entirely and doing
something else. Sector strength is used as a secondary confirming signal on top of the
4.5R gate (Defence-sector day and Fertilizer-sector day both named as worked examples,
chunks 5, 6, 8).

## Strong starts / opening range
- Explicit ORB (opening-range breakout) reference: "9:32 को सारे फर्टिलाइजर्स में ओआरबी
  आया था" (chunk 6).
- First-15-minutes volatility warning, specifically for a suspected weak/choppy/falling
  market open: "आप वेट फॉर फर्स्ट 15 मिनट्स ... पहले 15 मिनट में सबसे ज्यादा वोलेटिलिटी
  रहती है, आपके एसएल कटने के चांसेस सबसे ज्यादा" (chunk 4). This is a personal, regime-
  conditional habit, not a universal every-day rule.
- Early tell for a genuinely bad market day (chunk 4): if MULTIPLE stocks fail to respect
  VWAP within the first 5-10 minutes ("वीवप की ना इज्जत नहीं करता"), that alone predicts
  the whole session and he sits it out.

## Entry / exit / sizing mechanics
- **Anticipation vs. confirmation, by zone**: anticipation entries preferred at
  open/end-of-day (his default "एंटीिसिपेशन ट्रेडर" style); volume CONFIRMATION required
  for weaker middle-market shapes (see ranked list above).
- Prefer LIMIT orders over MARKET orders — market orders in a fast/illiquid name can
  create your own slippage ("आ जाओ बस फिर पता चलता है कि भाई पूरा स्टॉक ऊपर हमारा ऑर्डर
  ही ले गया," chunk 4). Scale in via 2-3 tranches once conviction builds.
- Trail via **20 EMA** (faster/tighter exit, more booked gain) or **50 EMA** (looser,
  better if the stock is a "UC [upper-circuit] candidate" that may re-base and
  re-breakout) or **VWAP** (loosest, best when a genuine 1-day-circuit is likely). His own
  universal default: **"50 ईएमए पे हमेशा मैं आइडियल सेल मानता हूं"** (chunk 6).
- Parabolic-move handling (chunk 5): on a post-entry parabolic run, sell at the 20EMA
  violation by default; hold to 50EMA or carry to swing only if conviction is genuinely
  high. Near the 20% intraday circuit limit, book around 18-19% — "19% पे जाके रिवर्स हो
  जाएगा ... 1% के चक्कर में लोग पूरा गेन वाइप आउट हो जाते हैं" (chunk 8).
- **Sizing**: liquid names get his normal default ~25-30% of capital ("मिनिमम 30% साइज
  रखूंगा ... लिक्विडिटी के हिसाब से मेरा साइज रहता है," chunk 5); per-trade risk framed
  at the PORTFOLIO level, 1-1.5% max ("एक से 1.5% रखता हूं," chunk 6); soft cap of
  **3-4 concurrent open positions** ("तीन से चार पोजीशंस ओपन मत करो," chunk 6); personal
  habit — after 2 (occasionally 3) stop-losses in a day, stop trading for the day
  ("अगर दो स्टॉप लॉस हो गए तो मैं तीसरा ट्रेड नहीं करूंगा," chunk 6).
- **20% max intraday leverage/exposure** rule via MIS stated early (chunk 1): "इंट्राडे
  में 20% की मैक्सिमम लेवट है आपकी" — read in context as position/product-level
  leverage cap, not a risk-per-trade number.

## Daily routine (chunk 8, verbatim schedule)
Wake ~7:30-8:00; watchlist pre-built the previous evening; active/focused screen time
9:15-10:30 for intraday; largely off-screen 10:30-14:30 (alerts only, does other things,
sometimes literally sleeps through market hours if positions are light); resumes scanning
~14:30-15:00 for next-day swing setups; runs an EOD scan over a ~200-stock fixed list
(loaded with sub-200EMA "bottom bouncers") plus a running breakout-tracking list used to
gauge the market's "average move size" and calibrate trailing tightness for the next day
(if average moves are running ~10%, trail tight; if ~30%+, trail looser).

## What's adoptable for an EP-PREP morning-confirm loop
Most directly codable, novel pieces not already covered by the daily-timeframe digests:
1. The **VWAP-relative 3-shape classification** (above/dip-then-reclaim/below) as a
   coarse intraday setup-quality tag.
2. The **hard "leg-before-base" gate** — refuse any base with no prior up-move, regardless
   of tightness.
3. The **zone-conditional anticipation-vs-confirmation split** (open/EOD = anticipation
   OK; midday = confirmation required) — this is the single most novel piece NOT yet
   represented in the live FSM (see DELTA below).
4. The **live-recomputed 4.5R gate** as an intraday (not just EOD) regime signal.

## DELTA vs `manas_os/alerts/live_fsm.py`
Read: `live_fsm.py:1-100` (module docstring, states, `_zone_bounds`, `arm_from_armed_list`).
- FSM states: `ARMED -> ALERTED -> {CONFIRM_PENDING, CONFIRMED_15M} -> CONFIRMED`
  (terminal), plus `EXPIRED`/`EXPIRED_MOVED` (terminal). `ALERTED` gates on: price clears
  trigger + first-15m holds OR-low/VWAP + gap-fill ≤33% + projected RVOL ≥2 (module
  docstring, lines 6-8).
- **Strong match**: the OR-low/VWAP "holds in the first 15 minutes" gate already encodes
  two of Umang's core rules almost exactly — (a) his explicit "wait out the volatile first
  15 minutes" habit, and (b) his "VWAP must be respected" tell for a healthy open. The
  RVOL≥2 gate is a reasonable analog to his volume-confirmation requirement for weaker
  setups.
- **GAP — no zone-conditional gating**: Umang applies anticipation-vs-confirmation
  DIFFERENTLY by time-of-day (anticipation OK at open/EOD, confirmation required midday).
  `live_fsm.py`'s `ALERTED` gate (RVOL≥2 + OR/VWAP holds) appears to apply uniformly
  regardless of time-of-day — there is no time-zone-conditional branch visible in what was
  read. This is the clearest, most actionable gap for an EP-PREP morning-confirm loop.
- **GAP — no live-recomputed intraday breadth feed**: Umang's model assumes a
  CONTINUOUSLY-refreshing 4.5R-style number checked repeatedly through the session
  ("आज का 4.5 आर नंबर..."). Nothing in `live_fsm.py`, `regime/snapshot.py`, or
  `regime/four_phase.py` (per the MBI digest's own DELTA section) recomputes breadth
  intraday — the regime snapshot is an EOD/pre-market construct. This is an architecture
  gap, not a parameter gap: matching Umang's method would need a live breadth feed, not
  just a threshold change.
- **Not checked / possible existing match, stated honestly rather than claimed as a
  gap**: `governor.py` and `risk/plan.py` were not read deeply enough in this pass to
  confirm or deny whether a "3-4 max concurrent positions" or "N stop-losses -> halt for
  the day" rule already exists elsewhere in the risk-sizing stack; `governor.py` does
  expose `max_open_positions` and `MAX_NEW_POSITIONS_PER_DAY` per market_mode, which may
  already partially cover this — flagged as unverified rather than asserted as absent.

## OPEN QUESTIONS (not answered in this transcript)
1. No exact formula for "how much RVOL/volume counts as confirmation" in the middle-market
   zone — only qualitative "wait for volume confirmation" language.
2. No precise numeric definition of "average move size" used to calibrate trailing
   tightness — only the illustrative ~10% (tight trail) vs. ~30%+ (loose trail) anchors.
3. The "20% max intraday leverage" line is stated once, briefly, without further
   elaboration on how it interacts with the separate 1-1.5% portfolio risk cap — the
   relationship between the two is not spelled out.
