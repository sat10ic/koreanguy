import { useEffect, useState } from "react";
import { getRegimeHistory } from "../api.js";
import InfoDot from "./InfoDot.jsx";
import Read from "./Read.jsx";

/**
 * BreadthGrid — MBI-style color-coded breadth grid (JOB 2, reference:
 * MarketSmith MBI). Absorbs/replaces the old 20-session day-color calendar
 * (BreadthSparkline's day-color strip) — this is the one grid, not two.
 *
 * Columns = last ~20 sessions (oldest -> newest, dated at the ends).
 * Rows = XP band, 4.5R, 20R, 50R, day-color — each cell a small square
 * colored by that metric's band, using the exact JOB-1 thresholds:
 *   20R  >=75 green / 50-75 white / <50 red
 *   50R  >=85 green / 60-85 white / <60 red
 *   4.5R <50 red / 50-200 white / 200-400 green / >=400 orange
 *   day-color  >=+3 GREEN / <=-3 RED / else WHITE (mbi_day_color, computed server-side)
 *   XP band  <15 low / 15-40 building / 40-100 strong / >100 extreme
 *
 * Data: /api/regime/history?days=20 — already returns xp_value, r10, r20,
 * r50, r4p5, mbi_day_color, warning_day per row (extended in this pass).
 */
const DAYS = 20;

const BAND_SQUARE_CLS = {
  GREEN: "bg-bull border-bull",
  WHITE: "bg-muted-bg border-muted-border",
  RED: "bg-bear border-bear",
  ORANGE: "bg-warn border-warn",
  NONE: "bg-hairline2 border-hairline",
};

function bandRatio(value) {
  if (value == null) return null;
  if (value >= 75) return "GREEN";
  if (value >= 50) return "WHITE";
  return "RED";
}
function bandR50(value) {
  if (value == null) return null;
  if (value >= 85) return "GREEN";
  if (value >= 60) return "WHITE";
  return "RED";
}
function bandR4p5(value) {
  if (value == null) return null;
  if (value < 50) return "RED";
  if (value < 200) return "WHITE";
  if (value < 400) return "GREEN";
  return "ORANGE";
}
function bandXp(value) {
  if (value == null) return null;
  if (value < 15) return "RED"; // low energy reads as the "weak" square
  if (value < 40) return "WHITE"; // building
  if (value < 100) return "GREEN"; // strong
  return "ORANGE"; // extreme
}
function bandDayColor(value) {
  if (value === "GREEN" || value === "RED" || value === "WHITE") return value;
  return null;
}

const ROWS = [
  { key: "xp", label: "XP band", term: "xp-band", get: (r) => r.xp_value, band: bandXp, fmt: (v) => v.toFixed(0) },
  { key: "r4p5", label: "4.5R", term: "burst", get: (r) => r.r4p5, band: bandR4p5, fmt: (v) => v.toFixed(0) },
  { key: "r20", label: "20R", term: "r20", get: (r) => r.r20, band: bandRatio, fmt: (v) => v.toFixed(0) },
  { key: "r50", label: "50R", term: "r50", get: (r) => r.r50, band: bandR50, fmt: (v) => v.toFixed(0) },
  {
    key: "day",
    label: "Day color",
    term: "mbi",
    get: (r) => r.mbi_day_color,
    band: bandDayColor,
    fmt: (v) => v,
  },
];

