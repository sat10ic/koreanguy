import { useEffect, useMemo, useRef, useState } from "react";
import * as echarts from "echarts";
import { addJournalTrade, closeJournalTrade, deleteJournalTrade, getExpectancy, getGateHealth, getJournal, getJournalVisuals, updateJournalTrade } from "../api.js";
import DataStamp from "./DataStamp.jsx";
import InfoDot from "./InfoDot.jsx";
import MentorChecklistPanel from "./MentorChecklistPanel.jsx";
import Read from "./Read.jsx";
import SymbolChip from "./SymbolChip.jsx";
import { Caption, MetricTape, PosterBand, PosterCanvas, ProximityBar, SectionBadge, Verdict } from "./poster/Primitives.jsx";

const DEFAULT_TRADE = {
  trade_date: new Date().toISOString().slice(0, 10),
  symbol: "",
  setup: "",
  entry: "",
  exit: "",
  stop: "",
  mistake_tags: "",
  notes: "",
};

export default function JournalPage({ onSymbolSelect }) {
  const [state, setState] = useState({ loading: true, error: null, data: null });
  const [expectancy, setExpectancy] = useState({ loading: true, error: null, data: null });
  const [visuals, setVisuals] = useState({ loading: true, error: null, data: null });
  const [gateHealth, setGateHealth] = useState({ loading: true, error: null, data: null });
  const [form, setForm] = useState(DEFAULT_TRADE);
  const [editingId, setEditingId] = useState(null);

  const load = () => {
    setState({ loading: true, error: null, data: null });
    getJournal()
      .then((d) => setState({ loading: false, error: null, data: d }))
      .catch((e) => setState({ loading: false, error: e.message, data: null }));
    getExpectancy()
      .then((d) => setExpectancy({ loading: false, error: null, data: d }))
      .catch((e) => setExpectancy({ loading: false, error: e.message, data: null }));
    getJournalVisuals()
      .then((d) => setVisuals({ loading: false, error: null, data: d }))
      .catch((e) => setVisuals({ loading: false, error: e.message, data: null }));
    getGateHealth({ days: 60 })
      .then((d) => setGateHealth({ loading: false, error: null, data: d }))
      .catch((e) => setGateHealth({ loading: false, error: e.message, data: null }));
  };

  useEffect(() => {
    load();
  }, []);

  const submit = async (event) => {
    event.preventDefault();
    const payload = {
      ...form,
      symbol: form.symbol.toUpperCase(),
      entry: Number(form.entry),
      exit: Number(form.exit),
      stop: Number(form.stop),
      mistake_tags: form.mistake_tags.split(",").map((t) => t.trim()).filter(Boolean),
    };
    if (editingId) {
      await updateJournalTrade(editingId, payload);
    } else {
      await addJournalTrade(payload);
    }
    setForm(DEFAULT_TRADE);
    setEditingId(null);
    load();
  };

  const onEdit = (trade) => {
    setEditingId(trade.trade_id);
    setForm({
      trade_date: trade.trade_date || DEFAULT_TRADE.trade_date,
      symbol: trade.symbol || "",
      setup: trade.setup || "",
      entry: trade.entry ?? "",
      exit: trade.exit ?? "",
      stop: trade.stop ?? "",
      mistake_tags: (trade.mistake_tags || []).join(", "),
      notes: trade.notes || "",
    });
  };

  const onDelete = async (tradeId) => {
    await deleteJournalTrade(tradeId);
    if (editingId === tradeId) {
      setEditingId(null);
      setForm(DEFAULT_TRADE);
    }
    load();
  };

  const onCloseTrade = async (tradeId, payload) => {
    await closeJournalTrade(tradeId, payload);
    load();
  };

  const stats = state.data?.stats || {};
  const trades = state.data?.trades || [];

  return (
    <PosterCanvas data-testid="journal-page" className="space-y-4">
      <PosterBand state="info" kicker="JOURNAL" title="the moat rendered">
        <ExpectancyHeader stats={stats} />
        <JournalCharts trades={trades} stats={stats} expectancy={expectancy.data} />
        <LearningVisuals visuals={visuals.data} gateHealth={gateHealth.data} />
      </PosterBand>
      <TradeEntryForm
        form={form}
        setForm={setForm}
        onSubmit={submit}
        editingId={editingId}
        onCancelEdit={() => {
          setEditingId(null);
          setForm(DEFAULT_TRADE);
        }}
      />
      <TradeLogTable
        loading={state.loading}
        error={state.error}
        trades={trades}
        onSymbolSelect={onSymbolSelect}
        onEdit={onEdit}
        onDelete={onDelete}
        onCloseTrade={onCloseTrade}
      />
      <MentorChecklistPanel />
      <DataStamp />
    </PosterCanvas>
  );
}

