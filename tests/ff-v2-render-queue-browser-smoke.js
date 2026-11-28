#!/usr/bin/env node
/* Chromium regression: V2 frame queue pause/resume, chunk ZIP export and reload persistence. */
const { spawn } = require('node:child_process');
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const os = require('node:os');
const path = require('node:path');

const PORT = 4177;
const BASE_URL = 'http://127.0.0.1:' + PORT;

async function waitForServer(server) {
  const started = Date.now();
  while (Date.now() - started < 15000) {
    if (server.exitCode !== null) throw new Error('Render queue smoke server exited.');
    try {
      const response = await fetch(BASE_URL);
      if (response.ok) return;
    } catch (_) { /* Wait for local server startup. */ }
    await new Promise(resolve => setTimeout(resolve, 200));
  }
  throw new Error('Render queue smoke server did not start.');
}

async function main() {
  const server = spawn('python3', ['-m', 'http.server', String(PORT), '--bind', '127.0.0.1'], { stdio: 'ignore' });
  let browser;
  const temporary = await fs.mkdtemp(path.join(os.tmpdir(), 'frameforge-render-queue-'));
  try {
    await waitForServer(server);
    browser = await chromium.launch({ headless: true, args: ['--no-sandbox'] });
    const context = await browser.newContext({ acceptDownloads: true, viewport: { width: 1440, height: 1100 } });
    const page = await context.newPage();
    const pageErrors = [];
    page.on('pageerror', error => pageErrors.push(error.message));
    await page.goto(BASE_URL, { waitUntil: 'domcontentloaded' });
    await page.waitForFunction(() => window.FFV2Studio?.getProject?.() && window.FFV2RenderQueue);

    await page.evaluate(async () => {
      const project = window.FFV2Studio.getProject();
      const sequence = window.FFV2Core.getMainSequence(project);
      sequence.width = 320;
      sequence.height = 180;
      sequence.fps = 30;
      sequence.duration_frames = 24;
      const graphics = sequence.tracks.find(track => track.type === 'graphic') ||
        window.FFV2Core.addTrack(project, 'graphic', 'Smoke graphics');
      window.FFV2Core.addGraphicClip(project, graphics.id, 'svg', {
        svg: '<svg xmlns="http://www.w3.org/2000/svg" width="320" height="180" viewBox="0 0 320 180"><rect width="320" height="180" fill="#123456"/><circle cx="160" cy="90" r="52" fill="#55a7ff"/></svg>'
      }, 0, 24);
      window.FFV2Studio.markDirty();
      const store = window.FFV2Studio.renderStorage;
      const original = store.saveFrame.bind(store);
      let pauseOnce = false;
      store.saveFrame = async (...args) => {
        const key = await original(...args);
        if (!pauseOnce) {
          pauseOnce = true;
          window.FFV2RenderQueue.pause();
        }
        return key;
      };
    });

    await page.locator('#ffv2RenderQueueChunkSize').selectOption('12');
    await page.locator('#ffv2RenderQueueCreate').click();
    const queueState = await page.evaluate(() => ({
      job: window.FFV2RenderQueue.getCurrentJob(),
      status: document.getElementById('ffv2RenderQueueStatus')?.textContent,
      ready: Boolean(window.FFV2Studio.getProject()),
      buttonDisabled: document.getElementById('ffv2RenderQueueStart')?.disabled
    }));
    assert.ok(queueState.job?.id, 'Render job creation failed: ' + JSON.stringify(queueState));
    const jobId = queueState.job.id;
    await page.locator('#ffv2RenderQueueStart').click();
    await page.waitForFunction(async id => {
      const count = await window.FFV2Studio.renderStorage.countFrames(id);
      const job = await window.FFV2Studio.renderStorage.getJob(id);
      return count >= 1 && job?.status === 'paused';
    }, jobId, { timeout: 30000 });

    const pausedCount = await page.evaluate(id => window.FFV2Studio.renderStorage.countFrames(id), jobId);
    assert.equal(pausedCount, 1, 'Expected pause immediately after the first durable frame.');
    await page.locator('#ffv2RenderQueueStart').click();
    await page.waitForFunction(async id => {
      const job = await window.FFV2Studio.renderStorage.getJob(id);
      return job?.status === 'complete';
    }, jobId, { timeout: 30000 });

    const completed = await page.evaluate(async id => {
      const job = await window.FFV2Studio.renderStorage.getJob(id);
      const count = await window.FFV2Studio.renderStorage.countFrames(id);
      return {
        count,
        rendered_frames: job.rendered_frames,
        skipped_frames: job.skipped_frames,
        status: job.status,
        chunk_count: job.chunks
      };
    }, jobId);
    assert.equal(completed.status, 'complete');
    assert.equal(completed.count, 24);
    assert.equal(completed.rendered_frames, 24, 'Each unique frame should be rendered exactly once.');
    assert.ok(completed.skipped_frames >= 1, 'Resume should skip the already stored frame.');
    assert.equal(completed.chunk_count, 2);

    await page.locator('#ffv2RenderQueueChunk').selectOption('0');
    const downloadPromise = page.waitForEvent('download');
    await page.locator('#ffv2RenderQueueExport').click();
    const download = await downloadPromise;
    const archivePath = path.join(temporary, download.suggestedFilename());
    await download.saveAs(archivePath);
    const bytes = await fs.readFile(archivePath);
    assert.equal(bytes.readUInt32LE(0), 0x04034b50, 'Chunk ZIP should begin with a ZIP local-file header.');
    assert.ok(bytes.includes(Buffer.from('chunk-manifest.json')));
    assert.ok(bytes.includes(Buffer.from('frame_000000.png')));
    assert.ok(bytes.includes(Buffer.from('frame_000011.png')));

    await page.waitForTimeout(900);
    await page.reload({ waitUntil: 'domcontentloaded' });
    await page.waitForFunction(async id => {
      const job = await window.FFV2Studio?.renderStorage?.getJob(id);
      return Boolean(job);
    }, jobId, { timeout: 15000 });
    const persisted = await page.evaluate(async id => ({
      job: await window.FFV2Studio.renderStorage.getJob(id),
      frameCount: await window.FFV2Studio.renderStorage.countFrames(id)
    }), jobId);
    assert.equal(persisted.job.status, 'complete');
    assert.equal(persisted.frameCount, 24);
    assert.equal(persisted.job.width, 320);
    assert.equal(persisted.job.height, 180);
    assert.deepEqual(pageErrors, []);

    console.log('FRAMEFORGE_V2_RENDER_QUEUE_BROWSER_SMOKE_PASS');
    await context.close();
  } finally {
    if (browser) await browser.close();
    server.kill('SIGTERM');
    await fs.rm(temporary, { recursive: true, force: true });
  }
}

main().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
