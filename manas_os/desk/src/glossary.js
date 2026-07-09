export const GLOSSARY = {
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
  "morning-brief": {
    label: "MORNING BRIEF",
    plain: "The morning brief is the run-card summary of regime, shortlist, debates, signals, coaching, lessons, and errors.",
    care: "You care because it gives the quickest plain-English read before opening the details.",
  },
};

export const GLOSSARY_KEYS = Object.freeze(Object.keys(GLOSSARY));

export function hasGlossaryTerm(key) {
  return Object.prototype.hasOwnProperty.call(GLOSSARY, key);
}
