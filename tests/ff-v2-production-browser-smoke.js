#!/usr/bin/env node
/* Chromium integration smoke test for FrameForge V2 production steps 36–40. */
const { spawn } = require('node:child_process');
const { chromium } = require('playwright');
const assert = require('node:assert/strict');

const PORT = 4176;
const BASE_URL = 'http://127.0.0.1:' + PORT;

function makeWav() {
  const sampleRate = 48000;
  const frames = sampleRate;
  const dataBytes = frames * 2 * 2;
  const bytes = Buffer.alloc(44 + dataBytes);
  bytes.write('RIFF', 0);
  bytes.writeUInt32LE(36 + dataBytes, 4);
  bytes.write('WAVE', 8);
  bytes.write('fmt ', 12);
  bytes.writeUInt32LE(16, 16);
  bytes.writeUInt16LE(1, 20);
  bytes.writeUInt16LE(2, 22);
  bytes.writeUInt32LE(sampleRate, 24);
  bytes.writeUInt32LE(sampleRate * 4, 28);
  bytes.writeUInt16LE(4, 32);
  bytes.writeUInt16LE(16, 34);
  bytes.write('data', 36);
  bytes.writeUInt32LE(dataBytes, 40);
  for (let frame = 0; frame < frames; frame++) {
    const sample = Math.round(5000 * Math.sin(2 * Math.PI * 330 * frame / sampleRate));
    bytes.writeInt16LE(sample, 44 + frame * 4);
    bytes.writeInt16LE(sample, 46 + frame * 4);
  }
  return bytes;
}

async function waitForServer(server) {
  const started = Date.now();
  while (Date.now() - started < 15000) {
    if (server.exitCode !== null) throw new Error('Production smoke server exited.');
    try {
      const response = await fetch(BASE_URL);
      const ready = response.ok;
      await response.arrayBuffer();
      if (ready) return;
    } catch (_) { /* Wait for the local test server. */ }
    await new Promise(resolve => setTimeout(resolve, 200));
  }
  throw new Error('Production smoke server did not start.');
}

