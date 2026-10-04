const { chromium } = require('playwright');
(async () => { const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' }); const pg = await b.newPage({ viewport: { width: 412, height: 900 } });
const errs=[]; pg.on('pageerror',e=>errs.push(e.message));
await pg.goto('file://' + process.cwd() + '/../camapp/preview.html'); await pg.waitForTimeout(1500);
const r = await pg.evaluate(async () => { S.rv.lay = 'top'; S.view = 'review'; render();
  const cams = rvCams(); const e = Data.events.find(e => e.interesting && cams.some(c => c.id === e.cam)); S.rv.t = e.t + 1000; render(); await new Promise(r => setTimeout(r, 300));
  /* fake: one camera has no recording, one an uninteresting alert */
  const others = cams.filter(c => !rvAt(c, S.rv.t));
  document.querySelector('#rv-' + others[0].id + ' img').setAttribute('src', NOREC);
  Data.events.push({ id: 'u1', cam: others[others.length - 1].id, t: S.rv.t - 500, end: S.rv.t + 5000, label: 'car', interesting: false, img: '' });
  rvLayout(S.rv.t);
  return [...document.querySelectorAll('.rvcam')].sort((a, b) => (+a.style.order || 0) - (+b.style.order || 0)).map(n => n.id.slice(3) + (n.classList.contains('feat') ? '*' : '') + ':' + n.style.order).concat(['hit=' + e.cam, 'norec=' + others[0].id, 'unint=' + others[others.length - 1].id, 'order=' + cams.map(c => c.id).join(',')]); });
console.log(r.join('  '), errs); await b.close(); })();
