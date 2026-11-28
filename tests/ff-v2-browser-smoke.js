#!/usr/bin/env node
/* Headless browser smoke test for the integrated FrameForge V2 workspace. */
const { spawn } = require('node:child_process');
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');

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

function makeTestGlb() {
  const positions = Buffer.alloc(36);
  [0,0,0, 1,0,0, 0,1,0].forEach((n,i)=>positions.writeFloatLE(n,i*4));
  const indices = Buffer.alloc(6);
  [0,1,2].forEach((n,i)=>indices.writeUInt16LE(n,i*2));
  const padding = Buffer.alloc(2);
  const times = Buffer.alloc(8); times.writeFloatLE(0,0); times.writeFloatLE(1,4);
  const translations = Buffer.alloc(24);
  [0,0,0, 0,0,0.5].forEach((n,i)=>translations.writeFloatLE(n,i*4));
  const binary = Buffer.concat([positions,indices,padding,times,translations]);
  const gltf = {
    asset:{version:'2.0',generator:'FrameForge smoke test'},
    scene:0,scenes:[{nodes:[0]}],nodes:[{name:'Triangle',mesh:0}],
    meshes:[{name:'Animated Triangle',primitives:[{attributes:{POSITION:0},indices:1}]}],
    buffers:[{byteLength:76}],
    bufferViews:[
      {buffer:0,byteOffset:0,byteLength:36,target:34962},
      {buffer:0,byteOffset:36,byteLength:6,target:34963},
      {buffer:0,byteOffset:44,byteLength:8},
      {buffer:0,byteOffset:52,byteLength:24}
    ],
    accessors:[
      {bufferView:0,componentType:5126,count:3,type:'VEC3',min:[0,0,0],max:[1,1,0]},
      {bufferView:1,componentType:5123,count:3,type:'SCALAR'},
      {bufferView:2,componentType:5126,count:2,type:'SCALAR',min:[0],max:[1]},
      {bufferView:3,componentType:5126,count:2,type:'VEC3'}
    ],
    animations:[{name:'Triangle bob',samplers:[{input:2,output:3,interpolation:'LINEAR'}],channels:[{sampler:0,target:{node:0,path:'translation'}}]}]
  };
  const json = Buffer.from(JSON.stringify(gltf));
  const jsonPad = Buffer.concat([json,Buffer.alloc((4-json.length%4)%4,0x20)]);
  const binPad = Buffer.concat([binary,Buffer.alloc((4-binary.length%4)%4)]);
  const header = Buffer.alloc(12); header.write('glTF',0);header.writeUInt32LE(2,4);
  const jsonHeader = Buffer.alloc(8);jsonHeader.writeUInt32LE(jsonPad.length,0);jsonHeader.writeUInt32LE(0x4e4f534a,4);
  const binHeader = Buffer.alloc(8);binHeader.writeUInt32LE(binPad.length,0);binHeader.writeUInt32LE(0x004e4942,4);
  const total = 12+8+jsonPad.length+8+binPad.length;header.writeUInt32LE(total,8);
  return Buffer.concat([header,jsonHeader,jsonPad,binHeader,binPad]);
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
    255, 70, 60, 128,
    255, 70, 60, 128,
    255, 70, 60, 128,
    255, 70, 60, 128
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

async function waitForCompositorRevision(page, previous) {
  await page.waitForFunction(value => Number(document.getElementById('ffv2CompositorStatus').dataset.renderId || 0) > value,
    previous, { timeout: 20000 });
}

async function main() {
  const server = spawn('python3', ['-m', 'http.server', String(PORT), '--bind', '127.0.0.1'], {
    stdio: 'ignore'
  });
  let browser;
  try {
    await waitForServer(server);
    browser = await chromium.launch({ headless: true, args: ['--enable-webgl','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'] });
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
    assert.ok(pixels.corner[3] === 0, 'Unoccupied compositor canvas must preserve transparent alpha');
    const translucentSourcePixel = await page.locator('#ffv2CompositorCanvas').evaluate(canvas => Array.from(canvas.getContext('2d').getImageData(300, 100, 1, 1).data));
    assert.ok(translucentSourcePixel[3] >= 126 && translucentSourcePixel[3] <= 130,
      'Imported semi-transparent PNG alpha must be retained through the layer compositor');

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

    // Seeded particle system should produce repeatable frames from the same project/frame.
    await page.locator('#ffv2ParticlePreset').selectOption('embers');
    await page.locator('#ffv2AddParticles').click();
    assert.equal(await page.locator('.ffv2-clip').count(), 5);
    const beforeParticleScrub = Number(await page.locator('#ffv2CompositorStatus').getAttribute('data-render-id') || 0);
    await page.locator('#ffv2Playhead').evaluate(el => {
      el.value = '24';
      el.dispatchEvent(new Event('input', { bubbles: true }));
    });
    await waitForCompositorRevision(page,beforeParticleScrub);
    const particleFrameA = await page.locator('#ffv2CompositorCanvas').evaluate(canvas => {
      const d=canvas.getContext('2d').getImageData(0,0,canvas.width,canvas.height).data;
      let hash=2166136261, visible=0;
      for(let i=0;i<d.length;i+=4){
        hash=Math.imul(hash^d[i],16777619);
        hash=Math.imul(hash^d[i+1],16777619);
        hash=Math.imul(hash^d[i+2],16777619);
        if(d[i+3]>0) visible++;
      }
      return {hash:hash>>>0,visible};
    });
    const renderRevision = Number(await page.locator('#ffv2CompositorStatus').getAttribute('data-render-id')||0);
    await page.locator('#ffv2RenderFrame').click();
    await page.waitForFunction(previous => Number(document.getElementById('ffv2CompositorStatus').dataset.renderId||0)>previous, renderRevision);
    const particleFrameB = await page.locator('#ffv2CompositorCanvas').evaluate(canvas => {
      const d=canvas.getContext('2d').getImageData(0,0,canvas.width,canvas.height).data;
      let hash=2166136261, visible=0;
      for(let i=0;i<d.length;i+=4){
        hash=Math.imul(hash^d[i],16777619);
        hash=Math.imul(hash^d[i+1],16777619);
        hash=Math.imul(hash^d[i+2],16777619);
        if(d[i+3]>0) visible++;
      }
      return {hash:hash>>>0,visible};
    });
    assert.equal(particleFrameA.hash,particleFrameB.hash,'Seeded particles must render deterministically at a fixed frame');
    assert.ok(particleFrameA.visible>0,'Particle and lower layers should contribute visible pixels');

    // Apply a clip effect and animate its intensity.
    await page.locator('#ffv2ClipEffectType').selectOption('glitch');
    await page.locator('#ffv2ClipEffectIntensity').fill('0.25');
    await page.locator('#ffv2AddClipEffect').click();
    await page.locator('#ffv2KeyframeEffect').click();
    await page.locator('#ffv2Playhead').evaluate(el => {
      el.value = '42';
      el.dispatchEvent(new Event('input', { bubbles: true }));
    });
    await page.locator('#ffv2ClipEffectIntensity').fill('0.9');
    await page.locator('#ffv2KeyframeEffect').click();
    assert.match(await page.locator('#ffv2ClipEffectInfo').textContent(), /2 effect keyframe/);

    // Set an incoming wipe and an outgoing fade on the particle clip.
    await page.locator('#ffv2TransitionType').selectOption('wipe');
    await page.locator('#ffv2TransitionDuration').fill('18');
    await page.locator('#ffv2TransitionDirection').selectOption('left');
    await page.locator('#ffv2ApplyTransitionIn').click();
    await page.locator('#ffv2TransitionType').selectOption('fade');
    await page.locator('#ffv2ApplyTransitionOut').click();
    assert.match(await page.locator('#ffv2TransitionInfo').textContent(), /In: wipe/);
    assert.match(await page.locator('#ffv2TransitionInfo').textContent(), /Out: fade/);

    // Playback-rate keyframes provide a speed-ramp primitive.
    await page.locator('#ffv2KeyframeProperty').selectOption('playback_rate');
    await page.locator('#ffv2KeyframeValue').fill('1.75');
    await page.locator('#ffv2SetKeyframe').click();

    // Named atmosphere preset and ordered Canvas2D fallback passes.
    await page.locator('#ffv2PostRenderer').selectOption('canvas2d');
    await page.locator('#ffv2PostPreset').selectOption('soft_glow');
    const beforePresetRender = Number(await page.locator('#ffv2CompositorStatus').getAttribute('data-render-id') || 0);
    await page.locator('#ffv2ApplyPostPreset').click();
    assert.ok(await page.locator('.ffv2-postfx-row').count()>=2);
    await waitForCompositorRevision(page,beforePresetRender);
    assert.match(await page.locator('#ffv2CompositorStatus').textContent(), /canvas2d/i);

    // Add a custom GLSL pass and confirm the browser either runs WebGL or reports fallback.
    await page.locator('#ffv2PostRenderer').selectOption('webgl');
    await page.locator('.ffv2-custom-shader summary').click();
    const beforeShaderRender = Number(await page.locator('#ffv2CompositorStatus').getAttribute('data-render-id') || 0);
    await page.locator('#ffv2AddCustomShader').click();
    await waitForCompositorRevision(page,beforeShaderRender);
    await page.waitForFunction(() => {
      const text=document.getElementById('ffv2CompositorStatus').textContent.toLowerCase();
      return text.includes('webgl') || text.includes('canvas2d') || text.includes('fell back');
    });
    assert.ok(await page.locator('.ffv2-postfx-row').count()>=3);

    // Import an actual animated glTF 2.0 model through the local, pinned Three.js runtime.
    assert.equal(await page.evaluate(() => window.THREE?.REVISION), '164');
    const glb = makeTestGlb();
    await page.locator('#ffv2FileInput').setInputFiles({
      name:'frameforge-animated-triangle.glb',
      mimeType:'model/gltf-binary',
      buffer:glb
    });
    await page.waitForFunction(() => document.querySelectorAll('.ffv2-asset-card').length===2, null, {timeout:20000});
    const modelMeta = await page.locator('.ffv2-asset-card').first().locator('.ffv2-asset-details').innerText();
    assert.match(modelMeta,/glTF Binary 2.0/);
    assert.match(modelMeta,/mesh/i);
    await page.locator('#ffv2TargetTrack').selectOption('');
    await page.locator('.ffv2-asset-card').first().locator('button.primary').click();
    await page.waitForFunction(() => document.querySelectorAll('.ffv2-clip').length===6);
    await page.locator('.ffv2-clip').last().click();
    await page.waitForFunction(() => !document.getElementById('ffv23DClipControls').classList.contains('hidden'));
    assert.equal(await page.locator('#ffv2ModelAnimation option').count(),2);
    assert.equal(await page.locator('#ffv2ModelAnimation').inputValue(),'');
    await page.locator('#ffv2ModelAnimation').selectOption('Triangle bob');
    await page.locator('#ffv2ModelAnimationSpeed').fill('1.25');
    await page.locator('#ffv2GroundContact').check();
    await page.locator('#ffv2AabbCollision').check();
    await page.locator('#ffv2Apply3DClip').click();
    assert.match(await page.locator('#ffv23DModelInfo').textContent(),/1 mesh/);
    await page.locator('#ffv2KeyframeProperty').selectOption('position3d.x');
    await page.locator('#ffv2KeyframeValue').fill('1.25');
    await page.locator('#ffv2SetKeyframe').click();
    assert.match(await page.locator('#ffv2SaveStatus').textContent(),/Keyframe stored at local frame/);
    assert.match(await page.locator('#ffv2KeyframeInfo').textContent(),/1 keyframe/);

    // Camera/lighting values are serializable, and the scene renderer reports its backend.
    await page.locator('#ffv2CameraX').fill('5');
    await page.locator('#ffv2AmbientIntensity').fill('0.6');
    await page.locator('#ffv2Apply3DScene').click();
    const threeRenderBefore = Number(await page.locator('#ffv2CompositorStatus').getAttribute('data-render-id')||0);
    await page.locator('#ffv2RenderFrame').click();
    await waitForCompositorRevision(page,threeRenderBefore);
    const threeStatus = await page.locator('#ffv2CompositorStatus').textContent();
    assert.match(threeStatus,/layer|3D/i);

    // The Blender bridge export is a portable ZIP containing the scene manifest, GLB and script.
    const downloadPromise = page.waitForEvent('download');
    await page.locator('#ffv2ExportBlender').click();
    const bridgeDownload = await downloadPromise;
    assert.match(bridgeDownload.suggestedFilename(),/blender-bridge\.zip$/);
    const bridgePath = '/tmp/frameforge-v2-blender-bridge-test.zip';
    await bridgeDownload.saveAs(bridgePath);
    const bridgeBytes = fs.readFileSync(bridgePath);
    assert.equal(bridgeBytes.readUInt32LE(0),0x04034b50,'Blender bridge should be a valid ZIP archive');
    assert.ok(bridgeBytes.length>500,'Blender bridge ZIP should contain the scene and model files');
    assert.ok(bridgeBytes.includes(Buffer.from('position3d.x')),'Bridge manifest should carry local 3D transform keyframes');
    assert.ok(bridgeBytes.includes(Buffer.from('Triangle bob')),'Bridge manifest should carry the selected glTF animation');

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
