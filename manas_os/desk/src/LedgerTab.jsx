import React, { useEffect, useState } from "react";
import { fetchTrackRecord, fetchLessons, fetchJournal, addJournalTrade, updateJournalTrade, deleteJournalTrade } from "./api.js";
import { Term } from "./Glossary.jsx";
import { useDensity } from "./DensityContext.jsx";
import { SectionLabel, Panel } from "./components/v5/index.js";
import "./LedgerTab.v5.css";

// ------------------------------------------------------------------
// DEMO FIXTURES — turn this to false to restore the honest live fetch.
// Purpose: exercise every JOURNAL state (closed win/loss, open trade, drawn
// equity curve, populated stats, proven + building-sample cohorts, lessons +
// digest) for visual verification. These payloads mirror the shapes the real
// endpoints return (/api/journal, /api/desk/track-record, /api/desk/lessons);
// flip USE_DEMO_DATA to false to resume the real independent section loads.
// ------------------------------------------------------------------


// ------------------------------------------------------------------
// pure helpers (real payload only -- no synthetic fill anywhere)
// ------------------------------------------------------------------

function round(n, digits = 1) {
  if (n === null || n === undefined) return "—";
  const f = Math.pow(10, digits);
  return Math.round(n * f) / f;
}

// Server-implied trust floor for the "passed" (taken) cohort. The expectancy
// payload's own `unproven` field is authoritative -- this is only the legacy
// n<20 floor that applied before `unproven` existed, kept so a cohort that
// reports `unproven:false` but tiny n still reads as building.
const TRUST_FLOOR_N = 20;

function familyLabel(family) {
  return (family || "unknown").replace(/[/_]/g, " ").toUpperCase();
}

// Plain-language evidence status from the real `trust` + `unproven` fields.
// `unproven` is authoritative; `trust` is additive color language.
function trustStatus(cell) {
  if (!cell || !cell.n) return { label: "no sample", tone: "mute" };
  if (cell.unproven || cell.n < TRUST_FLOOR_N) {
    return { label: "building sample", tone: "amber" };
  }
  const t = cell.trust;
  if (t === "operational") return { label: "operational", tone: "green" };
  if (t === "directional") return { label: "directional", tone: "teal" };
  if (t === "descriptive") return { label: "descriptive", tone: "mute" };
  return { label: "measured", tone: "teal" };
}

// ------------------------------------------------------------------
// Personal journal: stat rail
// ------------------------------------------------------------------

// A single cardless stat tile. Null/undefined value renders an honest "--"
// with a title explaining why -- the whole point on a thin journal.
function StatTile({ label, value, title, children }) {
  const isDash = value === null || value === undefined || value === "—";
  return (
    <div className={"v5-jr-stat" + (isDash ? " v5-jr-stat-empty" : "")}>
      <span className="v5-jr-stat-lbl">{label}</span>
      <span className="v5-jr-stat-val mono-num" title={title || (isDash ? "not enough closed trades yet" : undefined)}>
        {isDash ? "—" : value}
      </span>
      {children}
    </div>
  );
}

// Small win/loss ratio bar. With 0 closed trades this renders null (the parent
// guards on closedCount), so it never fakes a split.
function WinLossBar({ wins, losses }) {
  const total = wins + losses;
  if (total === 0) return null;
  const winPct = (wins / total) * 100;
  return (
    <div className="v5-jr-winloss" title={`${wins} win / ${losses} loss`}>
      <div className="v5-jr-winloss-win" style={{ width: `${winPct}%` }} />
      <div className="v5-jr-winloss-loss" style={{ width: `${100 - winPct}%` }} />
    </div>
  );
}

function StatRail({ stats, closedCount, wins, losses }) {
  return (
    <>
      <div className="v5-jr-stat-rail">
        <StatTile label="Trades" value={stats.count} title={stats.count ? `${stats.count} trade(s) on record` : "no trades yet"} />
        <StatTile
          label={<Term k="hit-rate">Win %</Term>}
          value={stats.win_pct !== null && stats.win_pct !== undefined ? `${round(stats.win_pct, 0)}%` : null}
          title="win rate includes both R-based (tool-logged) and P&L-based (imported) closed trades"
        >
          {closedCount > 0 && <WinLossBar wins={wins} losses={losses} />}
        </StatTile>
        <StatTile
          label={<Term k="avg-r">Avg R</Term>}
          value={round(stats.avg_r, 2)}
          title="average R needs closed trades with a stop -- imported trades carry no stop and are excluded"
        />
        <StatTile
          label={<Term k="stage-expectancy">Expectancy</Term>}
          value={round(stats.expectancy_r, 2)}
          title="expectancy (R per trade) needs closed trades with a stop -- imported trades carry no stop and are excluded"
        />
        {stats.realized_pnl_total !== null && stats.realized_pnl_total !== undefined && (
          <StatTile
            label="Realized P&L"
            value={`${stats.realized_pnl_total >= 0 ? "+" : ""}₹${round(stats.realized_pnl_total, 0)}`}
            title="sum of broker-reported realized P&L across imported trades"
          />
        )}
        {stats.top_mistake && (
          <StatTile
            label="Top mistake"
            value={stats.top_mistake}
            title="most frequent mistake tag across closed trades"
          />
        )}
      </div>
      {stats.r_stats_caption && <p className="v5-jr-caption">{stats.r_stats_caption}</p>}
    </>
  );
}

