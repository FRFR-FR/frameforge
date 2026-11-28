#!/usr/bin/env node
/* Chromium regression: V2 frame queue pause/resume, chunk ZIP export and reload persistence. */
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const os = require('node:os');
const path = require('node:path');
const http = require('node:http');

const PORT = 4177;
const BASE_URL = 'http://127.0.0.1:' + PORT;

function createStaticServer() {
  const root = path.resolve(__dirname, '..');
  const mime = {
    '.html': 'text/html; charset=utf-8',
    '.js': 'text/javascript; charset=utf-8',
    '.css': 'text/css; charset=utf-8',
    '.json': 'application/json; charset=utf-8',
    '.svg': 'image/svg+xml',
    '.wasm': 'application/wasm',
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.webp': 'image/webp'
  };
  return http.createServer(async (request, response) => {
    try {
      const url = new URL(request.url, BASE_URL);
      const requested = decodeURIComponent(url.pathname === '/' ? '/index.html' : url.pathname);
      const file = path.resolve(root, '.' + requested);
      if (file !== root && !file.startsWith(root + path.sep)) {
        response.writeHead(403);
        response.end('Forbidden');
        return;
      }
      const contents = await fs.readFile(file);
      response.writeHead(200, { 'Content-Type': mime[path.extname(file).toLowerCase()] || 'application/octet-stream' });
      response.end(contents);
    } catch (_) {
      response.writeHead(404);
      response.end('Not found');
    }
  });
}

async function waitForRenderState(page, jobId, predicate, timeoutMs = 30000) {
  const started = Date.now();
  let lastState = null;
  let lastError = '';
  while (Date.now() - started < timeoutMs) {
    try {
      lastState = await page.evaluate(async id => {
        const storage = window.FFV2Studio?.renderStorage;
        if (!storage) return null;
        const job = await storage.getJob(id);
        const count = await storage.countFrames(id);
        const frameZero = await storage.getFrame(id, 0);
        const frameRecords = await storage.getAllFrames(id);
        return {
          job,
          count,
          frameZero: frameZero ? {
            id: frameZero.id, job_id: frameZero.job_id, frame: frameZero.frame,
            blobSize: frameZero.blob?.size || 0
          } : null,
          frameRecords: frameRecords.map(item => ({
            id: item.id, job_id: item.job_id, frame: item.frame, blobSize: item.blob?.size || 0
          }))
        };
      }, jobId);
      if (lastState && predicate(lastState)) return lastState;
    } catch (error) {
      lastError = error.message;
    }
    await page.waitForTimeout(75);
  }
  throw new Error(
    'Timed out waiting for render queue state. Last state: ' +
    JSON.stringify(lastState, null, 2) + (lastError ? ' Last read error: ' + lastError : '')
  );
}

