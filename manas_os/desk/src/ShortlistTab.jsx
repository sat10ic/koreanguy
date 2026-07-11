import React, { useCallback, useEffect, useState } from "react";
import { fetchWatchlist, addWatchlistSymbol, removeWatchlistSymbol, pushSymbolToDebate } from "./api.js";
import ChartDrawer from "./ChartDrawer.jsx";
import { useDensity } from "./DensityContext.jsx";

const STATUS_COLOR = {
  ADDED: "#1f8cff",
  HOLD: "#7c8495",
  PROMOTE: "#00c878",
  DEMOTE: "#ffb020",
  DROP: "#ff4a5f",
};

const STATUS_LABEL = {
  ADDED: "added",
  HOLD: "held",
  PROMOTE: "PROMOTE",
  DEMOTE: "demote",
  DROP: "dropped",
};

const GROUPS = [
  { key: "PROMOTED", title: "PROMOTED ↑", match: (row) => row.status === "PROMOTE" },
  { key: "NEW", title: "NEW", match: (row) => row.status === "ADDED" },
  { key: "HOLDING", title: "HOLDING", match: (row) => row.status === "HOLD" || row.status === "DEMOTE" },
  { key: "DROPPED", title: "DEMOTED ↓ / DROPPED ✕", match: (row) => row.status === "DROP" },
];

function convictionArrow(status) {
  if (status === "PROMOTE") return "▲";
  if (status === "DEMOTE" || status === "DROP") return "▼";
  return "–";
}

function TimelineStrip({ events, latestDate }) {
  if (!events || events.length === 0) return null;
  const dates = events.map((e) => e.date).sort();
  const first = dates[0];
  const last = dates[dates.length - 1];
  const span = Math.max(1, daysBetween(first, last));
  return (
    <div className="shortlist-timeline" aria-hidden="true">
      <div className="shortlist-timeline-track" />
      {events.map((ev, idx) => {
        const offset = span === 0 ? 0 : (daysBetween(first, ev.date) / span) * 100;
        const isLatest = ev.date === latestDate;
        return (
          <span
            key={`${ev.date}-${idx}`}
            className={"shortlist-timeline-dot" + (isLatest ? " shortlist-timeline-dot-pulse" : "")}
            style={{ left: `${offset}%`, background: STATUS_COLOR[ev.action] || "#7c8495" }}
            title={`${ev.date} ${STATUS_LABEL[ev.action] || ev.action}: ${ev.reason || ""}`}
          />
        );
      })}
    </div>
  );
}

function daysBetween(a, b) {
  const da = new Date(a + "T00:00:00");
  const db = new Date(b + "T00:00:00");
  return Math.round((db - da) / 86400000);
}

