import { useState, type ReactNode, useSyncExternalStore } from "react";
import { WifiOff } from "lucide-react";
import { useMode } from "../../lib/ModeContext";
import { bundledSessionName, deskHealth, deskSource, subscribeDeskData } from "../../data/deskData";
import { Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";

/*
  App shell (spec SS4): fixed sidebar (208/64, persisted) + 56px top bar +
  12-column-ready content area with spec paddings (inline 24-32, top 20-24).
  E-3: renders the LOUD OFFLINE banner when the desk server is unreachable —
  the bundled snapshot is shown, and it NAMES its session (house rule 1:
  never a silent substitution). B2-7: shows the last scheduled nightly
  failure, so a failed automation is never silent.
*/

export function AppShell({ breadcrumb, children }: { breadcrumb: string[]; children: ReactNode }) {
  const { mode, setMode } = useMode();
  const [collapsed, setCollapsed] = useState<boolean>(() => {
    try { return localStorage.getItem("unidesk.sidebarCollapsed") === "1"; } catch { return false; }
  });
  // re-render when the data layer re-hydrates (boot fetch + post-Run refetch)
  useSyncExternalStore(subscribeDeskData, () => deskSource());
  const source = deskSource();
  const health = deskHealth();
  const lastRun = health?.last_scheduled_run ?? null;
  const lastRunFailed = !!lastRun && lastRun.status !== "succeeded";

  function toggle() {
    setCollapsed((v) => {
      try { localStorage.setItem("unidesk.sidebarCollapsed", v ? "0" : "1"); } catch { /* private mode */ }
      return !v;
    });
  }

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-surface-0 text-ink-primary">
      <Sidebar collapsed={collapsed} onToggle={toggle} />
      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar mode={mode} onModeChange={setMode} breadcrumb={breadcrumb} />
        {source === "bundled" && (
          <div className="flex items-center gap-2 border-b border-warning-border bg-warning-bg px-6 py-1.5 text-caption text-ink-secondary" role="alert">
            <WifiOff size={13} className="shrink-0 text-warning" aria-hidden />
            <span>
              <span className="font-semibold text-warning">OFFLINE</span> — desk server unreachable on :8181. Showing the
              {" "}bundled snapshot (session {bundledSessionName() || "—"}); data will not update live. Start the server:
              <code className="ml-1 rounded-[4px] bg-surface-2 px-1 py-0.5 font-mono-num text-[11px]">python -m uvicorn unidesk.server.app:app --port 8181</code>
            </span>
          </div>
        )}
        {lastRunFailed && (
          <div className="flex items-center gap-2 border-b border-danger-border bg-danger-bg px-6 py-1.5 text-caption text-ink-secondary" role="alert">
            <span>
              <span className="font-semibold text-danger">Last scheduled nightly FAILED</span>
              {" "}— stage "{lastRun?.failed_stage ?? "unknown"}" (exit {lastRun?.exit_code ?? "—"}) at {lastRun?.finished_at}. The desk is
              running on older data; see unidesk\logs\ for the dated log.
            </span>
          </div>
        )}
        <main className="min-h-0 flex-1 overflow-y-auto px-6 pb-12 pt-5">{children}</main>
      </div>
    </div>
  );
}
