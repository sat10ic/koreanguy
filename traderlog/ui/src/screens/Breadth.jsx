// BREADTH — WIREFRAMES.md §4
// XP and MBI are adopted reverse-engineering (manas_os/regime/xp.py and
// snapshot.py::compute_mbi). Band cutoffs come from those modules — do not
// re-invent them here.
import React from "react";
import { fetchBreadth } from "../api.js";
import { Bar, ErrorBox, Loading, Panel, fmtDate, useApi } from "../components/ui.jsx";
import { BandLine, Ribbon } from "../components/charts.jsx";

// XP band thresholds, from regime/xp.py + snapshot.py::xp_band. Doubles as
// the `bands` prop for the house BandLine component (F9) -- same shape.
const XP_BANDS = [
  { at: 15, label: "low" },
  { at: 40, label: "building" },
  { at: 100, label: "strong" },
];

// F11: the old 4-up padded/bordered card grid was the banned KPI-card
// pattern at n=4 (VISUAL_LANGUAGE §1). This renders as one item in the
// `.ratio-row` dense row -- band colour stays, because RED/WHITE/GREEN is a
// measured state, not an undifferentiated category (unlike F5's chips).
function Ratio({ k, v, band }) {
  return (
    <div className={`ratio-item b-${band || "none"}`}>
      <span className="k">{k}</span>
      <span className="v">{v == null ? "—" : Math.round(v)}</span>
      <span className={`b color-${band}`}>{band || "no data"}</span>
    </div>
  );
}

export default function Breadth() {
  const { data, error } = useApi(() => fetchBreadth(90), []);
  if (error) return <ErrorBox error={error} />;
  if (!data) return <Loading />;

  const t = data.today;

  // F9: local XpTrend/Ribbon reimplementations deleted -- map this screen's
  // data onto the house BandLine/Ribbon components (charts.jsx) instead.
  // Their own empty frames (role="img" + labelled reason) replace the bare
  // <p> text this screen used to render by hand for "not enough history".
  const xpPoints = data.history
    .filter((r) => r.xp_value != null)
    .map((r) => ({ x: r.trade_date, y: r.xp_value }));
  const ribbonCells = data.history.map((r) => ({
    key: r.trade_date,
    state: r.mbi_day_color || "NONE",
    warn: r.warning_day,
    title: `${r.trade_date}${r.mbi_day_color ? ` · ${r.mbi_day_color}` : " · no data"}${r.warning_day ? " · warning day" : ""}`,
  }));

  return (
    <>
      <p className="page-lede">
        What the market internals actually did, beside what each trader said about
        them.
      </p>

      <Panel
        title={t ? `Today · ${fmtDate(t.trade_date)}` : "Today"}
        cite="XP: finallynitin's recursion · MBI: Stocksgeeks"
      >
        {!t && (
          <p className="empty">
            No breadth data yet — no market-internals sessions have been captured.
          </p>
        )}
        {t && (
          <>
            <div className="regime-hero">
              <div className="dial">
                {/* F10: exactly one dominant number per screen (VISUAL_LANGUAGE
                    §4). XP keeps the mega size; MBI below is deliberately
                    smaller so the two tiles never compete. */}
                <div className="v mono">{t.xp_value?.toFixed(1)}</div>
                <div className="band">XP · {t.xp_band}</div>
                <div className="cap">bands 15 / 40 / 100</div>
              </div>
              <div className="dial">
                <div className={`v-sub color-${t.mbi_day_color}`}>{t.mbi_day_color}</div>
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

            <div className="ratio-row">
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
        <Ribbon cells={ribbonCells} />
        <div className="legend">
          <span><i style={{ background: "var(--ok)" }} />green</span>
          <span><i style={{ background: "var(--surface-3)" }} />white</span>
          <span><i style={{ background: "var(--bad)" }} />red</span>
          <span>· dot above = warning day (3+ red bands)</span>
        </div>
      </Panel>

      <Panel title="XP trend · 90d">
        <BandLine points={xpPoints} bands={XP_BANDS} log />
      </Panel>

      <Panel title="What traders said">
        {data.stances.length === 0 && <p className="empty">No breadth commentary captured yet.</p>}
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
                {/* F13: Bar now carries role="img" + an aria-label stating
                    what it encodes, via the `label` prop. */}
                <Bar pct={a.agreed_pct} tone="teal" width={160} label={`@${a.handle} agreement rate`} />
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
