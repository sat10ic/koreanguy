# CONVICTION RANK — the top-picks product (wave E1)

Trigger: 2026-07-21. Friday's scan ranked 154 names; the top 20 were ALL
"Pullback-to-EMA" while the practitioner bought RAIN/SKIPPER/EIEL/GENUSPOWER/
STALLION (episodic bursts, fresh breakouts, theme leaders) — refused or buried.
Diagnosis: the ordinal rank has NO setup-conviction axis. It sorts by
delivery_z + sector-adjusted momentum + confluence COUNT, so a quiet
continuation outranks a fresh initiation. That is backwards from the corpus
(Arora/TradeTM: initiation and catalyst first; continuation is the add, not
the alpha).

## The product
A hard TOP-15 CONVICTION LIST is the scan's headline output. Everything else
collapses under "also cleared the gate — lower conviction (N)". No user should
scroll 154 rows to find the trade.

## Conviction score (transparent, every component rendered on the card)
Composite of FIVE named axes. No black box: the card shows each axis's value
and the phrase that earned it. All weights Assumption-flagged; calibration
against practitioner picks + the scorecard is the promotion gate.

1. SETUP TIER (dominant axis)
   - A / initiation (weight 3): ep, d2_episodic, strong_start_ready,
     ipo_base, fresh base breakout (breakout_age <= 3 AND close > pivot).
   - B / velocity continuation (weight 2): pocket_pivot, persistent_momentum,
     near_pivot when leg is fresh (extension_21 <= 8%).
   - C / mean-reversion continuation (weight 1): pullback (10/20/50 EMA),
     long_tail, generic watchlist_timing.
   Cite: initiation > continuation is corpus doctrine, not invention.

2. PARTICIPATION SURGE
   - day RVOL vs 20d (have: eod_detectors day_rvol)
   - U/D RATIO (NEW): sum(up-day volume) / sum(down-day volume) over 21
     sessions. The shared practitioner charts (SAREGAMA 2.49, EXICOM 1.48)
     display it as a first-class accumulation read; we do not compute it.
     Assumption: >= 1.5 strong, 1.0-1.5 neutral, < 1.0 distribution.

3. LOCATION
   - nearness_52w (have) — leaders trade near highs, not off lows.
   - pct_up_from_65d_low with the LATE_IN_MOVE penalty (>80% = arriving late,
     the trade-autopsy's worst tag).

4. CONFLUENCE ACROSS INDEPENDENT SCREENS ("featured in")
   - NEW: compose screener_hits (ChartsMaze families) + our own detector tags
     into a NAMED, recency-stamped list per symbol ("Price Uptrend · ATR
     Expansion · 52-week High · 3 screens, newest 1d"). Count DISTINCT
     FAMILIES, never raw hit count (a symbol in 6 momentum screens is one
     signal, not six). Practitioner tools (tradl/stockvision screenshots
     2026-07-21) all surface exactly this.

5. THEME MEMBERSHIP
   - from scanner/theme_pulse.py: name is a member of a firing industry theme
     (>=3 names moving together). The water-pump cluster (WABAG/EIEL/DENTA)
     and "Chemicals Group" (STALLION) are the practitioner's own framing.

## Chart-quality grade (gate-adjacent, not a rank axis)
30-SMMA CROSS COUNT (Koroush AK method, user-supplied 2026-07-21): count
price crosses of the 30-period smoothed MA since the last structure break.
0-3 crosses + trending MA = momentum-ideal; 7+ crosses or sideways MA =
momentum-poor (that chart is reversion turf, not our game). Render as a
CHART-FIT chip; a momentum-family candidate on a momentum-poor chart carries
a named objection. Assumption: 30 periods on daily; calibrate before it gates.

## Rails (unchanged)
- The gate still decides pass/refuse. Conviction only ORDERS survivors.
- risk/plan.py remains the single writer of stop/size/R:R.
- Every axis value must trace to a computed field; missing -> em dash, never
  a fabricated component.
- Promotion gate before conviction influences anything but display order.

## Done-tests
- Friday 2026-07-17 re-scored: the practitioner's names (once the measured-
  move fix lets them survive) appear in the TOP 15; the 20 pullbacks do not
  monopolise it.
- Card renders all five axes with their numbers.
- U/D ratio + featured-in + chart-fit have unit tests on hand-built bars.
- Scorecard gains a conviction-decile cohort so the ranking itself gets graded
  against forward returns — the ranking must earn trust, not assert it.
