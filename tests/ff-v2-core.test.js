const test = require('node:test');
const assert = require('node:assert/strict');
const Core = require('../ff-v2-core.js');

function makeAsset(id = 'asset-test', mediaType = 'image') {
  return {
    id,
    label: 'Test asset',
    file_name: 'test.png',
    media_type: mediaType,
    metadata: { size_bytes: 4 },
    provenance: { source_type: 'user_supplied', notes: 'Test fixture' },
    rights: { status: 'pending', attribution_required: false },
    tags: []
  };
}

function setupProject() {
  const project = Core.createDefaultProject('Core tests', '2026-11-28T00:00:00.000Z');
  Core.addAsset(project, makeAsset());
  return project;
}

test('creates a valid version 2 default project', () => {
  const project = Core.createDefaultProject('New film', '2026-11-28T00:00:00.000Z');
  assert.equal(project.format, 'frameforge-project');
  assert.equal(project.schema_version, 2);
  assert.equal(Core.validateProject(project).length, 0);
  assert.equal(project.sequences[0].tracks.length, 6);
});

test('creates additional tracks with stable ordering and supported types', () => {
  const project = Core.createDefaultProject();
  const track = Core.addTrack(project, 'scene3d', '3D Scene');
  assert.equal(track.type, 'scene3d');
  assert.equal(track.order, 6);
  assert.equal(Core.validateProject(project).length, 0);
  assert.throws(() => Core.addTrack(project, 'unsupported', 'Bad'), /Unsupported track type/);
});

test('maps imported media to useful default track types', () => {
  assert.equal(Core.trackForAssetType('image'), 'image');
  assert.equal(Core.trackForAssetType('graphic'), 'graphic');
  assert.equal(Core.trackForAssetType('video'), 'video');
  assert.equal(Core.trackForAssetType('audio'), 'sfx');
  assert.equal(Core.trackForAssetType('model3d'), 'scene3d');
});

test('adds an asset clip and extends sequence duration when needed', () => {
  const project = setupProject();
  const track = project.sequences[0].tracks.find(item => item.type === 'image');
  const clip = Core.addAssetClip(project, 'asset-test', track.id, 890, 80);
  assert.equal(clip.start_frame, 890);
  assert.equal(clip.duration_frames, 80);
  assert.equal(project.sequences[0].duration_frames, 970);
  assert.equal(Core.validateProject(project).length, 0);
});

test('snaps clip movement to the supplied frame grid', () => {
  const project = setupProject();
  const track = project.sequences[0].tracks.find(item => item.type === 'image');
  const clip = Core.addAssetClip(project, 'asset-test', track.id, 0, 90);
  Core.moveClip(project, clip.id, 47, 30);
  assert.equal(clip.start_frame, 60);
  Core.moveClip(project, clip.id, 47, 1);
  assert.equal(clip.start_frame, 47);
});

test('trims clip start and duration without losing its asset reference', () => {
  const project = setupProject();
  const track = project.sequences[0].tracks.find(item => item.type === 'image');
  const clip = Core.addAssetClip(project, 'asset-test', track.id, 0, 120);
  Core.trimClip(project, clip.id, 25, 45);
  assert.equal(clip.start_frame, 25);
  assert.equal(clip.duration_frames, 45);
  assert.equal(clip.asset_id, 'asset-test');
});

test('splits a clip at an interior playhead frame', () => {
  const project = setupProject();
  const track = project.sequences[0].tracks.find(item => item.type === 'image');
  const clip = Core.addAssetClip(project, 'asset-test', track.id, 10, 90);
  const right = Core.splitClip(project, clip.id, 45);
  assert.equal(clip.duration_frames, 35);
  assert.equal(right.start_frame, 45);
  assert.equal(right.duration_frames, 55);
  assert.equal(right.source_in_frame, 35);
  assert.equal(Core.validateProject(project).length, 0);
});

test('refuses to split outside a clip interior', () => {
  const project = setupProject();
  const track = project.sequences[0].tracks.find(item => item.type === 'image');
  const clip = Core.addAssetClip(project, 'asset-test', track.id, 10, 90);
  assert.throws(() => Core.splitClip(project, clip.id, 10), /inside the clip/);
  assert.throws(() => Core.splitClip(project, clip.id, 100), /inside the clip/);
});

