import { AlertTriangle, CalendarRange, ChevronDown, ChevronRight, FileText } from "lucide-react";
import { Link } from "react-router-dom";
import { useState } from "react";
import { AppShell } from "../components/shell/AppShell";
import { Chip } from "../components/ui/Chip";
import { REAL_CALLS, OUTCOMES_META } from "../data/outcomes";
import type { OutcomeCall } from "../data/fixtures";
import { useMode } from "../lib/ModeContext";
import { SETUP_LABEL, type SetupType } from "../data/fixtures";

/*
  HOME 3 — PRIOR CALLS (UI_BUILD_SPEC_V1 PART 5). This screen shows WHAT THE
  SCANNER CALLED and how those calls resolved. It never shows broker trades
  (X-02) — broker reality lives on Desk (D-09), the only place the two
  grains meet, labelled on both sides.

  H3-01 verdict (investigated 2026-09-01, see handoff report): the outcomes
  builder emits ONE outcome field per row — hit_target | stopped_out |
  unresolved (unidesk/run_history_outcomes_export.py _outcome_of). A
  "No longer in universe" label does not exist anywhere in the builder or
  the data; the audit's "both labels on one row" cannot occur. The real
  conflation risk is different: gap-through stops are labelled stopped_out
  with a different note — rendered here as a distinct state (H3-06).
*/

type OutcomeState = "WIN" | "STOPPED" | "STOPPED_GAP" | "OPEN" | "FLAT" | "NO_DATA";

const STATE_META: Record<OutcomeState, { label: string; tone: "positive" | "danger" | "neutral" | "accent" }> = {
  WIN: { label: "Win", tone: "positive" },
  STOPPED: { label: "Stopped", tone: "danger" },
  STOPPED_GAP: { label: "Stopped (gap-through)", tone: "danger" },
  // Horizon not elapsed. Counting these as wins is what produced a 94% win
  // rate on the newest session against a 35% archive base rate.
  OPEN: { label: "Still open", tone: "accent" },
  FLAT: { label: "Flat (no target)", tone: "neutral" },
  NO_DATA: { label: "No data", tone: "neutral" },
};

function stateOf(c: OutcomeCall): OutcomeState {
  if (c.outcome === "hit_target") return "WIN";
  if (c.outcome === "stopped_out") return c.gapThrough ? "STOPPED_GAP" : "STOPPED";
  if (c.outcome === "open") return "OPEN";
  if (c.outcome === "resolved_flat") return "FLAT";
  return "NO_DATA";
}

type RangeKey = "latest" | "this_week" | "last_week" | "this_month" | "all";
const RANGES: { key: RangeKey; label: string }[] = [
  { key: "latest", label: "Latest" },
  { key: "this_week", label: "This week" },
  { key: "last_week", label: "Last week" },
  { key: "this_month", label: "This month" },
  { key: "all", label: "All" },
];

function inRange(callDate: string, key: RangeKey, latest: string): boolean {
  if (key === "all") return true;
  const anchor = new Date(latest + "T00:00:00");
  const d = new Date(callDate + "T00:00:00");
  if (isNaN(anchor.getTime()) || isNaN(d.getTime())) return true;
  if (key === "latest") return d >= new Date(anchor.getTime() - 6 * 86400000);
  if (key === "this_week") {
    const start = anchor.getTime() - ((anchor.getDay() + 6) % 7) * 86400000;
    return d.getTime() >= start && d.getTime() <= anchor.getTime() + 86400000;
  }
  if (key === "last_week") {
    const thisMonday = anchor.getTime() - ((anchor.getDay() + 6) % 7) * 86400000;
    return d.getTime() >= thisMonday - 7 * 86400000 && d.getTime() < thisMonday;
  }
  const monthStart = new Date(anchor.getFullYear(), anchor.getMonth(), 1).getTime();
  return d.getTime() >= monthStart && d.getTime() <= anchor.getTime() + 86400000;
}

const num = (v: number | null | undefined, digits = 1, suffix = ""): string =>
  v === null || v === undefined ? "—" : `${v > 0 ? "+" : ""}${v.toFixed(digits)}${suffix}`;

