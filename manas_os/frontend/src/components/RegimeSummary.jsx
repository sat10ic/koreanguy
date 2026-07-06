import { useEffect, useState } from "react";
import { getRegimeSummary, getSetups } from "../api.js";
import { useDensity } from "../DensityContext.jsx";
import PostureCommandBar from "./PostureCommandBar.jsx";
import SetupStickers from "./SetupStickers.jsx";
import RegimeTrend from "./RegimeTrend.jsx";
import DataStamp from "./DataStamp.jsx";
import ParticipationPanel from "./ParticipationPanel.jsx";
import BreadthGrid from "./BreadthGrid.jsx";
import Read from "./Read.jsx";
import SectorsThemesPanel from "./SectorsThemesPanel.jsx";
import TopIndicesPanel from "./TopIndicesPanel.jsx";
import ShowDetails from "./ShowDetails.jsx";

export default function RegimeSummary({ onPosture }) {
  const [state, setState] = useState({ loading: true, error: null, data: null });
  const [setups, setSetups] = useState({ loading: true, error: null, rows: [], asOf: null, governor: null });

  useEffect(() => {
    let cancelled = false;
    setState({ loading: true, error: null, data: null });
    getRegimeSummary()
      .then((d) => !cancelled && setState({ loading: false, error: null, data: d }))
      .catch((e) => !cancelled && setState({ loading: false, error: e.message, data: null }));
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    getSetups({ limit: 5 })
      .then((d) => {
        if (cancelled) return;
        setSetups({
          loading: false,
          error: null,
          rows: d?.available ? (d.candidates || []).slice(0, 5) : [],
          asOf: d?.as_of || null,
          governor: d?.governor || null,
        });
      })
      .catch((e) => !cancelled && setSetups({ loading: false, error: e.message, rows: [], asOf: null, governor: null }));
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!onPosture) return;
    if (!state.data?.available) return onPosture(null);
    onPosture(state.data.data_stale ? "STALE" : state.data.market_mode);
  }, [state.data, onPosture]);

  if (state.loading) return <StripSkeleton />;
  if (state.error) {
    return (
      <EmptyBlock title="Couldn't reach the API">
        Make sure the backend is running: <code>python -m manas_os.api</code>
      </EmptyBlock>
    );
  }
  if (!state.data?.available) {
    return (
      <EmptyBlock title="No regime snapshot yet">
        Run the pipeline to populate: <code>python manas.py run-eod --date YYYY-MM-DD</code>
      </EmptyBlock>
    );
  }

  const d = state.data;
  const stale = Boolean(d.data_stale);
  const governor = setups.governor || {};
  // T3.7b: the density toggle is now real (BEGINNER_EXPERT_SPEC §3.1). Beginner
  // sees the verdict + actionable setups + a collapsed "show the numbers"; the
  // GovernorPanel (diagnostic internals) and the full numbers block are Expert-only.
  // Same data, less of it — never a different verdict.
  const { density } = useDensity();
  const expert = density === "expert";

  const InternalsBlock = (
    <div className="mt-3 space-y-4">
      <ParticipationPanel />
      <BreadthGrid />
      <SectorsThemesPanel />
      <TopIndicesPanel />
      <SetupStickers preferred={d.preferred_setups || []} avoid={d.avoid_setups || []} />
      <RegimeTrend />
      <QuadrantGrid quadrant={d.quadrant || {}} />
      {d.technical_detail && <TechnicalDetail text={d.technical_detail} defaultOpen={expert} />}
    </div>
  );

  return (
    <section data-testid="regime-summary" className="mb-6 space-y-4">
      {expert && <GovernorPanel data={d} governor={governor} stale={stale} />}
      <PostureCommandBar data={d} stale={stale} />
      <HomeSetupsPanel data={d} setups={setups} stale={stale} />

      {expert ? (
        // Expert: render the full internals inline — no expander in the way.
        <div className="border border-hairline bg-card p-3">
          <div className="mb-2 font-mono text-[11px] font-bold uppercase tracking-overline text-ink">
            The numbers
          </div>
          {InternalsBlock}
        </div>
      ) : (
        // Beginner: the same numbers, collapsed behind a single affordance.
        // A curious beginner can peek; it's never forced.
        <ShowDetails label="Show the numbers" testid="regime-numbers">
          {InternalsBlock}
        </ShowDetails>
      )}
      <DataStamp />
    </section>
  );
}

