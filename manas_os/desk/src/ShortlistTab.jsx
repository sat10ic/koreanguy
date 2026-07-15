import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  fetchWatchlist,
  addWatchlistSymbol,
  removeWatchlistSymbol,
  pushSymbolToDebate,
  fetchFocusList,
  addFocusSymbol,
  removeFocusSymbol,
  chartUrl,
} from "./api.js";
import ChartDrawer from "./ChartDrawer.jsx";
import { colorScale } from "./viz.js";
import { SectionLabel, Panel, VerdictChip, ListRelationshipLegend, CrossBadges, useListMembership } from "./components/v5/index.js";
import "./ShortlistTab.v5.css";

// v5 tokens only (no raw hex): teal = system/added, mute = hold,
// green/amber/red = literal promote/demote/drop semantics.
const STATUS_COLOR = {
  ADDED: "var(--v5-teal)",
  HOLD: "var(--v5-ink-mute)",
  PROMOTE: "var(--v5-green)",
  DEMOTE: "var(--v5-amber)",
  DROP: "var(--v5-red)",
};

const STATUS_LABEL = {
  ADDED: "added",
  HOLD: "held",
  PROMOTE: "PROMOTE",
  DEMOTE: "demote",
  DROP: "dropped",
};

const TIER_LABEL = {
  PASSED: "gate-passed",
  NEAR_MISS: "near-miss",
  USER: "user-added",
};

const GROUPS = [
  { key: "PROMOTED", title: "PROMOTED", match: (row) => row.status === "PROMOTE" },
  { key: "NEW", title: "IN TONIGHT'S POOL", match: (row) => row.status === "ADDED" },
  { key: "HOLDING", title: "HOLDING", match: (row) => row.status === "HOLD" || row.status === "DEMOTE" },
  { key: "DROPPED", title: "DEMOTED / DROPPED", match: (row) => row.status === "DROP" },
];

function convictionArrow(status) {
  if (status === "PROMOTE") return "▲";
  if (status === "DEMOTE" || status === "DROP") return "▼";
  return "–";
}

function daysBetween(a, b) {
  const da = new Date(a + "T00:00:00");
  const db = new Date(b + "T00:00:00");
  return Math.round((db - da) / 86400000);
}

// ------------------------------------------------------------------
// real dated timeline — every dot is a real events[] entry from the
// server; no synthetic/interpolated points.
// ------------------------------------------------------------------

function Timeline({ events, latestDate }) {
  if (!events || events.length === 0) return null;
  const dates = events.map((e) => e.date).sort();
  const first = dates[0];
  const last = dates[dates.length - 1];
  const span = Math.max(1, daysBetween(first, last));
  return (
    <div className="sl-timeline" role="list" aria-label="status history timeline">
      <div className="sl-timeline-track" aria-hidden="true" />
      {events.map((ev, idx) => {
        const offset = span === 0 ? 0 : (daysBetween(first, ev.date) / span) * 100;
        const isLatest = ev.date === latestDate;
        return (
          <span
            key={`${ev.date}-${idx}`}
            role="listitem"
            className={"sl-timeline-dot" + (isLatest ? " sl-timeline-dot-pulse" : "")}
            style={{ left: `${offset}%`, background: STATUS_COLOR[ev.action] || "var(--v5-ink-mute)" }}
            title={`${ev.date} — ${STATUS_LABEL[ev.action] || ev.action}: ${ev.reason || ""}`}
          />
        );
      })}
    </div>
  );
}

// ------------------------------------------------------------------
// chart thumbnail (real, via existing /api/desk/chart endpoint)
// ------------------------------------------------------------------

function ChartThumb({ date, symbol, onOpen }) {
  const [failed, setFailed] = useState(false);
  return (
    <button type="button" className="sl-thumb-btn" onClick={() => onOpen(symbol)} title={`Open ${symbol} chart`}>
      {failed ? (
        <div className="sl-thumb-missing mono-num">no chart</div>
      ) : (
        <img
          className="sl-thumb"
          src={chartUrl(date, symbol, "daily")}
          alt={`${symbol} daily chart`}
          loading="lazy"
          onError={() => setFailed(true)}
        />
      )}
    </button>
  );
}

