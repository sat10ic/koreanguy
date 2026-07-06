import { useEffect, useState } from "react";
import { addWatchlist, getSetups } from "../api.js";
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

  const gateText =
    mode === "RISK_ON"
      ? "RISK-ON — A and B setups are allowed."
      : mode === "SELECTIVE"
        ? "SELECTIVE — showing A-setups only."
        : mode === "DEFENSIVE"
          ? "DEFENSIVE — only flawless A-setups should survive."
          : mode === "NO_TRADE"
            ? "NO-TRADE — no new setups should be acted on."
            : mode === "STALE"
              ? "STALE — candidates are informational until data is fresh."
              : "UNKNOWN — waiting for regime posture.";

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
      ) : !state.data?.available || filteredCandidates(state.data.candidates, lens).length === 0 ? (
        <EmptySetups mode={mode} />
      ) : (
        <div className="grid gap-3 lg:grid-cols-2 xl:grid-cols-3">
          {filteredCandidates(state.data.candidates, lens).map((candidate) => (
            <CandidateCard
              key={`${candidate.symbol}-${candidate.setup_type || candidate.setup}`}
              candidate={candidate}
              onSymbolSelect={onSymbolSelect}
              focus={lens === "ipo_ep"}
            />
          ))}
        </div>
      )}

      <DataStamp />
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

function CandidateCard({ candidate, onSymbolSelect, focus = false }) {
  const band = candidate.grade === "A+" || candidate.grade === "A" ? "bull" : candidate.grade === "B" ? "warn" : "muted";
  const add = async () => {
    await addWatchlist(candidate.symbol, candidate.setup);
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
            {candidate.grade} · {candidate.setup}
            {confluenceCount != null && (
              <span className="rounded-chip border border-hairline bg-raised px-1 py-px text-[9px] font-bold tabular-nums text-ink2">
                {confluenceCount} screens
              </span>
            )}
          </div>
          <div className="font-sans text-[11px] text-ink3">Trade readiness {candidate.readiness}/100</div>
        </div>
        <span className="font-mono text-[20px] font-bold tabular-nums text-ink">{candidate.readiness.toFixed(0)}</span>
      </div>

      <ScoreBreakdown breakdown={candidate.score_breakdown} />

      {focus && <FocusFields candidate={candidate} />}

      <div className="mb-2 grid grid-cols-3 gap-1 border border-hairline bg-raised p-2 font-mono text-[10px] tabular-nums text-ink2">
        <Metric label="entry" value={fmt(candidate.entry)} />
        <Metric label="stop" value={fmt(candidate.stop)} />
        <Metric label="measured move" value={fmt(candidate.measured_move)} />
      </div>
      {candidate.measured_move != null && candidate.measured_move_note && (
        <div className="mb-2 font-sans text-[10px] italic leading-snug text-ink3">
          measured move (if it works): {candidate.measured_move_note}
        </div>
      )}

      <TradePlan plan={candidate.trade_plan} />

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

function FocusFields({ candidate }) {
  const growth = candidate.score_breakdown?.eps_growth_pctile;
  const rr = candidate.trade_plan?.rr;
  return (
    <div className="mb-2 grid grid-cols-4 gap-1 border border-info-border bg-info-bg p-2 font-mono text-[9px] uppercase tracking-overline text-info">
      <Metric label="pattern" value={candidate.pattern_label || candidate.setup} />
      <Metric label="readiness" value={String(Math.round(candidate.readiness || 0))} />
      <Metric label="age" value={candidate.days_since_listing != null ? `${candidate.days_since_listing}d` : candidate.base_age != null ? `${candidate.base_age}d` : "—"} />
      <Metric label="R:R" value={rr == null ? "—" : `${Number(rr).toFixed(2)}R`} />
      <Metric label="growth" value={growth == null ? "—" : `${Number(growth).toFixed(0)} pctile`} />
      <Metric label="circuit" value="clear" />
    </div>
  );
}

function TradePlan({ plan }) {
  if (!plan) return null;
  return (
    <div className="mb-2 border border-hairline bg-card p-2">
      <div className="mb-1 font-mono text-[9px] font-bold uppercase tracking-overline text-ink3">Trade plan</div>
      <div className="grid gap-1 font-sans text-[11px] leading-snug text-ink2">
        <div>{plan.entry_trigger}</div>
        <div className="font-mono text-[10px] uppercase tracking-overline text-ink3">
          stop {fmt(plan.stop)} · target {fmt(plan.target)} · R:R {plan.rr == null ? "—" : Number(plan.rr).toFixed(2)}
        </div>
        <div>{plan.watch_for_failure}</div>
      </div>
    </div>
  );
}

// Component-first breakdown of the readiness number (design rule: readiness
// is the only big/ranked number on the card — this row is small, informational,
// never a second score). Renders whichever components scored/are present.
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
  if (value == null) return "—";
  return Number(value).toFixed(2).replace(/\.00$/, "");
}
