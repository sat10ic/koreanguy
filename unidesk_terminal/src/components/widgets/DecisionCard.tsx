import type { Candidate } from "../../data/fixtures";
import { useMode } from "../../lib/ModeContext";
import { chopBandDisplay, stopRoomDisplay, stopRoomNullReason, triggerDistPct } from "../../lib/candidates";
import { sectorFor, SECTOR_SOURCE_LABEL } from "../../lib/sectors";
import { verdictFor } from "../../lib/verdict";
import { Chip } from "../ui/Chip";
import { ScaleMeter } from "../ui/ScaleMeter";
import { QualityStack } from "./QualityStack";

/*
  Stock decision panel (spec §17.6/§17.7) + ContextRibbon (§7.8/§17.3).

  Beginner = verdict + WHY in words + the three entry questions.
  Pro = same verdict + every raw metric (§0.5: Pro never shows less).
  Score→word bands are a documented display mapping (75/60/45), not a new
  formula. The unqualified word "Regime" never appears (§17.8).
*/

// documented display bands for 0-100 scores (mirrors scoreTone thresholds
// plus a Good tier — presentation only, no scoring change)
function band(score: number | null | undefined): string {
  if (score == null) return "—";
  if (score >= 75) return "Excellent";
  if (score >= 60) return "Good";
  if (score >= 45) return "Fair";
  return "Poor";
}

