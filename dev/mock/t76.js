const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' }); const pg = await b.newPage({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2 });
  await pg.route(/jsdelivr/, r => r.fulfill({ path: '../skins/node_modules/hls.js/dist/hls.min.js', contentType: 'text/javascript' }));
  const errs = []; pg.on('pageerror', e => errs.push(e.message));
  await pg.goto('http://localhost:8765/'); await pg.waitForTimeout(2000);
  await pg.evaluate(() => { S.layout = 'list'; S.expanded = 'front_door'; render(); document.getElementById('cam-front_door').scrollIntoView(); });
  await pg.waitForTimeout(800);
  console.log(await pg.evaluate(() => [document.querySelectorAll('#cam-front_door .chead button').length, document.querySelectorAll('.pctl .round').length, document.querySelectorAll('.sndb').length]), errs);
  await pg.click('#livebtn'); await pg.click('.chctl [data-act="boxes"]'); await pg.waitForTimeout(300);
  console.log(await pg.evaluate(() => [Box.on, document.getElementById('livebtn').className]));
  await pg.screenshot({ path: 'chead.png' }); await b.close();
})();
