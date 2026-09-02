// Real History outcomes data — auto-discovers the newest bundled
// outcomes_<date>.json. Source of truth:
// unidesk/run_history_outcomes_export.py, reading the research event store
// and emitting every past candidate that fired a VALID detector, joined to
// its measured 10-bar outcome. Static build-time snapshot (no runtime
// fetch). netBps coverage is surfaced honestly (see OUTCOMES_META).
const modules = import.meta.glob("./outcomes_*.json", { eager: true }) as Record<string, unknown>;

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

export const REAL_CALLS: OutcomeCall[] = (OUTCOMES_BUNDLE?.calls ?? [])
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

export const OUTCOMES_META = {
  reportSession: OUTCOMES_BUNDLE?.report_session ?? "none",
  outcomeLabelsVersion: OUTCOMES_BUNDLE?.outcome_labels_version ?? "none",
  count: OUTCOMES_BUNDLE?.count ?? 0,
  netBpsCoverage: (OUTCOMES_BUNDLE?.calls ?? []).filter((c) => c.netBps !== null).length,
  symbolsCovered: new Set((OUTCOMES_BUNDLE?.calls ?? []).map((c) => c.symbol)).size,
};
