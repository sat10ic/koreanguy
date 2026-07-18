import React, { useEffect, useRef, useState } from "react";
import { fetchDebate, chartUrl, pushSymbolToDebate } from "./api.js";
import ChartDrawer from "./ChartDrawer.jsx";
import DebateAlphaCard from "./DebateAlphaCard.jsx";
import {
  SectionLabel,
  Panel,
  FunnelPanel,
  LaneCard,
  CallBanner,
  VoteBar,
  MLBar,
  Sparkline,
  ReturnCell,
  VerdictChip,
  GatePassTag,
  GateCellGrid,
  SizerStamp,
  StruckNote,
  LensLane,
  DebateLivePanel,
  StatusBadge,
  CrossBadges,
  useListMembership,
  ListRelationshipLegend,
} from "./components/v5/index.js";
import { useLiveWork } from "./livework/useJobStream.js";
import { useDensity } from "./DensityContext.jsx";
import { formatDisplayFloat, newHighsLowsCopy } from "./presentation.js";
import "./DebateTab.v5.css";

// ------------------------------------------------------------------
// pure derivations (real payload only -- no synthetic fill anywhere)
// ------------------------------------------------------------------

// Coarse setup family -> the three round-4 mechanism lanes.
function laneFamily(family) {
  const f = (family || "").toLowerCase();
  if (f.includes("momentum")) return "momentum";
  if (f.includes("ipo") || f.includes("catalyst")) return "ipobase";
  return "basepattern";
}

const LANE_META = {
  momentum: { name: "Momentum", sub: "Velocity entries — Strong Start / breakout continuation" },
  basepattern: { name: "Base / Pattern", sub: "Magnitude entries — pullback / consolidation break" },
  ipobase: { name: "IPO Base / Catalyst", sub: "Fresh-listing / catalyst structure" },
};

function symStatus(sym) {
  return sym.plan ? "gatepass" : "nearmiss";
}

function symIsLive(sym) {
  const q = sym.sizer && sym.sizer.final_qty;
  return q !== null && q !== undefined && q > 0;
}

function hmmState(sym) {
  const s = sym.stock_hmm;
  if (!s || s.available === false || !s.state) return "NA";
  return s.state;
}

function voteCounts(sym) {
  let take = 0;
  let skip = 0;
  (sym.models || []).forEach((m) => {
    if (m.verdict === "TAKE") take += 1;
    else if (m.verdict === "SKIP") skip += 1;
  });
  return { take, skip };
}

function round(n, digits = 1) {
  if (n === null || n === undefined) return "—";
  const f = Math.pow(10, digits);
  return Math.round(n * f) / f;
}

function InfoDot({ label }) {
  return <span className="v5-info-dot" tabIndex={0} role="note" aria-label={label} title={label}>ⓘ</span>;
}

// GROWW deep-dive gate cells: state derived from real gate rows/evidence.
function gateCells(sym) {
  return (sym.gates || []).map((g) => {
    const ev = g.evidence || {};
    let state = g.pass ? "PASS" : "FAIL";
    let objection = null;
    const note = ev.note ? String(ev.note) : "";
    if (g.pass && /waiv/i.test(note)) {
      state = "WAIVED";
      objection = note.replace(/^[^:]*:\s*/, "");
    }
    if (g.gate === "participation" && ev.delivery_z !== undefined && ev.delivery_z !== null) {
      objection = `delivery z ${ev.delivery_z >= 0 ? "+" : ""}${ev.delivery_z}`;
    }
    if (g.gate === "risk" && ev.stop_pct !== undefined && ev.stop_pct !== null) {
      state = g.pass ? "PASS (raw)" : "FAIL";
      objection = `stop ${ev.stop_pct}% (sizer cap 5.0%)`;
    }
    if (!g.pass && g.reason) objection = g.reason;
    return { name: g.gate, state, objection };
  });
}

// ------------------------------------------------------------------
// context row: regime + breadth + funnel
// ------------------------------------------------------------------

function RegimeRing({ confidence }) {
  const pct = confidence === null || confidence === undefined ? null : Math.max(0, Math.min(100, confidence));
  const R = 38;
  const C = 2 * Math.PI * R;
  const offset = pct === null ? C : C * (1 - pct / 100);
  return (
    <div className="v5-regime-ring">
      <svg viewBox="0 0 92 92" aria-hidden="true">
        <circle cx="46" cy="46" r={R} fill="none" stroke="var(--v5-line)" strokeWidth="8" />
        {pct !== null && (
          <circle
            cx="46"
            cy="46"
            r={R}
            fill="none"
            stroke="var(--v5-amber-bright)"
            strokeWidth="8"
            strokeDasharray={C.toFixed(2)}
            strokeDashoffset={offset.toFixed(2)}
            strokeLinecap="round"
          />
        )}
      </svg>
      <div className="v5-rv">
        <span className="v5-rn mono-num">{pct === null ? "—" : `${Math.round(pct)}%`}</span>
        <span className="v5-ru">confidence</span>
      </div>
    </div>
  );
}

