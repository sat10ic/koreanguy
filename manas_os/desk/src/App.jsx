import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  fetchRunCard,
  fetchLatest,
  fetchMarket,
  fetchDebate,
  fetchFlowToday,
  fetchSymbolSearch,
  pushSymbolToDebate,
  fetchFyersStatus,
  fetchFyersAuthUrl,
  exchangeFyersAuthCode,
} from "./api.js";
import MarketHomeTab from "./MarketHomeTab.jsx";
import ScannersTab from "./ScannersTab.jsx";
import ShortlistTab from "./ShortlistTab.jsx";
import DebateTab from "./DebateTab.jsx";
import TradePlanTab from "./TradePlanTab.jsx";
import PositionsTab from "./PositionsTab.jsx";
import LedgerTab from "./LedgerTab.jsx";
import AlphaLab from "./AlphaLab.jsx";
import { DensityContext, DENSITY_STORAGE_KEY, normalizeDensityMode } from "./DensityContext.jsx";
import { REGIME_GAUGE_ZONES } from "./viz.js";
import { Term } from "./Glossary.jsx";
import { CommandStrip, TickerTape, GuidedFlowRail, CollapsedFlowStrip, TabPurposeHeader } from "./components/v5/index.js";
import LiveWorkInspector from "./livework/LiveWorkInspector.jsx";
import { LiveWorkProvider, useLiveWork } from "./livework/useJobStream.js";
import TraderProfileModal from "./TraderProfileModal.jsx";
import "./App.css";

const TABS = ["MARKET", "SCANNERS", "SHORTLIST", "DEBATE", "ALPHA", "POSITIONS", "JOURNAL"];
const TAB_LABELS = { SHORTLIST: "SHORTLIST / SS" };
const BEGINNER_TAB_LABELS = {
  MARKET: "TODAY",
  SCANNERS: "PREPARE",
  SHORTLIST: "WATCH",
  DEBATE: "DECIDE",
  POSITIONS: "MANAGE",
  JOURNAL: "REVIEW",
};

function todayIso() {
  return new Date().toISOString().slice(0, 10);
}

function shiftDate(iso, days) {
  const d = new Date((iso || todayIso()) + "T00:00:00");
  d.setDate(d.getDate() + days);
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${d.getFullYear()}-${m}-${day}`;
}

function findPrevRunDate(currentDate, runCardDates) {
  if (!currentDate) return todayIso();
  if (!runCardDates || runCardDates.length === 0) return shiftDate(currentDate, -1);
  const sorted = [...runCardDates].sort();
  const valid = sorted.filter((d) => d < currentDate);
  if (valid.length > 0) {
    return valid[valid.length - 1];
  }
  return shiftDate(currentDate, -1);
}

function findNextRunDate(currentDate, runCardDates) {
  if (!currentDate) return todayIso();
  if (!runCardDates || runCardDates.length === 0) return shiftDate(currentDate, 1);
  const sorted = [...runCardDates].sort();
  const valid = sorted.filter((d) => d > currentDate);
  if (valid.length > 0) {
    return valid[0];
  }
  return shiftDate(currentDate, 1);
}

function findNearestRunDate(currentDate, runCardDates) {
  if (!currentDate || !runCardDates || runCardDates.length === 0) return null;
  const currentMs = new Date(currentDate + "T00:00:00").getTime();
  let nearest = runCardDates[0];
  let minDiff = Math.abs(new Date(nearest + "T00:00:00").getTime() - currentMs);
  for (let i = 1; i < runCardDates.length; i++) {
    const d = runCardDates[i];
    const diff = Math.abs(new Date(d + "T00:00:00").getTime() - currentMs);
    if (diff < minDiff) {
      minDiff = diff;
      nearest = d;
    }
  }
  return nearest;
}

function modeTerm(mode) {
  const m = (mode || "").toUpperCase();
  if (m === "RISK_ON") return "mode-risk-on";
  if (m === "SELECTIVE") return "mode-selective";
  if (m === "DEFENSIVE") return "mode-defensive";
  if (m === "NO_TRADE") return "mode-no-trade";
  return null;
}

function RegimeGauge({ regime }) {
  const mode = regime && regime.mode;
  const age = regime && regime.age_days;
  const zoneW = 100 / REGIME_GAUGE_ZONES.length;
  const activeIdx = REGIME_GAUGE_ZONES.findIndex((z) => z.mode === mode);
  const markerX = activeIdx >= 0 ? zoneW * activeIdx + zoneW / 2 : null;

  return (
    <div className="regime-gauge" title={mode ? `[B] regime mode: ${mode}` : "no regime snapshot"}>
      <svg className="regime-gauge-svg" viewBox="0 0 100 14" preserveAspectRatio="none">
        {REGIME_GAUGE_ZONES.map((z, i) => (
          <rect
            key={z.mode}
            x={zoneW * i}
            y="2"
            width={zoneW}
            height="8"
            fill={z.color}
            opacity={mode === z.mode ? 1 : 0.28}
          />
        ))}
        {markerX !== null && (
          <polygon points={`${markerX - 3},0 ${markerX + 3},0 ${markerX},5`} fill="var(--ink)" />
        )}
      </svg>
      <div className="regime-gauge-label mono">
        {mode && modeTerm(mode) ? <Term k={modeTerm(mode)}>{mode}</Term> : <span>{mode || "—"}</span>}
        {age !== null && age !== undefined && (
          <span className="regime-gauge-day">
            <Term k="regime-age">day {age}</Term>
          </span>
        )}
      </div>
    </div>
  );
}

function XpBadge({ regime }) {
  const xp = regime && regime.xp;
  if (xp === null || xp === undefined) return null;
  return (
    <div className="xp-badge mono" title="[B] Desk readiness score">
      <span className="xp-badge-value">{Math.round(xp)}</span>
      <span className="xp-badge-label">
        <Term k="xp-badge">XP</Term>
      </span>
    </div>
  );
}

function lastExpectedTradingDay(iso) {
  let d = new Date(iso + "T00:00:00");
  do {
    d.setDate(d.getDate() - 1);
  } while (d.getDay() === 0 || d.getDay() === 6);
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${d.getFullYear()}-${m}-${day}`;
}

