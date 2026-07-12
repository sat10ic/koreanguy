import React, { useState } from "react";
import { useDensity } from "../../DensityContext.jsx";

// Per-tab purpose headers. Copy describes the TOOL, not trading advice.
// Source: Manas OS design corpus / UX_AUDIT_FULL.md intent.
const TAB_COPY = {
  MARKET: {
    what: "Regime, breadth, and market structure for today's date.",
    how:  "Read regime mode first (RISK_ON / SELECTIVE / DEFENSIVE / NO_TRADE). Then check breadth — are more stocks above their DMAs than below? If both are supportive, the setup funnel is open.",
    next: "Review the setup funnel count, then go to SCANNERS or DEBATE →",
  },
  SCANNERS: {
    what: "Preset technical scans run against the NSE universe.",
    how:  "Each preset shows the stocks that matched its conditions today. Hits are raw scan results — not vetted by the council. Use them as candidates, not decisions.",
    next: "Pick interesting candidates and push them to DEBATE for a full council review →",
  },
  SHORTLIST: {
    what: "Stocks you have added to your watchlist from past debate sessions.",
    how:  "Each row shows the current verdict, setup context, and next trigger. A TAKE chip means the council endorsed it; always check the current regime before acting.",
    next: "Review trigger levels, then open a TRADE PLAN for any setup you want to act on →",
  },
  DEBATE: {
    what: "The AI council's verdict on tonight's gate-passed setup candidates.",
    how:  "Each card shows the chair verdict (TAKE / SKIP), conviction score, and the seat breakdown. Read the chair summary and contradiction notes before the individual seats.",
    next: "For any TAKE you agree with, open the TRADE PLAN or add to SHORTLIST →",
  },
  ALPHA: {
    what: "Shadow cross-sectional ranking of the universe and research bench status.",
    how:  "The opportunity rank shows which stocks are leading after removing broad market moves. This is a SHADOW/RESEARCH rank, not a tradeable call — it informs the debate council, not your sizing.",
    next: "Cross-reference Alpha leaders with tonight's DEBATE cards to see alignment →",
  },
  POSITIONS: {
    what: "Your open positions tracked against their original trade plan.",
    how:  "Each row shows current P&L vs the plan's stop and target. Flagged exits have a reason from the nightly pipeline. Live prices (when feed is connected) show LTP with a freshness indicator.",
    next: "Act on any flagged exit, then update the journal →",
  },
  JOURNAL: {
    what: "A log of every trade decision — entries, exits, and skips.",
    how:  "Each row shows the symbol, decision type, and outcome. Use it to review your decision quality over time — pattern your reasons, not just your P&L.",
    next: "After reviewing, go back to MARKET or DEBATE for the next session →",
  },
  TRADE_PLAN: {
    what: "The exact broker ticket for one decision — entry, stop, target, size, and the do-not-trade gates.",
    how:  "The do-not-trade gates are hard stops on execution. The checklist is what to confirm at the broker; it saves per symbol and date.",
    next: "Work the checklist, then log the decision (TAKE / SKIP) in JOURNAL to close the loop →",
  },
};

// TabPurposeHeader: renders a WHAT / HOW / NEXT header for each tab.
// - Beginner mode: expanded by default.
// - Expert mode: collapsed to one line with a [?] toggle button.
export default function TabPurposeHeader({ tab }) {
  const { isExpert } = useDensity();
  const [expanded, setExpanded] = useState(false);
  const copy = TAB_COPY[tab];
  if (!copy) return null;

  if (isExpert) {
    return (
      <div className="tph-expert">
        <span className="tph-expert-label">{tab}</span>
        <button
          className="tph-toggle"
          onClick={() => setExpanded((v) => !v)}
          aria-expanded={expanded}
          aria-label="Toggle tab guide"
        >
          {expanded ? "▲ hide guide" : "? guide"}
        </button>
        {expanded && (
          <div className="tph-body">
            <div className="tph-row"><span className="tph-key">WHAT</span><span>{copy.what}</span></div>
            <div className="tph-row"><span className="tph-key">HOW</span><span>{copy.how}</span></div>
            <div className="tph-row"><span className="tph-key">NEXT</span><span>{copy.next}</span></div>
          </div>
        )}
      </div>
    );
  }

  // Beginner: always visible
  return (
    <div className="tph-beginner" role="region" aria-label={`${tab} guide`}>
      <div className="tph-row"><span className="tph-key">WHAT</span><span>{copy.what}</span></div>
      <div className="tph-row"><span className="tph-key">HOW TO READ</span><span>{copy.how}</span></div>
      <div className="tph-row tph-row--next"><span className="tph-key">NEXT</span><span>{copy.next}</span></div>
    </div>
  );
}