// ------------------------------------------------------------------
// Personal journal: equity curve (pure inline SVG, honest empty state)
// ------------------------------------------------------------------

// Cumulative-R equity curve. `closedTrades` must be chronological (oldest
// first). Below 2 closed points we cannot draw a line, so we say so plainly
// rather than fake a flat one. No synthetic series ever.
function EquityCurve({ closedTrades }) {
  if (!closedTrades || closedTrades.length < 2) {
    return (
      <div className="v5-jr-equity-empty">
        <span className="v5-jr-equity-empty-icon" aria-hidden="true">◌</span>
        <p className="v5-jr-equity-empty-line">Not enough closed trades yet.</p>
        <p className="v5-jr-equity-empty-sub">
          The equity curve appears from your second closed trade. Right now every trade on
          the journal is still open, so there is no R path to draw.
        </p>
      </div>
    );
  }
  let running = 0;
  const cumulative = closedTrades.map((t) => {
    running += Number(t.r_result) || 0;
    return running;
  });
  const min = Math.min(...cumulative, 0);
  const max = Math.max(...cumulative, 0);
  const span = max - min || 1;
  const W = 100;
  const H = 28;
  const stepX = W / (cumulative.length - 1);
  const pts = cumulative
    .map((v, i) => {
      const x = i * stepX;
      const y = H - ((v - min) / span) * H;
      return `${x.toFixed(2)},${y.toFixed(2)}`;
    })
    .join(" ");
  const last = cumulative[cumulative.length - 1];
  const up = last >= 0;
  const stroke = up ? "var(--v5-green)" : "var(--v5-red)";
  const zeroY = H - ((0 - min) / span) * H;
  return (
    <div className="v5-jr-equity-wrap">
      <svg className="v5-jr-equity-svg" viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" role="img" aria-label={`cumulative R ${up ? "up" : "down"} ${round(last, 1)}R`}>
        <line x1="0" y1={zeroY.toFixed(2)} x2={W} y2={zeroY.toFixed(2)} className="v5-jr-equity-zero" />
        <polyline points={pts} fill="none" stroke={stroke} strokeWidth="1.4" strokeLinejoin="round" strokeLinecap="round" />
      </svg>
      <div className="v5-jr-equity-readout">
        <span className="v5-jr-equity-readout-lbl">cumulative R</span>
        <span className={"v5-jr-equity-readout-val mono-num " + (up ? "v5-jr-pos" : "v5-jr-neg")}>
          {up ? "+" : ""}
          {round(last, 1)}R
        </span>
      </div>
    </div>
  );
}

// ------------------------------------------------------------------
// Personal journal: trade history
// ------------------------------------------------------------------

// Zero-anchored horizontal bar for a single trade's R. Green right of center
// for wins, red left of center for losses, "open" label when r_result is null.
// Never animates (a11y §5: motion never marks R).
function RBar({ r }) {
  if (r === null || r === undefined) {
    return <span className="v5-jr-r-open mono-num">open</span>;
  }
  const capAt = 5;
  const pct = Math.min(Math.abs(r), capAt) / capAt * 50; // half-track max
  const up = r >= 0;
  const style = {
    width: `${pct}%`,
    ...(up ? { left: "50%" } : { right: "50%" }),
  };
  return (
    <div className="v5-jr-r-bar">
      <div className="v5-jr-r-bar-mid" />
      <div className={"v5-jr-r-bar-fill " + (up ? "v5-jr-pos" : "v5-jr-neg")} style={style} />
      <span className={"v5-jr-r-bar-val mono-num " + (up ? "v5-jr-pos" : "v5-jr-neg")}>
        {up ? "+" : ""}
        {round(r, 1)}R
      </span>
    </div>
  );
}

// Broker-import trades carry realized P&L / return% / holding-days instead of
// an R multiple (the tradebook has no initial stop). Same visual language as
// RBar (signed, redundant +/- with color per a11y §5) but reads P&L, not R.
function BrokerPnlChip({ trade }) {
  const pnl = trade.broker_realized_pnl;
  if (pnl === null || pnl === undefined) {
    return <span className="v5-jr-r-open mono-num">closed</span>;
  }
  const up = pnl >= 0;
  const pct = trade.broker_return_pct;
  return (
    <span className={"v5-jr-r-bar-val mono-num " + (up ? "v5-jr-pos" : "v5-jr-neg")}>
      {up ? "+" : ""}₹{round(pnl, 0)}
      {pct !== null && pct !== undefined ? ` (${up ? "+" : ""}${round(pct, 1)}%)` : ""}
    </span>
  );
}

function reasonFor(trade) {
  if (trade.imported) {
    const dir = trade.broker_direction || "long";
    const days = trade.broker_holding_days;
    return days !== null && days !== undefined ? `${dir} · ${days}d held` : dir;
  }
  if (trade.mistake_tags && trade.mistake_tags.length > 0) return trade.mistake_tags.join(", ");
  if (trade.result === "open") return "—";
  return trade.result === "win" ? "sold into strength" : "stopped out";
}