export function relativeDayLabel(dataAsOf, todayIsoStr) {
  if (!dataAsOf) return "unknown";
  const a = new Date(dataAsOf + "T00:00:00");
  const b = new Date(todayIsoStr + "T00:00:00");
  const days = Math.round((b - a) / 86400000);
  if (days === 0) return "today";
  if (days === 1) return "yesterday";
  if (days > 1) return `${days} days ago`;
  return dataAsOf;
}

export function computeFreshnessBanner(latest, card, todayIsoStr) {
  if (!latest && (!card || !card.available)) return null;
  const stages = card?.pipeline || [];
  const lastBad = stages.find((stage) => ["error", "partial", "fail"].includes(stage.status));
  if (lastBad) {
    const reason = card?.council_status?.state === "run_failed"
      ? card.council_status.reason
      : `${String(lastBad.stage || "nightly update").replaceAll("_", " ")} failed`;
    const dataAsOf = card?.scan_date || card?.run_date || latest?.data_as_of || "unknown";
    return {
      state: "run_failed",
      reason,
      text: `RUN FAILED — ${reason}. Data through ${dataAsOf}.`,
    };
  }
  if (card?.no_op) {
    return {
      state: "awaiting_tonight",
      text: `STALE — showing last completed night ${card.scan_date || card.run_date}`,
    };
  }
  if (!latest) return null;
  const dataAsOf = latest.data_as_of;
  const rel = relativeDayLabel(dataAsOf, todayIsoStr);
  const hint = latest.next_update_hint || "";
  // R2: offline_fallback payloads mean the API is unreachable and this is a
  // cached local snapshot -- the freshness stamp must say OFFLINE, not a
  // build sha, so it can't be mistaken for a live build.
  const sha = latest.offline_fallback ? "OFFLINE" : latest.build_sha || "unknown";
  const text = `DATA AS OF ${dataAsOf || "unknown"} (${rel}) · ${hint} · build ${sha}`;
  const state = dataAsOf === todayIsoStr && !latest.offline_fallback ? "fresh" : "awaiting_tonight";
  return { state, text };
}

// R2: true when any payload the shell has consumed came back tagged
// offline_fallback:true (api.js returns cached local JSON when the API is
// unreachable) -- used to render an honest "API offline" banner instead of
// silently presenting stale local data as if it were live.
export function computeOfflineBanner(latestMeta, card) {
  const offline = !!(latestMeta && latestMeta.offline_fallback) || !!(card && card.offline_fallback);
  if (!offline) return null;
  return "API offline — showing cached snapshot from 2026-07-10, numbers may be stale";
}

// Wave 1 CommandStrip VIX: honest passthrough only. Never present the
// offline-fallback hardcoded vix:13.4 as live -- an offline_fallback payload
// renders "--" with a title, the same as a genuinely missing vix.
export function computeVixDisplay(market) {
  if (!market || market.offline_fallback) {
    return { value: null, title: "India VIX not available for this date (API offline -- cached snapshot)" };
  }
  const vix = market.vix;
  if (!vix || vix.value === null || vix.value === undefined) {
    return { value: null, title: "India VIX not available for this date" };
  }
  return { value: vix.value, title: vix.band ? `VIX band: ${vix.band}` : undefined };
}

