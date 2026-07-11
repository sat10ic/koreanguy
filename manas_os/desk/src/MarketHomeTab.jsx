import React, { useEffect, useState } from "react";
import { fetchMarket, getPipelineStatus, fetchDebate, fetchScannerPresets } from "./api.js";
import MarketTab from "./MarketTab.jsx";
import { LawRow, ModelsSayPanel, RegimeStrip } from "./DeskTab.jsx";
import { useDensity } from "./DensityContext.jsx";
import { stripCitationCodes } from "./utils.js";
import { Term } from "./Glossary.jsx";

// F5: strip backend jargon out of the BEGINNER verdict headline only --
// "passed the gate" phrasing and "(n=29)"-style base-rate counts stay
// available verbatim in expert/dense mode (the raw card.tonights_call
// headline, rendered unchanged there), but a beginner reading only the hero
// shouldn't hit either. This is a display-only strip; it never rewrites the
// backend payload.
function beginnerSafeHeadline(text) {
  if (!text) return text;
  return text
    .replace(/\bpassed the gate\b/gi, "cleared tonight's checklist")
    .replace(/\s*\(n=\d+\)/gi, "")
    .replace(/\s{2,}/g, " ")
    .trim();
}

// F5: one plain, jargon-free why-clause for the actionable===0 sit-out
// case, keyed off the stance the backend already computed (run_card.py
// _tonights_call) -- paraphrased in plain language, no base-rate numbers,
// no "gate" vocabulary.
function plainSitOutWhy(call) {
  const stance = call && call.stance;
  if (stance === "STAND_ASIDE") return "The market regime says cash is the safer position tonight.";
  if (stance === "CAUTION") return "The few setups that qualified have a weak track record so far.";
  return "No name tonight cleared the bar with real conviction.";
}

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

// F1: honest hero counts. pool_summary is fetched live from
// /api/desk/debate ({actionable, watchlist, pool_total}) -- watchlist is
// relabeled "shortlisted" here to match the wireframe's copy. "screener
// hits" is a SEPARATE number: the sum of today's LIVE preset hit counts
// from /api/scanners/presets, which is the true SCANNER universe total
// (not the post-gate pool_total). CRITICAL: no hardcoded fallback -- any
// field whose fetch failed or is unavailable renders "-" (em dash), never
// a fake number like "1".
function usePoolSummary(date) {
  const [pool, setPool] = useState(null); // {actionable, shortlisted, pool_total} | null
  const [screenerHits, setScreenerHits] = useState(null); // number | null

  useEffect(() => {
    let cancelled = false;
    setPool(null);
    fetchDebate(date)
      .then((body) => {
        if (cancelled) return;
        const ps = body?.pool_summary;
        if (ps && typeof ps.actionable === "number") {
          setPool({
            actionable: ps.actionable,
            shortlisted: ps.watchlist,
            poolTotal: ps.pool_total,
          });
        }
      })
      .catch(() => {
        if (!cancelled) setPool(null);
      });
    return () => {
      cancelled = true;
    };
  }, [date]);

  useEffect(() => {
    let cancelled = false;
    setScreenerHits(null);
    fetchScannerPresets(date)
      .then((body) => {
        if (cancelled || !body?.available) return;
        const presets = body.presets || [];
        const total = presets
          .filter((p) => p.status === "LIVE" && typeof p.hits === "number")
          .reduce((sum, p) => sum + p.hits, 0);
        setScreenerHits(total);
      })
      .catch(() => {
        if (!cancelled) setScreenerHits(null);
      });
    return () => {
      cancelled = true;
    };
  }, [date]);

  return {
    actionable: pool?.actionable ?? null,
    shortlisted: pool?.shortlisted ?? null,
    poolTotal: pool?.poolTotal ?? null,
    screenerHits,
  };
}

function fmtCount(n) {
  return n === null || n === undefined ? "—" : n;
}

