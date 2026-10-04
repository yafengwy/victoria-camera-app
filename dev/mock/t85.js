const { chromium } = require('playwright');
(async () => { const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' }); const pg = await b.newPage({ viewport: { width: 1100, height: 900 } });
await pg.goto('file://' + process.cwd() + '/../camapp/preview.html'); await pg.waitForTimeout(1500);
await pg.evaluate(() => { S.layout = 'grid'; S.expanded = 'front_door'; setWin(2 * HOUR); render(); document.getElementById('panel').scrollIntoView({ block: 'center' }); });
const box = await pg.evaluate(() => { const r = document.getElementById('track').getBoundingClientRect(); return { x: r.left + r.width / 2, y: r.top + r.height / 2 }; });
await pg.mouse.move(box.x, box.y);
for (let i = 0; i < 30; i++) { await pg.mouse.wheel(i % 4 === 3 ? 2 : 14, i % 4 === 3 ? 6.5 : 1.5); await pg.waitForTimeout(16); }
const a = await pg.evaluate(() => winLabel(S.win));
await pg.waitForTimeout(400);
for (let i = 0; i < 10; i++) { await pg.mouse.wheel(0.5, 6.5); await pg.waitForTimeout(16); }
const b2 = await pg.evaluate(() => winLabel(S.win));
console.log('after sideways swipe:', a, ' after vertical swipe:', b2); await b.close(); })();
