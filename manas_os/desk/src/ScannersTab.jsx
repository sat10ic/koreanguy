import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  addWatchlistSymbol,
  addFocusSymbol,
  deleteUserScreen,
  fetchScannerPresets,
  fetchUserScreens,
  pushSymbolToDebate,
  runDeskScreener,
  runScannerPreset,
  saveUserScreen,
  chartUrl,
} from "./api.js";
import ChartDrawer from "./ChartDrawer.jsx";
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
  const [failed, setFailed] = useState(false);
  if (failed) {
    return <div className="scn-thumb-missing mono-num">no chart</div>;
  }
  return (
    <img
      className="scn-thumb"
      src={chartUrl(date, symbol, "daily")}
      alt={`${symbol} daily chart`}
      loading="lazy"
      onError={() => setFailed(true)}
    />
  );
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
    <li className="scn-result-row">
      <button type="button" className="scn-result-thumb-btn" onClick={() => onOpenChart(row.symbol)} title={`Open ${row.symbol} chart`}>
        <ChartThumb date={date} symbol={row.symbol} />
      </button>
      <div className="scn-result-main">
        <div className="scn-result-head">
          <span className="scn-result-symbol">{row.symbol}</span>
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

function ResultList({ rows, date, title, scannerKey, onPushDebate, onOpenChart, onAddShortlist, onAddSS, toast, pendingPush }) {
  const [expanded, setExpanded] = useState(false);
  const normalized = normalizeRows(rows);
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
            {build ? "coming" : `hits: ${preset.hits === null || preset.hits === undefined ? "-" : fmtInt(preset.hits)}`}
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
        <span className="mono-num scn-lane-n">{presets.length}</span>
      </div>
      {presets.length === 0 ? (
        <p className="scn-empty-line scn-lane-empty">no live scanner in this lane yet.</p>
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
  const totalHits = LANES.reduce((sum, lane) => {
    const list = presetsByLane[lane.key] || [];
    return sum + list.reduce((s, p) => s + (typeof p.hits === "number" ? p.hits : 0), 0);
  }, 0);
  return (
    <section className="scn-stage-block">
      <SectionLabel count={`${fmtInt(totalHits)} hits tonight`}>{stage.label}</SectionLabel>
      <p className="scn-stage-sub">{stage.sub}</p>
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

function PractitionerPane({ date, presets, selected, rows, loadingKey, onOpen, onPushDebate, onOpenChart, onAddShortlist, onAddSS, toast, pendingPush }) {
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
        />
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
        />
      )}
    </>
  );
}

// ------------------------------------------------------------------
// main
// ------------------------------------------------------------------

export default function ScannersTab({ date }) {
  const [mode, setMode] = useState("practitioner");
  const [presets, setPresets] = useState([]);
  const [selectedPreset, setSelectedPreset] = useState(null);
  const [presetRows, setPresetRows] = useState([]);
  const [loadingKey, setLoadingKey] = useState(null);
  const [chartSymbol, setChartSymbol] = useState(null);
  const [toast, setToast] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    setError(null);
    fetchScannerPresets(date)
      .then((body) => {
        if (cancelled) return;
        setPresets(body.presets || []);
      })
      .catch((err) => {
        if (!cancelled) setError(String(err.message || err));
      });
    return () => {
      cancelled = true;
    };
  }, [date]);

  const openPreset = useCallback((preset) => {
    setSelectedPreset(preset);
    setLoadingKey(preset.key);
    setToast(null);
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
      </section>
      {error && <div className="stale-banner">Scanner presets failed: {error}</div>}
      {mode === "practitioner" ? (
        <PractitionerPane
          date={date}
          presets={presets}
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
        />
      ) : (
        <BuilderPane
          date={date}
          onPushDebate={pushDebate}
          onAddShortlist={addShortlist}
          onAddSS={addSS}
          onOpenChart={setChartSymbol}
          toast={toast}
          pendingPush={pendingPush}
        />
      )}
      <ChartDrawer symbol={chartSymbol} date={date} defaultInterval="W" onClose={() => setChartSymbol(null)} />
    </div>
  );
}
