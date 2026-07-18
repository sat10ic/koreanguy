import fs from 'node:fs';
import crypto from 'node:crypto';
import { DatabaseSync } from 'node:sqlite';

const ROOT = 'C:/Users/satta/Downloads/koreanguy';
const CSV_PATH = 'C:/Users/satta/Downloads/DEMO SHEET - MARCH APRIL - Sheet1.csv';
const TRANSCRIPT_PATH = 'C:/Users/satta/Downloads/NoteGPT_Transcript_How To Track Smart Money Footprint In Indian Stock Market  Proper Step By Step Video.txt';
const DB_PATH = `${ROOT}/manas_os/data/manas.db`;
const OUT_PATH = `${ROOT}/_smf_codex/results.json`;
const RESIDUAL_PATH = `${ROOT}/_smf_codex/best_model_residuals.csv`;

function sha256(path) {
  return crypto.createHash('sha256').update(fs.readFileSync(path)).digest('hex');
}

function parseCsv(text) {
  const rows = [];
  let row = [], field = '', quoted = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (quoted) {
      if (c === '"' && text[i + 1] === '"') { field += '"'; i++; }
      else if (c === '"') quoted = false;
      else field += c;
    } else if (c === '"') quoted = true;
    else if (c === ',') { row.push(field); field = ''; }
    else if (c === '\n') { row.push(field.replace(/\r$/, '')); rows.push(row); row = []; field = ''; }
    else field += c;
  }
  if (field.length || row.length) { row.push(field.replace(/\r$/, '')); rows.push(row); }
  return rows.filter((r) => r.some((v) => v !== ''));
}

function parseHeaderDate(value) {
  if (!/^\d{5,6}$/.test(value)) return null;
  const s = value.padStart(6, '0');
  return `20${s.slice(4, 6)}-${s.slice(2, 4)}-${s.slice(0, 2)}`;
}

const mean = (xs) => xs.reduce((a, b) => a + b, 0) / xs.length;
function median(xs) {
  const a = [...xs].sort((x, y) => x - y), n = a.length;
  return n % 2 ? a[(n - 1) / 2] : (a[n / 2 - 1] + a[n / 2]) / 2;
}
function quantile(xs, q) {
  const a = [...xs].sort((x, y) => x - y);
  if (!a.length) return NaN;
  const p = (a.length - 1) * q, lo = Math.floor(p), hi = Math.ceil(p);
  return a[lo] + (a[hi] - a[lo]) * (p - lo);
}
function pearson(a, b) {
  if (a.length < 3 || a.length !== b.length) return NaN;
  const ma = mean(a), mb = mean(b);
  let num = 0, da = 0, db = 0;
  for (let i = 0; i < a.length; i++) {
    const xa = a[i] - ma, xb = b[i] - mb;
    num += xa * xb; da += xa * xa; db += xb * xb;
  }
  return da > 0 && db > 0 ? num / Math.sqrt(da * db) : NaN;
}
function ranks(xs) {
  const order = xs.map((v, i) => ({ v, i })).sort((a, b) => a.v - b.v || a.i - b.i);
  const out = Array(xs.length);
  for (let i = 0; i < order.length;) {
    let j = i + 1;
    while (j < order.length && order[j].v === order[i].v) j++;
    const r = (i + j - 1) / 2 + 1;
    for (let k = i; k < j; k++) out[order[k].i] = r;
    i = j;
  }
  return out;
}
const spearman = (a, b) => pearson(ranks(a), ranks(b));

function solveLinear(A, b) {
  const n = b.length;
  const M = A.map((row, i) => [...row, b[i]]);
  for (let col = 0; col < n; col++) {
    let pivot = col;
    for (let r = col + 1; r < n; r++) if (Math.abs(M[r][col]) > Math.abs(M[pivot][col])) pivot = r;
    [M[col], M[pivot]] = [M[pivot], M[col]];
    const d = M[col][col];
    if (Math.abs(d) < 1e-12) throw new Error(`Singular system at column ${col}`);
    for (let c = col; c <= n; c++) M[col][c] /= d;
    for (let r = 0; r < n; r++) if (r !== col) {
      const f = M[r][col];
      if (f === 0) continue;
      for (let c = col; c <= n; c++) M[r][c] -= f * M[col][c];
    }
  }
  return M.map((row) => row[n]);
}

