import { useEffect, useState } from "react";
import { getPortfolioHeat, getRegimeSummary, getSetups } from "../api.js";
import BreadthGrid from "./BreadthGrid.jsx";
import ParticipationPanel from "./ParticipationPanel.jsx";
import ShowDetails from "./ShowDetails.jsx";
import TopIndicesPanel from "./TopIndicesPanel.jsx";

export default function RegimeSummary({ onPosture }) {
  const [state, setState] = useState({ loading: true, error: null, data: null });
  const [setups, setSetups] = useState({ loading: true, error: null, rows: [], governor: null });
  const [heat, setHeat] = useState({ loading: true, error: null, data: null });

  useEffect(() => {
    let cancelled = false;
    setState({ loading: true, error: null, data: null });
    getRegimeSummary()
      .then((data) => !cancelled && setState({ loading: false, error: null, data }))
      .catch((error) => !cancelled && setState({ loading: false, error: error.message, data: null }));
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    getSetups({ limit: 5 })
      .then((data) => {
        if (cancelled) return;
        setSetups({
          loading: false,
          error: null,
          rows: data?.available ? (data.candidates || []).slice(0, 5) : [],
          governor: data?.governor || null,
        });
      })
      .catch((error) => !cancelled && setSetups({ loading: false, error: error.message, rows: [], governor: null }));
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    getPortfolioHeat()
      .then((data) => !cancelled && setHeat({ loading: false, error: null, data }))
      .catch((error) => !cancelled && setHeat({ loading: false, error: error.message, data: null }));
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!onPosture) return;
    if (!state.data?.available) return onPosture(null);
    return onPosture(state.data.data_stale ? "STALE" : state.data.market_mode);
  }, [state.data, onPosture]);

  if (state.loading) return <RegimeSkeleton />;
  if (state.error) {
    return (
      <EmptyBlock title="Couldn't reach the API">
        Make sure the backend is running: <code>python -m manas_os.api</code>
      </EmptyBlock>
    );
  }
  if (!state.data?.available) {
    return (
      <EmptyBlock title="No regime data yet">
        Run the pipeline to populate: <code>python manas.py run-eod --date YYYY-MM-DD</code>
      </EmptyBlock>
    );
  }

  return (
    <main data-testid="regime-summary" className="mb-6 space-y-3 font-body">
      <GovernorPanel data={state.data} governor={setups.governor || {}} heat={heat} />
      <TopSetupsStrip data={state.data} setups={setups} />
      <ShowDetails label="[E] Show the numbers" testid="regime-numbers">
        <NumbersAccordion />
      </ShowDetails>
    </main>
  );
}

function GovernorPanel({ data, governor, heat }) {
  const stale = Boolean(data.data_stale);
  const mode = stale ? "STALE" : data.market_mode || "UNKNOWN";
  const allowed = governor.allowed_families || governor.allowed_setups || data.preferred_setups || [];
  const riskBase = governor.risk_band?.base_pct ?? governor.risk_band?.base ?? governor.risk_base_pct ?? data.allowed_risk_min_pct;
  const riskMax = governor.risk_band?.hard_max_pct ?? governor.risk_band?.hard_max ?? governor.risk_hard_max_pct ?? data.allowed_risk_max_pct;
  const pushes = governor.push_allowed ?? governor.pushes_enabled ?? governor.pushes_on ?? mode !== "NO_TRADE";
  const heatData = heat.data || {};
  const openRisk = heatData.open_risk_pct ?? data.open_risk_pct;
  const openRiskCap = heatData.cap_pct ?? governor.open_risk_cap_pct ?? data.open_risk_cap_pct;
  const why = data.read || data.explanation_text || data.command || data.technical_detail || "Use the governor law before choosing risk.";

  return (
    <section className="border border-hairline bg-card p-4" aria-label="GOVERNOR PANEL">
      <div className="font-display text-[28px] uppercase leading-none text-ink">
        {postureVerdict(mode)}
      </div>
      <div className="mt-3 grid gap-2 md:grid-cols-5">
        <LawTile label="MAX CARDS" value={governor.max_cards ?? data.max_cards ?? "-"} />
        <LawTile label="RISK/TRADE" value={riskBase == null && riskMax == null ? "-" : `${fmtPct(riskBase)}-${fmtPct(riskMax)}`} />
        <AllowedTile allowed={allowed} />
        <LawTile
          label="OPEN-RISK CAP"
          value={openRiskCap == null ? (openRisk == null ? "-" : `${fmtPct(openRisk)} used`) : `${fmtPct(openRiskCap)} (${openRisk == null ? "-" : fmtPct(openRisk)} used)`}
          sub={heat.error || null}
        />
        <LawTile label="PUSHES" value={pushes ? "ON" : "OFF"} />
      </div>
      <div className="mt-3 border-t border-hairline pt-3 font-sans text-[13px] leading-snug text-ink2">
        <span className="font-mono text-[10px] font-bold uppercase tracking-overline text-ink3">WHY (plain): </span>
        {why}
      </div>
    </section>
  );
}

