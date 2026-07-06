import { useEffect, useState } from "react";
import { getRegimeSectors, getSectorStocks, getIndustryStocks } from "../api.js";
import DataStamp from "./DataStamp.jsx";
import SymbolChip from "./SymbolChip.jsx";

/**
 * SectorsThemesPanel — the regime page's Sectors & Themes leaderboard.
 *
 * Two tabs (top-right, pill style):
 *   • Sectors — ~15 NSE sectors from ChartsMaze sector-analytics-Relative
 *               Strength. Horizontal bar fill ∝ RS%; band by threshold.
 *   • Themes  — finer industries from industry-analytics.csv. Bar fill ∝
 *               1M performance; green ≥0 / red <0; 1M & 3M values on right.
 *
 * Each row = label (left) + horizontal bar + value(s) — the motif from the
 * reference photo, rendered in the committed design language (mono, hairline,
 * functional color only).
 *
 * Honors the §7 state matrix: loading skeleton, empty ("no data"), the normal
 * populated view, and a stale banner when `as_of` is older than ~3 calendar
 * days (covers a long weekend; older than that the data is presumed stale and
 * the banner becomes loud, per design §7).
 */
const TABS = [
  { id: "sectors", label: "Sectors" },
  { id: "themes", label: "Themes" },
];
const TIMEFRAMES = ["1d", "1w", "1m", "3m", "6m"];

export default function SectorsThemesPanel({ onSymbolSelect }) {
  const [tab, setTab] = useState("sectors");
  const [timeframe, setTimeframe] = useState("1m");
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    getRegimeSectors()
      .then((d) => !cancelled && setData(d))
      .catch((e) => !cancelled && setError(e.message))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <section
      data-testid="sectors-themes-panel"
      className="max-w-content mx-auto border border-hairline rounded-card bg-card"
    >
      {/* Header */}
      <header className="flex items-center justify-between border-b border-hairline px-4 py-3">
        <div className="flex items-center gap-2">
          <span className="inline-block h-1.5 w-1.5 rounded-full bg-info-dot" />
          <h2 className="font-mono text-[13px] font-bold tracking-tight">
            Sectors &amp; Themes
          </h2>
          <span className="font-mono text-[10px] uppercase tracking-overline text-ink3">
            · ChartsMaze
          </span>
        </div>
        <div className="flex flex-wrap items-center justify-end gap-1">
          {TIMEFRAMES.map((tf) => (
            <button
              key={tf}
              onClick={() => setTimeframe(tf)}
              data-testid={`theme-timeframe-${tf}`}
              className={
                "border px-2 py-0.5 font-mono text-[10px] uppercase tracking-overline transition-colors " +
                (timeframe === tf
                  ? "border-info text-info"
                  : "border-hairline text-ink2 hover:text-ink")
              }
            >
              {tf}
            </button>
          ))}
          {TABS.map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              data-testid={`tab-${t.id}`}
              className={
                "border px-2 py-0.5 font-mono text-[10px] uppercase tracking-overline transition-colors " +
                (tab === t.id
                  ? "border-bull text-bull"
                  : "border-hairline text-ink2 hover:text-ink")
              }
            >
              {t.label}
            </button>
          ))}
        </div>
      </header>

      {/* Body */}
      <div className="px-4 py-3">
        {loading ? (
          <SkeletonRows />
        ) : error ? (
          <EmptyState title="Couldn't reach the API">
            Make sure the backend is running: <code>python -m manas_os.api</code>
          </EmptyState>
        ) : !data?.available ? (
          <EmptyState title="No sector data yet">
            Run the pipeline to populate:{" "}
            <code>python manas.py run-eod --date YYYY-MM-DD</code>
          </EmptyState>
        ) : (
          <>
            {isStale(data.as_of) && <StaleBanner asOf={data.as_of} />}
            <div className={isStale(data.as_of) ? "opacity-60" : ""}>
              {tab === "sectors" ? (
                <SectorsList sectors={data.sectors} timeframe={timeframe} onSymbolSelect={onSymbolSelect} />
              ) : (
                <ThemesList
                  industries={data.industries}
                  timeframe={timeframe}
                  unavailable={data.unavailable_timeframes || {}}
                  onSymbolSelect={onSymbolSelect}
                />
              )}
            </div>
          </>
        )}

        {data?.available && <DataStamp />}
      </div>
    </section>
  );
}

