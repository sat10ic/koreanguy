import React, { useEffect, useRef, useState } from "react";
import { fetchDebate, fetchSignalGuide, chartUrl, pushSymbolToDebate } from "./api.js";
import ChartDrawer from "./ChartDrawer.jsx";
import { Term } from "./Glossary.jsx";
import { modelSeatLabel, humanizeSourceCite, stripCitationCodes } from "./utils.js";
import { useDensity } from "./DensityContext.jsx";

// T10(b): strip inline citation codes from user-facing prose, keeping the
// original (with codes) available via a hover affordance.
function CitedText({ text, className }) {
  const { clean, codes } = stripCitationCodes(text);
  if (!codes.length) return <span className={className}>{clean}</span>;
  return (
    <span className={className}>
      {clean}
      <span className="sources-affordance" title={`sources: ${codes.join(", ")}`}>i</span>
    </span>
  );
}

// F4: WIREFRAMES_V4.md section 4 -- "Seats: Scout · Skeptic · Analyst ·
// Historian (hover = which model)." The 4 debating models always come back
// in the same query order (see api/app.py rows filtered to agent not in
// chair/vision/sizer), so seat role is assigned by that stable ordinal
// position; the raw model id moves from the visible label into the title
// (hover) attribute, same affordance AgentChip already had.
const SEAT_ROLES = ["SCOUT", "SKEPTIC", "ANALYST", "HISTORIAN"];

function seatRoleLabel(seatIndex) {
  if (seatIndex === undefined || seatIndex === null) return null;
  return SEAT_ROLES[seatIndex] || `SEAT ${seatIndex + 1}`;
}

// F4: small conviction dot/badge -- fill/opacity intensity scales with the
// payload's conviction integer (0-5). Distinct from the multi-segment
// ConvictionRow meter below: this one sits inline next to a seat's name
// wherever the seat appears (bull/bear columns), not just the summary row.
function ConvictionBadge({ conviction }) {
  if (conviction === null || conviction === undefined) return null;
  const c = Math.min(Math.max(conviction, 0), 5);
  const intensity = 0.3 + (c / 5) * 0.7;
  return (
    <span
      className="conviction-badge"
      style={{ opacity: intensity }}
      title={`conviction ${c}/5`}
      aria-label={`conviction ${c} of 5`}
    />
  );
}

// T10(a): plain seat-role name for a raw model id, full id kept in title.
// seatIndex (when passed) selects a role name (SCOUT/SKEPTIC/ANALYST/
// HISTORIAN); without it, falls back to the old modelSeatLabel plain model
// name (used by non-seat contexts like the track-record footer).
function AgentChip({ agent, seatIndex, conviction, ...rest }) {
  const label = seatIndex !== undefined && seatIndex !== null ? seatRoleLabel(seatIndex) : modelSeatLabel(agent);
  return (
    <span className="agent-chip mono" data-agent={agentKey(agent)} title={agent} {...rest}>
      {label}
      {conviction !== undefined && <ConvictionBadge conviction={conviction} />}
    </span>
  );
}

// T5: near-miss failed-gate label in plain words.
const FAILED_GATE_HUMAN = {
  regime: "Regime",
  tradability: "Tradability",
  "trend-template": "Trend template",
  "fresh-leg": "Fresh leg",
  participation: "Participation",
  risk: "Risk sizing",
};

function humanFailedGate(gate) {
  if (!gate) return "gate";
  return FAILED_GATE_HUMAN[gate] || gate.replace(/[-_]/g, " ");
}

// Strongest bear point: highest-conviction model's bear_case, else first
// available non-empty bear_case.
function strongestBearLine(models) {
  if (!models || !models.length) return null;
  const withBear = models.map((m, idx) => ({ ...m, idx })).filter((m) => m.bear_case);
  if (!withBear.length) return null;
  const sorted = [...withBear].sort((a, b) => (b.conviction || 0) - (a.conviction || 0));
  const m = sorted[0];
  return { agent: m.agent, text: m.bear_case, idx: m.idx, conviction: m.conviction };
}

function agentKey(actor) {
  return (actor || "").toLowerCase();
}

function round(n, digits = 1) {
  if (n === null || n === undefined) return "—";
  const f = Math.pow(10, digits);
  return Math.round(n * f) / f;
}

// V4: extend the conviction-meter idiom to the sizer multiplier — a linear
// bar over the 0.25-1.25x band the sizer agent actually outputs.
const SIZER_MIN = 0.25;
const SIZER_MAX = 1.25;

function sizerRead(multiplier) {
  if (multiplier === null || multiplier === undefined) return "Sizer did not return a multiplier.";
  if (multiplier === 0) return `Sizer ${multiplier}x - take ZERO size, sizer refused this trade.`;
  if (multiplier < 0.75) return `Sizer ${multiplier}x - cut below base size because risk quality is weak.`;
  if (multiplier > 1.05) return `Sizer ${multiplier}x - above base size because the risk read is stronger.`;
  return `Sizer ${multiplier}x - close to base size.`;
}

