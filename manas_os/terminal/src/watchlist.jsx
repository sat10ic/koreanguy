// Watchlist — "what I hold, what to do today".
// Heat row (money-at-risk) → coach cards (HOLD/EXIT verdict + plain action +
// lifecycle river) → dense watch table (beginner columns default).

import { useEffect, useMemo, useState } from "react";
import { getOrganicWatchlist, getPortfolioHeat, getWatchlist } from "./api.js";
import { TermPanel, BandChip, EmptyLine, MeterBar, fmtPct, signed } from "./primitives.jsx";

const EXPERT_COLUMNS = [
  { key: "symbol", label: "sym" },
  { key: "health", label: "health" },
  { key: "action", label: "action" },
  { key: "rs", label: "rs" },
  { key: "adr", label: "adr%" },
  { key: "delivery_z", label: "dlv-z" },
  { key: "dist_pivot", label: "dist-pivot" },
  { key: "exit_state", label: "exit-state" },
  { key: "trail", label: "trail" },
  { key: "days", label: "days" },
  { key: "open_r", label: "open R" },
];

const BEGINNER_COLUMNS = [
  { key: "symbol", label: "sym" },
  { key: "health", label: "health" },
  { key: "action", label: "action" },
];

export default function WatchlistPage({ density }) {
  const expert = density === "expert";
  const [organic, setOrganic] = useState({ loading: true, error: null, data: null });
  const [heat, setHeat] = useState({ loading: true, error: null, data: null });
  const [watch, setWatch] = useState({ loading: true, error: null, data: null });

  useEffect(() => {
    let alive = true;
    getOrganicWatchlist()
      .then((d) => !alive || setOrganic({ loading: false, error: null, data: d }))
      .catch((e) => !alive || setOrganic({ loading: false, error: e.message, data: null }));
    getPortfolioHeat()
      .then((d) => !alive || setHeat({ loading: false, error: null, data: d }))
      .catch((e) => !alive || setHeat({ loading: false, error: e.message, data: null }));
    getWatchlist()
      .then((d) => !alive || setWatch({ loading: false, error: null, data: d }))
      .catch((e) => !alive || setWatch({ loading: false, error: e.message, data: null }));
    return () => {
      alive = false;
    };
  }, []);

  const positions = organic.data?.active_positions || [];
  const rows = useMemo(
    () => buildRows(positions, watch.data?.items || []),
    [positions, watch.data?.items],
  );
  const columns = expert ? EXPERT_COLUMNS : BEGINNER_COLUMNS;

  return (
    <div className="space-y-3">
      <HeatRow heat={heat.data} loading={heat.loading} error={heat.error} />

      <TermPanel
        title="Position coach"
        sub="What to do with each open position, in plain words."
        right={<span className="font-mono text-[10px] text-ink3">{positions.length} open</span>}
      >
        {organic.loading ? (
          <EmptyLine>loading positions…</EmptyLine>
        ) : organic.error ? (
          <EmptyLine tone="bear">{organic.error}</EmptyLine>
        ) : positions.length === 0 ? (
          <EmptyLine>no open positions — nothing to manage today</EmptyLine>
        ) : (
          <div className="grid gap-2">
            {positions.map((p) => (
              <CoachCard key={p.trade_id ?? p.symbol} position={p} />
            ))}
          </div>
        )}
      </TermPanel>

      <TermPanel
        title="Watch table"
        sub={expert ? "Full terminal view." : "The plain view — expert columns are behind the density toggle."}
        right={<BandChip tone="info">{rows.length} rows</BandChip>}
      >
        {rows.length === 0 ? (
          <EmptyLine>no watchlist symbols or open positions</EmptyLine>
        ) : (
          <WatchTable rows={rows} columns={columns} />
        )}
      </TermPanel>
    </div>
  );
}

