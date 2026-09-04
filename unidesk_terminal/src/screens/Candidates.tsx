import { useMemo, useState } from "react";
import { motion } from "framer-motion";
import { AppShell } from "../components/shell/AppShell";
import { FilterChip } from "../components/ui/FilterChip";
import { Chip } from "../components/ui/Chip";
import { ThrustCohortBanner } from "../components/widgets/ThrustCohortBanner";
import { useMode } from "../lib/ModeContext";
import { useReport } from "../lib/useReport";
import { chopBandDisplay, compareCandidates, mapCandidates, stopRoomDisplay, triggerDistPct } from "../lib/candidates";
import { deriveState, STATE_META, type ActionableState } from "../lib/status";
import { rsDelta1D, rsTrend, temporalFor } from "../lib/metricHistory";
import { sectorFor } from "../lib/sectors";
import { Sparkline } from "../components/ui/Sparkline";
import { SETUP_LABEL, type Candidate, type SetupType } from "../data/fixtures";
import type { RawBaseEpisode } from "../data/tonight";
import { Cell, LabelList, ReferenceArea, ReferenceLine, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis, ZAxis } from "recharts";

/*
  CANDIDATES — cross-sectional lab (UI_BUILD_SPEC_V1 PART 7). This screen
  does NOT repeat Home 2's section feed (C-01): it is one ranked research
  table, a quadrant landscape with selectable real-field axes, and panels
  for accumulation and tightness evidence. Every column/axis maps to a
  real report field (C-02/C-04).
*/

type AxisKey = "clean_entry" | "setup_entry" | "rs_accumulation" | "tight_entry" | "risk_reward";

// C-04: only axis pairs whose fields exist in the report.
interface AxisDef {
  key: AxisKey;
  label: string;
  x: (c: Candidate) => number | null;
  y: (c: Candidate) => number | null;
  xlabel: string;
  ylabel: string;
}

const AXES: AxisDef[] = [
  {
    /* Default. Setup quality is 100.0 for every candidate (it is a
       rule-completion flag, not a graded score — see features/thrust.py and
       the I7 invariant), so "Setup × Entry" cannot separate anything.
       ChopScore genuinely varies (spread ~28) AND is independent of reward
       geometry, so this pair asks a real question: which names are BOTH
       cleanly-behaved and well-timed? Y is inverted — high = clean. */
    key: "clean_entry", label: "Cleanliness × Entry",
    x: (c) => c.entryTiming ?? null,
    y: (c) => (c.chopScore != null ? 100 - c.chopScore : null),
    xlabel: "Entry quality →", ylabel: "↑ Cleanliness (low chop)",
  },
  {
    key: "setup_entry", label: "Setup × Entry",
    x: (c) => c.entryTiming ?? null, y: (c) => c.setupQuality ?? null,
    xlabel: "Entry quality →", ylabel: "↑ Setup quality",
  },
  {
    key: "rs_accumulation", label: "RS × Accumulation",
    x: (c) => c.activityScore?.activity_score ?? null, y: (c) => c.rsRank ?? null,
    xlabel: "Reactor Scale (proxy) →", ylabel: "↑ RS rank",
  },
  {
    key: "tight_entry", label: "Tightness × Entry",
    x: (c) => c.entryTiming ?? null, y: (c) => (c.contraction != null ? 100 - Math.min(100, c.contraction * 50) : null),
    xlabel: "Entry quality →", ylabel: "↑ Tightness (from contraction)",
  },
  {
    key: "risk_reward", label: "Risk × Reward",
    x: (c) => {
      if (c.close == null || c.invalidation == null || !c.close) return null;
      return ((c.close - c.invalidation) / c.close) * 100;
    },
    y: (c) => c.rr ?? null,
    xlabel: "Risk to stop (% of close) →", ylabel: "↑ R:R",
  },
];

const STATES = Object.keys(STATE_META) as ActionableState[];
const SETUP_TYPES = Object.keys(SETUP_LABEL) as SetupType[];
// B-5: CHOP and STOP/TH gained their band word beside the raw number.
const GRID = "grid-cols-[36px_40px_96px_110px_90px_70px_70px_44px_64px_56px_64px_60px_60px_112px_112px_92px]";

/* Chop band -> tone. High chop = shakeout-prone, so VERY_CHOPPY reads as a
   warning even when every other column looks good. */
const CHOP_TONE: Record<string, string> = {
  CLEAN: "text-positive",
  MODERATE: "text-ink-secondary",
  MESSY: "text-warning",
  VERY_CHOPPY: "text-danger",
};

/* §16: regime-aware research lens — UI emphasis only, never a score.
   Listed priorities are limited to columns this build actually renders. */
