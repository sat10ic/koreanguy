import { useEffect, useState } from "react";
import { getRegimeSummary, getRegimeHistory, getSetups } from "../api.js";
import InfoDot from "./InfoDot.jsx";
import PostureCommandBar from "./PostureCommandBar.jsx";
import FlipDial from "./FlipDial.jsx";
import SetupStickers from "./SetupStickers.jsx";
import RegimeTrend from "./RegimeTrend.jsx";
import DataStamp from "./DataStamp.jsx";
import BreadthSparkline from "./BreadthSparkline.jsx";
import ParticipationPanel from "./ParticipationPanel.jsx";
import BreadthGrid from "./BreadthGrid.jsx";
import Read from "./Read.jsx";

/**
 * RegimeSummary — thin container (design §1.6): renders PostureCommandBar +
 * FlipDial strip + SetupStickers + MarketQuadrant + RegimeTrend. The old
 * 6-tile StripCard grid is dissolved into these pieces (KILL list §7).
 * Answers "how aggressive am I allowed to be today?" in ~3 seconds.
 */
const DAY_COLOR_CHIP = {
  GREEN: "bg-bull-bg text-bull border-bull-border",
  WHITE: "bg-muted-bg text-muted border-muted-border",
  RED: "bg-bear-bg text-bear border-bear-border",
};

// XP bands (JOB 1): a beginner one-liner + label surfaced next to the XP
// dial value. Mirrors manas_os/regime/snapshot.py::xp_band thresholds.
function xpBand(value) {
  if (value == null) return null;
  if (value < 15) return "LOW";
  if (value < 40) return "BUILDING";
  if (value < 100) return "STRONG";
  return "EXTREME";
}
const XP_BAND_CLS = {
  LOW: "text-muted",
  BUILDING: "text-info",
  STRONG: "text-bull",
  EXTREME: "text-warn",
};

// MBI ratio bands + one-line action copy (JOB 1: numeric value + color + a
// plain-English action, not just a color chip). Thresholds mirror
// manas_os/regime/snapshot.py exactly (20R/10R share one scale; 50R has its
// own higher bar; 4.5R burst has four bands including ORANGE).
function bandRatio(value) {
  if (value == null) return null;
  if (value >= 75) return "GREEN";
  if (value >= 50) return "WHITE";
  return "RED";
}
function bandR50(value) {
  if (value == null) return null;
  if (value >= 85) return "GREEN";
  if (value >= 60) return "WHITE";
  return "RED";
}
function bandR4p5(value) {
  if (value == null) return null;
  if (value < 50) return "RED";
  if (value < 200) return "WHITE";
  if (value < 400) return "GREEN";
  return "ORANGE";
}
const MBI_BAND_TEXT_CLS = {
  GREEN: "text-bull",
  WHITE: "text-muted",
  RED: "text-bear",
  ORANGE: "text-warn",
};
const MBI_BAND_ACTION = {
  GREEN: "strong, normal-to-full sizing",
  WHITE: "neutral, normal sizing",
  RED: "weak, size down or skip",
  ORANGE: "extreme burst, stay selective",
};

function mbiRatioLine(label, term, value, band) {
  if (value == null || band == null) {
    return { label, term, text: "—", cls: "text-ink3" };
  }
  return {
    label,
    term,
    text: `${label} ${Math.round(value)} — ${MBI_BAND_ACTION[band]}`,
    cls: MBI_BAND_TEXT_CLS[band] || "text-muted",
  };
}

