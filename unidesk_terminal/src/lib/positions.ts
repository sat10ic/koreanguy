// D-03: Positions register — manual, local, read-only with respect to
// anything external. No broker API, no routing (charter: manual execution
// only). Persisted in localStorage so D-02/D-05/D-06 can read it.
export interface Position {
  id: string;
  symbol: string;
  entryDate: string;      // ISO date
  entryPrice: number;
  sizeInr: number;
  invalidation?: number | null; // recorded stop level; absent = unmanaged
  notes?: string;
  // R-05: a paper call (no money placed) records the desk's own call so it
  // resolves against real bars tomorrow — same register, distinct flag.
  paper?: boolean;
}

const KEY = "unidesk.positions.v1";

export function loadPositions(): Position[] {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function savePositions(list: Position[]): void {
  localStorage.setItem(KEY, JSON.stringify(list));
}

export function addPosition(p: Omit<Position, "id">): Position[] {
  const list = loadPositions();
  const withId: Position = { ...p, id: `pos-${Date.now()}-${Math.random().toString(36).slice(2, 7)}` };
  savePositions([...list, withId]);
  return loadPositions();
}

export function removePosition(id: string): Position[] {
  savePositions(loadPositions().filter((p) => p.id !== id));
  return loadPositions();
}
