import { useEffect, useMemo, useRef, useState } from "react";
import * as echarts from "echarts";
import { addWatchlist, getSetups, getSetupsRefusals, postSetupDecision } from "../api.js";
import DataStamp from "./DataStamp.jsx";
import Read from "./Read.jsx";
import SymbolCard from "./SymbolCard.jsx";

const SETUP_TYPES = ["", "Pullback", "Near pivot", "Pocket pivot", "Shakeout", "Launch Pad", "EP", "IPO Base"];
const RS_LEVELS = ["", "70", "50", "40"];
const GRADE_LEVELS = ["", "A", "B", "C"];

export default function SetupsPage({ posture, onSymbolSelect }) {
  const mode = posture || "UNKNOWN";
  const noTrade = mode === "NO_TRADE";
  const [filters, setFilters] = useState({ setup: "", minRs: "", grade: "" });
  const [lens, setLens] = useState("all");
  const [state, setState] = useState({ loading: true, error: null, data: null });
  const [refusals, setRefusals] = useState({ loading: true, error: null, data: null });

  const load = () => {
    setState({ loading: true, error: null, data: null });
    getSetups({
      setup: filters.setup || undefined,
      minRs: filters.minRs || undefined,
      grade: filters.grade || undefined,
    })
      .then((d) => setState({ loading: false, error: null, data: d }))
      .catch((e) => setState({ loading: false, error: e.message, data: null }));
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters.setup, filters.minRs, filters.grade]);

  useEffect(() => {
    let cancelled = false;
    setRefusals({ loading: true, error: null, data: null });
    getSetupsRefusals({ limit: 50 })
      .then((d) => !cancelled && setRefusals({ loading: false, error: null, data: d }))
      .catch((e) => !cancelled && setRefusals({ loading: false, error: e.message, data: null }));
    return () => {
      cancelled = true;
    };
  }, []);

  const gateText =
    mode === "RISK_ON"
      ? "RISK-ON - A and B setups are allowed."
      : mode === "SELECTIVE"
        ? "SELECTIVE - showing A-setups only."
        : mode === "DEFENSIVE"
          ? "DEFENSIVE - only flawless A-setups should survive."
          : mode === "NO_TRADE"
            ? "NO-TRADE - no new setups should be acted on."
            : mode === "STALE"
              ? "STALE - candidates are informational until data is fresh."
              : "UNKNOWN - waiting for regime posture.";

  // T3.7a fix: when the IPO+EP focus lens is on, render from the backend's
  // focus_candidates (pre-cap, EP/IPO-base from the full ranked list) instead
  // of filtering the already-governor-capped `candidates` array — otherwise
  // the lens shows "0 setups" whenever the top-cap cards are pullbacks.
  const candidates = lens === "ipo_ep"
    ? (state.data?.focus_candidates || [])
    : filteredCandidates(state.data?.candidates || [], lens);

  return (
    <section data-testid="setups-page" className="space-y-4">
      <div className="border border-hairline bg-card p-3">
        <div className="mb-2 font-mono text-[10px] font-bold uppercase tracking-overline text-ink3">
          Filter bar
        </div>
        <div className="mb-3 border border-hairline bg-raised px-3 py-2 font-mono text-[11px] uppercase tracking-overline text-ink2">
          {gateText}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <SelectLabel
            label="setup type"
            value={filters.setup}
            items={SETUP_TYPES}
            labels={["All setups", "Pullback", "Near pivot", "Pocket pivot", "Shakeout", "Launch Pad", "EP", "IPO Base"]}
            onChange={(setup) => setFilters((f) => ({ ...f, setup }))}
          />
          <SelectLabel
            label="min rs"
            value={filters.minRs}
            items={RS_LEVELS}
            labels={["Any RS", "RS 70+", "RS 50+", "RS 40+"]}
            onChange={(minRs) => setFilters((f) => ({ ...f, minRs }))}
          />
          <div className="ml-auto">
            <SelectLabel
              label="min grade"
              value={filters.grade}
              items={GRADE_LEVELS}
              labels={["Any grade", "A or better", "B or better", "C or better"]}
              onChange={(grade) => setFilters((f) => ({ ...f, grade }))}
            />
          </div>
          <div className="flex gap-1">
            {["all", "ipo_ep"].map((key) => (
              <button
                key={key}
                type="button"
                onClick={() => setLens(key)}
                className={
                  "border px-2 py-1 font-mono text-[10px] uppercase tracking-overline " +
                  (lens === key ? "border-ink bg-ink text-white" : "border-hairline text-ink3 hover:text-ink")
                }
              >
                {key === "ipo_ep" ? "IPO+EP Focus" : "All"}
              </button>
            ))}
          </div>
        </div>
      </div>

      {lens === "ipo_ep" && <FocusNote />}
      <RefusalFunnel setups={state.data} refusals={refusals.data} />

      {state.loading ? (
        <div className="border border-hairline bg-card px-4 py-8 font-mono text-[11px] text-ink3">
          loading setups...
        </div>
      ) : state.error ? (
        <div className="border border-bear-border bg-bear-bg px-4 py-6 font-mono text-[11px] text-bear">
          {state.error}
        </div>
      ) : noTrade ? (
        <EmptySetups mode={mode} />
      ) : !state.data?.available || candidates.length === 0 ? (
        <EmptySetups mode={mode} />
      ) : (
        <div className="grid gap-3 lg:grid-cols-2 xl:grid-cols-3">
          {candidates.map((candidate, idx) => (
            <CandidateCard
              key={`${candidate.symbol}-${candidate.setup_type || candidate.setup}`}
              candidate={candidate}
              scanDate={state.data.as_of}
              onSymbolSelect={onSymbolSelect}
              focus={lens === "ipo_ep"}
              fallbackRank={idx + 1}
              fallbackRankOf={candidates.length}
            />
          ))}
        </div>
      )}

      <NearMisses refusals={refusals.data?.refusals || []} />
      <DataStamp />
    </section>
  );
}