function ContextRow({ regime, funnel }) {
  const r = regime || {};
  const ev = r.four_phase_evidence || {};
  const ratios = r.ratios || {};
  const funnelStages = funnel
    ? [
        { label: "universe scanned", n: funnel.universe },
        { label: "passed screeners", n: funnel.screeners },
        { label: "passed hard gates", n: funnel.gates },
        { label: "shortlist pool", n: funnel.shortlist },
        { label: "debated by panel", n: funnel.debated },
      ]
    : [];
  const drops = funnel && funnel.by_gate
    ? Object.entries(funnel.by_gate)
        .sort((a, b) => b[1] - a[1])
        .map(([gate, n]) => ({ label: gate, n }))
    : [];

  const dayColor = r.mbi_day_color;
  const ratioCells = [
    { k: "R10", v: ratios.r10 },
    { k: "R20", v: ratios.r20 },
    { k: "R50", v: ratios.r50 },
    { k: "R4.5", v: ratios.r4p5 },
  ];

  return (
    <div className="v5-ctx-grid">
      <Panel title="Regime · Four-Phase" cite={r.four_phase ? "TradeTM C1" : undefined}>
        <div className="v5-regime-hero">
          <RegimeRing confidence={r.four_phase_confidence} />
          <div className="v5-regime-txt">
            <div className="v5-mode">{r.four_phase || r.mode || "—"}</div>
            <div className="v5-phase">
              regime <b>{r.mode || "—"}</b>
              {r.age_days !== null && r.age_days !== undefined ? ` · day ${r.age_days}` : ""}
            </div>
            <div className="v5-conf">
              {ev.level_pct_above_ma !== undefined ? <>
                {`% above MA ${round(ev.level_pct_above_ma)} · ${ev.lookback_days || 5}d ROC ${round(ev.roc_pct_above_ma)}pp · ${newHighsLowsCopy(ev.nhnl_trend, ev.nhnl_source)}`}
                {" "}<InfoDot label="New highs and lows are not ingested; this proxy compares the number of stocks up 4% with the number down 4%." />
              </> : "phase evidence unavailable"}
            </div>
          </div>
        </div>
        {r.hmm_caption && (
          <div className="v5-hmm-line">
            <span className="v5-lbl">HMM:</span>{" "}
            {/warming|insufficient/i.test(r.hmm_caption) ? (
              <StatusBadge status="WARMING" why={r.hmm_caption.replace(/^HMM confirm:\s*/i, "")} />
            ) : (
              r.hmm_caption.replace(/^HMM confirm:\s*/i, "")
            )}
          </div>
        )}
        <div className="v5-mbi-row">
          <div className={"v5-mbi-chip" + (dayColor === "GREEN" ? " v5-day-green" : "")}>
            <span className="v5-k">MBI Day</span>
            <span className="v5-v">{dayColor || "—"}</span>
          </div>
          <div className="v5-mbi-chip">
            <span className="v5-k">Choppy Brake</span>
            <span className="v5-v">{r.choppy_brake ? (r.choppy_brake.active ? "active" : "inactive") : "—"}</span>
          </div>
          <div className="v5-mbi-chip">
            <span className="v5-k">Regime Age</span>
            <span className="v5-v">{r.age_days !== null && r.age_days !== undefined ? `${r.age_days}d` : "—"}</span>
          </div>
        </div>
      </Panel>

      <Panel title="Breadth Ratios" cite="up4.5 : down4.5">
        <div className="v5-breadth-grid">
          {ratioCells.map((c) => (
            <div className="v5-breadth-cell" key={c.k}>
              <span className="v5-lbl">{c.k}</span>
              <span className="v5-val mono-num">{c.v === null || c.v === undefined ? "—" : round(c.v, 2)}</span>
            </div>
          ))}
        </div>
        <div className="v5-breadth-foot">
          {Object.keys(ratios).length
            ? "Breadth ratios from the nightly universe-breadth ingest. High ratios say buyers are present; the four-phase read is the follow-through cross-check."
            : "No breadth ratios ingested for this date."}
        </div>
      </Panel>

      <Panel title="Gate Funnel" cite="universe → debated">
        <FunnelPanel stages={funnelStages} drops={drops} />
        {funnel && funnel.tradable_summary && (
          <div className="v5-breadth-foot">{funnel.tradable_summary}</div>
        )}
      </Panel>
    </div>
  );
}

// ------------------------------------------------------------------
// governor / heat / coverage row
// ------------------------------------------------------------------

function CouncilPipelineNote({ card, isExpert, canRetry, retryBusy, retryError, onRetry }) {
  const failed = card?.council_status?.state === "run_failed";
  const errors = card?.errors || [];
  if (!failed && errors.length === 0) return <span>0 pipeline errors.</span>;
  return <div className="v5-pipeline-notes">
    <p>{failed ? card.council_status.pipeline_message : `${errors.length} pipeline issue${errors.length === 1 ? "" : "s"} logged.`}</p>
    {failed && (
      <button type="button" className="v5-text-action" disabled={!canRetry || retryBusy} onClick={onRetry}>
        {retryBusy ? "retrying…" : "Retry council"}
      </button>
    )}
    {failed && !canRetry && <small>Open ACTIVITY to retry the failed council stage.</small>}
    {retryError && <small role="alert">{retryError}</small>}
    {isExpert && errors.length > 0 && (
      <details>
        <summary>Expert: raw pipeline details</summary>
        <ul className="v5-pipeline-notes-list">
          {errors.map((error, index) => <li key={index}><pre>{JSON.stringify(error, null, 2)}</pre></li>)}
        </ul>
      </details>
    )}
  </div>;
}

