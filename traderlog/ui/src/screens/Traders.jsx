// TRADERS — WIREFRAMES.md §2
import React from "react";
import { fetchTrader, fetchTraders } from "../api.js";
import {
  Bar, Chip, ErrorBox, Loading, Num, Panel, fmtDate, useApi,
} from "../components/ui.jsx";

function pct(v) {
  return v === null || v === undefined ? null : Math.round(v * 100);
}

function Profile({ handle }) {
  const { data, error } = useApi(() => fetchTrader(handle), [handle]);
  if (error) return <ErrorBox error={error} />;
  if (!data) return <Loading />;

  const s = data.style;
  const tilt = s?.sector_tilt || {};
  const tiltTop = Object.entries(tilt).sort((a, b) => b[1] - a[1]);

  return (
    <Panel
      title={`@${data.trader.handle}`}
      right={<Chip kind={data.trader.tier}>{data.trader.tier}</Chip>}
    >
      {!s && <p className="empty">No style profile computed yet — that is W6.</p>}

      {s && (
        <>
          <div className="hero-stats">
            <div className="hero-stat">
              <div className="n">
                {s.stated_win_rate == null ? "—" : `${pct(s.stated_win_rate)}%`}
              </div>
              <div className="k">stated win rate</div>
              <div className="q">of {data.closed.length} closed</div>
            </div>
            <div className="hero-stat">
              <div className="n">{s.avg_r ? `${s.avg_r.toFixed(1)}R` : "—"}</div>
              <div className="k">avg result</div>
              <div className="q">where a result was stated</div>
            </div>
            <div className="hero-stat">
              <div className="n">
                {s.median_hold_days ? `${Math.round(s.median_hold_days)}d` : "—"}
              </div>
              <div className="k">median hold</div>
              <div className="q">entry to stated exit</div>
            </div>
            <div className="hero-stat">
              <div className="n">
                {s.preach_score == null ? "—" : `${pct(s.preach_score)}%`}
              </div>
              <div className="k">practices what they preach</div>
              <div className="q">linked trades only</div>
            </div>
          </div>

          <div className="sub-label">Stop discipline</div>
          <div className="metric-row">
            <span className="mk">stop stated on</span>
            <span className="mv mono">{pct(s.stop_stated_pct)}%</span>
            <Bar pct={pct(s.stop_stated_pct)} tone="teal" />
            <span className="unstated">of positions</span>
          </div>
          <div className="metric-row">
            <span className="mk">stop honoured</span>
            <span className="mv mono">{pct(s.stop_honored_pct)}%</span>
            <Bar pct={pct(s.stop_honored_pct)} tone="amber" />
            <span className="unstated">of those</span>
          </div>
          {s.stop_stated_pct > s.stop_honored_pct && (
            <div className="interpret">
              the {pct(s.stop_stated_pct) - pct(s.stop_honored_pct)}pt gap = stops
              quietly widened, not hit
            </div>
          )}

          {tiltTop.length > 0 && (
            <>
              <div className="sub-label">Where they play</div>
              {tiltTop.slice(0, 4).map(([sector, v]) => (
                <div className="metric-row" key={sector}>
                  <span className="mk">{sector}</span>
                  <span className="mv mono">{v}%</span>
                  <Bar pct={v * 3} tone="teal" />
                </div>
              ))}
            </>
          )}
        </>
      )}

      <div className="sub-label">Open now · {data.open.length}</div>
      {data.open.length === 0 && <p className="empty">nothing open</p>}
      <table className="data">
        <tbody>
          {data.open.map((p) => (
            <tr key={p.position_id}>
              <td>
                <strong>{p.symbol}</strong>
              </td>
              <td>{p.status}</td>
              <td className="num">{p.holding_days}d</td>
              <td>
                {p.unresolved?.length > 0 && (
                  <span className="row-note">⚠ {p.unresolved.join(" · ")}</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </Panel>
  );
}

export default function Traders() {
  const { data, error } = useApi(fetchTraders, []);
  const [selected, setSelected] = React.useState(null);

  React.useEffect(() => {
    if (!selected && data?.traders?.length) setSelected(data.traders[0].handle);
  }, [data, selected]);

  return (
    <>
      <p className="page-lede">
        How each tracked trader actually trades — measured from what they posted,
        not from what they claim.
      </p>
      <ErrorBox error={error} />

      <Panel title="Roster">
        {!data && !error && <Loading />}
        {data?.traders?.length === 0 && (
          <p className="empty">No traders configured. Add the roster at W1.</p>
        )}
        {data?.traders?.length > 0 && (
          <table className="data">
            <thead>
              <tr>
                <th>handle</th>
                <th>tier</th>
                <th className="num">posts</th>
                <th className="num">open</th>
                <th className="num">closed</th>
                <th className="num">hold</th>
                <th className="num">win</th>
                <th className="num">preach</th>
                <th>last seen</th>
              </tr>
            </thead>
            <tbody>
              {data.traders.map((t) => (
                <tr
                  key={t.handle}
                  className="clickable"
                  onClick={() => setSelected(t.handle)}
                >
                  <td>
                    <strong>@{t.handle}</strong>
                  </td>
                  <td>
                    <Chip kind={t.tier}>{t.tier}</Chip>
                  </td>
                  <td className="num mono">{t.posts}</td>
                  <td className="num mono">{t.open_positions}</td>
                  <td className="num mono">{t.closed_positions}</td>
                  <td className="num mono">
                    {t.median_hold_days ? `${Math.round(t.median_hold_days)}d` : "—"}
                  </td>
                  {/* A bare em dash, never "—%" and never "0%": no data and a
                      genuine zero must not look the same. */}
                  <td className="num mono">
                    {t.stated_win_rate === null || t.stated_win_rate === undefined
                      ? "—"
                      : `${pct(t.stated_win_rate)}%`}
                  </td>
                  <td className="num mono">
                    {t.preach_score === null || t.preach_score === undefined
                      ? "—"
                      : `${pct(t.preach_score)}%`}
                  </td>
                  <td>{fmtDate(t.last_seen_ts)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Panel>

      {selected && <Profile handle={selected} />}
    </>
  );
}
