// Shell. Tab state syncs to ?tab= so screens are deep-linkable without pulling
// in a router. SCOUTING × WIRE rewrite (2026-08-24): FEED became TODAY and
// BREADTH became MARKET; STYLE stays routed but out of the visible nav, and
// SYMBOL is the symbol landing route (?tab=SYMBOL&symbol=X). The ⌘K command
// bar mounts here and navigates through the same navigate() as everything
// else.
//
// To add a screen: add it to NAV_TABS (or ALL_TABS for a route-only tab), add
// a render branch, add its screen file, AND add its ASCII section to
// design/WIREFRAMES.md first. The wireframe is the spec; the screenshot is
// diffed against it.
import React from "react";
import { fetchHealth } from "./api.js";
import { MockBanner } from "./components/ui.jsx";
import CommandBar from "./components/CommandBar.jsx";
import Today from "./screens/Today.jsx";
import Ledger from "./screens/Ledger.jsx";
import Traders from "./screens/Traders.jsx";
import Ideas from "./screens/Ideas.jsx";
import Library from "./screens/Library.jsx";
import Market from "./screens/Market.jsx";
import Style from "./screens/Style.jsx";
import Symbol from "./screens/Symbol.jsx";

// The six product tabs are the visible navigation, uppercase labels. STYLE
// (development reference) and SYMBOL (landing page) are route-only — never in
// the visible nav.
const NAV_TABS = ["TODAY", "LEDGER", "TRADERS", "IDEAS", "LIBRARY", "MARKET"];
const ALL_TABS = [...NAV_TABS, "STYLE", "SYMBOL"];

// Old deep links: ?tab=FEED pointed at what is now TODAY, ?tab=BREADTH at what
// is now MARKET. Map them so a stale link still lands; the URL-sync effect
// below rewrites the param to the new name on first render.
function initialTab() {
  const t = new URLSearchParams(window.location.search).get("tab");
  if (ALL_TABS.includes(t)) return t;
  if (t === "FEED") return "TODAY";
  if (t === "BREADTH") return "MARKET";
  return "TODAY";
}

// C2: the preselection a screen opens with -- ?tab=TRADERS&handle=X,
// ?tab=LEDGER&symbol=Y, ?tab=LEDGER&position=Z. Same "no router" approach
// as the tab param above: read once on mount, kept in sync on navigate().
const NAV_PARAM_KEYS = ["handle", "symbol", "position"];
function initialNavParams() {
  const usp = new URLSearchParams(window.location.search);
  const params = {};
  NAV_PARAM_KEYS.forEach((k) => {
    const v = usp.get(k);
    if (v) params[k] = v;
  });
  return params;
}

export default function App() {
  const [tab, setTab] = React.useState(initialTab);
  const [navParams, setNavParams] = React.useState(initialNavParams);
  const [health, setHealth] = React.useState(null);

  // Passed down to every screen so any handle/symbol/position it renders can
  // jump to another tab with that value pre-selected there. One function,
  // no router: it just moves tab + navParams state, and the effect below
  // mirrors both into the URL so the destination is still a real deep link.
  const navigate = React.useCallback((toTab, params = {}) => {
    setTab(toTab);
    setNavParams(params);
  }, []);

  // W3: the TODAY badge counts open review items. A review decision changes
  // that count, so the fetch must be re-runnable -- not a mount-only effect --
  // and Today needs a handle on it to refresh in the same session.
  const refreshHealth = React.useCallback(() => {
    return fetchHealth().then(setHealth).catch(() => setHealth(null));
  }, []);

  React.useEffect(() => {
    refreshHealth();
  }, [refreshHealth]);

  React.useEffect(() => {
    const url = new URL(window.location);
    url.searchParams.set("tab", tab);
    NAV_PARAM_KEYS.forEach((k) => {
      if (navParams[k]) url.searchParams.set(k, navParams[k]);
      else url.searchParams.delete(k);
    });
    window.history.replaceState({}, "", url);
  }, [tab, navParams]);

  const reviewCount = health?.counts?.review_open || 0;

  return (
    <div className="shell">
      <header className="topbar">
        <div className="topbar-in">
          <span className="brand">traderlog</span>
          <nav className="tabs" aria-label="Sections">
            {NAV_TABS.map((t) => (
              <button
                key={t}
                className={`tab${t === tab ? " active" : ""}`}
                onClick={() => navigate(t, {})}
              >
                {t}
                {t === "TODAY" && reviewCount > 0 && (
                  <span className="tab-count">{reviewCount}</span>
                )}
              </button>
            ))}
          </nav>
        </div>
      </header>

      <MockBanner show={!!health?.is_mock} />

      <main className="page">
        {tab === "TODAY" && <Today refreshHealth={refreshHealth} onNavigate={navigate} />}
        {tab === "TRADERS" && (
          <Traders presetHandle={navParams.handle} onNavigate={navigate} />
        )}
        {tab === "LEDGER" && (
          <Ledger
            presetSymbol={navParams.symbol}
            presetPositionId={navParams.position}
            onNavigate={navigate}
          />
        )}
        {tab === "IDEAS" && <Ideas onNavigate={navigate} />}
        {tab === "LIBRARY" && <Library />}
        {tab === "MARKET" && <Market onNavigate={navigate} />}
        {tab === "STYLE" && <Style />}
        {tab === "SYMBOL" && <Symbol symbol={navParams.symbol} onNavigate={navigate} />}
      </main>

      <CommandBar onNavigate={navigate} />
    </div>
  );
}