import { useMemo, useState } from "react";
import { motion } from "framer-motion";
import { AppShell } from "../components/shell/AppShell";
import { CandidateCard } from "../components/widgets/CandidateCard";
import { ThrustCohortBanner } from "../components/widgets/ThrustCohortBanner";
import { HonestyFooter } from "../components/widgets/HonestyFooter";
import { Chip } from "../components/ui/Chip";
import { SectionHeader } from "../components/ui/SectionHeader";
import { MetricRow } from "../components/ui/MetricRow";
import { CountUp } from "../components/ui/CountUp";
import { useMode } from "../lib/ModeContext";
import { useReport } from "../lib/useReport";
import {
  compareCandidates, groupBySetup, mapCandidates, OTHER_SECTION_KEY, SECTION_METRIC,
  triggerDistPct, type SetupSectionKey,
} from "../lib/candidates";
import { regimeHistoryBefore } from "../lib/regimeHistory";
import { playbookFor, PLAYBOOK_CAVEAT } from "../lib/playbook";
import { deriveState, STATE_META } from "../lib/status";
import { sessionsElapsedAfter } from "../data/stockHistory";
import { SETUP_LABEL, type Candidate } from "../data/fixtures";
import { REAL_CALLS } from "../data/outcomes";

/*
  TONIGHT (spec §3.2 + §9-§12): one page, four anchored subsections with a
  sticky subnav — Market State / Setup Feed / Prior Calls / Trigger Proximity.
  Reading order per §9.2: market state → action implication → breadth
  evidence → direction/change → opportunity concentration → diagnostics.
  Every number traces to the selected report; absent series render "—"
  (§0.1); leadership/sector data does not exist and is NOT faked (§9.8 gap).
*/

const SUBNAV = [
  { id: "market-state", label: "Market State" },
  { id: "setup-feed", label: "Setup Feed" },
  { id: "prior-calls", label: "Prior Calls" },
  { id: "trigger-proximity", label: "Trigger Proximity" },
];

const REGIME_COLOR: Record<string, string> = {
  BULL: "var(--positive)",
  BEAR: "var(--danger)",
  CHOP: "var(--warning)",
};

