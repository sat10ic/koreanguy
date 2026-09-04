import React, { useEffect, useMemo, useState } from "react";
import { fetchFootprintBoard } from "../../api.js";
import { StickerRow } from "./Sticker.jsx";
import SectionLabel from "./SectionLabel.jsx";
import { deriveTier } from "../../stickers.js";
import "./FlowBoard.v5.css";

// ============================================================
// Flow Board — the score x volume x direction matrix.
// Spec: manas_os/design/FOOTPRINT_DRIVER_SPEC_2026-07-18.md
//   "UI — FLOW BOARD + STICKER REGISTRY" -> "Flow Board" subsection.
// Data: GET /api/footprint/board?date= (backend already live).
// Five lanes, in the exact order the spec names them.
// sticker: null for lanes that don't have a sticker in the initial
// registry set (public_markup / retail_churn) — no fabrication.
// ============================================================

const LANES = [
  {
    key: "silent_accumulation",
    title: "Silent Accumulation",
    read: "Institutions absorbing quietly — unusual score, volume NOT elevated, price flat in a base. Volume screens miss this by design.",
    sticker: "SA",
  },
  {
    key: "absorption",
    title: "Absorption",
    read: "A Wyckoff-style flush met by size — high volume, down day, narrow range. Bullish if it happens in or near a base.",
    sticker: "AB",
  },
  {
    key: "public_markup",
    title: "Public Markup",
    read: "Everyone sees it now — unusual score, high volume, up on a breakout day. Confirmation, not early.",
    sticker: null,
  },
  {
    key: "retail_churn",
    title: "Retail Churn",
    read: "Small prints driving the volume, not institutions — low score, high volume. Fade-grade evidence.",
    sticker: null,
  },
  {
    key: "silent_offloading",
    title: "Silent Offloading",
    read: "Big prints selling into strength near highs while price holds up — exit-side caution on a holding.",
    sticker: "SO",
  },
];

function fmtScore(v) {
  return v === null || v === undefined || Number.isNaN(Number(v)) ? "—" : Number(v).toFixed(1);
}

function fmtFlow(v) {
  if (v === null || v === undefined || Number.isNaN(Number(v))) return "—";
  const n = Number(v);
  return `${n >= 0 ? "+" : ""}${n.toFixed(1)}`;
}

function NetFlowBar({ value, maxAbs }) {
  const v = Number(value) || 0;
  const pct = maxAbs > 0 ? Math.min(100, (Math.abs(v) / maxAbs) * 100) : 0;
  const positive = v >= 0;
  return (
    <span className="fb-netbar-track" title={`net silent flow ${fmtFlow(v)} (20d, delivery-weighted)`}>
      <span
        className={"fb-netbar" + (positive ? " fb-netbar-pos" : " fb-netbar-neg")}
        style={{ width: `${Math.max(v === 0 ? 0 : 6, pct)}%` }}
      />
    </span>
  );
}

function SymbolChip({ entry, laneStickerCode, maxAbsFlow, onOpen }) {
  const tier = deriveTier(entry.score);
  const codes = [];
  if (laneStickerCode) codes.push(laneStickerCode);
  if (tier) codes.push("FP");
  const details = tier ? { FP: `score ${fmtScore(entry.score)}, tier ${tier}` } : undefined;

  return (
    <div className="fb-chip">
      <button
        type="button"
        className="fb-chip-symbol-btn"
        onClick={() => onOpen?.(entry.symbol)}
        title={`Open ${entry.symbol} chart`}
      >
        {entry.symbol}
      </button>
      {codes.length > 0 && (
        <StickerRow codes={codes} details={details} onSelect={() => onOpen?.(entry.symbol)} className="fb-chip-stickers" />
      )}
      <span className="fb-chip-meta mono-num">
        <span className="fb-chip-balance" title="silent accumulation/distribution days (20d): accum/dist">
          {entry.balance || "—"}
        </span>
        <span className="fb-chip-score" title="footprint score, today">
          {fmtScore(entry.score)}
        </span>
        {typeof entry.streak_days === "number" && entry.streak_days > 0 && (
          <span className="fb-chip-streak" title="consecutive abnormal-score sessions">
            {entry.streak_days}d
          </span>
        )}
      </span>
      <span className="fb-chip-flow-row">
        <NetFlowBar value={entry.net_silent_flow} maxAbs={maxAbsFlow} />
        <span className="fb-chip-flow-val mono-num">{fmtFlow(entry.net_silent_flow)}</span>
      </span>
    </div>
  );
}

function Lane({ lane, entries, onOpen }) {
  const sorted = useMemo(
    () => [...entries].sort((a, b) => Math.abs(Number(b.net_silent_flow) || 0) - Math.abs(Number(a.net_silent_flow) || 0)),
    [entries],
  );
  const maxAbsFlow = useMemo(
    () => sorted.reduce((m, e) => Math.max(m, Math.abs(Number(e.net_silent_flow) || 0)), 0),
    [sorted],
  );

  return (
    <div className="fb-lane">
      <div className="fb-lane-hd">
        <span className="fb-lane-title">{lane.title}</span>
        <span className="fb-lane-count mono-num">{entries.length}</span>
      </div>
      <p className="fb-lane-read">{lane.read}</p>
      {sorted.length === 0 ? (
        <p className="fb-lane-empty">none today</p>
      ) : (
        <div className="fb-lane-row">
          {sorted.map((entry) => (
            <SymbolChip key={entry.symbol} entry={entry} laneStickerCode={lane.sticker} maxAbsFlow={maxAbsFlow} onOpen={onOpen} />
          ))}
        </div>
      )}
    </div>
  );
}

// FlowBoard: date -> board fetch; onOpenChart(symbol) -> caller's existing
// ChartDrawer open handler (same pattern as ShortlistRow's onChart).
export default function FlowBoard({ date, onOpenChart }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetchFootprintBoard(date)
      .then((body) => {
        if (!cancelled) setData(body);
      })
      .catch((err) => {
        if (!cancelled) setError(String(err.message || err));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [date]);

  const lanesData = data?.lanes || {};
  const totalNames = LANES.reduce((sum, lane) => sum + (lanesData[lane.key]?.length || 0), 0);

  return (
    <div className="fb-board">
      <SectionLabel count={loading ? "loading…" : data?.available ? `${totalNames} names · as of ${data.date || date}` : undefined}>
        Flow Board — footprint x volume x direction
      </SectionLabel>
      <p className="fb-caption">
        Five lanes read what today's institutional footprint activity looks like from outside — score never sizes or authors
        risk; it only says where to look. Symbols click through to the chart.
      </p>
      {error && <p className="fb-error">Flow Board failed to load: {error}</p>}
      {!error && !loading && data && !data.available && (
        <p className="fb-empty">Footprint board not available for {date} yet.</p>
      )}
      {!error && (loading || (data && data.available)) && (
        <div className="fb-lanes">
          {LANES.map((lane) => (
            <Lane key={lane.key} lane={lane} entries={lanesData[lane.key] || []} onOpen={onOpenChart} />
          ))}
        </div>
      )}
    </div>
  );
}
