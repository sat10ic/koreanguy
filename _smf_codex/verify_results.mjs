import fs from 'node:fs';

function parseCsv(text) {
  const out = []; let row = [], field = '', q = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (q && c === '"' && text[i + 1] === '"') { field += '"'; i++; }
    else if (c === '"') q = !q;
    else if (!q && c === ',') { row.push(field); field = ''; }
    else if (!q && c === '\n') { row.push(field.replace(/\r$/, '')); out.push(row); row = []; field = ''; }
    else field += c;
  }
  if (field || row.length) { row.push(field); out.push(row); }
  return out;
}
function corr(x, y) {
  const n = x.length;
  const sx = x.reduce((a,b)=>a+b,0), sy = y.reduce((a,b)=>a+b,0);
  const sxx = x.reduce((a,b)=>a+b*b,0), syy = y.reduce((a,b)=>a+b*b,0);
  const sxy = x.reduce((a,b,i)=>a+b*y[i],0);
  return (n*sxy-sx*sy)/Math.sqrt((n*sxx-sx*sx)*(n*syy-sy*sy));
}
function rank(x) {
  const a=x.map((v,i)=>[v,i]).sort((u,v)=>u[0]-v[0]||u[1]-v[1]), r=Array(x.length);
  for(let i=0;i<a.length;){let j=i+1; while(j<a.length&&a[j][0]===a[i][0])j++; const z=(i+j+1)/2; for(let k=i;k<j;k++)r[a[k][1]]=z; i=j;}
  return r;
}
const table=parseCsv(fs.readFileSync('_smf_codex/best_model_residuals.csv','utf8'));
const h=table[0], rows=table.slice(1).map(a=>Object.fromEntries(h.map((k,i)=>[k,a[i]])));
const actual=rows.map(r=>Number(r.score)), pred=rows.map(r=>Number(r.predicted));
const abs=actual.map((v,i)=>Math.abs(v-pred[i]));
const grouped=Map.groupBy(rows,(r)=>r.date);
const dayP=[], dayS=[];
for(const rs of grouped.values()){
  const a=rs.map(r=>Number(r.score)), p=rs.map(r=>Number(r.predicted));
  dayP.push(corr(a,p)); dayS.push(corr(rank(a),rank(p)));
}
const med=(a)=>{const b=[...a].sort((x,y)=>x-y),n=b.length;return n%2?b[(n-1)/2]:(b[n/2-1]+b[n/2])/2};
const check={
  n:rows.length, pearson:corr(actual,pred), spearman:corr(rank(actual),rank(pred)),
  per_day_pearson_mean:dayP.reduce((a,b)=>a+b,0)/dayP.length, per_day_pearson_median:med(dayP),
  per_day_spearman_mean:dayS.reduce((a,b)=>a+b,0)/dayS.length, per_day_spearman_median:med(dayS),
  mae:abs.reduce((a,b)=>a+b,0)/abs.length,
  exact_after_2dp_share:actual.filter((v,i)=>Number(v.toFixed(2))===Number(pred[i].toFixed(2))).length/actual.length,
};
const results=JSON.parse(fs.readFileSync('_smf_codex/results.json','utf8'));
const expected=results.models.find(m=>m.id===results.best_model_id).fitted_metrics;
const comparisons=Object.fromEntries(Object.entries(check).map(([k,v])=>[k,{check:v,expected:expected[k],difference:v-expected[k]}]));
const maxDifference=Math.max(...Object.values(comparisons).map(x=>Math.abs(x.difference)));
console.log(JSON.stringify({best:results.best_model_id, comparisons, maxDifference, pass:maxDifference<1e-10},null,2));
if(maxDifference>=1e-10) process.exitCode=1;