export function Tonight() {
  const { mode } = useMode();
  const isPro = mode === "pro";
  const report = useReport();
  const hf = report.honesty_footer;

  const candidates = useMemo(() => mapCandidates(report), [report]);
  const sections = useMemo(() => groupBySetup(candidates), [candidates]);
  const regimeHistory = useMemo(() => regimeHistoryBefore(report.session_date, 20), [report.session_date]);
  // A-6 (audit S2-1): the detector count was a hardcoded "seven detectors"
  // while Settings said "6 of 8" and the report emitted 6. Both numbers are
  // derived here from the selected report: detectors with candidates tonight,
  // out of the detectors the report carries a trust audit for.
  const firedDetectors = useMemo(
    () => new Set(candidates.map((c) => c.setupType)).size,
    [candidates],
  );
  const auditedDetectors = useMemo(
    () => Object.keys(report.detector_trust ?? {}).length,
    [report],
  );

  function scrollTo(id: string) {
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  return (
    <AppShell breadcrumb={["Tonight"]}>
      {/* sticky subnav (spec §3.2 preferred) */}
      <div className="sticky top-[-20px] z-10 -mx-6 mb-5 flex items-center gap-1 border-b border-subtle bg-surface-0/95 px-6 py-2 backdrop-blur-sm">
        {SUBNAV.map((s, i) => (
          <span key={s.id} className="flex items-center gap-1">
            {i > 0 && <span className="px-1 text-ink-muted">·</span>}
            <button
              onClick={() => scrollTo(s.id)}
              className="rounded-[5px] px-2 py-1 text-t3 font-medium text-ink-secondary transition-colors hover:bg-surface-2 hover:text-ink-primary"
            >
              {s.label}
            </button>
          </span>
        ))}
      </div>

      <div className="flex flex-col gap-8">
        {/* ============ MARKET STATE (§9) ============ */}
        <section>
          <a id="market-state" className="block scroll-mt-24" />
          <div className="grid grid-cols-12 gap-8">
            {/* Hero (§9.4) — editorial composition, no box */}
            <div className="col-span-12 xl:col-span-8">
              <div className="text-[10px] font-semibold uppercase tracking-[0.14em] text-ink-tertiary">Market state</div>
              <div className="mt-2 flex items-end justify-between gap-4">
                <RegimeHero note={hf.regime_note} built={hf.regime_built} beginner={!isPro} />
                <div className="pb-2 text-right">
                  <CountUp
                    className="font-mono-num text-h1 font-semibold tracking-tight text-ink-primary"
                    value={hf.pct_above_ema50 ?? 0}
                    format={(v) => (hf.pct_above_ema50 != null ? `${v.toFixed(1)}%` : "—")}
                    title={hf.universe_scanned ? `${Math.round(((hf.pct_above_ema50 ?? 0) / 100) * hf.universe_scanned)} of ${hf.universe_scanned.toLocaleString()} scanned stocks above their 50-day average` : undefined}
                  />
                  <div className="text-caption text-ink-tertiary">above EMA50</div>
                </div>
              </div>

              {/* position strip (§9.4) */}
              <div className="mt-4">
                <div className="flex justify-between text-[10px] uppercase tracking-wide text-ink-muted">
                  <span>Risk-Off</span><span>Weak</span><span>CHOP</span><span>Healthy</span><span>Strong</span>
                </div>
                <div className="relative mt-1 h-1.5 rounded-full bg-surface-2">
                  <div className="absolute top-1/2 h-3 w-3 -translate-y-1/2 rounded-full border-2 border-surface-0 bg-accent"
                    style={{ left: `calc(${hf.pct_above_ema50 != null ? Math.min(100, Math.max(0, hf.pct_above_ema50)) : 50}% - 6px)` }} />
                </div>
              </div>

              {/* 20-session breadth micro-bars (§9.4 "20D") — real stored breadth */}
              {regimeHistory.length > 0 && (
                <div className="mt-4 flex items-end gap-2">
                  <span className="text-caption text-ink-muted">20D</span>
                  <div className="flex flex-1 items-end gap-[3px]" aria-hidden>
                    {regimeHistory.map((row) => {
                      const pct = row.pct_above_ema50;
                      const h = pct != null ? Math.max(8, Math.min(100, pct)) : 4;
                      const color = REGIME_COLOR[row.regime ?? row.regime_replayed ?? ""] ?? "var(--neutral)";
                      return (
                        <div key={row.date} className="flex-1 rounded-t-[2px]"
                          style={{ height: `${h * 0.28}px`, background: color, opacity: 0.65 }}
                          title={`${row.date} — ${pct != null ? pct.toFixed(1) + "% above EMA50" : "no breadth"} · ${row.regime ?? row.regime_replayed ?? "not classified"}`} />
                      );
                    })}
                  </div>
                </div>
              )}
            </div>

            {/* Playbook (§9.5) — 4 cols, the one tinted "action" element */}
            <div className="col-span-12 rounded-card border border-accent-border/60 bg-accent-bg/40 px-5 py-4 xl:col-span-4">
              <div className="mb-3 flex items-baseline justify-between">
                <span className="text-[10px] font-semibold uppercase tracking-[0.14em] text-ink-tertiary">Tonight's playbook</span>
                <span className="text-[10px] text-warning" title={PLAYBOOK_CAVEAT}>{isPro ? "⚠ " + PLAYBOOK_CAVEAT : "guidance"}</span>
              </div>
              <PlaybookRows note={hf.regime_note} />
            </div>
          </div>

          {/* Participation (§9.6) — ruled editorial section, no box */}
          <div className="mt-8">
            <SectionHeader
              eyebrow="Breadth evidence"
              title="Market participation"
              subtitle="universe in tooltips · deltas vs archived sessions"
              right={<span className="text-[10px] uppercase tracking-wide text-ink-muted">TODAY · 1D · 5D</span>}
            />
            <ParticipationTable hf={hf} history={regimeHistory} sessionDate={report.session_date} />
          </div>

          {/* Funnel (§9.7) + derived breadth (§9.6 second half) */}
          <div className="mt-8 grid grid-cols-12 gap-8">
            <div className="col-span-12 lg:col-span-6">
              <SectionHeader eyebrow="Opportunity concentration" title="Opportunity funnel" subtitle="each step defined in tooltips" />
              <OpportunityFunnel hf={hf} candidates={candidates} />
              <p className="mt-3 text-caption text-ink-tertiary">
                Leadership concentration is not shown — sector and theme data are not in tonight's export.
              </p>
            </div>
            <div className="col-span-12 lg:col-span-6 lg:border-l lg:border-border lg:pl-8">
              <SectionHeader eyebrow="Market internals" title="Breadth analytics" subtitle="derived nightly from the full scan" />
              <BreadthAnalyticsPanel hf={hf} />
            </div>
          </div>
        </section>

        {/* ============ SETUP FEED (§10) ============ */}
        <section>
          <a id="setup-feed" className="block scroll-mt-24" />
          <SectionHeader
            title="Setup feed"
            subtitle={`${firedDetectors} of ${auditedDetectors} detectors fired tonight · identical row grammar · chart thumbnails are real bars`}
            count={`${candidates.length} candidates`}
          />
          <ThrustCohortBanner cohort={candidates} />
          <div className="mt-2 flex flex-col gap-5">
            {sections.map(([setupType, list], idx) => {
              // A-1: zero-candidate sections render in Pro only — a "0" is
              // informative there; Beginner gets no empty headers.
              if (list.length === 0 && !isPro) return null;
              return (
                <motion.div
                  key={setupType}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.22, delay: Math.min(idx * 0.04, 0.25), ease: "easeOut" }}
                >
                  <SetupSection
                    setupType={setupType}
                    list={list}
                    trust={report.setups?.find((s) => s.detector === setupType)?.trust}
                    isPro={isPro}
                    sessionDate={report.session_date}
                  />
                </motion.div>
              );
            })}
          </div>
        </section>

        {/* ============ PRIOR CALLS (§11, compact) ============ */}
        <section>
          <a id="prior-calls" className="block scroll-mt-24" />
          <SectionHeader
            eyebrow="Outcome review"
            title="Prior calls"
            subtitle="newest session whose 10-bar horizon has elapsed relative to this report — open and no-data calls shown, never scored"
            right={<span className="text-[10px] uppercase tracking-wide text-ink-muted">win · stopped · flat · open · no data</span>}
          />
          <PriorCallsCompact />
        </section>

        {/* ============ TRIGGER PROXIMITY (§12) ============ */}
        <section>
          <a id="trigger-proximity" className="block scroll-mt-24" />
          <SectionHeader
            eyebrow="Actionable watch"
            title="Trigger proximity"
            subtitle="distance now vs prior session · groups by state"
            count={`${candidates.filter((c) => triggerDistPct(c) != null).length} tracked`}
          />
          <ProximitySection candidates={candidates} isPro={isPro} />
        </section>

        {/* Data quality bar (§7.6) — the one diagnostics drawer */}
        <HonestyFooter hf={hf} />
      </div>
    </AppShell>
  );
}

