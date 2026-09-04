import { useMemo } from "react";
import { useMode } from "../lib/ModeContext";
import { useReport } from "../lib/useReport";
import { getRealHistory } from "../data/stockHistory";
import eventsBundle from "../data/events_bundle.json";
import { AppShell } from "../components/shell/AppShell";
import { Chip } from "../components/ui/Chip";
import {
  CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer,
  Tooltip, XAxis, YAxis,
} from "recharts";

/*
  EVENTS (event-track §5) — IPO track, Lab tier (KDE §10).

  A lens, never a second ranking: every name here already appears in the main
  feed. X = sessions since the listing, Y = % from the day-0 close; every line
  starts at (0, 0). Formulas MIRROR unidesk/momentum/features/
  event_relative.py (the backend owns the definitions; the UI re-derives the
  same numbers from the same bundled bars and cites the module here).
  Constitution §22: this shows what happened to similar listings — never a
  probability, never a prediction. Sample counts are attached.
*/

type Listing = { listing_date: string };
const LISTINGS = (eventsBundle as { listings: Record<string, Listing> }).listings;
const LISTINGS_COUNT = Object.keys(LISTINGS).length;

interface Overlay {
  symbol: string;
  age: number;
  points: { x: number; y: number }[];
  pctFromListingHigh: number;
  firstDayRangePct: number;
  baseVsListingRange: number;
}

function buildOverlay(symbol: string, listingDate: string, session: string): Overlay | null {
  const bars = getRealHistory(symbol, session);
  if (!bars || bars.length === 0) return null;
  const day0Index = bars.findIndex((b) => b.time >= listingDate);
  if (day0Index < 0) return null;
  const since = bars.slice(day0Index);
  if (since.length < 2) return null; // listing session + at least one more
  const day0 = since[0];
  const day0Close = day0.close;
  const day0Range = day0.high - day0.low;
  const firstDayRangePct = day0Range > 0 && day0.low > 0 ? (day0Range / day0.low) * 100 : 0;
  let listingHigh = day0.high;
  let lowestLow = day0.low;
  const points: { x: number; y: number }[] = [];
  since.forEach((b, i) => {
    listingHigh = Math.max(listingHigh, b.high);
    lowestLow = Math.min(lowestLow, b.low);
    points.push({ x: i, y: day0Close > 0 ? (b.close / day0Close - 1) * 100 : 0 });
  });
  const lastClose = since[since.length - 1].close;
  const pctFromListingHigh = listingHigh > 0 ? (lastClose / listingHigh - 1) * 100 : 0;
  const baseVsListingRange = day0Range > 0 ? (listingHigh - lowestLow) / day0Range : 0;
  return {
    symbol, age: since.length, points,
    pctFromListingHigh, firstDayRangePct, baseVsListingRange,
  };
}