const RESEARCH_LENS: Record<string, { priorities: string[]; note: string }> = {
  CHOP: {
    priorities: ["rs", "rvol", "tight", "entry", "quality"],
    note: "In chop: leadership, volume and tight setups only — entry precision matters more than pattern size.",
  },
  BULL: {
    priorities: ["quality", "tight", "rr"],
    note: "In a broad bull: setup quality and tightness lead; participation carries mediocre entries.",
  },
  BEAR: {
    priorities: ["rvol", "quality"],
    note: "Defensive: demand volume confirmation and top-tier quality; scarcity is normal.",
  },
};
function lensFor(regimeNote?: string) {
  const regime = (regimeNote ?? "").split(/[ (—]/)[0] ?? "";
  return RESEARCH_LENS[regime] ?? { priorities: [], note: "Regime unclear — standard emphasis." };
}
const PRIORITY_LABEL: Record<string, string> = {
  rs: "RS", rvol: "RVOL", tight: "Tightness", entry: "Entry precision",
  quality: "Setup quality", rr: "Reward vs risk",
};

export function Candidates() {
  const { mode } = useMode();
  const isPro = mode === "pro";
  const report = useReport();
  const lens = lensFor(report.honesty_footer.regime_note);
  const all = useMemo(() => mapCandidates(report), [report]);
  const episodes = useMemo(
    () => new Map((report.base_episodes ?? []).map((e) => [e.symbol, e])),
    [report],
  );

  const [activeSetupTypes, setActiveSetupTypes] = useState<Set<SetupType>>(new Set());
  const [activeStates, setActiveStates] = useState<Set<ActionableState>>(new Set());
  const [axisKey, setAxisKey] = useState<AxisKey>("clean_entry");
  const [preset, setPreset] = useState<string>("");
  const [cohort, setCohort] = useState<Set<string>>(new Set());
  const [hiddenCols, setHiddenCols] = useState<Set<string>>(new Set());

  const presetNames = useMemo(() => {
    const names = new Set<string>();
    for (const e of report.base_episodes ?? []) if (e.vcp_match?.preset) names.add(e.vcp_match.preset);
    return [...names].sort();
  }, [report]);

  const filtered = useMemo(() => {
    let base = all;
    if (activeSetupTypes.size > 0) base = base.filter((c) => activeSetupTypes.has(c.setupType));
    if (activeStates.size > 0) base = base.filter((c) => activeStates.has(deriveState(c)));
    return base;
  }, [all, activeSetupTypes, activeStates]);

  // P-04: rankable detectors rank first (one documented comparator);
  // non-rankable rows stay visible below, unranked, with their reason.
  const ranked = useMemo(() => {
    const ok = filtered.filter((c) => c.detectorTrust?.rankable !== false).sort(compareCandidates);
    const notOk = filtered
      .filter((c) => c.detectorTrust?.rankable === false)
      .sort((a, b) => a.symbol.localeCompare(b.symbol));
    return [...ok.map((c) => ({ c, rank: 0 })), ...notOk.map((c) => ({ c, rank: undefined as number | undefined }))]
      .map((row, i) => ({ ...row, rank: row.rank !== undefined ? i + 1 : undefined }));
  }, [filtered]);

  // P-03: preset as a pure predicate over the episode's own vcp_match —
  // every exclusion carries the specific failed rules.
  const presetResult = useMemo(() => {
    if (!preset) return null;
    const included: string[] = [];
    const excluded: { symbol: string; failedRules: string[] }[] = [];
    for (const c of filtered) {
      const raw = episodes.get(c.symbol)?.vcp_match as unknown as
        | { preset: string; included: boolean; failed_rules: string[] }
        | { preset: string; included: boolean; failed_rules: string[] }[]
        | null | undefined;
      const match = Array.isArray(raw)
        ? raw.find((m) => m.preset === preset)
        : raw && raw.preset === preset ? raw : undefined;
      if (match) {
        if (match.included) included.push(c.symbol);
        else excluded.push({ symbol: c.symbol, failedRules: match.failed_rules });
      } else {
        excluded.push({ symbol: c.symbol, failedRules: ["no base episode / no preset evaluation for this symbol"] });
      }
    }
    return { included, excluded };
  }, [preset, filtered, episodes]);

  const axis = AXES.find((a) => a.key === axisKey) ?? AXES[0];

  // Raw values first, so we can report the true spread and keep them for tooltips.
  const rawRows = useMemo(
    () => filtered
      .map((c) => ({ symbol: c.symbol, x: axis.x(c), y: axis.y(c), z: c.rsRank ?? null }))
      .filter((r): r is { symbol: string; x: number; y: number; z: number | null } => r.x != null && r.y != null),
    [filtered, axis],
  );

  const ys = rawRows.map((r) => r.y);
  const xs = rawRows.map((r) => r.x);
  const ySpread = ys.length ? Math.max(...ys) - Math.min(...ys) : 0;
  const xSpread = xs.length ? Math.max(...xs) - Math.min(...xs) : 0;
  const yMin = ys.length ? Math.min(...ys) : 0;
  const yMax = ys.length ? Math.max(...ys) : 0;

  /* Plotting raw 0-100 scores crushes every point against an edge whenever the
     cohort is tightly clustered (setup quality is 100.0 for all 88 names, so the
     whole field sat on the top border and the lower quadrants were structurally
     empty). Plot the PERCENTILE WITHIN TONIGHT'S COHORT instead: points spread
     across the full square by construction, and the midlines at 50 become a
     real median split. Raw values are kept for the tooltip so a percentile is
     never mistaken for the underlying score. */
  const pctRank = (vals: number[], v: number): number => {
    if (vals.length <= 1) return 50;
    const below = vals.filter((x) => x < v).length;
    const equal = vals.filter((x) => x === v).length;
    return ((below + 0.5 * equal) / vals.length) * 100;
  };
  const scatterRows = useMemo(
    () => rawRows.map((r) => ({ ...r, x: pctRank(xs, r.x), y: pctRank(ys, r.y), rawX: r.x, rawY: r.y })),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [rawRows],
  );
  const scatterExcluded = filtered.length - scatterRows.length;
  // §7.9: permanently label the top names (by the Y metric)
  const labelled = useMemo(() => [...scatterRows].sort((a, b) => b.y - a.y).slice(0, 3), [scatterRows]);
  const bySymbol = useMemo(() => new Map(all.map((c) => [c.symbol, c])), [all]);

  function toggle<T>(set: Set<T>, setter: (s: Set<T>) => void, v: T) {
    const next = new Set(set);
    if (next.has(v)) next.delete(v); else next.add(v);
    setter(next);
  }

  const cohortRows = all.filter((c) => cohort.has(c.symbol));

  return (
    <AppShell breadcrumb={["Candidates"]}>
      <div className="flex flex-col gap-4 p-4">
        <div className="flex flex-wrap items-center gap-1.5">
          {SETUP_TYPES.map((s) => (
            <FilterChip key={s} label={SETUP_LABEL[s]} active={activeSetupTypes.has(s)}
              onClick={() => toggle(activeSetupTypes, setActiveSetupTypes, s)} />
          ))}
          <span className="mx-1 h-4 w-px bg-border-subtle" aria-hidden />
          {STATES.map((s) => (
            <FilterChip key={s} label={STATE_META[s].label} active={activeStates.has(s)}
              onClick={() => toggle(activeStates, setActiveStates, s)} />
          ))}
          <span className="mx-1 h-4 w-px bg-border-subtle" aria-hidden />
          <span className="text-caption text-ink-muted">preset:</span>
          <select value={preset} onChange={(e) => setPreset(e.target.value)} aria-label="Screen preset"
            className="rounded-chip border border-border bg-surface-input px-2 py-1 text-caption text-ink-primary outline-none">
            <option value="">none</option>
            {presetNames.map((p) => <option key={p} value={p}>{p}</option>)}
          </select>
        </div>

        {/* C-03/C-04 + §15.2 Row A: landscape 8 cols + research lens 4 cols */}
        <div className="grid grid-cols-12 gap-4">
          <div className="col-span-12 rounded-card border border-border bg-surface-1 px-3.5 py-3 xl:col-span-8">
            <div className="mb-2 flex flex-wrap items-baseline justify-between gap-2">
              <h2 className="text-h4 font-semibold text-ink-primary">Opportunity landscape</h2>
              <div role="group" aria-label="Scatter axes" className="flex items-center gap-1 rounded-chip border border-border-subtle p-0.5">
                {AXES.map((a) => (
                  <button key={a.key} onClick={() => setAxisKey(a.key)} aria-pressed={axisKey === a.key}
                    className={"rounded-[4px] px-2 py-1 text-caption font-medium transition-colors " +
                      (axisKey === a.key ? "bg-accent-bg text-accent-strong" : "text-ink-tertiary hover:text-ink-secondary")}>
                    {a.label}
                  </button>
                ))}
              </div>
            </div>
            <div className="relative h-80 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <ScatterChart margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
                  <ReferenceArea x1={50} x2={100} y1={50} y2={100} fill="var(--accent)" fillOpacity={0.05} stroke="none" />
                  <XAxis type="number" dataKey="x" name={axis.xlabel} domain={[0, 100]}
                    tick={{ fill: "var(--text-tertiary)", fontSize: 11 }} stroke="var(--border)"
                    label={{ value: `${axis.xlabel} — percentile of tonight's ${scatterRows.length}`, position: "insideBottom", offset: -4, fill: "var(--text-tertiary)", fontSize: 11 }} />
                  <YAxis type="number" dataKey="y" name={axis.ylabel} domain={[0, 100]}
                    tick={{ fill: "var(--text-tertiary)", fontSize: 11 }} stroke="var(--border)"
                    label={{ value: `${axis.ylabel} — percentile`, angle: -90, position: "insideLeft", fill: "var(--text-tertiary)", fontSize: 11 }} />
                  <ZAxis type="number" dataKey="z" range={[40, 260]} />
                  <ReferenceLine x={50} stroke="var(--border-strong)" strokeDasharray="4 4" />
                  <ReferenceLine y={50} stroke="var(--border-strong)" strokeDasharray="4 4" />
                  <Tooltip cursor={{ stroke: "var(--border-strong)", strokeDasharray: "3 3" }}
                    content={({ active, payload }) => {
                      if (!active || !payload?.length) return null;
                      const d = payload[0].payload as { symbol: string; x: number; y: number; z: number | null; rawX?: number; rawY?: number };
                      const yl = axis.ylabel.replace("↑ ", "").replace("← ", "");
                      return (
                        <div className="rounded-btn border border-border-strong bg-surface-1 px-2.5 py-2 text-caption shadow-lg">
                          <div className="font-semibold text-ink-primary">{d.symbol}</div>
                          {/* raw score first — the percentile is only the plotting position */}
                          <div className="font-mono-num text-ink-secondary">
                            {axis.xlabel} {d.rawX?.toFixed(1) ?? d.x.toFixed(1)} · {yl} {d.rawY?.toFixed(1) ?? d.y.toFixed(1)}
                            {d.z != null ? ` · RS ${d.z.toFixed(0)}` : ""}
                          </div>
                          <div className="font-mono-num text-ink-muted">
                            percentile {d.x.toFixed(0)} / {d.y.toFixed(0)} of tonight's cohort
                          </div>
                        </div>
                      );
                    }} />
                  <Scatter data={scatterRows} fillOpacity={0.55}
                    onClick={(d) => { const sym = (d as unknown as { symbol?: string }).symbol; if (sym) location.hash = `#/stock/${sym}`; }} cursor="pointer">
                    {scatterRows.map((d) => {
                      const c = bySymbol.get(d.symbol);
                      const tone = c ? STATE_META[deriveState(c)].tone : "neutral";
                      const fill = tone === "positive" ? "var(--positive)" : tone === "info" ? "var(--info)" : tone === "warning" ? "var(--warning)" : tone === "danger" ? "var(--danger)" : "var(--accent)";
                      return <Cell key={d.symbol} fill={fill} fillOpacity={0.55} stroke={fill} />;
                    })}
                  </Scatter>
                  {/* top candidates permanently labelled (spec §7.9) */}
                  <Scatter data={labelled} fill="transparent" stroke="transparent" isAnimationActive={false}>
                    <LabelList dataKey="symbol" position="top" offset={6}
                      style={{ fill: "var(--text-secondary)", fontSize: 10, fontWeight: 600 }} />
                  </Scatter>
                </ScatterChart>
              </ResponsiveContainer>
              {/* Axes are percentiles within tonight's cohort, so the midlines are
                  a true median split and all four quadrants are reachable —
                  no point can be crushed against an edge. */}
              <QuadLabel className="left-6 top-2" text="WATCH" />
              <QuadLabel className="right-6 top-2" text="PRIME ZONE" strong />
              <QuadLabel className="left-6 bottom-8" text="IGNORE" />
              <QuadLabel className="right-6 bottom-8" text="SPECULATIVE" />
            </div>
            {/* Positions are percentile ranks, so the plot always spreads. That must
                not hide a cohort whose RAW scores are effectively identical — rank
                order among near-equal values is close to noise. */}
            {ySpread < 2 && xSpread < 2 ? (
              <p className="mt-1.5 text-caption text-warning">
                Both raw scores are nearly identical tonight (spread {ySpread.toFixed(1)} / {xSpread.toFixed(1)} points).
                Points are spread by percentile rank, but that ordering separates near-equal values — treat this
                view as low-confidence and try another axis pair.
              </p>
            ) : ySpread < 2 ? (
              <p className="mt-1.5 text-caption text-warning">
                {axis.ylabel.replace("↑ ", "").replace("← ", "")} is nearly identical ({yMin.toFixed(0)}–{yMax.toFixed(0)}) across all plotted candidates.
                The vertical axis shows percentile rank so points separate, but that ranking carries little real
                signal tonight — differentiation is on {axis.xlabel}.
              </p>
            ) : null}
            {scatterExcluded > 0 && (
              <p className="mt-1.5 text-caption text-ink-muted">
                {scatterExcluded} candidate{scatterExcluded === 1 ? "" : "s"} not plotted — the selected axes'
                fields are not computed for them (no invented zeros).
              </p>
            )}
          </div>

          <div className="col-span-12 rounded-card border border-border bg-surface-1 px-3.5 py-3 xl:col-span-4">
            <div className="mb-2 flex items-baseline justify-between">
              <h2 className="text-h4 font-semibold text-ink-primary">Research lens</h2>
              <Chip tone="warning">{(report.honesty_footer.regime_note ?? "").split(/[ (]/)[0] || "—"}</Chip>
            </div>
            <div className="mb-2 flex flex-wrap gap-1.5">
              {lens.priorities.map((p) => (
                <span key={p} className="rounded-btn border border-accent-border bg-accent-bg px-2 py-0.5 text-caption font-medium text-accent-strong">
                  {PRIORITY_LABEL[p] ?? p}
                </span>
              ))}
            </div>
            <p className="text-caption text-ink-secondary">{lens.note}</p>
            <p className="mt-2 text-[10px] text-ink-muted">UI emphasis only — not a score, not validated weighting.</p>
          </div>
        </div>

        {/* C-02: ranked research table */}
        <div className="rounded-card border border-border bg-surface-1 px-3.5 py-3">
          <div className="mb-2 flex flex-wrap items-baseline justify-between gap-2">
            <h2 className="text-h4 font-semibold text-ink-primary">Ranked research table</h2>
            <div className="flex items-center gap-2">
              <span className="text-caption text-ink-muted">
                {filtered.length} shown · ranked by state, then trigger distance, then RS
              </span>
              <ColumnToggle hidden={hiddenCols} setHidden={setHiddenCols} />
            </div>
          </div>
          {/* B-4: the cohort-level stop-room finding, stated once, computed
              from the live report — never a hardcoded count. */}
          <ThrustCohortBanner cohort={all} />
          <div className="overflow-x-auto">
            <div className="min-w-[1240px]">
              <div className={`grid ${GRID} gap-2 px-2 pb-1 text-caption font-medium text-ink-muted`}>
                <span /><span />
                <span>STOCK</span>
                <span>SETUP</span>
                {!hiddenCols.has("sector") && <span>SECTOR</span>}
                {!hiddenCols.has("quality") && <span className="text-right" title="stock quality 0-100: leadership + trend + participation; shows coverage % on the stock page">QUALITY</span>}
                {!hiddenCols.has("entry") && <span className="text-right" title="entry quality 0-100: how attractive today's price is vs the trigger and stop">ENTRY</span>}
                {!hiddenCols.has("rs") && <span className="text-right" title="relative strength: percentile rank of 20-day performance vs every scanned stock">RS</span>}
                {!hiddenCols.has("drs") && <span className="text-right">RS Δ1D</span>}
                {!hiddenCols.has("rvol") && <span className="text-right" title="volume vs recent normal">RVOL</span>}
                {!hiddenCols.has("tight") && <span className="text-right" title="range compression: recent range vs prior range (lower = tighter)">TIGHT</span>}
                {!hiddenCols.has("trend") && <span>RS 10D</span>}
                {!hiddenCols.has("rr") && <span className="text-right" title="reward vs risk: distance to trigger over distance to stop">R:R</span>}
                {!hiddenCols.has("chop") && (
                  <span className="text-right" title="ChopScore — price-action cleanliness over the prior 20 sessions. High = choppy, shakeout-prone. Independent of reward geometry.">CHOP</span>
                )}
                {!hiddenCols.has("thrust") && (
                  <span className="text-right" title="Stop distance in the stock's own thrust-days (ADRMAX). Below 1.0 the stop sits inside one ordinary strong day's expansion.">STOP/TH</span>
                )}
                <span>STATE</span>
              </div>
              {ranked.map(({ c, rank }) => {
                const sec = sectorFor(c.symbol);
                const drs = rsDelta1D(c.symbol, c.rsRank ?? null);
                const trend = rsTrend(c.symbol);
                return (
                  <motion.label layout transition={{ duration: 0.18, ease: "easeOut" }} key={c.symbol + c.setupType}
                    className={`grid cursor-pointer ${GRID} items-center gap-2 rounded-chip px-2 py-1.5 text-caption hover:bg-surface-2`}>
                    <input type="checkbox" checked={cohort.has(c.symbol)}
                      onChange={() => toggle(cohort, setCohort, c.symbol)} aria-label={`Compare ${c.symbol}`} />
                    <span className="text-right font-mono-num text-ink-muted">
                      {rank == null ? "·" : String(rank).padStart(2, "0")}
                    </span>
                    <span className="font-semibold text-ink-primary">{c.symbol}</span>
                    <span className="truncate text-ink-tertiary"
                      title={c.detectorTrust && !c.detectorTrust.rankable ? c.detectorTrust.reason : undefined}>
                      {SETUP_LABEL[c.setupType] ?? c.setupType}
                      {c.detectorTrust && !c.detectorTrust.rankable && <span className="ml-1 text-warning">⚠</span>}
                    </span>
                    {!hiddenCols.has("sector") && (
                      <span className="truncate text-ink-tertiary" title={sec ? sec.industry : "not in vendor mapping"}>
                        {sec ? sec.sector : "—"}
                      </span>
                    )}
                    {!hiddenCols.has("quality") && <Num v={c.stockStrength} digits={0} />}
                    {!hiddenCols.has("entry") && <Num v={c.entryTiming} digits={0} warn={!!c.entryQualitySnapshot && c.entryQualitySnapshot.coverage < 0.9} />}
                    {!hiddenCols.has("rs") && <Num v={c.rsRank} digits={0} />}
                    {!hiddenCols.has("drs") && (
                      <span className={"text-right font-mono-num " + (drs == null ? "text-ink-muted" : drs >= 0 ? "text-positive" : "text-danger")}
                        title="RS rank change vs this symbol's prior archived session">
                        {drs == null ? "—" : `${drs > 0 ? "+" : ""}${drs.toFixed(0)}`}
                      </span>
                    )}
                    {!hiddenCols.has("rvol") && <Num v={c.rvol} digits={1} suffix="x" />}
                    {!hiddenCols.has("tight") && <Num v={c.contraction} digits={2} />}
                    {!hiddenCols.has("trend") && (
                      <span className="flex justify-center"
                        title={trend.length > 1 ? `RS over last ${trend.length} archived sessions` : "no RS history in archive"}>
                        {trend.length > 2
                          ? <Sparkline values={trend} width={56} height={16} strokeWidth={1.2} color="var(--info)" />
                          : <span className="font-mono-num text-ink-muted">—</span>}
                      </span>
                    )}
                    {!hiddenCols.has("rr") && <Num v={c.rr} digits={1} suffix="R" dangerBelow={1} />}
                    {!hiddenCols.has("chop") && (
                      (() => {
                        // B-5: the raw ChopScore keeps its place; the band word
                        // is the same mirror of chop_band the cards render.
                        const d = chopBandDisplay(c.chopBand);
                        return (
                          <span className={"text-right font-mono-num " + (c.chopBand ? CHOP_TONE[c.chopBand] : "text-ink-muted")}
                            title={c.chopBand ? `${c.chopBand.replace("_", " ").toLowerCase()} price action — ChopScore ${c.chopScore?.toFixed(1) ?? "—"}/100 (higher = choppy); band from the report's chop_band (features/thrust.py)` : "not computed"}>
                            {c.chopScore == null ? "—" : c.chopScore.toFixed(0)}
                            {d && <span className="ml-1 font-sans text-[10px] text-ink-tertiary">{d.word}</span>}
                          </span>
                        );
                      })()
                    )}
                    {!hiddenCols.has("thrust") && (
                      /* Under 1.0 the entire risk budget is smaller than one
                         ordinary strong day — flagged, since that is what makes
                         a stop get taken out by noise rather than by thesis. */
                      (() => {
                        const d = stopRoomDisplay(c.stopThrustDays);
                        return (
                          <span className={"text-right font-mono-num " +
                            (c.stopThrustDays == null ? "text-ink-muted"
                              : c.stopThrustDays < 1 ? "font-semibold text-danger" : "text-ink-secondary")}
                            title={c.adrMaxPct == null
                              ? "needs 250 sessions of history — not computed"
                              : `stop is ${c.stopThrustDays?.toFixed(2)} x ADRMAX (${c.adrMaxPct.toFixed(1)}% thrust). Bands: ≥1.5 roomy · 1.0–1.5 OK · 0.75–1.0 tight · <0.75 inside noise.`}>
                            {c.stopThrustDays == null ? "—" : c.stopThrustDays.toFixed(2)}
                            {d && <span className="ml-1 font-sans text-[10px] font-normal text-ink-tertiary">{d.word}</span>}
                          </span>
                        );
                      })()
                    )}
                    <span><Chip tone={STATE_META[deriveState(c)].tone}>{STATE_META[deriveState(c)].label}</Chip></span>
                  </motion.label>
                );
              })}
              {ranked.length === 0 && (
                <p className="px-2 py-3 text-caption text-ink-tertiary">No candidates match the selected filters.</p>
              )}
            </div>
          </div>
          {isPro && (
            <p className="mt-2 text-[10px] text-ink-muted">
              Historical expectancy per setup: not computed — gated behind the N5 experiment. No expectancy
              number is shown anywhere by design.
              {/* C-10 (audit S2-3): stock-quality coverage is systematically
                  partial, so the ⚠ fired on every row and stopped being a
                  warning. Stated once here, computed from the live rows. */}
              {(() => {
                const withSq = filtered.filter((c) => c.stockQuality != null);
                const lowCov = withSq.filter((c) => (c.stockQuality as { coverage: number }).coverage < 0.9).length;
                return lowCov > 0
                  ? ` Stock-quality coverage is below 90% for ${lowCov} of ${withSq.length} shown rows (partial evidence by design — named unknowns on each stock page), so the QUALITY column no longer warns per row.`
                  : "";
              })()}
              {" "}ENTRY ⚠ = coverage below 90%.
            </p>
          )}
        </div>

        {/* P-03: preset result — every exclusion explains itself */}
        {preset && presetResult && (
          <div className="rounded-card border border-border bg-surface-1 px-3.5 py-3">
            <h2 className="mb-2 text-h4 font-semibold text-ink-primary">
              Preset: {preset} · structure description, not advice
            </h2>
            <p className="mb-2 text-caption text-ink-secondary">
              {presetResult.included.length} included · {presetResult.excluded.length} excluded
            </p>
            <div className="grid grid-cols-1 gap-1.5 sm:grid-cols-2">
              {presetResult.included.map((s) => (
                <div key={s} className="rounded-chip bg-surface-2 px-2.5 py-1.5 text-caption text-positive">✓ {s}</div>
              ))}
              {presetResult.excluded.map((e) => (
                <div key={e.symbol} className="rounded-chip bg-surface-2 px-2.5 py-1.5 text-caption text-ink-tertiary"
                  title={e.failedRules.join("; ")}>
                  · {e.symbol} — excluded: {e.failedRules.join("; ") || "no rule recorded"}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* C-08: cohort comparison — aligned columns, no radar chart */}
        {cohortRows.length > 1 && (
          <div className="rounded-card border border-border bg-surface-1 px-3.5 py-3">
            <h2 className="mb-2 text-h4 font-semibold text-ink-primary">
              Cohort comparison · {cohortRows.length} selected
            </h2>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[560px] text-caption">
                <thead>
                  <tr className="text-left text-ink-muted">
                    <th className="py-1 pr-3 font-medium">Metric</th>
                    {cohortRows.map((c) => (
                      <th key={c.symbol} className="py-1 pr-3 font-semibold text-ink-primary">{c.symbol}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="font-mono-num">
                  {([
                    ["Setup", (c: Candidate) => SETUP_LABEL[c.setupType] ?? c.setupType],
                    ["Close", (c: Candidate) => c.close?.toFixed(2) ?? "—"],
                    ["Quality", (c: Candidate) => fmt(c.stockStrength, 0)],
                    ["Entry", (c: Candidate) => fmt(c.entryTiming, 0)],
                    ["RS", (c: Candidate) => fmt(c.rsRank, 0)],
                    ["RVOL", (c: Candidate) => fmt(c.rvol, 1) + (c.rvol == null ? "" : "x")],
                    ["Tight", (c: Candidate) => fmt(c.contraction, 2)],
                    ["R:R", (c: Candidate) => fmt(c.rr, 1)],
                    ["Pivot dist", (c: Candidate) => { const d = triggerDistPct(c); return d == null ? "—" : d.toFixed(1) + "%"; }],
                    ["Base stage", (c: Candidate) => c.baseStage?.replace(/_/g, " ") ?? "—"],
                    ["State", (c: Candidate) => STATE_META[deriveState(c)].label],
                  ] as [string, (c: Candidate) => string][]).map(([label, get]) => (
                    <tr key={label} className="border-t border-border-subtle">
                      <td className="py-1 pr-3 font-sans text-ink-muted">{label}</td>
                      {cohortRows.map((c) => (
                        <td key={c.symbol} className="py-1 pr-3 text-ink-secondary">{get(c)}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* C-06/C-07: accumulation + tightness evidence */}
        <div className="rounded-card border border-border bg-surface-1 px-3.5 py-3">
          <div className="mb-1 flex items-baseline justify-between">
            <h2 className="text-h4 font-semibold text-ink-primary">Accumulation evidence</h2>
            <span className="text-caption text-ink-muted">proxies — not confirmed institutional activity</span>
          </div>
          <AccumulationPanel candidates={filtered} isPro={isPro} />
          <h3 className="mb-1.5 mt-3 text-caption font-medium uppercase text-ink-muted">Tightness</h3>
          <TightnessPanel candidates={filtered} episodes={episodes} />
        </div>
      </div>
    </AppShell>
  );
}

function Num({ v, digits, suffix, dangerBelow, warn }: {
  v: number | null | undefined; digits: number; suffix?: string; dangerBelow?: number; warn?: boolean;
}) {
  const text = v == null ? "—" : `${v.toFixed(digits)}${suffix ?? ""}`;
  return (
    <span className={"text-right font-mono-num " +
      (v != null && dangerBelow != null && v < dangerBelow ? "font-semibold text-danger"
        : warn ? "text-warning" : "text-ink-secondary")}>
      {text}{warn && v != null ? " ⚠" : ""}
    </span>
  );
}

function QuadLabel({ className, text, strong }: { className: string; text: string; strong?: boolean }) {
  return (
    <span className={"pointer-events-none absolute rounded-chip px-1.5 py-0.5 text-[10px] tracking-wide " + className +
      (strong ? " bg-accent-bg font-semibold text-accent-strong" : " bg-surface-2 text-ink-muted")}>
      {text}
    </span>
  );
}

function ColumnToggle({ hidden, setHidden }: { hidden: Set<string>; setHidden: (s: Set<string>) => void }) {
  const cols = ["sector", "quality", "entry", "rs", "drs", "rvol", "tight", "trend", "rr", "chop", "thrust"];
  function flip(c: string) {
    const next = new Set(hidden);
    if (next.has(c)) next.delete(c); else next.add(c);
    setHidden(next);
  }
  return (
    <div className="flex items-center gap-1" role="group" aria-label="Show or hide columns">
      <span className="text-caption text-ink-muted">columns:</span>
      {cols.map((c) => <FilterChip key={c} label={c} active={!hidden.has(c)} onClick={() => flip(c)} />)}
    </div>
  );
}

/* C-06: Reactor Scale temporal view. The caveat below is carried verbatim —
   it must never be presented as institutional identity or a risk input. */
function AccumulationPanel({ candidates }: { candidates: Candidate[]; isPro: boolean }) {
  const rows = candidates
    .filter((c) => c.activityScore != null)
    .sort((a, b) => (b.activityScore!.activity_score ?? 0) - (a.activityScore!.activity_score ?? 0))
    .slice(0, 10);
  if (rows.length === 0) {
    return <p className="text-caption text-ink-tertiary">No accumulation evidence computed for the filtered candidates.</p>;
  }
  const G = "grid-cols-[96px_64px_64px_80px_80px_76px_110px_90px]";
  return (
    <div className="overflow-x-auto">
      <div className="min-w-[760px]">
        <div className={`grid ${G} gap-2 px-2 pb-1 text-[10px] font-medium uppercase tracking-wide text-ink-muted`}>
          <span>Stock</span>
          <span className="text-right">Now</span>
          <span className="text-right">Prev</span>
          <span className="text-right">5D avg</span>
          <span className="text-right">10D avg</span>
          <span className="text-right">Streak</span>
          <span>10D trend</span>
          <span className="text-right">Delivery</span>
        </div>
        {rows.map((c) => {
          const t = temporalFor(c.symbol, "act");
          const delta = t.now != null && t.prev != null ? t.now - t.prev : null;
          return (
            <a key={c.symbol} href={`#/stock/${c.symbol}`}
              className={`grid ${G} items-center gap-2 rounded-chip px-2 py-1.5 text-caption hover:bg-surface-2`}>
              <span className="font-semibold text-ink-primary">{c.symbol}</span>
              <span className="text-right font-mono-num font-semibold text-ink-primary"
                title="Reactor Scale — must never be presented as institutional identity, trade direction, or a risk input">
                {t.now == null ? "—" : t.now.toFixed(0)}
              </span>
              <span className={"text-right font-mono-num " + (delta == null ? "text-ink-muted" : delta >= 0 ? "text-positive" : "text-danger")}>
                {delta == null ? "—" : `${delta > 0 ? "+" : ""}${delta.toFixed(0)}`}
              </span>
              <span className="text-right font-mono-num text-ink-secondary">{t.avg5 == null ? "—" : t.avg5.toFixed(0)}</span>
              <span className="text-right font-mono-num text-ink-secondary">{t.avg10 == null ? "—" : t.avg10.toFixed(0)}</span>
              <span className="text-right font-mono-num text-ink-secondary">{t.streak}</span>
              <span>
                {t.trend.length > 2
                  ? <Sparkline values={t.trend} width={100} height={16} strokeWidth={1.2} color="var(--info)" />
                  : <span className="font-mono-num text-ink-muted">—</span>}
              </span>
              <span className="text-right font-mono-num text-ink-secondary">
                {c.deliveryRatio == null ? "—" : (c.deliveryRatio * 100).toFixed(0) + "%"}
              </span>
            </a>
          );
        })}
      </div>
    </div>
  );
}

/* C-07: contraction sequence straight off the BaseEpisode — nothing recomputed
   in the UI; a symbol with no episode says so rather than showing a guess. */
function TightnessPanel({ candidates, episodes }: { candidates: Candidate[]; episodes: Map<string, RawBaseEpisode> }) {
  const rows = candidates
    .filter((c) => c.contraction != null)
    .sort((a, b) => (a.contraction ?? 99) - (b.contraction ?? 99))
    .slice(0, 8);
  if (rows.length === 0) {
    return <p className="text-caption text-ink-tertiary">No contraction fields computed for the filtered candidates.</p>;
  }
  return (
    <div className="overflow-x-auto">
      <div className="min-w-[560px]">
        <div className="grid grid-cols-[96px_90px_1fr] gap-2 px-2 pb-1 text-caption font-medium text-ink-muted">
          <span>STOCK</span>
          <span className="text-right">COMPRESSION</span>
          <span>CONTRACTION SEQUENCE (base episode)</span>
        </div>
        {rows.map((c) => {
          const depths = episodes.get(c.symbol)?.pullback_depths ?? null;
          return (
            <div key={c.symbol} className="grid grid-cols-[96px_90px_1fr] items-center gap-2 rounded-chip px-2 py-1.5 text-caption hover:bg-surface-2">
              <span className="font-semibold text-ink-primary">{c.symbol}</span>
              <span className="text-right font-mono-num text-ink-secondary">{c.contraction!.toFixed(2)}</span>
              <span className="truncate font-mono-num text-ink-tertiary">
                {depths && depths.length > 0 ? depths.map((d) => d.toFixed(1) + "%").join(" → ") : "no base episode for this symbol"}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function fmt(v: number | null | undefined, digits: number): string {
  return v == null ? "—" : v.toFixed(digits);
}
