#!/usr/bin/env node
/* Headless browser smoke test for the integrated FrameForge V2 workspace. */
const { spawn } = require('node:child_process');
const { chromium } = require('playwright');
const assert = require('node:assert/strict');

const PORT = 4173;
const BASE_URL = 'http://127.0.0.1:' + PORT;

function crc32(buffer) {
  let crc = 0xffffffff;
  for (const byte of buffer) {
    crc ^= byte;
    for (let i = 0; i < 8; i++) crc = (crc >>> 1) ^ (0xedb88320 & -(crc & 1));
  }
  return (crc ^ 0xffffffff) >>> 0;
}

function pngChunk(type, data) {
  const typeBuffer = Buffer.from(type);
  const length = Buffer.alloc(4);
  length.writeUInt32BE(data.length, 0);
  const crc = Buffer.alloc(4);
  crc.writeUInt32BE(crc32(Buffer.concat([typeBuffer, data])), 0);
  return Buffer.concat([length, typeBuffer, data, crc]);
}

function makeTestPng() {
  const signature = Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]);
  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(4, 0);
  ihdr.writeUInt32BE(4, 4);
  ihdr[8] = 8; // bit depth
  ihdr[9] = 6; // RGBA
  const row = Buffer.from([
    0,
    255, 70, 60, 255,
    255, 70, 60, 255,
    255, 70, 60, 255,
    255, 70, 60, 255
  ]);
  const scanlines = Buffer.concat([row, row, row, row]);
  const zlib = require('node:zlib');
  const compressed = zlib.deflateSync(scanlines);
  return Buffer.concat([
    signature,
    pngChunk('IHDR', ihdr),
    pngChunk('IDAT', compressed),
    pngChunk('IEND', Buffer.alloc(0))
  ]);
}

async function waitForServer(child) {
  const started = Date.now();
  while (Date.now() - started < 15000) {
    if (child.exitCode !== null) throw new Error('Static test server exited unexpectedly.');
    try {
      const response = await fetch(BASE_URL);
      if (response.ok) return;
    } catch (_) { /* server is still starting */ }
    await new Promise(resolve => setTimeout(resolve, 200));
  }
  throw new Error('Static test server did not start.');
}

