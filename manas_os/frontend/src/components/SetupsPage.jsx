import { useEffect, useMemo, useRef, useState } from "react";
import * as echarts from "echarts";
import {
  addWatchlist,
  getSetups,
  getSetupsNearMisses,
  getSetupsRefusals,
  getSymbolOhlc,
  overrideSetup,
  postSetupDecision,
  trackWatchlistCandidate,
} from "../api.js";
import DataStamp from "./DataStamp.jsx";
import Read from "./Read.jsx";
import { AnnotatedChart, Callout, Caption, MetricBar, MetricTape, PosterBand, PosterCanvas, ProximityBar, SectionBadge, Verdict, VisualCard } from "./poster/Primitives.jsx";

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
  const [nearMisses, setNearMisses] = useState({ loading: true, error: null, data: null });

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
    setNearMisses({ loading: true, error: null, data: null });
    getSetupsRefusals({ limit: 50 })
      .then((d) => !cancelled && setRefusals({ loading: false, error: null, data: d }))
      .catch((e) => !cancelled && setRefusals({ loading: false, error: e.message, data: null }));
    getSetupsNearMisses({ limit: 12 })
      .then((d) => !cancelled && setNearMisses({ loading: false, error: null, data: d }))
      .catch((e) => !cancelled && setNearMisses({ loading: false, error: e.message, data: null }));
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
    <PosterCanvas data-testid="setups-page" className="space-y-4">
      <SetupsPosterHeader mode={mode} data={state.data} gateText={gateText} candidates={candidates} />
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

      <NearMisses
        nearMisses={nearMisses.data?.near_misses || []}
        loading={nearMisses.loading}
        onRefresh={() => {
          getSetupsNearMisses({ limit: 12 })
            .then((d) => setNearMisses({ loading: false, error: null, data: d }))
            .catch((e) => setNearMisses({ loading: false, error: e.message, data: null }));
        }}
      />
      <DataStamp />
    </PosterCanvas>
  );
}

