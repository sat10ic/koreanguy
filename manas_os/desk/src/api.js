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

async function getJson(path, params) {
  const url = new URL(API_ROOT + path);
  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== "") url.searchParams.set(k, v);
    });
  }
  let res;
  try {
    res = await fetch(url.toString());
  } catch (err) {
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

export function fetchDebate(date) {
  return getJson("/api/desk/debate", { date });
}

export function fetchChartData(symbol, date) {
  return getJson("/api/desk/chart-data", { symbol, date });
}

export function fetchSignalGuide(symbol, date) {
  return getJson("/api/desk/signal-guide", { symbol, date });
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

export function fetchLessons(limit) {
  return getJson("/api/desk/lessons", limit ? { limit } : undefined);
}

export function fetchJournal() {
  return getJson("/api/journal");
}

export function fetchLatest() {
  return getJson("/api/desk/latest");
}

export function fetchScannerPresets(date) {
  return getJson("/api/scanners/presets", { date });
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

export function runPipeline(opts) {
  return postJson("/api/pipeline/run", opts || { fetch_sources: true });
}

// Chartink screener + push-to-debate amendment (2026-07-11 ~09:30): "push
// the stock to the debate panel to the llms? on top of whatever it itself
// screens". Runs synchronously server-side; the caller shows a toast with
// the result and should refetch the debate tab to see the new card.
export function pushSymbolToDebate(symbol, date) {
  return postJson("/api/desk/debate/push", { symbol, date });
}

export function getPipelineStatus() {
  return getJson("/api/pipeline/status");
}

export function chartUrl(date, symbol, tf) {
  const url = new URL(API_ROOT + "/api/desk/chart");
  url.searchParams.set("date", date);
  url.searchParams.set("symbol", symbol);
  url.searchParams.set("tf", tf);
  return url.toString();
}