function AllowedTile({ allowed }) {
  const items = allowed.length ? allowed : ["none"];
  return (
    <div className="border border-hairline bg-raised p-3">
      <div className="mb-1 font-mono text-[9px] uppercase tracking-overline text-ink3">ALLOWED SETUPS</div>
      <div className="flex flex-wrap gap-1">
        {items.map((family) => (
          <span key={family} className="rounded-chip border border-hairline bg-card px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-overline text-ink2">
            {family}
          </span>
        ))}
      </div>
    </div>
  );
}

function LawTile({ label, value, sub = null }) {
  return (
    <div className="border border-hairline bg-raised p-3">
      <div className="font-mono text-[9px] uppercase tracking-overline text-ink3">{label}</div>
      <div className="mt-1 font-mono text-[18px] font-bold tabular-nums text-ink">{value}</div>
      {sub && <div className="mt-1 font-mono text-[9px] uppercase tracking-overline text-bear">{sub}</div>}
    </div>
  );
}

function TopSetupsStrip({ data, setups }) {
  const cap = setups.governor?.max_cards ?? data.max_cards ?? setups.rows.length;
  const reviewed = setups.rows.filter((setup) => setup.decision || setup.reviewed || setup.status === "reviewed").length;
  const reviewedText = `${reviewed} of ${cap || setups.rows.length} reviewed`;

  return (
    <section data-testid="home-setups-panel" className="border border-hairline bg-card p-3" aria-label="TOP SETUPS STRIP">
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <div className="font-mono text-[11px] font-bold uppercase tracking-overline text-ink">TOP SETUPS STRIP</div>
        <button
          type="button"
          onClick={() => document.querySelector('[data-testid="nav-setups"]')?.click()}
          className="border border-hairline px-2 py-1 font-mono text-[10px] uppercase tracking-overline text-ink2 hover:border-ink hover:text-ink"
        >
          go to Setups
        </button>
      </div>
      {setups.loading ? (
        <div className="font-mono text-[11px] text-ink3">loading top setups...</div>
      ) : setups.error ? (
        <div className="font-mono text-[11px] text-bear">{setups.error}</div>
      ) : setups.rows.length === 0 ? (
        <div className="font-mono text-[11px] uppercase tracking-overline text-ink3">no setup candidates passed the quality gate</div>
      ) : (
        <div className="flex flex-wrap items-center gap-2">
          {setups.rows.slice(0, 5).map((setup, index) => (
            <div key={`${setup.symbol}-${setup.setup_type || setup.setup || index}`} className="border border-hairline bg-raised px-2 py-2">
              <span className="font-mono text-[12px] font-bold text-ink">{index + 1}. {setup.symbol}</span>
              <span className="ml-2 font-mono text-[10px] uppercase tracking-overline text-ink3">
                {setup.setup_type || setup.setup || "setup"} rank {setup.rank ?? index + 1}/{cap || setups.rows.length}
              </span>
            </div>
          ))}
          <span className="font-mono text-[10px] uppercase tracking-overline text-ink3">-&gt; {reviewedText}</span>
        </div>
      )}
    </section>
  );
}

function NumbersAccordion() {
  return (
    <div className="space-y-3">
      <div className="grid gap-3 lg:grid-cols-2">
        <BreadthGrid />
        <SectorRotationScatter />
      </div>
      <ParticipationPanel />
      <TopIndicesPanel />
    </div>
  );
}

function SectorRotationScatter() {
  return (
    <section className="mt-4 border border-hairline bg-card p-3">
      <div className="mb-2 font-mono text-[12px] font-bold uppercase tracking-overline text-ink">
        Sector rotation scatter
      </div>
      <div className="grid h-44 grid-cols-2 grid-rows-2 border border-hairline bg-raised font-mono text-[10px] uppercase tracking-overline text-ink3">
        <div className="border-b border-r border-hairline p-2">improving</div>
        <div className="border-b border-hairline p-2 text-right text-bull">leading</div>
        <div className="border-r border-hairline p-2">lagging</div>
        <div className="p-2 text-right text-warn">weakening</div>
      </div>
    </section>
  );
}

function RegimeSkeleton() {
  return (
    <div className="mb-6 space-y-3">
      <div className="h-40 animate-pulse rounded bg-hairline2" />
      <div className="h-20 animate-pulse rounded bg-hairline2" />
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

function postureVerdict(mode) {
  if (mode === "RISK_ON") return "RISK-ON - press clean longs";
  if (mode === "SELECTIVE") return "SELECTIVE - trade small and picky";
  if (mode === "DEFENSIVE") return "DEFENSIVE - protect capital";
  if (mode === "NO_TRADE") return "NO-TRADE - sit out";
  if (mode === "STALE") return "STALE - wait for fresh data";
  return "UNKNOWN - wait for the law";
}

function fmtPct(value) {
  if (value == null || Number.isNaN(Number(value))) return "-";
  return `${Number(value).toFixed(2).replace(/\.00$/, "")}%`;
}
