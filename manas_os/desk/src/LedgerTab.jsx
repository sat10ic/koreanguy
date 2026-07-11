import React, { useEffect, useState } from "react";
import { fetchTrackRecord, fetchLessons, fetchJournal } from "./api.js";
import { Term } from "./Glossary.jsx";
import { useDensity } from "./DensityContext.jsx";
import { SectionLabel, Panel } from "./components/v5/index.js";
import "./LedgerTab.v5.css";

// ------------------------------------------------------------------
// DEMO FIXTURES — turn this to false to restore the honest live fetch.
// Purpose: exercise every JOURNAL state (closed win/loss, open trade, drawn
// equity curve, populated stats, proven + building-sample cohorts, lessons +
// digest) for visual verification. These payloads mirror the shapes the real
// endpoints return (/api/journal, /api/desk/track-record, /api/desk/lessons);
// flip USE_DEMO_DATA to false to resume the real Promise.all.
// ------------------------------------------------------------------
const USE_DEMO_DATA = false;

const DEMO_JOURNAL = {
  available: true,
  // newest-first, matching the live payload order
  trades: [
    {
      trade_id: 12, trade_date: "2026-07-09", symbol: "HUDCO", setup: "Pullback-to-EMA",
      entry: 218.0, exit: null, stop: 210.84, r_result: null,
      notes: "auto-captured from setups", created_at: "2026-07-09 19:35:11",
      exit_date: null, mistake_tags: [], result: "open", mfe_r: 0.74, mae_r: -0.31,
    },
    {
      trade_id: 11, trade_date: "2026-07-07", symbol: "MAZDOCK", setup: "IPO-Base",
      entry: 412.0, exit: 455.2, stop: 398.0, r_result: 3.31,
      notes: "broke out of 3-week base on volume", created_at: "2026-07-07 10:05:00",
      exit_date: "2026-07-09", mistake_tags: ["clean-hit"], result: "win",
    },
    {
      trade_id: 10, trade_date: "2026-07-04", symbol: "INFY", setup: "Pullback-to-EMA",
      entry: 1582.0, exit: 1561.0, stop: 1556.0, r_result: -2.1,
      notes: "ema support failed, gap down next session", created_at: "2026-07-04 09:40:00",
      exit_date: "2026-07-05", mistake_tags: ["wrong-process-win"], result: "loss",
    },
    {
      trade_id: 9, trade_date: "2026-07-02", symbol: "TATACHEM", setup: "Base/Pattern",
      entry: 940.0, exit: 1018.0, stop: 912.0, r_result: 2.78,
      notes: "cup-and-handle continuation", created_at: "2026-07-02 11:15:00",
      exit_date: "2026-07-08", mistake_tags: ["clean-hit"], result: "win",
    },
    {
      trade_id: 8, trade_date: "2026-06-30", symbol: "DLF", setup: "Breakout",
      entry: 612.0, exit: 601.0, stop: 596.0, r_result: -1.0,
      notes: "low-volume breakout, faded immediately", created_at: "2026-06-30 14:20:00",
      exit_date: "2026-07-01", mistake_tags: ["right-process-loss"], result: "loss",
    },
  ],
  // 4 closed trades: 2 wins (+3.31, +2.78), 2 losses (-2.1, -1.0).
  // win_pct = 50, avg_r = (3.31+2.78-2.1-1.0)/4 = +0.75, expectancy same.
  stats: { count: 5, win_pct: 50.0, avg_r: 0.75, expectancy_r: 0.75, top_mistake: "wrong-process-win" },
};

