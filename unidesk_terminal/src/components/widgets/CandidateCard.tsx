import { Link } from "react-router-dom";
import type { Candidate } from "../../data/fixtures";
import { useMode } from "../../lib/ModeContext";
import { deriveState, STATE_META } from "../../lib/status";
import { chopBandDisplay, stopRoomDisplay, stopRoomNullReason, triggerDistPct } from "../../lib/candidates";
import { getRealHistory } from "../../data/stockHistory";
import { Chip } from "../ui/Chip";
import { MiniCandles } from "../ui/MiniCandles";
import { ScaleMeter } from "../ui/ScaleMeter";

/*
  Candidate row (spec §10.4): RANK | TICKER+PRICE | MINI CHART (real bars) |
  RS | RVOL | PIVOT DIST | ADR | STATE — one grammar under every setup
  section. Pro appends raw geometry/quality/base-stage; Beginner gets
  interpreted labels (§8). Chart cell renders "—" when no real bars (§7.5).
*/

// H2-07 caveat — required verbatim wherever the Reactor Scale is shown.
const REACTOR_CAVEAT =
  "must never be presented as institutional identity, trade direction, or a risk input";

interface CandidateCardProps {
  candidate: Candidate;
  rank?: number; // undefined → non-rankable detector (P-04): row renders unranked
  sessionDate?: string;
}

