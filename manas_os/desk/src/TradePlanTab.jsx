import React, { useEffect, useState } from "react";
import { fetchDebate, fetchSignalGuide, chartUrl } from "./api.js";
import { humanizeSourceCite } from "./utils.js";
import { useDensity } from "./DensityContext.jsx";
import {
  SectionLabel,
  Panel,
  VerdictChip,
  GateCellGrid,
  SizerStamp,
  StruckNote,
  CallBanner,
} from "./components/v5/index.js";
import "./TradePlanTab.v5.css";

// UI-5 (remainder): TRADE PLAN rebuilt as the "exactly what do I do manually"
// execution ticket + management contract per UI_OVERHAUL_HANDOFF.md §5/§6.
//
// ONE-WRITER-FOR-RISK: every stop/qty/RR value below is read verbatim off
// the /api/desk/signal-guide payload (guide.plan / guide.sizer /
// guide.risk_checks). The only client-side arithmetic left is
// qty(server) x (entry(server) - stop(server)) to produce a rupee-risk
// figure the backend does not yet expose as its own field (flagged below).
// The previous build let the user's typed capital re-derive a base qty and
// override the sizer's final_qty -- that was a one-writer violation and has
// been removed; capital/position-sizing math is not shown here anymore.

function n(v, digits = 1) {
  if (v === null || v === undefined || Number.isNaN(Number(v))) return "—";
  return Number(v).toFixed(digits);
}

function pct(v, digits = 1) {
  if (v === null || v === undefined || Number.isNaN(Number(v))) return "—";
  return `${Number(v).toFixed(digits)}%`;
}

function hasNum(v) {
  return v !== null && v !== undefined && !Number.isNaN(Number(v));
}

// -------------------------------------------------------------------
// ticket state classification -- one honest state, never a guess
// -------------------------------------------------------------------
function classifyTicket(guide) {
  if (!guide || !guide.available) return "no-guide";
  if (guide.source === "morning_setups") return "not-sized"; // pre-open checklist, sizer hasn't run
  if (!guide.plan || !hasNum(guide.plan.entry) || !hasNum(guide.plan.stop)) return "no-plan"; // near-miss / no cand row
  if (!guide.sizer) return "sizing-unavailable"; // plan exists but sizer row missing
  if (guide.sizer.final_qty === 0 || guide.sizer.final_qty === null) return "refused";
  return "live-paper"; // sized, qty > 0 -- still paper/manual, this app places no live orders
}

// -------------------------------------------------------------------
// management-contract step extraction -- reuse the SAME deterministic
// steps the ticket's broker checklist shows; pick the one that states how
// this family is normally managed (trail / exit-line language), sourced
// and cited, never re-authored.
// -------------------------------------------------------------------
const MANAGEMENT_STEP_RE = /trail|exit line|manage this|over-manage/i;

function findManagementStep(steps) {
  if (!steps || steps.length === 0) return null;
  return steps.find((s) => MANAGEMENT_STEP_RE.test(s.title) || MANAGEMENT_STEP_RE.test(s.instruction)) || null;
}

const TEMPLATE_INTENT_COPY = {
  magnitude: "Magnitude trade — hold the big move, sell into weakness, not strength.",
  velocity: "Velocity trade — the entry window is short; act on the trigger, not the story.",
  hybrid: "Hybrid trade — size and manage per the checklist below; no single template dominates.",
};

