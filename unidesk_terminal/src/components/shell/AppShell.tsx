import { useState, type ReactNode } from "react";
import { useMode } from "../../lib/ModeContext";
import { Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";

/*
  App shell (spec SS4): fixed sidebar (208/64, persisted) + 56px top bar +
  12-column-ready content area with spec paddings (inline 24-32, top 20-24).
*/

export function AppShell({ breadcrumb, children }: { breadcrumb: string[]; children: ReactNode }) {
  const { mode, setMode } = useMode();
  const [collapsed, setCollapsed] = useState<boolean>(() => localStorage.getItem("unidesk.sidebarCollapsed") === "1");

  function toggle() {
    setCollapsed((v) => {
      localStorage.setItem("unidesk.sidebarCollapsed", v ? "0" : "1");
      return !v;
    });
  }

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-surface-0 text-ink-primary">
      <Sidebar collapsed={collapsed} onToggle={toggle} />
      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar mode={mode} onModeChange={setMode} breadcrumb={breadcrumb} />
        <main className="min-h-0 flex-1 overflow-y-auto px-6 pb-12 pt-5">{children}</main>
      </div>
    </div>
  );
}
