export const GLOSSARY = {
  "four-phase": {
    label: "Four-phase read",
    plain: "TradeTM's four-phase market model (Demand Domination, Supply Domination, Lack of Demand, Lack of Supply) approximated from the existing MBI day-color and pillar checks — display-only, does not change the governor's law.",
    care: "You care because 'Lack of' phases are where TradeTM says most momentum-burst failures cluster and setups trigger without following through — a chop warning on top of the mode you already see.",
  },
  "mbi-day-color": {
    label: "MBI day-color",
    plain: "MBI day-color is the daily breadth color computed from R10, R20, R50, and R4.5 breadth bands.",
    care: "You care because green means broad support, red means broad weakness, and white means mixed conditions.",
  },
  xp: {
    label: "XP",
    plain: "XP is the recursive regime dial driven by prior XP plus today's breadth, big advancers, big decliners, and 10/20-day participation.",
    care: "You care because low XP means weak desk readiness while stronger XP says the market backdrop can support more risk.",
  },
  "xp-badge": {
    label: "XP badge",
    plain: "The XP badge is the header's compact display of the current XP regime value.",
    care: "You care because it gives a quick read on whether tonight is a weak, building, strong, or extreme breadth environment.",
  },
  r10: {
    label: "R10",
    plain: "R10 is the ratio of stocks above their 10-day average to stocks below it, multiplied by 100.",
    care: "You care because it shows very short-term breadth support or weakness.",
  },
  r20: {
    label: "R20",
    plain: "R20 is the ratio of stocks above their 20-day average to stocks below it, multiplied by 100.",
    care: "You care because it shows swing breadth and helps judge whether setups have enough market participation.",
  },
  r50: {
    label: "R50",
    plain: "R50 is the ratio of stocks above their 50-day average to stocks below it, multiplied by 100.",
    care: "You care because it shows whether the intermediate trend has broad support.",
  },
  "r4.5": {
    label: "R4.5",
    plain: "R4.5 is the ratio of stocks up at least about 4.5% to stocks down at least about 4.5%, multiplied by 100.",
    care: "You care because it flags whether the day's burst moves are dominated by buyers or sellers.",
  },
  "mode-risk-on": {
    label: "RISK_ON",
    plain: "RISK_ON is the most permissive regime, reserved for green breadth with all four known pillars passing and no warning-day downgrade.",
    care: "You care because it allows the broadest setup families and the most cards.",
  },
  "mode-selective": {
    label: "SELECTIVE",
    plain: "SELECTIVE is the default constructive-but-picky regime when conditions are not strong enough for RISK_ON and not weak enough for DEFENSIVE.",
    care: "You care because the desk narrows to catalyst and base/pattern setups.",
  },
  "mode-defensive": {
    label: "DEFENSIVE",
    plain: "DEFENSIVE is used when breadth is red or all known pillars are failing, unless the full NO_TRADE condition is met.",
    care: "You care because the desk only permits catalyst-style opportunities and cuts size.",
  },
  "mode-no-trade": {
    label: "NO_TRADE",
    plain: "NO_TRADE is the cash-first regime used when a red day combines with zero pillars passing or an unknown mode is degraded safely.",
    care: "You care because the governor intentionally shows zero setup cards.",
  },
  "regime-age": {
    label: "Regime age",
    plain: "Regime age is the number of calendar days between the run date and the latest regime snapshot used by the desk.",
    care: "You care because day 0 is fresh, while an older number means the desk is leaning on a stale-but-real regime read.",
  },
  "law-max-cards": {
    label: "Max cards",
    plain: "Max cards is the governor's cap on how many ranked setup cards the feed may show today.",
    care: "You care because it prevents a weak regime from flooding the desk with marginal ideas.",
  },
  "law-risk-trade": {
    label: "Risk/trade",
    plain: "Risk/trade is the governor's base-to-hard-maximum percent risk band for one new trade in today's mode.",
    care: "You care because it defines how large a single idea is allowed to be.",
  },
  "law-allowed-families": {
    label: "Allowed families",
    plain: "Allowed families are the setup families the governor permits in the current regime.",
    care: "You care because candidates outside this list are refused before the models debate them.",
  },
  "law-open-risk": {
    label: "Open-risk",
    plain: "Open-risk compares current portfolio risk against the governor's open-risk cap for today's regime.",
    care: "You care because it tells you whether there is room to add risk.",
  },
  "law-pushes": {
    label: "Pushes",
    plain: "Pushes shows whether the governor allows outbound signals in the current regime.",
    care: "You care because NO_TRADE and DEFENSIVE suppress pushes even if something looks interesting.",
  },
  "gate-regime": {
    label: "Regime gate",
    plain: "The regime gate checks whether today's market mode allows the candidate's setup family.",
    care: "You care because a setup can be good but still disallowed by today's law.",
  },
  "gate-tradability": {
    label: "Tradability gate",
    plain: "The tradability gate refuses universe failures, ASM flags, lottery profiles, and pump signatures.",
    care: "You care because it keeps structurally dangerous or untradeable names out before scoring.",
  },
  "gate-trend": {
    label: "Trend gate",
    plain: "The trend gate checks history, moving-average structure, relative strength, and nearness to highs.",
    care: "You care because it rejects names that are not in a confirmed uptrend or are just recovery rallies.",
  },
  "gate-fresh-leg": {
    label: "Fresh-leg gate",
    plain: "The fresh-leg gate checks whether the move is still fresh versus the 21EMA, pivot, and breakout age.",
    care: "You care because it avoids chasing stale or parabolic entries.",
  },
  "gate-participation": {
    label: "Participation gate",
    plain: "The participation gate checks delivery and breakout-volume confirmation.",
    care: "You care because a trigger without real participation is more likely to fail.",
  },
  "gate-risk": {
    label: "Risk gate",
    plain: "The risk gate accepts or refuses the candidate using the risk plan's stop, reward/risk, and quantity math.",
    care: "You care because an attractive chart is still skipped if the trade cannot be sized cleanly.",
  },
  conviction: {
    label: "Conviction",
    plain: "Conviction is a model's numeric confidence in its TAKE or SKIP verdict.",
    care: "You care because higher conviction means the model is less lukewarm about the setup.",
  },
  spread: {
    label: "Spread",
    plain: "Spread is the difference between the highest and lowest model conviction for the same symbol.",
    care: "You care because a large spread flags disagreement even when the final verdict looks simple.",
  },
  struck: {
    label: "Struck",
    plain: "Struck means the chair risk gate removed a shortlisted symbol on a stated risk ground.",
    care: "You care because struck names are intentionally pushed below usable ideas or turned into SKIP.",
  },
  chair: {
    label: "Chair",
    plain: "The chair is the final merge pass that aggregates model verdicts and may strike names for portfolio, correlation, or event risk.",
    care: "You care because it is the final risk referee after the model debate.",
  },
  bull: {
    label: "BULL",
    plain: "BULL is the model's positive case for why the setup could work.",
    care: "You care because it shows the upside thesis you would be buying.",
  },
  bear: {
    label: "BEAR",
    plain: "BEAR is the model's negative case for why the setup could fail.",
    care: "You care because it shows the risk thesis you need to accept or reject.",
  },
  take: {
    label: "TAKE",
    plain: "TAKE is a model or chair verdict saying the candidate is acceptable to act on.",
    care: "You care because only TAKE names can move toward sizing and signals.",
  },
  skip: {
    label: "SKIP",
    plain: "SKIP is a verdict saying the candidate should not be acted on tonight.",
    care: "You care because it keeps weak or unresolved setups out of the actionable list.",
  },
  veto: {
    label: "VETO",
    plain: "VETO is a hard refusal concept: a blocking risk is strong enough to override interest in the setup.",
    care: "You care because one hard veto should outweigh attractive but unsafe evidence.",
  },
  "tier-passed": {
    label: "PASSED tier",
    plain: "PASSED means the candidate survived the deterministic gate cascade and was eligible for debate.",
    care: "You care because it separates true shortlist names from refused near-misses.",
  },
  "tier-near-miss": {
    label: "NEAR_MISS tier",
    plain: "NEAR_MISS means a refused candidate was close enough to inspect, but it did not pass the gate cascade.",
    care: "You care because near-misses are learning material, not normal trade candidates.",
  },
  "vision-strip": {
    label: "Vision strip",
    plain: "The vision strip shows chart thumbnails plus the vision agent's stamp when that pass ran.",
    care: "You care because it gives a quick visual check beside the text debate.",
  },
  "sizer-multiplier": {
    label: "Sizer multiplier",
    plain: "The sizer multiplier scales the base quantity, currently displayed on a 0.25x to 1.25x band.",
    care: "You care because it turns the plan's base quantity into the final suggested quantity.",
  },
  "dry-run": {
    label: "DRY-RUN",
    plain: "DRY-RUN means no live signal was sent from the current run card.",
    care: "You care because you are reviewing the desk output without treating it as a live alert.",
  },
  live: {
    label: "LIVE",
    plain: "LIVE means at least one signal row on the current run card was marked sent.",
    care: "You care because the desk has actually pushed an actionable alert.",
  },
  "activity-stream": {
    label: "Activity stream",
    plain: "The activity stream is the ordered log of pipeline stages and agent events for the selected run.",
    care: "You care because it shows what ran, what failed, and where the desk's outputs came from.",
  },
  "stage-ingest_bhavcopy": {
    label: "ingest_bhavcopy",
    plain: "ingest_bhavcopy loads local bhavcopy price and delivery data.",
    care: "You care because prices and delivery are the raw market inputs for later stages.",
  },
  "stage-indicators": {
    label: "indicators",
    plain: "indicators computes per-symbol technical features from daily prices.",
    care: "You care because scans and setup evidence depend on these features.",
  },
  "stage-regime_snapshot": {
    label: "regime_snapshot",
    plain: "regime_snapshot writes the XP, MBI, and market posture row from breadth data.",
    care: "You care because today's law and setup permissions start from this regime read.",
  },
  "stage-scan_candidates": {
    label: "scan_candidates",
    plain: "scan_candidates runs setup discovery, gates, readiness ranking, and persistence.",
    care: "You care because this is where raw market data becomes a shortlist.",
  },
  "stage-agents_debate": {
    label: "agents_debate",
    plain: "agents_debate asks the debate models for verdicts and then runs the chair merge.",
    care: "You care because it turns a deterministic shortlist into argued TAKE/SKIP decisions.",
  },
  "stage-agents_coach": {
    label: "agents_coach",
    plain: "agents_coach reviews open journal positions and writes coaching output.",
    care: "You care because it connects tonight's desk to existing holdings.",
  },
  "coach-verdict": {
    label: "Coach verdict",
    plain: "The coach verdict is the nightly exit-engine action for an open position: hold, trim, exit, or move the stop.",
    care: "You care because it turns the holding into a concrete next action instead of a passive row.",
  },
  "open-r": {
    label: "Open R",
    plain: "Open R is the current unrealized profit or loss measured against the original entry-to-stop risk.",
    care: "You care because +1R means the trade has earned one unit of planned risk, while -1R means it has reached the original stop distance.",
  },
  "days-held": {
    label: "Days held",
    plain: "Days held is the number of trading sessions since the position's entry date.",
    care: "You care because a setup that should work quickly needs different patience from a longer base or trend hold.",
  },
  "stage-expectancy": {
    label: "expectancy",
    plain: "expectancy updates base-rate cells by setup family and regime.",
    care: "You care because it tells whether similar setups have historically paid.",
  },
  "stage-candidate_outcomes": {
    label: "candidate_outcomes",
    plain: "candidate_outcomes records forward-return outcomes for persisted candidates.",
    care: "You care because future expectancy and lessons need actual follow-through data.",
  },
  "stage-eod_alerts": {
    label: "eod_alerts",
    plain: "eod_alerts builds the nightly manual-trading alerts from candidates and watchlist data.",
    care: "You care because this is what can become actionable end-of-day work.",
  },
  "stage-telegram_digest": {
    label: "telegram_digest",
    plain: "telegram_digest builds and persists the deterministic Telegram digest and armed list.",
    care: "You care because it is the outbound summary layer for the run.",
  },
  "trail-stop": {
    label: "Trail stop",
    plain: "The trail stop is the current protective stop price after the exit engine has raised it past the original structural stop.",
    care: "You care because it is the live price that would trigger an exit today, not the original entry-day stop.",
  },
  "position-phase": {
    label: "Phase",
    plain: "Phase is the exit engine's read of where a position sits along its R-multiple path (e.g. building, extended, trailing).",
    care: "You care because it explains why the coach verdict is hold vs trim vs exit right now.",
  },
  "hit-rate": {
    label: "Hit rate",
    plain: "Hit rate is the share of trades in a setup/regime cell that closed with a positive R result.",
    care: "You care because a high hit rate with tiny wins can still be a losing system — pair it with avg R and n.",
  },
  "avg-r": {
    label: "Avg R",
    plain: "Avg R is the mean R-multiple result (profit or loss measured in units of planned risk) across trades in a cell.",
    care: "You care because it is the actual payoff size, the other half of expectancy alongside hit rate.",
  },
  unproven: {
    label: "UNPROVEN",
    plain: "UNPROVEN marks a setup/screener cell whose sample size (n) is below the trust floor for a real base rate.",
    care: "You care because a confident-looking number on too few trades is noise, not evidence — wait for more n before trusting it.",
  },
  "base-rate": {
    label: "Base rate",
    plain: "Base rate is the historical hit rate/avg R for a setup family or screener in a given regime, computed from actual past outcomes.",
    care: "You care because it is the honest prior for how often a similar setup has actually worked, not a guess.",
  },
  "screener-calibration": {
    label: "Screener calibration",
    plain: "Screener calibration is the T+5/T+10/T+20 forward-return check on stocks a screener flagged, versus a same-universe baseline.",
    care: "You care because it tells you whether a screener hit has actually predicted excess return, not just looked interesting.",
  },
  "fii-dii": {
    label: "FII/DII",
    plain: "FII/DII is the daily net buy/sell flow from Foreign and Domestic Institutional Investors in the cash market.",
    care: "You care because sustained one-sided flow (especially DII absorbing FII selling) is a market-wide tailwind/headwind signal.",
  },
  "vix-band": {
    label: "VIX band",
    plain: "The VIX band reads India VIX's level against calm/normal/elevated/panic thresholds and whether it is rising or falling.",
    care: "You care because a rising VIX often precedes wider stops and smaller size being the safer call, independent of price action.",
  },
  "delivery-pct": {
    label: "Delivery %",
    plain: "Delivery % is the share of traded quantity settled by actual delivery instead of same-day squared-off (intraday) volume.",
    care: "You care because high, rising delivery% on up days suggests real accumulation rather than speculative churn.",
  },
  "pct-of-mcap": {
    label: "% of mcap",
    plain: "% of mcap is a bulk/block deal's traded value as a percentage of the company's total market capitalization.",
    care: "You care because a large deal in a small-cap moves the float far more than the same rupee amount in a mega-cap.",
  },
  "prop-desk": {
    label: "Prop/HFT counterparty",
    plain: "A prop/HFT counterparty is a known proprietary-trading or high-frequency firm on the other side of a bulk/block deal.",
    care: "You care because their trades are often inventory/arbitrage flow, not a directional conviction signal like a fund or promoter buy.",
  },
  "vol-forecast-experimental": {
    label: "Vol forecast (experimental)",
    plain: "The vol forecast is an experimental HAR-RV model's estimate of NIFTY realized volatility over the next 5 sessions, from today's short/medium/long-run volatility averages.",
    care: "You care because rising forecast volatility is a heads-up for wider stops and smaller size ahead — it is a walk-forward-validated fact for context, never a governor input.",
  },
  "risk-experimental": {
    label: "RISK (experimental)",
    plain: "RISK is an experimental hierarchical model's estimate of the chance a sector falls 2%+ over the next 5 sessions, shrunk toward the market-wide pooled rate.",
    care: "You care because it is a walk-forward-validated fact for context — it never gates or sizes trades, and should be weighed alongside, not instead of, the regime and setup evidence.",
  },
  "stock-hmm-experimental": {
    label: "Stock HMM regime (experimental)",
    plain: "A 3-state Gaussian HMM fit on this stock's own price/volume history (log return, 10d volatility, volume z-score), reporting P(Bullish)/P(Bearish)/P(Chop) for each recent session and the model's current best-guess state.",
    care: "You care because it is a read of this stock alone (not the market), display-only — it never gates, sizes, or ranks a trade, and needs at least 150 clean bars of history before it will show anything.",
  },
  "morning-brief": {
    label: "TONIGHT'S BRIEF",
    plain: "The morning brief is the run-card summary of regime, shortlist, debates, signals, coaching, lessons, and errors.",
    care: "You care because it gives the quickest plain-English read before opening the details.",
  },
  "tonights-call": {
    label: "TONIGHT'S CALL",
    plain: "Tonight's call is the desk's one-line verdict for tonight — what stance to take and what to actually do — computed deterministically from the regime, the chair's verdicts, and each setup's historical base rate.",
    care: "You care because this is the answer to \"so what do I do\" — the rest of the card is the evidence behind this one line.",
  },
  rs: {
    label: "RS",
    plain: "RS (Relative Strength) is ChartsMaze's 1-99 percentile rank of a stock's price performance against the rest of the traded universe.",
    care: "You care because a high RS name is outperforming almost everything else right now — the raw material swing setups are built from.",
  },
  adr: {
    label: "ADR",
    plain: "ADR% (Average Daily Range) is the average of a stock's daily high-low spread over 20 days, as a percentage of price.",
    care: "You care because ADR sets how wide a stop needs to be — a high-ADR stock needs more room and smaller size for the same risk.",
  },
  "glyph-strip": {
    label: "dot strip",
    plain: "The filled-dot strip (up to 8 dots shown) is a quick visual count of purple dots (accumulation-signal days) in the last 60 days — hover or check the title for the exact count.",
    care: "You care because more purple dots in a short window is a stronger accumulation read than the same count spread thin.",
  },
  "ema-stack": {
    label: "EMA-stack",
    plain: "EMA-stack reads whether price sits above a rising-order EMA10>EMA21>EMA50 (Lead), below a falling-order stack (Lag), or neither (Mixed).",
    care: "You care because a Lead stack means the short, medium, and long trend all agree — Mixed or Lag means the trend picture is contested.",
  },
  stance: {
    label: "Stance",
    plain: "Stance is one of four fixed labels: STAND ASIDE (regime forbids trading), SIT OUT (nothing cleared the gate tonight), CAUTION (a setup cleared the gate but its own history argues for smaller size or paper-trading), or ACT PER PLAN (trade it as sized).",
    care: "You care because the stance tells you the desk's confidence level before you commit capital, not just what technically passed.",
  },
};

export const GLOSSARY_KEYS = Object.freeze(Object.keys(GLOSSARY));

export function hasGlossaryTerm(key) {
  return Object.prototype.hasOwnProperty.call(GLOSSARY, key);
}
