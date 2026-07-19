import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  addWatchlistSymbol,
  addFocusSymbol,
  deleteUserScreen,
  fetchAlphaActivity,
  fetchEarningsUpcoming,
  fetchScannerPresets,
  fetchUserScreens,
  pushSymbolToDebate,
  runDeskScreener,
  runScannerPreset,
  saveUserScreen,
} from "./api.js";
import ChartDrawer from "./ChartDrawer.jsx";
import PriceSparkThumb from "./PriceSparkThumb.jsx";
import { colorScale } from "./viz.js";
import {
  SectionLabel,
  Panel,
  LaneCard,
  StatusChip,
} from "./components/v5/index.js";
import "./ScannersTab.v5.css";

// ------------------------------------------------------------------
// TradeTM opportunity/execution stage + parallel mechanism lane map.
// Every preset key here is a real key from scanner_presets.PRESET_REGISTRY
// (manas_os/api/app.py -> /api/scanners/presets). Placement is derived from
// each preset's own `owner`/`recipe_line`/`cite` text -- not invented.
// ------------------------------------------------------------------

const STAGES = [
  {
    key: "momentum",
    label: "Momentum / Velocity Entries",
    sub: "Breakout, burst and Strong-Start continuation — tight stop, LTF trail",
  },
  {
    key: "basepattern",
    label: "Base / Pattern Pullbacks",
    sub: "Consolidation, contraction and reversal — pullback to a rising MA, wider structural stop",
  },
  {
    key: "ipobase",
    label: "IPO Base / Catalyst",
    sub: "Fresh-listing base coil and earnings-power gap — catalyst-conditioned entries",
  },
];

const LANES = [
  { key: "tradetm", label: "TradeTM-native" },
  { key: "arora", label: "Arora / Strong Start" },
  { key: "stocksgeeks", label: "StocksGeeks specialist" },
];

// preset key -> { stage, lane, glyph }
const PLACEMENT = {
  arora_baseline: { stage: "momentum", lane: "arora", glyph: "breakout" },
  persistent_momentum: { stage: "momentum", lane: "tradetm", glyph: "staircase" },
  d2_episodic: { stage: "momentum", lane: "tradetm", glyph: "burst2" },
  todays_movers: { stage: "momentum", lane: "tradetm", glyph: "burst1" },
  lf_jump: { stage: "momentum", lane: "arora", glyph: "spike" },
  long_tail: { stage: "momentum", lane: "stocksgeeks", glyph: "tailcandle" },
  weekly_base_breakout: { stage: "momentum", lane: "tradetm", glyph: "breakout" },

  vcp_tightness: { stage: "basepattern", lane: "arora", glyph: "coil" },
  pullback_to_rising_ma: { stage: "basepattern", lane: "arora", glyph: "pullback" },
  pullback_to_50ma: { stage: "basepattern", lane: "arora", glyph: "pullback" },
  reversal_busted: { stage: "basepattern", lane: "arora", glyph: "vreversal" },
  aoi_down_base: { stage: "basepattern", lane: "stocksgeeks", glyph: "downbase" },

  ep_ipo: { stage: "ipobase", lane: "tradetm", glyph: "gapbase" },
  recent_listing: { stage: "ipobase", lane: "stocksgeeks", glyph: "ipocoil" },
  ipo_inside_bar: { stage: "ipobase", lane: "stocksgeeks", glyph: "insidebar" },
};

const CHARTSMAZE_KEYS = ["chhirag", "himanshu", "hiren", "nitin", "shashank"];

const RESULT_PAGE_SIZE = 30;

function statusLabel(status) {
  if (status === "DATA_READY") return "DATA-RDY";
  return status || "-";
}

function statusTone(status) {
  if (status === "LIVE") return "green";
  if (status === "DATA_READY") return "amber";
  return "neutral";
}

function fmtNum(value, digits = 1) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "-";
  return Number(value).toFixed(digits);
}

function fmtInt(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "-";
  return Math.round(Number(value)).toLocaleString("en-IN");
}

function rowMetric(row, scannerKey, field) {
  if (field === "move") return row.pct_chg ?? row.pct_change_1d;
  if (field === "upLow") return row.pct_up_65d_low ?? row.pct_up_from_65d_low;
  if (field === "dots") return row.purple_dot_count ?? row.purple_dot_count_60d;
  if (field === "rs") return row.rs ?? row.rs_rating;
  if (field === "scout") {
    if (row.scout_note) return row.scout_note;
    if (scannerKey === "todays_movers") return "Day-1 burst; check weekly base before shortlist.";
    return "Scanner hit; verify weekly trend and volume before acting.";
  }
  return row[field];
}

function normalizeRows(rows) {
  return (rows || []).map((row) => ({
    ...row,
    symbol: String(row.symbol || "").toUpperCase(),
  })).filter((row) => row.symbol);
}

// ------------------------------------------------------------------
// setup-specific miniature visual -- schematic motif per archetype, plain
// SVG, no chart lib, no synthetic price data (this is an iconographic
// pattern-shape reminder, not a rendering of any symbol's real price).
// ------------------------------------------------------------------

const GLYPH_PATHS = {
  breakout: "M2,22 L14,18 L24,20 L34,10 L44,12 L54,3",
  staircase: "M2,24 L12,24 L12,17 L24,17 L24,11 L36,11 L36,6 L54,6",
  burst2: "M2,22 L16,20 L22,21 L30,6 L38,9 L54,4",
  burst1: "M2,23 L20,22 L30,21 L38,6 L54,5",
  spike: "M4,24 L4,20 M14,24 L14,16 M24,24 L24,4 M34,24 L34,18 M44,24 L44,21 M54,24 L54,22",
  tailcandle: "M28,4 L28,10 M22,10 L34,10 L34,16 L22,16 Z M28,16 L28,25",
  coil: "M2,20 L10,10 L18,17 L26,11 L34,15 L42,12 L54,13",
  pullback: "M2,6 L14,10 L20,18 L28,12 L38,14 L54,4",
  vreversal: "M2,6 L18,22 L36,7 L54,5",
  downbase: "M2,10 L16,20 L34,20 L54,10",
  gapbase: "M2,20 L20,20 L26,20 L26,4 L54,4",
  ipocoil: "M2,18 L14,18 L20,14 L26,17 L32,15 L54,15",
  insidebar: "M6,4 L6,22 M4,10 L4,17 M50,10 L50,17 M48,4 L48,22",
};

