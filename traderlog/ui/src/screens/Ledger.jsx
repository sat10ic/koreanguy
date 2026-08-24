// LEDGER — REDESIGN_SCOUTING_WIRE.md §4.2, handoff 2026-08-24 (S5).
//
// The shared time axis is the signature element and is not negotiable: ONE
// time domain, one lane per position (PositionBars from charts.jsx — an
// ECharts custom series after S4's remap), clips spanning entry→exit, markers
// on the lane for adds and stop moves. The outcome sits in words beside the
// axis with a --caution line for anything unstated, ONE sentence below the
// axis names what the overlap shows (computed from the row intervals, never
// a placeholder), and the sortable/filterable table stays beneath.
import React from "react";
import "../styles/ledger.css";
import { fetchPosition, fetchPositions, fetchTraders } from "../api.js";
import {
  Conf, Disclosure, ErrorBox, Loading, Num, Panel, Pct, SortableTh, fmtDate, useApi,
} from "../components/ui.jsx";
import { PositionBars } from "../components/charts.jsx";

// F4: confidence floor belongs in /api/positions so pagination stays complete.
const CONF_OPTIONS = [0, 0.5, 0.7, 0.9];
const STATUS_OPTIONS = ["open", "added", "partial", "closed", "scratched", "unclear"];
const DAY_MS = 86400000;

// Protected copy (handoff copy appendix #3) — the footnote, verbatim. This
// screen records what traders SAID; no number here is computed from the
// market.
const FOOTNOTE = (
  <p className="footnote">
    Results are what the trader <em>said</em> — never computed from market data.
  </p>
);

// Client-side sort -- the payload doesn't sort server-side, and this table
// is small enough (<=200 rows) that it doesn't need to.
function sortPositions(rows, key, dir) {
  if (!key) return rows;
  const mul = dir === "asc" ? 1 : -1;
  const get = {
    trader: (p) => p.handle || "",
    symbol: (p) => p.symbol || "",
    entry: (p) => p.entry,
    stop: (p) => p.stop,
    exit: (p) => p.exit,
    net: (p) => p.net_result_pct,
    days: (p) => p.holding_days,
    cf: (p) => p.confidence,
  }[key];
  return [...rows].sort((a, b) => {
    const av = get(a);
    const bv = get(b);
    if (av === null || av === undefined) return bv === null || bv === undefined ? 0 : 1;
    if (bv === null || bv === undefined) return -1;
    if (typeof av === "string") return av.localeCompare(bv) * mul;
    return (av - bv) * mul;
  });
}

// The outcome in words, from the payload and nothing else. A stated
// net_result_pct is the trader's own claim ("booked +X%"); an open position
// is "still open"; a closed position without a stated result is "not stated"
// — the --caution line names exactly what is missing (from unresolved[]).
function outcomeWords(p) {
  if (p.net_result_pct !== null && p.net_result_pct !== undefined) {
    return { kind: "booked", pct: p.net_result_pct };
  }
  if (!p.closed_at || p.status === "open") return { kind: "open" };
  return { kind: "unstated" };
}

function outcomeLine(w) {
  if (w.kind === "booked") {
    return (
      <>
        <span className="ledger-outcome-booked">booked</span> <Pct value={w.pct} />
      </>
    );
  }
  if (w.kind === "open") return "still open";
  return "not stated";
}

// Unix-day floor of a date string; NaN when unparseable.
function dayFloor(iso) {
  const t = iso ? new Date(iso).getTime() : NaN;
  return Number.isNaN(t) ? NaN : Math.floor(t / DAY_MS);
}

// A row's calendar window on the shared axis: opened day → closed day, or
// today for anything still open (same rule as the axis "to"). Only rows with
// a parseable start can take part in an overlap.
function windowOf(row, todayMs) {
  const start = dayFloor(row.start);
  if (Number.isNaN(start)) return null;
  const end = row.end ? dayFloor(row.end) : Math.floor(todayMs / DAY_MS);
  return { start, end: Math.max(start, end), row };
}

