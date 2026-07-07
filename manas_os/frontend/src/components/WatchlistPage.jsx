import { useEffect, useMemo, useRef, useState } from "react";
import * as echarts from "echarts";
import { getOrganicWatchlist, getPortfolioHeat, getWatchlist } from "../api.js";

const SECTOR_MAX = 2;

const TABLE_COLUMNS = [
  { key: "symbol", label: "SYM" },
  { key: "rs", label: "RS" },
  { key: "adr", label: "ADR%" },
  { key: "delivery_z", label: "dlv_z" },
  { key: "dist_pivot", label: "dist-pivot" },
  { key: "exit_state", label: "exit-state" },
  { key: "trail", label: "trail" },
  { key: "days_held", label: "days" },
  { key: "open_r", label: "open R" },
];

export default function WatchlistPage({ onSymbolSelect }) {
  const [heat, setHeat] = useState({ loading: true, error: null, data: null });
  const [watch, setWatch] = useState({ loading: true, error: null, data: null });
  const [organic, setOrganic] = useState({ loading: true, error: null, data: null });

  useEffect(() => {
    let cancelled = false;
    getPortfolioHeat()
      .then((data) => !cancelled && setHeat({ loading: false, error: null, data }))
      .catch((error) => !cancelled && setHeat({ loading: false, error: error.message, data: null }));
    getWatchlist()
      .then((data) => !cancelled && setWatch({ loading: false, error: null, data }))
      .catch((error) => !cancelled && setWatch({ loading: false, error: error.message, data: null }));
    getOrganicWatchlist()
      .then((data) => !cancelled && setOrganic({ loading: false, error: null, data }))
      .catch((error) => !cancelled && setOrganic({ loading: false, error: error.message, data: null }));
    return () => {
      cancelled = true;
    };
  }, []);

  const activePositions = organic.data?.active_positions || [];
  const watchRows = useMemo(
    () => buildWatchRows(activePositions, watch.data?.items || []),
    [activePositions, watch.data?.items],
  );

  return (
    <main data-testid="watchlist-page" className="space-y-3">
      <HeatRow state={heat} />
      <PositionCoachCards state={organic} positions={activePositions} onSymbolSelect={onSymbolSelect} />
      <WatchTable state={watch} rows={watchRows} onSymbolSelect={onSymbolSelect} />
    </main>
  );
}

function HeatRow({ state }) {
  const heat = state.data || {};
  const rolling = heat.rolling_10_avg_r || {};
  const sectors = Object.entries(heat.sector_counts || {}).sort((a, b) => b[1] - a[1]);
  const maxSector = sectors[0] || null;
  const halfSize = Boolean(heat.half_size_mode);

  return (
    <section className="border border-hairline bg-card p-3" aria-label="HEAT ROW">
      <div className="grid gap-3 lg:grid-cols-[1fr_0.9fr_1.35fr]">
        <HeatPanel title="OPEN-RISK gauge">
          <OpenRiskGauge
            openRiskPct={heat.open_risk_pct}
            capPct={heat.cap_pct}
            loading={state.loading}
            error={state.error}
          />
        </HeatPanel>
        <HeatPanel title="SECTOR donut">
          <SectorDonut sectors={sectors} />
          <div className="mt-2 min-h-5 font-mono text-[11px] uppercase tracking-overline">
            {maxSector ? (
              <span className={maxSector[1] >= SECTOR_MAX ? "text-warn" : "text-ink3"}>
                {maxSector[0]} {maxSector[1]}
                {maxSector[1] >= SECTOR_MAX ? " !max" : ""}
              </span>
            ) : (
              <span className="text-ink3">no open sectors</span>
            )}
          </div>
        </HeatPanel>
        <HeatPanel title="PROGRESSIVE EXPOSURE">
          <div className="flex h-full min-h-44 flex-col justify-center">
            <div className="font-mono text-[12px] uppercase tracking-overline text-ink3">last-10-trade avg R</div>
            <div className="mt-2 font-mono text-[34px] font-bold leading-none tabular-nums text-ink">
              {rolling.value == null ? "-" : signed(rolling.value, "R")}
            </div>
            <div
              className={
                "mt-4 w-fit border px-2 py-1 font-mono text-[12px] font-bold uppercase tracking-overline " +
                (halfSize ? "border-bear-border bg-bear-bg text-bear" : "border-bull-border bg-bull-bg text-bull")
              }
            >
              {halfSize ? "HALF SIZE MODE" : "full size"}
            </div>
            <div className="mt-2 font-sans text-[12px] text-ink3">
              {rolling.n ? `n=${rolling.n} closed trades` : "needs closed trades"}
            </div>
          </div>
        </HeatPanel>
      </div>
    </section>
  );
}