export function History() {
  const { mode } = useMode();
  const isPro = mode === "pro";
  const [range, setRange] = useState<RangeKey>("latest");
  const latest = OUTCOMES_META.reportSession;
  const calls = REAL_CALLS.filter((c) => inRange(c.date, range, latest));

  // H3-02: performance summary — only statistics the outcomes file supports.
  const wins = calls.filter((c) => stateOf(c) === "WIN");
  const stopped = calls.filter((c) => { const s = stateOf(c); return s === "STOPPED" || s === "STOPPED_GAP"; });
  const open = calls.filter((c) => stateOf(c) === "OPEN");
  const flat = calls.filter((c) => stateOf(c) === "FLAT");
  const noData = calls.filter((c) => stateOf(c) === "NO_DATA");
  // Only calls whose horizon has elapsed count toward hit rate / avg R.
  // "open" positions are excluded — grading a trade before it can fail is what
  // inflated the newest session to 94%.
  const resolved = [...wins, ...stopped, ...flat];
  const rOf = (c: OutcomeCall) => c.rMultiple;
  const rsResolved = resolved.map(rOf).filter((r): r is number => r != null);
  const hitRate = rsResolved.length > 0 ? (rsResolved.filter((r) => r > 0).length / rsResolved.length) * 100 : null;
  const avgR = rsResolved.length > 0 ? rsResolved.reduce((s, r) => s + r, 0) / rsResolved.length : null;
  const bestR = rsResolved.length > 0 ? Math.max(...rsResolved) : null;
  const worstR = rsResolved.length > 0 ? Math.min(...rsResolved) : null;

  // H3-08: setup-level scorecard (resolved rows only; n shown beside every
  // figure; n<10 visibly marked low-sample).
  const bySetup = new Map<SetupType, OutcomeCall[]>();
  for (const c of resolved) {
    const k = c.setupType as SetupType;
    if (!bySetup.has(k)) bySetup.set(k, []);
    bySetup.get(k)!.push(c);
  }
  const scorecard = [...bySetup.entries()]
    .map(([setup, rows]) => {
      const rs = rows.map(rOf).filter((r): r is number => r != null);
      return {
        setup,
        n: rows.length,
        avgR: rs.length ? rs.reduce((s, r) => s + r, 0) / rs.length : null,
        hit: rs.length ? (rs.filter((r) => r > 0).length / rs.length) * 100 : null,
      };
    })
    .sort((a, b) => (b.avgR ?? -99) - (a.avgR ?? -99));

  // H3-07: collapsible outcome groups.
  const [openGroups, setOpenGroups] = useState<Record<string, boolean>>({ WIN: true, STOPPED: false, OPEN: false, FLAT: false, NO_DATA: false });
  const groups: { key: string; title: string; rows: OutcomeCall[] }[] = [
    { key: "WIN", title: `Winners · ${wins.length}`, rows: wins.slice(0, 40) },
    { key: "STOPPED", title: `Stopped · ${stopped.length}`, rows: stopped.slice(0, 40) },
    { key: "OPEN", title: `Still open — horizon not elapsed · ${open.length}`, rows: open.slice(0, 40) },
    { key: "FLAT", title: `Flat — ran full horizon, never reached +1R · ${flat.length}`, rows: flat.slice(0, 40) },
    { key: "NO_DATA", title: `No data / unresolved · ${noData.length}`, rows: noData.slice(0, 40) },
  ];

  return (
    <AppShell breadcrumb={["History"]}>
      <div className="flex flex-col gap-4 p-4">
        <div className="rounded-card border border-border bg-surface-1 px-3.5 py-3">
          <div className="mb-2 flex items-center gap-1.5 text-caption text-ink-muted">
            <FileText size={13} aria-hidden />
            What the scanner called
          </div>
          <p className="text-caption text-ink-tertiary">
            Every candidate call from the scan archive, joined to its measured
            10-bar outcome: {OUTCOMES_META.count.toLocaleString()} calls across{" "}
            {OUTCOMES_META.symbolsCovered} symbols through the {OUTCOMES_META.reportSession} session
            (labels: {OUTCOMES_META.outcomeLabelsVersion}). Broker trades are never shown here — that is the Desk's D-09 view.
          </p>
        </div>

        {OUTCOMES_META.netBpsCoverage === 0 && (
          <div className="flex items-center gap-2 rounded-card border border-border bg-surface-1 px-3.5 py-2.5 text-caption text-ink-muted">
            <AlertTriangle size={13} className="text-warning" aria-hidden />
            Net-of-cost numbers are not on disk yet ({OUTCOMES_META.netBpsCoverage}/{OUTCOMES_META.count.toLocaleString()} rows carry one). R-multiples and outcome classes are unaffected.
          </div>
        )}

        <div className="flex items-center gap-1.5 rounded-chip border border-border-subtle p-0.5 w-fit">
          <CalendarRange size={13} className="ml-1 text-ink-tertiary" aria-hidden />
          {RANGES.map((r) => (
            <button key={r.key} onClick={() => setRange(r.key)} aria-pressed={range === r.key}
              className={"whitespace-nowrap rounded-[4px] px-2.5 py-1 text-caption font-medium transition-colors " +
                (range === r.key ? "bg-accent-bg text-accent-strong" : "text-ink-tertiary hover:text-ink-secondary")}>
              {r.label}
            </button>
          ))}
        </div>

        {/* H3-02: performance summary */}
        <div className="rounded-card border border-border bg-surface-1 px-3.5 py-3">
          <div className="mb-2 flex items-baseline justify-between">
            <h2 className="text-h4 font-semibold text-ink-primary">Performance summary</h2>
            <span className="font-mono-num text-caption text-ink-muted">{calls.length} calls in range</span>
          </div>
          <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1 text-caption">
            <span className="text-positive font-semibold">{wins.length} won</span>
            <span className="text-danger font-semibold">{stopped.length} stopped</span>
            <span className="text-ink-secondary">{flat.length} flat</span>
            <span className="text-accent-strong">{open.length} still open</span>
            <span className="text-ink-tertiary">{noData.length} no data</span>
            <span className="font-mono-num text-ink-muted">Hit rate {hitRate != null ? (hitRate.toFixed(0) + "%") : "—"}</span>
            <span className="font-mono-num text-ink-muted">Avg {num(avgR, 2, "R")}</span>
            <span className="font-mono-num text-positive">Best {num(bestR, 1, "R")}</span>
            <span className="font-mono-num text-danger">Worst {num(worstR, 1, "R")}</span>
          </div>

          {/* H3-03: outcome strip — one cell per resolved call, counts match */}
          <div className="mt-2.5 flex flex-wrap items-center gap-0.5">
            {resolved.slice(0, 120).map((c, i) => (
              <span key={c.symbol + c.date + i}
                className={"inline-block h-2.5 w-2 rounded-[2px] " + (stateOf(c) === "WIN" ? "bg-positive" : "bg-danger")}
                title={`${c.symbol} ${c.date} ${stateOf(c)}`} />
            ))}
            {noData.slice(0, 40).map((c, i) => (
              <span key={"nd" + c.symbol + c.date + i} className="inline-block h-2.5 w-2 rounded-[2px] bg-neutral-bg border border-border-subtle"
                title={`${c.symbol} ${c.date} no data`} />
            ))}
          </div>
          <div className="mt-1 text-caption text-ink-tertiary">
            Win / stopped / flat are horizon-elapsed and count toward hit rate and avg R.
            Still-open calls are excluded until their 10-bar horizon completes
            ({wins.length} + {stopped.length} + {flat.length} + {open.length} + {noData.length} = {calls.length})
          </div>
        </div>

        {/* H3-08: setup-level scorecard */}
        <div className="rounded-card border border-border bg-surface-1 px-3.5 py-3">
          <h2 className="mb-2.5 text-h4 font-semibold text-ink-primary">Setup scorecard</h2>
          {scorecard.length === 0 ? (
            <p className="text-caption text-ink-tertiary">No resolved calls in this range.</p>
          ) : (
            <div className="flex flex-col gap-1.5">
              {scorecard.map((s) => {
                const width = s.hit != null ? Math.max(2, s.hit) : 0;
                return (
                  <div key={s.setup} className="grid grid-cols-[130px_46px_1fr_70px_60px] items-center gap-2 text-caption">
                    <span className="text-ink-secondary">{SETUP_LABEL[s.setup] ?? s.setup}</span>
                    <span className={"font-mono-num " + (s.n < 10 ? "text-warning" : "text-ink-muted")}
                      title={s.n < 10 ? "low sample — treat the average as noise" : "resolved calls"}>
                      n={s.n}{s.n < 10 ? " ⚠" : ""}
                    </span>
                    <div className="h-2.5 overflow-hidden rounded-sm bg-surface-2">
                      <div className="h-full rounded-sm bg-accent/60" style={{ width: width + "%" }} />
                    </div>
                    <span className="text-right font-mono-num text-ink-muted">hit {s.hit != null ? s.hit.toFixed(0) + "%" : "—"}</span>
                    <span className="text-right font-mono-num font-semibold text-ink-primary">{num(s.avgR, 2, "R")}</span>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* H3-04/06/07/09: collapsible groups + compact outcome table */}
        <div className="rounded-card border border-border bg-surface-1 px-3.5 py-3">
          <h2 className="mb-2 text-h4 font-semibold text-ink-primary">Calls</h2>
          <div className="flex flex-col gap-2">
            {groups.map((g) => (
              <div key={g.key}>
                <button onClick={() => setOpenGroups({ ...openGroups, [g.key]: !openGroups[g.key] })}
                  aria-expanded={openGroups[g.key]}
                  className="flex w-full items-center gap-1.5 py-1 text-left text-caption font-medium text-ink-secondary">
                  {openGroups[g.key] ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
                  {g.title}
                </button>
                {openGroups[g.key] && (
                  g.rows.length === 0 ? (
                    <p className="px-3 text-caption text-ink-tertiary">— none in range —</p>
                  ) : (
                    <div className="flex flex-col">
                      <div className="grid grid-cols-[92px_72px_110px_96px_64px_60px_60px_1fr] gap-2 px-2 py-1 text-caption font-medium text-ink-muted">
                        <span>DATE</span><span>STOCK</span><span>SETUP</span><span>RESULT</span>
                        <span className="text-right">RETURN</span><span className="text-right">MFE</span><span className="text-right">MAE</span>
                        <span className="pl-2">REASON</span>
                      </div>
                      {g.rows.map((c) => {
                        const meta = STATE_META[stateOf(c)];
                        return (
                          <Link key={c.symbol + "-" + c.date + "-" + c.setupType} to={`/stock/${c.symbol}`}
                            className="grid grid-cols-[92px_72px_110px_96px_64px_60px_60px_1fr] items-center gap-2 rounded-chip px-2 py-1.5 hover:bg-surface-2">
                            <span className="font-mono-num text-caption text-ink-muted">{c.date}</span>
                            <span className="text-caption font-semibold text-ink-primary">{c.symbol}</span>
                            <span className="truncate text-caption text-ink-tertiary">{SETUP_LABEL[c.setupType as SetupType] ?? c.setupType}</span>
                            <span><Chip tone={meta.tone}>{meta.label}</Chip></span>
                            <span className="text-right font-mono-num text-caption text-ink-secondary">{num(rOf(c), 1, "R")}</span>
                            {/* H3-05: null-guarded MFE/MAE — this file has real nulls */}
                            <span className="text-right font-mono-num text-caption text-ink-tertiary">{num(c.mfePct ?? null, 1, "%")}</span>
                            <span className="text-right font-mono-num text-caption text-ink-tertiary">{num(c.maePct ?? null, 1, "%")}</span>
                            {/* H3-09: the machine-derived note is the only reason field */}
                            <span className="truncate pl-2 text-caption text-ink-muted">{c.note}</span>
                          </Link>
                        );
                      })}
                      {g.key === "STOPPED" && isPro && (
                        <p className="px-2 pt-1 text-[10px] text-ink-muted">
                          States WIN / STOPPED / STOPPED (gap-through) / NO DATA are the only outcome classes the
                          outcomes file emits. NO TRIGGER, EXPIRED and INVALIDATED are not recorded by the backend
                          and are deliberately not shown.
                        </p>
                      )}
                    </div>
                  )
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </AppShell>
  );
}
