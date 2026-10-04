const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' }); const pg = await b.newPage({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });
  await pg.route(/jsdelivr/, r => r.fulfill({ path: '../skins/node_modules/hls.js/dist/hls.min.js', contentType: 'text/javascript' }));
  const errs = []; pg.on('pageerror', e => errs.push(e.message));
  await pg.goto('http://localhost:8765/'); await pg.waitForTimeout(2000);
  await pg.evaluate(() => { S.focus = { cam: 'front_door' }; S.camTime.front_door = now() - 10 * 60000; S.playing = false; render(); });
  await pg.waitForTimeout(500);
  const btn = await pg.evaluate(() => { const n = document.querySelector('#fsc [data-act]'); const r = n.getBoundingClientRect(); return { x: r.left + 20, y: r.top + r.height / 2, act: n.dataset.act }; });
  await pg.evaluate(() => { window._ev = []; ['touchstart','touchmove','touchend','touchcancel','click'].forEach(k => document.addEventListener(k, e => _ev.push(k + (e.touches ? e.touches.length : '') + (e.touches && e.touches[0] ? '@' + Math.round(e.touches[0].clientY) : '')), true)); });
  const c = await pg.context().newCDPSession(pg);
  const T = (type, pts) => c.send('Input.dispatchTouchEvent', { type, touchPoints: pts.map(([x, y], i) => ({ x, y, id: i })) });
  // drag that starts and ends on the same card (small 12px move, like a nudge)
  await T('touchStart', [[btn.x, btn.y]]); for (const dy of [10, 25, 40, 25, 5]) await T('touchMove', [[btn.x, btn.y - dy]]); await T('touchEnd', []);
  // synthetic click as iOS might send
  console.log(await pg.evaluate(() => _ev.join(' ')));
  console.log('TG', await pg.evaluate(() => JSON.stringify(TG) + ' ' + (Date.now() - TG.end)));
  await pg.evaluate(b => { const n = document.elementFromPoint(b.x, b.y); n.dispatchEvent(new MouseEvent('click', { bubbles: true, clientX: b.x, clientY: b.y })); }, btn);
  await pg.waitForTimeout(300);
  const after1 = await pg.evaluate(() => Dbg.a.filter(l => /tap alert|not a tap/.test(l)).slice(-3));
  // a real tap afterwards still works
  await pg.touchscreen.tap(btn.x, btn.y); await pg.waitForTimeout(300);
  const after2 = await pg.evaluate(() => Dbg.a.filter(l => /tap alert|not a tap/.test(l)).slice(-3));
  console.log(btn.act, JSON.stringify(after1), JSON.stringify(after2), errs); await b.close();
})();
