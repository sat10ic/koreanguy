import { useDensity } from "../DensityContext.jsx";

const CHIP = "AI opinion - advisory, not a signal";

export default function AdvisorStrip({ notes = [], scope, symbol = null, className = "" }) {
  const { density } = useDensity();
  const filtered = notes.filter((note) => {
    if (scope && note.scope !== scope) return false;
    if (symbol == null) return !note.symbol;
    return String(note.symbol || "").toUpperCase() === String(symbol).toUpperCase();
  });
  if (!filtered.length) return null;
  const expanded = density === "expert";
  return (
    <div className={"border border-hairline bg-raised px-3 py-2 text-ink2 " + className}>
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-mono text-[10px] font-bold uppercase tracking-overline text-ink3">ADVISOR</span>
        <span className="rounded-chip border border-hairline bg-card px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-overline text-ink3">
          {CHIP}
        </span>
      </div>
      <div className="mt-1 space-y-1">
        {filtered.map((note) => (
          <div key={`${note.note_date}-${note.scope}-${note.symbol || "market"}`} className="font-sans text-[12px] leading-snug text-ink2">
            <span className="font-mono text-[10px] font-bold uppercase tracking-overline text-ink">{note.stance}: </span>
            {note.note}
            {expanded && note.watch_for ? <span className="text-ink3"> Watch: {note.watch_for}</span> : null}
          </div>
        ))}
      </div>
    </div>
  );
}
