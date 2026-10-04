const { chromium } = require('playwright');
(async () => { const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' });
for (const lay of ['grid', 'list']) { const pg = await b.newPage({ viewport: { width: 412, height: 900 } });
await pg.goto('file://' + process.cwd() + '/../camapp/preview.html'); await pg.waitForTimeout(1500);
const prep = () => pg.evaluate(l => { S.layout = l; S.expanded = 'front_door'; syncAll(now() - HOUR); render(); document.getElementById('livebtn').scrollIntoView({ block: 'center' }); }, lay);
const st = () => pg.evaluate(() => Data.cams.map(c => S.camTime[c.id] == null ? 'L' : 'p').join(''));
await prep(); await pg.click('#livebtn'); await pg.waitForTimeout(700); const one = await st();
await prep(); await pg.waitForTimeout(600); await pg.click('#livebtn'); await pg.waitForTimeout(120); await pg.click('#livebtn'); await pg.waitForTimeout(300); const two = await st();
console.log(lay, 'single:', one, ' double:', two); await pg.close(); }
await b.close(); })();
