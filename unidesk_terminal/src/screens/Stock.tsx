import { History as HistoryIcon } from "lucide-react";
import { useParams } from "react-router-dom";
import { AppShell } from "../components/shell/AppShell";
import { Chip } from "../components/ui/Chip";
import { ContextRibbon, DecisionCard } from "../components/widgets/DecisionCard";
import { StockChart } from "../components/widgets/StockChart";
import { useMode } from "../lib/ModeContext";
import { useReport } from "../lib/useReport";
import { mapCandidates } from "../lib/candidates";
import { offLowReading, lateEntryWarning } from "../lib/veto";
import { getRealHistory } from "../data/stockHistory";
import { outcomesForSymbol } from "../data/outcomeHistory";
import type { Candidate } from "../data/fixtures";
import type { RawBaseEpisode } from "../data/tonight";

/*
  STOCK DETAIL (UI_BUILD_SPEC_V1 PART 8 + P-02/P-05). Reading order:
  header (verdict inside the decision card), chart (real bars only — a
  synthetic chart is never rendered as tradable-looking, S-06), base
  structure (P-02), setup evidence (S-08), past signals (S-09/S-10).
  D-08's late-entry warning fires above the fold when the percentile is
  in the owner's audited worst zone.
*/

export function Stock() {
  const { symbol } = useParams<{ symbol: string }>();
  const { mode } = useMode();
  const isPro = mode === "pro";
  const report = useReport();
  const candidate = mapCandidates(report).find((c) => c.symbol === symbol?.toUpperCase());
  const hf = report.honesty_footer;

  if (!candidate) {
    return (
      <AppShell breadcrumb={["Stock"]}>
        <div className="flex h-full flex-col items-center justify-center gap-2 text-center">
          <h1 className="text-h3 font-semibold text-ink-primary">No symbol selected</h1>
          <p className="max-w-sm text-caption text-ink-tertiary">
            Open a candidate from Tonight or Candidates to see its deep-dive workspace.
          </p>
        </div>
      </AppShell>
    );
  }

  const episode = (report.base_episodes ?? []).find((e) => e.symbol === candidate.symbol);
  const history = getRealHistory(candidate.symbol, report.session_date);
  const priorCalls = outcomesForSymbol(candidate.symbol);
  const offLow = offLowReading(candidate.symbol, candidate.close, report.session_date);

  return (
    <AppShell breadcrumb={["Stock", candidate.symbol]}>
      <div className="flex flex-col gap-4 p-4">
        {/* D-08: late-entry warning — the owner's own audited zone */}
        {offLow?.late && (
          <div className="rounded-card border border-warning bg-warning-bg px-3.5 py-2.5 text-caption font-medium text-warning">
            {lateEntryWarning(offLow)}
            <span className="ml-2 font-normal text-ink-tertiary">
              (bars through {offLow.throughDate}; zone: &gt;{offLow.pctOffLow > 80 ? 80 : offLow.pctOffLow.toFixed(0)}% off the low)
            </span>
          </div>
        )}

        {/* Header */}
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-card border border-border bg-surface-1 px-4 py-3">
          <div className="flex items-baseline gap-3">
            <h1 className="text-h2 font-semibold text-ink-primary">{candidate.symbol}</h1>
            <span className="font-mono-num text-h4 text-ink-primary">₹{candidate.close.toFixed(2)}</span>
            <span className="text-caption text-ink-tertiary">{candidate.sessions ?? "—"} sessions of history used</span>
          </div>
          <div className="flex items-center gap-2">
            <Chip tone="accent">{titleCase(candidate.setupType)}</Chip>
            <Chip tone="neutral">Advisory</Chip>
          </div>
        </div>

        <ContextRibbon candidate={candidate} marketRegimeNote={hf.regime_note} />

        <div className="grid grid-cols-[1fr_360px] gap-4">
          <div className="flex flex-col gap-4">
            {/* S-06: chart only from real bars; otherwise the levels table
                plus an unmissable banner — never a tradable-looking demo */}
            <div className="rounded-card border border-border bg-surface-1 p-3">
              {history ? (
                <>
                  <div className="mb-2 flex items-center justify-between gap-2">
                    <h2 className="text-h4 font-semibold text-ink-primary">Price chart</h2>
                    <span className="text-caption text-ink-muted">
                      Real NSE bhavcopy · {history.length} daily sessions through {history[history.length - 1].time}
                    </span>
                  </div>
                  <div className="h-[360px]">
                    <StockChart
                      symbol={candidate.symbol}
                      price={candidate.close}
                      history={history}
                      triggerPrice={candidate.trigger ?? undefined}
                      invalidationPrice={candidate.invalidation ?? undefined}
                    />
                  </div>
                </>
              ) : (
                <>
                  <div className="mb-2 flex items-center gap-2 rounded-chip border-2 border-danger bg-danger-bg px-3 py-2 text-caption font-bold tracking-wide text-danger">
                    ⚠ DEMO CHART · SYNTHETIC DATA · DO NOT TRADE — no real bars for {candidate.symbol} in this snapshot, so no chart is drawn.
                  </div>
                  <LevelsTable c={candidate} isPro={isPro} />
                </>
              )}
            </div>

            {/* S-03: levels visual (target omitted — no field backs it) */}
            <LevelsRow c={candidate} isPro={isPro} />

            {/* P-02: base structure — every number traces to the episode */}
            {episode && <BaseStructurePanel episode={episode} isPro={isPro} />}
          </div>

          <DecisionCard candidate={candidate} marketRegimeNote={hf.regime_note} />
        </div>

        {/* S-08: setup evidence in both modes */}
        <div className="rounded-card border border-border bg-surface-1 px-3.5 py-3">
          <div className="mb-2.5 flex items-baseline justify-between">
            <h2 className="text-h4 font-semibold text-ink-primary">Setup evidence</h2>
            <span className="text-caption text-ink-muted">why it qualified</span>
          </div>
          <SetupEvidence c={candidate} isPro={isPro} />
        </div>

        {/* S-09/S-10: past signals as one line; Replay only when replayable */}
        <div className="rounded-card border border-border bg-surface-1 px-4 py-3">
          <div className="mb-2 flex items-center gap-2 text-caption text-ink-tertiary">
            <HistoryIcon size={14} aria-hidden />
            <span>Past signals for {candidate.symbol}</span>
          </div>
          {priorCalls.length === 0 ? (
            <p className="text-caption text-ink-muted">None recorded.</p>
          ) : (
            <div className="flex flex-col gap-1.5">
              {priorCalls.slice(0, 12).map((c) => (
                <div key={c.date} className="flex items-center gap-3 text-caption">
                  <span className="font-mono-num text-ink-muted">{c.date}</span>
                  <span className="text-ink-secondary">{c.note}</span>
                </div>
              ))}
            </div>
          )}
          {history && (
            <button
              className="mt-3 rounded-chip border border-border-subtle px-2.5 py-1.5 text-caption text-ink-muted"
              title="Point-in-time replay is not wired yet (needs the U-P0.5 recorder)"
            >
              Replay — not wired yet
            </button>
          )}
        </div>
      </div>
    </AppShell>
  );
}

