// Read-only browser benchmark. Keep the browser open while inspecting server RSS.
import { chromium } from '@playwright/test';

const url = process.argv[2] || 'http://127.0.0.1:8080';
const legacy = process.argv.includes('--legacy');
const browser = await chromium.launch();
const page = await browser.newPage({viewport:{width:1440,height:1000}});
let encodedBytes = 0;
const session = await page.context().newCDPSession(page);
await session.send('Network.enable');
session.on('Network.loadingFinished', event => {encodedBytes += event.encodedDataLength;});
const start = performance.now();
await page.goto(url, {waitUntil:'domcontentloaded'});
if (legacy) {
  await page.getByRole('textbox', {name:/Video Subject|视频主题|Tema do vídeo/}).first().waitFor({timeout:60000});
  await page.getByRole('button',{name:/^Generate Video$|^生成视频$|^Gerar Vídeo$/}).first().waitFor({timeout:60000});
} else {
  await page.getByRole('heading',{name:/Roteiro|Script|视频/}).first().waitFor({timeout:60000});
  await page.locator('textarea').first().waitFor();
}
const readyMs = Math.round(performance.now() - start);
const heap = await page.evaluate(() => performance.memory?.usedJSHeapSize ?? null);
console.log(JSON.stringify({url,legacy,readyMs,encodedBytes,jsHeapBytes:heap}));
// ponytail: one bounded observation window, not a continuous monitoring service.
await page.waitForTimeout(5000);
await browser.close();
