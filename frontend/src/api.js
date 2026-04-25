import axios from "axios";

const BASE = process.env.REACT_APP_BACKEND_URL || "";

export const api = axios.create({
  baseURL: BASE,
  timeout: 60000,
});

export const endpoints = {
  health: () => api.get("/api/health").then((r) => r.data),
  regime: () => api.get("/api/regime").then((r) => r.data),
  universeSummary: () => api.get("/api/universe/summary").then((r) => r.data),
  universe: () => api.get("/api/universe").then((r) => r.data),
  screen: (params) => api.get("/api/screen", { params }).then((r) => r.data),
  rsGrid: () => api.get("/api/rs_grid").then((r) => r.data),
  candidates: () => api.get("/api/candidates").then((r) => r.data),
  candidatesHistory: (days = 30) =>
    api.get("/api/candidates/history", { params: { days } }).then((r) => r.data),
  positions: (state) =>
    api.get("/api/positions", { params: state ? { state } : {} }).then((r) => r.data),
  watchlist: () => api.get("/api/watchlist").then((r) => r.data),
  watchlistAdd: (symbol, reason) =>
    api.post("/api/watchlist/add", { symbol, reason }).then((r) => r.data),
  watchlistRemove: (symbol) =>
    api.post("/api/watchlist/remove", { symbol }).then((r) => r.data),
  watchlistRefreshMeta: (symbol) =>
    api
      .post("/api/watchlist/refresh_meta", symbol ? { symbol } : {})
      .then((r) => r.data),
  positionAdd: (data) =>
    api.post("/api/positions/add", data).then((r) => r.data),
  positionUpdate: (id, data) =>
    api.post(`/api/positions/${id}/update`, data).then((r) => r.data),
  positionExit: (id, data) =>
    api.post(`/api/positions/${id}/exit`, data).then((r) => r.data),
  positionDelete: (id) =>
    api.post(`/api/positions/${id}/delete`).then((r) => r.data),
  svroArms: () => api.get("/api/svro/arms").then((r) => r.data),
  symbol: (sym, days = 180) =>
    api.get(`/api/symbol/${sym}`, { params: { days } }).then((r) => r.data),
  pipelineStatus: () => api.get("/api/pipeline/status").then((r) => r.data),
  pipelineRun: (maxSymbols) =>
    api
      .post("/api/pipeline/run", maxSymbols ? { max_symbols: maxSymbols } : {})
      .then((r) => r.data),
  config: () => api.get("/api/config").then((r) => r.data),
};
