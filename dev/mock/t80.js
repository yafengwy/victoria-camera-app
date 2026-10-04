const { chromium } = require('playwright');
(async () => { const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' });
for (const [w,h,n] of [[950,700,'desk'],[390,844,'phone'],[1440,900,'wide']]) { const pg = await b.newPage({ viewport: { width: w, height: h } }); const errs=[]; pg.on('pageerror',e=>errs.push(e.message));
  await pg.route(/jsdelivr/, r => r.fulfill({ path: '../skins/node_modules/hls.js/dist/hls.min.js', contentType: 'text/javascript' }));
  await pg.goto('http://localhost:8765/'); await pg.waitForTimeout(1800);
  await pg.evaluate(() => { S.layout = 'grid'; S.expanded = 'front_door'; render(); document.getElementById('panel').scrollIntoView({block:'center'}); }); await pg.waitForTimeout(500);
  const r = await pg.evaluate(() => { const p = document.querySelector('.pctl'); const pr = p.getBoundingClientRect(); return { acts: [...p.querySelectorAll('.pctl2 button')].map(b => b.dataset.act), trioL: Math.round(document.querySelector('.pctl .trio').getBoundingClientRect().left - pr.left), right: Math.round(pr.right - document.querySelector('.pctl2').getBoundingClientRect().right), overflow: p.scrollWidth > p.clientWidth }; });
  console.log(n, JSON.stringify(r), errs); await pg.screenshot({ path: 'wide/pctl_' + n + '.png' }); await pg.close(); }
await b.close(); })();
