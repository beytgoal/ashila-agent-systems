const { chromium } = require('playwright-core');
(async () => {
  const browser = await chromium.launch({ executablePath: '/home/user/.cache/ms-playwright/chromium-1248/chrome-linux64/chrome',
    args: ['--no-sandbox', '--enable-unsafe-swiftshader', '--use-angle=swiftshader', '--disable-dev-shm-usage'] });
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 } });
  page.on('pageerror', e => console.log('[pageerror]', String(e).slice(0, 300)));
  await page.goto('http://127.0.0.1:8901/index.html', { waitUntil: 'load', timeout: 60000 });
  await page.waitForFunction('window.__ready === true', null, { timeout: 30000 });
  for (const t of [3, 9, 15, 21, 27, 33, 40]) {
    await page.evaluate(`window.__renderOnce(${t})`);
    await page.waitForFunction('window.__frameDone === true', null, { timeout: 15000 });
    await page.screenshot({ path: `/tmp/scene-t${t}.jpg`, type: 'jpeg', quality: 82 });
    console.log('saved t=' + t);
  }
  await browser.close();
})().catch(e => { console.error('FAILED:', e.message); process.exit(1); });
