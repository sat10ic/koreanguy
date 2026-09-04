import React, { useEffect, useMemo, useState } from "react";
import {
  fetchMarket,
  fetchDebate,
  fetchScannerPresets,
  fetchRegimeHistory,
  fetchBreadthHistory,
  fetchBreadthAnalytics,
} from "./api.js";
import MarketTab from "./MarketTab.jsx";
import { LawRow, ModelsSayPanel } from "./DeskTab.jsx";
import { useDensity } from "./DensityContext.jsx";
import { stripCitationCodes } from "./utils.js";
import { LastJobSummary, LiveWorkStrip } from "./livework/LiveWorkInspector.jsx";
import { Panel, SectionLabel, CallBanner, FunnelPanel, StatusChip } from "./components/v5/index.js";
import { BANDS } from "./components/v5/bands.js";
import { DataHealthStrip } from "./DataStatus.jsx";
import "./MarketHomeTab.v5.css";

// ------------------------------------------------------------------
// pure helpers (real payload only -- no synthetic fill anywhere)
// ------------------------------------------------------------------

function round(n, digits = 2) {
  if (n === null || n === undefined || Number.isNaN(Number(n))) return null;
  const f = Math.pow(10, digits);
  return Math.round(Number(n) * f) / f;
}

function fmtNum(n, digits = 2) {
  const r = round(n, digits);
  return r === null ? "—" : r;
}

function pct(n) {
  if (n === null || n === undefined) return "—";
  return `${Number(n) >= 0 ? "+" : ""}${round(n, 1)}%`;
}

function cleanText(text) {
  return stripCitationCodes(text || "").clean || text || "";
}

function fmtCount(n) {
  return n === null || n === undefined ? "—" : n;
}

const STANCE_LABEL = {
  STAND_ASIDE: "STAND ASIDE",
  SIT_OUT: "SIT OUT",
  CAUTION: "CAUTION",
  ACT_PER_PLAN: "ACT PER PLAN",
};

const STANCE_ICON = { STAND_ASIDE: "◧", SIT_OUT: "◧", CAUTION: "▲", ACT_PER_PLAN: "●" };

// Canonical Wyckoff-style four-phase cycle order (regime/snapshot.py::four_phase_label).
const FOUR_PHASE_ORDER = ["Demand Domination", "Lack of Supply", "Lack of Demand", "Supply Domination"];

function lawWhy(card) {
  const regime = card?.regime || {};
  const governor = card?.governor || {};
  const pieces = [];
  if (regime.four_phase) pieces.push(regime.four_phase);
  if (regime.mbi_day_color) pieces.push(`MBI ${String(regime.mbi_day_color).toLowerCase()}`);
  if ((governor.allowed_families || []).length) pieces.push(`${governor.allowed_families.join(" / ")} lead`);
  return pieces.length ? pieces.join(" · ") : "breadth and setup-family gates drive tonight's law";
}

function choppyBrakeLine(card) {
  const brake = card?.regime?.choppy_brake;
  if (brake?.active) return `Choppy brake ON — ${brake.reason || "no new entries"}`;
  return "Choppy brake OFF";
}

// F1: honest hero counts (pool_summary from /api/desk/debate + live scanner
// preset hit totals). No hardcoded fallback -- any field whose fetch failed
// or is unavailable renders "—", never a fake number.
function usePoolSummary(date) {
  const [pool, setPool] = useState(null);
  const [screenerHits, setScreenerHits] = useState(null);

  useEffect(() => {
    let cancelled = false;
    setPool(null);
    fetchDebate(date)
      .then((body) => {
        if (cancelled) return;
        const ps = body?.pool_summary;
        if (ps && typeof ps.actionable === "number") {
          setPool({ actionable: ps.actionable, shortlisted: ps.watchlist, poolTotal: ps.pool_total });
        }
      })
      .catch(() => {
        if (!cancelled) setPool(null);
      });
    return () => {
      cancelled = true;
    };
  }, [date]);

  useEffect(() => {
    let cancelled = false;
    setScreenerHits(null);
    fetchScannerPresets(date)
      .then((body) => {
        if (cancelled || !body?.available) return;
        const presets = body.presets || [];
        const total = presets
          .filter((p) => p.status === "LIVE" && typeof p.hits === "number")
          .reduce((sum, p) => sum + p.hits, 0);
        setScreenerHits(total);
      })
      .catch(() => {
        if (!cancelled) setScreenerHits(null);
      });
    return () => {
      cancelled = true;
    };
  }, [date]);

  return {
    actionable: pool?.actionable ?? null,
    shortlisted: pool?.shortlisted ?? null,
    poolTotal: pool?.poolTotal ?? null,
    screenerHits,
  };
}

