import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  fetchWatchlist,
  addWatchlistSymbol,
  removeWatchlistSymbol,
  pushSymbolToDebate,
  fetchFocusList,
  addFocusSymbol,
  removeFocusSymbol,
} from "./api.js";
import ChartDrawer from "./ChartDrawer.jsx";
import { useDensity } from "./DensityContext.jsx";
import { colorScale } from "./viz.js";
import { Term } from "./Glossary.jsx";

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
  { key: "NEW", title: "IN TONIGHT'S POOL", match: (row) => row.status === "ADDED" },
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

function ShortlistRow({ row, onDebate, onChart, onRemove, onTradePlan, onSSAdd, isExpert, pendingDebate }) {
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
          <button
            type="button"
            onClick={() => onDebate(row.symbol)}
            disabled={pendingDebate?.has(row.symbol)}
            title={pendingDebate?.has(row.symbol) ? "Push pending..." : "Push to DEBATE"}
          >
            {pendingDebate?.has(row.symbol) ? "… pending" : <>&rarr; debate</>}
          </button>
          {onTradePlan && (
            <button type="button" onClick={() => onTradePlan(row.symbol)}>open trade plan</button>
          )}
          <button type="button" onClick={() => onChart(row.symbol)}>chart</button>
          {onSSAdd && (
            <button
              type="button"
              className="ss-plus-btn"
              onClick={() => onSSAdd(row.symbol)}
              title="add to Strong Start list"
              aria-label={`add ${row.symbol} to Strong Start`}
            >
              ⚡ SS+
            </button>
          )}
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

function ShortlistPane({ date, onOpenTradePlan }) {
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

  const [pendingDebate, setPendingDebate] = useState(() => new Set());

  const handleDebate = useCallback((symbol) => {
    setPendingDebate((cur) => new Set(cur).add(symbol));
    setToast({ kind: "ok", text: `Pushing ${symbol} to debate...` });
    pushSymbolToDebate(symbol, date)
      .then((body) => {
        if (body.already_debated) {
          setToast({ kind: "ok", text: `${symbol} already debated for this date - showing existing card` });
        } else {
          setToast({ kind: "ok", text: `${symbol} pushed to debate (${body.status || "ok"})` });
        }
      })
      .catch((err) => {
        if (err.status === 409) {
          setToast({ kind: "err", text: `${symbol} push already running - please wait` });
        } else {
          setToast({ kind: "err", text: `Debate push failed for ${symbol}: ${String(err.message || err)}` });
        }
      })
      .finally(() => {
        setPendingDebate((cur) => {
          const next = new Set(cur);
          next.delete(symbol);
          return next;
        });
      });
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

  const handleSSAdd = useCallback((symbol) => {
    setToast({ kind: "ok", text: `Adding ${symbol} to Strong Start...` });
    addFocusSymbol(symbol, "user", "added from shortlist")
      .then(() => setToast({ kind: "ok", text: `${symbol} added to Strong Start` }))
      .catch((err) => setToast({ kind: "err", text: `Strong Start add failed for ${symbol}: ${String(err.message || err)}` }));
  }, []);

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
        <p className="shortlist-delta-caption caption-b">
          "added N" above is only tonight's curator changes — the group header counts below include every name already sitting in that status bucket, not just tonight's adds.
        </p>
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
                onSSAdd={handleSSAdd}
                pendingDebate={pendingDebate}
              />
            ))}
          </div>
        </section>
      ))}
      <AddBox symbol={addSymbol} setSymbol={setAddSymbol} reason={addReason} setReason={setAddReason} onSubmit={handleAdd} />
      <ChartDrawer symbol={chartSymbol} date={date} defaultInterval="W" onClose={() => setChartSymbol(null)} />
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

// STRONG START / Arora focus list -- SS RVOL dashboard grammar per
// manas_os/design/STRONG_START_FOCUS_SPEC.md (frontend section).
const SS_CHG_FLAG = 1.5;

function ssRowColor(chgPct) {
  if (chgPct === null || chgPct === undefined || Number.isNaN(Number(chgPct))) return "";
  const v = Number(chgPct);
  if (v >= SS_CHG_FLAG) return "ss-row-green";
  if (v <= -SS_CHG_FLAG) return "ss-row-red";
  return "ss-row-amber";
}

function fmtPct1(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "-";
  return `${Number(value).toFixed(1)}%`;
}

const SS_DOT_CAP = 8;

function SSDotStrip({ count }) {
  const n = count === null || count === undefined || Number.isNaN(Number(count)) ? 0 : Math.round(Number(count));
  if (!n) return <span className="dot-strip-empty mono">-</span>;
  const shown = Math.min(n, SS_DOT_CAP);
  return (
    <span className="dot-strip mono" title={`${n} purple dot${n !== 1 ? "s" : ""} (60d)`}>
      {"●".repeat(shown)}
      {n > SS_DOT_CAP ? "+" : ""}
    </span>
  );
}

const SS_SORTS = [
  { key: "rvol", label: "RVOL" },
  { key: "chg", label: "Chg%" },
  { key: "ss", label: "SS" },
];

function sortSSRows(rows, sortKey) {
  const arr = [...rows];
  if (sortKey === "chg") {
    arr.sort((a, b) => (b.chg_pct ?? -Infinity) - (a.chg_pct ?? -Infinity));
  } else if (sortKey === "ss") {
    arr.sort((a, b) => {
      const ssDiff = (b.ss_flag ? 1 : 0) - (a.ss_flag ? 1 : 0);
      if (ssDiff !== 0) return ssDiff;
      return (b.rvol20 ?? -Infinity) - (a.rvol20 ?? -Infinity);
    });
  } else {
    arr.sort((a, b) => (b.rvol20 ?? -Infinity) - (a.rvol20 ?? -Infinity));
  }
  return arr;
}

