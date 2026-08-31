// Report registry — statically imports all available tonight_*.json snapshots.
// Add a new import+entry when landing a new report snapshot.
import tonight0703 from "./tonight_2026-07-03.json";
import tonight0828 from "./tonight_2026-08-28.json";

export interface ReportEntry {
  sessionDate: string;
  json: Record<string, unknown>;
}

const _registry: ReportEntry[] = [
  { sessionDate: "2026-07-03", json: tonight0703 as Record<string, unknown> },
  { sessionDate: "2026-08-28", json: tonight0828 as Record<string, unknown> },
].sort((a, b) => b.sessionDate.localeCompare(a.sessionDate)); // newest first

// Default to the newest report
export const DEFAULT_REPORT = _registry[0];

export function getReport(sessionDate: string): ReportEntry | undefined {
  return _registry.find((r) => r.sessionDate === sessionDate);
}

export function getAvailableSessions(): string[] {
  return _registry.map((r) => r.sessionDate);
}

export function hasMultipleReports(): boolean {
  return _registry.length > 1;
}