function HeatPanel({ title, children }) {
  return (
    <div className="min-h-52 border border-hairline bg-raised p-3">
      <div className="mb-2 font-mono text-[11px] font-bold uppercase tracking-overline text-ink">{title}</div>
      {children}
    </div>
  );
}

function OpenRiskGauge({ openRiskPct, capPct, loading, error }) {
  const open = Number(openRiskPct || 0);
  const cap = Number(capPct || 0);
  const pct = cap > 0 ? Math.min(100, (open / cap) * 100) : 0;
  return (
    <div className="flex h-full min-h-44 flex-col justify-center">
      <div className="flex items-end gap-2">
        <span className="font-mono text-[34px] font-bold leading-none tabular-nums text-ink">{fmtPct(openRiskPct)}</span>
        <span className="pb-1 font-mono text-[12px] uppercase tracking-overline text-ink3">cap {fmtPct(capPct)}</span>
      </div>
      <div className="mt-4 h-5 border border-hairline bg-card">
        <div
          className={"h-full " + (cap > 0 && open > cap ? "bg-bear-dot" : pct >= 75 ? "bg-warn-dot" : "bg-bull-dot")}
          style={{ width: `${pct}%` }}
        />
      </div>
      <div className="mt-2 font-sans text-[12px] text-ink3">
        {loading ? "loading portfolio heat" : error ? error : `${fmtPct(openRiskPct)} vs cap ${fmtPct(capPct)}`}
      </div>
    </div>
  );
}

function SectorDonut({ sectors }) {
  const option = useMemo(
    () => ({
      color: ["#0f7a3d", "#9a5b00", "#175cd3", "#5b6472", "#b42318"],
      tooltip: { trigger: "item" },
      series: [
        {
          type: "pie",
          radius: ["52%", "78%"],
          avoidLabelOverlap: true,
          label: {
            formatter: ({ name, value }) => `${name} ${value}${value >= SECTOR_MAX ? " !max" : ""}`,
            fontFamily: "JetBrains Mono",
            fontSize: 10,
          },
          data: sectors.map(([name, value]) => ({
            name,
            value,
            itemStyle: value >= SECTOR_MAX ? { borderColor: "#9a5b00", borderWidth: 3 } : undefined,
          })),
        },
      ],
    }),
    [sectors],
  );
  if (!sectors.length) {
    return <div className="flex h-36 items-center justify-center border border-dashed border-hairline bg-card font-mono text-[11px] uppercase tracking-overline text-ink3">empty</div>;
  }
  return <EChart option={option} className="h-36" />;
}

function PositionCoachCards({ state, positions, onSymbolSelect }) {
  return (
    <section className="border border-hairline bg-card p-3" aria-label="POSITION COACH CARDS">
      <div className="mb-2 font-mono text-[11px] font-bold uppercase tracking-overline text-ink">POSITION COACH CARDS</div>
      {state.loading ? (
        <EmptyLine>loading open positions</EmptyLine>
      ) : state.error ? (
        <EmptyLine tone="bear">{state.error}</EmptyLine>
      ) : positions.length ? (
        <ul className="divide-y divide-hairline border border-hairline">
          {positions.map((position) => (
            <CoachCard
              key={position.trade_id || position.symbol}
              position={position}
              onSymbolSelect={onSymbolSelect}
            />
          ))}
        </ul>
      ) : (
        <EmptyLine>no open positions</EmptyLine>
      )}
    </section>
  );
}

