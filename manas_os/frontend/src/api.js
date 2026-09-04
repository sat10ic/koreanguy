// Talks directly to the FastAPI backend on :8000 (CORS allowed for :5173 in
// api/app.py). No proxy, no env var — single-user local-first tool.
const API_BASE = "http://127.0.0.1:8000";

async function getJSON(path) {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) {
    throw new Error(`${path} -> ${res.status} ${res.statusText}`);
  }
  return res.json();
}

async function postJSON(path, body) {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body || {}),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    // FastAPI puts the human message in `detail`.
    throw new Error(data.detail || `${path} -> ${res.status} ${res.statusText}`);
  }
  return data;
}

async function putJSON(path, body) {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body || {}),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || `${path} -> ${res.status} ${res.statusText}`);
  return data;
}

async function deleteJSON(path) {
  const res = await fetch(`${API_BASE}${path}`, { method: "DELETE" });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || `${path} -> ${res.status} ${res.statusText}`);
  return data;
}

// ── Pipeline refresh + data coverage ───────────────────────────────────────
export const runPipeline = (opts = {}) =>
  postJSON("/api/pipeline/run", {
    ...(opts.date ? { date: opts.date } : {}),
    ...(opts.fetchSources ? { fetch_sources: true } : {}),
  });
export const getPipelineStatus = () => getJSON("/api/pipeline/status");
export const getDataCoverage = () => getJSON("/api/data/coverage");

// ── Symbol + watchlist execution surfaces ───────────────────────────────────
export const getSymbolTiming = (symbol, date) => {
  const qs = date ? `?date=${encodeURIComponent(date)}` : "";
  return getJSON(`/api/symbol/${encodeURIComponent(symbol)}/timing${qs}`);
};

export const getSymbolOhlc = (symbol, opts = {}) => {
  const params = new URLSearchParams();
  if (opts.tf) params.set("tf", opts.tf);
  if (opts.n) params.set("n", opts.n);
  if (opts.date) params.set("date", opts.date);
  const qs = params.toString();
  return getJSON(`/api/symbol/${encodeURIComponent(symbol)}/ohlc${qs ? `?${qs}` : ""}`);
};

export const getWatchlist = (date) => {
  const qs = date ? `?date=${encodeURIComponent(date)}` : "";
  return getJSON(`/api/watchlist${qs}`);
};
export const addWatchlist = (symbol, note = null) => postJSON("/api/watchlist", { symbol, note });
export async function deleteWatchlist(symbol) {
  const res = await fetch(`${API_BASE}/api/watchlist/${encodeURIComponent(symbol)}`, { method: "DELETE" });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || `/api/watchlist/${symbol} -> ${res.status}`);
  return data;
}

export const getSetups = (opts = {}) => {
  const params = new URLSearchParams();
  if (opts.date) params.set("date", opts.date);
  if (opts.minRs) params.set("min_rs", opts.minRs);
  if (opts.setup) params.set("setup", opts.setup);
  if (opts.sector) params.set("sector", opts.sector);
  if (opts.grade) params.set("grade", opts.grade);
  if (opts.limit) params.set("limit", opts.limit);
  const qs = params.toString();
  return getJSON(`/api/setups${qs ? `?${qs}` : ""}`);
};
export const postSetupDecision = (decision) => postJSON("/api/setups/decision", decision);
export const getSetupsRefusals = (opts = {}) => {
  const params = new URLSearchParams();
  if (opts.date) params.set("date", opts.date);
  if (opts.limit) params.set("limit", opts.limit);
  const qs = params.toString();
  return getJSON(`/api/setups/refusals${qs ? `?${qs}` : ""}`);
};
export const getSetupsNearMisses = (opts = {}) => {
  const params = new URLSearchParams();
  if (opts.date) params.set("date", opts.date);
  if (opts.limit) params.set("limit", opts.limit);
  const qs = params.toString();
  return getJSON(`/api/setups/near-misses${qs ? `?${qs}` : ""}`);
};
export const trackWatchlistCandidate = (candidate) => postJSON("/api/watchlist/candidates", candidate);
export const overrideSetup = (payload) => postJSON("/api/setups/override", payload);
export const getOrganicWatchlist = (date) => {
  const qs = date ? `?date=${encodeURIComponent(date)}` : "";
  return getJSON(`/api/watchlist/organic${qs}`);
};
export const getGateHealth = (opts = {}) => {
  const params = new URLSearchParams();
  if (opts.date) params.set("date", opts.date);
  if (opts.days) params.set("days", opts.days);
  const qs = params.toString();
  return getJSON(`/api/visuals/gate-health${qs ? `?${qs}` : ""}`);
};
export const getPortfolioHeat = () => getJSON("/api/portfolio/heat");
export const getAdvisorToday = (date) => {
  const qs = date ? `?date=${encodeURIComponent(date)}` : "";
  return getJSON(`/api/advisor/today${qs}`);
};
export const postAdvisorNoteAction = (payload) => postJSON("/api/advisor/note-action", payload);
export const getExpectancy = () => getJSON("/api/expectancy");
export const getFlowToday = () => getJSON("/api/flow/today");
export const getMentorChecklists = () => getJSON("/api/mentor/checklists");
export const getMentorChecklistResponses = (checklistId, date) => {
  const qs = date ? `?date=${encodeURIComponent(date)}` : "";
  return getJSON(`/api/mentor/checklists/${encodeURIComponent(checklistId)}/responses${qs}`);
};
export const postMentorChecklistResponse = (checklistId, payload) =>
  postJSON(`/api/mentor/checklists/${encodeURIComponent(checklistId)}/responses`, payload);

