// Setups / Focus — the feed that says NO.
// Refusal funnel (compact band) → candidate terminal rows (grade chips,
// plan line, readiness/TAKE-WATCH-SKIP) with expandable detail.

import { useEffect, useState } from "react";
import { getSetups, getSetupsRefusals, getSetupsNearMisses } from "./api.js";
import { TermPanel, BandChip, Expandable, EmptyLine, fmtNum } from "./primitives.jsx";

const GATE_PLAIN = {
  regime: "market ok",
  tradable: "can trade",
  trend: "trending",
  fresh: "fresh setup",
  particip: "volume",
  risk: "risk fits",
  "no-trade": "market says wait",
};

function plainGate(gate) {
  return GATE_PLAIN[String(gate || "").toLowerCase()] || String(gate || "").replace(/_/g, "-");
}

const GRADE_TONE = { "A+": "bull", A: "bull", B: "warn", C: "muted" };

export default function SetupsPage({ posture, density, focus = false }) {
  const [state, setState] = useState({ loading: true, error: null, data: null });
  const [refusals, setRefusals] = useState({ loading: true, data: null });
  const [nearMisses, setNearMisses] = useState({ loading: true, items: [] });

  useEffect(() => {
    let alive = true;
    setState({ loading: true, error: null, data: null });
    getSetups()
      .then((d) => !alive || setState({ loading: false, error: null, data: d }))
      .catch((e) => !alive || setState({ loading: false, error: e.message, data: null }));
    getSetupsRefusals({ limit: 50 })
      .then((d) => !alive || setRefusals({ loading: false, data: d }))
      .catch(() => !alive || setRefusals({ loading: false, data: null }));
    getSetupsNearMisses({ limit: 12 })
      .then((d) => !alive || setNearMisses({ loading: false, items: d?.near_misses || [] }))
      .catch(() => !alive || setNearMisses({ loading: false, items: [] }));
    return () => {
      alive = false;
    };
  }, []);

  const candidates = focus ? state.data?.focus_candidates || [] : state.data?.candidates || [];
  const cap = Number(state.data?.governor?.max_cards ?? state.data?.max_cards ?? candidates.length);
  const visible = candidates.slice(0, Number.isFinite(cap) && cap > 0 ? cap : candidates.length);
  const noTrade = posture === "NO_TRADE";

  return (
    <div className="space-y-3">
      {/* ── Refusal funnel band ──────────────────────────────────── */}
      <FunnelBand data={state.data} refusals={refusals.data} loading={refusals.loading} />

      {/* ── Candidates ───────────────────────────────────────────── */}
      <TermPanel
        title={focus ? "Focus candidates" : "Setups that cleared the gates"}
        sub={focus ? "The catalyst-lens names the governor allows." : "Ranked by readiness. Expand a row for the full plan."}
        right={
          <BandChip tone={noTrade ? "bear" : "info"}>
            {noTrade ? "market says wait" : `${visible.length} ${visible.length === 1 ? "name" : "names"}`}
          </BandChip>
        }
      >
        {state.loading ? (
          <EmptyLine>loading setups…</EmptyLine>
        ) : state.error ? (
          <EmptyLine tone="bear">{state.error}</EmptyLine>
        ) : noTrade || !state.data?.available || visible.length === 0 ? (
          <EmptyLine tone={noTrade ? "warn" : "muted"}>
            {noTrade ? "market is NO-TRADE — nothing to decide today" : "no candidates cleared the gates tonight"}
          </EmptyLine>
        ) : (
          <div className="grid gap-2">
            {visible.map((c, i) => (
              <CandidateRow key={`${c.symbol}-${i}`} candidate={c} rank={i + 1} rankOf={visible.length} density={density} />
            ))}
          </div>
        )}
      </TermPanel>

      {/* ── Near-misses (expert) ─────────────────────────────────── */}
      {density === "expert" && (
        <TermPanel
          title="Near-misses"
          sub="Names the gate refused, and how far they were from passing."
          right={<span className="font-mono text-[10px] text-ink3">{nearMisses.items.length}</span>}
        >
          {nearMisses.loading ? (
            <EmptyLine>loading near-misses…</EmptyLine>
          ) : nearMisses.items.length === 0 ? (
            <EmptyLine>no near-misses this scan</EmptyLine>
          ) : (
            <div className="divide-y divide-hairline2 border border-hairline bg-card">
              {nearMisses.items.slice(0, 8).map((item) => (
                <div key={`${item.candidate_date}-${item.symbol}`} className="flex flex-wrap items-center gap-x-3 gap-y-1 px-2 py-1.5">
                  <span className="font-mono text-[11px] font-bold uppercase text-ink">{item.symbol}</span>
                  <span className="font-mono text-[10px] uppercase tracking-overline text-ink3">
                    failed {plainGate(item.failed_gate)}
                  </span>
                  {item.distance?.value != null && (
                    <BandChip tone={item.distance.label === "hard no" ? "bear" : "warn"}>
                      {item.distance.label === "hard no" ? "hard no" : `${item.distance.value}${item.distance.unit} to pass`}
                    </BandChip>
                  )}
                  <span className="min-w-0 flex-1 font-sans text-[11px] leading-snug text-ink2">
                    {item.distance?.what_would_it_take || item.reason}
                  </span>
                </div>
              ))}
            </div>
          )}
        </TermPanel>
      )}
    </div>
  );
}

