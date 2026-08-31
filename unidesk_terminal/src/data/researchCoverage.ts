// Real research archive coverage + detector stats for the Research screen —
// wired 2026-08-31 (UI_BACKEND_INTEGRATION_PLAN.md row 5).
//
// Source of truth: unidesk/run_research_coverage_export.py, fast pyarrow
// probe across every event-store partition.
import coverageJson from "./research_coverage_2026-08-28.json";

export interface CoverageFacts {
  partitions: number;
  partitionRange: { oldest: string; newest: string };
  labelVersionHomogeneous: boolean;
  labelVersion: string;
  statusDistribution: Record<string, number>;
  detectorValidHits: Record<string, number>;
  detectors: { name: string; title: string; trust: { status: string; reason: string; rankable: boolean } | null }[];
  negativeFindings: { detector: string; title: string; trust: { status: string; reason: string } }[];
}

interface RawResearch {
  partitions: number;
  partition_range: { oldest: string; newest: string };
  label_version_homogeneous: boolean;
  label_version: string;
  status_distribution: Record<string, number>;
  detector_valid_hits: Record<string, number>;
  detectors: { name: string; title: string; trust: { status: string; reason: string; rankable: boolean } | null }[];
  negative_findings: { detector: string; title: string; trust: { status: string; reason: string } }[];
}

const RAW = coverageJson as unknown as RawResearch;

export const RESEARCH_COVERAGE: CoverageFacts = {
  partitions: RAW.partitions,
  partitionRange: RAW.partition_range,
  labelVersionHomogeneous: RAW.label_version_homogeneous,
  labelVersion: RAW.label_version,
  statusDistribution: RAW.status_distribution,
  detectorValidHits: RAW.detector_valid_hits,
  detectors: RAW.detectors,
  negativeFindings: RAW.negative_findings,
};

export function detectorHitRate(detector: string): number {
  return RAW.detector_valid_hits[detector] ?? 0;
}