const STATE_DOT = {
  bull: "bg-bull-dot",
  warn: "bg-warn-dot",
  bear: "bg-bear-dot",
  muted: "bg-ink3",
};

const SHADE = {
  bull: "bg-bull-bg",
  bear: "bg-bear-bg",
};

const BAND = {
  bull: "border-bull-border bg-bull-bg",
  warn: "border-warn-border bg-warn-bg",
  bear: "border-bear-border bg-bear-bg",
  info: "border-info-border bg-info-bg",
  muted: "border-hairline bg-card",
};

export function PosterCanvas({ children, className = "", ...props }) {
  return (
    <section {...props} className={`relative overflow-hidden bg-bg text-ink ${className}`}>
      {/* Grid disabled for now — it was making the UI busier without the full poster treatment */}
      {/* <div className="pointer-events-none absolute inset-0 opacity-[0.28] [background-image:linear-gradient(#d9ded7_1px,transparent_1px),linear-gradient(90deg,#d9ded7_1px,transparent_1px)] [background-size:28px_28px]" /> */}
      <div className="relative space-y-4">{children}</div>
    </section>
  );
}

export function PosterBand({ title, kicker, children, state = "muted", action = null, className = "" }) {
  return (
    <section className={`border p-3 md:p-4 ${BAND[state] || BAND.muted} ${className}`}>
      {(title || kicker || action) && (
        <div className="mb-3 flex flex-wrap items-start justify-between gap-2">
          <div>
            {kicker && <div className="font-mono text-[10px] font-bold uppercase tracking-overline text-ink3">{kicker}</div>}
            {title && <div className="font-display text-[18px] uppercase leading-none tracking-normal text-ink md:text-[22px]">{title}</div>}
          </div>
          {action}
        </div>
      )}
      {children}
    </section>
  );
}

export function AnnotatedChart({ children, note, className = "" }) {
  return (
    <div className={`relative min-h-40 overflow-hidden border border-hairline bg-raised ${className}`}>
      {children}
      {note && (
        <div className="absolute left-3 top-3 max-w-[24ch] border border-ink bg-card/95 px-2 py-1 font-mono text-[10px] uppercase tracking-overline text-ink">
          {note}
        </div>
      )}
    </div>
  );
}

/**
 * MetricBar — a single 0-100 (or arbitrary max) value as a labeled horizontal
 * bar instead of plain text. Use for percentile/percentage evidence (RS,
 * absolute strength, EPS growth, delivery) so the card reads as visual/metric
 * rather than a wall of inline numbers.
 */