function GovernorRow({ card, debate, isExpert, canRetryCouncil, retryBusy, retryError, onRetryCouncil }) {
  const gov = (card && card.governor) || {};
  const heat = (card && card.heat) || {};
  const heatPct = heat.open_risk_pct;
  const capPct = heat.cap_pct;
  const heatWidth = heatPct !== undefined && heatPct !== null && capPct
    ? Math.max(0, Math.min(100, (heatPct / capPct) * 100))
    : 0;

  // coverage: real counts from the debate payload
  const symbols = (debate && debate.symbols) || [];
  const modelSet = new Set();
  let verdictCount = 0;
  symbols.forEach((s) => {
    (s.models || []).forEach((m) => {
      if (m.agent) modelSet.add(m.agent);
      verdictCount += 1;
    });
  });
  const cardCount = symbols.length;

  return (
    <div className="v5-ctx-grid v5-gov-grid">
      <Panel title="Governor" cite={gov.profile ? `${gov.profile} profile` : undefined}>
        <div className="v5-gov-rows">
          <div className="v5-gov-row">
            <span className="v5-k">Max cards / new pos</span>
            <span className="v5-v">{gov.max_cards ?? "—"} / {gov.max_new_positions ?? "—"}</span>
          </div>
          <div className="v5-gov-row">
            <span className="v5-k">Max open positions</span>
            <span className="v5-v">{gov.max_open_positions ?? "—"}</span>
          </div>
          <div className="v5-gov-row">
            <span className="v5-k">Open risk cap</span>
            <span className="v5-v v5-amber">{formatDisplayFloat(gov.open_risk_cap_pct, { digits: 2, unit: "%" })}</span>
          </div>
          <div className="v5-gov-row">
            <span className="v5-k">Risk band</span>
            <span className="v5-v">
              {gov.risk_band ? `${formatDisplayFloat(gov.risk_band.base_pct, { digits: 2, unit: "%" })} – ${formatDisplayFloat(gov.risk_band.hard_max_pct, { digits: 2, unit: "%" })}` : "—"}
            </span>
          </div>
          <div className="v5-gov-row">
            <span className="v5-k">Push allowed</span>
            <span className="v5-v v5-cyan">{gov.push_allowed === undefined ? "—" : gov.push_allowed ? "yes" : "no"}</span>
          </div>
        </div>
        {gov.allowed_families && gov.allowed_families.length > 0 && (
          <div className="v5-gov-fam">
            {gov.allowed_families.map((f) => (
              <span key={f}>{f}</span>
            ))}
          </div>
        )}
      </Panel>

      <Panel title="Portfolio Heat" cite="open risk">
        <div className="v5-heat-big mono-num">
          {formatDisplayFloat(heatPct, { digits: 1, unit: "%" })}
          <small> used</small>
        </div>
        <div className="v5-heat-track">
          <div className="v5-heat-fill" style={{ width: `${heatWidth}%` }} />
        </div>
        <div className="v5-heat-legend">
          <span>0%</span>
          <span>cap {formatDisplayFloat(capPct, { digits: 2, unit: "%" })}</span>
        </div>
        <div className="v5-breadth-foot">
          Deterministic risk owns these numbers; the desk never recomputes stop/qty/heat.
        </div>
      </Panel>

      <Panel title="Pipeline · Panel Coverage" cite={`${modelSet.size} models · ${verdictCount} verdicts`}>
        <div className="v5-coverage-note">
          <b>{cardCount} cards</b> reached full debate → <b>{modelSet.size}</b> models fired,{" "}
          <b className="v5-cyan">{verdictCount} verdicts</b> parsed.
          <CouncilPipelineNote card={card} isExpert={isExpert} canRetry={canRetryCouncil} retryBusy={retryBusy} retryError={retryError} onRetry={onRetryCouncil} />
        </div>
      </Panel>
    </div>
  );
}

// ------------------------------------------------------------------
// lanes
// ------------------------------------------------------------------

function LanesRow({ symbols }) {
  const buckets = { momentum: [], basepattern: [], ipobase: [] };
  symbols.forEach((s) => {
    buckets[laneFamily(s.family)].push(s);
  });
  return (
    <div className="v5-lanes-grid">
      {["momentum", "basepattern", "ipobase"].map((fam) => {
        const list = buckets[fam];
        const passers = list.filter((s) => symStatus(s) === "gatepass");
        const shown = Math.min(list.length, 6);
        const summary =
          list.length === 0 ? (
            "no names in this lane tonight"
          ) : (
            <>
              {list.slice(0, 6).map((s, i) => (
                <span key={s.symbol}>
                  <b>{s.symbol}</b>
                  {s.chair && s.chair.struck ? " struck" : symStatus(s) === "gatepass" ? " gate-pass" : ""}
                  {i < shown - 1 ? " · " : ""}
                </span>
              ))}
              {list.length > 6 ? ` +${list.length - 6} more` : ""}
            </>
          );
        return (
          <LaneCard
            key={fam}
            family={fam}
            name={LANE_META[fam].name}
            count={list.length}
            sub={`${LANE_META[fam].sub}${passers.length ? ` · ${passers.length} gate-pass` : ""}`}
            summary={summary}
          />
        );
      })}
    </div>
  );
}

// ------------------------------------------------------------------
// tonight's call
// ------------------------------------------------------------------

const STANCE_ICON = {
  CAUTION: "⚠",
  ACT_PER_PLAN: "✓",
  SIT_OUT: "○",
  STAND_ASIDE: "✋",
};

function TonightsCall({ call, councilStatus }) {
  if (!call || (!call.headline && !(call.what_to_do && call.what_to_do.length))) return null;
  const bullets = (call.what_to_do || []).map((text) => {
    const m = text.match(/\[([^\]]+)\]\s*$/);
    if (m) {
      return { text: text.slice(0, m.index).trim(), cite: m[1] };
    }
    return { text };
  });
  return (
    <CallBanner
      stance={(call.stance || "CAUTION").replace(/_/g, " ")}
      icon={STANCE_ICON[call.stance] || "⚠"}
      headline={councilStatus?.state === "run_failed" ? councilStatus.message : call.headline}
      bullets={bullets}
    />
  );
}

// ------------------------------------------------------------------
// the debated-names table (17 columns)
// ------------------------------------------------------------------

const TABLE_COLS = [
  "Rank", "Symbol", "Family", "30d Price", "EOD", "3D", "7D", "1M", "3M",
  "ADR20", "Off 65d-Low", "Purple Dots", "Stock HMM", "ML P(up 10d)",
  "Model Votes", "Chair", "Status",
];