export function ContextRibbon({ candidate, marketRegimeNote }: {
  candidate: Candidate;
  marketRegimeNote?: string;
}) {
  const market = (marketRegimeNote ?? "").split(/[ (—]/)[0] || "—";
  const sector = sectorFor(candidate.symbol);
  return (
    <div className="flex flex-wrap items-center gap-x-5 gap-y-1 rounded-card border border-subtle bg-surface-1 px-4 py-2 text-caption">
      <span className="text-ink-muted">MARKET <span className="ml-1 font-semibold text-ink-primary">{market}</span></span>
      <span className="text-ink-muted">
        SECTOR
        {sector ? (
          <span className="ml-1 font-semibold text-ink-primary" title={`${SECTOR_SOURCE_LABEL} · ${sector.industry}`}>
            {sector.sector}
          </span>
        ) : (
          <span className="ml-1 text-ink-tertiary" title="Symbol not in the vendor sector mapping">—</span>
        )}
      </span>
      <span className="text-ink-muted">
        THIS STOCK <span className="ml-1 font-semibold text-ink-primary">{(candidate.trend ?? "").replace(/_/g, " ").toLowerCase() || "—"}</span>
      </span>
    </div>
  );
}

export function DecisionCard({ candidate: c, marketRegimeNote }: {
  candidate: Candidate;
  marketRegimeNote?: string;
}) {
  const { mode } = useMode();
  const isPro = mode === "pro";
  const verdict = verdictFor(c);
  const dist = triggerDistPct(c);
  const market = (marketRegimeNote ?? "").split(/[ (—]/)[0] || "—";
  const distRead = dist == null ? "—"
    : dist < 0 ? `${Math.abs(dist).toFixed(1)}% past trigger`
    : `${dist.toFixed(1)}% below`;
  const rrRead = c.rr == null ? "—" : c.rr >= 2 ? "Good" : c.rr >= 1 ? "Fair" : "Poor";
  const distState = dist == null ? "—" : dist < 0 ? "Past trigger" : dist <= 2 ? "At breakout" : dist <= 8 ? "Close" : "Far";

  return (
    <div className="flex flex-col gap-4 rounded-card border border-subtle bg-surface-1 p-5">
      {/* VERDICT (§17.6) — above all scores */}
      <div>
        <div className="flex items-baseline justify-between">
          <span className="text-caption font-medium uppercase tracking-widest text-ink-tertiary">Verdict</span>
          <Chip tone={verdict.tone}>{verdict.key.replace("_", " ")}</Chip>
        </div>
        <p className="mt-1.5 text-body font-medium text-ink-primary">{verdict.headline}</p>
      </div>

      <div className="rule-under pb-3">
        <div className="mb-2 text-caption font-medium uppercase tracking-widest text-ink-tertiary">Why</div>
        <dl className="grid grid-cols-[130px_1fr] gap-y-1.5">
          <dt className="text-t3 text-ink-secondary">Stock quality</dt>
          <dd className="text-right text-t3 font-semibold" style={{ color: bandColor(c.stockStrength) }}>{band(c.stockStrength)}</dd>
          <dt className="text-t3 text-ink-secondary">Setup quality</dt>
          <dd className="text-right text-t3 font-semibold" style={{ color: bandColor(c.setupQuality) }}>{band(c.setupQuality)}</dd>
          <dt className="text-t3 text-ink-secondary">Entry timing</dt>
          <dd className="text-right text-t3 font-semibold" style={{ color: bandColor(c.entryTiming) }}>{band(c.entryTiming)}</dd>
        </dl>
        <dl className="mt-3 grid grid-cols-[150px_1fr] gap-y-1.5 border-t border-subtle pt-3">
          <dt className="text-t3 text-ink-secondary">{isPro ? "Room to trigger" : "Distance to breakout"}</dt>
          <dd className="text-right font-mono-num text-t3 text-ink-primary">{distRead}<span className="ml-1.5 font-sans text-ink-tertiary">({distState})</span></dd>
          <dt className="text-t3 text-ink-secondary">{isPro ? "Risk:Reward" : "Reward vs risk"}</dt>
          <dd className={"text-right font-mono-num text-t3 " + (c.rr != null && c.rr < 1 ? "font-semibold text-danger" : "text-ink-primary")}>
            {c.rr != null ? `${c.rr.toFixed(1)}R` : "—"}<span className="ml-1.5 font-sans text-ink-tertiary">({rrRead})</span>
          </dd>
          <dt className="text-t3 text-ink-secondary">{isPro ? "Compression" : "Price tightening"}</dt>
          <dd className="text-right font-mono-num text-t3 text-ink-primary">
            {c.contraction != null ? c.contraction.toFixed(2) : "—"}
          </dd>
        </dl>
      </div>

      {/* scores: null-safe (H2-05); Pro adds coverage + unknowns */}
      <QualityStack
        stock={c.stockStrength ?? null}
        setup={c.setupQuality ?? null}
        entry={c.entryTiming ?? null}
        size="full"
        coverage={{
          stock: c.stockQuality?.coverage,
          setup: c.setupQualitySnapshot?.coverage,
          entry: c.entryQualitySnapshot?.coverage,
        }}
        unknowns={{
          stock: c.stockQuality?.unknowns,
          setup: c.setupQualitySnapshot?.unknowns,
          entry: c.entryQualitySnapshot?.unknowns,
        }}
      />

      {/* CONTEXT (§17.8): two named levels, never a bare "Regime:" */}
      <div className="grid grid-cols-2 gap-2 border-t border-subtle pt-3 text-caption">
        <div>
          <span className="block text-ink-muted">{isPro ? "Broad Market Regime" : "Broader market"}</span>
          <span className="font-semibold text-ink-primary">{market}</span>
        </div>
        <div>
          <span className="block text-ink-muted">{isPro ? "Stock Trend Regime" : "This stock"}</span>
          <span className="font-semibold text-ink-primary">{(c.trend ?? "").replace(/_/g, " ").toLowerCase() || "—"}</span>
        </div>
      </div>

      {/* PRO: raw metrics (§17.7) — superset of Beginner */}
      {isPro && (
        <div className="border-t border-subtle pt-3">
          <div className="mb-2 text-caption font-medium uppercase tracking-widest text-ink-tertiary">Raw metrics</div>
          <RawGroup title="Levels" rows={[
            ["Trigger", c.trigger != null ? `₹${c.trigger.toFixed(2)}` : "—"],
            ["Current", `₹${c.close.toFixed(2)}`],
            ["Invalidation", c.invalidation != null ? `₹${c.invalidation.toFixed(2)}` : "—"],
          ]} />
          <RawGroup title="Setup evidence" rows={[
            ["RS rank", c.rsRank != null ? c.rsRank.toFixed(1) : "—"],
            ["RVOL", c.rvol != null ? `${c.rvol.toFixed(2)}x` : "—"],
            ["ADR%", c.adrPct != null ? c.adrPct.toFixed(2) + "%" : "—"],
            ["Delivery", c.deliveryRatio != null ? (c.deliveryRatio * 100).toFixed(0) + "%" : "—"],
            ["Sessions", c.sessions != null ? String(c.sessions) : "—"],
          ]} />
          {/* B-5: the simplified meters sit above the raw thrust rows — the
              word layer and the number layer of the same report fields. */}
          <div className="mb-3">
            <div className="mb-1 text-[10px] font-medium uppercase tracking-wider text-ink-muted">Thrust, in plain terms</div>
            <div className="flex flex-col gap-1.5">
              {(() => {
                const d = chopBandDisplay(c.chopBand);
                return d ? (
                  <ScaleMeter density="panel" label="Cleanliness" segments={d.segments} word={d.word} tone={d.tone}
                    isPro={isPro} proValue={c.chopScore != null ? `${c.chopScore.toFixed(1)} chop` : undefined}
                    tooltip={`ChopScore ${c.chopScore != null ? c.chopScore.toFixed(1) : "—"}/100, higher = choppy. Band mirrored from the report's chop_band (features/thrust.py: ${c.chopBand}).`} />
                ) : (
                  <ScaleMeter density="panel" label="Cleanliness" segments={1} word="—" tone="neutral"
                    tooltip="chop band not computed for this candidate" nullReason="not computed" />
                );
              })()}
              {(() => {
                const d = stopRoomDisplay(c.stopThrustDays);
                return d ? (
                  <ScaleMeter density="panel" label="Stop room" segments={d.segments} word={d.word} tone={d.tone}
                    isPro={isPro} proValue={c.stopThrustDays != null ? `${c.stopThrustDays.toFixed(2)}d` : undefined}
                    tooltip={`Stop sits ${c.stopThrustDays?.toFixed(2)} thrust-days away. Bands: ≥1.5 roomy · 1.0–1.5 OK · 0.75–1.0 tight · <0.75 inside noise. Source: report stop_thrust_days (features/thrust.py).`} />
                ) : (
                  <ScaleMeter density="panel" label="Stop room" segments={1} word="—" tone="neutral"
                    tooltip={`Stop room — ${stopRoomNullReason(c)}`} nullReason={stopRoomNullReason(c)} />
                );
              })()}
            </div>
          </div>
          <RawGroup title="Thrust / price action" rows={[
            ["ADRMAX", c.adrMaxPct != null ? c.adrMaxPct.toFixed(2) + "%" : "— (<250 sessions)"],
            ["Chop score", c.chopScore != null ? `${c.chopScore.toFixed(1)} (${c.chopBand ?? "—"})` : "—"],
            ["Stop in thrust-days", c.stopThrustDays != null ? c.stopThrustDays.toFixed(2) : "—"],
          ]} footnote="ADRMAX / ChopScore: clean-room from the authors' public descriptions (features/thrust.py); stop_thrust_days = invalidation distance expressed in ADRMAX units." />
          <RawGroup title="Participation" rows={[
            ["Reactor Scale", c.activityScore ? c.activityScore.activity_score.toFixed(1) : "—"],
            ["q-ratio", c.activityScore ? c.activityScore.q_ratio.toFixed(1) + "x" : "—"],
            ["d-ratio", c.activityScore ? c.activityScore.d_ratio.toFixed(1) + "x" : "—"],
          ]} footnote="Reactor Scale — must never be presented as institutional identity, trade direction, or a risk input." />
          <RawGroup title="Data quality" rows={[
            ["Stock cov", c.stockQuality ? (c.stockQuality.coverage * 100).toFixed(0) + "%" : "—"],
            ["Setup cov", c.setupQualitySnapshot ? (c.setupQualitySnapshot.coverage * 100).toFixed(0) + "%" : "—"],
            ["Entry cov", c.entryQualitySnapshot ? (c.entryQualitySnapshot.coverage * 100).toFixed(0) + "%" : "—"],
            ["Unknowns", c.stockQuality && c.stockQuality.unknowns.length > 0 ? c.stockQuality.unknowns.join(", ") : "—"],
          ]} />
        </div>
      )}
    </div>
  );
}

function bandColor(score: number | null | undefined): string {
  if (score == null) return "var(--text-muted)";
  if (score >= 75) return "var(--positive)";
  if (score >= 60) return "var(--positive)";
  if (score >= 45) return "var(--info)";
  return "var(--danger)";
}

function RawGroup({ title, rows, footnote }: { title: string; rows: [string, string][]; footnote?: string }) {
  return (
    <div className="mb-3">
      <div className="mb-1 text-[10px] font-medium uppercase tracking-wider text-ink-muted">{title}</div>
      <dl className="grid grid-cols-[110px_1fr] gap-y-1">
        {rows.map(([k, v]) => (
          <div key={k} className="contents">
            <dt className="text-t3 text-ink-secondary">{k}</dt>
            <dd className="text-right font-mono-num text-t3 text-ink-primary">{v}</dd>
          </div>
        ))}
      </dl>
      {footnote && <p className="mt-1 text-[10px] text-ink-muted">{footnote}</p>}
    </div>
  );
}