function fitRidge(rows, features, lambda = 1e-4) {
  const mus = features.map((f) => mean(rows.map((r) => r[f])));
  const sds = features.map((f, j) => {
    const v = mean(rows.map((r) => (r[f] - mus[j]) ** 2));
    return Math.sqrt(v) || 1;
  });
  const p = features.length + 1;
  const A = Array.from({ length: p }, () => Array(p).fill(0));
  const b = Array(p).fill(0);
  for (const row of rows) {
    const x = [1, ...features.map((f, j) => (row[f] - mus[j]) / sds[j])];
    for (let i = 0; i < p; i++) {
      b[i] += x[i] * row.score;
      for (let j = 0; j < p; j++) A[i][j] += x[i] * x[j];
    }
  }
  for (let j = 1; j < p; j++) A[j][j] += lambda * rows.length;
  return { features, mus, sds, beta: solveLinear(A, b), lambda };
}
function predict(model, row) {
  let y = model.beta[0];
  for (let j = 0; j < model.features.length; j++) y += model.beta[j + 1] * (row[model.features[j]] - model.mus[j]) / model.sds[j];
  return y;
}
function metrics(rows, predictions) {
  const actual = rows.map((r) => r.score);
  const byDate = new Map();
  rows.forEach((r, i) => {
    if (!byDate.has(r.date)) byDate.set(r.date, []);
    byDate.get(r.date).push(i);
  });
  const dayP = [], dayS = [];
  for (const indices of byDate.values()) {
    const a = indices.map((i) => actual[i]), p = indices.map((i) => predictions[i]);
    const pc = pearson(a, p), sc = spearman(a, p);
    if (Number.isFinite(pc)) dayP.push(pc);
    if (Number.isFinite(sc)) dayS.push(sc);
  }
  const mae = mean(actual.map((y, i) => Math.abs(y - predictions[i])));
  const errors = actual.map((y, i) => Math.abs(y - predictions[i]));
  const ybar = mean(actual);
  const sse = actual.reduce((s, y, i) => s + (y - predictions[i]) ** 2, 0);
  const sst = actual.reduce((s, y) => s + (y - ybar) ** 2, 0);
  return {
    n: rows.length, dates: byDate.size, pearson: pearson(actual, predictions), spearman: spearman(actual, predictions),
    per_day_pearson_mean: mean(dayP), per_day_pearson_median: median(dayP),
    per_day_spearman_mean: mean(dayS), per_day_spearman_median: median(dayS),
    mae, median_absolute_error: median(errors), max_absolute_error: Math.max(...errors),
    exact_after_2dp_share: mean(actual.map((y, i) => Number(y.toFixed(2)) === Number(predictions[i].toFixed(2)) ? 1 : 0)),
    within_0_05_share: mean(errors.map((e) => e <= 0.05 ? 1 : 0)),
    within_0_10_share: mean(errors.map((e) => e <= 0.10 ? 1 : 0)),
    r2: 1 - sse / sst,
  };
}

function ratio(value, values) {
  if (!Number.isFinite(value) || !values.length || values.some((x) => !Number.isFinite(x))) return NaN;
  const m = mean(values); return m > 0 ? value / m : NaN;
}
function pctRank(value, group) {
  if (!Number.isFinite(value) || !group.length) return NaN;
  return group.filter((x) => x <= value).length / group.length;
}

const csvText = fs.readFileSync(CSV_PATH, 'utf8');
const csvRows = parseCsv(csvText);
const headers = csvRows[0];
const dateColumns = headers.map((h, i) => ({ i, date: parseHeaderDate(h) })).filter((x) => x.date);
const sourceRows = csvRows.slice(2).filter((r) => r[0]);
const foRows = sourceRows.filter((r) => r[4].trim().toUpperCase() === 'F&O');
const metadata = new Map(foRows.map((r) => [r[0].trim().toUpperCase(), { sector: r[2].trim(), industry: r[3].trim() }]));
const labels = [];
for (const r of foRows) for (const c of dateColumns) {
  const score = Number(r[c.i]);
  if (Number.isFinite(score)) labels.push({ symbol: r[0].trim().toUpperCase(), date: c.date, score, ...metadata.get(r[0].trim().toUpperCase()) });
}
const symbols = [...new Set(labels.map((r) => r.symbol))].sort();