/* ---- hero regime ---- */
function RegimeHero({ note, built, beginner }: { note: string; built: boolean; beginner?: boolean }) {
  const first = built ? (note.split(/[ (—]/)[0] ?? "") : "";
  const label = ["BULL", "BEAR", "CHOP"].includes(first) ? first : "UNKNOWN";
  const color = REGIME_COLOR[label] ?? "var(--neutral)";
  // H1-08: engineering tokens never in Beginner; Pro sees the verbatim note.
  // C-8: the strip used to leave the parenthetical unclosed — "CHOP (breadth
  // 50.0% above EMA50" read as a rendering bug. After stripping, any bracket
  // opened but not closed is closed.
  const display = beginner ? beginnerGloss(note) : note;
  return (
    <div>
      <div className="text-display font-bold leading-none tracking-tight" style={{ color }}>{label}</div>
      <p className="mt-2 max-w-2xl text-body text-ink-secondary">{display}</p>
    </div>
  );
}

/** Beginner gloss of the verbatim regime_note: engineering tokens stripped,
 *  brackets guaranteed balanced. */
function beginnerGloss(note: string): string {
  let s = note
    .replace(/,?\s*breadth_only/g, "")
    .replace(/;\s*[^;)]*already scored[^)]*\)?/g, "");
  const opens = (s.match(/\(/g) ?? []).length;
  const closes = (s.match(/\)/g) ?? []).length;
  if (opens > closes) s = s.replace(/[\s;,]+$/, "") + ")";
  return s;
}

/* ---- playbook (§9.5) — qualitative only, X-03: never a number ---- */
function PlaybookRows({ note }: { note: string }) {
  const pb = playbookFor(note);
  const rows: [string, string][] = [
    ["Exposure", pb.exposure],
    ["Favour", pb.favour],
    ["Avoid", pb.avoid],
    ["Selectivity", pb.selectivity],
  ];
  return (
    <dl className="grid grid-cols-[88px_1fr] gap-y-2.5">
      {rows.map(([k, v]) => (
        <div key={k} className="contents">
          <dt className="text-t3 text-ink-muted">{k}</dt>
          <dd className="text-t3 font-medium text-ink-primary">{v}</dd>
        </div>
      ))}
    </dl>
  );
}

