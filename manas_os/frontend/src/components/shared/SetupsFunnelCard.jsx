import { useState } from "react";
import { postSetupDecision } from "../../api.js";
import { useDensity } from "../../DensityContext.jsx";
import Read from "../Read.jsx";
import AdvisorStrip from "../AdvisorStrip.jsx";
import { Callout, PosterBand, VisualCard } from "../poster/Primitives.jsx";

const GATE_NAMES = ["regime", "tradable", "trend", "fresh", "particip", "risk"];

export function RefusalFunnel({ setups, refusals }) {
  const byGate = refusals?.by_gate || {};
  const drops = Object.entries(byGate)
    .map(([gate, value]) => [displayGate(gate), Number(value || 0)])
    .filter(([, n]) => n > 0)
    .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]));
  const passed = Number(setups?.total_passed || setups?.candidates?.length || 0);
  const gateDrops = drops.reduce((sum, [, n]) => sum + n, 0);
  const universe = firstFiniteNumber(refusals?.universe, refusals?.total_universe, setups?.universe, gateDrops + passed);
  const screeners = firstFiniteNumber(refusals?.screeners, refusals?.screened, setups?.screeners, Math.max(universe - gateDrops, passed));
  const gated = firstFiniteNumber(refusals?.gates, refusals?.gated, setups?.gates, Math.max(passed, passed));
  const cap = setups?.governor?.max_cards ?? "-";
  const dropTitle = drops.length ? drops.map(([gate, n]) => `${gate}: -${n}`).join("\n") : "No gate drops returned";
  const stages = [
    ["Universe", universe],
    ["Screeners", screeners],
    ["Gates", gated],
    ["PASSED", passed],
  ];

  return (
    <section className="border border-hairline bg-card p-3" aria-label="Refusal funnel">
      <div className="mb-3 flex items-center justify-between gap-2">
        <div className="font-mono text-[12px] font-bold uppercase tracking-overline text-ink">Refusal funnel</div>
        <div className="font-mono text-[10px] uppercase tracking-overline text-ink3">selective cap: {cap}</div>
      </div>
      <div className="grid items-stretch gap-2 md:grid-cols-[1fr_auto_1fr_auto_1fr_auto_1fr]">
        {stages.map(([label, value], index) => [
          <div key={label} className={"border px-3 py-3 " + (label === "PASSED" ? "border-bull-border bg-bull-bg" : "border-hairline bg-raised")}>
            <div className="font-mono text-[10px] uppercase tracking-overline text-ink3">{label}</div>
            <div className="mt-1 font-display text-[26px] uppercase leading-none text-ink tabular-nums">{fmtCount(value)}</div>
          </div>,
          index < stages.length - 1 ? (
            <div key={`arrow-${index}`} className="hidden items-center font-display text-[24px] text-ink3 md:flex">-&gt;</div>
          ) : null,
        ])}
      </div>
      <div className="mt-2 flex flex-wrap gap-x-3 gap-y-1 font-mono text-[10px] uppercase tracking-overline text-ink3" title={dropTitle}>
        {drops.length ? drops.map(([gate, n]) => <span key={gate}>{gate} -{n}</span>) : <span>per-gate drops unavailable</span>}
      </div>
      <Callout className="mt-1">the feed that says NO - every survivor beat the full cascade</Callout>
    </section>
  );
}