// ONE sentence below the axis naming what the overlap shows, computed from
// the row intervals — never a placeholder. The densest overlap (in calendar
// days) wins; on a tie a same-symbol pair is preferred, because two traders
// on one name is the finding this view exists for. When nothing overlaps the
// sentence says so honestly.
function computeOverlapSentence(rows) {
  const todayMs = Date.now();
  const spans = rows.map((r) => windowOf(r, todayMs)).filter(Boolean);
  let best = null; // { a, b, days, same }
  for (let i = 0; i < spans.length; i += 1) {
    for (let j = i + 1; j < spans.length; j += 1) {
      const a = spans[i];
      const b = spans[j];
      const days = Math.min(a.end, b.end) - Math.max(a.start, b.start) + 1;
      if (days <= 0) continue;
      const same = a.row.symbol === b.row.symbol;
      if (!best || days > best.days || (days === best.days && same && !best.same)) {
        best = { a, b, days, same };
      }
    }
  }
  if (!best) return "No two positions overlapped in this window.";
  const name = (h) => (h ? h.charAt(0).toUpperCase() + h.slice(1) : "?");
  const aName = name(best.a.row.handle);
  const bName = name(best.b.row.handle);
  if (best.same) {
    return `${aName} and ${bName} were both in ${best.a.row.symbol} at the same time.`;
  }
  return `${aName} and ${bName} were both holding at the same time — one in ${best.a.row.symbol}, the other in ${best.b.row.symbol}.`;
}

function Detail({ id }) {
  const { data, error } = useApi(() => fetchPosition(id), [id]);
  if (error) return <ErrorBox error={error} />;
  if (!data) return <Loading />;
  const p = data.position;

  return (
    <Panel
      title={`${p.symbol} · @${p.handle} · ${p.status}`}
      right={p.net_result_pct != null ? <Pct value={p.net_result_pct} /> : null}
    >
      <div className="detail-grid">
        <div>
          <div className="timeline">
            {data.events.map((e) => (
              <div className="tl-row" key={e.id}>
                <span>{fmtDate(e.stated_at)}</span>
                <span className="tl-kind">{e.kind.replace(/_/g, " ")}</span>
                <span>
                  {e.price != null ? <Num value={e.price} prefix="₹" /> : <span className="unstated">no price</span>}
                  {e.qty_pct != null && <span className="mono"> · {e.qty_pct}%</span>}
                </span>
                <span className="tl-quote">{e.post_text ? `"${e.post_text}"` : ""}</span>
                <span>
                  {e.post_url && (
                    <a href={e.post_url} target="_blank" rel="noreferrer">
                      ↗ post
                    </a>
                  )}
                </span>
              </div>
            ))}
          </div>

          {p.unresolved?.length > 0 && (
            /* Complete strings, verbatim — never paraphrased. */
            <div className="interpret">unresolved: {p.unresolved.join(" · ")}</div>
          )}
        </div>

        <div>
          {data.media.length > 0 ? (
            data.media.map((m) => (
              <figure className="media-box" key={`${m.post_id}-${m.idx}`}>
                {/* The archived image, served from disk by /api/media. The "no
                    file" line is an onError fallback and nothing else. */}
                <img
                  src={`/api/media/${m.post_id}/${m.idx}`}
                  alt={
                    m.vision?.structure_note ||
                    `chart attached to post ${m.post_id}`
                  }
                  onError={(e) => {
                    e.currentTarget.style.display = "none";
                    const note = e.currentTarget.nextElementSibling;
                    if (note) note.hidden = false;
                  }}
                />
                <figcaption className="media-missing" hidden>
                  image not on disk — archive may be incomplete
                </figcaption>
                {m.vision?.annotated_levels?.length > 0 && (
                  <figcaption className="media-note">
                    {m.vision.annotated_levels.length} level(s) read
                  </figcaption>
                )}
              </figure>
            ))
          ) : (
            <div className="media-box">no chart attached</div>
          )}

          {/* Evidence is deliberately always visible on expansion, never behind
              a toggle: it is the reason this table can be trusted at all. */}
          <div className="sub-label">Evidence</div>
          <dl className="evidence">
            {Object.entries(p.evidence || {}).map(([field, pid]) => (
              <React.Fragment key={field}>
                <dt>{field}</dt>
                <dd>← {pid}</dd>
              </React.Fragment>
            ))}
          </dl>
        </div>
      </div>
    </Panel>
  );
}