const DEMO_TRACK_RECORD = {
  records: [
    { agent: "Manas-v4", family: "base/pattern", hit_rate: 0.61, avg_r: 0.82, n: 44, thin: false },
    { agent: "Manas-v4", family: "catalyst", hit_rate: 0.33, avg_r: -0.4, n: 6, thin: true },
    { agent: "Manas-v3", family: "base/pattern", hit_rate: 0.54, avg_r: 0.41, n: 88, thin: false },
  ],
  expectancy: [
    {
      family: "base/pattern", regime: "SELECTIVE",
      passed: { n: 24, hit_rate: 0.0, mean_r: -1.263, median_r: -1.107, trust: "directional", unproven: false },
      refused: { n: 19065, hit_rate: 0.479, mean_r: 0.303, median_r: -0.313, trust: "operational", unproven: false },
    },
    {
      family: "catalyst", regime: "DEFENSIVE",
      passed: { n: 5, hit_rate: 0.0, mean_r: -1.619, median_r: -1.158, trust: "descriptive", unproven: true },
      refused: { n: 256, hit_rate: 0.512, mean_r: 0.577, median_r: 0.334, trust: "operational", unproven: false },
    },
    {
      family: "catalyst", regime: "SELECTIVE",
      passed: { n: 29, hit_rate: 0.0, mean_r: -1.132, median_r: -1.063, trust: "directional", unproven: false },
      refused: { n: 1436, hit_rate: 0.533, mean_r: 1.584, median_r: 0.455, trust: "operational", unproven: false },
    },
  ],
  screener_calibration: [
    {
      screener: "vcp", horizon: 10, n: 1, avg_excess_pct: 0.646, median_excess_pct: 0.646,
      win_rate: 1.0, baseline_win_rate: 0.0, baseline_n: 0, as_of: "2026-07-10", unproven: true,
    },
    {
      screener: "ema-pullback", horizon: 10, n: 62, avg_excess_pct: 1.84, median_excess_pct: 0.92,
      win_rate: 0.58, baseline_win_rate: 0.47, baseline_n: 240, as_of: "2026-07-10", unproven: false,
    },
  ],
};

const DEMO_LESSONS = {
  lessons: [
    {
      filename: "2026-07-09_mazdock.md", tag: "clean-hit",
      first_line: "Patience on the 3-week base paid off — waited for the volume confirmation, not the first touch.",
    },
    {
      filename: "2026-07-04_infy.md", tag: "wrong-process-win",
      first_line: "Took partial profit early out of fear; if the thesis was right, the exit was wrong.",
    },
    {
      filename: "2026-06-30_dlf.md", tag: "right-process-loss",
      first_line: "Low-volume breakout was a valid setup that failed — process was right, outcome wasn't.",
    },
  ],
  digest:
    "Week of 2026-07-04:\n" +
    "- Win rate 50% but expectancy +0.75R — winners ran, losers were cut.\n" +
    "- 'wrong-process-win' on INFY is the recurring mistake to watch.\n" +
    "- Catalyst setups still thin (n=6); keep size small until n>20.",
};

// ------------------------------------------------------------------
// pure helpers (real payload only -- no synthetic fill anywhere)
// ------------------------------------------------------------------

function round(n, digits = 1) {
  if (n === null || n === undefined) return "—";
  const f = Math.pow(10, digits);
  return Math.round(n * f) / f;
}

// Server-implied trust floor for the "passed" (taken) cohort. The expectancy
// payload's own `unproven` field is authoritative -- this is only the legacy
// n<20 floor that applied before `unproven` existed, kept so a cohort that
// reports `unproven:false` but tiny n still reads as building.
const TRUST_FLOOR_N = 20;

function familyLabel(family) {
  return (family || "unknown").replace(/[/_]/g, " ").toUpperCase();
}

// Plain-language evidence status from the real `trust` + `unproven` fields.
// `unproven` is authoritative; `trust` is additive color language.
function trustStatus(cell) {
  if (!cell || !cell.n) return { label: "no sample", tone: "mute" };
  if (cell.unproven || cell.n < TRUST_FLOOR_N) {
    return { label: "building sample", tone: "amber" };
  }
  const t = cell.trust;
  if (t === "operational") return { label: "operational", tone: "green" };
  if (t === "directional") return { label: "directional", tone: "teal" };
  if (t === "descriptive") return { label: "descriptive", tone: "mute" };
  return { label: "measured", tone: "teal" };
}

// ------------------------------------------------------------------
// Personal journal: stat rail
// ------------------------------------------------------------------

