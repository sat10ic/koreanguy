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
