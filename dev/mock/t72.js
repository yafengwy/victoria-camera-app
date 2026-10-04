const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' }); const pg = await b.newPage({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });
  await pg.route(/jsdelivr/, r => r.fulfill({ path: '../skins/node_modules/hls.js/dist/hls.min.js', contentType: 'text/javascript' }));
  const errs = []; pg.on('pageerror', e => errs.push(e.message));
  await pg.goto('http://localhost:8765/'); await pg.waitForTimeout(2000);
  await pg.evaluate(() => { S.focus = { cam: 'front_door' }; S.camTime.front_door = now() - 50 * 60000; S.playing = true; render(); Playback.sync(); ACT.fclip(); });
  await pg.waitForTimeout(4000);
  const c = await pg.context().newCDPSession(pg);
  const T = (type, pts) => c.send('Input.dispatchTouchEvent', { type, touchPoints: pts.map(([x, y], i) => ({ x, y, id: i })) });
  const log = [];
  const snap = async (k) => log.push([k, await pg.evaluate(() => hms(S.camTime.front_door))]);
  await snap('before');
  await T('touchStart', [[120, 700]]); for (let k = 1; k <= 8; k++) { await T("touchMove", [[120, 700 - k * 3]]); await pg.waitForTimeout(30); } await T('touchEnd', []);
  await snap('release');
  for (let i = 0; i < 6; i++) { await pg.waitForTimeout(800); await snap('t+' + (i + 1) * 0.8); }
  console.log(JSON.stringify(log), errs.slice(0, 3));
  console.log((await pg.evaluate(() => Dbg.lines ? Dbg.lines.slice(-25) : (localStorage.getItem('vhlog') || '').split('\n').slice(-25))).join('\n'));
  await b.close();
})();
