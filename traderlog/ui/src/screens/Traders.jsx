// TRADERS — WIREFRAMES.md §2
import React from "react";
import { fetchTrader, fetchTraders } from "../api.js";
import {
  Chip, ErrorBox, Loading, Num, Panel, fmtDate, useApi,
} from "../components/ui.jsx";
import { Dumbbell, StackedStrip, StripPlot } from "../components/charts.jsx";

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
  const tiltSegments = tiltTop.slice(0, 3).map(([sector, v]) => ({ label: sector, value: v }));
  const tiltRest = tiltTop.slice(3).reduce((sum, [, v]) => sum + v, 0);
  if (tiltRest > 0) tiltSegments.push({ label: `+${tiltTop.length - 3} more`, value: tiltRest });

  const stopStatedPct = pct(s?.stop_stated_pct);
  const stopHonoredPct = pct(s?.stop_honored_pct);
  const dumbbellRows =
    stopStatedPct != null && stopHonoredPct != null
      ? [{ label: "stop discipline", a: { value: stopStatedPct, label: "stated" }, b: { value: stopHonoredPct, label: "honoured" } }]
      : [];

  const holdDays = (data.closed || [])
    .map((p) => p.holding_days)
    .filter((v) => v !== null && v !== undefined);

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
              {/* The one serif hero number on this screen (VISUAL_LANGUAGE.md §4) --
                  the headline stated-win-rate claim, which the rest of the panel
                  either supports or complicates. */}
              <div className="n hero-serif">
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
          {/* n from trader_style.n_positions -- a stop-discipline percentage
              over four positions and over four hundred are different claims,
              and §1 forbids showing one without saying which. */}
          <Dumbbell
            rows={dumbbellRows} max={100} gapWarn={10} suffix="%"
            n={s.n_positions ?? null}
          />
          {stopStatedPct != null && stopHonoredPct != null && stopStatedPct > stopHonoredPct && (
            <div className="interpret">
              the {stopStatedPct - stopHonoredPct}pt gap = stops quietly widened, not hit
            </div>
          )}

          <div className="sub-label">Hold days</div>
          <StripPlot values={holdDays} median={s.median_hold_days ? Math.round(s.median_hold_days) : undefined} suffix="d" />

          <div className="sub-label">Where they play</div>
          <StackedStrip segments={tiltSegments} n={s.n_positions ?? null} suffix="%" />
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
