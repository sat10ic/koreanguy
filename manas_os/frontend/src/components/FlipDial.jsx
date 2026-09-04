import { useState } from "react";
import InfoDot from "./InfoDot.jsx";
import MiniSpark from "./MiniSpark.jsx";

/**
 * FlipDial — replaces the flat StripCard for headline numbers (design §1.3).
 * Face 1 (default): big headline number + label + InfoDot.
 * Face 2 (click the tile or the flip icon): a mini-sparkline of recent
 * history + a signed delta chip vs N sessions ago + first/last values.
 * Same tile box both faces — no layout shift.
 *
 * `history` is an array of numbers (oldest -> newest), already sliced to the
 * window the caller wants (design: 10-15 sessions). Pass an empty/short
 * array (or omit) to render "trend unavailable" — used today for 4.5R until
 * a caller wires real history (the r4p5 field is now returned by
 * /api/regime/history, see PHASE A backend change).
 */
export default function FlipDial({ label, term, value, fmt, history = [], sub = null }) {
  const [flipped, setFlipped] = useState(false);
  const hasHistory = history.filter((v) => v != null).length >= 2;

  return (
    <div
      data-testid={`flip-dial-${term}`}
      className="flex flex-col gap-1 border border-hairline bg-card p-2"
    >
      <div className="flex items-center justify-between">
        <span className="flex items-center font-mono text-[9px] uppercase tracking-overline text-ink3">
          {label}
          {term && <InfoDot term={term} />}
        </span>
        <button
          type="button"
          onClick={() => setFlipped((v) => !v)}
          data-testid={`flip-dial-${term}-toggle`}
          title="Toggle trend view"
          className="font-mono text-[10px] text-ink3 hover:text-ink"
        >
          {flipped ? "◂" : "▸flip"}
        </button>
      </div>

      {!flipped ? (
        <div className="flex items-baseline gap-1.5">
          <span className="font-mono text-[20px] font-bold tabular-nums text-ink">
            {fmt ? fmt(value) : fmtNum(value)}
          </span>
          {sub}
        </div>
      ) : hasHistory ? (
        <FlipFace history={history} />
      ) : (
        <span className="font-mono text-[11px] text-ink3">trend unavailable</span>
      )}
    </div>
  );
}

function FlipFace({ history }) {
  const clean = history.filter((v) => v != null);
  const first = clean[0];
  const last = clean[clean.length - 1];
  const delta = last - first;
  const positive = delta >= 0;

  return (
    <div className="flex items-center gap-2">
      <div className="h-7 w-16">
        <MiniSpark values={history} />
      </div>
      <div className="flex flex-col">
        <span
          className={"font-mono text-[11px] font-bold tabular-nums " + (positive ? "text-bull" : "text-bear")}
          title={`vs ${clean.length} sessions ago`}
        >
          {positive ? "▲+" : "▼"}
          {Math.abs(delta).toFixed(1)}
        </span>
        <span className="font-mono text-[9px] tabular-nums text-ink3">
          {first.toFixed(0)} → {last.toFixed(0)}
        </span>
      </div>
    </div>
  );
}

function fmtNum(n) {
  if (n == null) return "—";
  return typeof n === "number" ? n.toFixed(1) : String(n);
}
