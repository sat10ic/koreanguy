// Shell. Tab state syncs to ?tab= so screens are deep-linkable without pulling
// in a router -- same approach as manas_os/desk.
//
// To add a screen: add it to NAV_TABS (or ALL_TABS for a dev-only route), add a
// render branch, add its screen file, AND add its ASCII section to
// design/WIREFRAMES.md first. The wireframe is the spec; the screenshot is
// diffed against it.
import React from "react";
import { fetchHealth } from "./api.js";
import { MockBanner } from "./components/ui.jsx";
import Feed from "./screens/Feed.jsx";
import Traders from "./screens/Traders.jsx";
import Ledger from "./screens/Ledger.jsx";
import Breadth from "./screens/Breadth.jsx";
import Ideas from "./screens/Ideas.jsx";
import Library from "./screens/Library.jsx";
import Style from "./screens/Style.jsx";

// W3c: the six product tabs are the visible navigation. STYLE is a
// development reference screen -- excluded from nav but still routed, so the
// deep link ?tab=STYLE keeps working for anyone holding it.
const NAV_TABS = ["FEED", "TRADERS", "LEDGER", "BREADTH", "IDEAS", "LIBRARY"];
const ALL_TABS = [...NAV_TABS, "STYLE"];

function initialTab() {
  const t = new URLSearchParams(window.location.search).get("tab");
  return ALL_TABS.includes(t) ? t : "FEED";
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

  // W3: the FEED badge counts open review items. A review decision changes
  // that count, so the fetch must be re-runnable -- not a mount-only effect --
  // and Feed needs a handle on it to refresh in the same session.
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
          <span className="brand">
            trader<em>log</em>
          </span>
          <nav className="tabs">
            {NAV_TABS.map((t) => (
              <button
                key={t}
                className={`tab${t === tab ? " active" : ""}`}
                onClick={() => navigate(t, {})}
              >
                {t}
                {t === "FEED" && reviewCount > 0 && (
                  <span className="tab-count">{reviewCount}</span>
                )}
              </button>
            ))}
          </nav>
        </div>
      </header>

      <MockBanner show={!!health?.is_mock} />

      <main className="page">
        {tab === "FEED" && <Feed refreshHealth={refreshHealth} onNavigate={navigate} />}
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
        {tab === "BREADTH" && <Breadth />}
        {tab === "IDEAS" && <Ideas onNavigate={navigate} />}
        {tab === "LIBRARY" && <Library />}
        {tab === "STYLE" && <Style />}
      </main>
    </div>
  );
}
