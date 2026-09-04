// G-02/G-04 coherence: every screen and widget reads THE selected report
// through this hook. No widget imports a static report for display data.
import { useMode } from "./ModeContext";
import { getReport } from "../data/reportRegistry";
import { asReport, type TonightReport } from "../data/tonight";

export function useReport(): TonightReport {
  const { activeReport } = useMode();
  const entry = getReport(activeReport);
  return asReport(entry?.json ?? {});
}
