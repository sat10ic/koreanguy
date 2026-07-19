import React, { useEffect, useState } from "react";
import {
  fetchDebate,
  fetchSignalGuide,
  fetchChecklistEvaluation,
  toggleChecklistTick,
  fetchMentorChecklists,
  postSetupDecision,
  addJournalTrade,
} from "./api.js";
import { humanizeSourceCite } from "./utils.js";
import { useDensity } from "./DensityContext.jsx";
import ChartDrawer from "./ChartDrawer.jsx";
import PriceSparkThumb from "./PriceSparkThumb.jsx";
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
// ONE-WRITER-FOR-RISK: every stop/qty/RR/rupee_risk value below is read
// verbatim off /api/desk/signal-guide (guide.plan / guide.sizer /
// guide.rupee_risk / guide.management_contract / guide.risk_checks).
// Client no longer multiplies qty x stop-distance — server owns rupee_risk.

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

// Fallback only for old payloads that lack management_contract.
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
  const mc = guide.management_contract;
  // Prefer server block; regex over steps is legacy fallback only.
  const mgmtStep = !mc ? findManagementStep(guide.steps) : null;
  const trailText = mc?.trail_rule || (mgmtStep && mgmtStep.instruction) || null;
  const cite = mc?.source_cite || (mgmtStep && mgmtStep.source_cite) || null;
  const tradeType = mc?.trade_type || intent;
  const behaviours = Array.isArray(mc?.normal_behaviour) ? mc.normal_behaviour : [];
  return (
    <Panel title="Management Contract" cite={family ? `${family} lens` : undefined} className="v5-tp-mgmt-panel">
      <div className="v5-tp-mgmt-type">
        <span className="v5-tp-mgmt-fam">{(family || "unknown").replace(/_/g, " ").toUpperCase()}</span>
        <span className="v5-tp-mgmt-intent">
          {tradeType
            ? TEMPLATE_INTENT_COPY[tradeType] || `${tradeType} trade`
            : "Template intent not classified for this family."}
        </span>
      </div>
      <div className="v5-tp-mgmt-body">
        <div className="v5-ctx-title">What &quot;normal&quot; looks like for {symbol}</div>
        {trailText ? (
          <>
            <p className="v5-tp-mgmt-text">{trailText}</p>
            {behaviours.map((line) => (
              <p key={line} className="v5-tp-mgmt-text">{line}</p>
            ))}
            {cite && (
              <p className="v5-tp-mgmt-cite mono-num" title={cite}>
                source: {humanizeSourceCite(cite)}
              </p>
            )}
          </>
        ) : (
          <p className="v5-tp-mgmt-text">
            No explicit trail/exit-line step is recorded for this family&apos;s guide tonight. Hold the
            stop discipline in the broker checklist and do not loosen it intraday on a &quot;feeling&quot; —
            that discretion is exactly what the deterministic guide exists to remove.
          </p>
        )}
      </div>
      <div className="v5-tp-mgmt-body">
        <div className="v5-ctx-title">Wobble days / noise</div>
        <p className="v5-tp-mgmt-text">
          A close still above your stop line on a red day is a wobble, not an exit signal — manage
          off the stop/trail rule above, not the day&apos;s colour. Only the stop line (or the exit-line
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
        <PriceSparkThumb className="v5-groww-chart v5-price-spark-full" date={date} symbol={symbol} />
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

  const [checklistId, setChecklistId] = useState("arora_entry_v1");
  const [allChecklists, setAllChecklists] = useState([]);
  const [checklistEval, setChecklistEval] = useState(null);
  const [chartSymbol, setChartSymbol] = useState(null);

  const [loggingDecision, setLoggingDecision] = useState(false);
  const [decisionStatus, setDecisionStatus] = useState(null);
  const [showSkipInput, setShowSkipInput] = useState(false);
  const [skipReason, setSkipReason] = useState("");

  const [retryCount, setRetryCount] = useState(0);

  useEffect(() => {
    if (!symbol || !date) return undefined;
    const abortController = new AbortController();
    const signal = abortController.signal;

    let cancelled = false;
    setLoading(true);
    setError(null);
    setChecked({});
    setDecisionStatus(null);
    setShowSkipInput(false);
    setSkipReason("");

    // Start 8-second timeout for primary fetch
    let timeoutFired = false;
    const timeoutId = setTimeout(() => {
      if (!cancelled && loading) {
        timeoutFired = true;
        abortController.abort();
        setError(`Timeout: primary signal guide took longer than 8s to load.`);
        setLoading(false);
      }
    }, 8000);

    // Primary load: signal guide
    fetchSignalGuide(symbol, date, signal)
      .then((guideBody) => {
        if (cancelled || timeoutFired) return;
        setGuide(guideBody);
        setLoading(false);
        clearTimeout(timeoutId);

        // Optional Context loads (fire-and-forget; do not block primary decisions)
        fetchDebate(date, signal)
          .then((debateBody) => {
            if (cancelled) return;
            const sym = debateBody && debateBody.symbols ? debateBody.symbols.find((s) => s.symbol === symbol) : null;
            setDebateSym(sym || null);
          })
          .catch((err) => {
            if (err.name !== 'AbortError') console.warn("Optional context fetchDebate failed:", err);
          });
        
        fetchChecklistEvaluation(checklistId, symbol, date, signal)
          .then((evalBody) => {
            if (cancelled) return;
            setChecklistEval(evalBody);
          })
          .catch((err) => {
            if (err.name !== 'AbortError') console.warn("Optional context fetchChecklistEvaluation failed:", err);
          });
          
        fetchMentorChecklists(signal)
          .then((mentorChecklistsBody) => {
            if (cancelled) return;
            if (mentorChecklistsBody && mentorChecklistsBody.checklists) {
              setAllChecklists(mentorChecklistsBody.checklists);
            }
          })
          .catch((err) => {
            if (err.name !== 'AbortError') console.warn("Optional context fetchMentorChecklists failed:", err);
          });
      })
      .catch((err) => {
        if (!cancelled && !timeoutFired) {
          if (err.name !== 'AbortError') setError(String(err.message || err));
          setLoading(false);
          clearTimeout(timeoutId);
        }
      });

    return () => {
      cancelled = true;
      clearTimeout(timeoutId);
      abortController.abort();
    };
  }, [symbol, date, checklistId, retryCount]);

  const toggleCheck = (i) => setChecked((c) => ({ ...c, [i]: !c[i] }));

  const handleCheckItem = (itemId, newChecked) => {
    toggleChecklistTick(checklistId, itemId, symbol, date, newChecked)
      .then(() => {
        fetchChecklistEvaluation(checklistId, symbol, date)
          .then((data) => setChecklistEval(data))
          .catch(() => {});
      })
      .catch((err) => {
        alert(`Failed to save tick: ${err.message || String(err)}`);
      });
  };

  const handleLogTaken = () => {
    if (loggingDecision) return;
    // Mechanical gate, client side: mirrors the server's actionability
    // verdict (guide.actionable) so this handler can never fire a TAKEN
    // for a plan the server will refuse anyway. The render guard below
    // disables the button for the same reason, but this stays here too --
    // never trust only a disabled prop.
    if (!guide || !guide.actionable) {
      setDecisionStatus(
        `Cannot log TAKEN: ${(guide && guide.not_actionable_reason) || "this trade is not actionable"}.`
      );
      return;
    }
    setLoggingDecision(true);
    setDecisionStatus(null);
    const _plan = guide && guide.plan;
    const _sizer = guide && guide.sizer;
    const qtyValue = _sizer ? _sizer.final_qty : _plan ? _plan.suggested_qty : 0;
    const payload = {
      scan_date: date,
      symbol: symbol,
      decision: "taken",
      entry_price: _plan?.entry || 0,
      qty: qtyValue || 0,
    };

    postSetupDecision(payload)
      .then(() => {
        setDecisionStatus("Trade logged successfully as TAKEN!");
      })
      .catch((err) => {
        // NOT_ACTIONABLE (409) is the server's mechanical gate rejecting a
        // non-actionable TAKEN -- surface its reason verbatim and stop.
        // Never fall through to the direct-journal fallback for this case;
        // that fallback exists for transient/plumbing failures, not for a
        // deliberate server refusal.
        if (err && err.status === 409 && err.detail && err.detail.code === "NOT_ACTIONABLE") {
          setDecisionStatus(`Cannot log TAKEN: ${err.detail.cause || "this trade is not actionable"}.`);
          setLoggingDecision(false);
          return;
        }
        console.warn("[sat10ic os] postSetupDecision failed, trying direct addJournalTrade fallback:", err);
        const journalPayload = {
          trade_date: date,
          symbol: symbol,
          setup: (guide && guide.family) || "Unknown",
          entry: _plan?.entry || 0,
          stop: _plan?.stop || 0,
          notes: "Manual entry from Trade Plan (setup fallback)",
        };
        addJournalTrade(journalPayload)
          .then(() => {
            setDecisionStatus("Trade logged successfully as TAKEN (fallback direct journal)!");
          })
          .catch((errFallback) => {
            setDecisionStatus(`Failed to log: ${errFallback.message || String(errFallback)}`);
          })
          .finally(() => {
            setLoggingDecision(false);
          });
        return;
      })
      .finally(() => {
        setLoggingDecision(false);
      });
  };

  const handleLogSkip = (e) => {
    if (e) e.preventDefault();
    if (loggingDecision) return;
    setLoggingDecision(true);
    setDecisionStatus(null);

    const payload = {
      scan_date: date,
      symbol: symbol,
      decision: "skipped",
      skip_reason: skipReason.trim() || "Manual skip from Trade Plan checklist",
    };

    postSetupDecision(payload)
      .then(() => {
        setDecisionStatus("Decision logged as SKIPPED.");
        setShowSkipInput(false);
        setSkipReason("");
      })
      .catch((err) => {
        setDecisionStatus(`Failed to log skip: ${err.message || String(err)}`);
      })
      .finally(() => {
        setLoggingDecision(false);
      });
  };

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
        <p style={{ fontFamily: "var(--v5-mono)", fontSize: "11px", color: "var(--v5-red)" }}>{error}</p>
        <button 
          type="button" 
          className="v5-btn v5-btn-teal" 
          style={{ marginTop: "10px", padding: "8px 16px" }}
          onClick={() => {
            setError(null);
            setLoading(true);
            setRetryCount(r => r + 1);
          }}
        >
          Retry Load
        </button>
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
  // Prefer server rupee_risk (one-writer); fallback only for old payloads.
  const rupeeRisk = hasNum(guide.rupee_risk)
    ? Number(guide.rupee_risk)
    : hasNum(qty) && stopDist !== null
      ? qty * stopDist
      : null;
  const rMultiple =
    plan && hasNum(plan.target) && stopDist && stopDist > 0 ? (plan.target - plan.entry) / stopDist : null;

  const isDominantRefusal = ticketState === "refused" || ticketState === "no-plan" || ticketState === "not-sized" || ticketState === "sizing-unavailable";

  // Mechanical gate (render side): prefer the server's own actionability
  // verdict (guide.actionable, set by /api/desk/signal-guide's
  // _plan_actionability -- the same rule POST /api/setups/decision
  // enforces server-side). Fall back to the local ticketState/qty
  // computation only for older cached payloads that predate the field, so
  // a stale offline snapshot never renders TAKEN as enabled by omission.
  const isActionable =
    typeof guide.actionable === "boolean"
      ? guide.actionable
      : ticketState === "live-paper" && hasNum(qty) && qty > 0;
  const notActionableReason =
    guide.not_actionable_reason ||
    (ticketState === "refused"
      ? (sizer && sizer.reasoning) || "sizer refused — final qty 0"
      : ticketState === "sizing-unavailable"
        ? "no sizer verdict recorded for this date — final qty is unknown, not zero"
        : ticketState === "not-sized"
          ? "pre-open checklist — the sizer has not run yet"
          : ticketState === "no-plan"
            ? "no sized entry/stop for this symbol on this date"
            : "this trade is not actionable");

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

      <div style={{ display: "flex", gap: "16px", alignItems: "flex-start", marginBottom: "14px" }}>
        <button
          type="button"
          onClick={() => setChartSymbol(symbol)}
          style={{
            border: "1px solid var(--v5-line)",
            borderRadius: "var(--v5-r-md)",
            padding: 0,
            background: "var(--v5-panel-2)",
            cursor: "pointer",
            width: "120px",
            height: "60px",
            overflow: "hidden",
            flexShrink: 0,
          }}
          title={`Click to inspect ${symbol} chart`}
        >
          <PriceSparkThumb className="v5-tp-price-spark" date={date} symbol={symbol} />
        </button>
        <div className="v5-tp-provenance mono-num" style={{ margin: 0 }}>
          {(guide.family || "unknown").replace(/_/g, " ")} lens · deterministic signal_guide.py ·{" "}
          {guide.source === "morning_setups" ? "morning_setups (pre-open)" : "scan_candidates"} · {guide.scan_date}
        </div>
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
              {sizer && sizer.provenance && (
                <span className="v5-tp-level-sub mono-num" style={{ color: "var(--v5-teal)", marginTop: "4px" }}>
                  Provenance: {sizer.provenance}
                </span>
              )}
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
        {/* Decision Logging Group */}
        <div className="v5-tp-decision-box" style={{ marginTop: "20px", borderTop: "1px solid var(--v5-line)", paddingTop: "16px" }}>
          <div className="v5-ctx-title" style={{ marginBottom: "8px" }}>Log Setup Decision to Journal</div>
          
          {decisionStatus && (
            <div className={`v5-tp-decision-status ${decisionStatus.includes("Failed") ? "error" : "success"}`} style={{ marginBottom: "12px", padding: "8px 12px", borderRadius: "var(--v5-r-sm)", fontSize: "12px", fontWeight: "600", background: decisionStatus.includes("Failed") ? "var(--v5-red-dim)" : "var(--v5-teal-dim)", color: decisionStatus.includes("Failed") ? "var(--v5-red)" : "var(--v5-teal-ink)" }}>
              {decisionStatus}
            </div>
          )}

          {!showSkipInput ? (
            <div>
              <div style={{ display: "flex", gap: "10px", alignItems: "center", flexWrap: "wrap" }}>
                <button
                  type="button"
                  className="v5-btn v5-btn-teal"
                  disabled={loggingDecision || !isActionable}
                  aria-disabled={loggingDecision || !isActionable}
                  title={!isActionable ? `Cannot mark TAKEN: ${notActionableReason}` : undefined}
                  onClick={handleLogTaken}
                  style={{
                    padding: "8px 16px", borderRadius: "var(--v5-r-xs)", fontWeight: "600",
                    cursor: !isActionable ? "not-allowed" : "pointer",
                    background: !isActionable ? "var(--v5-panel-2)" : "var(--v5-teal-dim)",
                    border: `1px solid ${!isActionable ? "var(--v5-line)" : "var(--v5-teal)"}`,
                    color: !isActionable ? "var(--v5-ink-dim)" : "var(--v5-teal-ink)",
                    opacity: !isActionable ? 0.6 : 1,
                  }}
                >
                  {loggingDecision ? "Logging..." : "✓ Log as TAKEN (Long)"}
                </button>
                <button
                  type="button"
                  className="v5-btn"
                  disabled={loggingDecision}
                  onClick={() => setShowSkipInput(true)}
                  style={{ padding: "8px 16px", borderRadius: "var(--v5-r-xs)", fontWeight: "600", cursor: "pointer", background: "var(--v5-panel-2)", border: "1px solid var(--v5-line)", color: "var(--v5-ink)" }}
                >
                  ✗ Log as SKIPPED
                </button>
              </div>
              {!isActionable && (
                <p
                  className="mono-num"
                  style={{ marginTop: "8px", fontSize: "12px", color: "var(--v5-red)" }}
                >
                  No valid size — this trade is not actionable; the gate says wait. ({notActionableReason})
                </p>
              )}
            </div>
          ) : (
            <form onSubmit={handleLogSkip} style={{ display: "flex", flexDirection: "column", gap: "8px", maxWidth: "400px" }}>
              <label htmlFor="skip-reason-input" className="mono-num" style={{ fontSize: "11px", color: "var(--v5-ink-dim)" }}>
                Reason for skipping this setup:
              </label>
              <input
                id="skip-reason-input"
                type="text"
                value={skipReason}
                onChange={(e) => setSkipReason(e.target.value)}
                placeholder="e.g. Regime cap, bad R:R, missed entry..."
                required
                className="v5-tp-select"
                style={{ width: "100%", padding: "6px 8px" }}
              />
              <div style={{ display: "flex", gap: "8px" }}>
                <button
                  type="submit"
                  disabled={loggingDecision}
                  className="v5-btn"
                  style={{ padding: "6px 12px", borderRadius: "var(--v5-r-xs)", background: "var(--v5-red-dim)", border: "1px solid var(--v5-red)", color: "var(--v5-red)", cursor: "pointer" }}
                >
                  Submit Skip
                </button>
                <button
                  type="button"
                  onClick={() => setShowSkipInput(false)}
                  className="v5-btn"
                  style={{ padding: "6px 12px", borderRadius: "var(--v5-r-xs)", background: "var(--v5-panel-2)", border: "1px solid var(--v5-line)", color: "var(--v5-ink)", cursor: "pointer" }}
                >
                  Cancel
                </button>
              </div>
            </form>
          )}
        </div>
      </div>

      <MentorChecklistPanel
        checklistEval={checklistEval}
        allChecklists={allChecklists}
        checklistId={checklistId}
        setChecklistId={setChecklistId}
        onToggle={handleCheckItem}
      />

      <ManagementContract guide={guide} symbol={symbol} />

      <EvidenceInspector date={date} symbol={symbol} guide={guide} debateSym={debateSym} isExpert={isExpert} />

      <button type="button" className="v5-tp-debate-link" onClick={onBackToDebate}>
        &rarr; back to debate card
      </button>

      {chartSymbol && (
        <ChartDrawer
          symbol={chartSymbol}
          date={date}
          defaultInterval="D"
          onClose={() => setChartSymbol(null)}
        />
      )}
    </div>
  );
}

