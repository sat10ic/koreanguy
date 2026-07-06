import { useEffect, useState } from "react";
import { getDataCoverage } from "../api.js";

/**
 * DataStamp — generalized `DataCoverage.jsx` (design §0.2C). One row of
 * per-source freshness chips: `SOURCE · date · dot`. Green <=1d / amber <=5d
 * / red beyond-or-missing. Rendered as a thin footer strip on every screen
 * so "as-of which source" is always answerable in one glance — this REPLACES
 * every ad-hoc "as of {date}" string scattered across components.
 *
 * `mini` renders a compact single-chip form (worst-source freshness dot +
 * date) for the header, per design §0.1.
 */
export default function DataStamp({ mini = false, nonce }) {
  const [data, setData] = useState(null);

  useEffect(() => {
    let cancelled = false;
    getDataCoverage()
      .then((d) => !cancelled && setData(d))
      .catch(() => !cancelled && setData(null));
    return () => {
      cancelled = true;
    };
  }, [nonce]);

  if (!data) return null;

  if (mini) return <MiniStamp data={data} />;

  return (
    <div
      data-testid="data-stamp"
      className="mt-4 flex flex-wrap items-center gap-2 border-t border-hairline2 pt-2"
    >
      <span className="font-mono text-[9px] uppercase tracking-overline text-ink3">
        data updated until
      </span>
      {data.sources.map((s) => (
        <SourceChip key={s.key} source={s} today={data.as_of_query} />
      ))}
    </div>
  );
}

function MiniStamp({ data }) {
  // Worst-source freshness across all sources — a single dot + the query date.
  const worst = data.sources.reduce((acc, s) => {
    const band = bandFor(s.until, data.as_of_query);
    const rank = { red: 2, amber: 1, green: 0 }[band];
    return rank > acc.rank ? { rank, band } : acc;
  }, { rank: -1, band: "green" });

  const dotCls = {
    green: "bg-bull-dot",
    amber: "bg-warn-dot",
    red: "bg-bear-dot",
  }[worst.band];

  return (
    <span
      data-testid="data-stamp-mini"
      className="flex items-center gap-1 font-mono text-[10px] text-ink3"
      title={data.sources.map((s) => `${shortLabel(s.label)}: ${s.until || "no data"}`).join(" · ")}
    >
      <span className={"inline-block h-1.5 w-1.5 rounded-full " + dotCls} />
      {data.as_of_query}
    </span>
  );
}

function bandFor(until, today) {
  if (until == null) return "red";
  const days = tradingDaysBetween(until, today);
  if (days <= 1) return "green";
  if (days <= 5) return "amber";
  return "red";
}

function SourceChip({ source, today }) {
  const { label, until, live_fetch } = source;
  const days = until ? tradingDaysBetween(until, today) : null;
  const band = bandFor(until, today);
  const cls = {
    green: "bg-bull-bg text-bull border-bull-border",
    amber: "bg-warn-bg text-warn border-warn-border",
    red: "bg-bear-bg text-bear border-bear-border",
  }[band];
  return (
    <span
      className={"inline-flex items-center gap-1 rounded-chip border px-1.5 py-0.5 font-mono text-[10px] " + cls}
      title={
        (live_fetch ? "Fetched live from source each run. " : "") +
        (until ? `Latest: ${until}${days != null ? ` (${days} trading day${days !== 1 ? "s" : ""} behind)` : ""}` : "No data yet")
      }
    >
      <span className="uppercase tracking-overline">{shortLabel(label)}</span>
      <span className="tabular-nums font-bold">{until || "—"}</span>
      {live_fetch && <span title="live-fetched">⟲</span>}
    </span>
  );
}

function shortLabel(label) {
  return label.split(" (")[0];
}

/** Calendar days between two YYYY-MM-DD strings. */
function calendarDaysBetween(from, to) {
  const a = new Date(from + "T00:00:00").getTime();
  const b = new Date(to + "T00:00:00").getTime();
  return Math.round((b - a) / (24 * 60 * 60 * 1000));
}

/** Trading (weekday) days between two YYYY-MM-DD strings.
 *  Counts only Mon–Fri, so a Friday source on a Sunday reads 0 days behind. */
function tradingDaysBetween(from, to) {
  let days = calendarDaysBetween(from, to);
  if (days <= 0) return days;
  // Walk backwards from `to` (today), skipping weekends, `days` calendar steps.
  let trading = 0;
  const start = new Date(from + "T00:00:00");
  const end = new Date(to + "T00:00:00");
  let cur = new Date(end);
  while (cur > start) {
    const dow = cur.getDay(); // 0=Sun, 6=Sat
    if (dow >= 1 && dow <= 5) trading++;
    cur = new Date(cur.getTime() - 24 * 60 * 60 * 1000);
  }
  return trading;
}