const db = new DatabaseSync(DB_PATH, { readOnly: true });
db.exec('PRAGMA query_only=ON; BEGIN');
const schema = db.prepare('PRAGMA table_info(daily_prices)').all().map((r) => ({ name: r.name, type: r.type }));
const globalCoverage = db.prepare('SELECT MIN(trade_date) min_date, MAX(trade_date) max_date, COUNT(*) rows FROM daily_prices').get();
const placeholders = symbols.map(() => '?').join(',');
const priceRows = db.prepare(`
  SELECT trade_date,symbol,series,open,high,low,close,prev_close,avg_price,volume,turnover,num_trades,delivery_qty,delivery_pct,source
  FROM daily_prices
  WHERE series='EQ' AND source='bhavcopy' AND trade_date BETWEEN '2024-11-01' AND '2025-04-29'
    AND symbol IN (${placeholders})
  ORDER BY symbol,trade_date
`).all(...symbols).map((r) => ({ ...r }));
db.exec('COMMIT');
db.close();

const bySymbol = new Map();
for (const row of priceRows) {
  if (!bySymbol.has(row.symbol)) bySymbol.set(row.symbol, []);
  bySymbol.get(row.symbol).push(row);
}
const featuresByKey = new Map();
for (const [symbol, rows] of bySymbol) {
  const base = rows.map((r) => ({
    atq: r.volume > 0 && r.num_trades > 0 ? r.volume / r.num_trades : NaN,
    atv: r.turnover > 0 && r.num_trades > 0 ? r.turnover / r.num_trades : NaN,
    dqpt: r.delivery_qty >= 0 && r.num_trades > 0 ? r.delivery_qty / r.num_trades : NaN,
    dpct: Number(r.delivery_pct), vol: Number(r.volume), turn: Number(r.turnover), trades: Number(r.num_trades),
    range: r.prev_close > 0 ? (r.high - r.low) / r.prev_close : NaN,
    absret: r.prev_close > 0 ? Math.abs(r.close - r.prev_close) / r.prev_close : NaN,
    closeLoc: r.high > r.low ? (r.close - r.low) / (r.high - r.low) : 0.5,
    gap: r.prev_close > 0 ? Math.abs(r.open / r.prev_close - 1) : NaN,
  }));
  const derived = [];
  for (let i = 0; i < rows.length; i++) {
    const prior20 = base.slice(i - 20, i), prior19 = base.slice(i - 19, i), inc20 = base.slice(i - 19, i + 1);
    const f = {
      symbol, date: rows[i].trade_date,
      q: ratio(base[i].atq, inc20.map((x) => x.atq)),
      d: ratio(base[i].dpct, prior19.map((x) => x.dpct)),
      dq: ratio(base[i].dqpt, prior20.map((x) => x.dqpt)),
      atv: ratio(base[i].atv, inc20.map((x) => x.atv)),
      volr: ratio(base[i].vol, prior20.map((x) => x.vol)),
      turnr: ratio(base[i].turn, prior20.map((x) => x.turn)),
      tradesr: ratio(base[i].trades, prior20.map((x) => x.trades)),
      ranger: ratio(base[i].range, prior20.map((x) => x.range)),
      absretr: ratio(base[i].absret, prior20.map((x) => x.absret)),
      closeLoc: base[i].closeLoc, gap: base[i].gap,
      rawVolume: base[i].vol, rawTrades: base[i].trades, rawDeliveryPct: base[i].dpct,
    };
    derived.push(f);
    const last3 = derived.slice(Math.max(0, i - 2), i + 1), last4 = derived.slice(Math.max(0, i - 3), i + 1);
    f.q3 = last3.length === 3 && last3.every((x) => Number.isFinite(x.q)) ? mean(last3.map((x) => x.q)) : NaN;
    f.d3 = last3.length === 3 && last3.every((x) => Number.isFinite(x.d)) ? mean(last3.map((x) => x.d)) : NaN;
    f.q4 = last4.length === 4 && last4.every((x) => Number.isFinite(x.q)) ? mean(last4.map((x) => x.q)) : NaN;
    f.d4 = last4.length === 4 && last4.every((x) => Number.isFinite(x.d)) ? mean(last4.map((x) => x.d)) : NaN;
    f.qd_sqrt = Math.sqrt(Math.max(0, f.q * f.d));
    f.qd_0825 = Math.max(0, f.q * f.d) ** 0.825;
    f.qd = f.q * f.d;
    f.logq = Math.log(Math.max(f.q, 1e-9));
    f.logd = Math.log(Math.max(f.d, 1e-9));
    f.capq5 = Math.min(f.q, 5);
    f.capd3 = Math.min(f.d, 3);
    featuresByKey.set(`${symbol}|${rows[i].trade_date}`, f);
  }
}

