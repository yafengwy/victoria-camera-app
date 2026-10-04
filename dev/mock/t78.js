const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' });
  for (const [w,h,name] of [[1440,900,'w1440'],[1100,800,'w1100'],[390,844,'phone']]) {
    const pg = await b.newPage({ viewport: { width: w, height: h } });
    const errs = []; pg.on('pageerror', e => errs.push(e.message));
    await pg.goto('file://' + process.cwd() + '/../camapp/preview.html'); await pg.waitForTimeout(1500);
    for (const id of ['driveway','california_room']) {
      await pg.evaluate(id => { S.layout = 'grid'; S.expanded = id; render(); }, id);
      await pg.waitForTimeout(500);
      const r = await pg.evaluate(() => { const p = document.getElementById('panel'); const g = p.parentNode; const cs = getComputedStyle(g).gridTemplateColumns.split(' ').length; const pr = p.getBoundingClientRect(), cr = document.querySelector('.cam.on').getBoundingClientRect(); return { cols: cs, pw: Math.round(pr.width), px: Math.round(pr.left), camx: Math.round(cr.left), below: Math.round(pr.top - cr.bottom) }; });
      console.log(name, id, JSON.stringify(r), errs);
      await pg.screenshot({ path: 'wide/impl_' + name + '_' + id + '.png' });
    }
    await pg.close();
  }
  await b.close();
})();
