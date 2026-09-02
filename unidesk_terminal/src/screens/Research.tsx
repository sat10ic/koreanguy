import { FlaskConical, LineChart as LineChartIcon, ShieldAlert, Skull } from "lucide-react";
import { AppShell } from "../components/shell/AppShell";
import { Chip } from "../components/ui/Chip";
import { RESEARCH_COVERAGE } from "../data/researchCoverage";
import { useMode } from "../lib/ModeContext";
import { REAL_CALLS, OUTCOMES_META } from "../data/outcomes";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";

/*
  RESEARCH (manual V2 §7, pro-focused): ablation ladder status, baseline
  comparisons, parameter register, leakage-suite status, negative findings
  board ("a killed feature is documented, not deleted" — manual rule R-H).

  Real-data wiring 2026-08-31: archive coverage, label-version health,
  detector hit rates, and the negative findings board are now read from
  the real event store (research_coverage_<date>.json). The ablation
  ladder expectancy numbers stay illustrative — they need N5 experiments
  to actually run (blocked on CA-applied series for long-window backtests).
*/
const ABLATION_STEPS = [
  { name: "Baseline (rule output only)", expectancy: null, note: "Reference point — no model applied." },
  { name: "+ Setup detection", expectancy: null, note: "Awaiting recorded N5 experiments" },
  { name: "+ Geometry / entry quality", expectancy: null, note: "Awaiting recorded N5 experiments" },
  { name: "+ Liquidity gate", expectancy: null, note: "Awaiting recorded N5 experiments" },
  { name: "+ Flow (optional live module)", expectancy: null, note: "Deferred — live module not built (N7)" },
  { name: "+ Social evidence", expectancy: null, note: "Deferred — U-P4.x owner decision pending" },
  { name: "+ Judge", expectancy: null, note: "Not built" },
];

