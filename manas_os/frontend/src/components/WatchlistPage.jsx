import { useEffect, useMemo, useRef, useState } from "react";
import * as echarts from "echarts";
import { addWatchlist, deleteWatchlist, getPortfolioHeat, getRegimeSummary, getWatchlist } from "../api.js";
import DataStamp from "./DataStamp.jsx";
import InfoDot from "./InfoDot.jsx";
import Read from "./Read.jsx";
import SymbolChip from "./SymbolChip.jsx";

export default function WatchlistPage({ posture, onSymbolSelect }) {
  const [summary, setSummary] = useState(null);
  const [heat, setHeat] = useState({ loading: true, error: null, data: null });
  const [watch, setWatch] = useState({ loading: true, error: null, data: null });
  const [symbol, setSymbol] = useState("");
  const [note, setNote] = useState("");

  useEffect(() => {
    let cancelled = false;
    getRegimeSummary()
      .then((d) => !cancelled && setSummary(d?.available ? d : null))
      .catch(() => !cancelled && setSummary(null));
    getPortfolioHeat()
      .then((d) => !cancelled && setHeat({ loading: false, error: null, data: d }))
      .catch((e) => !cancelled && setHeat({ loading: false, error: e.message, data: null }));
    return () => {
      cancelled = true;
    };
  }, []);

  const loadWatchlist = () => {
    setWatch({ loading: true, error: null, data: null });
    getWatchlist()
      .then((d) => setWatch({ loading: false, error: null, data: d }))
      .catch((e) => setWatch({ loading: false, error: e.message, data: null }));
  };

  useEffect(() => {
    loadWatchlist();
  }, []);

  const onAdd = async (event) => {
    event.preventDefault();
    if (!symbol.trim()) return;
    await addWatchlist(symbol, note || null);
    setSymbol("");
    setNote("");
    loadWatchlist();
  };

  const onDrop = async (sym) => {
    await deleteWatchlist(sym);
    loadWatchlist();
  };

  return (
    <section data-testid="watchlist-page" className="space-y-4">
      <PositionSizer summary={summary} posture={posture} />
      <HeatRow heat={heat} />
      <form onSubmit={onAdd} className="flex flex-wrap items-end gap-2 border border-hairline bg-card p-3">
        <label className="flex flex-col gap-1 font-mono text-[10px] uppercase tracking-overline text-ink3">
          Symbol
          <input
            value={symbol}
            onChange={(e) => setSymbol(e.target.value.toUpperCase())}
            placeholder="RELIANCE"
            className="w-36 border border-hairline bg-raised px-2 py-1 font-mono text-[12px] text-ink outline-none"
          />
        </label>
        <label className="flex flex-1 flex-col gap-1 font-mono text-[10px] uppercase tracking-overline text-ink3">
          Note
          <input
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="near pivot, watch RVOL"
            className="min-w-48 border border-hairline bg-raised px-2 py-1 font-mono text-[12px] text-ink outline-none"
          />
        </label>
        <button type="submit" className="border border-ink bg-ink px-3 py-1 font-mono text-[10px] uppercase tracking-overline text-white">
          + Watchlist
        </button>
      </form>
      <WatchlistTable posture={posture} state={watch} onDrop={onDrop} onSymbolSelect={onSymbolSelect} />
      <DataStamp />
    </section>
  );
}

