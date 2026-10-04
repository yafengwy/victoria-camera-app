const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' }); const pg = await b.newPage({ viewport: { width: 377, height: 475 }, isMobile: true, hasTouch: true });
  await pg.route(/jsdelivr/, r => r.fulfill({ path: '../skins/node_modules/hls.js/dist/hls.min.js', contentType: 'text/javascript' }));
  const errs = []; pg.on('pageerror', e => errs.push(e.message));
  await pg.goto('http://localhost:8765/'); await pg.waitForTimeout(2000);
  const P = await pg.evaluate(() => {
    const base = now() - 3 * HOUR; Data.events = Data.events.filter(e => e.t < base - HOUR || e.t > base + HOUR);
    const mk = (id, cam, t, end, label) => ({ id, cam, t, end, label, dets: [], interesting: true, zones: [], img: '' });
    Data.events.push(mk('c1', 'garage1', base, base + 200e3, 'Car'), mk('p1', 'front_door', base + 100e3, base + 103e3, 'Person'), mk('p2', 'front_door', base + 110e3, base + 112e3, 'Person'));
    S.view = 'review'; S.playing = false; S.rv.t = base - 20 * MIN; render(); rvScrollTo(S.rv.t); drawRvTrack(true); paintReview(); return base + 100e3;
  });
  await pg.waitForTimeout(500);
  const ic = await pg.evaluate(() => [...document.querySelectorAll('#rvtrack .hico')].map(n => { const q = n.getBoundingClientRect(); return { x: q.left + q.width / 2, y: q.top + q.height / 2, t: n.title, d: n.dataset.t }; }).filter(o => o.x > 10 && o.x < 320));
  console.log(ic.map(o => o.t + '@' + Math.round(o.x)).join(' '));
  const pi = ic.find(o => /person/i.test(o.t)) || ic[0];
  await pg.touchscreen.tap(pi.x + 8, pi.y + 3); await pg.waitForTimeout(500);
  console.log(await pg.evaluate(P => { const ln = document.querySelector('.hline').getBoundingClientRect(), bars = [...document.querySelectorAll('#rvtrack .hbar')].map(n => n.getBoundingClientRect()).map(q => Math.round(q.left + q.width / 2 - (ln.left + ln.width / 2))).filter(d => Math.abs(d) < 30); return ['jump off person start by s', Math.round((S.rv.t - P) / 1000), 'bar centers vs line px', bars]; }, P), errs);
  await b.close();
})();