function DoNotTradeConditions({ ticketState, guide, symbol, date }) {
  const rc = guide && guide.risk_checks;
  const rows = [];

  if (ticketState === "refused") {
    rows.push({
      state: "FAIL",
      label: "Sizer verdict",
      detail: (guide.sizer && guide.sizer.reasoning) || "sizer refused — final qty 0",
    });
  }
  if (ticketState === "no-plan") {
    rows.push({
      state: "FAIL",
      label: "Sized plan",
      detail: `no entry/stop for ${symbol} on ${date} — this is a near-miss/watch name, not a trade`,
    });
  }
  if (ticketState === "not-sized") {
    rows.push({
      state: "UNAVAILABLE",
      label: "Sizer",
      detail: "pre-open checklist — the sizer has not run yet; do not infer a live qty from this screen",
    });
  }
  if (rc) {
    if (hasNum(rc.stop_pct) && hasNum(rc.regime_stop_cap)) {
      const fail = rc.stop_pct > rc.regime_stop_cap;
      rows.push({
        state: fail ? "FAIL" : "PASS",
        label: "Stop % vs regime cap",
        detail: `${n(rc.stop_pct, 2)}% vs cap ${n(rc.regime_stop_cap, 2)}%`,
      });
    } else {
      rows.push({ state: "UNAVAILABLE", label: "Stop % vs regime cap", detail: "not in payload" });
    }
    if (hasNum(rc.open_risk_after) && hasNum(rc.open_risk_cap)) {
      const fail = rc.open_risk_after > rc.open_risk_cap;
      rows.push({
        state: fail ? "FAIL" : "PASS",
        label: "Open risk after this trade vs cap",
        detail: `${n(rc.open_risk_after, 4)}% vs cap ${n(rc.open_risk_cap, 2)}%`,
      });
    } else {
      rows.push({ state: "UNAVAILABLE", label: "Open risk after this trade vs cap", detail: "not in payload" });
    }
    if (hasNum(rc.concurrent_tight_sl) && hasNum(rc.concurrent_cap)) {
      const fail = rc.concurrent_tight_sl >= rc.concurrent_cap;
      rows.push({
        state: fail ? "FAIL" : "PASS",
        label: "Concurrent tight-SL positions vs cap",
        detail: `${rc.concurrent_tight_sl} open vs cap ${rc.concurrent_cap}`,
      });
    } else {
      rows.push({ state: "UNAVAILABLE", label: "Concurrent tight-SL positions vs cap", detail: "not in payload" });
    }
  } else if (ticketState === "live-paper" || ticketState === "refused") {
    rows.push({ state: "UNAVAILABLE", label: "Risk checks", detail: "risk_checks block missing from payload" });
  }

  if (rows.length === 0) return null;
  return (
    <div className="v5-tp-dnt">
      {rows.map((r, i) => (
        <div className={"v5-tp-dnt-row v5-tp-dnt-" + r.state.toLowerCase()} key={i}>
          <span className="v5-tp-dnt-state mono-num">{r.state}</span>
          <span className="v5-tp-dnt-label">{r.label}</span>
          <span className="v5-tp-dnt-detail mono-num">{r.detail}</span>
        </div>
      ))}
      <p className="v5-tp-dnt-rule">
        Hard stop must be a LIVE (GTT) order in your broker — no mental stops. Any FAIL above means
        stand aside, not "size down and hope".
      </p>
    </div>
  );
}

function BrokerChecklist({ steps, checked, onToggle, isExpert }) {
  if (!steps || steps.length === 0) {
    return <p className="v5-tp-empty-note">No checklist steps available for this symbol/date.</p>;
  }
  return (
    <ol className="v5-tp-checklist">
      {steps.map((step) => {
        const isStopStep = /place a live stop-loss order/i.test(step.instruction || "");
        return (
          <li
            key={step.n}
            className={"v5-tp-step" + (step.n === 0 ? " v5-tp-step-refusal" : "")}
          >
            <label className="v5-tp-step-head">
              <input type="checkbox" checked={!!checked[step.n]} onChange={() => onToggle(step.n)} />
              <span className="v5-tp-step-title">{step.title}</span>
            </label>
            <p className="v5-tp-step-instruction">{step.instruction}</p>
            {isStopStep && (
              <p className="v5-tp-step-gtt">
                Place this as a <b>GTT (Good-Till-Triggered) SELL</b> order at your broker the moment
                you enter — not a mental note, not a price alert.
              </p>
            )}
            <p className="v5-tp-step-check mono-num">Check before you proceed: {step.check}</p>
            {isExpert && step.source_cite && (
              <p className="v5-tp-step-cite mono-num" title={step.source_cite}>
                source: {humanizeSourceCite(step.source_cite)}
              </p>
            )}
          </li>
        );
      })}
    </ol>
  );
}