function EChart({ option, className = "h-48" }) {
  const ref = useRef(null);
  useEffect(() => {
    if (!ref.current) return undefined;
    const chart = echarts.init(ref.current);
    chart.setOption(option);
    const resize = () => chart.resize();
    window.addEventListener("resize", resize);
    return () => {
      window.removeEventListener("resize", resize);
      chart.dispose();
    };
  }, [option]);
  return <div ref={ref} className={className} />;
}

function RefusalFunnel({ setups, refusals }) {
  const byGate = refusals?.by_gate || {};
  const drops = Object.entries(byGate).sort((a, b) => Number(b[1]) - Number(a[1]));
  const passed = Number(setups?.total_passed || setups?.candidates?.length || 0);
  const gateDrops = drops.reduce((sum, [, n]) => sum + Number(n || 0), 0);
  const universe = Math.max(gateDrops + passed, passed);
  const tradabilityDrop = Number(byGate.tradability || byGate.tradable || 0);
  const pool = Math.max(universe - tradabilityDrop, passed);
  const gated = Math.max(passed + Number(byGate.risk || 0), passed);
  const cap = setups?.governor?.max_cards ?? "-";
  const data = useMemo(() => [
    { name: "Universe", value: universe },
    { name: "Pool", value: pool },
    { name: "Gates", value: gated },
    { name: "Passed", value: passed },
  ], [gated, passed, pool, universe]);
  const option = useMemo(() => ({
    tooltip: {
      trigger: "item",
      formatter: (p) => {
        const gateLines = drops.map(([gate, n]) => `${gate}: -${n}`).join("<br/>");
        return `${p.name}: ${p.value}<br/>${gateLines || "No gate drops"}`;
      },
    },
    series: [{
      type: "funnel",
      left: "4%",
      top: 12,
      bottom: 8,
      width: "92%",
      minSize: "20%",
      maxSize: "100%",
      sort: "none",
      label: { color: "#2f3437", fontSize: 11, formatter: "{b} {c}" },
      itemStyle: { borderColor: "#f8faf8", borderWidth: 1 },
      data,
    }],
  }), [data, drops]);
  return (
    <section className="border border-hairline bg-card p-3">
      <div className="mb-2 flex items-center justify-between gap-2">
        <div className="font-mono text-[12px] font-bold uppercase tracking-overline text-ink">
          Refusal funnel
        </div>
        <div className="font-mono text-[10px] uppercase tracking-overline text-ink3">
          selective cap: {cap}
        </div>
      </div>
      <EChart option={option} className="h-44" />
      <div className="mt-2 flex flex-wrap gap-2 font-mono text-[10px] uppercase tracking-overline text-ink3">
        {drops.slice(0, 5).map(([gate, n]) => <span key={gate}>{gate} -{n}</span>)}
      </div>
    </section>
  );
}