// ── Heat row: money-at-risk bar + sector spread + last-10 avg R ──────────
function HeatRow({ heat, loading, error }) {
  const open = Number(heat?.open_risk_pct || 0);
  const cap = Number(heat?.cap_pct || 0);
  const pct = cap > 0 ? (open / cap) * 100 : 0;
  const tone = cap > 0 && open > cap ? "bear" : pct >= 75 ? "warn" : "bull";
  const sectors = Object.entries(heat?.sector_counts || {}).sort((a, b) => b[1] - a[1]);
  const maxSector = sectors[0] || null;
  const rolling = heat?.rolling_10_avg_r || {};

  return (
    <section className="border border-hairline bg-card p-3">
      <div className="grid gap-3 md:grid-cols-3">
        <div className="border border-hairline bg-raised px-3 py-2">
          <div className="font-mono text-[9px] uppercase tracking-overline text-ink3">money at risk</div>
          <div className="mt-1 flex items-end gap-2">
            <span className={`font-mono text-[24px] font-bold leading-none tabular-nums ${tone === "bull" ? "text-bull" : tone === "warn" ? "text-warn" : "text-bear"}`}>
              {fmtPct(open, 1)}
            </span>
            <span className="pb-0.5 font-mono text-[10px] uppercase tracking-overline text-ink3">of {fmtPct(cap, 0)} cap</span>
          </div>
          <MeterBar pct={pct} tone={tone} className="mt-2" />
        </div>

        <div className="border border-hairline bg-raised px-3 py-2">
          <div className="font-mono text-[9px] uppercase tracking-overline text-ink3">sector spread</div>
          {maxSector ? (
            <>
              <div className="mt-1 font-mono text-[13px] font-bold uppercase text-ink">{maxSector[0]}</div>
              <div className={`font-mono text-[11px] tabular-nums ${maxSector[1] >= 2 ? "text-warn" : "text-ink2"}`}>
                {maxSector[1]} {maxSector[1] >= 2 ? "· max!" : "position(s)"}
              </div>
              {sectors.length > 1 && (
                <div className="mt-1 flex flex-wrap gap-1">
                  {sectors.slice(0, 4).map(([name, n]) => (
                    <span key={name} className="rounded-chip border border-hairline bg-card px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-overline text-ink3">
                      {name} {n}
                    </span>
                  ))}
                </div>
              )}
            </>
          ) : (
            <EmptyLine>no open sectors</EmptyLine>
          )}
        </div>

        <div className="border border-hairline bg-raised px-3 py-2">
          <div className="font-mono text-[9px] uppercase tracking-overline text-ink3">last-10 trades · avg R</div>
          <div className={`mt-1 font-mono text-[24px] font-bold leading-none tabular-nums ${(rolling.value ?? 0) >= 0 ? "text-bull" : "text-bear"}`}>
            {rolling.value == null ? "—" : signed(rolling.value, "R", 2)}
          </div>
          <div className="mt-1 font-mono text-[10px] uppercase tracking-overline text-ink3">
            {rolling.n ? `n=${rolling.n} closed` : "needs closed trades"}
          </div>
          {heat?.half_size_mode && <BandChip tone="bear" className="mt-1">half size mode</BandChip>}
        </div>
      </div>
    </section>
  );
}

