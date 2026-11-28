#!/usr/bin/env node
/* Render a 10-second FrameForge V2 anger-rise VFX demonstration from a licensed portrait. */
const { spawn } = require('node:child_process');
const fs = require('node:fs/promises');
const path = require('node:path');
const { chromium } = require('playwright');

const PORT = 4174;
const BASE_URL = 'http://127.0.0.1:' + PORT;
const FPS = 24;
const FRAMES = 240;
const OUT_DIR = path.resolve(process.env.OUTPUT_DIR || 'artifacts/vfx-test');
const PORTRAIT_PATH = path.resolve(process.env.PORTRAIT_PATH || 'assets/putin-portrait.png');

function run(command, args, options = {}) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, { stdio: 'inherit', ...options });
    child.once('error', reject);
    child.once('exit', code => code === 0 ? resolve() : reject(new Error(command + ' exited with code ' + code)));
  });
}

async function waitForServer() {
  const started = Date.now();
  while (Date.now() - started < 20000) {
    try {
      const response = await fetch(BASE_URL);
      if (response.ok) return;
    } catch (_) { /* server is still starting */ }
    await new Promise(resolve => setTimeout(resolve, 200));
  }
  throw new Error('FrameForge static server did not start.');
}

async function main() {
  await fs.access(PORTRAIT_PATH);
  await fs.mkdir(OUT_DIR, { recursive: true });
  const framesDir = path.join(OUT_DIR, 'frames');
  await fs.rm(framesDir, { recursive: true, force: true });
  await fs.mkdir(framesDir, { recursive: true });

  const server = spawn('python3', ['-m', 'http.server', String(PORT), '--bind', '127.0.0.1'], { stdio: 'ignore' });
  let browser;
  try {
    await waitForServer();
    browser = await chromium.launch({
      headless: true,
      args: ['--enable-webgl', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader']
    });
    const context = await browser.newContext({ viewport: { width: 1365, height: 980 }, deviceScaleFactor: 1 });
    const page = await context.newPage();
    const pageErrors = [];
    page.on('pageerror', error => pageErrors.push(error.message));
    await page.goto(BASE_URL, { waitUntil: 'domcontentloaded' });
    await page.waitForFunction(() => window.FFV2Studio && document.getElementById('ffv2SaveStatus') &&
      /Saved locally|New V2 project created|V2 project restored/.test(document.getElementById('ffv2SaveStatus').textContent),
      null, { timeout: 30000 });

    await page.locator('[data-panel="ffv2AssetsPanel"]').click();
    await page.locator('#ffv2FileInput').setInputFiles(PORTRAIT_PATH);
    await page.waitForFunction(() => document.querySelectorAll('.ffv2-asset-card').length === 1, null, { timeout: 20000 });
    await page.locator('.ffv2-asset-card button.primary').first().click();
    await page.waitForFunction(() => window.FFV2Studio.getSelectedClip() !== null, null, { timeout: 15000 });

    const clipData = await page.evaluate(() => {
      const project = window.FFV2Studio.getProject();
      const selected = window.FFV2Studio.getSelectedClip();
      if (!project || !selected?.clip) throw new Error('The imported portrait was not added to the V2 timeline.');
      const sequence = project.sequences[0];
      if (sequence.width !== 1280 || sequence.height !== 720) {
        sequence.width = 1280;
        sequence.height = 720;
      }
      sequence.fps = 24;
      selected.clip.start_frame = 0;
      selected.clip.duration_frames = 240;
      window.FFV2Studio.markDirty();
      window.FFV2Studio.refreshTimeline();
      return { clipId: selected.clip.id, width: sequence.width, height: sequence.height, fps: sequence.fps };
    });

    await page.locator('#ffv2ClipEffectType').selectOption('anger-rise');
    await page.locator('#ffv2ClipEffectIntensity').fill('0');
    await page.locator('#ffv2AngerTintStrength').fill('0.62');
    await page.locator('#ffv2AngerFlameHeight').fill('0.22');
    await page.locator('#ffv2AngerBurstThreshold').fill('0.985');
    await page.locator('#ffv2AddClipEffect').click();

    await page.evaluate(({ clipId }) => {
      const project = window.FFV2Studio.getProject();
      const selected = window.FFV2Studio.getSelectedClip();
      if (!selected?.clip || selected.clip.id !== clipId) throw new Error('The target VFX clip lost selection.');
      const effect = (selected.clip.effects || []).find(item => item.type === 'anger-rise');
      if (!effect) throw new Error('The FrameForge anger-rise effect was not attached.');
      const points = [
        [0, 0.00],
        [48, 0.14],
        [100, 0.38],
        [145, 0.72],
        [180, 1.00],
        [239, 1.00]
      ];
      for (const [frame, value] of points) {
        window.FFV2Core.setEffectParameterKeyframe(project, clipId, effect.id, 'intensity', frame, value, 'linear');
      }
      window.FFV2Studio.markDirty();
    }, { clipId: clipData.clipId });

    const canvas = page.locator('#ffv2CompositorCanvas');
    if (await canvas.count() !== 1) throw new Error('The V2 compositor canvas is missing.');

    for (let frame = 0; frame < FRAMES; frame++) {
      const render = await page.evaluate(async (frameNumber) => {
        const canvasElement = document.getElementById('ffv2CompositorCanvas');
        const studio = window.FFV2Studio;
        const project = studio.getProject();
        const result = await window.FFV2Renderer.composeFrame({
          project,
          frame: frameNumber,
          canvas: canvasElement,
          background: '#081322',
          resolveAsset: studio.resolveRenderAsset,
          resolveModelAsset: studio.resolve3DAsset,
          modelAssets: studio.getAssetRecords(),
          resolveModelDependency: studio.resolve3DDependency
        });
        if (result.warnings.length) {
          throw new Error('Frame ' + frameNumber + ' warning: ' + result.warnings[0].message);
        }
        return { frame: result.frame, drawn: result.drawn };
      }, frame);
      if (render.drawn < 1) throw new Error('Frame ' + frame + ' did not render the portrait layer.');
      const filename = path.join(framesDir, 'frame-' + String(frame).padStart(4, '0') + '.jpg');
      await canvas.screenshot({ path: filename, type: 'jpeg', quality: 88 });
      if (frame % 48 === 0) process.stdout.write('Rendered frame ' + frame + '/' + (FRAMES - 1) + '\n');
    }

    if (pageErrors.length) throw new Error('Browser errors: ' + pageErrors.join(' | '));
    await context.close();
    await browser.close();
    browser = null;

    const font = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf';
    const bold = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf';
    const filter = [
      'crop=1280:720:0:0',
      "drawtext=fontfile=" + bold + ":text='FRAMEFORGE VFX TEST':fontcolor=white:fontsize=34:x=(w-text_w)/2:y=26:box=1:boxcolor=0x081322cc:boxborderw=14",
      "drawtext=fontfile=" + font + ":text='SIMULATED DIGITAL EFFECT DEMONSTRATION':fontcolor=0xe3edf8:fontsize=17:x=(w-text_w)/2:y=h-74:box=1:boxcolor=0x081322cc:boxborderw=10",
      "drawtext=fontfile=" + font + ":text='Photo: Kremlin.ru | CC BY 4.0 | modified':fontcolor=0xe3edf8:fontsize=14:x=(w-text_w)/2:y=h-36:box=1:boxcolor=0x081322cc:boxborderw=8"
    ].join(',');
    await run('ffmpeg', [
      '-hide_banner', '-y',
      '-framerate', String(FPS),
      '-i', path.join(framesDir, 'frame-%04d.jpg'),
      '-vf', filter,
      '-frames:v', String(FRAMES),
      '-r', String(FPS),
      '-c:v', 'libx264', '-preset', 'medium', '-crf', '20',
      '-pix_fmt', 'yuv420p', '-movflags', '+faststart',
      '-an',
      path.join(OUT_DIR, 'frameforge-vfx-russia-president-10s.mp4')
    ]);

    await fs.writeFile(path.join(OUT_DIR, 'CREDITS.txt'),
      'FrameForge V2 — 10-second VFX test\n' +
      'Subject: Vladimir Putin, President of the Russian Federation (photograph dated 23 February 2024).\n' +
      'Photograph source: https://en.kremlin.ru/events/president/news/73529/photos\n' +
      'Photograph file: https://commons.wikimedia.org/wiki/File:Vladimir_Putin_portrait_(2024-02-23).png\n' +
      'Author/source: Presidential Executive Office of Russia / Kremlin.ru.\n' +
      'Licence: Creative Commons Attribution 4.0 International (CC BY 4.0): https://creativecommons.org/licenses/by/4.0/\n' +
      'Changes: Cropped/fit to the FrameForge 1280x720 composition and modified with FrameForge V2 anger-rise colour, flame, ember and burst effects; title and attribution overlays added.\n' +
      'This is a stylised VFX software test, not documentary footage and not an endorsement by the photograph source.\n'
    );

    await fs.rm(framesDir, { recursive: true, force: true });
    process.stdout.write('Wrote 10-second 1280x720 H.264 VFX test to ' +
      path.join(OUT_DIR, 'frameforge-vfx-russia-president-10s.mp4') + '\n');
  } finally {
    if (browser) await browser.close().catch(() => {});
    server.kill('SIGTERM');
  }
}

main().catch(error => {
  console.error('FRAMEFORGE_VFX_DEMO_FAIL');
  console.error(error);
  process.exitCode = 1;
});
