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

export default function App() {
  const [tab, setTab] = React.useState(initialTab);
  const [health, setHealth] = React.useState(null);

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
    window.history.replaceState({}, "", url);
  }, [tab]);

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
                onClick={() => setTab(t)}
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
        {tab === "FEED" && <Feed refreshHealth={refreshHealth} />}
        {tab === "TRADERS" && <Traders />}
        {tab === "LEDGER" && <Ledger />}
        {tab === "BREADTH" && <Breadth />}
        {tab === "IDEAS" && <Ideas />}
        {tab === "LIBRARY" && <Library />}
        {tab === "STYLE" && <Style />}
      </main>
    </div>
  );
}
