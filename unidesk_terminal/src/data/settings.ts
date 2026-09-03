// Real config / detector-trust facts for the Settings screen.
// Auto-discovers the newest bundled settings_<date>.json (source:
// unidesk/run_settings_export.py). Every field is read off the JSON, never
// typed in by hand, so the screen cannot drift from what the backend runs.
const modules = import.meta.glob("./settings_*.json", { eager: true, import: "default" }) as Record<string, unknown>; // namespace-safe: see stockHistory.ts note

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

// C-2 (audit S3-3): Object.values() of the glob follows path order, which
// put the OLDEST settings file first the moment a second landed. Sort
// newest-first by report_session, same convention as reportRegistry.ts /
// outcomes.ts, so the newest export is always the one displayed.
const BUNDLES = Object.values(modules)
  .map((json) => json as unknown as RawSettings)
  .sort((a, b) => b.report_session.localeCompare(a.report_session));
const RAW = BUNDLES[0] ?? {
  report_session: "none",
  generated_at: "none",
  costs: { version: "none", assumptions_bps: {} },
  labels: { outcome_labels_version: "none" },
  research: { schema_version: "none" },
  universe_gates: { min_price_rs: 0, min_avg_turnover_cr: 0, exclude_etf: true },
  detector_trust_version: "none",
  detectors: [],
};

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

/** E-3: rehydrate SETTINGS in place from the desk server's newest export. */
export function hydrateSettings(raw: RawSettings): void {
  Object.assign(SETTINGS, {
    reportSession: raw.report_session,
    generatedAt: raw.generated_at,
    costsVersion: raw.costs.version,
    costAssumptionsBps: raw.costs.assumptions_bps,
    outcomeLabelsVersion: raw.labels.outcome_labels_version,
    researchSchemaVersion: raw.research.schema_version,
    minPriceRs: raw.universe_gates.min_price_rs,
    minAvgTurnoverCr: raw.universe_gates.min_avg_turnover_cr,
    excludeEtf: raw.universe_gates.exclude_etf,
    detectorTrustVersion: raw.detector_trust_version,
    detectors: raw.detectors,
  });
}
