const test = require('node:test');
const assert = require('node:assert/strict');
const Core = require('../ff-v2-core.js');
const Renderer = require('../ff-v2-renderer.js');

test('visual clips are ordered bottom to top and exclude disabled/audio tracks', () => {
  const p = Core.createDefaultProject();
  const seq = p.sequences[0];
  const imageTrack = seq.tracks.find(t => t.type === 'graphic');
  const titleTrack = seq.tracks.find(t => t.type === 'title');
  const audioTrack = seq.tracks.find(t => t.type === 'voiceover');
  const a = Core.addGraphicClip(p, titleTrack.id, 'text', { text: 'TOP' }, 0, 40);
  const b = Core.addGraphicClip(p, imageTrack.id, 'shape', { shape: 'rect' }, 0, 40);
  audioTrack.clips.push({ id: 'audio', kind: 'generated', start_frame: 0, duration_frames: 40, enabled: true });
  assert.deepEqual(Core.getActiveVisualClips(p, 5).map(x => x.clip.id), [b.id, a.id]);
  assert.equal(Core.getActiveVisualClips(p, 50).length, 0);
});

test('keyframes interpolate arrays and numbers with easing', () => {
  const p = Core.createDefaultProject();
  const track = p.sequences[0].tracks.find(t => t.type === 'image');
  const clip = { id:'c', kind:'generated', start_frame:10, duration_frames:100, enabled:true, generator:{type:'shape',parameters:{}}, transform:{position:[0,0],scale:[1,1],rotation_degrees:0,opacity:1,anchor:[0.5,0.5]}, keyframes:[] };
  track.clips.push(clip);
  Core.setKeyframe(p, clip.id, 'position.x', 10, 0, 'linear');
  Core.setKeyframe(p, clip.id, 'position.x', 110, 100, 'linear');
  Core.setKeyframe(p, clip.id, 'opacity', 10, 0, 'ease_in_out');
  Core.setKeyframe(p, clip.id, 'opacity', 110, 1, 'ease_in_out');
  const atMid = Core.evaluateClipTransform(clip, 60);
  assert.equal(atMid.position[0], 50);
  assert.equal(atMid.opacity, 0.5);
});

test('Bezier keyframe easing produces deterministic intermediate values', () => {
  const clip = { start_frame:0, duration_frames:100, keyframes:[
    { property:'rotation_degrees', frame:0, value:0, interpolation:'bezier', bezier:[0.25,0.1,0.25,1] },
    { property:'rotation_degrees', frame:100, value:100, interpolation:'linear' }
  ]};
  const value = Core.evaluateKeyframes(clip, 'rotation_degrees', 50, 0);
  assert.ok(value > 50 && value < 100);
  assert.equal(value, Core.evaluateKeyframes(clip, 'rotation_degrees', 50, 0));
});

test('parent transforms propagate and parent cycles are rejected', () => {
  const p = Core.createDefaultProject();
  const track = p.sequences[0].tracks.find(t => t.type === 'graphic');
  const parent = Core.addGraphicClip(p, track.id, 'shape', { width:100,height:100 }, 0, 60);
  const child = Core.addGraphicClip(p, track.id, 'shape', { width:20,height:20 }, 0, 60);
  Core.setClipTransform(p, parent.id, { position:[100,40], scale:[2,2], rotation_degrees:90, opacity:0.5 });
  Core.setClipTransform(p, child.id, { position:[10,0] });
  Core.setClipParent(p, child.id, parent.id);
  const all = track.clips;
  const byId = new Map(all.map(item => [item.id,item]));
  const result = Renderer.resolveGlobalTransform(child, 10, byId);
  assert.equal(Math.round(result.position[0]), 100);
  assert.equal(Math.round(result.position[1]), 60);
  assert.equal(result.opacity, 0.5);
  assert.throws(() => Core.setClipParent(p, parent.id, child.id), /cycle/);
});

