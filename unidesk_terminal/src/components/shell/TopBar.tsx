import { Bell, CalendarClock, Command, Search } from "lucide-react";
import { useState } from "react";
import { REAL_SESSION } from "../../data/tonight";

interface TopBarProps {
  mode: "beginner" | "pro";
  onModeChange: (mode: "beginner" | "pro") => void;
  breadcrumb: string[];
}

export function TopBar({ mode, onModeChange, breadcrumb }: TopBarProps) {
  const [alertsOpen, setAlertsOpen] = useState(false);

  return (
    <header className="flex h-12 shrink-0 items-center gap-3 border-b border-border-subtle bg-surface-0 px-4">
      <div className="flex min-w-0 items-center gap-1.5 text-caption text-ink-tertiary">
        {breadcrumb.map((b, i) => (
          <span key={b} className="flex items-center gap-1.5">
            {i > 0 && <span className="text-ink-muted">/</span>}
            <span className={i === breadcrumb.length - 1 ? "font-medium text-ink-secondary" : ""}>{b}</span>
          </span>
        ))}
      </div>

      <div className="mx-auto flex w-full max-w-sm items-center gap-2 rounded-chip border border-border bg-surface-input px-2.5 py-1.5 text-ink-tertiary transition-colors duration-150 ease-out focus-within:border-border-focus">
        <Search size={14} aria-hidden />
        <input
          aria-label="Search symbol, setup, or sector"
          placeholder="Search symbol, setup, sector..."
          className="w-full bg-transparent text-caption text-ink-primary outline-none placeholder:text-ink-muted"
        />
        <span className="flex items-center gap-0.5 rounded-[4px] border border-border-subtle px-1 py-0.5 text-[10px] text-ink-muted">
          <Command size={10} />K
        </span>
      </div>

      <div className="flex items-center gap-3">
        <div
          className="flex items-center gap-1.5 rounded-chip border border-border-subtle px-2 py-1 text-caption text-ink-tertiary"
          title="Every screen reflects this session's report — the desk never silently shows a newer date than the data supports"
        >
          <CalendarClock size={13} className="text-accent" aria-hidden />
          <span>As of {REAL_SESSION.date}</span>
        </div>

        <div role="group" aria-label="Display mode" className="flex items-center rounded-chip border border-border-subtle p-0.5 text-caption">
          {(["beginner", "pro"] as const).map((m) => (
            <button
              key={m}
              onClick={() => onModeChange(m)}
              aria-pressed={mode === m}
              className={`min-h-[28px] rounded-[4px] px-2.5 py-1 font-medium capitalize transition-colors duration-150 ease-out ${
                mode === m ? "bg-accent-bg text-accent-strong" : "text-ink-tertiary hover:text-ink-secondary"
              }`}
            >
              {m}
            </button>
          ))}
        </div>

        <button
          onClick={() => setAlertsOpen((v) => !v)}
          aria-label="Alerts"
          aria-pressed={alertsOpen}
          className={`relative flex h-10 w-10 items-center justify-center rounded-chip border transition-colors duration-150 ease-out ${
            alertsOpen ? "border-border-strong bg-surface-2" : "border-border-subtle text-ink-tertiary hover:text-ink-secondary"
          }`}
        >
          <Bell size={14} aria-hidden />
          <span className="absolute right-2 top-2 h-1.5 w-1.5 rounded-full bg-danger" aria-hidden />
        </button>
      </div>
    </header>
  );
}
