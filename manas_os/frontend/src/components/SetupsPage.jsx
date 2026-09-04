import { useEffect, useState } from "react";
import { getAdvisorToday, getSetups, getSetupsNearMisses, getSetupsRefusals } from "../api.js";
import { useDensity } from "../DensityContext.jsx";
import DataStamp from "./DataStamp.jsx";
import { PosterCanvas } from "./poster/Primitives.jsx";
import { CandidateCard, EmptySetups, NearMisses, RefusalFunnel } from "./shared/SetupsFunnelCard.jsx";

export default function SetupsPage({ posture, onSymbolSelect }) {
  const mode = posture || "UNKNOWN";
  const noTrade = mode === "NO_TRADE";
  const [state, setState] = useState({ loading: true, error: null, data: null });
  const [refusals, setRefusals] = useState({ loading: true, error: null, data: null });
  const [nearMisses, setNearMisses] = useState({ loading: true, error: null, data: null });
  const [advisor, setAdvisor] = useState({ loading: true, error: null, notes: [] });
  const { density } = useDensity();
  const expert = density === "expert";

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
    getAdvisorToday()
      .then((data) => !cancelled && setAdvisor({ loading: false, error: null, notes: data?.available ? data.notes || [] : [] }))
      .catch((error) => !cancelled && setAdvisor({ loading: false, error: error.message, notes: [] }));
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    setRefusals({ loading: true, error: null, data: null });
    setNearMisses({ loading: true, error: null, data: null });
    getSetupsRefusals({ limit: 50 })
      .then((data) => !cancelled && setRefusals({ loading: false, error: null, data }))
      .catch((error) => !cancelled && setRefusals({ loading: false, error: error.message, data: null }));
    getSetupsNearMisses({ limit: 12 })
      .then((data) => !cancelled && setNearMisses({ loading: false, error: null, data }))
      .catch((error) => !cancelled && setNearMisses({ loading: false, error: error.message, data: null }));
    return () => {
      cancelled = true;
    };
  }, []);

  const candidates = state.data?.candidates || [];
  const cap = Number(state.data?.governor?.max_cards ?? state.data?.max_cards ?? candidates.length);
  const visibleCandidates = candidates.slice(0, Number.isFinite(cap) && cap > 0 ? cap : candidates.length);

  return (
    <PosterCanvas data-testid="setups-page" className="space-y-4">
      <RefusalFunnel setups={state.data} refusals={refusals.data} />

      {state.loading ? (
        <div className="border border-hairline bg-card px-4 py-8 font-mono text-[11px] text-ink3">loading setups...</div>
      ) : state.error ? (
        <div className="border border-bear-border bg-bear-bg px-4 py-6 font-mono text-[11px] text-bear">{state.error}</div>
      ) : noTrade || !state.data?.available || visibleCandidates.length === 0 ? (
        <EmptySetups mode={mode} />
      ) : (
        <div className="space-y-3">
          {visibleCandidates.map((candidate, idx) => (
            <CandidateCard
              key={`${candidate.symbol}-${candidate.setup_type || candidate.setup}`}
              candidate={candidate}
              scanDate={state.data.as_of}
              onSymbolSelect={onSymbolSelect}
              advisorNotes={advisor.notes}
              fallbackRank={idx + 1}
              fallbackRankOf={visibleCandidates.length}
            />
          ))}
        </div>
      )}

      {expert && (
        <NearMisses
          nearMisses={nearMisses.data?.near_misses || []}
          loading={nearMisses.loading}
          onRefresh={() => {
            getSetupsNearMisses({ limit: 12 })
              .then((data) => setNearMisses({ loading: false, error: null, data }))
              .catch((error) => setNearMisses({ loading: false, error: error.message, data: null }));
          }}
        />
      )}
      <DataStamp />
    </PosterCanvas>
  );
}