// N3: the phase name and "MBI" are raw TradeTM jargon with no gloss in
// beginner mode -- wrap both with the existing glossary Term so a beginner
// gets a hover/tap explanation instead of an unglossed acronym string.
function RegimeLine({ card }) {
  const regime = card?.regime || {};
  const governor = card?.governor || {};
  const mode = governor.market_mode || regime.mode || "UNKNOWN";
  const phase = regime.four_phase;
  const mbiColor = regime.mbi_day_color;
  return (
    <>
      {mode} market ·{" "}
      {phase ? (
        <Term k="four-phase" as="span">{phase}</Term>
      ) : (
        "phase not computed"
      )}{" "}
      ·{" "}
      {mbiColor ? (
        <>
          <Term k="mbi-day-color" as="span">MBI</Term> {String(mbiColor).toLowerCase()}
        </>
      ) : (
        "MBI not computed"
      )}
    </>
  );
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

function EveningStepper({ card, summary, onNavigate }) {
  const urgent = (card?.coach || []).length || 0;
  const hitsLabel = summary.screenerHits === null ? "—" : summary.screenerHits;
  const steps = [
    { n: 1, label: "Read the law", done: true },
    { n: 2, label: `Manage open${urgent ? ` (${urgent} needs action!)` : ""}`, tab: "POSITIONS" },
    { n: 3, label: `Run tonight's scanners (${hitsLabel} hits)`, tab: "SCANNERS" },
    { n: 4, label: "Review shortlist", tab: "SHORTLIST" },
    { n: 5, label: "Size & arm the takes", note: "TRADE PLAN" },
    { n: 6, label: "Done - orders placed, stops live" },
  ];
  const current = urgent ? 2 : (summary.actionable || 0) > 0 ? 5 : 3;
  const prevCurrentRef = React.useRef(current);
  const [pulseStep, setPulseStep] = useState(null);

  // F5: one-shot pulse on the stepper's current-step indicator when it
  // advances -- respects prefers-reduced-motion (handled in CSS via the
  // shared @keyframes step-pulse, same 150-250ms ease-out idiom used
  // elsewhere in App.css). Never re-fires just from a re-render.
  useEffect(() => {
    if (prevCurrentRef.current !== current) {
      prevCurrentRef.current = current;
      setPulseStep(current);
      const t = setTimeout(() => setPulseStep(null), 260);
      return () => clearTimeout(t);
    }
  }, [current]);

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
            className={"market-step" + (step.n === current ? " active" : "") + (step.n === pulseStep ? " market-step-pulse" : "")}
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
            {open ? "▾" : "▸"} four-phase evidence · <Term k="mbi-day-color" as="span">MBI</Term> bands · sector treemap · movers · dense tables
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

// F5: proportional funnel bars scanned -> pool -> shortlisted -> actionable,
// reusing the FunnelPanel visual idiom (DebateTab.jsx funnel-stages) rather
// than inventing a new bar component. Renders "—" stages honestly when a
// count hasn't loaded, never fabricates a width.
function MarketFunnelBars({ summary }) {
  const stages = [
    { key: "scanned", label: "screener hits", value: summary.screenerHits },
    { key: "pool", label: "in tonight's pool", value: summary.poolTotal },
    { key: "shortlisted", label: "shortlisted", value: summary.shortlisted },
    { key: "actionable", label: "actionable", value: summary.actionable },
  ];
  const max = Math.max(1, ...stages.map((s) => (typeof s.value === "number" ? s.value : 0)));
  return (
    <div className="market-funnel-bars">
      {stages.map((s) => {
        const pctWidth = typeof s.value === "number" ? Math.max(2, (s.value / max) * 100) : 0;
        return (
          <div className="market-funnel-bar-row" key={s.key}>
            <span className="market-funnel-bar-label mono">{s.label}</span>
            <div className="market-funnel-bar-track">
              <div className="market-funnel-bar-fill" style={{ width: `${pctWidth}%` }} />
            </div>
            <span className="market-funnel-bar-value mono">{fmtCount(s.value)}</span>
          </div>
        );
      })}
    </div>
  );
}

export default function MarketHomeTab({ date, card, loading, error, onNavigate }) {
  const summary = usePoolSummary(date);
  const { isExpert } = useDensity();

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
  // F5: beginner headline must cohere with the DEBATE outcome -- when
  // nothing is actionable, lead with the fixed sit-out sentence + one plain
  // why-clause instead of the backend's raw (jargon-bearing) headline.
  // Expert/dense mode always sees the backend headline verbatim.
  const zeroActionable = summary.actionable === 0;
  const beginnerHeadline =
    zeroActionable
      ? `Sit out — nothing to take live tonight. ${plainSitOutWhy(call)}`
      : beginnerSafeHeadline(cleanText(call.headline));

  return (
    <div className="market-home">
      <section className="panel market-verdict-hero">
        <div className="market-panel-head">
          <p className="panel-title small-caps">The verdict</p>
          <span className="mono">[B]</span>
        </div>
        <h1>
          {isExpert ? (
            <>
              <span>{stance}</span>
              {cleanText(call.headline) ? ` - ${cleanText(call.headline)}` : ""}
            </>
          ) : (
            <span>{beginnerHeadline}</span>
          )}
        </h1>
        <p className="market-regime-line">● <RegimeLine card={card} /></p>
        <p className="market-funnel-line mono">
          Tonight: {fmtCount(summary.actionable)} actionable · {fmtCount(summary.shortlisted)} shortlisted ·{" "}
          {fmtCount(summary.poolTotal)} in tonight's pool
          <button type="button" className="link-btn" onClick={() => onNavigate("SCANNERS")}>→ SCANNERS</button>
          <button type="button" className="link-btn" onClick={() => onNavigate("SHORTLIST")}>→ SHORTLIST</button>
        </p>
        <MarketFunnelBars summary={summary} />
      </section>

      <section className="market-law-home">
        <LawRow governor={card.governor} heat={card.heat} />
        <p className="market-law-why">Why: {lawWhy(card)}</p>
        <p className={"market-choppy-line" + (card.regime?.choppy_brake?.active ? " active" : "")}>
          {choppyBrakeLine(card)}
        </p>
      </section>

      <PipelineProgress />
      <EveningStepper card={card} summary={summary} onNavigate={onNavigate} />
      <MarketEvidence date={date} />
      <ExpertBlocks card={card} />
    </div>
  );
}