// TickerTape items from /api/desk/debate symbols: chair verdict only. The old
// 65d-low chip was removed because it appeared static across symbols in the
// rendered audit; the per-symbol metric remains available in DEBATE itself.
export function debateToTapeItems(debate) {
  if (!debate || !debate.available || !Array.isArray(debate.symbols)) return [];
  return debate.symbols.map((s) => {
    const chair = s.chair || {};
    const tag = chair.verdict === "TAKE" ? "take" : chair.verdict === "SKIP" ? "skip" : null;
    return {
      symbol: s.symbol,
      tag,
      tagLabel: chair.struck && tag === "skip" ? "SKIP*" : undefined,
    };
  });
}

function LiveReadiness() {
  const [data, setData] = useState(null);

  useEffect(() => {
    const fetchIt = () => {
      fetch("/api/live/readiness")
        .then(res => res.json())
        .then(body => setData(body))
        .catch(() => {});
    };
    fetchIt();
    const timer = setInterval(fetchIt, 30_000);
    return () => clearInterval(timer);
  }, []);

  if (!data) return null;

  return (
    <div className="live-readiness mono" style={{ display: 'flex', gap: '8px', alignItems: 'center', fontSize: '0.8em', color: 'var(--v5-ink-mute)', marginLeft: '1rem' }}>
      <span title="Telegram Configured">{data.telegram_configured ? '✅ TG' : '❌ TG'}</span>
      {data.telegram_dry_run && <span style={{ color: 'var(--amber)' }} title="Telegram is in Dry Run Mode">DRY-RUN</span>}
      {data.halt_state && <span style={{ color: 'var(--red)' }} title="Entries are halted">HALTED</span>}
      <span title="Last Heartbeat">HB: {data.last_heartbeat ? data.last_heartbeat.slice(11,19) : 'none'}</span>
      {data.last_error && <span style={{ color: 'var(--red)' }} title={data.last_error}>⚠ ERR</span>}
    </div>
  );
}