/* ---- participation (§9.6): TODAY / 1D / 5D deltas from the archived
   breadth series — every delta computed from real stored sessions ---- */
function ParticipationTable({ hf, history, sessionDate }: {
  hf: ReturnType<typeof useReport>["honesty_footer"];
  history: ReturnType<typeof regimeHistoryBefore>;
  sessionDate: string;
}) {
  const prior = useMemo(() => {
    // history rows strictly BEFORE the selected session
    const before = history.filter((r) => r.date < sessionDate);
    return { d1: before[before.length - 1] ?? null, d5: before[before.length - 5] ?? null };
  }, [history, sessionDate]);

  const delta = (today: number | null | undefined, prev: number | null | undefined) => {
    if (today == null || prev == null) return null;
    const d = today - prev;
    return `${d >= 0 ? "↑" : "↓"} ${Math.abs(d).toFixed(1)} pp`;
  };

  const ema21Pct = hf.above_ema21_of ? (hf.above_ema21 / hf.above_ema21_of) * 100 : null;
  const rows = [
    { label: "Above EMA21", today: ema21Pct, d1: delta(ema21Pct, prior.d1?.pct_above_ema21), d5: delta(ema21Pct, prior.d5?.pct_above_ema21), tone: "var(--accent)",
      tip: hf.above_ema21_of ? `${hf.above_ema21} of ${hf.above_ema21_of} scanned stocks are above their short-term trend average (21-day, called EMA21)` : undefined },
    { label: "Above EMA50", today: hf.pct_above_ema50, d1: delta(hf.pct_above_ema50, prior.d1?.pct_above_ema50), d5: delta(hf.pct_above_ema50, prior.d5?.pct_above_ema50), tone: "var(--accent)",
      tip: hf.universe_scanned ? `${Math.round(((hf.pct_above_ema50 ?? 0) / 100) * hf.universe_scanned)} of ${hf.universe_scanned.toLocaleString()} scanned stocks are above their long-term trend average (50-day, called EMA50)` : undefined },
    { label: "Near 52W high", today: hf.breadth?.near_highs_pct, d1: delta(hf.breadth?.near_highs_pct, prior.d1?.near_highs_pct), d5: delta(hf.breadth?.near_highs_pct, prior.d5?.near_highs_pct), tone: "var(--positive)",
      tip: hf.universe_scanned ? `trading within 5% of their 52-week high · ${hf.universe_scanned.toLocaleString()} scanned` : undefined },
    { label: "Near 52W low", today: hf.breadth?.near_lows_pct, d1: delta(hf.breadth?.near_lows_pct, prior.d1?.near_lows_pct), d5: delta(hf.breadth?.near_lows_pct, prior.d5?.near_lows_pct), tone: "var(--danger)",
      tip: hf.universe_scanned ? `trading within 5% of their 52-week low · ${hf.universe_scanned.toLocaleString()} scanned` : undefined },
  ];
  const anyPrior = prior.d1 != null;

  return (
    <div>
      <div className="grid grid-cols-[130px_1fr_64px_64px_64px] gap-x-3 pb-1 text-[10px] font-medium uppercase tracking-wide text-ink-muted">
        <span>Metric</span><span />
        <span className="text-right">Today</span><span className="text-right">1D</span><span className="text-right">5D</span>
      </div>
      {rows.map((r) => (
        <MetricRow key={r.label} label={r.label} barPct={r.today} barTone={r.tone} tooltip={r.tip}
          value={r.today != null ? r.today.toFixed(1) + "%" : "—"} delta={r.d1} delta5={r.d5} />
      ))}
      {!anyPrior && (
        <p className="pt-1.5 text-caption text-ink-tertiary">
          Deltas appear once earlier sessions exist in the local archive.
        </p>
      )}
    </div>
  );
}

