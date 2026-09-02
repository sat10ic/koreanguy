// Report registry — auto-discovers every bundled tonight_*.json snapshot
// via Vite's glob import. Landing a new report file in src/data (the
// refresh driver does this) is enough; no code edit needed.
const modules = import.meta.glob("./tonight_*.json", { eager: true }) as Record<string, unknown>;

export interface ReportEntry {
  sessionDate: string;
  json: Record<string, unknown>;
}

function sessionDateOf(path: string, json: Record<string, unknown>): string {
  const fromJson = typeof json.session_date === "string" ? json.session_date : null;
  return fromJson ?? path.replace("./tonight_", "").replace(".json", "");
}

const _registry: ReportEntry[] = Object.entries(modules)
  .map(([path, json]) => {
    const j = json as Record<string, unknown>;
    return { sessionDate: sessionDateOf(path, j), json: j };
  })
  .sort((a, b) => b.sessionDate.localeCompare(a.sessionDate)); // newest first

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