// A single cardless stat tile. Null/undefined value renders an honest "--"
// with a title explaining why -- the whole point on a thin journal.
function StatTile({ label, value, title, children }) {
  const isDash = value === null || value === undefined || value === "—";
  return (
    <div className={"v5-jr-stat" + (isDash ? " v5-jr-stat-empty" : "")}>
      <span className="v5-jr-stat-lbl">{label}</span>
      <span className="v5-jr-stat-val mono-num" title={title || (isDash ? "not enough closed trades yet" : undefined)}>
        {isDash ? "—" : value}
      </span>
      {children}
    </div>
  );
}

// Small win/loss ratio bar. With 0 closed trades this renders null (the parent
// guards on closedCount), so it never fakes a split.
function WinLossBar({ wins, losses }) {
  const total = wins + losses;
  if (total === 0) return null;
  const winPct = (wins / total) * 100;
  return (
    <div className="v5-jr-winloss" title={`${wins} win / ${losses} loss`}>
      <div className="v5-jr-winloss-win" style={{ width: `${winPct}%` }} />
      <div className="v5-jr-winloss-loss" style={{ width: `${100 - winPct}%` }} />
    </div>
  );
}

function StatRail({ stats, closedCount, wins, losses }) {
  return (
    <div className="v5-jr-stat-rail">
      <StatTile label="Trades" value={stats.count} title={stats.count ? `${stats.count} trade(s) on record` : "no trades yet"} />
      <StatTile
        label={<Term k="hit-rate">Win %</Term>}
        value={stats.win_pct !== null && stats.win_pct !== undefined ? `${round(stats.win_pct, 0)}%` : null}
        title="win rate needs closed trades to compute"
      >
        {closedCount > 0 && <WinLossBar wins={wins} losses={losses} />}
      </StatTile>
      <StatTile
        label={<Term k="avg-r">Avg R</Term>}
        value={round(stats.avg_r, 2)}
        title="average R needs closed trades to compute"
      />
      <StatTile
        label={<Term k="stage-expectancy">Expectancy</Term>}
        value={round(stats.expectancy_r, 2)}
        title="expectancy (R per trade) needs closed trades to compute"
      />
      {stats.top_mistake && (
        <StatTile
          label="Top mistake"
          value={stats.top_mistake}
          title="most frequent mistake tag across closed trades"
        />
      )}
    </div>
  );
}

// ------------------------------------------------------------------
// Personal journal: equity curve (pure inline SVG, honest empty state)
// ------------------------------------------------------------------

// Cumulative-R equity curve. `closedTrades` must be chronological (oldest
// first). Below 2 closed points we cannot draw a line, so we say so plainly
// rather than fake a flat one. No synthetic series ever.
function EquityCurve({ closedTrades }) {
  if (!closedTrades || closedTrades.length < 2) {
    return (
      <div className="v5-jr-equity-empty">
        <span className="v5-jr-equity-empty-icon" aria-hidden="true">◌</span>
        <p className="v5-jr-equity-empty-line">Not enough closed trades yet.</p>
        <p className="v5-jr-equity-empty-sub">
          The equity curve appears from your second closed trade. Right now every trade on
          the journal is still open, so there is no R path to draw.
        </p>
      </div>
    );
  }
  let running = 0;
  const cumulative = closedTrades.map((t) => {
    running += Number(t.r_result) || 0;
    return running;
  });
  const min = Math.min(...cumulative, 0);
  const max = Math.max(...cumulative, 0);
  const span = max - min || 1;
  const W = 100;
  const H = 28;
  const stepX = W / (cumulative.length - 1);
  const pts = cumulative
    .map((v, i) => {
      const x = i * stepX;
      const y = H - ((v - min) / span) * H;
      return `${x.toFixed(2)},${y.toFixed(2)}`;
    })
    .join(" ");
  const last = cumulative[cumulative.length - 1];
  const up = last >= 0;
  const stroke = up ? "var(--v5-green)" : "var(--v5-red)";
  const zeroY = H - ((0 - min) / span) * H;
  return (
    <div className="v5-jr-equity-wrap">
      <svg className="v5-jr-equity-svg" viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" role="img" aria-label={`cumulative R ${up ? "up" : "down"} ${round(last, 1)}R`}>
        <line x1="0" y1={zeroY.toFixed(2)} x2={W} y2={zeroY.toFixed(2)} className="v5-jr-equity-zero" />
        <polyline points={pts} fill="none" stroke={stroke} strokeWidth="1.4" strokeLinejoin="round" strokeLinecap="round" />
      </svg>
      <div className="v5-jr-equity-readout">
        <span className="v5-jr-equity-readout-lbl">cumulative R</span>
        <span className={"v5-jr-equity-readout-val mono-num " + (up ? "v5-jr-pos" : "v5-jr-neg")}>
          {up ? "+" : ""}
          {round(last, 1)}R
        </span>
      </div>
    </div>
  );
}

