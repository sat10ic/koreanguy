// Journal — the numbers that say whether the process makes money.
// Stats row (win-rate / avg R / missed trades) → equity curve (line spark
// with drawdown) → cohort medians → compact trade log.

import { useEffect, useMemo, useState } from "react";
import { getJournal, getJournalVisuals, getExpectancy } from "./api.js";
import {
  TermPanel,
  StatTile,
  BandChip,
  EmptyLine,
  LineSpark,
  fmtPct,
  signed,
  fmtNum,
} from "./primitives.jsx";

export default function JournalPage({ density }) {
  const [journal, setJournal] = useState({ loading: true, error: null, data: null });
  const [visuals, setVisuals] = useState({ loading: true, data: null });
  const [expectancy, setExpectancy] = useState({ loading: true, data: null });

  useEffect(() => {
    let alive = true;
    getJournal()
      .then((d) => !alive || setJournal({ loading: false, error: null, data: d }))
      .catch((e) => !alive || setJournal({ loading: false, error: e.message, data: null }));
    getJournalVisuals()
      .then((d) => !alive || setVisuals({ loading: false, data: d }))
      .catch(() => !alive || setVisuals({ loading: false, data: null }));
    getExpectancy()
      .then((d) => !alive || setExpectancy({ loading: false, data: d }))
      .catch(() => !alive || setExpectancy({ loading: false, data: null }));
    return () => {
      alive = false;
    };
  }, []);

  const trades = journal.data?.trades || [];
  const stats = journal.data?.stats || {};
  const closed = useMemo(
    () =>
      trades
        .filter((t) => t.r_result != null)
        .slice()
        .sort((a, b) => `${a.trade_date}-${a.trade_id}`.localeCompare(`${b.trade_date}-${b.trade_id}`)),
    [trades],
  );
  const equity = useMemo(() => equitySeries(closed), [closed]);
  const lastEquity = equity.length ? equity[equity.length - 1].cumulative_r : 0;

  return (
    <div className="space-y-3">
      {/* ── Stats row ────────────────────────────────────────────── */}
      <section className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
        <StatTile label="Win rate" value={stats.win_pct == null ? "—" : fmtPct(stats.win_pct, 0)} sub={stats.closed_count ? `of ${stats.closed_count} closed` : "needs closed trades"} gloss="Share of closed trades that made money." />
        <StatTile label="Avg R" value={stats.avg_r == null ? "—" : signed(stats.avg_r, "R", 2)} tone={(stats.avg_r ?? 0) >= 0 ? "bull" : "bear"} gloss="Average reward per trade, in R." />
        <StatTile label="Total trades" value={fmtNum(trades.length)} sub={`${stats.r_count ?? 0} with R`} />
        <StatTile label="Top mistake" value={stats.top_mistake ? <span className="uppercase">{stats.top_mistake}</span> : "—"} sub="most-tagged mistake" />
      </section>

      {/* ── Equity curve ─────────────────────────────────────────── */}
      <TermPanel
        title="Equity in R"
        sub="Cumulative reward — the process line. Drawdown shaded."
        right={closed.length ? <BandChip tone={lastEquity >= 0 ? "bull" : "bear"}>{signed(lastEquity, "R", 2)}</BandChip> : null}
      >
        {journal.loading ? (
          <EmptyLine>loading equity…</EmptyLine>
        ) : journal.error ? (
          <EmptyLine tone="bear">{journal.error}</EmptyLine>
        ) : closed.length === 0 ? (
          <EmptyLine>no closed trades yet — add a trade to start tracking</EmptyLine>
        ) : (
          <EquityChart equity={equity} />
        )}
      </TermPanel>

      {/* ── Cohort medians ───────────────────────────────────────── */}
      <TermPanel
        title="Cohort medians"
        sub="What you got from taken vs skipped names."
        right={visuals.data ? <BandChip tone="info">{visuals.data?.cohort_counts?.taken ?? 0} taken</BandChip> : null}
      >
        {visuals.loading ? (
          <EmptyLine>loading cohorts…</EmptyLine>
        ) : !visuals.data?.cohort_medians ? (
          <EmptyLine>no cohort outcomes yet — they fill in as names resolve</EmptyLine>
        ) : (
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
            {["taken", "pushed-skipped", "armed-skipped", "refused"].map((key) => {
              const row = visuals.data.cohort_medians[key] || {};
              const value = row.median_r;
              return (
                <div key={key} className="border border-hairline bg-raised px-3 py-2">
                  <div className="font-mono text-[9px] uppercase tracking-overline text-ink3">{key.replace("-", " · ")}</div>
                  <div className={`mt-1 font-mono text-[20px] font-bold leading-none tabular-nums ${(value ?? 0) >= 0 ? "text-bull" : "text-bear"}`}>
                    {value == null ? "—" : signed(value, "R", 2)}
                  </div>
                  <div className="mt-1 font-mono text-[10px] uppercase tracking-overline text-ink3">n={row.n ?? 0}</div>
                </div>
              );
            })}
          </div>
        )}
        {visuals.data?.cohort_medians?.taken?.median_r != null &&
          visuals.data.cohort_medians["pushed-skipped"]?.median_r != null &&
          visuals.data.cohort_medians["pushed-skipped"].median_r > visuals.data.cohort_medians.taken.median_r && (
            <div className="mt-2 border border-warn-border bg-warn-bg px-2 py-1.5 font-sans text-[12px] text-ink">
              <span className="font-mono text-[9px] font-bold uppercase tracking-overline text-ink3">read: </span>
              You skip winners — pushed/skipped names outperformed taken. That's the edge to chase next.
            </div>
          )}
      </TermPanel>

      {/* ── Expectancy matrix (expert) ───────────────────────────── */}
      {density === "expert" && (
        <TermPanel title="Expectancy matrix" sub="Posterior R by setup x regime. Dim = thin sample.">
          <ExpectancyMatrix data={expectancy.data} />
        </TermPanel>
      )}

      {/* ── Trade log ────────────────────────────────────────────── */}
      <TermPanel title="Trade log" sub="Every logged trade, newest first.">
        <TradeLog trades={trades} loading={journal.loading} />
      </TermPanel>
    </div>
  );
}

