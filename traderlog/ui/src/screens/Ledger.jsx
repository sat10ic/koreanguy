// LEDGER — WIREFRAMES.md §3
import React from "react";
import { fetchPosition, fetchPositions, fetchTraders } from "../api.js";
import {
  Conf, Disclosure, ErrorBox, Loading, Num, Panel, Pct, SortableTh, fmtDate, useApi,
} from "../components/ui.jsx";
import { PositionBars } from "../components/charts.jsx";

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
            <div className="interpret">unresolved: {p.unresolved.join(" · ")}</div>
          )}
        </div>

        <div>
          {data.media.length > 0 ? (
            data.media.map((m) => (
              <figure className="media-box" key={`${m.post_id}-${m.idx}`}>
                {/* The archived image, served from disk by /api/media. This used
                    to be a placeholder div with the words "mock rows have no
                    file on disk" printed unconditionally -- over REAL images
                    that serve fine. It told the user their own captured evidence
                    did not exist. The "no file" line is now an onError fallback
                    and nothing else. */}
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

          {/* Evidence is deliberately always visible, never behind a toggle:
              it is the reason this table can be trusted at all. */}
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

export default function Ledger() {
  const [handle, setHandle] = React.useState("");
  const [status, setStatus] = React.useState("");
  const [symbol, setSymbol] = React.useState("");
  const [openId, setOpenId] = React.useState(null);
  const [sortKey, setSortKey] = React.useState(null);
  const [sortDir, setSortDir] = React.useState("desc");

  const { data, error } = useApi(
    () => fetchPositions({ handle, status, symbol, limit: 200 }),
    [handle, status, symbol]
  );
  const { data: roster } = useApi(fetchTraders, []);

  const sorted = sortPositions(data?.positions || [], sortKey, sortDir);

  function onSort(key) {
    if (sortKey === key) setSortDir(sortDir === "asc" ? "desc" : "asc");
    else {
      setSortKey(key);
      setSortDir("desc");
    }
  }

  // Shared time axis for the lead graphic -- rows are only comparable in
  // time if they all sit on the same domain. The /api/positions payload
  // doesn't carry add/stop-move dates (only opened_at/closed_at), so the
  // bar shows entry, exit/open state and result but no interior event
  // ticks; those only exist in the per-position detail payload.
  const barRows = sorted.map((p) => ({
    id: p.position_id,
    label: p.symbol,
    sublabel: `@${p.handle}`,
    start: p.opened_at,
    end: p.closed_at || null,
    result: p.net_result_pct,
    warn: p.unresolved?.length ? p.unresolved.join(" · ") : undefined,
    // Dated interior events now come from /api/positions itself. A stop that
    // moved UP is the trader taking risk off, and it is the most informative
    // mark on this chart -- without these the bar is a plain line with nothing
    // happening inside it.
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
      <p className="page-lede">
        Every position reconstructed from a thread, with the posts that justify
        each number. Results are what the trader <em>said</em> — never computed
        from market data.
      </p>
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
              {["open", "added", "partial", "closed", "scratched", "unclear"].map((s) => (
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
        </div>
      </Panel>

      <Panel title="Positions" right={data ? `${data.positions.length} shown` : ""}>
        {!data && !error && <Loading />}
        {data && (
          <div className="chart-wrap">
            <PositionBars from={barFrom} to={barTo} rows={barRows} onRowClick={(id) => setOpenId(openId === id ? null : id)} />
            {barRows.length > 0 && (
              <div className="chart-caption">
                Every shown position on one shared axis — clustering in time is the point,
                and a table sorted by symbol destroys it. ● entry · ● add ·
                ▲ stop raised · ○ exit · ▶ still open.
              </div>
            )}
          </div>
        )}
        {data?.positions?.length === 0 && (
          <p className="empty">
            Nothing reconstructed yet. The reconciler is W2.
          </p>
        )}
        {data?.positions?.length > 0 && (
          <>
            <table className="data">
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
                      <td>@{p.handle}</td>
                      <td>
                        <strong>{p.symbol}</strong>
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
                          ⚠ {p.unresolved.join(" · ")}
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                ))}
              </tbody>
            </table>
          </>
        )}
      </Panel>

      {openId && <Detail id={openId} />}
    </>
  );
}