// ─── Staleness ──────────────────────────────────────────────────────────────
// `as_of` older than 3 calendar days → stale (covers a long weekend; beyond
// that the snapshot is presumed out of date). Design §7: stale must be loud.
function isStale(asOf) {
  if (!asOf) return false;
  const ageMs = Date.now() - new Date(asOf + "T00:00:00").getTime();
  return ageMs > 3 * 24 * 60 * 60 * 1000;
}

function StaleBanner({ asOf }) {
  return (
    <div
      data-testid="stale-banner"
      className="mb-3 flex items-center gap-2 border border-warn-border bg-warn-bg px-3 py-2"
    >
      <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-warn-dot" />
      <span className="font-mono text-[11px] font-bold uppercase tracking-overline text-warn">
        Stale data
      </span>
      <span className="font-sans text-[12px] text-ink2">
        Last snapshot {asOf} — re-run the pipeline for fresh numbers.
      </span>
    </div>
  );
}

// ─── Sectors tab ────────────────────────────────────────────────────────────
function SectorsList({ sectors, timeframe, onSymbolSelect }) {
  if (sectors.length === 0)
    return <EmptyState title="No sector rows">ChartsMaze sector-analytics missing for this date.</EmptyState>;
  return (
    <>
      <div className="mb-2 border border-info-border bg-info-bg px-2 py-1 font-sans text-[11px] text-info">
        Sector rows use latest ChartsMaze relative strength. The {timeframe.toUpperCase()} flip applies to Themes, where performance fields exist.
      </div>
      {/* Column header — mono uppercase eyebrow (design: terminal chrome) */}
      <div className="mb-1 grid grid-cols-12 gap-2 px-1 font-mono text-[10px] uppercase tracking-overline text-ink3">
        <span className="col-span-4">Sector</span>
        <span className="col-span-5">Relative Strength</span>
        <span className="col-span-1 text-right">RS%</span>
        <span className="col-span-2 text-right" title="Moving Average Relative Strength vs benchmark (pp). Falls back to MA participation when Fyers is offline.">
          MARS ⓘ
        </span>
      </div>
      <ul data-testid="sectors-list" className="space-y-1.5">
        {sectors.map((s) => (
          <SectorRow key={s.name} {...s} onSymbolSelect={onSymbolSelect} />
        ))}
      </ul>
    </>
  );
}

// MARS chip — band by state (design: Absolute Outperformance = blue secondary
// highlight, Gross/Relative Out = green, underperformance variants = red/orange).
// Falls back to the MA-participation breadth chip when MARS isn't available
// (Fyers not connected), so the row always carries a second dimension.
const MARS_BAND = {
  ABSOLUTE_OUT:   { cls: "bg-info-bg text-info border-info-border", label: "Absolute Outperformance" },
  GROSS_OUT:      { cls: "bg-bull-bg text-bull border-bull-border", label: "Gross Outperformance" },
  RELATIVE_OUT:   { cls: "bg-bull-bg text-bull border-bull-border", label: "Relative Outperformance" },
  ABSOLUTE_UNDER: { cls: "bg-bear-bg text-bear border-bear-border", label: "Absolute Underperformance" },
  GROSS_UNDER:    { cls: "bg-bear-bg text-bear border-bear-border", label: "Gross Underperformance" },
  RELATIVE_UNDER: { cls: "bg-warn-bg text-warn border-warn-border", label: "Relative Underperformance" },
};

