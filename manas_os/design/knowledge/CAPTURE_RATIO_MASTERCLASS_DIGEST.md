# DIGEST — "Stop Giving Back Profits" masterclass (capture ratios, velocity vs magnitude)

Source: user-shared YT transcript (live trade-review, TradeTM/stocksgeeks ecosystem — mentor +
Harendra/Preetu/Nitin/Deepanshu/Shiv). Topic: WHY traders give back healthy gains, and the
metric/discipline that fixes it. Management-side — our thinnest layer (exit engine exists, but
no capture accounting). Fidelity: Hinglish→EN; quotes marked; quantified vs vague flagged.

## THE CORE METRIC — Capture Ratio (buildable, high value)
- Def (his words): of the TOTAL move available to you, how much did you realize.
  `capture = realized_R / total_move_R`. Total move measured **relative to objective**:
  - magnitude trade → total = entry→peak→your exit; loss-of-capture counted **from the top**,
    not the bottom ("your actual loss of capture should be from the top, not from the bottom").
  - velocity trade → total on the fast leg you were playing.
- **Benchmark (QUANTIFIED): prop books consider 70%+ "very good."** He also says on a ~40% move,
  capturing 28-30% is "good enough" (i.e. ~70%).
- Track capture ratio **separately by objective** (velocity vs magnitude) — never pooled.
- Worked example: NETWORK trade, entry 2162 → ran ~118%, 35% size = ~40% portfolio impact
  possible; he realized only ~14-15% → captured ~40% of available (sold half + didn't rebuy +
  sold balance into weakness). The two leaks: partial-and-never-rebought, and sold-into-weakness.
- THE CRIME (quote): "You can't go to a five-hour [5R] and cut it to zero and say the stock
  squatted — if you're playing a velocity trade, that is a crime." Giving back more than you keep.

## VELOCITY vs MAGNITUDE (per-trade objective, decided at ENTRY)
- The distinction is NOT capital risk — it's **"giving room to PROFIT, not to capital"** (quote).
  Once SL is at cost, risk shifts capital→profit; velocity vs magnitude = how much *profit* room.
- Velocity: demand must come FAST (his frame: "2 minutes" vs magnitude "2 days"); trail hard
  (5-min 20MA / prior swing / 10-min-stagnation rule); capture fast, rotate portfolio, edge = FREQUENCY.
- Magnitude: give wide room (10/20 EMA, base lows, 3R-then-let-run); catalyst/event-based; edge = MAGNITUDE.
- Failure mode (named repeatedly): taking a VELOCITY trade then, once in profit, mentally
  converting it to MAGNITUDE and pinning hopes → round-trips to zero. "Decide the objective FIRST."
- The market doesn't know which you intended — so measure MAE/capture and stop guessing.

## DISCIPLINES (quantified where he stated)
- Breakeven-fast (QUOTE): "your first duty is to place as many trades as you can and bring the
  stop loss to breakeven as quickly as possible." Early entry's value = more room to reach BE, not profit itself.
- MAE exercise: compute Maximum Adverse Excursion across your trades → right-size stops to reality.
- Two-leg SL: one slow initial SL (barely moved) + one aggressive MA-trail (20MA); cut one, run the other.
- Anticipation vs confirmation (VAGUE numerically): "you need enough confirmation to anticipate —
  never 100% either side"; more confirmation = you're filling someone else's exit ("retail vs
  wholesale entry"). Zone rule matches Umang digest (open = anticipate, later = confirm).
- Choppy-market truth (QUOTE): markets are poor "~70% of the time in a year" → expect stop-outs,
  protect downside first, play for regularity not home-runs; small move × big size > chasing 100%.
- Scaling: risk asymmetry lives in PROFIT not capital — sizing up risks unrealized profit for
  higher realized, capital stays constant %. Trading maturity = "big size on an AVERAGE move."

## ENGINEERING TRANSLATION (feeds Position Coach + Journal — plan T2.4/T3.9)
1. **Capture Ratio metric** [BUILD — highest value]: on each closed journal trade compute
   `realized_R / MFE_R` (we already log MFE/MAE in scanner/outcomes). Store per trade + roll up
   per objective × regime in setup_expectancy. Card chip: "captured 42% (target 70%)". This is a
   NEW moat metric — the journal already exists, this makes it teach capture, not just win-rate.
2. **Objective tag** [BUILD]: velocity | magnitude, set at TAKEN time (default from setup family:
   Strong-Start/D2/EP-velocity → velocity; base/pullback/catalyst-magnitude → magnitude). Drives
   which trail the coach shows (fast MA vs wide structure) — reuses the exit engine's modes.
3. **Capture-leak guard** [BUILD, extends late-exit guard T3.9]: when a velocity position gives
   back >X% of peak-R unrealized, red coach flag "you're round-tripping a 5R — velocity crime."
4. **MAE mirror** [display]: JOURNAL panel showing per-setup MAE distribution → "your stops are
   2x wider than your trades' actual adverse move" style coaching. Data exists.
5. Regularity framing in copy: coach speaks in "keep the portfolio moving" language for velocity.

## OPEN QUESTIONS
- Exact velocity-vs-magnitude auto-classifier boundary (he keeps it discretionary "decide first").
- The X% capture-leak threshold for the guard (he gives 70% capture target but no give-back trigger number).
- Capture measured intraday (his examples are 1-min/velocity) vs our EOD data — our capture is
  EOD-bar-resolution; note as approximation until intraday backfill.
