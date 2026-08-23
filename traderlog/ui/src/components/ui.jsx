// Shared primitives. Kept in one file at this size -- splitting six small
// components across six files costs more to read than it saves.
import React from "react";

export function Panel({ title, cite, right, children, tone }) {
  return (
    <section className={`panel${tone ? ` panel-${tone}` : ""}`}>
      {(title || right) && (
        <header className="panel-head">
          <span className="panel-title">{title}</span>
          {cite && <span className="panel-cite">{cite}</span>}
          {right && <span className="panel-right">{right}</span>}
        </header>
      )}
      <div className="panel-body">{children}</div>
    </section>
  );
}

export function Chip({ kind, children }) {
  return <span className={`chip chip-${kind || "default"}`}>{children}</span>;
}

// Confidence as a mono two-decimal value, never a percentage -- it is a model
// confidence, not a probability of profit, and showing "91%" invites that read.
export function Conf({ value }) {
  if (value === null || value === undefined) return <span className="conf">--</span>;
  return <span className="conf mono">{Number(value).toFixed(2)}</span>;
}

// Precision is adaptive by default, because a fixed 0dp silently destroyed real
// evidence: a VCPSwing fill price of 39.05 -- recovered from a broker order
// screenshot -- rendered as "39". On a sub-100 stock the paise are material, and
// rounding away a number the trader actually stated is the same class of error
// as inventing one. Above 100 the paise are noise (DIXON at 14,200), so they go.
// Pass `dp` explicitly to override.
function autoDp(value) {
  const n = Math.abs(Number(value));
  if (n === 0) return 0;
  if (n < 100) return 2;
  return 0;
}

export function Num({ value, prefix = "", suffix = "", dp, dash = "not stated" }) {
  if (value === null || value === undefined) return <span className="unstated">{dash}</span>;
  const places = dp === undefined ? autoDp(value) : dp;
  return (
    <span className="mono">
      {prefix}
      {Number(value).toLocaleString("en-IN", {
        minimumFractionDigits: places,
        maximumFractionDigits: places,
      })}
      {suffix}
    </span>
  );
}

export function Pct({ value }) {
  if (value === null || value === undefined) return <span className="unstated">—</span>;
  const n = Number(value);
  return (
    <span className={`mono ${n >= 0 ? "pos" : "neg"}`}>
      {n >= 0 ? "+" : ""}
      {n.toFixed(1)}%
    </span>
  );
}

// `label` names what the bar encodes ("@handle agreement rate") so the
// aria-label states a finding rather than a bare number. Optional -- falls
// back to the raw value so existing callers that don't pass it still get an
// accessible (if generic) label rather than none at all. F13.
export function Bar({ pct, tone = "teal", width = 160, label }) {
  const w = Math.max(0, Math.min(100, Number(pct) || 0));
  const aria = label ? `${label}: ${w}%` : `${w}%`;
  return (
    <span className="bar" style={{ width }} role="img" aria-label={aria}>
      <span className={`bar-fill bar-${tone}`} style={{ width: `${w}%` }} />
    </span>
  );
}

// Mutually exclusive view switch, preferred over a <select> wherever there
// are <=4 options -- it shows the alternatives without a click.
export function Segmented({ options, value, onChange }) {
  return (
    <div className="segmented" role="group">
      {(options || []).map((opt) => (
        <button
          key={opt}
          type="button"
          className={`segmented-btn${opt === value ? " active" : ""}`}
          aria-pressed={opt === value}
          onClick={() => onChange && onChange(opt)}
        >
          {opt}
        </button>
      ))}
    </div>
  );
}

// Sortable column header with a caret -- tables are dense, sorting is the
// primary interaction.
export function SortableTh({ label, active, dir, onClick, className }) {
  return (
    <th
      className={`sortable-th${active ? " active" : ""}${className ? ` ${className}` : ""}`}
      onClick={onClick}
      role="columnheader"
      aria-sort={active ? (dir === "asc" ? "ascending" : "descending") : "none"}
    >
      <button type="button" className="sortable-th-btn">
        {label}
        <span className="caret" aria-hidden="true">
          {active ? (dir === "asc" ? "▲" : "▼") : "▵"}
        </span>
      </button>
    </th>
  );
}

// A real disclosure caret. Replaces a whole-row click with no affordance.
export function Disclosure({ open, onToggle }) {
  return (
    <button
      type="button"
      className={`disclosure${open ? " open" : ""}`}
      aria-expanded={!!open}
      aria-label={open ? "collapse" : "expand"}
      onClick={onToggle}
    >
      <span className="caret" aria-hidden="true">▸</span>
    </button>
  );
}

export function Empty({ children }) {
  return <p className="empty">{children}</p>;
}

export function Loading() {
  return <p className="empty">loading…</p>;
}

// Shown whenever any payload reports is_mock. A tool that looks real while
// showing invented data is the specific failure this project exists to avoid,
// so this is not dismissible.
export function MockBanner({ show }) {
  if (!show) return null;
  return (
    <div className="mock-banner">
      SHOWING MOCK DATA — nothing here has been ingested. Seeded by{" "}
      <code>traderlog/seed_mock.py</code>. Handles, prices and results are invented.
    </div>
  );
}

export function ErrorBox({ error }) {
  if (!error) return null;
  return (
    <div className="error-box">
      <strong>Could not load.</strong> {String(error.message || error)}
      <div className="error-hint">Is the API running? <code>python traderlog/run_api.py</code></div>
    </div>
  );
}

// Small hook so every screen handles loading/error the same way.
export function useApi(fn, deps = []) {
  const [data, setData] = React.useState(null);
  const [error, setError] = React.useState(null);
  React.useEffect(() => {
    let alive = true;
    setError(null);
    fn()
      .then((d) => alive && setData(d))
      .catch((e) => alive && setError(e));
    return () => {
      alive = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
  return { data, error };
}

export function fmtDate(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso.slice(0, 10);
  return d.toLocaleDateString("en-IN", { day: "2-digit", month: "short" });
}

export function fmtTime(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit", hour12: false });
}
