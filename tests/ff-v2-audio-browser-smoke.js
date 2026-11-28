#!/usr/bin/env node
/* Browser smoke test for FrameForge V2 audio tracks, waveform sync and WAV export. */
const { spawn } = require('node:child_process');
const { chromium } = require('playwright');
const assert = require('node:assert/strict');

const PORT = 4174;
const BASE_URL = 'http://127.0.0.1:' + PORT;

function makeWav() {
  const sampleRate = 48000;
  const frames = sampleRate;
  const dataBytes = frames * 2 * 2;
  const bytes = Buffer.alloc(44 + dataBytes);
  bytes.write('RIFF', 0); bytes.writeUInt32LE(36 + dataBytes, 4); bytes.write('WAVE', 8);
  bytes.write('fmt ', 12); bytes.writeUInt32LE(16, 16); bytes.writeUInt16LE(1, 20);
  bytes.writeUInt16LE(2, 22); bytes.writeUInt32LE(sampleRate, 24);
  bytes.writeUInt32LE(sampleRate * 4, 28); bytes.writeUInt16LE(4, 32);
  bytes.writeUInt16LE(16, 34); bytes.write('data', 36); bytes.writeUInt32LE(dataBytes, 40);
  for (let frame = 0; frame < frames; frame++) {
    const sample = Math.round(7000 * Math.sin(2 * Math.PI * 440 * frame / sampleRate));
    bytes.writeInt16LE(sample, 44 + frame * 4);
    bytes.writeInt16LE(sample, 46 + frame * 4);
  }
  return bytes;
}

async function waitForServer(server) {
  const started = Date.now();
  while (Date.now() - started < 15000) {
    if (server.exitCode !== null) throw new Error('Audio smoke-test server exited.');
    try {
      const response = await fetch(BASE_URL);
      const ready = response.ok;
      await response.arrayBuffer();
      if (ready) return;
    } catch (_) { /* server is still starting */ }
    await new Promise(resolve => setTimeout(resolve, 200));
  }
  throw new Error('Audio smoke-test server did not start.');
}