export function CandidateCard({ candidate: c, rank, sessionDate }: CandidateCardProps) {
  const { mode } = useMode();
  const isPro = mode === "pro";
  const state = deriveState(c);
  const sm = STATE_META[state];
  const distPct = triggerDistPct(c);
  const sq = c.stockQuality;
  const score = c.stockStrength;
  const lowRR = c.rr != null && c.rr < 1.0;
  const bars = sessionDate ? getRealHistory(c.symbol, sessionDate) : undefined;
  const candleBars = bars?.slice(-40);

  return (
    <Link
      to={`/stock/${c.symbol}`}
      className="flex items-center gap-3 px-3 py-2 border-b border-subtle last:border-b-0 hover:bg-surface-3 transition-colors duration-150"
    >
      <span className="w-7 shrink-0 text-right font-mono-num text-t2 text-ink-muted">
        {rank != null ? String(rank).padStart(2, "0") : "·"}
      </span>

      <span className="w-40 shrink-0 truncate text-t3 font-semibold text-ink-primary">
        {c.symbol}
        <span className="ml-1.5 font-mono-num font-normal text-ink-secondary">₹{c.close?.toFixed(2)}</span>
      </span>

      <span className="w-[104px] shrink-0" title={candleBars ? `Last ${candleBars.length} real sessions` : "no real bars in snapshot"}>
        {candleBars && candleBars.length > 4
          ? <MiniCandles bars={candleBars} trigger={c.trigger ?? null} />
          : <span className="font-mono-num text-caption text-ink-muted">—</span>}
      </span>

      <span className="w-32 shrink-0 text-t3">
        {isPro ? (
          <span className="font-mono-num text-ink-secondary">
            RS {c.rsRank?.toFixed(0) ?? "—"} <span className="text-ink-muted">·</span> RV {c.rvol != null ? c.rvol.toFixed(1) + "x" : "—"}
          </span>
        ) : (
          <span className="text-ink-secondary">
            {c.rsRank != null ? `Top ${Math.max(1, Math.round(100 - c.rsRank))}%` : "— RS"}
            {c.rvol != null && (c.rvol >= 3 ? " · high volume" : c.rvol >= 1 ? " · normal volume" : " · quiet volume")}
          </span>
        )}
      </span>

      <span className="w-16 shrink-0 text-right font-mono-num text-t3 text-ink-secondary"
        title="Distance to trigger (negative = price above trigger)">
        {distPct != null ? `${distPct > 0 ? "+" : ""}${distPct.toFixed(1)}%` : "—"}
      </span>

      <span className="w-14 shrink-0 text-right font-mono-num text-t3 text-ink-muted" title="avg daily range - how much the stock typically moves in a day">
        {c.adrPct != null ? `${c.adrPct.toFixed(1)}%` : "—"}
      </span>

      {/* PART B: the owner's thrust meters, in simplified good→bad terms.
          Words/bands are mirrors of the backend's own values (lib/candidates.ts
          cites features/thrust.py) — the UI computes no band itself. Null
          renders "—" + the named reason, never a 0. */}
      <span className="w-[92px] shrink-0">
        {(() => {
          const d = chopBandDisplay(c.chopBand);
          return d ? (
            <ScaleMeter
              segments={d.segments} word={d.word} tone={d.tone} isPro={isPro}
              proValue={c.chopScore != null ? c.chopScore.toFixed(0) : undefined}
              tooltip={`Cleanliness — ChopScore ${c.chopScore != null ? c.chopScore.toFixed(1) : "—"} of 100 (higher = choppy). Band from the report's chop_band (features/thrust.py: ${c.chopBand}).`}
            />
          ) : (
            <ScaleMeter segments={1} word="—" tone="neutral"
              tooltip="Cleanliness — chop band not computed for this candidate"
              nullReason="not computed" />
          );
        })()}
      </span>

      <span className="w-[92px] shrink-0">
        {(() => {
          const d = stopRoomDisplay(c.stopThrustDays);
          return d ? (
            <ScaleMeter
              segments={d.segments} word={d.word} tone={d.tone} isPro={isPro}
              proValue={c.stopThrustDays != null ? `${c.stopThrustDays.toFixed(2)}d` : undefined}
              tooltip={`Stop room — stop sits ${c.stopThrustDays?.toFixed(2)} thrust-days away (stop_thrust_days; ADRMAX ${c.adrMaxPct != null ? c.adrMaxPct.toFixed(1) + "%" : "—"}). Bands: ≥1.5 roomy · 1.0–1.5 OK · 0.75–1.0 tight · <0.75 inside noise.`}
            />
          ) : (
            <ScaleMeter segments={1} word="—" tone="neutral"
              tooltip={`Stop room — ${stopRoomNullReason(c)}`}
              nullReason={stopRoomNullReason(c)} />
          );
        })()}
      </span>

      {isPro && (
        <>
          <span className={"w-14 shrink-0 text-right font-mono-num text-t3 " + (lowRR ? "font-semibold text-danger" : "text-ink-secondary")}
            title={lowRR ? "R:R below 1.0 — risk larger than reward at these levels" : "Reward vs risk"}>
            {c.rr != null ? `${c.rr.toFixed(1)}R${lowRR ? " !" : ""}` : "—"}
          </span>
          {sq && score != null && (
            <span className="shrink-0 font-mono-num text-t3"
              title={`stock quality · coverage ${(sq.coverage * 100).toFixed(0)}%${sq.unknowns.length ? " · unknowns: " + sq.unknowns.join(", ") : ""}`}>
              <span style={{ color: score >= 75 ? "var(--positive)" : score >= 45 ? "var(--info)" : "var(--danger)" }}>
                Q {score.toFixed(0)}
              </span>
              <span className="text-ink-tertiary">@{(sq.coverage * 100).toFixed(0)}%</span>
            </span>
          )}
          {c.activityScore && (
            <span className="shrink-0 font-mono-num text-t2 text-ink-tertiary" title={`Reactor Scale — ${REACTOR_CAVEAT}`}>
              RSch {c.activityScore.activity_score.toFixed(0)}
            </span>
          )}
          <span className="w-20 shrink-0 text-t2 text-ink-tertiary" title="Clean-room base episode verdict">
            {c.baseStage ? c.baseStage.replace(/_/g, " ") : "—"}
          </span>
        </>
      )}

      <span className="ml-auto flex shrink-0 items-center gap-2">
        {c.detectorTrust && !c.detectorTrust.rankable && isPro && (
          <span className="max-w-52 truncate text-[10px] text-warning" title={c.detectorTrust.reason}>
            {c.detectorTrust.status}
          </span>
        )}
        <Chip tone={sm.tone}>{sm.label}</Chip>
      </span>
    </Link>
  );
}