// Generic data hook for the three regime/breadth series endpoints -- keeps
// last-confirmed data visible while a newer date loads (no full-surface
// "Loading" flash on date scrub), and is honest about unavailable series.
function useSeries(fetcher, date, days) {
  const [state, setState] = useState({ rows: null, available: null, loading: true, error: null });
  useEffect(() => {
    let cancelled = false;
    setState((s) => ({ ...s, loading: true, error: null }));
    fetcher(date, days)
      .then((body) => {
        if (cancelled) return;
        setState({ rows: body?.rows || [], available: !!body?.available, loading: false, error: null });
      })
      .catch((err) => {
        if (cancelled) return;
        setState((s) => ({ ...s, loading: false, error: String(err?.message || err) }));
      });
    return () => {
      cancelled = true;
    };
  }, [date, days]);
  return state;
}

const MODE_TONE = {
  RISK_ON: "var(--v5-green-dim)",
  SELECTIVE: "var(--v5-amber-glow)",
  DEFENSIVE: "var(--v5-line-soft)",
  NO_TRADE: "var(--v5-red-dim)",
};

// ------------------------------------------------------------------
// plain-SVG chart primitive shared by every trend/ratio panel below --
// draws N polylines over an optional set of categorical background bands
// (regime-mode per day) and an optional horizontal reference line. Reduced-
// motion respected via CSS (no animation is used here at all).
// ------------------------------------------------------------------
function TrendChart({
  rows,
  lines,
  bandKey,
  refLine,
  width = 520,
  height = 84,
  yFmt = (v) => fmtNum(v, 1),
}) {
  const dates = rows.map((r) => r.date_key ?? r.trade_date ?? r.snapshot_date);
  const valid = lines.filter((l) => rows.some((r) => typeof r[l.key] === "number"));
  if (!rows.length || !valid.length) {
    return <p className="v5-mkt-empty">{"— no series for this window"}</p>;
  }
  const allVals = valid.flatMap((l) => rows.map((r) => r[l.key]).filter((v) => typeof v === "number"));
  let min = Math.min(...allVals);
  let max = Math.max(...allVals);
  if (refLine !== undefined && refLine !== null) {
    min = Math.min(min, refLine);
    max = Math.max(max, refLine);
  }
  if (min === max) {
    min -= 1;
    max += 1;
  }
  const pad = (max - min) * 0.08;
  min -= pad;
  max += pad;
  const n = rows.length;
  const stepX = n > 1 ? width / (n - 1) : width;
  const yOf = (v) => height - ((v - min) / (max - min)) * height;

  const bands = bandKey
    ? rows.map((r, i) => {
        const x = i * stepX;
        const w = i < n - 1 ? stepX : stepX;
        const tone = MODE_TONE[r[bandKey]] || "transparent";
        return <rect key={`b${i}`} x={x - stepX / 2} y={0} width={w} height={height} fill={tone} />;
      })
    : null;

  const refY = refLine !== undefined && refLine !== null ? yOf(refLine) : null;

  return (
    <svg
      className="v5-mkt-chart"
      viewBox={`0 0 ${width} ${height}`}
      width="100%"
      height={height}
      role="img"
      aria-label={valid.map((l) => l.label).join(", ")}
      preserveAspectRatio="none"
    >
      {bands}
      {refY !== null && (
        <line x1={0} x2={width} y1={refY} y2={refY} className="v5-mkt-refline" strokeDasharray="3,3" />
      )}
      {valid.map((l) => {
        const pts = rows
          .map((r, i) => (typeof r[l.key] === "number" ? `${(i * stepX).toFixed(1)},${yOf(r[l.key]).toFixed(1)}` : null))
          .filter(Boolean)
          .join(" ");
        return (
          <polyline
            key={l.key}
            points={pts}
            fill="none"
            stroke={l.color || "var(--v5-teal)"}
            strokeWidth={l.width || 1.6}
            strokeLinejoin="round"
            strokeLinecap="round"
          />
        );
      })}
      {rows.map((r, i) =>
        r.warning_day ? (
          <circle key={`w${i}`} cx={i * stepX} cy={2} r={2.4} className="v5-mkt-warn-dot">
            <title>Warning day (red_count≥3) — {dates[i]}</title>
          </circle>
        ) : null
      )}
    </svg>
  );
}

