import React, { useEffect, useMemo, useState } from "react";
import { fetchMarket, getPipelineStatus } from "./api.js";
import MarketTab from "./MarketTab.jsx";
import { LawRow, ModelsSayPanel, RegimeStrip } from "./DeskTab.jsx";
import { useDensity } from "./DensityContext.jsx";
import { stripCitationCodes } from "./utils.js";

function round(n, digits = 2) {
  if (n === null || n === undefined || Number.isNaN(Number(n))) return "-";
  const f = Math.pow(10, digits);
  return Math.round(Number(n) * f) / f;
}

function pct(n) {
  if (n === null || n === undefined) return "-";
  return `${Number(n) >= 0 ? "+" : ""}${round(n, 1)}%`;
}

function cleanText(text) {
  return stripCitationCodes(text || "").clean || text || "";
}

const STANCE_LABEL = {
  STAND_ASIDE: "STAND ASIDE",
  SIT_OUT: "SIT OUT",
  CAUTION: "CAUTION",
  ACT_PER_PLAN: "ACT PER PLAN",
};

function parseScannedTotal(card) {
  const pool = card?.debate?.pool_summary || card?.pool_summary || card?.scan_metrics?.pool_summary;
  if (pool?.scanned_total !== undefined) return pool.scanned_total;
  const scanStage = (card?.pipeline || []).find((p) => p.stage === "scan_candidates");
  const detailMatch = String(scanStage?.detail || "").match(/candidates=(\d+)/);
  if (detailMatch) return Number(detailMatch[1]);
  return scanStage?.rows_affected ?? (card?.shortlist || []).length;
}

function poolSummary(card) {
  const pool = card?.debate?.pool_summary || card?.pool_summary;
  const chair = card?.chair || [];
  return {
    actionable: pool?.actionable ?? chair.filter((c) => c.verdict === "TAKE").length,
    shortlisted: pool?.shortlisted ?? (card?.shortlist || []).length,
    scanned: pool?.scanned_total ?? parseScannedTotal(card),
  };
}

function regimeLine(card) {
  const regime = card?.regime || {};
  const governor = card?.governor || {};
  const mode = governor.market_mode || regime.mode || "UNKNOWN";
  const phase = regime.four_phase || "phase not computed";
  const mbi = regime.mbi_day_color ? `MBI ${String(regime.mbi_day_color).toLowerCase()}` : "MBI not computed";
  return `${mode} market · ${phase} · ${mbi}`;
}

function lawWhy(card) {
  const regime = card?.regime || {};
  const governor = card?.governor || {};
  const pieces = [];
  if (regime.four_phase) pieces.push(regime.four_phase);
  if (regime.mbi_day_color) pieces.push(`MBI ${String(regime.mbi_day_color).toLowerCase()}`);
  if ((governor.allowed_families || []).length) pieces.push(`${governor.allowed_families.join(" / ")} lead`);
  return pieces.length ? pieces.join(" · ") : "breadth and setup-family gates drive tonight's law";
}

function choppyBrakeLine(card) {
  const brake = card?.regime?.choppy_brake;
  if (brake?.active) return `Choppy brake ON - ${brake.reason || "no new entries"}`;
  return "Choppy brake OFF";
}