function DebateRow({ sym, isHero, onJumpToHero, onOpenChart, membership, onNavigate }) {
  const status = symStatus(sym);
  const live = symIsLive(sym);
  const paper = status === "gatepass" && !live;
  const metrics = sym.scan_metrics || {};
  const returns = sym.returns || {};
  const votes = voteCounts(sym);
  const hmm = hmmState(sym);
  const chair = sym.chair;
  const marketData = sym.market_data || {};
  const note = status === "gatepass"
    ? (sym.objections && sym.objections[0] ? sym.objections[0].reason : (chair && chair.struck ? chair.strike_reason : null))
    : (sym.near_miss ? `${sym.near_miss.failed_gate}: ${sym.near_miss.reason}` : null);

  const rowClass =
    (status === "gatepass" ? "v5-gatepass " : "") + (isHero ? "v5-hero-row" : "");

  const heroProps = isHero
    ? {
        role: "button",
        tabIndex: 0,
        "aria-label": `${sym.symbol} — open deep-dive`,
        onClick: onJumpToHero,
        onKeyDown: (e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            onJumpToHero();
          }
        },
      }
    : {};

  return (
    <tr id={`row-${sym.symbol}`} className={rowClass.trim()} {...heroProps}>
      <td className="v5-num mono-num">{chair && chair.rank !== null && chair.rank !== undefined ? chair.rank : "—"}</td>
      <td>
        <div className="v5-sym-cell">
          <button
            type="button"
            className="v5-sym-name"
            style={{ background: "none", border: "none", padding: 0, cursor: "pointer", color: "inherit" }}
            onClick={(e) => {
              e.stopPropagation();
              onOpenChart(sym.symbol);
            }}
            title={`Open ${sym.symbol} chart`}
          >
            {sym.symbol}
          </button>
          {marketData.price !== null && marketData.price !== undefined && (
            <span className={`v5-market-price v5-${String(marketData.state || "empty").toLowerCase()}`}>
              ₹{Number(marketData.price).toLocaleString("en-IN", { maximumFractionDigits: 2 })}
              {marketData.state ? ` · ${marketData.state.replace("_", " ")}` : ""}
            </span>
          )}
          <div className="v5-fam-tag">{sym.family_label || sym.family || ""}</div>
          <span className={"v5-src-tag v5-" + (sym.source || "scanner")}>
            {sym.source === "user_pushed" ? "pushed" : "scan"}
          </span>
          <CrossBadges symbol={sym.symbol} membership={membership} active="DEBATE" onNavigate={onNavigate} />
        </div>
      </td>
      <td><span style={{ fontSize: "10.5px", color: "var(--v5-ink-dim)" }}>{sym.family || "—"}</span></td>
      <td><Sparkline series={sym.spark} width={90} height={26} /></td>
      <td><ReturnCell value={returns.eod} /></td>
      <td><ReturnCell value={returns.d3} /></td>
      <td><ReturnCell value={returns.d7} /></td>
      <td><ReturnCell value={returns.m1} /></td>
      <td><ReturnCell value={returns.m3} /></td>
      <td className="v5-num mono-num">{metrics.adr20 !== null && metrics.adr20 !== undefined ? `${metrics.adr20.toFixed(2)}%` : "—"}</td>
      <td className="v5-num mono-num">
        {metrics.pct_up_from_65d_low !== null && metrics.pct_up_from_65d_low !== undefined
          ? `+${metrics.pct_up_from_65d_low.toFixed(1)}%`
          : "—"}
      </td>
      <td className="v5-num mono-num">{metrics.purple_dot_count_60d !== null && metrics.purple_dot_count_60d !== undefined ? metrics.purple_dot_count_60d : "—"}</td>
      <td><span className={"v5-hmm-chip v5-" + hmm}>{hmm === "NA" ? "n/a" : hmm}</span></td>
      <td><MLBar pUp={sym.ml ? sym.ml.p_up_10d : null} /></td>
      <td><VoteBar take={votes.take} skip={votes.skip} /></td>
      <td>
        {chair && chair.verdict ? (
          <VerdictChip verdict={chair.verdict} struck={!!chair.struck} conviction={chair.conviction} />
        ) : (
          <span style={{ color: "var(--v5-ink-mute)", fontFamily: "var(--v5-mono)", fontSize: "10px" }}>
            no chair (1-model)
          </span>
        )}
      </td>
      <td><GatePassTag status={status} paper={paper} note={note} /></td>
    </tr>
  );
}

