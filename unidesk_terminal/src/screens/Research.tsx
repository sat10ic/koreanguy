import { FlaskConical, ShieldAlert, Skull } from "lucide-react";
import { AppShell } from "../components/shell/AppShell";
import { Chip } from "../components/ui/Chip";

/*
  RESEARCH (manual V2 §7, pro-focused): ablation ladder status, baseline
  comparisons, parameter register, leakage-suite status, negative findings
  board ("a killed feature is documented, not deleted" — manual rule R-H).
  The ablation ladder itself needs recorded live outcomes over weeks
  (GOAL.md hard stop #5) — every number below is illustrative until then.
*/
const ABLATION_STEPS = [
  { name: "Baseline (rule output only)", expectancy: null, note: "Reference point — no model applied." },
  { name: "+ Setup detection", expectancy: null, note: "Awaiting recorded outcomes" },
  { name: "+ Geometry / entry quality", expectancy: null, note: "Awaiting recorded outcomes" },
  { name: "+ Liquidity gate", expectancy: null, note: "Awaiting recorded outcomes" },
  { name: "+ Flow (optional live module)", expectancy: null, note: "Deferred — live module not built (N7)" },
  { name: "+ Social evidence", expectancy: null, note: "Deferred — U-P4.x owner decision pending" },
  { name: "+ Judge", expectancy: null, note: "Not built" },
];

const NEGATIVE_FINDINGS = [
  {
    feature: "Benchmark-less RS rank (universe percentile)",
    diedOn: "2026-06-30",
    reason: "Provisional only — RS rank needs an index-series benchmark to mean anything cross-session; universe percentile drifts with universe composition.",
    status: "Superseded, not deleted",
  },
];

export function Research() {
  return (
    <AppShell breadcrumb={["Research"]}>
      <div className="flex flex-col gap-4 p-4">
        <div className="rounded-card border border-border bg-surface-1 p-3.5">
          <div className="mb-2.5 flex items-center gap-1.5 text-caption text-ink-muted">
            <FlaskConical size={13} aria-hidden />
            Ablation ladder
            <Chip tone="neutral">Illustrative — needs weeks of recorded live outcomes</Chip>
          </div>
          <div className="flex flex-col gap-1.5">
            {ABLATION_STEPS.map((s, i) => (
              <div key={s.name} className="flex items-center gap-3 rounded-chip border border-border-subtle bg-surface-2 px-2.5 py-2">
                <span className="w-5 shrink-0 font-mono-num text-caption text-ink-muted">{i}</span>
                <span className="flex-1 text-caption text-ink-primary">{s.name}</span>
                <span className="font-mono-num text-caption text-ink-muted">
                  {s.expectancy === null ? "—" : `${s.expectancy > 0 ? "+" : ""}${s.expectancy}R`}
                </span>
                <span className="w-52 shrink-0 text-right text-caption text-ink-muted">{s.note}</span>
              </div>
            ))}
          </div>
        </div>

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
              on the short calendar rather than faked.
            </p>
          </div>

          <div className="rounded-card border border-border bg-surface-1 p-3.5">
            <div className="mb-2.5 text-caption text-ink-muted">Parameter register</div>
            <p className="text-caption text-ink-tertiary">
              Every threshold in the detector engine is caller-supplied config, not a literal (R14) — the register
              view (config hash, active weights) is queued behind SETTINGS.
            </p>
          </div>
        </div>

        <div className="rounded-card border border-border bg-surface-1 p-3.5">
          <div className="mb-2.5 flex items-center gap-1.5 text-caption text-ink-muted">
            <Skull size={13} aria-hidden />
            Negative findings board
          </div>
          <div className="flex flex-col gap-2">
            {NEGATIVE_FINDINGS.map((f) => (
              <div key={f.feature} className="rounded-chip border border-border-subtle bg-surface-2 p-3">
                <div className="flex items-center justify-between">
                  <span className="text-caption font-semibold text-ink-primary">{f.feature}</span>
                  <span className="font-mono-num text-caption text-ink-muted">{f.diedOn}</span>
                </div>
                <p className="mt-1 text-caption text-ink-tertiary">{f.reason}</p>
                <span className="mt-1.5 inline-block text-caption text-ink-muted">{f.status}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </AppShell>
  );
}
