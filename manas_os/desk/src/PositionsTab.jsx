import React, { useEffect, useState } from "react";
import { addPosition, closePosition, fetchPositions, updatePosition } from "./api.js";
import { Term } from "./Glossary.jsx";
import { colorScale } from "./viz.js";

const SPARK_W = 460;
const SPARK_H = 80;
const SPARK_PAD = 10;
const CLOSE_REASONS = ["target", "stop-hit", "fear", "need-cash", "thesis-change", "other"];

function round(n, digits = 1) {
  if (n === null || n === undefined) return "-";
  const f = Math.pow(10, digits);
  return Math.round(Number(n) * f) / f;
}

function phaseForR(r) {
  if (r === null || r === undefined) return "INITIATION";
  if (r >= 2) return "EXTENSION";
  if (r >= 1) return "TREND";
  return "INITIATION";
}

function verdictClass(verdict) {
  const v = (verdict || "").toLowerCase();
  if (v === "exit") return "exit";
  if (v === "trim") return "trim";
  if (v === "move_stop") return "move-stop";
  return "hold";
}

function RPathSparkline({ position }) {
  const points = position.r_path || [];
  const entry = position.entry;
  const stop = position.stop;
  const risk = entry !== null && entry !== undefined && stop !== null && stop !== undefined ? entry - stop : null;
  const trailR =
    risk && risk > 0 && position.trail_stop !== null && position.trail_stop !== undefined
      ? (position.trail_stop - entry) / risk
      : null;

  if (points.length === 0) {
    return <div className="rpath-empty mono">R-path unavailable (no priced sessions yet)</div>;
  }

  const rValues = points.map((p) => p.r);
  const allValues = trailR !== null ? [...rValues, trailR, 0] : [...rValues, 0];
  const rMin = Math.min(...allValues);
  const rMax = Math.max(...allValues);
  const span = rMax - rMin || 1;
  const innerH = SPARK_H - SPARK_PAD * 2;
  const innerW = SPARK_W - SPARK_PAD * 2;

  const yFor = (r) => SPARK_PAD + innerH - ((r - rMin) / span) * innerH;
  const xFor = (i) => SPARK_PAD + (points.length === 1 ? 0 : (i / (points.length - 1)) * innerW);
  const linePoints = points.map((p, i) => `${xFor(i)},${yFor(p.r)}`).join(" ");

  const bands = [];
  let bandStart = 0;
  let bandPhase = phaseForR(points[0].r);
  for (let i = 1; i <= points.length; i += 1) {
    const phase = i < points.length ? phaseForR(points[i].r) : null;
    if (phase !== bandPhase) {
      bands.push({ phase: bandPhase, x0: xFor(bandStart), x1: xFor(i - 1) });
      bandStart = i;
      bandPhase = phase;
    }
  }

  const bandColor = { INITIATION: "var(--bg-sunken)", TREND: "var(--accent-soft)", EXTENSION: "var(--positive-soft)" };
  const zeroY = yFor(0);

  return (
    <svg className="rpath-svg" viewBox={`0 0 ${SPARK_W} ${SPARK_H}`} preserveAspectRatio="none">
      {bands.map((b, i) => (
        <rect
          key={i}
          x={Math.min(b.x0, b.x1)}
          y={0}
          width={Math.max(Math.abs(b.x1 - b.x0), 1)}
          height={SPARK_H}
          fill={bandColor[b.phase]}
        />
      ))}
      <line x1={SPARK_PAD} y1={zeroY} x2={SPARK_W - SPARK_PAD} y2={zeroY} stroke="var(--border)" strokeWidth="1" />
      {trailR !== null && (
        <line
          x1={SPARK_PAD}
          y1={yFor(trailR)}
          x2={SPARK_W - SPARK_PAD}
          y2={yFor(trailR)}
          stroke="var(--warn)"
          strokeWidth="1"
          strokeDasharray="4 3"
        />
      )}
      <polyline points={linePoints} fill="none" stroke="var(--accent)" strokeWidth="2" />
      <circle cx={xFor(points.length - 1)} cy={yFor(points[points.length - 1].r)} r="3" fill="var(--accent)" />
    </svg>
  );
}

function OriginalThesisBox({ thesis }) {
  if (!thesis || thesis.note) {
    return (
      <div className="thesis-box mono">
        <p className="panel-title small-caps">Original thesis</p>
        <p>no agent thesis</p>
      </div>
    );
  }
  const label = thesis.agent ? `${thesis.agent}${thesis.scan_date ? `, ${thesis.scan_date}` : ""}` : thesis.scan_date || "-";
  return (
    <div className="thesis-box">
      <p className="panel-title small-caps">Original thesis</p>
      <p className="thesis-quote">"{thesis.bull_case || "-"}"</p>
      <span className="thesis-attribution">- {label}</span>
    </div>
  );
}

