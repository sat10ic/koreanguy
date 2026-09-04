// Regime — "Can I take longs today?"
// Sticky posture strip (decision) → quadrant rows (evidence with 60-session
// history each) → regime ribbon (mode-per-day) + expert expansion.

import { useEffect, useMemo, useState } from "react";
import {
  getRegimeSummary,
  getRegimeHistory,
  getBreadthAnalytics,
  getMswing,
  getSetups,
  getPortfolioHeat,
} from "./api.js";
import {
  TermPanel,
  StatTile,
  StatusChip,
  BandChip,
  BarSpark,
  PlainRead,
  Gloss,
  Expandable,
  EmptyLine,
  MeterBar,
  fmtPct,
} from "./primitives.jsx";

const POSTURE_TEXT = {
  RISK_ON: "RISK-ON — the market supports long trades",
  SELECTIVE: "SELECTIVE — trade small and picky",
  DEFENSIVE: "DEFENSIVE — protect capital",
  NO_TRADE: "NO-TRADE — sit out today",
  STALE: "STALE — wait for fresh data",
};

function verdictFor(value, { good, bad, invert = false }) {
  if (value == null) return { word: "NO DATA", tone: "muted" };
  const v = invert ? -value : value;
  const g = invert ? -good : good;
  const b = invert ? -bad : bad;
  if (v >= g) return { word: "UP", tone: "bull" };
  if (v <= b) return { word: "DOWN", tone: "bear" };
  return { word: "MIXED", tone: "warn" };
}