/* ---- opportunity funnel (§9.7) — every step from real footer counts ---- */
function OpportunityFunnel({ hf, candidates }: {
  hf: ReturnType<typeof useReport>["honesty_footer"];
  candidates: Candidate[];
}) {
  const scanned = hf.universe_scanned ?? 0;
  const gated = hf.universe_gate_skips_total ?? 0;
  const skipped = hf.universe_skipped_insufficient_history ?? 0;
  const raw = scanned + gated + skipped;
  // Each step must be a SUBSET of the one above it. Previously "near trigger"
  // filtered all candidates rather than the high-quality survivors, so the
  // funnel widened at the last step (64 -> 75), which a funnel cannot do.
  const highQual = candidates.filter((c) => (c.stockStrength ?? -1) >= 60);
  const highQ = highQual.length;
  const nearTrig = highQual.filter((c) => {
    const d = triggerDistPct(c);
    return d != null && d <= 8; // within the READY band or already past trigger
  }).length;

  const steps = [
    { label: "Universe seen", n: raw, tip: `${scanned.toLocaleString()} scanned + ${gated.toLocaleString()} gated out + ${skipped.toLocaleString()} skipped (short history)` },
    { label: "Passed gates · live", n: scanned, tip: "post price/turnover/ETF/circuit gates and liveness (traded on the session date)" },
    { label: "Technical candidates", n: candidates.length, tip: "≥1 detector fired VALID" },
    { label: "High quality", n: highQ, tip: "stock quality score ≥ 60 (same threshold as the WATCH state)" },
    { label: "· and near / past trigger", n: nearTrig, tip: "of the high-quality names, those within 8% of trigger or past it (READY band) — a subset of the step above" },
  ];
  // A funnel cannot widen. If a future step breaks that, surface it rather
  // than drawing a misleading chart.
  const nonMonotonic = steps.some((s, i) => i > 0 && s.n > steps[i - 1].n);
  const max = Math.max(1, ...steps.map((s) => s.n));
  return (
    <div className="flex flex-col gap-2">
      {nonMonotonic && (
        <p className="text-caption text-warning">
          Funnel steps are not nested — a later step is larger than the one above it. Treat these as
          independent filters, not a funnel.
        </p>
      )}
      {steps.map((s, i) => (
        <div key={s.label}>
          {i > 0 && <div className="pb-1 pl-1 text-[10px] text-ink-muted">↓</div>}
          <div className="flex items-center gap-3" title={s.tip}>
            <span className="w-44 shrink-0 text-t3 text-ink-secondary">{s.label}</span>
            <div className="h-4 flex-1 overflow-hidden rounded-sm bg-surface-2">
              <div className="h-full rounded-sm bg-accent/50" style={{ width: Math.max(2, (s.n / max) * 100) + "%" }} />
            </div>
            <span className="w-14 shrink-0 text-right font-mono-num text-t3 font-semibold text-ink-primary">
              {s.n.toLocaleString()}
            </span>
          </div>
        </div>
      ))}
    </div>
  );
}

/* ---- breadth analytics + NH/NL balance (§9.6 second half) ---- */
function BreadthAnalyticsPanel({ hf }: { hf: ReturnType<typeof useReport>["honesty_footer"] }) {
  const a = hf.breadth?.analytics;
  if (!a) {
    return <p className="text-t3 text-ink-tertiary">Breadth analytics not computed in this report.</p>;
  }
  const interp = (v: number | null, pos: string, neg: string, neutral: string, band = 0.05) =>
    v == null ? "—" : v > band ? pos : v < -band ? neg : neutral;
  return (
    <div>
      <dl className="grid grid-cols-[130px_1fr_auto] gap-y-2">
        {[
          { k: "New highs vs lows", tip: "how many stocks near 52-week highs minus those near lows, balanced against the whole list", v: a.net_nh_nl, fmt: (v: number) => v.toFixed(3), read: interp(a.net_nh_nl, "Positive", "Negative", "Neutral") },
          { k: "Stocks closing up", tip: "share of scanned stocks that closed above their previous close", v: a.up_down_close_pct, fmt: (v: number) => v.toFixed(1) + "%", read: a.up_down_close_pct == null ? "—" : a.up_down_close_pct > 50 ? "Positive" : "Negative" },
          { k: "Volume vs normal", tip: "today's traded volume divided by its recent norm", v: a.volume_ratio, fmt: (v: number) => v.toFixed(2), read: a.volume_ratio == null ? "—" : a.volume_ratio > 1 ? "Above normal" : "Below normal" },
          { k: "Volatility vs normal", tip: "how much prices swung today relative to recent swings", v: a.volatility_ratio, fmt: (v: number) => v.toFixed(2), read: a.volatility_ratio == null ? "—" : a.volatility_ratio > 1 ? "Elevated" : "Contained" },
          { k: "Breakouts vs breakdowns", tip: "upward range breaks minus downward range breaks (needs the breakout detector pass)", v: a.bo_bd_ratio, fmt: (v: number) => v.toFixed(2), read: "—" },
        ].map((r) => (
          <div key={r.k} className="contents">
            <dt className="text-t3 text-ink-secondary" title={(r as { tip?: string }).tip}>{r.k}</dt>
            <dd className="text-center font-mono-num text-t3 font-semibold text-ink-primary">
              {r.v == null ? "—" : r.fmt(r.v)}
            </dd>
            <dd className="text-right text-t3 text-ink-tertiary">{r.read}</dd>
          </div>
        ))}
      </dl>
      {a.net_nh_nl != null && (
        <div className="mt-4">
          <div className="relative h-1.5 rounded-full bg-surface-2">
            <div className="absolute top-1/2 h-3 w-3 -translate-y-1/2 rounded-full border-2 border-surface-0 bg-accent"
              style={{ left: `calc(${Math.min(100, Math.max(0, (a.net_nh_nl + 5) / 10 * 100))}% - 6px)` }} />
          </div>
          <div className="mt-1 flex justify-between text-[10px] uppercase tracking-wide text-ink-muted">
            <span>Low dominance</span><span>High dominance</span>
          </div>
        </div>
      )}
    </div>
  );
}