// F9: per-section freshness stamps. Everything on this tab is EOD-derived
// (regime_snapshots / breadth_daily / sector_index_prices / fii_dii_daily --
// none of it comes from the live Fyers quote layer), so every stamp reads
// "EOD as of <date>" using whichever as-of/date field that section's own
// payload actually carries. Never fabricates "live" -- if a section has no
// date field yet (still loading / empty), the stamp is omitted rather than
// showing a fake date.
function eodCite(cite, dateStr) {
  if (!dateStr) return cite;
  const stamp = `EOD as of ${dateStr}`;
  return cite ? `${cite} · ${stamp}` : stamp;
}

function FreshnessStamp({ date }) {
  if (!date) return null;
  return <span className="v5-mkt-freshness mono">EOD as of {date}</span>;
}

function ChartLegend({ lines }) {
  return (
    <div className="v5-mkt-legend">
      {lines.map((l) => (
        <span key={l.key} className="v5-mkt-legend-item">
          <span className="v5-mkt-legend-swatch" style={{ background: l.color }} aria-hidden="true" />
          {l.label}
        </span>
      ))}
    </div>
  );
}

// ------------------------------------------------------------------
// section 1 — regime headline
// ------------------------------------------------------------------

function FourPhasePath({ phase }) {
  return (
    <ol className="v5-mkt-phasepath" aria-label="four-phase market cycle">
      {FOUR_PHASE_ORDER.map((p) => (
        <li key={p} className={p === phase ? "v5-mkt-phase-active" : ""} aria-current={p === phase ? "step" : undefined}>
          {p}
        </li>
      ))}
      {!FOUR_PHASE_ORDER.includes(phase) && phase ? <li className="v5-mkt-phase-active">{phase}</li> : null}
    </ol>
  );
}

// F1/T3 (USABILITY_UX_AUDIT_2026-07-19 exec-verdict bullet 3): the headline
// and the gate-passed/actionable/pending counts below it come verbatim from
// card.decision_summary -- the one shared contract also read by
// /api/flow/today's setups step and DebateTab's decision banner. No local
// beginner/expert headline derivation here anymore; every density sees the
// same reconciling sentence, expert additionally sees the raw counts.
function RegimeHeadline({ card, date }) {
  const { isExpert } = useDensity();
  if (!card || !card.available) return null;
  const call = card.tonights_call || {};
  const regime = card.regime || {};
  const governor = card.governor || {};
  const decision = card.decision_summary || null;
  const stance = STANCE_LABEL[call.stance] || call.stance || "NO CALL";
  const headline = decision ? decision.headline : "Decision summary unavailable.";
  const mode = governor.market_mode || regime.mode || "UNKNOWN";

  return (
    <section className="panel v5-mkt-hero">
      <div className="v5-mkt-sec-head">
        <SectionLabel>The verdict</SectionLabel>
        <FreshnessStamp date={regime.snapshot_date || card.date || date} />
      </div>
      <CallBanner
        stance={stance}
        icon={STANCE_ICON[call.stance] || "◧"}
        headline={headline}
        bullets={[
          { text: `${mode} market · ${regime.four_phase || "phase not computed"}` },
          regime.mbi_day_color
            ? { text: `MBI ${String(regime.mbi_day_color).toLowerCase()}${regime.warning_day ? " · warning day" : ""}` }
            : null,
        ].filter(Boolean)}
      />
      {isExpert && decision && (
        <p className="v5-mkt-decision-counts mono">
          {decision.gate_passed_count} gate-passed · {decision.actionable_count} actionable ·{" "}
          {decision.pending_decisions_count} pending decision{decision.pending_decisions_count === 1 ? "" : "s"}
        </p>
      )}
      <p className="v5-mkt-onequestion">
        <b>The one question:</b> Can I take risk today, and where? <span className="v5-mkt-onequestion-a">{lawWhy(card)}</span>
      </p>
      <FourPhasePath phase={regime.four_phase} />
      <p className={"v5-mkt-choppy" + (regime.choppy_brake?.active ? " v5-mkt-choppy-active" : "")}>
        {choppyBrakeLine(card)}
      </p>
      <div className="v5-mkt-lawrow">
        <LawRow governor={governor} heat={card.heat} />
      </div>
    </section>
  );
}

// ------------------------------------------------------------------
// section 2 — XP + MBI trend + current values
// ------------------------------------------------------------------

const MBI_DOT = { GREEN: "var(--v5-green)", WHITE: "var(--v5-ink-faint)", RED: "var(--v5-red)" };