function LearningVisuals({ visuals, gateHealth }) {
  const cohorts = visuals?.cohort_counts || {};
  const medians = gateHealth?.rolling_t10_medians || [];
  return (
    <PosterBand state="info" kicker="learning loop" title="near-miss and refusal intelligence">
      <MetricTape
        items={[
          { label: "taken", value: cohorts.taken ?? 0, sub: "executed setups", state: "bull" },
          { label: "skipped", value: cohorts.skipped ?? 0, sub: "manual refusals", state: "warn" },
          { label: "tracked near-miss", value: cohorts.tracked_near_miss ?? 0, sub: "organic watch lane", state: "info" },
          { label: "refused", value: cohorts.refused ?? 0, sub: "scanner hard no", state: "bear" },
        ]}
      />
      <div className="mt-3 grid gap-3 xl:grid-cols-3">
        <Panel title="Refusal funnel over time">
          <EChart option={refusalTimeOption(gateHealth)} />
        </Panel>
        <Panel title="T+10 cohort medians">
          <EChart option={medianOption(medians)} />
        </Panel>
        <Panel title="Slippage tracker">
          <EChart option={slippageOption(visuals?.slippage || [])} />
        </Panel>
      </div>
      <div className="mt-3">
        <Panel title="Near-miss verdict (passed vs refused-near cohort T+10)">
          <EChart option={nearMissVerdictOption(medians)} className="h-44" />
          <div className="mt-1 font-sans text-[11px] text-ink2">If near-miss line/median stays above passed, gate calibration review needed (see VIZ_BRAINSTORM).</div>
        </Panel>
      </div>
    </PosterBand>
  );
}

