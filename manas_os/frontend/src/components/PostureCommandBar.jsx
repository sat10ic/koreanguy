import { useEffect, useState } from "react";
import InfoDot from "./InfoDot.jsx";
import Read from "./Read.jsx";
import DivergenceFlag from "./DivergenceFlag.jsx";
import { getBreadthHistory, getRegimeHistory } from "../api.js";

/**
 * PostureCommandBar — replaces the vague 8-tile "Posture" StripCard (design
 * §1.2). A Direction-B "briefing" banner: big posture badge + a two-line
 * concrete instruction generated from fields already in /api/regime/summary,
 * plus the DivergenceFlag caution folded into its footer (design §1.6: move
 * DivergenceFlag "to render inside PostureCommandBar footer so the caution
 * sits with the posture read").
 */
const POSTURE = {
  RISK_ON: { cls: "bg-bull text-white border-bull", label: "Risk-On", band: "bull" },
  SELECTIVE: { cls: "bg-warn text-white border-warn", label: "Selective", band: "warn" },
  DEFENSIVE: { cls: "bg-bear text-white border-bear", label: "Defensive", band: "bear" },
  NO_TRADE: { cls: "bg-ink text-white border-ink", label: "No Trade", band: "muted" },
};
const POSTURE_FALLBACK = { cls: "bg-muted text-white border-muted", label: "Unknown", band: "muted" };

// Approach table — deterministic, coded literally per design §1.2. Keyed to
// market_mode; STALE/DEGRADED is handled by the `stale` prop overriding this.
const APPROACH = {
  RISK_ON: { positions: "up to 5", size: "full", setups: "A & B setups" },
  SELECTIVE: { positions: "2–3 max", size: "half", setups: "A-setups only" },
  DEFENSIVE: { positions: "0–1", size: "quarter", setups: "flawless only" },
  NO_TRADE: { positions: "0", size: "—", setups: "sit out" },
};

export default function PostureCommandBar({ data, stale }) {
  const posture = stale ? POSTURE_FALLBACK : POSTURE[data.market_mode] || POSTURE_FALLBACK;
  const approach = stale ? null : APPROACH[data.market_mode] || null;
  const breadthRead = useBreadthReadLine();
  const deltas = useSinceYesterdayDeltas();

  return (
    <section
      data-testid="posture-command-bar"
      className={
        "mb-4 border border-hairline p-4 " +
        (stale ? "bg-muted-bg" : { bull: "bg-bull-bg", warn: "bg-warn-bg", bear: "bg-bear-bg", muted: "bg-muted-bg" }[posture.band])
      }
    >
      <div className="flex flex-wrap items-start gap-4">
        <div className="flex flex-col items-center gap-1">
          <span
            data-testid="posture-badge"
            className={
              "inline-flex items-center rounded-chip border px-3 py-1.5 font-mono text-[16px] font-bold uppercase tracking-overline " +
              posture.cls
            }
          >
            {stale ? "Stale" : posture.label}
            <InfoDot term="posture" />
          </span>
        </div>

        <div className="min-w-[260px] flex-1">
          {breadthRead && (
            <p className="font-sans text-[12px] leading-snug text-ink2">{breadthRead}</p>
          )}
          {deltas && <DeltaRow deltas={deltas} />}
          {stale ? (
            <p className="mt-1 font-mono text-[11px] font-bold uppercase tracking-overline text-muted">
              APPROACH: wait for fresh data before sizing risk
            </p>
          ) : approach ? (
            <p className="mt-1 font-mono text-[11px] font-bold uppercase tracking-overline text-ink">
              APPROACH: trade {approach.positions} positions, {approach.size} size, {approach.setups}. Risk{" "}
              {fmtPct(data.allowed_risk_min_pct)}–{fmtPct(data.allowed_risk_max_pct)} per trade.
            </p>
          ) : null}
          {data.explanation_text && <Read band={posture.band}>{data.explanation_text}</Read>}
        </div>
      </div>

      <div className="mt-3 border-t border-dashed border-hairline2 pt-2">
        <DivergenceFlag />
      </div>
    </section>
  );
}

