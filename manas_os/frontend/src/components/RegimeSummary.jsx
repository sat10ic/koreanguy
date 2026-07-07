import { useEffect, useMemo, useRef, useState } from "react";
import * as echarts from "echarts";
import { fetchRegimeBreadthHistory, fetchRegimeHistory, getPortfolioHeat, getRegimeSummary, getSetups } from "../api.js";
import { useDensity } from "../DensityContext.jsx";
import PostureCommandBar from "./PostureCommandBar.jsx";
import SetupStickers from "./SetupStickers.jsx";
import DataStamp from "./DataStamp.jsx";
import ParticipationPanel from "./ParticipationPanel.jsx";
import BreadthGrid from "./BreadthGrid.jsx";
import Read from "./Read.jsx";
import SectorsThemesPanel from "./SectorsThemesPanel.jsx";
import TopIndicesPanel from "./TopIndicesPanel.jsx";
import ShowDetails from "./ShowDetails.jsx";
import { Callout, Caption, MetricTape, MiniTable, PosterBand, PosterCanvas, SectionBadge, StateRibbon, Verdict } from "./poster/Primitives.jsx";

export default function RegimeSummary({ onPosture }) {
  const [state, setState] = useState({ loading: true, error: null, data: null });
  const [setups, setSetups] = useState({ loading: true, error: null, rows: [], asOf: null, governor: null });
  const [heat, setHeat] = useState({ loading: true, error: null, data: null });

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
          governor: d?.governor || null,
        });
      })
      .catch((e) => !cancelled && setSetups({ loading: false, error: e.message, rows: [], asOf: null, governor: null }));
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    getPortfolioHeat()
      .then((d) => !cancelled && setHeat({ loading: false, error: null, data: d }))
      .catch((e) => !cancelled && setHeat({ loading: false, error: e.message, data: null }));
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!onPosture) return;
    if (!state.data?.available) return onPosture(null);
    onPosture(state.data.data_stale ? "STALE" : state.data.market_mode);
  }, [state.data, onPosture]);

  // Hooks must run unconditionally — keep this above the early returns.
  const { density } = useDensity();
  const posterHistory = usePosterHistory();

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
        Run the pipeline to populate: <code>python manas.py run-eod --date YYYY-MM-DD</code>
      </EmptyBlock>
    );
  }

  const d = state.data;
  const stale = Boolean(d.data_stale);
  const governor = setups.governor || {};
  // T3.7b: the density toggle is now real (BEGINNER_EXPERT_SPEC §3.1). Beginner
  // sees the verdict + actionable setups + a collapsed "show the numbers"; the
  // GovernorPanel (diagnostic internals) and the full numbers block are Expert-only.
  // Same data, less of it — never a different verdict.
  const expert = density === "expert";

  const InternalsBlock = (
    <div className="mt-3 space-y-4">
      <BreadthGrid />
      <SectorsThemesPanel />
      <ParticipationPanel />
      <RegimeHistoryPanel state={posterHistory} />
      <TopIndicesPanel />
      <SetupStickers preferred={d.preferred_setups || []} avoid={d.avoid_setups || []} />
      <QuadrantGrid quadrant={d.quadrant || {}} />
      {d.technical_detail && <TechnicalDetail text={d.technical_detail} defaultOpen={expert} />}
    </div>
  );

  return (
    <PosterCanvas data-testid="regime-summary" className="mb-6 space-y-5 font-body">
      <GovernorPanel data={d} governor={governor} heat={heat} stale={stale} />
      <HomeSetupsPanel data={d} setups={setups} stale={stale} />

      {expert && (
        // Expert: render the full internals inline — no expander in the way.
        <ShowDetails label="[E] Show the numbers" testid="regime-numbers">
          {InternalsBlock}
        </ShowDetails>
      )}
      <DataStamp />
    </PosterCanvas>
  );
}

