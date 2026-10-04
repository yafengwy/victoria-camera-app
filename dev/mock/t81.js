const { chromium } = require('playwright');
(async () => { const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' });
for (const lay of ['grid','list']) for (const [w,h] of [[412,915],[1100,800]]) { const pg = await b.newPage({ viewport: { width: w, height: h } });
  await pg.route(/jsdelivr/, r => r.fulfill({ path: '../skins/node_modules/hls.js/dist/hls.min.js', contentType: 'text/javascript' }));
  await pg.goto('http://localhost:8765/'); await pg.waitForTimeout(1800);
  await pg.evaluate(l => { S.layout = l; S.expanded = 'front_door'; render(); document.getElementById('panel').scrollIntoView({block:'center'}); }, lay); await pg.waitForTimeout(500);
  const r = await pg.evaluate(() => { const H = s => { const e = document.querySelector(s); return e ? Math.round(e.getBoundingClientRect().height) : null; }; return { panel: H('#panel'), pctl: H('.pctl'), round: H('.pctl .round'), trioBtn: H('.trio button'), tl: H('.tl'), tabs: H('.tabs'), tabbody: H('.tabbody'), thumb: H('.thumb'), btn: H('.tabbody .btn') }; });
  console.log(lay, w, JSON.stringify(r)); await pg.screenshot({ path: 'wide/cmp_' + lay + w + '.png' }); await pg.close(); }
await b.close(); })();