let joined = labels.map((l) => ({ ...l, ...(featuresByKey.get(`${l.symbol}|${l.date}`) || {}) }));
const daily = new Map();
for (const r of joined) {
  if (!daily.has(r.date)) daily.set(r.date, []);
  daily.get(r.date).push(r);
}
for (const rows of daily.values()) {
  for (const [src, dst] of [['q','qRank'], ['d','dRank'], ['atv','atvRank']]) {
    const group = rows.map((r) => r[src]).filter(Number.isFinite);
    for (const r of rows) r[dst] = pctRank(r[src], group);
  }
  const sectors = new Map();
  for (const r of rows) {
    if (!sectors.has(r.sector)) sectors.set(r.sector, []);
    sectors.get(r.sector).push(r);
  }
  for (const sectorRows of sectors.values()) for (const [src, dst] of [['q','sectorQRank'], ['d','sectorDRank']]) {
    const group = sectorRows.map((r) => r[src]).filter(Number.isFinite);
    for (const r of sectorRows) r[dst] = pctRank(r[src], group);
  }
}

const models = [
  { id: 'M1', name: 'Own-history average-trade-quantity shock', formula: 'OLS: score ~ q; q=(volume/num_trades)/inclusive-20 mean', features: ['q'] },
  { id: 'M2', name: 'Delivery participation shock', formula: 'OLS: score ~ d + dq; d=delivery_pct/prior-19 mean; dq=(delivery_qty/num_trades)/prior-20 mean', features: ['d','dq'] },
  { id: 'M3', name: 'Turnover/order-value proxy', formula: 'OLS: score ~ atv + turnr; atv=(turnover/num_trades)/inclusive-20 mean; turnr=turnover/prior-20 mean', features: ['atv','turnr'] },
  { id: 'M4', name: 'Multi-day accumulation', formula: 'OLS: score ~ q+d+3d/4d means of q,d', features: ['q','d','q3','d3','q4','d4'] },
  { id: 'M5', name: 'Cross-sectional and sector-relative (auxiliary metadata)', formula: 'OLS on daily F&O percentile ranks of q,d,atv and within-sector ranks of q,d; sector comes from the demo sheet, not bhavcopy', features: ['qRank','dRank','atvRank','sectorQRank','sectorDRank'] },
  { id: 'M6', name: 'Maximal nonlinear/capped public-bhavcopy model', formula: 'Ridge on q,d, nonlinear/capped q*d terms, order-value/delivery/volume/turnover/trade-count/range/return, multi-day and F&O cross-sectional features; no sector metadata', features: ['q','d','dq','atv','volr','turnr','tradesr','ranger','absretr','closeLoc','q3','d3','q4','d4','qd_sqrt','qd_0825','qd','logq','logd','capq5','capd3','qRank','dRank','atvRank'] },
];
const allFeatures = [...new Set(models.flatMap((m) => m.features))];
joined = joined.filter((r) => allFeatures.every((f) => Number.isFinite(r[f])) && Number.isFinite(r.score));

const dates = [...new Set(joined.map((r) => r.date))].sort();
const foldByDate = new Map();
dates.forEach((d, i) => foldByDate.set(d, Math.min(4, Math.floor(i * 5 / dates.length))));
const results = [];
for (const spec of models) {
  const model = fitRidge(joined, spec.features, spec.id === 'M6' ? 1e-3 : 1e-6);
  const fitted = joined.map((r) => predict(model, r));
  const oof = Array(joined.length);
  for (let fold = 0; fold < 5; fold++) {
    const train = joined.filter((r) => foldByDate.get(r.date) !== fold);
    const held = joined.map((r, i) => ({ r, i })).filter(({ r }) => foldByDate.get(r.date) === fold);
    const fm = fitRidge(train, spec.features, spec.id === 'M6' ? 1e-3 : 1e-6);
    for (const { r, i } of held) oof[i] = predict(fm, r);
  }
  results.push({ ...spec, model, fitted_metrics: metrics(joined, fitted), date_block_oof_metrics: metrics(joined, oof), fitted, oof });
}
results.sort((a, b) => b.fitted_metrics.spearman - a.fitted_metrics.spearman);
const best = results[0];
const bestPred = best.fitted;
const fixedBenchmarks = [
  {
    id: 'activity_v1',
    formula: '1.1048768252*q + 1.0099667732*d + 1.1730986222*(q*d)^0.825 - 0.14',
    predictions: joined.map((r) => 1.1048768252*r.q + 1.0099667732*r.d + 1.1730986222*r.qd_0825 - 0.14),
  },
  {
    id: 'sat10ic_eod_activity_v2',
    formula: '1.165335*q + 1.04631*d + 1.152161*(q*d)^0.84 - 0.213928',
    predictions: joined.map((r) => 1.165335*r.q + 1.04631*r.d + 1.152161*(Math.max(0,r.q*r.d)**0.84) - 0.213928),
  },
].map((b) => ({ id: b.id, formula: b.formula, metrics: metrics(joined, b.predictions) }));