/* ---- setup sections (§10) ---- */
function SetupSection({ setupType, list, trust, isPro, sessionDate }: {
  setupType: SetupSectionKey;
  list: Candidate[];
  trust?: { status: string; reason: string; version: string; rankable: boolean };
  isPro: boolean;
  sessionDate: string;
}) {
  // §10.8 defaults: zero-candidate sections collapsed; others open
  // (large sections still collapse to keep the page scannable).
  const actionable = list.filter((c) => ["PRIME", "READY", "NEAR_PIVOT"].includes(deriveState(c))).length;
  const extended = list.filter((c) => deriveState(c) === "EXTENDED").length;
  const [collapsed, setCollapsed] = useState(list.length === 0 || list.length > 12);
  const rankable = trust?.rankable !== false;
  const ordered = [...list].sort(rankable ? compareCandidates : (a, b) => a.symbol.localeCompare(b.symbol));
  const metric = setupType === OTHER_SECTION_KEY ? undefined : SECTION_METRIC[setupType];
  const label = setupType === OTHER_SECTION_KEY
    ? "Other / unmapped detector"
    : SETUP_LABEL[setupType];

  return (
    <div>
      <button
        onClick={() => setCollapsed(!collapsed)}
        aria-expanded={!collapsed}
        className="mb-1 flex w-full items-baseline gap-3 text-left"
      >
        <span className="text-t2 text-ink-muted">{collapsed ? "▸" : "▾"}</span>
        <h3 className="text-t3 font-semibold uppercase tracking-wider text-ink-primary">{label}</h3>
        <span className="font-mono-num text-t3 text-ink-muted">{list.length === 0 ? "0" : list.length}</span>
        {list.length > 0 && (
          <span className="text-caption text-ink-tertiary">
            {actionable} actionable{extended > 0 ? ` · ${extended} extended` : ""}
          </span>
        )}
        {setupType === OTHER_SECTION_KEY && list.length > 0 && (
          <span className="text-[10px] text-warning"
            title="This detector has no UI section mapping yet — candidates are listed here rather than dropped. Extend SETUP_ORDER/SETUP_LABEL in src/data/fixtures.ts and lib/candidates.ts.">
            unmapped — shown so nothing disappears
          </span>
        )}
        {trust && !trust.rankable && (
          <span className="text-[10px] text-warning" title={trust.reason}>{trust.status} — not ranked</span>
        )}
        {setupType === "ipo_base" && (
          <span className="text-[10px] text-ink-tertiary"
            title="The scan's history floor (~3 months of sessions) cannot verify fresh listings, so this detector never sees a genuine new IPO — a known, frozen coverage limit (B2-8).">
            recent listings (~3 months) not covered
          </span>
        )}
        {isPro && metric?.blocked && list.length > 0 && (
          <span className="text-[10px] text-ink-muted" title="H2-11">setup metric blocked — {metric.blocked}</span>
        )}
      </button>
      {!collapsed && (
        list.length === 0 ? (
          <p className="px-3 py-1.5 text-t3 text-ink-tertiary">No {label} candidates tonight.</p>
        ) : (
          <div className="overflow-hidden rounded-card border border-subtle bg-surface-1">
            {ordered.map((c, i) => (
              <CandidateCard key={c.symbol + "-" + c.setupType} candidate={c}
                rank={rankable ? i + 1 : undefined} sessionDate={sessionDate} />
            ))}
          </div>
        )
      )}
    </div>
  );
}