function SetupsPosterHeader({ mode, data, gateText, candidates }) {
  const cap = data?.governor?.max_cards ?? data?.max_cards ?? "-";
  const passed = data?.total_passed ?? candidates.length ?? 0;
  const state = mode === "RISK_ON" ? "bull" : mode === "SELECTIVE" ? "warn" : mode === "DEFENSIVE" || mode === "NO_TRADE" ? "bear" : "muted";
  return (
    <PosterBand state={state} kicker="setups">
      <SectionBadge label="SETUPS" state={state} />
      <div className="mt-3">
        <Verdict>{passed} NAMES PASSED - {mode} CAP {cap}</Verdict>
        <Caption>{gateText}</Caption>
      </div>
      <MetricTape
        items={[
          { label: "passed", value: passed, sub: "survivors after gates", state },
          { label: "display cap", value: cap, sub: "governor law", state: "muted" },
          { label: "posture", value: mode, sub: "sets action size", state },
          { label: "next action", value: passed ? "review cards" : "track misses", sub: "decision before table", state: passed ? "bull" : "warn" },
        ]}
      />
    </PosterBand>
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
  const FUNNEL_COLORS = ["#5b6472", "#175cd3", "#9a5b00", "#0f7a3d"]; // muted, info, warn, bull — universe -> passed
  const data = useMemo(() => [
    { name: "Universe", value: universe, itemStyle: { color: FUNNEL_COLORS[0] } },
    { name: "Pool", value: pool, itemStyle: { color: FUNNEL_COLORS[1] } },
    { name: "Gates", value: gated, itemStyle: { color: FUNNEL_COLORS[2] } },
    { name: "Passed", value: passed, itemStyle: { color: FUNNEL_COLORS[3] } },
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
      left: "6%",
      top: 8,
      bottom: 8,
      width: "88%",
      minSize: "24%",
      maxSize: "100%",
      gap: 3,
      sort: "none",
      label: { position: "inside", color: "#f8faf8", fontSize: 11, fontWeight: "bold", formatter: "{b}  {c}" },
      itemStyle: { borderWidth: 0 },
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
      <Callout className="mt-1">the feed that says NO — every survivor beat the full cascade</Callout>
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
  const CAUTION_FILTERS = new Set(["exit-conflict", "wide-stop-vs-adr"]);
  const cautions = (candidate.evidence || []).filter((e) => CAUTION_FILTERS.has(String(e.filter || "").toLowerCase()));
  return (
    <VisualCard state={band} className="space-y-3">
      <div className="flex items-start justify-between gap-2">
        <div>
          <button
            type="button"
            onClick={() => openCandidateChart({ symbol: candidate.symbol })}
            className="font-display text-[24px] uppercase leading-none text-ink hover:underline"
          >
            {candidate.symbol}
          </button>
          <div className="mt-1 flex flex-wrap items-center gap-1.5 font-mono text-[10px] font-bold uppercase tracking-overline text-ink2">
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
          <span
            title="Trade readiness 0-100: how many of this setup's named checks are in place right now."
            className="flex items-baseline gap-1 font-mono text-ink"
          >
            <span className="text-[9px] uppercase tracking-overline text-ink3">ready</span>
            <span className="text-[20px] font-bold tabular-nums">{Number(candidate.readiness || 0).toFixed(0)}</span>
            <span className="text-[10px] text-ink3">/100</span>
          </span>
        </div>
      </div>

      <AnnotatedChart className="h-48">
        <MiniSetupChart candidate={candidate} scanDate={scanDate} />
      </AnnotatedChart>

      {cautions.map((c) => (
        <div key={c.filter} className="border border-warn-border bg-warn-bg px-2 py-1.5 font-sans text-[11px] leading-snug text-warn">
          <span className="font-mono text-[9px] font-bold uppercase tracking-overline">caution —</span> {c.value}
        </div>
      ))}

      <MetricStrip candidate={candidate} />
      <GateDots gates={candidate.gates} />
      {focus && <FocusFields candidate={candidate} />}

      <SetupStoryboard candidate={candidate} />

      <div className="grid gap-2 md:grid-cols-[1.2fr_1fr]">
        <RiskLadder plan={candidate.trade_plan} candidate={candidate} />
        <ExpectancyChip expectancy={candidate.expectancy} />
      </div>

      {candidate.measured_move != null && candidate.measured_move_note && (
        <div className="mb-2 font-sans text-[10px] italic leading-snug text-ink3">
          measured move (if it works): {candidate.measured_move_note}
        </div>
      )}

      <EvidenceTags evidence={candidate.evidence || []} />

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
    </VisualCard>
  );
}

function MiniSetupChart({ candidate, scanDate, chartPayload }) {
  const [payload, setPayload] = useState(chartPayload || null);
  useEffect(() => {
    let cancelled = false;
    if (chartPayload) {
      setPayload(chartPayload);
      return undefined;
    }
    getSymbolOhlc(candidate.symbol, { n: 70, date: scanDate })
      .then((d) => !cancelled && setPayload(d))
      .catch(() => !cancelled && setPayload({ available: false, candles: [] }));
    return () => {
      cancelled = true;
    };
  }, [candidate.symbol, scanDate, chartPayload]);
  const candles = payload?.candles || [];
  const option = useMemo(() => {
    const dates = candles.map((c) => c.date);
    const values = candles.map((c) => [c.open, c.close, c.low, c.high]);
    const entry = candidate.entry ?? candidate.trade_plan?.entry;
    const stop = candidate.stop ?? candidate.trade_plan?.stop;
    const target = candidate.measured_move ?? candidate.target ?? candidate.trade_plan?.target;
    return {
      animation: false,
      grid: { left: 34, right: 48, top: 10, bottom: 22 },
      xAxis: { type: "category", data: dates, axisLabel: { show: false }, axisTick: { show: false } },
      yAxis: { scale: true, splitLine: { lineStyle: { color: "#d9ded7" } }, axisLabel: { fontSize: 9 } },
      tooltip: { trigger: "axis" },
      series: [
        {
          type: "candlestick",
          data: values,
          itemStyle: { color: "#147a4d", color0: "#b8443c", borderColor: "#147a4d", borderColor0: "#b8443c" },
          markLine: {
            symbol: "none",
            lineStyle: { type: "dashed", width: 1.4 },
            label: { fontSize: 9, formatter: "{b}" },
            data: [
              entry != null && { name: "entry", yAxis: Number(entry), lineStyle: { color: "#111827" } },
              stop != null && { name: "stop", yAxis: Number(stop), lineStyle: { color: "#b8443c" } },
              target != null && { name: "target", yAxis: Number(target), lineStyle: { color: "#147a4d" } },
            ].filter(Boolean),
          },
        },
        payload?.ema21?.length && {
          type: "line",
          name: "21EMA",
          data: dates.map((date) => payload.ema21.find((p) => p.date === date)?.value ?? null),
          showSymbol: false,
          smooth: true,
          lineStyle: { color: "#2563eb", width: 1.2 },
        },
      ].filter(Boolean),
    };
  }, [candles, candidate, payload]);
  if (!candles.length) {
    return <div className="flex h-full items-center justify-center font-mono text-[10px] uppercase tracking-overline text-ink3">chart loading</div>;
  }
  return <EChart option={option} className="h-full" />;
}

function RiskLadder({ plan, candidate }) {
  const entry = plan?.entry ?? candidate?.entry;
  const stop = plan?.stop ?? candidate?.stop;
  const target = candidate?.measured_move ?? candidate?.target ?? plan?.target;
  const risk = entry != null && stop != null ? Math.max(0, Number(entry) - Number(stop)) : null;
  const reward = entry != null && target != null ? Math.max(0, Number(target) - Number(entry)) : null;
  const rr = risk ? reward / risk : (plan?.rr ?? candidate?.rr);
  return (
    <div className="border border-hairline bg-card p-2">
      <div className="mb-2 font-mono text-[9px] font-bold uppercase tracking-overline text-ink3">R:R ladder</div>
      <div className="grid grid-cols-[1fr_1fr_1fr] items-end gap-1 font-mono text-[10px] uppercase tracking-overline">
        <LadderStep label="stop" value={fmt(stop)} tone="bear" />
        <LadderStep label="entry" value={fmt(entry)} tone="ink" />
        <LadderStep label="target" value={fmt(target)} tone="bull" />
      </div>
      <div className="mt-2 h-2 overflow-hidden border border-hairline bg-bear-bg">
        <div className="h-full bg-bull" style={{ width: `${Math.min(100, Math.max(10, Number(rr || 1) * 28))}%` }} />
      </div>
      <div className="mt-1 font-mono text-[10px] uppercase tracking-overline text-ink3">
        {rr == null ? "R:R unavailable" : `${Number(rr).toFixed(2)}R reward for 1R risk`} - qty {plan?.suggested_qty ?? candidate?.suggested_qty ?? "-"}
      </div>
      {plan?.watch_for_failure && <div className="mt-1 font-sans text-[11px] leading-snug text-ink3">{plan.watch_for_failure}</div>}
    </div>
  );
}

function LadderStep({ label, value, tone }) {
  const cls = tone === "bull" ? "text-bull" : tone === "bear" ? "text-bear" : "text-ink";
  return (
    <div className="border border-hairline bg-raised px-2 py-1">
      <div className="text-ink3">{label}</div>
      <div className={`text-[14px] font-bold tabular-nums ${cls}`}>{value}</div>
    </div>
  );
}

function SetupStoryboard({ candidate }) {
  const steps = [
    { label: "base", value: candidate.pattern_label || candidate.setup || "formed" },
    { label: "trigger", value: candidate.trade_plan?.entry_trigger || `entry ${fmt(candidate.entry)}` },
    { label: "risk", value: `stop ${fmt(candidate.stop)}` },
    { label: "action", value: candidate.grade === "A+" || candidate.grade === "A" ? "review now" : "watch size" },
  ];
  return (
    <div className="grid gap-1 sm:grid-cols-4">
      {steps.map((step, idx) => (
        <div key={step.label} className="border border-hairline bg-raised px-2 py-1">
          <div className="font-mono text-[9px] uppercase tracking-overline text-ink3">{idx + 1}. {step.label}</div>
          <div className="truncate font-sans text-[11px] text-ink2" title={step.value}>{step.value}</div>
        </div>
      ))}
    </div>
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
    <div className="flex items-center gap-1 font-mono text-[9px] uppercase tracking-overline text-ink3">
      <span className="mr-1">gate rail</span>
      {names.map((name) => {
        const g = items.find((item) => (item.name || item.gate || "").toLowerCase().includes(name));
        const passed = g?.passed ?? g?.ok ?? true;
        return (
          <span
            key={name}
            title={g?.reason || g?.detail || (passed ? "passed" : "failed")}
            className={"flex flex-1 flex-col gap-1 border px-1.5 py-1 " + (passed ? "border-bull-border bg-bull-bg text-bull" : "border-bear-border bg-bear-bg text-bear")}
          >
            <span className="h-1.5 w-full rounded-full bg-current" />
            <span className="truncate">{name}</span>
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

function NearMisses({ nearMisses, loading, onRefresh }) {
  if (loading) {
    return (
      <PosterBand state="warn" kicker="watch candidates" title="near-miss lane loading">
        <div className="font-mono text-[11px] uppercase tracking-overline text-ink3">finding refused names that are closest to useful...</div>
      </PosterBand>
    );
  }
  if (!nearMisses.length) return null;
  return (
    <PosterBand state="warn" kicker="watch candidates" title="near-misses worth learning from">
      <div className="mb-3 font-sans text-[12px] text-ink2">
        These did not pass the official gate. Track them, ignore them, or log a half-size override without mutating the scanner verdict.
      </div>
      <div className="grid gap-3 lg:grid-cols-2 xl:grid-cols-3">
        {nearMisses.map((item) => <NearMissCard key={`${item.candidate_date}-${item.symbol}-${item.failed_gate}`} item={item} onRefresh={onRefresh} />)}
      </div>
    </PosterBand>
  );
}

function NearMissCard({ item, onRefresh }) {
  const [busy, setBusy] = useState(null);
  const track = async (status) => {
    setBusy(status);
    await trackWatchlistCandidate({
      candidate_date: item.candidate_date,
      symbol: item.symbol,
      source: "near_miss",
      status,
      reason: item.reason,
      failed_gate: item.failed_gate,
      snapshot: item,
    });
    setBusy(null);
    onRefresh?.();
  };
  const override = async () => {
    const reason = window.prompt(`Why override ${item.symbol} half-size?`, item.distance?.what_would_it_take || item.reason || "");
    if (!reason) return;
    setBusy("override");
    await overrideSetup({
      candidate_date: item.candidate_date,
      symbol: item.symbol,
      reason,
      failed_gate: item.failed_gate,
      snapshot: item,
    });
    setBusy(null);
    onRefresh?.();
  };
  const dist = item.distance || {};
  const state = dist.severity === "hard" ? "bear" : "warn";
  return (
    <VisualCard state={state} className="space-y-2">
      <div className="flex items-start justify-between gap-2">
        <div>
          <div className="font-display text-[22px] uppercase leading-none text-ink">{item.symbol}</div>
          <div className="mt-1 font-mono text-[10px] uppercase tracking-overline text-ink3">failed {item.failed_gate}</div>
        </div>
        <div className="text-right font-mono text-[10px] uppercase tracking-overline text-ink3">
          {item.tracked?.status || item.override ? "tracked" : "not tracked"}
        </div>
      </div>
      <AnnotatedChart note={dist.label || "watch"} className="h-36">
        <MiniSetupChart candidate={{ symbol: item.symbol }} scanDate={item.candidate_date} chartPayload={item.chart} />
      </AnnotatedChart>
      <ProximityBar
        value={dist.value}
        unit={dist.unit}
        severity={dist.severity}
        label={dist.what_would_it_take || item.reason}
        className="mt-1"
      />
      <Caption>{item.reason}</Caption>
      <div className="flex flex-wrap justify-end gap-1 pt-1">
        <button type="button" disabled={Boolean(busy)} onClick={() => track("tracking")} className="border border-ink bg-ink px-2 py-0.5 font-mono text-[9px] uppercase tracking-overline text-white">
          Track
        </button>
        <button type="button" disabled={Boolean(busy)} onClick={() => track("ignored")} className="border border-hairline px-2 py-0.5 font-mono text-[9px] uppercase tracking-overline text-ink3">
          Ignore
        </button>
        <button type="button" disabled={Boolean(busy)} onClick={override} className="border border-warn-border bg-warn-bg px-2 py-0.5 font-mono text-[9px] uppercase tracking-overline text-warn">
          Override ½
        </button>
      </div>
    </VisualCard>
  );
}

// One place that turns raw score_breakdown/evidence percentiles into bars —
// replaces the old ScoreBreakdown text wall, which just repeated numbers
// already shown elsewhere as unstyled inline text.
function firstFiniteNumber(...candidates) {
  for (const c of candidates) {
    if (c == null) continue;
    // parseFloat (not Number) so values like "69 pctile" or "43%" still parse.
    const n = parseFloat(c);
    if (Number.isFinite(n)) return n;
  }
  return null;
}

function MetricStrip({ candidate }) {
  const breakdown = candidate.score_breakdown || {};
  const evidence = candidate.evidence || [];
  const findEvidence = (key) => evidence.find((e) => String(e.filter || "").toLowerCase() === key);
  const rsValue = firstFiniteNumber(breakdown.rs, findEvidence("rs>=70")?.value);
  const absStr = firstFiniteNumber(breakdown.abs_strength_pctile, findEvidence("abs-strength")?.value);
  const epsGrowth = firstFiniteNumber(breakdown.eps_growth_pctile, findEvidence("eps-growth")?.value);
  const delivery = firstFiniteNumber(breakdown.delivery, findEvidence("delivery>=60")?.value);
  const bars = [
    rsValue != null && { label: "RS rank", value: Math.round(rsValue), tone: "bull" },
    absStr != null && { label: "abs strength", value: Math.round(absStr), tone: "info" },
    epsGrowth != null && { label: "EPS growth pctile", value: Math.round(epsGrowth), tone: "info" },
    delivery != null && { label: "delivery %", value: Math.round(delivery), tone: "info" },
  ].filter(Boolean);
  if (!bars.length) return null;
  return (
    <div className="grid grid-cols-2 gap-x-3 gap-y-1.5">
      {bars.map((b) => (
        <MetricBar key={b.label} label={b.label} value={b.value} tone={b.tone} />
      ))}
    </div>
  );
}

// Human-readable labels for the raw filter keys the backend emits. Any key
// not in this map still renders (kebab-case -> Title Case) rather than being
// dropped silently — new backend filters show up readably without a code
// change here, they just won't have a hand-tuned label yet.
const EVIDENCE_LABELS = {
  "ep": "Earnings Power",
  "ipo base": "IPO Base",
  "launch-pad": "Launch Pad",
  "near-pivot": "Near Pivot",
  "ants": "Accumulation",
  "asm-clear": "No ASM Flag",
  "rvol>=1.5": "Volume Surge",
  "delivery>=60": "Delivery Confirmed",
  "eps yoy": "EPS Growth YoY",
  "theme": "Sector",
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

function evidenceLabel(filter) {
  const key = String(filter || "").toLowerCase();
  if (EVIDENCE_LABELS[key]) return EVIDENCE_LABELS[key];
  return String(filter || "")
    .replace(/[-_]/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

// Filters already promoted elsewhere (metric bars, caution callouts) or that
// carry zero decision value (raw personal-screener booleans with value
// "hit" and no recognized label) are dropped here so the tag row is
// evidence a trader can act on, not a dump of internal filter keys.
const PROMOTED_ELSEWHERE = new Set(["rs>=70", "abs-strength", "eps-growth", "delivery>=60", "exit-conflict", "wide-stop-vs-adr"]);

function EvidenceTags({ evidence }) {
  const kept = evidence.filter((e) => {
    const key = String(e.filter || "").toLowerCase();
    if (PROMOTED_ELSEWHERE.has(key)) return false;
    if (e.value === "hit" && !EVIDENCE_LABELS[key]) return false;
    return true;
  });
  if (!kept.length) return null;
  // Short values (percentages, multiples, single words) read fine as chips.
  // Long descriptive values (full sentences from signal detectors) read as
  // walls of text when crammed into a chip pill — render those as their own
  // compact lines instead.
  const isShort = (v) => String(v).length <= 18;
  const chips = kept.filter((e) => isShort(e.value));
  const notes = kept.filter((e) => !isShort(e.value));
  return (
    <div className="space-y-1">
      {chips.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {chips.map((e) => (
            <span
              key={`${e.filter}-${e.value}`}
              className="rounded-chip border border-info-border bg-info-bg px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-overline text-info"
            >
              {evidenceLabel(e.filter)}
              {e.value !== "hit" && e.value !== evidenceLabel(e.filter) ? ` · ${e.value}` : ""}
            </span>
          ))}
        </div>
      )}
      {notes.map((e) => (
        <div key={`${e.filter}-note`} className="border-l-2 border-info-border pl-2 font-sans text-[10px] leading-snug text-ink3">
          <span className="font-mono text-[9px] font-bold uppercase tracking-overline text-info">{evidenceLabel(e.filter)} —</span> {e.value}
        </div>
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
