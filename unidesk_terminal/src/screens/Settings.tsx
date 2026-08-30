import { Database, SlidersHorizontal } from "lucide-react";
import { AppShell } from "../components/shell/AppShell";
import { useMode } from "../lib/ModeContext";
import { SESSION } from "../data/fixtures";

export function Settings() {
  const { mode, setMode } = useMode();

  return (
    <AppShell breadcrumb={["Settings"]}>
      <div className="flex flex-col gap-4 p-4">
        <div className="rounded-card border border-border bg-surface-1 p-3.5">
          <h2 className="mb-2.5 text-h4 font-semibold text-ink-primary">Display mode</h2>
          <p className="mb-3 text-caption text-ink-tertiary">
            One app structure, two vocabularies — Beginner and Pro never diverge in layout, only in labels.
          </p>
          <div role="group" aria-label="Display mode" className="flex w-fit items-center rounded-chip border border-border-subtle p-0.5">
            {(["beginner", "pro"] as const).map((m) => (
              <button
                key={m}
                onClick={() => setMode(m)}
                aria-pressed={mode === m}
                className={`min-h-[32px] rounded-[4px] px-4 py-1.5 text-caption font-medium capitalize transition-colors duration-150 ease-out ${
                  mode === m ? "bg-accent-bg text-accent-strong" : "text-ink-tertiary hover:text-ink-secondary"
                }`}
              >
                {m}
              </button>
            ))}
          </div>
        </div>

        <div className="rounded-card border border-border bg-surface-1 p-3.5">
          <div className="mb-2.5 flex items-center gap-1.5 text-caption text-ink-muted">
            <Database size={13} aria-hidden />
            Data status
          </div>
          <div className="grid grid-cols-3 gap-2">
            <div className="rounded-chip border border-border-subtle bg-surface-2 px-2.5 py-2">
              <div className="text-caption text-ink-muted">Last session</div>
              <div className="font-mono-num text-body font-semibold text-ink-primary">{SESSION.date}</div>
            </div>
            <div className="rounded-chip border border-border-subtle bg-surface-2 px-2.5 py-2">
              <div className="text-caption text-ink-muted">Universe scanned</div>
              <div className="font-mono-num text-body font-semibold text-ink-primary">{SESSION.universeScanned}</div>
            </div>
            <div className="rounded-chip border border-border-subtle bg-surface-2 px-2.5 py-2">
              <div className="text-caption text-ink-muted">Skipped (insufficient history)</div>
              <div className="font-mono-num text-body font-semibold text-ink-primary">{SESSION.universeSkipped}</div>
            </div>
          </div>
          <p className="mt-2 text-caption text-ink-muted">
            Source: NSE bhavcopy (EQ series), unadjusted. Corporate-action adjustment pass is still open (N3).
          </p>
        </div>

        <div className="rounded-card border border-border-subtle bg-surface-1 p-3.5">
          <div className="mb-2.5 flex items-center gap-1.5 text-caption text-ink-muted">
            <SlidersHorizontal size={13} aria-hidden />
            Weights &amp; gates
          </div>
          <p className="text-caption text-ink-tertiary">
            Detector thresholds and entry-quality weights are caller-supplied config (R14), not literals — but
            there's no config-editing UI here yet. Editing them today means changing the values passed into
            <code className="mx-1 rounded-[4px] bg-surface-2 px-1 py-0.5 font-mono-num text-caption">unidesk/momentum</code>
            call sites directly. A settings UI over the parameter register is queued behind RESEARCH.
          </p>
        </div>
      </div>
    </AppShell>
  );
}
