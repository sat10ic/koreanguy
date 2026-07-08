import { useEffect, useMemo, useRef, useState } from "react";
import * as echarts from "echarts";
import { getAdvisorToday, getPortfolioHeat, getRegimeHistory, getRegimeSummary, getSetups } from "../api.js";
import AdvisorStrip from "./AdvisorStrip.jsx";
import BreadthGrid from "./BreadthGrid.jsx";
import ParticipationPanel from "./ParticipationPanel.jsx";
import ShowDetails from "./ShowDetails.jsx";
import TopIndicesPanel from "./TopIndicesPanel.jsx";

export default function RegimeSummary({ onPosture }) {
  const [state, setState] = useState({ loading: true, error: null, data: null });
  const [setups, setSetups] = useState({ loading: true, error: null, rows: [], governor: null });
  const [heat, setHeat] = useState({ loading: true, error: null, data: null });
  const [advisor, setAdvisor] = useState({ loading: true, error: null, notes: [] });

  useEffect(() => {
    let cancelled = false;
    setState({ loading: true, error: null, data: null });
    getRegimeSummary()
      .then((data) => !cancelled && setState({ loading: false, error: null, data }))
      .catch((error) => !cancelled && setState({ loading: false, error: error.message, data: null }));
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    getAdvisorToday()
      .then((data) => !cancelled && setAdvisor({ loading: false, error: null, notes: data?.available ? data.notes || [] : [] }))
      .catch((error) => !cancelled && setAdvisor({ loading: false, error: error.message, notes: [] }));
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    getSetups({ limit: 5 })
      .then((data) => {
        if (cancelled) return;
        setSetups({
          loading: false,
          error: null,
          rows: data?.available ? (data.candidates || []).slice(0, 5) : [],
          governor: data?.governor || null,
        });
      })
      .catch((error) => !cancelled && setSetups({ loading: false, error: error.message, rows: [], governor: null }));
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    getPortfolioHeat()
      .then((data) => !cancelled && setHeat({ loading: false, error: null, data }))
      .catch((error) => !cancelled && setHeat({ loading: false, error: error.message, data: null }));
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!onPosture) return;
    if (!state.data?.available) return onPosture(null);
    return onPosture(state.data.data_stale ? "STALE" : state.data.market_mode);
  }, [state.data, onPosture]);

  if (state.loading) return <RegimeSkeleton />;
  if (state.error) {
    return (
      <EmptyBlock title="Couldn't reach the API">
        Make sure the backend is running: <code>python -m manas_os.api</code>
      </EmptyBlock>
    );
  }
  if (!state.data?.available) {
    return (
      <EmptyBlock title="No regime data yet">
        Run the pipeline to populate: <code>python manas.py run-eod --date YYYY-MM-DD</code>
      </EmptyBlock>
    );
  }

  return (
    <main data-testid="regime-summary" className="mb-6 space-y-3 font-body">
      <GovernorPanel data={state.data} governor={setups.governor || {}} heat={heat} />
      <TopSetupsStrip data={state.data} setups={setups} />
      <AdvisorStrip notes={advisor.notes} scope="regime" />
      <ShowDetails label="[E] Show the numbers" testid="regime-numbers">
        <NumbersAccordion />
      </ShowDetails>
    </main>
  );
}

