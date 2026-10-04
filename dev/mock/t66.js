const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' });
  const pg = await b.newPage({ viewport: { width: 844, height: 390 }, isMobile: true, hasTouch: true, deviceScaleFactor: 2 });
  await pg.route(/jsdelivr/, r => r.fulfill({ path: '../skins/node_modules/hls.js/dist/hls.min.js', contentType: 'text/javascript' }));
  const errs = []; pg.on('pageerror', e => errs.push(e.message));
  await pg.goto('http://localhost:8765/'); await pg.waitForTimeout(2000);
  await pg.evaluate(() => { S.focus = { cam: 'front_door' }; S.full = true; S.fui = true; render(); });
  await pg.waitForTimeout(800);
  const c = await pg.context().newCDPSession(pg);
  const T = async (type, pts) => c.send('Input.dispatchTouchEvent', { type, touchPoints: pts.map(([x, y], i) => ({ x, y, id: i })) });
  await T('touchStart', [[300, 180], [340, 200]]);
  for (let k = 1; k <= 8; k++) await T('touchMove', [[300 - k * 15, 180 - k * 8], [340 + k * 15, 200 + k * 8]]);
  await T('touchEnd', []);
  await pg.waitForTimeout(300);
  const r1 = await pg.evaluate(() => { const w = document.querySelector('#fullv .fvw'); const side = document.querySelector('#fullv .fside, #fullv #fts'); const q = side && side.getBoundingClientRect();
    return { zs: w.style.getPropertyValue('--zs'), zoomed: w.classList.contains('zoomed'), side: q && [Math.round(q.left), Math.round(q.right)], vw: innerWidth, vv: visualViewport.scale, fui: S.fui, full: S.full }; });
  // one finger pan
  await T('touchStart', [[400, 200]]); for (let k = 1; k <= 5; k++) await T('touchMove', [[400 - k * 20, 200 - k * 10]]); await T('touchEnd', []);
  await pg.waitForTimeout(200);
  const r2 = await pg.evaluate(() => { const w = document.querySelector('#fullv .fvw'); return [w.style.getPropertyValue('--zx'), S.full, S.fui]; });
  // tap (should toggle UI)
  await pg.waitForTimeout(500); await pg.touchscreen.tap(400, 200); await pg.waitForTimeout(300);
  const r3 = await pg.evaluate(() => [S.fui, document.querySelector('#fullv .fvw').style.getPropertyValue('--zs')]);
  console.log(JSON.stringify([r1, r2, r3]), errs);
  await pg.waitForTimeout(500); await pg.touchscreen.tap(400, 200); await pg.waitForTimeout(500); await pg.evaluate(() => { const i = document.getElementById('fullimg'); if (i) i.src = 'front_s.jpg'; }); await pg.waitForTimeout(500); await pg.screenshot({ path: 'fz.png' }); await b.close();
})();