export function Events() {
  const { mode } = useMode();
  const report = useReport();

  const { overlays, skippedNoListing, skippedNoBars } = useMemo(() => {
    const seen = new Set<string>();
    const out: Overlay[] = [];
    let skippedNoListing = 0;
    let skippedNoBars = 0;
    for (const c of report.candidates ?? []) {
      if (seen.has(c.symbol)) continue;
      seen.add(c.symbol);
      const listing = LISTINGS[c.symbol];
      if (!listing) { skippedNoListing += 1; continue; }
      const overlay = buildOverlay(c.symbol, listing.listing_date, report.session_date);
      if (!overlay) { skippedNoBars += 1; continue; }
      out.push(overlay);
    }
    out.sort((a, b) => a.age - b.age);
    return { overlays: out.slice(0, 30), skippedNoListing, skippedNoBars };
  }, [report]);

  const lab = mode === "lab";
  const chartRows = overlays.filter((o) => o.age >= 2);
  const longest = Math.max(2, ...chartRows.map((o) => o.age));

  if (!lab) {
    return (
      <AppShell breadcrumb={["Events"]}>
        <div className="p-4">
          <div className="rounded-card border border-border bg-surface-1 px-3.5 py-6 text-center">
            <p className="text-body font-medium text-ink-primary">Events is a Lab surface.</p>
            <p className="mx-auto mt-1 max-w-xl text-caption text-ink-tertiary">
              It carries computed, unit-tested research overlays with no measured edge yet
              (HANDOFF_2026-09-04_EVENT_TRACK_IPO_EP §4/§5). Switch the mode to{" "}
              <span className="font-semibold">lab</span> in the top bar to view it — Beginner
              and Pro never render unvalidated surfaces.
            </p>
          </div>
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell breadcrumb={["Events"]}>
      <div className="flex flex-col gap-4 p-4">
        <div className="rounded-card border border-violet-border bg-violet-bg px-3.5 py-3">
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-h3 font-semibold text-ink-primary">Events</h1>
            <Chip tone="neutral">EXPLORATORY — computed and unit-tested; no measured edge.
              See HANDOFF_2026-09-04_EVENT_TRACK_IPO_EP §4/§5.</Chip>
          </div>
          <p className="mt-1 text-caption text-ink-tertiary">
            A lens on the main feed, never a second ranking: ranked order on Tonight and
            Candidates is byte-identical with this screen present or absent. What follows
            shows what happened to similar listings — not a probability, not advice.
          </p>
        </div>

        <div className="rounded-card border border-border bg-surface-1 px-3.5 py-3">
          <div className="mb-2 flex flex-wrap items-baseline justify-between gap-2">
            <h2 className="text-h4 font-semibold text-ink-primary">IPO track — event-normalised overlay</h2>
            <span className="text-caption text-ink-muted">
              X: sessions since listing · Y: % from day-0 close · {chartRows.length} of{" "}
              {(report.candidates ?? []).length} candidates shown
            </span>
          </div>
          {chartRows.length === 0 ? (
            <p className="py-6 text-center text-t3 text-ink-tertiary">
              No tonight-candidate has a bundled listing with ≥2 sessions yet.
            </p>
          ) : (
            <div className="h-80 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
                  <CartesianGrid stroke="var(--border-subtle)" strokeDasharray="3 3" />
                  <XAxis dataKey="x" type="number" domain={[0, longest]}
                    tick={{ fill: "var(--text-tertiary)", fontSize: 11 }} stroke="var(--border)"
                    label={{ value: "sessions since listing", position: "insideBottom", offset: -4,
                             fill: "var(--text-tertiary)", fontSize: 11 }} />
                  <YAxis tick={{ fill: "var(--text-tertiary)", fontSize: 11 }} stroke="var(--border)"
                    tickFormatter={(v: number) => `${v > 0 ? "+" : ""}${v.toFixed(0)}%`} width={54} />
                  <Tooltip
                    content={({ active, payload }) => {
                      if (!active || !payload?.length) return null;
                      const p = payload[0].payload as { x: number; y: number; symbol?: string };
                      return (
                        <div className="rounded-btn border border-border-strong bg-surface-1 px-2.5 py-2 text-caption shadow-lg">
                          <div className="font-semibold text-ink-primary">{p.symbol ?? ""}</div>
                          <div className="font-mono-num text-ink-secondary">
                            session {p.x} · {p.y > 0 ? "+" : ""}{p.y.toFixed(1)}% from day-0 close
                          </div>
                        </div>
                      );
                    }} />
                  <ReferenceLine y={0} stroke="var(--border-strong)" />
                  {chartRows.map((o) => (
                    <Line key={o.symbol} data={o.points.map((p) => ({ ...p, symbol: o.symbol }))}
                      dataKey="y" type="monotone" dot={false} strokeWidth={o.age === Math.max(...chartRows.map((r) => r.age)) ? 2 : 1}
                      stroke="var(--accent)" strokeOpacity={0.55} isAnimationActive={false} />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
          <p className="mt-1 text-[10px] text-ink-muted">
            Lines overlap by design — muted; the longest history is boldest. n = {chartRows.length} listings
            drawn from the bundled NSE equity master ({LISTINGS_COUNT} listings total); no missing
            listing is invented — {overlays.length} candidates qualified, {skippedNoListing} without a
            bundled listing and {skippedNoBars} without bundled bars are disclosed here, not dropped
            silently. Mirror of features/event_relative.py over the same bundled bars.
          </p>
        </div>

        <div className="rounded-card border border-border bg-surface-1 px-3.5 py-3">
          <h2 className="mb-2 text-h4 font-semibold text-ink-primary">IPO rows</h2>
          <div className="flex flex-col gap-1">
            {overlays.map((o) => (
              <div key={o.symbol} className="flex flex-wrap items-center gap-3 rounded-chip px-2 py-1.5 text-caption hover:bg-surface-2">
                <span className="w-24 font-semibold text-ink-primary">{o.symbol}</span>
                <span className="font-mono-num text-ink-secondary">
                  Day {o.age} · {o.pctFromListingHigh >= 0 ? "+" : ""}{o.pctFromListingHigh.toFixed(1)}% from listing high
                </span>
                <span className="font-mono-num text-ink-tertiary">first-day range {o.firstDayRangePct.toFixed(1)}%</span>
                <span className="font-mono-num text-ink-tertiary">
                  base {o.baseVsListingRange.toFixed(2)}× first-day range
                </span>
              </div>
            ))}
            {overlays.length === 0 && (
              <p className="text-caption text-ink-tertiary">No candidates qualify.</p>
            )}
          </div>
          <p className="mt-2 text-[10px] text-ink-muted">
            EP track pending the announcements catalyst feed (coverage begins 2026-04) — an
            empty frame is not shipped as data. Listing dates: bundled NSE equity master
            (events_bundle.json); bars: bundled point-in-time stock history.
          </p>
        </div>
      </div>
    </AppShell>
  );
}
