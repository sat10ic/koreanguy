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

// One item in the `.be-row` ratio line. Band colour stays — RED/WHITE/GREEN
// is a measured state, not an undifferentiated category (unlike the chips).
function Ratio({ k, v, band }) {
  return (
    <span className={`be-ratio b-${band || "none"}`}>
      <span className="k">{k}</span>
      <span className="v">{v == null ? "—" : Math.round(v)}</span>
      <span className={`b color-${band}`}>{band || "no data"}</span>
    </span>
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
            {/* ONE understated evidence block replaces the three dial tiles and
                the ratio row: labelled ledger rows under hairlines. Same data —
                XP value+band, MBI colour+score+warning flag, the four ratios.
                XP keeps the screen's single dominant number (VISUAL_LANGUAGE
                §4) with no dial/gauge frame; nothing else on the screen competes. */}
            <div className="breadth-evidence">
              <div className="be-row">
                <span className="be-k">XP</span>
                <span className="be-v be-v-dominant mono">{t.xp_value?.toFixed(1)}</span>
                <span className="be-band">{t.xp_band}</span>
                <span className="be-cap">bands 15 / 40 / 100</span>
              </div>
              <div className="be-row">
                <span className="be-k">MBI</span>
                <span className={`be-v color-${t.mbi_day_color}`}>{t.mbi_day_color}</span>
                <span className="be-cap">score {t.mbi_score} of 4 bands</span>
                {t.warning_day ? (
                  <span className="warn-flag">⚠ warning day</span>
                ) : (
                  <span className="unstated">no warning</span>
                )}
                <span className="be-cap">warning = 3 or more bands red</span>
              </div>
              <div className="be-row">
                <Ratio k="r10" v={t.r10} band={t.band_r10} />
                <Ratio k="r20" v={t.r20} band={t.band_r20} />
                <Ratio k="r50" v={t.r50} band={t.band_r50} />
                <Ratio k="r4.5" v={t.r4p5} band={t.band_r4p5} />
              </div>
              <div className="be-note">
                r50 uses its own 85 / 60 cutoffs; r10 and r20 use 75 / 50.
                Taken from the adopted module rather than re-derived.
              </div>
            </div>
          </>
        )}
      </Panel>

      <Panel title={`MBI day colour · last ${data.history.length} sessions`}>
        {/* Slice C: with zero history the whole panel is future-wave — ONE
            compact block instead of the Ribbon's empty frame with a legend
            floating over nothing. Keep the chart whenever any history
            exists; its internal compact empty handles a partial series. */}
        {data.history.length === 0 ? (
          <p className="future-block">
            MBI day-colour history is unavailable — no market-internals
            sessions have been captured. Breadth history is provided by W4's
            adopted bhavcopy/breadth ingest.
          </p>
        ) : (
          <>
            <Ribbon cells={ribbonCells} />
            <div className="legend">
              <span><i style={{ background: "var(--ok)" }} />green</span>
              <span><i style={{ background: "var(--surface-3)" }} />white</span>
              <span><i style={{ background: "var(--bad)" }} />red</span>
              <span>· dot above = warning day (3+ red bands)</span>
            </div>
          </>
        )}
      </Panel>

      <Panel title="XP trend · 90d">
        {/* Slice C: same future-wave judgement as the MBI panel above — zero
            history means the panel has no real data, so the BandLine's empty
            frame would dominate it. ONE compact block instead. With any real
            history the BandLine stays (its compact empty remains valid for a
            partial series). */}
        {data.history.length === 0 ? (
          <p className="future-block">
            XP trend history is unavailable — no market-internals sessions
            have been captured. Breadth history is provided by W4's adopted
            bhavcopy/breadth ingest.
          </p>
        ) : (
          <BandLine points={xpPoints} bands={XP_BANDS} log />
        )}
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
                <th className="sentence">XP / MBI that day</th>
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
