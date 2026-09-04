import fs from 'node:fs';

const path = 'C:/Users/satta/Downloads/NoteGPT_Transcript_How To Track Smart Money Footprint In Indian Stock Market  Proper Step By Step Video.txt';
const text = fs.readFileSync(path, 'utf8');
const keys = [
  'ऑर्डर', 'ट्रेड', 'क्वांटिटी', 'वॉल्यूम', 'एक्टिविटी', '3.5', 'फिल्टर',
  'थ्री डेज', 'फोर डे', 'टेन डेज', 'एवरेज', 'डिलीवरी', 'परसेंट', 'रेशियो',
  'स्कोर', 'फुटप्रिंट', 'स्प्लिट', 'एक्यूमुलेशन', 'डिस्ट्रीब्यूशन', 'कन्सीक्यूटिव',
  'कंटीन्यू', 'एडीआर', 'डेली बेसिस', 'दिन', 'डे', '50 की', '100', 'चार दिन',
  'तीन दिन', 'दस दिन', '20 दिन', 'थ्रेशोल्ड', 'ग्रेटर देन', 'बिलो', 'ऊपर', 'नीचे',
];
const rows = [];
for (const [index, line] of text.split(/\r?\n/).entries()) {
  const parts = line.trim().split(/(?<=[।?!])\s+/u).filter(Boolean);
  for (const part of parts) {
    if (keys.some((key) => part.toLocaleLowerCase('hi').includes(key.toLocaleLowerCase('hi')))) {
      rows.push({ line: index + 1, text: part });
    }
  }
}
console.log(`source_lines=${text.split(/\r?\n/).length} source_chars=${text.length} selected_units=${rows.length}`);
const start = Math.max(1, Number(process.argv[2] || 1));
const end = Math.min(rows.length, Number(process.argv[3] || rows.length));
rows.slice(start - 1, end).forEach((row, i) => {
  const n = start + i;
  console.log(`${String(n).padStart(3, '0')}\tL${row.line}\t${row.text}`);
});