export const getJournal = () => getJSON("/api/journal");
export const getJournalVisuals = () => getJSON("/api/journal/visuals");
export const addJournalTrade = (trade) => postJSON("/api/journal", trade);
export const updateJournalTrade = (tradeId, trade) => putJSON(`/api/journal/${tradeId}`, trade);
export async function closeJournalTrade(tradeId, payload) {
  const res = await fetch(`${API_BASE}/api/journal/trades/${tradeId}/close`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload || {}),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.message || data.detail || `/api/journal/trades/${tradeId}/close -> ${res.status}`);
    err.status = res.status;
    err.payload = data;
    throw err;
  }
  return data;
}
export const deleteJournalTrade = (tradeId) => deleteJSON(`/api/journal/${tradeId}`);
export const getEodAlerts = (opts = {}) => {
  const params = new URLSearchParams();
  if (opts.date) params.set("date", opts.date);
  if (opts.limit) params.set("limit", opts.limit);
  const qs = params.toString();
  return getJSON(`/api/alerts/eod${qs ? `?${qs}` : ""}`);
};

// ── Fyers login ──────────────────────────────────────────────────────────
export const getFyersStatus = () => getJSON("/api/fyers/status");
export const setFyersCredentials = (client_id, secret_id, redirect_uri) =>
  postJSON("/api/fyers/credentials", { client_id, secret_id, redirect_uri });
export const getFyersAuthUrl = () => getJSON("/api/fyers/auth-url");
export const submitFyersAuthCode = (value) => postJSON("/api/fyers/exchange", { value });
export const submitFyersToken = (token) => postJSON("/api/fyers/token", { token });

/** GET /api/regime/sectors — Sectors & Themes leaderboard for the regime page. */
export function getRegimeSectors(date) {
  const qs = date ? `?date=${encodeURIComponent(date)}` : "";
  return getJSON(`/api/regime/sectors${qs}`);
}

/** GET /api/regime/indices - sector-index performance leaderboard. */
export function getRegimeIndices(date) {
  const qs = date ? `?date=${encodeURIComponent(date)}` : "";
  return getJSON(`/api/regime/indices${qs}`);
}

/** GET /api/regime/sectors/{sectorKey}/stocks — stock RS drill-down for a sector. */
export function getSectorStocks(sectorKey, date) {
  const qs = date ? `?date=${encodeURIComponent(date)}` : "";
  return getJSON(`/api/regime/sectors/${encodeURIComponent(sectorKey)}/stocks${qs}`);
}

/** GET /api/regime/industries/{industryName}/stocks — stock RS drill-down for a theme/industry. */
export function getIndustryStocks(industryName, date) {
  const qs = date ? `?date=${encodeURIComponent(date)}` : "";
  return getJSON(`/api/regime/industries/${encodeURIComponent(industryName)}/stocks${qs}`);
}

/** GET /api/regime/summary — Top Decision Strip + Quadrant for the regime page. */
export function getRegimeSummary(date) {
  const qs = date ? `?date=${encodeURIComponent(date)}` : "";
  return getJSON(`/api/regime/summary${qs}`);
}

/** GET /api/regime/history — XP line + posture ribbon for the regime page. */
export function fetchRegimeHistory(days, date) {
  const params = new URLSearchParams();
  if (days != null) params.set("days", days);
  if (date) params.set("date", date);
  const qs = params.toString();
  return getJSON(`/api/regime/history${qs ? `?${qs}` : ""}`);
}

export const getRegimeHistory = fetchRegimeHistory;

/** GET /api/regime/breadth-history - 20DMA breadth sparkline for the decision strip. */
export function fetchRegimeBreadthHistory(days, date) {
  const params = new URLSearchParams();
  if (days != null) params.set("days", days);
  if (date) params.set("date", date);
  const qs = params.toString();
  return getJSON(`/api/regime/breadth-history${qs ? `?${qs}` : ""}`);
}

export const getBreadthHistory = fetchRegimeBreadthHistory;