export default function RegimePage({ onPosture, density }) {
  const [state, setState] = useState({ loading: true, error: null, data: null });
  const [breadth, setBreadth] = useState({ loading: true, rows: [] });
  const [mswing, setMswing] = useState({ loading: true, rows: [] });
  const [history, setHistory] = useState({ loading: true, rows: [] });
  const [setups, setSetups] = useState({ loading: true, rows: [] });
  const [heat, setHeat] = useState({ loading: true, data: null });

  useEffect(() => {
    let alive = true;
    setState({ loading: true, error: null, data: null });
    getRegimeSummary()
      .then((d) => !alive || setState({ loading: false, error: null, data: d }))
      .catch((e) => !alive || setState({ loading: false, error: e.message, data: null }));
    getBreadthAnalytics(60)
      .then((d) => !alive || setBreadth({ loading: false, rows: d?.rows || [] }))
      .catch(() => !alive || setBreadth({ loading: false, rows: [] }));
    getMswing(90)
      .then((d) => !alive || setMswing({ loading: false, rows: d?.rows || [] }))
      .catch(() => !alive || setMswing({ loading: false, rows: [] }));
    getRegimeHistory(90)
      .then((d) => !alive || setHistory({ loading: false, rows: d?.rows || [] }))
      .catch(() => !alive || setHistory({ loading: false, rows: [] }));
    getSetups({ limit: 5 })
      .then((d) => !alive || setSetups({ loading: false, rows: d?.candidates || [] }))
      .catch(() => !alive || setSetups({ loading: false, rows: [] }));
    getPortfolioHeat()
      .then((d) => !alive || setHeat({ loading: false, data: d }))
      .catch(() => !alive || setHeat({ loading: false, data: null }));
    return () => {
      alive = false;
    };
  }, []);

  const data = state.data;
  useEffect(() => {
    if (!onPosture) return;
    if (!data?.available) return onPosture(null);
    return onPosture(data.data_stale ? "STALE" : data.market_mode);
  }, [data, onPosture]);

  // ── Quadrant rows ────────────────────────────────────────────────
  const rows = useMemo(() => buildQuadrantRows(breadth.rows, mswing.rows), [breadth.rows, mswing.rows]);

  if (state.loading) {
    return (
      <div className="space-y-3">
        <div className="h-16 animate-pulse bg-hairline2" />
        <div className="h-48 animate-pulse bg-hairline2" />
        <div className="h-16 animate-pulse bg-hairline2" />
      </div>
    );
  }
  if (state.error) {
    return <EmptyLine tone="bear">couldn't reach the API — {state.error}</EmptyLine>;
  }
  if (!data?.available) {
    return (
      <EmptyLine>
        no regime data yet — run the pipeline to populate it (python manas.py run-eod --date YYYY-MM-DD)
      </EmptyLine>
    );
  }

  const stale = Boolean(data.data_stale);
  const mode = stale ? "STALE" : data.market_mode || "UNKNOWN";
  const riskBase = data.allowed_risk_min_pct;
  const riskMax = data.allowed_risk_max_pct;
  const pushes = data.push_allowed ?? data.pushes_enabled ?? mode !== "NO_TRADE";
  const openRisk = heat.data?.open_risk_pct ?? data.open_risk_pct;
  const openRiskCap = heat.data?.cap_pct ?? data.cap_pct;
  const riskPct = openRiskCap > 0 ? (openRisk / openRiskCap) * 100 : 0;
  const openRiskTone = openRiskCap > 0 && openRisk > openRiskCap ? "bear" : riskPct >= 75 ? "warn" : "bull";
  const why = data.explanation_text || data.read || "Use the governor law before choosing risk.";
  const maxCards = data.max_cards;
  const preferred = data.preferred_setups || data.allowed_setups || [];

  return (
    <div className="space-y-3">
      {/* ── Sticky posture strip ─────────────────────────────────── */}
      <section className="border border-hairline bg-card px-3 py-2">
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
          <span className="flex items-center gap-2">
            <StatusChip tone={stale ? "muted" : mode === "RISK_ON" ? "bull" : mode === "SELECTIVE" ? "warn" : "bear"} label={mode} />
            <span className="font-mono text-[11px] font-bold uppercase tracking-overline text-ink">{POSTURE_TEXT[mode] || mode}</span>
          </span>
          <span className="font-sans text-[12px] text-ink2">
            <span className="font-mono text-[9px] font-bold uppercase tracking-overline text-ink3">why: </span>
            {why}
          </span>
        </div>
        <div className="mt-2 grid gap-2 sm:grid-cols-2 lg:grid-cols-5">
          <StatTile label="Max open trades" value={maxCards ?? "—"} gloss="The most positions the governor allows at once." />
          <StatTile label="Risk / trade" value={riskBase == null && riskMax == null ? "—" : `${fmtPct(riskBase, 0)}-${fmtPct(riskMax, 0)}`} gloss="How much of your capital one trade may risk." />
          <StatTile label="Allowed setups" value={<span className="flex flex-wrap gap-1">{preferred.length ? preferred.slice(0, 3).map((s) => <BandChip key={s} tone="info">{s}</BandChip>) : "—"}</span>} gloss="The setups the regime lets you take." />
          <StatTile label="Money at risk" value={openRisk == null ? "—" : <span className="flex items-center gap-2">{fmtPct(openRisk, 1)}<MeterBar pct={riskPct} tone={openRiskTone} className="w-12" /></span>} sub={openRiskCap == null ? null : `of ${fmtPct(openRiskCap, 0)} cap`} gloss="Open risk vs the governor's cap." tone={openRiskTone} />
          <StatTile label="Trade alerts" value={pushes ? "ON" : "OFF"} tone={pushes ? "bull" : "muted"} gloss="Whether position alerts are pushed to you." />
        </div>
      </section>

      {/* ── Quadrant — each row carries 60 sessions of history ───── */}
      <TermPanel
        title="Can I take longs today?"
        sub="Five market reads, each with its recent history. Latest bar is highlighted."
        right={<BandChip tone={stale ? "muted" : mode === "RISK_ON" ? "bull" : mode === "SELECTIVE" ? "warn" : "bear"}>{mode}</BandChip>}
      >
        <div className="grid gap-1">
          {rows.map((row) => (
            <QuadrantRow key={row.label} {...row} />
          ))}
        </div>

        {density === "expert" && (
          <div className="mt-3 border-t border-hairline pt-2">
            <Expandable label="full numbers · last 3 sessions" defaultOpen>
              <Last3Table rows={breadth.rows} />
            </Expandable>
          </div>
        )}
      </TermPanel>

      {/* ── Regime ribbon ────────────────────────────────────────── */}
      <TermPanel
        title="Regime history"
        sub="Posture per session — color = state. Trade outcomes overlaid."
        right={<span className="font-mono text-[10px] text-ink3">{history.rows.length} sessions</span>}
      >
        <RegimeRibbon rows={history.rows} />
        <div className="mt-2 flex flex-wrap gap-x-3 gap-y-1 font-mono text-[9px] uppercase tracking-overline text-ink3">
          <span><span className="text-bull">■</span> risk-on</span>
          <span><span className="text-info">■</span> selective</span>
          <span><span className="text-warn">■</span> defensive</span>
          <span><span className="text-bear">■</span> no-trade</span>
          <span className="text-ink3">· dots = journal trade outcomes</span>
        </div>
      </TermPanel>

      {/* ── Top setups strip ─────────────────────────────────────── */}
      <TermPanel
        title="Tonight's top setups"
        sub="The strongest names that cleared the gates."
        right={setups.loading ? null : <span className="font-mono text-[10px] text-ink3">{setups.rows.length} shown</span>}
      >
        {setups.loading ? (
          <EmptyLine>loading top setups…</EmptyLine>
        ) : setups.rows.length === 0 ? (
          <EmptyLine>no setup candidates passed the quality gate</EmptyLine>
        ) : (
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-5">
            {setups.rows.map((s, i) => (
              <div key={`${s.symbol}-${i}`} className="border border-hairline bg-raised px-2 py-1.5">
                <div className="font-mono text-[13px] font-bold uppercase text-ink">{i + 1}. {s.symbol}</div>
                <div className="mt-0.5 font-mono text-[9px] uppercase tracking-overline text-ink3">
                  {s.setup_type || s.setup || "setup"} · rank {s.rank ?? i + 1}
                </div>
              </div>
            ))}
          </div>
        )}
      </TermPanel>
    </div>
  );
}

