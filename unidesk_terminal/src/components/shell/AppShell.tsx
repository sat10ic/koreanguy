import type { ReactNode } from "react";
import { useMode } from "../../lib/ModeContext";
import { LeftRail } from "./LeftRail";
import { TopBar } from "./TopBar";

interface AppShellProps {
  breadcrumb: string[];
  children: ReactNode;
}

export function AppShell({ breadcrumb, children }: AppShellProps) {
  const { mode, setMode } = useMode();

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-surface-0 text-ink-primary">
      <LeftRail />
      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar mode={mode} onModeChange={setMode} breadcrumb={breadcrumb} />
        <main className="min-h-0 flex-1 overflow-y-auto">{children}</main>
      </div>
    </div>
  );
}