function funnelRead(funnel, drops) {
  const universe = funnel.universe ?? "-";
  const shortlist = funnel.shortlist ?? "-";
  const debated = funnel.debated ?? "-";
  const nearMisses = typeof funnel.debated === "number" && typeof funnel.shortlist === "number"
    ? Math.max(funnel.debated - funnel.shortlist, 0)
    : null;
  const debatedNote = nearMisses
    ? `${shortlist} passed every gate; ${nearMisses} near-misses were added back in for debate (${debated} debated total)`
    : `${shortlist} passed every gate and were debated`;
  if (drops) return `${universe} names entered, ${debatedNote}; biggest drops: ${drops}.`;
  return `${universe} names entered, ${debatedNote}.`;
}

// E2: base-rate proof chip. NEVER renders "n/a" when a cell exists in
// setup_expectancy (system loop, passed cohort) -- only when chip_for()
// truly found no row for this family x regime does it fall back to
// "no data yet" (honest: pipeline hasn't observed this cell at all).
// Below the trust floor (n<20) it renders UNPROVEN instead of a hit-rate
// that would read as more reliable than the sample supports.
const TRUST_FLOOR_N = 20;

function cohortLine(cell, label, unit) {
  if (!cell || !cell.n) return null;
  if (cell.n < TRUST_FLOOR_N) {
    return `${label} UNPROVEN — building sample (n=${cell.n})`;
  }
  const winPct = round((cell.hit_rate || 0) * 100, 0);
  const avg = round(cell.mean_r ?? cell.median_r ?? cell.posterior_r, 2);
  const sign = avg >= 0 ? "+" : "";
  if (unit === "pct") {
    // Refused cohort: no stop was ever set for a refused name, so this is a
    // raw close-to-close %-return baseline, NOT an R-multiple. Labeled
    // distinctly to avoid implying R-precision the data doesn't have.
    return `${label} n=${cell.n}, win ${winPct}%, avg ${sign}${avg}% (no stop set)`;
  }
  return `${label} n=${cell.n}, hit ${winPct}%, avg ${sign}${avg}R (system)`;
}

function BaseRateChip({ baseRate, family, lensTag }) {
  if (!baseRate || (!baseRate.system && !baseRate.refused)) {
    return <span className="mono base-rate-chip">base rate {lensTag}: no data yet for {family || "this family"}</span>;
  }
  const passedLine = cohortLine(baseRate.system, "passed", "r");
  const refusedLine = cohortLine(baseRate.refused, "refused", "pct");
  return (
    <span className="mono base-rate-chip">
      base rate {lensTag}: {passedLine || "no passed-cohort data yet"}
      {refusedLine ? ` · ${refusedLine}` : ""}
    </span>
  );
}

// SHIP-1 #7: ML direction P(up 10d) chip. A labeled probability FACT from
// the LightGBM walk-forward classifier — always tagged EXPERIMENTAL, never
// styled/treated as a verdict or gate (AD8).
function MlChip({ ml }) {
  if (!ml || ml.p_up_10d === null || ml.p_up_10d === undefined) return null;
  const drivers = ml.drivers && ml.drivers.length ? ml.drivers.join(", ") : "n/a";
  return (
    <span className="mono ml-chip" title="Labeled probability fact from the walk-forward LightGBM classifier — informational only, never used to gate/size/rank.">
      ML: P(up 10d)={round(ml.p_up_10d, 2)} drivers: {drivers}
    </span>
  );
}

// SHIP-1 #9: delivery% accumulation/distribution chip — fact-only, read
// from features_daily. Was computed by the API (sym.delivery) but never
// rendered anywhere; this is the fix for "no trace of the ML features".
function DeliveryChip({ delivery }) {
  if (!delivery || !delivery.flag) return null;
  const isAccum = delivery.flag === "ACCUMULATION";
  return (
    <span className={"mono delivery-chip " + (isAccum ? "accum" : "distrib")} title="Delivery% accumulation/distribution tag — fact only, lift not yet validated.">
      Delivery: {delivery.flag}
    </span>
  );
}

// Per-stock 3-state HMM regime chip (see ml/stock_hmm.py) — same fact as
// the chart drawer's MODEL STATE box, surfaced here too so it isn't buried
// behind a click into the chart.
function StockHmmChip({ hmm }) {
  if (!hmm) return null;
  if (hmm.available === false) {
    return (
      <span className="mono stock-hmm-chip stock-hmm-chip-muted" title="Per-stock 3-state GaussianHMM regime read — unavailable.">
        stock HMM: unavailable ({hmm.reason || "no reason given"})
      </span>
    );
  }
  if (!hmm.line) return null;
  return (
    <span className={"mono stock-hmm-chip" + (hmm.stale ? " stock-hmm-chip-stale" : "")} title="Per-stock 3-state GaussianHMM regime read — fact only, never gates/sizes.">
      {hmm.line}
    </span>
  );
}

