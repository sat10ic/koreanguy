import React, { useEffect, useState } from "react";
import { fetchPositions } from "./api.js";

const SPARK_W = 460;
const SPARK_H = 80;
const SPARK_PAD = 10;

function round(n, digits = 1) {
  if (n === null || n === undefined) return "—";
  const f = Math.pow(10, digits);
  return Math.round(n * f) / f;
}

function phaseForR(r) {
  if (r === null || r === undefined) return "INITIATION";
  if (r >= 2) return "EXTENSION";
  if (r >= 1) return "TREND";
  return "INITIATION";
}

function RPathSparkline({ position }) {
  const points = position.r_path || [];
  const entry = position.entry;
  const stop = position.stop;
  const risk = entry !== null && entry !== undefined && stop !== null && stop !== undefined ? entry - stop : null;
  const trailR =
    risk && risk > 0 && position.trail_stop !== null && position.trail_stop !== undefined
      ? (position.trail_stop - entry) / risk
      : null;

  if (points.length === 0) {
    return <div className="rpath-empty mono">R-path unavailable (no priced sessions yet)</div>;
  }

  const rValues = points.map((p) => p.r);
  const allValues = trailR !== null ? [...rValues, trailR, 0] : [...rValues, 0];
  const rMin = Math.min(...allValues);
  const rMax = Math.max(...allValues);
  const span = rMax - rMin || 1;
  const innerH = SPARK_H - SPARK_PAD * 2;
  const innerW = SPARK_W - SPARK_PAD * 2;

  const yFor = (r) => SPARK_PAD + innerH - ((r - rMin) / span) * innerH;
  const xFor = (i) => SPARK_PAD + (points.length === 1 ? 0 : (i / (points.length - 1)) * innerW);

  const linePoints = points.map((p, i) => `${xFor(i)},${yFor(p.r)}`).join(" ");

  // Phase bands: contiguous runs of the same phase along the R-path.
  const bands = [];
  let bandStart = 0;
  let bandPhase = phaseForR(points[0].r);
  for (let i = 1; i <= points.length; i += 1) {
    const phase = i < points.length ? phaseForR(points[i].r) : null;
    if (phase !== bandPhase) {
      bands.push({ phase: bandPhase, x0: xFor(bandStart), x1: xFor(i - 1) });
      bandStart = i;
      bandPhase = phase;
    }
  }

  const bandColor = { INITIATION: "var(--bg-sunken)", TREND: "var(--accent-soft)", EXTENSION: "var(--positive-soft)" };
  const bandLabel = { INITIATION: "INITIATION", TREND: "TREND", EXTENSION: "EXTENSION" };
  const zeroY = yFor(0);

  return (
    <svg className="rpath-svg" viewBox={`0 0 ${SPARK_W} ${SPARK_H}`} preserveAspectRatio="none">
      {bands.map((b, i) => (
        <rect
          key={i}
          x={Math.min(b.x0, b.x1)}
          y={0}
          width={Math.max(Math.abs(b.x1 - b.x0), 1)}
          height={SPARK_H}
          fill={bandColor[b.phase]}
        />
      ))}
      <line x1={SPARK_PAD} y1={zeroY} x2={SPARK_W - SPARK_PAD} y2={zeroY} stroke="var(--border)" strokeWidth="1" />
      {trailR !== null && (
        <line
          x1={SPARK_PAD}
          y1={yFor(trailR)}
          x2={SPARK_W - SPARK_PAD}
          y2={yFor(trailR)}
          stroke="var(--warn)"
          strokeWidth="1"
          strokeDasharray="4 3"
        />
      )}
      <polyline points={linePoints} fill="none" stroke="var(--accent)" strokeWidth="2" />
      <circle cx={xFor(points.length - 1)} cy={yFor(points[points.length - 1].r)} r="3" fill="var(--accent)" />
    </svg>
  );
}

function OriginalThesisBox({ thesis }) {
  if (!thesis || thesis.note) {
    return (
      <div className="thesis-box mono">
        <p className="panel-title small-caps">Original thesis</p>
        <p>no agent thesis</p>
      </div>
    );
  }
  const label = thesis.agent ? `${thesis.agent}${thesis.scan_date ? `, ${thesis.scan_date}` : ""}` : thesis.scan_date || "—";
  return (
    <div className="thesis-box">
      <p className="panel-title small-caps">Original thesis ({label})</p>
      <p className="thesis-quote">&ldquo;{thesis.bull_case || "—"}&rdquo;</p>
    </div>
  );
}

function TelegramMirror({ coach }) {
  if (!coach) {
    return <div className="telegram-mirror mono">no coach signal sent yet</div>;
  }
  const status = coach.sent ? `✔ sent ${(coach.created_at || "").slice(11, 16) || ""}` : "dry-run: shown, not sent";
  return (
    <div className="telegram-mirror mono">
      {status} &nbsp;&ldquo;{coach.message}&rdquo;
    </div>
  );
}

function PositionCard({ position }) {
  const urgent = position.urgent;
  return (
    <div className={"panel position-card" + (urgent ? " urgent" : "")}>
      <div className="position-card-header">
        {urgent && <span className="urgent-icon">⛔</span>}
        <span className="position-symbol">{position.symbol}</span>
        <span className="position-meta mono">
          open &middot; entry {position.trade_date} @ {round(position.entry, 2)}
        </span>
        {urgent && <span className="urgent-label">EXIT NOW &mdash; {(position.fired || []).join(", ") || "two-strike rule"} fired</span>}
      </div>

      <RPathSparkline position={position} />
      <p className="rpath-caption mono">
        now {position.r !== null && position.r !== undefined ? `${position.r >= 0 ? "+" : ""}${round(position.r, 2)}R` : "—"}
        &nbsp;&middot;&nbsp; trail stop {round(position.trail_stop, 2)} &nbsp;&middot;&nbsp; phase {position.phase || "—"}
      </p>

      <div className={"coach-line" + (urgent ? " urgent" : "")}>
        <span className="coach-dot">●</span> {position.action_line}
      </div>
      {position.banner && <p className="position-banner mono">{position.banner}</p>}

      <OriginalThesisBox thesis={position.original_thesis} />

      <TelegramMirror coach={position.coach} />
    </div>
  );
}

export default function PositionsTab({ date }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetchPositions(date)
      .then((body) => {
        if (!cancelled) setData(body);
      })
      .catch((err) => {
        if (!cancelled) setError(String(err));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [date]);

  if (loading) {
    return <div className="empty-state">Loading…</div>;
  }
  if (error) {
    return <div className="empty-state">{error}</div>;
  }
  if (!data || !data.positions || data.positions.length === 0) {
    return (
      <div className="empty-state">No open positions. Entry signals appear here once the desk takes a name.</div>
    );
  }

  return (
    <div>
      {data.positions.map((p) => (
        <PositionCard key={p.trade_id} position={p} />
      ))}
    </div>
  );
}
