const test = require('node:test');
const assert = require('node:assert/strict');
const Core = require('../ff-v2-core.js');
const Renderer = require('../ff-v2-renderer.js');

test('visual clips are ordered bottom to top and exclude disabled/audio tracks', () => {
  const p = Core.createDefaultProject();
  const seq = p.sequences[0];
  const imageTrack = seq.tracks.find(t => t.type === 'image');
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
