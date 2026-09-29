// Playwright take: record the Granny Firewall dashboard offscreen at 2560x1440.
// usage: node pw_take.mjs <replay|botfight> <out_dir> [duration_s]
import { chromium } from 'playwright';

const mode = process.argv[2] || 'replay';
const outDir = process.argv[3] || 'takes';
const dur = parseFloat(process.argv[4] || (mode === 'replay' ? 100 : 95));

const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({
  viewport: { width: 2560, height: 1440 },
  deviceScaleFactor: 1,
  recordVideo: { dir: outDir, size: { width: 2560, height: 1440 } },
});
const page = await ctx.newPage();
await page.goto('http://localhost:8008/', { waitUntil: 'networkidle' });
await page.waitForTimeout(2500);

if (mode === 'replay') {
  await page.click('button.mode-btn:has-text("replay"), button:has-text("REPLAY")');
  await page.waitForTimeout(1500);
  await page.click('button:has-text("Replay the scam call")');
} else {
  await page.click('button:has-text("BOTFIGHT")');
  await page.waitForTimeout(1500);
  await page.click('button:has-text("Start the duel")');
}
console.log(`${mode} started, recording ${dur}s`);
await page.waitForTimeout(dur * 1000);
await ctx.close();            // finalizes webm
await browser.close();
console.log('done');
