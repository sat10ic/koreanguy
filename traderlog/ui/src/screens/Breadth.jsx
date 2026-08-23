// BREADTH — WIREFRAMES.md §4
// XP and MBI are adopted reverse-engineering (manas_os/regime/xp.py and
// snapshot.py::compute_mbi). Band cutoffs come from those modules — do not
// re-invent them here.
import React from "react";
import { fetchBreadth } from "../api.js";
import { ErrorBox, Loading, Panel, fmtDate, useApi } from "../components/ui.jsx";

// XP band thresholds, from regime/xp.py + snapshot.py::xp_band.
const XP_BANDS = [
  { at: 15, label: "low" },
  { at: 40, label: "building" },
  { at: 100, label: "strong" },
];

function XpTrend({ history }) {
  const rows = history.filter((r) => r.xp_value != null);
  if (rows.length < 2) return <p className="empty">not enough history yet</p>;

  const W = 900;
  const H = 150;
  const max = Math.max(100, ...rows.map((r) => r.xp_value));
  const y = (v) => H - (Math.log(Math.max(v, 1)) / Math.log(max)) * (H - 12) - 6;
  const x = (i) => (i / (rows.length - 1)) * W;
  const path = rows.map((r, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(r.xp_value).toFixed(1)}`).join("");
  const last = rows[rows.length - 1];

  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" height={H} role="img" aria-label="XP trend">
      {XP_BANDS.map((b) => (
        <g key={b.at}>
          <line
            x1="0" x2={W} y1={y(b.at)} y2={y(b.at)}
            stroke="var(--ink)" strokeDasharray="3 4"
          />
          <text x={W - 4} y={y(b.at) - 3} textAnchor="end"
                fontSize="9" fill="var(--ink-4)">
            {b.label} {b.at}
          </text>
        </g>
      ))}
      <path d={path} fill="none" stroke="var(--info)" strokeWidth="1.6" />
      <circle cx={x(rows.length - 1)} cy={y(last.xp_value)} r="3.5" fill="var(--info-ink)" />
    </svg>
  );
}

function Ribbon({ history }) {
  const rows = history.filter((r) => r.mbi_day_color);
  if (!rows.length) return <p className="empty">no MBI history yet</p>;
  return (
    <>
      <div className="ribbon">
        {rows.map((r) => (
          <span
            key={r.trade_date}
            className={`ribbon-cell cell-${r.mbi_day_color}${r.warning_day ? " warn" : ""}`}
            title={`${r.trade_date} · ${r.mbi_day_color}${r.warning_day ? " · warning day" : ""}`}
          />
        ))}
      </div>
      <div className="legend">
        <span><i className="cell-GREEN" style={{ background: "var(--ok)" }} />green</span>
        <span><i style={{ background: "var(--surface-3)" }} />white</span>
        <span><i style={{ background: "var(--bad)" }} />red</span>
        <span>· dot above = warning day (3+ red bands)</span>
      </div>
    </>
  );
}

function Ratio({ k, v, band }) {
  return (
    <div className={`ratio b-${band || "none"}`}>
      <div className="k">{k}</div>
      <div className="v">{v == null ? "—" : Math.round(v)}</div>
      <div className={`b color-${band}`}>{band || "no data"}</div>
    </div>
  );
}

export default function Breadth() {
  const { data, error } = useApi(() => fetchBreadth(90), []);
  if (error) return <ErrorBox error={error} />;
  if (!data) return <Loading />;

  const t = data.today;

  return (
    <>
      <p className="page-lede">
        What the market internals actually did, beside what each trader said about
        them.
      </p>

      <Panel
        title={t ? `Today · ${fmtDate(t.trade_date)}` : "Today"}
        cite="XP: finallynitin recursion · MBI: Stocksgeeks — both adopted from manas_os"
      >
        {!t && <p className="empty">No breadth data yet — that is W4.</p>}
        {t && (
          <>
            <div className="regime-hero">
              <div className="dial">
                <div className="v mono">{t.xp_value?.toFixed(1)}</div>
                <div className="band">XP · {t.xp_band}</div>
                <div className="cap">bands 15 / 40 / 100</div>
              </div>
              <div className="dial">
                <div className={`v color-${t.mbi_day_color}`}>{t.mbi_day_color}</div>
                <div className="band">MBI day colour</div>
                <div className="cap">score {t.mbi_score} of 4 bands</div>
              </div>
              <div className="dial">
                {t.warning_day ? (
                  <span className="warn-flag">⚠ WARNING DAY</span>
                ) : (
                  <span className="unstated">no warning</span>
                )}
                <div className="cap" style={{ marginTop: 8 }}>
                  warning = 3 or more bands red
                </div>
              </div>
            </div>

            <div className="ratio-grid">
              <Ratio k="r10" v={t.r10} band={t.band_r10} />
              <Ratio k="r20" v={t.r20} band={t.band_r20} />
              <Ratio k="r50" v={t.r50} band={t.band_r50} />
              <Ratio k="r4.5" v={t.r4p5} band={t.band_r4p5} />
            </div>
            <div className="footnote">
              r50 uses its own 85 / 60 cutoffs; r10 and r20 use 75 / 50. Taken
              from the adopted module rather than re-derived.
            </div>
          </>
        )}
      </Panel>

      <Panel title={`MBI day colour · last ${data.history.length} sessions`}>
        <Ribbon history={data.history} />
      </Panel>

      <Panel title="XP trend · 90d">
        <XpTrend history={data.history} />
      </Panel>

      <Panel title="What traders said">
        {data.stances.length === 0 && <p className="empty">no breadth commentary captured yet</p>}
        {data.stances.length > 0 && (
          <table className="data">
            <thead>
              <tr>
                <th>date</th>
                <th>trader</th>
                <th>stance</th>
                <th>XP / MBI that day</th>
                <th>agreed?</th>
              </tr>
            </thead>
            <tbody>
              {data.stances.slice(0, 14).map((s) => (
                <tr key={`${s.trade_date}-${s.handle}`}>
                  <td>{fmtDate(s.trade_date)}</td>
                  <td>@{s.handle}</td>
                  <td>{s.stance?.replace("_", "-")}</td>
                  <td>
                    {s.xp_value != null ? (
                      <>
                        <span className="mono">{s.xp_value.toFixed(1)}</span> {s.xp_band} ·{" "}
                        <span className={`color-${s.mbi_day_color}`}>{s.mbi_day_color}</span>
                      </>
                    ) : (
                      <span className="unstated">no data</span>
                    )}
                  </td>
                  <td>{s.agreed === null ? "—" : s.agreed ? "✓" : "✗"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {data.agreement.length > 0 && (
          <>
            <div className="sub-label">Agreement</div>
            {data.agreement.map((a) => (
              <div className="metric-row" key={a.handle}>
                <span className="mk">@{a.handle}</span>
                <span className="mv mono">{a.agreed_pct}%</span>
                <span className="bar" style={{ width: 160 }}>
                  <span className="bar-fill bar-teal" style={{ width: `${a.agreed_pct}%` }} />
                </span>
                {/* n is mandatory beside any percentage on this screen */}
                <span className="unstated">n={a.n}</span>
              </div>
            ))}
          </>
        )}

        <div className="footnote">
          "Agreed" is a deliberately crude three-way match: risk-on vs GREEN,
          risk-off vs RED, neutral vs WHITE. It measures agreement with one
          particular breadth model — <strong>not</strong> whether the trader was
          right. A low score here is not evidence that someone reads the market
          badly.
        </div>
      </Panel>
    </>
  );
}