export function CandidateCard({
  candidate,
  scanDate,
  onSymbolSelect,
  fallbackRank = 1,
  fallbackRankOf = 1,
  showFocusFields = false,
  advisorNotes = [],
}) {
  const { density } = useDensity();
  const expert = density === "expert";
  const band = candidate.grade === "A+" || candidate.grade === "A" ? "bull" : candidate.grade === "B" ? "warn" : "muted";
  const [decision, setDecision] = useState(null);
  const [skipOpen, setSkipOpen] = useState(false);
  const rank = candidate.rank ?? fallbackRank;
  const rankOf = candidate.rank_of ?? candidate.rank_total ?? fallbackRankOf;
  const family = candidate.setup_family || candidate.family || candidate.setup_type || "unclassified";
  const setup = candidate.setup || candidate.setup_type || "setup";
  const probation = isProbationFamily(candidate);
  const debate = candidate.agent_debate?.[0] || null;

  const submitDecision = async (nextDecision, skipReason = null) => {
    const result = await postSetupDecision({
      scan_date: scanDate,
      symbol: candidate.symbol,
      decision: nextDecision,
      ...(skipReason ? { skip_reason: skipReason } : {}),
      ...(nextDecision === "taken" ? { entry_price: candidate.entry, qty: candidate.suggested_qty } : {}),
    });
    setDecision({ decision: result.decision, skipReason });
    setSkipOpen(false);
  };

  const openCandidateChart = () => {
    onSymbolSelect?.({
      symbol: candidate.symbol,
      source: "setups",
      entry: candidate.entry,
      stop: candidate.stop,
      measured_move: candidate.measured_move,
    });
  };

  return (
    <VisualCard state={band} className="space-y-3">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <button
            type="button"
            onClick={openCandidateChart}
            className="font-display text-[24px] uppercase leading-none text-ink hover:underline"
          >
            {candidate.symbol}
          </button>
          <div className="mt-1 font-mono text-[10px] font-bold uppercase tracking-overline text-ink2">
            {setup} - {family} - rank {rank} of {rankOf} today
          </div>
        </div>
        <div className="flex shrink-0 flex-col items-end gap-1">
          {decision ? (
            <span className="rounded-chip border border-hairline bg-raised px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-overline text-ink2">
              LOGGED ok {decision.decision}{decision.skipReason ? ` (${decision.skipReason})` : ""}
            </span>
          ) : (
            <div className="flex items-center justify-end gap-1">
              <button type="button" onClick={() => submitDecision("taken")} className="border border-bull-border px-2 py-0.5 font-mono text-[9px] uppercase tracking-overline text-bull">
                TAKEN
              </button>
              <button type="button" onClick={() => setSkipOpen((v) => !v)} className="border border-hairline px-2 py-0.5 font-mono text-[9px] uppercase tracking-overline text-ink3">
                SKIPPED v
              </button>
            </div>
          )}
          {skipOpen && !decision && (
            <select
              autoFocus
              defaultValue=""
              onChange={(event) => event.target.value && submitDecision("skipped", event.target.value)}
              className="border border-hairline bg-raised px-1 py-0.5 font-mono text-[10px] text-ink2"
            >
              <option value="" disabled>reason</option>
              {["fear", "risk-too-wide", "regime-doubt", "better-name", "other"].map((reason) => (
                <option key={reason} value={reason}>{reason}</option>
              ))}
            </select>
          )}
        </div>
      </div>

      <GateDots gates={candidate.gates || candidate.gates_json} />
      {showFocusFields && <FocusFields candidate={candidate} />}

      <BeginnerCandidateRead candidate={candidate} />

      {!expert && (debate?.bull_case || debate?.bear_case) && (
        <div className="border border-hairline bg-raised p-3 space-y-2" data-testid="setups-agent-debate">
          <div className="font-mono text-[9px] font-bold uppercase tracking-overline text-ink3">
            Agent Analyst Debate{debate?.verdict ? ` - ${debate.verdict}${debate.conviction ? ` ${debate.conviction}/5` : ""}` : ""}
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            {debate?.bull_case && (
              <div className="space-y-1">
                <div className="font-mono text-[9px] uppercase tracking-overline text-bull font-bold">🟢 Bull Case</div>
                <p className="font-sans text-[11px] leading-snug text-ink2">{debate.bull_case}</p>
              </div>
            )}
            {debate?.bear_case && (
              <div className="space-y-1">
                <div className="font-mono text-[9px] uppercase tracking-overline text-bear font-bold">🔴 Bear Case</div>
                <p className="font-sans text-[11px] leading-snug text-ink2">{debate.bear_case}</p>
              </div>
            )}
          </div>
          {debate?.reasoning && (
            <div className="mt-2 pt-2 border-t border-hairline font-mono text-[9px] text-ink3 uppercase tracking-overline">
              {debate.reasoning}
            </div>
          )}
        </div>
      )}

      {expert ? (
        <div className="grid gap-2 md:grid-cols-[minmax(0,1.35fr)_minmax(0,1fr)]" data-testid="setups-expert-diagnostics">
          <RiskLadder plan={candidate.trade_plan} candidate={candidate} expert={expert} />
          <ExpectancyChip expectancy={candidate.expectancy} />
        </div>
      ) : (
        <RiskLadder plan={candidate.trade_plan} candidate={candidate} expert={expert} />
      )}

      <EvidenceTags evidence={candidate.evidence || []} expert={expert} />
      <AdvisorStrip notes={advisorNotes} scope="entry" symbol={candidate.symbol} />

      {probation && (
        <div className="w-fit rounded-chip border border-warn-border bg-warn-bg px-2 py-1 font-mono text-[9px] uppercase tracking-overline text-warn">
          unproven - building sample, half size
        </div>
      )}
    </VisualCard>
  );
}

