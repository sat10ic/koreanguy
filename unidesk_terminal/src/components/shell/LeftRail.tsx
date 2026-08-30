import { FlaskConical, History, LayoutGrid, Moon, Radar, Settings } from "lucide-react";
import { NavLink } from "react-router-dom";

// V2 nav (plan/UNIFIED_DESK_UI_UX_MANUAL_V2.md §2). Market/Watchlist/Flow/
// Traders/Journal are explicitly deferred or removed in V2 — see manual §10
// "Screens not built (and why)" — not reproduced here as dead nav entries.
interface NavItem {
  to: string;
  label: string;
  icon: typeof Moon;
  end?: boolean;
}

const NAV: NavItem[] = [
  { to: "/", label: "Tonight", icon: Moon, end: true },
  { to: "/candidates", label: "Candidates", icon: Radar },
  { to: "/stock", label: "Stock", icon: LayoutGrid },
  { to: "/history", label: "History", icon: History },
  { to: "/research", label: "Research", icon: FlaskConical },
  { to: "/settings", label: "Settings", icon: Settings },
];

export function LeftRail() {
  return (
    <nav className="flex h-full w-[68px] shrink-0 flex-col items-center gap-1 border-r border-border-subtle bg-surface-rail py-3">
      <div className="mb-3 flex h-8 w-8 items-center justify-center rounded-chip border border-accent-border bg-accent-bg">
        <span className="text-caption font-bold text-accent-strong">U</span>
      </div>
      {NAV.map(({ to, label, icon: Icon, end }) => (
        <NavLink
          key={to}
          to={to}
          end={end}
          aria-label={label}
          className={({ isActive }) =>
            `group relative flex w-14 flex-col items-center gap-1 rounded-chip px-1 py-2 transition-colors duration-150 ease-out ${
              isActive ? "text-accent-strong" : "text-ink-tertiary hover:text-ink-secondary"
            }`
          }
        >
          {({ isActive }) => (
            <>
              {isActive && (
                <span className="absolute left-0 top-1/2 h-4 w-0.5 -translate-y-1/2 rounded-full bg-accent" />
              )}
              <span
                className={`flex h-8 w-8 items-center justify-center rounded-chip transition-colors duration-150 ease-out ${
                  isActive ? "bg-accent-bg" : "group-hover:bg-surface-2"
                }`}
              >
                <Icon size={17} strokeWidth={2} />
              </span>
              <span className="text-[10px] font-medium leading-none tracking-tight">{label}</span>
            </>
          )}
        </NavLink>
      ))}
    </nav>
  );
}
