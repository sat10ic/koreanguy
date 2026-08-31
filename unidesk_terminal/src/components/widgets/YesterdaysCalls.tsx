import { Link } from "react-router-dom";
import type { OutcomeCall } from "../../data/fixtures";
import { Chip } from "../ui/Chip";

const OUTCOME_META: Record<OutcomeCall["outcome"], { label: string; tone: "positive" | "danger" | "neutral" }> = {
  hit_target: { label: "Hit", tone: "positive" },
  stopped_out: { label: "Stopped", tone: "danger" },
  unresolved: { label: "Active", tone: "neutral" },
};

export function YesterdaysCalls({ calls }: { calls: OutcomeCall[] }) {
  // H3-02: Performance summary
  const wins = calls.filter((c) => c.outcome === "hit_target");
  const losses = calls.filter((c) => c.outcome === "stopped_out");
  const active = calls.filter((c) => c.outcome === "unresolved");
  const resolved = [...wins, ...losses];
  const hitRate = resolved.length > 0 ? (wins.length / resolved.length * 100) : null;
  const avgR = resolved.length > 0
    ? (resolved.reduce((s, c) => s + (c.rMultiple ?? 0), 0) / resolved.length)
    : null;
  const bestR = wins.length > 0 ? Math.max(...wins.map((c) => c.rMultiple ?? 0)) : null;
  const worstR = losses.length > 0 ? Math.min(...losses.map((c) => c.rMultiple ?? 0)) : null;

  return (
    <div className="rounded-card border border-border bg-surface-1 p-3.5">
      <div className="mb-2 flex items-baseline justify-between">
        <h2 className="text-h4 font-semibold text-ink-primary">Yesterday's calls</h2>
        <span className="text-caption text-ink-muted">{calls.length} total</span>
      </div>

      {/* H3-02: Performance summary */}
      <div className="flex items-baseline gap-3 mb-2 text-caption">
        <span className="font-semibold text-ink-primary">{wins.length} hit</span>
        <span className="font-semibold text-danger">{losses.length} stopped</span>
        <span className="text-ink-muted">{active.length} active</span>
        {hitRate != null && <span className="font-mono-num text-ink-muted">Hit rate {hitRate.toFixed(0)}%</span>}
        {avgR != null && <span className="font-mono-num text-ink-muted">{avgR >= 0 ? "+" : ""}{avgR.toFixed(2)}R avg</span>}
        {bestR != null && <span className="font-mono-num text-positive">Best +{bestR.toFixed(1)}R</span>}
        {worstR != null && <span className="font-mono-num text-danger">Worst {worstR.toFixed(1)}R</span>}
      </div>

      {/* H3-03: Outcome strip */}
      <div className="flex items-center gap-0.5 mb-2 overflow-x-auto pb-0.5">
        {calls.slice(0, 30).map((c, i) => (
          <span key={i} className={"inline-block w-2 h-2.5 rounded-[2px] " + (
            c.outcome === "hit_target" ? "bg-positive" :
            c.outcome === "stopped_out" ? "bg-danger" : "bg-neutral"
          )} title={c.symbol + " " + c.outcome} />
        ))}
      </div>

      {/* H3-04: Compact outcome table */}
      <div className="flex flex-col gap-1">
        <div className="flex items-center gap-2 text-caption text-ink-muted font-medium px-2 py-1">
          <span className="w-16">STOCK</span>
          <span className="w-14">RESULT</span>
          <span className="w-14 text-right">RETURN</span>
          <span className="w-14 text-right">MFE</span>
          <span className="w-14 text-right">MAE</span>
          <span className="flex-1" />
        </div>
        {calls.slice(0, 15).map((c) => {
          const meta = OUTCOME_META[c.outcome];
          return (
            <Link key={`${c.symbol}-${c.date}`} to={`/stock/${c.symbol}`}
              className="flex items-center gap-2 rounded-chip px-2 py-1.5 transition-colors hover:bg-surface-2">
              <span className="w-16 text-caption font-semibold text-ink-primary">{c.symbol}</span>
              <Chip tone={meta.tone}>{meta.label}</Chip>
              <span className="w-14 text-right font-mono-num text-caption text-ink-tertiary">
                {c.rMultiple === null ? "—" : `${c.rMultiple > 0 ? "+" : ""}${c.rMultiple.toFixed(1)}R`}
              </span>
              <span className="w-14 text-right font-mono-num text-caption text-ink-tertiary">
                {c.mfePct != null ? "+" + c.mfePct.toFixed(1) + "%" : "—"}
              </span>
              <span className="w-14 text-right font-mono-num text-caption text-ink-tertiary">
                {c.maePct != null ? c.maePct.toFixed(1) + "%" : "—"}
              </span>
              <span className="flex-1 truncate text-caption text-ink-muted">{c.note}</span>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
