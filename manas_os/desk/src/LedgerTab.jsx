import React, { useEffect, useState } from "react";
import { fetchTrackRecord, fetchLessons, fetchJournal } from "./api.js";
import { Term } from "./Glossary.jsx";

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
    </div>
  );
}

export default function LedgerTab() {
  const [trackRecord, setTrackRecord] = useState(null);
  const [lessons, setLessons] = useState(null);
  const [journal, setJournal] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [systemEdgeOpen, setSystemEdgeOpen] = useState(false);

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