// F8: Fyers connection card -- shows connected/expired via /api/fyers/status
// and, when expired, a "Re-authenticate Fyers" flow: open the login URL
// (from /api/fyers/auth-url), the user logs in on Fyers's own site and
// pastes the returned auth code back here, which POSTs to
// /api/fyers/exchange. We never store or echo the app secret or the
// resulting access token -- only booleans/status strings come back from
// the API.
function FyersConnectionCard() {
  const [status, setStatus] = useState(null);
  const [open, setOpen] = useState(false);
  const [authUrl, setAuthUrl] = useState(null);
  const [authUrlError, setAuthUrlError] = useState(null);
  const [code, setCode] = useState("");
  const [exchanging, setExchanging] = useState(false);
  const [exchangeError, setExchangeError] = useState(null);
  const popoverRef = useRef(null);

  const refreshStatus = useCallback(() => {
    fetchFyersStatus()
      .then((body) => setStatus(body))
      .catch(() => setStatus((s) => s || { status: "unknown", token_ready: false }));
  }, []);

  useEffect(() => {
    refreshStatus();
    const timer = setInterval(refreshStatus, 60_000);
    return () => clearInterval(timer);
  }, [refreshStatus]);

  useEffect(() => {
    if (!open) return undefined;
    function onClickOutside(e) {
      if (popoverRef.current && !popoverRef.current.contains(e.target)) setOpen(false);
    }
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, [open]);

  const ready = status?.token_ready === true;
  const label = status ? (ready ? "FYERS live" : "FYERS auth needed") : "FYERS —";

  function openLogin() {
    setAuthUrlError(null);
    fetchFyersAuthUrl()
      .then((body) => {
        setAuthUrl(body?.url || null);
        if (body?.url) window.open(body.url, "_blank", "noopener,noreferrer");
      })
      .catch((err) => setAuthUrlError(String(err?.message || err)));
  }

  function submitCode(e) {
    e.preventDefault();
    if (!code.trim()) return;
    setExchanging(true);
    setExchangeError(null);
    exchangeFyersAuthCode(code.trim())
      .then((body) => {
        setStatus(body);
        setCode("");
        setExchangeError(null);
      })
      .catch((err) => setExchangeError(String(err?.message || err)))
      .finally(() => setExchanging(false));
  }

  return (
    <div className="fyers-conn" ref={popoverRef}>
      <button
        type="button"
        className={"fyers-conn-chip mono" + (ready ? " fyers-conn-ready" : " fyers-conn-expired")}
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        title={ready ? "Fyers token is live" : "Fyers auth needed -- click to reconnect"}
      >
        <span className="fyers-conn-dot" aria-hidden="true" />
        {label}
      </button>
      {open && (
        <div className="fyers-conn-pop mono" role="dialog" aria-label="Fyers connection">
          <p className="fyers-conn-status">
            {status ? (
              <>
                app id {status.app_id_set ? "set" : "missing"} · secret {status.secret_set ? "set" : "missing"} ·
                token {status.token_ready ? "ready" : "missing"}
              </>
            ) : (
              "loading status…"
            )}
          </p>
          {!ready && (
            <p className="fyers-conn-warn">Entries needing live Fyers quotes will not work until you reconnect.</p>
          )}
          <button type="button" className="fyers-conn-reauth-btn" onClick={openLogin}>
            Re-authenticate Fyers →
          </button>
          {authUrlError && <p className="fyers-conn-error">{authUrlError}</p>}
          {authUrl && (
            <p className="fyers-conn-hint">
              Opened the Fyers login page. After you approve, paste the auth code (or the full
              redirect URL) from the address bar below.
            </p>
          )}
          <form className="fyers-conn-form" onSubmit={submitCode}>
            <input
              type="text"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              placeholder="paste auth code / redirect URL"
              aria-label="Fyers auth code"
            />
            <button type="submit" disabled={exchanging || !code.trim()}>
              {exchanging ? "checking…" : "connect"}
            </button>
          </form>
          {exchangeError && <p className="fyers-conn-error">{exchangeError}</p>}
        </div>
      )}
    </div>
  );
}

function DeskApp() {
  const [date, setDate] = useState(null);
  const [latestDate, setLatestDate] = useState(null);
  const [runCardDates, setRunCardDates] = useState([]);
  const [tab, setTab] = useState("MARKET");
  const [mode, setModeState] = useState(() => {
    if (typeof window === "undefined") return "beginner";
    return normalizeDensityMode(window.localStorage.getItem(DENSITY_STORAGE_KEY));
  });
  const [symbolSearch, setSymbolSearch] = useState("");
  const [card, setCard] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [latestMeta, setLatestMeta] = useState(null);
  const [debateJump, setDebateJump] = useState(null);
  const [tradePlan, setTradePlan] = useState(null);
  const [market, setMarket] = useState(null);
  const [tapeDebate, setTapeDebate] = useState(null);
  // Handoff 10: guided daily flow state
  const [flow, setFlow] = useState(null);
  // Handoff 7: symbol typeahead suggestions state
  const [suggestions, setSuggestions] = useState([]);
  const liveWork = useLiveWork();
  const wasRunningRef = useRef(false);
  // #28: keyboard shortcuts state
  const [railOpen, setRailOpen] = useState(true);
  const [helpOpen, setHelpOpen] = useState(false);
  const searchInputRef = useRef(null);
  const chordRef = useRef(null);

  // Handoff 7: fetch symbol suggestions on input change
  useEffect(() => {
    const q = symbolSearch.trim();
    if (q.length < 1) {
      setSuggestions([]);
      return undefined;
    }
    const timer = setTimeout(() => {
      fetchSymbolSearch(q)
        .then((res) => {
          setSuggestions(res.symbols || []);
        })
        .catch(() => {
          setSuggestions([]);
        });
    }, 150);
    return () => clearTimeout(timer);
  }, [symbolSearch]);


  const goToDebate = useCallback((symbol) => {
    setDebateJump({ symbol: symbol || null, ts: Date.now() });
    setTradePlan(null);
    setTab("DEBATE");
  }, []);

  // #23: jump to a symbol's debate on a SPECIFIC date (the entry/scan date for
  // a position's origin thesis). Sets the date first so DebateTab loads that
  // session, then signals the deep-dive scroll. Used by POSITIONS origin link.
  const goToDebateOnDate = useCallback((symbol, scanDate) => {
    if (scanDate) setDate(scanDate);
    setDebateJump({ symbol: symbol || null, ts: Date.now() });
    setTradePlan(null);
    setTab("DEBATE");
  }, []);

  // #23 / #49: kick off a fresh streamed debate for a symbol from POSITIONS
  // (e.g. a manually-added position with no recorded thesis) and jump to it.
  const runDebateFor = useCallback(
    (symbol) => {
      if (!symbol) return;
      pushSymbolToDebate(symbol, date, true)
        .then((res) => {
          if (res.job_id) liveWork.chooseJob(res.job_id, { reveal: true });
          setDebateJump({ symbol, jobId: res.job_id || null, ts: Date.now() });
          setTradePlan(null);
          setTab("DEBATE");
        })
        .catch((err) => {
          alert(`Search failed: ${err.message || String(err)}`);
        });
    },
    [date, liveWork]
  );

  // V4-T13: per-symbol TRADE PLAN route (like the debateJump pattern) --
  // opened from a DEBATE card's [TRADE PLAN->] link or a SHORTLIST row's
  // "open trade plan" action. No router lib: tradePlan!=null simply
  // replaces the tab body with the full-screen route until dismissed.
  const openTradePlan = useCallback(
    (symbol) => {
      if (!symbol) return;
      setTradePlan({ symbol, date });
    },
    [date]
  );

  const closeTradePlan = useCallback(
    (symbol) => {
      goToDebate(symbol);
    },
    [goToDebate]
  );

  const navigateTab = useCallback((nextTab) => {
    if (TABS.includes(nextTab)) setTab(nextTab);
  }, []);

  const setMode = useCallback((nextMode) => {
    const normalized = normalizeDensityMode(nextMode);
    setModeState(normalized);
    if (typeof window !== "undefined") {
      window.localStorage.setItem(DENSITY_STORAGE_KEY, normalized);
    }
  }, []);

  const densityValue = useMemo(
    () => ({
      mode,
      isExpert: mode === "expert",
      setMode,
      toggleMode: () => setMode(mode === "expert" ? "beginner" : "expert"),
    }),
    [mode, setMode]
  );

  const submitSymbolSearch = useCallback(
    (event) => {
      event.preventDefault();
      const symbol = symbolSearch.trim().toUpperCase();
      if (!symbol) return;

      setSymbolSearch("");
      setSuggestions([]);

      // Handoff 7: Start stream debate on demand
      pushSymbolToDebate(symbol, date, true)
        .then((res) => {
          if (res.already_debated) {
            // Already analyzed, just navigate directly
            setDebateJump({ symbol, ts: Date.now() });
            setTradePlan(null);
            setTab("DEBATE");
          } else if (res.job_id) {
            // Streaming job created: select the job and open inspector
            liveWork.chooseJob(res.job_id, { reveal: true });
            setDebateJump({ symbol, jobId: res.job_id, ts: Date.now() });
            setTradePlan(null);
            setTab("DEBATE");
          } else {
            // Synchronous fallback
            setDebateJump({ symbol, ts: Date.now() });
            setTradePlan(null);
            setTab("DEBATE");
          }
        })
        .catch((err) => {
          // Honest alert if ticker doesn't exist
          alert(`Search failed: ${err.message || String(err)}`);
        });
    },
    [date, liveWork, symbolSearch]
  );

  const jumpToLatest = useCallback(() => {
    return fetchLatest()
      .then((latest) => {
        const params = new URLSearchParams(window.location.search);
        const urlDate = params.get("date");
        const next = urlDate || latest.latest_run_card_date || latest.latest_scan_date || todayIso();
        setDate(next);

        const urlTab = params.get("tab");
        if (urlTab && TABS.includes(urlTab)) {
          setTab(urlTab);
        }

        const urlPlan = params.get("plan");
        if (urlPlan) {
          setTradePlan({ symbol: urlPlan, date: next });
        }

        const urlInspector = params.get("inspector") === "1";
        if (urlInspector) {
          liveWork.setOpen(true);
        }

        setLatestDate(latest.latest_run_card_date || latest.latest_scan_date || todayIso());
        setRunCardDates(latest.run_card_dates || []);
        setLatestMeta(latest);
        // eslint-disable-next-line no-console
        console.log(`[sat10ic os] build ${latest.build_sha || "unknown"} · data as of ${latest.data_as_of || "unknown"}`);
        return latest;
      })
      .catch(() => {
        const params = new URLSearchParams(window.location.search);
        const urlDate = params.get("date");
        setDate(urlDate || todayIso());

        const urlTab = params.get("tab");
        if (urlTab && TABS.includes(urlTab)) setTab(urlTab);
      });
  }, [liveWork]);

  useEffect(() => {
    jumpToLatest();
  }, [jumpToLatest]);

  useEffect(() => {
    const id = setInterval(() => {
      fetchLatest()
        .then((latest) => {
          setLatestMeta(latest);
          setLatestDate(latest.latest_run_card_date || latest.latest_scan_date || todayIso());
          setRunCardDates(latest.run_card_dates || []);
        })
        .catch(() => {});
    }, 5 * 60 * 1000);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    if (!date) return undefined;
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetchRunCard(date)
      .then((data) => {
        if (cancelled) return;
        setCard(data);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(String(err));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [date]);

  // Wave 1: CommandStrip needs VIX (from /api/desk/market) and the tape needs
  // debate symbols (from /api/desk/debate) -- fetched once per date,
  // independent of the tab-body fetches above so the shell renders real data
  // even when the user is sitting on a tab that doesn't itself call these.
  // Handoff 10: also fetch /api/flow/today and poll every 30 seconds.
  useEffect(() => {
    if (!date) return undefined;
    let cancelled = false;
    fetchMarket(date)
      .then((data) => {
        if (!cancelled) setMarket(data);
      })
      .catch(() => {
        if (!cancelled) setMarket(null);
      });
    fetchDebate(date)
      .then((data) => {
        if (!cancelled) setTapeDebate(data);
      })
      .catch(() => {
        if (!cancelled) setTapeDebate(null);
      });
    // Flow today does not take a date — always returns the current day's state.
    fetchFlowToday(date)
      .then((data) => {
        if (!cancelled) setFlow(data);
      })
      .catch(() => {
        if (!cancelled) setFlow(null);
      });
    return () => {
      cancelled = true;
    };
  }, [date]);

  // Handoff 10: poll /api/flow/today every 30 seconds to pick up pipeline changes.
  useEffect(() => {
    const id = setInterval(() => {
      fetchFlowToday(date)
        .then((data) => setFlow(data))
        .catch(() => {});
    }, 30_000);
    return () => clearInterval(id);
  }, []);

  const startUpdate = useCallback(() => {
    if (liveWork.running) return;
    liveWork.start({ date, fetchSources: true }).catch((err) => setError(String(err)));
  }, [date, liveWork]);

  useEffect(() => {
    if (wasRunningRef.current && !liveWork.running) jumpToLatest();
    wasRunningRef.current = liveWork.running;
  }, [liveWork.running, jumpToLatest]);

  // Sync state changes to the URL query parameters
  useEffect(() => {
    if (!date) return;
    const params = new URLSearchParams(window.location.search);
    params.set("tab", tab);
    params.set("date", date);
    if (tradePlan && tradePlan.symbol) {
      params.set("plan", tradePlan.symbol);
    } else {
      params.delete("plan");
    }
    if (liveWork.open) {
      params.set("inspector", "1");
    } else {
      params.delete("inspector");
    }
    const newSearch = params.toString() ? `?${params.toString()}` : "";
    if (window.location.search !== newSearch) {
      window.history.pushState(null, "", window.location.pathname + newSearch);
    }
  }, [tab, date, tradePlan, liveWork.open]);

  // Sync URL changes (like Back/Forward buttons) back to component state
  useEffect(() => {
    const handlePopState = () => {
      const params = new URLSearchParams(window.location.search);

      const urlDate = params.get("date");
      if (urlDate && urlDate !== date) {
        setDate(urlDate);
      }

      const urlTab = params.get("tab");
      if (urlTab && urlTab !== tab && TABS.includes(urlTab)) {
        setTab(urlTab);
      }

      const urlPlan = params.get("plan");
      if (urlPlan) {
        setTradePlan({ symbol: urlPlan, date: urlDate || date });
      } else {
        setTradePlan(null);
      }

      const urlInspector = params.get("inspector") === "1";
      if (urlInspector !== liveWork.open) {
        liveWork.setOpen(urlInspector);
      }
    };
    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, [date, tab, tradePlan, liveWork.open]);

  const staleLatestNudge = useMemo(() => {
    if (!date || liveWork.running) return false;
    return date < lastExpectedTradingDay(todayIso());
  }, [date, liveWork.running]);

  const freshnessBanner = useMemo(() => {
    const banner = computeFreshnessBanner(latestMeta, card, todayIso());
    if (banner || !staleLatestNudge) return banner;
    return {
      state: "awaiting_tonight",
      text: `Data fresh only through ${date} — a more recent trading session is available. Run update now.`,
    };
  }, [latestMeta, card, staleLatestNudge, date]);
  const offlineBanner = useMemo(() => computeOfflineBanner(latestMeta, card), [latestMeta, card]);

  const vixDisplay = useMemo(() => computeVixDisplay(market), [market]);
  const tapeItems = useMemo(() => debateToTapeItems(tapeDebate), [tapeDebate]);
  const regime = card && card.regime;
  const funnel = tapeDebate && tapeDebate.funnel;

  const flowSteps = flow?.steps || [];
  const flowCurrent = flow?.current_step;
  const flowAvailable = !!(flow?.available);

  // #28: global keyboard shortcuts. Single listener, ignores shortcuts while
  // typing in a field (Escape still closes). Chord model: `g` then a letter.
  // Declared after flowAvailable so it is in scope for the dependency array.
  useEffect(() => {
    const isTyping = (el) =>
      el && (el.tagName === "INPUT" || el.tagName === "TEXTAREA" || el.tagName === "SELECT" || el.isContentEditable);
    const handler = (e) => {
      // Escape: close trade-plan route, then live-work inspector, then help.
      if (e.key === "Escape") {
        if (tradePlan) {
          closeTradePlan(tradePlan.symbol);
          return;
        }
        if (liveWork.open) {
          liveWork.setOpen(false);
          return;
        }
        if (helpOpen) setHelpOpen(false);
        return;
      }
      if (isTyping(e.target) || e.metaKey || e.ctrlKey || e.altKey) return;

      if (e.key === "/") {
        e.preventDefault();
        searchInputRef.current?.focus();
        return;
      }
      if (e.key === "?") {
        e.preventDefault();
        // Beginner + guided flow present: toggle the side rail. Otherwise show
        // the shortcut help toast.
        if (!densityValue.isExpert && flowAvailable) {
          setRailOpen((v) => !v);
        } else {
          setHelpOpen((v) => !v);
        }
        return;
      }
      // Chord: `g` followed by a destination letter.
      if (chordRef.current === "g") {
        chordRef.current = null;
        const map = {
          h: "MARKET",
          d: "DEBATE",
          p: "POSITIONS",
          j: "JOURNAL",
          s: "SHORTLIST",
          a: "ALPHA",
        };
        const target = map[e.key.toLowerCase()];
        if (target) {
          e.preventDefault();
          setTradePlan(null);
          setTab(target);
        }
        return;
      }
      if (e.key.toLowerCase() === "g") {
        chordRef.current = "g";
        setTimeout(() => {
          if (chordRef.current === "g") chordRef.current = null;
        }, 1200);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [tradePlan, liveWork.open, helpOpen, densityValue.isExpert, flowAvailable, closeTradePlan]);


  const isNoRunDay = date && runCardDates.length > 0 && !runCardDates.includes(date);
  const nearestRunDate = isNoRunDay ? findNearestRunDate(date, runCardDates) : null;

  return (
    <DensityContext.Provider value={densityValue}>
      <div className={`v5 v5-shell shell density-${mode}`}>
        <CommandStrip
          date={date}
          dayColor={regime && regime.mbi_day_color}
          regimeMode={regime && regime.mode}
          hmmCaption={regime && regime.hmm_caption}
          vix={vixDisplay.value}
          vixTitle={vixDisplay.title}
          xp={regime && regime.xp !== null && regime.xp !== undefined ? regime.xp.toFixed(2) : null}
          universe={funnel && funnel.universe}
          debated={funnel && funnel.debated}
        />
        <TickerTape items={tapeItems} emptyLabel={`no debate for ${date || "this date"}`} />

        <header className="shell-header shell-utility-row" aria-label="desk controls">
          <div className="date-scrubber" role="group" aria-label="date scrubber">
            <button onClick={() => setDate((d) => findPrevRunDate(d, runCardDates))} aria-label="previous date">
              ◀
            </button>
            <input
              type="date"
              value={date || ""}
              onChange={(e) => {
                if (e.target.value) setDate(e.target.value);
              }}
              className="mono date-picker-input"
              aria-label="select date"
            />
            <button onClick={() => setDate((d) => findNextRunDate(d, runCardDates))} aria-label="next date">
              ▶
            </button>
            {latestDate && date !== latestDate && (
              <button
                type="button"
                className="latest-jump-btn mono"
                onClick={() => setDate(latestDate)}
                title={`Jump to latest completed run: ${latestDate}`}
              >
                latest ⚡
              </button>
            )}
          </div>
          <div className="shell-header-right">
            <form className="symbol-search" onSubmit={submitSymbolSearch} role="search">
              <span aria-hidden="true">⌕</span>
              <input
                ref={searchInputRef}
                value={symbolSearch}
                onChange={(e) => setSymbolSearch(e.target.value)}
                placeholder="symbol search"
                aria-label="symbol search"
                list="symbol-suggestions"
                autoComplete="off"
              />
              <datalist id="symbol-suggestions">
                {suggestions.map((sym) => (
                  <option key={sym} value={sym} />
                ))}
              </datalist>
            </form>
            <FyersConnectionCard />
            <LiveReadiness />
            <div className="mode-toggle mono" role="group" aria-label="beginner expert mode">
              <button type="button" className={mode === "beginner" ? "active" : ""} onClick={() => setMode("beginner")}>
                beginner
              </button>
              <button type="button" className={mode === "expert" ? "active" : ""} onClick={() => setMode("expert")}>
                expert
              </button>
            </div>
            <button className="update-btn mono" onClick={startUpdate} disabled={liveWork.running}>
              {liveWork.running ? "⟳ UPDATING" : "⟳ UPDATE"}
            </button>
          </div>
        </header>

        <nav className="shell-tabs">
          <div className="shell-tabs-inner">
            {(densityValue.isExpert ? TABS : TABS.filter(t => t !== "ALPHA")).map((t) => (
              <button
                key={t}
                className={"tab-btn" + (t === tab && !tradePlan ? " active" : "")}
                onClick={() => {
                  // F7(a): top-nav clicks must exit the TRADE PLAN full-screen
                  // route -- tradePlan!=null short-circuits the tab body
                  // (see shell-body-inner below), so a bare setTab() here was
                  // a no-op while a plan was open. Clear the route first.
                  setTradePlan(null);
                  setTab(t);
                }}
              >
                {densityValue.isExpert ? (TAB_LABELS[t] || t) : (BEGINNER_TAB_LABELS[t] || t)}
              </button>
            ))}
            <button type="button" className="v5-live-trigger" onClick={() => liveWork.setOpen(true)}>
              {liveWork.running && <span className="v5-live-dot" aria-hidden="true" />}
              {liveWork.running ? `${liveWork.steps.filter((s) => s.status === "ok").length}/${liveWork.steps.length || "—"} live work` : "activity"}
            </button>
          </div>
        </nav>

        {offlineBanner && (
          <div className="stale-banner offline-fallback-banner">
            <span>⚠ {offlineBanner}</span>
          </div>
        )}
        {freshnessBanner && (
          <div className={"freshness-stamp mono" + (freshnessBanner.state !== "fresh" ? " freshness-stamp-amber" : "")}>
            {freshnessBanner.text}
          </div>
        )}
        {latestMeta && latestMeta.stale_build && (
          <div className="stale-banner">
            <span>⚠ desk running an older build - restart to pick up updates</span>
          </div>
        )}
        {isNoRunDay && nearestRunDate && (
          <div className="stale-banner no-run-banner">
            <span>
              ⚠ No run data for {date} — nearest is{" "}
              <button className="stale-banner-link" onClick={() => setDate(nearestRunDate)}>
                {nearestRunDate}
              </button>
            </span>
          </div>
        )}

        {/* Handoff 10: expert mode gets inline strip above main body */}
        {densityValue.isExpert && flowAvailable && (
          <CollapsedFlowStrip steps={flowSteps} currentStep={flowCurrent} />
        )}

        <main className="shell-body">
          <div className="shell-body-layout">
            {/* Handoff 10: beginner mode gets persistent side rail (toggle with `?`) */}
            {!densityValue.isExpert && flowAvailable && railOpen && (
              <GuidedFlowRail
                steps={flowSteps}
                currentStep={flowCurrent}
                onNavigate={navigateTab}
                onStartUpdate={startUpdate}
                onOpenTradePlan={openTradePlan}
              />
            )}
            {!densityValue.isExpert && flowAvailable && !railOpen && (
              <button type="button" className="gfr-reopen" onClick={() => setRailOpen(true)} title="Show guided flow (?)">
                guide 〉
              </button>
            )}
            <div className="shell-body-inner">
              {/* Handoff 10: tab purpose header — describes WHAT/HOW/NEXT for each tab */}
              {!tradePlan && <TabPurposeHeader tab={tab} />}
              {tradePlan ? (
                <>
                  {/* Handoff 13 task C: TRADE_PLAN purpose header */}
                  <TabPurposeHeader tab="TRADE_PLAN" />
                  <TradePlanTab
                    date={tradePlan.date}
                    symbol={tradePlan.symbol}
                    card={card}
                    onBackToDebate={() => closeTradePlan(tradePlan.symbol)}
                  />
                </>
              ) : (
                <>
                  {tab === "MARKET" && (
                    <MarketHomeTab date={date} card={card} loading={loading} error={error} onNavigate={navigateTab} />
                  )}
                  {tab === "SCANNERS" && (
                    <ScannersTab date={date} />
                  )}
                  {tab === "SHORTLIST" && <ShortlistTab date={date} onOpenTradePlan={openTradePlan} onNavigate={navigateTab} />}
                  {tab === "DEBATE" && (
                    <DebateTab
                      date={date}
                      card={card}
                      initialData={tapeDebate}
                      jumpSignal={debateJump}
                      onOpenTradePlan={openTradePlan}
                      onNavigate={navigateTab}
                    />
                  )}
                  {tab === "ALPHA" && <AlphaLab date={date} onNavigate={navigateTab} />}
                  {tab === "POSITIONS" && <PositionsTab date={date} onOpenOrigin={goToDebateOnDate} onRunDebate={runDebateFor} />}
                  {tab === "JOURNAL" && <LedgerTab />}
                </>
              )}
            </div>
          </div>
        </main>
        <LiveWorkInspector />

        {/* #28: keyboard shortcut help overlay (toggle with `?`) */}
        {helpOpen && (
          <div className="shortcut-help" role="dialog" aria-label="keyboard shortcuts">
            <div className="shortcut-help-head">
              <span>Keyboard shortcuts</span>
              <button type="button" className="shortcut-help-close" onClick={() => setHelpOpen(false)} aria-label="close">×</button>
            </div>
            <ul>
              <li><kbd>/</kbd> focus symbol search</li>
              <li><kbd>g</kbd> <kbd>h</kbd> MARKET</li>
              <li><kbd>g</kbd> <kbd>d</kbd> DEBATE</li>
              <li><kbd>g</kbd> <kbd>s</kbd> SHORTLIST</li>
              <li><kbd>g</kbd> <kbd>a</kbd> ALPHA</li>
              <li><kbd>g</kbd> <kbd>p</kbd> POSITIONS</li>
              <li><kbd>g</kbd> <kbd>j</kbd> JOURNAL</li>
              <li><kbd>?</kbd> {!densityValue.isExpert && flowAvailable ? "toggle guided rail" : "this help"}</li>
              <li><kbd>Esc</kbd> close panel / help</li>
            </ul>
          </div>
        )}
        
        <TraderProfileModal onProfileConfirmed={(p) => {
          console.log("Profile confirmed:", p);
        }} />
      </div>
    </DensityContext.Provider>
  );
}

export default function App() {
  return (
    <LiveWorkProvider>
      <DeskApp />
    </LiveWorkProvider>
  );
}

function PlaceholderPane({ label, note }) {
  return (
    <div className="empty-state placeholder-tab">
      <div className="empty-state-icon">○</div>
      <p className="empty-state-line">{label}</p>
      <p className="empty-state-sub">{note}</p>
    </div>
  );
}