function sourceTag(row) {
  if (row.source === "llm") {
    return <span className="ss-badge ss-badge-llm" title={row.reason || "Arora-qualified push"}>AI (Arora match)</span>;
  }
  const label = row.source === "screener" ? "screener" : "user";
  return <span className="ss-badge ss-badge-source" title={row.reason || ""}>{label}</span>;
}

function StrongStartRow({ row, isExpert, onRemove }) {
  return (
    <tr className={ssRowColor(row.chg_pct)}>
      <td className="scanner-symbol mono">{row.symbol}</td>
      <td className="mono">{row.rvol20 === null || row.rvol20 === undefined ? "-" : `${Math.round(row.rvol20 * 100)}%`}</td>
      <td className="mono" style={colorScale(row.chg_pct, 8)}>{fmtNum1(row.chg_pct)}%</td>
      <td className="ss-flag-cell">{row.ss_flag ? <span className="ss-star" title="Strong Start: gap-up-and-hold">★</span> : ""}</td>
      <td><SSDotStrip count={row.purple_dot_count} /></td>
      {isExpert && <td className="mono">{fmtPct1(row.pct_up_65d_low)}</td>}
      {isExpert && <td className="mono">{fmtPct1(row.dist_20dma_pct)}</td>}
      {isExpert && <td className="mono">{row.near_52w_high ? "yes" : "no"}</td>}
      {isExpert && <td className="mono">{row.rs === null || row.rs === undefined ? "-" : Math.round(row.rs)}</td>}
      {isExpert && <td>{sourceTag(row)}</td>}
      <td className="ss-actions">
        {!isExpert && sourceTag(row)}
        <button type="button" className="shortlist-remove-btn" onClick={() => onRemove(row.symbol)}>remove</button>
      </td>
    </tr>
  );
}

function fmtNum1(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "-";
  return Number(value).toFixed(1);
}

function StrongStartPane({ date }) {
  const { isExpert } = useDensity();
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [toast, setToast] = useState(null);
  const [sortKey, setSortKey] = useState("rvol");
  const [reloadTick, setReloadTick] = useState(0);

  const reload = useCallback(() => setReloadTick((t) => t + 1), []);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetchFocusList(date)
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

  const handleRemove = useCallback((symbol) => {
    setToast({ kind: "ok", text: `Removing ${symbol} from Strong Start...` });
    removeFocusSymbol(symbol)
      .then(() => {
        setToast({ kind: "ok", text: `${symbol} removed from Strong Start` });
        reload();
      })
      .catch((err) => setToast({ kind: "err", text: `Remove failed for ${symbol}: ${String(err.message || err)}` }));
  }, [reload]);

  const rows = useMemo(() => sortSSRows(data?.rows || [], sortKey), [data, sortKey]);

  if (loading && !data) {
    return <div className="empty-state"><p className="empty-state-line">Loading Strong Start...</p></div>;
  }
  if (error) {
    return <div className="empty-state"><p className="empty-state-line">Strong Start failed to load</p><p className="empty-state-sub">{error}</p></div>;
  }

  return (
    <div className="ss-tab">
      <p className="caption-b ss-caption">
        Strong Start = opened above yesterday's close and held (gap-up-and-hold) + Arora fast-mover checks.
        {" "}
        <Term k="strong-start">what is this?</Term>
      </p>
      {toast && <p className={`scanner-toast ${toast.kind}`}>{toast.text}</p>}
      <div className="ss-sort-row">
        <span className="ss-sort-label mono">sort</span>
        {SS_SORTS.map((s) => (
          <button
            key={s.key}
            type="button"
            className={sortKey === s.key ? "active" : ""}
            onClick={() => setSortKey(s.key)}
          >
            {s.label}
          </button>
        ))}
      </div>
      {rows.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">○</div>
          <p className="empty-state-line">No Strong Start names yet</p>
          <p className="empty-state-sub">add from SHORTLIST or SCANNERS with the SS+ button</p>
        </div>
      ) : (
        <section className="panel scanner-results-panel">
          <div className="scanner-results-head">
            <h3 className="panel-title small-caps">Strong Start / Arora focus list - {date || ""}</h3>
            <span className="mono scanner-match-count">{rows.length} names</span>
          </div>
          <div className="scanner-table-wrap">
            <table className="scanner-hit-table ss-table">
              <thead>
                <tr>
                  <th>symbol</th>
                  <th>RVOL</th>
                  <th>chg%</th>
                  <th><Term k="strong-start">SS</Term></th>
                  <th><Term k="glyph-strip">dots</Term></th>
                  {isExpert && <th>%up-low</th>}
                  {isExpert && <th>dist-MA</th>}
                  {isExpert && <th>near-high</th>}
                  {isExpert && <th><Term k="rs">RS</Term></th>}
                  {isExpert && <th>source</th>}
                  <th>actions</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <StrongStartRow key={row.symbol} row={row} isExpert={isExpert} onRemove={handleRemove} />
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  );
}

export default function ShortlistTab({ date, onOpenTradePlan }) {
  const [mode, setMode] = useState("shortlist");
  return (
    <div className="shortlist-outer">
      <section className="scanner-segmented panel">
        <button
          type="button"
          className={mode === "shortlist" ? "active" : ""}
          onClick={() => setMode("shortlist")}
        >
          SHORTLIST
        </button>
        <button
          type="button"
          className={mode === "strong-start" ? "active" : ""}
          onClick={() => setMode("strong-start")}
        >
          STRONG START
        </button>
      </section>
      {mode === "shortlist" ? (
        <ShortlistPane date={date} onOpenTradePlan={onOpenTradePlan} />
      ) : (
        <StrongStartPane date={date} />
      )}
    </div>
  );
}
