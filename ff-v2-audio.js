/* FrameForge V2 audio engine — editable timeline audio, deterministic WAV mixing and SFX cues. */
(function (root) {
  'use strict';

  const AUDIO_TYPES = new Set(['audio', 'voiceover', 'music', 'sfx']);
  const DEFAULT_CLIP_AUDIO = { gain: 1, pan: 0, fade_in_frames: 0, fade_out_frames: 0, muted: false, automation: [] };
  const DEFAULT_TRACK_AUDIO = { gain: 1, pan: 0, solo: false };
  const DEFAULT_DUCKING = { enabled: false, amount_db: -12, threshold: 0.025, attack_ms: 120, release_ms: 300 };
  const getBuffer = (map, id) => map instanceof Map ? map.get(id) : map && map[id];

  function clamp(value, min, max, fallback) {
    const number = Number(value);
    return Number.isFinite(number) ? Math.max(min, Math.min(max, number)) : fallback;
  }

  function normalizeClipAudio(value, durationFrames) {
    const audio = Object.assign({}, DEFAULT_CLIP_AUDIO, value || {});
    audio.gain = clamp(audio.gain, 0, 4, 1);
    audio.pan = clamp(audio.pan, -1, 1, 0);
    audio.fade_in_frames = Math.round(clamp(audio.fade_in_frames, 0, Math.max(0, durationFrames || 1000000), 0));
    audio.fade_out_frames = Math.round(clamp(audio.fade_out_frames, 0, Math.max(0, durationFrames || 1000000), 0));
    audio.muted = Boolean(audio.muted);
    audio.automation = Array.isArray(audio.automation)
      ? audio.automation.filter(key => Number.isInteger(key.frame) && key.frame >= 0 && Number.isFinite(Number(key.gain)))
        .map(key => ({ frame: key.frame, gain: clamp(key.gain, 0, 4, 1) }))
        .sort((a, b) => a.frame - b.frame)
      : [];
    return audio;
  }

  function normalizeTrackAudio(value) {
    const audio = Object.assign({}, DEFAULT_TRACK_AUDIO, value || {});
    audio.gain = clamp(audio.gain, 0, 4, 1);
    audio.pan = clamp(audio.pan, -1, 1, 0);
    audio.solo = Boolean(audio.solo);
    return audio;
  }

  function ensureProjectAudio(project) {
    let changed = false;
    if (!project.extensions) { project.extensions = {}; changed = true; }
    if (!project.extensions.ffv2_audio) {
      project.extensions.ffv2_audio = { version: 1, cues: [], ducking: Object.assign({}, DEFAULT_DUCKING) };
      changed = true;
    }
    const audioState = project.extensions.ffv2_audio;
    if (!Array.isArray(audioState.cues)) { audioState.cues = []; changed = true; }
    audioState.ducking = Object.assign({}, DEFAULT_DUCKING, audioState.ducking || {});
    for (const sequence of project.sequences || []) {
      for (const track of sequence.tracks || []) {
        if (!AUDIO_TYPES.has(track.type)) continue;
        const normalized = normalizeTrackAudio(track.audio);
        if (JSON.stringify(normalized) !== JSON.stringify(track.audio || {})) changed = true;
        track.audio = normalized;
        for (const clip of track.clips || []) {
          if (clip.kind !== 'asset') continue;
          const clipAudio = normalizeClipAudio(clip.audio, clip.duration_frames);
          if (JSON.stringify(clipAudio) !== JSON.stringify(clip.audio || {})) changed = true;
          clip.audio = clipAudio;
        }
      }
    }
    return changed;
  }

  function getAutomationGain(automation, localFrame, fallback) {
    const keys = (automation || []).slice().sort((a, b) => a.frame - b.frame);
    if (!keys.length) return fallback;
    if (localFrame <= keys[0].frame) return keys[0].gain;
    if (localFrame >= keys[keys.length - 1].frame) return keys[keys.length - 1].gain;
    for (let i = 0; i < keys.length - 1; i++) {
      const left = keys[i], right = keys[i + 1];
      if (localFrame >= left.frame && localFrame <= right.frame) {
        const span = Math.max(1, right.frame - left.frame);
        const t = (localFrame - left.frame) / span;
        return left.gain + (right.gain - left.gain) * t;
      }
    }
    return fallback;
  }

  function setClipAudio(project, clipId, updates) {
    const Core = root.FFV2Core;
    const found = Core.findClip(project, clipId);
    if (found.track.locked) throw new Error('This track is locked.');
    if (!AUDIO_TYPES.has(found.track.type)) throw new Error('Select a clip on an audio track.');
    const audio = normalizeClipAudio(found.clip.audio, found.clip.duration_frames);
    for (const key of ['gain', 'pan', 'fade_in_frames', 'fade_out_frames', 'muted']) {
      if (updates && Object.prototype.hasOwnProperty.call(updates, key)) audio[key] = updates[key];
    }
    const normalized = normalizeClipAudio(audio, found.clip.duration_frames);
    found.clip.audio = normalized;
    return normalized;
  }

  function addGainKeyframe(project, clipId, globalFrame, gain) {
    const Core = root.FFV2Core;
    const found = Core.findClip(project, clipId);
    if (found.track.locked) throw new Error('This track is locked.');
    if (!AUDIO_TYPES.has(found.track.type)) throw new Error('Select a clip on an audio track.');
    const localFrame = Math.max(0, Math.min(found.clip.duration_frames, Math.round(globalFrame - found.clip.start_frame)));
    const value = clamp(gain, 0, 4, 1);
    found.clip.audio = normalizeClipAudio(found.clip.audio, found.clip.duration_frames);
    const keys = found.clip.audio.automation;
    const existing = keys.findIndex(key => key.frame === localFrame);
    const record = { frame: localFrame, gain: value };
    if (existing >= 0) keys[existing] = record;
    else keys.push(record);
    keys.sort((a, b) => a.frame - b.frame);
    return record;
  }

  function resolveCueFrame(cue, project) {
    if (cue.event_type === 'clip_start' || cue.event_type === 'clip_end') {
      try {
        const found = root.FFV2Core.findClip(project, cue.clip_id);
        return found.clip.start_frame + (cue.event_type === 'clip_end' ? found.clip.duration_frames : 0);
      } catch (_) {
        return null;
      }
    }
    return Number.isInteger(cue.frame) && cue.frame >= 0 ? cue.frame : null;
  }

  function addCue(project, assetId, eventType, frame, clipId) {
    const valid = ['playhead', 'clip_start', 'clip_end'];
    if (!valid.includes(eventType)) throw new Error('Choose a supported SFX trigger.');
    if (!project.assets.some(asset => asset.id === assetId && asset.media_type === 'audio')) {
      throw new Error('Choose an imported audio asset for the SFX cue.');
    }
    if ((eventType === 'clip_start' || eventType === 'clip_end') && !clipId) {
      throw new Error('Select a visual clip before attaching an event cue.');
    }
    if (clipId) {
      const found = root.FFV2Core.findClip(project, clipId);
      if (AUDIO_TYPES.has(found.track.type)) throw new Error('Attach visual-event cues to a visual clip, not an audio clip.');
    }
    const ext = project.extensions || (project.extensions = {});
    const state = ext.ffv2_audio || (ext.ffv2_audio = { version: 1, cues: [], ducking: Object.assign({}, DEFAULT_DUCKING) });
    state.cues = Array.isArray(state.cues) ? state.cues : [];
    const cue = {
      id: root.FFV2Core.makeId('cue'),
      asset_id: assetId,
      event_type: eventType,
      frame: Math.max(0, Math.round(Number(frame) || 0)),
      clip_id: clipId || '',
      gain: 1,
      pan: 0
    };
    state.cues.push(cue);
    return cue;
  }

  function removeCue(project, cueId) {
    const cues = project.extensions?.ffv2_audio?.cues || [];
    project.extensions.ffv2_audio.cues = cues.filter(cue => cue.id !== cueId);
  }

  function getResolvedCues(project) {
    return (project.extensions?.ffv2_audio?.cues || []).map(cue => ({
      cue,
      frame: resolveCueFrame(cue, project)
    })).filter(item => Number.isInteger(item.frame));
  }

  function sampleAt(buffer, position, channel) {
    if (!buffer || !Number.isFinite(position) || position < 0 || position >= buffer.length) return 0;
    const index = Math.floor(position);
    const next = Math.min(buffer.length - 1, index + 1);
    const data = buffer.getChannelData(Math.min(channel, buffer.numberOfChannels - 1));
    const fraction = position - index;
    return data[index] + (data[next] - data[index]) * fraction;
  }

  function makeDescriptors(project, buffers) {
    const Core = root.FFV2Core;
    const sequence = Core.getMainSequence(project);
    const fps = sequence.fps;
    const tracks = sequence.tracks || [];
    const audioTracks = tracks.filter(track => AUDIO_TYPES.has(track.type));
    const soloActive = audioTracks.some(track => track.audio?.solo);
    const descriptors = [];
    for (const track of audioTracks) {
      if (track.enabled === false || track.muted || (soloActive && !track.audio?.solo)) continue;
      const trackAudio = normalizeTrackAudio(track.audio);
      for (const clip of track.clips || []) {
        if (clip.enabled === false || clip.audio?.muted || !clip.asset_id) continue;
        const buffer = getBuffer(buffers, clip.asset_id);
        if (!buffer) continue;
        const audio = normalizeClipAudio(clip.audio, clip.duration_frames);
        descriptors.push({
          id: clip.id, asset_id: clip.asset_id, track, track_type: track.type, clip, buffer,
          start_frame: clip.start_frame, duration_frames: clip.duration_frames,
          source_in_seconds: Math.max(0, (Number(clip.source_in_frame) || 0) / fps),
          playback_rate: clamp(clip.playback_rate, 0.05, 8, 1),
          gain: audio.gain * trackAudio.gain,
          pan: clamp(audio.pan + trackAudio.pan, -1, 1, 0),
          fade_in_frames: audio.fade_in_frames, fade_out_frames: audio.fade_out_frames,
          automation: audio.automation
        });
      }
    }

    const sfxTrack = audioTracks.find(track => track.type === 'sfx');
    const sfxTrackAudio = normalizeTrackAudio(sfxTrack?.audio);
    const cues = getResolvedCues(project);
    for (const item of cues) {
      if (!sfxTrack || sfxTrack.enabled === false || sfxTrack.muted || (soloActive && !sfxTrack.audio?.solo)) continue;
      const cue = item.cue;
      const buffer = getBuffer(buffers, cue.asset_id);
      if (!buffer) continue;
      const asset = project.assets.find(entry => entry.id === cue.asset_id);
      const durationFrames = Math.max(1, Math.round((Number(asset?.metadata?.duration_seconds) || buffer.duration || 0.25) * fps));
      descriptors.push({
        id: cue.id, asset_id: cue.asset_id, track: sfxTrack, track_type: 'sfx', clip: { audio: { automation: [] } }, buffer,
        start_frame: item.frame, duration_frames: durationFrames,
        source_in_seconds: 0, playback_rate: 1,
        gain: clamp(cue.gain, 0, 4, 1) * sfxTrackAudio.gain,
        pan: clamp(Number(cue.pan || 0) + sfxTrackAudio.pan, -1, 1, 0),
        fade_in_frames: 0, fade_out_frames: 0, automation: []
      });
    }
    return { descriptors, fps, sequence };
  }

  function buildDuckingEnvelope(descriptors, totalSamples, sampleRate, ducking) {
    const voiceovers = descriptors.filter(item => item.track_type === 'voiceover');
    if (!ducking?.enabled || !voiceovers.length) return null;
    const blockSamples = Math.max(1, Math.round(sampleRate * 0.02));
    const count = Math.ceil(totalSamples / blockSamples);
    const envelope = new Float32Array(count);
    const threshold = clamp(ducking.threshold, 0, 1, DEFAULT_DUCKING.threshold);
    const duckGain = Math.pow(10, clamp(ducking.amount_db, -36, 0, -12) / 20);
    const attack = Math.max(0.01, clamp(ducking.attack_ms, 10, 2000, 120) / 1000);
    const release = Math.max(0.01, clamp(ducking.release_ms, 20, 4000, 300) / 1000);
    let current = 1;

    for (let block = 0; block < count; block++) {
      const timelineTime = (block * blockSamples + blockSamples * 0.5) / sampleRate;
      let energy = 0, voices = 0;
      for (const voice of voiceovers) {
        const start = voice.start_frame / voice._fps;
        const duration = voice.duration_frames / voice._fps;
        const localTime = timelineTime - start;
        if (localTime < 0 || localTime >= duration) continue;
        const sourcePosition = (voice.source_in_seconds + localTime * voice.playback_rate) * voice.buffer.sampleRate;
        let localEnergy = 0;
        for (const fraction of [0.2, 0.4, 0.6, 0.8]) {
          const offsetSeconds = (fraction - 0.5) * 0.02;
          const position = (voice.source_in_seconds + (localTime + offsetSeconds) * voice.playback_rate) * voice.buffer.sampleRate;
          const left = sampleAt(voice.buffer, position, 0);
          const right = sampleAt(voice.buffer, position, 1);
          localEnergy += (left * left + right * right) * 0.5;
        }
        energy += localEnergy / 4;
        voices++;
      }
      const rms = voices ? Math.sqrt(energy / voices) : 0;
      const target = rms >= threshold ? duckGain : 1;
      const dt = blockSamples / sampleRate;
      const timeConstant = target < current ? attack : release;
      const coefficient = Math.exp(-dt / timeConstant);
      current = target + (current - target) * coefficient;
      envelope[block] = current;
    }
    return { values: envelope, block_samples: blockSamples };
  }

  function automationValue(descriptor, localFrame) {
    return getAutomationGain(descriptor.automation, localFrame, 1);
  }

  function renderBlock(descriptors, duckEnvelope, blockStart, blockLength, sampleRate, fps) {
    const output = new Float32Array(blockLength * 2);
    const blockEnd = blockStart + blockLength;
    for (const item of descriptors) {
      const clipStart = Math.round(item.start_frame / fps * sampleRate);
      const clipEnd = Math.min(blockEnd, Math.round((item.start_frame + item.duration_frames) / fps * sampleRate));
      const from = Math.max(blockStart, clipStart);
      const to = Math.min(blockEnd, clipEnd);
      if (to <= from) continue;
      const leftPan = item.pan > 0 ? 1 - item.pan : 1;
      const rightPan = item.pan < 0 ? 1 + item.pan : 1;
      const sourceRate = item.buffer.sampleRate / sampleRate * item.playback_rate;
      const fadeIn = item.fade_in_frames;
      const fadeOut = item.fade_out_frames;
      for (let absolute = from; absolute < to; absolute++) {
        const localSample = absolute - clipStart;
        const localFrame = localSample / sampleRate * fps;
        const sourcePosition = (item.source_in_seconds * item.buffer.sampleRate) + localSample * sourceRate;
        if (sourcePosition >= item.buffer.length) break;
        let gain = item.gain * automationValue(item, localFrame);
        if (fadeIn > 0) gain *= Math.min(1, localFrame / fadeIn);
        if (fadeOut > 0) gain *= Math.min(1, Math.max(0, (item.duration_frames - localFrame) / fadeOut));
        if (item.track_type === 'music' && duckEnvelope) {
          const index = Math.min(duckEnvelope.values.length - 1, Math.floor(absolute / duckEnvelope.block_samples));
          gain *= duckEnvelope.values[Math.max(0, index)] || 1;
        }
        const left = sampleAt(item.buffer, sourcePosition, 0);
        const right = sampleAt(item.buffer, sourcePosition, item.buffer.numberOfChannels > 1 ? 1 : 0);
        const outputIndex = (absolute - blockStart) * 2;
        output[outputIndex] += left * gain * leftPan;
        output[outputIndex + 1] += right * gain * rightPan;
      }
    }
    return output;
  }

  function makeWavHeader(dataBytes, sampleRate, channels) {
    const header = new ArrayBuffer(44);
    const view = new DataView(header);
    const write = (offset, value) => {
      for (let i = 0; i < value.length; i++) view.setUint8(offset + i, value.charCodeAt(i));
    };
    write(0, 'RIFF'); view.setUint32(4, 36 + dataBytes, true); write(8, 'WAVE');
    write(12, 'fmt '); view.setUint32(16, 16, true); view.setUint16(20, 1, true);
    view.setUint16(22, channels, true); view.setUint32(24, sampleRate, true);
    view.setUint32(28, sampleRate * channels * 2, true); view.setUint16(32, channels * 2, true);
    view.setUint16(34, 16, true); write(36, 'data'); view.setUint32(40, dataBytes, true);
    return new Uint8Array(header);
  }

  async function renderWav(project, buffers, options) {
    options = options || {};
    const prepared = makeDescriptors(project, buffers);
    const sampleRate = Math.round(clamp(options.sampleRate || project.settings?.sample_rate, 22050, 96000, 48000));
    const channels = 2;
    const totalSeconds = prepared.sequence.duration_frames / prepared.fps;
    const maxDuration = clamp(options.maxDurationSeconds, 1, 1800, 600);
    if (totalSeconds <= 0 || totalSeconds > maxDuration) {
      throw new Error('Audio master duration must be between 0 and ' + maxDuration + ' seconds on this device.');
    }
    const totalSamples = Math.ceil(totalSeconds * sampleRate);
    const dataBytes = totalSamples * channels * 2;
    if (dataBytes > 0xffffffff - 36) throw new Error('The WAV master would exceed the 4 GB PCM WAV limit.');
    for (const item of prepared.descriptors) item._fps = prepared.fps;
    const ducking = project.extensions?.ffv2_audio?.ducking || DEFAULT_DUCKING;
    const duckEnvelope = buildDuckingEnvelope(prepared.descriptors, totalSamples, sampleRate, ducking);
    const chunkSamples = sampleRate * 5;
    let peak = 0, sumSquares = 0, sampleCount = 0;

    for (let start = 0; start < totalSamples; start += chunkSamples) {
      const length = Math.min(chunkSamples, totalSamples - start);
      const mixed = renderBlock(prepared.descriptors, duckEnvelope, start, length, sampleRate, prepared.fps);
      for (let i = 0; i < mixed.length; i++) {
        const absolute = Math.abs(mixed[i]);
        if (absolute > peak) peak = absolute;
        sumSquares += mixed[i] * mixed[i];
        sampleCount++;
      }
      if (options.onProgress) options.onProgress(Math.min(0.5, 0.5 * (start + length) / totalSamples));
      await new Promise(resolve => setTimeout(resolve, 0));
    }

    const targetDb = clamp(options.targetPeakDb, -12, 0, -1);
    const targetLinear = Math.pow(10, targetDb / 20);
    const normalizationGain = options.normalize === false || peak <= 0 ? 1 : Math.min(8, targetLinear / peak);
    const parts = [makeWavHeader(dataBytes, sampleRate, channels)];
    for (let start = 0; start < totalSamples; start += chunkSamples) {
      const length = Math.min(chunkSamples, totalSamples - start);
      const mixed = renderBlock(prepared.descriptors, duckEnvelope, start, length, sampleRate, prepared.fps);
      const pcm = new Int16Array(mixed.length);
      for (let i = 0; i < mixed.length; i++) {
        const value = Math.max(-1, Math.min(1, mixed[i] * normalizationGain));
        pcm[i] = Math.round(value < 0 ? value * 32768 : value * 32767);
      }
      parts.push(new Uint8Array(pcm.buffer));
      if (options.onProgress) options.onProgress(0.5 + 0.5 * (start + length) / totalSamples);
      await new Promise(resolve => setTimeout(resolve, 0));
    }

    const blob = new Blob(parts, { type: 'audio/wav' });
    const rms = sampleCount ? Math.sqrt(sumSquares / sampleCount) : 0;
    const db = value => value > 0 ? 20 * Math.log10(value) : -Infinity;
    return {
      blob,
      metrics: {
        duration_seconds: totalSeconds, sample_rate: sampleRate, channels,
        peak_dbfs: db(peak * normalizationGain), rms_dbfs: db(rms * normalizationGain),
        pre_normalization_peak_dbfs: db(peak),
        normalization_gain: normalizationGain,
        clips_mixed: prepared.descriptors.length,
        ducking_enabled: Boolean(ducking.enabled && duckEnvelope)
      }
    };
  }

  function waveformPeaks(buffer, bucketCount) {
    const count = Math.max(16, Math.min(2048, Math.round(bucketCount || 256)));
    const peaks = new Float32Array(count);
    if (!buffer || !buffer.length) return peaks;
    const channels = Math.max(1, buffer.numberOfChannels || 1);
    for (let bucket = 0; bucket < count; bucket++) {
      const start = Math.floor(bucket * buffer.length / count);
      const end = Math.max(start + 1, Math.floor((bucket + 1) * buffer.length / count));
      let peak = 0;
      for (let channel = 0; channel < channels; channel++) {
        const samples = buffer.getChannelData(channel);
        for (let i = start; i < Math.min(end, buffer.length); i++) peak = Math.max(peak, Math.abs(samples[i]));
      }
      peaks[bucket] = peak;
    }
    return peaks;
  }

  const ui = {
    context: null, buffers: new Map(), currentPeaks: null, currentBufferId: '',
    renderedBlob: null, renderedUrl: '', dirty: true, syncTimer: null, waveToken: 0
  };

  function studio() { return root.FFV2Studio; }
  function project() { return studio()?.getProject?.(); }
  function el(id) { return root.document && root.document.getElementById(id); }
  function setStatus(message, kind) {
    const node = el('ffv2AudioStatus');
    if (node) { node.textContent = message; node.dataset.kind = kind || 'info'; }
  }
  function markDirty() {
    ui.dirty = true;
    ui.renderedBlob = null;
    if (studio()?.markDirty) studio().markDirty();
  }

  function audioContext() {
    if (!ui.context) {
      const Context = root.AudioContext || root.webkitAudioContext;
      if (!Context) throw new Error('This browser does not support Web Audio decoding.');
      ui.context = new Context();
    }
    return ui.context;
  }

  async function decodeAsset(assetId) {
    if (ui.buffers.has(assetId)) return ui.buffers.get(assetId);
    const record = studio()?.getAssetRecords?.().find(item => item.id === assetId);
    const blob = record?.blob || await studio()?.getAssetBlob?.(assetId);
    if (!blob) throw new Error('Audio source is missing from this browser. Re-import the file on this device.');
    const context = audioContext();
    const buffer = await context.decodeAudioData(await blob.arrayBuffer());
    ui.buffers.set(assetId, buffer);
    return buffer;
  }

  function drawWaveform(canvas, peaks, progress) {
    if (!canvas || !peaks) return;
    const rect = canvas.getBoundingClientRect();
    const width = Math.max(1, Math.round(rect.width || canvas.width || 600));
    const height = Math.max(1, Math.round(rect.height || canvas.height || 110));
    const ratio = Math.max(1, root.devicePixelRatio || 1);
    canvas.width = width * ratio; canvas.height = height * ratio;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    ctx.scale(ratio, ratio);
    ctx.clearRect(0, 0, width, height);
    ctx.fillStyle = '#091521'; ctx.fillRect(0, 0, width, height);
    ctx.strokeStyle = '#1d3348'; ctx.lineWidth = 1;
    ctx.beginPath(); ctx.moveTo(0, height / 2); ctx.lineTo(width, height / 2); ctx.stroke();
    const step = width / peaks.length;
    ctx.fillStyle = '#63b6eb';
    for (let i = 0; i < peaks.length; i++) {
      const h = Math.max(1, peaks[i] * (height * 0.43));
      ctx.fillRect(i * step, (height - h) / 2, Math.max(1, step * 0.72), h);
    }
    if (Number.isFinite(progress)) {
      const x = Math.max(0, Math.min(width, progress * width));
      ctx.strokeStyle = '#f5c46b'; ctx.lineWidth = 2;
      ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, height); ctx.stroke();
    }
  }

  function selectedAudioClip() {
    const found = studio()?.getSelectedClip?.();
    if (!found) return null;
    if (!AUDIO_TYPES.has(found.track.type) || !found.clip.asset_id) return null;
    const asset = project()?.assets?.find(item => item.id === found.clip.asset_id);
    return asset?.media_type === 'audio' ? Object.assign({ asset }, found) : null;
  }

  function populateTrackOptions() {
    const select = el('ffv2AudioTrack');
    const currentProject = project();
    if (!select || !currentProject) return;
    const current = select.value;
    select.replaceChildren();
    const tracks = root.FFV2Core.getMainSequence(currentProject).tracks.filter(track => AUDIO_TYPES.has(track.type));
    for (const track of tracks) {
      const option = root.document.createElement('option');
      option.value = track.id;
      option.textContent = track.name + ' (' + track.type + ')';
      select.append(option);
    }
    const selected = studio()?.getSelectedClip?.();
    const preferred = selected && AUDIO_TYPES.has(selected.track.type) ? selected.track.id : current;
    select.value = tracks.some(track => track.id === preferred) ? preferred : (tracks[0]?.id || '');
    syncTrackControls();
  }

  function syncTrackControls() {
    const currentProject = project();
    const select = el('ffv2AudioTrack');
    if (!select || !currentProject) return;
    const track = root.FFV2Core.getMainSequence(currentProject).tracks.find(item => item.id === select.value);
    if (!track) return;
    const audio = normalizeTrackAudio(track.audio);
    el('ffv2AudioTrackGain').value = String(audio.gain);
    el('ffv2AudioTrackPan').value = String(audio.pan);
    el('ffv2AudioTrackSolo').checked = audio.solo;
  }

  function populateCueAssets() {
    const select = el('ffv2AudioCueAsset');
    const currentProject = project();
    if (!select || !currentProject) return;
    const current = select.value;
    select.replaceChildren();
    const assets = currentProject.assets.filter(asset => asset.media_type === 'audio');
    for (const asset of assets) {
      const option = root.document.createElement('option');
      option.value = asset.id; option.textContent = asset.label || asset.file_name || asset.id;
      select.append(option);
    }
    select.value = assets.some(asset => asset.id === current) ? current : (assets[0]?.id || '');
    el('ffv2AudioAddCue').disabled = assets.length === 0;
  }

  function syncClipControls() {
    const found = selectedAudioClip();
    const panel = el('ffv2AudioClipControls');
    if (!panel) return;
    panel.classList.toggle('hidden', !found);
    if (!found) {
      el('ffv2AudioSelectedClip').textContent = 'Select an audio clip in the timeline to edit its waveform and clip mix.';
      ui.currentBufferId = ''; ui.currentPeaks = null;
      drawWaveform(el('ffv2AudioWaveform'), null, null);
      return;
    }
    const audio = normalizeClipAudio(found.clip.audio, found.clip.duration_frames);
    el('ffv2AudioSelectedClip').textContent = (found.asset.label || found.asset.file_name) + ' · ' + found.track.name;
    el('ffv2AudioClipGain').value = String(audio.gain);
    el('ffv2AudioClipPan').value = String(audio.pan);
    el('ffv2AudioFadeIn').value = String(audio.fade_in_frames);
    el('ffv2AudioFadeOut').value = String(audio.fade_out_frames);
    el('ffv2AudioClipMuted').checked = audio.muted;
    el('ffv2AudioAutomationInfo').textContent = audio.automation.length + ' gain keyframe(s) · keyframes use clip-local frames';
    loadSelectedWaveform(found.asset.id);
  }

  async function loadSelectedWaveform(assetId) {
    const token = ++ui.waveToken;
    if (ui.currentBufferId === assetId && ui.currentPeaks) {
      updateWaveformCursor();
      return;
    }
    ui.currentBufferId = assetId;
    setStatus('Decoding selected audio for waveform display…');
    try {
      const buffer = await decodeAsset(assetId);
      if (token !== ui.waveToken) return;
      ui.currentPeaks = waveformPeaks(buffer, 512);
      drawWaveform(el('ffv2AudioWaveform'), ui.currentPeaks, currentWaveProgress());
      setStatus('Waveform ready · ' + buffer.duration.toFixed(2) + ' s · ' + buffer.sampleRate + ' Hz', 'success');
    } catch (error) {
      if (token === ui.waveToken) setStatus(error.message, 'warning');
    }
  }

  function currentWaveProgress() {
    const found = selectedAudioClip();
    if (!found) return 0;
    const frame = studio()?.getPlayheadFrame?.() || 0;
    return Math.max(0, Math.min(1, (frame - found.clip.start_frame) / Math.max(1, found.clip.duration_frames)));
  }

  function updateWaveformCursor() {
    if (ui.currentPeaks) drawWaveform(el('ffv2AudioWaveform'), ui.currentPeaks, currentWaveProgress());
  }

  function renderCueList() {
    const host = el('ffv2AudioCueList');
    const currentProject = project();
    if (!host || !currentProject) return;
    const cues = currentProject.extensions?.ffv2_audio?.cues || [];
    host.replaceChildren();
    if (!cues.length) {
      const empty = root.document.createElement('div');
      empty.className = 'ffv2-empty'; empty.textContent = 'No SFX cues yet.';
      host.append(empty); return;
    }
    for (const cue of cues) {
      const asset = currentProject.assets.find(item => item.id === cue.asset_id);
      const frame = resolveCueFrame(cue, currentProject);
      const row = root.document.createElement('div');
      row.className = 'ffv2-audio-cue-row';
      const label = root.document.createElement('span');
      label.textContent = (asset?.label || 'Missing audio') + ' · ' + cue.event_type.replace('_', ' ') + ' · frame ' + (frame == null ? 'unresolved' : frame);
      const remove = root.document.createElement('button');
      remove.type = 'button'; remove.className = 'button small danger-text'; remove.textContent = 'Remove';
      remove.addEventListener('click', () => {
        removeCue(currentProject, cue.id); markDirty(); renderCueList(); setStatus('SFX cue removed.', 'success');
      });
      row.append(label, remove); host.append(row);
    }
  }

  async function loadRequiredBuffers(currentProject) {
    const ids = new Set();
    const sequence = root.FFV2Core.getMainSequence(currentProject);
    for (const track of sequence.tracks) {
      if (!AUDIO_TYPES.has(track.type)) continue;
      for (const clip of track.clips || []) if (clip.asset_id && clip.enabled !== false) ids.add(clip.asset_id);
    }
    for (const cue of currentProject.extensions?.ffv2_audio?.cues || []) ids.add(cue.asset_id);
    const buffers = new Map();
    let index = 0;
    for (const id of ids) {
      const asset = currentProject.assets.find(item => item.id === id);
      if (!asset || asset.media_type !== 'audio') continue;
      index++;
      setStatus('Decoding audio ' + index + ' of ' + ids.size + '…');
      buffers.set(id, await decodeAsset(id));
    }
    return buffers;
  }

  async function renderMaster(playAfter) {
    const currentProject = project();
    if (!currentProject) return null;
    try {
      const buffers = await loadRequiredBuffers(currentProject);
      setStatus('Mixing audio master…');
      const result = await renderWav(currentProject, buffers, {
        sampleRate: currentProject.settings?.sample_rate || 48000,
        normalize: true, targetPeakDb: -1,
        onProgress: progress => { setStatus('Mixing audio master… ' + Math.round(progress * 100) + '%'); }
      });
      ui.renderedBlob = result.blob;
      ui.dirty = false;
      if (ui.renderedUrl) URL.revokeObjectURL(ui.renderedUrl);
      ui.renderedUrl = URL.createObjectURL(result.blob);
      const player = el('ffv2AudioPlayer');
      player.src = ui.renderedUrl;
      player.classList.remove('hidden');
      player.load();
      const metrics = result.metrics;
      el('ffv2AudioMetrics').textContent =
        metrics.duration_seconds.toFixed(2) + ' s · ' + metrics.sample_rate + ' Hz · stereo PCM16 · ' +
        'peak ' + (Number.isFinite(metrics.peak_dbfs) ? metrics.peak_dbfs.toFixed(1) : '-∞') + ' dBFS · ' +
        'RMS ' + (Number.isFinite(metrics.rms_dbfs) ? metrics.rms_dbfs.toFixed(1) : '-∞') + ' dBFS · ' +
        metrics.clips_mixed + ' clips/cues mixed';
      setStatus('WAV master rendered successfully.', 'success');
      if (playAfter) {
        player.currentTime = Math.min(player.duration || metrics.duration_seconds, (studio()?.getPlayheadFrame?.() || 0) / root.FFV2Core.getMainSequence(currentProject).fps);
        try { await player.play(); startSync(); }
        catch (_) { setStatus('Audio master is ready. Use the player controls below to start playback.', 'warning'); }
      }
      return result;
    } catch (error) {
      setStatus('Audio render failed: ' + error.message, 'error');
      return null;
    }
  }

  function startSync() {
    stopSync();
    ui.syncTimer = root.setInterval(() => {
      const player = el('ffv2AudioPlayer');
      if (!player || player.paused) { stopSync(); return; }
      const sequence = root.FFV2Core.getMainSequence(project());
      studio()?.setPlayhead?.(Math.round(player.currentTime * sequence.fps), { noPreview: true });
    }, 30);
  }

  function stopSync() {
    if (ui.syncTimer) root.clearInterval(ui.syncTimer);
    ui.syncTimer = null;
  }

  function stopPlayback() {
    const player = el('ffv2AudioPlayer');
    if (player) player.pause();
    stopSync();
  }

  function downloadMaster() {
    if (!ui.renderedBlob || ui.dirty) return renderMaster(false).then(result => result && downloadBlob(result.blob));
    downloadBlob(ui.renderedBlob);
  }

  function downloadBlob(blob) {
    const currentProject = project();
    const anchor = root.document.createElement('a');
    const name = (currentProject?.project?.name || 'FrameForge').replace(/[\\/:*?"<>|]/g, '_');
    const url = URL.createObjectURL(blob);
    anchor.href = url; anchor.download = name + '-audio-master.wav';
    root.document.body.append(anchor); anchor.click(); anchor.remove();
    root.setTimeout(() => URL.revokeObjectURL(url), 5000);
  }

  function applyClipControls() {
    const found = selectedAudioClip();
    if (!found) return;
    try {
      setClipAudio(project(), found.clip.id, {
        gain: Number(el('ffv2AudioClipGain').value),
        pan: Number(el('ffv2AudioClipPan').value),
        fade_in_frames: Number(el('ffv2AudioFadeIn').value),
        fade_out_frames: Number(el('ffv2AudioFadeOut').value),
        muted: el('ffv2AudioClipMuted').checked
      });
      markDirty(); refresh(); setStatus('Audio clip mix settings updated.', 'success');
    } catch (error) { setStatus(error.message, 'warning'); }
  }

  function addSelectedGainKeyframe() {
    const found = selectedAudioClip();
    if (!found) return;
    try {
      const frame = studio().getPlayheadFrame();
      addGainKeyframe(project(), found.clip.id, frame, Number(el('ffv2AudioClipGain').value));
      markDirty(); syncClipControls(); setStatus('Audio gain keyframe added at frame ' + frame + '.', 'success');
    } catch (error) { setStatus(error.message, 'warning'); }
  }

  function applyTrackControls() {
    const currentProject = project();
    const select = el('ffv2AudioTrack');
    const track = root.FFV2Core.getMainSequence(currentProject).tracks.find(item => item.id === select.value);
    if (!track) return;
    track.audio = normalizeTrackAudio(track.audio);
    track.audio.gain = Number(el('ffv2AudioTrackGain').value);
    track.audio.pan = Number(el('ffv2AudioTrackPan').value);
    track.audio.solo = el('ffv2AudioTrackSolo').checked;
    track.audio = normalizeTrackAudio(track.audio);
    markDirty();
    studio()?.renderTracks?.();
    syncTrackControls();
    setStatus('Audio track mix settings updated.', 'success');
  }

  function addSelectedCue() {
    const currentProject = project();
    const assetId = el('ffv2AudioCueAsset').value;
    const eventType = el('ffv2AudioCueType').value;
    const selected = studio()?.getSelectedClip?.();
    const clipId = selected && !AUDIO_TYPES.has(selected.track.type) ? selected.clip.id : '';
    try {
      addCue(currentProject, assetId, eventType, studio()?.getPlayheadFrame?.() || 0, clipId);
      markDirty(); renderCueList(); setStatus('SFX cue added to the event list.', 'success');
    } catch (error) { setStatus(error.message, 'warning'); }
  }

  function applyDucking() {
    const currentProject = project();
    currentProject.extensions.ffv2_audio = currentProject.extensions.ffv2_audio || { version: 1, cues: [], ducking: Object.assign({}, DEFAULT_DUCKING) };
    currentProject.extensions.ffv2_audio.ducking = Object.assign({}, DEFAULT_DUCKING, {
      enabled: el('ffv2AudioDucking').checked,
      amount_db: Number(el('ffv2AudioDuckingAmount').value)
    });
    markDirty(); setStatus('Music ducking settings saved.', 'success');
  }

  function bindUI() {
    el('ffv2AudioTrack').addEventListener('change', syncTrackControls);
    el('ffv2AudioApplyTrack').addEventListener('click', applyTrackControls);
    el('ffv2AudioApplyClip').addEventListener('click', applyClipControls);
    el('ffv2AudioAddGainKeyframe').addEventListener('click', addSelectedGainKeyframe);
    el('ffv2AudioPlayMix').addEventListener('click', () => renderMaster(true));
    el('ffv2AudioStop').addEventListener('click', stopPlayback);
    el('ffv2AudioRender').addEventListener('click', () => renderMaster(false).then(result => result && downloadBlob(result.blob)));
    el('ffv2AudioAddCue').addEventListener('click', addSelectedCue);
    el('ffv2AudioApplyDucking').addEventListener('click', applyDucking);
    el('ffv2AudioWaveform').addEventListener('click', event => {
      const found = selectedAudioClip();
      if (!found) return;
      const rect = event.currentTarget.getBoundingClientRect();
      const fraction = Math.max(0, Math.min(1, (event.clientX - rect.left) / Math.max(1, rect.width)));
      const frame = found.clip.start_frame + Math.round(fraction * found.clip.duration_frames);
      studio()?.setPlayhead?.(frame);
    });
    const player = el('ffv2AudioPlayer');
    player.addEventListener('pause', stopSync);
    player.addEventListener('ended', stopSync);
  }

  function refresh() {
    if (!studio()?.getProject?.()) return;
    const currentProject = project();
    const changed = ensureProjectAudio(currentProject);
    if (changed) markDirty();
    populateTrackOptions();
    populateCueAssets();
    syncClipControls();
    renderCueList();
    const ducking = currentProject.extensions?.ffv2_audio?.ducking || DEFAULT_DUCKING;
    el('ffv2AudioDucking').checked = Boolean(ducking.enabled);
    el('ffv2AudioDuckingAmount').value = String(ducking.amount_db);
  }

  function onPlayheadChange() {
    updateWaveformCursor();
  }

  function initialize() {
    if (!studio()?.getProject?.()) return;
    bindUI();
    ensureProjectAudio(project());
    refresh();
    document.addEventListener('ffv2:playhead', onPlayheadChange);
  }

  const api = {
    AUDIO_TYPES, DEFAULT_CLIP_AUDIO, DEFAULT_TRACK_AUDIO, DEFAULT_DUCKING,
    normalizeClipAudio, normalizeTrackAudio, ensureProjectAudio,
    getAutomationGain, setClipAudio, addGainKeyframe,
    resolveCueFrame, addCue, removeCue, getResolvedCues,
    waveformPeaks, renderWav, refresh, onPlayheadChange
  };
  root.FFV2Audio = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  if (root.document) document.addEventListener('ffv2:ready', initialize);
})(typeof globalThis !== 'undefined' ? globalThis : this);
