import React, { useEffect, useState } from "react";
import Today from "./screens/Today.jsx";

/**
 * The deck — a fresh front end over the existing manas.db and API.
 *
 * Five screens, built one at a time. A screen appears in the nav only once it is
 * real; the rest are visibly disabled rather than shipped as empty shells.
 *
 *   TODAY       can I trade at all?            <- built
 *   CANDIDATES  the <=5 names, or nothing      <- after PB-1 has a detector
 *   PLAN        entry / stop / size / exit
 *   POSITIONS   what I hold, what to do today
 *   JOURNAL     the stats table
 *
 * Nothing here is ported from the old desk app except MarketQuadrant, which was
 * written for this and briefly patched into the wrong tree.
 */

const SCREENS = [
  { key: "TODAY", label: "TODAY", ready: true },
  { key: "CANDIDATES", label: "CANDIDATES", ready: false },
  { key: "PLAN", label: "PLAN", ready: false },
  { key: "POSITIONS", label: "POSITIONS", ready: false },
  { key: "JOURNAL", label: "JOURNAL", ready: false },
];

export default function App() {
  const [screen, setScreen] = useState("TODAY");
  const [date, setDate] = useState(null);

  useEffect(() => {
    // Latest session the data actually covers, not today's wall clock.
    fetch("/api/regime/breadth-analytics?days=1")
      .then((r) => r.json())
      .then((d) => {
        const rows = d?.rows || [];
        if (rows.length) setDate(rows[rows.length - 1].trade_date);
      })
      .catch(() => {});
  }, []);

  return (
    <div className="deck">
      <nav className="deck-nav" aria-label="Screens">
        {SCREENS.map((s) => (
          <button
            key={s.key}
            onClick={() => s.ready && setScreen(s.key)}
            disabled={!s.ready}
            aria-current={screen === s.key}
            title={s.ready ? undefined : "Not built yet"}
          >
            {s.label}
          </button>
        ))}
      </nav>

      {screen === "TODAY" && <Today date={date} />}
      {screen !== "TODAY" && (
        <div className="deck-stub">{screen} is not built yet.</div>
      )}
    </div>
  );
}
