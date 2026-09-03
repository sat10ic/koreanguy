// Real research archive coverage + detector stats for the Research screen.
// Auto-discovers the newest bundled research_coverage_<date>.json
// (source: unidesk/run_research_coverage_export.py, fast pyarrow probe
// across every event-store partition).
const modules = import.meta.glob("./research_coverage_*.json", { eager: true }) as Record<string, unknown>;

export interface CoverageFacts {
  partitions: number;
  partitionRange: { oldest: string; newest: string };
  labelVersionHomogeneous: boolean;
  labelVersion: string;
  /** Per-version partition counts behind a MIXED verdict (e.g. "<missing": 20). */
  staleVersions: Record<string, number>;
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
  stale_versions?: Record<string, number>;
  status_distribution: Record<string, number>;
  detector_valid_hits: Record<string, number>;
  detectors: { name: string; title: string; trust: { status: string; reason: string; rankable: boolean } | null }[];
  negative_findings: { detector: string; title: string; trust: { status: string; reason: string } }[];
}

// C-2 (audit S3-3): sort newest-first by partition range, same convention as
// reportRegistry.ts / outcomes.ts — raw Object.values() path order picks an
// arbitrary file the moment a second export lands.
const BUNDLES = Object.values(modules)
  .map((json) => json as unknown as RawResearch)
  .sort((a, b) => b.partition_range.newest.localeCompare(a.partition_range.newest));
const RAW = BUNDLES[0] ?? {
  partitions: 0,
  partition_range: { oldest: "-", newest: "-" },
  label_version_homogeneous: false,
  label_version: "none",
  stale_versions: {},
  status_distribution: {},
  detector_valid_hits: {},
  detectors: [],
  negative_findings: [],
};

export const RESEARCH_COVERAGE: CoverageFacts = {
  partitions: RAW.partitions,
  partitionRange: RAW.partition_range,
  labelVersionHomogeneous: RAW.label_version_homogeneous,
  labelVersion: RAW.label_version,
  staleVersions: RAW.stale_versions ?? {},
  statusDistribution: RAW.status_distribution,
  detectorValidHits: RAW.detector_valid_hits,
  detectors: RAW.detectors,
  negativeFindings: RAW.negative_findings,
};

export function detectorHitRate(detector: string): number {
  return RAW.detector_valid_hits[detector] ?? 0;
}