export default function RegimeSummary({ onPosture }) {
  const [state, setState] = useState({ loading: true, error: null, data: null });
  const [history, setHistory] = useState({ loading: true, rows: [] });
  const [setups, setSetups] = useState({ loading: true, error: null, rows: [], asOf: null });

  useEffect(() => {
    let cancelled = false;
    setState({ loading: true, error: null, data: null });
    getRegimeSummary()
      .then((d) => !cancelled && setState({ loading: false, error: null, data: d }))
      .catch((e) => !cancelled && setState({ loading: false, error: e.message, data: null }));
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    getSetups({ limit: 5 })
      .then((d) => {
        if (cancelled) return;
        setSetups({
          loading: false,
          error: null,
          rows: d?.available ? (d.candidates || []).slice(0, 5) : [],
          asOf: d?.as_of || null,
        });
      })
      .catch((e) => !cancelled && setSetups({ loading: false, error: e.message, rows: [], asOf: null }));
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    // 15 sessions for the FlipDial mini-sparklines (design §1.3).
    getRegimeHistory(15)
      .then((d) => !cancelled && setHistory({ loading: false, rows: d?.rows || [] }))
      .catch(() => !cancelled && setHistory({ loading: false, rows: [] }));
    return () => {
      cancelled = true;
    };
  }, []);

  // Bubble the resolved posture up to App's header badge (stale forces "muted").
  useEffect(() => {
    if (!onPosture) return;
    if (!state.data?.available) return onPosture(null);
    onPosture(state.data.data_stale ? "STALE" : state.data.market_mode);
  }, [state.data, onPosture]);

  if (state.loading) return <StripSkeleton />;
  if (state.error) {
    return (
      <EmptyBlock title="Couldn't reach the API">
        Make sure the backend is running: <code>python -m manas_os.api</code>
      </EmptyBlock>
    );
  }
  if (!state.data?.available) {
    return (
      <EmptyBlock title="No regime snapshot yet">
        Run the pipeline to populate:{" "}
        <code>python manas.py run-eod --date YYYY-MM-DD</code>
      </EmptyBlock>
    );
  }

  const d = state.data;
  const stale = Boolean(d.data_stale);
  const quadrant = d.quadrant || {};
  const xpHistory = history.rows.map((r) => r.xp_value);
  const r4p5History = history.rows.map((r) => r.r4p5);

  return (
    <section data-testid="regime-summary" className="mb-6">
      <PostureCommandBar data={d} stale={stale} />

      <HomeSetupsPanel data={d} setups={setups} stale={stale} />

      <div
        data-testid="flip-dial-strip"
        className={"mb-4 grid grid-cols-2 gap-2 sm:grid-cols-4 " + (stale ? "opacity-60 grayscale" : "")}
      >
        <FlipDial
          label="XP dial"
          term="xp"
          value={d.xp_value}
          history={xpHistory}
          sub={
            xpBand(d.xp_value) && (
              <span
                className={
                  "flex items-center font-mono text-[9px] font-bold uppercase tracking-overline " +
                  XP_BAND_CLS[xpBand(d.xp_value)]
                }
              >
                {xpBand(d.xp_value).toLowerCase()}
                <InfoDot term="xp-band" />
              </span>
            )
          }
        />
        <FlipDial
          label="4.5R burst"
          term="burst"
          value={d.r4p5}
          history={r4p5History}
          fmt={(n) => (n == null ? "—" : n.toFixed(0))}
        />
        <div className="flex flex-col gap-1 border border-hairline bg-card p-2">
          <span className="flex items-center font-mono text-[9px] uppercase tracking-overline text-ink3">
            MBI day
            <InfoDot term="mbi" />
          </span>
          <span
            className={
              "inline-block w-fit rounded-chip border px-2 py-0.5 font-mono text-[13px] font-bold uppercase " +
              (DAY_COLOR_CHIP[d.mbi_day_color] || DAY_COLOR_CHIP.WHITE)
            }
          >
            {d.mbi_day_color || "—"}
          </span>
          {Boolean(d.warning_day) && (
            <div className="mt-0.5 flex items-center font-mono text-[9px] font-bold uppercase tracking-overline text-warn">
              ⚠ warning day
              <InfoDot term="warning" />
            </div>
          )}
          <MbiRatioRows d={d} />
        </div>
        <div className="flex flex-col gap-1 border border-hairline bg-card p-2">
          <span className="flex items-center font-mono text-[9px] uppercase tracking-overline text-ink3">
            Breadth 20d
            <InfoDot term="breadth" />
          </span>
          <BreadthSparkline />
        </div>
      </div>

      <ParticipationPanel />

      <BreadthGrid />

      <SetupStickers preferred={d.preferred_setups || []} avoid={d.avoid_setups || []} />

      <div
        data-testid="market-quadrant"
        className={"grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-4 " + (stale ? "opacity-60 grayscale" : "")}
      >
        <QuadrantCard title="Momentum" q={quadrant.momentum} />
        <QuadrantCard title="Swing" q={quadrant.swing} />
        <QuadrantCard title="Trend" q={quadrant.trend} />
        <QuadrantCard title="Bias" q={quadrant.bias} />
      </div>

      <RegimeTrend />

      {d.technical_detail && <TechnicalDetail text={d.technical_detail} />}
      <DataStamp />
    </section>
  );
}

