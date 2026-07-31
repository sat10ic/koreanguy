import React, { useEffect, useState } from "react";
import MarketQuadrant from "../components/MarketQuadrant.jsx";
import "../components/MarketQuadrant.css";
import { fetchRegime } from "../api.js";

/**
 * TODAY — can I trade, and how hard?
 *
 * One question, answered by the quadrant. Nothing else on this screen. The old
 * app answered this with 29 panels; the audit showed 26 measured characteristics
 * carried no signal, so more panels is not the missing ingredient.
 */
export default function Today({ date }) {
  const [regime, setRegime] = useState(null);

  useEffect(() => {
    if (!date) return;
    let alive = true;
    fetchRegime(date)
      .then((d) => alive && setRegime(d))
      .catch(() => {});
    return () => {
      alive = false;
    };
  }, [date]);

  if (!date) return <div className="deck-stub">Loading the latest session…</div>;

  const mode = regime?.market_mode || regime?.regime?.market_mode || null;

  return (
    <div>
      <MarketQuadrant date={date} mode={mode} />
    </div>
  );
}
