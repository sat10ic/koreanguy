import React, { useEffect, useState } from "react";
import { fetchTrackRecord, fetchLessons, fetchJournal } from "./api.js";
import { Term } from "./Glossary.jsx";
import { colorScale, sparklinePoints } from "./viz.js";
import { useDensity } from "./DensityContext.jsx";

function round(n, digits = 1) {
  if (n === null || n === undefined) return "—";
  const f = Math.pow(10, digits);
  return Math.round(n * f) / f;
}

function agentKey(actor) {
  return (actor || "").toLowerCase();
}

const TAG_LABELS = {
  "clean-hit": "clean hit",
  "clean-miss": "clean miss",
  "right-process-loss": "right process, loss",
  "wrong-process-win": "wrong process, win",
};

function TagPill({ tag }) {
  if (!tag) return <span className="spread-badge mono">untagged</span>;
  return <span className={"spread-badge mono tag-pill tag-" + tag}>{TAG_LABELS[tag] || tag}</span>;
}

function TrackRecordTable({ records }) {
  if (!records || records.length === 0) {
    return (
      <div className="empty-state">
        <div className="empty-state-icon">◌</div>
        <p className="empty-state-line">No closed outcomes yet.</p>
        <p className="empty-state-sub">
          Track records and lessons fill in as trades resolve — nothing to show yet, that's the
          current reality, not a broken panel.
        </p>
      </div>
    );
  }
  return (
    <div className="ledger-table-wrap">
      <table className="ledger-table mono">
        <thead>
          <tr>
            <th>Agent</th>
            <th>Family</th>
            <th><Term k="hit-rate">Hit</Term></th>
            <th><Term k="avg-r">Avg R</Term></th>
            <th>n</th>
          </tr>
        </thead>
        <tbody>
          {records.map((r) => (
            <tr key={`${r.agent}-${r.family}`} className={r.thin ? "thin-row" : ""}>
              <td>
                <span className="agent-chip mono" data-agent={agentKey(r.agent)} title={r.agent}>
                  {r.agent}
                </span>
              </td>
              <td>{(r.family || "unknown").replace(/[/_]/g, " ").toUpperCase()}</td>
              <td>
                {r.n ? `${round((r.hit_rate || 0) * r.n, 0)}/${r.n}` : "—"}
                {r.hit_rate !== null && r.hit_rate !== undefined ? ` (${round(r.hit_rate * 100, 0)}%)` : ""}
              </td>
              <td>{round(r.avg_r, 1)}</td>
              <td>
                {r.n}
                {r.thin && <span className="thin-note"> building sample</span>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

const TRUST_FLOOR_N = 20;

function cohortCell(cell, unit) {
  if (!cell || !cell.n) return <span className="mono">—</span>;
  if (cell.n < TRUST_FLOOR_N) {
    return (
      <span className="mono thin-note">
        <Term k="unproven">UNPROVEN</Term> — building sample (n={cell.n})
      </span>
    );
  }
  const pct = round((cell.hit_rate || 0) * 100, 0);
  const avg = round(cell.mean_r ?? cell.median_r, 2);
  const sign = avg >= 0 ? "+" : "";
  if (unit === "pct") {
    // Refused: no stop was set, so this is a raw %-return baseline, not R.
    return (
      <span className="mono">
        n={cell.n} win {pct}% avg {sign}
        {avg}% (no stop set)
      </span>
    );
  }
  return (
    <span className="mono">
      n={cell.n} hit {pct}% avg {sign}
      {avg}R
    </span>
  );
}

function ExpectancyLedger({ rows }) {
  if (!rows || rows.length === 0) {
    return (
      <div className="empty-state">
        <div className="empty-state-icon">◌</div>
        <p className="empty-state-line">No system expectancy cells yet.</p>
        <p className="empty-state-sub">
          Runs the replay across history and persists per-family passed vs refused cohorts —
          nothing has been persisted yet.
        </p>
      </div>
    );
  }
  return (
    <div className="ledger-table-wrap">
      <table className="ledger-table mono">
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
              <td>{(r.family || "unknown").replace(/[/_]/g, " ").toUpperCase()}</td>
              <td>{r.regime}</td>
              <td>{cohortCell(r.passed, "r")}</td>
              <td>{cohortCell(r.refused, "pct")}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="caption-b">[B] System loop: every persisted candidate's forward return at T+10, whether taken or not — proves or kills the setup family over time, independent of any one trade.</p>
    </div>
  );
}

function ScreenerCalibrationPanel({ rows }) {
  if (!rows || rows.length === 0) {
    return (
      <div className="empty-state">
        <div className="empty-state-icon">◌</div>
        <p className="empty-state-line">No screener calibration yet.</p>
        <p className="empty-state-sub">
          Runs nightly against screener_hits — nothing has been persisted yet.
        </p>
      </div>
    );
  }
  return (
    <div className="ledger-table-wrap">
      <table className="ledger-table mono">
        <thead>
          <tr>
            <th><Term k="screener-calibration">Screener</Term></th>
            <th>n</th>
            <th>Avg excess (T+10)</th>
            <th>Median excess</th>
            <th>Win %</th>
            <th><Term k="base-rate">Baseline win %</Term></th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.screener} className={r.unproven ? "thin-row" : ""}>
              <td>{r.screener}</td>
              <td>
                {r.n}
                {r.unproven && <span className="thin-note"> n&lt;30 — building sample</span>}
              </td>
              <td>
                {r.avg_excess_pct >= 0 ? "+" : ""}
                {round(r.avg_excess_pct, 2)}%
              </td>
              <td>
                {r.median_excess_pct >= 0 ? "+" : ""}
                {round(r.median_excess_pct, 2)}%
              </td>
              <td>{round(r.win_rate * 100, 0)}%</td>
              <td>{round(r.baseline_win_rate * 100, 0)}%</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="caption-b">[B] Screeners ranked by whether their picks actually went up afterwards.</p>
    </div>
  );
}

function LessonsDiary({ lessons, digest }) {
  const hasLessons = lessons && lessons.length > 0;
  const hasDigest = digest && digest.trim().length > 0;
  return (
    <>
      <div className="panel ledger-panel">
        <p className="panel-title small-caps">Lessons diary</p>
        {hasLessons ? (
          <div className="lessons-list">
            {lessons.map((l) => (
              <div key={l.filename} className="lesson-row">
                <span className="lesson-filename mono">{l.filename}</span>
                <TagPill tag={l.tag} />
                <p className="lesson-preview">{l.first_line || "—"}</p>
              </div>
            ))}
          </div>
        ) : (
          <div className="empty-state">
            <div className="empty-state-icon">◌</div>
            <p className="empty-state-line">No lessons written yet.</p>
            <p className="empty-state-sub">
              Lessons accumulate once trades close and the desk reflects on them.
            </p>
          </div>
        )}
      </div>

      <div className="panel ledger-panel digest-panel">
        <p className="overline accent">What the desk carries forward</p>
        {hasDigest ? (
          <pre className="digest-text">{digest}</pre>
        ) : (
          <p className="empty-state-sub">No digest in force yet — nothing has been distilled to carry forward.</p>
        )}
      </div>
    </>
  );
}

// T15: cumulative-R equity curve. `trades` must already be in chronological
// order (oldest first). Only closed trades (r_result present) count toward
// the curve; open trades don't move it. Honest empty state below 2 points --
// a single point can't draw a line, so we say so rather than fake a flat one.
function EquityCurve({ closedTrades }) {
  if (!closedTrades || closedTrades.length < 2) {
    return (
      <div className="empty-state equity-curve-empty">
        <p className="empty-state-sub">
          Not enough closed trades yet — the equity curve appears from trade 2.
        </p>
      </div>
    );
  }
  let running = 0;
  const cumulative = closedTrades.map((t) => {
    running += Number(t.r_result) || 0;
    return running;
  });
  const points = sparklinePoints(cumulative, 320, 64);
  if (!points) return null;
  const last = cumulative[cumulative.length - 1];
  const tone = colorScale(last, 5);
  return (
    <div className="equity-curve-wrap">
      <svg viewBox="0 0 320 64" preserveAspectRatio="none" className="equity-curve-svg">
        <line x1="0" y1="63.5" x2="320" y2="63.5" className="equity-curve-baseline" />
        <polyline points={points} className="equity-curve-line" style={{ stroke: tone.color }} />
      </svg>
      <div className="equity-curve-readout mono">
        <span>cumulative R</span>
        <span style={{ color: tone.color }}>{last >= 0 ? "+" : ""}{round(last, 1)}R</span>
      </div>
    </div>
  );
}

// Zero-anchored horizontal bar for a single trade's R -- green right of
// center for wins, red left of center for losses. Reuses viz.js colorScale
// so the color language matches every other R/%% cell in the app.
function RBar({ r }) {
  if (r === null || r === undefined) {
    return <span className="mono thin-note">open</span>;
  }
  const capAt = 5;
  const tone = colorScale(r, capAt);
  const pct = Math.min(Math.abs(r), capAt) / capAt * 50; // half-track max
  const style = {
    width: `${pct}%`,
    background: tone.color,
    ...(r >= 0 ? { left: "50%" } : { right: "50%" }),
  };
  return (
    <div className="r-bar-track">
      <div className="r-bar-mid" />
      <div className={"r-bar-fill " + (r >= 0 ? "r-bar-fill-pos" : "r-bar-fill-neg")} style={style} />
      <span className="r-bar-label mono" style={{ color: tone.color }}>
        {r >= 0 ? "+" : ""}
        {round(r, 1)}R
      </span>
    </div>
  );
}

// Small win/loss ratio bar rendered beside the Win% tile.
function WinLossBar({ wins, losses }) {
  const total = wins + losses;
  if (total === 0) return null;
  const winPct = (wins / total) * 100;
  return (
    <div className="winloss-bar" title={`${wins} win / ${losses} loss`}>
      <div className="winloss-bar-win" style={{ width: `${winPct}%` }} />
      <div className="winloss-bar-loss" style={{ width: `${100 - winPct}%` }} />
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
    <div className="ledger-table-wrap">
      <table className="ledger-table mono">
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
              <td>{t.trade_date}</td>
              <td>
                <span className="agent-chip mono" title={t.symbol}>{t.symbol}</span>
              </td>
              <td>{(t.setup || "—").replace(/[/_]/g, " ")}</td>
              <td>{t.entry ?? "—"}</td>
              <td>{t.exit ?? (t.result === "open" ? "open" : "—")}</td>
              <td><RBar r={t.r_result} /></td>
              <td>{reasonFor(t)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function JournalStrip({ journal }) {
  if (!journal || !journal.available || !journal.trades || journal.trades.length === 0) {
    return (
      <div className="panel ledger-panel">
        <p className="panel-title small-caps">Trade journal</p>
        <div className="empty-state">
          <div className="empty-state-icon">◌</div>
          <p className="empty-state-line">No journal trades yet.</p>
        </div>
      </div>
    );
  }
  const stats = journal.stats || {};
  // journal.trades comes back newest-first (trade_date DESC); the equity
  // curve reads chronologically, so reverse a copy for that one purpose.
  const chronological = [...journal.trades].reverse();
  const closedChronological = chronological.filter(
    (t) => t.r_result !== null && t.r_result !== undefined
  );
  const wins = closedChronological.filter((t) => t.r_result > 0).length;
  const losses = closedChronological.filter((t) => t.r_result <= 0).length;
  return (
    <div className="panel ledger-panel">
      <p className="panel-title small-caps">Trade journal</p>
      <div className="stat-row">
        <div className="stat-tile">
          <span className="stat-tile-label">Trades</span>
          <span className="stat-tile-value mono">{stats.count ?? journal.trades.length}</span>
        </div>
        <div className="stat-tile">
          <span className="stat-tile-label">Win %</span>
          <span className="stat-tile-value mono">
            {stats.win_pct !== null && stats.win_pct !== undefined ? `${round(stats.win_pct, 0)}%` : "—"}
          </span>
          <WinLossBar wins={wins} losses={losses} />
        </div>
        <div className="stat-tile">
          <span className="stat-tile-label"><Term k="avg-r">Avg R</Term></span>
          <span className="stat-tile-value mono">{round(stats.avg_r, 2)}</span>
        </div>
        <div className="stat-tile">
          <span className="stat-tile-label"><Term k="stage-expectancy">Expectancy</Term></span>
          <span className="stat-tile-value mono">{round(stats.expectancy_r, 2)}</span>
        </div>
        {stats.top_mistake && (
          <div className="stat-tile">
            <span className="stat-tile-label">Top mistake</span>
            <span className="stat-tile-value mono">{stats.top_mistake}</span>
          </div>
        )}
      </div>

      <p className="overline accent equity-curve-title">Equity curve (cumulative R)</p>
      <EquityCurve closedTrades={closedChronological} />

      <TradeHistoryTable trades={journal.trades} />
    </div>
  );
}

export default function LedgerTab() {
  const [trackRecord, setTrackRecord] = useState(null);
  const [lessons, setLessons] = useState(null);
  const [journal, setJournal] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const { isExpert } = useDensity();
  const [systemEdgeOpen, setSystemEdgeOpen] = useState(isExpert);

  // T15: expert mode auto-expands SYSTEM EDGE (advanced); beginner keeps it
  // collapsed by default but a manual toggle still overrides either way.
  useEffect(() => {
    setSystemEdgeOpen(isExpert);
  }, [isExpert]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    Promise.all([fetchTrackRecord(), fetchLessons(), fetchJournal()])
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
    return <div className="empty-state">Loading…</div>;
  }
  if (error) {
    return (
      <div className="empty-state">
        <div className="empty-state-icon">⚠</div>
        <p className="empty-state-line">Could not load the ledger.</p>
        <p className="empty-state-sub">{error}</p>
      </div>
    );
  }

  const records = (trackRecord && trackRecord.records) || [];
  const expectancyRows = (trackRecord && trackRecord.expectancy) || [];
  const screenerCalibrationRows = (trackRecord && trackRecord.screener_calibration) || [];
  const lessonItems = (lessons && lessons.lessons) || [];
  const digest = lessons && lessons.digest;

  // T8: TRADE JOURNAL is what the user acts on tonight -- it now renders
  // first. System expectancy / screener calibration / agent track records
  // are historical proof-of-system tables, useful but secondary; they move
  // below the journal behind a closed-by-default "SYSTEM EDGE (advanced)"
  // disclosure. All existing empty-state copy is unchanged, only reordered.
  return (
    <div className="ledger-tab">
      <JournalStrip journal={journal} />

      <button
        type="button"
        className="disclosure-toggle"
        onClick={() => setSystemEdgeOpen((o) => !o)}
      >
        {systemEdgeOpen ? "▾" : "▸"} SYSTEM EDGE (advanced)
      </button>
      {systemEdgeOpen && (
        <div className="disclosure-body">
          <div className="panel ledger-panel">
            <p className="panel-title small-caps">System expectancy (setup families)</p>
            <ExpectancyLedger rows={expectancyRows} />
          </div>

          <div className="panel ledger-panel">
            <p className="panel-title small-caps">Agent track records</p>
            <TrackRecordTable records={records} />
          </div>

          <div className="panel ledger-panel">
            <p className="panel-title small-caps">Which screeners predict</p>
            <ScreenerCalibrationPanel rows={screenerCalibrationRows} />
          </div>
        </div>
      )}

      <LessonsDiary lessons={lessonItems} digest={digest} />
    </div>
  );
}