function MbiRibbon({ rows }) {
  if (!rows.length) return <p className="v5-mkt-empty">{"— no MBI history"}</p>;
  return (
    <div className="v5-mkt-ribbon" role="img" aria-label="MBI day-color ribbon">
      {rows.map((r) => (
        <span
          key={r.snapshot_date}
          className="v5-mkt-ribbon-cell"
          style={{ background: MBI_DOT[r.mbi_day_color] || "var(--v5-line)" }}
          title={`${r.snapshot_date} · MBI ${r.mbi_day_color || "n/a"}${r.warning_day ? " · warning day" : ""}`}
        >
          {r.warning_day ? <span className="v5-mkt-ribbon-warn" aria-hidden="true" /> : null}
        </span>
      ))}
    </div>
  );
}

const R_LINES = [
  { key: "r4p5", label: "r4.5", color: "var(--v5-teal)" },
  { key: "r10", label: "r10", color: "var(--v5-amber-bright)" },
  { key: "r20", label: "r20", color: "var(--v5-green)" },
  { key: "r50", label: "r50", color: "var(--v5-red)" },
];

const XP_LINES = [{ key: "xp_value", label: "XP", color: "var(--v5-teal-ink)", width: 2 }];

function XpMbiSection({ date }) {
  const { rows, available, loading, error } = useSeries(fetchRegimeHistory, date, 90);
  const latest = rows && rows.length ? rows[rows.length - 1] : null;

  return (
    <section className="v5-mkt-grid2">
      <Panel title="XP trend" cite={eodCite("regime_snapshots", latest?.snapshot_date)}>
        <PlainRead>XP is the desk’s market permission score. Rising XP allows more aggression; low or falling XP means protect capital and demand cleaner setups.</PlainRead>
        {loading && !rows?.length && <p className="v5-mkt-empty">Loading…</p>}
        {error && !rows?.length && <p className="v5-mkt-empty">Could not load XP history.</p>}
        {!loading && available === false && <p className="v5-mkt-empty">{"— no XP history yet"}</p>}
        {rows && rows.length > 0 && (
          <>
            <TrendChart rows={rows.map((r) => ({ ...r, date_key: r.snapshot_date }))} lines={XP_LINES} bandKey="market_mode" />
            <div className="v5-mkt-currentrow">
              <StatusChip label="XP now" value={latest ? fmtNum(latest.xp_value, 2) : "—"} title="Current XP (regime_snapshots.xp_value)" />
              <StatusChip label="mode" value={latest?.market_mode || "—"} qual />
              <StatusChip label="as of" value={latest?.snapshot_date || "—"} qual />
            </div>
          </>
        )}
      </Panel>

      <Panel title="MBI" cite={eodCite("regime_snapshots", latest?.snapshot_date)}>
        <PlainRead>MBI checks whether momentum is healthy across several timeframes. Green supports swing entries; warning or red readings call for smaller exposure or patience.</PlainRead>
        {loading && !rows?.length && <p className="v5-mkt-empty">Loading…</p>}
        {!loading && available === false && <p className="v5-mkt-empty">{"— no MBI history yet"}</p>}
        {rows && rows.length > 0 && (
          <>
            <MbiRibbon rows={rows} />
            <TrendChart rows={rows.map((r) => ({ ...r, date_key: r.snapshot_date }))} lines={R_LINES} refLine={100} />
            <ChartLegend lines={R_LINES} />
            <div className="v5-mkt-currentrow">
              <StatusChip
                label="day"
                value={latest?.mbi_day_color || "—"}
                tone={latest?.mbi_day_color === "GREEN" ? "green" : latest?.mbi_day_color === "RED" ? "red" : "neutral"}
              />
              {R_LINES.map((l) => (
                <StatusChip key={l.key} label={l.label} value={latest ? fmtNum(latest[l.key], 0) : "—"} />
              ))}
              {latest?.warning_day ? <StatusChip label="flag" value="warning day (red≥3)" tone="red" qual /> : null}
            </div>
          </>
        )}
      </Panel>
    </section>
  );
}

// ------------------------------------------------------------------
// section 3 — Market Breadth V2.0 panels
// ------------------------------------------------------------------

const DMA_LINES = [
  { key: "pct_above_10dma", label: "%>10dma", color: "var(--v5-teal)" },
  { key: "pct_above_20dma", label: "%>20dma", color: "var(--v5-amber-bright)" },
  { key: "pct_above_40dma", label: "%>40dma", color: "var(--v5-green)" },
  { key: "pct_above_50dma", label: "%>50dma", color: "var(--v5-red)" },
];

const NET_BREADTH_LINES = [{ key: "net_breadth", label: "net breadth (pp)", color: "var(--v5-teal-ink)", width: 2 }];

const AD_RATIO_LINES = [
  { key: "ad_ratio_5d", label: "5d AD ratio", color: "var(--v5-teal)" },
  { key: "ad_ratio_10d", label: "10d AD ratio", color: "var(--v5-amber-bright)" },
];

