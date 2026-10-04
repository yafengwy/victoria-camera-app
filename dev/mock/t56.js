const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' }); const pg = await b.newPage({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });
  await pg.route(/jsdelivr/, r => r.fulfill({ path: '../skins/node_modules/hls.js/dist/hls.min.js', contentType: 'text/javascript' }));
  const errs = []; pg.on('pageerror', e => errs.push(e.message));
  await pg.goto('http://localhost:8765/'); await pg.waitForTimeout(2500);
  await pg.evaluate(() => { S.view = 'review'; S.playing = false; S.rv.t = now() - 60000; render(); paintReview(); });
  await pg.waitForTimeout(3000);
  const r = await pg.evaluate(() => [...document.querySelectorAll('.rvcam')].slice(0, 6).map(n => { const id = n.id.slice(3), w = RecMap.w[id], tm = n.querySelector('.tm'), s = n.querySelector('img').getAttribute('src') || '';
    return [id, tm.hidden ? '-' : tm.textContent, getComputedStyle(tm).fontSize, s.startsWith('data:') ? decodeURIComponent(s).replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').slice(0, 60) : s.slice(-60), w && w.segs ? w.segs.length : 'nomap', Data.source].join(' | '); }));
  console.log(r.join('\n'), errs);
  await pg.screenshot({ path: 'rvtm.png' });
  await b.close();
})();
