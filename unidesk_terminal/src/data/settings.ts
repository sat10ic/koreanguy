// Real config / detector-trust facts for the Settings screen —
// wired 2026-08-30 (UI_BACKEND_INTEGRATION_PLAN.md row 6, "Settings").
//
// Source of truth: unidesk/run_settings_export.py, which reads the frozen
// committed config (unidesk/config/costs.yaml) and the backend's code
// constants (costs.py, labels.py, event_store.py, trust.py, gates.py,
// report.py) and emits a settings_<report-session>.json as a committed
// build-time snapshot (same convention as tonight_<date>.json /
// stock_history_<date>.json — a static Vite bundle, no runtime fetch).
//
// Every field below is read off the JSON, never typed in by hand, so this
// screen cannot drift from what the backend actually runs.
import settingsJson from "./settings_2026-08-28.json";

export interface DetectorTrust {
  status: string;
  reason: string;
  version: string;
  rankable: boolean;
}

export interface DetectorFacts {
  name: string;
  title: string;
  trust: DetectorTrust | null;
}

export interface SettingsFacts {
  reportSession: string;
  generatedAt: string;
  costsVersion: string;
  costAssumptionsBps: Record<string, number | string>;
  outcomeLabelsVersion: string;
  researchSchemaVersion: string;
  minPriceRs: number;
  minAvgTurnoverCr: number;
  excludeEtf: boolean;
  detectorTrustVersion: string;
  detectors: DetectorFacts[];
}

interface RawSettings {
  report_session: string;
  generated_at: string;
  costs: { version: string; assumptions_bps: Record<string, number | string> };
  labels: { outcome_labels_version: string };
  research: { schema_version: string };
  universe_gates: { min_price_rs: number; min_avg_turnover_cr: number; exclude_etf: boolean };
  detector_trust_version: string;
  detectors: DetectorFacts[];
}

const RAW = settingsJson as unknown as RawSettings;

export const SETTINGS: SettingsFacts = {
  reportSession: RAW.report_session,
  generatedAt: RAW.generated_at,
  costsVersion: RAW.costs.version,
  costAssumptionsBps: RAW.costs.assumptions_bps,
  outcomeLabelsVersion: RAW.labels.outcome_labels_version,
  researchSchemaVersion: RAW.research.schema_version,
  minPriceRs: RAW.universe_gates.min_price_rs,
  minAvgTurnoverCr: RAW.universe_gates.min_avg_turnover_cr,
  excludeEtf: RAW.universe_gates.exclude_etf,
  detectorTrustVersion: RAW.detector_trust_version,
  detectors: RAW.detectors,
};