function filteredCandidates(candidates, lens) {
  if (lens !== "ipo_ep") return candidates;
  return candidates.filter((c) => ["ep", "ipo_base"].includes(c.setup_type));
}

function FocusNote() {
  return (
    <div className="border border-info-border bg-info-bg px-3 py-2">
      <div className="font-mono text-[10px] font-bold uppercase tracking-overline text-info">
        IPO+EP Focus Center
      </div>
      <p className="font-sans text-[12px] text-ink2">
        Filtered lens on the same Setups feed. Same rows, same readiness number; only EP and IPO-base patterns are shown.
      </p>
    </div>
  );
}

function SelectLabel({ label, value, items, labels, onChange }) {
  return (
    <label className="flex items-center gap-1 font-mono text-[10px] uppercase tracking-overline text-ink3">
      {label}
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="border border-hairline bg-raised px-2 py-1 text-[10px] text-ink2"
      >
        {items.map((item, idx) => (
          <option key={item || "all"} value={item}>
            {labels[idx]}
          </option>
        ))}
      </select>
    </label>
  );
}

function EmptySetups({ mode }) {
  const noTrade = mode === "NO_TRADE";
  return (
    <div className="border border-dashed border-hairline bg-card px-4 py-8 text-center">
      <div className="font-mono text-[12px] font-bold uppercase tracking-overline text-ink">
        0 setups tonight
      </div>
      <p className="mx-auto mt-1 max-w-xl font-sans text-[12px] leading-snug text-ink3">
        Market is {mode}; sit tight.
      </p>
      <Read band={noTrade ? "bear" : "muted"} verdict={noTrade ? "SIT OUT" : "EMPTY"}>
        No current daily-price candidates passed the named evidence filters.
      </Read>
    </div>
  );
}