function ManagementContract({ guide, symbol }) {
  const family = guide.family;
  const intent = guide.template_intent;
  const mgmtStep = findManagementStep(guide.steps);
  return (
    <Panel title="Management Contract" cite={family ? `${family} lens` : undefined} className="v5-tp-mgmt-panel">
      <div className="v5-tp-mgmt-type">
        <span className="v5-tp-mgmt-fam">{(family || "unknown").replace(/_/g, " ").toUpperCase()}</span>
        <span className="v5-tp-mgmt-intent">
          {intent ? TEMPLATE_INTENT_COPY[intent] || `${intent} trade` : "Template intent not classified for this family."}
        </span>
      </div>
      <div className="v5-tp-mgmt-body">
        <div className="v5-ctx-title">What "normal" looks like for {symbol}</div>
        {mgmtStep ? (
          <>
            <p className="v5-tp-mgmt-text">{mgmtStep.instruction}</p>
            <p className="v5-tp-mgmt-cite mono-num" title={mgmtStep.source_cite}>
              source: {humanizeSourceCite(mgmtStep.source_cite)}
            </p>
          </>
        ) : (
          <p className="v5-tp-mgmt-text">
            No explicit trail/exit-line step is recorded for this family's guide tonight. Hold the
            stop discipline in the broker checklist and do not loosen it intraday on a "feeling" —
            that discretion is exactly what the deterministic guide exists to remove.
          </p>
        )}
      </div>
      <div className="v5-tp-mgmt-body">
        <div className="v5-ctx-title">Wobble days / noise</div>
        <p className="v5-tp-mgmt-text">
          A close still above your stop line on a red day is a wobble, not an exit signal — manage
          off the stop/trail rule above, not the day's colour. Only the stop line (or the exit-line
          rule above, once stated) ends the trade.
        </p>
      </div>
    </Panel>
  );
}

