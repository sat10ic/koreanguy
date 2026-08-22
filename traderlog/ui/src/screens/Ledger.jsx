// LEDGER — WIREFRAMES.md §3
import React from "react";
import { fetchPosition, fetchPositions, fetchTraders } from "../api.js";
import {
  Conf, ErrorBox, Loading, Num, Panel, Pct, fmtDate, useApi,
} from "../components/ui.jsx";

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
              <div className="media-box" key={`${m.post_id}-${m.idx}`}>
                <div>[ chart image ]</div>
                {m.vision?.annotated_levels?.length > 0 && (
                  <div style={{ marginTop: 6 }}>
                    {m.vision.annotated_levels.length} level(s) read
                  </div>
                )}
                <div style={{ marginTop: 6, fontSize: 9 }}>
                  mock rows have no file on disk
                </div>
              </div>
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

  const { data, error } = useApi(
    () => fetchPositions({ handle, status, symbol, limit: 200 }),
    [handle, status, symbol]
  );
  const { data: roster } = useApi(fetchTraders, []);

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
        {data?.positions?.length === 0 && (
          <p className="empty">
            Nothing reconstructed yet. The reconciler is W2.
          </p>
        )}
        {data?.positions?.length > 0 && (
          <table className="data">
            <thead>
              <tr>
                <th>trader</th>
                <th>symbol</th>
                <th className="num">entry</th>
                <th className="num">adds</th>
                <th className="num">stop</th>
                <th className="num">exit</th>
                <th className="num">net</th>
                <th className="num">days</th>
                <th className="num">cf</th>
              </tr>
            </thead>
            <tbody>
              {data.positions.map((p) => (
                <React.Fragment key={p.position_id}>
                  <tr
                    className="clickable"
                    onClick={() =>
                      setOpenId(openId === p.position_id ? null : p.position_id)
                    }
                  >
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
                      <td colSpan={9} className="row-note">
                        ⚠ {p.unresolved.join(" · ")}
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
    </>
  );
}
