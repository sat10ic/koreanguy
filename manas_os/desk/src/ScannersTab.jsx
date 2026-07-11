import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  addWatchlistSymbol,
  deleteUserScreen,
  fetchScannerPresets,
  fetchUserScreens,
  pushSymbolToDebate,
  runDeskScreener,
  runScannerPreset,
  saveUserScreen,
} from "./api.js";
import ChartDrawer from "./ChartDrawer.jsx";
import { useDensity } from "./DensityContext.jsx";

const OWNER_GROUPS = [
  "Arora",
  "TradeTM",
  "StocksGeeks",
  "ChartsMaze templates",
  "House",
];

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
  { field: "rs", op: "gte", value: 80 },
];

function statusLabel(status) {
  if (status === "DATA_READY") return "DATA-RDY";
  return status || "-";
}

function ownerGroup(preset) {
  const owner = String(preset.owner || "");
  const key = String(preset.key || "");
  if (/ChartsMaze/i.test(owner)) return "ChartsMaze templates";
  if (/TradeTM/i.test(owner)) return "TradeTM";
  if (/StocksGeeks|Umang|IPO playbook/i.test(owner)) return "StocksGeeks";
  if (/builder preset|House/i.test(owner) || key === "todays_movers") return "House";
  return "Arora";
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

function ResultRows({ rows, title, scannerKey, onPushDebate, onOpenChart, onAddShortlist, toast }) {
  const { isExpert } = useDensity();
  const normalized = normalizeRows(rows);
  if (!normalized.length) {
    return (
      <section className="panel scanner-results-panel">
        <div className="scanner-results-head">
          <h3 className="panel-title small-caps">{title}</h3>
          <span className="mono scanner-match-count">0 matches</span>
        </div>
        <p className="empty-state-line">No hits for this screen/date.</p>
      </section>
    );
  }

  const cols = isExpert
    ? ["symbol", "move", "adr20", "dots", "rs", "upLow", "volume", "delivery_pct", "scout", "actions"]
    : ["symbol", "move", "adr20", "dots", "scout"];

  return (
    <section className="panel scanner-results-panel">
      <div className="scanner-results-head">
        <h3 className="panel-title small-caps">{title}</h3>
        <span className="mono scanner-match-count">{normalized.length} matches</span>
      </div>
      {toast && <p className={`scanner-toast ${toast.kind}`}>{toast.text}</p>}
      <div className="scanner-table-wrap">
        <table className="scanner-hit-table">
          <thead>
            <tr>
              {cols.map((col) => (
                <th key={col}>{col === "upLow" ? "%off low" : col === "dots" ? "dots" : col}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {normalized.map((row) => (
              <tr key={row.symbol}>
                {cols.includes("symbol") && <td className="scanner-symbol mono">{row.symbol}</td>}
                {cols.includes("move") && <td>{fmtNum(rowMetric(row, scannerKey, "move"))}%</td>}
                {cols.includes("adr20") && <td>{fmtNum(row.adr20)}%</td>}
                {cols.includes("dots") && <td>{fmtInt(rowMetric(row, scannerKey, "dots"))}</td>}
                {cols.includes("rs") && <td>{fmtInt(rowMetric(row, scannerKey, "rs"))}</td>}
                {cols.includes("upLow") && <td>{fmtNum(rowMetric(row, scannerKey, "upLow"))}%</td>}
                {cols.includes("volume") && <td>{fmtInt(row.volume)}</td>}
                {cols.includes("delivery_pct") && <td>{fmtNum(row.delivery_pct)}%</td>}
                {cols.includes("scout") && (
                  <td className="scanner-scout">
                    <span>{rowMetric(row, scannerKey, "scout")}</span>
                    {!isExpert && (
                      <span className="scanner-actions scanner-actions-inline">
                        <button onClick={() => onAddShortlist(row.symbol)} aria-label={`shortlist ${row.symbol}`}>
                          star
                        </button>
                        <button onClick={() => onPushDebate(row.symbol)} aria-label={`push ${row.symbol} to debate`}>
                          -&gt; debate
                        </button>
                        <button onClick={() => onOpenChart(row.symbol)} aria-label={`open ${row.symbol} chart`}>
                          chart
                        </button>
                      </span>
                    )}
                  </td>
                )}
                {cols.includes("actions") && (
                  <td className="scanner-actions">
                    <button onClick={() => onAddShortlist(row.symbol)} aria-label={`shortlist ${row.symbol}`}>
                      star
                    </button>
                    <button onClick={() => onPushDebate(row.symbol)} aria-label={`push ${row.symbol} to debate`}>
                      -&gt; debate
                    </button>
                    <button onClick={() => onOpenChart(row.symbol)} aria-label={`open ${row.symbol} chart`}>
                      chart
                    </button>
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function PresetCard({ preset, active, loading, onOpen }) {
  const build = preset.status === "BUILD";
  return (
    <button
      type="button"
      className={`scanner-preset-card${active ? " active" : ""}${build ? " build" : ""}`}
      onClick={() => !build && onOpen(preset)}
      disabled={build || loading}
      title={build ? "coming" : `open ${preset.label}`}
    >
      <span className={`scanner-status-chip status-${String(preset.status || "").toLowerCase()}`}>
        {statusLabel(preset.status)}
      </span>
      <span className="scanner-card-title">{preset.label}</span>
      <span className="scanner-card-owner">owner: {preset.owner}</span>
      <span className="scanner-card-recipe">recipe: {preset.recipe_line}</span>
      <span className="scanner-card-foot mono">
        hits: {preset.hits === null || preset.hits === undefined ? "-" : fmtInt(preset.hits)}
        <span>{build ? "coming" : active ? "open" : "open v"}</span>
      </span>
    </button>
  );
}

function PractitionerPane({ date, presets, selected, rows, loadingKey, onOpen, onPushDebate, onOpenChart, onAddShortlist, toast }) {
  const grouped = useMemo(() => {
    const out = new Map(OWNER_GROUPS.map((group) => [group, []]));
    (presets || []).forEach((preset) => {
      const group = ownerGroup(preset);
      out.get(group).push(preset);
    });
    return out;
  }, [presets]);

  return (
    <>
      <section className="scanner-section">
        {OWNER_GROUPS.map((group) => {
          const items = grouped.get(group) || [];
          if (!items.length) return null;
          return (
            <div className="scanner-owner-group" key={group}>
              <div className="scanner-owner-title mono">{group}</div>
              <div className="scanner-card-grid">
                {items.map((preset) => (
                  <PresetCard
                    key={preset.key}
                    preset={preset}
                    active={selected?.key === preset.key}
                    loading={loadingKey === preset.key}
                    onOpen={onOpen}
                  />
                ))}
              </div>
            </div>
          );
        })}
      </section>
      {selected && (
        <ResultRows
          title={`${selected.label} result rows - ${date || ""}`}
          rows={rows}
          scannerKey={selected.key}
          onPushDebate={onPushDebate}
          onAddShortlist={onAddShortlist}
          onOpenChart={onOpenChart}
          toast={toast}
        />
      )}
    </>
  );
}

function ConditionRow({ row, idx, onChange, onRemove, removable }) {
  const fieldMeta = FIELD_OPTIONS.find((f) => f.field === row.field) || FIELD_OPTIONS[0];
  return (
    <div className="scanner-condition-row">
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
      <span className="scanner-condition-suffix mono">{fieldMeta.suffix}</span>
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

function BuilderPane({ date, onPushDebate, onOpenChart, onAddShortlist, toast }) {
  const { isExpert } = useDensity();
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

  const visibleFields = isExpert ? FIELD_OPTIONS : FIELD_OPTIONS.slice(0, 8);

  return (
    <>
      <section className="panel scanner-builder-panel">
        <div className="scanner-results-head">
          <h3 className="panel-title small-caps">Build a screen</h3>
          <span className="mono scanner-match-count">matches: {matches ?? "-"}</span>
        </div>
        <p className="scanner-builder-kicker">WHEN a stock has...</p>
        <div className="scanner-condition-stack">
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
          className="scanner-add-condition"
          onClick={() => setConditions((cur) => [...cur, { field: "delivery_pct", op: "gte", value: 35 }])}
        >
          + add condition
        </button>
        <p className="scanner-field-list">
          metrics: {visibleFields.map((field) => field.label).join(" · ")}
        </p>
        <div className="scanner-builder-actions">
          <button type="button" onClick={() => runConditions()} disabled={running}>Run screen</button>
          <input value={screenName} onChange={(e) => setScreenName(e.target.value)} aria-label="screen name" />
          <button type="button" onClick={saveScreen}>Save as...</button>
        </div>
        {localToast && <p className={`scanner-toast ${localToast.kind}`}>{localToast.text}</p>}
      </section>

      <section className="panel scanner-saved-panel">
        <div className="scanner-results-head">
          <h3 className="panel-title small-caps">Saved screens</h3>
          <span className="mono scanner-match-count">{screens.length} saved</span>
        </div>
        <div className="scanner-saved-list">
          {screens.length ? screens.map((screen) => (
            <span className="scanner-saved-chip" key={screen.name}>
              <button type="button" onClick={() => runSaved(screen)}>v {screen.name}</button>
              <button type="button" onClick={() => removeSaved(screen.name)} aria-label={`delete ${screen.name}`}>x</button>
            </span>
          )) : <span className="empty-state-line">No saved screens yet.</span>}
        </div>
      </section>

      {(rows.length > 0 || matches !== null) && (
        <ResultRows
          title={`Builder result rows - ${date || ""}`}
          rows={rows}
          scannerKey="builder"
          onPushDebate={onPushDebate}
          onAddShortlist={onAddShortlist}
          onOpenChart={onOpenChart}
          toast={toast}
        />
      )}
    </>
  );
}

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

  const pushDebate = useCallback((symbol) => {
    setToast({ kind: "ok", text: `Pushing ${symbol} to debate...` });
    pushSymbolToDebate(symbol, date)
      .then((body) => setToast({ kind: "ok", text: `${symbol} pushed to debate (${body.status || "ok"})` }))
      .catch((err) => setToast({ kind: "err", text: `Debate push failed for ${symbol}: ${String(err.message || err)}` }));
  }, [date]);

  return (
    <div className="scanners-tab">
      <section className="scanner-segmented panel">
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
          onOpenChart={setChartSymbol}
          toast={toast}
        />
      ) : (
        <BuilderPane date={date} onPushDebate={pushDebate} onAddShortlist={addShortlist} onOpenChart={setChartSymbol} toast={toast} />
      )}
      <ChartDrawer symbol={chartSymbol} date={date} onClose={() => setChartSymbol(null)} />
    </div>
  );
}