test('normalized crop, opacity and fit reject invalid transforms', () => {
  const p = Core.createDefaultProject();
  const track = p.sequences[0].tracks.find(t => t.type === 'image');
  const clip = { id:'c', kind:'generated', start_frame:0, duration_frames:40, enabled:true, generator:{type:'shape',parameters:{}}, transform:{} };
  track.clips.push(clip);
  Core.setClipTransform(p, clip.id, { crop:{x:0.1,y:0.1,width:0.8,height:0.8}, fit:'cover', opacity:0.4 });
  assert.equal(clip.transform.fit, 'cover');
  assert.throws(() => Core.setClipTransform(p, clip.id, { opacity:2 }), /between 0 and 1/);
  assert.throws(() => Core.setClipTransform(p, clip.id, { crop:{x:0.8,y:0.8,width:0.4,height:0.4} }), /normalized rectangle/);
});

test('shape and matte masks are stored with bounded parameters', () => {
  const p = Core.createDefaultProject();
  const track = p.sequences[0].tracks.find(t => t.type === 'graphic');
  const clip = Core.addGraphicClip(p, track.id, 'shape', { width:200,height:100 }, 0, 30);
  Core.setClipMask(p, clip.id, { type:'shape', shape:'ellipse', feather:8, bounds:{x:0.1,y:0.2,width:0.8,height:0.6} });
  assert.equal(clip.mask.shape, 'ellipse');
  assert.throws(() => Core.setClipMask(p, clip.id, { type:'shape', shape:'triangle' }), /rectangles and ellipses/);
});


test('procedural particle clips store reproducible seeds and supported presets', () => {
  const p = Core.createDefaultProject();
  const track = p.sequences[0].tracks.find(t => t.type === 'graphic');
  const clip = Core.addGraphicClip(p, track.id, 'particles', { preset:'embers', seed:4242, count:90 }, 12, 90);
  assert.equal(clip.generator.type, 'particles');
  assert.equal(clip.generator.parameters.seed, 4242);
  assert.equal(clip.generator.parameters.preset, 'embers');
  const a = Renderer.seededRandom(4242);
  const b = Renderer.seededRandom(4242);
  assert.deepEqual([a(),a(),a()], [b(),b(),b()]);
});

test('global post-processing pass stack supports ordering, presets and backend selection', () => {
  const p = Core.createDefaultProject();
  const first = Core.addPostProcessPass(p, 'glow', { intensity:0.4 });
  const second = Core.addPostProcessPass(p, 'vignette');
  assert.deepEqual(p.settings.post_processing.passes.map(pass=>pass.id),[first.id,second.id]);
  const preset = Core.applyPostProcessPreset(p,'cinematic');
  assert.equal(preset.length,3);
  assert.equal(p.settings.post_processing.passes.length,5);
  Core.setPostProcessRenderer(p,'canvas2d');
  assert.equal(p.settings.post_processing.renderer,'canvas2d');
  Core.removePostProcessPass(p,first.id);
  assert.equal(p.settings.post_processing.passes.some(pass=>pass.id===first.id),false);
  assert.throws(()=>Core.applyPostProcessPreset(p,'unknown'),/Unknown post-processing preset/);
});

test('clip effects can keyframe intensity in clip-local frame time', () => {
  const p = Core.createDefaultProject();
  const track = p.sequences[0].tracks.find(t=>t.type==='image');
  const clip = { id:'effect-clip',kind:'generated',start_frame:20,duration_frames:80,enabled:true,generator:{type:'shape',parameters:{}},effects:[] };
  track.clips.push(clip);
  const effect=Core.setClipEffect(p,clip.id,'glitch',{intensity:0.2,amount:0.8,seed:10});
  Core.setEffectParameterKeyframe(p,clip.id,effect.id,'intensity',20,0,'linear');
  Core.setEffectParameterKeyframe(p,clip.id,effect.id,'intensity',100,1,'linear');
  assert.equal(Core.evaluateEffectParameters(effect,20).intensity,0.25);
  assert.throws(()=>Core.setEffectParameterKeyframe(p,clip.id,effect.id,'unsupported',40,0.5),/Unsupported animated/);
});

