// Report registry — every bundled tonight_*.json snapshot via Vite's glob
// import (the OFFLINE fallback), hydrated in place from the desk server when
// it is reachable (E-3). Landing a new report file in src/data is enough for
// the fallback; the server path serves whatever is on disk.
const modules = import.meta.glob("./tonight_*.json", { eager: true, import: "default" }) as Record<string, unknown>; // namespace-safe: see stockHistory.ts note

export interface ReportEntry {
  sessionDate: string;
  json: Record<string, unknown>;
}

function sessionDateOf(path: string, json: Record<string, unknown>): string {
  const fromJson = typeof json.session_date === "string" ? json.session_date : null;
  return fromJson ?? path.replace("./tonight_", "").replace(".json", "");
}

function buildRegistry(source: Record<string, unknown>): ReportEntry[] {
  return Object.entries(source)
    .map(([path, json]) => {
      const j = json as Record<string, unknown>;
      return { sessionDate: sessionDateOf(path, j), json: j };
    })
    .sort((a, b) => b.sessionDate.localeCompare(a.sessionDate)); // newest first
}

// Mutated in place by applyServerSessions — ModeContext and every screen read
// through these bindings at render time, so hydration needs no re-import.
const _registry: ReportEntry[] = buildRegistry(modules);

/** The default entry. Kept as a stable object reference whose CONTENTS track
 *  the newest known session (bundled or server). */
export const DEFAULT_REPORT: ReportEntry = _registry[0] ?? { sessionDate: "", json: {} };

/** E-3: replace registry contents with server-served sessions (newest first). */
export function applyServerSessions(entries: ReportEntry[]): void {
  if (entries.length === 0) return;
  _registry.length = 0;
  _registry.push(...entries);
  const newest = _registry[0];
  DEFAULT_REPORT.sessionDate = newest.sessionDate;
  DEFAULT_REPORT.json = newest.json;
}

export function getReport(sessionDate: string): ReportEntry | undefined {
  return _registry.find((r) => r.sessionDate === sessionDate);
}

export function getAvailableSessions(): string[] {
  return _registry.map((r) => r.sessionDate);
}

export function hasMultipleReports(): boolean {
  return _registry.length > 1;
}

/** Newest session among the BUNDLED snapshots — the OFFLINE banner names it. */
export function bundledNewestSession(): string {
  return buildRegistry(modules)[0]?.sessionDate ?? "";
}
