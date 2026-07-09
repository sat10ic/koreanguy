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

export function chartUrl(date, symbol, tf) {
  const url = new URL(API_ROOT + "/api/desk/chart");
  url.searchParams.set("date", date);
  url.searchParams.set("symbol", symbol);
  url.searchParams.set("tf", tf);
  return url.toString();
}
