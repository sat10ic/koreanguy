import fallbackRunCardRaw from "./fallbackRunCard.2026-07-10.json";

const API_ROOT = "http://127.0.0.1:8000";

// R2: fallback payloads used when the API is unreachable. Every fallback
// return is tagged offline_fallback:true so the UI can render an honest
// "API offline — cached snapshot" banner instead of silently presenting
// stale local data as live (previously available:true / build_sha:"local"
// masked a dead API as a live one).
const fallbackRunCard = { ...fallbackRunCardRaw, available: true, offline_fallback: true };

const fallbackMarket = {
  available: true,
  offline_fallback: true,
  indices: [
    { symbol: "NIFTY50", name: "Nifty 50", returns: { "1d": 0.3 }, spark: [] },
    { symbol: "NIFTYMIDSML400", name: "MidSmall 400", returns: { "1d": 0.8 }, spark: [] },
  ],
  vix: { value: 13.4, band: "calm" },
  sectors: [
    { symbol: "NIFTY PHARMA", name: "PHARMA", move_pct: 1.2, num_stocks: 6 },
    { symbol: "NIFTY REALTY", name: "REALTY", move_pct: 0.9, num_stocks: 5 },
  ],
  movers: {},
  stock_movers: [],
  deals: {},
  chartsmaze_sectors: [],
};

function fallbackJson(path) {
  if (path === "/api/desk/latest") {
    return {
      latest_run_card_date: fallbackRunCard.scan_date || fallbackRunCard.run_date,
      latest_scan_date: fallbackRunCard.scan_date || fallbackRunCard.run_date,
      data_as_of: fallbackRunCard.scan_date || fallbackRunCard.run_date,
      next_update_hint: "next update ~19:25",
      build_sha: "OFFLINE",
      offline_fallback: true,
    };
  }
  if (path === "/api/desk/run-card") return fallbackRunCard;
  if (path === "/api/desk/market") return fallbackMarket;
  if (path === "/api/pipeline/status") return { running: false };
  return null;
}

async function getJson(path, params, signal) {
  const url = new URL(API_ROOT + path);
  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== "") url.searchParams.set(k, v);
    });
  }
  let res;
  try {
    const opts = signal ? { signal } : {};
    res = await fetch(url.toString(), opts);
  } catch (err) {
    if (err.name === 'AbortError') throw err;
    const fallback = fallbackJson(path);
    if (fallback) return fallback;
    throw err;
  }
  if (!res.ok) {
    const fallback = fallbackJson(path);
    if (fallback) return fallback;
    throw new Error(`${path} -> HTTP ${res.status}`);
  }
  return res.json();
}

async function deleteJson(path) {
  const res = await fetch(API_ROOT + path, { method: "DELETE" });
  if (!res.ok) {
    throw new Error(`${path} -> HTTP ${res.status}`);
  }
  return res.json();
}


export function fetchFeed(date) {
  return getJson("/api/desk/feed", { date });
}

export function fetchRunCard(date) {
  return getJson("/api/desk/run-card", { date });
}

const debateReadsInFlight = new Map();

export function fetchDebate(date, signal) {
  const key = date || "latest";
  if (debateReadsInFlight.has(key)) return debateReadsInFlight.get(key);
  const request = getJson("/api/desk/debate", { date }, signal).finally(() => {
    debateReadsInFlight.delete(key);
  });
  debateReadsInFlight.set(key, request);
  return request;
}

export function fetchChartData(symbol, date) {
  return getJson("/api/desk/chart-data", { symbol, date });
}

export function fetchDataCoverage() {
  return getJson("/api/data/coverage");
}

export function fetchSignalGuide(symbol, date, signal) {
  return getJson("/api/desk/signal-guide", { symbol, date }, signal);
}

export function fetchPositions(date) {
  return getJson("/api/desk/positions", { date });
}

export function addPosition(payload) {
  return postJson("/api/desk/positions", payload);
}

export function updatePosition(tradeId, payload) {
  return postJson(`/api/desk/positions/${tradeId}/update`, payload);
}

export function closePosition(tradeId, payload) {
  return postJson(`/api/desk/positions/${tradeId}/close`, payload);
}

