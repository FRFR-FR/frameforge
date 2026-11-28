const test = require('node:test');
const assert = require('node:assert/strict');
const Core = require('../ff-v2-core.js');
const Audio = require('../ff-v2-audio.js');

function makeAsset(id, mediaType = 'audio', duration = 1) {
  return {
    id, label: id, file_name: id + (mediaType === 'audio' ? '.wav' : '.png'),
    media_type: mediaType, metadata: { duration_seconds: duration, size_bytes: 100 },
    provenance: { source_type: 'user_supplied', notes: 'Audio unit test fixture' },
    rights: { status: 'pending', attribution_required: false }, tags: []
  };
}

function makeBuffer(value = 0.25, durationSeconds = 1, sampleRate = 48000, channels = 1) {
  const length = Math.round(durationSeconds * sampleRate);
  const arrays = Array.from({ length: channels }, () => new Float32Array(length).fill(value));
  return {
    sampleRate, length, duration: durationSeconds, numberOfChannels: channels,
    getChannelData(channel) { return arrays[Math.min(channel, arrays.length - 1)]; }
  };
}

function createAudioProject() {
  const project = Core.createDefaultProject('Audio tests', '2026-11-28T00:00:00.000Z');
  Core.addAsset(project, makeAsset('voice'));
  Core.addAsset(project, makeAsset('music'));
  Core.addAsset(project, makeAsset('effect'));
  const sequence = Core.getMainSequence(project);
  const voiceTrack = sequence.tracks.find(track => track.type === 'voiceover');
  const musicTrack = sequence.tracks.find(track => track.type === 'music');
  const sfxTrack = sequence.tracks.find(track => track.type === 'sfx');
  const voiceClip = Core.addAssetClip(project, 'voice', voiceTrack.id, 0, 30);
  const musicClip = Core.addAssetClip(project, 'music', musicTrack.id, 0, 30);
  sequence.duration_frames = 30;
  Audio.ensureProjectAudio(project);
  return { project, sequence, voiceTrack, musicTrack, sfxTrack, voiceClip, musicClip };
}

test('default and newly created audio tracks and clips have audio settings', () => {
  const project = Core.createDefaultProject();
  const voice = project.sequences[0].tracks.find(track => track.type === 'voiceover');
  assert.deepEqual(voice.audio, { gain: 1, pan: 0, solo: false });
  const newTrack = Core.addTrack(project, 'audio', 'Dialogue');
  assert.deepEqual(newTrack.audio, { gain: 1, pan: 0, solo: false });
  const asset = makeAsset('dialogue');
  Core.addAsset(project, asset);
  const clip = Core.addAssetClip(project, asset.id, newTrack.id, 0, 30);
  assert.deepEqual(clip.audio, {
    gain: 1, pan: 0, fade_in_frames: 0, fade_out_frames: 0, muted: false, automation: []
  });
  assert.equal(Core.validateProject(project).length, 0);
});

test('audio settings are normalized and automation is interpolated', () => {
  const normalized = Audio.normalizeClipAudio({
    gain: 9, pan: -4, fade_in_frames: 100, fade_out_frames: -2,
    automation: [{ frame: 20, gain: 2 }, { frame: 0, gain: 0.2 }, { frame: -1, gain: 1 }]
  }, 30);
  assert.equal(normalized.gain, 4);
  assert.equal(normalized.pan, -1);
  assert.equal(normalized.fade_in_frames, 30);
  assert.equal(normalized.fade_out_frames, 0);
  assert.deepEqual(normalized.automation, [{ frame: 0, gain: 0.2 }, { frame: 20, gain: 2 }]);
  assert.equal(Audio.getAutomationGain(normalized.automation, 10, 1), 1.1);
});

test('clip gain, pan, fades and gain keyframes are stored against local frames', () => {
  const { project, voiceClip } = createAudioProject();
  Audio.setClipAudio(project, voiceClip.id, { gain: 0.7, pan: 0.25, fade_in_frames: 8, fade_out_frames: 10 });
  const key = Audio.addGainKeyframe(project, voiceClip.id, 12, 0.4);
  assert.equal(key.frame, 12);
  assert.equal(voiceClip.audio.automation[0].gain, 0.4);
  assert.equal(voiceClip.audio.gain, 0.7);
  assert.equal(voiceClip.audio.fade_in_frames, 8);
});

