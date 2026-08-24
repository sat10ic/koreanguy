// TRADERS — WIREFRAMES.md §2
import React from "react";
import { fetchTrader, fetchTraders } from "../api.js";
import {
  Chip, Disclosure, ErrorBox, Loading, Panel, SortableTh, fmtDate, useApi,
} from "../components/ui.jsx";
import { Dumbbell, StackedStrip, StripPlot } from "../components/charts.jsx";

function pct(v) {
  return v === null || v === undefined ? null : Math.round(v * 100);
}

// F7: roster headers were plain <th> -- sortable is the primary interaction
// on a dense table (VISUAL_LANGUAGE §3), and Ledger already sets the pattern.
function sortTraders(rows, key, dir) {
  if (!key) return rows;
  const mul = dir === "asc" ? 1 : -1;
  const get = {
    handle: (t) => t.handle || "",
    tier: (t) => t.tier || "",
    posts: (t) => t.posts,
    open: (t) => t.open_positions,
    closed: (t) => t.closed_positions,
    hold: (t) => t.median_hold_days,
    win: (t) => t.stated_win_rate,
    preach: (t) => t.preach_score,
    last: (t) => t.last_seen_ts,
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

function Profile({ handle, onNavigate }) {
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
      right={<Chip kind={data.trader.tier}>{data.trader.tier.toLowerCase()}</Chip>}
    >
      {/* Slice C: when no trader_style row exists (true for all four production
          traders today) the whole profile is future-wave — ONE compact
          explanatory block. The three chart sub-sections below are skipped
          entirely: their empty frames would stack into the large empty wall
          the evidence-desk revision forbids. */}
      {!s && (
        <p className="future-block">
          Not enough closed, reconciled positions yet to compute a style
          profile. Style profiles arrive with W2 thread reconciliation and the
          W6 derive/style pass.
        </p>
      )}

      {s && (
        /* The 4-equal-KPI grid is gone (VISUAL_LANGUAGE §4). The stated win
           rate stays the ONE dominant number on the screen — size + weight,
           never a dial/frame — and the other three stats read as one
           supporting evidence line with their qualifiers, same data. */
        <div className="profile-lead">
          <div className="lead-win">
            <div className="lead-number">
              {s.stated_win_rate == null ? "—" : `${pct(s.stated_win_rate)}%`}
            </div>
            <div className="lead-label">
              stated win rate — of {data.closed.length} closed
            </div>
          </div>
          <p className="lead-line">
            avg result {s.avg_r ? `${s.avg_r.toFixed(1)}R` : "—"} (where a
            result was stated) · median hold{" "}
            {s.median_hold_days ? `${Math.round(s.median_hold_days)}d` : "—"}{" "}
            (entry to stated exit) · practises what they preach{" "}
            {s.preach_score == null ? "—" : `${pct(s.preach_score)}%`} (linked
            trades only)
          </p>
        </div>
      )}

      {/* F8: these three charts render their OWN labelled empty frame when an
          individual series is missing — but only inside a data-bearing
          profile. When `s` is null the whole profile collapses to the one
          future-block above (Slice C), so this chart block is gated on `s`
          too. dumbbellRows/tiltSegments are already [] when `s` is null, so
          this is the same empty-frame path W6's real data will use. */}
      {s && (
        <>
          <div className="sub-label">Stop discipline</div>
          {/* n from trader_style.n_positions -- a stop-discipline percentage
              over four positions and over four hundred are different claims,
              and §1 forbids showing one without saying which. */}
          <Dumbbell
            rows={dumbbellRows} max={100} gapWarn={10} suffix="%"
            n={s?.n_positions ?? null}
          />
          {stopStatedPct != null && stopHonoredPct != null && stopStatedPct > stopHonoredPct && (
            <div className="interpret">
              the {stopStatedPct - stopHonoredPct}pt gap = stops quietly widened, not hit
            </div>
          )}

          <div className="sub-label">Hold days</div>
          <StripPlot values={holdDays} median={s?.median_hold_days ? Math.round(s.median_hold_days) : undefined} suffix="d" />

          <div className="sub-label">Where they play</div>
          <StackedStrip segments={tiltSegments} n={s?.n_positions ?? null} suffix="%" />
        </>
      )}

      <div className="sub-label">Open now · {data.open.length}</div>
      {data.open.length === 0 && <p className="empty">Nothing open.</p>}
      <table className="data">
        <tbody>
          {data.open.map((p) => (
            <tr key={p.position_id}>
              <td>
                {/* C2.5: jump to LEDGER pre-filtered to this symbol -- the
                    ledger row this open position resolves to. */}
                <button
                  type="button"
                  className="xlink"
                  onClick={() => onNavigate?.("LEDGER", { symbol: p.symbol })}
                >
                  <strong>{p.symbol}</strong>
                </button>
              </td>
              <td>{p.status}</td>
              {/* Never render a bare "d". A null hold time is "not stated",
                  the same as every other unstated value in this app. */}
              <td className="num">
                {p.holding_days != null ? `${p.holding_days}d` : "—"}
              </td>
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

export default function Traders({ presetHandle, onNavigate }) {
  const { data, error } = useApi(fetchTraders, []);
  const [selected, setSelected] = React.useState(() => presetHandle || null);
  const [sortKey, setSortKey] = React.useState(null);
  const [sortDir, setSortDir] = React.useState("asc");

  React.useEffect(() => {
    if (!selected && data?.traders?.length) setSelected(data.traders[0].handle);
  }, [data, selected]);

  function onSort(key) {
    if (sortKey === key) setSortDir(sortDir === "asc" ? "desc" : "asc");
    else {
      setSortKey(key);
      setSortDir("asc");
    }
  }

  const traders = sortTraders(data?.traders || [], sortKey, sortDir);

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
          <p className="empty">
            No traders configured yet. Add tracked handles to start pulling in their
            posts.
          </p>
        )}
        {data?.traders?.length > 0 && (
          <>
            {/* Slice C: WIREFRAMES §2 asks for a small-multiples roster
                graphic above the table, but no per-trader series exists in
                the payload and never can yet — that derivation is W6. The
                evidence-desk revision forbids a large framed empty chart
                here; ONE compact block states what is unavailable and what
                provides it. */}
            <div className="sub-label">Roster trend · small multiples, shared scale</div>
            <p className="future-block">
              Per-trader trend series are unavailable, so the roster graphic
              cannot be drawn yet. They are provided by the W6 style derivation
              over closed positions.
            </p>

            <table className="data">
              <thead>
                <tr>
                  <th aria-hidden="true" />
                  <SortableTh label="handle" active={sortKey === "handle"} dir={sortDir} onClick={() => onSort("handle")} />
                  <SortableTh label="tier" active={sortKey === "tier"} dir={sortDir} onClick={() => onSort("tier")} />
                  <SortableTh label="posts" className="num" active={sortKey === "posts"} dir={sortDir} onClick={() => onSort("posts")} />
                  <SortableTh label="open" className="num" active={sortKey === "open"} dir={sortDir} onClick={() => onSort("open")} />
                  <SortableTh label="closed" className="num" active={sortKey === "closed"} dir={sortDir} onClick={() => onSort("closed")} />
                  <SortableTh label="hold" className="num" active={sortKey === "hold"} dir={sortDir} onClick={() => onSort("hold")} />
                  <SortableTh label="win" className="num" active={sortKey === "win"} dir={sortDir} onClick={() => onSort("win")} />
                  <SortableTh label="preach" className="num" active={sortKey === "preach"} dir={sortDir} onClick={() => onSort("preach")} />
                  <SortableTh label="last seen" className="sentence" active={sortKey === "last"} dir={sortDir} onClick={() => onSort("last")} />
                </tr>
              </thead>
              <tbody>
                {traders.map((t) => (
                  <tr
                    key={t.handle}
                    className={`trader-row${selected === t.handle ? " selected" : ""}`}
                  >
                    <td>
                      {/* C1: a real disclosure caret, keyboard-operable
                          (Enter/Space via the button element), never a bare
                          row click. Only one trader is ever "open" -- the
                          selected one -- so this is a single-open accordion,
                          same shape as Ledger's per-row Disclosure. */}
                      <Disclosure
                        open={selected === t.handle}
                        onToggle={() => setSelected(t.handle)}
                      />
                    </td>
                    <td>
                      <strong>@{t.handle}</strong>
                    </td>
                    <td>
                      <Chip kind={t.tier}>{t.tier.toLowerCase()}</Chip>
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
          </>
        )}
      </Panel>

      {selected && <Profile handle={selected} onNavigate={onNavigate} />}
    </>
  );
}