function titleCase(s: string): string {
  return s.replace(/_/g, " ").replace(/\b\w/g, (m) => m.toUpperCase());
}

function LevelsTable({ c, isPro }: { c: Candidate; isPro: boolean }) {
  return (
    <dl className="grid grid-cols-[1fr_auto] gap-y-1.5 px-1 py-2">
      <dt className="text-caption text-ink-secondary">{isPro ? "Invalidation" : "Setup fails below"}</dt>
      <dd className="text-right font-mono-num text-body text-danger">{c.invalidation != null ? `₹${c.invalidation.toFixed(2)}` : "—"}</dd>
      <dt className="text-caption text-ink-secondary">Close</dt>
      <dd className="text-right font-mono-num text-body text-ink-primary">₹{c.close.toFixed(2)}</dd>
      <dt className="text-caption text-ink-secondary">{isPro ? "Trigger" : "Breakout above"}</dt>
      <dd className="text-right font-mono-num text-body text-ink-primary">{c.trigger != null ? `₹${c.trigger.toFixed(2)}` : "—"}</dd>
    </dl>
  );
}

// S-03: STOP | CURRENT | TRIGGER on one rail; no TARGET — no field backs it.
function LevelsRow({ c, isPro }: { c: Candidate; isPro: boolean }) {
  const vals = [c.invalidation, c.close, c.trigger].filter((v): v is number => v != null);
  if (vals.length < 2) {
    return (
      <div className="rounded-card border border-border bg-surface-1 px-3.5 py-3 text-caption text-ink-tertiary">
        Levels unavailable — no trigger/invalidation geometry recorded for this candidate.
      </div>
    );
  }
  const lo = Math.min(...vals), hi = Math.max(...vals);
  const pos = (v: number) => (hi === lo ? 50 : ((v - lo) / (hi - lo)) * 100);
  return (
    <div className="rounded-card border border-border bg-surface-1 px-3.5 py-3">
      <h2 className="mb-2.5 text-h4 font-semibold text-ink-primary">Levels</h2>
      <div className="relative h-1.5 rounded-full bg-surface-2">
        {[c.invalidation, c.trigger].filter((v): v is number => v != null).map((v) => (
          <span key={v} className="absolute top-1/2 h-3 w-0.5 -translate-y-1/2 bg-accent" style={{ left: pos(v) + "%" }} />
        ))}
        <span className="absolute top-1/2 h-3 w-3 -translate-y-1/2 rounded-full bg-ink-primary" style={{ left: `calc(${pos(c.close)}% - 6px)` }} />
      </div>
      <div className="mt-2 flex justify-between text-caption">
        <span className="text-danger">
          {isPro ? "STOP" : "Setup fails below"}
          <span className="ml-1.5 font-mono-num">{c.invalidation != null ? c.invalidation.toFixed(2) : "—"}</span>
        </span>
        <span className="text-ink-secondary">
          {isPro ? "CURRENT" : "Now"}
          <span className="ml-1.5 font-mono-num">{c.close.toFixed(2)}</span>
        </span>
        <span className="text-positive">
          {isPro ? "TRIGGER" : "Breakout above"}
          <span className="ml-1.5 font-mono-num">{c.trigger != null ? c.trigger.toFixed(2) : "—"}</span>
        </span>
      </div>
    </div>
  );
}