// ── One quadrant row: label pill + spark bars + latest + plain read ───────
function QuadrantRow({ label, question, values, mid, latest, read, gloss, tone, action }) {
  return (
    <div className="grid grid-cols-[120px_minmax(0,1fr)] items-center gap-3 border border-hairline2 bg-raised px-2 py-1.5 sm:grid-cols-[150px_220px_minmax(0,1fr)]">
      <div className="min-w-0">
        <div className="flex items-center gap-1">
          <BandChip tone={tone}>{label}</BandChip>
          <Gloss text={gloss} />
        </div>
        <div className="mt-0.5 font-sans text-[11px] leading-tight text-ink3">{question}</div>
      </div>
      <div className="min-w-0">
        <BarSpark values={values} mid={mid} />
      </div>
      <div className="min-w-0">
        <div className="flex items-baseline gap-2">
          <span className={`font-mono text-[16px] font-bold tabular-nums ${tone === "bull" ? "text-bull" : tone === "bear" ? "text-bear" : tone === "warn" ? "text-warn" : "text-ink"}`}>
            {latest}
          </span>
          <span className="text-xs font-bold uppercase tracking-overline text-ink2">{read}</span>
        </div>
        {action && <PlainRead label="" question="" read={action} tone="muted" />}
      </div>
    </div>
  );
}