test('duplicates a selected clip after the original', () => {
  const project = setupProject();
  const track = project.sequences[0].tracks.find(item => item.type === 'image');
  const original = Core.addAssetClip(project, 'asset-test', track.id, 0, 30);
  const duplicate = Core.duplicateClip(project, original.id);
  assert.notEqual(duplicate.id, original.id);
  assert.equal(duplicate.start_frame, 30);
  assert.equal(duplicate.asset_id, original.asset_id);
  assert.equal(Core.validateProject(project).length, 0);
});

test('deletes clips while preserving the track', () => {
  const project = setupProject();
  const track = project.sequences[0].tracks.find(item => item.type === 'image');
  const clip = Core.addAssetClip(project, 'asset-test', track.id, 0, 30);
  Core.deleteClip(project, clip.id);
  assert.equal(track.clips.length, 0);
  assert.equal(Core.validateProject(project).length, 0);
});

test('rejects edits on a locked track', () => {
  const project = setupProject();
  const track = project.sequences[0].tracks.find(item => item.type === 'image');
  const clip = Core.addAssetClip(project, 'asset-test', track.id, 0, 30);
  track.locked = true;
  assert.throws(() => Core.moveClip(project, clip.id, 60, 1), /locked/);
  assert.throws(() => Core.trimClip(project, clip.id, 10, 20), /locked/);
  assert.throws(() => Core.deleteClip(project, clip.id), /locked/);
});

test('rejects dangling asset references and malformed sequences', () => {
  const project = setupProject();
  const track = project.sequences[0].tracks.find(item => item.type === 'image');
  const clip = Core.addAssetClip(project, 'asset-test', track.id, 0, 30);
  clip.asset_id = 'missing';
  assert.ok(Core.validateProject(project).some(error => error.includes('missing asset')));
  const malformed = Core.clone(project);
  malformed.sequences[0].tracks = null;
  assert.ok(Core.validateProject(malformed).some(error => error.includes('tracks must be an array')));
});

test('rejects clips that fall outside the sequence duration', () => {
  const project = setupProject();
  const track = project.sequences[0].tracks.find(item => item.type === 'image');
  const clip = Core.addAssetClip(project, 'asset-test', track.id, 0, 30);
  project.sequences[0].duration_frames = 20;
  assert.ok(Core.validateProject(project).some(error => error.includes('exceeds sequence duration')));
});

test('classifies supported image, video, audio and 3D formats', () => {
  const cases = [
    ['cutout.png', 'image/png', 'image'],
    ['scene.mp4', 'video/mp4', 'video'],
    ['music.mp3', 'audio/mpeg', 'audio'],
    ['model.glb', 'model/gltf-binary', 'model3d'],
    ['vector.svg', 'image/svg+xml', 'image']
  ];
  for (const [name, type, expected] of cases) {
    assert.equal(Core.classifyFile({ name, type, size: 100 }).category, expected);
  }
});

test('rejects unsupported file extensions, type mismatches and oversized files', () => {
  assert.throws(() => Core.classifyFile({ name: 'archive.zip', type: 'application/zip', size: 100 }), /Unsupported file type/);
  assert.throws(() => Core.classifyFile({ name: 'image.png', type: 'audio/mpeg', size: 100 }), /do not match/);
  assert.throws(() => Core.classifyFile({ name: 'huge.mp4', type: 'video/mp4', size: Core.MAX_FILE_BYTES + 1 }), /250 MB/);
});

test('verifies media signatures and rejects malformed GLB headers', () => {
  const png = new Uint8Array([0x89,0x50,0x4e,0x47,0x0d,0x0a,0x1a,0x0a]);
  assert.equal(Core.verifySignature('png', png), '');
  assert.match(Core.verifySignature('png', new Uint8Array([0,1,2,3])), /PNG signature/);
  assert.match(Core.verifySignature('glb', new Uint8Array([0x67,0x6c,0x54,0x46])), /GLB header/);
});

test('rejects active or externally linked SVG content', () => {
  assert.throws(() => Core.validateSvgText('<svg><script>alert(1)</script></svg>'), /active or external content/);
  assert.throws(() => Core.validateSvgText('<svg><image href="https://example.com/a.png"/></svg>'), /active or external content/);
  assert.throws(() => Core.validateSvgText('<svg><style>@import url(https://example.com/a.css)</style></svg>'), /active or external content/);
  assert.doesNotThrow(() => Core.validateSvgText('<svg xmlns="http://www.w3.org/2000/svg"><rect width="10" height="10" fill="url(#paint)"/></svg>'));
});