// Full var=value audit trail — collapsed by default. Not deleted (the "no
// black box" rule needs it to stay traceable), just not forced on a
// beginner's primary view.
function TechnicalDetail({ text }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="mt-1.5">
      <button
        onClick={() => setOpen((v) => !v)}
        data-testid="technical-detail-toggle"
        className="font-mono text-[9px] uppercase tracking-overline text-ink3 hover:text-ink2"
      >
        {open ? "▾ hide technical detail" : "▸ show technical detail"}
      </button>
      {open && (
        <div
          data-testid="technical-detail-body"
          className="mt-1 border border-hairline2 bg-raised p-2 font-mono text-[10px] leading-relaxed text-ink3"
        >
          {text}
        </div>
      )}
    </div>
  );
}

function HomeSetupsPanel({ data, setups, stale }) {
  const swing = data?.quadrant?.swing || {};
  const breadth = data?.breadth_20dma_pct ?? data?.breadth_pct ?? data?.pct_above_20dma;
  const swingState = swing.state || "UNKNOWN";
  const mode = data?.market_mode || "UNKNOWN";
  const goodSwing = ["UP", "BULLISH"].includes(swingState);
  const band = stale || mode === "NO_TRADE" ? "bear" : goodSwing && mode === "RISK_ON" ? "bull" : "warn";
  const chipCls = {
    bull: "border-bull-border bg-bull-bg text-bull",
    warn: "border-warn-border bg-warn-bg text-warn",
    bear: "border-bear-border bg-bear-bg text-bear",
  }[band];
  const verdict = stale ? "WAIT" : band === "bull" ? "SWING FRIENDLY" : band === "warn" ? "PICKY" : "SIT OUT";

  return (
    <section data-testid="home-setups-panel" className="mb-4 border border-hairline bg-card p-3">
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-mono text-[11px] font-bold uppercase tracking-overline text-ink">
            Breadth / swing state
          </span>
          <span className={"rounded-chip border px-2 py-0.5 font-mono text-[10px] font-bold uppercase tracking-overline " + chipCls}>
            {verdict}
          </span>
          <span className="font-sans text-[12px] text-ink3">
            {breadth == null ? "Breadth unavailable" : `${Number(breadth).toFixed(0)}% above 20-DMA`} · swing {String(swingState).toLowerCase()}.
          </span>
        </div>
        {setups.asOf && (
          <span className="font-mono text-[10px] uppercase tracking-overline text-ink3">
            setups {setups.asOf}
          </span>
        )}
      </div>

      {setups.loading ? (
        <div className="font-mono text-[11px] text-ink3">loading top setups...</div>
      ) : setups.error ? (
        <div className="font-mono text-[11px] text-bear">{setups.error}</div>
      ) : setups.rows.length === 0 ? (
        <Read band="muted" verdict="NO SETUPS">
          No setup candidates passed the quality gate for the latest scan.
        </Read>
      ) : (
        <div className="flex gap-2 overflow-x-auto pb-1">
          {setups.rows.slice(0, 5).map((s) => (
            <div key={`${s.symbol}-${s.setup}`} className="min-w-[190px] border border-hairline bg-raised px-2 py-2">
              <div className="flex items-center justify-between gap-2">
                <span className="font-mono text-[12px] font-bold text-ink">{s.symbol}</span>
                <span className="font-mono text-[16px] font-bold tabular-nums text-ink">
                  {Number(s.readiness || 0).toFixed(0)}
                </span>
              </div>
              <div className="mt-0.5 truncate font-mono text-[9px] uppercase tracking-overline text-ink3">
                {s.grade} · {s.setup}
              </div>
              <div className="mt-1 font-sans text-[11px] leading-snug text-ink3">
                {(s.read || "").replace(/\.$/, "") || "Evidence-backed setup candidate."}
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

// Quadrant state → band. UP/BULLISH = bull, DOWN/BEARISH = bear, everything
// else (NEUTRAL/MIXED) = muted. Unknown state renders as muted with no claim.
const QUAD_BAND = {
  UP: "bull",
  BULLISH: "bull",
  DOWN: "bear",
  BEARISH: "bear",
};

function QuadrantCard({ title, q }) {
  const state = q?.state || null;
  const band = QUAD_BAND[state] || "muted";
  const railCls = { bull: "bg-bull", bear: "bg-bear", muted: "bg-muted" }[band];
  const textCls = { bull: "text-bull", bear: "text-bear", muted: "text-muted" }[band];
  const confidence = typeof q?.confidence === "number" ? q.confidence : null;

  return (
    <div
      data-testid={`quadrant-${title.toLowerCase()}`}
      className="relative overflow-hidden border border-hairline bg-card p-3 pl-4"
    >
      <div className={"absolute left-0 top-0 h-full w-[3px] " + railCls} />
      <div className="mb-1 flex items-center justify-between">
        <span className="flex items-center font-mono text-[12px] font-bold uppercase tracking-overline text-ink">
          {title}
          <InfoDot term={title.toLowerCase()} />
        </span>
        <span className={"font-mono text-[11px] font-bold uppercase " + textCls}>
          {state || "—"}
        </span>
      </div>
      {confidence != null && (
        <div className="mb-2 h-1 rounded-sm bg-hairline">
          <div
            className={"h-full rounded-sm " + railCls}
            style={{ width: `${Math.max(0, Math.min(100, confidence))}%` }}
          />
        </div>
      )}
      <Read band={band} verdict={state || "NO DATA"}>
        {q?.reason || "No data for this quadrant yet."}
      </Read>
    </div>
  );
}

// MBI clarity (JOB 1): show numeric ratio value + color + a one-line action
// for each of 20R/50R/4.5R, not just the aggregate day-color chip above.
function MbiRatioRows({ d }) {
  const rows = [
    mbiRatioLine("20R", "r20", d.r20, bandRatio(d.r20)),
    mbiRatioLine("50R", "r50", d.r50, bandR50(d.r50)),
    mbiRatioLine("4.5R", "burst", d.r4p5, bandR4p5(d.r4p5)),
  ];
  return (
    <div className="mt-1 flex flex-col gap-0.5">
      {rows.map((r) => (
        <span
          key={r.label}
          data-testid={`mbi-ratio-${r.label.toLowerCase().replace(/[^a-z0-9]+/g, "")}`}
          className={"flex items-center font-mono text-[9px] " + r.cls}
        >
          {r.text}
          <InfoDot term={r.term} />
        </span>
      ))}
    </div>
  );
}

function StripSkeleton() {
  return (
    <div className="mb-6 grid grid-cols-2 gap-2 border border-hairline bg-card p-3 sm:grid-cols-4 lg:grid-cols-6">
      {Array.from({ length: 7 }).map((_, i) => (
        <div key={i} className="flex flex-col gap-1.5">
          <div className="h-2 w-10 animate-pulse rounded bg-hairline2" />
          <div className="h-4 w-16 animate-pulse rounded bg-hairline" />
        </div>
      ))}
    </div>
  );
}

function EmptyBlock({ title, children }) {
  return (
    <div className="mb-6 border border-dashed border-hairline px-4 py-6 text-center">
      <div className="font-mono text-[12px] font-semibold text-ink2">{title}</div>
      <div className="mt-1 font-sans text-[12px] leading-snug text-ink3">{children}</div>
    </div>
  );
}