export function MetricBar({ label, value, max = 100, unit = "", tone = "info", className = "" }) {
  const toneCls = {
    bull: "bg-bull",
    warn: "bg-warn",
    bear: "bg-bear",
    info: "bg-info",
  }[tone] || "bg-info";
  const pct = value == null ? 0 : Math.max(0, Math.min(100, (Number(value) / max) * 100));
  return (
    <div className={className}>
      <div className="mb-0.5 flex items-baseline justify-between font-mono text-[9px] uppercase tracking-overline text-ink3">
        <span>{label}</span>
        <span className="text-ink2 tabular-nums">{value == null ? "—" : `${value}${unit}`}</span>
      </div>
      <div className="h-1.5 w-full overflow-hidden bg-hairline2">
        <div className={`h-full ${toneCls}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

export function MetricTape({ items = [] }) {
  return (
    <div className="grid gap-1 sm:grid-cols-2 lg:grid-cols-5">
      {items.map((item) => (
        <div key={item.label} className={`border px-3 py-2 ${BAND[item.state] || BAND.muted}`}>
          <div className="font-mono text-[9px] uppercase tracking-overline text-ink3">{item.label}</div>
          <div className="mt-1 font-display text-[18px] uppercase leading-none text-ink">{item.value}</div>
          {item.sub && <div className="mt-1 font-sans text-[11px] leading-tight text-ink3">{item.sub}</div>}
        </div>
      ))}
    </div>
  );
}

export function StateRibbon({ items = [], getState = (item) => item.state || "muted" }) {
  return (
    <div className="flex min-h-7 overflow-hidden border border-hairline bg-card">
      {items.map((item, index) => {
        const state = getState(item);
        const cls = {
          bull: "bg-bull",
          warn: "bg-warn",
          bear: "bg-bear",
          info: "bg-info",
          muted: "bg-ink3",
        }[state] || "bg-ink3";
        return (
          <div
            key={item.date || item.label || index}
            title={item.title || item.date || item.label}
            className={`min-w-2 flex-1 border-r border-paper/40 ${cls}`}
          />
        );
      })}
    </div>
  );
}

export function VisualCard({ children, state = "muted", className = "", onClick }) {
  const Tag = onClick ? "button" : "article";
  return (
    <Tag
      type={onClick ? "button" : undefined}
      onClick={onClick}
      className={`block w-full border p-3 text-left transition hover:-translate-y-0.5 ${BAND[state] || BAND.muted} ${className}`}
    >
      {children}
    </Tag>
  );
}

export function SectionBadge({ label, state = "muted" }) {
  return (
    <div className="inline-flex items-center gap-2 rounded-full bg-ink px-4 py-2">
      <span className={"h-2.5 w-2.5 rounded-full " + (STATE_DOT[state] || STATE_DOT.muted)} />
      <span className="font-display text-[12px] uppercase leading-none tracking-normal text-white">
        {label}
      </span>
    </div>
  );
}

export function Verdict({ children }) {
  return (
    <div className="inline-block border-b-[3px] border-ink pb-1 font-display text-[22px] uppercase leading-[1.05] tracking-normal text-ink md:text-[28px]">
      {children}
    </div>
  );
}

export function Caption({ children }) {
  return (
    <p className="mt-2 max-w-[36ch] font-body text-[13px] leading-snug text-ink2">
      {children}
    </p>
  );
}

export function MiniTable({ columns = [], rows = [], shade }) {
  return (
    <div className="overflow-hidden border border-hairline bg-card font-mono text-[10px] uppercase tracking-overline text-ink2">
      <div className="grid" style={{ gridTemplateColumns: `repeat(${columns.length || 1}, minmax(0, 1fr))` }}>
        {columns.map((column) => (
          <div key={column} className="border-b border-hairline bg-raised px-2 py-1 text-ink3">
            {column}
          </div>
        ))}
        {rows.map((row, rowIndex) =>
          columns.map((column) => {
            const value = row[column] ?? row[column.toLowerCase()] ?? "-";
            const tone = shade?.(value, column, row, rowIndex);
            return (
              <div key={`${rowIndex}-${column}`} className={"border-t border-hairline2 px-2 py-1 tabular-nums " + (SHADE[tone] || "")}>
                {value}
              </div>
            );
          }),
        )}
      </div>
    </div>
  );
}

/**
 * ProximityBar — visual density for gate distance / "what would it take".
 * Shows a compact horizontal bar + caption for how far a near-miss is from passing.
 * severity: "caution" | "hard" | "ok" maps to warn/bear/bull bands.
 */
export function ProximityBar({ value, unit = "", severity = "caution", label = "", className = "" }) {
  const isHard = severity === "hard";
  const isOk = severity === "ok" || (value != null && value <= 0);
  const band = isHard ? "bear" : isOk ? "bull" : "warn";
  const pct = value == null ? 40 : Math.max(8, Math.min(92, 50 + (Number(value) * (isHard ? -12 : 8))));
  return (
    <div className={`border border-hairline bg-raised p-2 ${className}`}>
      <div className="flex items-center justify-between font-mono text-[9px] uppercase tracking-overline text-ink3 mb-1">
        <span>proximity</span>
        <span className="text-ink">{value == null ? "—" : `${value}${unit}`}</span>
      </div>
      <div className="h-2 w-full bg-hairline2 overflow-hidden rounded">
        <div
          className={`h-2 ${isHard ? "bg-bear" : isOk ? "bg-bull" : "bg-warn"}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      {label && <div className="mt-1 font-sans text-[10px] leading-snug text-ink2">{label}</div>}
    </div>
  );
}

/**
 * Callout — lightweight hand-annotation style label for poster charts / cards.
 * Use for "hand-annotated feel" per AESTHETIC_BAR without adding shadows/motion.
 */
export function Callout({ children, className = "" }) {
  return (
    <div className={`inline-block border border-ink bg-card/95 px-2 py-0.5 font-mono text-[10px] uppercase tracking-overline text-ink ${className}`}>
      {children}
    </div>
  );
}