function CandidateCard({ candidate, scanDate, onSymbolSelect, focus = false, fallbackRank = 1, fallbackRankOf = 1 }) {
  const band = candidate.grade === "A+" || candidate.grade === "A" ? "bull" : candidate.grade === "B" ? "warn" : "muted";
  const [decision, setDecision] = useState(null);
  const [skipOpen, setSkipOpen] = useState(false);
  const add = async () => {
    await addWatchlist(candidate.symbol, candidate.setup);
  };
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
  const openCandidateChart = (payload) => {
    onSymbolSelect?.({
      ...payload,
      source: "setups",
      entry: candidate.entry,
      stop: candidate.stop,
      measured_move: candidate.measured_move,
    });
  };
  const confluenceCount = candidate.confluence_count;
  const rank = candidate.rank ?? fallbackRank;
  const rankOf = candidate.rank_of ?? candidate.rank_total ?? fallbackRankOf;
  return (
    <SymbolCard
      symbol={candidate.symbol}
      rs={candidate.rs}
      rsAsOf={candidate.rs_as_of}
      deliveryPct={candidate.delivery_pct}
      deliveryAsOf={candidate.delivery_as_of}
      verdictBand={band}
      onSelect={openCandidateChart}
    >
      <div className="mb-2 flex items-start justify-between gap-2">
        <div>
          <div className="flex items-center gap-1.5 font-mono text-[11px] font-bold uppercase tracking-overline text-ink">
            {candidate.grade} - {candidate.setup}
            {confluenceCount != null && (
              <span className="rounded-chip border border-hairline bg-raised px-1 py-px text-[9px] font-bold tabular-nums text-ink2">
                {confluenceCount} screens
              </span>
            )}
          </div>
          <div className="mt-1 w-fit rounded-chip border border-hairline bg-raised px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-overline text-ink2">
            rank {rank} of {rankOf} today
          </div>
          <div className="font-sans text-[11px] text-ink3">Trade readiness {candidate.readiness}/100</div>
        </div>
        <div className="flex flex-col items-end gap-1">
          {decision ? (
            <span className="rounded-chip border border-hairline bg-raised px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-overline text-ink2">
              LOGGED ok {decision.decision}{decision.skipReason ? ` (${decision.skipReason})` : ""}
            </span>
          ) : (
            <div className="flex items-center justify-end gap-1">
              <button
                type="button"
                onClick={() => submitDecision("taken")}
                className="border border-bull-border px-2 py-0.5 font-mono text-[9px] uppercase tracking-overline text-bull"
              >
                TAKEN
              </button>
              <button
                type="button"
                onClick={() => setSkipOpen((v) => !v)}
                className="border border-hairline px-2 py-0.5 font-mono text-[9px] uppercase tracking-overline text-ink3"
              >
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
          <span className="font-mono text-[20px] font-bold tabular-nums text-ink">{Number(candidate.readiness || 0).toFixed(0)}</span>
        </div>
      </div>

      <ScoreBreakdown breakdown={candidate.score_breakdown} />
      <GateDots gates={candidate.gates} />
      {focus && <FocusFields candidate={candidate} />}

      <div className="mb-2 grid gap-2 md:grid-cols-[1.5fr_1fr]">
        <TradePlan plan={candidate.trade_plan} candidate={candidate} />
        <ExpectancyChip expectancy={candidate.expectancy} />
      </div>

      {candidate.measured_move != null && candidate.measured_move_note && (
        <div className="mb-2 font-sans text-[10px] italic leading-snug text-ink3">
          measured move (if it works): {candidate.measured_move_note}
        </div>
      )}

      <div className="mb-2 flex flex-wrap gap-1">
        {(candidate.evidence || []).slice(0, 8).map((e) => (
          <span
            key={`${e.filter}-${e.value}`}
            title={String(e.value)}
            className="rounded-chip border border-info-border bg-info-bg px-1.5 py-0.5 font-mono text-[9px] text-info"
          >
            {e.filter}
          </span>
        ))}
      </div>

      <Read band={band}>{candidate.read}</Read>

      <div className="mt-2 flex justify-end gap-1">
        <button
          type="button"
          onClick={add}
          className="border border-hairline px-2 py-0.5 font-mono text-[10px] uppercase tracking-overline text-ink2 hover:border-ink hover:text-ink"
        >
          + Watchlist
        </button>
      </div>
    </SymbolCard>
  );
}

function GateDots({ gates }) {
  const names = ["regime", "tradable", "trend", "fresh", "particip", "risk"];
  const items = Array.isArray(gates)
    ? gates
    : names.map((name) => {
        const value = gates?.[name];
        return typeof value === "object" ? { name, ...value } : { name, passed: value !== false, reason: value === false ? "failed" : "passed" };
      });
  return (
    <div className="mb-2 flex flex-wrap items-center gap-1 font-mono text-[9px] uppercase tracking-overline text-ink3">
      <span>gates:</span>
      {names.map((name) => {
        const g = items.find((item) => (item.name || item.gate || "").toLowerCase().includes(name));
        const passed = g?.passed ?? g?.ok ?? true;
        return (
          <span key={name} title={g?.reason || g?.detail || (passed ? "passed" : "failed")} className="inline-flex items-center gap-1">
            <span className={"h-2 w-2 rounded-full " + (passed ? "bg-bull" : "bg-bear")} />
            {name}
          </span>
        );
      })}
    </div>
  );
}

function FocusFields({ candidate }) {
  const growth = candidate.score_breakdown?.eps_growth_pctile;
  const rr = candidate.trade_plan?.rr;
  return (
    <div className="mb-2 grid grid-cols-4 gap-1 border border-info-border bg-info-bg p-2 font-mono text-[9px] uppercase tracking-overline text-info">
      <Metric label="pattern" value={candidate.pattern_label || candidate.setup} />
      <Metric label="readiness" value={String(Math.round(candidate.readiness || 0))} />
      <Metric label="age" value={candidate.days_since_listing != null ? `${candidate.days_since_listing}d` : candidate.base_age != null ? `${candidate.base_age}d` : "-"} />
      <Metric label="R:R" value={rr == null ? "-" : `${Number(rr).toFixed(2)}R`} />
      <Metric label="growth" value={growth == null ? "-" : `${Number(growth).toFixed(0)} pctile`} />
      <Metric label="circuit" value="clear" />
    </div>
  );
}

function TradePlan({ plan, candidate }) {
  const entry = plan?.entry ?? candidate?.entry;
  const stop = plan?.stop ?? candidate?.stop;
  const rr = plan?.rr ?? candidate?.rr ?? candidate?.trade_plan?.rr;
  const qty = plan?.suggested_qty ?? candidate?.suggested_qty;
  return (
    <div className="border border-hairline bg-card p-2">
      <div className="mb-1 font-mono text-[9px] font-bold uppercase tracking-overline text-ink3">Plan</div>
      <div className="grid gap-1 font-sans text-[11px] leading-snug text-ink2">
        {plan?.entry_trigger && <div>{plan.entry_trigger}</div>}
        <div className="font-mono text-[10px] uppercase tracking-overline text-ink3">
          entry {fmt(entry)} - stop {fmt(stop)} - R:R {rr == null ? "-" : Number(rr).toFixed(2)}
        </div>
        <div className="font-mono text-[10px] uppercase tracking-overline text-ink3">
          suggested qty {qty == null ? "-" : Number(qty).toLocaleString("en-IN")}
        </div>
        {plan?.watch_for_failure && <div>{plan.watch_for_failure}</div>}
      </div>
    </div>
  );
}

function ExpectancyChip({ expectancy }) {
  if (!expectancy) {
    return (
      <div className="border border-hairline bg-raised p-2 font-mono text-[10px] uppercase tracking-overline text-ink3">
        Expectancy: no cell yet
      </div>
    );
  }
  const system = expectancy.system;
  const personal = expectancy.personal;
  return (
    <div className="border border-info-border bg-info-bg p-2">
      <div className="mb-1 font-mono text-[9px] font-bold uppercase tracking-overline text-info">Expectancy</div>
      <div className="font-mono text-[10px] leading-snug text-info">
        {system ? `system: ${pct(system.hit_rate)} hit, ${signed(system.posterior_r, "R")} post (n=${system.n})` : "system: no sample"}
      </div>
      <div className="font-mono text-[10px] leading-snug text-info">
        {expectancy.personal_note || (personal ? `yours: ${signed(personal.posterior_r, "R")} post (n=${personal.n})` : "yours: no sample")}
      </div>
    </div>
  );
}

function NearMisses({ refusals }) {
  if (!refusals.length) return null;
  return (
    <details className="border border-hairline bg-card p-3">
      <summary className="cursor-pointer font-mono text-[11px] font-bold uppercase tracking-overline text-ink">
        Near-misses
      </summary>
      <ul className="mt-2 grid gap-1 font-mono text-[10px] text-ink3">
        {refusals.slice(0, 10).map((r) => (
          <li key={`${r.symbol}-${r.failed_gate}-${r.reason}`}>
            {r.symbol} - failed {r.failed_gate}: {r.reason}
          </li>
        ))}
      </ul>
    </details>
  );
}

function ScoreBreakdown({ breakdown }) {
  if (!breakdown) return null;
  const rows = [
    breakdown.confluence != null && { label: "confluence", value: `${breakdown.confluence}x` },
    breakdown.theme && { label: "theme", value: breakdown.theme },
    breakdown.eps_yoy != null && { label: "eps yoy", value: `+${Number(breakdown.eps_yoy).toFixed(0)}%` },
    breakdown.rs != null && { label: "rs", value: Number(breakdown.rs).toFixed(0) },
    breakdown.delivery != null && { label: "delivery", value: `${Number(breakdown.delivery).toFixed(0)}%` },
    breakdown.signal && { label: "signal", value: breakdown.signal },
    breakdown.ants && { label: "ants", value: "yes" },
    breakdown.setup_type && { label: "type", value: breakdown.setup_type },
    breakdown.abs_strength_pctile != null && { label: "abs str", value: `${Number(breakdown.abs_strength_pctile).toFixed(0)} pctile` },
    breakdown.eps_growth_pctile != null && { label: "eps growth", value: `${Number(breakdown.eps_growth_pctile).toFixed(0)} pctile` },
  ].filter(Boolean);
  if (rows.length === 0) return null;
  return (
    <div className="mb-2 flex flex-wrap gap-x-3 gap-y-0.5 font-mono text-[9px] uppercase tracking-overline text-ink3">
      {rows.map((r) => (
        <span key={r.label}>
          {r.label} <span className="text-ink2">{r.value}</span>
        </span>
      ))}
    </div>
  );
}

function Metric({ label, value }) {
  return (
    <div>
      <div className="uppercase tracking-overline text-ink3">{label}</div>
      <div className="font-bold text-ink">{value}</div>
    </div>
  );
}

function fmt(value) {
  if (value == null) return "-";
  return Number(value).toFixed(2).replace(/\.00$/, "");
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