async function main() {
  const server = createStaticServer();
  let browser;
  const temporary = await fs.mkdtemp(path.join(os.tmpdir(), 'frameforge-render-queue-'));
  try {
    await new Promise((resolve, reject) => {
      server.once('error', reject);
      server.listen(PORT, '127.0.0.1', resolve);
    });
    browser = await chromium.launch({ headless: true, args: ['--no-sandbox'] });
    const context = await browser.newContext({ acceptDownloads: true, viewport: { width: 1440, height: 1100 } });
    const page = await context.newPage();
    const pageErrors = [];
    page.on('pageerror', error => pageErrors.push(error.message));
    await page.goto(BASE_URL, { waitUntil: 'domcontentloaded' });
    await page.waitForFunction(() => window.FFV2Studio?.getProject?.() &&
      window.FFV2RenderQueue?.isBound?.() === true &&
      document.getElementById('ffv2RenderQueueStatus')?.textContent.includes('Render queue ready'),
      null, { timeout: 20000 });

    await page.evaluate(async () => {
      const project = window.FFV2Studio.getProject();
      const sequence = window.FFV2Core.getMainSequence(project);
      sequence.width = 320;
      sequence.height = 180;
      sequence.fps = 30;
      sequence.duration_frames = 4;
      const graphics = sequence.tracks.find(track => track.type === 'graphic') ||
        window.FFV2Core.addTrack(project, 'graphic', 'Smoke graphics');
      window.FFV2Core.addGraphicClip(project, graphics.id, 'svg', {
        svg: '<svg xmlns="http://www.w3.org/2000/svg" width="320" height="180" viewBox="0 0 320 180"><rect width="320" height="180" fill="#123456"/><circle cx="160" cy="90" r="52" fill="#55a7ff"/></svg>'
      }, 0, 4);
      window.FFV2Studio.markDirty();
      const originalCompose = window.FFV2Renderer.composeFrame.bind(window.FFV2Renderer);
      window.FFV2Renderer.composeFrame = async options => {
        await new Promise(resolve => window.setTimeout(resolve, 250));
        return originalCompose(options);
      };
    });

    await page.locator('#ffv2RenderQueueChunkSize').selectOption('2');
    await page.locator('#ffv2RenderQueueCreate').click();
    await page.waitForFunction(() =>
      Boolean(window.FFV2RenderQueue.getCurrentJob()?.id) &&
      document.getElementById('ffv2RenderQueueStatus')?.textContent.includes('Render job created'),
      null, { timeout: 20000 }
    );
    const queueState = await page.evaluate(() => ({
      job: window.FFV2RenderQueue.getCurrentJob(),
      status: document.getElementById('ffv2RenderQueueStatus')?.textContent,
      ready: Boolean(window.FFV2Studio.getProject()),
      buttonDisabled: document.getElementById('ffv2RenderQueueStart')?.disabled
    }));
    assert.ok(queueState.job?.id, 'Render job creation failed: ' + JSON.stringify(queueState));
    const jobId = queueState.job.id;
    await page.locator('#ffv2RenderQueueStart').click();
    await waitForRenderState(page, jobId, state =>
      state.count >= 1 || state.job?.status === 'failed', 30000
    );
    await page.evaluate(() => window.FFV2RenderQueue.pause());
    const pausedState = await waitForRenderState(page, jobId, state =>
      state.job?.status === 'paused' || state.job?.status === 'failed' || state.job?.status === 'complete',
      30000
    );
    pausedState.statusText = await page.locator('#ffv2RenderQueueStatus').innerText();
    console.log('RENDER_QUEUE_PAUSED_STATE', JSON.stringify({
      count: pausedState.count,
      jobStatus: pausedState.job?.status,
      jobError: pausedState.job?.error,
      completedFrames: pausedState.job?.completed_frames,
      renderedFrames: pausedState.job?.rendered_frames,
      skippedFrames: pausedState.job?.skipped_frames,
      hasFrameZero: Boolean(pausedState.frameZero?.blobSize),
      frameRecordKeys: pausedState.frameRecords || [],
      statusText: pausedState.statusText
    }));
    assert.equal(pausedState.job?.status, 'paused', 'Render job failed or did not pause: ' + JSON.stringify(pausedState.job));
    assert.ok(pausedState.count >= 1 && pausedState.count <= 2, 'Pause should occur after one or two durable frames.');
    assert.equal(pausedState.job?.completed_frames, pausedState.count);
    assert.ok(pausedState.frameZero?.blobSize > 0, 'The first completed PNG must be durable before pausing.');
    await page.locator('#ffv2RenderQueueStart').click();
    const completedState = await waitForRenderState(page, jobId, state =>
      state.job?.status === 'complete' || state.job?.status === 'failed', 30000
    );
    const completed = {
      count: completedState.count,
      rendered_frames: completedState.job?.rendered_frames,
      skipped_frames: completedState.job?.skipped_frames,
      status: completedState.job?.status,
      chunk_count: completedState.job?.chunks,
      error: completedState.job?.error
    };
    assert.equal(completed.status, 'complete');
    assert.equal(completed.count, 4);
    assert.equal(completed.rendered_frames, 4, 'Each unique frame should be rendered exactly once.');
    assert.ok(completed.skipped_frames >= pausedState.count, 'Resume should skip every frame stored before pausing.');
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
    assert.ok(bytes.includes(Buffer.from('frame_000001.png')));

    await page.waitForTimeout(900);
    await page.reload({ waitUntil: 'domcontentloaded' });
    const persistedState = await waitForRenderState(page, jobId, state =>
      Boolean(state.job), 15000
    );
    const persisted = {
      job: persistedState.job,
      frameCount: persistedState.count
    };
    assert.equal(persisted.job.status, 'complete');
    assert.equal(persisted.frameCount, 4);
    assert.equal(persisted.job.width, 320);
    assert.equal(persisted.job.height, 180);
    assert.deepEqual(pageErrors, []);

    console.log('FRAMEFORGE_V2_RENDER_QUEUE_BROWSER_SMOKE_PASS');
    await context.close();
  } finally {
    if (browser) await browser.close();
    await new Promise(resolve => server.close(resolve));
    await fs.rm(temporary, { recursive: true, force: true });
  }
}

main().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