function usePosterHistory() {
  const [state, setState] = useState({ loading: true, error: null, history: null, breadth: null });

  useEffect(() => {
    let cancelled = false;
    setState({ loading: true, error: null, history: null, breadth: null });
    Promise.all([fetchRegimeHistory(60), fetchRegimeBreadthHistory(60)])
      .then(([history, breadth]) => {
        if (cancelled) return;
        setState({ loading: false, error: null, history, breadth });
      })
      .catch((e) => {
        if (cancelled) return;
        setState({ loading: false, error: e.message, history: null, breadth: null });
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return state;
}

function RegimePoster({ data, governor, stale, historyState }) {
  const quadrant = data.quadrant || {};
  const historyRows = historyState.history?.available ? (historyState.history.rows || []).slice(-60) : [];
  const breadthRows = historyState.breadth?.available ? (historyState.breadth.rows || []).slice(-5) : [];
  const latestBreadth = breadthRows[breadthRows.length - 1] || {};
  const mode = stale ? "STALE" : data.market_mode || "UNKNOWN";
  const readText = data.read || data.explanation_text || data.command || data.technical_detail || "Use the posture and governor law before choosing risk.";

  return (
    <PosterCanvas className="space-y-4">
      <PosterBand state={modeTone(mode)} kicker="REGIME" action={<PostureCommandBar data={data} stale={stale} />}>
        <Verdict>{postureVerdict(mode)}</Verdict>
        <div className="mb-2 mt-1">
          <Caption>{readText}</Caption>
        </div>
        <MetricTape items={governorTapeItems(governor, data)} />
        <div className="mt-3">
          <MiniTable columns={["Metric", "Now", "Delta"]} rows={postureRows(data, historyRows, breadthRows, latestBreadth)} shade={deltaShade} />
        </div>
      </PosterBand>

      <div className="border border-hairline bg-card p-2">
        <div className="font-mono text-[10px] uppercase tracking-overline text-ink3 mb-1">BREADTH WEATHER (last 5)</div>
        <div className="flex gap-1">
          {breadthRows.slice(-5).map((r, i) => {
            const pct = Number(r.pct_above_20dma ?? 50);
            const tone = pct >= 65 ? "bull" : pct >= 48 ? "muted" : "bear";
            return <div key={i} className={`h-3 flex-1 ${tone === "bull" ? "bg-bull" : tone === "bear" ? "bg-bear" : "bg-ink3"}`} title={`${r.trade_date || r.snapshot_date}: ${pct.toFixed(0)}%`} />;
          })}
        </div>
      </div>

      <PosterBand state={quadTone(quadrant.swing?.state)} kicker="SWING" title={`SWING is ${quadrant.swing?.state || "UNKNOWN"}`}>
        <Caption>{quadrant.swing?.reason || "No swing read is available yet."}</Caption>
        <div className="mt-3">
          <MiniTable columns={["Date", "%>10DMA", "%>20DMA"]} rows={swingRows(breadthRows)} shade={breadthShade} />
        </div>
        <div className="mt-3">
          <RegimeHistoryPanel state={historyState} compact />
        </div>
      </PosterBand>

      <PosterBand state={quadTone(quadrant.trend?.state)} kicker="TREND" title={`TREND is ${quadrant.trend?.state || "UNKNOWN"}`}>
        <Caption>{quadrant.trend?.reason || "No trend read is available yet."}</Caption>
        <PosterNote>
          Trend breadth is shown as the last three dated sessions, so the long-term read is labeled before any action is taken.
        </PosterNote>
      </PosterBand>

      <PosterBand state={quadTone(quadrant.bias?.state)} kicker="BIAS" title={`BIAS is ${quadrant.bias?.state || "UNKNOWN"}`}>
        <Caption>{quadrant.bias?.reason || "No bias read is available yet."}</Caption>
        <PosterNote>
          Bias is the final posture filter: it decides whether new risk gets a green light, a haircut, or a hard pass.
        </PosterNote>
      </PosterBand>
    </PosterCanvas>
  );
}

function PosterNote({ children }) {
  return (
    <div className="border border-hairline2 bg-raised px-4 py-5 font-body text-[13px] leading-snug text-ink2">
      {children}
    </div>
  );
}

function postureRows(data, historyRows, breadthRows, latestBreadth) {
  const latest = historyRows[historyRows.length - 1] || {};
  const previous = historyRows[historyRows.length - 2] || {};
  return [
    { Metric: "XP", Now: fmtNumber(latest.xp_value ?? data.xp_value, 1), Delta: fmtDelta(diff(latest.xp_value, previous.xp_value), 1) },
    { Metric: "4.5R", Now: fmtNumber(latest.r4p5 ?? data.r4p5, 0), Delta: fmtDelta(diff(latest.r4p5, previous.r4p5), 0) },
    { Metric: "%>20DMA", Now: fmtPct0(latestBreadth.pct_above_20dma ?? data.breadth_20dma_pct ?? data.pct_above_20dma), Delta: fmtDelta(diffLatestBreadth(latestBreadth, breadthRows), 0, "pp") },
  ];
}

function governorRows(data, governor, stale) {
  const mode = stale ? "STALE" : data.market_mode || "UNKNOWN";
  const allowed = governor.allowed_families || governor.allowed_setups || data.preferred_setups || [];
  const riskBase = governor.risk_band?.base_pct ?? governor.risk_band?.base ?? governor.risk_base_pct ?? data.allowed_risk_min_pct;
  const riskMax = governor.risk_band?.hard_max_pct ?? governor.risk_band?.hard_max ?? governor.risk_hard_max_pct ?? data.allowed_risk_max_pct;
  const pushes = governor.push_allowed ?? governor.pushes_enabled ?? governor.pushes_on ?? mode !== "NO_TRADE";
  return [
    { Rule: "Max cards", Value: governor.max_cards ?? "-" },
    { Rule: "Risk band", Value: riskBase == null && riskMax == null ? "-" : `${fmtPct(riskBase)}-${fmtPct(riskMax)}` },
    { Rule: "Families", Value: allowed.length ? allowed.join(", ") : "none" },
    { Rule: "Pushes", Value: pushes ? "ON" : "OFF" },
  ];
}

function governorTapeItems(governor, data) {
  const maxCards = governor.max_cards ?? data.max_cards ?? "-";
  const riskBase = governor.risk_band?.base_pct ?? governor.risk_band?.base ?? data.allowed_risk_min_pct ?? 0.5;
  const riskMax = governor.risk_band?.hard_max_pct ?? governor.risk_band?.hard_max ?? data.allowed_risk_max_pct ?? 1;
  const risk = `${riskBase}-${riskMax}%`;
  const allowed = (governor.allowed_families || governor.allowed_setups || data.preferred_setups || []).slice(0, 2).join(" / ") || "-";
  const pushes = (governor.pushes_enabled ?? data.pushes_on) ? "ON" : "OFF";
  const openRisk = data.open_risk_pct != null ? `${data.open_risk_pct}%` : "-";
  return [
    { label: "MAX CARDS", value: String(maxCards), state: "info" },
    { label: "RISK/TRADE", value: risk, state: "warn" },
    { label: "ALLOWED", value: allowed, state: "bull" },
    { label: "OPEN RISK", value: openRisk, state: "muted" },
    { label: "PUSHES", value: pushes, state: pushes === "ON" ? "bull" : "bear" },
  ];
}

function swingRows(rows) {
  return rows.slice(-3).map((row) => ({
    Date: row.trade_date || row.snapshot_date || "-",
    "%>10DMA": fmtPct0(row.pct_above_10dma),
    "%>20DMA": fmtPct0(row.pct_above_20dma),
  }));
}

function trendRows(rows) {
  return rows.slice(-3).map((row) => ({
    Date: row.trade_date || row.snapshot_date || "-",
    "%>40DMA": fmtPct0(row.pct_above_40dma),
    "%>50DMA": fmtPct0(row.pct_above_50dma),
  }));
}

function postureVerdict(mode) {
  if (mode === "RISK_ON") return "RISK-ON - press clean longs";
  if (mode === "SELECTIVE") return "SELECTIVE - trade small and picky";
  if (mode === "DEFENSIVE") return "DEFENSIVE - protect capital";
  if (mode === "NO_TRADE") return "NO-TRADE - sit out";
  if (mode === "STALE") return "STALE - wait for fresh data";
  return "UNKNOWN - wait for the law";
}

function modeTone(mode) {
  if (mode === "RISK_ON") return "bull";
  if (mode === "SELECTIVE") return "warn";
  if (mode === "DEFENSIVE" || mode === "NO_TRADE" || mode === "STALE") return "bear";
  return "muted";
}

function quadTone(state) {
  if (["UP", "BULLISH", "POSITIVE"].includes(state)) return "bull";
  if (["DOWN", "BEARISH", "NEGATIVE"].includes(state)) return "bear";
  if (["MIXED", "NEUTRAL", "CAUTION"].includes(state)) return "warn";
  return "muted";
}

function deltaShade(value, column) {
  if (column !== "Delta" || typeof value !== "string") return null;
  if (value.startsWith("+")) return "bull";
  if (value.startsWith("-")) return "bear";
  return null;
}

function breadthShade(value, column) {
  if (!column.includes("%>")) return null;
  const n = Number(String(value).replace("%", ""));
  if (!Number.isFinite(n)) return null;
  if (n >= 55) return "bull";
  if (n < 40) return "bear";
  return null;
}

function diff(a, b) {
  if (a == null || b == null) return null;
  return Number(a) - Number(b);
}

function diffLatestBreadth(latestBreadth, historyRows) {
  const rows = historyRows.filter((r) => r?.pct_above_20dma != null);
  const prev = rows.length >= 2 ? rows[rows.length - 2] : null;
  if (latestBreadth?.pct_above_20dma == null || prev?.pct_above_20dma == null) return null;
  return Number(latestBreadth.pct_above_20dma) - Number(prev.pct_above_20dma);
}

function fmtNumber(value, digits = 0) {
  if (value == null || !Number.isFinite(Number(value))) return "-";
  return Number(value).toFixed(digits).replace(/\.0$/, "");
}

function fmtPct0(value) {
  if (value == null || !Number.isFinite(Number(value))) return "-";
  return `${Number(value).toFixed(0)}%`;
}

function fmtDelta(value, digits = 0, suffix = "") {
  if (value == null || !Number.isFinite(Number(value))) return "-";
  const n = Number(value);
  if (n === 0) return `0${suffix}`;
  return `${n > 0 ? "+" : ""}${n.toFixed(digits).replace(/\.0$/, "")}${suffix}`;
}

function GovernorPanel({ data, governor, heat, stale }) {
  const mode = stale ? "STALE" : data.market_mode || "UNKNOWN";
  const allowed = governor.allowed_families || governor.allowed_setups || data.preferred_setups || [];
  const riskBase = governor.risk_band?.base_pct ?? governor.risk_band?.base ?? governor.risk_base_pct ?? data.allowed_risk_min_pct;
  const riskMax = governor.risk_band?.hard_max_pct ?? governor.risk_band?.hard_max ?? governor.risk_hard_max_pct ?? data.allowed_risk_max_pct;
  const pushes = governor.push_allowed ?? governor.pushes_enabled ?? governor.pushes_on ?? mode !== "NO_TRADE";
  const heatData = heat?.data || {};
  const openRisk = heatData.open_risk_pct ?? data.open_risk_pct;
  const openRiskCap = heatData.cap_pct ?? governor.open_risk_cap_pct ?? data.open_risk_cap_pct;
  const why = data.read || data.explanation_text || data.command || data.technical_detail || "Use the governor law before choosing risk.";
  return (
    <section className="border border-hairline bg-card p-4" aria-label="Governor panel">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="font-mono text-[11px] font-bold uppercase tracking-overline text-ink3">
            Governor panel
          </div>
          <div className="mt-1 font-display text-[28px] uppercase leading-none text-ink">
            {postureVerdict(mode)}
          </div>
        </div>
        <PostureCommandBar data={data} stale={stale} />
      </div>
      <div className="grid gap-2 md:grid-cols-5">
        <LawTile label="MAX CARDS" value={governor.max_cards ?? data.max_cards ?? "-"} />
        <LawTile label="RISK/TRADE" value={riskBase == null && riskMax == null ? "-" : `${fmtPct(riskBase)}-${fmtPct(riskMax)}`} />
        <div className="border border-hairline bg-raised p-3">
          <div className="mb-1 font-mono text-[9px] uppercase tracking-overline text-ink3">ALLOWED SETUPS</div>
          <div className="flex flex-wrap gap-1">
            {(allowed.length ? allowed : ["none"]).map((family) => (
              <span key={family} className="rounded-chip border border-hairline bg-card px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-overline text-ink2">
                {family}
              </span>
            ))}
          </div>
        </div>
        <LawTile
          label="OPEN-RISK CAP"
          value={openRiskCap == null ? (openRisk == null ? "-" : `${fmtPct(openRisk)} used`) : `${fmtPct(openRiskCap)} (${openRisk == null ? "-" : fmtPct(openRisk)} used)`}
          sub={heat?.error || null}
        />
        <LawTile label="PUSHES" value={pushes ? "ON" : "OFF"} />
      </div>
      <div className="mt-3 border-t border-hairline pt-3 font-sans text-[13px] leading-snug text-ink2">
        <span className="font-mono text-[10px] font-bold uppercase tracking-overline text-ink3">WHY (plain): </span>
        {why}
      </div>
    </section>
  );
}

function LawTile({ label, value, sub = null }) {
  return (
    <div className="border border-hairline bg-raised p-3">
      <div className="font-mono text-[9px] uppercase tracking-overline text-ink3">{label}</div>
      <div className="mt-1 font-mono text-[18px] font-bold tabular-nums text-ink">{value}</div>
      {sub && <div className="mt-1 font-mono text-[9px] uppercase tracking-overline text-bear">{sub}</div>}
    </div>
  );
}

function HomeSetupsPanel({ data, setups, stale }) {
  const cap = setups.governor?.max_cards ?? data?.max_cards ?? setups.rows.length;
  const reviewed = setups.rows.filter((s) => s.decision || s.reviewed || s.status === "reviewed").length;
  const reviewedText = `${reviewed} of ${cap || setups.rows.length} reviewed`;

  return (
    <section data-testid="home-setups-panel" className="border border-hairline bg-card p-3" aria-label="Top setups strip">
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-mono text-[11px] font-bold uppercase tracking-overline text-ink">
            Top setups strip
          </span>
          <span className="font-sans text-[12px] text-ink3">
            {reviewedText}
          </span>
        </div>
        <button
          type="button"
          onClick={() => document.querySelector('[data-testid="nav-setups"]')?.click()}
          className="border border-hairline px-2 py-1 font-mono text-[10px] uppercase tracking-overline text-ink2 hover:border-ink hover:text-ink"
        >
          go to Setups
        </button>
      </div>

      {setups.loading ? (
        <div className="font-mono text-[11px] text-ink3">loading top setups...</div>
      ) : setups.error ? (
        <div className="font-mono text-[11px] text-bear">{setups.error}</div>
      ) : setups.rows.length === 0 ? (
        <Read band="muted" verdict="NO SETUPS">No setup candidates passed the quality gate for the latest scan.</Read>
      ) : (
        <div className="flex flex-wrap items-center gap-2">
          {setups.rows.slice(0, 5).map((s, idx) => (
            <div key={`${s.symbol}-${s.setup}`} className="border border-hairline bg-raised px-2 py-2">
              <span className="font-mono text-[12px] font-bold text-ink">{idx + 1}. {s.symbol}</span>
              <span className="ml-2 font-mono text-[10px] uppercase tracking-overline text-ink3">
                {s.setup_type || s.setup || "setup"} rank {s.rank ?? idx + 1}/{cap || setups.rows.length}
              </span>
            </div>
          ))}
          <span className="font-mono text-[10px] uppercase tracking-overline text-ink3">-&gt; {reviewedText}</span>
        </div>
      )}
    </section>
  );
}

function RegimeHistoryPanel({ state: externalState = null, compact = false } = {}) {
  const [localState, setLocalState] = useState({ loading: true, error: null, history: null, breadth: null });

  useEffect(() => {
    if (externalState) return undefined;
    let cancelled = false;
    setLocalState({ loading: true, error: null, history: null, breadth: null });
    Promise.all([fetchRegimeHistory(60), fetchRegimeBreadthHistory(60)])
      .then(([history, breadth]) => {
        if (cancelled) return;
        setLocalState({ loading: false, error: null, history, breadth });
      })
      .catch((e) => {
        if (cancelled) return;
        setLocalState({ loading: false, error: e.message, history: null, breadth: null });
      });
    return () => {
      cancelled = true;
    };
  }, [externalState]);

  const state = externalState || localState;

  if (state.loading) {
    return (
      <div className="border border-hairline bg-card p-3">
        <div className="mb-2 h-3 w-40 animate-pulse rounded bg-hairline2" />
        <div className={(compact ? "h-[180px]" : "h-40") + " w-full animate-pulse rounded bg-hairline2"} />
      </div>
    );
  }
  if (state.error || !state.history?.available || !state.breadth?.available) return null;

  const rows = (state.history.rows || []).slice(-60);
  const breadthRows = (state.breadth.rows || []).slice(-5);
  if (rows.length === 0 || breadthRows.length === 0) return null;

  return (
    <section data-testid="regime-history-strip" className="border border-hairline bg-card p-3">
      {!compact && <div className="mb-2 flex flex-wrap items-baseline justify-between gap-2">
        <div>
          <div className="font-mono text-[12px] font-bold uppercase tracking-overline text-ink">
            Regime history
          </div>
          <p className="mt-0.5 font-sans text-[11px] leading-snug text-ink3">
            XP line over the last 60 sessions, shaded by market posture.
          </p>
        </div>
        <HistoryLegend />
      </div>}
      {compact && <div className="mb-2 flex justify-end"><HistoryLegend /></div>}
      <RegimeHistoryChart rows={rows} height={compact ? "h-[180px]" : "h-44"} />
      <StateRibbon
        items={rows.map((r) => ({ date: r.snapshot_date, state: (r.market_mode || "muted").toLowerCase() === "risk_on" ? "bull" : (r.market_mode || "").toLowerCase() === "selective" ? "warn" : (r.market_mode || "").toLowerCase() === "defensive" ? "bear" : "muted", title: `${r.snapshot_date} ${r.market_mode}` }))}
        getState={(it) => it.state}
      />
      <div className="mt-2 font-sans text-[12px] text-ink3">{breadthCaption(breadthRows)}</div>
      <Callout className="mt-1">color bands = daily market posture (full history ribbon for density)</Callout>
    </section>
  );
}

function RegimeHistoryChart({ rows, height = "h-44" }) {
  const option = useMemo(() => regimeHistoryOption(rows), [rows]);
  return <EChart option={option} className={height} />;
}

function EChart({ option, className }) {
  const ref = useRef(null);

  useEffect(() => {
    if (!ref.current) return undefined;
    const chart = echarts.init(ref.current);
    chart.setOption(option);
    const resize = () => chart.resize();
    window.addEventListener("resize", resize);
    return () => {
      window.removeEventListener("resize", resize);
      chart.dispose();
    };
  }, [option]);

  return <div ref={ref} className={className} />;
}

const MODE_STYLE = {
  RISK_ON: { label: "Risk-On", color: "#e6f6ec", dot: "bg-bull-dot" },
  SELECTIVE: { label: "Selective", color: "#fdf0dd", dot: "bg-warn-dot" },
  DEFENSIVE: { label: "Defensive", color: "#fdecea", dot: "bg-bear-dot" },
  NO_TRADE: { label: "No-Trade", color: "#f0f1f4", dot: "bg-muted-dot" },
};

function regimeHistoryOption(rows) {
  const dates = rows.map((r) => r.snapshot_date);
  return {
    animation: false,
    tooltip: { trigger: "axis" },
    grid: { left: 36, right: 14, top: 14, bottom: 26 },
    xAxis: {
      type: "category",
      data: dates,
      boundaryGap: false,
      axisLabel: { fontSize: 10, color: "#8a93a0" },
      axisLine: { lineStyle: { color: "#e7e9ee" } },
      axisTick: { show: false },
    },
    yAxis: {
      type: "value",
      min: 0,
      max: 100,
      splitLine: { lineStyle: { color: "#eef0f3" } },
      axisLabel: { fontSize: 10, color: "#8a93a0" },
    },
    series: [
      {
        name: "XP",
        type: "line",
        smooth: true,
        showSymbol: false,
        data: rows.map((r) => r.xp_value),
        lineStyle: { color: "#175cd3", width: 2 },
        markArea: {
          silent: true,
          itemStyle: { opacity: 1 },
          data: postureSegments(rows),
        },
      },
      // Linked backend journal_outcomes overlaid on regime ribbon (from enriched /api/regime/history)
      {
        name: "Trades",
        type: "scatter",
        symbolSize: 8,
        data: rows.flatMap((r) => (r.journal_outcomes || []).map((t) => ({
          name: t.symbol,
          value: [r.snapshot_date, 50 + (t.r || 0) * 5], // position on chart for visibility
          itemStyle: { color: (t.r || 0) > 0 ? "#0f7a3d" : "#b42318" },
        }))),
      },
    ],
  };
}

function postureSegments(rows) {
  const segments = [];
  let start = 0;
  for (let i = 1; i <= rows.length; i += 1) {
    if (i < rows.length && rows[i].market_mode === rows[start].market_mode) continue;
    const mode = rows[start].market_mode;
    const style = MODE_STYLE[mode] || MODE_STYLE.NO_TRADE;
    segments.push([
      { xAxis: rows[start].snapshot_date, itemStyle: { color: style.color } },
      { xAxis: rows[i - 1].snapshot_date },
    ]);
    start = i;
  }
  return segments;
}

function breadthCaption(rows) {
  const values = rows.map((r) => Number(r.pct_above_20dma)).filter((v) => Number.isFinite(v));
  let improving = 0;
  let declining = 0;
  for (let i = 1; i < values.length; i += 1) {
    if (values[i] > values[i - 1]) improving += 1;
    if (values[i] < values[i - 1]) declining += 1;
  }
  const label = improving >= declining ? "improving" : "declining";
  const count = Math.max(improving, declining);
  return `breadth ${label} ${count} of last 5 days`;
}

function HistoryLegend() {
  return (
    <div className="flex flex-wrap items-center gap-3 font-mono text-[9px] uppercase tracking-overline text-ink3">
      {Object.entries(MODE_STYLE).map(([mode, style]) => (
        <span key={mode} className="flex items-center gap-1">
          <span className={"inline-block h-2 w-2 rounded-sm " + style.dot} />
          {style.label}
        </span>
      ))}
    </div>
  );
}

function QuadrantGrid({ quadrant }) {
  return (
    <div data-testid="market-quadrant" className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-4">
      <QuadrantCard title="Momentum" q={quadrant.momentum} />
      <QuadrantCard title="Swing" q={quadrant.swing} />
      <QuadrantCard title="Trend" q={quadrant.trend} />
      <QuadrantCard title="Bias" q={quadrant.bias} />
    </div>
  );
}

const QUAD_BAND = { UP: "bull", BULLISH: "bull", DOWN: "bear", BEARISH: "bear" };

function QuadrantCard({ title, q }) {
  const state = q?.state || null;
  const band = QUAD_BAND[state] || "muted";
  const railCls = { bull: "bg-bull", bear: "bg-bear", muted: "bg-muted" }[band];
  const textCls = { bull: "text-bull", bear: "text-bear", muted: "text-muted" }[band];
  return (
    <div className="relative overflow-hidden border border-hairline bg-card p-3 pl-4">
      <div className={"absolute left-0 top-0 h-full w-[3px] " + railCls} />
      <div className="mb-1 flex items-center justify-between">
        <span className="font-mono text-[12px] font-bold uppercase tracking-overline text-ink">{title}</span>
        <span className={"font-mono text-[11px] font-bold uppercase " + textCls}>{state || "-"}</span>
      </div>
      <Read band={band} verdict={state || "NO DATA"}>{q?.reason || "No data for this quadrant yet."}</Read>
    </div>
  );
}

function TechnicalDetail({ text, defaultOpen = false }) {
  // Axis E: collapsed by default in Beginner, open by default in Expert.
  return (
    <details open={defaultOpen} className="border border-hairline2 bg-raised p-2">
      <summary className="cursor-pointer font-mono text-[9px] uppercase tracking-overline text-ink3">
        technical detail (var=value audit trail)
      </summary>
      <div className="mt-1 font-mono text-[10px] leading-relaxed text-ink3">{text}</div>
    </details>
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

function fmtPct(value) {
  if (value == null) return "-";
  return `${Number(value).toFixed(2).replace(/\.00$/, "")}%`;
}