// ------------------------------------------------------------------
// reversible, structured remove (replaces window.prompt) — inline
// reason field + confirm/cancel, then an inline "removed — undo"
// result that re-adds the symbol via the existing add endpoint.
// ------------------------------------------------------------------

function RemoveControl({ symbol, onConfirm }) {
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState("");

  if (!open) {
    return (
      <button type="button" className="sl-remove-btn" onClick={() => setOpen(true)} aria-expanded="false">
        remove
      </button>
    );
  }
  return (
    <span className="sl-remove-inline" role="group" aria-label={`remove ${symbol} reason`}>
      <input
        type="text"
        value={reason}
        onChange={(e) => setReason(e.target.value)}
        placeholder="why? (optional)"
        aria-label={`reason for removing ${symbol}`}
        autoFocus
      />
      <button
        type="button"
        className="sl-remove-confirm"
        onClick={() => {
          onConfirm(reason);
          setOpen(false);
          setReason("");
        }}
      >
        confirm
      </button>
      <button type="button" className="sl-remove-cancel" onClick={() => setOpen(false)}>
        cancel
      </button>
    </span>
  );
}

function ShortlistRow({ row, onDebate, onChart, onRemove, onTradePlan, onSSAdd, pendingDebate, date, membership, onNavigate }) {
  const events = row.events || [];
  const latest = events[events.length - 1];
  const latestDate = latest ? latest.date : row.scan_date;
  return (
    <div className={"sl-row sl-row-" + (row.status || "").toLowerCase()}>
      <ChartThumb date={date} symbol={row.symbol} onOpen={onChart} />
      <div className="sl-row-body">
        <div className="sl-row-top">
          <span className="sl-symbol">{row.symbol}</span>
          <CrossBadges symbol={row.symbol} membership={membership} active="SHORTLIST" onNavigate={onNavigate} />
          {row.tier && <span className="sl-tier-chip" title="provenance tier">{TIER_LABEL[row.tier] || row.tier}</span>}
          {row.family_label && (
            <span className="sl-tier-chip" title={row.family || "setup family"}>
              {row.family_label}
            </span>
          )}
          {row.next_trigger && (
            <span className="sl-onlist mono-num" title="next trigger from plan">
              {row.next_trigger}
            </span>
          )}
          <span className="sl-onlist">on list {row.days_on_list ?? 0}d</span>
          <VerdictChip verdict={row.chair_verdict} conviction={row.conviction} showDots={row.conviction !== null && row.conviction !== undefined} />
          {typeof row.miss_streak === "number" && row.miss_streak > 0 && (
            <span className="sl-miss-streak">miss {row.miss_streak}/2</span>
          )}
          <span className="sl-conviction-arrow" aria-hidden="true">{convictionArrow(row.status)}</span>
        </div>

        <p className="sl-story">
          <span className="sl-story-label">
            {!row.chair_verdict ? "Pending verdict:" : row.chair_verdict === "TAKE" ? "Active:" : row.chair_verdict === "SKIP" ? "Rejected:" : "Waiting on:"}
          </span>{" "}
          <span className="sl-story-date mono-num">{row.scan_date || date}</span>{" "}
          {row.reason || "no reason recorded"}
        </p>


        <Timeline events={events} latestDate={latestDate} />

        {events.length > 1 && (
          <details className="sl-event-log">
            <summary>state history ({events.length} events)</summary>
            <ul>
              {events.slice(0, -1).reverse().map((ev, idx) => (
                <li key={idx}>
                  <span className="mono-num">{ev.date}</span>{" "}
                  <span className={"sl-action sl-action-" + ev.action.toLowerCase()}>{STATUS_LABEL[ev.action] || ev.action}:</span>{" "}
                  {ev.reason || ""}
                </li>
              ))}
            </ul>
          </details>
        )}

        <div className="sl-row-actions">
          <button
            type="button"
            onClick={() => onDebate(row.symbol)}
            disabled={pendingDebate?.has(row.symbol)}
            title={pendingDebate?.has(row.symbol) ? "Push pending..." : "Push to DEBATE"}
          >
            {pendingDebate?.has(row.symbol) ? "… pending" : "→ debate"}
          </button>
          {onTradePlan && (
            <button type="button" onClick={() => onTradePlan(row.symbol)}>trade plan</button>
          )}
          {onSSAdd && (
            <button
              type="button"
              className="ss-plus-btn"
              onClick={() => onSSAdd(row.symbol)}
              title="add to Strong Start list"
              aria-label={`add ${row.symbol} to Strong Start`}
            >
              &#9889; SS+
            </button>
          )}
          <RemoveControl symbol={row.symbol} onConfirm={(reason) => onRemove(row.symbol, reason)} />
        </div>
      </div>
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

function AddBox({ symbol, setSymbol, reason, setReason, onSubmit }) {
  return (
    <form className="sl-add-box" onSubmit={onSubmit}>
      <span className="sl-add-label">Add a symbol</span>
      <div className="sl-add-row">
        <input
          type="text"
          placeholder="SYMBOL"
          value={symbol}
          onChange={(e) => setSymbol(e.target.value)}
          className="mono-num"
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

// ------------------------------------------------------------------
// Strong Start — integrated as one mechanism/view within SHORTLIST,
// not a separate conceptual universe. Data via /api/desk/focus-list.
// ------------------------------------------------------------------

const SS_CHG_FLAG = 1.5;

function ssRowTone(chgPct) {
  if (chgPct === null || chgPct === undefined || Number.isNaN(Number(chgPct))) return "";
  const v = Number(chgPct);
  if (v >= SS_CHG_FLAG) return "sl-ss-green";
  if (v <= -SS_CHG_FLAG) return "sl-ss-red";
  return "sl-ss-amber";
}

function fmtPct1(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "-";
  return `${Number(value).toFixed(1)}%`;
}

function sourceTag(row) {
  if (row.source === "llm") {
    return <span className="sl-ss-badge sl-ss-badge-llm" title={row.reason || "Arora-qualified push"}>AI (Arora match)</span>;
  }
  const label = row.source === "screener" ? "screener" : "user";
  return <span className="sl-ss-badge" title={row.reason || ""}>{label}</span>;
}

function StrongStartRow({ row, date, onRemove, onChart, onDebate, pendingDebate }) {
  const events = row.events || [];
  const latestDate = events.length ? events[events.length - 1].date : date;

  return (
    <div className={"sl-row sl-ss-row " + ssRowTone(row.chg_pct)}>
      <ChartThumb date={date} symbol={row.symbol} onOpen={onChart} />
      <div className="sl-row-body">
        <div className="sl-row-top">
          <span className="sl-symbol">{row.symbol}</span>
          {sourceTag(row)}
          {row.ss_flag && <span className="sl-ss-star" title="Strong Start: gap-up-and-hold">&#9733; SS</span>}
        </div>
        <div className="sl-ss-metrics mono-num">
          <span><b>RVOL</b> {row.rvol20 === null || row.rvol20 === undefined ? "-" : `${Math.round(row.rvol20 * 100)}%`}</span>
          <span style={colorScale(row.chg_pct, 8)}><b>chg</b> {fmtPct1(row.chg_pct)}</span>
          <span><b>dots</b> {row.purple_dot_count ?? "-"}</span>
          <span><b>%off low</b> {fmtPct1(row.pct_up_65d_low)}</span>
          <span><b>RS</b> {row.rs === null || row.rs === undefined ? "-" : Math.round(row.rs)}</span>
        </div>
        <p className="sl-story">
          <span className="sl-story-label">Tracked:</span> {row.days_on_list || 0}d
          <span className="sl-story-label" style={{ marginLeft: "1rem" }}>Lens:</span> {row.setup || "none"}
          <br/>
          <span className="sl-story-label">Status:</span> {row.arora_qualifies ? "READY" : "WAITING"} — {row.arora_qualifies ? row.arora_reasons?.join("; ") : row.arora_fails?.join("; ")}
          {row.morning && (
            <>
              <br/>
              <span className="sl-story-label">Entry:</span> {row.morning.entry_rule}
              <br/>
              <span className="sl-story-label">Invalidation:</span> {row.morning.stop_rule}
            </>
          )}
        </p>
        <Timeline events={events} latestDate={latestDate} />
        <div className="sl-row-actions">
          <button
            type="button"
            onClick={() => onDebate(row.symbol)}
            disabled={pendingDebate?.has(row.symbol)}
            title={pendingDebate?.has(row.symbol) ? "Push pending..." : "Push to DEBATE"}
          >
            {pendingDebate?.has(row.symbol) ? "… pending" : "→ debate"}
          </button>
          <RemoveControl symbol={row.symbol} onConfirm={() => onRemove(row.symbol)} />
        </div>
      </div>
    </div>
  );
}

function StrongStartSection({ date, onDebate, pendingDebate, onOpenChart, reloadKey }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [toast, setToast] = useState(null);
  const [tick, setTick] = useState(0);

  const reload = useCallback(() => setTick((t) => t + 1), []);

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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [date, tick, reloadKey]);

  const handleRemove = useCallback((symbol) => {
    setToast({ kind: "ok", text: `Removing ${symbol} from Strong Start...` });
    removeFocusSymbol(symbol)
      .then(() => {
        setToast({ kind: "ok", text: `${symbol} removed from Strong Start` });
        reload();
      })
      .catch((err) => setToast({ kind: "err", text: `Remove failed for ${symbol}: ${String(err.message || err)}` }));
  }, [reload]);

  const rows = useMemo(() => {
    const list = data?.rows || [];
    return [...list].sort((a, b) => (b.rvol20 ?? -Infinity) - (a.rvol20 ?? -Infinity));
  }, [data]);

  return (
    <>
      <SectionLabel count={loading ? "loading…" : `${rows.length} names`}>
        Strong Start — Arora Fast-Mover Mechanism
      </SectionLabel>
      <Panel
        title="gap-up-and-hold + fast-mover checks"
        cite="one mechanism among many, not a separate universe"
        className="sl-ss-panel"
      >
        <p className="sl-ss-caption">
          Strong Start = opened above yesterday's close and held (gap-up-and-hold) + Arora fast-mover checks.
        </p>
        {toast && <p className={`scanner-toast ${toast.kind}`}>{toast.text}</p>}
        {error && <p className="sl-empty-sub">Strong Start failed to load: {error}</p>}
        {!error && !loading && rows.length === 0 && (
          <div className="sl-empty">
            <div className="sl-empty-icon">&#9675;</div>
            <p className="sl-empty-line">No Strong Start names for {date}</p>
            <p className="sl-empty-sub">Real and honest — not every session produces a gap-up-and-hold. Add one with SS+ from SCANNERS or SHORTLIST.</p>
          </div>
        )}
        {rows.length > 0 && (
          <div className="sl-ss-list">
            {rows.map((row) => (
              <StrongStartRow
                key={row.symbol}
                row={row}
                date={date}
                onRemove={handleRemove}
                onChart={onOpenChart}
                onDebate={onDebate}
                pendingDebate={pendingDebate}
              />
            ))}
          </div>
        )}
      </Panel>
    </>
  );
}

// ------------------------------------------------------------------
// main shortlist pane
// ------------------------------------------------------------------

function ShortlistPane({ date, onOpenTradePlan, onOpenChart, membership, onNavigate }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [toast, setToast] = useState(null);
  const [addSymbol, setAddSymbol] = useState("");
  const [addReason, setAddReason] = useState("");
  const [reloadTick, setReloadTick] = useState(0);
  const [undo, setUndo] = useState(null);

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

  const handleRemove = useCallback((symbol, reason) => {
    setToast(null);
    setUndo(null);
    removeWatchlistSymbol(symbol, reason, date)
      .then(() => {
        reload();
        setUndo({ symbol, reason });
      })
      .catch((err) => setToast({ kind: "err", text: `Remove failed for ${symbol}: ${String(err.message || err)}` }));
  }, [date, reload]);

  const handleUndo = useCallback(() => {
    if (!undo) return;
    const { symbol } = undo;
    setUndo(null);
    addWatchlistSymbol(symbol, "user: restored (undo remove)")
      .then(() => {
        setToast({ kind: "ok", text: `${symbol} restored to shortlist` });
        reload();
      })
      .catch((err) => setToast({ kind: "err", text: `Undo failed for ${symbol}: ${String(err.message || err)}` }));
  }, [undo, reload]);

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

  const rows = data?.rows || [];
  const groups = useMemo(
    () => GROUPS.map((g) => ({ ...g, rows: rows.filter(g.match) })).filter((g) => g.rows.length > 0),
    [rows]
  );

  if (loading && !data) {
    return (
      <div className="v5-loading-state" role="status" aria-live="polite">
        <div className="v5-loading-kicker">Curated watch</div>
        <div className="v5-loading-title">Building your shortlist</div>
        <p>Joining saved names with current setup context, triggers and Strong Start status.</p>
        <div className="v5-loading-steps" aria-hidden="true">
          <span />
          <span />
          <span />
        </div>
      </div>
    );
  }
  if (error) {
    return (
      <div className="sl-empty">
        <p className="sl-empty-line">Shortlist failed to load</p>
        <p className="sl-empty-sub">{error}</p>
      </div>
    );
  }

  const noRows = !data || !data.available || rows.length === 0;

  return (
    <>
      {toast && <p className={`scanner-toast ${toast.kind}`}>{toast.text}</p>}
      {undo && (
        <p className="sl-undo-banner">
          {undo.symbol} removed.{" "}
          <button type="button" className="sl-undo-btn" onClick={handleUndo}>undo</button>
        </p>
      )}
      {noRows ? (
        <div className="sl-empty">
          <div className="sl-empty-icon">&#9675;</div>
          <p className="sl-empty-line">No shortlist yet for {date}</p>
          <p className="sl-empty-sub">The Curator hasn't debated any names for this date, or none survived hard gates.</p>
        </div>
      ) : (
        <>
          <Panel title="Curator delta" cite="since last night" className="sl-delta-panel">
            <span>{curatorDeltaLine(data.curator_delta)}</span>
            <p className="sl-delta-caption">
              "added N" is only tonight's curator changes — the group counts below include every name already sitting
              in that status bucket, not just tonight's adds.
            </p>
          </Panel>
          <StrongStartSection
            date={date}
            onDebate={handleDebate}
            pendingDebate={pendingDebate}
            onOpenChart={onOpenChart}
            reloadKey={reloadTick}
          />
          {groups.map((g) => (
            <React.Fragment key={g.key}>
              <SectionLabel count={g.rows.length}>{g.title}</SectionLabel>
              <div className="sl-group-rows">
                {g.rows.map((row) => (
                  <ShortlistRow
                    key={row.symbol}
                    row={row}
                    date={date}
                    onDebate={handleDebate}
                    onChart={onOpenChart}
                    onRemove={handleRemove}
                    onTradePlan={onOpenTradePlan}
                    onSSAdd={handleSSAdd}
                    pendingDebate={pendingDebate}
                    membership={membership}
                    onNavigate={onNavigate}
                  />
                ))}
              </div>
            </React.Fragment>
          ))}
        </>
      )}
      <AddBox symbol={addSymbol} setSymbol={setAddSymbol} reason={addReason} setReason={setAddReason} onSubmit={handleAdd} />
      {noRows && <StrongStartSection date={date} onDebate={handleDebate} pendingDebate={pendingDebate} onOpenChart={onOpenChart} reloadKey={reloadTick} />}
    </>
  );
}

export default function ShortlistTab({ date, onOpenTradePlan, onNavigate }) {
  const [chartSymbol, setChartSymbol] = useState(null);
  const membership = useListMembership(date); // #13b legend + cross-badges
  return (
    <div className="sl-tab">
      <ListRelationshipLegend active="SHORTLIST" membership={membership} onNavigate={onNavigate} />
      <ShortlistPane date={date} onOpenTradePlan={onOpenTradePlan} onOpenChart={setChartSymbol} membership={membership} onNavigate={onNavigate} />
      <ChartDrawer symbol={chartSymbol} date={date} defaultInterval="W" onClose={() => setChartSymbol(null)} />
    </div>
  );
}
