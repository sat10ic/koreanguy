// Real History outcomes data — wired 2026-08-31.
//
// Source of truth: unidesk/run_history_outcomes_export.py, reading the
// research event store at data/market/research/events/date=*/*.parquet
// and emitting every past candidate that fired a VALID detector, joined
// to its measured 10-bar outcome (RESOLVED, PARTIAL, or UNRESOLVED).
//
// This is the same shape the existing synthetic YESTERDAYS_CALLS
// fixture already had, so the History screen renders real rows without
// UI changes. The fixture trio is kept in fixtures.ts, tagged, as a
// fallback / dev convenience -- the History screen is now driven
// primarily by REAL_CALLS (below) for the same static-Vite-bundle
// reasons tonight.ts cites: there is no runtime fetch; the JSON is
// a build-time snapshot.
//
// Honnet\u00e9t\u00e9: netBps is null across every persisted event. The
// net-cost wire bumped OUTCOME_LABELS_VERSION to v4-net-cost but
// candidates.py's attach_outcomes writer looks up adv_value in the
// snapshot dict, which doesn't carry it; the v4-regen completed with
// the v3-shape writer still in place. The UI must render netBps as
// "--" and never pretend the v4-stamp means net_bps is real. The
// gross_bps / r_multiple fields are real and are what the existing
// "note" line cites; the "net" line is omitted from the note when
// netBps is null so the screen doesn't mislead the owner.
import outcomesJson from "./outcomes_2026-08-28.json";
import type { OutcomeCall } from "./fixtures";

interface RawOutcome {
  symbol: string;
  setupType: string;
  date: string;
  entry: number;
  outcome: "hit_target" | "stopped_out" | "unresolved";
  rMultiple: number | null;
  mfePct: number;
  maePct: number;
  stopHit: boolean | null;
  gapThrough: boolean | null;
  netBps: number | null;
  labelVersion: string;
  note: string;
}

export const OUTCOMES_JSON_FILENAME = "outcomes_2026-08-28.json";

interface OutcomesBundle {
  report_session: string;
  outcome_labels_version: string;
  count: number;
  calls: RawOutcome[];
}

export const OUTCOMES_BUNDLE = outcomesJson as unknown as OutcomesBundle;

// Same shape as the synthetic OutcomeCall -- the History screen
// already renders this. Newest first; the screen's own slice picks
// the visible window.
export const REAL_CALLS: OutcomeCall[] = OUTCOMES_BUNDLE.calls
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
  reportSession: OUTCOMES_BUNDLE.report_session,
  outcomeLabelsVersion: OUTCOMES_BUNDLE.outcome_labels_version,
  count: OUTCOMES_BUNDLE.count,
  // netBps coverage: how many calls have a real net-of-cost number.
  // The current archive has 0/863,771 -- this is the indicator the
  // History screen will surface to the owner instead of pretending
  // the field exists. The note string in the render code branches
  // on this same value.
  netBpsCoverage: OUTCOMES_BUNDLE.calls.filter((c) => c.netBps !== null).length,
  // Distinct symbols that produced at least one VALID-detector event
  // in the report window.
  symbolsCovered: new Set(OUTCOMES_BUNDLE.calls.map((c) => c.symbol)).size,
};
