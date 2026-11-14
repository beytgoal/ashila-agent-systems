#!/usr/bin/env node
/**
 * record_frames.js — deterministic frame-stepping recorder (PRIMARY path).
 * Steps the viewer through every frame (window.__renderOnce(t)), screenshots
 * each frame as JPEG, then assembles with ffmpeg into an mp4.
 * Usage: node record_frames.js [url] [outdir] [fps]
 * Env: CHROME_PATH to override the Chromium binary.
 *
 * Why frame-stepping instead of CCapture real-time capture:
 * headless SwiftShader renders slower than real time, so a real-time
 * recorder would drop frames. Frame-stepping is deterministic: every frame
 * is rendered fully before the screenshot, so motion is exact at any fps.
 */
const { chromium } = require('playwright-core');
const { execFileSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const URL = process.argv[2] || 'http://127.0.0.1:8901/index.html';
const OUTDIR = process.argv[3] || path.join(__dirname, '..', 'frames');
const FPS = parseInt(process.argv[4] || '30', 10);
const CHROME = process.env.CHROME_PATH ||
  '/home/user/.cache/ms-playwright/chromium-1248/chrome-linux64/chrome';

(async () => {
  fs.mkdirSync(OUTDIR, { recursive: true });
  const browser = await chromium.launch({
    executablePath: CHROME,
    args: ['--no-sandbox', '--enable-unsafe-swiftshader',
      '--use-angle=swiftshader', '--disable-dev-shm-usage'],
  });
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 } });
  page.on('pageerror', e => console.log('[pageerror]', String(e).slice(0, 300)));
  await page.goto(URL, { waitUntil: 'load', timeout: 60000 });
  await page.waitForFunction('window.__ready === true', null, { timeout: 60000 });
  const duration = await page.evaluate('window.__duration');
  const total = Math.round(duration * FPS);
  console.log(`duration=${duration}s fps=${FPS} frames=${total}`);
  const t0 = Date.now();
  let skipped = 0;
  for (let i = 0; i < total; i++) {
    const fp = path.join(OUTDIR, `f${String(i).padStart(5, '0')}.jpg`);
    if (fs.existsSync(fp)) { skipped++; continue; } // resume-safe: keep already-rendered frames
    const t = i / FPS;
    await page.evaluate(`window.__renderOnce(${t})`);
    await page.waitForFunction('window.__frameDone === true', null, { timeout: 20000 });
    // Screenshot timeout 120s + 1 retry: di bawah beban CPU berat (job divisi
    // lain), capture 1080x1920 via SwiftShader bisa >30s (default Playwright).
    try {
      await page.screenshot({ path: fp, type: 'jpeg', quality: 88, timeout: 120000 });
    } catch (e) {
      console.log(`frame ${i}: screenshot timeout, retry once...`);
      await page.evaluate(`window.__renderOnce(${t})`);
      await page.waitForFunction('window.__frameDone === true', null, { timeout: 20000 });
      await page.screenshot({ path: fp, type: 'jpeg', quality: 88, timeout: 120000 });
    }
    if ((i + 1) % 100 === 0 || i === total - 1) {
      const el = ((Date.now() - t0) / 1000).toFixed(0);
      console.log(`frame ${i + 1}/${total} (${el}s elapsed, ~${((Date.now() - t0) / (i + 1)).toFixed(0)}ms/frame)`);
    }
  }
  await browser.close();
  const mp4 = path.join(path.dirname(OUTDIR), 'ac-cycle-3d.mp4');
  console.log('assembling mp4 with ffmpeg...');
  execFileSync('ffmpeg', ['-y', '-framerate', String(FPS), '-i', path.join(OUTDIR, 'f%05d.jpg'),
    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18', '-movflags', '+faststart', mp4],
    { stdio: 'inherit' });
  console.log('DONE:', mp4);
})().catch(e => { console.error('RECORD FAILED:', e.message); process.exit(1); });