function EChart({ option, className = "h-44" }) {
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

function HeatRow({ heat }) {
  const data = heat.data || {};
  const rolling = data.rolling_10_avg_r || {};
  const sectors = Object.entries(data.sector_counts || {});
  const gauge = useMemo(() => ({
    series: [{
      type: "gauge",
      min: 0,
      max: Math.max(Number(data.cap_pct || 0), Number(data.open_risk_pct || 0), 1),
      progress: { show: true },
      axisLabel: { formatter: "{value}%" },
      detail: { formatter: `${fmtNum(data.open_risk_pct)}%`, fontSize: 18 },
      data: [{ value: Number(data.open_risk_pct || 0), name: `cap ${fmtNum(data.cap_pct)}%` }],
    }],
  }), [data.cap_pct, data.open_risk_pct]);
  const donut = useMemo(() => ({
    tooltip: { trigger: "item" },
    series: [{
      type: "pie",
      radius: ["48%", "76%"],
      label: { formatter: "{b} {c}", fontSize: 10 },
      data: sectors.map(([name, value]) => ({ name, value })),
    }],
  }), [sectors]);
  return (
    <section className="grid gap-3 border border-hairline bg-card p-3 lg:grid-cols-3">
      <div>
        <div className="mb-1 font-mono text-[11px] font-bold uppercase tracking-overline text-ink">Open risk</div>
        <EChart option={gauge} />
      </div>
      <div>
        <div className="mb-1 font-mono text-[11px] font-bold uppercase tracking-overline text-ink">Sector donut</div>
        {sectors.length ? <EChart option={donut} /> : <div className="flex h-44 items-center justify-center font-mono text-[11px] text-ink3">no open sectors</div>}
      </div>
      <div className="flex flex-col justify-center border border-hairline bg-raised p-3">
        <div className="font-mono text-[11px] font-bold uppercase tracking-overline text-ink">Progressive exposure</div>
        <div className={"mt-2 w-fit rounded-chip border px-2 py-1 font-mono text-[12px] font-bold uppercase tracking-overline " + (data.half_size_mode ? "border-bear-border bg-bear-bg text-bear" : "border-bull-border bg-bull-bg text-bull")}>
          {data.half_size_mode ? "HALF SIZE MODE" : "FULL SIZE MODE"}
        </div>
        <div className="mt-2 font-sans text-[12px] text-ink3">
          last-10-trade avg R: {rolling.value == null ? "not enough closed trades" : signed(rolling.value, "R")} (n={rolling.n || 0})
        </div>
        {heat.error && <div className="mt-2 font-mono text-[10px] text-bear">{heat.error}</div>}
      </div>
    </section>
  );
}

function PositionSizer({ summary, posture }) {
  const [capital, setCapital] = useState(1000000);
  const [riskPct, setRiskPct] = useState(0.5);
  const [riskTouched, setRiskTouched] = useState(false);
  const [entry, setEntry] = useState(1000);
  const [stop, setStop] = useState(970);

  const mode = summary?.market_mode || posture || "UNKNOWN";
  useEffect(() => {
    if (riskTouched) return;
    if (mode === "RISK_ON") setRiskPct(0.5);
    if (mode === "SELECTIVE") setRiskPct(0.25);
  }, [mode, riskTouched]);

  const maxRisk = typeof summary?.allowed_risk_max_pct === "number" ? summary.allowed_risk_max_pct : riskPct;
  const noTrade = mode === "NO_TRADE" || posture === "STALE";
  const usedRisk = noTrade ? 0 : Math.min(riskPct, maxRisk);
  const clamped = !noTrade && riskPct > maxRisk;
  const stopDist = Math.max(0, Number(entry) - Number(stop));

  const calc = useMemo(() => {
    if (noTrade || stopDist <= 0 || capital <= 0 || usedRisk <= 0) return { shares: 0, positionValue: 0, riskRupees: 0 };
    const riskBudget = Number(capital) * (usedRisk / 100);
    const shares = Math.floor(riskBudget / stopDist);
    return { shares, positionValue: shares * Number(entry), riskRupees: shares * stopDist };
  }, [capital, entry, noTrade, stopDist, usedRisk]);

  return (
    <section data-testid="position-sizer" className="sticky top-0 z-10 border border-hairline bg-card p-3">
      <div className="mb-2 flex items-center gap-2">
        <span className="font-mono text-[12px] font-bold uppercase tracking-overline text-ink">Position size calculator</span>
        <InfoDot term="risk" />
      </div>
      <div className="grid gap-2 md:grid-cols-4">
        <NumberField label="Capital" value={capital} onChange={setCapital} prefix="Rs" />
        <NumberField label="Risk %" value={riskPct} onChange={(value) => { setRiskTouched(true); setRiskPct(value); }} step="0.05" />
        <NumberField label="Entry" value={entry} onChange={setEntry} prefix="Rs" />
        <NumberField label="Stop" value={stop} onChange={setStop} prefix="Rs" />
      </div>
      <div className="mt-3 grid gap-2 border border-hairline bg-raised p-3 sm:grid-cols-3">
        <Result label="Shares" value={calc.shares.toLocaleString("en-IN")} />
        <Result label="Position" value={`Rs${Math.round(calc.positionValue).toLocaleString("en-IN")}`} />
        <Result label="Risk" value={`Rs${Math.round(calc.riskRupees).toLocaleString("en-IN")}`} />
      </div>
      {noTrade ? (
        <p className="mt-2 font-sans text-[12px] text-bear">{posture === "STALE" ? "No new risk while market data is stale." : `No new risk in ${mode} regime.`}</p>
      ) : clamped ? (
        <p className="mt-2 font-sans text-[12px] text-warn">Regime-gated: {mode} caps risk at {maxRisk}%; using the cap.</p>
      ) : (
        <p className="mt-2 font-sans text-[12px] text-ink3">Using {usedRisk}% risk and Rs{fmt(stopDist)} stop distance per share.</p>
      )}
    </section>
  );
}

function WatchlistTable({ posture, state, onDrop, onSymbolSelect }) {
  const noTrade = posture === "NO_TRADE" || posture === "STALE";
  const [sort, setSort] = useState({ key: null, dir: null });
  const rows = state.data?.items || [];
  const hasDeliveryZ = rows.some((item) => item.timing?.delivery_z != null || item.delivery_z != null);
  const items = useMemo(() => {
    if (!sort.key || !sort.dir) return rows;
    return [...rows].sort((a, b) => {
      const av = sortValue(a, sort.key);
      const bv = sortValue(b, sort.key);
      return sort.dir === "desc" ? bv - av : av - bv;
    });
  }, [rows, sort]);
  const cycle = (key) => setSort((prev) => {
    if (prev.key !== key) return { key, dir: "desc" };
    if (prev.dir === "desc") return { key, dir: "asc" };
    if (prev.dir === "asc") return { key: null, dir: null };
    return { key, dir: "desc" };
  });
  return (
    <section className="border border-hairline bg-card p-3">
      <div className="mb-2 grid grid-cols-12 gap-2 font-mono text-[10px] uppercase tracking-overline text-ink3">
        <span className="col-span-4">Symbol</span>
        <span className="col-span-1">RVOL</span>
        <span className="col-span-1">Gap%</span>
        <span className="col-span-2">Dist-pivot</span>
        <button type="button" title="Average daily range - how much this name moves in a day. Bigger = more swing per unit time but wider stops." onClick={() => cycle("adr")} className="col-span-1 text-left">
          ADR% {sortMark(sort, "adr")}
        </button>
        <button type="button" onClick={() => cycle("delivery_z")} className="col-span-1 text-left">
          {hasDeliveryZ ? "DLV_Z" : "DLV%"} {sortMark(sort, "delivery_z")}
        </button>
        <span className="col-span-2 text-right">Actions</span>
      </div>
      {state.loading ? (
        <div className="py-6 font-mono text-[11px] text-ink3">loading watchlist...</div>
      ) : state.error ? (
        <div className="py-6 font-mono text-[11px] text-bear">{state.error}</div>
      ) : items.length === 0 ? (
        <div className="border border-dashed border-hairline px-4 py-8 text-center">
          <div className="font-mono text-[12px] font-bold uppercase tracking-overline text-ink">No watchlist symbols yet</div>
          <Read band={noTrade ? "bear" : "muted"} verdict={noTrade ? "NO NEW RISK" : "READY"}>
            Add tickers above; timing columns populate from daily_prices, not a fake live feed.
          </Read>
        </div>
      ) : (
        <ul className="space-y-1.5">
          {items.map((item) => <WatchRow key={item.symbol} item={item} onDrop={onDrop} onSymbolSelect={onSymbolSelect} />)}
        </ul>
      )}
    </section>
  );
}

function WatchRow({ item, onDrop, onSymbolSelect }) {
  const t = item.timing || {};
  return (
    <li className="border border-hairline2 bg-raised px-2 py-2">
      <div className="grid grid-cols-12 items-center gap-2 text-[12px]">
        <div className="col-span-4">
          <SymbolChip symbol={item.symbol} deliveryPct={t.delivery_pct} deliveryAsOf={t.as_of} onSelect={onSymbolSelect} />
          {item.note && <div className="mt-1 font-sans text-[11px] text-ink3">{item.note}</div>}
          <ExitChips exitState={item.exit_state} />
        </div>
        <MetricCell value={t.rvol == null ? "-" : `${t.rvol.toFixed(2)}x`} band={t.rvol >= 1.5 ? "bull" : "muted"} />
        <MetricCell value={fmtSigned(t.gap_pct, "%")} band={t.gap_pct > 0 ? "bull" : t.gap_pct < 0 ? "bear" : "muted"} />
        <MetricCell wide value={fmtSigned(t.dist_pivot, "%")} band={Math.abs(t.dist_pivot || 99) <= 1 ? "bull" : "muted"} />
        <MetricCell value={item.adr == null ? "-" : `${item.adr.toFixed(1)}%`} band="muted" />
        <MetricCell value={deliveryValue(item)} band={(t.delivery_z ?? item.delivery_z ?? t.delivery_pct) >= 60 ? "bull" : "muted"} />
        <div className="col-span-2 flex justify-end gap-1">
          <button type="button" onClick={() => onSymbolSelect?.({ symbol: item.symbol, deliveryPct: t.delivery_pct, deliveryAsOf: t.as_of })} className="border border-hairline px-2 py-0.5 font-mono text-[10px] uppercase tracking-overline text-ink2 hover:border-ink hover:text-ink">chart</button>
          <button type="button" onClick={() => onDrop(item.symbol)} className="border border-hairline px-2 py-0.5 font-mono text-[10px] uppercase tracking-overline text-bear hover:border-bear">drop</button>
        </div>
      </div>
      <CoachLine coach={item.coach} />
      <Read band="muted">{t.read || "No timing read yet."}</Read>
    </li>
  );
}

function CoachLine({ coach }) {
  if (!coach) return null;
  const band = coach.exit_now ? "bear" : coach.phase === "EXTENSION" ? "warn" : coach.phase === "TREND" ? "bull" : "muted";
  const cls = { bull: "text-bull", warn: "text-warn", bear: "text-bear", muted: "text-ink3" }[band];
  const text = coach.exit_now ? `EXIT TODAY - ${(coach.fired || []).join(", ")}` : coach.action;
  return <div className={`mt-1 font-mono text-[10px] uppercase tracking-overline ${cls}`}>{text}</div>;
}

function ExitChips({ exitState }) {
  if (!exitState) return null;
  const band = exitState.state === "Broken" ? "bear" : exitState.state === "Weakening" ? "warn" : "bull";
  const cls = { bull: "border-bull-border bg-bull-bg text-bull", warn: "border-warn-border bg-warn-bg text-warn", bear: "border-bear-border bg-bear-bg text-bear" }[band];
  return (
    <div className="mt-1 flex flex-wrap gap-1">
      <span className={`rounded-chip border px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-overline ${cls}`}>exit {exitState.state}</span>
      {(exitState.fired_rules || []).slice(0, 3).map((rule) => (
        <span key={rule.rule} title={rule.detail} className="rounded-chip border border-hairline bg-card px-1.5 py-0.5 font-mono text-[9px] text-ink3">{rule.rule}</span>
      ))}
    </div>
  );
}

function MetricCell({ value, band = "muted", wide = false }) {
  const cls = { bull: "text-bull", bear: "text-bear", muted: "text-ink2", info: "text-info" }[band];
  return <div className={(wide ? "col-span-2" : "col-span-1") + " font-mono tabular-nums " + cls}>{value}</div>;
}

function NumberField({ label, value, onChange, prefix = "", step = "1" }) {
  return (
    <label className="flex flex-col gap-1 font-mono text-[10px] uppercase tracking-overline text-ink3">
      {label}
      <span className="flex items-center border border-hairline bg-raised px-2 py-1">
        {prefix && <span className="mr-1 text-ink3">{prefix}</span>}
        <input type="number" min="0" step={step} value={value} onChange={(e) => onChange(Number(e.target.value))} className="w-full bg-transparent font-mono text-[12px] tabular-nums text-ink outline-none" />
      </span>
    </label>
  );
}

function Result({ label, value }) {
  return (
    <div>
      <div className="font-mono text-[9px] uppercase tracking-overline text-ink3">{label}</div>
      <div className="font-mono text-[18px] font-bold tabular-nums text-ink">{value}</div>
    </div>
  );
}

function sortValue(item, key) {
  if (key === "adr") return Number(item.adr ?? -Infinity);
  if (key === "delivery_z") return Number(item.timing?.delivery_z ?? item.delivery_z ?? item.timing?.delivery_pct ?? -Infinity);
  return -Infinity;
}

function sortMark(sort, key) {
  if (sort.key !== key) return "";
  return sort.dir === "desc" ? "desc" : "asc";
}

function deliveryValue(item) {
  const z = item.timing?.delivery_z ?? item.delivery_z;
  if (z != null) return `${Number(z).toFixed(1)}z`;
  const pct = item.timing?.delivery_pct;
  return pct == null ? "-" : `${pct.toFixed(0)}%`;
}

function fmtSigned(value, suffix = "") {
  if (value == null) return "-";
  return `${value > 0 ? "+" : ""}${value.toFixed(1)}${suffix}`;
}

function signed(value, suffix = "") {
  if (value == null) return "-";
  return `${value > 0 ? "+" : ""}${Number(value).toFixed(2).replace(/\.00$/, "")}${suffix}`;
}

function fmtNum(n) {
  return Number(n || 0).toFixed(2).replace(/\.00$/, "");
}

function fmt(n) {
  return Number.isFinite(n) ? n.toFixed(2).replace(/\.00$/, "") : "0";
}