function SectorRow({ name, sector_key, rs_pct, breadth, mars_score, mars_state, rs_delta_1w, onSymbolSelect }) {
  const v = rs_pct ?? 0;
  // RS% band (the bar fill): green ≥50, gray 40–49, red <40.
  const band = v >= 50 ? "bull" : v >= 40 ? "muted" : "bear";
  const fillClass = {
    bull: "bg-bull",
    muted: "bg-ink3",
    bear: "bg-bear",
  }[band];

  const hasMars = mars_score != null;
  const mars = MARS_BAND[mars_state] || MARS_BAND.GROSS_UNDER;
  // MA% breadth as fallback chip when MARS absent.
  const bVal = breadth ?? null;

  const chipTitle = hasMars
    ? `MARS ${mars_score > 0 ? "+" : ""}${mars_score.toFixed(1)} pp — ${mars.label}`
    : `MA participation: ${bVal != null ? bVal.toFixed(0) + "%" : "n/a"} (MARS needs Fyers)`;
  const chipCls = hasMars
    ? mars.cls
    : bVal == null
      ? "bg-raised text-ink3 border-hairline"
      : bVal >= 65
        ? "bg-bull-bg text-bull border-bull-border"
        : bVal >= 48
          ? "bg-muted-bg text-muted border-muted-border"
          : "bg-bear-bg text-bear border-bear-border";
  const chipText = hasMars
    ? `${mars_score > 0 ? "+" : ""}${mars_score.toFixed(1)}`
    : bVal != null
      ? `${bVal.toFixed(0)}%`
      : "—";

  const [expanded, setExpanded] = useState(false);
  const canDrill = Boolean(sector_key);

  return (
    <li data-testid={`sector-row-${slug(name)}`}>
      <div
        role={canDrill ? "button" : undefined}
        tabIndex={canDrill ? 0 : undefined}
        onClick={canDrill ? () => setExpanded((v) => !v) : undefined}
        onKeyDown={
          canDrill
            ? (e) => (e.key === "Enter" || e.key === " ") && setExpanded((v) => !v)
            : undefined
        }
        className={
          "grid grid-cols-12 items-center gap-2 px-1 py-1 text-[12px] " +
          (canDrill ? "cursor-pointer hover:bg-raised" : "")
        }
      >
        <div className="col-span-4 flex items-center gap-1 truncate font-mono text-ink" title={name}>
          {canDrill && (
            <span
              data-testid={`sector-chevron-${slug(name)}`}
              className="inline-block w-2.5 text-[9px] text-ink3"
            >
              {expanded ? "▾" : "▸"}
            </span>
          )}
          <span className="truncate">{name}</span>
          <RsDeltaChip delta={rs_delta_1w} />
        </div>
        <div className="col-span-5 h-2 rounded-sm bg-hairline">
          <div
            className={"h-full rounded-sm " + fillClass}
            style={{ width: `${Math.min(100, Math.max(0, v))}%` }}
          />
        </div>
        <div className="col-span-1 text-right font-mono tabular-nums text-ink2">
          {rs_pct != null ? `${rs_pct.toFixed(0)}%` : "—"}
        </div>
        <div className="col-span-2 flex justify-end">
          <span
            title={chipTitle}
            className={
              "inline-block rounded-chip border px-1.5 py-px font-mono text-[10px] tabular-nums " +
              chipCls
            }
          >
            {chipText}
          </span>
        </div>
      </div>
      {expanded && canDrill && (
        <StockDrilldown
          fetcher={() => getSectorStocks(sector_key)}
          label={name}
          onSymbolSelect={onSymbolSelect}
        />
      )}
    </li>
  );
}

// B1 — sector momentum arrow: ▲/▼ + 1-week RS delta, muted so it doesn't
// compete with the RS%/MARS chips. Flat/near-zero (|delta| < 0.5) shows no
// arrow at all rather than a meaningless ▲/▼0.0 — not enough data / no move.
function RsDeltaChip({ delta }) {
  if (delta == null || Math.abs(delta) < 0.5) return null;
  const up = delta > 0;
  return (
    <span
      title={`1-week RS change: ${up ? "+" : ""}${delta.toFixed(1)}pp`}
      className="ml-1 shrink-0 font-mono text-[9px] tabular-nums text-ink3"
    >
      {up ? "▲" : "▼"}
      {Math.abs(delta).toFixed(1)}
    </span>
  );
}

