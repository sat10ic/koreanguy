import fs from 'node:fs';
import { DatabaseSync } from 'node:sqlite';

const csvPath = 'C:/Users/satta/Downloads/DEMO SHEET - MARCH APRIL - Sheet1.csv';
const transcriptPath = 'C:/Users/satta/Downloads/NoteGPT_Transcript_How To Track Smart Money Footprint In Indian Stock Market  Proper Step By Step Video.txt';
const dbPath = 'C:/Users/satta/Downloads/koreanguy/manas_os/data/manas.db';

const csv = fs.readFileSync(csvPath, 'utf8');
const lines = csv.split(/\r?\n/).filter((line) => line.length);
console.log(JSON.stringify({
  csvBytes: Buffer.byteLength(csv),
  csvRowsIncludingHeader: lines.length,
  csvHeader: lines[0],
  csvFirstRows: lines.slice(1, 4),
  transcriptBytes: fs.statSync(transcriptPath).size,
  transcriptLines: fs.readFileSync(transcriptPath, 'utf8').split(/\r?\n/).length,
}, null, 2));

const db = new DatabaseSync(dbPath, { readOnly: true });
console.log('PRAGMA', db.prepare('PRAGMA table_info(daily_prices)').all());
console.log('COVERAGE', db.prepare(`
  SELECT MIN(trade_date) min_date, MAX(trade_date) max_date,
         COUNT(*) rows, COUNT(DISTINCT symbol) symbols,
         SUM(num_trades IS NOT NULL) with_num_trades,
         SUM(turnover IS NOT NULL) with_turnover,
         SUM(delivery_qty IS NOT NULL) with_delivery_qty,
         SUM(delivery_pct IS NOT NULL) with_delivery_pct
  FROM daily_prices WHERE trade_date BETWEEN '2025-03-03' AND '2025-04-29'
`).get());
console.log('DATES', db.prepare(`
  SELECT trade_date, COUNT(*) rows, COUNT(DISTINCT symbol) symbols,
         SUM(num_trades IS NOT NULL) with_num_trades,
         SUM(turnover IS NOT NULL) with_turnover
  FROM daily_prices WHERE trade_date BETWEEN '2025-03-03' AND '2025-04-29'
  GROUP BY trade_date ORDER BY trade_date
`).all());
db.close();