function EvidenceInspector({ date, symbol, guide, debateSym, isExpert }) {
  const rc = guide && guide.risk_checks;
  return (
    <details className="v5-tp-inspector">
      <summary>Evidence &amp; alternative scenarios</summary>
      <div className="v5-tp-inspector-body">
        {guide.source === "morning_setups" && (
          <div className="v5-note-box">
            <b>Pre-open checklist</b> — entry rule: {guide.entry_rule || "—"}; stop rule:{" "}
            {guide.stop_rule || "—"}. Day-1 high {n(guide.day1_high, 2)}, day-1 low {n(guide.day1_low, 2)}.
          </div>
        )}

        {debateSym && debateSym.gates && debateSym.gates.length > 0 && (
          <>
            <div className="v5-ctx-title" style={{ marginTop: 10 }}>Deterministic gates</div>
            <GateCellGrid
              gates={debateSym.gates.map((g) => {
                const ev = g.evidence || {};
                let state = g.pass ? "PASS" : "FAIL";
                let objection = g.reason || null;
                if (g.pass && ev.note && /waiv/i.test(String(ev.note))) {
                  state = "WAIVED";
                  objection = String(ev.note).replace(/^[^:]*:\s*/, "");
                }
                return { name: g.gate, state, objection };
              })}
            />
          </>
        )}

        {debateSym && debateSym.chair && (
          <>
            <div className="v5-ctx-title" style={{ marginTop: 10 }}>Chair verdict</div>
            <div className="v5-tp-inspector-row">
              <VerdictChip
                verdict={debateSym.chair.verdict}
                struck={!!debateSym.chair.struck}
                conviction={debateSym.chair.conviction}
              />
              {debateSym.chair.rank !== null && debateSym.chair.rank !== undefined && (
                <span className="v5-tp-inspector-note">debate rank {debateSym.chair.rank}</span>
              )}
            </div>
            {debateSym.chair.struck && (
              <StruckNote>
                <b>
                  Chair struck the vote
                  {debateSym.chair.pre_strike_verdict ? ` (${debateSym.chair.pre_strike_verdict} → SKIP)` : " (→ SKIP)"}:
                </b>{" "}
                {debateSym.chair.strike_reason || debateSym.chair.reasoning || "risk strike"}
              </StruckNote>
            )}
          </>
        )}

        {debateSym && debateSym.models && debateSym.models.length > 0 && (
          <>
            <div className="v5-ctx-title" style={{ marginTop: 10 }}>
              {debateSym.models.length}-model council vote
            </div>
            <div className="v5-tp-inspector-votes">
              {debateSym.models.map((m) => (
                <div className="v5-vote-panel-row" key={m.agent}>
                  <span className="v5-model-name">{m.agent}</span>
                  <VerdictChip verdict={m.verdict} conviction={m.conviction} />
                </div>
              ))}
            </div>
          </>
        )}

        {debateSym && debateSym.objections && debateSym.objections.length > 0 && (
          <>
            <div className="v5-ctx-title" style={{ marginTop: 10 }}>Objections (alternative read)</div>
            <div className="v5-note-box">{debateSym.objections.map((o) => o.reason).join(" · ")}</div>
          </>
        )}

        {debateSym && debateSym.near_miss && (
          <>
            <div className="v5-ctx-title" style={{ marginTop: 10 }}>Near-miss reason</div>
            <div className="v5-note-box">
              {debateSym.near_miss.failed_gate}: {debateSym.near_miss.reason}
            </div>
          </>
        )}

        {guide.sizer && guide.sizer.reasoning && (
          <>
            <div className="v5-ctx-title" style={{ marginTop: 10 }}>Sizer reasoning (full)</div>
            <div className="v5-note-box">{guide.sizer.reasoning}</div>
          </>
        )}

        {isExpert && rc && (
          <>
            <div className="v5-ctx-title" style={{ marginTop: 10 }}>Expert risk detail</div>
            <div className="v5-note-box mono-num">
              k×ADR {hasNum(rc.k_adr) ? `${rc.k_adr}x` : "—"} · ADR20{" "}
              {hasNum(rc.adr20) ? `${n(rc.adr20, 2)}%` : "—"} · open risk now{" "}
              {hasNum(rc.open_risk_now) ? `${n(rc.open_risk_now, 4)}%` : "—"}
            </div>
          </>
        )}

        <div className="v5-ctx-title" style={{ marginTop: 10 }}>Chart</div>
        <img
          className="v5-groww-chart"
          style={{ marginTop: 6 }}
          src={chartUrl(date, symbol, "daily")}
          alt={`${symbol} daily chart`}
          onError={(e) => {
            e.currentTarget.style.display = "none";
          }}
        />
      </div>
    </details>
  );
}