// ─── Themes tab ─────────────────────────────────────────────────────────────
function ThemesList({ industries, timeframe, unavailable, onSymbolSelect }) {
  const [showAll, setShowAll] = useState(false);
  if (industries.length === 0)
    return <EmptyState title="No theme rows">ChartsMaze industry-analytics missing for this date.</EmptyState>;
  if (unavailable?.[timeframe]) {
    return <EmptyState title={`${timeframe.toUpperCase()} not available`}>{unavailable[timeframe]}</EmptyState>;
  }
  const limit = 12;
  const sorted = [...industries].sort(
    (a, b) => (b.performance?.[timeframe] ?? -1e9) - (a.performance?.[timeframe] ?? -1e9)
  );
  const shown = showAll ? sorted : sorted.slice(0, limit);
  return (
    <>
      <ul data-testid="themes-list" className="space-y-1.5">
        {shown.map((it) => (
          <ThemeRow key={it.name} {...it} timeframe={timeframe} onSymbolSelect={onSymbolSelect} />
        ))}
      </ul>
      {sorted.length > limit && (
        <button
          onClick={() => setShowAll((v) => !v)}
          className="mt-2 font-mono text-[10px] uppercase tracking-overline text-bull hover:text-ink"
        >
          {showAll ? "Collapse" : `Show all ${sorted.length}`}
        </button>
      )}
    </>
  );
}

function ThemeRow({ name, performance, perf_1m, perf_3m, num_stocks, timeframe, onSymbolSelect }) {
  const v = performance?.[timeframe] ?? 0;
  // Bar fill ∝ 1M perf clamped to ±20% → 0..100% width. Green ≥0, red <0.
  const width = Math.min(100, (Math.abs(v) / 20) * 100);
  const positive = v >= 0;
  const [expanded, setExpanded] = useState(false);

  return (
    <li data-testid={`theme-row-${slug(name)}`}>
      <div
        role="button"
        tabIndex={0}
        onClick={() => setExpanded((val) => !val)}
        onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && setExpanded((val) => !val)}
        className="grid cursor-pointer grid-cols-12 items-center gap-2 px-1 py-1 text-[12px] hover:bg-raised"
      >
        <div className="col-span-5 flex items-center gap-1 truncate font-mono text-ink" title={name}>
          <span
            data-testid={`theme-chevron-${slug(name)}`}
            className="inline-block w-2.5 text-[9px] text-ink3"
          >
            {expanded ? "▾" : "▸"}
          </span>
          <span className="truncate">{name}</span>
        </div>
        <div className="col-span-5 h-2 rounded-sm bg-hairline">
          <div
            className={"h-full rounded-sm " + (positive ? "bg-bull" : "bg-bear")}
            style={{ width: `${width}%` }}
          />
        </div>
        <div className="col-span-2 flex items-baseline justify-end gap-1.5 font-mono tabular-nums">
          <span
            className={"text-[11px] " + (positive ? "text-bull" : "text-bear")}
            title={`${timeframe.toUpperCase()} performance`}
          >
            {fmtPct(performance?.[timeframe])}
          </span>
          <span
            className={"text-[10px] " + (perf_3m >= 0 ? "text-bull" : "text-bear")}
            title={timeframe === "3m" ? "1-month performance" : "3-month performance"}
          >
            {timeframe === "3m" ? fmtPct(perf_1m) : fmtPct(perf_3m)}
          </span>
        </div>
      </div>
      {expanded && (
        <StockDrilldown
          fetcher={() => getIndustryStocks(name)}
          label={name}
          count={num_stocks}
          onSymbolSelect={onSymbolSelect}
        />
      )}
    </li>
  );
}

