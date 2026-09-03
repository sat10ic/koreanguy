// E-3: server-first data layer. On boot (and after a successful Run), this
// module fetches everything the desk renders from the localhost server and
// hydrates the data modules IN PLACE, so no screen changes and no screen
// ever imports fetch logic. If the server is unreachable, the bundled
// snapshots remain — with a LOUD OFFLINE banner naming the bundled session
// (house rule 1: never a silent substitution). Static-bundle fallback stays
// fully functional with no server at all.
import {
  applyServerSessions, bundledNewestSession, type ReportEntry,
} from "./reportRegistry";
import { hydrateOutcomes } from "./outcomes";
import { hydrateSettings } from "./settings";
import { hydrateCoverage } from "./researchCoverage";
import { hydrateStockHistory } from "./stockHistory";
import { hydrateRegimeHistory } from "../lib/regimeHistory";
import { hydrateSectors } from "../lib/sectors";
import { hydrateMetricHistory } from "../lib/metricHistory";
import { hydrateDeskChecks } from "../components/widgets/HonestyFooter";

export type DeskSource = "server" | "bundled";

export interface DeskHealth {
  ok: boolean;
  newest_session_on_disk: string | null;
  newest_derived_session: string | null;
  reports_dir: string;
  job_running: boolean;
  last_scheduled_run?: {
    status: string; exit_code: number; failed_stage?: string | null;
    session?: string | null; finished_at: string; log_file?: string;
  } | null;
}

let _source: DeskSource = "bundled";
let _health: DeskHealth | null = null;
const _listeners = new Set<() => void>();

export function deskSource(): DeskSource {
  return _source;
}

export function deskHealth(): DeskHealth | null {
  return _health;
}

/** Subscribe to data changes (useSyncExternalStore-friendly). */
export function subscribeDeskData(fn: () => void): () => void {
  _listeners.add(fn);
  return () => _listeners.delete(fn);
}

function emit(): void {
  for (const fn of _listeners) fn();
}

async function getJson<T>(url: string, timeoutMs = 8000): Promise<T> {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), timeoutMs);
  try {
    const res = await fetch(url, { signal: ctrl.signal });
    if (!res.ok) throw new Error(`${url} -> HTTP ${res.status}`);
    return await res.json() as T;
  } finally {
    clearTimeout(timer);
  }
}

/** Hydrate every data domain from the server. Any failure leaves the bundled
 *  data untouched-and-disclosed (source stays "bundled"). */
export async function refreshDeskData(): Promise<DeskSource> {
  try {
    const health = await getJson<DeskHealth>("/api/health", 4000);
    const { sessions } = await getJson<{ sessions: string[] }>("/api/reports");
    const newest = sessions.slice(0, 3); // match the bundle's 2-3 snapshot window
    const reportEntries: ReportEntry[] = [];
    const histories: [string, Record<string, unknown>][] = [];
    await Promise.all(newest.map(async (s) => {
      reportEntries.push({
        sessionDate: s,
        json: await getJson<Record<string, unknown>>(`/api/report/${s}`),
      });
      histories.push([s, await getJson<Record<string, unknown>>(`/api/stock-history/${s}`)]);
    }));
    const outcomes = await getJson<{ session: string; data: Parameters<typeof hydrateOutcomes>[0] }>("/api/outcomes");
    const settings = await getJson<{ data: Parameters<typeof hydrateSettings>[0] }>("/api/settings");
    const coverage = await getJson<{ data: Parameters<typeof hydrateCoverage>[0] }>("/api/coverage");
    const deskChecks = await getJson<{ checks: never[] }>("/api/desk-checks");
    const regimeHistory = await getJson<Parameters<typeof hydrateRegimeHistory>[0]>("/api/regime-history");
    const metricHistory = await getJson<Parameters<typeof hydrateMetricHistory>[0]>("/api/metric-history");
    const sectorMapping = await getJson<Parameters<typeof hydrateSectors>[0]>("/api/sector-mapping");

    reportEntries.sort((a, b) => b.sessionDate.localeCompare(a.sessionDate));
    applyServerSessions(reportEntries);
    for (const [session, symbols] of histories) {
      hydrateStockHistory(session, symbols as never);
    }
    hydrateOutcomes(outcomes.data);
    hydrateSettings(settings.data);
    hydrateCoverage(coverage.data);
    hydrateDeskChecks(deskChecks);
    hydrateRegimeHistory(regimeHistory);
    hydrateMetricHistory(metricHistory);
    hydrateSectors(sectorMapping);

    _source = "server";
    _health = health;
  } catch {
    // Server unreachable (or a partial failure): keep bundled data, say so.
    _source = "bundled";
    _health = null;
  }
  emit();
  return _source;
}

/** The session the OFFLINE banner must name when no server is reachable. */
export function bundledSessionName(): string {
  return bundledNewestSession();
}

let _started = false;

/** Boot-time hydration. Idempotent; resolves after the first attempt. */
export async function initDeskData(): Promise<DeskSource> {
  if (_started) return _source;
  _started = true;
  return refreshDeskData();
}