async function main() {
  const server = spawn('python3', ['-m', 'http.server', String(PORT), '--bind', '127.0.0.1'], { stdio: 'ignore' });
  let browser;
  try {
    await waitForServer(server);
    browser = await chromium.launch({ headless: true, args: ['--no-sandbox'] });
    const context = await browser.newContext({ acceptDownloads: true, viewport: { width: 1440, height: 1200 } });
    const page = await context.newPage();
    const pageErrors = [];
    page.on('pageerror', error => pageErrors.push(error.message));

    await page.goto(BASE_URL, { waitUntil: 'domcontentloaded' });
    await page.waitForFunction(() =>
      document.getElementById('ffv2ProductionStatus')?.textContent.includes('Production workflows loaded'),
      null, { timeout: 15000 }
    );

    // Step 36: generate a narration plan and apply a reusable recipe.
    await page.locator('#ffv2BriefTopic').fill('How a router forwards a request');
    await page.locator('#ffv2BriefNiche').selectOption('cybersecurity');
    await page.locator('#ffv2BriefDuration').fill('6');
    await page.locator('#ffv2BriefScript').fill(
      'A device sends a request to the router.\n\nThe router checks the destination address.\n\nThe router forwards the packet toward its next hop.'
    );
    await page.locator('#ffv2GenerateShotPlan').click();
    await page.waitForFunction(() =>
      window.FFV2Studio.getProject().shot_plan?.beats?.length === 3
    );
    await page.evaluate(() => window.FFV2ProductionUI.refresh());
    await page.locator('#ffv2RecipeChoice').selectOption('diagram');
    await page.locator('#ffv2RecipeDuration').fill('1.15');
    await page.locator('#ffv2ApplyRecipe').click();
    const recipeState = await page.evaluate(() => {
      const beat = window.FFV2Studio.getProject().shot_plan.beats[0];
      return { id: beat.shot_recipe?.id, duration: beat.recipe_duration_frames, start: beat.start_frame, span: beat.end_frame - beat.start_frame };
    });
    assert.equal(recipeState.id, 'diagram');
    assert.ok(recipeState.duration > 0);
    assert.ok(recipeState.span > 0);
    assert.equal(recipeState.duration, Math.round(recipeState.span * 1.15));

    // Step 38: create a real editable SVG clip from procedural parameters.
    await page.locator('#ffv2GraphicType').selectOption('flowchart');
    await page.locator('#ffv2GraphicTitle').fill('Router decision path');
    await page.locator('#ffv2GraphicSubtitle').fill('A simple illustrative routing sequence');
    await page.locator('#ffv2GraphicLabels').fill('Device\nRouter\nNext hop');
    await page.locator('#ffv2GraphicStart').fill('0');
    await page.locator('#ffv2GraphicDuration').fill('90');
    await page.locator('#ffv2CreateProceduralGraphic').click();
    const proceduralClip = await page.evaluate(() => {
      const project = window.FFV2Studio.getProject();
      return project.sequences[0].tracks.flatMap(track => track.clips)
        .find(clip => clip.generator?.type === 'svg');
    });
    assert.ok(proceduralClip, 'Expected an editable generated SVG clip.');

    // Step 39: import audio through the standard validated local importer.
    await page.locator('#ffv2AudioRole').selectOption('music');
    await page.locator('#ffv2ProductionProvider').fill('User supplied');
    await page.locator('#ffv2ProductionTitle').fill('Original test music bed');
    await page.locator('#ffv2ProductionCreator').fill('Project owner');
    await page.locator('#ffv2ProductionLicense').fill('CC0 1.0');
    await page.locator('#ffv2ProductionAttribution').fill('Original test audio by the project owner.');
    await page.locator('#ffv2ProductionImportFile').setInputFiles({
      name: 'production-smoke.wav',
      mimeType: 'audio/wav',
      buffer: makeWav()
    });
    await page.waitForFunction(() =>
      window.FFV2Studio.getProject().assets.some(asset => asset.media_type === 'audio')
    );
    await page.evaluate(() => window.FFV2ProductionUI.refresh());
    const audioId = await page.evaluate(() =>
      window.FFV2Studio.getProject().assets.find(asset => asset.media_type === 'audio').id
    );
    await page.locator('#ffv2AudioAsset').selectOption(audioId);
    await page.locator('#ffv2AudioLicense').fill('CC0 1.0');
    await page.locator('#ffv2AudioAttributionRequired').uncheck();
    await page.locator('#ffv2AudioAttribution').fill('Original test audio by the project owner.');
    await page.locator('#ffv2SaveAudioMetadata').click();
    await page.locator('#ffv2BuildAudioCredits').click();
    const audioGate = await page.locator('#ffv2AudioReport').innerText();
    assert.match(audioGate, /BLOCKED/);
    assert.match(audioGate, /not rights-approved/i);

    // Step 40: assemble approved visual inputs, keep missing source footage unfilled.
    const assemblyInputs = await page.evaluate(id => {
      const project = window.FFV2Studio.getProject();
      const beats = project.shot_plan.beats;
      beats[0].media_mix = ['procedural_2d'];
      beats[0].visual_role = 'illustration';
      beats[0].asset_ids = [id];
      beats[1].media_mix = ['source_footage'];
      beats[1].visual_role = 'illustration';
      beats[1].evidence_requirement = 'actual_footage';
      beats[1].asset_ids = [];
      beats[2].media_mix = ['procedural_2d'];
      beats[2].visual_role = 'illustration';
      beats[2].asset_ids = [];
      return true;
    }, audioId);
    assert.equal(assemblyInputs, true);
    await page.locator('#ffv2AssembleShotPlan').click();
    const assembled = await page.evaluate(() => {
      const project = window.FFV2Studio.getProject();
      const tracks = project.sequences[0].tracks;
      return {
        report: project.extensions.production_orchestration,
        audio: tracks.find(track => track.type === 'music')?.clips?.length || 0,
        graphics: tracks.find(track => track.type === 'graphic')?.clips?.length || 0,
        errors: window.FFV2Core.validateProject(project)
      };
    });
    assert.ok(assembled.report);
    assert.equal(assembled.report.review_required_before_render, true);
    assert.equal(assembled.report.unfilled_beats.length, 1);
    assert.ok(assembled.report.created_clip_ids.length >= 2);
    assert.ok(assembled.audio >= 1, 'Expected an editable music-track clip.');
    assert.ok(assembled.graphics >= 2, 'Expected generated SVG graphic clips.');
    assert.deepEqual(assembled.errors, []);

    await page.waitForTimeout(1200);
    await page.reload({ waitUntil: 'domcontentloaded' });
    await page.waitForFunction(() =>
      document.getElementById('ffv2ProductionStatus')?.textContent.includes('Production workflows loaded')
    );
    const persisted = await page.evaluate(() => {
      const project = window.FFV2Studio.getProject();
      return {
        orchestration: project.extensions?.production_orchestration?.version,
        audio: project.assets.find(asset => asset.media_type === 'audio')?.rights?.license_name,
        recipe: project.shot_plan?.beats?.[0]?.shot_recipe?.id,
        unfilled: project.extensions?.production_orchestration?.unfilled_beats?.length
      };
    });
    assert.equal(persisted.orchestration, 1);
    assert.equal(persisted.audio, 'CC0 1.0');
    assert.equal(persisted.recipe, 'diagram');
    assert.equal(persisted.unfilled, 1);
    assert.deepEqual(pageErrors, []);

    console.log('FRAMEFORGE_V2_PRODUCTION_BROWSER_SMOKE_PASS');
    await context.close();
  } finally {
    if (browser) await browser.close();
    server.kill('SIGTERM');
  }
}

main().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
