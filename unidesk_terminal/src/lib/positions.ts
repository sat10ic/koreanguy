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

// F-4.3: the server copy under data/market/desk_register.json is the DURABLE
// record; localStorage stays a cache. Mirroring is fire-and-forget — a missed
// mirror keeps the local register intact, and Export remains the offline
// guarantee.
export function mirrorRegisterToServer(list: Position[], accountSize: number | null): void {
  try {
    void fetch("/api/register", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ positions: list, accountSize, updatedAt: new Date().toISOString() }),
    }).catch(() => { /* offline: cache remains the record */ });
  } catch { /* offline */ }
}

/** Boot seed: a fresh browser (empty cache) restores the server's copy once.
 *  Never overwrites a non-empty local register — local edits win until saved. */
export async function seedRegisterFromServer(): Promise<void> {
  try {
    if (loadPositions().length > 0) return;
    const res = await fetch("/api/register");
    if (!res.ok) return;
    const data = await res.json() as { positions?: Position[]; accountSize?: number | null };
    if (Array.isArray(data.positions) && data.positions.length > 0) {
      savePositions(data.positions);
      if (typeof data.accountSize === "number" && data.accountSize > 0) {
        try { localStorage.setItem("unidesk.accountSize", String(data.accountSize)); } catch { /* ignore */ }
      }
    }
  } catch { /* offline: cache as before */ }
}
