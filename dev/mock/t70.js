const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' }); const pg = await b.newPage({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });
  await pg.route(/jsdelivr/, r => r.fulfill({ path: '../skins/node_modules/hls.js/dist/hls.min.js', contentType: 'text/javascript' }));
  const errs = []; pg.on('pageerror', e => errs.push(e.message));
  await pg.goto('http://localhost:8765/'); await pg.waitForTimeout(2000);
  await pg.evaluate(() => { S.focus = { cam: 'front_door' }; S.camTime.front_door = now() - 30 * 60000; S.playing = false; render(); });
  await pg.waitForTimeout(500);
  const c = await pg.context().newCDPSession(pg);
  const T = (type, pts) => c.send('Input.dispatchTouchEvent', { type, touchPoints: pts.map(([x, y], i) => ({ x, y, id: i })) });
  const before = await pg.evaluate(() => S.camTime.front_door);
  await T('touchStart', [[250, 600]]); for (let k = 1; k <= 10; k++) { await T('touchMove', [[250, 600 - k * 20]]); await pg.waitForTimeout(16); } await T('touchEnd', []);
  await pg.waitForTimeout(1200);
  const after = await pg.evaluate(() => S.camTime.front_door);
  // a plain tap still works
  await pg.touchscreen.tap(250, 700); await pg.waitForTimeout(500);
  const tap = await pg.evaluate(() => S.camTime.front_door);
  console.log(JSON.stringify({ movedMin: Math.round((after - before) / 60000), tapChanged: tap !== after }), errs);
  await b.close();
})();