function GovernorPanel({ data, governor, heat }) {
  const stale = Boolean(data.data_stale);
  const mode = stale ? "STALE" : data.market_mode || "UNKNOWN";
  const allowed = governor.allowed_families || governor.allowed_setups || data.preferred_setups || [];
  const riskBase = governor.risk_band?.base_pct ?? governor.risk_band?.base ?? governor.risk_base_pct ?? data.allowed_risk_min_pct;
  const riskMax = governor.risk_band?.hard_max_pct ?? governor.risk_band?.hard_max ?? governor.risk_hard_max_pct ?? data.allowed_risk_max_pct;
  const pushes = governor.push_allowed ?? governor.pushes_enabled ?? governor.pushes_on ?? mode !== "NO_TRADE";
  const heatData = heat.data || {};
  const openRisk = heatData.open_risk_pct ?? data.open_risk_pct;
  const openRiskCap = heatData.cap_pct ?? governor.open_risk_cap_pct ?? data.open_risk_cap_pct;
  const why = data.read || data.explanation_text || data.command || data.technical_detail || "Use the governor law before choosing risk.";

  return (
    <section className="border border-hairline bg-card p-4" aria-label="GOVERNOR PANEL">
      <div className="font-display text-[28px] uppercase leading-none text-ink">
        {postureVerdict(mode)}
      </div>
      <div className="mt-3 grid gap-2 md:grid-cols-5">
        <LawTile label="MAX CARDS" value={governor.max_cards ?? data.max_cards ?? "-"} />
        <LawTile label="RISK/TRADE" value={riskBase == null && riskMax == null ? "-" : `${fmtPct(riskBase)}-${fmtPct(riskMax)}`} />
        <AllowedTile allowed={allowed} />
        <LawTile
          label="OPEN-RISK CAP"
          value={openRiskCap == null ? (openRisk == null ? "-" : `${fmtPct(openRisk)} used`) : `${fmtPct(openRiskCap)} (${openRisk == null ? "-" : fmtPct(openRisk)} used)`}
          sub={heat.error || null}
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

function AllowedTile({ allowed }) {
  const items = allowed.length ? allowed : ["none"];
  return (
    <div className="border border-hairline bg-raised p-3">
      <div className="mb-1 font-mono text-[9px] uppercase tracking-overline text-ink3">ALLOWED SETUPS</div>
      <div className="flex flex-wrap gap-1">
        {items.map((family) => (
          <span key={family} className="rounded-chip border border-hairline bg-card px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-overline text-ink2">
            {family}
          </span>
        ))}
      </div>
    </div>
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

function TopSetupsStrip({ data, setups }) {
  const shownRows = setups.rows.slice(0, 5);
  const reviewed = setups.rows.filter((setup) => setup.decision || setup.reviewed || setup.status === "reviewed").length;
  const reviewedText = `${reviewed} of ${shownRows.length} reviewed`;

  return (
    <section data-testid="home-setups-panel" className="border border-hairline bg-card p-3" aria-label="TOP SETUPS STRIP">
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <div className="font-mono text-[11px] font-bold uppercase tracking-overline text-ink">TOP SETUPS STRIP</div>
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
        <div className="font-mono text-[11px] uppercase tracking-overline text-ink3">no setup candidates passed the quality gate</div>
      ) : (
        <div className="flex flex-wrap items-center gap-2">
          {shownRows.map((setup, index) => (
            <div key={`${setup.symbol}-${setup.setup_type || setup.setup || index}`} className="border border-hairline bg-raised px-2 py-2">
              <span className="font-mono text-[12px] font-bold text-ink">{index + 1}. {setup.symbol}</span>
              <span className="ml-2 font-mono text-[10px] uppercase tracking-overline text-ink3">
                {setup.setup_type || setup.setup || "setup"} rank {setup.rank ?? index + 1}/{setup.rank_of ?? setup.rank_total ?? shownRows.length}
              </span>
            </div>
          ))}
          <span className="font-mono text-[10px] uppercase tracking-overline text-ink3">-&gt; {reviewedText}</span>
        </div>
      )}
    </section>
  );
}

function NumbersAccordion() {
  return (
    <div className="space-y-3">
      {/* W2.4: regime ribbon with outcomes overlaid (market_mode per session
          + journal trade entry/exit markers). VIZ_BRAINSTORM #5. Expert only. */}
      <RegimeRibbon />
      <div className="grid gap-3 lg:grid-cols-2">
        <BreadthGrid />
        <SectorRotationScatter />
      </div>
      <ParticipationPanel />
      <TopIndicesPanel />
    </div>
  );
}

// W2.4: regime ribbon with outcomes overlaid. Answers "do I actually make
// money in the regimes the governor lets me trade?" Calendar strip of
// market_mode per session (colored), journal trade entries plotted on top
// with R-result color. Data: regime_snapshots + journal_trades (one endpoint,
// /api/regime/history, which already joins both).
function RegimeRibbon() {
  const [state, setState] = useState({ loading: true, error: null, data: null });
  useEffect(() => {
    let cancelled = false;
    setState({ loading: true, error: null, data: null });
    getRegimeHistory({ days: 90 })
      .then((data) => !cancelled && setState({ loading: false, error: null, data }))
      .catch((error) => !cancelled && setState({ loading: false, error: error.message, data: null }));
    return () => {
      cancelled = true;
    };
  }, []);
  const ref = useRef(null);
  const option = useMemo(() => regimeRibbonOption(state.data), [state.data]);
  useEffect(() => {
    if (!ref.current || !state.data?.available) return;
    const chart = echarts.init(ref.current);
    chart.setOption(option);
    return () => chart.dispose();
  }, [option, state.data]);
  const trades = useMemo(() => flatTrades(state.data), [state.data]);
  return (
    <section className="border border-hairline bg-card p-3" aria-label="REGIME RIBBON">
      <div className="mb-2 font-mono text-[11px] font-bold uppercase tracking-overline text-ink">Regime ribbon with outcomes</div>
      {state.loading ? (
        <div className="font-mono text-[11px] text-ink3">loading regime ribbon...</div>
      ) : state.error ? (
        <div className="font-mono text-[11px] text-bear">{state.error}</div>
      ) : !state.data?.available || !state.data.rows?.length ? (
        <div className="font-mono text-[11px] uppercase tracking-overline text-ink3">no regime history yet</div>
      ) : (
        <>
          <div ref={ref} className="h-48 w-full" />
          <div className="mt-2 flex flex-wrap gap-x-3 gap-y-1 font-mono text-[9px] uppercase tracking-overline text-ink3">
            <span><span className="text-bull">■</span> RISK_ON</span>
            <span><span className="text-info">■</span> SELECTIVE</span>
            <span><span className="text-warn">■</span> DEFENSIVE</span>
            <span><span className="text-bear">■</span> NO_TRADE</span>
            {trades > 0 && <span>· {trades} journal trades overlaid</span>}
          </div>
        </>
      )}
    </section>
  );
}

function flatTrades(data) {
  if (!data?.rows) return 0;
  return data.rows.reduce((sum, r) => sum + (r.journal_outcomes?.length || 0), 0);
}

function regimeRibbonOption(data) {
  if (!data?.rows?.length) return {};
  const rows = data.rows;
  const modeColor = { RISK_ON: "#22c55e", SELECTIVE: "#3b82f6", DEFENSIVE: "#eab308", NO_TRADE: "#ef4444" };
  // Trade markers: one scatter series per date with an entry, colored by R.
  const markerData = [];
  rows.forEach((r) => {
    (r.journal_outcomes || []).forEach((t) => {
      markerData.push({
        value: [r.snapshot_date, markerY(t.r)],
        symbol: t.exit == null ? "triangle" : "circle",
        itemStyle: { color: t.r == null ? "#94a3b8" : Number(t.r) >= 0 ? "#22c55e" : "#ef4444" },
        trade: t,
      });
    });
  });
  return {
    grid: { left: 40, right: 12, top: 12, bottom: 48 },
    xAxis: {
      type: "category",
      data: rows.map((r) => r.snapshot_date),
      axisLabel: { fontSize: 9, formatter: (v) => v.slice(5) },
    },
    yAxis: { type: "value", show: false, min: -0.5, max: 1.5 },
    tooltip: {
      trigger: "axis",
      formatter: (params) => {
        const idx = params[0]?.dataIndex;
        if (idx == null) return "";
        const r = rows[idx];
        const trades = r.journal_outcomes || [];
        const tradeLines = trades.map((t) => `<br/>${t.symbol} ${t.r == null ? "-" : t.r + "R"}`).join("");
        return `${r.snapshot_date} · ${r.market_mode}${tradeLines}`;
      },
    },
    // Ribbon: XP line with markArea bands colored by market_mode is noisy;
    // use a single line series for XP (context) + the ribbon as markArea.
    series: [
      {
        type: "line",
        name: "XP",
        data: rows.map((r) => r.xp_value),
        smooth: true,
        symbol: "none",
        lineStyle: { width: 1, color: "#94a3b8", opacity: 0.5 },
        markArea: {
          silent: true,
          data: modeMarkAreas(rows, modeColor),
        },
      },
      {
        type: "scatter",
        name: "trades",
        data: markerData,
        symbolSize: 9,
        z: 10,
      },
    ],
  };
}

function markerY(r) {
  // Spread markers across the ribbon so overlapping trades on one date don't stack.
  if (r == null) return 0.5;
  return Number(r) >= 1 ? 1.2 : Number(r) >= 0 ? 0.8 : 0.2;
}

function modeMarkAreas(rows, modeColor) {
  // Build contiguous [start, end] runs of each market_mode and shade them.
  const areas = [];
  let runStart = 0;
  for (let i = 1; i <= rows.length; i++) {
    const prev = rows[i - 1]?.market_mode;
    const curr = rows[i]?.market_mode;
    if (curr !== prev || i === rows.length) {
      const mode = prev;
      const color = (modeColor[mode] || "#94a3b8") + "22"; // hex alpha
      areas.push({ xAxis: [runStart, i - 1], itemStyle: { color } });
      runStart = i;
    }
  }
  return areas;
}

function SectorRotationScatter() {
  return (
    <section className="mt-4 border border-hairline bg-card p-3">
      <div className="mb-2 font-mono text-[12px] font-bold uppercase tracking-overline text-ink">
        Sector rotation scatter
      </div>
      <div className="grid h-44 grid-cols-2 grid-rows-2 border border-hairline bg-raised font-mono text-[10px] uppercase tracking-overline text-ink3">
        <div className="border-b border-r border-hairline p-2">improving</div>
        <div className="border-b border-hairline p-2 text-right text-bull">leading</div>
        <div className="border-r border-hairline p-2">lagging</div>
        <div className="p-2 text-right text-warn">weakening</div>
      </div>
    </section>
  );
}

function RegimeSkeleton() {
  return (
    <div className="mb-6 space-y-3">
      <div className="h-40 animate-pulse rounded bg-hairline2" />
      <div className="h-20 animate-pulse rounded bg-hairline2" />
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

function postureVerdict(mode) {
  if (mode === "RISK_ON") return "RISK-ON - press clean longs";
  if (mode === "SELECTIVE") return "SELECTIVE - trade small and picky";
  if (mode === "DEFENSIVE") return "DEFENSIVE - protect capital";
  if (mode === "NO_TRADE") return "NO-TRADE - sit out";
  if (mode === "STALE") return "STALE - wait for fresh data";
  return "UNKNOWN - wait for the law";
}

function fmtPct(value) {
  if (value == null || Number.isNaN(Number(value))) return "-";
  return `${Number(value).toFixed(2).replace(/\.00$/, "")}%`;
}