const spikeChecks = [];
for (const [symbol, date] of [['ICICIBANK','2025-03-21'], ['RELIANCE','2025-03-21']]) {
  const i = joined.findIndex((r) => r.symbol === symbol && r.date === date);
  if (i < 0) { spikeChecks.push({ symbol, date, found: false }); continue; }
  const indices = joined.map((r, j) => ({ r, j })).filter(({ r }) => r.date === date);
  const actualGroup = indices.map(({ r }) => r.score), predGroup = indices.map(({ j }) => bestPred[j]);
  spikeChecks.push({
    symbol, date, found: true, actual: joined[i].score, predicted: bestPred[i],
    actual_percentile: pctRank(joined[i].score, actualGroup), predicted_percentile: pctRank(bestPred[i], predGroup),
    actual_top_decile: pctRank(joined[i].score, actualGroup) >= 0.9,
    predicted_top_decile: pctRank(bestPred[i], predGroup) >= 0.9,
    n_on_date: indices.length,
    components: Object.fromEntries(['q','d','dq','atv','q3','d3','qRank','dRank'].map((f) => [f, joined[i][f]])),
  });
}

const residualRows = joined.map((r, i) => ({ ...r, predicted: bestPred[i], residual: r.score - bestPred[i], absResidual: Math.abs(r.score - bestPred[i]) }));
const worst = [...residualRows].sort((a, b) => b.absResidual - a.absResidual).slice(0, 25);
const cutoff = quantile(residualRows.map((r) => r.absResidual), 0.9);
const worstDecile = residualRows.filter((r) => r.absResidual >= cutoff), rest = residualRows.filter((r) => r.absResidual < cutoff);
const summarize = (rows) => ({
  n: rows.length, mean_score: mean(rows.map((r) => r.score)), mean_abs_residual: mean(rows.map((r) => r.absResidual)),
  mean_q: mean(rows.map((r) => r.q)), mean_d: mean(rows.map((r) => r.d)), mean_dq: mean(rows.map((r) => r.dq)),
  mean_range_ratio: mean(rows.map((r) => r.ranger)), mean_abs_return_ratio: mean(rows.map((r) => r.absretr)),
  gap_over_20pct_share: mean(rows.map((r) => r.gap > 0.2 ? 1 : 0)),
  early_block_share: mean(rows.map((r) => r.date <= '2025-03-25' ? 1 : 0)),
  label_top_decile_share: mean(rows.map((r) => r.score >= quantile(residualRows.filter((x) => x.date === r.date).map((x) => x.score), 0.9) ? 1 : 0)),
});
const residualCorrelations = ['q','d','dq','atv','volr','turnr','tradesr','ranger','absretr','closeLoc','q3','d3','qRank','dRank'].map((f) => ({
  feature: f, pearson: pearson(residualRows.map((r) => r.residual), residualRows.map((r) => r[f])),
  spearman: spearman(residualRows.map((r) => r.residual), residualRows.map((r) => r[f])),
})).sort((a, b) => Math.abs(b.pearson) - Math.abs(a.pearson));

const nnFeatures = ['q','d','dq','atv','volr','turnr','tradesr','ranger','absretr','closeLoc','q3','d3'];
const nnMus = nnFeatures.map((f) => mean(joined.map((r) => r[f])));
const nnSds = nnFeatures.map((f, j) => Math.sqrt(mean(joined.map((r) => (r[f] - nnMus[j]) ** 2))) || 1);
const z = joined.map((r) => nnFeatures.map((f, j) => (r[f] - nnMus[j]) / nnSds[j]));
const contradictions = [];
for (let i = 0; i < joined.length; i++) {
  let bd = Infinity, bj = -1;
  for (let j = 0; j < joined.length; j++) {
    if (i === j || joined[i].date === joined[j].date) continue;
    let d2 = 0;
    for (let k = 0; k < nnFeatures.length; k++) d2 += (z[i][k] - z[j][k]) ** 2;
    if (d2 < bd) { bd = d2; bj = j; }
  }
  if (bj >= 0 && i < bj) contradictions.push({
    a: `${joined[i].symbol} ${joined[i].date}`, b: `${joined[bj].symbol} ${joined[bj].date}`,
    distance: Math.sqrt(bd / nnFeatures.length), score_a: joined[i].score, score_b: joined[bj].score,
    score_diff: Math.abs(joined[i].score - joined[bj].score),
  });
}
contradictions.sort((a, b) => (b.score_diff / (b.distance + 0.02)) - (a.score_diff / (a.distance + 0.02)));

