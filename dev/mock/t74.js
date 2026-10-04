const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' }); const pg = await b.newPage({ viewport: { width: 1440, height: 860 } });
  await pg.route(/jsdelivr/, r => r.fulfill({ path: '../skins/node_modules/hls.js/dist/hls.min.js', contentType: 'text/javascript' }));
  const errs = []; pg.on('pageerror', e => errs.push(e.message));
  await pg.goto('http://localhost:8765/'); await pg.waitForTimeout(2000);
  await pg.evaluate(() => { const ims = ['front_s.jpg','driveway_s.jpg','person_s.jpg','car_s.jpg','living_s.jpg']; Data.events.forEach((e, i) => { e.img = ims[i % 5]; }); S.view = 'events'; render(); });
  await pg.waitForTimeout(1500);
  const r1 = await pg.evaluate(() => [S.evSel, S.evPlay, document.querySelectorAll('.evrow').length, !!document.querySelector('#evplayer video')]);
  const id2 = await pg.evaluate(() => document.querySelectorAll('.evrow')[2].dataset.v);
  await pg.click('.evrow:nth-of-type(3)'); await pg.waitForTimeout(800);
  const r2 = await pg.evaluate(() => [S.evSel, S.evPlay, document.querySelector('.evrow.sel').dataset.v]);
  console.log(JSON.stringify([r1, id2, r2]), errs);
  await pg.screenshot({ path: 'evwide.png' });
  await pg.setViewportSize({ width: 390, height: 844 }); await pg.waitForTimeout(600);
  console.log('narrow', await pg.evaluate(() => [document.querySelectorAll('.evrow').length, document.querySelectorAll('.evcard').length]));
  await b.close();
})();
