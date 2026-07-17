import React, { useEffect, useMemo, useRef, useState } from "react";
import { fetchChartData } from "./api.js";

function pointsFor(bars, width = 120, height = 48) {
  const closes = (bars || []).slice(-60).map((bar) => Number(bar.close)).filter(Number.isFinite);
  if (closes.length < 2) return "";
  const low = Math.min(...closes);
  const high = Math.max(...closes);
  const span = Math.max(high - low, Number.EPSILON);
  return closes.map((close, index) => {
    const x = (index / (closes.length - 1)) * width;
    const y = height - ((close - low) / span) * (height - 4) - 2;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(" ");
}

export default function PriceSparkThumb({ date, symbol, className = "" }) {
  const hostRef = useRef(null);
  const [near, setNear] = useState(false);
  const [bars, setBars] = useState([]);
  const [state, setState] = useState("idle");

  useEffect(() => {
    const node = hostRef.current;
    if (!node || typeof IntersectionObserver === "undefined") {
      setNear(true);
      return undefined;
    }
    const observer = new IntersectionObserver(
      ([entry]) => entry.isIntersecting && setNear(true),
      { rootMargin: "160px" },
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (!near || !symbol) return undefined;
    let cancelled = false;
    setState("loading");
    fetchChartData(symbol, date)
      .then((payload) => {
        if (cancelled) return;
        const next = payload?.available ? payload.bars || [] : [];
        setBars(next);
        setState(next.length > 1 ? "ready" : "empty");
      })
      .catch(() => !cancelled && setState("error"));
    return () => { cancelled = true; };
  }, [date, near, symbol]);

  const points = useMemo(() => pointsFor(bars), [bars]);
  return (
    <div ref={hostRef} className={className} aria-label={`${symbol} price thumbnail`}>
      {points ? (
        <svg viewBox="0 0 120 48" role="img" aria-label={`${symbol} recent closing-price sparkline`}>
          <polyline points={points} fill="none" stroke="currentColor" strokeWidth="2" vectorEffect="non-scaling-stroke" />
        </svg>
      ) : (
        <span className="mono-num">{state === "error" ? "chart unavailable" : "loading chart"}</span>
      )}
    </div>
  );
}

export { pointsFor };
