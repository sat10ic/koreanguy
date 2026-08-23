// Shell. Tab state syncs to ?tab= so screens are deep-linkable without pulling
// in a router -- same approach as manas_os/desk.
//
// To add a screen: add it to TABS, add a render branch, add its screen file,
// AND add its ASCII section to design/WIREFRAMES.md first. The wireframe is the
// spec; the screenshot is diffed against it.
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

const TABS = ["FEED", "TRADERS", "LEDGER", "BREADTH", "IDEAS", "LIBRARY", "STYLE"];

function initialTab() {
  const t = new URLSearchParams(window.location.search).get("tab");
  return TABS.includes(t) ? t : "FEED";
}

export default function App() {
  const [tab, setTab] = React.useState(initialTab);
  const [health, setHealth] = React.useState(null);

  React.useEffect(() => {
    fetchHealth().then(setHealth).catch(() => setHealth(null));
  }, []);

  React.useEffect(() => {
    const url = new URL(window.location);
    url.searchParams.set("tab", tab);
    window.history.replaceState({}, "", url);
  }, [tab]);

  const reviewCount = health?.counts?.review_open || 0;

  return (
    <div className="shell">
      <header className="topbar">
        <span className="brand">
          trader<em>log</em>
        </span>
        <nav className="tabs">
          {TABS.map((t) => (
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
      </header>

      <MockBanner show={!!health?.is_mock} />

      <main className="page">
        {tab === "FEED" && <Feed />}
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
