const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' }); const pg = await b.newPage({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });
  await pg.route(/jsdelivr/, r => r.fulfill({ path: '../skins/node_modules/hls.js/dist/hls.min.js', contentType: 'text/javascript' }));
  const errs = []; pg.on('pageerror', e => errs.push(e.message));
  await pg.goto('http://localhost:8765/#cam=front_door&t=' + (Date.now() - 600e3)); await pg.waitForTimeout(4000);
  const a = await pg.evaluate(() => camT('front_door')); await pg.waitForTimeout(4000); const c = await pg.evaluate(() => camT('front_door'));
  console.log('advanced s', ((c - a) / 1000).toFixed(1), errs); await b.close();
})();