function DebateTable({ symbols, heroSymbols, onJumpToHero, onOpenChart, membership, onNavigate }) {
  // gate-passed names first (chair rank), then near-misses (chair rank).
  const ordered = [...symbols].sort((a, b) => {
    const pa = symStatus(a) === "gatepass" ? 0 : 1;
    const pb = symStatus(b) === "gatepass" ? 0 : 1;
    if (pa !== pb) return pa - pb;
    const ra = (a.chair && a.chair.rank) ?? 9999;
    const rb = (b.chair && b.chair.rank) ?? 9999;
    return ra - rb;
  });
  return (
    <div className="v5-table-wrap">
      <table className="v5-debate">
        <thead>
          <tr>
            {TABLE_COLS.map((c) => (
              <th key={c} scope="col">{c}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {ordered.map((sym) => (
            <DebateRow
              key={sym.symbol}
              sym={sym}
              isHero={heroSymbols.includes(sym.symbol)}
              onJumpToHero={() => onJumpToHero(sym.symbol)}
              onOpenChart={onOpenChart}
              membership={membership}
              onNavigate={onNavigate}
            />
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ------------------------------------------------------------------
// GROWW-style deep-dive for a gate-passed symbol
// ------------------------------------------------------------------

function ChartImg({ date, symbol }) {
  const [failed, setFailed] = useState(false);
  if (failed) {
    return <div className="v5-chart-missing mono-num">[ {symbol} daily chart unavailable ]</div>;
  }
  return (
    <img
      className="v5-groww-chart"
      src={chartUrl(date, symbol, "daily")}
      alt={`${symbol} daily chart`}
      onError={() => setFailed(true)}
    />
  );
}

function DeepDive({ date, sym, deepRef, onOpenTradePlan }) {
  const [showExpert, setShowExpert] = React.useState(false);
  const status = symStatus(sym);
  if (status !== "gatepass") return null;
  const chair = sym.chair || {};
  const plan = sym.plan || {};
  const sizer = sym.sizer;
  const live = symIsLive(sym);
  const votes = voteCounts(sym);
  const stopPct =
    plan.entry && plan.stop ? ((plan.entry - plan.stop) / plan.entry) * 100 : null;
  const priceSub = [];
  if (sym.delivery && sym.delivery.flag) priceSub.push(`delivery ${sym.delivery.flag}`);
  if (chair.pre_strike_verdict) priceSub.push(`council ${votes.take}T/${votes.skip}S`);

  const obs = sym.vision && sym.vision.observer_payload ? sym.vision.observer_payload : {};

  return (
    <div className="v5-groww-block" ref={deepRef} id={`deepdive-${sym.symbol}`}>
      <div className="v5-groww-head">
        <div className="v5-groww-title">
          <div className="v5-name">{sym.symbol}</div>
          <div className="v5-fam">{sym.family_label || sym.family || ""}</div>
          <div className="v5-rank">
            {chair.rank !== null && chair.rank !== undefined ? `debate rank ${chair.rank}` : ""}
            {sym.source ? ` · ${sym.source === "user_pushed" ? "user-pushed" : "scanner-sourced"}` : ""}
          </div>
        </div>
        {sym.debate_cost_inr !== null && sym.debate_cost_inr !== undefined && (
          <div className="v5-debate-cost">Council cost · ₹{Number(sym.debate_cost_inr).toFixed(3)}</div>
        )}
        <div className="v5-groww-price">
          <div className="v5-p mono-num">{plan.entry !== undefined && plan.entry !== null ? `₹${round(plan.entry, 2)}` : "—"}</div>
          <div className="v5-c">{priceSub.length ? priceSub.join(" · ") : "entry level"}</div>
          <button type="button" className="v5-tradeplan-link" style={{marginRight: "10px"}} onClick={() => setShowExpert(!showExpert)}>
            {showExpert ? "BEGINNER VIEW" : "EXPERT VIEW"} &rarr;
          </button>
          {onOpenTradePlan && (
            <button
              type="button"
              className="v5-tradeplan-link"
              onClick={() => onOpenTradePlan(sym.symbol)}
            >
              TRADE PLAN &rarr;
            </button>
          )}
        </div>
      </div>

      {!showExpert && (
        <div className="v5-groww-body v5-seq-layout">
          <div className="v5-seq-col">
            <div className="v5-ctx-title">WHAT I SEE</div>
            <ul className="v5-note-box">
              <li><b>Phase:</b> {obs.phase_and_sequence || "—"}</li>
              <li><b>S/D:</b> {obs.supply_demand_behavior || "—"}</li>
              <li><b>Base:</b> {obs.base_age_and_quality || "—"}</li>
              <li><b>Volume:</b> {obs.volume_behavior || "—"}</li>
              <li><b>Group:</b> {obs.stock_vs_group || "—"}</li>
            </ul>
          </div>
          <div className="v5-seq-col">
            <div className="v5-ctx-title">WHY IT MAY WORK</div>
            <ul className="v5-note-box">
              <li><b>Hypotheses:</b> {(obs.plausible_hypotheses || []).join("; ") || "—"}</li>
              <li><b>Confirming:</b> {obs.confirming_evidence || "—"}</li>
            </ul>
            <div className="v5-ctx-title" style={{marginTop: "12px"}}>WHAT MUST HAPPEN NEXT</div>
            <div className="v5-note-box">{obs.what_must_happen_next || "—"}</div>
          </div>
          <div className="v5-seq-col">
            <div className="v5-ctx-title">WHAT PROVES ME WRONG</div>
            <ul className="v5-note-box">
              <li><b>Contradiction:</b> {obs.strongest_contradiction || "—"}</li>
              <li><b>Invalidation:</b> {obs.invalidation_criteria || "—"}</li>
            </ul>
            <div className="v5-ctx-title" style={{marginTop: "12px"}}>PLAN / NO PLAN</div>
            <div className="v5-note-box">
              <VerdictChip verdict={chair.verdict} struck={!!chair.struck} conviction={chair.conviction} />
              <div className="v5-plan-row" style={{marginTop: "8px", fontSize: "11px"}}>
                <span>RR <b>{round(plan.rr, 2)}</b></span>
                <span>Stop <b className="v5-red">{stopPct !== null ? `${stopPct.toFixed(2)}%` : "—"}</b></span>
              </div>
            </div>
          </div>
        </div>
      )}

      {showExpert && (
        <div className="v5-groww-body">
          <div className="v5-groww-col">
            <div className="v5-ctx-title">Price · daily chart</div>
            <div style={{ marginTop: "8px" }}>
              <ChartImg date={date} symbol={sym.symbol} />
            </div>
            <div className="v5-plan-row">
              <span>RR <b>{round(plan.rr, 2)}</b></span>
              <span>Qty plan <b>{plan.suggested_qty ?? "—"}</b></span>
              <span>Stop <b className="v5-red">{stopPct !== null ? `${stopPct.toFixed(2)}%` : "—"}</b></span>
              <span>ADR20 <b>{sym.scan_metrics && sym.scan_metrics.adr20 !== null && sym.scan_metrics.adr20 !== undefined ? `${sym.scan_metrics.adr20.toFixed(2)}%` : "—"}</b></span>
            </div>
          </div>

          <div className="v5-groww-col">
            <div className="v5-ctx-title">Deterministic gates</div>
            <GateCellGrid gates={gateCells(sym)} />
            {sym.vision && (
              <>
                <div className="v5-ctx-title" style={{ marginTop: "12px" }}>Observer payload</div>
                <div className="v5-note-box">
                  {JSON.stringify(obs).substring(0, 150)}...
                </div>
              </>
            )}
          </div>

          <div className="v5-groww-col">
            <div className="v5-ctx-title">{`${(sym.models || []).length}-model vote — ${votes.take} TAKE / ${votes.skip} SKIP`}</div>
            <div style={{ marginTop: "8px" }}>
              {(sym.models || []).map((m) => (
                <div className="v5-vote-panel-row" key={m.agent}>
                  <span className="v5-model-name">{m.agent}</span>
                  <VerdictChip verdict={m.verdict} conviction={m.conviction} />
                </div>
              ))}
            </div>
            {sym.objections && sym.objections.length > 0 && (
              <>
                <div className="v5-ctx-title" style={{ marginTop: "12px" }}>Objections</div>
                <div className="v5-note-box">
                  {sym.objections.map((o) => o.reason).join(" · ")}
                </div>
              </>
            )}
          </div>
        </div>
      )}

      {showExpert && <DebateAlphaCard symbol={sym.symbol} date={date} attached={sym.alpha_evidence} />}

      {chair.struck && (
        <div className="v5-strike-wrap">
          <StruckNote>
            <b>
              Chair struck the vote{chair.pre_strike_verdict ? ` (${chair.pre_strike_verdict} → SKIP` : " (→ SKIP"}
              {chair.conviction !== null && chair.conviction !== undefined ? `, conviction ${chair.conviction}` : ""}):
            </b>{" "}
            {chair.strike_reason || chair.reasoning || "risk strike"}
          </StruckNote>
        </div>
      )}

      {sizer && !live && (
        <div className="v5-sizer-wrap">
          <SizerStamp
            reason={
              (sizer.reasoning || "no reason recorded") +
              " — The chair, the models, and the setup all pointed TAKE; the sizer overrides all of them. Paper-trade / watch only, not a live buy."
            }
            multiplier={sizer.multiplier ?? 0}
            qty={sizer.final_qty ?? 0}
            rupeeRisk={sizer.final_qty === 0 ? 0 : "—"}
          />
        </div>
      )}
    </div>
  );
}

// ------------------------------------------------------------------
// lens lanes (real facts only)
// ------------------------------------------------------------------

function LensLanes({ symbols }) {
  const buckets = { momentum: [], basepattern: [], ipobase: [] };
  symbols.forEach((s) => buckets[laneFamily(s.family)].push(s));
  const total = symbols.length || 1;
  const lenses = [];
  const ipoPass = buckets.ipobase.filter((s) => symStatus(s) === "gatepass");
  if (buckets.ipobase.length) {
    lenses.push({
      label: "IPO Base / Catalyst lens",
      value: ipoPass.length ? ipoPass.map((s) => s.symbol).join(", ") : `0 / ${buckets.ipobase.length}`,
      pct: (ipoPass.length / total) * 100,
      desc: ipoPass.length
        ? "Fresh-listing / catalyst structure — the lane that produced tonight's gate-passes."
        : "Names present but none cleared every gate.",
    });
  }
  const momBlocked = buckets.momentum.filter((s) => symStatus(s) === "nearmiss");
  if (buckets.momentum.length) {
    lenses.push({
      label: "Momentum / regime gate",
      value: momBlocked.length ? `${momBlocked.length} blocked` : `${buckets.momentum.length} in lane`,
      pct: (momBlocked.length / total) * 100,
      desc: momBlocked.length
        ? `${momBlocked.map((s) => s.symbol).join(", ")} — momentum names blocked by regime / hard gates.`
        : "Momentum names present.",
    });
  }
  if (buckets.basepattern.length) {
    const split = buckets.basepattern.filter((s) => {
      const v = voteCounts(s);
      return v.take > 0 && v.skip > 0;
    });
    lenses.push({
      label: "Base / Pattern lens",
      value: `${buckets.basepattern.length} debated`,
      pct: (buckets.basepattern.length / total) * 100,
      desc: split.length
        ? `${split.map((s) => s.symbol).join(", ")} drew split council votes; the rest were clean SKIPs.`
        : "Pullback / consolidation names, mostly clean SKIP on trend-template / participation gates.",
    });
  }
  const struck = symbols.filter((s) => s.chair && s.chair.struck);
  lenses.push({
    label: "Chair strikes",
    value: struck.length ? `${struck.length} struck` : "0 struck",
    pct: (struck.length / total) * 100,
    desc: struck.length
      ? `${struck.map((s) => s.symbol).join(", ")} — cleared debate but struck on a stated risk ground.`
      : "No chair strikes tonight.",
  });
  return <LensLane lenses={lenses} />;
}

// ------------------------------------------------------------------
// foot stats + model ledger
// ------------------------------------------------------------------

function FootStats({ debate, card }) {
  const vs = debate.verdict_summary || {};
  const pool = debate.pool_summary || {};
  const live = vs.live_count ?? 0;
  const paper = vs.paper_only_count ?? 0;
  const near = vs.near_miss_count ?? 0;
  const regimeMode = debate.regime_mode || (card && card.regime && card.regime.mode);
  const dayColor = card && card.regime && card.regime.mbi_day_color;

  const stats = [
    { n: live, lbl: "Live Trades", cls: live === 0 ? "v5-zero" : "" },
    { n: paper, lbl: "Paper-Only", cls: paper > 0 ? "v5-amber" : "" },
    { n: near, lbl: "Near-Misses", cls: "" },
    { n: `${pool.pool_total ?? "—"}`, lbl: `Pool / ${pool.watchlist ?? "—"} Watchlist`, cls: "" },
    { n: pool.debate_card_count ?? debate.symbols.length, lbl: "Debated Tonight", cls: "" },
  ];

  // model ledger: real per-model verdict counts from the payload
  const modelCounts = {};
  debate.symbols.forEach((s) => {
    (s.models || []).forEach((m) => {
      if (!m.agent) return;
      modelCounts[m.agent] = (modelCounts[m.agent] || 0) + 1;
    });
  });
  const models = Object.entries(modelCounts).sort((a, b) => b[1] - a[1]);
  const modelStatuses = debate.model_statuses || [];

  return (
    <>
      <div className="v5-foot-grid">
        {stats.map((s) => (
          <div className="v5-foot-stat" key={s.lbl}>
            <div className={"v5-n " + s.cls}>{s.n}</div>
            <div className="v5-lbl">{s.lbl}</div>
          </div>
        ))}
      </div>
      <div className="v5-headline-strip">
        {vs.headline || (
          <>
            Regime <b>{regimeMode || "—"}</b>, day-color <b>{dayColor || "—"}</b>. {live} live · {paper} paper · {near} near-miss.
          </>
        )}
      </div>
      <div className="v5-ledger-footer">
        <div>
          <div className="v5-ctx-title" style={{ marginBottom: "8px" }}>Council · verdict ledger</div>
          <div className="v5-models-strip">
            {models.length ? (
              models.map(([agent, n]) => (
                <span className="v5-model-chip" key={agent}>
                  <b>{agent}</b> {n} verdict{n === 1 ? "" : "s"}
                </span>
              ))
            ) : (
              <span className="v5-model-chip">no model verdicts recorded</span>
            )}
          </div>
          <div className="v5-model-health-ledger" aria-label="configured model status">
            {modelStatuses.map((item) => (
              <span className={`v5-model-health ${String(item.status || "empty").startsWith("ok") ? "ok" : "bad"}`} key={item.model}>
                <b>{item.model}</b> · {item.status || "empty"}
                {item.reason ? ` · ${item.reason}` : ""}
                {Number(item.cost_inr) > 0 ? ` · ₹${Number(item.cost_inr).toFixed(3)}` : ""}
              </span>
            ))}
          </div>
          <div className="v5-nightly-cost">Nightly council total · ₹{Number(debate.nightly_cost_inr || 0).toFixed(3)}</div>
        </div>
        <div className="v5-ledger-disclaimer">
          {live === 0
            ? "0 live is a correct read of tonight's pool, not a system failure. A struck / refused name counts in neither live nor chair-take — deterministic risk always outranks debate conviction."
            : "Deterministic risk has final authority over every sized number shown above."}
        </div>
      </div>
    </>
  );
}

// ------------------------------------------------------------------
// main
// ------------------------------------------------------------------

export default function DebateTab({ date, card, initialData, jumpSignal, onOpenTradePlan, onNavigate, onPushToCouncil }) {
  const liveWork = useLiveWork();
  const { isExpert } = useDensity();
  const membership = useListMembership(date); // #13b cross-badges (watch / shadow-rank)
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [chartSymbol, setChartSymbol] = useState(null);
  const [reloadTick, setReloadTick] = useState(0);
  const [retryBusy, setRetryBusy] = useState(false);
  const [retryError, setRetryError] = useState(null);
  const [dismissedLiveJobId, setDismissedLiveJobId] = useState(null);
  const firstDeepRef = useRef(null);

  // The app shell already reads the same date-scoped debate payload for the
  // ticker. Reuse that completed response when it arrives so the main debate
  // surface is never left behind a duplicate request. Explicit reloads after
  // a push still use the effect below and therefore remain fresh.
  useEffect(() => {
    if (!initialData || reloadTick > 0) return;
    setData(initialData);
    setError(null);
    setLoading(false);
  }, [initialData, reloadTick]);

  // onOpenTradePlan is part of the route contract -- wired to the deep-dive
  // [TRADE PLAN ->] affordance below (preserved from the prior contract;
  // UI-5 remainder restored the link, which had gone dead in the round-4
  // rebuild).

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

  // cross-tab handoff: scroll to a symbol's deep-dive (or the first) on jump.
  useEffect(() => {
    if (!jumpSignal || loading || !data || !data.available) return;
    const target = jumpSignal.symbol
      ? document.getElementById(`deepdive-${jumpSignal.symbol}`) ||
        document.getElementById(`row-${jumpSignal.symbol}`)
      : firstDeepRef.current;
    if (target) target.scrollIntoView({ behavior: "auto", block: "start" });
  }, [jumpSignal, loading, data]);

  const jumpToHero = (symbol) => {
    const el = document.getElementById(`deepdive-${symbol}`);
    if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  // BUGFIX (DEBATE wipe): a live run for a symbol used to fully replace this
  // tab's return value with just <DebateLivePanel/>, which made every other
  // debate card for the day vanish from the screen while the run streamed.
  // The DebateCouncilOverlay slide-over already exists for exactly this
  // (queue-driven pushes from App.jsx); this local jumpSignal-driven path
  // (header search, POSITIONS "run debate", cross-tab jump-with-job) has no
  // queue entry to attach to, so it renders the same overlay chrome inline
  // instead, ON TOP of the normal card list underneath -- never in place of it.
  const showLivePanel =
    jumpSignal?.jobId &&
    liveWork.job?.job_id === jumpSignal.jobId &&
    liveWork.running &&
    dismissedLiveJobId !== jumpSignal.jobId;
  const debateRetryStep = [...(liveWork.steps || [])].reverse().find(
    (step) => step.name === "agents_debate" && step.status === "fail"
  );
  const canRetryCouncil = Boolean(
    debateRetryStep && liveWork.job && (!card?.run_date || liveWork.job.run_date === card.run_date)
  );
  const retryCouncil = async () => {
    if (!canRetryCouncil || retryBusy) return;
    setRetryBusy(true);
    setRetryError(null);
    try {
      await liveWork.retry(debateRetryStep.step_id);
      setReloadTick((tick) => tick + 1);
    } catch (retryFailure) {
      setRetryError(`Council retry failed: ${String(retryFailure.message || retryFailure)}`);
    } finally {
      setRetryBusy(false);
    }
  };

  const liveOverlay = showLivePanel ? (
    <div className="v5-council-overlay" role="dialog" aria-label={`Live council run — ${jumpSignal.symbol}`}>
      <div className="v5-council-overlay-backdrop" onClick={() => setDismissedLiveJobId(jumpSignal.jobId)} />
      <div className="v5-council-overlay-panel">
        <header className="v5-council-overlay-header">
          <div>
            <span className="v5-live-kicker">LIVE COUNCIL RUN</span>
            <h3>{jumpSignal.symbol}</h3>
          </div>
          <button
            type="button"
            className="v5-council-overlay-close"
            onClick={() => setDismissedLiveJobId(jumpSignal.jobId)}
            aria-label="Close live run panel — the run keeps going in the background"
          >
            &times;
          </button>
        </header>
        <div className="v5-council-overlay-body">
          <DebateLivePanel
            symbol={jumpSignal.symbol}
            jobId={jumpSignal.jobId}
            onComplete={() => setReloadTick((t) => t + 1)}
            onRetry={onPushToCouncil ? () => onPushToCouncil(jumpSignal.symbol) : undefined}
          />
        </div>
      </div>
    </div>
  ) : null;

  if (loading) {
    return (
      <>
        <div className="v5-debate v5-loading-state" role="status" aria-live="polite">
          <div className="v5-loading-kicker">Council workspace</div>
          <div className="v5-loading-title">Assembling tonight's debate</div>
          <p>Loading the market context, practitioner lenses, chair decisions and comparable evidence.</p>
          <div className="v5-loading-steps" aria-hidden="true">
            <span />
            <span />
            <span />
          </div>
        </div>
        {liveOverlay}
      </>
    );
  }
  if (error) {
    return (
      <>
        <div className="v5-debate v5-debate-empty">
          <p>Could not load the debate.</p>
          <p style={{ fontFamily: "var(--v5-mono)", fontSize: "11px" }}>{error}</p>
        </div>
        {liveOverlay}
      </>
    );
  }
  if (!data || !data.available || !data.symbols || data.symbols.length === 0) {
    return (
      <>
        <div className="v5-debate">
          <PushSymbolBox date={date} onPushed={() => setReloadTick((t) => t + 1)} onPushToCouncil={onPushToCouncil} />
          {card?.council_status?.state === "run_failed" && (
            <div className="v5-debate-empty" role="status">
              <CouncilPipelineNote card={card} isExpert={isExpert} canRetry={canRetryCouncil} retryBusy={retryBusy} retryError={retryError} onRetry={retryCouncil} />
            </div>
          )}
          <div className="v5-debate-empty">
            <p>No debate for this date.</p>
            <p>Shortlist was empty or the debate stage didn't run.</p>
          </div>
        </div>
        {liveOverlay}
      </>
    );
  }

  const symbols = data.symbols;
  const heroSymbols = symbols.filter((s) => symStatus(s) === "gatepass").map((s) => s.symbol);
  const debatedCount = symbols.length;

  return (
    <div className="v5-debate">
      <PushSymbolBox date={date} onPushed={() => setReloadTick((t) => t + 1)} onPushToCouncil={onPushToCouncil} />

      {/* relationship legend: why the 3 lists show different stocks (audit 51) */}
      <ListRelationshipLegend active="DEBATE" membership={membership} onNavigate={onNavigate} />

      <SectionLabel>Market Context — Why We're Picky Tonight</SectionLabel>
      <ContextRow regime={card && card.regime} funnel={data.funnel} />
      <GovernorRow card={card} debate={data} isExpert={isExpert} canRetryCouncil={canRetryCouncil} retryBusy={retryBusy} retryError={retryError} onRetryCouncil={retryCouncil} />

      <SectionLabel count={`${debatedCount} debated`}>
        Mechanism Lanes — TradeTM Setup Families, In Parallel
      </SectionLabel>
      <LanesRow symbols={symbols} />

      {card && card.tonights_call && (
        <>
          <SectionLabel>Tonight's Call</SectionLabel>
          <TonightsCall call={card.tonights_call} councilStatus={card.council_status} />
        </>
      )}

      <SectionLabel count="gate-pass vs near-miss">
        {`The ${debatedCount} Debated Names — 4-Model Council vs Chair Adjudication`}
      </SectionLabel>
      <DebateTable
        symbols={symbols}
        heroSymbols={heroSymbols}
        onJumpToHero={jumpToHero}
        onOpenChart={setChartSymbol}
        membership={membership}
        onNavigate={onNavigate}
      />

      {heroSymbols.length > 0 && (
        <>
          <SectionLabel count={`${heroSymbols.length} gate-passed`}>
            Gate-Passed Candidates — Deep Dive
          </SectionLabel>
          {symbols
            .filter((s) => symStatus(s) === "gatepass")
            .map((s, idx) => (
              <DeepDive
                key={s.symbol}
                date={date}
                sym={s}
                deepRef={idx === 0 ? firstDeepRef : null}
                onOpenTradePlan={onOpenTradePlan}
              />
            ))}
        </>
      )}

      <SectionLabel count="what each lens said tonight, as data">
        TradeTM Context — Parallel Mechanism Lenses
      </SectionLabel>
      <LensLanes symbols={symbols} />

      <SectionLabel>Tonight, In Five Numbers</SectionLabel>
      <FootStats debate={data} card={card} />

      <ChartDrawer symbol={chartSymbol} date={date} onClose={() => setChartSymbol(null)} />
      {liveOverlay}
    </div>
  );
}

// ------------------------------------------------------------------
// push-symbol box (ported from the previous DebateTab, restyled v5)
// ------------------------------------------------------------------

function PushSymbolBox({ date, onPushed, onPushToCouncil }) {
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
      if (onPushToCouncil) {
        // Streamed path: the council overlay + toast (App shell) carry the
        // live status from here on. This box just clears itself on accept.
        const result = await onPushToCouncil(sym);
        setToast({ ok: true, text: result?.already_debated ? `${sym} already debated for this date — watch it live.` : `${sym} pushed to the council — watching live.` });
        setSymbol("");
        if (onPushed) onPushed();
      } else {
        const result = await pushSymbolToDebate(sym, date);
        if (result.already_debated) {
          setToast({ ok: true, text: `${sym} already debated for this date — showing existing card.` });
          setSymbol("");
          if (onPushed) onPushed();
        } else if (result.status === "ok" || result.status === "partial") {
          setToast({ ok: true, text: `${sym} pushed to debate — ${result.verdicts || 0} verdict(s) landed.` });
          setSymbol("");
          if (onPushed) onPushed();
        } else {
          setToast({ ok: false, text: `${sym}: ${result.detail || result.status}` });
        }
      }
    } catch (err) {
      if (err.status === 409) {
        setToast({ ok: false, text: `${sym}: push already running — please wait.` });
      } else {
        setToast({ ok: false, text: String(err.message || err) });
      }
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="v5-push-box">
      <form onSubmit={submit} className="v5-push-form">
        <input
          type="text"
          value={symbol}
          onChange={(e) => setSymbol(e.target.value)}
          placeholder="Push a symbol to the LLMs (e.g. TANLA)"
          className="v5-push-input"
          aria-label="push a symbol to the debate"
          disabled={busy}
        />
        <button type="submit" className="v5-push-btn" disabled={busy || !symbol.trim()}>
          {busy ? "Debating…" : "PUSH TO DEBATE"}
        </button>
      </form>
      {toast && <p className={"v5-push-toast " + (toast.ok ? "v5-ok" : "v5-err")}>{toast.text}</p>}
    </div>
  );
}
