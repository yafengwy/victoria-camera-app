const { chromium } = require('playwright');
(async () => { const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' });
for (const [w,h] of [[412,900],[820,1180],[1180,820],[1440,860]]) { const pg = await b.newPage({ viewport: { width: w, height: h } }); const errs=[]; pg.on('pageerror',e=>errs.push(e.message));
await pg.goto('file://' + process.cwd() + '/../camapp/preview.html'); await pg.waitForTimeout(1500);
const r = await pg.evaluate(async () => { const base = Data.cams.slice(0, 6); for (let i = 0; i < 8; i++) Data.cams.push(Object.assign({}, base[i % base.length], { id: 'x' + i, name: 'Extra ' + i })); S.view = 'review'; S.rv.lay = 'top'; S.rv.t = null; render(); await new Promise(r => setTimeout(r, 600));
  const t = [...document.querySelectorAll('.rvcam')].map(n => ({ n, q: n.getBoundingClientRect() })).sort((a, b) => a.q.top - b.q.top || a.q.left - b.q.left).slice(0, 5).map(({ n, q }) => (n.classList.contains('feat') ? '*' : '') + Math.round(q.left) + ',' + Math.round(q.top) + ' ' + Math.round(q.width) + 'x' + Math.round(q.height));
  S.rv.colsOpen = true; render(); const menu = [...document.querySelectorAll('[data-act=rvlay]')].map(b => b.dataset.v + (b.getAttribute('aria-checked') === 'true' ? '*' : '')).join(',');
  S.rv.colsOpen = false; render(); return { lay: rvLay(), tiles: t.join(' | '), menu }; });
console.log(w + 'x' + h, JSON.stringify(r), errs); await pg.screenshot({ path: 'wide/merge_' + w + '.png' }); await pg.close(); }
await b.close(); })();
