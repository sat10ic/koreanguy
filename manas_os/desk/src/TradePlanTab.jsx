import React, { useEffect, useMemo, useState } from "react";
import { fetchDebate, fetchSignalGuide } from "./api.js";
import { humanizeSourceCite } from "./utils.js";
import { useDensity } from "./DensityContext.jsx";
import { Term } from "./Glossary.jsx";

// V4-T13: TRADE PLAN route -- the per-name "pre-trade checklist + sizing,
// made concrete" screen (WIREFRAMES_V4.md section 5). Opened from a DEBATE
// card's [TRADE PLAN->] link or a SHORTLIST row's "open trade plan" action.
// Consumes /api/desk/signal-guide (steps + risk_checks, deterministic, no
// LLM) and the matching card from /api/desk/debate (plan/sizer/gates), the
// same two endpoints HowToTradeThis already used before being promoted here.

const CAPITAL_KEY = "manas.tradeplan.capital";

// B1(d): one consistent decimal place everywhere in this tab -- default
// digits dropped from 2 to 1 so every unlabeled round() call (rupees,
// stop-distance, R-multiples, risk-check values) renders the same way.
function round(n, digits = 1) {
  if (n === null || n === undefined || Number.isNaN(n)) return "—";
  return Number(n).toFixed(digits);
}

function pct(n, digits = 1) {
  if (n === null || n === undefined || Number.isNaN(n)) return "—";
  return `${Number(n).toFixed(digits)}%`;
}

function readCapital() {
  if (typeof window === "undefined") return 1200000;
  const raw = window.localStorage.getItem(CAPITAL_KEY);
  const n = raw ? Number(raw) : NaN;
  return Number.isFinite(n) && n > 0 ? n : 1200000;
}

// B · R-LADDER RAIL -- a horizontal price line with stop (-1R), entry, and
// target markers, distances labelled in Rs and %. Draws in once on open
// (transition on mount), never re-animates.
function RLadderRail({ entry, stop, target }) {
  const [drawn, setDrawn] = useState(false);
  useEffect(() => {
    const t = setTimeout(() => setDrawn(true), 30);
    return () => clearTimeout(t);
  }, []);

  if (entry === null || entry === undefined || stop === null || stop === undefined) {
    return <p className="mono trade-plan-ladder-missing">R-ladder unavailable — plan has no entry/stop.</p>;
  }
  const risk = entry - stop;
  const hasTarget = target !== null && target !== undefined && risk > 0;
  const lo = Math.min(stop, entry, hasTarget ? target : entry);
  const hi = Math.max(stop, entry, hasTarget ? target : entry);
  const span = hi - lo || 1;
  const xOf = (v) => ((v - lo) / span) * 100;
  const stopX = xOf(stop);
  const entryX = xOf(entry);
  const targetX = hasTarget ? xOf(target) : null;
  const rMultiple = hasTarget ? (target - entry) / risk : null;

  return (
    <div className="r-ladder-rail">
      <div className={"r-ladder-track" + (drawn ? " r-ladder-drawn" : "")}>
        <div className="r-ladder-line" />
        {hasTarget && (
          <div
            className="r-ladder-segment r-ladder-segment-reward"
            style={{ left: `${entryX}%`, width: `${Math.max(targetX - entryX, 0)}%` }}
          />
        )}
        <div
          className="r-ladder-segment r-ladder-segment-risk"
          style={{ left: `${Math.min(stopX, entryX)}%`, width: `${Math.abs(entryX - stopX)}%` }}
        />
        <div className="r-ladder-marker r-ladder-marker-stop" style={{ left: `${stopX}%` }}>
          <span className="r-ladder-dot" />
          <span className="r-ladder-label mono">STOP ₹{round(stop)}</span>
          <span className="r-ladder-sub mono">−<Term k="r-multiple" as="span">1R</Term> · −₹{round(risk)} ({pct((risk / entry) * 100)})</span>
        </div>
        <div className="r-ladder-marker r-ladder-marker-entry" style={{ left: `${entryX}%` }}>
          <span className="r-ladder-dot" />
          <span className="r-ladder-label mono">ENTRY ₹{round(entry)}</span>
        </div>
        {hasTarget && (
          <div className="r-ladder-marker r-ladder-marker-target" style={{ left: `${targetX}%` }}>
            <span className="r-ladder-dot" />
            <span className="r-ladder-label mono">TARGET ₹{round(target)}</span>
            <span className="r-ladder-sub mono">
              +{round(rMultiple)}R · +₹{round(target - entry)} ({pct(((target - entry) / entry) * 100)})
            </span>
          </div>
        )}
      </div>
      {!hasTarget && <p className="mono trade-plan-ladder-missing">no target on this plan — risk side only.</p>}
    </div>
  );
}