function ShortlistRow({ row, onDebate, onChart, onRemove, onTradePlan, isExpert }) {
  const events = row.events || [];
  const latest = events[events.length - 1];
  const latestDate = latest ? latest.date : row.scan_date;
  return (
    <div className={"shortlist-row shortlist-row-" + row.status?.toLowerCase()}>
      <div className="shortlist-row-top">
        <span className="shortlist-symbol">{row.symbol}</span>
        <span className="shortlist-onlist">on list {row.days_on_list ?? 0}d</span>
        {isExpert && row.tier && <span className="shortlist-tier-chip">{row.tier}</span>}
        <span className="shortlist-conviction">
          conviction {row.conviction ?? "–"} <span className="shortlist-conviction-arrow">{convictionArrow(row.status)}</span>
        </span>
        {isExpert && typeof row.miss_streak === "number" && row.miss_streak > 0 && (
          <span className="shortlist-miss-streak">miss {row.miss_streak}/2</span>
        )}
        <span className={"shortlist-verdict-chip verdict-" + (row.chair_verdict || "none").toLowerCase()}>
          {row.chair_verdict ? `Council: ${row.chair_verdict}` : "not debated"}
        </span>
        <span className="shortlist-row-actions">
          <button type="button" onClick={() => onDebate(row.symbol)}>&rarr; debate</button>
          {onTradePlan && (
            <button type="button" onClick={() => onTradePlan(row.symbol)}>open trade plan</button>
          )}
          <button type="button" onClick={() => onChart(row.symbol)}>chart</button>
          <button type="button" className="shortlist-remove-btn" onClick={() => onRemove(row.symbol)}>remove</button>
        </span>
      </div>
      <TimelineStrip events={events} latestDate={latestDate} />
      <div className="shortlist-reason-line">
        {latest ? (
          <>
            <span className="mono shortlist-reason-date">{latest.date}</span>{" "}
            <span className={"shortlist-reason-action action-" + latest.action.toLowerCase()}>{STATUS_LABEL[latest.action] || latest.action}:</span>{" "}
            "{latest.reason || "no reason recorded"}"
          </>
        ) : (
          <span className="shortlist-reason-empty">no history yet</span>
        )}
      </div>
      {isExpert && events.length > 1 && (
        <ul className="shortlist-event-log">
          {events.slice(0, -1).reverse().map((ev, idx) => (
            <li key={idx}>
              <span className="mono">{ev.date}</span> <span className={"action-" + ev.action.toLowerCase()}>{STATUS_LABEL[ev.action] || ev.action}:</span> "{ev.reason || ""}"
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function curatorDeltaLine(delta) {
  if (!delta) return "no curator activity recorded yet.";
  const parts = [];
  if (delta.promoted?.length) parts.push(`promoted ${delta.promoted.length}`);
  if (delta.added?.length) parts.push(`added ${delta.added.length}`);
  if (delta.demoted?.length) parts.push(`demoted ${delta.demoted.length}`);
  if (delta.dropped?.length) parts.push(`dropped ${delta.dropped.length}`);
  if (parts.length === 0) return "no changes since last night.";
  return `Curator ${parts.join(" · ")} since last night.`;
}

export default function ShortlistTab({ date, onOpenTradePlan }) {
  const { isExpert } = useDensity();
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [chartSymbol, setChartSymbol] = useState(null);
  const [toast, setToast] = useState(null);
  const [addSymbol, setAddSymbol] = useState("");
  const [addReason, setAddReason] = useState("");
  const [reloadTick, setReloadTick] = useState(0);

  const reload = useCallback(() => setReloadTick((t) => t + 1), []);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetchWatchlist(date)
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
  }, [date, reloadTick]);

  const handleDebate = useCallback((symbol) => {
    setToast({ kind: "ok", text: `Pushing ${symbol} to debate...` });
    pushSymbolToDebate(symbol, date)
      .then((body) => setToast({ kind: "ok", text: `${symbol} pushed to debate (${body.status || "ok"})` }))
      .catch((err) => setToast({ kind: "err", text: `Debate push failed for ${symbol}: ${String(err.message || err)}` }));
  }, [date]);

  const handleRemove = useCallback((symbol) => {
    const reason = window.prompt(`Reason for removing ${symbol} from the shortlist?`, "");
    if (reason === null) return;
    setToast({ kind: "ok", text: `Removing ${symbol}...` });
    removeWatchlistSymbol(symbol, reason, date)
      .then(() => {
        setToast({ kind: "ok", text: `${symbol} removed` });
        reload();
      })
      .catch((err) => setToast({ kind: "err", text: `Remove failed for ${symbol}: ${String(err.message || err)}` }));
  }, [date, reload]);

  const handleAdd = useCallback((e) => {
    e.preventDefault();
    const symbol = addSymbol.trim().toUpperCase();
    if (!symbol) return;
    setToast({ kind: "ok", text: `Adding ${symbol}...` });
    addWatchlistSymbol(symbol, addReason.trim())
      .then(() => {
        setToast({ kind: "ok", text: `${symbol} added to shortlist` });
        setAddSymbol("");
        setAddReason("");
        reload();
      })
      .catch((err) => setToast({ kind: "err", text: `Add failed for ${symbol}: ${String(err.message || err)}` }));
  }, [addSymbol, addReason, reload]);

  if (loading && !data) {
    return <div className="empty-state"><p className="empty-state-line">Loading shortlist...</p></div>;
  }
  if (error) {
    return <div className="empty-state"><p className="empty-state-line">Shortlist failed to load</p><p className="empty-state-sub">{error}</p></div>;
  }
  if (!data || !data.available || (data.rows || []).length === 0) {
    return (
      <div className="shortlist-tab">
        <div className="empty-state">
          <div className="empty-state-icon">○</div>
          <p className="empty-state-line">No shortlist yet for {date}</p>
          <p className="empty-state-sub">The Curator hasn't debated any names for this date, or none survived hard gates.</p>
        </div>
        <AddBox symbol={addSymbol} setSymbol={setAddSymbol} reason={addReason} setReason={setAddReason} onSubmit={handleAdd} />
      </div>
    );
  }

  const rows = data.rows || [];
  const groups = GROUPS.map((g) => ({ ...g, rows: rows.filter(g.match) })).filter((g) => g.rows.length > 0);

  return (
    <div className="shortlist-tab">
      <div className="panel shortlist-delta-strip">
        <span>{curatorDeltaLine(data.curator_delta)}</span>
      </div>
      {toast && <p className={`scanner-toast ${toast.kind}`}>{toast.text}</p>}
      {groups.map((g) => (
        <section key={g.key} className="panel shortlist-group">
          <h3 className="panel-title small-caps">{g.title} ({g.rows.length})</h3>
          <div className="shortlist-group-rows">
            {g.rows.map((row) => (
              <ShortlistRow
                key={row.symbol}
                row={row}
                isExpert={isExpert}
                onDebate={handleDebate}
                onChart={setChartSymbol}
                onRemove={handleRemove}
                onTradePlan={onOpenTradePlan}
              />
            ))}
          </div>
        </section>
      ))}
      <AddBox symbol={addSymbol} setSymbol={setAddSymbol} reason={addReason} setReason={setAddReason} onSubmit={handleAdd} />
      <ChartDrawer symbol={chartSymbol} date={date} onClose={() => setChartSymbol(null)} />
    </div>
  );
}

function AddBox({ symbol, setSymbol, reason, setReason, onSubmit }) {
  return (
    <form className="panel shortlist-add-box" onSubmit={onSubmit}>
      <h3 className="panel-title small-caps">Add a symbol to the shortlist</h3>
      <div className="shortlist-add-row">
        <input
          type="text"
          placeholder="SYMBOL"
          value={symbol}
          onChange={(e) => setSymbol(e.target.value)}
          className="mono"
        />
        <input
          type="text"
          placeholder="why (optional)"
          value={reason}
          onChange={(e) => setReason(e.target.value)}
        />
        <button type="submit" disabled={!symbol.trim()}>+ add</button>
      </div>
    </form>
  );
}
