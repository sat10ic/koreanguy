# COACH_LINES — deterministic coach sentence bank

Ready-made psychology/discipline sentences from `INDIA_PLAYBOOK.md` §9 (Psychology → Coach-Line
Bank). Each line is `[JUDGMENT]` (not a gate) — selection is a deterministic key match on
position state (phase/verdict/R), never an LLM call. `manas_os/agents/coach.py` looks up
situation-keys against the open position's deterministic read and appends 1-2 matched lines
verbatim to the coach message.

Format: `situation-key` -> line text + cite. One or more lines per key; coach.py picks in listed
order, capped at 2 total lines per position.

## exit_now
Position hit a deterministic exit trigger (verdict == EXIT).

- "Two kinds of letting go — of profit and of capital. The regret of an early exit on a later
  home-run is the necessary cost of ever holding a real winner; a fizzler and a runner look
  identical at day zero." [TTM-E8, TTM-E9]
- "Stop-loss execution is mechanical and non-negotiable; profit-taking is discretionary. Exit at
  market now, no second-guessing — even on a gap-down below the stop." [TTM-D13, TTM-E6]

## new_position
First deterministic read on a fresh position (phase == INITIATION).

- "There is no such thing as a mental stop-loss. If it isn't a live order, it doesn't exist — a
  50% drawdown has been traced to exactly this mistake." [TTM-D11, AR-Stop-Hit]
- "Quantify fear with a number: the moment you assign the exact rupee amount you'll accept losing
  from the peak, the dread vanishes. You don't need to predict the top." [TTM-H-II3]

## drawdown
Position is open at a negative R (underwater vs entry).

- "Ignorance creates fear, not the loss itself — you already defined the ₹ you'll accept losing.
  Trust the stop; don't manage the position from the P&L screen." [TTM-H-II3]
- "The pain of a −1R outweighs the joy of a +1R — a profitable strategy can still feel
  net-negative while it's running. That's prospect theory, not a signal something is wrong."
  [TTM-F1, TTM-F2]

## extension
Position has moved into the EXTENSION phase (trim/partial-sell zone).

- "Sell into strength, never into weakness, on a velocity trade — half out at 15-20% gain, trail
  the rest with no predetermined target." [AR-Selling-Into-Strength, AR-Half-Sell]

## trend_hold
Position is trending and being held (phase == TREND, no exit trigger).

- "Never doubt the trend. Trend-following means giving back part of the profit at the exit —
  accept it. The only risk that matters is the stop-loss, not the % giveback." [TTM-H-II4]

## overdue_exit
Exit flagged 2+ sessions ago and still open (banner set).

- "Confusion is not good for this business. Regret is part of the business — stand by the
  decision you already made and close it out." [AR-Regret, AR-RVNL]
