import React, { useEffect, useState } from "react";
import { fetchDebate, chartUrl } from "./api.js";
import { Term } from "./Glossary.jsx";

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
  if (multiplier < 0.75) return `Sizer ${multiplier}x - cut below base size because risk quality is weak.`;
  if (multiplier > 1.05) return `Sizer ${multiplier}x - above base size because the risk read is stronger.`;
  return `Sizer ${multiplier}x - close to base size.`;
}

function funnelRead(funnel, drops) {
  const universe = funnel.universe ?? "-";
  const shortlist = funnel.shortlist ?? "-";
  const debated = funnel.debated ?? "-";
  if (drops) return `${universe} names entered, ${shortlist} survived gates, ${debated} were debated; biggest refusals: ${drops}.`;
  return `${universe} names entered, ${shortlist} survived gates, ${debated} were debated.`;
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
      ML: P(up 10d)={round(ml.p_up_10d, 2)} [EXPERIMENTAL] drivers: {drivers}
    </span>
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
  return (
    <div className="panel funnel-panel">
      <p className="panel-title small-caps">The gate</p>
      <div className="funnel-stages mono">
        <span>
          <span className="funnel-stage-value">{funnel.universe ?? "—"}</span>
          <span className="funnel-stage-label">Universe</span>
        </span>
        <span className="funnel-arrow">─▶</span>
        <span>
          <span className="funnel-stage-value">{funnel.screeners ?? "—"}</span>
          <span className="funnel-stage-label">Screeners</span>
        </span>
        <span className="funnel-arrow">─▶</span>
        <span>
          <span className="funnel-stage-value">{funnel.gates ?? "—"}</span>
          <span className="funnel-stage-label">Gates</span>
        </span>
        <span className="funnel-arrow">─▶</span>
        <span>
          <span className="funnel-stage-value">{funnel.shortlist ?? "—"}</span>
          <span className="funnel-stage-label">Shortlist</span>
        </span>
        <span className="funnel-arrow">─▶</span>
        <span>
          <span className="funnel-stage-value">{funnel.debated ?? "—"}</span>
          <span className="funnel-stage-label">Debated</span>
        </span>
      </div>
      {drops && <p className="funnel-drops mono">drops: {drops}</p>}
      <p className="caption-b">[B] {funnelRead(funnel, drops)}</p>
    </div>
  );
}

function SymbolCard({ date, sym }) {
  const chair = sym.chair;
  const spread = chair && chair.conviction_spread;
  const disagreement = chair && chair.disagreement;
  const lensTag = (sym.family || "unknown").replace(/[/_]/g, " ").toUpperCase();

  return (
    <div className="panel debate-card">
      <div className="debate-card-header">
        <span className="debate-symbol">{sym.symbol}</span>
        <span className="debate-lens mono">{lensTag}</span>
        <span className={"debate-chair-verdict mono " + (chair && chair.verdict === "TAKE" ? "take" : "skip")}>
          <Term k="chair">CHAIR</Term>:{" "}
          {chair && verdictTerm(chair.verdict) ? <Term k={verdictTerm(chair.verdict)}>{chair.verdict}</Term> : chair ? chair.verdict : "—"}
        </span>
      </div>

      <GateDotsRow gates={sym.gates} />

      <div className="debate-card-body">
        <div className="conviction-row">
          <span className="overline">
            <Term k="conviction">Conviction</Term>
          </span>
          {sym.models.map((m) => (
            <span key={m.agent} className="conviction-item">
              <span className="agent-chip mono" data-agent={agentKey(m.agent)} title={m.agent}>
                {m.agent}
              </span>
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

        <div className="bull-bear-columns">
          <div className="bull-column">
            <p className="panel-title small-caps">
              <Term k="bull">Bull</Term>
            </p>
            {sym.models.map((m) => (
              <p key={m.agent} className="case-line">
                <span className="agent-chip mono" data-agent={agentKey(m.agent)} title={m.agent}>
                  {m.agent}
                </span>
                : {m.bull_case || "—"}
              </p>
            ))}
          </div>
          <div className="bear-column">
            <p className="panel-title small-caps">
              <Term k="bear">Bear</Term>
            </p>
            {sym.models.map((m) => (
              <p key={m.agent} className="case-line">
                <span className="agent-chip mono" data-agent={agentKey(m.agent)} title={m.agent}>
                  {m.agent}
                </span>
                : {m.bear_case || "—"}
              </p>
            ))}
          </div>
        </div>

        <div className="vision-strip">
          <p className="panel-title small-caps">
            <Term k="vision-strip">Vision strip</Term>
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

        <div className="plan-block">
          <p className="panel-title small-caps">
            Plan <span className="math-engine-label mono">[math: engine]</span>
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
                <span className="stat-tile-label">Base qty</span>
                <span className="stat-tile-value mono">{sym.plan.suggested_qty ?? "—"}</span>
              </div>
            </div>
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
              <p className="sizer-callout-reason">{sym.sizer.reasoning || "—"}</p>
              <p className="caption-b">[B] {sizerRead(sym.sizer.multiplier)}</p>
            </div>
          )}
        </div>

        <div className="debate-footer">
          <BaseRateChip baseRate={sym.base_rate} family={sym.family} lensTag={lensTag} />
          <MlChip ml={sym.ml} />
          {sym.track_record.map((t) => (
            <span key={t.agent} className="mono track-chip">
              {t.agent} on {sym.family}: {t.n ? `${round((t.hit_rate || 0) * t.n, 0)}/${t.n}` : "n/a"}
              {t.thin ? " (thin)" : ""}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}

function ZeroTakeState({ symbols }) {
  const struck = symbols.filter((s) => s.chair && s.chair.verdict !== "TAKE");
  return (
    <div className="panel zero-take-panel">
      <p className="panel-title small-caps">The desk sat out</p>
      <p>
        The desk took nothing on this date. {symbols.length} name{symbols.length === 1 ? "" : "s"} debated, all
        <Term k="struck">struck</Term>.
      </p>
      {struck.map((s) => (
        <p key={s.symbol} className="mono struck-line">
          {s.symbol} — <Term k="chair">chair</Term> <Term k="struck">struck</Term>: "{s.chair ? s.chair.reasoning : "—"}"
        </p>
      ))}
    </div>
  );
}

export default function DebateTab({ date }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

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
  }, [date]);

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
        <div className="empty-state-icon">◌</div>
        <p className="empty-state-line">No debate for this date.</p>
        <p className="empty-state-sub">Shortlist was empty or the debate stage didn't run.</p>
      </div>
    );
  }

  const anyTake = data.symbols.some((s) => s.chair && s.chair.verdict === "TAKE");

  return (
    <div>
      <FunnelPanel funnel={data.funnel} />
      {!anyTake && <ZeroTakeState symbols={data.symbols} />}
      {data.symbols.map((sym) => (
        <SymbolCard key={sym.symbol} date={date} sym={sym} />
      ))}
    </div>
  );
}
