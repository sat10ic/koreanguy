import { useEffect, useState } from "react";
import { getSetups, getSetupsRefusals, getSetupsNearMisses } from "../api.js";
import DataStamp from "./DataStamp.jsx";
import { PosterCanvas } from "./poster/Primitives.jsx";
import { CandidateCard, EmptySetups, NearMisses, RefusalFunnel } from "./shared/SetupsFunnelCard.jsx";

export default function FocusPage({ posture, onSymbolSelect }) {
  const mode = posture || "UNKNOWN";
  const noTrade = mode === "NO_TRADE";
  const [state, setState] = useState({ loading: true, error: null, data: null });
  const [refusals, setRefusals] = useState({ loading: true, error: null, data: null });
  const [nearMisses, setNearMisses] = useState({ loading: true, error: null, data: null });

  useEffect(() => {
    let cancelled = false;
    setState({ loading: true, error: null, data: null });
    getSetups()
      .then((data) => !cancelled && setState({ loading: false, error: null, data }))
      .catch((error) => !cancelled && setState({ loading: false, error: error.message, data: null }));
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    setRefusals({ loading: true, error: null, data: null });
    getSetupsRefusals({ limit: 50 })
      .then((data) => !cancelled && setRefusals({ loading: false, error: null, data }))
      .catch((error) => !cancelled && setRefusals({ loading: false, error: error.message, data: null }));
    return () => {
      cancelled = true;
    };
  }, []);

  // W2.2: near-miss lane on Focus too (spec: SetupsPage + FocusPage). Expert
  // only — the proximity map is a diagnostic, not a beginner decision aid.
  useEffect(() => {
    let cancelled = false;
    setNearMisses({ loading: true, error: null, data: null });
    getSetupsNearMisses({ limit: 12 })
      .then((data) => !cancelled && setNearMisses({ loading: false, error: null, data }))
      .catch((error) => !cancelled && setNearMisses({ loading: false, error: error.message, data: null }));
    return () => {
      cancelled = true;
    };
  }, []);

  const candidates = state.data?.focus_candidates || [];
  const cap = Number(state.data?.governor?.max_cards ?? state.data?.max_cards ?? candidates.length);
  const visibleCandidates = candidates.slice(0, Number.isFinite(cap) && cap > 0 ? cap : candidates.length);

  return (
    <PosterCanvas data-testid="focus-page" className="space-y-4">
      <RefusalFunnel setups={state.data} refusals={refusals.data} />

      {state.loading ? (
        <div className="border border-hairline bg-card px-4 py-8 font-mono text-[11px] text-ink3">loading focus candidates...</div>
      ) : state.error ? (
        <div className="border border-bear-border bg-bear-bg px-4 py-6 font-mono text-[11px] text-bear">{state.error}</div>
      ) : noTrade || !state.data?.available || visibleCandidates.length === 0 ? (
        <EmptySetups mode={mode} label="0 focus candidates tonight" />
      ) : (
        <div className="space-y-3">
          {visibleCandidates.map((candidate, idx) => (
            <CandidateCard
              key={`${candidate.symbol}-${candidate.setup_type || candidate.setup}`}
              candidate={candidate}
              scanDate={state.data.as_of}
              onSymbolSelect={onSymbolSelect}
              fallbackRank={idx + 1}
              fallbackRankOf={visibleCandidates.length}
              showFocusFields
            />
          ))}
        </div>
      )}

      {/* W2.2: near-miss lane with gate proximity map (expert diagnostic). */}
      <NearMisses nearMisses={nearMisses.data?.near_misses || []} loading={nearMisses.loading} />

      <DataStamp />
    </PosterCanvas>
  );
}