export function fetchMarket(date, includeThematic) {
  return getJson("/api/desk/market", { date, include_thematic: includeThematic ? "true" : undefined });
}

export function fetchSectorStocks(sector, date) {
  return getJson("/api/desk/market/sector-stocks", { sector, date });
}

export function fetchFocus(date) {
  return getJson("/api/desk/focus", { date });
}

export function fetchTrackRecord() {
  return getJson("/api/desk/track-record");
}

// UI-3 MARKET: daily XP + MBI series (regime_snapshots read-back) for the
// trend line + ribbon.
export function fetchRegimeHistory(date, days) {
  return getJson("/api/regime/history", { date, days });
}

// UI-3 MARKET: %-above-DMA breadth trend (breadth_daily read-back).
export function fetchBreadthHistory(date, days) {
  return getJson("/api/regime/breadth-history", { date, days });
}

// UI-3 MARKET: Stockbee COMPUTE-now analytics (net breadth, 5/10-day AD
// ratio, monthly move breadth, DMA-cross) -- server-computed, see
// api/app.py::regime_breadth_analytics.
export function fetchBreadthAnalytics(date, days) {
  return getJson("/api/regime/breadth-analytics", { date, days });
}

export function fetchLessons(limit) {
  return getJson("/api/desk/lessons", limit ? { limit } : undefined);
}

// Fyers re-auth (F8): status/auth-url/exchange -- no secrets ever echoed
// back by the API, only booleans + the login URL + a status string.
export function fetchFyersStatus() {
  return getJson("/api/fyers/status");
}

export function fetchFyersAuthUrl() {
  return getJson("/api/fyers/auth-url");
}

export function exchangeFyersAuthCode(value) {
  return postJson("/api/fyers/exchange", { value });
}

export function fetchJournal() {
  return getJson("/api/journal");
}

export function addJournalTrade(payload) {
  return postJson("/api/journal", payload);
}

export function updateJournalTrade(tradeId, payload) {
  return putJson(`/api/journal/${tradeId}`, payload);
}

export function postSetupDecision(payload) {
  return postJson("/api/setups/decision", payload);
}

export function deleteJournalTrade(tradeId) {
  return deleteJson(`/api/journal/${tradeId}`);
}


export function fetchLatest() {
  return getJson("/api/desk/latest");
}

export function fetchScannerPresets(date, includeHits = true) {
  return getJson("/api/scanners/presets", { date, include_hits: includeHits });
}

export function fetchScannerPresetHits(key, date) {
  return getJson("/api/scanners/preset-hits", { key, date });
}

export function runScannerPreset(key, date) {
  return getJson("/api/scanners/run", { key, date });
}

export function runDeskScreener(conditions, date) {
  return getJson("/api/desk/screener", { conditions: JSON.stringify(conditions || []), date });
}

export function fetchUserScreens() {
  return getJson("/api/desk/user_screens");
}

export function saveUserScreen(name, conditions) {
  return postJson("/api/desk/user_screens", { name, conditions });
}

export function addWatchlistSymbol(symbol, reason) {
  return postJson("/api/desk/watchlist/add", { symbol, reason });
}

export function fetchWatchlist(date) {
  return getJson("/api/desk/watchlist", { date });
}

export function removeWatchlistSymbol(symbol, reason, date) {
  return postJson("/api/desk/watchlist/remove", { symbol, reason, scan_date: date });
}

export function deleteUserScreen(name) {
  return deleteJson(`/api/desk/user_screens/${encodeURIComponent(name)}`);
}

// STRONG START / Arora focus list (manas_os/design/STRONG_START_FOCUS_SPEC.md).
export function fetchFocusList(date) {
  return getJson("/api/desk/focus-list", { date });
}

export function addFocusSymbol(symbol, source, reason) {
  return postJson("/api/desk/focus-list/add", { symbol, source, reason });
}

export function removeFocusSymbol(symbol) {
  return postJson("/api/desk/focus-list/remove", { symbol });
}

async function postJson(path, body) {
  const res = await fetch(API_ROOT + path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body || {}),
  });
  if (!res.ok) {
    const err = new Error(`${path} -> HTTP ${res.status}`);
    err.status = res.status;
    throw err;
  }
  return res.json();
}

