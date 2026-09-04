import { Briefcase, ChevronLeft, FlaskConical, History, LayoutDashboard, Radar, Settings as SettingsIcon, Sparkles } from "lucide-react";
import { NavLink } from "react-router-dom";
import { atLeast, useMode } from "../../lib/ModeContext";

/*
  Sidebar (spec §4.2): expanded 208px / collapsed 64px, fixed left, full
  height, subtle right divider — NOT a floating card. Text labels are
  primary; icons secondary. Collapse state persists locally (§4.2).
  Stock Detail is contextual (§3.1) and deliberately absent from primary nav.
*/

interface NavItem {
  to: string;
  label: string;
  icon: typeof Radar;
  end?: boolean;
  hint?: string;
  lab?: boolean;  // §10: Lab surface — shown only when the mode ladder reaches lab
}

const NAV: NavItem[] = [
  { to: "/", label: "Tonight", icon: LayoutDashboard, end: true, hint: "What kind of market is this?" },
  { to: "/market", label: "Market", icon: Radar, hint: "Where is participation strengthening?" },
  { to: "/candidates", label: "Candidates", icon: Radar, hint: "Which candidates stand out cross-sectionally?" },
  { to: "/desk", label: "Desk", icon: Briefcase, hint: "Veto · positions · exits" },
  { to: "/history", label: "History", icon: History, hint: "What did the calls do?" },
  { to: "/research", label: "Research", icon: FlaskConical, hint: "What evidence backs the scanner?" },
  { to: "/events", label: "Events", icon: Sparkles, hint: "Lab — event-normalised IPO overlays (unvalidated)", lab: true },
  { to: "/settings", label: "Settings", icon: SettingsIcon },
];

export function Sidebar({ collapsed, onToggle }: { collapsed: boolean; onToggle: () => void }) {
  const { mode } = useMode();
  const nav = NAV.filter((item) => !item.lab || atLeast(mode, "lab"));
  return (
    <nav
      className="flex h-full shrink-0 flex-col border-r border-subtle bg-surface-0 transition-[width] duration-200"
      style={{ width: collapsed ? 64 : 208 }}
      aria-label="Primary"
    >
      <div className="flex h-14 items-center gap-2.5 border-b border-subtle px-4">
        <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-btn border border-accent-border bg-accent-bg text-caption font-bold text-accent-strong">
          U
        </span>
        {!collapsed && (
          <span className="truncate text-t3 font-semibold tracking-tight text-ink-primary">Momentum OS</span>
        )}
      </div>

      <div className="flex flex-1 flex-col gap-0.5 px-2 py-3">
        {nav.map(({ to, label, icon: Icon, end, hint }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            title={collapsed ? label : hint}
            className={({ isActive }) =>
              `group relative flex items-center gap-3 rounded-btn px-3 py-2 text-t3 font-medium transition-colors duration-150 ${
                isActive
                  ? "bg-surface-2 text-ink-primary"
                  : "text-ink-secondary hover:bg-surface-2 hover:text-ink-primary"
              }`}
          >
            {({ isActive }) => (
              <>
                {isActive && (
                  <span className="absolute left-0 top-1/2 h-4 w-0.5 -translate-y-1/2 rounded-full bg-accent" />
                )}
                <Icon size={16} strokeWidth={2} className={isActive ? "text-accent" : "text-ink-tertiary"} />
                {!collapsed && <span className="truncate">{label}</span>}
              </>
            )}
          </NavLink>
        ))}
      </div>

      <button
        onClick={onToggle}
        aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        className="flex h-10 items-center gap-3 border-t border-subtle px-5 text-ink-tertiary transition-colors hover:text-ink-secondary"
      >
        <ChevronLeft size={14} className={`transition-transform duration-200 ${collapsed ? "rotate-180" : ""}`} />
        {!collapsed && <span className="text-caption">Collapse</span>}
      </button>
    </nav>
  );
}