// Distinct purpose from the coach-why paragraph above: this is an audit of
// what actually went to Telegram, not a re-statement of the read. The first
// line of `coach.message` is always "{SYMBOL} coach: {action_line}", which
// duplicates the card's coach-why text (plain_why/advisor_note), so it is
// stripped here to avoid printing the same exit sentence three times.
function dedupedTelegramBody(message, symbol) {
  const lines = (message || "").split("\n");
  const prefix = `${symbol} coach: `;
  if (lines.length && lines[0].startsWith(prefix)) {
    lines.shift();
  }
  return lines.join(" ").trim();
}

function TelegramMirror({ coach, symbol }) {
  if (!coach) {
    return <div className="telegram-mirror mono">no coach signal sent yet</div>;
  }
  const status = coach.sent ? `sent ${(coach.created_at || "").slice(11, 16) || ""}` : "dry-run: shown, not sent";
  const body = dedupedTelegramBody(coach.message, symbol);
  return (
    <div className="telegram-mirror mono">
      {status}
      {body ? ` "${body}"` : ""}
    </div>
  );
}

function PositionForm({ initial, onCancel, onSubmit, busy, error }) {
  const [form, setForm] = useState(
    initial || { symbol: "", entry: "", stop: "", qty: "", date: new Date().toISOString().slice(0, 10) },
  );
  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));
  return (
    <form
      className="position-form"
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit(form);
      }}
    >
      <input value={form.symbol} onChange={(e) => set("symbol", e.target.value)} placeholder="Symbol" />
      <input value={form.entry} onChange={(e) => set("entry", e.target.value)} placeholder="Entry" type="number" step="0.01" />
      <input value={form.stop} onChange={(e) => set("stop", e.target.value)} placeholder="SL" type="number" step="0.01" />
      <input value={form.qty} onChange={(e) => set("qty", e.target.value)} placeholder="Qty" type="number" step="1" />
      <input value={form.date} onChange={(e) => set("date", e.target.value)} type="date" />
      <div className="position-form-actions">
        <button className="position-action primary" type="submit" disabled={busy}>
          Add
        </button>
        <button className="position-action" type="button" onClick={onCancel} disabled={busy}>
          Cancel
        </button>
      </div>
      {error && <p className="position-form-error">{error}</p>}
    </form>
  );
}

function CloseModal({ position, onCancel, onSubmit, busy, error }) {
  const [exitPrice, setExitPrice] = useState("");
  const [reasonTag, setReasonTag] = useState("target");
  return (
    <div className="position-modal-backdrop">
      <form
        className="position-modal"
        onSubmit={(event) => {
          event.preventDefault();
          onSubmit({ exit_price: exitPrice, reason_tag: reasonTag });
        }}
      >
        <p className="panel-title small-caps">Close {position.symbol}</p>
        <label>
          Exit price
          <input value={exitPrice} onChange={(e) => setExitPrice(e.target.value)} type="number" step="0.01" autoFocus />
        </label>
        <label>
          Reason
          <select value={reasonTag} onChange={(e) => setReasonTag(e.target.value)}>
            {CLOSE_REASONS.map((reason) => (
              <option key={reason} value={reason}>
                {reason}
              </option>
            ))}
          </select>
        </label>
        <div className="position-form-actions">
          <button className="position-action danger" type="submit" disabled={busy}>
            Close
          </button>
          <button className="position-action" type="button" onClick={onCancel} disabled={busy}>
            Cancel
          </button>
        </div>
        {error && <p className="position-form-error">{error}</p>}
      </form>
    </div>
  );
}

// Card slot priority: LLM narrative (advisor_note, persisted nightly by
// agents/coach.py into advisor_notes) when available, else the deterministic
// exit-engine read (plain_why — verdict/fired/trail-stop already folded in
// by _plain_action_line). "Coach read unavailable" only fires when neither
// exists, i.e. there is truly no deterministic verdict for this position.
function coachWhyText(position) {
  if (position.advisor_note) return position.advisor_note;
  if (position.plain_why) return position.plain_why;
  return "Coach read unavailable for this position (no priced sessions yet).";
}