// One editable numeric cell. When `editing` matches this trade+field it renders
// an input; otherwise a plain value that starts an edit on click. R is never
// edited here — the server recomputes it from entry/exit/stop.
function EditableCell({ trade, field, value, editing, editDraft, onStartEdit, onDraftChange, onCommit, onCancel }) {
  const isEditing = editing && editing.tradeId === trade.trade_id && editing.field === field;
  if (isEditing) {
    return (
      <input
        className="v5-jr-edit-input mono-num"
        type="number"
        step="0.01"
        autoFocus
        value={editDraft}
        onChange={(e) => onDraftChange(e.target.value)}
        onBlur={onCommit}
        onKeyDown={(e) => {
          if (e.key === "Enter") onCommit();
          if (e.key === "Escape") onCancel();
        }}
      />
    );
  }
  return (
    <span
      className="v5-jr-editable mono-num"
      role="button"
      tabIndex={0}
      title="click to edit"
      onClick={() => onStartEdit(trade, field)}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onStartEdit(trade, field);
        }
      }}
    >
      {value ?? "—"}
    </span>
  );
}

function DeleteControl({ tradeId, symbol, onDelete }) {
  const [confirming, setConfirming] = useState(false);
  
  if (!confirming) {
    return (
      <button
        type="button"
        className="v5-jr-delete-btn"
        onClick={() => setConfirming(true)}
        title={`Delete ${symbol} trade`}
      >
        🗑
      </button>
    );
  }
  
  return (
    <span className="v5-jr-delete-confirm-group">
      <button
        type="button"
        className="v5-jr-delete-confirm-btn"
        onClick={() => onDelete(tradeId)}
      >
        delete
      </button>
      <button
        type="button"
        className="v5-jr-delete-cancel-btn"
        onClick={() => setConfirming(false)}
      >
        cancel
      </button>
    </span>
  );
}

