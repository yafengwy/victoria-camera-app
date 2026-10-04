const { chromium } = require('playwright');
(async () => { const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' });
for (const [w,h] of [[393,852],[1440,860],[820,1180]]) { const pg = await b.newPage({ viewport: { width: w, height: h } }); const errs=[]; pg.on('pageerror',e=>errs.push(e.message));
await pg.goto('file://' + process.cwd() + '/../camapp/preview.html'); await pg.waitForTimeout(1500);
await pg.evaluate(() => { S.view = 'review'; S.rv.list = false; S.rv.f.unint = false; render(); });
await pg.waitForTimeout(400);
await pg.click('[data-act=rvlist]'); await pg.waitForTimeout(500);
const a = await pg.evaluate(() => { const l = document.getElementById('rvlist'); const items = [...l.querySelectorAll('.rvli')]; return { n: items.length, allInt: items.every(i => !i.classList.contains('un')), first: items[0] && items[0].innerText.replace(/\n/g, ' '), listH: Math.round(l.getBoundingClientRect().height), listW: Math.round(l.getBoundingClientRect().width) }; });
await pg.evaluate(() => { const it = document.querySelectorAll('#rvlist .rvli')[3]; it.scrollIntoView({ block: 'center' }); });
const tgt = await pg.evaluate(() => { const it = document.querySelectorAll('#rvlist .rvli')[3]; return { t: +it.dataset.t, id: it.dataset.id }; });
await pg.click('#rvlist .rvli:nth-of-type(4)').catch(()=>{}); await pg.evaluate(() => document.querySelectorAll('#rvlist .rvli')[3].click()); await pg.waitForTimeout(700);
const b2 = await pg.evaluate(tg => { const first = [...document.querySelectorAll('.rvcam')].sort((x, y) => (+x.style.order || 0) - (+y.style.order || 0))[0]; return { dt: Math.round((S.rv.t - tg.t) / 1000), firstCam: first.id.slice(3), want: tg.id, cur: document.querySelectorAll('#rvlist .rvli.cur').length }; }, tgt);
await pg.evaluate(() => { S.rv.f.unint = true; render(); }); await pg.waitForTimeout(300);
const c = await pg.evaluate(() => [...document.querySelectorAll('#rvlist .rvli')].some(i => i.classList.contains('un')));
console.log(w, JSON.stringify(a), JSON.stringify(b2), 'unint shown:', c, errs); await pg.screenshot({ path: 'wide/rvlist_' + w + '.png' }); await pg.close(); }
await b.close(); })();