// ─── Stock drill-down (the pulldown) ───────────────────────────────────────
// Shared by both tabs. Owns its own fetch/loading/error/empty state so a row
// expand never blocks the rest of the list. RS band mirrors SectorRow's
// thresholds (≥50 bull, ≥40 muted, <40 bear) for one consistent read.
const RS_FILTER_MIN = 70;

function StockDrilldown({ fetcher, label, count, onSymbolSelect }) {
  const [state, setState] = useState({ loading: true, error: null, data: null });
  const [query, setQuery] = useState("");
  const [rsOnly, setRsOnly] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setState({ loading: true, error: null, data: null });
    fetcher()
      .then((d) => !cancelled && setState({ loading: false, error: null, data: d }))
      .catch((e) => !cancelled && setState({ loading: false, error: e.message, data: null }));
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [label]);

  const allStocks = state.data?.available ? state.data.stocks : [];
  const q = query.trim().toUpperCase();
  const stocks = allStocks.filter((s) => {
    if (q && !s.ticker.toUpperCase().includes(q)) return false;
    if (rsOnly && !(s.rs != null && s.rs >= RS_FILTER_MIN)) return false;
    return true;
  });

  return (
    <div
      data-testid={`drilldown-${slug(label)}`}
      className="ml-4 mb-1.5 border-l-2 border-hairline pl-3"
    >
      {state.loading ? (
        <div className="py-1.5 font-mono text-[10px] text-ink3">loading stocks…</div>
      ) : state.error ? (
        <div className="py-1.5 font-mono text-[10px] text-bear">{state.error}</div>
      ) : allStocks.length === 0 ? (
        <div className="py-1.5 font-mono text-[10px] text-ink3">
          No constituent stocks for this date.
        </div>
      ) : (
        <>
          <div className="flex flex-wrap items-center gap-1.5 py-1.5">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search ticker…"
              data-testid={`drilldown-search-${slug(label)}`}
              className="w-28 border border-hairline bg-card px-1.5 py-0.5 font-mono text-[10px] text-ink placeholder:text-ink3 focus:border-info focus:outline-none"
            />
            <button
              type="button"
              onClick={() => setRsOnly((v) => !v)}
              data-testid={`drilldown-rs-filter-${slug(label)}`}
              className={
                "rounded-chip border px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-overline " +
                (rsOnly
                  ? "border-bull bg-bull-bg text-bull"
                  : "border-hairline text-ink3 hover:text-ink2")
              }
            >
              RS ≥ {RS_FILTER_MIN}
            </button>
          </div>
          {stocks.length === 0 ? (
            <div className="pb-1.5 font-mono text-[10px] text-ink3">No stocks match this filter.</div>
          ) : (
            <ul className="flex flex-wrap gap-1 pb-1.5">
              {stocks.map((s) => (
                <li key={s.ticker}>
                  <SymbolChip symbol={s.ticker} rs={s.rs} onSelect={onSymbolSelect} />
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </div>
  );
}

// ─── Shared bits ────────────────────────────────────────────────────────────
function SkeletonRows() {
  return (
    <ul className="space-y-1.5">
      {Array.from({ length: 8 }).map((_, i) => (
        <li key={i} className="grid grid-cols-12 items-center gap-2 px-1 py-1">
          <div className="col-span-5 h-3 animate-pulse rounded bg-hairline" />
          <div className="col-span-5 h-2 animate-pulse rounded bg-hairline2" />
          <div className="col-span-2 h-3 animate-pulse rounded bg-hairline2" />
        </li>
      ))}
    </ul>
  );
}

function EmptyState({ title, children }) {
  return (
    <div className="border border-dashed border-hairline px-4 py-6 text-center">
      <div className="font-mono text-[12px] font-semibold text-ink2">{title}</div>
      <div className="mt-1 font-sans text-[12px] leading-snug text-ink3">{children}</div>
    </div>
  );
}

function fmtPct(n) {
  if (n == null) return "—";
  return `${n > 0 ? "+" : ""}${n.toFixed(1)}%`;
}

function slug(s) {
  return s.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
}
