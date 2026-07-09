import React, { useEffect, useState } from "react";
import { fetchDebate, chartUrl } from "./api.js";

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
            />
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
          />
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
      <p className="caption-b">[B] everything the desk refused before the models even argued</p>
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
          CHAIR: {chair ? chair.verdict : "—"}
        </span>
      </div>

      <GateDotsRow gates={sym.gates} />

      <div className="debate-card-body">
        <div className="conviction-row">
          <span className="overline">Conviction</span>
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
              spread {spread}
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
            <p className="panel-title small-caps">Bull</p>
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
            <p className="panel-title small-caps">Bear</p>
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
          <p className="panel-title small-caps">Vision strip</p>
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
                SIZER {sym.sizer.multiplier ?? "—"}x → final qty {sym.sizer.final_qty ?? "—"}
              </p>
              <SizerBar multiplier={sym.sizer.multiplier} />
              <p className="sizer-callout-reason">{sym.sizer.reasoning || "—"}</p>
            </div>
          )}
        </div>

        <div className="debate-footer">
          {sym.base_rate ? (
            <span className="mono">
              base rate {lensTag}: sys n=
              {sym.base_rate.system ? sym.base_rate.system.n : "—"}
              {sym.base_rate.system
                ? ` hit ${round((sym.base_rate.system.hit_rate || 0) * 100, 0)}%`
                : ""}
            </span>
          ) : (
            <span className="mono">base rate — n/a</span>
          )}
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
        struck.
      </p>
      {struck.map((s) => (
        <p key={s.symbol} className="mono struck-line">
          {s.symbol} — chair struck: "{s.chair ? s.chair.reasoning : "—"}"
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
