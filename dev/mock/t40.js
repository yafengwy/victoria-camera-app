const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' }); const pg = await b.newPage({ viewport: { width: 390, height: 600 }, isMobile: true, hasTouch: true });
  await pg.route(/jsdelivr/, r => r.fulfill({ path: '../skins/node_modules/hls.js/dist/hls.min.js', contentType: 'text/javascript' }));
  const errs = []; pg.on('pageerror', e => errs.push(e.message));
  await pg.goto('http://localhost:8765/'); await pg.waitForTimeout(2500);
  await pg.evaluate(() => { const e = Data.events[0]; S.view = 'review'; S.rv.cols = 1; try { ACT.rvcols({ v: 1 }); } catch (x) {} S.rv.t = e.t + 2000; S.playing = false; render(); });
  await pg.waitForTimeout(500);
  const st = async () => pg.evaluate(() => { const n = document.getElementById('rvhint'); return n ? [n.hidden, n.textContent] : null; });
  console.log('top', await st());
  await pg.evaluate(() => { document.body.style.minHeight = '2000px'; window.scrollTo(0, 600); }); await pg.waitForTimeout(400);
  console.log('scrolled', await st(), await pg.evaluate(() => document.getElementById('rv-front_door').getBoundingClientRect().top));
  await pg.screenshot({ path: 'hint.png' });
  await pg.click('#rvhint').catch(e => console.log('click fail', e.message.slice(0, 80))); await pg.waitForTimeout(800);
  console.log('after tap', await st(), errs); await b.close();
})();