function EChart({ option, className = "h-56" }) {
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

function JournalCharts({ trades, stats, expectancy }) {
  const closed = trades.filter((t) => t.r_result != null).slice().sort((a, b) => String(a.trade_date).localeCompare(String(b.trade_date)));
  return (
    <section className="space-y-3">
      <Panel title="Equity curve in R">
        <EChart option={equityOption(closed)} className="h-64" />
      </Panel>
      <div className="grid gap-3 xl:grid-cols-3">
        <Panel title="Expectancy matrix">
          <EChart option={matrixOption(expectancy)} />
        </Panel>
        <Panel title="R histogram">
          <EChart option={histogramOption(closed)} />
        </Panel>
        <Panel title="Mistake-tag Pareto">
          <EChart option={paretoOption(stats, trades)} />
        </Panel>
      </div>
    </section>
  );
}

function Panel({ title, children }) {
  return (
    <div className="border border-hairline bg-card p-3">
      <div className="mb-2 font-mono text-[11px] font-bold uppercase tracking-overline text-ink">{title}</div>
      {children}
    </div>
  );
}

function refusalTimeOption(gateHealth) {
  const rows = gateHealth?.refusal_counts || [];
  const dates = [...new Set(rows.map((r) => r.date))];
  const gates = [...new Set(rows.map((r) => r.gate))];
  return {
    tooltip: { trigger: "axis" },
    legend: { type: "scroll", textStyle: { fontSize: 9 } },
    grid: { left: 38, right: 12, top: 28, bottom: 28 },
    xAxis: { type: "category", data: dates },
    yAxis: { type: "value" },
    series: gates.map((gate) => ({
      name: gate,
      type: "bar",
      stack: "refusals",
      data: dates.map((date) => rows.find((r) => r.date === date && r.gate === gate)?.count || 0),
    })),
  };
}

function medianOption(rows) {
  return {
    tooltip: { trigger: "axis" },
    grid: { left: 36, right: 14, top: 16, bottom: 34 },
    xAxis: { type: "category", data: rows.map((r) => r.source) },
    yAxis: { type: "value", axisLabel: { formatter: "{value}%" } },
    series: [{ type: "bar", data: rows.map((r) => r.median_ret_10 || 0), label: { show: true, formatter: (p) => `${p.value}%` } }],
  };
}

/** Near-miss verdict chart (VIZ_BRAINSTORM Tier 1): compare T+10 outcomes for passed vs near-miss/refused cohorts. */
function nearMissVerdictOption(medians = []) {
  // medians: [{source, median_ret_10, n}]
  const passed = medians.find((m) => /pass/i.test(m.source || "")) || medians[0] || {};
  const near = medians.find((m) => /near|refus|miss/i.test(m.source || "")) || medians[1] || {};
  const data = [
    { name: "PASSED", value: passed.median_ret_10 ?? 0, n: passed.n || 0 },
    { name: "NEAR-MISS", value: near.median_ret_10 ?? 0, n: near.n || 0 },
  ];
  return {
    tooltip: { trigger: "item" },
    grid: { left: 24, right: 12, top: 16, bottom: 28 },
    xAxis: { type: "category", data: data.map((d) => d.name) },
    yAxis: { type: "value", name: "med T+10 R", axisLabel: { formatter: "{value}R" } },
    series: [{
      type: "bar",
      data: data.map((d) => ({ value: d.value, itemStyle: { color: d.name === "PASSED" ? "#0f7a3d" : "#9a5b00" } })),
      label: { show: true, formatter: (p) => `${p.value}R (n=${data.find((dd) => dd.name === p.name)?.n || 0})` },
    }],
  };
}

function slippageOption(rows) {
  return {
    tooltip: { trigger: "axis" },
    grid: { left: 38, right: 12, top: 18, bottom: 42 },
    xAxis: { type: "category", data: rows.map((r) => r.symbol) },
    yAxis: { type: "value", axisLabel: { formatter: "{value}%" } },
    series: [{ type: "scatter", symbolSize: 12, data: rows.map((r) => r.slip_pct || 0) }],
  };
}

function equityOption(closed) {
  let cumulative = 0;
  let peak = 0;
  const labels = [];
  const equity = [];
  const drawdown = [];
  closed.forEach((trade) => {
    cumulative += Number(trade.r_result || 0);
    peak = Math.max(peak, cumulative);
    labels.push(trade.trade_date);
    equity.push(Number(cumulative.toFixed(2)));
    drawdown.push(Number((cumulative - peak).toFixed(2)));
  });
  return {
    tooltip: { trigger: "axis" },
    grid: { left: 36, right: 16, top: 20, bottom: 28 },
    xAxis: { type: "category", data: labels },
    yAxis: { type: "value" },
    series: [
      { name: "cumulative R", type: "line", smooth: true, data: equity, lineStyle: { width: 2 } },
      { name: "drawdown", type: "line", data: drawdown, areaStyle: { opacity: 0.18 }, lineStyle: { width: 1 } },
    ],
  };
}

function matrixOption(expectancy) {
  const rows = expectancy?.system || [];
  const families = [...new Set(rows.map((r) => r.setup_family))];
  const regimes = [...new Set(rows.map((r) => r.regime))];
  const data = rows.map((r) => ({
    value: [regimes.indexOf(r.regime), families.indexOf(r.setup_family), Number(r.posterior_r || 0), r.n],
    itemStyle: { opacity: r.n < 20 ? 0.35 : 0.95 },
  }));
  return {
    tooltip: { formatter: (p) => `${families[p.value[1]]} x ${regimes[p.value[0]]}<br/>${p.value[2]}R, n=${p.value[3]}` },
    grid: { left: 78, right: 12, top: 16, bottom: 40 },
    xAxis: { type: "category", data: regimes },
    yAxis: { type: "category", data: families },
    visualMap: { min: -1, max: 1, show: false },
    series: [{
      type: "heatmap",
      data,
      label: { show: true, formatter: (p) => `n=${p.value[3]}` },
    }],
  };
}

function histogramOption(closed) {
  const bins = new Map();
  closed.forEach((t) => {
    const r = Number(t.r_result || 0);
    const bin = Math.floor(r / 0.5) * 0.5;
    const label = `${bin.toFixed(1)} to ${(bin + 0.5).toFixed(1)}R`;
    bins.set(label, (bins.get(label) || 0) + 1);
  });
  const labels = [...bins.keys()];
  return {
    tooltip: { trigger: "axis" },
    grid: { left: 28, right: 10, top: 18, bottom: 54 },
    xAxis: { type: "category", data: labels, axisLabel: { rotate: 35 } },
    yAxis: { type: "value" },
    series: [{ type: "bar", data: labels.map((label) => bins.get(label)) }],
  };
}

function paretoOption(stats, trades) {
  const counts = {};
  trades.forEach((trade) => (trade.mistake_tags || []).forEach((tag) => {
    counts[tag] = (counts[tag] || 0) + 1;
  }));
  if (stats.top_mistake && !counts[stats.top_mistake]) counts[stats.top_mistake] = 1;
  const rows = Object.entries(counts).sort((a, b) => b[1] - a[1]).slice(0, 8);
  return {
    tooltip: { trigger: "axis" },
    grid: { left: 90, right: 12, top: 18, bottom: 28 },
    xAxis: { type: "value" },
    yAxis: { type: "category", data: rows.map(([tag]) => tag) },
    series: [{ type: "bar", data: rows.map(([, n]) => n) }],
  };
}

function ExpectancyHeader({ stats }) {
  const expectancy = stats.expectancy_r;
  const band = expectancy == null ? "muted" : expectancy > 0 ? "bull" : expectancy < 0 ? "bear" : "muted";
  return (
    <section className="border border-hairline bg-card p-3">
      <div className="mb-4">
        <SectionBadge label="JOURNAL" state={band} />
        <div className="mt-3">
          <Verdict>{expectancy == null ? "NO TRADES LOGGED" : expectancy > 0 ? "EDGE POSITIVE" : "CHECK THE LEAK"}</Verdict>
          <Caption>
            {stats.count
              ? `Expectancy is ${signed(expectancy, "R")}; biggest leak ${stats.top_mistake || "not tagged yet"}.`
              : "Log completed trades to see expectancy and repeat mistakes."}
          </Caption>
        </div>
      </div>
      <div className="grid gap-2 sm:grid-cols-4">
        <Metric label="Win%" value={stats.win_pct == null ? "-" : `${stats.win_pct.toFixed(0)}%`} />
        <Metric label="Avg R" value={stats.avg_r == null ? "-" : signed(stats.avg_r, "R")} />
        <Metric label="Expectancy" value={expectancy == null ? "-" : signed(expectancy, "R")} term="expectancy" />
        <Metric label="Trades" value={String(stats.count || 0)} />
      </div>
      <Read band={band} verdict={expectancy == null ? "NO TRADES" : expectancy > 0 ? "EDGE POSITIVE" : "CHECK LEAKS"}>
        {stats.count
          ? `Expectancy is ${signed(expectancy, "R")}; biggest leak ${stats.top_mistake || "not tagged yet"}.`
          : "Log completed trades to see expectancy and repeat mistakes."}
      </Read>
    </section>
  );
}

function TradeEntryForm({ form, setForm, onSubmit, editingId, onCancelEdit }) {
  const update = (key, value) => setForm((f) => ({ ...f, [key]: value }));
  return (
    <form onSubmit={onSubmit} className="grid gap-2 border border-hairline bg-card p-3 lg:grid-cols-8">
      <Field label="Date" type="date" value={form.trade_date} onChange={(v) => update("trade_date", v)} />
      <Field label="Symbol" value={form.symbol} onChange={(v) => update("symbol", v.toUpperCase())} placeholder="RELIANCE" />
      <Field label="Setup" value={form.setup} onChange={(v) => update("setup", v)} placeholder="Pullback" />
      <Field label="Entry" type="number" value={form.entry} onChange={(v) => update("entry", v)} />
      <Field label="Exit" type="number" value={form.exit} onChange={(v) => update("exit", v)} />
      <Field label="Stop" type="number" value={form.stop} onChange={(v) => update("stop", v)} />
      <Field label="Mistakes" value={form.mistake_tags} onChange={(v) => update("mistake_tags", v)} placeholder="chased, late-stop" />
      <div className="flex items-end gap-1">
        <button type="submit" className="border border-ink bg-ink px-3 py-1 font-mono text-[10px] uppercase tracking-overline text-white">
          {editingId ? "Save trade" : "Add trade"}
        </button>
        {editingId && (
          <button type="button" onClick={onCancelEdit} className="border border-hairline px-2 py-1 font-mono text-[10px] uppercase tracking-overline text-ink3 hover:border-ink hover:text-ink">
            Cancel
          </button>
        )}
      </div>
      <label className="flex flex-col gap-1 font-mono text-[10px] uppercase tracking-overline text-ink3 lg:col-span-8">
        Notes
        <input value={form.notes} onChange={(e) => update("notes", e.target.value)} className="border border-hairline bg-raised px-2 py-1 font-mono text-[12px] text-ink outline-none" />
      </label>
    </form>
  );
}

function TradeLogTable({ loading, error, trades, onSymbolSelect, onEdit, onDelete, onCloseTrade }) {
  return (
    <section className="border border-hairline bg-card p-3">
      <div className="mb-2 grid grid-cols-12 gap-2 font-mono text-[10px] uppercase tracking-overline text-ink3">
        <span className="col-span-2">Date</span>
        <span className="col-span-2">Symbol</span>
        <span className="col-span-2">Setup</span>
        <span className="col-span-1">R</span>
        <span className="col-span-3">Mistake tags</span>
        <span className="col-span-1">Result</span>
        <span className="col-span-1 text-right">Actions</span>
      </div>
      {loading ? (
        <div className="py-6 font-mono text-[11px] text-ink3">loading journal...</div>
      ) : error ? (
        <div className="py-6 font-mono text-[11px] text-bear">{error}</div>
      ) : trades.length === 0 ? (
        <div className="border border-dashed border-hairline px-4 py-8 text-center">
          <div className="font-mono text-[12px] font-bold uppercase tracking-overline text-ink">No trades logged yet</div>
          <p className="mt-1 font-sans text-[12px] text-ink3">Add a closed trade above to start expectancy tracking.</p>
        </div>
      ) : (
        <ul className="space-y-1">
          {trades.map((trade) => (
            <TradeRow key={trade.trade_id} trade={trade} onSymbolSelect={onSymbolSelect} onEdit={onEdit} onDelete={onDelete} onCloseTrade={onCloseTrade} />
          ))}
        </ul>
      )}
    </section>
  );
}

function TradeRow({ trade, onSymbolSelect, onEdit, onDelete, onCloseTrade }) {
  const positive = trade.r_result > 0;
  return (
    <li className="grid grid-cols-12 items-center gap-2 border border-hairline2 bg-raised px-2 py-2 text-[12px]">
      <span className="col-span-2 font-mono text-ink2">{trade.trade_date}</span>
      <span className="col-span-2">
        <SymbolChip symbol={trade.symbol} onSelect={onSymbolSelect} />
        {trade.exit_state?.state && (
          <span className="mt-1 inline-flex rounded-chip border border-hairline bg-card px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-overline text-ink3">
            exit {trade.exit_state.state}
          </span>
        )}
      </span>
      <span className="col-span-2 font-mono text-ink2">{trade.setup || "-"}</span>
      <span className={"col-span-1 font-mono font-bold tabular-nums " + (positive ? "text-bull" : "text-bear")}>{signed(trade.r_result, "R")}</span>
      <span className="col-span-3 flex flex-wrap gap-1">
        {(trade.mistake_tags || []).length ? trade.mistake_tags.map((tag) => (
          <span key={tag} className="rounded-chip border border-bear-border bg-bear-bg px-1.5 py-0.5 font-mono text-[9px] text-bear">{tag}</span>
        )) : <span className="font-mono text-[10px] text-ink3">-</span>}
      </span>
      <span className={"col-span-1 font-mono uppercase tracking-overline " + (positive ? "text-bull" : "text-bear")}>{trade.result}</span>
      <span className="col-span-1 flex justify-end gap-1">
        {trade.result === "open" && <CloseTradeControl trade={trade} onCloseTrade={onCloseTrade} />}
        <button type="button" onClick={() => onEdit(trade)} className="border border-hairline px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-overline text-ink3 hover:border-ink hover:text-ink">edit</button>
        <button type="button" onClick={() => onDelete(trade.trade_id)} className="border border-hairline px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-overline text-bear hover:border-bear">del</button>
      </span>
    </li>
  );
}

function CloseTradeControl({ trade, onCloseTrade }) {
  const [exitPrice, setExitPrice] = useState("");
  const [guard, setGuard] = useState(null);
  const [error, setError] = useState(null);
  const submit = async (mistakeTag = null) => {
    setError(null);
    try {
      await onCloseTrade(trade.trade_id, {
        exit_price: Number(exitPrice || trade.entry),
        ...(mistakeTag ? { mistake_tag: mistakeTag } : {}),
      });
      setGuard(null);
      setExitPrice("");
    } catch (err) {
      if (err.status === 409 && err.payload?.guard) {
        setGuard(err.payload);
      } else {
        setError(err.message);
      }
    }
  };
  return (
    <span className="flex flex-col items-end gap-1">
      <span className="flex gap-1">
        <input
          type="number"
          step="0.01"
          value={exitPrice}
          onChange={(e) => setExitPrice(e.target.value)}
          placeholder="exit"
          className="w-16 border border-hairline bg-card px-1 py-0.5 font-mono text-[9px] text-ink outline-none"
        />
        <button type="button" onClick={() => submit()} className="border border-hairline px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-overline text-ink3 hover:border-ink hover:text-ink">close</button>
      </span>
      {guard && (
        <span className="col-span-12 flex flex-wrap justify-end gap-1 text-right">
          <span className="w-full font-sans text-[10px] text-bear">{guard.message}</span>
          {(guard.reasons || []).map((reason) => (
            <button key={reason} type="button" onClick={() => submit(reason)} className="border border-bear-border bg-bear-bg px-1.5 py-0.5 font-mono text-[9px] text-bear">
              {reason}
            </button>
          ))}
        </span>
      )}
      {error && <span className="font-sans text-[10px] text-bear">{error}</span>}
    </span>
  );
}

function Field({ label, value, onChange, type = "text", placeholder = "" }) {
  return (
    <label className="flex flex-col gap-1 font-mono text-[10px] uppercase tracking-overline text-ink3">
      {label}
      <input
        type={type}
        value={value}
        placeholder={placeholder}
        required={["Date", "Symbol", "Entry", "Exit", "Stop"].includes(label)}
        step={type === "number" ? "0.01" : undefined}
        onChange={(e) => onChange(e.target.value)}
        className="border border-hairline bg-raised px-2 py-1 font-mono text-[12px] text-ink outline-none"
      />
    </label>
  );
}

function Metric({ label, value, term }) {
  return (
    <div className="border border-hairline bg-raised p-2">
      <div className="flex items-center font-mono text-[9px] uppercase tracking-overline text-ink3">
        {label}
        {term && <InfoDot term={term} />}
      </div>
      <div className="font-mono text-[20px] font-bold tabular-nums text-ink">{value}</div>
    </div>
  );
}

function signed(value, suffix = "") {
  if (value == null) return "-";
  return `${value > 0 ? "+" : ""}${Number(value).toFixed(2).replace(/\.00$/, "")}${suffix}`;
}