test('visual clip event cues resolve at the clip start and end', () => {
  const { project } = createAudioProject();
  const image = makeAsset('visual', 'image');
  Core.addAsset(project, image);
  const imageTrack = project.sequences[0].tracks.find(track => track.type === 'image');
  const visualClip = Core.addAssetClip(project, 'visual', imageTrack.id, 45, 90);
  const start = Audio.addCue(project, 'effect', 'clip_start', 0, visualClip.id);
  const end = Audio.addCue(project, 'effect', 'clip_end', 0, visualClip.id);
  const resolved = Audio.getResolvedCues(project);
  assert.equal(Audio.resolveCueFrame(start, project), 45);
  assert.equal(Audio.resolveCueFrame(end, project), 135);
  assert.deepEqual(resolved.map(item => item.frame), [45, 135]);
  Audio.removeCue(project, start.id);
  assert.equal(project.extensions.ffv2_audio.cues.length, 1);
});

test('waveform peak extraction returns bounded peak buckets', () => {
  const buffer = makeBuffer(0.4, 1, 48000, 2);
  const peaks = Audio.waveformPeaks(buffer, 128);
  assert.equal(peaks.length, 128);
  assert.ok(peaks.every(value => value >= 0 && value <= 1));
  assert.ok(peaks.some(value => value > 0.39));
});

test('WAV render mixes overlapping tracks, respects solo and writes PCM16 stereo', async () => {
  const { project, voiceTrack } = createAudioProject();
  project.sequences[0].tracks.find(track => track.type === 'music').audio.gain = 0.8;
  voiceTrack.audio.solo = true;
  const buffers = new Map([
    ['voice', makeBuffer(0.25)],
    ['music', makeBuffer(0.25)]
  ]);
  const result = await Audio.renderWav(project, buffers, { sampleRate: 48000, normalize: false });
  const bytes = new Uint8Array(await result.blob.arrayBuffer());
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  assert.equal(result.blob.type, 'audio/wav');
  assert.equal(String.fromCharCode(...bytes.slice(0, 4)), 'RIFF');
  assert.equal(String.fromCharCode(...bytes.slice(8, 12)), 'WAVE');
  assert.equal(view.getUint16(22, true), 2);
  assert.equal(view.getUint32(24, true), 48000);
  assert.equal(view.getUint16(34, true), 16);
  assert.ok(Math.abs(view.getInt16(44, true) - 8192) <= 2);
  assert.ok(Math.abs(view.getInt16(46, true) - 8192) <= 2);
  assert.equal(result.metrics.clips_mixed, 1);
  assert.equal(result.metrics.duration_seconds, 1);
});

test('WAV render applies fade-in and hard-right panning', async () => {
  const { project, voiceClip } = createAudioProject();
  voiceClip.duration_frames = 30;
  Audio.setClipAudio(project, voiceClip.id, { pan: 1, fade_in_frames: 10 });
  const result = await Audio.renderWav(project, new Map([['voice', makeBuffer(0.5)]]), {
    sampleRate: 48000, normalize: false
  });
  const bytes = new Uint8Array(await result.blob.arrayBuffer());
  const view = new DataView(bytes.buffer);
  const frame0Left = view.getInt16(44, true);
  const frame0Right = view.getInt16(46, true);
  const halfwaySample = Math.round((5 / 30) * 48000);
  const halfLeft = view.getInt16(44 + halfwaySample * 4, true);
  const halfRight = view.getInt16(44 + halfwaySample * 4 + 2, true);
  assert.equal(frame0Left, 0);
  assert.equal(frame0Right, 0);
  assert.equal(halfLeft, 0);
  assert.ok(Math.abs(halfRight - 8192) <= 4);
});

test('WAV render can duck music under detected voiceover', async () => {
  const { project } = createAudioProject();
  project.extensions.ffv2_audio.ducking = {
    enabled: true, amount_db: -18, threshold: 0.1, attack_ms: 10, release_ms: 40
  };
  const result = await Audio.renderWav(project, new Map([
    ['voice', makeBuffer(0.5)],
    ['music', makeBuffer(0.1)]
  ]), { sampleRate: 48000, normalize: false });
  assert.equal(result.metrics.ducking_enabled, true);
  const bytes = new Uint8Array(await result.blob.arrayBuffer());
  const view = new DataView(bytes.buffer);
  const laterSample = Math.round(0.5 * 48000);
  const musicAndVoiceExpectedUnducked = 0.6 * 32767;
  const actual = view.getInt16(44 + laterSample * 4, true);
  assert.ok(actual < musicAndVoiceExpectedUnducked * 0.8);
});

test('audio cues reject non-audio assets and non-visual event targets', () => {
  const { project, voiceClip } = createAudioProject();
  assert.throws(() => Audio.addCue(project, 'voice', 'clip_start', 0, voiceClip.id), /visual clip/);
  assert.throws(() => Audio.addCue(project, 'missing', 'playhead', 0), /imported audio asset/);
});
