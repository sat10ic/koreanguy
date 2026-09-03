import { useState } from "react";
import { CalendarClock, Moon, Search, Sun } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useMode } from "../../lib/ModeContext";
import { useReport } from "../../lib/useReport";
import { useTheme } from "../../lib/ThemeContext";

/*
  Top bar (spec SS43): 56px. Left-right: breadcrumb / session date /
  global search / Beginner-Pro toggle / data status. The session
  date appears HERE and nowhere else on the page.
  C-7: the search now navigates to /stock/<SYMBOL> on Enter (the route
  exists and renders any candidate symbol). The alerts BELL was deleted —
  no alerts subsystem exists anywhere in this build, and a control that
  looks interactive but does nothing is worse than an absent one.
*/

interface TopBarProps {
  mode: "beginner" | "pro";
  onModeChange: (mode: "beginner" | "pro") => void;
  breadcrumb: string[];
}

const MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"];

function formatDate(iso: string): string {
  const [y, m, d] = iso.split("-").map(Number);
  if (!y || !m || !d) return iso;
  return `${String(d).padStart(2, "0")} ${MONTHS[m - 1]} ${y}`;
}

export function TopBar({ mode, onModeChange, breadcrumb }: TopBarProps) {
  const { theme, setTheme } = useTheme();
  const { activeReport, availableSessions, setActiveReport } = useMode();
  const report = useReport();
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const sessionDate = report.session_date ?? activeReport;
  // "stale" = OLDER than the newest bundled session -- not "not today":
  // at 2am the latest completed session is yesterday's, and it is current.
  const newest = availableSessions.length ? availableSessions[0] : sessionDate;
  const stale = sessionDate < newest;

  function submitSearch() {
    const sym = query.trim().toUpperCase();
    if (!sym) return;
    navigate(`/stock/${encodeURIComponent(sym)}`);
    setQuery("");
  }

  return (
    <header className="flex h-14 shrink-0 items-center gap-4 border-b border-subtle bg-surface-0 px-6">
      <div className="flex min-w-0 items-center gap-1.5 text-caption text-ink-tertiary">
        {breadcrumb.map((b, i) => (
          <span key={b} className="flex items-center gap-1.5">
            {i > 0 && <span className="text-ink-muted">/</span>}
            <span className={i === breadcrumb.length - 1 ? "font-semibold text-ink-secondary" : ""}>{b}</span>
          </span>
        ))}
      </div>

      <div className="flex items-center gap-1.5 rounded-btn border border-subtle px-2 py-1 text-caption text-ink-secondary" title="Selected report session - follows the picker">
        <CalendarClock size={12} className="text-ink-tertiary" aria-hidden />
        <span className="font-mono-num tracking-wide">{formatDate(sessionDate)}</span>
        {stale && <span className="text-warning" title={`Older than the newest bundled session (${newest})`}>- stale</span>}
      </div>

      {availableSessions.length > 1 && (
        <div className="flex items-center gap-0.5 rounded-btn border border-subtle p-0.5">
          {availableSessions.map((s) => (
            <button
              key={s}
              onClick={() => setActiveReport(s)}
              aria-pressed={s === activeReport}
              className={"rounded-[5px] px-2 py-0.5 font-mono-num text-[11px] font-medium transition-colors duration-150 " +
                (s === activeReport ? "bg-accent-bg text-accent-strong" : "text-ink-tertiary hover:text-ink-secondary")}
            >
              {s.slice(5)}
            </button>
          ))}
        </div>
      )}

      <div className="mx-auto flex w-full max-w-sm items-center gap-2 rounded-btn border border-subtle bg-surface-input px-2.5 py-1.5 text-ink-tertiary transition-colors duration-150 focus-within:border-border-focus">
        <Search size={14} aria-hidden />
        <input
          aria-label="Go to a stock page by symbol"
          placeholder="Go to symbol (press Enter)…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter") submitSearch(); }}
          className="w-full bg-transparent text-t3 text-ink-primary outline-none placeholder:text-ink-muted"
        />
      </div>

      <div role="group" aria-label="Display mode" className="flex items-center rounded-btn border border-subtle p-0.5 text-caption">
        {(["beginner", "pro"] as const).map((m) => (
          <button
            key={m}
            onClick={() => onModeChange(m)}
            aria-pressed={mode === m}
            className={"rounded-[5px] px-2.5 py-1 font-medium capitalize transition-colors duration-150 " +
              (mode === m ? "bg-accent-bg text-accent-strong" : "text-ink-tertiary hover:text-ink-secondary")}
          >
            {m}
          </button>
        ))}
      </div>

      <button
        onClick={() => setTheme(theme === "light" ? "dark" : "light")}
        aria-label={`Switch to ${theme === "light" ? "dark" : "light"} theme`}
        title={`Switch to ${theme === "light" ? "dark" : "light"} terminal`}
        className="flex h-9 w-9 items-center justify-center rounded-btn border border-subtle text-ink-tertiary transition-colors hover:text-ink-secondary"
      >
        {theme === "light" ? <Moon size={14} /> : <Sun size={14} />}
      </button>
    </header>
  );
}