// ── Coach card: verdict pill + plain instruction + lifecycle river ───────
function CoachCard({ position }) {
  const coach = position.coach || {};
  const urgent = Boolean(coach.exit_now || /exit|overdue|unacted/i.test(coach.plain_instruction || coach.action || ""));
  const sentence = coach.plain_instruction || coach.action || position.action_line || "No coach instruction returned.";
  const [open, setOpen] = useState(true);
  const lifecycle = position.lifecycle || [];

  return (
    <div className={`border px-3 py-2 ${urgent ? "border-bear-border bg-bear-bg" : "border-hairline bg-card"}`}>
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
        <BandChip tone={urgent ? "bear" : coach.phase === "EXTENSION" ? "warn" : "bull"}>
          {urgent ? "EXIT" : coach.phase === "EXTENSION" ? "TRIM" : "HOLD"}
        </BandChip>
        <span className="font-mono text-[14px] font-bold uppercase text-ink">{position.symbol}</span>
        <span className={`font-mono text-[13px] font-bold tabular-nums ${Number(position.open_r ?? 0) >= 0 ? "text-bull" : "text-bear"}`}>
          {position.open_r == null ? "—" : signed(position.open_r, "R", 2)}
        </span>
        <span className="min-w-0 flex-1 font-sans text-[12px] leading-snug text-ink">{sentence}</span>
        {lifecycle.length > 1 && (
          <button
            type="button"
            onClick={() => setOpen((v) => !v)}
            className="shrink-0 border border-hairline px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-overline text-ink3 hover:border-ink hover:text-ink"
          >
            {open ? "river ▾" : "river ▸"}
          </button>
        )}
      </div>
      {open && lifecycle.length > 1 && (
        <div className="mt-2 border-t border-hairline2 pt-2">
          <div className="mb-1 flex justify-between font-mono text-[9px] uppercase tracking-overline text-ink3">
            <span>sessions since entry</span>
            <span>open R · phase bands</span>
          </div>
          <LifecycleRiver lifecycle={lifecycle} />
        </div>
      )}
    </div>
  );
}

function LifecycleRiver({ lifecycle }) {
  const values = lifecycle.map((p) => p.r);
  const min = Math.min(...values, 0);
  const max = Math.max(...values, 1);
  const span = max - min || 1;
  const w = 100;
  const h = 36;
  const x = (i) => (i / Math.max(1, values.length - 1)) * w;
  const y = (v) => h - ((v - min) / span) * (h - 6) - 3;
  const line = lifecycle.map((p, i) => `${x(i)},${y(p.r)}`).join(" ");

  const phaseColor = { INITIATION: "rgba(100,116,139,0.10)", TREND: "rgba(246,166,9,0.12)", EXTENSION: "rgba(34,197,94,0.16)" };
  const bands = [];
  let start = 0;
  for (let i = 1; i <= lifecycle.length; i++) {
    if (i === lifecycle.length || lifecycle[i].phase !== lifecycle[start].phase) {
      bands.push({ from: start, to: i - 1, color: phaseColor[lifecycle[start].phase] || "transparent" });
      start = i;
    }
  }
  return (
    <svg viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none" className="block w-full" style={{ height: 80 }} aria-hidden="true">
      {bands.map((b, i) => (
        <rect key={`band-${i}`} x={x(b.from)} y="0" width={x(b.to) - x(b.from) + 2} height={h} fill={b.color} />
      ))}
      <polyline points={line} fill="none" stroke="#0f7a3d" strokeWidth="1.5" vectorEffect="non-scaling-stroke" />
      <circle cx={x(values.length - 1)} cy={y(values[values.length - 1])} r="2" fill="#0f7a3d" />
    </svg>
  );
}