// Consolidates ML / delivery / base-rate / stock-HMM chips into one
// visually distinct, clearly-labeled block so the models' voice is not
// buried in the footer among unrelated chips.
function AiSignalsBlock({ sym, lensTag }) {
  const hasAny = sym.ml || sym.delivery || sym.base_rate || sym.stock_hmm;
  if (!hasAny) return null;
  return (
    <div className="ai-signals-block">
      <p className="ai-signals-title small-caps">
        AI signals <span className="experimental-badge">EXPERIMENTAL</span>
      </p>
      <div className="ai-signals-chips">
        <BaseRateChip baseRate={sym.base_rate} family={sym.family} lensTag={lensTag} />
        <MlChip ml={sym.ml} />
        <DeliveryChip delivery={sym.delivery} />
        <StockHmmChip hmm={sym.stock_hmm} />
      </div>
    </div>
  );
}

function verdictTerm(verdict) {
  const v = (verdict || "").toUpperCase();
  if (v === "TAKE") return "take";
  if (v === "SKIP") return "skip";
  return null;
}

function gateTerm(name) {
  return name === "trend-template" ? "gate-trend" : `gate-${name}`;
}

function SizerBar({ multiplier }) {
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

function ConvictionDots({ conviction }) {
  const c = conviction || 0;
  const segs = [];
  for (let i = 0; i < 5; i += 1) {
    segs.push(<span key={i} className={"conv-seg" + (i < c ? " filled" : "")} />);
  }
  return (
    <span className="conv-meter">
      {segs}
      <span className="conv-count">({c || "—"})</span>
    </span>
  );
}

function ChartImg({ date, symbol, tf, stamp }) {
  const [failed, setFailed] = useState(false);
  if (failed) {
    return <div className="chart-thumb chart-thumb-missing mono">[ {symbol}_{tf}.png unavailable ]</div>;
  }
  return (
    <div className="chart-frame">
      <img
        className="chart-thumb"
        src={chartUrl(date, symbol, tf)}
        alt={`${symbol} ${tf}`}
        onError={() => setFailed(true)}
      />
      {stamp && <div className="chart-stamp-ribbon mono">{stamp}</div>}
    </div>
  );
}

const GATE_ORDER = ["regime", "tradability", "trend-template", "fresh-leg", "participation", "risk"];
const GATE_SHORT_LABEL = {
  regime: "REG",
  tradability: "TRD",
  "trend-template": "TRND",
  "fresh-leg": "LEG",
  participation: "PART",
  risk: "RISK",
};
const DROP_LABEL = {
  tradability: "tradability",
  regime: "regime",
  "trend-template": "trend",
  "fresh-leg": "fresh-leg",
  participation: "particip",
  risk: "risk",
};

function GateDotsRow({ gates }) {
  const byName = {};
  (gates || []).forEach((g) => {
    byName[g.gate] = g;
  });
  return (
    <div className="gate-dots-row">
      <span className="gate-dots-label">Gates</span>
      {GATE_ORDER.map((name) => {
        const g = byName[name];
        if (!g) {
          return (
            <span
              key={name}
              className="gate-dot missing"
              title={`${GATE_SHORT_LABEL[name]}: not evaluated`}
            >
              <Term k={gateTerm(name)}>{GATE_SHORT_LABEL[name]}</Term>
            </span>
          );
        }
        const evidence = g.evidence && Object.keys(g.evidence).length
          ? JSON.stringify(g.evidence)
          : null;
        const tooltip = `${GATE_SHORT_LABEL[name]} ${g.pass ? "PASS" : "FAIL"}${
          g.reason ? `: ${g.reason}` : ""
        }${evidence ? ` ${evidence}` : ""}`;
        return (
          <span
            key={name}
            className={"gate-dot " + (g.pass ? "pass" : "fail")}
            title={tooltip}
          >
            <Term k={gateTerm(name)}>{GATE_SHORT_LABEL[name]}</Term>
          </span>
        );
      })}
    </div>
  );
}

function FunnelPanel({ funnel }) {
  if (!funnel) return null;
  const byGate = funnel.by_gate || {};
  const drops = Object.entries(byGate)
    .sort((a, b) => b[1] - a[1])
    .map(([gate, n]) => `${DROP_LABEL[gate] || gate} −${n}`)
    .join(" · ");
  const noHitDrop = funnel.no_hit_drop ?? null;
  const screenerDrop = funnel.screener_drop ?? null;
  const gatesDrop = Object.values(byGate).reduce((a, b) => a + b, 0);
  const nearMisses = typeof funnel.debated === "number" && typeof funnel.shortlist === "number"
    ? Math.max(funnel.debated - funnel.shortlist, 0)
    : 0;
  return (
    <div className="panel funnel-panel">
      <p className="panel-title small-caps">The gate</p>
      {/* SHIP-3 #1: funnel stages narrow monotonically -- Universe -> Screeners
          -> Gates -> Passed. "Debated" is NOT a stage: near-misses that never
          cleared every gate get added back in for debate, so it can be
          larger than Passed. It renders as a separate annotation below. */}
      <div className="funnel-stages mono">
        <span>
          <span className="funnel-stage-value">{funnel.universe ?? "—"}</span>
          <span className="funnel-stage-label">Universe</span>
        </span>
        <span className="funnel-arrow" title={noHitDrop != null ? `−${noHitDrop} no screener/detector hit` : undefined}>─▶</span>
        <span>
          <span className="funnel-stage-value">{funnel.screeners ?? "—"}</span>
          <span className="funnel-stage-label">Screeners</span>
        </span>
        <span className="funnel-arrow" title={screenerDrop != null ? `−${screenerDrop} failed tradability` : undefined}>─▶</span>
        <span>
          <span className="funnel-stage-value">{funnel.gates ?? "—"}</span>
          <span className="funnel-stage-label">Gates</span>
        </span>
        <span className="funnel-arrow" title={gatesDrop ? `−${gatesDrop} failed a named gate` : undefined}>─▶</span>
        <span>
          <span className="funnel-stage-value">{funnel.shortlist ?? "—"}</span>
          <span className="funnel-stage-label">Passed</span>
          {funnel.tradable_summary && (
            <span className="funnel-stage-sub mono">{funnel.tradable_summary}</span>
          )}
        </span>
      </div>
      <p className="funnel-drops mono">
        {noHitDrop != null && <>−{noHitDrop} no screener/detector hit</>}
        {noHitDrop != null && screenerDrop != null && " · "}
        {screenerDrop != null && <>−{screenerDrop} failed tradability</>}
        {(noHitDrop != null || screenerDrop != null) && drops && " · "}
        {drops}
      </p>
      {nearMisses > 0 && (
        <p className="funnel-annotation mono">
          + {nearMisses} near-misses added for debate = {funnel.debated} DEBATED
        </p>
      )}
      <p className="caption-b">[B] {funnelRead(funnel, drops)}</p>
    </div>
  );
}

// F: per-signal HOW-TO-TRADE guide. Deterministic (signal_guide.py, no LLM) —
// fetched lazily on first expand so a card with 10+ names doesn't fire 10
// extra requests before anyone opens one.
function HowToTradeThis({ date, symbol }) {
  const [open, setOpen] = useState(false);
  const [guide, setGuide] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [checked, setChecked] = useState({});

  const toggle = () => {
    const next = !open;
    setOpen(next);
    if (next && !guide && !loading) {
      setLoading(true);
      setError(null);
      fetchSignalGuide(symbol, date)
        .then((body) => setGuide(body))
        .catch((err) => setError(String(err)))
        .finally(() => setLoading(false));
    }
  };

  const toggleCheck = (n) => setChecked((c) => ({ ...c, [n]: !c[n] }));

  return (
    <div className="how-to-trade-block">
      <button type="button" className="how-to-trade-toggle" onClick={toggle}>
        {open ? "▾" : "▸"} HOW TO TRADE THIS — step by step
      </button>
      {open && (
        <div className="how-to-trade-body">
          {loading && <p className="mono">Loading steps...</p>}
          {error && <p className="mono">Could not load steps: {error}</p>}
          {guide && !guide.available && (
            <p className="mono">No guide available for {symbol} on {date}.</p>
          )}
          {guide && guide.available && (
            <>
              <p className="caption-b">
                [B] Deterministic checklist, not an LLM call — the sizer has final authority on
                quantity (not the plan's base qty), ordered for a beginner. Lens: {guide.family}.
              </p>
              <ol className="how-to-trade-steps">
                {guide.steps.map((step) => (
                  <li key={step.n} className={"how-to-trade-step" + (step.n === 0 ? " how-to-trade-step-refusal" : "")}>
                    <label className="how-to-trade-step-head">
                      <input
                        type="checkbox"
                        checked={!!checked[step.n]}
                        onChange={() => toggleCheck(step.n)}
                      />
                      <span className="how-to-trade-step-title">{step.title}</span>
                    </label>
                    <p className="how-to-trade-instruction">{step.instruction}</p>
                    <p className="how-to-trade-check mono">Check before you proceed: {step.check}</p>
                    <p className="how-to-trade-cite mono" title={step.source_cite}>
                      source: {humanizeSourceCite(step.source_cite)}
                    </p>
                  </li>
                ))}
              </ol>
            </>
          )}
        </div>
      )}
    </div>
  );
}

function SymbolButton({ symbol, onOpenChart }) {
  return (
    <button className="symbol-chart-button debate-symbol" onClick={() => onOpenChart(symbol)} title={`Open ${symbol} chart`}>
      {symbol}
    </button>
  );
}

// Shared conviction-row, used by both the passed-card layout and the
// near-miss "show full debate" expansion.
function ConvictionRow({ models, chair }) {
  const spread = chair && chair.conviction_spread;
  const disagreement = chair && chair.disagreement;
  return (
    <div className="conviction-row">
      <span className="overline">
        <Term k="conviction">Conviction</Term>
      </span>
      {models.map((m, idx) => (
        <span key={m.agent} className="conviction-item">
          <AgentChip agent={m.agent} seatIndex={idx} />
          <ConvictionDots conviction={m.conviction} />
        </span>
      ))}
      {spread !== null && spread !== undefined && (
        <span className={"spread-badge mono" + (disagreement ? " disagree" : "")}>
          <Term k="spread">spread</Term> {spread}
          <span className="spread-mini-meter">
            <span
              className="spread-mini-meter-fill"
              style={{ width: `${Math.min(Math.max(spread, 0), 4) * 25}%` }}
            />
          </span>
        </span>
      )}
    </div>
  );
}

// T5: "model debate" = bull/bear columns + vision strip. Wrapped in a
// "show model debate" toggle on passed cards; rendered inline (already
// behind the near-miss card's own "show full debate" toggle) otherwise.
// F4: council balance bar -- summed BULL conviction (models with a
// bull_case) vs summed BEAR conviction (models with a bear_case),
// proportional bar above the bull/bear columns. A model can carry both a
// bull_case and a bear_case (each seat argues both sides); each side sums
// only the conviction of models that actually wrote that side's case.
function CouncilBalanceBar({ models }) {
  if (!models || !models.length) return null;
  const bullTotal = models.reduce((sum, m) => (m.bull_case ? sum + (m.conviction || 0) : sum), 0);
  const bearTotal = models.reduce((sum, m) => (m.bear_case ? sum + (m.conviction || 0) : sum), 0);
  const total = bullTotal + bearTotal;
  const bullPct = total > 0 ? (bullTotal / total) * 100 : 50;
  return (
    <div className="council-balance-bar" title={`Council balance: bull ${bullTotal} vs bear ${bearTotal} (summed conviction)`}>
      <div className="council-balance-track">
        <div className="council-balance-bull" style={{ width: `${bullPct}%` }} />
        <div className="council-balance-bear" style={{ width: `${100 - bullPct}%` }} />
      </div>
      <div className="council-balance-scale mono">
        <span>bull {bullTotal}</span>
        <span>bear {bearTotal}</span>
      </div>
    </div>
  );
}

// F4: vision ✓/✗ chip -- terse glyph form of the vision verdict, sitting
// next to the full vision-strip text so the read/no-read is scannable
// without parsing the reasoning line.
function VisionChip({ vision }) {
  if (!vision) {
    return <span className="vision-chip vision-chip-none mono" title="No vision pass ran for this card.">vision ✗</span>;
  }
  const v = String(vision.verdict || "").toLowerCase();
  const ok = v.includes("bull") || v.includes("pass") || v.includes("confirm") || v.includes("clean");
  return (
    <span
      className={"vision-chip mono " + (ok ? "vision-chip-ok" : "vision-chip-bad")}
      title={`Vision: ${vision.verdict || "—"} — ${vision.reasoning || "no reasoning"}`}
    >
      vision {ok ? "✓" : "✗"}
    </span>
  );
}

// F4: beginner-mode bull/bear lines show only the first sentence, with a
// "show more" toggle to expand the full argument. Expert mode always shows
// the full text (matches the spec's per-screen beginner/expert split — the
// debate screen itself STAYS visible either way, only the argument length
// differs). Falls back to the whole cleaned string when no sentence-ending
// punctuation is found (short/fragment reasoning).
const SENTENCE_END_RE = /^.*?[.!?](?=\s|$)/;

function CaseLine({ agent, seatIndex, conviction, text }) {
  const { isExpert } = useDensity();
  const [expanded, setExpanded] = useState(false);
  const { clean, codes } = stripCitationCodes(text || "—");
  const firstSentenceMatch = clean.match(SENTENCE_END_RE);
  const firstSentence = firstSentenceMatch ? firstSentenceMatch[0] : clean;
  const hasMore = !isExpert && firstSentence.length < clean.length;
  const showFull = isExpert || expanded;

  return (
    <p className="case-line">
      <AgentChip agent={agent} seatIndex={seatIndex} conviction={conviction} />
      {": "}
      <span>{showFull ? clean : firstSentence}</span>
      {codes.length > 0 && <span className="sources-affordance" title={`sources: ${codes.join(", ")}`}>i</span>}
      {hasMore && (
        <button type="button" className="case-line-toggle" onClick={() => setExpanded((v) => !v)}>
          {expanded ? "show less" : "show more"}
        </button>
      )}
    </p>
  );
}

function ModelDebateBlock({ date, sym }) {
  return (
    <>
      <CouncilBalanceBar models={sym.models} />
      <div className="bull-bear-columns">
        <div className="bull-column">
          <p className="panel-title small-caps">
            <Term k="bull">Bull</Term>
          </p>
          {sym.models.map((m, idx) => (
            <CaseLine key={m.agent} agent={m.agent} seatIndex={idx} conviction={m.conviction} text={m.bull_case} />
          ))}
        </div>
        <div className="bear-column">
          <p className="panel-title small-caps">
            <Term k="bear">Bear</Term>
          </p>
          {sym.models.map((m, idx) => (
            <CaseLine key={m.agent} agent={m.agent} seatIndex={idx} conviction={m.conviction} text={m.bear_case} />
          ))}
        </div>
      </div>

      <div className="vision-strip">
        <p className="panel-title small-caps">
          <Term k="vision-strip">Vision strip</Term> <VisionChip vision={sym.vision} />
        </p>
        <div className="vision-images">
          <ChartImg
            date={date}
            symbol={sym.symbol}
            tf="daily"
            stamp={sym.vision ? `${sym.vision.verdict || ""}` : null}
          />
          <ChartImg date={date} symbol={sym.symbol} tf="weekly" />
        </div>
        <p className="vision-stamp mono">
          {sym.vision
            ? `stamp: "${sym.vision.reasoning || "—"}" ${sym.vision.verdict || ""}`
            : "stamp: — (no vision pass)"}
        </p>
      </div>
    </>
  );
}

function PlanBlock({ sym, sizerZero, onOpenTradePlan }) {
  return (
    <div className="plan-block">
      <p className="panel-title small-caps">
        Plan <span className="math-engine-label mono">[math: engine]</span>
        {sym.plan && onOpenTradePlan && (
          <button
            type="button"
            className="trade-plan-link mono"
            onClick={() => onOpenTradePlan(sym.symbol)}
          >
            [TRADE PLAN&rarr;]
          </button>
        )}
      </p>
      {sym.plan ? (
        <div className="stat-row">
          <div className="stat-tile">
            <span className="stat-tile-label">Entry</span>
            <span className="stat-tile-value mono">{round(sym.plan.entry)}</span>
          </div>
          <div className="stat-tile">
            <span className="stat-tile-label">Stop</span>
            <span className="stat-tile-value mono">{round(sym.plan.stop)}</span>
          </div>
          <div className="stat-tile">
            <span className="stat-tile-label">Target</span>
            <span className="stat-tile-value mono">{round(sym.plan.target)}</span>
          </div>
          <div className="stat-tile">
            <span className="stat-tile-label">RR</span>
            <span className="stat-tile-value mono">{round(sym.plan.rr)}</span>
          </div>
          <div className="stat-tile">
            <span className="stat-tile-label">Final qty (sizer)</span>
            <span className={"stat-tile-value mono" + (sizerZero ? " stat-tile-value-danger" : "")}>
              {sym.sizer && sym.sizer.final_qty !== undefined && sym.sizer.final_qty !== null
                ? sym.sizer.final_qty
                : "—"}
            </span>
            <span className="stat-tile-sub mono">base qty {sym.plan.suggested_qty ?? "—"}</span>
          </div>
        </div>
      ) : sym.near_miss ? (
        <p className="plan-line mono">
          NEAR MISS — failed {humanFailedGate(sym.near_miss.failed_gate)}
          {sym.near_miss.reason ? `: ${sym.near_miss.reason}` : ""}
        </p>
      ) : (
        <p className="plan-line mono">plan unavailable</p>
      )}
      {sym.sizer && (
        <div className="sizer-callout">
          <p className="sizer-callout-headline mono">
            <Term k="sizer-multiplier">Sizer multiplier</Term>{" "}
            SIZER {sym.sizer.multiplier ?? "—"}x → final qty {sym.sizer.final_qty ?? "—"}
          </p>
          <SizerBar multiplier={sym.sizer.multiplier} />
          <p className="sizer-callout-reason"><CitedText text={sym.sizer.reasoning || "—"} /></p>
          <p className="caption-b">[B] {sizerRead(sym.sizer.multiplier)}</p>
        </div>
      )}
    </div>
  );
}

function DebateFooter({ sym }) {
  return (
    <div className="debate-footer">
      {sym.track_record.map((t) => (
        <span key={t.agent} className="mono track-chip" title={t.agent}>
          {modelSeatLabel(t.agent)} on {sym.family}: {t.n ? `${round((t.hit_rate || 0) * t.n, 0)}/${t.n}` : "n/a"}
          {t.thin ? " (thin)" : ""}
        </span>
      ))}
    </div>
  );
}

function CardHeader({ sym, lensTag, onOpenChart }) {
  const chair = sym.chair;
  return (
    <div className="debate-card-header">
      <SymbolButton symbol={sym.symbol} onOpenChart={onOpenChart} />
      <span className="debate-lens mono">{lensTag}</span>
      {sym.source === "user_pushed" && (
        <span className="debate-pushed-badge mono" title="pushed on-demand from the screener/search box">
          ★ PUSHED BY YOU
        </span>
      )}
      <VisionChip vision={sym.vision} />
      <span className={"debate-chair-verdict mono " + (chair && chair.verdict === "TAKE" ? "take" : "skip")}>
        <Term k="chair">CHAIR</Term>:{" "}
        {chair && verdictTerm(chair.verdict) ? <Term k={verdictTerm(chair.verdict)}>{chair.verdict}</Term> : chair ? chair.verdict : "—"}
      </span>
    </div>
  );
}

// T5: near-miss cards (no plan) collapse to a compact 3-line row by default —
// symbol+lens, failed-gate chip+reason, and the single strongest bear point.
// "show full debate" reveals the full 4-model debate (unchanged markup).
function NearMissSymbolCard({ date, sym, lensTag, onOpenChart }) {
  const [open, setOpen] = useState(false);
  const bear = strongestBearLine(sym.models);

  return (
    <div className="panel debate-card near-miss-card" id={`debate-card-${sym.symbol}`}>
      <div className="near-miss-row">
        <CardHeader sym={sym} lensTag={lensTag} onOpenChart={onOpenChart} />
        <p className="near-miss-row-line mono">
          Failed: {humanFailedGate(sym.near_miss.failed_gate)}
          {sym.near_miss.reason ? ` — ${sym.near_miss.reason}` : ""}
        </p>
        <p className="near-miss-row-line near-miss-evidence">
          {bear ? (
            <>
              <AgentChip agent={bear.agent} seatIndex={bear.idx} conviction={bear.conviction} />: <CitedText text={bear.text} />
            </>
          ) : (
            "no bear case recorded"
          )}
        </p>
      </div>

      <button type="button" className="disclosure-toggle" onClick={() => setOpen((o) => !o)}>
        {open ? "▾" : "▸"} show full debate
      </button>
      {open && (
        <div className="disclosure-body">
          <GateDotsRow gates={sym.gates} />
          <div className="debate-card-body">
            <ConvictionRow models={sym.models} chair={sym.chair} />
            <ModelDebateBlock date={date} sym={sym} />
            <PlanBlock sym={sym} sizerZero={false} />
            <AiSignalsBlock sym={sym} lensTag={lensTag} />
            <DebateFooter sym={sym} />
          </div>
        </div>
      )}
    </div>
  );
}

// T5: passed cards (with a plan) surface HOW TO TRADE THIS above the
// bull/bear model-debate section, which now collapses by default.
function PassedSymbolCard({ date, sym, lensTag, onOpenChart, onOpenTradePlan }) {
  const [debateOpen, setDebateOpen] = useState(false);
  const sizerZero = !!(sym.sizer && (sym.sizer.final_qty === 0 || sym.sizer.multiplier === 0));

  return (
    <div className="panel debate-card" id={`debate-card-${sym.symbol}`}>
      {sizerZero && (
        <div className="paper-only-banner">
          <span className="paper-only-banner-icon">⚠</span>
          <span className="paper-only-banner-text">
            PAPER ONLY — DO NOT TAKE LIVE. The sizer refused this trade (final qty 0). The chair
            verdict below is a debate opinion, not a sizing authority.
          </span>
        </div>
      )}
      <CardHeader sym={sym} lensTag={lensTag} onOpenChart={onOpenChart} />

      <GateDotsRow gates={sym.gates} />

      <div className="debate-card-body">
        <ConvictionRow models={sym.models} chair={sym.chair} />

        <PlanBlock sym={sym} sizerZero={sizerZero} onOpenTradePlan={onOpenTradePlan} />

        <HowToTradeThis date={date} symbol={sym.symbol} />

        <button type="button" className="disclosure-toggle" onClick={() => setDebateOpen((o) => !o)}>
          {debateOpen ? "▾" : "▸"} show model debate
        </button>
        {debateOpen && (
          <div className="disclosure-body">
            <ModelDebateBlock date={date} sym={sym} />
          </div>
        )}

        <AiSignalsBlock sym={sym} lensTag={lensTag} />

        <DebateFooter sym={sym} />
      </div>
    </div>
  );
}

function SymbolCard({ date, sym, onOpenChart, onOpenTradePlan }) {
  const lensTag = (sym.family_label || sym.family || "unknown").replace(/[/_]/g, " ").toUpperCase();
  if (!sym.plan && sym.near_miss) {
    return <NearMissSymbolCard date={date} sym={sym} lensTag={lensTag} onOpenChart={onOpenChart} />;
  }
  return <PassedSymbolCard date={date} sym={sym} lensTag={lensTag} onOpenChart={onOpenChart} onOpenTradePlan={onOpenTradePlan} />;
}

const STANCE_PILL_CLASS = {
  STAND_ASIDE: "stand-aside",
  SIT_OUT: "sit-out",
  CAUTION: "caution",
  ACT_PER_PLAN: "act-per-plan",
};

const STANCE_LABEL = {
  STAND_ASIDE: "STAND ASIDE",
  SIT_OUT: "SIT OUT",
  CAUTION: "CAUTION",
  ACT_PER_PLAN: "ACT PER PLAN",
};

function StancePill({ call }) {
  if (!call || !call.stance) return null;
  const pillClass = STANCE_PILL_CLASS[call.stance] || "sit-out";
  const label = STANCE_LABEL[call.stance] || call.stance;
  return (
    <span className={`call-stance-pill ${pillClass}`}>
      <Term k="stance">{label}</Term>
    </span>
  );
}

function ZeroTakeState({ symbols, call, onOpenChart }) {
  const struck = symbols.filter((s) => s.chair && s.chair.verdict !== "TAKE");
  return (
    <div className="panel zero-take-panel">
      <div className="call-stance-row">
        <p className="panel-title small-caps" style={{ margin: 0 }}>
          The desk sat out
        </p>
        <StancePill call={call} />
      </div>
      <p>
        The desk took nothing on this date. {symbols.length} name{symbols.length === 1 ? "" : "s"} debated, all
        <Term k="struck">struck</Term>.
      </p>
      {struck.map((s) => (
        <p key={s.symbol} className="mono struck-line">
          <SymbolButton symbol={s.symbol} onOpenChart={onOpenChart} /> — <Term k="chair">chair</Term> <Term k="struck">struck</Term>: "<CitedText text={s.chair ? s.chair.reasoning : "—"} />"
        </p>
      ))}
    </div>
  );
}

export default function DebateTab({ date, card, jumpSignal, onOpenTradePlan }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [chartSymbol, setChartSymbol] = useState(null);
  const [reloadTick, setReloadTick] = useState(0);
  const firstCardRef = useRef(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetchDebate(date)
      .then((body) => {
        if (!cancelled) setData(body);
      })
      .catch((err) => {
        if (!cancelled) setError(String(err));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [date, reloadTick]);

  // T7: cross-tab handoff -- DESK's "see tonight's idea ->" (and FOCUS NOW
  // deep-links) set jumpSignal to a fresh {symbol, ts} object; scroll to
  // that symbol's card (or the first card if no symbol given) once the
  // debate data for this date has loaded.
  useEffect(() => {
    if (!jumpSignal || loading || !data || !data.available) return;
    const target = jumpSignal.symbol
      ? document.getElementById(`debate-card-${jumpSignal.symbol}`)
      : firstCardRef.current;
    if (target) {
      // "auto" (not "smooth") -- deliberate: this fires right after the
      // debate data finishes loading, and an in-flight smooth-scroll can get
      // dropped by a render that happens mid-animation. An instant jump is
      // more reliable than a nicer-looking one that sometimes doesn't land.
      target.scrollIntoView({ behavior: "auto", block: "start" });
    }
  }, [jumpSignal, loading, data]);

  if (loading) {
    return <div className="empty-state">Loading…</div>;
  }
  if (error) {
    return (
      <div className="empty-state">
        <div className="empty-state-icon">⚠</div>
        <p className="empty-state-line">Could not load the debate.</p>
        <p className="empty-state-sub">{error}</p>
      </div>
    );
  }
  if (!data || !data.available || !data.symbols || data.symbols.length === 0) {
    return (
      <div className="empty-state">
        <PushSymbolBox date={date} onPushed={() => setReloadTick((t) => t + 1)} />
        <div className="empty-state-icon">◌</div>
        <p className="empty-state-line">No debate for this date.</p>
        <p className="empty-state-sub">Shortlist was empty or the debate stage didn't run.</p>
      </div>
    );
  }

  const anyTake = data.symbols.some((s) => s.chair && s.chair.verdict === "TAKE");
  // F4: user-pushed cards pinned to the top of the list; original chair-rank
  // order preserved within each group (stable sort).
  const orderedSymbols = [...data.symbols].sort((a, b) => {
    const aPushed = a.source === "user_pushed" ? 0 : 1;
    const bPushed = b.source === "user_pushed" ? 0 : 1;
    return aPushed - bPushed;
  });

  return (
    <div>
      <PushSymbolBox date={date} onPushed={() => setReloadTick((t) => t + 1)} />
      {/* T4: verdict-first summary lead line, above the funnel/cards. */}
      {data.verdict_summary && data.verdict_summary.headline && (
        <p className="lead-line">{data.verdict_summary.headline}</p>
      )}
      <FunnelPanel funnel={data.funnel} />
      {!anyTake && <ZeroTakeState symbols={data.symbols} call={card && card.tonights_call} onOpenChart={setChartSymbol} />}
      {orderedSymbols.map((sym, idx) => (
        <div key={sym.symbol} ref={idx === 0 ? firstCardRef : null}>
          <SymbolCard date={date} sym={sym} onOpenChart={setChartSymbol} onOpenTradePlan={onOpenTradePlan} />
        </div>
      ))}
      <ChartDrawer symbol={chartSymbol} date={date} onClose={() => setChartSymbol(null)} />
    </div>
  );
}

// Chartink screener + push-to-debate amendment (2026-07-11 ~09:30): "can't
// we have a screener option like Chartink.. from which we can push the
// stock to the debate panel to the llms? on top of whatever it itself
// screens". Minimal hook for tonight — full screener UI lands with V4's
// SCANNERS tab; this box just lets a symbol be pushed from anywhere on the
// DEBATE tab.
function PushSymbolBox({ date, onPushed }) {
  const [symbol, setSymbol] = useState("");
  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState(null);

  const submit = async (e) => {
    e.preventDefault();
    const sym = symbol.trim().toUpperCase();
    if (!sym || busy) return;
    setBusy(true);
    setToast(null);
    try {
      const result = await pushSymbolToDebate(sym, date);
      if (result.status === "ok" || result.status === "partial") {
        setToast({ ok: true, text: `${sym} pushed to debate — ${result.verdicts || 0} verdict(s) landed.` });
        setSymbol("");
        if (onPushed) onPushed();
      } else {
        setToast({ ok: false, text: `${sym}: ${result.detail || result.status}` });
      }
    } catch (err) {
      setToast({ ok: false, text: String(err) });
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="push-symbol-box">
      <form onSubmit={submit} className="push-symbol-form">
        <input
          type="text"
          value={symbol}
          onChange={(e) => setSymbol(e.target.value)}
          placeholder="Push a symbol to the LLMs (e.g. TANLA)"
          className="push-symbol-input mono"
          disabled={busy}
        />
        <button type="submit" className="push-symbol-button" disabled={busy || !symbol.trim()}>
          {busy ? "Debating…" : "PUSH TO DEBATE"}
        </button>
      </form>
      {toast && (
        <p className={"push-symbol-toast" + (toast.ok ? " ok" : " err")}>{toast.text}</p>
      )}
    </div>
  );
}