const byDateResidual = [...new Set(residualRows.map((r) => r.date))].map((date) => {
  const x = residualRows.filter((r) => r.date === date);
  return { date, n: x.length, mae: mean(x.map((r) => r.absResidual)), bias: mean(x.map((r) => r.residual)), pearson: pearson(x.map((r) => r.score), x.map((r) => r.predicted)), spearman: spearman(x.map((r) => r.score), x.map((r) => r.predicted)) };
}).sort((a, b) => b.mae - a.mae);

const out = {
  generated_at: new Date().toISOString(), runtime: { engine: process.version, note: 'Native Windows Node used because sandbox denied execution of installed native Python.' },
  inputs: { csv_path: CSV_PATH, csv_sha256: sha256(CSV_PATH), transcript_path: TRANSCRIPT_PATH, transcript_sha256: sha256(TRANSCRIPT_PATH), db_path: DB_PATH, db_open: 'DatabaseSync(readOnly=true) + PRAGMA query_only=ON + read transaction', db_schema: schema, db_global_coverage: globalCoverage },
  alignment: { csv_data_rows: sourceRows.length, fo_symbols_in_sheet: foRows.length, distinct_fo_symbols: symbols.length, label_dates: dateColumns.length, labels_nonmissing: labels.length, eligible_identical_cells: joined.length, eligible_dates: dates.length, eligible_symbols: new Set(joined.map((r) => r.symbol)).size, first_date: dates[0], last_date: dates.at(-1), price_rows_loaded: priceRows.length },
  label_distribution: { min: Math.min(...joined.map((r) => r.score)), p10: quantile(joined.map((r) => r.score), .1), median: median(joined.map((r) => r.score)), p90: quantile(joined.map((r) => r.score), .9), p99: quantile(joined.map((r) => r.score), .99), max: Math.max(...joined.map((r) => r.score)), mean: mean(joined.map((r) => r.score)) },
  models: results.map(({ fitted, oof, ...r }) => r), fixed_benchmarks: fixedBenchmarks, best_model_id: best.id,
  spike_checks: spikeChecks,
  residual_analysis: { worst_decile_cutoff: cutoff, worst_decile: summarize(worstDecile), rest: summarize(rest), top_residual_correlations: residualCorrelations.slice(0, 10), worst_dates: byDateResidual.slice(0, 10), worst_cells: worst.map((r) => ({ symbol: r.symbol, date: r.date, sector: r.sector, actual: r.score, predicted: r.predicted, residual: r.residual, q: r.q, d: r.d, dq: r.dq, atv: r.atv, ranger: r.ranger, gap: r.gap })), nearest_feature_contradictions: contradictions.slice(0, 10) },
};
fs.writeFileSync(OUT_PATH, JSON.stringify(out, null, 2));
const residualHeader = ['symbol','date','sector','score','predicted','residual','absResidual','q','d','dq','atv','volr','turnr','tradesr','ranger','absretr','q3','d3','qRank','dRank'];
fs.writeFileSync(RESIDUAL_PATH, [residualHeader.join(','), ...residualRows.map((r) => residualHeader.map((f) => JSON.stringify(r[f] ?? '')).join(','))].join('\n'));
console.log(JSON.stringify({ alignment: out.alignment, label_distribution: out.label_distribution, best_model_id: out.best_model_id, models: out.models.map((m) => ({ id: m.id, fitted: m.fitted_metrics, oof: m.date_block_oof_metrics })), fixed_benchmarks: out.fixed_benchmarks, spikes: out.spike_checks, residual_summary: { worst_decile: out.residual_analysis.worst_decile, rest: out.residual_analysis.rest, worst_dates: out.residual_analysis.worst_dates.slice(0, 5), worst_cells: out.residual_analysis.worst_cells.slice(0, 8), contradictions: out.residual_analysis.nearest_feature_contradictions.slice(0, 5) } }, null, 2));
