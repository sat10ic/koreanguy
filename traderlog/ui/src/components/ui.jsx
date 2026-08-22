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

export function Num({ value, prefix = "", suffix = "", dp = 0, dash = "not stated" }) {
  if (value === null || value === undefined) return <span className="unstated">{dash}</span>;
  return (
    <span className="mono">
      {prefix}
      {Number(value).toLocaleString("en-IN", {
        minimumFractionDigits: dp,
        maximumFractionDigits: dp,
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

export function Bar({ pct, tone = "teal", width = 160 }) {
  const w = Math.max(0, Math.min(100, Number(pct) || 0));
  return (
    <span className="bar" style={{ width }}>
      <span className={`bar-fill bar-${tone}`} style={{ width: `${w}%` }} />
    </span>
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