// ------------------------------------------------------------------
// Personal journal: trade history
// ------------------------------------------------------------------

// Zero-anchored horizontal bar for a single trade's R. Green right of center
// for wins, red left of center for losses, "open" label when r_result is null.
// Never animates (a11y §5: motion never marks R).
function RBar({ r }) {
  if (r === null || r === undefined) {
    return <span className="v5-jr-r-open mono-num">open</span>;
  }
  const capAt = 5;
  const pct = Math.min(Math.abs(r), capAt) / capAt * 50; // half-track max
  const up = r >= 0;
  const style = {
    width: `${pct}%`,
    background: up ? "var(--v5-green)" : "var(--v5-red)",
    ...(up ? { left: "50%" } : { right: "50%" }),
  };
  return (
    <div className="v5-jr-r-bar">
      <div className="v5-jr-r-bar-mid" />
      <div className={"v5-jr-r-bar-fill " + (up ? "v5-jr-pos" : "v5-jr-neg")} style={style} />
      <span className={"v5-jr-r-bar-val mono-num " + (up ? "v5-jr-pos" : "v5-jr-neg")}>
        {up ? "+" : ""}
        {round(r, 1)}R
      </span>
    </div>
  );
}

function reasonFor(trade) {
  if (trade.mistake_tags && trade.mistake_tags.length > 0) return trade.mistake_tags.join(", ");
  if (trade.result === "open") return "—";
  return trade.result === "win" ? "sold into strength" : "stopped out";
}