// ── Refusal funnel: Universe → Screeners → Gates → PASSED ───────────────
function FunnelBand({ data, refusals, loading }) {
  const byGate = refusals?.by_gate || {};
  const drops = Object.entries(byGate)
    .map(([gate, n]) => [plainGate(gate), Number(n)])
    .filter(([, n]) => n > 0)
    .sort((a, b) => b[1] - a[1]);
  const passed = Number(data?.total_passed ?? data?.candidates?.length ?? 0);
  const gateDrops = drops.reduce((s, [, n]) => s + n, 0);
  const screeners = Number(refusals?.total ?? refusals?.universe ?? (gateDrops + passed) ?? passed);
  const universe = Number(refusals?.universe ?? data?.universe ?? Math.max(screeners, passed));
  const stages = [
    ["universe", universe],
    ["screeners", screeners],
    ["gates", screeners - gateDrops],
    ["PASSED", passed],
  ];

  return (
    <section className="border border-hairline bg-card p-3">
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <div className="font-mono text-[11px] font-bold uppercase tracking-overline text-ink">
          Refusal funnel — the feed that says NO
        </div>
        <div className="font-mono text-[10px] uppercase tracking-overline text-ink3">
          selective cap: {data?.governor?.max_cards ?? data?.max_cards ?? "—"}
        </div>
      </div>
      {loading ? (
        <EmptyLine>loading funnel…</EmptyLine>
      ) : (
        <>
          <div className="grid items-stretch gap-1 md:grid-cols-[1fr_auto_1fr_auto_1fr_auto_1fr]">
            {stages.map(([label, value], i) => [
              <div
                key={label}
                className={`border px-3 py-2 ${label === "PASSED" ? "border-bull-border bg-bull-bg" : "border-hairline bg-raised"}`}
              >
                <div className="font-mono text-[9px] uppercase tracking-overline text-ink3">{label}</div>
                <div className={`mt-1 font-mono text-[20px] font-bold leading-none tabular-nums ${label === "PASSED" ? "text-bull" : "text-ink"}`}>
                  {fmtNum(value)}
                </div>
              </div>,
              i < stages.length - 1 ? (
              <div key={`arrow-${i}`} className="hidden items-center font-mono text-[18px] text-ink3 md:flex">→</div>
              ) : null,
            ])}
          </div>
          {drops.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-x-3 gap-y-1 font-mono text-[10px] uppercase tracking-overline text-ink3">
              {drops.map(([gate, n]) => (
                <span key={gate}>
                  {gate} <span className="text-bear">-{n}</span>
                </span>
              ))}
            </div>
          )}
        </>
      )}
    </section>
  );
}

