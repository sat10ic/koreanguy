// H1-07: Tonight's Playbook — the ONE named, documented regime→playbook
// mapping. It is a HEURISTIC, NOT VALIDATED: no backtest, no expectancy
// evidence backs these rows. Presented as qualitative guidance only.
// X-03 constraint: this mapping never emits a number — no size, no rupee
// amount, no position count. Quantitative exposure lives on the Desk
// screen (D-04) and is descriptive of the owner's own record, never this.
export interface PlaybookRow {
  exposure: string;    // qualitative only — never a number (X-03)
  favour: string;
  avoid: string;
  selectivity: string;
}

export const REGIME_PLAYBOOK: Record<string, PlaybookRow> = {
  CHOP: {
    exposure: "Reduced",
    favour: "Tight compression setups, episodic catalysts",
    avoid: "Chasing breakouts, momentum continuation",
    selectivity: "Very high — most breakouts fail in chop",
  },
  BULL: {
    exposure: "Normal",
    favour: "Breakouts, momentum continuation",
    avoid: "Shorting strength",
    selectivity: "Moderate",
  },
  BEAR: {
    exposure: "Defensive",
    favour: "Quality names, reversal reclaim",
    avoid: "High-beta momentum",
    selectivity: "Very high",
  },
};

export const PLAYBOOK_CAVEAT = "Heuristic mapping — not yet validated against outcomes";

export function playbookFor(regimeNote: string | undefined): PlaybookRow {
  const first = regimeNote?.split(/[ (—]/)[0] ?? "";
  return REGIME_PLAYBOOK[first] ?? {
    exposure: "Unknown",
    favour: "Setup quality only",
    avoid: "Regime-dependent bets",
    selectivity: "High",
  };
}