function TradeHistoryTable({ trades }) {
  return (
    <div className="v5-jr-table-wrap">
      <table className="v5-jr-table">
        <thead>
          <tr>
            <th>Date</th>
            <th>Symbol</th>
            <th>Setup</th>
            <th>Entry</th>
            <th>Exit</th>
            <th>R</th>
            <th>Reason</th>
          </tr>
        </thead>
        <tbody>
          {trades.map((t) => (
            <tr key={t.trade_id}>
              <td className="mono-num">{t.trade_date}</td>
              <td><span className="v5-jr-sym">{t.symbol}</span></td>
              <td>{(t.setup || "—").replace(/[/_]/g, " ")}</td>
              <td className="mono-num">{t.entry ?? "—"}</td>
              <td className="mono-num">{t.exit ?? (t.result === "open" ? "open" : "—")}</td>
              <td><RBar r={t.r_result} /></td>
              <td>{reasonFor(t)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// The whole personal-journal section. `journal.trades` is newest-first; the
// equity curve reads chronologically so we reverse a copy for that one path.
function JournalSection({ journal }) {
  const stats = (journal && journal.stats) || {};
  const trades = (journal && journal.trades) || [];
  const chronological = [...trades].reverse();
  const closedChronological = chronological.filter(
    (t) => t.r_result !== null && t.r_result !== undefined
  );
  const wins = closedChronological.filter((t) => t.r_result > 0).length;
  const losses = closedChronological.filter((t) => t.r_result <= 0).length;

  return (
    <>
      <SectionLabel count={`${stats.count ?? trades.length} on record`}>Trade journal — your edge</SectionLabel>

      <StatRail stats={stats} closedCount={closedChronological.length} wins={wins} losses={losses} />

      <div className="v5-jr-equity-block">
        <div className="v5-jr-subhead">Equity curve (cumulative R)</div>
        <EquityCurve closedTrades={closedChronological} />
      </div>

      <div className="v5-jr-history-block">
        <div className="v5-jr-subhead">Trade history</div>
        <TradeHistoryTable trades={trades} />
      </div>
    </>
  );
}

// ------------------------------------------------------------------
// SYSTEM EDGE (advanced) -- secondary, progressive disclosure
// ------------------------------------------------------------------

// One cohort cell for the expectancy table. The `unproven` field is
// authoritative; n<20 is the legacy floor. Thin samples read as building,
// never as green/proven.
function CohortCell({ cell, unit }) {
  if (!cell || !cell.n) {
    return <span className="v5-jr-cohort v5-jr-cohort-empty mono-num" title="no sample for this cohort">—</span>;
  }
  const st = trustStatus(cell);
  if (cell.unproven || cell.n < TRUST_FLOOR_N) {
    return (
      <span className="v5-jr-cohort v5-jr-cohort-thin">
        <span className={"v5-jr-status v5-jr-status-" + st.tone}>{st.label}</span>
        <span className="v5-jr-cohort-n mono-num">n={cell.n}</span>
      </span>
    );
  }
  const pct = round((cell.hit_rate || 0) * 100, 0);
  const avg = round(cell.mean_r ?? cell.median_r, 2);
  const sign = avg >= 0 ? "+" : "";
  if (unit === "pct") {
    // Refused: no stop was set, so this is a raw %-return baseline, not R.
    return (
      <span className="v5-jr-cohort">
        <span className={"v5-jr-status v5-jr-status-" + st.tone}>{st.label}</span>
        <span className="v5-jr-cohort-n mono-num">n={cell.n}</span>
        <span className="v5-jr-cohort-metric mono-num">
          win {pct}% · avg {sign}
          {avg}% <span className="v5-jr-cohort-note">(no stop set)</span>
        </span>
      </span>
    );
  }
  return (
    <span className="v5-jr-cohort">
      <span className={"v5-jr-status v5-jr-status-" + st.tone}>{st.label}</span>
      <span className="v5-jr-cohort-n mono-num">n={cell.n}</span>
      <span className="v5-jr-cohort-metric mono-num">
        hit {pct}% · avg {sign}
        {avg}R
      </span>
    </span>
  );
}

function ExpectancyTable({ rows }) {
  if (!rows || rows.length === 0) {
    return (
      <div className="v5-jr-empty">
        <span className="v5-jr-empty-icon" aria-hidden="true">◌</span>
        <p className="v5-jr-empty-line">No system expectancy cells yet.</p>
        <p className="v5-jr-empty-sub">
          Runs the replay across history and persists per-family passed vs refused cohorts —
          nothing has been persisted yet.
        </p>
      </div>
    );
  }
  return (
    <div className="v5-jr-table-wrap">
      <table className="v5-jr-table v5-jr-table-cohort">
        <thead>
          <tr>
            <th>Family</th>
            <th>Regime</th>
            <th>Passed (taken)</th>
            <th>Refused (near-miss)</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={`${r.family}-${r.regime}`}>
              <td>{familyLabel(r.family)}</td>
              <td>{r.regime}</td>
              <td><CohortCell cell={r.passed} unit="r" /></td>
              <td><CohortCell cell={r.refused} unit="pct" /></td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="v5-jr-caption">
        System loop: every persisted candidate's forward return at T+10, whether taken or not —
        proves or kills the setup family over time, independent of any one trade.
      </p>
    </div>
  );
}

function TrackRecordTable({ records }) {
  if (!records || records.length === 0) {
    return (
      <div className="v5-jr-empty">
        <span className="v5-jr-empty-icon" aria-hidden="true">◌</span>
        <p className="v5-jr-empty-line">No closed agent outcomes yet.</p>
        <p className="v5-jr-empty-sub">
          Track records and lessons fill in as trades resolve — nothing to show yet, that's the
          current reality, not a broken panel.
        </p>
      </div>
    );
  }
  return (
    <div className="v5-jr-table-wrap">
      <table className="v5-jr-table">
        <thead>
          <tr>
            <th>Agent</th>
            <th>Family</th>
            <th>Hit</th>
            <th>Avg R</th>
            <th>n</th>
          </tr>
        </thead>
        <tbody>
          {records.map((r) => (
            <tr key={`${r.agent}-${r.family}`} className={r.thin ? "v5-jr-thin-row" : ""}>
              <td><span className="v5-jr-sym" title={r.agent}>{r.agent}</span></td>
              <td>{familyLabel(r.family)}</td>
              <td className="mono-num">
                {r.n ? `${round((r.hit_rate || 0) * r.n, 0)}/${r.n}` : "—"}
                {r.hit_rate !== null && r.hit_rate !== undefined ? ` (${round(r.hit_rate * 100, 0)}%)` : ""}
              </td>
              <td className="mono-num">{round(r.avg_r, 1)}</td>
              <td className="mono-num">
                {r.n}
                {r.thin && <span className="v5-jr-thin-note"> building sample</span>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ScreenerCalibrationTable({ rows }) {
  if (!rows || rows.length === 0) {
    return (
      <div className="v5-jr-empty">
        <span className="v5-jr-empty-icon" aria-hidden="true">◌</span>
        <p className="v5-jr-empty-line">No screener calibration yet.</p>
        <p className="v5-jr-empty-sub">
          Runs nightly against screener hits — nothing has been persisted yet.
        </p>
      </div>
    );
  }
  return (
    <div className="v5-jr-table-wrap">
      <table className="v5-jr-table">
        <thead>
          <tr>
            <th>Screener</th>
            <th>n</th>
            <th>Avg excess (T+10)</th>
            <th>Median excess</th>
            <th>Win %</th>
            <th>Baseline win %</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.screener} className={r.unproven ? "v5-jr-thin-row" : ""}>
              <td>{r.screener}</td>
              <td className="mono-num">
                {r.n}
                {r.unproven && <span className="v5-jr-thin-note"> n&lt;30 — building sample</span>}
              </td>
              <td className={"mono-num " + (r.avg_excess_pct >= 0 ? "v5-jr-pos" : "v5-jr-neg")}>
                {r.avg_excess_pct >= 0 ? "+" : ""}
                {round(r.avg_excess_pct, 2)}%
              </td>
              <td className={"mono-num " + (r.median_excess_pct >= 0 ? "v5-jr-pos" : "v5-jr-neg")}>
                {r.median_excess_pct >= 0 ? "+" : ""}
                {round(r.median_excess_pct, 2)}%
              </td>
              <td className="mono-num">{round(r.win_rate * 100, 0)}%</td>
              <td className="mono-num">{round(r.baseline_win_rate * 100, 0)}%</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="v5-jr-caption">
        Screeners ranked by whether their picks actually went up afterwards.
      </p>
    </div>
  );
}

// ------------------------------------------------------------------
// Lessons diary + digest (always visible, outside the disclosure)
// ------------------------------------------------------------------

const TAG_LABELS = {
  "clean-hit": "clean hit",
  "clean-miss": "clean miss",
  "right-process-loss": "right process, loss",
  "wrong-process-win": "wrong process, win",
};

function TagPill({ tag }) {
  if (!tag) return <span className="v5-jr-tag v5-jr-tag-none">untagged</span>;
  return <span className={"v5-jr-tag v5-jr-tag-" + tag}>{TAG_LABELS[tag] || tag}</span>;
}

function LessonsDiary({ lessons, digest }) {
  const hasLessons = lessons && lessons.length > 0;
  const hasDigest = digest && digest.trim().length > 0;
  return (
    <>
      <SectionLabel>Lessons diary</SectionLabel>
      <div className="v5-jr-lessons-grid">
        <Panel title="Lessons diary" cite="from ~/.manas/lessons">
          {hasLessons ? (
            <div className="v5-jr-lessons-list">
              {lessons.map((l) => (
                <div key={l.filename} className="v5-jr-lesson-row">
                  <span className="v5-jr-lesson-fn mono-num">{l.filename}</span>
                  <TagPill tag={l.tag} />
                  <p className="v5-jr-lesson-preview">{l.first_line || "—"}</p>
                </div>
              ))}
            </div>
          ) : (
            <div className="v5-jr-empty">
              <span className="v5-jr-empty-icon" aria-hidden="true">◌</span>
              <p className="v5-jr-empty-line">No lessons written yet.</p>
              <p className="v5-jr-empty-sub">
                Lessons accumulate once trades close and the desk reflects on them.
              </p>
            </div>
          )}
        </Panel>

        <Panel title="What the desk carries forward" cite="digest">
          {hasDigest ? (
            <pre className="v5-jr-digest">{digest}</pre>
          ) : (
            <div className="v5-jr-empty">
              <span className="v5-jr-empty-icon" aria-hidden="true">◌</span>
              <p className="v5-jr-empty-line">No digest in force yet.</p>
              <p className="v5-jr-empty-sub">
                Nothing has been distilled to carry forward.
              </p>
            </div>
          )}
        </Panel>
      </div>
    </>
  );
}

// ------------------------------------------------------------------
// Root component
// ------------------------------------------------------------------

export default function LedgerTab() {
  const [trackRecord, setTrackRecord] = useState(null);
  const [lessons, setLessons] = useState(null);
  const [journal, setJournal] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const { isExpert } = useDensity();
  const [systemEdgeOpen, setSystemEdgeOpen] = useState(isExpert);

  // Expert mode auto-expands SYSTEM EDGE (advanced); beginner keeps it
  // collapsed by default but a manual toggle still overrides either way until
  // the next density change.
  useEffect(() => {
    setSystemEdgeOpen(isExpert);
  }, [isExpert]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    // DEMO FIXTURES: when USE_DEMO_DATA is true, skip the network entirely and
    // load the hypothetical payloads defined at the top of this file. Flip the
    // flag to false to resume the honest live Promise.all.
    const load = USE_DEMO_DATA
      ? Promise.resolve([DEMO_TRACK_RECORD, DEMO_LESSONS, DEMO_JOURNAL])
      : Promise.all([fetchTrackRecord(), fetchLessons(), fetchJournal()]);
    load
      .then(([tr, ls, jr]) => {
        if (cancelled) return;
        setTrackRecord(tr);
        setLessons(ls);
        setJournal(jr);
      })
      .catch((err) => {
        if (!cancelled) setError(String(err));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (loading) {
    return <div className="v5-journal v5-jr-loading">Loading…</div>;
  }
  if (error) {
    return (
      <div className="v5-journal v5-jr-error">
        <span className="v5-jr-empty-icon" aria-hidden="true">⚠</span>
        <p className="v5-jr-empty-line">Could not load the ledger.</p>
        <p className="v5-jr-empty-sub">{error}</p>
      </div>
    );
  }

  const records = (trackRecord && trackRecord.records) || [];
  const expectancyRows = (trackRecord && trackRecord.expectancy) || [];
  const screenerCalibrationRows = (trackRecord && trackRecord.screener_calibration) || [];
  const lessonItems = (lessons && lessons.lessons) || [];
  const digest = lessons && lessons.digest;
  const hasJournal = journal && journal.available && journal.trades && journal.trades.length > 0;

  return (
    <div className="v5-journal">
      {hasJournal ? (
        <JournalSection journal={journal} />
      ) : (
        <>
          <SectionLabel>Trade journal — your edge</SectionLabel>
          <div className="v5-jr-empty">
            <span className="v5-jr-empty-icon" aria-hidden="true">◌</span>
            <p className="v5-jr-empty-line">No journal trades yet.</p>
            <p className="v5-jr-empty-sub">
              The journal starts the first time a setup is captured or a trade is logged.
            </p>
          </div>
        </>
      )}

      <SectionLabel count="advanced">
        <button
          type="button"
          className="v5-jr-disclosure"
          aria-expanded={systemEdgeOpen}
          onClick={() => setSystemEdgeOpen((o) => !o)}
        >
          <span className="v5-jr-disclosure-mark" aria-hidden="true">{systemEdgeOpen ? "▾" : "▸"}</span>
          SYSTEM EDGE (advanced)
        </button>
      </SectionLabel>

      {systemEdgeOpen && (
        <div className="v5-jr-disclosure-body">
          <Panel title="System expectancy (setup families)" cite="TradeTM teaches this">
            <ExpectancyTable rows={expectancyRows} />
          </Panel>

          <Panel title="Agent track records" cite="Manas measured">
            <TrackRecordTable records={records} />
          </Panel>

          <Panel title="Which screeners predict" cite="T+10 forward return">
            <ScreenerCalibrationTable rows={screenerCalibrationRows} />
          </Panel>
        </div>
      )}

      <LessonsDiary lessons={lessonItems} digest={digest} />
    </div>
  );
}