// C · risk-check fill bars -- value vs cap, one CSS transition on load, no
// loops. Renders honestly: a check whose numbers aren't in the payload is
// shown as "not available" rather than faked.
function FillBar({ label, value, cap, unit, danger }) {
  const [drawn, setDrawn] = useState(false);
  useEffect(() => {
    const t = setTimeout(() => setDrawn(true), 30);
    return () => clearTimeout(t);
  }, []);
  const has = value !== null && value !== undefined && cap !== null && cap !== undefined && cap > 0;
  const pctFilled = has ? Math.min((value / cap) * 100, 100) : 0;
  const over = has && value > cap;
  return (
    <div className="risk-fill-row">
      <span className="risk-fill-label mono">{label}</span>
      {has ? (
        <>
          <div className="risk-fill-track">
            <div
              className={"risk-fill-bar" + (over || danger ? " risk-fill-bar-over" : "")}
              style={{ width: drawn ? `${pctFilled}%` : "0%" }}
            />
          </div>
          <span className={"risk-fill-value mono" + (over ? " risk-fill-value-over" : "")}>
            {round(value)}{unit} / cap {round(cap)}{unit} {over ? "✗" : "✓"}
          </span>
        </>
      ) : (
        <span className="risk-fill-value mono risk-fill-value-missing">not available in payload</span>
      )}
    </div>
  );
}

function EntryChecklist({ steps, checked, onToggle, isExpert }) {
  if (!steps || steps.length === 0) {
    return <p className="mono">No checklist steps available.</p>;
  }
  return (
    <ol className="how-to-trade-steps trade-plan-checklist">
      {steps.map((step) => (
        <li key={step.n} className={"how-to-trade-step" + (step.n === 0 ? " how-to-trade-step-refusal" : "")}>
          <label className="how-to-trade-step-head">
            <input type="checkbox" checked={!!checked[step.n]} onChange={() => onToggle(step.n)} />
            <span className="how-to-trade-step-title">{step.title}</span>
          </label>
          <p className="how-to-trade-instruction">{step.instruction}</p>
          <p className="how-to-trade-check mono">Check before you proceed: {step.check}</p>
          {isExpert && (
            <p className="how-to-trade-cite mono" title={step.source_cite}>
              source: {humanizeSourceCite(step.source_cite)}
            </p>
          )}
        </li>
      ))}
    </ol>
  );
}

