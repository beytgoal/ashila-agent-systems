#!/usr/bin/env node
/**
 * probe.js — quick WebGL + render-speed probe for the 3D viewer.
 * Usage: node probe.js [url]
 * Exits 0 if WebGL renders and __ready becomes true; prints ms/frame.
 */
const { chromium } = require('playwright-core');

const URL = process.argv[2] || 'http://127.0.0.1:8901/index.html';
const CHROME = process.env.CHROME_PATH ||
  '/home/user/.cache/ms-playwright/chromium-1248/chrome-linux64/chrome';

(async () => {
  const browser = await chromium.launch({
    executablePath: CHROME,
    args: ['--no-sandbox', '--enable-unsafe-swiftshader',
      '--use-angle=swiftshader', '--disable-dev-shm-usage'],
  });
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 } });
  page.on('console', m => console.log('[page]', m.type(), m.text().slice(0, 300)));
  page.on('pageerror', e => console.log('[pageerror]', String(e).slice(0, 500)));
  const webgl = await page.evaluate(() => {
    const c = document.createElement('canvas');
    const gl = c.getContext('webgl2') || c.getContext('webgl');
    return gl ? gl.getParameter(gl.VERSION) + ' | ' + gl.getParameter(gl.RENDERER) : null;
  });
  console.log('WebGL:', webgl || 'NOT AVAILABLE');
  await page.goto(URL, { waitUntil: 'load', timeout: 60000 });
  try {
    await page.waitForFunction('window.__ready === true', null, { timeout: 30000 });
  } catch (e) {
    console.log('READY TIMEOUT — window.__ready never became true');
    await browser.close();
    process.exit(2);
  }
  console.log('READY ok, duration:', await page.evaluate('window.__duration'));
  // render 5 frames, measure
  const times = [];
  for (const t of [0, 6, 12, 21, 36]) {
    const t0 = Date.now();
    await page.evaluate(`window.__renderOnce(${t})`);
    await page.waitForFunction('window.__frameDone === true', null, { timeout: 15000 });
    times.push(Date.now() - t0);
  }
  console.log('render ms/frame:', times.join(', '), 'avg:', (times.reduce((a, b) => a + b, 0) / times.length).toFixed(0));
  await page.screenshot({ path: '/tmp/probe-t12.jpg', type: 'jpeg', quality: 85 });
  console.log('screenshot saved: /tmp/probe-t12.jpg');
  await browser.close();
})().catch(e => { console.error('PROBE FAILED:', e.message); process.exit(1); });