function PipelineProgress() {
  const [status, setStatus] = useState(null);

  useEffect(() => {
    let cancelled = false;
    getPipelineStatus()
      .then((body) => {
        if (!cancelled) setStatus(body);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  const hasV4Fields =
    status &&
    status.running &&
    status.stage_index !== undefined &&
    status.total_stages !== undefined &&
    status.total_stages > 0;
  if (!hasV4Fields) return null;

  const pctDone = Math.max(0, Math.min(100, (status.stage_index / status.total_stages) * 100));
  const eta = status.eta_seconds ? `~${Math.ceil(status.eta_seconds / 60)} min left` : "ETA pending";

  return (
    <section className="panel market-live-pipeline">
      <div className="market-panel-head">
        <p className="panel-title small-caps">Live pipeline</p>
        <span className="mono">[B]</span>
      </div>
      <p className="market-pipeline-line mono">
        Building tonight's desk ... stage {status.stage_index}/{status.total_stages}{" "}
        {status.current_stage || status.stage || ""}
      </p>
      <div className="market-progress-track" aria-label="pipeline progress">
        <span className="market-progress-fill" style={{ width: `${pctDone}%` }} />
      </div>
      <p className="caption-b">
        {eta}
        {status.data_live_hint ? ` · data live ${status.data_live_hint}` : ""}
      </p>
    </section>
  );
}

function EveningStepper({ card, onNavigate }) {
  const summary = poolSummary(card);
  const urgent = (card?.coach || []).length || 0;
  const steps = [
    { n: 1, label: "Read the law", done: true },
    { n: 2, label: `Manage open${urgent ? ` (${urgent} needs action!)` : ""}`, tab: "POSITIONS" },
    { n: 3, label: `Run tonight's scanners (${summary.scanned} hits)`, tab: "SCANNERS" },
    { n: 4, label: "Review shortlist", tab: "SHORTLIST" },
    { n: 5, label: "Size & arm the takes", note: "TRADE PLAN" },
    { n: 6, label: "Done - orders placed, stops live" },
  ];
  const current = urgent ? 2 : summary.actionable > 0 ? 5 : 3;

  return (
    <section className="panel market-stepper-panel">
      <div className="market-panel-head">
        <p className="panel-title small-caps">What to do now</p>
        <span className="mono">[B]</span>
      </div>
      <div className="market-stepper">
        {steps.map((step) => (
          <button
            type="button"
            key={step.n}
            className={"market-step" + (step.n === current ? " active" : "")}
            onClick={() => step.tab && onNavigate(step.tab)}
            disabled={!step.tab}
          >
            <span className="market-step-num mono">{step.n}</span>
            <span>{step.label}</span>
            {step.done && <span className="market-step-check">✓</span>}
            {step.tab && <span className="market-step-arrow">→</span>}
          </button>
        ))}
      </div>
      <div className="market-current-step">
        <p className="mono">Current step: {steps.find((s) => s.n === current)?.label}</p>
        <button type="button" className="link-btn" onClick={() => onNavigate(steps.find((s) => s.n === current)?.tab || "DEBATE")}>
          continue →
        </button>
      </div>
    </section>
  );
}

function marketContextSummary(data) {
  if (!data?.available) return "Market context unavailable.";
  const byNorm = new Map((data.indices || []).map((r) => [String(r.symbol || "").toUpperCase().replace(/[^A-Z0-9]/g, ""), r]));
  const nifty = byNorm.get("NIFTY50");
  const midsml = byNorm.get("NIFTYMIDSML400");
  const sectors = [...(data.sectors || [])]
    .filter((s) => s.move_pct !== null && s.move_pct !== undefined)
    .sort((a, b) => b.move_pct - a.move_pct)
    .slice(0, 2)
    .map((s) => s.name || s.symbol);
  const rotation = sectors.length ? `Leading: ${sectors.join(", ")}` : "Leading sectors not available";
  return `NIFTY ${pct(nifty?.returns?.["1d"])} · MIDSML ${pct(midsml?.returns?.["1d"])} · VIX ${data.vix?.value ?? "-"} (${data.vix?.band || "n/a"}) · ${rotation}`;
}

function MarketEvidence({ date }) {
  const { isExpert } = useDensity();
  const [data, setData] = useState(null);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    let cancelled = false;
    fetchMarket(date, false)
      .then((body) => {
        if (!cancelled) setData(body);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [date]);

  return (
    <section className="panel market-evidence-panel">
      <div className="market-panel-head">
        <p className="panel-title small-caps">Market evidence</p>
        <span className="mono">[B] summary {isExpert ? "/ [E] full" : ""}</span>
      </div>
      <p className="market-context-line">{marketContextSummary(data)}</p>
      {isExpert && (
        <>
          <button type="button" className="disclosure-toggle" onClick={() => setOpen((v) => !v)}>
            {open ? "▾" : "▸"} four-phase evidence · MBI bands · sector treemap · movers · dense tables
          </button>
          {open && (
            <div className="market-evidence-full">
              <MarketTab date={date} />
            </div>
          )}
        </>
      )}
    </section>
  );
}

function ExpertBlocks({ card }) {
  const { isExpert } = useDensity();
  if (!isExpert) return null;
  return (
    <section className="market-expert-grid">
      <ModelsSayPanel modelsSay={card?.models_say} volForecast={card?.regime?.vol_forecast} />
      <RegimeStrip regime={card?.regime} scanDate={card?.scan_date} />
      <div className="panel">
        <p className="panel-title small-caps">Activity log</p>
        <p className="caption-b">[E] Full nightly activity remains on the legacy desk feed; V4-T1 keeps the hook here without adding backend reads.</p>
      </div>
    </section>
  );
}

export default function MarketHomeTab({ date, card, loading, error, onNavigate }) {
  const summary = useMemo(() => poolSummary(card), [card]);

  if (loading) return <div className="empty-state">Loading...</div>;
  if (error) {
    return (
      <div className="empty-state">
        <div className="empty-state-icon">⚠</div>
        <p className="empty-state-line">Could not load the market home.</p>
        <p className="empty-state-sub">{error}</p>
      </div>
    );
  }
  if (!card || !card.available) {
    return (
      <div className="empty-state">
        <div className="empty-state-icon">○</div>
        <p className="empty-state-line">No run for {date} yet.</p>
        <p className="empty-state-sub">The desk runs after market close.</p>
      </div>
    );
  }

  const call = card.tonights_call || {};
  const stance = STANCE_LABEL[call.stance] || call.stance || "NO CALL";

  return (
    <div className="market-home">
      <section className="panel market-verdict-hero">
        <div className="market-panel-head">
          <p className="panel-title small-caps">The verdict</p>
          <span className="mono">[B]</span>
        </div>
        <h1>
          <span>{stance}</span>
          {cleanText(call.headline) ? ` - ${cleanText(call.headline)}` : ""}
        </h1>
        <p className="market-regime-line">● {regimeLine(card)}</p>
        <p className="market-funnel-line mono">
          Tonight: {summary.actionable} actionable · {summary.shortlisted} shortlisted · {summary.scanned} scanned
          <button type="button" className="link-btn" onClick={() => onNavigate("SCANNERS")}>→ SCANNERS</button>
          <button type="button" className="link-btn" onClick={() => onNavigate("SHORTLIST")}>→ SHORTLIST</button>
        </p>
      </section>

      <section className="market-law-home">
        <LawRow governor={card.governor} heat={card.heat} />
        <p className="market-law-why">Why: {lawWhy(card)}</p>
        <p className={"market-choppy-line" + (card.regime?.choppy_brake?.active ? " active" : "")}>
          {choppyBrakeLine(card)}
        </p>
      </section>

      <PipelineProgress />
      <EveningStepper card={card} onNavigate={onNavigate} />
      <MarketEvidence date={date} />
      <ExpertBlocks card={card} />
    </div>
  );
}
