import { useEffect, useState } from "react";
import { getBreadthHistory } from "../api.js";

export default function DivergenceFlag() {
  const [showFlag, setShowFlag] = useState(false);

  useEffect(() => {
    let cancelled = false;

    getBreadthHistory(6)
      .then((rows) => {
        if (cancelled) return;

        const cleanRows = (rows || []).filter(
          (row) =>
            row &&
            row.pct_above_20dma != null &&
            row.advances != null &&
            row.declines != null,
        );

        if (cleanRows.length < 5) {
          setShowFlag(false);
          return;
        }

        const latest = cleanRows[cleanRows.length - 1];
        const fiveBack = cleanRows[Math.max(0, cleanRows.length - 6)];
        const netAdvances = Number(latest.advances) - Number(latest.declines);
        const breadthDrop =
          Number(fiveBack.pct_above_20dma) - Number(latest.pct_above_20dma);

        setShowFlag(netAdvances > 0 && breadthDrop >= 3);
      })
      .catch(() => {
        if (!cancelled) setShowFlag(false);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  if (!showFlag) return null;

  return (
    <div
      className="flex items-start gap-2 rounded border border-warn-border bg-warn-bg px-3 py-2 text-warn"
      data-testid="divergence-flag"
    >
      <span className="mt-1 h-2 w-2 shrink-0 rounded-full bg-warn-dot" />
      <span className="font-mono text-xs uppercase tracking-wide">CAUTION</span>
      <span className="font-sans text-sm text-ink2">
        Index rising but breadth is narrowing (fewer stocks above their 20-day
        average over the last 5 sessions) — a thinning rally; late breakouts are
        riskier here.
      </span>
    </div>
  );
}