// ── Watch table: dense terminal grid ─────────────────────────────────────
function WatchTable({ rows, columns }) {
  return (
    <div className="term-scroll overflow-x-auto">
      <table className="w-full border-collapse font-mono text-[11px]">
        <thead>
          <tr className="border border-hairline bg-raised text-left text-[9px] uppercase tracking-overline text-ink3">
            {columns.map((c) => (
              <th key={c.key} className="whitespace-nowrap border-r border-hairline px-2 py-1.5 last:border-r-0">{c.label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <WatchRow key={`${row.kind}-${row.symbol}-${i}`} row={row} columns={columns} />
          ))}
        </tbody>
      </table>
    </div>
  );
}

function WatchRow({ row, columns }) {
  const urgent = row.coach?.exit_now || row.exit_state?.state === "Broken";
  return (
    <tr className={`border-b border-hairline2 ${urgent ? "bg-bear-bg" : row.kind === "position" ? "bg-info-bg" : ""}`}>
      {columns.map((c) => (
        <td key={c.key} className="whitespace-nowrap border-r border-hairline2 px-2 py-1.5 last:border-r-0 tabular-nums">
          {renderCell(c.key, row, urgent)}
        </td>
      ))}
    </tr>
  );
}

function renderCell(key, row, urgent) {
  if (key === "symbol") {
    return <span className="font-bold uppercase text-ink">{row.symbol || "—"}</span>;
  }
  if (key === "health") {
    const health = row.exit_state?.state;
    const tone = urgent ? "bear" : health === "Weakening" ? "warn" : health === "Intact" ? "bull" : "muted";
    return (
      <span className={`font-bold uppercase ${tone === "bull" ? "text-bull" : tone === "bear" ? "text-bear" : tone === "warn" ? "text-warn" : "text-ink3"}`}>
        {health || "—"}
      </span>
    );
  }
  if (key === "action") {
    return (
      <span className="font-sans text-[11px] leading-snug text-ink2">
        {row.coach?.plain_instruction || row.coach?.action || "No action returned."}
      </span>
    );
  }
  if (key === "rs") return <CellNum value={row.rs} fmt={(v) => `${v.toFixed(0)}`} band={row.rs >= 70 ? "bull" : row.rs >= 50 ? "warn" : "bear"} />;
  if (key === "adr") return <CellNum value={row.adr} fmt={(v) => `${v.toFixed(1)}`} tone="muted" />;
  if (key === "delivery_z") return <CellNum value={row.timing?.delivery_z} fmt={(v) => signed(v, "", 1)} band={row.timing?.delivery_z > 0 ? "bull" : row.timing?.delivery_z < 0 ? "bear" : null} />;
  if (key === "dist_pivot") return <CellNum value={row.timing?.dist_pivot} fmt={(v) => signed(v, "%", 1)} band={Math.abs(row.timing?.dist_pivot) <= 1 ? "bull" : row.timing?.dist_pivot > 0 ? "warn" : null} />;
  if (key === "exit_state") {
    const state = row.exit_state?.state || "—";
    const tone = urgent ? "bear" : row.exit_state?.state === "Weakening" ? "warn" : "muted";
    return <TextTone value={state} tone={tone} />;
  }
  if (key === "trail") return <span className="text-ink2">{row.trail ?? "—"}</span>;
  if (key === "days") return <CellNum value={row.days_held} fmt={(v) => `${v}`} tone="muted" />;
  if (key === "open_r") return <CellNum value={row.open_r} fmt={(v) => signed(v, "R", 2)} band={row.open_r > 0 ? "bull" : row.open_r < 0 ? "bear" : null} />;
  return <span className="text-ink3">—</span>;
}

function CellNum({ value, fmt, tone, band }) {
  if (value == null || Number.isNaN(Number(value))) return <span className="text-ink3">—</span>;
  const cls =
    band === "bull" ? "text-bull" : band === "bear" ? "text-bear" : band === "warn" ? "text-warn" : tone === "muted" ? "text-ink2" : "text-ink";
  return <span className={cls}>{fmt(Number(value))}</span>;
}

function TextTone({ value, tone }) {
  const cls = tone === "bull" ? "text-bull" : tone === "bear" ? "text-bear" : tone === "warn" ? "text-warn" : "text-ink2";
  return <span className={cls}>{value}</span>;
}

// ── Row fusion: positions + manual watchlist ─────────────────────────────
function buildRows(positions, watchItems) {
  const manualBySym = new Map(watchItems.map((item) => [item.symbol, item]));
  const positionRows = positions.map((p) => {
    const manual = manualBySym.get(p.symbol) || {};
    manualBySym.delete(p.symbol);
    return {
      ...manual,
      ...p,
      kind: "position",
      rs: manual.rs ?? p.rs ?? null,
      adr: manual.adr ?? p.timing?.adr ?? null,
    };
  });
  const manualRows = [...manualBySym.values()].map((item) => ({
    ...item,
    kind: "watch",
    days_held: null,
    open_r: null,
    rs: item.rs ?? item.timing?.rs ?? null,
  }));
  return [...positionRows, ...manualRows];
}