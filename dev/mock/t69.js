const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' }); const pg = await b.newPage({ viewport: { width: 390, height: 844 }, acceptDownloads: true });
  await pg.route(/jsdelivr/, r => r.fulfill({ path: '../skins/node_modules/hls.js/dist/hls.min.js', contentType: 'text/javascript' }));
  const errs = []; pg.on('pageerror', e => errs.push(e.message));
  await pg.goto('http://localhost:8765/'); await pg.waitForTimeout(2000);
  await pg.evaluate(() => { S.focus = { cam: 'front_door' }; S.camTime.front_door = now() - 40 * 60000; S.playing = false; render(); });
  await pg.click('[data-act="fclip"]');
  await pg.click('[data-act="fclipdl"]'); const t1 = await pg.evaluate(() => document.getElementById('toast').textContent);
  await pg.evaluate(() => { S.camTime.front_door += 12 * 60000; }); await pg.evaluate(() => ACT.fclipmark({ v: 'b' }));
  const st = await pg.evaluate(() => [(S.fclip.b - S.fclip.a) / 60000, document.querySelectorAll('.fcmk').length, !!document.querySelector('.fcband')]);
  const [dl] = await Promise.all([pg.waitForEvent('download', { timeout: 8000 }), pg.evaluate(() => ACT.fclipdl())]);
  console.log(JSON.stringify([t1, st, dl.suggestedFilename()]), errs);
  await pg.evaluate(() => { const f = document.getElementById('fsc'); const m = document.querySelector('.fcmk'); f.scrollTop = Math.max(0, m.offsetTop - 200); });
  // show the progress bar look
  await pg.evaluate(() => { SaveBar.show('Preparing Video', 42); });
  await pg.screenshot({ path: 'fclip2.png' }); await b.close();
})();
