import React, { useEffect, useState } from "react";
import { fetchTrackRecord, fetchLessons, fetchJournal } from "./api.js";

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
            <th>Hit</th>
            <th>Avg R</th>
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
          <span className="stat-tile-label">Avg R</span>
          <span className="stat-tile-value mono">{round(stats.avg_r, 2)}</span>
        </div>
        <div className="stat-tile">
          <span className="stat-tile-label">Expectancy</span>
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
  const lessonItems = (lessons && lessons.lessons) || [];
  const digest = lessons && lessons.digest;

  return (
    <div className="ledger-tab">
      <div className="panel ledger-panel">
        <p className="panel-title small-caps">Agent track records</p>
        <TrackRecordTable records={records} />
      </div>

      <LessonsDiary lessons={lessonItems} digest={digest} />

      <JournalStrip journal={journal} />
    </div>
  );
}
