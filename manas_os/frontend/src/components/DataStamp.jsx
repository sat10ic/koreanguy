import { useEffect, useState } from "react";
import { getDataCoverage } from "../api.js";

export default function DataStamp({ mini = false, nonce, onOpenHealth }) {
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
  if (mini) return <MiniStamp data={data} onOpenHealth={onOpenHealth} />;

  return (
    <div data-testid="data-stamp" className="mt-4 flex flex-wrap items-center gap-2 border-t border-hairline2 pt-2">
      <span className="font-mono text-[9px] uppercase tracking-overline text-ink3">data updated until</span>
      {data.sources.map((source) => (
        <SourceChip key={source.key} source={source} today={data.as_of_query} />
      ))}
    </div>
  );
}

function MiniStamp({ data, onOpenHealth }) {
  const worst = data.sources.reduce((acc, source) => {
    const band = bandFor(source.until, data.as_of_query);
    const rank = { red: 2, amber: 1, green: 0 }[band];
    return rank > acc.rank ? { rank, band } : acc;
  }, { rank: -1, band: "green" });

  const dotCls = {
    green: "bg-bull-dot",
    amber: "bg-warn-dot",
    red: "bg-bear-dot",
  }[worst.band];
  const title = data.sources.map((source) => `${shortLabel(source.label)}: ${source.until || "no data"}`).join(" - ");

  if (!onOpenHealth) {
    return (
      <span data-testid="data-stamp-mini" className="flex items-center gap-1 font-mono text-[10px] text-ink3" title={title}>
        <span className={"inline-block h-1.5 w-1.5 rounded-full " + dotCls} />
        {data.as_of_query}
      </span>
    );
  }

  return (
    <button
      type="button"
      data-testid="data-stamp-mini"
      onClick={onOpenHealth}
      className="flex items-center gap-1 font-mono text-[10px] text-ink3 hover:text-ink"
      title={`${title} - open data health`}
    >
      <span className={"inline-block h-1.5 w-1.5 rounded-full " + dotCls} />
      {data.as_of_query}
      <span className="border-l border-hairline pl-1 uppercase tracking-overline">data health</span>
    </button>
  );
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
      <span className="font-bold tabular-nums">{until || "-"}</span>
      {live_fetch && <span title="live-fetched">live</span>}
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

function shortLabel(label) {
  return label.split(" (")[0];
}

function calendarDaysBetween(from, to) {
  const a = new Date(from + "T00:00:00").getTime();
  const b = new Date(to + "T00:00:00").getTime();
  return Math.round((b - a) / (24 * 60 * 60 * 1000));
}

function tradingDaysBetween(from, to) {
  let days = calendarDaysBetween(from, to);
  if (days <= 0) return days;
  let trading = 0;
  const start = new Date(from + "T00:00:00");
  let cur = new Date(to + "T00:00:00");
  while (cur > start) {
    const dow = cur.getDay();
    if (dow >= 1 && dow <= 5) trading++;
    cur = new Date(cur.getTime() - 24 * 60 * 60 * 1000);
  }
  return trading;
}
