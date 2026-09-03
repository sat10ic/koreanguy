// Real History outcomes data — auto-discovers the newest bundled
// outcomes_<date>.json. Source of truth:
// unidesk/run_history_outcomes_export.py, reading the research event store
// and emitting every past candidate that fired a VALID detector, joined to
// its measured 10-bar outcome. Static build-time snapshot (no runtime
// fetch). netBps coverage is surfaced honestly (see OUTCOMES_META).
const modules = import.meta.glob("./outcomes_*.json", { eager: true, import: "default" }) as Record<string, unknown>; // namespace-safe: see stockHistory.ts note

interface RawOutcome {
  symbol: string;
  setupType: string;
  date: string;
  entry: number;
  outcome: "hit_target" | "stopped_out" | "open" | "resolved_flat" | "unresolved";
  rMultiple: number | null;
  mfePct: number | null;
  maePct: number | null;
  stopHit: boolean | null;
  gapThrough: boolean | null;
  netBps: number | null;
  labelVersion: string;
  note: string;
}

interface OutcomesBundle {
  report_session: string;
  outcome_labels_version: string;
  count: number;
  calls: RawOutcome[];
}

const BUNDLES = Object.values(modules)
  .map((json) => json as unknown as OutcomesBundle)
  .sort((a, b) => b.report_session.localeCompare(a.report_session));

const OUTCOMES_BUNDLE = BUNDLES[0];

export const OUTCOMES_JSON_FILENAME = OUTCOMES_BUNDLE ? `outcomes_${OUTCOMES_BUNDLE.report_session}.json` : "none";

import type { OutcomeCall } from "./fixtures";

function mapCalls(bundle: OutcomesBundle | undefined): OutcomeCall[] {
  return (bundle?.calls ?? [])
    .map((c) => ({
      symbol: c.symbol,
      setupType: c.setupType as OutcomeCall["setupType"],
      date: c.date,
      entry: c.entry,
      outcome: c.outcome,
      rMultiple: c.rMultiple,
      mfePct: c.mfePct,
      maePct: c.maePct,
      netBps: c.netBps,
      stopHit: c.stopHit,
      gapThrough: c.gapThrough,
      note: c.note,
    }))
    .sort((a, b) => (a.date < b.date ? 1 : a.date > b.date ? -1 : 0));
}

// Mutated in place by hydrateOutcomes (E-3) — History/Research read these at
// render time, so hydration needs no re-import.
export const REAL_CALLS: OutcomeCall[] = mapCalls(OUTCOMES_BUNDLE);

export const OUTCOMES_META = {
  reportSession: OUTCOMES_BUNDLE?.report_session ?? "none",
  outcomeLabelsVersion: OUTCOMES_BUNDLE?.outcome_labels_version ?? "none",
  count: OUTCOMES_BUNDLE?.count ?? 0,
  netBpsCoverage: (OUTCOMES_BUNDLE?.calls ?? []).filter((c) => c.netBps !== null).length,
  symbolsCovered: new Set((OUTCOMES_BUNDLE?.calls ?? []).map((c) => c.symbol)).size,
};

/** E-3: rehydrate from the desk server's newest outcomes export. */
export function hydrateOutcomes(bundle: { report_session: string; outcome_labels_version: string; count: number; calls: RawOutcome[] }): void {
  REAL_CALLS.length = 0;
  REAL_CALLS.push(...mapCalls(bundle as OutcomesBundle));
  Object.assign(OUTCOMES_META, {
    reportSession: bundle.report_session,
    outcomeLabelsVersion: bundle.outcome_labels_version,
    count: bundle.count,
    netBpsCoverage: (bundle.calls ?? []).filter((c) => c.netBps !== null).length,
    symbolsCovered: new Set((bundle.calls ?? []).map((c) => c.symbol)).size,
  });
}