function BeginnerCandidateRead({ candidate }) {
  const readiness = candidate.readiness ?? candidate.score ?? candidate.grade_score ?? null;
  const read = candidate.read || candidate.plain_read || candidate.reason || candidate.setup_read || "Passed the named setup checks.";
  return (
    <div className="grid gap-2 border border-hairline bg-raised p-2 sm:grid-cols-[auto_minmax(0,1fr)]" data-testid="setups-beginner-summary">
      <div>
        <div className="font-mono text-[9px] font-bold uppercase tracking-overline text-ink3">readiness</div>
        <div className="font-display text-[24px] uppercase leading-none text-ink tabular-nums">
          {readiness == null ? "PASS" : Number(readiness).toFixed(0)}
        </div>
      </div>
      <div className="font-sans text-[12px] leading-snug text-ink2">{read}</div>
    </div>
  );
}

export function EmptySetups({ mode, label = "0 setups tonight" }) {
  const noTrade = mode === "NO_TRADE";
  return (
    <div className="border border-dashed border-hairline bg-card px-4 py-8 text-center">
      <div className="font-mono text-[12px] font-bold uppercase tracking-overline text-ink">{label}</div>
      <p className="mx-auto mt-1 max-w-xl font-sans text-[12px] leading-snug text-ink3">Market is {mode}; sit tight.</p>
      <Read band={noTrade ? "bear" : "muted"} verdict={noTrade ? "SIT OUT" : "EMPTY"}>
        No current daily-price candidates passed the named evidence filters.
      </Read>
    </div>
  );
}

export function NearMisses({ nearMisses, loading, onRefresh }) {
  if (loading) {
    return (
      <PosterBand state="warn" kicker="[E] near-misses" title="near-miss lane loading">
        <div className="font-mono text-[11px] uppercase tracking-overline text-ink3">finding refused names that are closest to useful...</div>
      </PosterBand>
    );
  }
  if (!nearMisses.length) return null;
  return (
    <PosterBand state="warn" kicker="[E] near-misses" title="top refused names">
      <div className="divide-y divide-hairline border border-hairline bg-card">
        {nearMisses.slice(0, 10).map((item) => {
          // W2.2 gate proximity map: surface the per-gate distance value
          // (e.g. "0.9pp over", "0.3z under") and the watch/hard-no label
          // alongside the existing what-would-it-take chip text. All fields
          // come server-side from _distance_to_pass (one writer).
          const d = item.distance || {};
          const hasValue = d.value != null && d.unit;
          const hardNo = d.label === "hard no";
          return (
            <div key={`${item.candidate_date}-${item.symbol}-${item.failed_gate}`} className="flex flex-wrap items-center gap-x-2 gap-y-1 px-3 py-2 font-mono text-[10px] uppercase tracking-overline text-ink2">
              <span className="font-bold text-ink">{item.symbol}</span>
              <span>failed {item.failed_gate || "gate not returned"}</span>
              {hasValue && (
                <span className={"rounded-chip border px-1.5 py-0.5 " + (hardNo ? "border-bear-border bg-bear-bg text-bear" : "border-warn-border bg-warn-bg text-warn")} title={d.read || ""}>
                  {hardNo ? "hard no" : `${d.value}${d.unit} to pass`}
                </span>
              )}
              <span className="text-ink3">{d.what_would_it_take || item.reason || "reason not returned"}</span>
            </div>
          );
        })}
      </div>
    </PosterBand>
  );
}