function GovernorPanel({ data, governor, stale }) {
  const mode = stale ? "STALE" : data.market_mode || "UNKNOWN";
  const allowed = governor.allowed_families || governor.allowed_setups || data.preferred_setups || [];
  const riskBase = governor.risk_band?.base ?? governor.risk_base_pct ?? data.allowed_risk_min_pct;
  const riskMax = governor.risk_band?.hard_max ?? governor.risk_hard_max_pct ?? data.allowed_risk_max_pct;
  const pushes = governor.pushes_enabled ?? governor.pushes_on ?? mode !== "NO_TRADE";
  return (
    <section className="border border-hairline bg-card p-3">
      <div className="mb-2 font-mono text-[12px] font-bold uppercase tracking-overline text-ink">
        Governor panel
      </div>
      <div className="mb-3 font-sans text-[13px] text-ink2">
        {mode} - today's law from the setup governor.
      </div>
      <div className="grid gap-2 md:grid-cols-5">
        <LawTile label="Max cards" value={governor.max_cards ?? "-"} />
        <LawTile label="Risk/trade" value={riskBase == null && riskMax == null ? "-" : `${fmtPct(riskBase)}-${fmtPct(riskMax)}`} />
        <div className="border border-hairline bg-raised p-2 md:col-span-2">
          <div className="mb-1 font-mono text-[9px] uppercase tracking-overline text-ink3">Allowed families</div>
          <div className="flex flex-wrap gap-1">
            {(allowed.length ? allowed : ["none"]).map((family) => (
              <span key={family} className="rounded-chip border border-hairline bg-card px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-overline text-ink2">
                {family}
              </span>
            ))}
          </div>
        </div>
        <LawTile label="Pushes" value={pushes ? "ON" : "OFF"} />
      </div>
      <div className="mt-2 font-sans text-[12px] text-ink3">
        Why: {data.read || data.command || data.technical_detail || "Use the posture line and setup strip below."}
      </div>
    </section>
  );
}

function LawTile({ label, value }) {
  return (
    <div className="border border-hairline bg-raised p-2">
      <div className="font-mono text-[9px] uppercase tracking-overline text-ink3">{label}</div>
      <div className="font-mono text-[18px] font-bold tabular-nums text-ink">{value}</div>
    </div>
  );
}