export default function BreadthGrid() {
  const [state, setState] = useState({ loading: true, error: null, rows: [] });

  useEffect(() => {
    let cancelled = false;
    setState({ loading: true, error: null, rows: [] });
    getRegimeHistory(DAYS)
      .then((d) => !cancelled && setState({ loading: false, error: null, rows: d?.rows || [] }))
      .catch((e) => !cancelled && setState({ loading: false, error: e.message, rows: [] }));
    return () => {
      cancelled = true;
    };
  }, []);

  if (state.loading) return <GridSkeleton />;
  if (state.error) {
    return (
      <EmptyBlock title="Couldn't reach the API">
        Make sure the backend is running: <code>python -m manas_os.api</code>
      </EmptyBlock>
    );
  }
  if (state.rows.length === 0) {
    return (
      <EmptyBlock title="No breadth history yet">
        Run the pipeline to populate:{" "}
        <code>python manas.py run-eod --date YYYY-MM-DD</code>
      </EmptyBlock>
    );
  }

  const rows = state.rows;
  const readLine = buildReadLine(rows);

  return (
    <section data-testid="breadth-grid" className="mt-4 border border-hairline bg-card p-3">
      <div className="mb-2">
        <span className="flex items-center font-mono text-[12px] font-bold uppercase tracking-overline text-ink">
          Breadth grid — last {rows.length} sessions
          <InfoDot term="mbi" />
        </span>
        <p className="mt-0.5 font-sans text-[11px] leading-snug text-ink3">
          Each column is one trading day; each square is that day's band for the metric on its row.
          Green = strong, white = neutral, red = weak, orange = extreme burst.
        </p>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full border-collapse">
          <tbody>
            {ROWS.map((rowDef) => (
              <tr key={rowDef.key}>
                <td className="whitespace-nowrap pr-2 align-middle font-mono text-[9px] uppercase tracking-overline text-ink3">
                  {rowDef.label}
                </td>
                {rows.map((r) => {
                  const raw = rowDef.get(r);
                  const band = rowDef.band(raw);
                  const title =
                    raw == null
                      ? `${r.snapshot_date}: no data`
                      : `${r.snapshot_date}: ${rowDef.label} ${rowDef.fmt(raw)}`;
                  return (
                    <td key={r.snapshot_date + rowDef.key} className="px-[1px] py-[1px]">
                      <div
                        title={title}
                        data-testid={`breadth-grid-cell-${rowDef.key}`}
                        className={
                          "h-4 w-4 border " + (BAND_SQUARE_CLS[band] || BAND_SQUARE_CLS.NONE)
                        }
                      />
                    </td>
                  );
                })}
              </tr>
            ))}
            <tr>
              <td />
              {rows.map((r, i) => (
                <td key={r.snapshot_date + "-date"} className="px-[1px] pt-0.5">
                  {(i === 0 || i === rows.length - 1) && (
                    <span className="block whitespace-nowrap font-mono text-[7px] text-ink3">
                      {shortDate(r.snapshot_date)}
                    </span>
                  )}
                </td>
              ))}
            </tr>
          </tbody>
        </table>
      </div>

      <Legend />
      <Read band="info">{readLine}</Read>
    </section>
  );
}

function Legend() {
  return (
    <div className="mt-2 flex flex-wrap items-center gap-3 font-mono text-[9px] uppercase tracking-overline text-ink3">
      <LegendSwatch cls={BAND_SQUARE_CLS.GREEN} label="Strong" />
      <LegendSwatch cls={BAND_SQUARE_CLS.WHITE} label="Neutral" />
      <LegendSwatch cls={BAND_SQUARE_CLS.RED} label="Weak" />
      <LegendSwatch cls={BAND_SQUARE_CLS.ORANGE} label="Extreme" />
    </div>
  );
}

function LegendSwatch({ cls, label }) {
  return (
    <span className="flex items-center gap-1">
      <span className={"inline-block h-2.5 w-2.5 border " + cls} />
      {label}
    </span>
  );
}

function shortDate(iso) {
  if (!iso) return "";
  const parts = iso.split("-");
  return parts.length === 3 ? `${parts[1]}/${parts[2]}` : iso;
}

// A plain-English caption comparing the most recent day's warning-day flag
// and day-color to the rest of the window, so the grid isn't just squares.
function buildReadLine(rows) {
  const latest = rows[rows.length - 1];
  const warningDays = rows.filter((r) => Boolean(r.warning_day)).length;
  const redDays = rows.filter((r) => r.mbi_day_color === "RED").length;
  const greenDays = rows.filter((r) => r.mbi_day_color === "GREEN").length;
  const latestColor = (latest?.mbi_day_color || "unknown").toLowerCase();
  return (
    `Most recent session was ${latestColor}. Over the last ${rows.length} sessions: ` +
    `${greenDays} green, ${redDays} red, ${warningDays} warning day${warningDays === 1 ? "" : "s"} ` +
    `(3+ of the 6 breadth checks turned red).`
  );
}

function GridSkeleton() {
  return (
    <div className="mt-4">
      <div className="mb-2 h-3 w-56 animate-pulse rounded bg-hairline2" />
      <div className="h-24 w-full animate-pulse rounded bg-hairline2" />
    </div>
  );
}

function EmptyBlock({ title, children }) {
  return (
    <div className="mt-4 border border-dashed border-hairline px-4 py-6 text-center">
      <div className="font-mono text-[12px] font-semibold text-ink2">{title}</div>
      <div className="mt-1 font-sans text-[12px] leading-snug text-ink3">{children}</div>
    </div>
  );
}
