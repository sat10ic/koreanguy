import { useEffect, useState } from "react";
import { addJournalTrade, deleteJournalTrade, getJournal, updateJournalTrade } from "../api.js";
import DataStamp from "./DataStamp.jsx";
import InfoDot from "./InfoDot.jsx";
import Read from "./Read.jsx";
import SymbolChip from "./SymbolChip.jsx";

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
  const [form, setForm] = useState(DEFAULT_TRADE);
  const [editingId, setEditingId] = useState(null);

  const load = () => {
    setState({ loading: true, error: null, data: null });
    getJournal()
      .then((d) => setState({ loading: false, error: null, data: d }))
      .catch((e) => setState({ loading: false, error: e.message, data: null }));
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

  const onCancelEdit = () => {
    setEditingId(null);
    setForm(DEFAULT_TRADE);
  };

  const stats = state.data?.stats || {};
  const trades = state.data?.trades || [];

  return (
    <section data-testid="journal-page" className="space-y-4">
      <ExpectancyHeader stats={stats} />
      <TradeEntryForm
        form={form}
        setForm={setForm}
        onSubmit={submit}
        editingId={editingId}
        onCancelEdit={onCancelEdit}
      />
      <TradeLogTable
        loading={state.loading}
        error={state.error}
        trades={trades}
        onSymbolSelect={onSymbolSelect}
        onEdit={onEdit}
        onDelete={onDelete}
      />
      <DataStamp />
    </section>
  );
}

function ExpectancyHeader({ stats }) {
  const expectancy = stats.expectancy_r;
  const band = expectancy == null ? "muted" : expectancy > 0 ? "bull" : expectancy < 0 ? "bear" : "muted";
  return (
    <section className="border border-hairline bg-card p-3">
      <div className="grid gap-2 sm:grid-cols-4">
        <Metric label="Win%" value={stats.win_pct == null ? "—" : `${stats.win_pct.toFixed(0)}%`} />
        <Metric label="Avg R" value={stats.avg_r == null ? "—" : signed(stats.avg_r, "R")} />
        <Metric label="Expectancy" value={expectancy == null ? "—" : signed(expectancy, "R")} term="expectancy" />
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
        <button
          type="submit"
          className="border border-ink bg-ink px-3 py-1 font-mono text-[10px] uppercase tracking-overline text-white"
        >
          {editingId ? "Save trade" : "Add trade"}
        </button>
        {editingId && (
          <button
            type="button"
            onClick={onCancelEdit}
            className="border border-hairline px-2 py-1 font-mono text-[10px] uppercase tracking-overline text-ink3 hover:border-ink hover:text-ink"
          >
            Cancel
          </button>
        )}
      </div>
      <label className="lg:col-span-8 flex flex-col gap-1 font-mono text-[10px] uppercase tracking-overline text-ink3">
        Notes
        <input
          value={form.notes}
          onChange={(e) => update("notes", e.target.value)}
          className="border border-hairline bg-raised px-2 py-1 font-mono text-[12px] text-ink outline-none"
        />
      </label>
    </form>
  );
}

function TradeLogTable({ loading, error, trades, onSymbolSelect, onEdit, onDelete }) {
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
          <div className="font-mono text-[12px] font-bold uppercase tracking-overline text-ink">
            No trades logged yet
          </div>
          <p className="mt-1 font-sans text-[12px] text-ink3">Add a closed trade above to start expectancy tracking.</p>
        </div>
      ) : (
        <ul className="space-y-1">
          {trades.map((trade) => (
            <TradeRow
              key={trade.trade_id}
              trade={trade}
              onSymbolSelect={onSymbolSelect}
              onEdit={onEdit}
              onDelete={onDelete}
            />
          ))}
        </ul>
      )}
    </section>
  );
}

function TradeRow({ trade, onSymbolSelect, onEdit, onDelete }) {
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
      <span className="col-span-2 font-mono text-ink2">{trade.setup || "—"}</span>
      <span className={"col-span-1 font-mono font-bold tabular-nums " + (positive ? "text-bull" : "text-bear")}>
        {signed(trade.r_result, "R")}
      </span>
      <span className="col-span-3 flex flex-wrap gap-1">
        {(trade.mistake_tags || []).length ? (
          trade.mistake_tags.map((tag) => (
            <span key={tag} className="rounded-chip border border-bear-border bg-bear-bg px-1.5 py-0.5 font-mono text-[9px] text-bear">
              {tag}
            </span>
          ))
        ) : (
          <span className="font-mono text-[10px] text-ink3">—</span>
        )}
      </span>
      <span className={"col-span-1 font-mono uppercase tracking-overline " + (positive ? "text-bull" : "text-bear")}>
        {trade.result}
      </span>
      <span className="col-span-1 flex justify-end gap-1">
        <button
          type="button"
          onClick={() => onEdit(trade)}
          className="border border-hairline px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-overline text-ink3 hover:border-ink hover:text-ink"
        >
          edit
        </button>
        <button
          type="button"
          onClick={() => onDelete(trade.trade_id)}
          className="border border-hairline px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-overline text-bear hover:border-bear"
        >
          del
        </button>
      </span>
    </li>
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
  if (value == null) return "—";
  return `${value > 0 ? "+" : ""}${Number(value).toFixed(2).replace(/\.00$/, "")}${suffix}`;
}
