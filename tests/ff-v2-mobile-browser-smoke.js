#!/usr/bin/env node
/* Mobile navigation smoke: verify each production area is reachable at phone width. */
const { spawn } = require('node:child_process');
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const PORT = 4177;
const BASE_URL = 'http://127.0.0.1:' + PORT;
async function waitForServer(child) {
  const started = Date.now();
  while (Date.now() - started < 15000) {
    if (child.exitCode !== null) throw new Error('Static test server exited unexpectedly.');
    try {
      const response = await fetch(BASE_URL);
      const ready = response.ok;
      await response.arrayBuffer();
      if (ready) return;
    } catch (_) {}
    await new Promise(resolve => setTimeout(resolve, 200));
  }
  throw new Error('Static test server did not start.');
}
async function main() {
  const server = spawn('python3', ['-m', 'http.server', String(PORT), '--bind', '127.0.0.1'], { stdio: 'ignore' });
  let browser;
  try {
    await waitForServer(server);
    browser = await chromium.launch({ headless:true, args:['--enable-webgl','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'] });
    const page = await browser.newPage({ viewport:{width:390,height:844}, isMobile:true, hasTouch:true, deviceScaleFactor:2 });
    const pageErrors = [];
    page.on('pageerror', error => pageErrors.push(error.message));
    await page.goto(BASE_URL, { waitUntil:'domcontentloaded' });
    await page.waitForFunction(() => {
      const node = document.getElementById('ffv2SaveStatus');
      return node && /Saved locally|New V2 project created|V2 project restored/.test(node.textContent);
    }, null, {timeout:20000});
    const nav = page.locator('#ffv2MobileNav');
    assert.equal(await nav.isVisible(), true, 'mobile nav must be visible at 390px');
    assert.equal(await nav.locator('button').count(), 5);
    const heights = await nav.locator('button').evaluateAll(items => items.map(item => Math.round(item.getBoundingClientRect().height)));
    assert.ok(heights.every(height => height >= 44), 'navigation targets must be at least 44px high');
    await page.locator('[data-mobile-target="assets"]').click();
    assert.equal(await page.locator('#ffv2AssetsPanel').isVisible(), true, 'asset panel should be reachable');
    await page.locator('[data-mobile-target="timeline"]').click();
    assert.equal(await page.locator('#ffv2TimelineSection').isVisible(), true, 'timeline should be reachable');
    await page.locator('[data-mobile-target="director"]').click();
    assert.equal(await page.locator('#ffv2DirectorPanel details').getAttribute('open'), '');
    await page.locator('[data-mobile-target="production"]').click();
    assert.equal(await page.locator('#ffv2ProductionPanel details').getAttribute('open'), '');
    await page.locator('[data-mobile-target="render"]').click();
    assert.equal(await page.locator('#ffv2RenderQueuePanel details').getAttribute('open'), '');
    assert.deepEqual(pageErrors, [], 'mobile navigation must not introduce browser errors');
    console.log('FRAMEFORGE_V2_MOBILE_BROWSER_SMOKE_PASS');
  } finally {
    if (browser) await browser.close();
    server.kill();
  }
}
main().catch(error => { console.error(error); process.exit(1); });
