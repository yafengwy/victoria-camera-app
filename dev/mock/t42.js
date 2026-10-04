const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' }); const pg = await b.newPage({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });
  await pg.route(/jsdelivr/, r => r.fulfill({ path: '../skins/node_modules/hls.js/dist/hls.min.js', contentType: 'text/javascript' }));
  const errs = []; pg.on('pageerror', e => errs.push(e.message));
  await pg.goto('http://localhost:8765/'); await pg.waitForTimeout(2500);
  await pg.evaluate(() => { S.view = 'review'; S.playing = false; S.rv.t = Data.events[0].t - 3600e3; render(); }); await pg.waitForTimeout(400);
  // scroll the timeline to 4 px away from an alert (well outside its 20 s length)
  const r = await pg.evaluate(() => { const e = Data.events[3]; const off = 4 / rvPx() * MIN; const sc = document.getElementById('rvsc'); const t = (e.end || e.t) + off; sc.scrollLeft = rvTW() - (rvEnd - t) / MIN * rvPx(); return { e: e.t, end: e.end, off: Math.round(off / 1000) }; });
  await pg.waitForTimeout(150);
  console.log('while near', await pg.evaluate(() => document.getElementById('rv-front_door').className), 'offset s', r.off);
  await pg.waitForTimeout(700);
  console.log('after stop', await pg.evaluate(e => [document.getElementById('rv-front_door').className, (S.rv.t - e.end) / 1000], r), errs);
  await b.close();
})();