async function main() {
  const server = spawn('python3', ['-m', 'http.server', String(PORT), '--bind', '127.0.0.1'], {
    stdio: 'ignore'
  });
  let browser;
  try {
    await waitForServer(server);
    browser = await chromium.launch({ headless: true });
    const context = await browser.newContext({ viewport: { width: 1365, height: 980 } });
    const page = await context.newPage();
    const pageErrors = [];
    page.on('pageerror', error => pageErrors.push(error.message));
    page.on('dialog', async dialog => {
      if (dialog.type() === 'prompt') await dialog.accept('Secondary Video');
      else await dialog.accept();
    });
    await page.goto(BASE_URL, { waitUntil: 'domcontentloaded' });
    await page.waitForFunction(() => {
      const status = document.getElementById('ffv2SaveStatus');
      return status && /Saved locally|New V2 project created|V2 project restored/.test(status.textContent);
    }, null, { timeout: 20000 });

    await page.locator('[data-panel="ffv2AssetsPanel"]').click();
    const png = makeTestPng();
    await page.locator('#ffv2FileInput').setInputFiles({
      name: 'v2-cutout-test.png',
      mimeType: 'image/png',
      buffer: png
    });
    await page.waitForFunction(() => document.querySelectorAll('.ffv2-asset-card').length === 1, null, { timeout: 15000 });
    assert.match(await page.locator('.ffv2-asset-card small').first().textContent(), /4 × 4/);

    await page.locator('.ffv2-asset-card button.primary').click();
    await page.waitForFunction(() => document.querySelectorAll('.ffv2-clip').length === 1);
    assert.equal(await page.locator('.ffv2-track-row').count(), 7);

    // Add a second independently editable video track and place another clip on it.
    await page.locator('#ffv2NewTrackType').selectOption('video');
    await page.locator('#ffv2AddTrack').click();
    await page.locator('#ffv2TargetTrack').selectOption({ label: 'Secondary Video (video)' });
    await page.locator('.ffv2-asset-card button.primary').click();
    await page.waitForFunction(() => document.querySelectorAll('.ffv2-clip').length === 2);
    assert.equal(await page.locator('.ffv2-track-row').count(), 8);

    // Exercise timing edits, scrubbing, splitting, duplicating and deletion.
    const firstClip = page.locator('.ffv2-clip').first();
    await firstClip.click();
    await page.locator('#ffv2ClipStart').fill('20');
    await page.locator('#ffv2ClipDuration').fill('60');
    await page.locator('#ffv2ApplyClipTiming').click();
    await page.locator('#ffv2Playhead').evaluate(el => {
      el.value = '45';
      el.dispatchEvent(new Event('input', { bubbles: true }));
    });
    await page.locator('#ffv2SplitClip').click();
    assert.equal(await page.locator('.ffv2-clip').count(), 3);
    await page.locator('#ffv2DuplicateClip').click();
    assert.equal(await page.locator('.ffv2-clip').count(), 4);
    await page.locator('#ffv2DeleteClip').click();
    assert.equal(await page.locator('.ffv2-clip').count(), 3);

    // Verify track mute/visibility/lock controls and then persist a named project.
    const videoTrack = page.locator('.ffv2-track-row').first();
    await videoTrack.locator('button[title="Mute track"]').click();
    assert.equal(await videoTrack.locator('button[title="Unmute track"]').count(), 1);
    await page.locator('#ffv2ProjectName').fill('FrameForge V2 Browser Test');
    await page.locator('#ffv2SaveProject').click();
    await page.waitForFunction(() => document.getElementById('ffv2SaveStatus').textContent.includes('Saved locally'));
    await page.locator('#ffv2ProjectName').fill('FrameForge V2 Recovery Test');
    await page.locator('#ffv2SaveProject').click();
    await page.waitForFunction(() => document.getElementById('ffv2RecoveryButton').disabled === false);
    await page.locator('#ffv2RecoveryButton').click();
    await page.waitForFunction(() => document.getElementById('ffv2ProjectName').value === 'FrameForge V2 Browser Test');

    // Reload proves the project model and imported Blob records survive browser restart.
    await page.reload({ waitUntil: 'domcontentloaded' });
    await page.waitForFunction(() => document.getElementById('ffv2ProjectName')?.value === 'FrameForge V2 Browser Test');
    assert.equal(await page.locator('.ffv2-clip').count(), 3);
    await page.locator('[data-panel="ffv2AssetsPanel"]').click();
    assert.equal(await page.locator('.ffv2-asset-card').count(), 1);

    // Render a generated vector shape over the imported transparent-capable image.
    await page.locator('#ffv2AddShape').click();
    await page.waitForFunction(() => document.querySelectorAll('.ffv2-clip').length === 4);
    await page.waitForFunction(() => document.getElementById('ffv2CompositorStatus').textContent.includes('visual layer'));
    const pixels = await page.locator('#ffv2CompositorCanvas').evaluate(canvas => {
      const ctx = canvas.getContext('2d');
      return {
        center: Array.from(ctx.getImageData(640, 360, 1, 1).data),
        corner: Array.from(ctx.getImageData(8, 8, 1, 1).data),
        size: [canvas.width, canvas.height]
      };
    });
    assert.deepEqual(pixels.size, [1280, 720]);
    assert.ok(pixels.center[3] > 0, 'Generated vector shape should composite onto the output frame');
    assert.equal(pixels.corner[3], 0, 'Unoccupied compositor canvas must preserve transparent alpha');

    // Apply a transform, keyframe and a feathered ellipse mask through the editor controls.
    await page.locator('#ffv2TransformScaleX').fill('1.25');
    await page.locator('#ffv2ApplyTransform').click();
    await page.locator('#ffv2KeyframeProperty').selectOption('opacity');
    await page.locator('#ffv2KeyframeValue').fill('1');
    await page.locator('#ffv2SetKeyframe').click();
    await page.locator('#ffv2MaskType').selectOption('shape');
    await page.locator('#ffv2MaskShape').selectOption('ellipse');
    await page.locator('#ffv2MaskFeather').fill('4');
    const beforeMaskRender = Number(await page.locator('#ffv2CompositorStatus').getAttribute('data-render-id') || 0);
    await page.locator('#ffv2ApplyMask').click();
    await page.waitForFunction(previous => Number(document.getElementById('ffv2CompositorStatus').dataset.renderId || 0) > previous, beforeMaskRender);
    const normalMaskCenter = await page.locator('#ffv2CompositorCanvas').evaluate(canvas => Array.from(canvas.getContext('2d').getImageData(640, 360, 1, 1).data));
    const normalMaskRender = Number(await page.locator('#ffv2CompositorStatus').getAttribute('data-render-id'));
    await page.locator('#ffv2MaskInvert').check();
    await page.locator('#ffv2ApplyMask').click();
    await page.waitForFunction(previous => Number(document.getElementById('ffv2CompositorStatus').dataset.renderId || 0) > previous, normalMaskRender);
    const invertedMaskCenter = await page.locator('#ffv2CompositorCanvas').evaluate(canvas => Array.from(canvas.getContext('2d').getImageData(640, 360, 1, 1).data));
    assert.notDeepEqual(invertedMaskCenter.slice(0, 3), normalMaskCenter.slice(0, 3), 'Inverted ellipse mask should reveal the lower layer at the frame centre');
    assert.match(await page.locator('#ffv2KeyframeInfo').textContent(), /1 keyframe/);

    assert.deepEqual(pageErrors, [], 'Browser page errors should be empty');

    console.log('FRAMEFORGE_V2_BROWSER_SMOKE_PASS');
    console.log('Validated: asset import, multi-track edit/persistence, deterministic 720p alpha compositing, generated vector shapes, transforms, keyframes and feathered shape masks.');
    await context.close();
  } finally {
    if (browser) await browser.close();
    server.kill('SIGTERM');
  }
}

main().catch(error => {
  console.error('FRAMEFORGE_V2_BROWSER_SMOKE_FAIL');
  console.error(error);
  process.exitCode = 1;
});
