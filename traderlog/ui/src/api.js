// One named function per endpoint. No generic client, no react-query.
// Same convention as manas_os/desk/src/api.js so a model moving between the two
// projects does not have to learn a second data-fetching pattern.
//
// Paths are relative: in dev Vite proxies /api to 127.0.0.1:8100, in production
// the API serves this bundle from the same origin. No environment switch.

async function getJson(path, params) {
  const qs = params
    ? "?" +
      new URLSearchParams(
        Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== "")
      ).toString()
    : "";
  const res = await fetch(`/api${path}${qs}`);
  if (!res.ok) throw new Error(`${path} -> HTTP ${res.status}`);
  return res.json();
}

export const fetchHealth = () => getJson("/health");
export const fetchFeed = (params) => getJson("/feed", params);
export const fetchReview = () => getJson("/review");
export const fetchTraders = () => getJson("/traders");
export const fetchTrader = (handle) => getJson(`/traders/${handle}`);
export const fetchPositions = (params) => getJson("/positions", params);
export const fetchPosition = (id) => getJson(`/positions/${id}`);
export const fetchBreadth = (days) => getJson("/breadth", { days });
export const fetchIdeas = () => getJson("/ideas");
export const fetchLibrary = () => getJson("/library");

export async function resolveReview(id, decision) {
  const res = await fetch(`/api/review/${id}?decision=${decision}`, { method: "POST" });
  if (!res.ok) throw new Error(`resolve ${id} -> HTTP ${res.status}`);
  return res.json();
}
