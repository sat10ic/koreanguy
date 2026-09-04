import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { DEFAULT_REPORT, getAvailableSessions } from "../data/reportRegistry";
import { subscribeDeskData } from "../data/deskData";

// §10.2: a monotonic ladder, not a second axis — beginner ⊂ pro ⊂ lab.
// `lab` is pro vocabulary PLUS unvalidated surfaces (Events screen,
// experimental fields). Never the default; the AppShell banners it loudly.
export type Mode = "beginner" | "pro" | "lab";

const MODE_ORDER: Mode[] = ["beginner", "pro", "lab"];

export function atLeast(mode: Mode, floor: Mode): boolean {
  return MODE_ORDER.indexOf(mode) >= MODE_ORDER.indexOf(floor);
}

function loadPersistedMode(): Mode {
  try {
    const raw = localStorage.getItem("unidesk.mode") as Mode | null;
    return raw && (MODE_ORDER as string[]).includes(raw) ? raw : "beginner";
  } catch {
    return "beginner";
  }
}

export interface ModeContextValue {
  mode: Mode;
  setMode: (mode: Mode) => void;
  activeReport: string;
  setActiveReport: (session: string) => void;
  availableSessions: string[];
  /** E-4: bumped whenever the desk data re-hydrates (Run finished), so every
   *  screen re-reads the data modules without a page reload. */
  dataVersion: number;
}

const ModeContext = createContext<ModeContextValue>({
  mode: "beginner", setMode: () => {},
  activeReport: DEFAULT_REPORT.sessionDate, setActiveReport: () => {},
  availableSessions: [],
  dataVersion: 0,
});

export function ModeProvider({ children }: { children: ReactNode }) {
  const [mode, setMode] = useState<Mode>(loadPersistedMode);
  const [activeReport, setActiveReport] = useState(DEFAULT_REPORT.sessionDate);
  const [dataVersion, setDataVersion] = useState(0);
  // E-3/E-4: desk data re-hydration (boot fetch + post-Run refetch) bumps the
  // version so every screen re-reads the hydrated modules — no reload.
  useEffect(() => subscribeDeskData(() => {
    setDataVersion((v) => v + 1);
    setActiveReport((cur) => (getAvailableSessions().includes(cur) ? cur : getAvailableSessions()[0] ?? cur));
  }), []);
  const setModePersisted = useCallback((m: Mode) => {
    setMode(m);
    try { localStorage.setItem("unidesk.mode", m); } catch { /* private mode */ }
  }, []);
  const availableSessions = getAvailableSessions();
  const value = { mode, setMode: setModePersisted, activeReport, setActiveReport, availableSessions, dataVersion };
  return (
    <ModeContext.Provider value={value}>
      {children}
    </ModeContext.Provider>
  );
}

export function useMode(): ModeContextValue {
  return useContext(ModeContext);
}
