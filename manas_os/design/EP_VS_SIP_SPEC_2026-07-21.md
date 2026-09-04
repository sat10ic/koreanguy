# EP vs SIP — nature + location (source: practitioner PDF, user-supplied 2026-07-21)

Source doctrine (verbatim points from "EP & SIP — A Thin Line Between Them"):
- EP = swing trade; SIP = intraday trade. The difference is STOCK NATURE +
  LOCATION + price action BEFORE the EP day.
- Stocks with clean swing nature are better for swing EP. Stocks with
  burst-and-fade nature have lower swing win rates and may be intraday only.
- Extended price -> intraday only. Fresh base breakout -> best location for a
  swing EP. Opening near resistance -> avoidable. Room above matters.
- "Price usually cannot break resistance without absorbing supply."
- Final checklist: historical continuation nature? room above? fresh base
  breakout? extended already? near resistance?

Why this matters here: the tool already DETECTS episodic pivots but never asks
whether a given stock's bursts historically HOLD. It therefore hands
burst-and-fade names to a SWING plan with a swing stop. That is a silent
category error the corpus explicitly warns about.

## Build: manas_os/scanner/ep_quality.py

### 1. burst_nature(bars) -> the novel metric (computable from daily_prices)
For one symbol, find every historical BURST DAY in its own history: a session
whose change >= BURST_PCT (start 8.0 — Assumption, slightly below the D2 10%
so the sample is not starved) OR gap >= 5% with day RVOL >= 2.
For each burst day, measure the forward path from that day's close:
 - fwd_5 = return over the next 5 sessions, fwd_10 over 10.
 - "held" = fwd_5 > 0 AND the stock did not close below the burst day's LOW
   within those 5 sessions (a fade that undercuts the burst bar is the
   signature the doctrine names).
Return {burst_days: n, held: k, hold_rate: k/n, median_fwd_5, median_fwd_10,
        nature: "swing" | "mixed" | "fade" | "unknown"}.
Nature thresholds (Assumption-flagged): hold_rate >= 0.6 and median_fwd_5 > 0
-> "swing"; hold_rate <= 0.35 or median_fwd_5 < -2% -> "fade"; else "mixed".
n < 4 burst days -> "unknown" (never guess a nature from one event).

### 2. location_read(bars, pivot/target inputs) -> the doctrine's four location tests
 - fresh_base_breakout: breakout_age <= 3 AND pre-burst tightness in the
   bottom quartile (reuse existing helpers, do not reinvent).
 - extended: close > 1.08 * EMA21 (the LOCKED extension number).
 - room_above: distance to the nearest overhead resistance (reuse
   risk/plan.structural_target's resistance scan READ-ONLY); room_pct =
   (resistance - close)/close*100; "no room" when room_pct < 4 (Assumption).
 - near_resistance: room_pct < 2 (Assumption) -> the doctrine's "avoidable".
Each returns the boolean AND the number behind it, for honest rendering.

### 3. classify(nature, location) -> {"verdict": "SWING_EP"|"INTRADAY_SIP"|
     "AVOID", "checklist": [...5 items with pass/fail + number...], "why": str}
 - AVOID when near_resistance, or nature == "fade" AND extended.
 - INTRADAY_SIP when extended, or no room above, or nature == "fade".
 - SWING_EP only when fresh_base_breakout AND room_above AND not extended AND
   nature in {"swing","mixed"}.
 - nature "unknown" can never produce SWING_EP on its own: it degrades to
   INTRADAY_SIP with the reason named ("no burst history to judge nature").

### 4. Persistence + wiring (later waves, NOT this lane)
Table ep_quality_daily(scan_date, symbol, verdict, nature, hold_rate,
median_fwd_5, room_pct, extended, fresh_base, checklist_json). The scan's EP/
D2 candidates carry the verdict; an INTRADAY_SIP name must not present a
SWING plan — it either renders as an intraday-only card or is refused with
this named reason. Conviction rank reads the verdict as evidence.

## Done-tests
- A synthetic fade-natured symbol (bursts that all undercut within 5 days)
  classifies "fade" and can never reach SWING_EP.
- A clean-continuation symbol at a fresh breakout with room classifies
  SWING_EP; the same symbol extended classifies INTRADAY_SIP.
- Under 4 burst days -> "unknown" -> never SWING_EP.
- Every checklist item renders its number, never a bare boolean.