/* ---- prior calls compact (§11.4/§11.5 on Tonight; full table on History) ---- */
/* Prior calls. A call is only scored once its 10-bar horizon has ELAPSED
   (win / stopped / flat). Picking the newest session with any non-unresolved
   row picked the LEAST-resolved session: with zero forward bars almost nothing
   can stop out, so it read 15 won / 1 stopped (94%) against a 35% archive base
   rate. Still-open calls are shown but never counted as wins. */
const HORIZON_BARS = 10;

function PriorCallsCompact() {
  // A-2 (audit S1-2): the old gate demanded EVERY call in a session have
  // finished its horizon. 238 rows across six symbols carry entry: null — no
  // geometry was ever derived, so they can NEVER resolve — and every recent
  // session holds ~7 of them, so no recent session could ever qualify and the
  // panel was stuck on 2026-05-21, drifting one day further behind daily.
  // The gate now matches its caption: the newest session whose 10-bar horizon
  // has elapsed relative to the newest bundled session, counted on the real
  // trading calendar (data/stockHistory). entry-null rows stay in the
  // displayed counts as "no data" — they just no longer gate the pick.
  const latest = useMemo(() => {
    const dates = [...new Set(REAL_CALLS.map((c) => c.date))].sort().reverse();
    for (const dt of dates) {
      if (sessionsElapsedAfter(dt) >= HORIZON_BARS) return dt;
    }
    return null;
  }, []);
  const age = latest ? sessionsElapsedAfter(latest) : null;
  const calls = useMemo(() => (latest ? REAL_CALLS.filter((c) => c.date === latest) : []), [latest]);
  const wins = calls.filter((c) => c.outcome === "hit_target");
  const stopped = calls.filter((c) => c.outcome === "stopped_out");
  const flat = calls.filter((c) => c.outcome === "resolved_flat");
  const stillOpen = calls.filter((c) => c.outcome === "open");
  const noData = calls.filter((c) => c.outcome === "unresolved");
  const rs = [...wins, ...stopped, ...flat].map((c) => c.rMultiple).filter((r): r is number => r != null);
  const avgR = rs.length ? rs.reduce((s, r) => s + r, 0) / rs.length : null;

  if (!latest || calls.length === 0) {
    return <p className="text-t3 text-ink-tertiary">No horizon-elapsed prior calls in the archive yet.</p>;
  }
  return (
    <div className="px-0.5">
      <div className="flex flex-wrap items-baseline gap-x-5 gap-y-1">
        <span className="font-mono-num text-t3 text-ink-muted">
          {latest}
          {age != null && (
            <span className="ml-1.5 text-caption text-ink-tertiary" title={`${age} trading sessions between this call date and the newest bundled session`}>
              · {age} sessions ago
            </span>
          )}
        </span>
        <span className="text-t3 font-semibold text-positive">{wins.length} won</span>
        <span className="text-t3 font-semibold text-danger">{stopped.length} stopped</span>
        {flat.length > 0 && <span className="text-t3 text-ink-secondary">{flat.length} flat</span>}
        {stillOpen.length > 0 && (
          <span className="text-t3 text-accent-strong" title="10-bar horizon has not elapsed — not scored">
            {stillOpen.length} still open
          </span>
        )}
        {noData.length > 0 && (
          <span className="text-t3 text-ink-tertiary"
            title="No entry geometry was ever derived for these calls (entry: null), so they can never resolve — a backend data defect, reported upstream">
            {noData.length} no data
          </span>
        )}
        {avgR != null && (
          <span className="font-mono-num text-t3 text-ink-secondary"
            title={rs.length < 10 ? "low sample — treat as noise" : "mean realised R"}>
            avg {avgR >= 0 ? "+" : ""}{avgR.toFixed(2)}R
            <span className="ml-1 text-ink-muted">n={rs.length}{rs.length < 10 ? " ⚠" : ""}</span>
          </span>
        )}
        <span className="ml-auto text-caption text-ink-muted">
          newest 10-bar-horizon-elapsed session · scorecard on History
        </span>
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-[3px]">
        {calls.slice(0, 60).map((c, i) => (
          <span key={c.symbol + i}
            className={"inline-block h-3 w-2.5 rounded-[2px] " +
              (c.outcome === "hit_target" ? "bg-positive"
                : c.outcome === "stopped_out" ? "bg-danger"
                : c.outcome === "open" ? "bg-accent/40"
                : c.outcome === "resolved_flat" ? "bg-ink-muted/30"
                : "border border-subtle bg-surface-2")}
            title={`${c.symbol} — ${c.outcome.replace("_", " ")}`} />
        ))}
        {calls.length > 60 && <span className="ml-1 text-[10px] text-ink-muted">+{calls.length - 60}</span>}
      </div>
    </div>
  );
}