export default function TradePlanTab({ date, symbol, onBackToDebate, card }) {
  const { isExpert } = useDensity();
  const [guide, setGuide] = useState(null);
  const [debateSym, setDebateSym] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [checked, setChecked] = useState({});

  useEffect(() => {
    if (!symbol || !date) return undefined;
    let cancelled = false;
    setLoading(true);
    setError(null);
    setChecked({});
    Promise.all([fetchSignalGuide(symbol, date), fetchDebate(date).catch(() => null)])
      .then(([guideBody, debateBody]) => {
        if (cancelled) return;
        setGuide(guideBody);
        const sym = debateBody && debateBody.symbols ? debateBody.symbols.find((s) => s.symbol === symbol) : null;
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

  const toggleCheck = (i) => setChecked((c) => ({ ...c, [i]: !c[i] }));

  if (!symbol) {
    return (
      <div className="v5-tp v5-debate-empty">
        <p>No symbol selected.</p>
      </div>
    );
  }
  if (loading) {
    return <div className="v5-tp v5-debate-empty">Loading trade plan for {symbol}…</div>;
  }
  if (error) {
    return (
      <div className="v5-tp v5-debate-empty">
        <p>Could not load the trade plan.</p>
        <p style={{ fontFamily: "var(--v5-mono)", fontSize: "11px" }}>{error}</p>
      </div>
    );
  }
  if (!guide || !guide.available) {
    return (
      <div className="v5-tp v5-debate-empty">
        <p>No guide available for {symbol} on {date}.</p>
        <button type="button" className="v5-tp-back" onClick={onBackToDebate}>
          &larr; back to debate
        </button>
      </div>
    );
  }

  const ticketState = classifyTicket(guide);
  const plan = guide.plan;
  const sizer = guide.sizer;
  const stopDist = plan && hasNum(plan.entry) && hasNum(plan.stop) ? plan.entry - plan.stop : null;
  const stopPct = stopDist !== null && plan.entry ? (stopDist / plan.entry) * 100 : null;
  const qty = sizer ? sizer.final_qty : plan ? plan.final_qty : null;
  // rupee risk = server qty x server stop-distance -- both verbatim server
  // numbers, multiplied, not derived from any client input. Flagged in the
  // final report as a field the backend could own directly.
  const rupeeRisk = hasNum(qty) && stopDist !== null ? qty * stopDist : null;
  const rMultiple =
    plan && hasNum(plan.target) && stopDist && stopDist > 0 ? (plan.target - plan.entry) / stopDist : null;

  const isDominantRefusal = ticketState === "refused" || ticketState === "no-plan" || ticketState === "not-sized" || ticketState === "sizing-unavailable";

  return (
    <div className="v5-tp">
      <button type="button" className="v5-tp-back" onClick={onBackToDebate}>
        &larr; DEBATE
      </button>

      <CallBanner
        stance="PAPER · MANUAL EXECUTION"
        icon="✋"
        headline="sat10ic os places no live orders. Every fill, stop and exit below is something you execute yourself in your broker."
        bullets={[
          { text: "This screen is a checklist, not an order ticket — nothing here transmits to a broker." },
        ]}
      />

      <SectionLabel count={guide.scan_date}>{`Execution Ticket — ${symbol}`}</SectionLabel>

      <div className="v5-tp-provenance mono-num">
        {(guide.family || "unknown").replace(/_/g, " ")} lens · deterministic signal_guide.py ·{" "}
        {guide.source === "morning_setups" ? "morning_setups (pre-open)" : "scan_candidates"} · {guide.scan_date}
      </div>

      <div className={"v5-tp-ticket" + (isDominantRefusal ? " v5-tp-ticket-refused" : "")}>
        {ticketState === "no-plan" && (
          <div className="v5-tp-no-plan">
            <div className="v5-tp-no-plan-h">NO SIZED PLAN — NOT A TRADE</div>
            <p>
              {symbol} has no entry/stop from tonight's run. It is a debate/watch name only; there is
              nothing to execute. Do not infer a level from the chart yourself.
            </p>
          </div>
        )}

        {ticketState === "not-sized" && (
          <div className="v5-tp-no-plan">
            <div className="v5-tp-no-plan-h">PRE-OPEN CHECKLIST — SIZER HAS NOT RUN</div>
            <p>
              This is a {guide.family === "d2" ? "Day-2" : "Strong Start"} pre-open reference level, not a
              sized trade. Trigger reference {n(plan && plan.entry, 2)}
              {plan && hasNum(plan.stop) ? `, stop reference ${n(plan.stop, 2)}` : " — no stop reference yet (pre-open)"}.
              No qty or rupee risk exists until the sizer runs on confirmed intraday structure.
            </p>
          </div>
        )}

        {ticketState === "sizing-unavailable" && (
          <div className="v5-tp-no-plan">
            <div className="v5-tp-no-plan-h">PLAN EXISTS, SIZER ROW MISSING</div>
            <p>
              {symbol} has a plan (entry {n(plan.entry, 2)} / stop {n(plan.stop, 2)}) but no sizer verdict
              was recorded for this date — final qty is unknown, not zero. Treat as not-actionable
              until a sizer verdict exists.
            </p>
          </div>
        )}

        {ticketState === "refused" && (
          <SizerStamp
            reason={(sizer && sizer.reasoning) || "no reason recorded"}
            multiplier={sizer && hasNum(sizer.multiplier) ? sizer.multiplier : 0}
            qty={0}
            rupeeRisk={0}
          />
        )}

        {(ticketState === "live-paper" || isDominantRefusal) && plan && (
          <div className="v5-tp-levels">
            <div className="v5-tp-level">
              <span className="v5-tp-level-lbl">Trigger / entry zone</span>
              <span className="v5-tp-level-val mono-num">{hasNum(plan.entry) ? `₹${n(plan.entry, 2)}` : "—"}</span>
            </div>
            <div className="v5-tp-level v5-tp-level-stop">
              <span className="v5-tp-level-lbl">Invalidation / stop</span>
              <span className="v5-tp-level-val mono-num">{hasNum(plan.stop) ? `₹${n(plan.stop, 2)}` : "—"}</span>
              <span className="v5-tp-level-sub mono-num">
                {stopPct !== null ? `−${n(stopPct, 2)}% (−₹${n(stopDist, 2)} / share)` : ""}
              </span>
            </div>
            <div className="v5-tp-level">
              <span className="v5-tp-level-lbl">Target</span>
              <span className="v5-tp-level-val mono-num">{hasNum(plan.target) ? `₹${n(plan.target, 2)}` : "—"}</span>
              <span className="v5-tp-level-sub mono-num">{rMultiple !== null ? `${n(rMultiple, 2)}R` : ""}</span>
            </div>
            <div className="v5-tp-level">
              <span className="v5-tp-level-lbl">R:R</span>
              <span className="v5-tp-level-val mono-num">{hasNum(plan.rr) ? n(plan.rr, 2) : "—"}</span>
            </div>
            <div className="v5-tp-level">
              <span className="v5-tp-level-lbl">Qty (server, final)</span>
              <span className={"v5-tp-level-val mono-num" + (qty === 0 ? " v5-tp-zero" : "")}>
                {hasNum(qty) ? qty : "—"}
              </span>
              <span className="v5-tp-level-sub mono-num">
                base plan qty {hasNum(plan.suggested_qty) ? plan.suggested_qty : "—"}
                {sizer && hasNum(sizer.multiplier) ? ` × ${sizer.multiplier}x sizer` : ""}
              </span>
            </div>
            <div className="v5-tp-level">
              <span className="v5-tp-level-lbl">Rupee risk (qty × stop distance)</span>
              <span className={"v5-tp-level-val mono-num" + (rupeeRisk === 0 ? " v5-tp-zero" : "")}>
                {rupeeRisk !== null ? `₹${n(rupeeRisk, 0)}` : "—"}
              </span>
            </div>
          </div>
        )}

        {ticketState === "live-paper" && qty > 0 && (
          <p className="v5-tp-paper-line">
            Sized and gate-passed — <b>still paper-only</b> (this build places no live orders). Follow
            the broker checklist below to execute manually if you choose to take this live yourself.
          </p>
        )}

        <div className="v5-ctx-title" style={{ marginTop: 16 }}>
          Do-not-trade conditions
        </div>
        <DoNotTradeConditions ticketState={ticketState} guide={guide} symbol={symbol} date={date} />

        {(guide.steps && guide.steps.length > 0) && (
          <>
            <div className="v5-ctx-title" style={{ marginTop: 16 }}>
              Broker checklist — step by step
            </div>
            <BrokerChecklist steps={guide.steps} checked={checked} onToggle={toggleCheck} isExpert={isExpert} />
          </>
        )}
      </div>

      <ManagementContract guide={guide} symbol={symbol} />

      <EvidenceInspector date={date} symbol={symbol} guide={guide} debateSym={debateSym} isExpert={isExpert} />

      <button type="button" className="v5-tp-debate-link" onClick={onBackToDebate}>
        &rarr; back to debate card
      </button>
    </div>
  );
}