// ── Build the five quadrant rows from breadth + mswing history ───────────
function buildQuadrantRows(breadthRows, mswingRows) {
  const pick = (k) => breadthRows.map((r) => r?.[k]).filter((v) => typeof v === "number");

  // MOMENTUM: mswing series (index momentum) with 9-day EMA, else burst diff.
  const msValues = mswingRows.map((r) => r?.mswing).filter((v) => typeof v === "number");
  const burstDiff = breadthRows
    .map((r) => (typeof r?.up_4pct === "number" && typeof r?.down_4pct === "number" ? r.up_4pct - r.down_4pct : null))
    .filter((v) => v != null);
  const momentumValues = msValues.length >= 2 ? msValues : burstDiff;
  const msNow = momentumValues.length ? momentumValues[momentumValues.length - 1] : null;

  const swing = pick("pct_above_10dma");
  const trend = pick("pct_above_50dma");
  const bias = pick("pct_above_200dma");
  const net = breadthRows
    .map((r) => (typeof r?.advances === "number" && typeof r?.declines === "number" ? r.advances - r.declines : null))
    .filter((v) => v != null);

  const last = breadthRows.length ? breadthRows[breadthRows.length - 1] : null;
  const lastOf = (a) => (a.length ? a[a.length - 1] : null);
  const one = (n, d = 0) => (typeof n === "number" ? n.toFixed(d) : "—");

  const swingNow = lastOf(swing);
  const trendNow = lastOf(trend);
  const biasNow = lastOf(bias);
  const netNow = lastOf(net);
  const msVerdict = verdictFor(msNow, { good: 0.2, bad: 0 });

  return [
    {
      label: "MOMENTUM",
      question: "Is the market speeding up?",
      tone: msVerdict.tone,
      values: momentumValues,
      mid: 0,
      latest: msNow == null ? "—" : msNow.toFixed(2),
      read: msVerdict.word.toLowerCase() === "up" ? "Speeding up" : msVerdict.tone === "warn" ? "No clear edge" : "Losing speed",
      gloss: "How fast the market is moving, and whether speed is above its own recent average.",
      action: msNow == null
        ? null
        : msNow <= 0
          ? "Do not start new longs on strength alone — wait for speed back above zero."
          : msNow < (mswingRows[mswingRows.length - 1]?.mswing_ema ?? 0)
            ? "Trade what is already working; be slower to add new names while speed fades."
            : "Fresh breakouts have the wind behind them. Full regime size is justified.",
    },
    {
      label: "SWING",
      question: "Is the short-term tide in?",
      tone: verdictFor(swingNow, { good: 55, bad: 45 }).tone,
      values: swing,
      mid: 50,
      latest: `${one(swingNow, 0)}%`,
      read: swingNow >= 55 ? "Short-term tide in" : swingNow <= 45 ? "Tide out" : "No clear edge",
      gloss: "How many stocks are holding their short-term 10-day support line.",
      action: swingNow >= 55
        ? "Pullback entries have a decent hit rate — buying dips is supported."
        : swingNow <= 45
          ? "Dip-buying is fighting the tide. Wait for a reclaim of the 10-day."
          : "No short-term edge either way — take only your best-structured name.",
    },
    {
      label: "TREND",
      question: "Are stocks in real uptrends?",
      tone: verdictFor(trendNow, { good: 55, bad: 45 }).tone,
      values: trend,
      mid: 50,
      latest: `${one(trendNow, 0)}%`,
      read: trendNow >= 55 ? "Uptrends intact" : trendNow <= 45 ? "Uptrends broken" : "Mixed",
      gloss: "How many stocks are above their medium-term 50-day trend line.",
      action: last?.net_new_highs_pct == null
        ? null
        : last.net_new_highs_pct > 0
          ? "There is a real leadership pool — breakout setups are worth taking."
          : "Leadership is thin. Expect breakouts to fail; demand tighter stops.",
    },
    {
      label: "BIAS",
      question: "What is the long-term picture?",
      tone: verdictFor(biasNow, { good: 55, bad: 45 }).tone,
      values: bias,
      mid: 50,
      latest: biasNow == null ? "—" : `${one(biasNow, 0)}%`,
      read: biasNow == null ? "No data" : biasNow >= 55 ? "Long-term up" : biasNow <= 45 ? "Long-term down" : "Long-term mixed",
      gloss: "How many stocks are in long-term uptrends (above their 200-day line).",
      action: biasNow == null
        ? null
        : biasNow >= 55
          ? "Weakness is a dip inside an uptrend. Hold winners through normal shakeouts."
          : biasNow <= 45
            ? "Rallies are counter-trend until this reclaims 50%. Book faster, trail tighter."
            : "Mixed floor — size at the regime's band, do not press.",
    },
    {
      label: "BREADTH",
      question: "Are more stocks up than down?",
      tone: verdictFor(netNow, { good: 40, bad: -40 }).tone,
      values: net,
      mid: 0,
      latest: `${last?.advances ?? "—"} up / ${last?.declines ?? "—"} down`,
      read: netNow > 0 ? "More up than down" : netNow < 0 ? "More down than up" : "Even",
      gloss: "Today's raw winners vs losers across the 400-name universe.",
      action: netNow > 0
        ? "Today's tape supports acting on a signal that fires."
        : "Today's tape is against you — let a signal prove itself before adding.",
    },
  ];
}

