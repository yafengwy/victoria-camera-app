const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' }); const pg = await b.newPage({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });
  await pg.route(/jsdelivr/, r => r.fulfill({ path: '../skins/node_modules/hls.js/dist/hls.min.js', contentType: 'text/javascript' }));
  const errs = []; pg.on('pageerror', e => errs.push(e.message));
  await pg.goto('http://localhost:8765/'); await pg.waitForTimeout(2500);
  const r = await pg.evaluate(() => {
    for (let i = 0; i < 8; i++) Data.cams.push(Object.assign({}, Data.cams[0], { id: 'x' + i, name: 'Cam ' + i }));
    const e = Data.events[4]; Data.events.push(Object.assign({}, e, { id: 'zz', cam: 'x5', label: 'Dog' }));
    S.view = 'review'; S.playing = false; S.rv.t = e.t + 2000; render(); paintReview();
    const order = () => [...document.querySelectorAll('.rvcam')].sort((a, b) => (+a.style.order) - (+b.style.order)).slice(0, 4).map(n => n.id + (n.classList.contains('feat') ? '*' : ''));
    const a = order(); S.rv.t = e.t - 3600e3; paintReview(); const b = order(); ACT.rvopen({ id: 'x3' }); const c = order();
    return [document.querySelector('.rvcams').className, a, b, c];
  });
  console.log(JSON.stringify(r), errs);
  await pg.evaluate(() => { S.rv.t = Data.events[4].t + 2000; S.rv.feat = null; S.rv.autoFeat = null; paintReview(); });
  await pg.screenshot({ path: 'rvbig.png' });
  await b.close();
})();