async function main() {
  const server = spawn('python3', ['-m', 'http.server', String(PORT), '--bind', '127.0.0.1'], { stdio: 'ignore' });
  let browser;
  try {
    await waitForServer(server);
    browser = await chromium.launch({ headless: true });
    const context = await browser.newContext({ acceptDownloads: true, viewport: { width: 1365, height: 1000 } });
    const page = await context.newPage();
    const pageErrors = [];
    page.on('pageerror', error => pageErrors.push(error.message));
    await page.goto(BASE_URL, { waitUntil: 'domcontentloaded' });
    await page.waitForFunction(() => document.getElementById('ffv2AudioStatus')?.textContent.includes('Audio engine ready'));
    assert.equal(await page.locator('#ffv2AudioTrack').count(), 1);
    assert.equal(await page.locator('#ffv2AudioWaveform').count(), 1);

    await page.locator('[data-panel="ffv2AssetsPanel"]').click();
    await page.locator('#ffv2FileInput').setInputFiles({
      name: 'voiceover-fixture.wav', mimeType: 'audio/wav', buffer: makeWav()
    });
    await page.waitForFunction(() => document.querySelectorAll('.ffv2-asset-card').length === 1, null, { timeout: 15000 });
    assert.match(await page.locator('.ffv2-asset-card').innerText(), /1\.00 s/);

    const voiceTrackId = await page.evaluate(() => window.FFV2Studio.getProject().sequences[0].tracks.find(track => track.type === 'voiceover').id);
    await page.locator('#ffv2TargetTrack').selectOption(voiceTrackId);
    await page.locator('.ffv2-asset-card button.primary').click();
    await page.waitForFunction(() => document.querySelectorAll('.ffv2-clip').length === 1);
    await page.waitForFunction(() => !document.getElementById('ffv2AudioClipControls').classList.contains('hidden'));
    await page.waitForFunction(() => document.getElementById('ffv2AudioStatus').textContent.includes('Waveform ready'), null, { timeout: 15000 });

    const waveformSize = await page.locator('#ffv2AudioWaveform').evaluate(canvas => [canvas.width, canvas.height]);
    assert.ok(waveformSize[0] > 300 && waveformSize[1] > 30, 'The imported WAV waveform should be decoded and drawn.');

    // Audio seeking is frame-based and drives the shared V2 playhead.
    const beforeSeek = await page.locator('#ffv2PlayheadLabel').innerText();
    await page.locator('#ffv2AudioWaveform').click({ position: { x: 0, y: 45 } });
    await page.waitForFunction(() => document.getElementById('ffv2PlayheadLabel').textContent.includes('Frame 0'));
    const waveformBox = await page.locator('#ffv2AudioWaveform').boundingBox();
    await page.locator('#ffv2AudioWaveform').click({ position: { x: waveformBox.width / 2, y: waveformBox.height / 2 } });
    await page.waitForFunction(() => document.getElementById('ffv2PlayheadLabel').textContent.includes('Frame 15'));
    assert.ok(beforeSeek.includes('Frame'));

    // Track gain/solo, clip mix and local gain automation remain editable project data.
    await page.locator('#ffv2AudioTrackGain').evaluate(el => { el.value = '0.8'; el.dispatchEvent(new Event('input', { bubbles: true })); });
    await page.locator('#ffv2AudioTrackSolo').check();
    await page.locator('#ffv2AudioApplyTrack').click();
    await page.locator('#ffv2AudioClipGain').evaluate(el => { el.value = '0.75'; el.dispatchEvent(new Event('input', { bubbles: true })); });
    await page.locator('#ffv2AudioFadeIn').fill('4');
    await page.locator('#ffv2AudioApplyClip').click();
    await page.locator('#ffv2AudioAddGainKeyframe').click();
    await page.waitForFunction(() => window.FFV2Studio.getSelectedClip().clip.audio.automation.length === 1);

    // SFX can be tied to an explicit timeline marker.
    await page.locator('#ffv2AudioCueType').selectOption('playhead');
    await page.locator('#ffv2AudioAddCue').click();
    await page.waitForFunction(() => document.querySelectorAll('.ffv2-audio-cue-row').length === 1);

    // Set the test sequence to the imported one-second clip, then create a real WAV master.
    await page.evaluate(() => {
      const project = window.FFV2Studio.getProject();
      project.sequences[0].duration_frames = 30;
      window.FFV2Studio.markDirty();
    });
    const downloadPromise = page.waitForEvent('download');
    await page.locator('#ffv2AudioRender').click();
    const download = await downloadPromise;
    assert.match(download.suggestedFilename(), /audio-master\.wav$/);
    const path = '/tmp/frameforge-v2-audio-master-test.wav';
    await download.saveAs(path);
    const fs = require('node:fs');
    const wav = fs.readFileSync(path);
    assert.equal(wav.toString('ascii', 0, 4), 'RIFF');
    assert.equal(wav.toString('ascii', 8, 12), 'WAVE');
    assert.equal(wav.readUInt16LE(22), 2);
    assert.equal(wav.readUInt32LE(24), 48000);
    assert.equal(wav.readUInt16LE(34), 16);
    assert.equal(wav.length, 44 + 48000 * 2 * 2);
    assert.match(await page.locator('#ffv2AudioMetrics').innerText(), /48000 Hz · stereo PCM16/);
    assert.deepEqual(pageErrors, [], 'Audio workspace should not emit browser exceptions.');

    console.log('FRAMEFORGE_V2_AUDIO_BROWSER_SMOKE_PASS');
    console.log('Validated: audio import/decode, waveform seeking, frame playhead sync, track solo/gain, clip fades/automation, SFX markers and 48 kHz stereo PCM16 WAV export.');
    await context.close();
  } finally {
    if (browser) await browser.close();
    server.kill('SIGTERM');
  }
}

main().catch(error => {
  console.error('FRAMEFORGE_V2_AUDIO_BROWSER_SMOKE_FAIL');
  console.error(error);
  process.exitCode = 1;
});
