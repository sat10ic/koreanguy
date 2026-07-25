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
    what: "Open holdings — marked to market against the latest close.",
    how:  "Each row shows unrealized P&L vs your average cost, plus the stop and target where a plan exists. Imported holdings with no cost basis show 'cost unknown' rather than a fabricated P&L. Flagged exits carry a reason from the nightly pipeline.",
    next: "Act on any flagged exit, then log the closed trade in JOURNAL →",
  },
  JOURNAL: {
    // The user reported "my entries are in the journal and I haven't marked
    // them closed, why is P&L not changing". Cause: journal_trades holds only
    // CLOSED round-trips (420 imported, zero open); open holdings live in
    // broker_open_lots and surface on POSITIONS. Nothing here will ever tick,
    // by construction -- so the header has to say that and point across.
    what: "Closed trades only — your expectancy history.",
    how:  "Every row here is a finished round-trip with its R result and mistake tags. Nothing on this tab moves with the market; open holdings are marked to market on POSITIONS.",
    next: "Review your decision quality here; manage anything still open on POSITIONS →",
  },
  TRADE_PLAN: {
    what: "The exact broker ticket for one decision — entry, stop, target, size, and the do-not-trade gates.",
    how:  "The do-not-trade gates are hard stops on execution. The checklist is what to confirm at the broker; it saves per symbol and date.",
    next: "Work the checklist, then log the decision (TAKE / SKIP) in JOURNAL to close the loop →",
  },
};

// Bridge chip on JOURNAL: "N open holdings -> POSITIONS". The count comes from
// /api/desk/positions, i.e. the SAME rows POSITIONS renders, so the number can
// never disagree with the tab it points at. Deliberately NOT read from
// broker_open_lots directly: that table holds 45 rows, of which 34 have
// NEGATIVE qty (FIFO sells with no matching buy) and only 11 are genuinely
// open. Counting the table would put "45" on screen -- wrong by 4x, and the
// exact class of on-screen falsehood this pass exists to remove.
function useOpenPositionCount(enabled) {
  const [count, setCount] = useState(null);
  React.useEffect(() => {
    if (!enabled) return undefined;
    let alive = true;
    fetch("/api/desk/positions")
      .then((r) => (r.ok ? r.json() : null))
      .then((j) => {
        if (alive && j && Array.isArray(j.positions)) setCount(j.positions.length);
      })
      .catch(() => { /* chip simply does not render; never block the tab */ });
    return () => { alive = false; };
  }, [enabled]);
  return count;
}

function OpenHoldingsBridge({ count, onGo }) {
  if (count === null || count === undefined) return null;
  const label = `${count} open holding${count === 1 ? "" : "s"}`;
  return (
    <button className="tph-bridge" onClick={onGo} title="Open holdings are marked to market on POSITIONS">
      {label} <span aria-hidden="true">→ POSITIONS</span>
    </button>
  );
}

// TabPurposeHeader: renders a WHAT / HOW / NEXT header for each tab.
// - Beginner mode: expanded by default.
// - Expert mode: collapsed to one line with a [?] toggle button.
export default function TabPurposeHeader({ tab, onNavigate }) {
  const { isExpert } = useDensity();
  const [expanded, setExpanded] = useState(false);
  const openCount = useOpenPositionCount(tab === "JOURNAL");
  const copy = TAB_COPY[tab];
  if (!copy) return null;
  const bridge = tab === "JOURNAL"
    ? <OpenHoldingsBridge count={openCount} onGo={() => onNavigate && onNavigate("POSITIONS")} />
    : null;

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
        {bridge}
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
      <div className="tph-row tph-row--next"><span className="tph-key">NEXT</span><span>{copy.next}</span>{bridge}</div>
    </div>
  );
}
