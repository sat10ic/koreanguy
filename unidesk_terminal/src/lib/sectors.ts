// Sector mapping — vendor labels (Chartsmaze) joined per symbol.
// DISTINCT SOURCE from scan data: provenance disclosed wherever shown.
// D-10 discipline applies: this is reference data, never merged into
// candidate rows by the backend — the UI joins it for display only.
import sectorJson from "../data/sector_mapping.json";

interface SectorFile {
  source: string;
  generator: string;
  count: number;
  symbols: Record<string, { industry: string; sector: string }>;
}

const FILE = sectorJson as unknown as SectorFile;

export const SECTOR_SOURCE_LABEL = "Chartsmaze vendor mapping — not NSE official";

export function sectorFor(symbol: string): { sector: string; industry: string } | null {
  const hit = FILE.symbols[symbol];
  return hit ? { sector: hit.sector, industry: hit.industry } : null;
}

// E-3: rehydrate in place from the desk server's export.
export function hydrateSectors(file: SectorFile): void {
  Object.assign(FILE, file);
}
