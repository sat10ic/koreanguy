import React, { useEffect, useState } from "react";
import { addPosition, closePosition, fetchPositions, updatePosition } from "./api.js";
import { useDensity } from "./DensityContext.jsx";
import { Term } from "./Glossary.jsx";
import {
  SectionLabel,
  Panel,
  ReturnCell,
  StruckNote,
  VerdictChip,
} from "./components/v5/index.js";
import "./PositionsTab.v5.css";

const SPARK_W = 460;
const SPARK_H = 80;
const SPARK_PAD = 10;
const CLOSE_REASONS = ["target", "stop-hit", "fear", "need-cash", "thesis-change", "other"];

function round(n, digits = 1) {
  if (n === null || n === undefined) return "—";
  const f = Math.pow(10, digits);
  return (Math.round(Number(n) * f) / f).toFixed(digits);
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
    return <div className="v5-pos-rpath-empty mono-num">R-path unavailable (no priced sessions yet)</div>;
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

  const bandColor = {
    INITIATION: "var(--v5-panel-3)",
    TREND: "var(--v5-teal-dim)",
    EXTENSION: "var(--v5-green-dim)"
  };
  const zeroY = yFor(0);

  return (
    <svg className="v5-pos-rpath-svg" viewBox={`0 0 ${SPARK_W} ${SPARK_H}`} preserveAspectRatio="none">
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
      <line x1={SPARK_PAD} y1={zeroY} x2={SPARK_W - SPARK_PAD} y2={zeroY} stroke="var(--v5-line)" strokeWidth="1" />
      {trailR !== null && (
        <line
          x1={SPARK_PAD}
          y1={yFor(trailR)}
          x2={SPARK_W - SPARK_PAD}
          y2={yFor(trailR)}
          stroke="var(--v5-amber-bright)"
          strokeWidth="1"
          strokeDasharray="4 3"
        />
      )}
      <polyline points={linePoints} fill="none" stroke="var(--v5-teal)" strokeWidth="2" />
      <circle cx={xFor(points.length - 1)} cy={yFor(points[points.length - 1].r)} r="3" fill="var(--v5-teal)" />
    </svg>
  );
}

