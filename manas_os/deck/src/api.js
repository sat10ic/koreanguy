// Thin API layer. One function per thing a screen needs -- no generic client,
// no caching layer, nothing speculative. Grows only when a screen needs it.

const BASE = "";

async function get(path, params = {}) {
  const qs = Object.entries(params)
    .filter(([, v]) => v != null && v !== "")
    .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`)
    .join("&");
  const res = await fetch(`${BASE}${path}${qs ? `?${qs}` : ""}`);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

/** Breadth series behind the TODAY quadrant. universe_breadth is the only writer. */
export function fetchBreadth(date, days = 60) {
  return get("/api/regime/breadth-analytics", { date, days });
}

/** Regime mode / posture for the date. */
export function fetchRegime(date) {
  return get("/api/regime/summary", { date });
}

/** XP / MBI / the four R-ratios, per day. regime_snapshots is the only writer. */
export function fetchRegimeHistory(date, days = 30) {
  return get("/api/regime/history", { date, days });
}

/** Mswing Homma per index — the MOMENTUM row. engine/mswing.py is the only writer. */
export function fetchMswing(date, days = 90) {
  return get("/api/regime/mswing", { date, days });
}

/** Daily OHLC for one index + that day's market_mode — the candle chart and its bands. */
export function fetchIndexCandles(date, symbol = "NIFTYMIDSML400", days = 120) {
  return get("/api/regime/index-candles", { date, symbol, days });
}
