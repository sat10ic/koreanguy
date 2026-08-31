import { ChevronDown, ChevronRight, ShieldCheck, AlertTriangle, Clock } from "lucide-react";
import { useState } from "react";
import { TONIGHT_REPORT } from "../../data/tonight";

export function HonestyFooter({ items }: { items: string[] }) {
  const [drawerOpen, setDrawerOpen] = useState(false);
  const hf = TONIGHT_REPORT.honesty_footer;
  const stale = hf?.stale_excluded ?? 0;
  const depth = hf?.history_depth ?? null;

  return (
    <div className="rounded-card border border-border-subtle bg-surface-1 p-3.5">
      <div className="mb-2 flex items-center gap-1.5 text-caption font-medium text-ink-secondary">
        <ShieldCheck size={13} className="text-ink-tertiary" aria-hidden />
        Honesty footer
      </div>
      <ul className="flex flex-col gap-1.5">
        {items.map((item, i) => (
          <li key={i} className="flex gap-2 text-caption text-ink-tertiary">
            <span className="text-ink-muted">-</span>
            <span>{item}</span>
          </li>
        ))}
        {stale > 0 && (
          <li className="flex gap-2 text-caption text-ink-tertiary">
            <span className="text-ink-muted">-</span>
            <span className="flex items-center gap-1">
              <AlertTriangle size={12} className="text-danger" />
              {stale} symbol{stale === 1 ? "" : "s"} excluded by liveness gate
            </span>
          </li>
        )}
        {depth && (
          <li className="flex gap-2 text-caption text-ink-tertiary">
            <span className="text-ink-muted">-</span>
            <span className="flex items-center gap-1">
              <Clock size={12} className="text-ink-muted" />
              {depth}
            </span>
          </li>
        )}
      </ul>

      <button
        onClick={() => setDrawerOpen(!drawerOpen)}
        className="mt-2 flex items-center gap-1 text-caption text-ink-muted hover:text-ink-secondary transition-colors"
      >
        {drawerOpen ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
        Data / Diagnostics
      </button>
      {drawerOpen && (
        <div className="mt-2 space-y-1.5 rounded-chip bg-surface-2 p-2.5">
          <div className="text-caption text-ink-muted">{hf.adjustment_note}</div>
          <div className="text-caption text-ink-muted">{hf.detection_inputs_policy}</div>
          {hf.universe_gate_skips && Object.keys(hf.universe_gate_skips).length > 0 && (
            <div className="text-caption text-ink-muted">
              Gate skips: {Object.entries(hf.universe_gate_skips as Record<string, number>).map(([k, v]) => k + "=" + v).join(", ")}
            </div>
          )}
          <div className="text-caption text-ink-tertiary">
            CA: {hf.actions_applied} actions, {hf.adjusted_symbols} symbols adjusted
          </div>
        </div>
      )}
    </div>
  );
}