// Since-yesterday delta chips (design: beginner reads direction before
// magnitude) — three small ▲/▼ chips comparing the latest session to the
// prior one: XP, 4.5R burst, and %-above-20DMA. XP/r4p5 come from
// /api/regime/history (already returns both per row); %>20DMA comes from
// /api/regime/breadth-history since breadth isn't on regime_snapshots.
function DeltaRow({ deltas }) {
  return (
    <div data-testid="since-yesterday-deltas" className="mt-1 flex flex-wrap items-center gap-2">
      <span className="font-mono text-[9px] uppercase tracking-overline text-ink3">
        Since yesterday
      </span>
      <DeltaChip label="XP" delta={deltas.xp} fmt={(n) => n.toFixed(1)} />
      <DeltaChip label="4.5R" delta={deltas.r4p5} fmt={(n) => n.toFixed(0)} />
      <DeltaChip label="%>20DMA" delta={deltas.pct20dma} fmt={(n) => `${n.toFixed(0)}pp`} />
    </div>
  );
}

function DeltaChip({ label, delta, fmt }) {
  if (delta == null) return null;
  const up = delta > 0;
  const flat = delta === 0;
  const cls = flat ? "text-muted" : up ? "text-bull" : "text-bear";
  const arrow = flat ? "—" : up ? "▲" : "▼";
  return (
    <span
      data-testid={`delta-chip-${label.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`}
      className={"inline-flex items-center gap-1 font-mono text-[10px] font-bold " + cls}
    >
      {arrow} {label} {fmt(Math.abs(delta))}
    </span>
  );
}

function useSinceYesterdayDeltas() {
  const [deltas, setDeltas] = useState(null);
  useEffect(() => {
    let cancelled = false;
    Promise.all([getRegimeHistory(2), getBreadthHistory(2)])
      .then(([hist, breadth]) => {
        if (cancelled) return;
        const hRows = hist?.rows || [];
        const bRows = (breadth?.rows || []).filter((r) => r?.pct_above_20dma != null);
        if (hRows.length < 2 && bRows.length < 2) return setDeltas(null);

        const xp = diffLatestTwo(hRows, "xp_value");
        const r4p5 = diffLatestTwo(hRows, "r4p5");
        const pct20dma = diffLatestTwo(bRows, "pct_above_20dma");
        if (xp == null && r4p5 == null && pct20dma == null) return setDeltas(null);
        setDeltas({ xp, r4p5, pct20dma });
      })
      .catch(() => !cancelled && setDeltas(null));
    return () => {
      cancelled = true;
    };
  }, []);
  return deltas;
}

function diffLatestTwo(rows, field) {
  if (rows.length < 2) return null;
  const latest = rows[rows.length - 1]?.[field];
  const prev = rows[rows.length - 2]?.[field];
  if (latest == null || prev == null) return null;
  return latest - prev;
}

// Breadth isn't a field on regime_snapshots — it lives in breadth_daily (the
// same source BreadthSparkline/DivergenceFlag already read). Fetch the last
// few sessions here so the command bar can generate its own plain-English
// breadth line without depending on RegimeSummary's payload shape.
function useBreadthReadLine() {
  const [line, setLine] = useState(null);
  useEffect(() => {
    let cancelled = false;
    getBreadthHistory(6)
      .then((res) => {
        if (cancelled) return;
        const rows = (res?.rows || []).filter((r) => r?.pct_above_20dma != null);
        if (rows.length === 0) return setLine(null);
        const latest = rows[rows.length - 1];
        const prev = rows.length > 1 ? rows[rows.length - 2] : null;
        const pct = latest.pct_above_20dma;
        const band = pct >= 65 ? "strong" : pct >= 45 ? "moderate" : "weak";
        const trend = prev == null ? "flat" : pct > prev.pct_above_20dma ? "improving" : pct < prev.pct_above_20dma ? "narrowing" : "flat";
        setLine(`Breadth ${Math.round(pct)}% of stocks above 20-DMA — ${band}, ${trend}.`);
      })
      .catch(() => !cancelled && setLine(null));
    return () => {
      cancelled = true;
    };
  }, []);
  return line;
}

function fmtPct(n) {
  if (n == null) return "—";
  return `${n}%`;
}
