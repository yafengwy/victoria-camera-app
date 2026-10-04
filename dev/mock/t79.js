const { chromium } = require('playwright');
(async () => { const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' }); const pg = await b.newPage({ viewport: { width: 1100, height: 900 } });
await pg.goto('file://' + process.cwd() + '/../camapp/preview.html'); await pg.waitForTimeout(1500);
const r = await pg.evaluate(() => { const base = Data.cams.filter(c => c.group === 'Outside'); for (let i = 0; i < 5; i++) Data.cams.push(Object.assign({}, base[i % base.length], { id: 'x' + i, name: 'Extra ' + i })); S.layout = 'grid'; S.expanded = 'california_room'; render();
  return [...document.querySelectorAll('.group')[0].querySelectorAll('.cam, .panel')].map(e => { const r = e.getBoundingClientRect(); return (e.id || '').replace('cam-', '') + '@' + Math.round(r.left) + ',' + Math.round(r.top); }); });
console.log(r.join(' ')); await pg.screenshot({ path: 'wide/dense.png' }); await b.close(); })();
