const { chromium } = require('playwright');
(async () => { const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' });
for (const [w,h] of [[1440,860],[1100,760],[412,900]]) { const pg = await b.newPage({ viewport: { width: w, height: h } }); const errs=[]; pg.on('pageerror',e=>errs.push(e.message));
await pg.goto('file://' + process.cwd() + '/../camapp/preview.html'); await pg.waitForTimeout(1500);
const r = await pg.evaluate(async () => { const base = Data.cams.slice(); for (let i = 0; i < 8; i++) Data.cams.push(Object.assign({}, base[i % base.length], { id: 'x' + i, name: 'Extra ' + i })); S.view = 'review';
  const out = {}; for (const lay of ['top', 'big']) { S.rv.lay = lay; const e = Data.events.find(e => e.interesting); S.rv.t = e.t + 1000; render(); await new Promise(r => setTimeout(r, 300)); rvLayout(S.rv.t);
    const vis = [...document.querySelectorAll('.rvcam')].filter(n => { const q = n.getBoundingClientRect(); return q.top < innerHeight - 80 && q.bottom > 60; }).length;
    const f = document.querySelector('.rvcam.feat'); out[lay] = { L: rvLay(), cols: getComputedStyle(document.querySelector('.rvcams')).gridTemplateColumns.split(' ').length, featW: f ? Math.round(f.getBoundingClientRect().width) : 0, visible: vis }; }
  S.rv.colsOpen = true; render(); out.menu = [...document.querySelectorAll('[data-act=rvlay]')].map(b => b.dataset.v + (b.getAttribute('aria-checked') === 'true' ? '*' : '')).join(','); return out; });
console.log(w, JSON.stringify(r), errs); if (w === 1440) { await pg.evaluate(() => { S.rv.colsOpen = false; S.rv.lay = 'big'; render(); }); await pg.waitForTimeout(500); await pg.screenshot({ path: 'wide/rvbig.png' }); } await pg.close(); }
await b.close(); })();
