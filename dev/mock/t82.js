const { chromium } = require('playwright');
(async () => { const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' });
for (const w of [1100, 1440]) { const pg = await b.newPage({ viewport: { width: w, height: 900 } });
await pg.goto('file://' + process.cwd() + '/../camapp/preview.html'); await pg.waitForTimeout(1500);
await pg.evaluate(() => { const base = Data.cams.filter(c => c.group === 'Outside'); for (let i = 0; i < 6; i++) Data.cams.push(Object.assign({}, base[i % base.length], { id: 'x' + i, name: 'Extra ' + i })); S.layout = 'grid'; });
const ids = await pg.evaluate(() => Data.cams.filter(c => c.group === 'Outside').slice(0, 5).map(c => c.id));
const out = [];
for (const id of ids) { const r = await pg.evaluate(id => { S.expanded = id; render(); const g = document.querySelector('#panel').parentNode; const cols = getComputedStyle(g).gridTemplateColumns.split(' ').map(parseFloat); const x0 = g.getBoundingClientRect().left; const camX = document.getElementById('cam-' + id).getBoundingClientRect().left - x0; const p = document.getElementById('panel').getBoundingClientRect(); const ci = x => { let a = 0; for (let i = 0; i < cols.length; i++) { if (x < a + cols[i] / 2) return i + 1; a += cols[i] + 10; } return cols.length; }; return ci(camX) + '->' + document.getElementById('panel').style.gridColumn; }, id); out.push(r); }
console.log(w, out.join('  ')); if (w === 1100) await pg.screenshot({ path: 'wide/pair.png' }); await pg.close(); }
await b.close(); })();
