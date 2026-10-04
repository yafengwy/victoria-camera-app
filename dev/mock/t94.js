const { chromium } = require('playwright');
(async () => { const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' });
for (const [w,h] of [[1180,820],[1440,860],[412,900]]) { const pg = await b.newPage({ viewport: { width: w, height: h } });
await pg.goto('file://' + process.cwd() + '/../camapp/preview.html'); await pg.waitForTimeout(1500);
const r = await pg.evaluate(async () => { S.view = 'review'; S.rv.fopen = true; render(); await new Promise(r => setTimeout(r, 400));
  const dd = document.querySelector('.rvdd'); const q = dd.getBoundingClientRect();
  const pts = [[q.right - 10, q.top + 40], [q.right - 10, q.bottom - 20], [q.left + 20, q.top + 60]];
  return { dd: [Math.round(q.left), Math.round(q.top), Math.round(q.right), Math.round(q.bottom)], onTop: pts.map(([x, y]) => !!document.elementFromPoint(x, y).closest('.rvdd')) }; });
console.log(w, JSON.stringify(r)); if (w === 1180) await pg.screenshot({ path: 'wide/dd.png' }); await pg.close(); }
await b.close(); })();
