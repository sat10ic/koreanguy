import { useState } from "react";
import { CalendarClock, Moon, Search, Sun } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useMode } from "../../lib/ModeContext";
import { useReport } from "../../lib/useReport";
import { useTheme } from "../../lib/ThemeContext";
import { RunPipeline } from "./RunPipeline";

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

/** A-8 (audit S1): "how far behind the MARKET is this report" — counted in
 *  weekday sessions after the report's session, up to and including today.
 *  Weekday approximation only (NSE holidays can make it one day pessimistic,
 *  which is the safe direction); labelled as approximate in the tooltip. The
 *  evening of the report's own completed session counts 0 — the original
 *  false-"stale"-at-night bug (UX_PANEL_AUDIT) stays fixed because the
 *  question is distance behind the market, never "is the timestamp today".
 *  The old `sessionDate < newestBundled` test could NEVER fire on the newest
 *  bundle, so a desk weeks behind the market showed no warning at all. */
export function sessionsBehind(sessionDate: string, now: Date = new Date()): number {
  const [y, m, d] = sessionDate.split("-").map(Number);
  if (!y || !m || !d) return 0;
  const session = new Date(y, m - 1, d);
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  let n = 0;
  for (const cur = new Date(session); cur < today; cur.setDate(cur.getDate() + 1)) {
    const wd = cur.getDay();
    if (wd !== 0 && wd !== 6) n++;
  }
  return n;
}

export function TopBar({ mode, onModeChange, breadcrumb }: TopBarProps) {
  const { theme, setTheme } = useTheme();
  const { activeReport, availableSessions, setActiveReport } = useMode();
  const report = useReport();
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const sessionDate = report.session_date ?? activeReport;
  // A-8: a permanent, truthful AGE — rendered always, escalated past one
  // session with the action that fixes it.
  const behind = sessionsBehind(sessionDate);
  const ageText = behind <= 0 ? "current" : `${behind} session${behind === 1 ? "" : "s"} behind`;

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

      <div className="flex items-center gap-1.5 rounded-btn border border-subtle px-2 py-1 text-caption text-ink-secondary"
        title={`Report session ${sessionDate}. Age is measured in weekday sessions behind today (weekday approximation — an NSE holiday can read one session behind; that is the safe direction).${behind > 1 ? " Fix: run the nightly refresh (unidesk\\run_desk_refresh.py or the Run button)." : ""}`}>
        <CalendarClock size={12} className="text-ink-tertiary" aria-hidden />
        <span className="font-mono-num tracking-wide">{formatDate(sessionDate)}</span>
        {behind <= 0 ? (
          <span className="text-positive">· {ageText}</span>
        ) : (
          <span className={behind > 1 ? "font-medium text-warning" : "text-warning"}
            title={behind > 1 ? "run the nightly refresh" : "expected one-session EOD lag"}>
            · {ageText}{behind > 1 ? " — run the nightly refresh" : ""}
          </span>
        )}
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

      {/* E-4.1: the real run control — the old one was a <span> with no
          onClick printing a shell command (PART E-REF). */}
      <RunPipeline />

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
