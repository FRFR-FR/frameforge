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
        await new Promise(resolve => window.setTimeout(resolve, 120));
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
    await page.waitForFunction(async id =>
      (await window.FFV2Studio.renderStorage.countFrames(id)) >= 1,
      jobId, { timeout: 30000 }
    );
    await page.evaluate(() => window.FFV2RenderQueue.pause());
    await page.waitForFunction(async id => {
      const job = await window.FFV2Studio.renderStorage.getJob(id);
      return job?.status === 'paused';
    }, jobId, { timeout: 30000 });

    const pausedState = await page.evaluate(async id => ({
      count: await window.FFV2Studio.renderStorage.countFrames(id),
      job: await window.FFV2Studio.renderStorage.getJob(id),
      frameZero: await window.FFV2Studio.renderStorage.getFrame(id, 0),
      statusText: document.getElementById('ffv2RenderQueueStatus')?.textContent
    }), jobId);
    console.log('RENDER_QUEUE_PAUSED_STATE', JSON.stringify({
      count: pausedState.count,
      jobStatus: pausedState.job?.status,
      completedFrames: pausedState.job?.completed_frames,
      renderedFrames: pausedState.job?.rendered_frames,
      skippedFrames: pausedState.job?.skipped_frames,
      hasFrameZero: Boolean(pausedState.frameZero?.blob?.size),
      statusText: pausedState.statusText
    }));
    assert.ok(pausedState.count >= 1 && pausedState.count <= 2, 'Pause should occur after one or two durable frames.');
    assert.equal(pausedState.job?.completed_frames, pausedState.count);
    assert.ok(pausedState.frameZero?.blob?.size, 'The first completed PNG must be durable before pausing.');
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
    await page.waitForFunction(async id => {
      const job = await window.FFV2Studio?.renderStorage?.getJob(id);
      return Boolean(job);
    }, jobId, { timeout: 15000 });
    const persisted = await page.evaluate(async id => ({
      job: await window.FFV2Studio.renderStorage.getJob(id),
      frameCount: await window.FFV2Studio.renderStorage.countFrames(id)
    }), jobId);
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