export default function Ledger({ presetSymbol, presetPositionId, onNavigate }) {
  const [handle, setHandle] = React.useState("");
  const [status, setStatus] = React.useState("");
  const [symbol, setSymbol] = React.useState(() => presetSymbol || "");
  const [confMin, setConfMin] = React.useState("");
  const [unresolvedOnly, setUnresolvedOnly] = React.useState(false);
  const [openId, setOpenId] = React.useState(() => presetPositionId || null);
  const [sortKey, setSortKey] = React.useState(null);
  const [sortDir, setSortDir] = React.useState("desc");

  const { data, error } = useApi(
    () => fetchPositions({ handle, status, symbol, min_confidence: confMin, limit: 200 }),
    [handle, status, symbol, confMin]
  );
  const { data: roster } = useApi(fetchTraders, []);

  // I6: LEDGER's own version of FEED's `unresolved` toggle. /api/positions
  // doesn't take an unresolved param (unlike /api/feed), so this filters the
  // already-fetched page client-side -- same approach the table's sort
  // already uses.
  const positions = unresolvedOnly
    ? (data?.positions || []).filter((p) => p.unresolved?.length > 0)
    : data?.positions || [];
  const sorted = sortPositions(positions, sortKey, sortDir);

  function onSort(key) {
    if (sortKey === key) setSortDir(sortDir === "asc" ? "desc" : "asc");
    else {
      setSortKey(key);
      setSortDir("desc");
    }
  }

  // Shared time axis for the lead graphic -- rows are only comparable in
  // time if they all sit on the same domain. Rows carry the frozen
  // PositionBars contract {id,label,sublabel,start,end,result,warn,events}
  // plus the symbol/handle the overlap sentence computes from. The interior
  // marker events come straight from /api/positions, which already maps
  // position_events to the shared {at,kind} vocabulary ("add" | "sl_up" |
  // "sl_down" | "exit"). Still-open positions have end null -> the clip
  // continues to the axis end; their lanes are --risk (open = money risked).
  const barRows = sorted.map((p) => ({
    id: p.position_id,
    symbol: p.symbol,
    handle: p.handle,
    label: p.symbol,
    sublabel: `@${p.handle}`,
    start: p.opened_at,
    end: p.closed_at || null,
    result: p.net_result_pct,
    warn: p.unresolved?.length ? p.unresolved.join(" · ") : undefined,
    events: p.events || [],
  }));
  const barTimes = barRows
    .flatMap((r) => [r.start, r.end])
    .filter(Boolean)
    .map((d) => new Date(d).getTime())
    .filter((t) => !Number.isNaN(t));
  const barFrom = barTimes.length ? new Date(Math.min(...barTimes)).toISOString().slice(0, 10) : undefined;
  const barTo = barTimes.length
    ? new Date(Math.max(...barTimes, Date.now())).toISOString().slice(0, 10)
    : undefined;

  return (
    <>
      <ErrorBox error={error} />

      <Panel title="Filters">
        <div className="filters">
          <label>
            trader
            <select value={handle} onChange={(e) => setHandle(e.target.value)}>
              <option value="">all</option>
              {roster?.traders?.map((t) => (
                <option key={t.handle} value={t.handle}>
                  {t.handle}
                </option>
              ))}
            </select>
          </label>
          <label>
            status
            <select value={status} onChange={(e) => setStatus(e.target.value)}>
              <option value="">all</option>
              {STATUS_OPTIONS.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </label>
          <label>
            symbol
            <input
              value={symbol}
              placeholder="e.g. DIXON"
              onChange={(e) => setSymbol(e.target.value.toUpperCase())}
            />
          </label>
          <label>
            conf
            <select
              value={confMin}
              onChange={(e) => setConfMin(e.target.value === "" ? "" : Number(e.target.value))}
            >
              <option value="">all</option>
              {CONF_OPTIONS.map((c) => (
                <option key={c} value={c}>{`≥${c.toFixed(1)}`}</option>
              ))}
            </select>
          </label>
          {/* I6: mirrors FEED's `.filter-toggle` pattern exactly -- LEDGER is
              the screen organised around stated-vs-missing fields, and had
              no way to isolate the ones with a gap. */}
          <button
            type="button"
            className={`filter-toggle${unresolvedOnly ? " active" : ""}`}
            aria-pressed={unresolvedOnly}
            onClick={() => setUnresolvedOnly((v) => !v)}
          >
            unresolved{unresolvedOnly ? " ✕" : ""}
          </button>
        </div>
      </Panel>

      <Panel title="Positions" right={data ? `${sorted.length} shown` : ""}>
        {!data && !error && <Loading />}
        {data && barRows.length > 0 && (
          <div className="ledger-chart">
            <PositionBars
              from={barFrom}
              to={barTo}
              rows={barRows}
              onRowClick={(id) => setOpenId(openId === id ? null : id)}
            />
            <p className="ledger-legend">● entry · ● add · ▲ stop raised · ○ exit · ▶ still open.</p>
            {/* Outcome in words, one line per lane — beside the axis. A
                --caution line follows anything unstated, naming exactly what
                is missing from unresolved[]. */}
            <ul className="ledger-outcomes">
              {sorted.map((p) => {
                const w = outcomeWords(p);
                return (
                  <li key={p.position_id} className="ledger-outcome">
                    <span className="ledger-outcome-id mono">
                      {p.symbol} · @{p.handle}
                    </span>
                    <span
                      className={`ledger-outcome-word${w.kind === "open" ? " ledger-outcome--open" : ""}`}
                    >
                      {outcomeLine(w)}
                    </span>
                    {p.unresolved?.length > 0 && (
                      <span className="ledger-caution">⚠ {p.unresolved.join(" · ")}</span>
                    )}
                  </li>
                );
              })}
            </ul>
            {/* ONE sentence naming what the overlap shows — computed from the
                row intervals, never a generic placeholder. */}
            <p className="ledger-overlap">{computeOverlapSentence(barRows)}</p>
          </div>
        )}
        {/* The chart's own labelled empty state when nothing is reconstructed
            yet; zero rows => no redundant frame+text pair (Slice C). */}
        {data && (data.positions || []).length === 0 && (
          <PositionBars from={undefined} to={undefined} rows={[]} />
        )}
        {data && (data.positions || []).length > 0 && sorted.length === 0 && (
          <p className="empty">No positions match these filters.</p>
        )}
        {sorted.length > 0 && (
          <table className="ledger-table">
            <thead>
              <tr>
                <th aria-hidden="true" />
                <SortableTh label="trader" active={sortKey === "trader"} dir={sortDir} onClick={() => onSort("trader")} />
                <SortableTh label="symbol" active={sortKey === "symbol"} dir={sortDir} onClick={() => onSort("symbol")} />
                <SortableTh label="entry" className="num" active={sortKey === "entry"} dir={sortDir} onClick={() => onSort("entry")} />
                <th className="num">adds</th>
                <SortableTh label="stop" className="num" active={sortKey === "stop"} dir={sortDir} onClick={() => onSort("stop")} />
                <SortableTh label="exit" className="num" active={sortKey === "exit"} dir={sortDir} onClick={() => onSort("exit")} />
                <SortableTh label="net" className="num" active={sortKey === "net"} dir={sortDir} onClick={() => onSort("net")} />
                <SortableTh label="days" className="num" active={sortKey === "days"} dir={sortDir} onClick={() => onSort("days")} />
                <SortableTh label="cf" className="num" active={sortKey === "cf"} dir={sortDir} onClick={() => onSort("cf")} />
              </tr>
            </thead>
            <tbody>
              {sorted.map((p) => (
                <React.Fragment key={p.position_id}>
                  <tr>
                    <td>
                      <Disclosure
                        open={openId === p.position_id}
                        onToggle={() => setOpenId(openId === p.position_id ? null : p.position_id)}
                      />
                    </td>
                    <td>
                      {/* C2.3: jump to this trader's TRADERS profile. */}
                      <button
                        type="button"
                        className="xlink"
                        onClick={() => onNavigate?.("TRADERS", { handle: p.handle })}
                      >
                        @{p.handle}
                      </button>
                    </td>
                    <td>
                      {/* C2.4: same-screen filter -- pre-fills the symbol
                          text input already in the filter row above. */}
                      <button
                        type="button"
                        className="xlink"
                        onClick={() => setSymbol(p.symbol)}
                      >
                        <strong>{p.symbol}</strong>
                      </button>
                    </td>
                    <td className="num">
                      <Num value={p.entry} dash="—" />
                    </td>
                    <td className="num">
                      {p.adds?.length ? (
                        <span className="mono">
                          {p.adds.length}×<Num value={p.adds[0].price} />
                        </span>
                      ) : (
                        "—"
                      )}
                    </td>
                    <td className="num">
                      <Num value={p.stop} dash="—" />
                    </td>
                    <td className="num">
                      <Num value={p.exit} dash="—" />
                    </td>
                    <td className="num">
                      <Pct value={p.net_result_pct} />
                    </td>
                    <td className="num mono">{p.holding_days ?? "—"}</td>
                    <td className="num">
                      <Conf value={p.confidence} />
                    </td>
                  </tr>
                  {p.unresolved?.length > 0 && (
                    <tr>
                      <td colSpan={10} className="row-note">
                        {/* W3c: the collapsed table shows a truthful count; the
                            complete strings render in the expanded detail. */}
                        ⚠ {p.unresolved.length} unresolved
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              ))}
            </tbody>
          </table>
        )}
      </Panel>

      {openId && <Detail id={openId} />}

      {FOOTNOTE}
    </>
  );
}