// P-02: base geometry — only episode fields, nothing recomputed.
function BaseStructurePanel({ episode, isPro }: { episode: RawBaseEpisode; isPro: boolean }) {
  return (
    <div className="rounded-card border border-border bg-surface-1 px-3.5 py-3">
      <div className="mb-2.5 flex items-baseline justify-between">
        <h2 className="text-h4 font-semibold text-ink-primary">Base structure</h2>
        <span className="text-caption text-ink-tertiary">{episode.verdict.replace(/_/g, " ")} · {episode.method_version}</span>
      </div>
      <dl className="grid grid-cols-[150px_1fr] gap-y-1.5 text-caption">
        <dt className="text-ink-muted">Window</dt>
        <dd className="font-mono-num text-ink-primary">{episode.base_start} → {episode.base_end} ({episode.base_sessions} sessions{episode.base_weeks != null ? `, ${episode.base_weeks.toFixed(1)} wk` : ""})</dd>
        {episode.depth_pct != null && (
          <>
            <dt className="text-ink-muted">Depth</dt>
            <dd className="font-mono-num text-ink-primary">{episode.depth_pct.toFixed(2)}%</dd>
          </>
        )}
        {episode.pullback_depths && episode.pullback_depths.length > 0 && (
          <>
            <dt className="text-ink-muted">Contractions</dt>
            <dd className="font-mono-num text-ink-primary">
              {episode.pullback_depths.length}
              {"  "}({episode.pullback_depths.map((d) => d.toFixed(1) + "%").join(" → ")})
            </dd>
          </>
        )}
        {episode.pivot != null && (
          <>
            <dt className="text-ink-muted">{isPro ? "Pivot" : "Breakout level"}</dt>
            <dd className="font-mono-num text-ink-primary">₹{episode.pivot.toFixed(2)}</dd>
          </>
        )}
        {episode.atrp_percentile != null && (
          <>
            <dt className="text-ink-muted">ATR percentile</dt>
            <dd className="font-mono-num text-ink-primary">{episode.atrp_percentile.toFixed(0)}</dd>
          </>
        )}
      </dl>
      {episode.annotations.length > 0 && (
        <div className="mt-2 border-t border-border-subtle pt-2">
          <div className="mb-1 text-caption text-ink-muted">Structure markers — shown with confirmation time (P-05)</div>
          {episode.annotations.map((a, i) => (
            <div key={i} className="text-caption text-ink-tertiary">
              {a.kind.replace(/_/g, " ")} · occurred {a.occurred_at.slice(0, 10)} · confirmed {a.known_at.slice(0, 10)}
              {a.known_at.slice(0, 10) > a.occurred_at.slice(0, 10) && (
                <span className="ml-1 text-warning">(confirmed later — not knowable on the day)</span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// S-08: real checks; Beginner interprets, Pro quantifies.
function SetupEvidence({ c, isPro }: { c: Candidate; isPro: boolean }) {
  const checks = [
    {
      pass: c.trend === "STRONG_UPTREND" || c.trend === "UPTREND",
      beginner: "Strong trend",
      pro: `Trend ${c.trend ?? "—"}`,
    },
    {
      pass: (c.rsRank ?? 0) >= 90,
      beginner: c.rsRank != null ? `Top ${Math.max(1, Math.round(100 - c.rsRank))}% of market` : "RS unavailable",
      pro: `RS ${(c.rsRank ?? 0).toFixed(1)}`,
    },
    {
      pass: (c.rvol ?? 0) >= 1.5,
      beginner: (c.rvol ?? 0) >= 3 ? "Exceptional volume" : (c.rvol ?? 0) >= 1.5 ? "High volume" : "Quiet volume",
      pro: `RVOL ${c.rvol != null ? c.rvol.toFixed(2) + "x" : "—"}`,
    },
    {
      pass: (c.contraction ?? 99) <= 1.0,
      beginner: "Range tightening",
      pro: `Compression ${c.contraction != null ? c.contraction.toFixed(2) : "—"}`,
    },
    {
      pass: (c.deliveryRatio ?? 0) >= 0.5,
      beginner: "Delivery participation",
      pro: `Delivery ${c.deliveryRatio != null ? (c.deliveryRatio * 100).toFixed(0) + "%" : "—"}`,
    },
  ];
  return (
    <div className="flex flex-col gap-1.5">
      {checks.map((k) => (
        <div key={k.pro} className="flex items-center gap-2.5 text-caption">
          <span className={k.pass ? "text-positive" : "text-ink-muted"}>{k.pass ? "✓" : "·"}</span>
          <span className="text-ink-primary">{isPro ? k.pro : k.beginner}</span>
        </div>
      ))}
    </div>
  );
}
