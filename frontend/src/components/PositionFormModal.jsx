import React, { useEffect, useState } from "react";
import { X, Loader2 } from "lucide-react";
import { Button } from "../ui";
import { endpoints } from "../api";
import { classNames, fmtPct } from "../utils";
import { InfoDot } from "./Tooltip";

/**
 * Modal that handles three flows:
 *   mode="add"   → create a new manual position
 *   mode="edit"  → trail stop / change size / notes of an existing row
 *   mode="exit"  → close out a position with exit_price
 *
 * Props:
 *   open, onClose, mode, initial (existing row when edit/exit), onSaved()
 */
export default function PositionFormModal({ open, mode = "add", initial, onClose, onSaved }) {
  const [form, setForm] = useState({});
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState(null);

  useEffect(() => {
    if (!open) return;
    setErr(null);
    if (mode === "add") {
      const today = new Date().toISOString().slice(0, 10);
      setForm({
        symbol: "",
        entry_date: today,
        signal_date: today,
        entry_price: "",
        stop_price: "",
        size_shares: "",
        entry_grade: "",
        regime_at_entry: "",
        state: "ACTIVE",
        notes: "",
      });
    } else if (mode === "edit") {
      setForm({
        stop_price: initial?.stop_price ?? "",
        size_shares: initial?.size_shares ?? "",
        notes: initial?.notes ?? "",
        state: initial?.state ?? "ACTIVE",
      });
    } else if (mode === "exit") {
      const today = new Date().toISOString().slice(0, 10);
      setForm({
        exit_date: today,
        exit_price: initial?.current_price ?? "",
        state: "EXITED_MANUAL",
        notes: "",
      });
    }
  }, [open, mode, initial]);

  if (!open) return null;

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  const submit = async (e) => {
    e?.preventDefault?.();
    if (busy) return;
    setBusy(true);
    setErr(null);
    try {
      if (mode === "add") {
        const body = {
          symbol: (form.symbol || "").trim().toUpperCase(),
          entry_price: parseFloat(form.entry_price),
          stop_price: parseFloat(form.stop_price),
          entry_date: form.entry_date || undefined,
          signal_date: form.signal_date || undefined,
          size_shares: form.size_shares ? parseInt(form.size_shares, 10) : undefined,
          entry_grade: form.entry_grade || undefined,
          regime_at_entry: form.regime_at_entry || undefined,
          state: form.state || "ACTIVE",
          notes: form.notes || undefined,
        };
        await endpoints.positionAdd(body);
      } else if (mode === "edit") {
        const body = {};
        if (form.stop_price !== "" && form.stop_price !== null) body.stop_price = parseFloat(form.stop_price);
        if (form.size_shares !== "" && form.size_shares !== null) body.size_shares = parseInt(form.size_shares, 10);
        if (form.notes !== undefined) body.notes = form.notes;
        if (form.state) body.state = form.state;
        await endpoints.positionUpdate(initial.id, body);
      } else if (mode === "exit") {
        await endpoints.positionExit(initial.id, {
          exit_price: parseFloat(form.exit_price),
          exit_date: form.exit_date,
          state: form.state || "EXITED_MANUAL",
          notes: form.notes || undefined,
        });
      }
      onSaved?.();
      onClose?.();
    } catch (e2) {
      setErr(e2?.response?.data?.detail || e2.message || "save failed");
    } finally {
      setBusy(false);
    }
  };

  // Live R / risk preview for add mode
  let preview = null;
  if (mode === "add") {
    const e = parseFloat(form.entry_price);
    const s = parseFloat(form.stop_price);
    const n = parseInt(form.size_shares, 10);
    if (e && s && e > s) {
      const riskPerShare = e - s;
      const riskPct = riskPerShare / e;
      const riskRupees = n ? riskPerShare * n : null;
      preview = (
        <div className="mt-2 grid grid-cols-3 gap-px bg-borderDefault text-[10px]">
          <Stat label="Risk / share" value={`₹ ${riskPerShare.toFixed(2)}`} />
          <Stat label="Risk %" value={fmtPct(riskPct, 2)} accent="text-warn" />
          <Stat
            label="Total risk"
            value={riskRupees != null ? `₹ ${riskRupees.toFixed(0)}` : "—"}
          />
        </div>
      );
    }
  }
  if (mode === "exit") {
    const e = parseFloat(initial?.entry_price);
    const x = parseFloat(form.exit_price);
    if (e && x && e > 0) {
      const pnl = (x - e) / e;
      preview = (
        <div className="mt-2 border border-borderDefault px-3 py-2">
          <div className="text-[10px] uppercase tracking-overline text-textMuted">
            Realised P&amp;L
          </div>
          <div
            className={classNames(
              "mt-0.5 font-mono text-lg tnum",
              pnl > 0 ? "text-bull" : pnl < 0 ? "text-bear" : "text-textSecondary"
            )}
          >
            {fmtPct(pnl, 2)}
          </div>
        </div>
      );
    }
  }

  const titles = {
    add: "Add Position · Manual Entry",
    edit: `Edit Position · ${initial?.symbol || ""}`,
    exit: `Close Position · ${initial?.symbol || ""}`,
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center bg-page/80 backdrop-blur-sm"
      onClick={onClose}
      data-testid={`position-form-modal-${mode}`}
    >
      <form
        onClick={(e) => e.stopPropagation()}
        onSubmit={submit}
        className="mt-16 w-full max-w-lg border border-borderDefault bg-surface shadow-2xl"
      >
        <header className="flex items-center justify-between border-b border-borderDefault px-4 py-3">
          <div className="text-[10px] font-medium uppercase tracking-overline text-saffron">
            {titles[mode]}
          </div>
          <button
            type="button"
            data-testid="position-form-close"
            onClick={onClose}
            className="text-textMuted transition-colors hover:text-textPrimary"
            aria-label="close"
          >
            <X size={16} />
          </button>
        </header>

        <div className="space-y-3 px-4 py-4">
          {mode === "add" && (
            <>
              <Field label="Symbol" required>
                <input
                  data-testid="pf-symbol"
                  value={form.symbol || ""}
                  onChange={set("symbol")}
                  placeholder="e.g. LENSKART"
                  required
                  className={inputCls}
                />
              </Field>
              <Row>
                <Field label="Entry Price" required>
                  <input
                    data-testid="pf-entry-price"
                    type="number"
                    step="0.01"
                    value={form.entry_price || ""}
                    onChange={set("entry_price")}
                    placeholder="520.00"
                    required
                    className={inputCls}
                  />
                </Field>
                <Field
                  label={
                    <span className="inline-flex items-center gap-1">
                      Stop Price <InfoDot k="Stop" />
                    </span>
                  }
                  required
                >
                  <input
                    data-testid="pf-stop-price"
                    type="number"
                    step="0.01"
                    value={form.stop_price || ""}
                    onChange={set("stop_price")}
                    placeholder="485.00"
                    required
                    className={inputCls}
                  />
                </Field>
              </Row>
              <Row>
                <Field label="Size (shares)">
                  <input
                    data-testid="pf-size"
                    type="number"
                    step="1"
                    value={form.size_shares || ""}
                    onChange={set("size_shares")}
                    placeholder="50"
                    className={inputCls}
                  />
                </Field>
                <Field label="Entry Date">
                  <input
                    data-testid="pf-entry-date"
                    type="date"
                    value={form.entry_date || ""}
                    onChange={set("entry_date")}
                    className={inputCls}
                  />
                </Field>
              </Row>
              <Row>
                <Field
                  label={
                    <span className="inline-flex items-center gap-1">
                      Grade at Entry <InfoDot k="Grade" />
                    </span>
                  }
                >
                  <input
                    data-testid="pf-grade"
                    value={form.entry_grade || ""}
                    onChange={set("entry_grade")}
                    placeholder="B+"
                    className={inputCls}
                  />
                </Field>
                <Field
                  label={
                    <span className="inline-flex items-center gap-1">
                      Regime <InfoDot k="Regime" />
                    </span>
                  }
                >
                  <select
                    data-testid="pf-regime"
                    value={form.regime_at_entry || ""}
                    onChange={set("regime_at_entry")}
                    className={inputCls}
                  >
                    <option value="">—</option>
                    <option value="RISK_ON">RISK_ON</option>
                    <option value="CAUTION">CAUTION</option>
                    <option value="RISK_OFF">RISK_OFF</option>
                  </select>
                </Field>
              </Row>
              <Field label="State">
                <select
                  data-testid="pf-state"
                  value={form.state || "ACTIVE"}
                  onChange={set("state")}
                  className={inputCls}
                >
                  <option value="ACTIVE">ACTIVE — already filled</option>
                  <option value="PENDING_CONFIRM">PENDING_CONFIRM — awaiting confirmation</option>
                </select>
              </Field>
              <Field label="Notes">
                <textarea
                  data-testid="pf-notes"
                  value={form.notes || ""}
                  onChange={set("notes")}
                  rows={2}
                  placeholder="why this trade — setup, catalyst, risk level…"
                  className={inputCls}
                />
              </Field>
              {preview}
            </>
          )}

          {mode === "edit" && (
            <>
              <Field
                label={
                  <span className="inline-flex items-center gap-1">
                    Stop Price (trail) <InfoDot k="Stop" />
                  </span>
                }
              >
                <input
                  data-testid="pf-edit-stop"
                  type="number"
                  step="0.01"
                  value={form.stop_price || ""}
                  onChange={set("stop_price")}
                  className={inputCls}
                />
              </Field>
              <Field label="Size (shares)">
                <input
                  data-testid="pf-edit-size"
                  type="number"
                  step="1"
                  value={form.size_shares || ""}
                  onChange={set("size_shares")}
                  className={inputCls}
                />
              </Field>
              <Field label="State">
                <select
                  data-testid="pf-edit-state"
                  value={form.state || "ACTIVE"}
                  onChange={set("state")}
                  className={inputCls}
                >
                  <option value="ACTIVE">ACTIVE</option>
                  <option value="PENDING_CONFIRM">PENDING_CONFIRM</option>
                  <option value="DISCARDED">DISCARDED</option>
                </select>
              </Field>
              <Field label="Notes">
                <textarea
                  data-testid="pf-edit-notes"
                  value={form.notes || ""}
                  onChange={set("notes")}
                  rows={3}
                  className={inputCls}
                />
              </Field>
            </>
          )}

          {mode === "exit" && (
            <>
              <Row>
                <Field label="Exit Price" required>
                  <input
                    data-testid="pf-exit-price"
                    type="number"
                    step="0.01"
                    value={form.exit_price || ""}
                    onChange={set("exit_price")}
                    required
                    className={inputCls}
                  />
                </Field>
                <Field label="Exit Date">
                  <input
                    data-testid="pf-exit-date"
                    type="date"
                    value={form.exit_date || ""}
                    onChange={set("exit_date")}
                    className={inputCls}
                  />
                </Field>
              </Row>
              <Field label="Reason">
                <select
                  data-testid="pf-exit-state"
                  value={form.state || "EXITED_MANUAL"}
                  onChange={set("state")}
                  className={inputCls}
                >
                  <option value="EXITED_MANUAL">EXITED_MANUAL — discretionary close</option>
                  <option value="EXITED_STOP">EXITED_STOP — stop hit</option>
                  <option value="EXITED_EXTENDED">EXITED_EXTENDED — booked, too extended</option>
                  <option value="EXITED_DECAY">EXITED_DECAY — grade decay</option>
                </select>
              </Field>
              <Field label="Notes">
                <textarea
                  data-testid="pf-exit-notes"
                  value={form.notes || ""}
                  onChange={set("notes")}
                  rows={2}
                  placeholder="why you closed — trigger, market context…"
                  className={inputCls}
                />
              </Field>
              {preview}
            </>
          )}

          {err && (
            <div className="border border-bear/40 bg-bear/5 px-3 py-2 text-[11px] text-bear">
              {err}
            </div>
          )}
        </div>

        <footer className="flex items-center justify-end gap-2 border-t border-borderDefault px-4 py-3">
          <Button onClick={onClose} variant="ghost" testId="pf-cancel">
            Cancel
          </Button>
          <Button
            onClick={submit}
            variant={mode === "exit" ? "danger" : "primary"}
            testId="pf-submit"
            disabled={busy}
          >
            {busy ? <Loader2 size={11} className="animate-spin" /> : null}
            {mode === "add" && (busy ? "Saving" : "Add Position")}
            {mode === "edit" && (busy ? "Saving" : "Save Changes")}
            {mode === "exit" && (busy ? "Closing" : "Close Position")}
          </Button>
        </footer>
      </form>
    </div>
  );
}

const inputCls =
  "w-full border border-borderDefault bg-page px-2 py-1.5 font-mono text-[12px] text-textPrimary placeholder-textMuted focus:border-bull focus:outline-none";

function Field({ label, children, required }) {
  return (
    <label className="block">
      <span className="mb-1 block text-[10px] uppercase tracking-overline text-textMuted">
        {label}
        {required && <span className="ml-1 text-bear">*</span>}
      </span>
      {children}
    </label>
  );
}

function Row({ children }) {
  return <div className="grid grid-cols-2 gap-3">{children}</div>;
}

function Stat({ label, value, accent }) {
  return (
    <div className="bg-surface px-3 py-2">
      <div className="text-[9px] uppercase tracking-overline text-textMuted">
        {label}
      </div>
      <div className={classNames("mt-0.5 font-mono tnum text-textPrimary", accent)}>
        {value}
      </div>
    </div>
  );
}
