const API_ROOT = "http://127.0.0.1:8000";

async function getJson(path, params) {
  const url = new URL(API_ROOT + path);
  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== "") url.searchParams.set(k, v);
    });
  }
  const res = await fetch(url.toString());
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

async function postJson(path, body) {
  const res = await fetch(API_ROOT + path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body || {}),
  });
  if (!res.ok) {
    throw new Error(`${path} -> HTTP ${res.status}`);
  }
  return res.json();
}

export function runPipeline(opts) {
  return postJson("/api/pipeline/run", opts || { fetch_sources: true });
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