// ── CandiateRow: dense terminal row with expandable plan detail ─────────
function CandidateRow({ candidate: c, rank, rankOf, density }) {
  const [open, setOpen] = useState(density !== "expert");
  const grade = c.grade || "C";
  const tone = GRADE_TONE[grade] || "muted";
  const setup = c.setup || c.setup_type || "setup";
  const readiness = c.readiness ?? c.grade_score ?? null;
  const entry = c.entry;
  const stop = c.stop;
  const target = c.measured_move ?? c.target;
  const rr = c.rr;
  const risk = entry != null && stop != null ? Math.max(0, Number(entry) - Number(stop)) : null;
  const read = c.read || c.plain_read || c.reason || "Passed the named setup checks.";

  return (
    <div className={`border ${open ? "border-hairline bg-card" : "border-hairline2 bg-raised"}`}>
      <button type="button" onClick={() => setOpen((v) => !v)} className="w-full text-left">
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 px-2 py-1.5">
          <span className="w-6 font-mono text-[10px] tabular-nums text-ink3">{rank}</span>
          <span className="font-mono text-[14px] font-bold uppercase text-ink">{c.symbol}</span>
          <BandChip tone={tone}>{grade}</BandChip>
          <span className="font-mono text-[10px] uppercase tracking-overline text-ink3">{setup}</span>
          <span className="ml-auto font-mono text-[10px] uppercase tracking-overline text-ink2">
            {open ? "▾ detail" : "▸ detail"}
          </span>
        </div>
      </button>

      {open && (
        <div className="border-t border-hairline2 px-2 py-2">
          <div className="grid gap-2 md:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
            {/* Left: verdict + read */}
            <div>
              <div className="flex items-baseline gap-2">
                <span className="font-mono text-[16px] font-bold uppercase tracking-overline text-ink">
                  {readiness == null ? "PASS" : `${Number(readiness).toFixed(0)}/100`}
                </span>
                <span className="font-sans text-[12px] leading-snug text-ink2">{read}</span>
              </div>
              {density === "expert" && c.evidence?.length > 0 && (
                <div className="mt-1 font-mono text-[10px] uppercase tracking-overline text-ink3">
                  evidence: {c.evidence.map((e) => e.filter || e.value).join(" · ")}
                </div>
              )}
            </div>

            {/* Right: plan numbers */}
            <div className="grid grid-cols-2 gap-x-4 gap-y-1 font-mono text-[11px] text-ink2 sm:grid-cols-4">
              <div><span className="text-ink3">entry</span> <span className="font-bold text-ink">{fmtNum(entry)}</span></div>
              <div><span className="text-ink3">stop</span> <span className="font-bold text-ink">{fmtNum(stop)}</span></div>
              <div><span className="text-ink3">target</span> <span className="font-bold text-ink">{fmtNum(target)}</span></div>
              <div><span className="text-ink3">risk</span> <span className="font-bold text-ink">{fmtNum(risk)}</span></div>
              {rr != null && (
                <div><span className="text-ink3">reward vs risk</span> <span className="font-bold text-ink">{rr}</span></div>
              )}
              <div><span className="text-ink3">rank</span> <span className="font-bold text-ink">{rank} of {rankOf}</span></div>
            </div>
          </div>

          {density === "expert" && c.gates && (
            <div className="mt-2 border-t border-hairline2 pt-1.5">
              <Expandable label="gate checks" defaultOpen>
                <div className="flex flex-wrap gap-2 font-mono text-[10px] uppercase tracking-overline text-ink3">
                  {gateList(c.gates).map((g, i) => (
                    <span key={i} className="inline-flex items-center gap-1">
                      <span className={`inline-block h-2 w-2 rounded-full ${g.passed ? "bg-bull-dot" : "bg-bear-dot"}`} />
                      {plainGate(g.name)}
                    </span>
                  ))}
                </div>
              </Expandable>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function gateList(gates) {
  if (Array.isArray(gates)) return gates;
  if (gates && typeof gates === "object") {
    return Object.entries(gates).map(([name, value]) => ({
      name,
      passed: typeof value === "object" ? value.passed !== false : value !== false,
    }));
  }
  return [];
}