export function Research() {
  const { mode } = useMode();
  const isPro = mode === "pro";
  const worstDetector = Object.entries(RESEARCH_COVERAGE.detectorValidHits)
    .sort(([, a], [, b]) => b - a)[0];
  const hitTotal = Object.values(RESEARCH_COVERAGE.detectorValidHits).reduce((a, b) => a + b, 0);
  const resolved = RESEARCH_COVERAGE.statusDistribution["RESOLVED"] ?? 0;
  const unresolved = RESEARCH_COVERAGE.statusDistribution["UNRESOLVED"] ?? 0;
  const partial = RESEARCH_COVERAGE.statusDistribution["PARTIAL"] ?? 0;
  const sampledTotal = Object.values(RESEARCH_COVERAGE.statusDistribution).reduce((a, b) => a + b, 0);
  return (
    <AppShell breadcrumb={["Research"]}>
      <div className="flex flex-col gap-4 p-4">
        {/* Archive coverage — real */}
        <div className="rounded-card border border-border bg-surface-1 p-3.5">
          <div className="mb-2.5 flex items-center gap-1.5 text-caption text-ink-muted">
            <FlaskConical size={13} aria-hidden />
            Archive coverage
          </div>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <div className="rounded-chip border border-border-subtle bg-surface-2 px-2.5 py-2">
              <div className="text-caption text-ink-muted">Partitions</div>
              <div className="font-mono-num text-body font-semibold text-ink-primary">{RESEARCH_COVERAGE.partitions}</div>
              <div className="mt-1 text-caption text-ink-tertiary">
                {RESEARCH_COVERAGE.partitionRange.oldest} → {RESEARCH_COVERAGE.partitionRange.newest}
              </div>
            </div>
            <div className="rounded-chip border border-border-subtle bg-surface-2 px-2.5 py-2">
              <div className="text-caption text-ink-muted">Sampled outcomes</div>
              <div className="font-mono-num text-body font-semibold text-ink-primary">{sampledTotal.toLocaleString()}</div>
              <div className="mt-1 text-caption text-ink-tertiary">
                <span className="text-positive">{resolved.toLocaleString()} resolved</span>
                <span> · </span>
                <span className="text-danger">{unresolved.toLocaleString()} unresolved</span>
                <span> · </span>
                <span className="text-ink-tertiary">{partial.toLocaleString()} partial</span>
              </div>
            </div>
            <div className="rounded-chip border border-border-subtle bg-surface-2 px-2.5 py-2">
              <div className="text-caption text-ink-muted">Label version</div>
              <div className={`font-mono-num text-body font-semibold ${RESEARCH_COVERAGE.labelVersionHomogeneous ? "text-positive" : "text-danger"}`}>
                {RESEARCH_COVERAGE.labelVersionHomogeneous ? "Homogeneous" : "MIXED"}
              </div>
              <div className="mt-1 text-caption text-ink-tertiary">{RESEARCH_COVERAGE.labelVersion}</div>
            </div>
            <div className="rounded-chip border border-border-subtle bg-surface-2 px-2.5 py-2">
              <div className="text-caption text-ink-muted">Detector hits (sampled)</div>
              <div className="font-mono-num text-body font-semibold text-ink-primary">{hitTotal.toLocaleString()}</div>
              <div className="mt-1 text-caption text-ink-tertiary">
                Top: {worstDetector ? `${worstDetector[0]} (${worstDetector[1]})` : "-"}
              </div>
            </div>
          </div>
        </div>

        {/* R-04: growth of ₹10,000 over the archived call outcomes.
            GROSS of costs — per-trade net-of-cost numbers are not on disk
            yet (netBps null on all rows), so the curve is labelled gross
            and this is backtest/labeller output, not account performance. */}
        <div className="rounded-card border border-border bg-surface-1 p-3.5">
          <div className="mb-2.5 flex items-center gap-1.5 text-caption text-ink-muted">
            <LineChartIcon size={13} aria-hidden />
            Cumulative R — archived calls, gross of costs
            <Chip tone="warning">backtest labels · not net · not account performance</Chip>
          </div>
          <EquityCurve />
          <p className="mt-2 text-caption text-ink-muted">
            Cumulative sum of R multiples over every RESOLVED call in the outcomes archive
            ({OUTCOMES_META.count.toLocaleString()} rows, labels {OUTCOMES_META.outcomeLabelsVersion}).
            A net-of-cost curve needs the per-trade cost figures the archive does not carry yet.
          </p>
        </div>

        {/* Ablation ladder — illustrative */}
        <div className="rounded-card border border-border bg-surface-1 p-3.5">
          <div className="mb-2.5 flex items-center gap-1.5 text-caption text-ink-muted">
            <FlaskConical size={13} aria-hidden />
            Ablation ladder
            <Chip tone="neutral">Expectancy numbers need N5 experiments</Chip>
          </div>
          <div className="flex flex-col gap-1.5">
            {ABLATION_STEPS.map((s, i) => (
              <div key={s.name} className="flex items-center gap-3 rounded-chip border border-border-subtle bg-surface-2 px-2.5 py-2">
                <span className="w-5 shrink-0 font-mono-num text-caption text-ink-muted">{i}</span>
                <span className="flex-1 text-caption text-ink-primary">{s.name}</span>
                {isPro && (
                  <span className="font-mono-num text-caption text-ink-muted">
                    {s.expectancy === null ? "—" : `${s.expectancy > 0 ? "+" : ""}${s.expectancy}R`}
                  </span>
                )}
                <span className="w-52 shrink-0 text-right text-caption text-ink-muted">
                  {isPro ? s.note : ""}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Leakage suite + Detector hit distribution */}
        <div className="grid grid-cols-2 gap-4">
          <div className="rounded-card border border-border bg-surface-1 p-3.5">
            <div className="mb-2.5 flex items-center gap-1.5 text-caption text-ink-muted">
              <ShieldAlert size={13} aria-hidden />
              Leakage suite
            </div>
            <div className="flex items-center justify-between rounded-chip border border-border-subtle bg-surface-2 px-2.5 py-2">
              <span className="text-caption text-ink-primary">Planted-bug leakage suite</span>
              <Chip tone="positive">Built (N4)</Chip>
            </div>
            <p className="mt-2 text-caption text-ink-muted">
              Expanding walk-forward + 5-session embargo, next-bar fill, net-of-cost simulator. 4y/1y folds refused
              on the short calendar rather than faked. Label version: {RESEARCH_COVERAGE.labelVersion}.
            </p>
          </div>

          <div className="rounded-card border border-border bg-surface-1 p-3.5">
            <div className="mb-2.5 text-caption text-ink-muted">Detector hit distribution</div>
            <div className="flex flex-col gap-1">
              {Object.entries(RESEARCH_COVERAGE.detectorValidHits)
                .sort(([, a], [, b]) => b - a)
                .slice(0, 6)
                .map(([name, hits]) => (
                  <div key={name} className="flex items-center justify-between rounded-chip bg-surface-2 px-2 py-1 text-caption">
                    <span className="text-ink-primary">{name}</span>
                    <span className="font-mono-num text-ink-tertiary">{hits}</span>
                  </div>
                ))}
            </div>
          </div>
        </div>

        {/* Negative findings — real from trust table */}
        <div className="rounded-card border border-border bg-surface-1 p-3.5">
          <div className="mb-2.5 flex items-center gap-1.5 text-caption text-ink-muted">
            <Skull size={13} aria-hidden />
            Negative findings board
            <Chip tone="neutral">{RESEARCH_COVERAGE.negativeFindings.length} findings</Chip>
          </div>
          <div className="flex flex-col gap-2">
            {RESEARCH_COVERAGE.negativeFindings.map((f) => (
              <div key={f.detector} className="rounded-chip border border-border-subtle bg-surface-2 p-3">
                <div className="flex items-center justify-between">
                  <span className="text-caption font-semibold text-ink-primary">{f.title}</span>
                  <Chip tone={f.trust?.status === "BLOCKED" ? "danger" : "warning"}>
                    {f.trust?.status === "BLOCKED" ? "Blocked" : "Review"}
                  </Chip>
                </div>
                <p className="mt-1 text-caption text-ink-tertiary">
                  {f.trust?.reason ? f.trust.reason.replace(/_/g, " ") : "No reason recorded"}
                </p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </AppShell>
  );
}

// R-04: equity curve from the real outcomes archive. Arithmetic CUMULATIVE
// R (a plain sum of rMultiples) — compounding a fixed fraction over 8,000+
// sequential calls produces astronomical, unreadable numbers; the sum is
// the honest legible unit. Gross of costs (net-bps null on 99.6% of rows).
function EquityCurve() {
  const resolved = REAL_CALLS
    .filter((c) => c.rMultiple != null)
    .sort((a, b) => (a.date < b.date ? -1 : 1));
  let cumR = 0;
  const points = resolved.map((c, i) => {
    cumR += c.rMultiple as number;
    return { i, date: c.date, cumR: Math.round(cumR * 10) / 10 };
  });
  const first = points[0]?.date ?? "";
  const last = points[points.length - 1]?.date ?? "";
  if (points.length < 2) {
    return <p className="text-caption text-ink-tertiary">Not enough resolved calls to draw a curve.</p>;
  }
  return (
    <div className="h-56 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={points} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
          <XAxis dataKey="i" tick={{ fill: "var(--text-tertiary)", fontSize: 10 }} stroke="var(--border)"
            tickFormatter={(i: number) => (i % 2000 === 0 ? String(i) : "")} />
          <YAxis tick={{ fill: "var(--text-tertiary)", fontSize: 10 }} stroke="var(--border)"
            tickFormatter={(v: number) => v.toFixed(0) + "R"} width={54} />
          <Tooltip
            cursor={{ stroke: "var(--border-strong)", strokeDasharray: "3 3" }}
            content={({ active, payload }) => {
              if (!active || !payload?.length) return null;
              const d = payload[0].payload as { date: string; cumR: number };
              return (
                <div className="rounded-chip border border-border-strong bg-surface-3 px-2 py-1.5 text-caption">
                  <div className="font-mono-num font-semibold text-ink-primary">{d.cumR > 0 ? "+" : ""}{d.cumR.toFixed(1)}R cumulative</div>
                  <div className="text-ink-tertiary">{d.date}</div>
                </div>
              );
            }} />
          <Line type="stepAfter" dataKey="cumR" stroke="var(--accent)" strokeWidth={1.5} dot={false} />
        </LineChart>
      </ResponsiveContainer>
      <div className="mt-1 flex justify-between text-[10px] text-ink-muted">
        <span>{first}</span>
        <span>{points.length.toLocaleString()} resolved calls · sum of R multiples (not compounded)</span>
        <span>{last}</span>
      </div>
    </div>
  );
}
