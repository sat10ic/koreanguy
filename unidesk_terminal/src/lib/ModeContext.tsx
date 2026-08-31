import { createContext, useContext, useState, type ReactNode } from "react";
import { DEFAULT_REPORT, getAvailableSessions } from "../data/reportRegistry";

export type Mode = "beginner" | "pro";

export interface ModeContextValue {
  mode: Mode;
  setMode: (mode: Mode) => void;
  activeReport: string;
  setActiveReport: (session: string) => void;
  availableSessions: string[];
}

const ModeContext = createContext<ModeContextValue>({
  mode: "beginner", setMode: () => {},
  activeReport: DEFAULT_REPORT.sessionDate, setActiveReport: () => {},
  availableSessions: [],
});

export function ModeProvider({ children }: { children: ReactNode }) {
  const [mode, setMode] = useState<Mode>("beginner");
  const [activeReport, setActiveReport] = useState(DEFAULT_REPORT.sessionDate);
  const availableSessions = getAvailableSessions();
  return (
    <ModeContext.Provider value={{ mode, setMode, activeReport, setActiveReport, availableSessions }}>
      {children}
    </ModeContext.Provider>
  );
}

export function useMode(): ModeContextValue {
  return useContext(ModeContext);
}