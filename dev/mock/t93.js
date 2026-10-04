const { chromium } = require('playwright');
(async () => { const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' }); const pg = await b.newPage({ viewport: { width: 820, height: 1180 }, deviceScaleFactor: 1, hasTouch: true });
const errs=[]; pg.on('pageerror',e=>errs.push(e.message));
await pg.goto('file://' + process.cwd() + '/../camapp/preview.html'); await pg.waitForTimeout(1500);
for (const [vw,vh,lay] of [[820,1180,'big'],[1180,820,'big'],[820,1180,'top']]) {
await pg.setViewportSize({ width: vw, height: vh }); await pg.evaluate(async l => { const base = Data.cams.slice(0, 6); if (!Data.cams.some(c => c.id === 'x0')) for (let i = 0; i < 8; i++) Data.cams.push(Object.assign({}, base[i % base.length], { id: 'x' + i, name: 'Extra ' + i })); S.view = 'review'; S.rv.lay = l; S.rv.t = null; render(); await new Promise(r => setTimeout(r, 600)); }, lay);
const r = await pg.evaluate(() => [...document.querySelectorAll('.rvcam')].slice(0, 6).map(n => { const q = n.getBoundingClientRect(); return n.id.slice(3) + (n.classList.contains('feat') ? '*' : '') + ' ' + Math.round(q.left) + ',' + Math.round(q.top) + ' ' + Math.round(q.width) + 'x' + Math.round(q.height) + ' gc=' + n.style.gridColumn; }).concat([getComputedStyle(document.querySelector('.rvcams')).gridTemplateColumns, document.querySelector('.rvcams').className]));
console.log(vw, lay, r.join(' | '), errs); await pg.screenshot({ path: 'wide/ipad_' + vw + lay + '.png' }); }
await b.close(); })();