async function putJson(path, body) {
  const res = await fetch(API_ROOT + path, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body || {}),
  });
  if (!res.ok) {
    const err = new Error(`${path} -> HTTP ${res.status}`);
    err.status = res.status;
    throw err;
  }
  return res.json();
}

export function runPipeline(opts) {
  return postJson("/api/pipeline/run", opts || { fetch_sources: true });
}

// Durable live-work API. The legacy pipeline endpoints remain exported for
// older surfaces, but the v5 desk owns run progress through these job records.
export function createJob(opts = {}) {
  return postJson("/api/jobs", {
    date: opts.date || null,
    fetch_sources: opts.fetchSources !== false,
  });
}

export function fetchJobs(limit = 30) {
  return getJson("/api/jobs", { limit });
}

export function fetchJob(jobId) {
  return getJson(`/api/jobs/${jobId}`);
}

export function fetchJobEvents(jobId, after = 0, limit = 200) {
  return getJson(`/api/jobs/${jobId}/events`, { after, limit });
}

export function cancelJob(jobId) {
  return postJson(`/api/jobs/${jobId}/cancel`, {});
}

export function retryJobStep(jobId, stepId) {
  return postJson(`/api/jobs/${jobId}/steps/${stepId}/retry`, {});
}

export function jobEventsUrl(jobId, after = 0) {
  const url = new URL(`${API_ROOT}/api/jobs/${jobId}/events/stream`);
  url.searchParams.set("after", String(after));
  return url.toString();
}

// Chartink screener + push-to-debate amendment (2026-07-11 ~09:30): "push
// the stock to the debate panel to the llms? on top of whatever it itself
// screens". Runs synchronously server-side; the caller shows a toast with
// the result and should refetch the debate tab to see the new card.
export function pushSymbolToDebate(symbol, date, stream = false) {
  const url = stream ? "/api/desk/debate/push?stream=true" : "/api/desk/debate/push";
  return postJson(url, { symbol, date });
}

export function fetchSymbolSearch(q) {
  return getJson("/api/symbols/search", { q });
}


export function getPipelineStatus() {
  return getJson("/api/pipeline/status");
}

export function fetchAlphaOverview() { return getJson("/api/alpha/overview"); }
export function fetchAlphaLeaders(date, limit = 20) { return getJson("/api/alpha/leaders", { date, limit }); }
export function fetchAlphaActivity(date, limit = 20) { return getJson("/api/alpha/activity", { date, limit }); }
export function fetchAlphaActivitySymbol(symbol, date, trail = 10) { return getJson(`/api/alpha/activity/${encodeURIComponent(symbol)}`, { date, trail }); }
export function fetchAlphaResearchQuality() { return getJson("/api/alpha/research-quality"); }
export function fetchAlphaModels() { return getJson("/api/alpha/models"); }
export function fetchAlphaExperiments() { return getJson("/api/alpha/experiments"); }
export function fetchAlphaSymbol(symbol, date) { return getJson(`/api/alpha/symbol/${encodeURIComponent(symbol)}`, { date }); }

// Guided daily flow — 6-step process (data → regime → positions → setups → plan → done).
// Built in app.py:2963, zero frontend references prior to handoff 10.
export function fetchFlowToday(date) { return getJson("/api/flow/today", date ? { date } : undefined); }

export function fetchMentorChecklists(signal) {
  return getJson("/api/mentor/checklists", undefined, signal);
}

export function fetchChecklistEvaluation(checklistId, symbol, date, signal) {
  return getJson(`/api/checklists/${checklistId}/evaluate`, { symbol, date }, signal);
}

export function toggleChecklistTick(checklistId, itemId, symbol, date, checked) {
  return postJson(`/api/checklists/${checklistId}/ticks`, { symbol, date, item_id: itemId, checked });
}

export function fetchTraderProfile() {
  return getJson("/api/trader-profile");
}

export function updateTraderProfile(payload) {
  return putJson("/api/trader-profile", payload);
}

export function chartUrl(date, symbol, tf) {
  const url = new URL(API_ROOT + "/api/desk/chart");
  url.searchParams.set("date", date);
  url.searchParams.set("symbol", symbol);
  url.searchParams.set("tf", tf);
  return url.toString();
}
