import { useEffect, useMemo, useRef, useState } from "react";
import * as echarts from "echarts";
import {
  addJournalTrade,
  closeJournalTrade,
  deleteJournalTrade,
  getExpectancy,
  getJournal,
  getJournalVisuals,
  updateJournalTrade,
} from "../api.js";

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

const COHORTS = [
  { key: "taken", label: "taken" },
  { key: "pushed-skipped", label: "pushed-skipped" },
  { key: "armed-skipped", label: "armed-skipped" },
  { key: "refused", label: "refused" },
];

export default function JournalPage({ onSymbolSelect }) {
  const [journal, setJournal] = useState({ loading: true, error: null, data: null });
  const [expectancy, setExpectancy] = useState({ loading: true, error: null, data: null });
  const [visuals, setVisuals] = useState({ loading: true, error: null, data: null });
  const [form, setForm] = useState(DEFAULT_TRADE);
  const [editingId, setEditingId] = useState(null);

  const load = () => {
    setJournal({ loading: true, error: null, data: null });
    getJournal()
      .then((data) => setJournal({ loading: false, error: null, data }))
      .catch((err) => setJournal({ loading: false, error: err.message, data: null }));
    getExpectancy()
      .then((data) => setExpectancy({ loading: false, error: null, data }))
      .catch((err) => setExpectancy({ loading: false, error: err.message, data: null }));
    getJournalVisuals()
      .then((data) => setVisuals({ loading: false, error: null, data }))
      .catch((err) => setVisuals({ loading: false, error: err.message, data: null }));
  };

  useEffect(() => {
    load();
  }, []);

  const trades = journal.data?.trades || [];
  const closedTrades = useMemo(
    () =>
      trades
        .filter((trade) => trade.r_result != null)
        .slice()
        .sort((a, b) => `${a.trade_date}-${a.trade_id}`.localeCompare(`${b.trade_date}-${b.trade_id}`)),
    [trades],
  );

  const submit = async (event) => {
    event.preventDefault();
    const payload = {
      ...form,
      symbol: form.symbol.toUpperCase(),
      entry: Number(form.entry),
      exit: Number(form.exit),
      stop: Number(form.stop),
      mistake_tags: form.mistake_tags.split(",").map((tag) => tag.trim()).filter(Boolean),
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

  return (
    <main data-testid="journal-page" className="space-y-4">
      <Panel title="EQUITY CURVE in R" subtitle="cumulative R, drawdown shaded" hero>
        <EChart option={equityOption(closedTrades)} className="h-80" />
      </Panel>

      <section className="grid gap-3 xl:grid-cols-[1.35fr_1fr_0.9fr]">
        <Panel title="EXPECTANCY MATRIX" subtitle="cell = posterior R; label = n">
          <EChart option={matrixOption(expectancy.data)} className="h-64" />
        </Panel>
        <Panel title="MFE/MAE scatter">
          <ExcursionPanel trades={trades} />
        </Panel>
        <Panel title="R histogram" subtitle="0.5R bins">
          <EChart option={histogramOption(closedTrades)} className="h-64" />
        </Panel>
      </section>

      <CohortStrip medians={visuals.data?.cohort_medians} counts={visuals.data?.cohort_counts} />

      <Panel title="MISTAKE-TAG PARETO">
        <EChart option={paretoOption(visuals.data?.mistake_pareto, trades)} className="h-56" />
      </Panel>

      <TradesBlock
        form={form}
        setForm={setForm}
        onSubmit={submit}
        editingId={editingId}
        onCancelEdit={() => {
          setEditingId(null);
          setForm(DEFAULT_TRADE);
        }}
        loading={journal.loading}
        error={journal.error}
        trades={trades}
        onSymbolSelect={onSymbolSelect}
        onEdit={onEdit}
        onDelete={onDelete}
        onCloseTrade={onCloseTrade}
      />
    </main>
  );
}

function Panel({ title, subtitle, hero = false, children }) {
  return (
    <section className={`border border-hairline bg-card p-3 ${hero ? "min-h-[22rem]" : ""}`}>
      <div className="mb-2 flex items-baseline justify-between gap-3">
        <h2 className="font-mono text-[11px] font-bold uppercase tracking-overline text-ink">{title}</h2>
        {subtitle && <span className="font-mono text-[10px] uppercase tracking-overline text-ink3">{subtitle}</span>}
      </div>
      {children}
    </section>
  );
}

function EChart({ option, className }) {
  const ref = useRef(null);
  useEffect(() => {
    if (!ref.current) return undefined;
    const chart = echarts.init(ref.current);
    chart.setOption(option, true);
    const resize = () => chart.resize();
    window.addEventListener("resize", resize);
    return () => {
      window.removeEventListener("resize", resize);
      chart.dispose();
    };
  }, [option]);
  return <div ref={ref} className={className} />;
}

function ExcursionPanel({ trades }) {
  const points = trades
    .map((trade) => ({
      symbol: trade.symbol,
      mfe: trade.mfe_r ?? trade.max_favorable_r,
      mae: trade.mae_r ?? trade.max_adverse_r,
      r: trade.r_result,
    }))
    .filter((point) => point.mfe != null && point.mae != null);

  if (!points.length) {
    return (
      <div className="flex h-64 items-center justify-center border border-dashed border-hairline bg-raised px-4 text-center">
        <div>
          <div className="font-mono text-[12px] font-bold uppercase tracking-overline text-ink">needs excursion data</div>
          <p className="mt-2 max-w-xs font-sans text-[12px] leading-5 text-ink3">
            Journal trades do not expose per-trade MFE/MAE yet.
          </p>
        </div>
      </div>
    );
  }

  return <EChart option={excursionOption(points)} className="h-64" />;
}

function CohortStrip({ medians = {}, counts = {} }) {
  const taken = Number(medians.taken?.median_r);
  const pushed = Number(medians["pushed-skipped"]?.median_r);
  const read = Number.isFinite(taken) && Number.isFinite(pushed) && pushed > taken
    ? "you skip winners - pushed-skipped outperform taken"
    : "cohort edge needs more completed outcome data";

  return (
    <section className="border border-hairline bg-card p-3">
      <div className="grid gap-2 md:grid-cols-4">
        {COHORTS.map((cohort) => {
          const row = medians[cohort.key] || {};
          const count = row.n ?? counts[cohort.key] ?? 0;
          return (
            <div key={cohort.key} className="border border-hairline bg-raised p-3">
              <div className="font-mono text-[10px] uppercase tracking-overline text-ink3">{cohort.label}</div>
              <div className={`mt-1 font-mono text-[22px] font-bold tabular-nums ${Number(row.median_r) >= 0 ? "text-bull" : "text-bear"}`}>
                {row.median_r == null ? "n/a" : signed(row.median_r, "R")}
              </div>
              <div className="font-mono text-[10px] uppercase tracking-overline text-ink3">n={count}</div>
            </div>
          );
        })}
      </div>
      <div className="mt-3 border border-hairline bg-bull-bg px-3 py-2 font-sans text-[13px] text-ink">
        <span className="font-mono text-[10px] font-bold uppercase tracking-overline text-ink3">READ: </span>
        {read}
      </div>
    </section>
  );
}

function TradesBlock({
  form,
  setForm,
  onSubmit,
  editingId,
  onCancelEdit,
  loading,
  error,
  trades,
  onSymbolSelect,
  onEdit,
  onDelete,
  onCloseTrade,
}) {
  return (
    <section className="border border-hairline bg-card p-3">
      <div className="mb-3 font-mono text-[11px] font-bold uppercase tracking-overline text-ink">TRADES</div>
      <TradeEntryForm form={form} setForm={setForm} onSubmit={onSubmit} editingId={editingId} onCancelEdit={onCancelEdit} />
      <TradeLogTable
        loading={loading}
        error={error}
        trades={trades}
        onSymbolSelect={onSymbolSelect}
        onEdit={onEdit}
        onDelete={onDelete}
        onCloseTrade={onCloseTrade}
      />
    </section>
  );
}

function TradeEntryForm({ form, setForm, onSubmit, editingId, onCancelEdit }) {
  const update = (key, value) => setForm((current) => ({ ...current, [key]: value }));
  return (
    <form onSubmit={onSubmit} className="mb-3 grid gap-2 border border-hairline bg-raised p-3 lg:grid-cols-8">
      <Field label="Date" type="date" value={form.trade_date} onChange={(value) => update("trade_date", value)} />
      <Field label="Symbol" value={form.symbol} onChange={(value) => update("symbol", value.toUpperCase())} placeholder="RELIANCE" />
      <Field label="Setup" value={form.setup} onChange={(value) => update("setup", value)} placeholder="Pullback" />
      <Field label="Entry" type="number" value={form.entry} onChange={(value) => update("entry", value)} />
      <Field label="Exit" type="number" value={form.exit} onChange={(value) => update("exit", value)} />
      <Field label="Stop" type="number" value={form.stop} onChange={(value) => update("stop", value)} />
      <Field label="Mistakes" value={form.mistake_tags} onChange={(value) => update("mistake_tags", value)} placeholder="chased, late-stop" />
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
        <input value={form.notes} onChange={(event) => update("notes", event.target.value)} className="border border-hairline bg-card px-2 py-1 font-mono text-[12px] text-ink outline-none" />
      </label>
    </form>
  );
}

function TradeLogTable({ loading, error, trades, onSymbolSelect, onEdit, onDelete, onCloseTrade }) {
  return (
    <div>
      <div className="mb-2 grid grid-cols-12 gap-2 border-b border-hairline pb-2 font-mono text-[10px] uppercase tracking-overline text-ink3">
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
    </div>
  );
}

function TradeRow({ trade, onSymbolSelect, onEdit, onDelete, onCloseTrade }) {
  const positive = Number(trade.r_result) >= 0;
  return (
    <li className="grid grid-cols-12 items-center gap-2 border border-hairline2 bg-raised px-2 py-2 text-[12px]">
      <span className="col-span-2 font-mono text-ink2">{trade.trade_date}</span>
      <span className="col-span-2">
        <button type="button" onClick={() => onSymbolSelect?.({ symbol: trade.symbol, source: "journal" })} className="font-mono font-bold uppercase text-ink hover:underline">
          {trade.symbol}
        </button>
      </span>
      <span className="col-span-2 font-mono text-ink2">{trade.setup || "-"}</span>
      <span className={`col-span-1 font-mono font-bold tabular-nums ${positive ? "text-bull" : "text-bear"}`}>{signed(trade.r_result, "R")}</span>
      <span className="col-span-3 flex flex-wrap gap-1">
        {(trade.mistake_tags || []).length ? (
          trade.mistake_tags.map((tag) => (
            <span key={tag} className="rounded-chip border border-bear-border bg-bear-bg px-1.5 py-0.5 font-mono text-[9px] text-bear">{tag}</span>
          ))
        ) : (
          <span className="font-mono text-[10px] text-ink3">-</span>
        )}
      </span>
      <span className={`col-span-1 font-mono uppercase tracking-overline ${positive ? "text-bull" : "text-bear"}`}>{trade.result}</span>
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
          onChange={(event) => setExitPrice(event.target.value)}
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
        onChange={(event) => onChange(event.target.value)}
        className="border border-hairline bg-card px-2 py-1 font-mono text-[12px] text-ink outline-none"
      />
    </label>
  );
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
    grid: { left: 42, right: 18, top: 24, bottom: 32 },
    xAxis: { type: "category", data: labels },
    yAxis: { type: "value", axisLabel: { formatter: "{value}R" } },
    series: [
      { name: "cumulative R", type: "line", smooth: true, data: equity, lineStyle: { width: 3 }, symbolSize: 6 },
      { name: "drawdown", type: "line", data: drawdown, areaStyle: { opacity: 0.18 }, lineStyle: { width: 1 }, symbolSize: 0 },
    ],
  };
}

function matrixOption(expectancy) {
  const rows = expectancy?.system || [];
  const families = [...new Set(rows.map((row) => row.setup_family))];
  const regimes = [...new Set(rows.map((row) => row.regime))];
  const data = rows.map((row) => ({
    value: [regimes.indexOf(row.regime), families.indexOf(row.setup_family), Number(row.posterior_r || 0), Number(row.n || 0)],
    itemStyle: {
      color: Number(row.n || 0) < 20 ? "#d4d4d4" : undefined,
      opacity: Number(row.n || 0) < 20 ? 0.7 : 1,
    },
  }));
  return {
    tooltip: {
      formatter: (point) => {
        const value = point.value || [];
        return `${families[value[1]]} x ${regimes[value[0]]}<br/>${signed(value[2], "R")} / n=${value[3]}`;
      },
    },
    grid: { left: 82, right: 12, top: 20, bottom: 44 },
    xAxis: { type: "category", data: regimes, axisLabel: { rotate: 25 } },
    yAxis: { type: "category", data: families },
    visualMap: { min: -1, max: 1, show: false, inRange: { color: ["#b94a48", "#f0efe9", "#2f855a"] } },
    series: [{
      type: "heatmap",
      data,
      label: { show: true, formatter: (point) => `n=${point.value[3]}` },
    }],
  };
}

function excursionOption(points) {
  return {
    tooltip: { formatter: (point) => `${point.data[2]}<br/>MFE ${signed(point.data[1], "R")}<br/>MAE ${signed(point.data[0], "R")}` },
    grid: { left: 42, right: 16, top: 18, bottom: 36 },
    xAxis: { type: "value", name: "MAE", axisLabel: { formatter: "{value}R" } },
    yAxis: { type: "value", name: "MFE", axisLabel: { formatter: "{value}R" } },
    series: [{
      type: "scatter",
      symbolSize: 10,
      data: points.map((point) => [Number(point.mae), Number(point.mfe), point.symbol, point.r]),
    }],
  };
}

function histogramOption(closed) {
  const bins = new Map();
  closed.forEach((trade) => {
    const value = Number(trade.r_result || 0);
    const start = Math.floor(value / 0.5) * 0.5;
    const label = `${start.toFixed(1)} to ${(start + 0.5).toFixed(1)}R`;
    bins.set(label, (bins.get(label) || 0) + 1);
  });
  const labels = [...bins.keys()];
  return {
    tooltip: { trigger: "axis" },
    grid: { left: 30, right: 10, top: 18, bottom: 58 },
    xAxis: { type: "category", data: labels, axisLabel: { rotate: 35 } },
    yAxis: { type: "value" },
    series: [{ name: "trades", type: "bar", data: labels.map((label) => bins.get(label)) }],
  };
}

function paretoOption(pareto = [], trades = []) {
  const counts = {};
  pareto.forEach((row) => {
    counts[row.tag] = Number(row.count || 0);
  });
  if (!Object.keys(counts).length) {
    trades.forEach((trade) => {
      (trade.mistake_tags || []).forEach((tag) => {
        counts[tag] = (counts[tag] || 0) + 1;
      });
    });
  }
  const rows = Object.entries(counts).sort((a, b) => b[1] - a[1]).slice(0, 8);
  return {
    tooltip: { trigger: "axis" },
    grid: { left: 110, right: 16, top: 16, bottom: 28 },
    xAxis: { type: "value" },
    yAxis: { type: "category", data: rows.map(([tag]) => tag) },
    series: [{ type: "bar", data: rows.map(([, count]) => count) }],
  };
}

function signed(value, suffix = "") {
  if (value == null || Number.isNaN(Number(value))) return "-";
  const rounded = Number(value).toFixed(2).replace(/\.00$/, "");
  return `${Number(value) > 0 ? "+" : ""}${rounded}${suffix}`;
}