function GateDots({ gates }) {
  const parsedGates = typeof gates === "string" ? safeJson(gates, []) : gates;
  const items = Array.isArray(parsedGates)
    ? parsedGates
    : GATE_NAMES.map((name) => {
        const value = parsedGates?.[name];
        return typeof value === "object" ? { name, ...value } : { name, passed: value !== false, reason: value === false ? "failed" : "" };
      });

  return (
    <div className="flex items-center gap-2 overflow-x-auto font-mono text-[9px] uppercase tracking-overline text-ink3">
      <span className="shrink-0">gates:</span>
      {GATE_NAMES.map((name) => {
        const g = items.find((item) => (item.name || item.gate || "").toLowerCase().includes(name));
        const passed = g?.passed ?? g?.pass ?? g?.ok ?? true;
        const title = gateEvidence(g) || (passed ? "passed" : "failed");
        return (
          <span key={name} title={title} className="inline-flex shrink-0 items-center gap-1 whitespace-nowrap text-ink2">
            <span className={"h-2.5 w-2.5 rounded-full border " + (passed ? "border-bull-border bg-bull" : "border-bear-border bg-bear")} />
            <span>{name}</span>
          </span>
        );
      })}
    </div>
  );
}

function FocusFields({ candidate }) {
  const fields = [
    ["base age", candidate.base_age],
    ["listed", candidate.days_since_listing],
    ["circuit", candidate.circuit_state ?? candidate.circuit],
  ].filter(([, value]) => value != null && value !== "");
  if (!fields.length) return null;
  return (
    <div className="grid gap-1 border border-info-border bg-info-bg p-2 font-mono text-[9px] uppercase tracking-overline text-info sm:grid-cols-3">
      {fields.map(([label, value]) => (
        <div key={label}>
          <div className="text-ink3">{label}</div>
          <div className="font-bold text-ink">{formatFocusValue(label, value)}</div>
        </div>
      ))}
    </div>
  );
}

function RiskLadder({ plan, candidate, expert = false }) {
  const entry = plan?.entry ?? candidate?.entry;
  const stop = plan?.stop ?? candidate?.stop;
  const target = candidate?.measured_move ?? candidate?.target ?? plan?.target;
  const risk = entry != null && stop != null ? Math.max(0, Number(entry) - Number(stop)) : null;
  const reward = entry != null && target != null ? Math.max(0, Number(target) - Number(entry)) : null;
  const rr = risk ? reward / risk : (plan?.rr ?? candidate?.rr);
  const stopPct = entry != null && stop != null && Number(entry) !== 0 ? (Math.abs(Number(entry) - Number(stop)) / Number(entry)) * 100 : null;
  const stopSource = plan?.stop_source || candidate?.stop_source || plan?.source;
  const qty = plan?.suggested_qty ?? candidate?.suggested_qty ?? plan?.qty ?? candidate?.qty;
  const riskRupees = plan?.risk_rupees ?? plan?.risk_inr ?? candidate?.risk_rupees ?? candidate?.risk_inr;
  return (
    <div className="border border-hairline bg-card p-2">
      <div className="mb-2 font-mono text-[9px] font-bold uppercase tracking-overline text-ink3">
        {expert ? "Plan - full math" : "Plan"}
      </div>
      <div className="space-y-1 font-mono text-[10px] uppercase tracking-overline text-ink2">
        <div>entry {fmt(entry)} - stop {fmt(stop)}</div>
        <div>qty {qty ?? "-"}{riskRupees == null ? "" : ` - risk Rs ${fmtCount(riskRupees)}`}</div>
        {expert && (
          <>
            <div>stop {stopPct == null ? "-" : `${stopPct.toFixed(1)}%`}{stopSource ? ` - ${stopSource}` : ""}</div>
            <div>R:R {rr == null ? "-" : Number(rr).toFixed(2)}</div>
          </>
        )}
        <div>watch-for: {plan?.watch_for_failure || candidate?.watch_for || "not returned"}</div>
      </div>
    </div>
  );
}

function ExpectancyChip({ expectancy }) {
  if (!expectancy) {
    return (
      <div className="border border-hairline bg-raised p-2 font-mono text-[10px] uppercase tracking-overline text-ink3">
        <div className="mb-1 font-mono text-[9px] font-bold uppercase tracking-overline text-ink3">Expectancy</div>
        no expectancy cell returned
      </div>
    );
  }
  const system = expectancy.system;
  const personal = expectancy.personal;
  const label = expectancy.label || expectancy.cell || "setup x regime";
  return (
    <div className="border border-info-border bg-info-bg p-2">
      <div className="mb-1 font-mono text-[9px] font-bold uppercase tracking-overline text-info">Expectancy</div>
      <div className="font-mono text-[10px] leading-snug text-info">
        {system ? `${label}: ${pct(system.hit_rate)} hit - ${signed(system.median_r ?? system.posterior_r, "R")} med (n=${system.n}, sys)` : `${label}: system sample not returned`}
      </div>
      <div className="font-mono text-[10px] leading-snug text-info">
        {expectancy.personal_note || (personal ? `yours: n=${personal.n ?? "-"}${personal.n != null && personal.n < 10 ? " thin" : ""}` : "yours: personal sample not returned")}
      </div>
    </div>
  );
}