const MONTHLY_LINES = [
  { key: "up_25pct_month", label: "25% up (mo)", color: "var(--v5-green)" },
  { key: "down_25pct_month", label: "25% down (mo)", color: "var(--v5-red)" },
  { key: "up_50pct_month", label: "50% up (mo)", color: "var(--v5-teal)" },
  { key: "down_50pct_month", label: "50% down (mo)", color: "var(--v5-amber-bright)" },
];

const DMA_CROSS_LINES = [
  { key: "pct_10dma_gt_20dma", label: "%10dma>20dma", color: "var(--v5-teal)" },
  { key: "pct_20dma_gt_40dma", label: "%20dma>40dma", color: "var(--v5-amber-bright)" },
];

const NH_NL_FOSBACK_LINES = [
  { key: "net_nh_nl", label: "net NH-NL", color: "var(--v5-teal)" },
  { key: "fosback_hl_logic_index", label: "Fosback HL", color: "var(--v5-amber-bright)" },
];

const VOLATILITY_LINES = [
  { key: "volatility_ratio", label: "vol ratio", color: "var(--v5-green)" },
];

const BO_SF_LINES = [
  { key: "bo_sf_ratio", label: "BO S/F", color: "var(--v5-teal)" },
  { key: "bd_sf_ratio", label: "BD S/F", color: "var(--v5-red)" },
];

function NeedsIngestCard({ title, why }) {
  return (
    <Panel title={title} cite="needs ingest">
      <p className="v5-mkt-needsingest">
        <span className="v5-mkt-needsingest-tag">NEEDS INGEST</span> {why}
      </p>
    </Panel>
  );
}

function PlainRead({ children }) {
  return (
    <p className="v5-mkt-plainread">
      <span>Plain-English read</span>{children}
    </p>
  );
}

function hasSeries(rows, keys) {
  return Boolean(rows?.some((row) => keys.some((key) => typeof row?.[key] === "number")));
}