export default function TradePlanTab({ date, symbol, onBackToDebate, card }) {
  const { isExpert } = useDensity();
  const [guide, setGuide] = useState(null);
  const [debateSym, setDebateSym] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [checked, setChecked] = useState({});
  const [capital, setCapital] = useState(readCapital);

  useEffect(() => {
    if (!symbol || !date) return undefined;
    let cancelled = false;
    setLoading(true);
    setError(null);
    setChecked({});
    Promise.all([
      fetchSignalGuide(symbol, date),
      fetchDebate(date).catch(() => null),
    ])
      .then(([guideBody, debateBody]) => {
        if (cancelled) return;
        setGuide(guideBody);
        const sym = debateBody && debateBody.symbols
          ? debateBody.symbols.find((s) => s.symbol === symbol)
          : null;
        setDebateSym(sym || null);
      })
      .catch((err) => {
        if (!cancelled) setError(String(err.message || err));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [symbol, date]);

  const updateCapital = (v) => {
    const n = Number(v);
    setCapital(Number.isFinite(n) && n >= 0 ? n : 0);
    if (typeof window !== "undefined") window.localStorage.setItem(CAPITAL_KEY, String(v));
  };

  const toggleCheck = (n) => setChecked((c) => ({ ...c, [n]: !c[n] }));

  // plan/sizer: prefer the guide's own copy (plan/sizer added in V4-T13),
  // fall back to the debate card's copy for symbols the guide didn't
  // resolve a plan for (e.g. an older payload shape).
  const plan = (guide && guide.plan) || (debateSym && debateSym.plan) || null;
  const sizer = (guide && guide.sizer) || (debateSym && debateSym.sizer) || null;
  const riskChecks = guide && guide.risk_checks;
  const templateIntent = guide && guide.template_intent;

  // B1(a): risk band in rupees = capital x the regime's risk/trade band. Read
  // straight off the debate/run-card payload's governor (card.governor.risk_band
  // = {base_pct, hard_max_pct}, e.g. 0.50-0.75% for SELECTIVE -- same field
  // LawRow already reads in DeskTab.jsx). No fallback to risk_checks: that
  // block only carries a stop-pct CAP, not a risk-per-trade band, so faking
  // one out of it would be a fabricated number.
  const riskBand = card && card.governor && card.governor.risk_band;
  const riskBandLowPct = riskBand && riskBand.base_pct !== undefined ? riskBand.base_pct : null;
  const riskBandHighPct = riskBand && riskBand.hard_max_pct !== undefined ? riskBand.hard_max_pct : null;
  const hasRiskBand = riskBandLowPct !== null && riskBandHighPct !== null;

  // B1(b): qty = floor(risk-rupees / (entry - stop)); FINAL = base * sizer
  // multiplier. Driven off the capital input (previously this math never
  // touched `capital` at all -- base/final qty came straight from the
  // backend's plan.suggested_qty / sizer.final_qty, which don't move when
  // the user types a capital number, so FINAL sat on the backend's fixed
  // value or "-" whenever that field was absent). multiplier===0 must force
  // FINAL to 0, never "-".
  const sizingMath = useMemo(() => {
    if (!plan || plan.entry === null || plan.entry === undefined || plan.stop === null || plan.stop === undefined) {
      return null;
    }
    const stopDist = plan.entry - plan.stop;
    const stopPct = plan.entry ? (stopDist / plan.entry) * 100 : null;
    const riskRupeesLow = hasRiskBand ? (capital * riskBandLowPct) / 100 : null;
    const riskRupeesHigh = hasRiskBand ? (capital * riskBandHighPct) / 100 : null;
    const baseQty =
      riskRupeesLow !== null && stopDist > 0
        ? Math.floor(riskRupeesLow / stopDist)
        : plan.suggested_qty ?? null;
    const multiplier = sizer ? sizer.multiplier : null;
    let finalQty;
    if (multiplier === 0) {
      finalQty = 0;
    } else if (baseQty !== null && multiplier !== null && multiplier !== undefined) {
      finalQty = Math.floor(baseQty * multiplier);
    } else {
      finalQty = sizer ? sizer.final_qty : plan.final_qty;
    }
    return { stopDist, stopPct, baseQty, finalQty, riskRupeesLow, riskRupeesHigh, multiplier };
  }, [plan, sizer, capital, hasRiskBand, riskBandLowPct, riskBandHighPct]);

  // sizerZero drives the paper-only banner: true when either the backend
  // sizer refused outright, or our capital-scaled FINAL comes out to 0.
  const sizerZero = !!(
    (sizer && (sizer.final_qty === 0 || sizer.multiplier === 0)) ||
    (sizingMath && sizingMath.finalQty === 0)
  );

  if (!symbol) {
    return (
      <div className="empty-state">
        <p className="empty-state-line">No symbol selected.</p>
      </div>
    );
  }
  if (loading) {
    return <div className="empty-state">Loading trade plan for {symbol}…</div>;
  }
  if (error) {
    return (
      <div className="empty-state">
        <div className="empty-state-icon">⚠</div>
        <p className="empty-state-line">Could not load the trade plan.</p>
        <p className="empty-state-sub">{error}</p>
      </div>
    );
  }
  if (!guide || !guide.available) {
    return (
      <div className="empty-state">
        <p className="empty-state-line">No guide available for {symbol} on {date}.</p>
        <button type="button" className="disclosure-toggle" onClick={onBackToDebate}>
          &larr; back to debate
        </button>
      </div>
    );
  }

  return (
    <div className="trade-plan-tab">
      <button type="button" className="trade-plan-back mono" onClick={onBackToDebate}>
        &larr; DEBATE
      </button>

      <div className="panel trade-plan-header">
        <p className="panel-title">
          {symbol} &middot; {(guide.family || "unknown").replace(/_/g, " ").toUpperCase()}
        </p>
        <p className="trade-plan-intent">
          {templateIntent
            ? `${templateIntent[0].toUpperCase()}${templateIntent.slice(1)} trade — ${
                templateIntent === "magnitude"
                  ? "hold the big move, sell into weakness not strength."
                  : templateIntent === "velocity"
                  ? "the entry window is short — act on the trigger, not the story."
                  : "size and manage per the checklist below; no single template dominates."
              }`
            : "Template intent not classified for this family."}
        </p>
      </div>

      {sizerZero && (
        <div className="paper-only-banner">
          <span className="paper-only-banner-icon">⚠</span>
          <span className="paper-only-banner-text">
            PAPER ONLY — final qty 0. The sizer refused this trade. Paper-trade the steps below to
            build the sample; do not take this live.
          </span>
        </div>
      )}

      <div className="panel">
        <p className="panel-title small-caps">A &middot; entry conditions (step by step)</p>
        <EntryChecklist steps={guide.steps} checked={checked} onToggle={toggleCheck} isExpert={isExpert} />
      </div>

      <div className="panel">
        <p className="panel-title small-caps">R-ladder</p>
        <RLadderRail entry={plan && plan.entry} stop={plan && plan.stop} target={plan && plan.target} />
      </div>

      <div className="panel">
        <p className="panel-title small-caps">B &middot; position size — sizer (the math, on your capital)</p>
        <div className="trade-plan-capital-row mono">
          <label htmlFor="trade-plan-capital">Your capital ₹</label>
          <input
            id="trade-plan-capital"
            type="number"
            min="0"
            step="1000"
            value={capital}
            onChange={(e) => updateCapital(e.target.value)}
            onFocus={(e) => e.target.select()}
          />
        </div>
        {sizingMath ? (
          <>
            {hasRiskBand ? (
              <p className="mono trade-plan-math-line">
                Risk this trade {round(riskBandLowPct, 2)}–{round(riskBandHighPct, 2)}% = ₹
                {round(sizingMath.riskRupeesLow, 0)}–₹{round(sizingMath.riskRupeesHigh, 0)}
              </p>
            ) : (
              <p className="mono trade-plan-math-line">Risk band not available — no governor risk_band on this payload.</p>
            )}
            <p className="mono trade-plan-math-line">
              Stop distance {round(plan.entry)} − {round(plan.stop)} = {round(sizingMath.stopDist)} ({pct(sizingMath.stopPct)})
            </p>
            <p className="mono trade-plan-math-line">
              Base qty {sizingMath.baseQty ?? "—"}
              {sizer ? ` × sizer ${sizer.multiplier ?? "—"}x` : ""} → FINAL{" "}
              <span className={sizerZero ? "stat-tile-value-danger" : ""}>
                {sizingMath.finalQty !== null && sizingMath.finalQty !== undefined ? sizingMath.finalQty : "—"}
              </span>
            </p>
            {sizer && <SizerBarInline multiplier={sizer.multiplier} />}
            {sizer && sizer.reasoning && <p className="sizer-callout-reason">{sizer.reasoning}</p>}
          </>
        ) : (
          <p className="mono">No sized plan available — sizing math not shown.</p>
        )}
      </div>

      <div className="panel">
        <p className="panel-title small-caps">C &middot; risk checks</p>
        {riskChecks ? (
          <div className="risk-fill-bars">
            <FillBar
              label="Stop % vs regime cap"
              value={riskChecks.stop_pct}
              cap={riskChecks.regime_stop_cap}
              unit="%"
            />
            <FillBar
              label="Open risk before → after (cap)"
              value={riskChecks.open_risk_after}
              cap={riskChecks.open_risk_cap}
              unit="%"
            />
            <div className="risk-fill-row">
              <span className="risk-fill-label mono">Open risk now</span>
              <span className="risk-fill-value mono">
                {riskChecks.open_risk_now !== null && riskChecks.open_risk_now !== undefined
                  ? pct(riskChecks.open_risk_now)
                  : "not available in payload"}
              </span>
            </div>
            {isExpert && (
              <div className="risk-fill-row">
                <span className="risk-fill-label mono">k × <Term k="adr" as="span">ADR</Term> (display-only)</span>
                <span className="risk-fill-value mono">
                  {riskChecks.k_adr !== null && riskChecks.k_adr !== undefined
                    ? `${riskChecks.k_adr}x (ADR20 ${round(riskChecks.adr20)}%)`
                    : "not available in payload"}
                </span>
              </div>
            )}
            <div className="risk-fill-row">
              <span className="risk-fill-label mono">Concurrent tight-SL positions</span>
              <span className="risk-fill-value mono">
                {riskChecks.concurrent_tight_sl !== null && riskChecks.concurrent_tight_sl !== undefined
                  ? `${riskChecks.concurrent_tight_sl} / ${riskChecks.concurrent_cap ?? "—"} max open`
                  : "not available in payload"}
              </span>
            </div>
            <p className="mono trade-plan-no-mental-stop">⚠ Hard stop must be a LIVE order — no mental stops.</p>
          </div>
        ) : (
          <p className="mono">Risk checks unavailable — no sized plan for this symbol on {date}.</p>
        )}
      </div>

      <button type="button" className="disclosure-toggle trade-plan-debate-link" onClick={onBackToDebate}>
        &rarr; debate card
      </button>
    </div>
  );
}

function SizerBarInline({ multiplier }) {
  const SIZER_MIN = 0.25;
  const SIZER_MAX = 1.25;
  if (multiplier === null || multiplier === undefined) return null;
  const clamped = Math.min(Math.max(multiplier, SIZER_MIN), SIZER_MAX);
  const pctFilled = ((clamped - SIZER_MIN) / (SIZER_MAX - SIZER_MIN)) * 100;
  return (
    <div className="sizer-bar" title={`[B] sizer multiplier ${multiplier}x (range ${SIZER_MIN}-${SIZER_MAX}x)`}>
      <div className="sizer-bar-track">
        <div className="sizer-bar-fill" style={{ width: `${pctFilled}%` }} />
        <div className="sizer-bar-marker" style={{ left: `${pctFilled}%` }} />
      </div>
      <div className="sizer-bar-scale mono">
        <span>{SIZER_MIN}x</span>
        <span>1.0x</span>
        <span>{SIZER_MAX}x</span>
      </div>
    </div>
  );
}