const EVIDENCE_LABELS = {
  ep: "Earnings Power",
  "ipo base": "IPO Base",
  "launch-pad": "Launch Pad",
  "near-pivot": "Near Pivot",
  ants: "Accumulation",
  "asm-clear": "No ASM Flag",
  "rvol>=1.5": "Volume Surge",
  "delivery>=60": "Delivery Confirmed",
  "eps yoy": "EPS Growth YoY",
  theme: "Sector",
  "positive-earnings-reaction": "Earnings Reaction",
  "earnings-gap-up": "Earnings Gap",
  "episodic-pivot": "Episodic Pivot",
  "top-gainers": "Top Gainer",
  "gap-up": "Gap Up",
  "past-winners": "Past Winner",
  "highest-volume": "High Volume",
  "volume-spike": "Volume Spike",
  "volume-footprint": "Volume Footprint",
};

const PROMOTED_ELSEWHERE = new Set(["rs>=70", "abs-strength", "eps-growth", "delivery>=60", "exit-conflict", "wide-stop-vs-adr"]);

function EvidenceTags({ evidence, expert = false }) {
  const kept = evidence.filter((e) => {
    const key = String(e.filter || "").toLowerCase();
    if (PROMOTED_ELSEWHERE.has(key)) return false;
    if (e.value === "hit" && !EVIDENCE_LABELS[key]) return false;
    return true;
  });
  if (!kept.length) return null;
  return (
    <div className="font-sans text-[11px] leading-snug text-ink2">
      <span className="font-mono text-[9px] font-bold uppercase tracking-overline text-ink3">evidence: </span>
      {kept.map((e) => `${evidenceLabel(e.filter)}${expert && e.value && e.value !== "hit" ? ` ${e.value}` : ""}`).join(" - ")}
    </div>
  );
}

function evidenceLabel(filter) {
  const key = String(filter || "").toLowerCase();
  if (EVIDENCE_LABELS[key]) return EVIDENCE_LABELS[key];
  return String(filter || "")
    .replace(/[-_]/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function gateEvidence(g) {
  const value = g?.evidence || g?.reason || g?.detail || g?.message || "";
  if (Array.isArray(value)) return value.filter(Boolean).join("; ");
  if (typeof value === "object" && value != null) return JSON.stringify(value);
  return String(value || "").trim();
}

function displayGate(gate) {
  return String(gate || "unknown").replace(/_/g, "-");
}

function formatFocusValue(label, value) {
  if (label === "circuit") return String(value);
  return Number.isFinite(Number(value)) ? `${Number(value)}d` : String(value);
}

function isProbationFamily(candidate) {
  const haystack = [
    candidate?.setup,
    candidate?.setup_type,
    candidate?.setup_family,
    candidate?.family,
    candidate?.pattern_label,
  ].map((value) => String(value || "").toLowerCase()).join(" ");
  return haystack.includes("ipo") || haystack.includes("flag");
}

function firstFiniteNumber(...candidates) {
  for (const c of candidates) {
    if (c == null) continue;
    const n = parseFloat(c);
    if (Number.isFinite(n)) return n;
  }
  return null;
}

function safeJson(value, fallback) {
  try {
    return JSON.parse(value);
  } catch {
    return fallback;
  }
}

function fmt(value) {
  if (value == null) return "-";
  return Number(value).toFixed(2).replace(/\.00$/, "");
}

function fmtCount(value) {
  if (value == null || value === "" || Number.isNaN(Number(value))) return "-";
  return Number(value).toLocaleString("en-IN", { maximumFractionDigits: 0 });
}

function signed(value, suffix = "") {
  if (value == null) return "-";
  return `${Number(value) > 0 ? "+" : ""}${Number(value).toFixed(2).replace(/\.00$/, "")}${suffix}`;
}

function pct(value) {
  if (value == null) return "-";
  const n = Number(value);
  return `${(n <= 1 ? n * 100 : n).toFixed(0)}%`;
}