function RThermometer({ position }) {
  const entry = position.entry;
  const stop = position.stop;
  if (entry === null || entry === undefined || stop === null || stop === undefined) return null;
  const risk = entry - stop;
  if (!risk) return null;
  const openR = position.open_r;
  const current = openR !== null && openR !== undefined ? entry + openR * risk : null;
  const target = position.target ?? null;

  const marks = [
    { key: "stop", label: "stop", value: stop, cls: "stop" },
    { key: "entry", label: "entry", value: entry, cls: "entry" }
  ];
  if (current !== null) marks.push({ key: "current", label: "now", value: current, cls: "current" });
  if (target !== null && target !== undefined) marks.push({ key: "target", label: "target", value: target, cls: "target" });

  const values = marks.map((m) => m.value);
  const lo = Math.min(...values);
  const hi = Math.max(...values);
  const span = hi - lo || 1;
  const padPct = 6;
  const pctFor = (v) => padPct + ((v - lo) / span) * (100 - padPct * 2);

  return (
    <div className="v5-pos-thermometer">
      <div className="v5-pos-thermometer-rail">
        {marks.map((m) => (
          <div key={m.key} className={"v5-pos-thermometer-mark " + m.cls} style={{ left: `${pctFor(m.value)}%` }}>
            <span className="v5-pos-thermometer-dot" />
            <span className="v5-pos-thermometer-label mono-num">
              {m.label} {round(m.value, 1)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function PnlDisplay({ pnl, pct }) {
  if (pnl === null || pnl === undefined) return null;
  const up = pnl >= 0;
  const sign = up ? "+" : "";
  const cls = up ? "v5-up" : "v5-down";
  return (
    <span className={`v5-pos-pnl mono-num ${cls}`}>
      {sign}₹{round(pnl, 0)}
      {pct !== null && pct !== undefined && (
        <span className="v5-pos-pnl-pct">
          {" "}({sign}{round(pct, 1)}%)
        </span>
      )}
    </span>
  );
}

function VerdictHead({ position }) {
  const urgent = position.urgent;
  const verdict = position.coach_verdict || "HOLD";
  const actionLine = position.action_line || (urgent ? "EXIT NOW — day-low break + two-strike fired." : null);
  const displayVerdict = urgent ? "EXIT" : verdict;
  const cls = verdictClass(displayVerdict);
  
  return (
    <div className={`v5-pos-verdict-head${urgent ? " v5-urgent" : ""}`}>
      <div className="v5-pos-verdict-row">
        <VerdictChip
          tone={`v5-pos-verdict-pill v5-tone-${cls}`}
        >
          <Term k="coach-verdict">{displayVerdict}</Term>
        </VerdictChip>
        {actionLine && <span className="v5-pos-action-line">{actionLine}</span>}
        <PnlDisplay pnl={position.pnl_rupees} pct={position.pnl_pct} />
      </div>
      {urgent && (
        <div className="v5-pos-urgent-sub mono-num">
          EXIT NOW: {(position.fired || []).join(", ") || "two-strike rule"} fired
        </div>
      )}
    </div>
  );
}

function OriginalThesisBox({ thesis, symbol, onOpenOrigin, onRunDebate }) {
  if (!thesis || thesis.note) {
    // Manually-added position, or one with no scanned thesis record. The audit
    // (#49) flagged "no agent thesis" as a dead end — say why, and offer the
    // action that would create one (run a debate for this symbol), instead of
    // a bare string that reads like an error.
    return (
      <div className="v5-pos-thesis mono-num">
        <p className="v5-pos-thesis-title small-caps">Original thesis</p>
        <p>
          No agent thesis on record
          {symbol ? <> for <b>{symbol}</b></> : null}.
          This position was added manually or predates the debate log — its entry
          thesis was never captured.
        </p>
        {symbol && onRunDebate && (
          <button
            type="button"
            className="v5-pos-thesis-run"
            onClick={() => onRunDebate(symbol)}
          >
            Run debate for {symbol}
          </button>
        )}
      </div>
    );
  }
  const label = thesis.agent ? `${thesis.agent}${thesis.scan_date ? `, ${thesis.scan_date}` : ""}` : thesis.scan_date || "—";
  return (
    <StruckNote>
      <div className="v5-pos-thesis">
        <p className="v5-pos-thesis-title small-caps">Original thesis</p>
        <p className="v5-pos-thesis-quote">"{thesis.bull_case || "—"}"</p>
        <span className="v5-pos-thesis-attribution">
          — {label}
          {symbol && thesis.scan_date && onOpenOrigin && (
            <button
              type="button"
              className="v5-pos-thesis-origin"
              onClick={() => onOpenOrigin(symbol, thesis.scan_date)}
            >
              open origin debate ({thesis.scan_date})
            </button>
          )}
        </span>
      </div>
    </StruckNote>
  );
}

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
    return <div className="v5-pos-telegram mono-num">no coach signal sent yet</div>;
  }
  const status = coach.sent ? `sent ${(coach.created_at || "").slice(11, 16) || ""}` : "Preview only (simulation mode)";
  const body = dedupedTelegramBody(coach.message, symbol);
  return (
    <div className="v5-pos-telegram mono-num">
      {status}
      {body ? ` "${body}"` : ""}
    </div>
  );
}


function coachWhyText(position) {
  if (position.advisor_note) return position.advisor_note;
  if (position.plain_why) return position.plain_why;
  return "Coach read unavailable for this position (no priced sessions yet).";
}

function PriceFreshnessBadge({ fyersConnected, marketOpen }) {
  if (fyersConnected === false) {
    return <span className="v5-pos-freshness v5-freshness-feed-down">feed down</span>;
  }
  if (marketOpen === false) {
    return <span className="v5-pos-freshness v5-freshness-last-close">last close</span>;
  }
  return <span className="v5-pos-freshness v5-freshness-live">live</span>;
}

function PositionCard({ position, onUpdate, onClose, fyersConnected, marketOpen, onOpenOrigin, onRunDebate }) {
  const { isExpert } = useDensity();
  const urgent = position.urgent;

  // Local state for inline editing
  const [editState, setEditState] = useState("idle"); // "idle", "editing_sl", "editing_qty"
  const [inputValue, setInputValue] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [editError, setEditError] = useState(null);

  // Close editor on Escape keypress
  useEffect(() => {
    if (editState === "idle") return;
    const handleKeyDown = (e) => {
      if (e.key === "Escape") {
        cancelEdit();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [editState]);

  const startEditSL = () => {
    setEditState("editing_sl");
    setInputValue(position.stop !== null && position.stop !== undefined ? String(position.stop) : "");
    setEditError(null);
  };

  const startEditQty = () => {
    setEditState("editing_qty");
    setInputValue(position.qty !== null && position.qty !== undefined ? String(position.qty) : "");
    setEditError(null);
  };

  const cancelEdit = () => {
    setEditState("idle");
    setInputValue("");
    setEditError(null);
    setIsSaving(false);
  };

  const handleSave = (e) => {
    if (e) e.preventDefault();

    // Client-side Validation
    const val = Number(inputValue);
    if (!inputValue.trim() || isNaN(val) || val <= 0) {
      setEditError("Please enter a valid positive number.");
      return;
    }

    if (editState === "editing_qty" && !Number.isInteger(val)) {
      setEditError("Quantity must be a whole number.");
      return;
    }

    setIsSaving(true);
    setEditError(null);

    const payload = editState === "editing_sl" ? { stop: inputValue } : { qty: inputValue };

    onUpdate(position.trade_id, payload)
      .then(() => {
        setEditState("idle");
        setIsSaving(false);
      })
      .catch((err) => {
        setEditError(String(err));
        setIsSaving(false);
      });
  };

  const renderInlineEditor = () => {
    if (editState === "idle") return null;
    const label = editState === "editing_sl" ? "Stop Loss (SL)" : "Quantity";
    const currentValue = editState === "editing_sl" ? position.stop : position.qty;
    const placeholder = editState === "editing_sl" ? "e.g. 210.84" : "e.g. 100";
    const step = editState === "editing_sl" ? "0.01" : "1";

    return (
      <form className="v5-pos-inline-edit" onSubmit={handleSave}>
        <div className="v5-pos-edit-header">
          <span className="v5-pos-edit-title">Edit {label}</span>
          <span className="v5-pos-edit-current mono-num">
            Current: {round(currentValue, editState === "editing_sl" ? 2 : 0)}
          </span>
        </div>
        <div className="v5-pos-edit-row">
          <input
            type="number"
            step={step}
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            disabled={isSaving}
            autoFocus
            placeholder={placeholder}
            className="v5-pos-edit-input mono-num"
          />
          <div className="v5-pos-edit-actions">
            <button
              type="submit"
              disabled={isSaving}
              className="v5-pos-btn v5-btn-primary"
            >
              {isSaving ? "Saving..." : "Save"}
            </button>
            <button
              type="button"
              onClick={cancelEdit}
              disabled={isSaving}
              className="v5-pos-btn"
            >
              Cancel
            </button>
          </div>
        </div>
        {editError && <div className="v5-pos-edit-error">{editError}</div>}
      </form>
    );
  };

  return (
    <div className={`v5-pos-card${urgent ? " v5-urgent" : ""}`}>
      <VerdictHead position={position} />

      <div className="v5-pos-card-header">
        <span className="v5-pos-symbol">{position.symbol}</span>
        {position.close !== null && position.close !== undefined && (
          <span className="v5-pos-current-price mono-num">
            NOW {round(position.close, 2)}
          </span>
        )}
        <PriceFreshnessBadge fyersConnected={fyersConnected} marketOpen={marketOpen} />
        <span className="v5-pos-meta mono-num">
          entry {round(position.entry, 2)} / SL {round(position.stop, 2)} / qty {round(position.qty, 0)} /{" "}
          <Term k="days-held">days held</Term> {position.days_held ?? "—"}
        </span>
        <span className="v5-pos-sl-today mono-num">SL today: {round(position.todays_stop, 2)}</span>
        <span className={`v5-pos-open-r mono-num ${position.open_r >= 0 ? "v5-up" : "v5-down"}`}>
          <Term k="open-r">Open R</Term>{" "}
          {position.open_r !== null && position.open_r !== undefined
            ? `${position.open_r >= 0 ? "+" : ""}${round(position.open_r, 2)}R`
            : "—"}
        </span>
      </div>

      <RThermometer position={position} />

      <div className="v5-pos-actions-container">
        {editState === "idle" ? (
          <div className="v5-pos-actions">
            <button className="v5-pos-btn" type="button" onClick={startEditSL}>
              Edit SL
            </button>
            <button className="v5-pos-btn" type="button" onClick={startEditQty}>
              Edit qty
            </button>
            <button className="v5-pos-btn v5-btn-danger" type="button" onClick={() => onClose(position)}>
              Close
            </button>
          </div>
        ) : (
          renderInlineEditor()
        )}
      </div>

      <div className="v5-pos-coach-block">
        <p className="v5-pos-coach-why">{coachWhyText(position)}</p>
        <p className="v5-pos-caption">Use this as the daily hold/trim/exit instruction; no new LLM call is made from this screen.</p>
        {position.advisor_note_stale && position.advisor_note_stale_text && (
          <p className="v5-pos-coach-why-stale mono-num">
            stale note (superseded by verdict): "{position.advisor_note_stale_text}"
          </p>
        )}
      </div>

      <RPathSparkline position={position} />
      <div className="v5-pos-rpath-caption-row">
        <span className="v5-pos-rpath-caption mono-num">
          <Term k="trail-stop">trail stop</Term> {round(position.trail_stop, 2)} /{" "}
          <Term k="position-phase">phase</Term> {position.phase || "—"}
        </span>
      </div>

      {position.banner && <p className="v5-pos-banner mono-num">{position.banner}</p>}

      {isExpert && (
        <div className="v5-pos-expert-block">
          {(position.fired || []).length > 0 && (
            <p className="v5-pos-fired mono-num">fired: {(position.fired || []).join(", ")}</p>
          )}
          <p className="v5-pos-trade-pointer mono-num">
            Entry steps were on the original DEBATE card's "HOW TO TRADE THIS" guide — this card is
            management only (hold/trim/exit), not re-shown here to avoid duplicating the coach read above.
          </p>
          <OriginalThesisBox thesis={position.original_thesis} symbol={position.symbol} onOpenOrigin={onOpenOrigin} onRunDebate={onRunDebate} />
          <TelegramMirror coach={position.coach} symbol={position.symbol} />
        </div>
      )}
    </div>
  );
}

function CloseModal({ position, onCancel, onSubmit }) {
  const [exitPrice, setExitPrice] = useState("");
  const [reasonTag, setReasonTag] = useState("target");
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState(null);

  // Close modal on Escape press
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === "Escape") {
        onCancel();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onCancel]);

  const handleSubmit = (event) => {
    event.preventDefault();

    // Validation
    const val = Number(exitPrice);
    if (!exitPrice.trim() || isNaN(val) || val <= 0) {
      setError("Please enter a valid positive exit price.");
      return;
    }

    setIsSaving(true);
    setError(null);

    onSubmit({ exit_price: exitPrice, reason_tag: reasonTag })
      .then(() => {
        // Closed and reloaded successfully
      })
      .catch((err) => {
        setError(String(err));
        setIsSaving(false);
      });
  };

  return (
    <div className="v5-pos-modal-backdrop">
      <div className="v5-pos-modal-container">
        <form className="v5-pos-modal-form" onSubmit={handleSubmit}>
          <div className="v5-pos-modal-header">
            <span className="v5-pos-modal-title">Close {position.symbol}</span>
            <span className="v5-pos-modal-subtitle mono-num">
              Qty: {round(position.qty, 0)} · Current SL: {round(position.stop, 2)}
            </span>
          </div>

          <div className="v5-pos-modal-body">
            <label className="v5-pos-modal-field">
              <span className="v5-pos-modal-label">Exit Price</span>
              <input
                value={exitPrice}
                onChange={(e) => setExitPrice(e.target.value)}
                type="number"
                step="0.01"
                disabled={isSaving}
                autoFocus
                placeholder="e.g. 206.96"
                className="v5-pos-modal-input mono-num"
              />
            </label>

            <label className="v5-pos-modal-field">
              <span className="v5-pos-modal-label">Reason</span>
              <select
                value={reasonTag}
                onChange={(e) => setReasonTag(e.target.value)}
                disabled={isSaving}
                className="v5-pos-modal-select"
              >
                {CLOSE_REASONS.map((reason) => (
                  <option key={reason} value={reason}>
                    {reason}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <div className="v5-pos-modal-actions">
            <button
              className="v5-pos-btn v5-btn-danger"
              type="submit"
              disabled={isSaving}
            >
              {isSaving ? "Closing..." : "Close Position"}
            </button>
            <button
              className="v5-pos-btn"
              type="button"
              onClick={onCancel}
              disabled={isSaving}
            >
              Cancel
            </button>
          </div>

          {error && <p className="v5-pos-modal-error">{error}</p>}
        </form>
      </div>
    </div>
  );
}

function PositionForm({ initial, onCancel, onSubmit, busy, error }) {
  const [form, setForm] = useState(
    initial || { symbol: "", entry: "", stop: "", qty: "", date: new Date().toISOString().slice(0, 10) },
  );

  // Close on Escape press
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === "Escape") {
        onCancel();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onCancel]);

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  return (
    <Panel title="Add Manual Position" className="v5-pos-add-panel">
      <form
        className="v5-pos-form"
        onSubmit={(event) => {
          event.preventDefault();
          onSubmit(form);
        }}
      >
        <div className="v5-pos-form-grid">
          <label className="v5-pos-form-field">
            <span className="v5-pos-form-label">Symbol</span>
            <input
              value={form.symbol}
              onChange={(e) => set("symbol", e.target.value)}
              placeholder="e.g. HUDCO"
              disabled={busy}
              autoFocus
              required
            />
          </label>
          <label className="v5-pos-form-field">
            <span className="v5-pos-form-label">Entry Price</span>
            <input
              value={form.entry}
              onChange={(e) => set("entry", e.target.value)}
              placeholder="e.g. 218.0"
              type="number"
              step="0.01"
              disabled={busy}
              required
              className="mono-num"
            />
          </label>
          <label className="v5-pos-form-field">
            <span className="v5-pos-form-label">Stop Loss (SL)</span>
            <input
              value={form.stop}
              onChange={(e) => set("stop", e.target.value)}
              placeholder="e.g. 210.84"
              type="number"
              step="0.01"
              disabled={busy}
              required
              className="mono-num"
            />
          </label>
          <label className="v5-pos-form-field">
            <span className="v5-pos-form-label">Quantity</span>
            <input
              value={form.qty}
              onChange={(e) => set("qty", e.target.value)}
              placeholder="e.g. 100"
              type="number"
              step="1"
              disabled={busy}
              required
              className="mono-num"
            />
          </label>
          <label className="v5-pos-form-field">
            <span className="v5-pos-form-label">Date</span>
            <input
              value={form.date}
              onChange={(e) => set("date", e.target.value)}
              type="date"
              disabled={busy}
              required
              className="mono-num"
            />
          </label>
        </div>
        <div className="v5-pos-form-actions">
          <button className="v5-pos-btn v5-btn-primary" type="submit" disabled={busy}>
            {busy ? "Adding..." : "Add Position"}
          </button>
          <button className="v5-pos-btn" type="button" onClick={onCancel} disabled={busy}>
            Cancel
          </button>
        </div>
        {error && <p className="v5-pos-form-error">{error}</p>}
      </form>
    </Panel>
  );
}

export default function PositionsTab({ date, onOpenOrigin, onRunDebate }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [adding, setAdding] = useState(false);
  const [busy, setBusy] = useState(false);
  const [formError, setFormError] = useState(null);
  const [closeTarget, setCloseTarget] = useState(null);

  const load = (showSpinner = true) => {
    if (showSpinner) {
      setLoading(true);
    }
    setError(null);
    return fetchPositions(date)
      .then((body) => setData(body))
      .catch((err) => setError(String(err)))
      .finally(() => {
        if (showSpinner) {
          setLoading(false);
        }
      });
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
        return load(false);
      })
      .catch((err) => setFormError(String(err)))
      .finally(() => setBusy(false));
  };

  const handleUpdatePosition = (tradeId, payload) => {
    return updatePosition(tradeId, payload)
      .then(() => {
        return load(false);
      });
  };

  const handleClosePosition = (payload) => {
    return closePosition(closeTarget.trade_id, payload)
      .then(() => {
        setCloseTarget(null);
        return load(false);
      });
  };

  if (loading) {
    return <div className="v5-positions-empty">Loading positions...</div>;
  }
  if (error) {
    return (
      <div className="v5-positions-empty">
        <div className="v5-positions-error-icon">!</div>
        <p className="v5-positions-error-line">Could not load positions.</p>
        <p className="v5-positions-error-sub">{error}</p>
      </div>
    );
  }

  const positions = [...(data?.positions || [])].sort((a, b) => (b.urgent ? 1 : 0) - (a.urgent ? 1 : 0));

  return (
    <div className="v5-positions">
      <div className="v5-positions-toolbar">
        <SectionLabel count={positions.length}>Open Positions</SectionLabel>
        {!adding && (
          <button className="v5-pos-btn v5-btn-primary" type="button" onClick={() => setAdding(true)} disabled={busy}>
            Add position
          </button>
        )}
      </div>

      {adding && (
        <div className="v5-pos-add-container">
          <PositionForm onCancel={() => setAdding(false)} onSubmit={submitAdd} busy={busy} error={formError} />
        </div>
      )}

      {positions.length === 0 ? (
        <div className="v5-positions-empty">
          <div className="v5-positions-empty-icon">○</div>
          <p className="v5-positions-empty-line">No open positions.</p>
          <p className="v5-positions-empty-sub">Add a manual position or take a setup from the desk.</p>
        </div>
      ) : (
        <div className="v5-positions-list">
          {positions.map((p) => (
            <PositionCard
              key={p.trade_id}
              position={p}
              onUpdate={handleUpdatePosition}
              onClose={setCloseTarget}
              fyersConnected={data?.fyers_connected}
              marketOpen={data?.market_open}
              onOpenOrigin={onOpenOrigin}
              onRunDebate={onRunDebate}
            />
          ))}
        </div>
      )}

      {closeTarget && (
        <CloseModal
          key={closeTarget.trade_id}
          position={closeTarget}
          onCancel={() => setCloseTarget(null)}
          onSubmit={handleClosePosition}
        />
      )}
    </div>
  );
}
