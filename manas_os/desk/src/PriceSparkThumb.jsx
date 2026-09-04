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
  const [stalled, setStalled] = useState(false);

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
    // R2026-07-19: some render contexts (backgrounded/inactive tabs, certain
    // embedded/automation viewports) never fire an IntersectionObserver
    // callback at all, which used to leave the card waiting on `near`
    // forever. Force the fetch attempt after 2s regardless so a card can
    // never get permanently stuck before it has even tried.
    const fallback = setTimeout(() => setNear(true), 2000);
    return () => {
      observer.disconnect();
      clearTimeout(fallback);
    };
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

  // R2026-07-19: never show an infinite "loading chart" spinner. If nothing
  // has resolved within 5s (dead endpoint, stalled network, a `near` that
  // never triggers), fall back to an honest static hint -- clicking the
  // thumbnail always opens the full chart drawer regardless of this
  // sparkline's state, so "chart on click" is true even when stalled.
  useEffect(() => {
    if (state === "ready" || state === "empty" || state === "error") {
      setStalled(false);
      return undefined;
    }
    setStalled(false);
    const t = setTimeout(() => setStalled(true), 5000);
    return () => clearTimeout(t);
  }, [state, near, symbol, date]);

  const points = useMemo(() => pointsFor(bars), [bars]);

  let label = null;
  if (!points) {
    if (state === "error") label = "chart unavailable";
    else if (state === "empty") label = "not enough chart data";
    else if (state === "ready") label = "chart data incomplete";
    else if (stalled) label = "chart on click";
    else label = "loading chart";
  }

  return (
    <div ref={hostRef} className={className} aria-label={`${symbol} price thumbnail`}>
      {points ? (
        <svg viewBox="0 0 120 48" role="img" aria-label={`${symbol} recent closing-price sparkline`}>
          <polyline points={points} fill="none" stroke="currentColor" strokeWidth="2" vectorEffect="non-scaling-stroke" />
        </svg>
      ) : (
        <span className="mono-num">{label}</span>
      )}
    </div>
  );
}

export { pointsFor };
