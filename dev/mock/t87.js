const { chromium } = require('playwright');
(async () => { const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' }); const pg = await b.newPage({ viewport: { width: 1440, height: 860 } });
const errs=[]; pg.on('pageerror',e=>errs.push(e.message));
await pg.goto('file://' + process.cwd() + '/../camapp/preview.html'); await pg.waitForTimeout(1500);
const ev = await pg.evaluate(() => { const base = Data.cams.slice(); for (let i = 0; i < 6; i++) Data.cams.push(Object.assign({}, base[i % base.length], { id: 'x' + i, name: 'Extra ' + i })); S.rv.lay = 'top'; S.view = 'review'; render();
  const e = Data.events.filter(e => e.cam === 'closet' || e.cam === 'living_room')[3] || Data.events[5]; return { t: e.t, cam: e.cam }; });
await pg.waitForTimeout(600);
await pg.evaluate(t => { S.rv.t = t + 2000; render(); rvScrollTo(S.rv.t); }, ev.t);
await pg.waitForTimeout(800);
const r = await pg.evaluate(() => { const sc = document.getElementById('rvsc'); const line = document.querySelector('.rvdock.v .hline'); const lr = line.getBoundingClientRect(), sr = sc.getBoundingClientRect();
  const tiles = [...document.querySelectorAll('.rvcam')].map(n => ({ id: n.id.slice(3), o: +n.style.order || 0, feat: n.classList.contains('feat'), x: Math.round(n.getBoundingClientRect().left), y: Math.round(n.getBoundingClientRect().top), w: Math.round(n.getBoundingClientRect().width) })).sort((a, b) => a.y - b.y || a.x - b.x).slice(0, 6);
  return { lay: rvLay(), lineMid: Math.round(lr.top - sr.top) + '/' + Math.round(sr.height), tiles }; });
console.log(ev.cam, JSON.stringify(r), errs);
await pg.screenshot({ path: 'wide/rvtop.png' });
// click an icon below the line: line should stay in the middle and time should change to that icon
const ic = await pg.evaluate(() => { const sc = document.getElementById('rvsc').getBoundingClientRect(); const ics = [...document.querySelectorAll('#rvsc .hico[data-t]')].map(n => { const q = n.getBoundingClientRect(); return { y: q.top + q.height / 2, x: q.left + q.width / 2, t: +n.dataset.t }; }).filter(q => q.y > sc.top + sc.height / 2 + 40 && q.y < sc.bottom - 20); return ics[0]; });
if (ic) { await pg.mouse.click(ic.x, ic.y); await pg.waitForTimeout(900);
  console.log('icon', await pg.evaluate(t => ({ diffS: Math.round((S.rv.t - t) / 1000), bub: document.getElementById('rvbub').textContent }), ic.t)); }
await b.close(); })();