function PositionCard({ position, onEditStop, onEditQty, onClose }) {
  const urgent = position.urgent;
  const verdict = position.coach_verdict || "-";
  return (
    <div className={"panel position-card" + (urgent ? " urgent" : "")}>
      <div className="position-card-header">
        {urgent && <span className="urgent-icon">!</span>}
        <span className="position-symbol">{position.symbol}</span>
        <span className="position-meta mono">
          entry {round(position.entry, 2)} / SL {round(position.stop, 2)} / qty {round(position.qty, 0)} /{" "}
          <Term k="days-held">days held</Term> {position.days_held ?? "-"}
        </span>
        {urgent && <span className="urgent-label">EXIT NOW: {(position.fired || []).join(", ") || "two-strike rule"} fired</span>}
      </div>

      <div className="position-actions">
        <button className="position-action" type="button" onClick={() => onEditStop(position)}>
          Edit SL
        </button>
        <button className="position-action" type="button" onClick={() => onEditQty(position)}>
          Edit qty
        </button>
        <button className="position-action danger" type="button" onClick={() => onClose(position)}>
          Close
        </button>
      </div>

      <div className="position-coach-block">
        <div className="position-coach-head">
          <span className={"verdict-pill " + verdictClass(verdict)}>
            <Term k="coach-verdict">{verdict}</Term>
          </span>
          <span className="sl-today mono">SL today: {round(position.todays_stop, 2)}</span>
          <span className="open-r mono" style={colorScale(position.open_r, 3)}>
            <Term k="open-r">Open R</Term> {position.open_r !== null && position.open_r !== undefined ? `${position.open_r >= 0 ? "+" : ""}${round(position.open_r, 2)}R` : "-"}
          </span>
          {/* F5: raw rupee P&L surfaced prominently alongside R -- payload
              already carries pnl_rupees/pnl_pct (manas_os/api/app.py), this
              was the missing render. */}
          {position.pnl_rupees !== null && position.pnl_rupees !== undefined && (
            <span className="position-pnl mono" style={colorScale(position.pnl_rupees, 1)}>
              {position.pnl_rupees >= 0 ? "+" : ""}
              {"₹"}{round(position.pnl_rupees, 0)}
              {position.pnl_pct !== null && position.pnl_pct !== undefined
                ? ` (${position.pnl_pct >= 0 ? "+" : ""}${round(position.pnl_pct, 1)}%)`
                : ""}
            </span>
          )}
        </div>
        <p className="coach-why">{coachWhyText(position)}</p>
        <p className="caption-b">[B] Use this as the daily hold/trim/exit instruction; no new LLM call is made from this screen.</p>
      </div>

      <RPathSparkline position={position} />
      <div className="rpath-caption-row">
        <span className="rpath-caption mono">
          <Term k="trail-stop">trail stop</Term> {round(position.trail_stop, 2)} /{" "}
          <Term k="position-phase">phase</Term> {position.phase || "-"}
        </span>
      </div>

      {position.banner && <p className="position-banner mono">{position.banner}</p>}
      <p className="how-to-trade-pointer mono">
        Entry steps were on the original DEBATE card's "HOW TO TRADE THIS" guide — this card is
        management only (hold/trim/exit), not re-shown here to avoid duplicating the coach read above.
      </p>
      <OriginalThesisBox thesis={position.original_thesis} />
      <TelegramMirror coach={position.coach} symbol={position.symbol} />
    </div>
  );
}

export default function PositionsTab({ date }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [adding, setAdding] = useState(false);
  const [busy, setBusy] = useState(false);
  const [formError, setFormError] = useState(null);
  const [closeTarget, setCloseTarget] = useState(null);

  const load = () => {
    setLoading(true);
    setError(null);
    return fetchPositions(date)
      .then((body) => setData(body))
      .catch((err) => setError(String(err)))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetchPositions(date)
      .then((body) => {
        if (!cancelled) setData(body);
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
  }, [date]);

  const submitAdd = (form) => {
    setBusy(true);
    setFormError(null);
    addPosition(form)
      .then(() => {
        setAdding(false);
        return load();
      })
      .catch((err) => setFormError(String(err)))
      .finally(() => setBusy(false));
  };

  const editStop = (position) => {
    const stop = window.prompt(`New SL for ${position.symbol}`, position.stop ?? "");
    if (stop === null) return;
    setBusy(true);
    updatePosition(position.trade_id, { stop })
      .then(load)
      .catch((err) => setError(String(err)))
      .finally(() => setBusy(false));
  };

  const editQty = (position) => {
    const qty = window.prompt(`New qty for ${position.symbol}`, position.qty ?? "");
    if (qty === null) return;
    setBusy(true);
    updatePosition(position.trade_id, { qty })
      .then(load)
      .catch((err) => setError(String(err)))
      .finally(() => setBusy(false));
  };

  const submitClose = (payload) => {
    setBusy(true);
    setFormError(null);
    closePosition(closeTarget.trade_id, payload)
      .then(() => {
        setCloseTarget(null);
        return load();
      })
      .catch((err) => setFormError(String(err)))
      .finally(() => setBusy(false));
  };

  if (loading) {
    return <div className="empty-state">Loading...</div>;
  }
  if (error) {
    return (
      <div className="empty-state">
        <div className="empty-state-icon">!</div>
        <p className="empty-state-line">Could not load positions.</p>
        <p className="empty-state-sub">{error}</p>
      </div>
    );
  }

  const positions = data?.positions || [];
  return (
    <div>
      <div className="positions-toolbar">
        <button className="position-action primary" type="button" onClick={() => setAdding(true)} disabled={busy}>
          Add position
        </button>
      </div>
      {adding && <PositionForm onCancel={() => setAdding(false)} onSubmit={submitAdd} busy={busy} error={formError} />}
      {positions.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">○</div>
          <p className="empty-state-line">No open positions.</p>
          <p className="empty-state-sub">Add a manual position or take a setup from the desk.</p>
        </div>
      ) : (
        positions.map((p) => (
          <PositionCard key={p.trade_id} position={p} onEditStop={editStop} onEditQty={editQty} onClose={setCloseTarget} />
        ))
      )}
      {closeTarget && (
        <CloseModal
          position={closeTarget}
          onCancel={() => setCloseTarget(null)}
          onSubmit={submitClose}
          busy={busy}
          error={formError}
        />
      )}
    </div>
  );
}