test('clip transitions store direction and clamp duration to clip length', () => {
  const p = Core.createDefaultProject();
  const track = p.sequences[0].tracks.find(t=>t.type==='image');
  const clip = { id:'transition-clip',kind:'generated',start_frame:10,duration_frames:30,enabled:true,generator:{type:'shape',parameters:{}},transform:{position:[0,0],scale:[1,1],rotation_degrees:0,opacity:1,anchor:[0.5,0.5]},effects:[] };
  track.clips.push(clip);
  Core.setClipTransition(p,clip.id,'in',{type:'wipe',duration_frames:80,direction:'left'});
  assert.equal(clip.transition_in.duration_frames,30);
  const incoming=Renderer.transitionValues(clip,10,p.sequences[0],Core.evaluateClipTransform(clip,10));
  assert.equal(incoming.masks.length,1);
  assert.equal(incoming.masks[0].edge,'in');
  Core.setClipTransition(p,clip.id,'out',{type:'fade',duration_frames:10});
  const outgoing=Renderer.transitionValues(clip,39,p.sequences[0],Core.evaluateClipTransform(clip,39));
  assert.ok(outgoing.opacity<0.2);
  assert.throws(()=>Core.setClipTransition(p,clip.id,'middle',{type:'fade',duration_frames:5}),/edge/);
});

test('playback rate can be keyframed for speed ramps', () => {
  const p=Core.createDefaultProject();
  const track=p.sequences[0].tracks.find(t=>t.type==='video');
  const clip={id:'speed-clip',kind:'generated',start_frame:10,duration_frames:100,playback_rate:1,enabled:true,generator:{type:'shape',parameters:{}},keyframes:[]};
  track.clips.push(clip);
  Core.setKeyframe(p,clip.id,'playback_rate',10,1,'linear');
  Core.setKeyframe(p,clip.id,'playback_rate',110,2,'linear');
  assert.equal(Core.evaluateClipPlaybackRate(clip,60),1.5);
  Core.setClipPlaybackRate(p,clip.id,0.5);
  assert.equal(clip.playback_rate,0.5);
  assert.throws(()=>Core.setClipPlaybackRate(p,clip.id,10),/between 0.05× and 8×/);
});

test('WebGL capability check fails gracefully when no DOM is present', () => {
  const Shaders=require('../ff-v2-shaders.js');
  const result=Shaders.capabilities();
  assert.equal(result.webgl,false);
  assert.match(result.reason,/document is not defined/);
});


test('depth-of-field and swirl-warp are supported fallback effects', () => {
  const p = Core.createDefaultProject();
  assert.ok(Core.POST_PROCESS_TYPES.includes('depth-of-field'));
  assert.ok(Core.CLIP_EFFECT_TYPES.includes('depth-of-field'));
  assert.ok(Core.POST_PROCESS_TYPES.includes('custom'));
  const clip = { id:'swirl', kind:'generated', start_frame:0, duration_frames:40, enabled:true, effects:[] };
  const track = p.sequences[0].tracks.find(t=>t.type==='graphic');
  track.clips.push(clip);
  Core.setClipTransition(p,clip.id,'in',{type:'swirl_warp',duration_frames:20});
  const state=Renderer.transitionValues(clip,5,p.sequences[0],{position:[0,0],scale:[1,1],rotation_degrees:0,opacity:1,anchor:[0.5,0.5]});
  assert.equal(state.distortions[0].type,'swirl-warp');
});


test('speed-ramp source time integrates each prior frame rate', () => {
  const clip={start_frame:0,duration_frames:100,playback_rate:1,keyframes:[
    {property:'playback_rate',frame:0,value:1,interpolation:'linear'},
    {property:'playback_rate',frame:60,value:2,interpolation:'linear'}
  ]};
  const sourceFrames=Renderer.sourceFramesAtClipFrame(clip,60);
  assert.ok(sourceFrames>80 && sourceFrames<85,'Gradual 1× to 2× ramp should integrate the prior per-frame rates');
});