function HomeSetupsPanel({ data, setups, stale }) {
  const swing = data?.quadrant?.swing || {};
  const breadth = data?.breadth_20dma_pct ?? data?.breadth_pct ?? data?.pct_above_20dma;
  const swingState = swing.state || "UNKNOWN";
  const mode = data?.market_mode || "UNKNOWN";
  const goodSwing = ["UP", "BULLISH"].includes(swingState);
  const band = stale || mode === "NO_TRADE" ? "bear" : goodSwing && mode === "RISK_ON" ? "bull" : "warn";
  const chipCls = {
    bull: "border-bull-border bg-bull-bg text-bull",
    warn: "border-warn-border bg-warn-bg text-warn",
    bear: "border-bear-border bg-bear-bg text-bear",
  }[band];
  const verdict = stale ? "WAIT" : band === "bull" ? "SWING FRIENDLY" : band === "warn" ? "PICKY" : "SIT OUT";

  return (
    <section data-testid="home-setups-panel" className="border border-hairline bg-card p-3">
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-mono text-[11px] font-bold uppercase tracking-overline text-ink">
            Breadth / swing state
          </span>
          <span className={"rounded-chip border px-2 py-0.5 font-mono text-[10px] font-bold uppercase tracking-overline " + chipCls}>
            {verdict}
          </span>
          <span className="font-sans text-[12px] text-ink3">
            {breadth == null ? "Breadth unavailable" : `${Number(breadth).toFixed(0)}% above 20-DMA`} - swing {String(swingState).toLowerCase()}.
          </span>
        </div>
        {setups.asOf && <span className="font-mono text-[10px] uppercase tracking-overline text-ink3">setups {setups.asOf}</span>}
      </div>

      {setups.loading ? (
        <div className="font-mono text-[11px] text-ink3">loading top setups...</div>
      ) : setups.error ? (
        <div className="font-mono text-[11px] text-bear">{setups.error}</div>
      ) : setups.rows.length === 0 ? (
        <Read band="muted" verdict="NO SETUPS">No setup candidates passed the quality gate for the latest scan.</Read>
      ) : (
        <div className="flex gap-2 overflow-x-auto pb-1">
          {setups.rows.slice(0, 5).map((s, idx) => (
            <div key={`${s.symbol}-${s.setup}`} className="min-w-[190px] border border-hairline bg-raised px-2 py-2">
              <div className="flex items-center justify-between gap-2">
                <span className="font-mono text-[12px] font-bold text-ink">{idx + 1}. {s.symbol}</span>
                <span className="font-mono text-[10px] uppercase tracking-overline text-ink3">rank {s.rank ?? idx + 1}/{setups.governor?.max_cards ?? setups.rows.length}</span>
              </div>
              <div className="mt-0.5 truncate font-mono text-[9px] uppercase tracking-overline text-ink3">
                {s.grade} - {s.setup}
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

function QuadrantGrid({ quadrant }) {
  return (
    <div data-testid="market-quadrant" className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-4">
      <QuadrantCard title="Momentum" q={quadrant.momentum} />
      <QuadrantCard title="Swing" q={quadrant.swing} />
      <QuadrantCard title="Trend" q={quadrant.trend} />
      <QuadrantCard title="Bias" q={quadrant.bias} />
    </div>
  );
}

const QUAD_BAND = { UP: "bull", BULLISH: "bull", DOWN: "bear", BEARISH: "bear" };

function QuadrantCard({ title, q }) {
  const state = q?.state || null;
  const band = QUAD_BAND[state] || "muted";
  const railCls = { bull: "bg-bull", bear: "bg-bear", muted: "bg-muted" }[band];
  const textCls = { bull: "text-bull", bear: "text-bear", muted: "text-muted" }[band];
  return (
    <div className="relative overflow-hidden border border-hairline bg-card p-3 pl-4">
      <div className={"absolute left-0 top-0 h-full w-[3px] " + railCls} />
      <div className="mb-1 flex items-center justify-between">
        <span className="font-mono text-[12px] font-bold uppercase tracking-overline text-ink">{title}</span>
        <span className={"font-mono text-[11px] font-bold uppercase " + textCls}>{state || "-"}</span>
      </div>
      <Read band={band} verdict={state || "NO DATA"}>{q?.reason || "No data for this quadrant yet."}</Read>
    </div>
  );
}

function TechnicalDetail({ text, defaultOpen = false }) {
  // Axis E: collapsed by default in Beginner, open by default in Expert.
  return (
    <details open={defaultOpen} className="border border-hairline2 bg-raised p-2">
      <summary className="cursor-pointer font-mono text-[9px] uppercase tracking-overline text-ink3">
        technical detail (var=value audit trail)
      </summary>
      <div className="mt-1 font-mono text-[10px] leading-relaxed text-ink3">{text}</div>
    </details>
  );
}

function StripSkeleton() {
  return (
    <div className="mb-6 grid grid-cols-2 gap-2 border border-hairline bg-card p-3 sm:grid-cols-4 lg:grid-cols-6">
      {Array.from({ length: 7 }).map((_, i) => (
        <div key={i} className="flex flex-col gap-1.5">
          <div className="h-2 w-10 animate-pulse rounded bg-hairline2" />
          <div className="h-4 w-16 animate-pulse rounded bg-hairline" />
        </div>
      ))}
    </div>
  );
}

function EmptyBlock({ title, children }) {
  return (
    <div className="mb-6 border border-dashed border-hairline px-4 py-6 text-center">
      <div className="font-mono text-[12px] font-semibold text-ink2">{title}</div>
      <div className="mt-1 font-sans text-[12px] leading-snug text-ink3">{children}</div>
    </div>
  );
}

function fmtPct(value) {
  if (value == null) return "-";
  return `${Number(value).toFixed(2).replace(/\.00$/, "")}%`;
}