function TradeHistoryTable({ trades, onDelete, editing, editDraft, onStartEdit, onDraftChange, onCommitEdit, onCancelEdit }) {
  return (
    <div className="v5-jr-table-wrap">
      <table className="v5-jr-table">
        <thead>
          <tr>
            <th>Entry date</th>
            <th>Exit date</th>
            <th>Symbol</th>
            <th>Setup</th>
            <th>Qty</th>
            <th>Entry</th>
            <th>Exit</th>
            <th>Stop</th>
            <th>R / P&amp;L</th>
            <th>Reason</th>
            <th style={{ width: "80px", textAlign: "center" }}>Action</th>
          </tr>
        </thead>
        <tbody>
          {trades.map((t) => (
            <tr key={t.trade_id}>
              <td className="mono-num">{t.trade_date}</td>
              <td className="mono-num">{t.exit_date || "—"}</td>
              <td>
                <span className="v5-jr-sym">{t.symbol}</span>
                {t.imported && (
                  <span
                    className="v5-jr-status v5-jr-status-teal"
                    style={{ marginLeft: "6px" }}
                    title="Imported from a Zerodha tradebook -- no stop, so no R"
                  >
                    imported
                  </span>
                )}
              </td>
              <td>{(t.setup || "—").replace(/[/_]/g, " ")}</td>
              <td className="mono-num">{t.qty ?? "—"}</td>
              <td>
                <EditableCell
                  trade={t}
                  field="entry"
                  value={t.entry ?? ""}
                  editing={editing}
                  editDraft={editDraft}
                  onStartEdit={onStartEdit}
                  onDraftChange={onDraftChange}
                  onCommit={onCommitEdit}
                  onCancel={onCancelEdit}
                />
              </td>
              <td>
                <EditableCell
                  trade={t}
                  field="exit"
                  value={t.exit ?? ""}
                  editing={editing}
                  editDraft={editDraft}
                  onStartEdit={onStartEdit}
                  onDraftChange={onDraftChange}
                  onCommit={onCommitEdit}
                  onCancel={onCancelEdit}
                />
              </td>
              <td>
                <EditableCell
                  trade={t}
                  field="stop"
                  value={t.stop ?? ""}
                  editing={editing}
                  editDraft={editDraft}
                  onStartEdit={onStartEdit}
                  onDraftChange={onDraftChange}
                  onCommit={onCommitEdit}
                  onCancel={onCancelEdit}
                />
              </td>
              <td>
                {t.r_result !== null && t.r_result !== undefined ? (
                  <RBar r={t.r_result} />
                ) : t.broker_realized_pnl !== null && t.broker_realized_pnl !== undefined ? (
                  <BrokerPnlChip trade={t} />
                ) : (
                  <RBar r={null} />
                )}
              </td>
              <td>{reasonFor(t)}</td>
              <td style={{ textAlign: "center" }}>
                <DeleteControl tradeId={t.trade_id} symbol={t.symbol} onDelete={onDelete} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ------------------------------------------------------------------
// Imported holdings (broker_open_lots) — compact, read-only. These are raw
// Zerodha inventory rows still open at import time: no stop, no coach
// thesis, so they don't fit the Positions tab's stop-based coach engine.
// Only positive-qty lots are shown -- negative qty is a pre-window FIFO
// artifact (a sell matched against a buy the tradebook window never saw).
// ------------------------------------------------------------------
function ImportedHoldingsTable({ holdings }) {
  if (!holdings || holdings.length === 0) return null;
  return (
    <>
      <SectionLabel count={holdings.length}>Imported holdings</SectionLabel>
      <div className="v5-jr-table-wrap">
        <table className="v5-jr-table">
          <thead>
            <tr>
              <th>Symbol</th>
              <th>Qty</th>
              <th>Avg cost</th>
              <th>First buy</th>
              <th>Last close</th>
              <th>Unrealized</th>
            </tr>
          </thead>
          <tbody>
            {holdings.map((h) => {
              const up = h.unrealized_pct !== null && h.unrealized_pct !== undefined ? h.unrealized_pct >= 0 : null;
              return (
                <tr key={h.symbol}>
                  <td>
                    <span className="v5-jr-sym">{h.symbol}</span>
                    <span
                      className="v5-jr-status v5-jr-status-teal"
                      style={{ marginLeft: "6px" }}
                      title="Still open in the Zerodha tradebook -- no stop, so not coached on the Positions tab"
                    >
                      imported holding
                    </span>
                  </td>
                  <td className="mono-num">{round(h.qty, 0)}</td>
                  <td className="mono-num">{round(h.avg_cost, 2)}</td>
                  <td className="mono-num">{h.first_buy_date}</td>
                  <td className="mono-num">
                    {h.last_close !== null && h.last_close !== undefined ? round(h.last_close, 2) : "—"}
                  </td>
                  <td className={"mono-num" + (up === null ? "" : up ? " v5-jr-pos" : " v5-jr-neg")}>
                    {h.unrealized_pct !== null && h.unrealized_pct !== undefined
                      ? `${up ? "+" : ""}${round(h.unrealized_pct, 1)}% (${up ? "+" : ""}₹${round(h.unrealized_pnl, 0)})`
                      : "no recent price"}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        <p className="v5-jr-caption">
          Open positions still held in the imported Zerodha tradebook — no stop was recorded, so these are not
          coached on the Positions tab. Last close from the daily price table; negative-qty lots (pre-window
          FIFO artifacts) are excluded.
        </p>
      </div>
    </>
  );
}

// The whole personal-journal section. `journal.trades` is newest-first; the
// equity curve reads chronologically so we reverse a copy for that one path.
function JournalSection({ journal, onDelete, onAdd, editing, editDraft, onStartEdit, onDraftChange, onCommitEdit, onCancelEdit }) {
  const stats = (journal && journal.stats) || {};
  const trades = (journal && journal.trades) || [];
  const chronological = [...trades].reverse();
  // R-only cohort: the equity curve is a cumulative-R line, so it can only
  // plot trades that have an R (imported trades carry no stop, no R).
  const closedChronological = chronological.filter(
    (t) => t.r_result !== null && t.r_result !== undefined
  );
  // Inclusive win/loss cohort (matches the backend's inclusive win_pct):
  // R-based outcome when present, else the imported trade's own broker
  // realized-P&L sign.
  const outcomeChronological = chronological.filter(
    (t) =>
      (t.r_result !== null && t.r_result !== undefined) ||
      (t.broker_realized_pnl !== null && t.broker_realized_pnl !== undefined)
  );
  const wins = outcomeChronological.filter((t) =>
    t.r_result !== null && t.r_result !== undefined ? t.r_result > 0 : t.broker_realized_pnl > 0
  ).length;
  const losses = outcomeChronological.length - wins;

  return (
    <>
      <div className="v5-jr-journal-head">
        <SectionLabel count={`${stats.count ?? trades.length} on record`}>Trade journal — your edge</SectionLabel>
        <button type="button" className="v5-jr-add-btn" onClick={onAdd}>Add trade</button>
      </div>

      <StatRail stats={stats} closedCount={outcomeChronological.length} wins={wins} losses={losses} />

      <div className="v5-jr-equity-block">
        <div className="v5-jr-subhead">Equity curve (cumulative R)</div>
        <EquityCurve closedTrades={closedChronological} />
      </div>

      <div className="v5-jr-history-block">
        <div className="v5-jr-subhead">Trade history</div>
        <TradeHistoryTable
          trades={trades}
          onDelete={onDelete}
          editing={editing}
          editDraft={editDraft}
          onStartEdit={onStartEdit}
          onDraftChange={onDraftChange}
          onCommitEdit={onCommitEdit}
          onCancelEdit={onCancelEdit}
        />
      </div>
    </>
  );
}

// #25: manual add-trade modal. R is computed by the server from entry/exit/stop,
// so the form only collects raw user inputs (money-math stays server-side).
function AddTradeModal({ onCancel, onSubmit, busy, error }) {
  const today = new Date().toISOString().slice(0, 10);
  const [form, setForm] = useState({
    symbol: "",
    trade_date: today,
    setup: "",
    entry: "",
    exit: "",
    stop: "",
    notes: "",
  });
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));
  const submit = (e) => {
    e.preventDefault();
    const payload = {
      symbol: form.symbol.trim().toUpperCase(),
      trade_date: form.trade_date,
      setup: form.setup.trim() || null,
      entry: form.entry === "" ? null : Number(form.entry),
      exit: form.exit === "" ? null : Number(form.exit),
      stop: form.stop === "" ? null : Number(form.stop),
      notes: form.notes.trim() || null,
    };
    if (!payload.symbol || !payload.trade_date) return;
    onSubmit(payload);
  };
  return (
    <div className="v5-jr-modal-backdrop" onMouseDown={onCancel}>
      <form className="v5-jr-modal" onMouseDown={(e) => e.stopPropagation()} onSubmit={submit}>
        <div className="v5-jr-modal-head">
          <span>Add journal trade</span>
          <button type="button" className="v5-jr-modal-close" onClick={onCancel} aria-label="close">×</button>
        </div>
        <div className="v5-jr-modal-grid">
          <label>
            Symbol<span className="v5-jr-req">*</span>
            <input value={form.symbol} onChange={set("symbol")} placeholder="INFY" autoFocus />
          </label>
          <label>
            Date<span className="v5-jr-req">*</span>
            <input type="date" value={form.trade_date} onChange={set("trade_date")} />
          </label>
          <label>
            Setup
            <input value={form.setup} onChange={set("setup")} placeholder="breakout" />
          </label>
          <label>
            Entry
            <input type="number" step="0.01" value={form.entry} onChange={set("entry")} placeholder="0.00" />
          </label>
          <label>
            Exit
            <input type="number" step="0.01" value={form.exit} onChange={set("exit")} placeholder="blank = open" />
          </label>
          <label>
            Stop
            <input type="number" step="0.01" value={form.stop} onChange={set("stop")} placeholder="0.00" />
          </label>
          <label className="v5-jr-modal-notes">
            Notes
            <textarea value={form.notes} onChange={set("notes")} rows={3} />
          </label>
        </div>
        {error && <div className="v5-jr-modal-error">{error}</div>}
        <div className="v5-jr-modal-actions">
          <button type="button" className="v5-pos-btn" onClick={onCancel} disabled={busy}>Cancel</button>
          <button type="submit" className="v5-pos-btn v5-btn-primary" disabled={busy}>
            {busy ? "Saving…" : "Save trade"}
          </button>
        </div>
      </form>
    </div>
  );
}


// ------------------------------------------------------------------
// SYSTEM EDGE (advanced) -- secondary, progressive disclosure
// ------------------------------------------------------------------

// One cohort cell for the expectancy table. The `unproven` field is
// authoritative; n<20 is the legacy floor. Thin samples read as building,
// never as green/proven.
function CohortCell({ cell, unit }) {
  if (!cell || !cell.n) {
    return <span className="v5-jr-cohort v5-jr-cohort-empty mono-num" title="no sample for this cohort">—</span>;
  }
  const st = trustStatus(cell);
  if (cell.unproven || cell.n < TRUST_FLOOR_N) {
    return (
      <span className="v5-jr-cohort v5-jr-cohort-thin">
        <span className={"v5-jr-status v5-jr-status-" + st.tone}>{st.label}</span>
        <span className="v5-jr-cohort-n mono-num">n={cell.n}</span>
      </span>
    );
  }
  const pct = round((cell.hit_rate || 0) * 100, 0);
  const avg = round(cell.mean_r ?? cell.median_r, 2);
  const sign = avg >= 0 ? "+" : "";
  if (unit === "pct") {
    // Refused: no stop was set, so this is a raw %-return baseline, not R.
    return (
      <span className="v5-jr-cohort">
        <span className={"v5-jr-status v5-jr-status-" + st.tone}>{st.label}</span>
        <span className="v5-jr-cohort-n mono-num">n={cell.n}</span>
        <span className="v5-jr-cohort-metric mono-num">
          win {pct}% · avg {sign}
          {avg}% <span className="v5-jr-cohort-note">(no stop set)</span>
        </span>
      </span>
    );
  }
  return (
    <span className="v5-jr-cohort">
      <span className={"v5-jr-status v5-jr-status-" + st.tone}>{st.label}</span>
      <span className="v5-jr-cohort-n mono-num">n={cell.n}</span>
      <span className="v5-jr-cohort-metric mono-num">
        hit {pct}% · avg {sign}
        {avg}R
      </span>
    </span>
  );
}

function ExpectancyTable({ rows }) {
  if (!rows || rows.length === 0) {
    return (
      <div className="v5-jr-empty">
        <span className="v5-jr-empty-icon" aria-hidden="true">◌</span>
        <p className="v5-jr-empty-line">No system expectancy cells yet.</p>
        <p className="v5-jr-empty-sub">
          Runs the replay across history and persists per-family passed vs refused cohorts —
          nothing has been persisted yet.
        </p>
      </div>
    );
  }
  return (
    <div className="v5-jr-table-wrap">
      <table className="v5-jr-table v5-jr-table-cohort">
        <thead>
          <tr>
            <th>Family</th>
            <th>Regime</th>
            <th>Passed (taken)</th>
            <th>Refused (near-miss)</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={`${r.family}-${r.regime}`}>
              <td>{familyLabel(r.family)}</td>
              <td>{r.regime}</td>
              <td><CohortCell cell={r.passed} unit="r" /></td>
              <td><CohortCell cell={r.refused} unit="pct" /></td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="v5-jr-caption">
        System loop: every persisted candidate's forward return at T+10, whether taken or not —
        proves or kills the setup family over time, independent of any one trade.
      </p>
    </div>
  );
}

function TrackRecordTable({ records }) {
  if (!records || records.length === 0) {
    return (
      <div className="v5-jr-empty">
        <span className="v5-jr-empty-icon" aria-hidden="true">◌</span>
        <p className="v5-jr-empty-line">No closed agent outcomes yet.</p>
        <p className="v5-jr-empty-sub">
          Track records and lessons fill in as trades resolve — nothing to show yet, that's the
          current reality, not a broken panel.
        </p>
      </div>
    );
  }
  return (
    <div className="v5-jr-table-wrap">
      <table className="v5-jr-table">
        <thead>
          <tr>
            <th>Agent</th>
            <th>Family</th>
            <th>Hit</th>
            <th>Avg R</th>
            <th>n</th>
          </tr>
        </thead>
        <tbody>
          {records.map((r) => (
            <tr key={`${r.agent}-${r.family}`} className={r.thin ? "v5-jr-thin-row" : ""}>
              <td><span className="v5-jr-sym" title={r.agent}>{r.agent}</span></td>
              <td>{familyLabel(r.family)}</td>
              <td className="mono-num">
                {r.n ? `${round((r.hit_rate || 0) * r.n, 0)}/${r.n}` : "—"}
                {r.hit_rate !== null && r.hit_rate !== undefined ? ` (${round(r.hit_rate * 100, 0)}%)` : ""}
              </td>
              <td className="mono-num">{round(r.avg_r, 1)}</td>
              <td className="mono-num">
                {r.n}
                {r.thin && <span className="v5-jr-thin-note"> building sample</span>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ScreenerCalibrationTable({ rows }) {
  if (!rows || rows.length === 0) {
    return (
      <div className="v5-jr-empty">
        <span className="v5-jr-empty-icon" aria-hidden="true">◌</span>
        <p className="v5-jr-empty-line">No screener calibration yet.</p>
        <p className="v5-jr-empty-sub">
          Runs nightly against screener hits — nothing has been persisted yet.
        </p>
      </div>
    );
  }
  return (
    <div className="v5-jr-table-wrap">
      <table className="v5-jr-table">
        <thead>
          <tr>
            <th>Screener</th>
            <th>n</th>
            <th>Avg excess (T+10)</th>
            <th>Median excess</th>
            <th>Win %</th>
            <th>Baseline win %</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.screener} className={r.unproven ? "v5-jr-thin-row" : ""}>
              <td>{r.screener}</td>
              <td className="mono-num">
                {r.n}
                {r.unproven && <span className="v5-jr-thin-note"> n&lt;30 — building sample</span>}
              </td>
              <td className={"mono-num " + (r.avg_excess_pct >= 0 ? "v5-jr-pos" : "v5-jr-neg")}>
                {r.avg_excess_pct >= 0 ? "+" : ""}
                {round(r.avg_excess_pct, 2)}%
              </td>
              <td className={"mono-num " + (r.median_excess_pct >= 0 ? "v5-jr-pos" : "v5-jr-neg")}>
                {r.median_excess_pct >= 0 ? "+" : ""}
                {round(r.median_excess_pct, 2)}%
              </td>
              <td className="mono-num">{round(r.win_rate * 100, 0)}%</td>
              <td className="mono-num">{round(r.baseline_win_rate * 100, 0)}%</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="v5-jr-caption">
        Screeners ranked by whether their picks actually went up afterwards.
      </p>
    </div>
  );
}

// ------------------------------------------------------------------
// Lessons diary + digest (always visible, outside the disclosure)
// ------------------------------------------------------------------

const TAG_LABELS = {
  "clean-hit": "clean hit",
  "clean-miss": "clean miss",
  "right-process-loss": "right process, loss",
  "wrong-process-win": "wrong process, win",
};

function TagPill({ tag }) {
  if (!tag) return <span className="v5-jr-tag v5-jr-tag-none">untagged</span>;
  return <span className={"v5-jr-tag v5-jr-tag-" + tag}>{TAG_LABELS[tag] || tag}</span>;
}

function LessonsDiary({ lessons, digest }) {
  const hasLessons = lessons && lessons.length > 0;
  const hasDigest = digest && digest.trim().length > 0;
  return (
    <>
      <SectionLabel>Lessons diary</SectionLabel>
      <div className="v5-jr-lessons-grid">
        <Panel title="Lessons diary" cite="from ~/.manas/lessons">
          {hasLessons ? (
            <div className="v5-jr-lessons-list">
              {lessons.map((l) => (
                <div key={l.filename} className="v5-jr-lesson-row">
                  <span className="v5-jr-lesson-fn mono-num">{l.filename}</span>
                  <TagPill tag={l.tag} />
                  <p className="v5-jr-lesson-preview">{l.first_line || "—"}</p>
                </div>
              ))}
            </div>
          ) : (
            <div className="v5-jr-empty">
              <span className="v5-jr-empty-icon" aria-hidden="true">◌</span>
              <p className="v5-jr-empty-line">No lessons written yet.</p>
              <p className="v5-jr-empty-sub">
                Lessons accumulate once trades close and the desk reflects on them.
              </p>
            </div>
          )}
        </Panel>

        <Panel title="What the desk carries forward" cite="digest">
          {hasDigest ? (
            <pre className="v5-jr-digest">{digest}</pre>
          ) : (
            <div className="v5-jr-empty">
              <span className="v5-jr-empty-icon" aria-hidden="true">◌</span>
              <p className="v5-jr-empty-line">No digest in force yet.</p>
              <p className="v5-jr-empty-sub">
                Nothing has been distilled to carry forward.
              </p>
            </div>
          )}
        </Panel>
      </div>
    </>
  );
}

// ------------------------------------------------------------------
// Root component
// ------------------------------------------------------------------

// One row per REVIEW section: journal, lessons, track record each load and
// fail independently (P0 fix -- a Promise.all previously meant one 500
// (e.g. /api/journal) tore down the entire learning surface, hiding working
// lessons + expectancy data behind one error card). Each section owns its
// own {data, loading, error} and retries on its own.
function SectionStatus({ loading, error, onRetry, loadingLabel, errorLabel }) {
  if (loading) {
    return <div className="v5-jr-loading">{loadingLabel || "Loading…"}</div>;
  }
  if (error) {
    return (
      <div className="v5-jr-error">
        <span className="v5-jr-empty-icon" aria-hidden="true">⚠</span>
        <p className="v5-jr-empty-line">{errorLabel || "Could not load this section."}</p>
        <p className="v5-jr-empty-sub">{error}</p>
        {onRetry && (
          <button type="button" className="v5-jr-add-btn" onClick={onRetry} style={{ marginTop: "8px" }}>
            Retry
          </button>
        )}
      </div>
    );
  }
  return null;
}

export default function LedgerTab() {
  const [trackRecord, setTrackRecord] = useState(null);
  const [trackRecordLoading, setTrackRecordLoading] = useState(true);
  const [trackRecordError, setTrackRecordError] = useState(null);

  const [lessons, setLessons] = useState(null);
  const [lessonsLoading, setLessonsLoading] = useState(true);
  const [lessonsError, setLessonsError] = useState(null);

  const [journal, setJournal] = useState(null);
  const [journalLoading, setJournalLoading] = useState(true);
  const [journalError, setJournalError] = useState(null);

  const { isExpert } = useDensity();
  const [systemEdgeOpen, setSystemEdgeOpen] = useState(isExpert);
  // #25: manual add-trade + inline edit state
  const [adding, setAdding] = useState(false);
  const [addBusy, setAddBusy] = useState(false);
  const [addError, setAddError] = useState(null);
  const [editing, setEditing] = useState(null); // { tradeId, field }
  const [editDraft, setEditDraft] = useState("");

  // Expert mode auto-expands SYSTEM EDGE (advanced); beginner keeps it
  // collapsed by default but a manual toggle still overrides either way until
  // the next density change.
  useEffect(() => {
    setSystemEdgeOpen(isExpert);
  }, [isExpert]);

  const loadTrackRecord = React.useCallback(() => {
    setTrackRecordLoading(true);
    setTrackRecordError(null);
    return fetchTrackRecord()
      .then((tr) => setTrackRecord(tr))
      .catch((err) => setTrackRecordError(String(err.message || err)))
      .finally(() => setTrackRecordLoading(false));
  }, []);

  const loadLessons = React.useCallback(() => {
    setLessonsLoading(true);
    setLessonsError(null);
    return fetchLessons()
      .then((ls) => setLessons(ls))
      .catch((err) => setLessonsError(String(err.message || err)))
      .finally(() => setLessonsLoading(false));
  }, []);

  const reloadJournal = React.useCallback(() => {
    setJournalLoading(true);
    setJournalError(null);
    return fetchJournal()
      .then((jr) => setJournal(jr))
      .catch((err) => setJournalError(String(err.message || err)))
      .finally(() => setJournalLoading(false));
  }, []);

  // Each section is fetched and settled independently (no Promise.all) so
  // one endpoint's failure -- e.g. /api/journal 500ing on a null-avg_cost
  // imported lot -- degrades only that section instead of hiding lessons
  // and track record, which have nothing to do with the journal failure.
  useEffect(() => {
    loadTrackRecord();
    loadLessons();
    reloadJournal();
  }, [loadTrackRecord, loadLessons, reloadJournal]);

  const handleDelete = (tradeId) => {
    deleteJournalTrade(tradeId)
      .then(() => reloadJournal())
      .catch((err) => alert("Delete failed: " + (err.message || err)));
  };

  const submitAdd = (form) => {
    setAddBusy(true);
    setAddError(null);
    addJournalTrade(form)
      .then(() => {
        setAdding(false);
        return reloadJournal();
      })
      .catch((err) => setAddError(String(err.message || err)))
      .finally(() => setAddBusy(false));
  };

  const startEdit = (trade, field) => {
    setEditing({ tradeId: trade.trade_id, field });
    setEditDraft(trade[field] === null || trade[field] === undefined ? "" : String(trade[field]));
  };

  const cancelEdit = () => {
    setEditing(null);
    setEditDraft("");
  };

  const commitEdit = (trade) => {
    if (!editing) return;
    const field = editing.field;
    const raw = editDraft.trim();
    const value = raw === "" ? null : Number(raw);
    const payload = {
      trade_date: trade.trade_date,
      symbol: trade.symbol,
      setup: trade.setup || null,
      entry: field === "entry" ? value : (trade.entry ?? null),
      exit: field === "exit" ? value : (trade.exit ?? null),
      stop: field === "stop" ? value : (trade.stop ?? null),
      notes: trade.notes || null,
    };
    updateJournalTrade(trade.trade_id, payload)
      .then(() => reloadJournal())
      .then(() => cancelEdit())
      .catch((err) => alert("Update failed: " + (err.message || err)));
  };

  const records = (trackRecord && trackRecord.records) || [];
  const expectancyRows = (trackRecord && trackRecord.expectancy) || [];
  const screenerCalibrationRows = (trackRecord && trackRecord.screener_calibration) || [];
  const lessonItems = (lessons && lessons.lessons) || [];
  const digest = lessons && lessons.digest;
  const hasJournal = journal && journal.available && journal.trades && journal.trades.length > 0;
  const importedHoldings = (journal && journal.imported_holdings) || [];

  return (
    <div className="v5-journal">
      {journalLoading || journalError ? (
        <SectionStatus
          loading={journalLoading}
          error={journalError}
          onRetry={reloadJournal}
          loadingLabel="Loading journal…"
          errorLabel="Could not load the journal."
        />
      ) : hasJournal ? (
        <>
          <JournalSection
            journal={journal}
            onDelete={handleDelete}
            onAdd={() => setAdding(true)}
            editing={editing}
            editDraft={editDraft}
            onStartEdit={startEdit}
            onDraftChange={setEditDraft}
            onCommitEdit={() => commitEdit(editing ? journal.trades.find((t) => t.trade_id === editing.tradeId) : null)}
            onCancelEdit={cancelEdit}
          />
          <ImportedHoldingsTable holdings={importedHoldings} />
        </>
      ) : (

        <>
          <div className="v5-jr-journal-head">
            <SectionLabel>Trade journal — your edge</SectionLabel>
            <button type="button" className="v5-jr-add-btn" onClick={() => setAdding(true)}>Add trade</button>
          </div>
          <div className="v5-jr-empty">
            <span className="v5-jr-empty-icon" aria-hidden="true">◌</span>
            <p className="v5-jr-empty-line">No journal trades yet.</p>
            <p className="v5-jr-empty-sub">
              The journal starts the first time a setup is captured or a trade is logged. Add one manually to begin.
            </p>
          </div>
          <ImportedHoldingsTable holdings={importedHoldings} />
        </>
      )}

      {adding && (
        <AddTradeModal
          onCancel={() => setAdding(false)}
          onSubmit={submitAdd}
          busy={addBusy}
          error={addError}
        />
      )}

      <SectionLabel count="advanced">
        <button
          type="button"
          className="v5-jr-disclosure"
          aria-expanded={systemEdgeOpen}
          onClick={() => setSystemEdgeOpen((o) => !o)}
        >
          <span className="v5-jr-disclosure-mark" aria-hidden="true">{systemEdgeOpen ? "▾" : "▸"}</span>
          SYSTEM EDGE (advanced)
        </button>
      </SectionLabel>

      {systemEdgeOpen && (
        <div className="v5-jr-disclosure-body">
          {trackRecordLoading || trackRecordError ? (
            <SectionStatus
              loading={trackRecordLoading}
              error={trackRecordError}
              onRetry={loadTrackRecord}
              loadingLabel="Loading system edge…"
              errorLabel="Could not load agent track records / system expectancy."
            />
          ) : (
            <>
              <Panel title="System expectancy (setup families)" cite="TradeTM teaches this">
                <ExpectancyTable rows={expectancyRows} />
              </Panel>

              <Panel title="Agent track records" cite="Manas measured">
                <TrackRecordTable records={records} />
              </Panel>

              <Panel title="Which screeners predict" cite="T+10 forward return">
                <ScreenerCalibrationTable rows={screenerCalibrationRows} />
              </Panel>
            </>
          )}
        </div>
      )}

      {lessonsLoading || lessonsError ? (
        <SectionStatus
          loading={lessonsLoading}
          error={lessonsError}
          onRetry={loadLessons}
          loadingLabel="Loading lessons…"
          errorLabel="Could not load lessons."
        />
      ) : (
        <LessonsDiary lessons={lessonItems} digest={digest} />
      )}
    </div>
  );
}