/* ---- trigger proximity (§12.4) with prior → now drift ---- */
function ProximitySection({ candidates, isPro }: { candidates: Candidate[]; isPro: boolean }) {
  const groups: { title: string; rows: Candidate[] }[] = [
    { title: "AT TRIGGER", rows: [] },
    { title: "APPROACHING", rows: [] },
    { title: "GETTING LATE (past trigger)", rows: [] },
    { title: "FAR", rows: [] },
  ];
  for (const c of candidates) {
    const d = triggerDistPct(c);
    if (d == null) continue;
    if (d >= -2 && d <= 2) groups[0].rows.push(c);
    else if (d > 2 && d <= 8) groups[1].rows.push(c);
    else if (d < -2) groups[2].rows.push(c);
    else groups[3].rows.push(c);
  }
  return (
    <div className="grid grid-cols-12 gap-6">
      {groups.map((g) => (
        <div key={g.title} className="col-span-12 border-t border-border pt-3 md:col-span-6 xl:col-span-3">
          <div className="mb-2.5 text-caption font-semibold uppercase tracking-wider text-ink-muted">
            {g.title} <span className="font-mono-num text-ink-tertiary">· {g.rows.length}</span>
          </div>
          {g.rows.length === 0 ? (
            <p className="text-t3 text-ink-tertiary">— none —</p>
          ) : (
            <div className="flex flex-col gap-1">
              {g.rows.slice(0, 8).map((c) => (
                <ProximityRow key={c.symbol} c={c} isPro={isPro} />
              ))}
              {g.rows.length > 8 && <span className="pt-1 text-caption text-ink-tertiary">+ {g.rows.length - 8} more</span>}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

function ProximityRow({ c, isPro }: { c: Candidate; isPro: boolean }) {
  const now = triggerDistPct(c) as number;
  const prev = c.prior?.triggerDistance ?? null;
  const sm = STATE_META[deriveState(c)];
  const lowRR = c.rr != null && c.rr < 1.0;
  const driftTag = prev != null
    ? Math.abs(now) < Math.abs(prev) ? "approaching" : now < 0 ? "extending" : "fading"
    : null;
  return (
    <div className="flex items-center gap-2 py-1 text-t3">
      <span className="w-20 shrink-0 font-semibold text-ink-primary">{c.symbol}</span>
      <span className="flex-1 font-mono-num text-ink-secondary" title="distance to trigger: prior session → now">
        {prev != null ? `${prev > 0 ? "+" : ""}${prev.toFixed(1)}% → ` : "— → "}
        <span className="font-semibold text-ink-primary">{now > 0 ? "+" : ""}{now.toFixed(1)}%</span>
        {driftTag && <span className="ml-1.5 text-[10px] text-ink-tertiary">{driftTag}</span>}
      </span>
      {isPro && (
        <span className={"w-12 shrink-0 text-right font-mono-num " + (lowRR ? "text-danger" : "text-ink-muted")}
          title={lowRR ? "R:R below 1.0" : "Reward vs risk"}>
          {c.rr != null ? c.rr.toFixed(1) + "R" : "—"}
        </span>
      )}
      <span className="w-7 shrink-0 text-right font-mono-num text-ink-tertiary" title="stock quality grade">
        {c.stockStrength != null ? gradeOf(c.stockStrength) : "—"}
      </span>
      <span className="w-[74px] shrink-0 text-right"><Chip tone={sm.tone}>{sm.label}</Chip></span>
    </div>
  );
}

function gradeOf(score: number): string {
  return score >= 80 ? "A" : score >= 65 ? "B" : score >= 50 ? "C" : "D";
}
