import { useMemo } from "react";
import { AppShell } from "../components/shell/AppShell";
import { SectionHeader } from "../components/ui/SectionHeader";
import { Chip } from "../components/ui/Chip";
import { useReport } from "../lib/useReport";
import { mapCandidates, triggerDistPct } from "../lib/candidates";
import { regimeHistoryBefore } from "../lib/regimeHistory";
import { sectorFor, SECTOR_SOURCE_LABEL } from "../lib/sectors";
import { deriveState } from "../lib/status";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";

/*
  MARKET (spec §13) — deeper than Home 1: where is participation
  strengthening or weakening?

  Honest scope (§0.1): full sector leadership needs universe-level
  per-sector breadth, which the nightly does not emit. What IS real here:
  the stored breadth/regime series, a rule-derived market character
  (heuristic, labelled), and tonight's candidates grouped by the vendor
  sector mapping. Anything beyond that is named as missing, not faked.
*/

export function Market() {
  const report = useReport();
  const hf = report.honesty_footer;
  const candidates = useMemo(() => mapCandidates(report), [report]);
  const history = useMemo(() => regimeHistoryBefore(report.session_date, 60), [report.session_date]);

  return (
    <AppShell breadcrumb={["Market"]}>
      <div className="flex flex-col gap-6">
        <div className="grid grid-cols-12 gap-4">
          {/* Breadth & regime history (§13.2 Row A, 8 cols) */}
          <div className="col-span-12 rounded-card border border-subtle bg-surface-1 px-5 py-4 xl:col-span-8">
            <SectionHeader
              title="Breadth history"
              subtitle="% of scanned universe above EMA50, per archived session"
              count={`${history.length} sessions`}
            />
            {history.length > 1 ? (
              <div className="h-56">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={history.map((h) => ({ date: h.date.slice(5), pct: h.pct_above_ema50 ?? null }))}
                    margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
                    <XAxis dataKey="date" tick={{ fill: "var(--text-tertiary)", fontSize: 10 }} stroke="var(--border)"
                      tickFormatter={(v: string, i: number) => (i % 5 === 0 ? v : "")} />
                    <YAxis domain={[0, 100]} tick={{ fill: "var(--text-tertiary)", fontSize: 10 }} stroke="var(--border)"
                      tickFormatter={(v: number) => v + "%"} width={44} />
                    <Tooltip cursor={{ stroke: "var(--border-strong)", strokeDasharray: "3 3" }}
                      content={({ active, payload }) => {
                        if (!active || !payload?.length) return null;
                        const d = payload[0].payload as { date: string; pct: number | null };
                        return (
                          <div className="rounded-btn border border-border-strong bg-surface-3 px-2.5 py-2 text-caption">
                            <div className="font-mono-num font-semibold text-ink-primary">{d.pct != null ? d.pct.toFixed(1) + "%" : "—"}</div>
                            <div className="text-ink-tertiary">{d.date}</div>
                          </div>
                        );
                      }} />
                    <Line type="monotone" dataKey="pct" stroke="var(--accent)" strokeWidth={1.5} dot={false} connectNulls />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <p className="text-t3 text-ink-tertiary">Not enough archived sessions to draw a series.</p>
            )}
            {/* regime letters under the line */}
            <div className="mt-2 flex gap-[3px]">
              {history.slice(-40).map((h) => {
                const label = h.regime ?? h.regime_replayed;
                const color = label === "BULL" ? "var(--positive)" : label === "BEAR" ? "var(--danger)" : label === "CHOP" ? "var(--warning)" : "var(--neutral)";
                return <div key={h.date} className="h-1 flex-1 rounded-full" style={{ background: color, opacity: 0.6 }}
                  title={`${h.date} — ${label ?? "not classified"}`} />;
              })}
            </div>
          </div>

          {/* Market character (§13.3) — rule-derived, labelled heuristic (4 cols) */}
          <div className="col-span-12 rounded-card border border-subtle bg-surface-1 px-5 py-4 xl:col-span-4">
            <SectionHeader title="Market character" subtitle="rule-derived · heuristic, not validated" />
            <div className="text-h3 font-bold tracking-tight text-ink-primary">{characterOf(hf).title}</div>
            <dl className="mt-3 grid grid-cols-[120px_1fr] gap-y-2">
              <CharacterRow k="Regime" v={hf.regime_note?.split(/[ (—]/)[0] ?? "—"} />
              <CharacterRow k="Participation" v={characterOf(hf).participation} />
              <CharacterRow k="NH-NL" v={characterOf(hf).nhnl} />
              <CharacterRow k="Volume" v={characterOf(hf).volume} />
              <CharacterRow k="Selectivity" v={characterOf(hf).selectivity} />
            </dl>
          </div>
        </div>

        {/* Candidates by sector (real join; scope disclosed) */}
        <div className="rounded-card border border-subtle bg-surface-1 px-5 py-4">
          <SectionHeader
            title="Candidates by sector"
            subtitle={`tonight's candidates only · ${SECTOR_SOURCE_LABEL}`}
            count={`${candidates.length} candidates`}
          />
          <SectorTable candidates={candidates} />
          <p className="mt-3 text-caption text-ink-tertiary">
            Market-wide sector breadth (every scanned symbol per sector) is not computed by the nightly yet —
            this table covers tonight's candidates only.
          </p>
        </div>
      </div>
    </AppShell>
  );
}

function CharacterRow({ k, v }: { k: string; v: string }) {
  return (
    <div className="contents">
      <dt className="text-t3 text-ink-muted">{k}</dt>
      <dd className="text-t3 font-medium text-ink-primary">{v}</dd>
    </div>
  );
}

/* Rule-derived market character (§13.3) — explicit thresholds, no prose
   generation. Heuristic, labelled as such in the header. */
function characterOf(hf: ReturnType<typeof useReport>["honesty_footer"]) {
  const pct = hf.pct_above_ema50;
  const participation = pct == null ? "—" : pct >= 55 ? "Broad" : pct <= 45 ? "Narrow" : "Mixed";
  const nhnl = hf.breadth?.analytics?.net_nh_nl ?? null;
  const nhnlRead = nhnl == null ? "—" : nhnl > 0.05 ? "Highs expanding" : nhnl < -0.05 ? "Highs fading" : "Balanced";
  const vol = hf.breadth?.analytics?.volume_ratio;
  const volume = vol == null ? "—" : vol > 1 ? "Above normal" : "Below normal";
  const regime = hf.regime_note?.split(/[ (—]/)[0] ?? "";
  const narrow = participation === "Narrow";
  let title = "UNCLEAR";
  if (regime === "CHOP") title = narrow ? "CHOP · NARROW LEADERSHIP" : "CHOP WITH MOMENTUM POCKETS";
  else if (regime === "BULL") title = narrow ? "BULL · NARROW LEADERSHIP" : "BROAD BULL";
  else if (regime === "BEAR") title = "BROAD DETERIORATION";
  const selectivity = regime === "CHOP" || regime === "BEAR" ? "High" : regime === "BULL" ? "Moderate" : "—";
  return { title, participation, nhnl: nhnlRead, volume, selectivity };
}

/* Sector table over tonight's candidates — count, avg RS, actionable count,
   best symbol. Vendor labels disclosed in the header. */
function SectorTable({ candidates }: { candidates: ReturnType<typeof mapCandidates> }) {
  const rows = useMemo(() => {
    const bySector = new Map<string, { n: number; rs: number[]; best: { symbol: string; rs: number } | null; actionable: number }>();
    for (const c of candidates) {
      const s = sectorFor(c.symbol);
      const sector = s?.sector ?? "Unclassified";
      const entry = bySector.get(sector) ?? { n: 0, rs: [], best: null, actionable: 0 };
      entry.n += 1;
      if (c.rsRank != null) entry.rs.push(c.rsRank);
      if (c.rsRank != null && (!entry.best || c.rsRank > entry.best.rs)) entry.best = { symbol: c.symbol, rs: c.rsRank };
      if (["PRIME", "READY", "NEAR_PIVOT"].includes(deriveState(c)) && triggerDistPct(c) != null) entry.actionable += 1;
      bySector.set(sector, entry);
    }
    return [...bySector.entries()]
      .map(([sector, e]) => ({
        sector,
        n: e.n,
        avgRs: e.rs.length ? e.rs.reduce((a, b) => a + b, 0) / e.rs.length : null,
        best: e.best,
        actionable: e.actionable,
      }))
      .sort((a, b) => (b.avgRs ?? -1) - (a.avgRs ?? -1));
  }, [candidates]);

  const unmapped = rows.find((r) => r.sector === "Unclassified");
  return (
    <div>
      <div className="grid grid-cols-[minmax(140px,2fr)_70px_90px_1fr_110px] gap-3 pb-1 text-[10px] font-medium uppercase tracking-wide text-ink-muted">
        <span>Sector</span><span className="text-right">Cands</span><span className="text-right">Avg RS</span>
        <span className="pl-4">Strongest</span><span className="text-right">Actionable</span>
      </div>
      {rows.map((r) => (
        <div key={r.sector} className="grid grid-cols-[minmax(140px,2fr)_70px_90px_1fr_110px] items-center gap-3 border-b border-subtle py-2 last:border-b-0">
          <span className="truncate text-t3 font-medium text-ink-primary">{r.sector}</span>
          <span className="text-right font-mono-num text-t3 text-ink-secondary">{r.n}</span>
          <span className="text-right font-mono-num text-t3 text-ink-secondary">{r.avgRs != null ? r.avgRs.toFixed(0) : "—"}</span>
          <span className="pl-4 truncate font-mono-num text-t3 text-ink-secondary">
            {r.best ? `${r.best.symbol} ${r.best.rs.toFixed(0)}` : "—"}
          </span>
          <span className="text-right">
            {r.actionable > 0 ? <Chip tone="positive">{r.actionable} ready-ish</Chip> : <span className="text-t3 text-ink-muted">—</span>}
          </span>
        </div>
      ))}
      {rows.length === 0 && <p className="text-t3 text-ink-tertiary">No candidates tonight.</p>}
      {unmapped && (
        <p className="pt-2 text-caption text-ink-tertiary">
          {unmapped.n} candidate{unmapped.n === 1 ? "" : "s"} not in the vendor sector mapping.
        </p>
      )}
    </div>
  );
}