function BreadthSection({ date }) {
  const hist = useSeries(fetchBreadthHistory, date, 90);
  const analytics = useSeries(fetchBreadthAnalytics, date, 90);
  const latestHist = hist.rows && hist.rows.length ? hist.rows[hist.rows.length - 1] : null;
  const latestAnalytics = analytics.rows && analytics.rows.length ? analytics.rows[analytics.rows.length - 1] : null;
  const hasMonthly = hasSeries(analytics.rows, MONTHLY_LINES.map((line) => line.key));
  const hasDmaCross = hasSeries(analytics.rows, DMA_CROSS_LINES.map((line) => line.key));
  const hasNhNl = hasSeries(analytics.rows, ["net_nh_nl"]);
  const hasFosback = hasSeries(analytics.rows, ["fosback_hl_logic_index"]);
  const hasVolatility = hasSeries(analytics.rows, ["volatility_ratio"]);
  const hasBoSf = hasSeries(analytics.rows, ["bo_sf_ratio", "bd_sf_ratio"]);

  return (
    <section className="v5-mkt-breadth">
      <div className="v5-mkt-sec-head">
        <SectionLabel>Market Breadth V2.0</SectionLabel>
        <FreshnessStamp date={latestHist?.trade_date || latestAnalytics?.trade_date} />
      </div>
      <PlainRead>
        This asks whether strength is broad enough to trust. More stocks participating means breakouts have better odds; weak participation means stay selective or in cash.
      </PlainRead>
      <p className="v5-mkt-breadth-cite">
        Stockbee framework — reverse-engineered from{" "}
        <span className="mono-num">Market Breadth V2.0.xlsm</span>; formulas honored per REVERSE_ENGINEERING.md §12.
      </p>
      <div className="v5-mkt-grid2">
        <Panel title="% above DMA" cite={eodCite("breadth_daily", latestHist?.trade_date)}>
          <PlainRead>Shows how many stocks are above their trend lines. Above 50% means strength is spreading; below 50% means fewer stocks are carrying the market.</PlainRead>
          {hist.available === false && <p className="v5-mkt-empty">{"— no breadth history yet"}</p>}
          {hist.rows && hist.rows.length > 0 && (
            <>
              <TrendChart rows={hist.rows.map((r) => ({ ...r, date_key: r.trade_date }))} lines={DMA_LINES} refLine={50} />
              <ChartLegend lines={DMA_LINES} />
              <div className="v5-mkt-currentrow">
                {DMA_LINES.map((l) => (
                  <StatusChip
                    key={l.key}
                    label={l.label}
                    value={latestHist ? fmtNum(latestHist[l.key], 1) : "—"}
                    raw={latestHist ? latestHist[l.key] : null}
                    band={BANDS.pctAboveDma}
                    title="Share of stocks above this moving average. Above 60% = broad participation; below 40% = few names carrying the market."
                  />
                ))}
              </div>
            </>
          )}
        </Panel>

        <Panel title="Net breadth" cite={eodCite("up_4pct − down_4pct", latestAnalytics?.trade_date)}>
          <PlainRead>Compares strong gainers with strong losers. Positive is supportive; negative means selling pressure is winning underneath the index.</PlainRead>
          {analytics.available === false && <p className="v5-mkt-empty">No strong-gainer versus strong-loser history is available yet. Run the nightly update after breadth data has been ingested.</p>}
          {analytics.rows && analytics.rows.length > 0 && (
            <>
              <TrendChart rows={analytics.rows.map((r) => ({ ...r, date_key: r.trade_date }))} lines={NET_BREADTH_LINES} refLine={0} />
              <div className="v5-mkt-currentrow">
                <StatusChip label="net breadth" value={latestAnalytics ? fmtNum(latestAnalytics.net_breadth, 2) : "—"} />
                <StatusChip label="advances" value={fmtCount(latestAnalytics?.advances)} />
                <StatusChip label="declines" value={fmtCount(latestAnalytics?.declines)} />
              </div>
            </>
          )}
        </Panel>

        <Panel title="5d / 10d AD ratio" cite="Stockbee">
          <PlainRead>Compares advancing stocks with declining stocks over one and two weeks. Above 1 favours buyers; below 1 favours sellers.</PlainRead>
          {!analytics.loading && (!analytics.rows || analytics.rows.length === 0) && <p className="v5-mkt-empty">No advance/decline history is available yet. Run the nightly update after breadth ingest completes.</p>}
          {analytics.rows && analytics.rows.length > 0 && (
            <>
              <TrendChart rows={analytics.rows.map((r) => ({ ...r, date_key: r.trade_date }))} lines={AD_RATIO_LINES} refLine={1} />
              <ChartLegend lines={AD_RATIO_LINES} />
              <div className="v5-mkt-currentrow">
                <StatusChip label="5d" value={latestAnalytics ? fmtNum(latestAnalytics.ad_ratio_5d, 2) : "—"} />
                <StatusChip label="10d" value={latestAnalytics ? fmtNum(latestAnalytics.ad_ratio_10d, 2) : "—"} />
              </div>
            </>
          )}
        </Panel>

        <Panel title="Monthly move breadth" cite="up/down 25% & 50%">
          <PlainRead>Counts unusually large monthly winners and losers. It reveals whether explosive opportunity or destructive downside is dominating.</PlainRead>
          {!analytics.loading && !hasMonthly && <p className="v5-mkt-empty">Monthly winner/loser counts are not populated yet. This panel will appear after the nightly breadth ingest has enough history; no zero is being inferred.</p>}
          {hasMonthly && (
            <>
              <TrendChart rows={analytics.rows.map((r) => ({ ...r, date_key: r.trade_date }))} lines={MONTHLY_LINES} />
              <ChartLegend lines={MONTHLY_LINES} />
              <div className="v5-mkt-currentrow">
                {MONTHLY_LINES.map((l) => (
                  <StatusChip key={l.key} label={l.label} value={fmtCount(latestAnalytics?.[l.key])} />
                ))}
              </div>
            </>
          )}
        </Panel>

        <Panel title="DMA-cross structure" cite="%10dma>20dma / %20dma>40dma">
          <PlainRead>Checks whether shorter trends sit above longer trends across the market. Higher readings mean more stocks are structurally trending up.</PlainRead>
          {!analytics.loading && !hasDmaCross && <p className="v5-mkt-empty">Moving-average cross counts are not populated yet. This panel will appear after those breadth fields are ingested; no blank chart or fake zero is shown.</p>}
          {hasDmaCross && (
            <>
              <TrendChart rows={analytics.rows.map((r) => ({ ...r, date_key: r.trade_date }))} lines={DMA_CROSS_LINES} refLine={50} />
              <ChartLegend lines={DMA_CROSS_LINES} />
              <div className="v5-mkt-currentrow">
                <StatusChip label="%10>20" value={latestAnalytics ? fmtNum(latestAnalytics.pct_10dma_gt_20dma, 1) : "—"} />
                <StatusChip label="%20>40" value={latestAnalytics ? fmtNum(latestAnalytics.pct_20dma_gt_40dma, 1) : "—"} />
              </div>
            </>
          )}
        </Panel>

        <Panel title="NH-NL / Fosback HL Logic Index" cite="breadth_counts">
          <PlainRead>Fosback's High-Low Logic Index measures market conflict. High readings mean both new highs and new lows are elevated.</PlainRead>
          {!analytics.loading && !hasNhNl && !hasFosback && (
            <p className="v5-mkt-needsingest">
              <span className="v5-mkt-needsingest-tag">NEEDS INGEST</span> Needs regime_universe_metrics.new_highs/new_lows ingest — currently empty. Fosback Index = min(NH%, NL%) × 100 once populated.
            </p>
          )}
          {(hasNhNl || hasFosback) && (
            <>
              <TrendChart rows={analytics.rows.map((r) => ({ ...r, date_key: r.trade_date }))} lines={NH_NL_FOSBACK_LINES} />
              <ChartLegend lines={NH_NL_FOSBACK_LINES} />
              <div className="v5-mkt-currentrow">
                <StatusChip label="net NH-NL" value={latestAnalytics ? fmtNum(latestAnalytics.net_nh_nl, 2) : "—"} />
                <StatusChip label="Fosback Index" value={latestAnalytics ? fmtNum(latestAnalytics.fosback_hl_logic_index, 2) : "—"} />
              </div>
            </>
          )}
        </Panel>

        <Panel title="Volatility ratio" cite="range expansion / contraction">
          <PlainRead>Compares range expansion with range contraction. Higher values mean volatility expansion is leading.</PlainRead>
          {!analytics.loading && !hasVolatility && (
            <p className="v5-mkt-needsingest">
              <span className="v5-mkt-needsingest-tag">NEEDS INGEST</span> Needs daily-range ingest (Range &lt;3% / Range &ge;5.01% counts) — not yet in breadth_daily.
            </p>
          )}
          {hasVolatility && (
            <>
              <TrendChart rows={analytics.rows.map((r) => ({ ...r, date_key: r.trade_date }))} lines={VOLATILITY_LINES} refLine={1} />
              <div className="v5-mkt-currentrow">
                <StatusChip label="vol ratio" value={latestAnalytics ? fmtNum(latestAnalytics.volatility_ratio, 2) : "—"} />
                <StatusChip label="volume ratio" value={latestAnalytics ? fmtNum(latestAnalytics.volume_ratio, 2) : "—"} />
              </div>
            </>
          )}
        </Panel>

        <Panel title="BO / BD sustained-failed ratios" cite="breakout / breakdown">
          <PlainRead>Measures the strength of breakouts and breakdowns. Values above 1 mean breakouts/breakdowns are sustained rather than failing.</PlainRead>
          {!analytics.loading && !hasBoSf && (
            <p className="v5-mkt-needsingest">
              <span className="v5-mkt-needsingest-tag">NEEDS INGEST</span> Needs breakout/breakdown sustained-vs-failed counts — not yet ingested.
            </p>
          )}
          {hasBoSf && (
            <>
              <TrendChart rows={analytics.rows.map((r) => ({ ...r, date_key: r.trade_date }))} lines={BO_SF_LINES} refLine={1} />
              <ChartLegend lines={BO_SF_LINES} />
              <div className="v5-mkt-currentrow">
                <StatusChip label="BO S/F" value={latestAnalytics ? fmtNum(latestAnalytics.bo_sf_ratio, 2) : "—"} />
                <StatusChip label="BD S/F" value={latestAnalytics ? fmtNum(latestAnalytics.bd_sf_ratio, 2) : "—"} />
              </div>
            </>
          )}
        </Panel>
      </div>
    </section>
  );
}

