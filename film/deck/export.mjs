import { chromium } from 'playwright';
import path from 'path';
import { fileURLToPath } from 'url';

const dir = path.dirname(fileURLToPath(import.meta.url));
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1280, height: 720 } });

// 1) slides -> PDF (each .slide is one 1280x720 page)
await page.goto('file://' + path.join(dir, 'slides.html'), { waitUntil: 'networkidle' });
await page.pdf({
  path: path.join(dir, 'granny_firewall_deck.pdf'),
  width: '1280px',
  height: '720px',
  printBackground: true,
  margin: { top: 0, bottom: 0, left: 0, right: 0 },
});
console.log('PDF exported');

// 2) cover -> 1920x1080 PNG (16:9)
await page.setViewportSize({ width: 1920, height: 1080 });
await page.goto('file://' + path.join(dir, 'cover.html'), { waitUntil: 'networkidle' });
await page.screenshot({
  path: path.join(dir, 'cover_16x9.png'),
  clip: { x: 0, y: 0, width: 1920, height: 1080 },
});
console.log('cover exported');

await browser.close();