function MentorChecklistPanel({
  checklistEval,
  allChecklists,
  checklistId,
  setChecklistId,
  onToggle,
}) {
  if (!checklistEval) return null;

  return (
    <Panel
      title="Mentor Discipline Checklist"
      className="v5-tp-mentor-checklist-panel"
    >
      <div className="v5-tp-mentor-select-row">
        <label htmlFor="mentor-checklist-select" className="v5-tp-select-label">Active Checklist:</label>
        <select
          id="mentor-checklist-select"
          value={checklistId}
          onChange={(e) => setChecklistId(e.target.value)}
          className="v5-tp-select"
        >
          {allChecklists.map((c) => (
            <option key={c.id} value={c.id}>
              {c.mentor} — {c.title}
            </option>
          ))}
        </select>
        <span className="v5-tp-checklist-summary mono-num">
          Score: {checklistEval.summary}
        </span>
      </div>

      {checklistEval.hard_fail_warning && (
        <div className="v5-tp-hard-fail-alert">
          ⚠ Hard fail advisory: {checklistEval.hard_fails.length} mandatory item(s) unchecked.
        </div>
      )}

      <ul className="v5-tp-mentor-checklist-list">
        {checklistEval.items.map((item) => {
          const isAuto = item.eval === "AUTO";
          const isPassed = item.state === "PASS";
          const isHard = item.kind === "hard";
          
          return (
            <li
              key={item.id}
              className={`v5-tp-mentor-item ${isHard ? "v5-tp-mentor-item-hard" : ""} ${
                !isPassed && isHard ? "v5-tp-mentor-item-failed" : ""
              }`}
            >
              <label className="v5-tp-mentor-item-label">
                <input
                  type="checkbox"
                  checked={isPassed}
                  disabled={isAuto}
                  onChange={() => onToggle(item.id, !isPassed)}
                />
                <span className={`v5-tp-mentor-item-text ${!isPassed && isHard ? "v5-tp-mentor-text-failed" : ""}`}>
                  {item.text}
                </span>
              </label>

              <div className="v5-tp-mentor-item-meta mono-num">
                {isAuto ? (
                  <span className={`v5-tp-badge v5-tp-badge-auto ${isPassed ? "pass" : "fail"}`}>
                    AUTO: {item.display} {isPassed ? "✓" : "✗"}
                  </span>
                ) : (
                  <span className="v5-tp-badge v5-tp-badge-manual">
                    MANUAL
                  </span>
                )}
                
                {item.source_cite && (
                  <span className="v5-tp-cite" title={item.source_cite}>
                    cite: {humanizeSourceCite(item.source_cite)}
                  </span>
                )}
              </div>
            </li>
          );
        })}
      </ul>
    </Panel>
  );
}
