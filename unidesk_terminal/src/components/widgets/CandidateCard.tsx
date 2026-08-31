import { Link } from "react-router-dom";
import type { Candidate } from "../../data/fixtures";
import { useMode } from "../../lib/ModeContext";
import { deriveState, STATE_META } from "../../lib/status";
import { Chip } from "../ui/Chip";

interface CandidateCardProps {
  candidate: Candidate;
  rank?: number;
}

export function CandidateCard({ candidate: c, rank }: CandidateCardProps) {
  const { mode } = useMode();
  const state = deriveState(c);
  const sm = STATE_META[state];
  const isPro = mode === "pro";

  // H2-05: Stock quality score + coverage + unknowns
  const sq = c.stockStrength;
  const cov: number | undefined = undefined; // coverage not on Candidate type yet
  const unknowns: string[] = [];

  // H2-07: Reactor Scale
  const act = c.activityScore;

  // Trigger distance
  let distPct: number | null = null;
  if (c.trigger != null && c.close) {
    distPct = (c.trigger - c.close) / c.close * 100;
  }

  return (
    <Link to={`/stock/${c.symbol}`}
      className="flex items-center gap-2 py-2 px-1.5 rounded-chip border-b border-border-subtle last:border-b-0 hover:bg-surface-2 transition-colors group">

      {/* H2-12: Rank */}
      {rank != null && <span className="font-mono-num text-caption text-ink-muted w-6 text-right shrink-0">{String(rank).padStart(2, "0")}</span>}

      {/* Symbol + price */}
      <div className="min-w-0 shrink-0 w-28">
        <span className="text-caption font-semibold text-ink-primary">{c.symbol}</span>
        <span className="text-caption text-ink-muted ml-1 font-mono-num">₹{c.close?.toFixed(2)}</span>
      </div>

      {/* State chip */}
      <Chip tone={sm.tone}>{sm.label}</Chip>

      {/* Pro: RS + RVOL + quality */}
      {isPro && (
        <>
          <span className="font-mono-num text-caption text-ink-muted shrink-0 w-16 text-right">RS {c.rsRank?.toFixed(0) ?? "--"}</span>
          <span className="font-mono-num text-caption text-ink-muted shrink-0 w-16 text-right">RV {c.rvol?.toFixed(1) ?? "--"}x</span>
          {sq != null && (
            <span className="font-mono-num text-caption shrink-0 w-14 text-right"
              style={{ color: sq >= 75 ? "var(--positive)" : sq >= 45 ? "var(--score-mid)" : "var(--danger)" }}>
              Q {sq.toFixed(0)}
            </span>
          )}
          {distPct != null && (
            <span className="font-mono-num text-caption text-ink-muted shrink-0 w-16 text-right"
              style={{ color: distPct < -8 ? "var(--positive)" : distPct < 0 ? "var(--score-mid)" : "var(--danger)" }}>
              {distPct > 0 ? "+" : ""}{distPct.toFixed(1)}%
            </span>
          )}
          {c.rr != null && (
            <span className="font-mono-num text-caption shrink-0 w-12 text-right"
              style={{ color: c.rr >= 1 ? "var(--positive)" : "var(--danger)" }}>
              {c.rr.toFixed(1)}R
            </span>
          )}
        </>
      )}

      {/* Beginner: interpreted labels */}
      {!isPro && (
        <span className="text-caption text-ink-tertiary shrink-0">
          {c.rsRank != null ? (c.rsRank >= 90 ? "Top 10%" : c.rsRank >= 70 ? "Top 30%" : c.rsRank >= 50 ? "Top half" : "Bottom half") : "--"} RS
          {c.rvol != null ? (c.rvol >= 3 ? " · High vol" : c.rvol >= 1 ? " · Avg vol" : " · Low vol") : ""}
        </span>
      )}

      {/* Score coverage + unknowns (always in Pro) */}
      {isPro && unknowns.length > 0 && (
        <span className="text-caption text-ink-tertiary shrink-0 text-[10px]" title={unknowns.join("; ")}>
          u:{unknowns.length} {cov != null ? `@${(cov * 100).toFixed(0)}%` : ""}
        </span>
      )}

      {/* Reactor scale (Pro only) */}
      {isPro && act && (
        <span className="text-caption text-ink-tertiary shrink-0 font-mono-num text-[10px]">
          {act.activity_score.toFixed(1)} · {act.q_ratio.toFixed(1)}x · {act.d_ratio.toFixed(1)}x
        </span>
      )}

      {/* H2-13: No pipeline language in primary view */}
    </Link>
  );
}