function CoachCard({ position, onSymbolSelect }) {
  const coach = position.coach || {};
  const urgent = Boolean(coach.exit_now || /exit|overdue|unacted/i.test(coach.plain_instruction || coach.action || ""));
  const glyph = urgent ? "EXIT" : coach.phase === "EXTENSION" ? "!" : "o";
  const sentence = coach.plain_instruction || coach.action || "No coach action returned.";
  return (
    <li className={"flex items-center gap-3 px-3 py-2 font-mono text-[12px] " + (urgent ? "bg-bear-bg text-bear" : "bg-card text-ink")}>
      <span className={"w-10 shrink-0 font-bold uppercase " + (urgent ? "text-bear" : "text-ink3")}>{glyph}</span>
      <button
        type="button"
        onClick={() => onSymbolSelect?.({ symbol: position.symbol })}
        className="w-24 shrink-0 text-left font-bold uppercase text-ink hover:underline"
      >
        {position.symbol}
      </button>
      <span className="w-20 shrink-0 tabular-nums">{position.open_r == null ? "-" : signed(position.open_r, "R")}</span>
      <span className="min-w-0 flex-1 whitespace-normal font-sans text-[13px] leading-snug">{sentence}</span>
    </li>
  );
}

function WatchTable({ state, rows, onSymbolSelect }) {
  const [sort, setSort] = useState({ key: "symbol", dir: "asc" });
  const sortedRows = useMemo(() => sortRows(rows, sort), [rows, sort]);
  const cycleSort = (key) => {
    setSort((prev) => {
      if (prev.key !== key) return { key, dir: "desc" };
      if (prev.dir === "desc") return { key, dir: "asc" };
      return { key, dir: "desc" };
    });
  };

  return (
    <section className="border border-hairline bg-card p-3" aria-label="WATCH TABLE">
      <div className="mb-2 font-mono text-[11px] font-bold uppercase tracking-overline text-ink">WATCH TABLE</div>
      {state.loading ? (
        <EmptyLine>loading watch table</EmptyLine>
      ) : state.error ? (
        <EmptyLine tone="bear">{state.error}</EmptyLine>
      ) : sortedRows.length ? (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[980px] border-collapse font-mono text-[12px]">
            <thead>
              <tr className="border border-hairline bg-raised text-left text-[10px] uppercase tracking-overline text-ink3">
                {TABLE_COLUMNS.map((column) => (
                  <th key={column.key} className="border-r border-hairline px-2 py-2 last:border-r-0">
                    <button type="button" onClick={() => cycleSort(column.key)} className="uppercase hover:text-ink">
                      {column.label} {sort.key === column.key ? (sort.dir === "desc" ? "desc" : "asc") : ""}
                    </button>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {sortedRows.map((row) => (
                <WatchRow key={`${row.kind}-${row.symbol}-${row.trade_id || row.added_at || ""}`} row={row} onSymbolSelect={onSymbolSelect} />
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <EmptyLine>no watchlist symbols or open positions</EmptyLine>
      )}
    </section>
  );
}

function WatchRow({ row, onSymbolSelect }) {
  const timing = row.timing || {};
  const urgent = row.coach?.exit_now || row.exit_state?.state === "Broken";
  return (
    <tr className={"border-x border-b border-hairline " + (urgent ? "bg-bear-bg" : row.kind === "position" ? "bg-info-bg" : "bg-card")}>
      <td className="px-2 py-2 font-bold uppercase text-ink">
        <button
          type="button"
          onClick={() => onSymbolSelect?.({ symbol: row.symbol })}
          className="text-left hover:underline"
        >
          {row.symbol || "-"}
        </button>
      </td>
      <BandCell value={row.rs == null ? "-" : fixed(row.rs, 0)} band={bandRs(row.rs)} />
      <BandCell value={row.adr == null ? "-" : fixed(row.adr, 1)} band={bandAdr(row.adr)} />
      <BandCell value={timing.delivery_z == null ? "-" : fixed(timing.delivery_z, 1)} band={bandSigned(timing.delivery_z)} />
      <BandCell value={timing.dist_pivot == null ? "-" : signed(timing.dist_pivot, "%")} band={bandPivot(timing.dist_pivot)} />
      <BandCell value={exitStateText(row.exit_state)} band={urgent ? "bear" : row.exit_state?.state === "Weakening" ? "warn" : "bull"} />
      <BandCell value={row.trail || row.exit_state?.trail || "-"} band="muted" />
      <BandCell value={row.days_held == null ? "-" : String(row.days_held)} band="muted" />
      <BandCell value={row.open_r == null ? "-" : signed(row.open_r, "R")} band={bandSigned(row.open_r)} />
    </tr>
  );
}

function BandCell({ value, band = "muted" }) {
  const cls = {
    bull: "bg-bull-bg text-bull",
    warn: "bg-warn-bg text-warn",
    bear: "bg-bear-bg text-bear",
    muted: "bg-muted-bg text-ink2",
  }[band] || "bg-muted-bg text-ink2";
  return <td className={"border-l border-hairline px-2 py-2 tabular-nums " + cls}>{value}</td>;
}

function EChart({ option, className }) {
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

function EmptyLine({ children, tone = "muted" }) {
  return (
    <div className={"border border-dashed border-hairline bg-raised px-3 py-5 font-mono text-[11px] uppercase tracking-overline " + (tone === "bear" ? "text-bear" : "text-ink3")}>
      {children}
    </div>
  );
}

function buildWatchRows(activePositions, watchItems) {
  const manualBySymbol = new Map(watchItems.map((item) => [item.symbol, item]));
  const positionRows = activePositions.map((position) => {
    const manual = manualBySymbol.get(position.symbol) || {};
    manualBySymbol.delete(position.symbol);
    return {
      ...manual,
      ...position,
      kind: "position",
      adr: manual.adr ?? manual.timing?.adr ?? position.adr ?? position.timing?.adr ?? null,
      rs: manual.rs ?? position.rs ?? null,
      rs_as_of: manual.rs_as_of ?? position.rs_as_of ?? null,
      timing: manual.timing || position.timing || {},
      exit_state: manual.exit_state || position.exit_state || null,
      trail: manual.exit_state?.trail || position.trail || position.exit_state?.trail || null,
    };
  });
  const manualRows = [...manualBySymbol.values()].map((item) => ({
    ...item,
    kind: "watch",
    adr: item.adr ?? item.timing?.adr ?? null,
    days_held: null,
    open_r: null,
    trail: item.exit_state?.trail || null,
  }));
  return [...positionRows, ...manualRows];
}

function sortRows(rows, sort) {
  return [...rows].sort((a, b) => {
    if (a.kind !== b.kind) return a.kind === "position" ? -1 : 1;
    const av = sortValue(a, sort.key);
    const bv = sortValue(b, sort.key);
    if (typeof av === "string" || typeof bv === "string") {
      return sort.dir === "desc" ? String(bv).localeCompare(String(av)) : String(av).localeCompare(String(bv));
    }
    return sort.dir === "desc" ? bv - av : av - bv;
  });
}

function sortValue(row, key) {
  if (key === "symbol") return row.symbol || "";
  if (key === "dist_pivot") return numericSort(row.timing?.dist_pivot);
  if (key === "delivery_z") return numericSort(row.timing?.delivery_z);
  if (key === "exit_state") return exitStateText(row.exit_state);
  if (key === "trail") return row.trail || "";
  return numericSort(row[key]);
}

function numericSort(value) {
  return value == null || Number.isNaN(Number(value)) ? -Infinity : Number(value);
}

function exitStateText(exitState) {
  return exitState?.state || "-";
}

function bandRs(value) {
  if (value == null) return "muted";
  return Number(value) >= 70 ? "bull" : Number(value) >= 50 ? "warn" : "bear";
}

function bandAdr(value) {
  if (value == null) return "muted";
  return Number(value) >= 5 ? "warn" : "muted";
}

function bandSigned(value) {
  if (value == null) return "muted";
  return Number(value) > 0 ? "bull" : Number(value) < 0 ? "bear" : "muted";
}

function bandPivot(value) {
  if (value == null) return "muted";
  return Math.abs(Number(value)) <= 1 ? "bull" : Number(value) > 0 ? "warn" : "muted";
}

function fmtPct(value) {
  return value == null ? "-" : `${fixed(value, 1)}%`;
}

function fixed(value, digits = 1) {
  if (value == null || Number.isNaN(Number(value))) return "-";
  return Number(value).toFixed(digits).replace(/\.0$/, "");
}

function signed(value, suffix = "") {
  if (value == null || Number.isNaN(Number(value))) return "-";
  const n = Number(value);
  return `${n > 0 ? "+" : ""}${fixed(n, suffix === "R" ? 2 : 1)}${suffix}`;
}
