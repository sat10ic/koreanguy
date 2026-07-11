import React, { useEffect, useState } from "react";

// v5 primitive: infinite-loop ticker tape (duplicated track for seamless
// scroll) with edge fades. Honors prefers-reduced-motion by rendering a
// static, non-animated row instead of looping. `items`: [{ symbol, tag
// ("take"|"skip"), tagLabel, metricLabel, metricValue }]. When `items` is
// empty, renders a single honest "no debate for {date}" row instead of
// looping empty space.
export default function TickerTape({ items, emptyLabel }) {
  const [reduced, setReduced] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined" || !window.matchMedia) return undefined;
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReduced(mq.matches);
    const onChange = (e) => setReduced(e.matches);
    mq.addEventListener ? mq.addEventListener("change", onChange) : mq.addListener(onChange);
    return () => {
      mq.removeEventListener ? mq.removeEventListener("change", onChange) : mq.removeListener(onChange);
    };
  }, []);

  if (!items || items.length === 0) {
    return (
      <div className="v5-tape-outer">
        <div className="v5-tape-empty">{emptyLabel || "no debate for this date"}</div>
      </div>
    );
  }

  const renderItems = (keyPrefix) =>
    items.map((it, i) => (
      <span className="v5-tape-item" key={`${keyPrefix}-${it.symbol}-${i}`}>
        <span className="v5-tape-sym">{it.symbol}</span>
        {it.tag && <span className={"v5-tape-tag v5-" + it.tag}>{it.tagLabel || it.tag.toUpperCase()}</span>}
        {it.metricLabel && (
          <span className="v5-tape-metric">
            {it.metricLabel} <b className="mono-num">{it.metricValue ?? "—"}</b>
          </span>
        )}
      </span>
    ));

  return (
    <div className="v5-tape-outer">
      <div className={"v5-tape-track" + (reduced ? " v5-tape-static" : "")}>
        {renderItems("a")}
        {!reduced && renderItems("b")}
      </div>
    </div>
  );
}