// ── Last 3 sessions table (expert) ──────────────────────────────────────
function Last3Table({ rows }) {
  const last3 = [...rows].slice(-3).reverse();
  const cols = [
    { key: "pct_above_10dma", label: "above 10-day" },
    { key: "pct_above_50dma", label: "above 50-day" },
    { key: "pct_above_200dma", label: "above 200-day" },
    { key: "advances", label: "up" },
    { key: "declines", label: "down" },
    { key: "net_breadth", label: "net breadth" },
  ];
  return (
    <div className="term-scroll overflow-x-auto">
      <table className="w-full border-collapse font-mono text-[11px]">
        <thead>
          <tr className="border border-hairline bg-raised text-left text-[9px] uppercase tracking-overline text-ink3">
            <th className="px-2 py-1.5">date</th>
            {cols.map((c) => (
              <th key={c.key} className="border-l border-hairline px-2 py-1.5">{c.label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {last3.map((r) => (
            <tr key={r.trade_date} className="border-b border-hairline2">
              <td className="px-2 py-1 text-ink3">{r.trade_date.slice(5)}</td>
              {cols.map((c) => {
                const v = r[c.key];
                const tone = typeof v === "number" && c.key !== "declines" && c.key !== "advances"
                  ? v >= 0 ? "text-bull" : "text-bear"
                  : "text-ink2";
                return (
                  <td key={c.key} className={`border-l border-hairline2 px-2 py-1 tabular-nums ${tone}`}>
                    {v ?? "—"}
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

// ── Regime ribbon: mode per session as a colored strip + trade dots ──────
const MODE_COLOR = { RISK_ON: "#0f7a3d", SELECTIVE: "#175cd3", DEFENSIVE: "#9a5b00", NO_TRADE: "#b42318" };

function RegimeRibbon({ rows }) {
  if (!rows.length) return <EmptyLine>no regime history yet</EmptyLine>;
  const withTrades = rows.some((r) => (r.journal_outcomes || []).length > 0);
  return (
    <div>
      <div className="flex h-7 w-full overflow-hidden border border-hairline bg-card">
        {rows.map((r) => (
          <div
            key={r.snapshot_date}
            title={`${r.snapshot_date} · ${r.market_mode}${r.journal_outcomes?.length ? ` · ${r.journal_outcomes.length} trade(s)` : ""}`}
            className="relative min-w-2 flex-1 border-r border-paper/40"
            style={{ backgroundColor: MODE_COLOR[r.market_mode] || "#c3ccd6" }}
          >
            {(r.journal_outcomes || []).map((t, i) => (
              <span
                key={i}
                title={`${t.symbol} ${t.r == null ? "" : `${t.r}R`}`}
                className="absolute bottom-0.5 rounded-full border border-white"
                style={{
                  left: "20%",
                  width: 5,
                  height: 5,
                  backgroundColor: t.r == null ? "#94a3b8" : Number(t.r) >= 0 ? "#22c55e" : "#fdecea",
                  borderColor: Number(t.r) >= 0 ? "#0f7a3d" : "#b42318",
                }}
              />
            ))}
          </div>
        ))}
      </div>
      {withTrades && (
        <div className="mt-1 font-mono text-[10px] text-ink3">trade outcomes overlaid on each session</div>
      )}
    </div>
  );
}