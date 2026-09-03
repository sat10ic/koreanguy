import { Database, SlidersHorizontal, ShieldCheck } from "lucide-react";
import { AppShell } from "../components/shell/AppShell";
import { Chip } from "../components/ui/Chip";
import { useMode } from "../lib/ModeContext";
import { SETTINGS } from "../data/settings";
import { useReport } from "../lib/useReport";

/*
  SETTINGS (manual V2 §7, row 6) — config surfacing, not config-authoring.
  Every number here is read from the committed settings snapshot
  (unidesk/run_settings_export.py), which reads costs.yaml + backend code
  constants — so this screen is the single place the desk's frozen
  assumptions are displayed honestly. There is still NO edit UI (weights/
  gates are caller-supplied config, R14) — that stays true and is stated.
*/
export function Settings() {
  const { mode, setMode } = useMode();
  const report = useReport();
  const hf = report.honesty_footer;

  return (
    <AppShell breadcrumb={["Settings"]}>
      <div className="flex flex-col gap-4 p-4">
        <div className="rounded-card border border-border bg-surface-1 p-3.5">
          <h2 className="mb-2.5 text-h4 font-semibold text-ink-primary">Display mode</h2>
          <p className="mb-3 text-caption text-ink-tertiary">
            One app structure, two vocabularies — Beginner and Pro never diverge in layout, only in labels.
          </p>
          <div role="group" aria-label="Display mode" className="flex w-fit items-center rounded-chip border border-border-subtle p-0.5">
            {(["beginner", "pro"] as const).map((m) => (
              <button
                key={m}
                onClick={() => setMode(m)}
                aria-pressed={mode === m}
                className={`min-h-[32px] rounded-[4px] px-4 py-1.5 text-caption font-medium capitalize transition-colors duration-150 ease-out ${
                  mode === m ? "bg-accent-bg text-accent-strong" : "text-ink-tertiary hover:text-ink-secondary"
                }`}
              >
                {m}
              </button>
            ))}
          </div>
        </div>

        <div className="rounded-card border border-border bg-surface-1 p-3.5">
          <div className="mb-2.5 flex items-center gap-1.5 text-caption text-ink-muted">
            <Database size={13} aria-hidden />
            Session data
          </div>
          <div className="grid grid-cols-3 gap-2">
            <div className="rounded-chip border border-border-subtle bg-surface-2 px-2.5 py-2">
              <div className="text-caption text-ink-muted">Report session</div>
              <div className="font-mono-num text-body font-semibold text-ink-primary">{report.session_date}</div>
            </div>
            <div className="rounded-chip border border-border-subtle bg-surface-2 px-2.5 py-2">
              <div className="text-caption text-ink-muted">Universe scanned</div>
              <div className="font-mono-num text-body font-semibold text-ink-primary">{hf.universe_scanned?.toLocaleString() ?? "—"}</div>
            </div>
            <div className="rounded-chip border border-border-subtle bg-surface-2 px-2.5 py-2">
              <div className="text-caption text-ink-muted">Above EMA50</div>
              <div className="font-mono-num text-body font-semibold text-ink-primary">{hf.pct_above_ema50 != null ? hf.pct_above_ema50.toFixed(1) + "%" : "—"}</div>
            </div>
          </div>
          {/* A-5 (audit S1-5): this line hardcoded "adjustment pass still open
              (N3)" while the report says confirmed_ca_applied / 4 actions — the
              CA pass is CLOSED on the verified table. Every claim now renders
              from the selected report's honesty_footer. */}
          <p className="mt-2 text-caption text-ink-muted">
            Source: NSE bhavcopy (EQ series). Corporate actions:{" "}
            <span className={hf.adjustment_status === "confirmed_ca_applied" ? "text-positive" : "text-warning"}>
              {hf.adjustment_status ?? "—"}
            </span>
            {hf.actions_applied != null ? ` — ${hf.actions_applied} action${hf.actions_applied === 1 ? "" : "s"} applied` : " — actions applied: —"}
            {hf.adjusted_symbols != null ? ` across ${hf.adjusted_symbols} symbol${hf.adjusted_symbols === 1 ? "" : "s"}` : ""}
            {hf.adjustment_note ? ` (${hf.adjustment_note})` : ""}
          </p>
        </div>

        {/* Real frozen config — costs + labels + universe gates */}
        <div className="rounded-card border border-border bg-surface-1 p-3.5">
          <div className="mb-2.5 flex items-center gap-1.5 text-caption text-ink-muted">
            <SlidersHorizontal size={13} aria-hidden />
            Frozen config (read-only)
          </div>
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
            <div className="rounded-chip border border-border-subtle bg-surface-2 px-2.5 py-2">
              <div className="text-caption text-ink-muted">Cost model</div>
              <div className="font-mono-num text-body font-semibold text-ink-primary">{SETTINGS.costsVersion}</div>
              <div className="mt-1 text-caption text-ink-tertiary">
                brk {SETTINGS.costAssumptionsBps.brokerage_gst_rt_bps} · STT {SETTINGS.costAssumptionsBps.stt_rt_bps} · exch
                {SETTINGS.costAssumptionsBps.exchange_sebi_stamp_rt_bps} · impact cap/side{" "}
                {SETTINGS.costAssumptionsBps.impact_cap_bps_side} · coef {SETTINGS.costAssumptionsBps.impact_coef_bps} ·
                gap {SETTINGS.costAssumptionsBps.gap_slippage_bps} (bps)
              </div>
            </div>
            <div className="rounded-chip border border-border-subtle bg-surface-2 px-2.5 py-2">
              <div className="text-caption text-ink-muted">Outcome labels</div>
              <div className="font-mono-num text-body font-semibold text-ink-primary">{SETTINGS.outcomeLabelsVersion}</div>
              <div className="mt-1 text-caption text-ink-tertiary">research schema {SETTINGS.researchSchemaVersion}</div>
            </div>
            <div className="rounded-chip border border-border-subtle bg-surface-2 px-2.5 py-2">
              <div className="text-caption text-ink-muted">Universe gates</div>
              <div className="font-mono-num text-body font-semibold text-ink-primary">
                ₹{SETTINGS.minPriceRs} · ₹{SETTINGS.minAvgTurnoverCr}cr
              </div>
              <div className="mt-1 text-caption text-ink-tertiary">
                {SETTINGS.excludeEtf ? "probable-ETF excluded" : "ETFs not excluded"} · mcap skipped-surfaced
              </div>
            </div>
            <div className="rounded-chip border border-border-subtle bg-surface-2 px-2.5 py-2">
              <div className="text-caption text-ink-muted">Detector trust</div>
              <div className="font-mono-num text-body font-semibold text-ink-primary">{SETTINGS.detectorTrustVersion}</div>
              <div className="mt-1 text-caption text-ink-tertiary">
                {SETTINGS.detectors.filter((d) => d.trust && !d.trust.rankable).length} of{" "}
                {SETTINGS.detectors.length} detectors not rankable
              </div>
            </div>
          </div>
        </div>

        {/* Real detector trust table — the audit's per-detector warnings */}
        <div className="rounded-card border border-border bg-surface-1 p-3.5">
          <div className="mb-2.5 flex items-center gap-1.5 text-caption text-ink-muted">
            <ShieldCheck size={13} aria-hidden />
            Detector trust — audit {SETTINGS.detectorTrustVersion}
          </div>
          <div className="flex flex-col gap-1.5">
            {SETTINGS.detectors.map((d) => {
              const t = d.trust;
              const tone = !t || !t.rankable ? "danger" : t.status === "REVIEW_REQUIRED" ? "warning" : "positive";
              const label = !t ? "Unknown" : t.status === "VERIFIED" ? "Rankable" : t.status === "REVIEW_REQUIRED" ? "Review" : "Blocked";
              return (
                <div key={d.name} className="flex items-center gap-3 rounded-chip px-2 py-1.5 text-caption">
                  <span className="w-44 shrink-0 font-semibold text-ink-primary">{d.title}</span>
                  <Chip tone={tone}>{label}</Chip>
                  <span className="flex-1 truncate text-ink-tertiary">{t ? t.reason.replace(/_/g, " ") : "no audit record"}</span>
                </div>
              );
            })}
          </div>
        </div>

        <div className="rounded-card border border-border-subtle bg-surface-1 p-3.5">
          <div className="mb-2.5 flex items-center gap-1.5 text-caption text-ink-muted">
            <SlidersHorizontal size={13} aria-hidden />
            Weights &amp; gates
          </div>
          <p className="text-caption text-ink-tertiary">
            Detector thresholds and entry-quality weights are caller-supplied config (R14), not literals — but
            there's no config-editing UI here yet. Editing them today means changing the values passed into
            <code className="mx-1 rounded-[4px] bg-surface-2 px-1 py-0.5 font-mono-num text-caption">unidesk/momentum</code>
            call sites directly. A settings UI over the parameter register is queued behind RESEARCH.
          </p>
        </div>
      </div>
    </AppShell>
  );
}