// ── Equity chart: line + drawdown fill ───────────────────────────────────
function EquityChart({ equity }) {
  const values = equity.map((e) => e.cumulative_r);
  return (
    <div>
      <div className="flex items-end justify-between font-mono text-[10px] text-ink3">
        <span>{equity[0]?.date?.slice(5) || ""}</span>
        <span className="text-ink2">cumulative R</span>
        <span>{equity[equity.length - 1]?.date?.slice(5) || ""}</span>
      </div>
      <LineSpark values={values} height={90} tone={values[values.length - 1] >= 0 ? "bull" : "bear"} />
    </div>
  );
}

function equitySeries(closed) {
  let cumulative = 0;
  return closed.map((t) => {
    cumulative += Number(t.r_result || 0);
    return { date: t.trade_date, cumulative_r: cumulative };
  });
}

// ── Expectancy matrix ────────────────────────────────────────────────────
function ExpectancyMatrix({ data }) {
  const rows = data?.system || [];
  if (!rows.length) return <EmptyLine>no expectancy cells yet — they fill in as outcomes resolve</EmptyLine>;
  const families = [...new Set(rows.map((r) => r.setup_family))];
  const regimes = [...new Set(rows.map((r) => r.regime))];
  const byCell = new Map(rows.map((r) => [`${r.regime}|${r.setup_family}`, r]));
  return (
    <div className="term-scroll overflow-x-auto">
      <table className="w-full border-collapse font-mono text-[11px]">
        <thead>
          <tr className="border border-hairline bg-raised text-left text-[9px] uppercase tracking-overline text-ink3">
            <th className="px-2 py-1.5" />
            {regimes.map((regime) => (
              <th key={regime} className="border-l border-hairline px-2 py-1.5">{regime.replace("_", " ")}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {families.map((family) => (
            <tr key={family} className="border-b border-hairline2">
              <td className="px-2 py-1 font-bold uppercase text-ink3">{family}</td>
              {regimes.map((regime) => {
                const cell = byCell.get(`${regime}|${family}`);
                if (!cell) return <td key={regime} className="border-l border-hairline2 px-2 py-1 text-ink3">—</td>;
                const thin = Number(cell.n || 0) < 20;
                return (
                  <td key={regime} className={`border-l border-hairline2 px-2 py-1 ${thin ? "opacity-50" : ""}`}>
                    <span className={Number(cell.posterior_r ?? 0) >= 0 ? "text-bull" : "text-bear"}>
                      {signed(cell.posterior_r, "R", 2)}
                    </span>
                    <span className="ml-1 text-ink3">n={cell.n}</span>
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Trade log ────────────────────────────────────────────────────────────
function TradeLog({ trades, loading }) {
  return (
    <div>
      {loading ? (
        <EmptyLine>loading journal…</EmptyLine>
      ) : trades.length === 0 ? (
        <EmptyLine>no trades logged yet</EmptyLine>
      ) : (
        <div className="divide-y divide-hairline2 border border-hairline bg-card">
          {trades.slice(0, 12).map((t) => {
            const positive = Number(t.r_result ?? 0) >= 0;
            return (
              <div key={t.trade_id} className="grid grid-cols-2 items-center gap-x-3 gap-y-1 px-2 py-1.5 font-mono text-[11px] sm:grid-cols-[80px_1fr_1fr_80px]">
                <span className="text-ink3">{t.trade_date}</span>
                <span className="font-bold uppercase text-ink">{t.symbol}</span>
                <span className="truncate text-ink2">{t.setup || "—"}</span>
                <span className={`text-right font-bold tabular-nums ${positive ? "text-bull" : "text-bear"}`}>
                  {t.r_result == null ? (t.result === "open" ? "OPEN" : "—") : signed(t.r_result, "R", 2)}
                </span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}