// ------------------------------------------------------------------
// section 4 — Sectors / Themes (KEEP existing section, retained as-is)
// ------------------------------------------------------------------

function marketContextSummary(data) {
  if (!data?.available) return "Market context unavailable.";
  const byNorm = new Map((data.indices || []).map((r) => [String(r.symbol || "").toUpperCase().replace(/[^A-Z0-9]/g, ""), r]));
  const nifty = byNorm.get("NIFTY50");
  const midsml = byNorm.get("NIFTYMIDSML400");
  const sectors = [...(data.sectors || [])]
    .filter((s) => s.move_pct !== null && s.move_pct !== undefined)
    .sort((a, b) => b.move_pct - a.move_pct)
    .slice(0, 2)
    .map((s) => s.name || s.symbol);
  const rotation = sectors.length ? `Leading: ${sectors.join(", ")}` : "Leading sectors not available";
  return `NIFTY ${pct(nifty?.returns?.["1d"])} · MIDSML ${pct(midsml?.returns?.["1d"])} · VIX ${data.vix?.value ?? "-"} (${data.vix?.band || "n/a"}) · ${rotation}`;
}

function SectorsThemesSection({ date }) {
  const [data, setData] = useState(null);

  useEffect(() => {
    let cancelled = false;
    fetchMarket(date, true)
      .then((body) => {
        if (!cancelled) setData(body);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [date]);

  return (
    <Panel title="Market rotation" cite={eodCite("Nifty · ChartsMaze · FII/DII", data?.as_of)}>
      <PlainRead>This shows where money is concentrating. Prefer setups in leading groups; a good stock fighting a weak group has less tailwind.</PlainRead>
      <p className="v5-mkt-context-line">{marketContextSummary(data)}</p>
      <div className="v5-mkt-evidence-full"><MarketTab date={date} /></div>
    </Panel>
  );
}

// ------------------------------------------------------------------
// section 5 — opportunity map + funnel (supporting, not hero) + one action
// ------------------------------------------------------------------

function ModelsSayAddendum({ card }) {
  const { isExpert } = useDensity();
  if (!isExpert || !card?.models_say) return null;
  return <ModelsSayPanel modelsSay={card.models_say} volForecast={card.regime?.vol_forecast} />;
}

function OpportunitySection({ card, summary, onNavigate }) {
  const governor = card?.governor || {};
  const families = governor.allowed_families || [];
  const urgent = (card?.coach || []).length || 0;
  const hitsLabel = summary.screenerHits === null ? "—" : summary.screenerHits;
  const primaryLabel = urgent
    ? `Manage open (${urgent} needs action)`
    : (summary.actionable || 0) > 0
    ? "Size & arm the takes"
    : `Run tonight's scanners (${hitsLabel} hits)`;
  const primaryTab = urgent ? "POSITIONS" : (summary.actionable || 0) > 0 ? "SHORTLIST" : "SCANNERS";

  const stages = [
    { key: "scanned", label: "screener hits", n: summary.screenerHits },
    { key: "pool", label: "in tonight's pool", n: summary.poolTotal },
    { key: "shortlisted", label: "shortlisted", n: summary.shortlisted },
    { key: "actionable", label: "actionable", n: summary.actionable },
  ];

  return (
    <section className="v5-mkt-grid2">
      <Panel title="Opportunity now" cite="governor.allowed_families">
        <PlainRead>This is the practical answer: which setup types suit today’s Indian market, or whether cash is the better position.</PlainRead>
        <p className="v5-mkt-opp-line">
          {families.length ? `Rewarded now: ${families.join(", ")}` : "No mechanism family is currently rewarded — cash is the position."}
        </p>
        <button type="button" className="v5-mkt-primary-action" onClick={() => onNavigate(primaryTab)}>
          {primaryLabel} →
        </button>
      </Panel>
      <Panel title="Funnel (supporting evidence)" cite="tonight's pipeline">
        <PlainRead>Shows how many names survived each quality check. A small final number is selectivity, not a broken scanner.</PlainRead>
        <FunnelPanel stages={stages} />
      </Panel>
    </section>
  );
}

// ------------------------------------------------------------------
// section 6 — live work (mounted globally in App.jsx; this is the
// always-visible summary/launcher for it — replaces the old placeholder
// Activity Log + one-shot PipelineProgress)
// ------------------------------------------------------------------

function LiveWorkSection() {
  return (
    <Panel title="Live work" cite="useJobStream">
      <LastJobSummary />
    </Panel>
  );
}

// ------------------------------------------------------------------
// root
// ------------------------------------------------------------------

export default function MarketHomeTab({ date, card, loading, error, onNavigate, coverage }) {
  const summary = usePoolSummary(date);

  if (loading) return <div className="empty-state">Loading...</div>;
  if (error) {
    return (
      <div className="empty-state">
        <div className="empty-state-icon">⚠</div>
        <p className="empty-state-line">Could not load the market home.</p>
        <p className="empty-state-sub">{error}</p>
      </div>
    );
  }
  if (!card || !card.available) {
    return (
      <div className="empty-state">
        <div className="empty-state-icon">○</div>
        <p className="empty-state-line">No run for {date} yet.</p>
        <p className="empty-state-sub">The desk runs after market close.</p>
      </div>
    );
  }

  return (
    <div className="v5-mkt-home">
      <LiveWorkStrip />
      <DataHealthStrip coverage={coverage} />
      <RegimeHeadline card={card} date={date} />
      <XpMbiSection date={date} />
      <BreadthSection date={date} />
      <SectorsThemesSection date={date} />
      <OpportunitySection card={card} summary={summary} onNavigate={onNavigate} />
      <ModelsSayAddendum card={card} />
      <LiveWorkSection />
    </div>
  );
}