function SetupGlyph({ type, label }) {
  const d = GLYPH_PATHS[type] || GLYPH_PATHS.breakout;
  return (
    <svg
      className="scn-glyph"
      viewBox="0 0 56 28"
      role="img"
      aria-label={`${label} pattern schematic`}
      title={`${label} — pattern schematic (not real price data)`}
    >
      <path d={d} fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

// ------------------------------------------------------------------
// chart-led result list
// ------------------------------------------------------------------

function ChartThumb({ date, symbol }) {
  return <PriceSparkThumb className="scn-thumb scn-thumb-spark" date={date} symbol={symbol} />;
}

function ResultRow({ row, date, scannerKey, onPushDebate, onOpenChart, onAddShortlist, onAddSS, pendingPush }) {
  const isPending = pendingPush?.has(row.symbol);
  const moveVal = rowMetric(row, scannerKey, "move");
  const adrVal = row.adr20;
  const dotsVal = rowMetric(row, scannerKey, "dots");
  const rsVal = rowMetric(row, scannerKey, "rs");
  const upLowVal = rowMetric(row, scannerKey, "upLow");
  const scoutVal = rowMetric(row, scannerKey, "scout");
  return (
    <li className={`scn-result-row${row.classification === "WATCH" ? " scn-result-row-watch" : ""}`}>
      <button type="button" className="scn-result-thumb-btn" onClick={() => onOpenChart(row.symbol)} title={`Open ${row.symbol} chart`}>
        <ChartThumb date={date} symbol={row.symbol} />
      </button>
      <div className="scn-result-main">
        <div className="scn-result-head">
          <span className="scn-result-symbol">{row.symbol}</span>
          {row.classification === "WATCH" && <span className="scn-chip scn-chip-anticipation">WATCH · trigger armed</span>}
          <span className="mono-num scn-result-move" style={colorScale(moveVal, 8)}>{fmtNum(moveVal)}%</span>
          {row.in_watchlist && <span className="scn-chip scn-chip-watch">on shortlist</span>}
          {row.in_debate && <span className="scn-chip scn-chip-debate">in debate</span>}
        </div>
        <p className="scn-result-scout">{scoutVal}</p>
        <details className="scn-result-metrics">
          <summary>expert metrics</summary>
          <div className="scn-metrics-grid">
            <span><b>ADR</b> {fmtNum(adrVal)}%</span>
            <span><b>RS</b> {fmtInt(rsVal)}</span>
            <span><b>%off low</b> {fmtNum(upLowVal)}%</span>
            <span><b>dots</b> {dotsVal === null || dotsVal === undefined ? "-" : Math.round(Number(dotsVal))}</span>
            <span><b>volume</b> {fmtInt(row.volume)}</span>
            <span><b>delivery%</b> {fmtNum(row.delivery_pct)}%</span>
          </div>
        </details>
      </div>
      <div className="scn-result-actions">
        <button type="button" onClick={() => onAddShortlist(row.symbol)} aria-label={`shortlist ${row.symbol}`} title="Add to shortlist">
          &#9733;
        </button>
        {onAddSS && (
          <button
            type="button"
            onClick={() => onAddSS(row.symbol)}
            aria-label={`add ${row.symbol} to Strong Start`}
            title="add to Strong Start list"
            className="ss-plus-btn"
          >
            &#9889; SS+
          </button>
        )}
        <button
          type="button"
          onClick={() => onPushDebate(row.symbol)}
          aria-label={`push ${row.symbol} to debate`}
          title={isPending ? "Push pending..." : "Push to DEBATE"}
          disabled={isPending}
        >
          {isPending ? "…" : "→"}
        </button>
        <button type="button" onClick={() => onOpenChart(row.symbol)} aria-label={`open ${row.symbol} chart`} title="Open chart">
          &#9636;
        </button>
      </div>
    </li>
  );
}

function ResultList({ rows, date, title, scannerKey, onPushDebate, onOpenChart, onAddShortlist, onAddSS, toast, pendingPush, isLoading }) {
  const [expanded, setExpanded] = useState(false);
  const normalized = normalizeRows(rows);
  if (isLoading) {
    return (
      <Panel title={title} cite="Loading..." className="scn-results-panel">
        <div className="scn-results-loading">
          <span className="scn-preset-hits-spinner">↻</span> Running screen query...
        </div>
      </Panel>
    );
  }
  if (!normalized.length) {
    return (
      <Panel title={title} cite={`${date || ""}`} className="scn-results-panel">
        <p className="scn-empty-line">No hits for this screen/date.</p>
      </Panel>
    );
  }
  const shown = expanded ? normalized : normalized.slice(0, RESULT_PAGE_SIZE);
  return (
    <Panel title={title} cite={`${normalized.length} matches · ${date || ""}`} className="scn-results-panel">
      {toast && <p className={`scanner-toast ${toast.kind}`}>{toast.text}</p>}
      <ul className="scn-result-list">
        {shown.map((row) => (
          <ResultRow
            key={row.symbol}
            row={row}
            date={date}
            scannerKey={scannerKey}
            onPushDebate={onPushDebate}
            onOpenChart={onOpenChart}
            onAddShortlist={onAddShortlist}
            onAddSS={onAddSS}
            pendingPush={pendingPush}
          />
        ))}
      </ul>
      {normalized.length > RESULT_PAGE_SIZE && !expanded && (
        <button type="button" className="scn-show-more" onClick={() => setExpanded(true)}>
          show all {normalized.length} matches
        </button>
      )}
    </Panel>
  );
}

function ActivitySparkline({ values, symbol }) {
  const clean = (values || []).map(Number).filter(Number.isFinite);
  if (!clean.length) return <span className="scn-activity-no-trend">no trail</span>;
  const max = Math.max(8, ...clean);
  return (
    <svg className="scn-activity-spark" viewBox="0 0 96 28" role="img" aria-label={`${symbol} ten-session activity trail: ${clean.join(", ")}`}>
      <line x1="0" y1={28 - (3.5 / max) * 26} x2="96" y2={28 - (3.5 / max) * 26} className="scn-activity-threshold" />
      {clean.map((value, index) => {
        const height = Math.max(2, (value / max) * 26);
        return <rect key={`${index}:${value}`} x={index * (94 / clean.length) + 1} y={28 - height} width={Math.max(3, 88 / clean.length)} height={height} rx="1" />;
      })}
    </svg>
  );
}

function ActivityPane({ payload, loading, error, onOpenChart, onAddShortlist, onPushDebate, pendingPush }) {
  const [quickFilter, setQuickFilter] = useState("hot");
  const [sortKey, setSortKey] = useState("score");
  const [query, setQuery] = useState("");
  const rows = useMemo(() => {
    const normalizedQuery = query.trim().toUpperCase();
    return [...(payload?.rows || [])]
      .filter((row) => {
        if (normalizedQuery && !row.symbol.includes(normalizedQuery)) return false;
        if (quickFilter === "hot") return Number(row.score) >= 3.5;
        if (quickFilter === "multi") return Number(row.persistence_sessions) >= 2;
        if (quickFilter === "surge") return Number(row.score_change) >= 2;
        if (quickFilter === "extreme") return Number(row.score) >= 8;
        return true;
      })
      .sort((a, b) => Number(b[sortKey] ?? -Infinity) - Number(a[sortKey] ?? -Infinity));
  }, [payload, query, quickFilter, sortKey]);
  const summary = payload?.summary || {};

  if (loading) return <Panel title="Loading unusual activity" cite="official NSE bhavcopy"><div className="scn-results-loading"><span className="scn-preset-hits-spinner">↻</span> Building the direction-neutral activity table…</div></Panel>;
  if (error) return <Panel title="Unusual activity unavailable" cite="retry after the nightly update"><p className="scn-empty-line">{error}</p></Panel>;
  if (!payload?.rows?.length) return <Panel title="Unusual activity warming" cite="20 valid sessions required"><p className="scn-stage-read">No values are invented while average trade quantity and delivery baselines warm up.</p></Panel>;

  const filters = [
    ["all", "All top rows"], ["hot", "3.5+"], ["multi", "Multi-day"], ["surge", "Surge"], ["extreme", "8+ extreme"],
  ];
  const sortButton = (key, label) => (
    <button type="button" className={sortKey === key ? "active" : ""} onClick={() => setSortKey(key)} aria-pressed={sortKey === key}>{label}</button>
  );

  return (
    <section className="scn-activity-pane">
      <div className="scn-activity-summary" aria-label="Unusual activity summary">
        <span><b>{fmtInt(summary.universe)}</b><small>covered</small></span>
        <span><b>{fmtInt(rows.length)}</b><small>shown</small></span>
        <span><b>{payload.as_of || "-"}</b><small>selected date</small></span>
        <span><b>{fmtInt(summary.abnormal)}</b><small>score 3.5+</small></span>
        <span><b>{fmtInt(summary.persistent)}</b><small>multi-day</small></span>
        <span><b>{fmtInt(summary.extreme)}</b><small>score 8+</small></span>
      </div>
      <p className="scn-stage-read"><b>What this means:</b> unusually large average trade quantity plus delivery participation. It detects abnormal participation, not buying direction or participant identity. Open the chart to decide whether price is accepting, absorbing, exhausting or distributing.</p>
      <Panel title="EOD unusual-activity analogue" cite={`${payload.as_of || "-"} · shadow evidence`} className="scn-activity-panel">
        <div className="scn-activity-tools">
          <div className="scn-activity-filters" role="group" aria-label="activity quick filters">
            {filters.map(([key, label]) => <button key={key} type="button" className={quickFilter === key ? "active" : ""} onClick={() => setQuickFilter(key)} aria-pressed={quickFilter === key}>{label}</button>)}
          </div>
          <label className="scn-activity-search"><span>Symbol</span><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search top 100" /></label>
        </div>
        <div className="scn-activity-table-wrap">
          <div className="scn-activity-table" role="table" aria-label="direction-neutral unusual activity rankings">
            <div className="scn-activity-table-head" role="row">
              <span>Symbol</span><span>{sortButton("score", "Score")}</span><span>{sortButton("score_change", "Day change")}</span><span>{sortButton("score_avg_4", "4-day avg")}</span><span>{sortButton("score_avg_10", "10-day avg")}</span><span>Streak</span><span>10-day trail</span><span>Evidence</span><span>Actions</span>
            </div>
            {rows.map((row) => {
              const pending = pendingPush?.has(row.symbol);
              return <div className="scn-activity-table-row" role="row" key={row.symbol}>
                <button type="button" className="scn-activity-symbol" onClick={() => onOpenChart(row.symbol)}>{row.symbol}</button>
                <span className={`mono-num scn-activity-score state-${row.state}`}>{fmtNum(row.score, 2)}</span>
                <span className="mono-num">{row.score_change === null ? "-" : `${Number(row.score_change) >= 0 ? "+" : ""}${fmtNum(row.score_change, 2)}`}</span>
                <span className="mono-num">{fmtNum(row.score_avg_4, 2)}</span>
                <span className="mono-num">{fmtNum(row.score_avg_10, 2)}</span>
                <span className="mono-num">{row.persistence_sessions ? `${row.persistence_sessions}d` : "-"}</span>
                <ActivitySparkline values={row.trail} symbol={row.symbol} />
                <span className="scn-activity-evidence"><b>{fmtNum(row.avg_trade_qty_ratio20, 2)}x</b> qty/trade · <b>{fmtNum(row.delivery_ratio19, 2)}x</b> delivery<span className="scn-activity-state">{String(row.state || "baseline").replaceAll("_", " ")}</span></span>
                <span className="scn-activity-actions"><button type="button" onClick={() => onAddShortlist(row.symbol)}>Watch</button><button type="button" disabled={pending} onClick={() => onPushDebate(row.symbol)}>{pending ? "Sending…" : "Debate"}</button><button type="button" onClick={() => onOpenChart(row.symbol)}>Chart</button></span>
              </div>;
            })}
          </div>
        </div>
        {!rows.length && <p className="scn-empty-line">No rows match this filter inside the top 100 activity readings.</p>}
        <p className="scn-activity-footnote">Formula: {payload.formula_version || "version unavailable"} · official aggregate bhavcopy · shadow only · direction unresolved.</p>
      </Panel>
    </section>
  );
}

// ------------------------------------------------------------------
// preset card (within a lane)
// ------------------------------------------------------------------

function PresetRow({ preset, active, loading, onOpen }) {
  const build = preset.status === "BUILD";
  return (
    <button
      type="button"
      className={`scn-preset-row${active ? " active" : ""}${build ? " build" : ""}`}
      onClick={() => !build && onOpen(preset)}
      disabled={build || loading}
      title={build ? "coming" : `open ${preset.label}`}
    >
      <SetupGlyph type={(PLACEMENT[preset.key] || {}).glyph || "breakout"} label={preset.label} />
      <span className="scn-preset-body">
        <span className="scn-preset-top">
          <span className="scn-preset-title">{preset.label}</span>
          <StatusChip value={statusLabel(preset.status)} tone={statusTone(preset.status)} dot={false} />
        </span>
        <span className="scn-preset-recipe">{preset.recipe_line}</span>
        <span className="scn-preset-foot mono-num">
          <span title={preset.cite}>{preset.cite}</span>
          <span className="scn-preset-hits">
            {build ? (
              "coming"
            ) : preset.hitsLoading ? (
              <span className="scn-preset-hits-spinner-wrapper">
                hits: <span className="scn-preset-hits-spinner">↻</span>
              </span>
            ) : (
              `hits: ${preset.hits === null || preset.hits === undefined ? "-" : fmtInt(preset.hits)}`
            )}
          </span>
        </span>
      </span>
    </button>
  );
}

function LaneColumn({ laneKey, laneLabel, presets, selectedKey, loadingKey, onOpen }) {
  return (
    <div className="scn-lane-col">
      <div className="scn-lane-hd">
        <span className="scn-lane-name">{laneLabel}</span>
        <span className="mono-num scn-lane-n">{presets.length || "—"}</span>
      </div>
      {presets.length === 0 ? (
        <p className="scn-empty-line scn-lane-empty">Not available yet. This lane is planned, not a zero-result scan.</p>
      ) : (
        <div className="scn-preset-stack">
          {presets.map((preset) => (
            <PresetRow
              key={preset.key}
              preset={preset}
              active={selectedKey === preset.key}
              loading={loadingKey === preset.key}
              onOpen={onOpen}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function StageBlock({ stage, presetsByLane, selectedKey, loadingKey, onOpen }) {
  const presetCount = LANES.reduce((sum, lane) => sum + (presetsByLane[lane.key] || []).length, 0);
  const totalHits = LANES.reduce((sum, lane) => {
    const list = presetsByLane[lane.key] || [];
    return sum + list.reduce((s, p) => s + (typeof p.hits === "number" ? p.hits : 0), 0);
  }, 0);
  return (
    <section className="scn-stage-block">
      <SectionLabel count={presetCount ? `${fmtInt(totalHits)} hits tonight` : "not wired yet"}>{stage.label}</SectionLabel>
      <p className="scn-stage-sub">{stage.sub}</p>
      <p className="scn-stage-read">
        {presetCount
          ? "Open a named scan to see its real stocks. Counts come from the selected trading date."
          : "No source-attributed scanner is implemented in this stage yet, so the desk will not pretend that an empty lane means zero opportunity."}
      </p>
      <div className="scn-lanes-grid">
        {LANES.map((lane) => (
          <LaneColumn
            key={lane.key}
            laneKey={lane.key}
            laneLabel={lane.label}
            presets={presetsByLane[lane.key] || []}
            selectedKey={selectedKey}
            loadingKey={loadingKey}
            onOpen={onOpen}
          />
        ))}
      </div>
    </section>
  );
}

function CommunityTemplates({ presets, selectedKey, loadingKey, onOpen }) {
  if (!presets.length) return null;
  return (
    <section className="scn-stage-block">
      <SectionLabel count={`${presets.length} templates`}>ChartsMaze Community Templates</SectionLabel>
      <p className="scn-stage-sub">
        Trader-authored screener templates ingested from ChartsMaze — not attributed to the TradeTM/Arora/StocksGeeks
        mechanism taxonomy above; kept as a flat reference set.
      </p>
      <div className="scn-cm-grid">
        {presets.map((preset) => (
          <LaneCard
            key={preset.key}
            family={undefined}
            name={preset.label}
            count={preset.hits === null || preset.hits === undefined ? "-" : fmtInt(preset.hits)}
            sub={preset.recipe_line}
            summary={
              <button type="button" className="scn-cm-open" onClick={() => onOpen(preset)} disabled={loadingKey === preset.key}>
                {selectedKey === preset.key ? "open" : "open ▾"}
              </button>
            }
          />
        ))}
      </div>
    </section>
  );
}

function PractitionerPane({ date, presets, selected, rows, loadingKey, onOpen, onPushDebate, onOpenChart, onAddShortlist, onAddSS, toast, pendingPush, resultsRef }) {
  const { staged, community } = useMemo(() => {
    const byStage = {};
    STAGES.forEach((s) => {
      byStage[s.key] = { tradetm: [], arora: [], stocksgeeks: [] };
    });
    const cm = [];
    (presets || []).forEach((preset) => {
      if (CHARTSMAZE_KEYS.includes(preset.key)) {
        cm.push(preset);
        return;
      }
      const place = PLACEMENT[preset.key];
      if (!place) {
        // unmapped preset: surface honestly rather than silently drop it
        cm.push(preset);
        return;
      }
      byStage[place.stage][place.lane].push(preset);
    });
    return { staged: byStage, community: cm };
  }, [presets]);

  return (
    <>
      {STAGES.map((stage) => (
        <StageBlock
          key={stage.key}
          stage={stage}
          presetsByLane={staged[stage.key]}
          selectedKey={selected?.key}
          loadingKey={loadingKey}
          onOpen={onOpen}
        />
      ))}
      <CommunityTemplates presets={community} selectedKey={selected?.key} loadingKey={loadingKey} onOpen={onOpen} />
      {selected && (
        <div ref={resultsRef}>
          <ResultList
            date={date}
            title={`${selected.label} — result rows`}
            rows={rows}
            scannerKey={selected.key}
            onPushDebate={onPushDebate}
            onAddShortlist={onAddShortlist}
            onAddSS={onAddSS}
            onOpenChart={onOpenChart}
            toast={toast}
            pendingPush={pendingPush}
            isLoading={loadingKey === selected.key}
          />
        </div>
      )}
    </>
  );
}

// ------------------------------------------------------------------
// CUSTOM BUILDER (unchanged behaviour, v5 restyle)
// ------------------------------------------------------------------

const FIELD_OPTIONS = [
  { field: "pct_change_1d", label: "%change", suffix: "%" },
  { field: "volume", label: "volume", suffix: "" },
  { field: "adr20", label: "ADR", suffix: "%" },
  { field: "rs", label: "RS rating", suffix: "" },
  { field: "pct_up_from_65d_low", label: "%off low", suffix: "%" },
  { field: "pct_off_52w_high", label: "%off 52w high", suffix: "%" },
  { field: "purple_dot_count_60d", label: "purple dots", suffix: "" },
  { field: "delivery_pct", label: "delivery %", suffix: "%" },
  { field: "close", label: "close", suffix: "" },
  { field: "above_ema10", label: ">10EMA", suffix: "0/1" },
  { field: "above_ema21", label: ">21EMA", suffix: "0/1" },
  { field: "above_ema50", label: ">50EMA", suffix: "0/1" },
];

const OP_OPTIONS = [
  { value: "gte", label: ">=" },
  { value: "gt", label: ">" },
  { value: "lte", label: "<=" },
  { value: "lt", label: "<" },
];

const DEFAULT_CONDITIONS = [
  { field: "pct_change_1d", op: "gte", value: 5 },
  { field: "volume", op: "gte", value: 1000000 },
  { field: "adr20", op: "gte", value: 4 },
];

function ConditionRow({ row, idx, onChange, onRemove, removable }) {
  const fieldMeta = FIELD_OPTIONS.find((f) => f.field === row.field) || FIELD_OPTIONS[0];
  return (
    <div className="scn-condition-row">
      <select value={row.field} onChange={(e) => onChange(idx, { ...row, field: e.target.value })}>
        {FIELD_OPTIONS.map((field) => (
          <option key={field.field} value={field.field}>{field.label}</option>
        ))}
      </select>
      <select value={row.op} onChange={(e) => onChange(idx, { ...row, op: e.target.value })}>
        {OP_OPTIONS.map((op) => (
          <option key={op.value} value={op.value}>{op.label}</option>
        ))}
      </select>
      <input
        value={row.value}
        onChange={(e) => onChange(idx, { ...row, value: e.target.value })}
        inputMode="decimal"
        aria-label={`${fieldMeta.label} value`}
      />
      <span className="mono-num scn-condition-suffix">{fieldMeta.suffix}</span>
      <button type="button" onClick={() => onRemove(idx)} disabled={!removable} aria-label="remove condition">
        x
      </button>
    </div>
  );
}

function cleanConditions(conditions) {
  return conditions.map((row) => ({
    field: row.field,
    op: row.op,
    value: Number(row.value),
  })).filter((row) => row.field && row.op && Number.isFinite(row.value));
}

function BuilderPane({ date, onPushDebate, onOpenChart, onAddShortlist, onAddSS, toast, pendingPush }) {
  const [conditions, setConditions] = useState(DEFAULT_CONDITIONS);
  const [rows, setRows] = useState([]);
  const [matches, setMatches] = useState(null);
  const [running, setRunning] = useState(false);
  const [screenName, setScreenName] = useState("my movers");
  const [screens, setScreens] = useState([]);
  const [localToast, setLocalToast] = useState(null);

  const loadScreens = useCallback(() => {
    fetchUserScreens()
      .then((body) => setScreens(body.screens || []))
      .catch((err) => setLocalToast({ kind: "err", text: `Saved screens failed: ${String(err.message || err)}` }));
  }, []);

  useEffect(() => {
    loadScreens();
  }, [loadScreens]);

  const runConditions = useCallback((nextConditions = conditions) => {
    const payload = cleanConditions(nextConditions);
    setRunning(true);
    setLocalToast(null);
    runDeskScreener(payload, date)
      .then((body) => {
        setRows(body.rows || []);
        setMatches(body.matched ?? (body.rows || []).length);
      })
      .catch((err) => setLocalToast({ kind: "err", text: `Run failed: ${String(err.message || err)}` }))
      .finally(() => setRunning(false));
  }, [conditions, date]);

  const saveScreen = useCallback(() => {
    const payload = cleanConditions(conditions);
    saveUserScreen(screenName, payload)
      .then(() => {
        setLocalToast({ kind: "ok", text: `Saved ${screenName}` });
        loadScreens();
      })
      .catch((err) => setLocalToast({ kind: "err", text: `Save failed: ${String(err.message || err)}` }));
  }, [conditions, loadScreens, screenName]);

  const runSaved = useCallback((screen) => {
    setConditions(screen.conditions || []);
    setRunning(true);
    setLocalToast(null);
    runScannerPreset(`user:${screen.name}`, date)
      .then((body) => {
        setRows(body.hits || []);
        setMatches((body.hits || []).length);
      })
      .catch((err) => setLocalToast({ kind: "err", text: `Saved run failed: ${String(err.message || err)}` }))
      .finally(() => setRunning(false));
  }, [date]);

  const removeSaved = useCallback((name) => {
    deleteUserScreen(name)
      .then(loadScreens)
      .catch((err) => setLocalToast({ kind: "err", text: `Delete failed: ${String(err.message || err)}` }));
  }, [loadScreens]);

  return (
    <>
      <Panel title="Build a screen" cite={`matches: ${matches ?? "-"}`} className="scn-builder-panel">
        <p className="scn-builder-kicker">WHEN a stock has…</p>
        <div className="scn-condition-stack">
          {conditions.map((row, idx) => (
            <ConditionRow
              key={`${idx}:${row.field}`}
              row={row}
              idx={idx}
              removable={conditions.length > 1}
              onChange={(i, next) => setConditions((cur) => cur.map((item, j) => (i === j ? next : item)))}
              onRemove={(i) => setConditions((cur) => cur.filter((_, j) => i !== j))}
            />
          ))}
        </div>
        <button
          type="button"
          className="scn-add-condition"
          onClick={() => setConditions((cur) => [...cur, { field: "delivery_pct", op: "gte", value: 35 }])}
        >
          + add condition
        </button>
        <p className="scn-field-list">
          metrics: {FIELD_OPTIONS.map((field) => field.label).join(" · ")}
        </p>
        <div className="scn-builder-actions">
          <button type="button" onClick={() => runConditions()} disabled={running}>Run screen</button>
          <input value={screenName} onChange={(e) => setScreenName(e.target.value)} aria-label="screen name" />
          <button type="button" onClick={saveScreen}>Save as…</button>
        </div>
        {localToast && <p className={`scanner-toast ${localToast.kind}`}>{localToast.text}</p>}
      </Panel>

      <Panel title="Saved screens" cite={`${screens.length} saved`} className="scn-saved-panel">
        <div className="scn-saved-list">
          {screens.length ? screens.map((screen) => (
            <span className="scn-saved-chip" key={screen.name}>
              <button type="button" onClick={() => runSaved(screen)}>v {screen.name}</button>
              <button type="button" onClick={() => removeSaved(screen.name)} aria-label={`delete ${screen.name}`}>x</button>
            </span>
          )) : <span className="scn-empty-line">No saved screens yet.</span>}
        </div>
      </Panel>

      {(rows.length > 0 || matches !== null) && (
        <ResultList
          date={date}
          title="Builder result rows"
          rows={rows}
          scannerKey="builder"
          onPushDebate={onPushDebate}
          onAddShortlist={onAddShortlist}
          onAddSS={onAddSS}
          onOpenChart={onOpenChart}
          toast={toast}
          pendingPush={pendingPush}
          isLoading={running}
        />
      )}
    </>
  );
}

// Module-level caches for scanner presets and hit counts
const presetsCache = new Map();
const runningPresetsFetches = new Map();

// ------------------------------------------------------------------
// EARNINGS SEASON panel (EARNINGS_SEASON_HANDHOLD step 3 / EP-PREP): who
// reports next, with cheap pre-context and a prep_class chip, plus the
// 3-step plain-English hand-hold for a beginner. Backed by
// GET /api/earnings/upcoming (see api/app.py::earnings_upcoming /
// _ep_prep_class for the prep_class thresholds).
// ------------------------------------------------------------------

const PREP_CLASS_TONE = { A_WATCH: "green", B_CONTEXT: "amber", C_IGNORE: "neutral" };
const PREP_CLASS_LABEL = { A_WATCH: "A-WATCH", B_CONTEXT: "B-CONTEXT", C_IGNORE: "C-IGNORE" };
const PREP_CLASS_RANK = { A_WATCH: 0, B_CONTEXT: 1, C_IGNORE: 2 };

function fmtDrift(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "-";
  const n = Number(value);
  return `${n > 0 ? "+" : ""}${n.toFixed(1)}%`;
}

function fmtDayLabel(dateStr) {
  const d = new Date(`${dateStr}T00:00:00`);
  if (Number.isNaN(d.getTime())) return dateStr;
  const wd = d.toLocaleDateString("en-IN", { weekday: "short" });
  const md = d.toLocaleDateString("en-IN", { day: "2-digit", month: "2-digit" });
  return `${wd} ${md}`;
}

function EarningsRow({ row, onOpenChart }) {
  return (
    <div className="esn-row" role="row">
      <button
        type="button"
        className="esn-symbol-chip"
        onClick={() => onOpenChart(row.symbol)}
        title={`Open ${row.symbol} chart`}
      >
        {row.symbol}
      </button>
      <StatusChip
        value={PREP_CLASS_LABEL[row.prep_class] || row.prep_class}
        tone={PREP_CLASS_TONE[row.prep_class] || "neutral"}
        title="Watch priority: A-list = in universe, RS>=70, liquid; B = tradeable but weaker/unknown; C = not tradeable"
      />
      <div className="esn-mini-cols">
        <span className="esn-mini-col" title="Relative Strength (nightly EP scan, falling back to ChartsMaze industry RS)">
          RS {fmtNum(row.rs, 0)}
        </span>
        <span className="esn-mini-col" title="20-day Average Daily Range, % of close">
          ADR {fmtNum(row.adr_pct, 1)}%
        </span>
        <span className="esn-mini-col" title="Distance below the 52-week high">
          {row.pct_off_52w_high == null ? "52wH -" : `52wH -${fmtNum(row.pct_off_52w_high, 1)}%`}
        </span>
        <span className="esn-mini-col" title="5-session price drift going into the print">
          {fmtDrift(row.pre_earnings_drift_5d_pct)} 5d
        </span>
      </div>
    </div>
  );
}

function EarningsSeasonPanel({ date, beginnerMode, onOpenChart }) {
  const [state, setState] = useState({ loading: true, error: null, data: null });

  useEffect(() => {
    let cancelled = false;
    setState({ loading: true, error: null, data: null });
    fetchEarningsUpcoming(date, 10)
      .then((body) => { if (!cancelled) setState({ loading: false, error: null, data: body }); })
      .catch((err) => { if (!cancelled) setState({ loading: false, error: String(err.message || err), data: null }); });
    return () => { cancelled = true; };
  }, [date]);

  const { loading, error, data } = state;

  if (loading) {
    return (
      <Panel title="EARNINGS SEASON" cite="BSE forthcoming-results calendar">
        <p className="scn-stage-read">Loading who reports next…</p>
      </Panel>
    );
  }
  if (error || !data || data.available === false) {
    return (
      <Panel title="EARNINGS SEASON" cite="BSE forthcoming-results calendar">
        <p className="scn-stage-read">
          {error ? `Earnings calendar failed: ${error}` : (data && data.reason) || "No forward earnings calendar available yet."}
        </p>
      </Panel>
    );
  }

  const rankedDays = (data.days || []).slice(0, 5).map((d) => ({
    ...d,
    symbols: [...d.symbols].sort((a, b) => (
      (PREP_CLASS_RANK[a.prep_class] ?? 3) - (PREP_CLASS_RANK[b.prep_class] ?? 3)
      || a.symbol.localeCompare(b.symbol)
    )),
  }));

  const beginnerDays = rankedDays
    .map((d) => ({ ...d, symbols: d.symbols.filter((s) => s.prep_class === "A_WATCH") }))
    .filter((d) => d.symbols.length > 0);
  // An empty beginner screen is worse than one extra non-A-list row: if
  // nothing clears the A-list bar anywhere in the window, fall back to the
  // full (unfiltered) list rather than showing nothing.
  const beginnerHasNothing = beginnerMode && beginnerDays.length === 0;
  const effectiveDays = beginnerMode && !beginnerHasNothing ? beginnerDays : rankedDays;

  const unmappedCount = (data.unmapped || []).length;

  return (
    <Panel title="EARNINGS SEASON" cite="BSE Corpforthresults — honest empty state when unavailable">
      <div className="esn-handhold">
        <div className="esn-step">
          <span className="esn-step-n">1</span>
          Tonight: skim the A-list charts below — who reports next with real relative strength and liquidity behind them.
        </div>
        <div className="esn-step">
          <span className="esn-step-n">2</span>
          Result day: do nothing at the open. No pre-result gambling — this tool only confirms an EP after the print (gap + volume + growth), never before.
        </div>
        <div className="esn-step">
          <span className="esn-step-n">3</span>
          Evening after: tonight's scan flags the real EPs. Strong ones surface in SCAN/DEBATE tomorrow evening — act only on gate-approved cards, not on the calendar alone.
        </div>
      </div>
      {beginnerHasNothing && (
        <p className="esn-note">No A-list names reporting in this window yet — showing the full list below.</p>
      )}
      {effectiveDays.length === 0 ? (
        <p className="scn-stage-read">No reporters in the next few sessions.</p>
      ) : (
        <div className="esn-days">
          {effectiveDays.map((d) => (
            <div className="esn-day" key={d.date}>
              <div className="esn-day-hd">{fmtDayLabel(d.date)}</div>
              <div className="esn-day-rows">
                {d.symbols.map((row) => (
                  <EarningsRow key={row.symbol} row={row} onOpenChart={onOpenChart} />
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
      {unmappedCount > 0 && (
        <p className="esn-unmapped">
          +{unmappedCount} smaller {unmappedCount === 1 ? "name" : "names"} unmapped in this window (BSE listing, not yet resolved to an NSE symbol)
        </p>
      )}
    </Panel>
  );
}

export default function ScannersTab({ date, beginnerMode = false }) {
  const [mode, setMode] = useState("practitioner");
  const [presets, setPresets] = useState([]);
  const [selectedPreset, setSelectedPreset] = useState(null);
  const [presetRows, setPresetRows] = useState([]);
  const [loadingKey, setLoadingKey] = useState(null);
  const [chartSymbol, setChartSymbol] = useState(null);
  const [toast, setToast] = useState(null);
  const [error, setError] = useState(null);
  const [presetsLoading, setPresetsLoading] = useState(true);
  const [activityState, setActivityState] = useState({ loading: false, error: null, data: null });

  const resultsRef = useRef(null);

  useEffect(() => {
    let cancelled = false;
    setError(null);
    setPresetsLoading(true);

    if (presetsCache.has(date)) {
      const cached = presetsCache.get(date);
      setPresets(cached);
      setPresetsLoading(false);
      return;
    }

    let presetsPromise;
    if (runningPresetsFetches.has(date)) {
      presetsPromise = runningPresetsFetches.get(date);
    } else {
      presetsPromise = fetchScannerPresets(date, true)
        .then((body) => {
          const list = body.presets || [];
          presetsCache.set(date, list);
          runningPresetsFetches.delete(date);
          return list;
        })
        .catch((err) => {
          runningPresetsFetches.delete(date);
          throw err;
        });
      runningPresetsFetches.set(date, presetsPromise);
    }

    presetsPromise
      .then((list) => {
        if (cancelled) return;
        setPresets(list);
        setPresetsLoading(false);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(String(err.message || err));
          setPresetsLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [date]);

  useEffect(() => {
    if (mode !== "activity") return undefined;
    let cancelled = false;
    setActivityState({ loading: true, error: null, data: null });
    fetchAlphaActivity(date, 100)
      .then((data) => { if (!cancelled) setActivityState({ loading: false, error: null, data }); })
      .catch((err) => { if (!cancelled) setActivityState({ loading: false, error: String(err.message || err), data: null }); });
    return () => { cancelled = true; };
  }, [date, mode]);

  const presetsWithHits = useMemo(() => {
    return presets.map((p) => {
      return {
        ...p,
        hitsLoading: false,
      };
    });
  }, [presets]);

  const openPreset = useCallback((preset) => {
    setSelectedPreset(preset);
    setPresetRows([]);
    setLoadingKey(preset.key);
    setToast(null);

    // Scroll to results panel smoothly
    setTimeout(() => {
      if (resultsRef.current) {
        resultsRef.current.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    }, 50);

    runScannerPreset(preset.key, date)
      .then((body) => setPresetRows(body.hits || []))
      .catch((err) => setToast({ kind: "err", text: `Open failed: ${String(err.message || err)}` }))
      .finally(() => setLoadingKey(null));
  }, [date]);

  const addShortlist = useCallback((symbol) => {
    setToast({ kind: "ok", text: `Adding ${symbol} to shortlist...` });
    addWatchlistSymbol(symbol, "added from scanners")
      .then(() => setToast({ kind: "ok", text: `${symbol} added to shortlist` }))
      .catch((err) => setToast({ kind: "err", text: `Shortlist add failed for ${symbol}: ${String(err.message || err)}` }));
  }, []);

  const addSS = useCallback((symbol) => {
    setToast({ kind: "ok", text: `Adding ${symbol} to Strong Start...` });
    addFocusSymbol(symbol, "screener", "added from scanners")
      .then(() => setToast({ kind: "ok", text: `${symbol} added to Strong Start` }))
      .catch((err) => setToast({ kind: "err", text: `Strong Start add failed for ${symbol}: ${String(err.message || err)}` }));
  }, []);

  const [pendingPush, setPendingPush] = useState(() => new Set());

  const pushDebate = useCallback((symbol) => {
    if (pendingPush.has(symbol)) return;
    setPendingPush((cur) => new Set(cur).add(symbol));
    setToast({ kind: "ok", text: `Pushing ${symbol} to debate...` });
    pushSymbolToDebate(symbol, date)
      .then((body) => {
        if (body.already_debated) {
          setToast({ kind: "ok", text: `${symbol} already debated for this date - showing existing card` });
        } else {
          setToast({ kind: "ok", text: `${symbol} pushed to debate (${body.status || "ok"})` });
        }
      })
      .catch((err) => {
        if (err.status === 409) {
          setToast({ kind: "err", text: `${symbol} push already running - please wait` });
        } else {
          setToast({ kind: "err", text: `Debate push failed for ${symbol}: ${String(err.message || err)}` });
        }
      })
      .finally(() => {
        setPendingPush((cur) => {
          const next = new Set(cur);
          next.delete(symbol);
          return next;
        });
      });
  }, [date, pendingPush]);

  return (
    <div className="scn-tab">
      <EarningsSeasonPanel date={date} beginnerMode={beginnerMode} onOpenChart={setChartSymbol} />
      <section className="scn-segmented">
        <button
          type="button"
          className={mode === "practitioner" ? "active" : ""}
          onClick={() => setMode("practitioner")}
        >
          PRACTITIONER SCANNERS
        </button>
        <button
          type="button"
          className={mode === "builder" ? "active" : ""}
          onClick={() => setMode("builder")}
        >
          CUSTOM BUILDER
        </button>
        <button
          type="button"
          className={mode === "activity" ? "active" : ""}
          onClick={() => setMode("activity")}
        >
          UNUSUAL ACTIVITY
        </button>
      </section>
      {error && <div className="stale-banner">Scanner presets failed: {error}</div>}
      {mode === "practitioner" && presetsLoading ? (
        <Panel title="Loading practitioner scanners" cite="real preset registry">
          <p className="scn-stage-read">Loading the source-attributed TradeTM, Manas Arora and StocksGeeks mechanisms for {date}. No zero counts are shown until the registry responds.</p>
        </Panel>
      ) : mode === "practitioner" ? (
        <PractitionerPane
          date={date}
          presets={presetsWithHits}
          selected={selectedPreset}
          rows={presetRows}
          loadingKey={loadingKey}
          onOpen={openPreset}
          onPushDebate={pushDebate}
          onAddShortlist={addShortlist}
          onAddSS={addSS}
          onOpenChart={setChartSymbol}
          toast={toast}
          pendingPush={pendingPush}
          resultsRef={resultsRef}
        />
      ) : mode === "builder" ? (
        <BuilderPane
          date={date}
          onPushDebate={pushDebate}
          onAddShortlist={addShortlist}
          onAddSS={addSS}
          onOpenChart={setChartSymbol}
          toast={toast}
          pendingPush={pendingPush}
        />
      ) : (
        <ActivityPane
          payload={activityState.data}
          loading={activityState.loading}
          error={activityState.error}
          onOpenChart={setChartSymbol}
          onAddShortlist={addShortlist}
          onPushDebate={pushDebate}
          pendingPush={pendingPush}
        />
      )}
      <ChartDrawer symbol={chartSymbol} date={date} defaultInterval="W" onClose={() => setChartSymbol(null)} />
    </div>
  );
}
