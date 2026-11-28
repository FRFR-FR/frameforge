/* FrameForge V2 core — portable project, timeline and media validation helpers.
 * No runtime network calls, paid APIs or third-party code are required.
 */
(function (root) {
  'use strict';

  const FORMAT = 'frameforge-project';
  const SCHEMA_VERSION = 2;
  const MAX_FILE_BYTES = 250 * 1024 * 1024;
  const HASH_LIMIT_BYTES = 32 * 1024 * 1024;

  const FORMATS = {
    image: {
      png: ['image/png'], jpg: ['image/jpeg'], jpeg: ['image/jpeg'],
      gif: ['image/gif'], webp: ['image/webp'], bmp: ['image/bmp'],
      avif: ['image/avif'], svg: ['image/svg+xml']
    },
    video: {
      mp4: ['video/mp4'], m4v: ['video/mp4', 'video/x-m4v'],
      mov: ['video/quicktime'], webm: ['video/webm'], ogv: ['video/ogg']
    },
    audio: {
      mp3: ['audio/mpeg', 'audio/mp3'], wav: ['audio/wav', 'audio/x-wav'],
      ogg: ['audio/ogg', 'application/ogg'], oga: ['audio/ogg', 'application/ogg'],
      flac: ['audio/flac', 'audio/x-flac'], m4a: ['audio/mp4', 'audio/x-m4a'],
      aac: ['audio/aac', 'audio/x-aac']
    },
    model3d: { glb: ['model/gltf-binary', 'application/octet-stream'], gltf: ['model/gltf+json', 'application/json'] }
  };

  const TRACK_TYPES = ['video', 'image', 'graphic', 'title', 'scene3d', 'audio', 'music', 'sfx', 'voiceover', 'effect', 'adjustment'];

  function makeId(prefix) {
    const uuid = root.crypto && typeof root.crypto.randomUUID === 'function'
      ? root.crypto.randomUUID()
      : Date.now().toString(36) + '-' + Math.random().toString(36).slice(2, 12);
    return (prefix ? prefix + '-' : '') + uuid;
  }

  function clone(value) {
    if (typeof structuredClone === 'function') return structuredClone(value);
    return JSON.parse(JSON.stringify(value));
  }

  function extensionOf(name) {
    const match = /\.([^.]+)$/.exec(String(name || '').toLowerCase());
    return match ? match[1] : '';
  }

  function classifyFile(file) {
    if (!file || typeof file.name !== 'string') throw new Error('Select a file to import.');
    if (file.size <= 0) throw new Error('The selected file is empty.');
    if (file.size > MAX_FILE_BYTES) throw new Error('File exceeds the 250 MB per-asset limit. Import a smaller or locally optimised version.');
    const extension = extensionOf(file.name);
    let category = '';
    for (const [kind, extensions] of Object.entries(FORMATS)) {
      if (Object.prototype.hasOwnProperty.call(extensions, extension)) {
        category = kind;
        break;
      }
    }
    if (!category) throw new Error('Unsupported file type. Supported: PNG, JPEG, GIF, WebP, BMP, AVIF, SVG, MP4, MOV, WebM, OGV, MP3, WAV, OGG, FLAC, M4A, AAC, GLB and glTF.');
    const allowedMimes = FORMATS[category][extension];
    const mime = String(file.type || '').toLowerCase();
    if (mime && mime !== 'application/octet-stream' && !allowedMimes.includes(mime)) {
      // Browsers sometimes report quicktime/mp4 variants differently; extension remains authoritative.
      const compatible = (category === 'video' && mime.startsWith('video/')) ||
        (category === 'audio' && mime.startsWith('audio/')) ||
        (category === 'image' && mime.startsWith('image/')) ||
        (category === 'model3d' && (mime.includes('gltf') || mime === 'application/json'));
      if (!compatible) throw new Error('File extension and MIME type do not match. The file was not imported.');
    }
    return { category, extension, mime: mime || allowedMimes[0] };
  }

  function verifySignature(extension, bytes) {
    const b = bytes instanceof Uint8Array ? bytes : new Uint8Array(bytes);
    const starts = (...values) => values.every((v, i) => b[i] === v);
    const ascii = (start, length) => String.fromCharCode(...b.slice(start, start + length));
    switch (extension) {
      case 'png': return starts(0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a) ? '' : 'PNG signature is invalid.';
      case 'jpg': case 'jpeg': return starts(0xff, 0xd8, 0xff) ? '' : 'JPEG signature is invalid.';
      case 'gif': return ['GIF87a', 'GIF89a'].includes(ascii(0, 6)) ? '' : 'GIF signature is invalid.';
      case 'webp': return ascii(0, 4) === 'RIFF' && ascii(8, 4) === 'WEBP' ? '' : 'WebP signature is invalid.';
      case 'bmp': return ascii(0, 2) === 'BM' ? '' : 'BMP signature is invalid.';
      case 'mp4': case 'm4v': case 'mov': return ascii(4, 4) === 'ftyp' ? '' : 'MP4/MOV container signature is invalid.';
      case 'webm': return starts(0x1a, 0x45, 0xdf, 0xa3) ? '' : 'WebM signature is invalid.';
      case 'ogv': case 'ogg': case 'oga': return ascii(0, 4) === 'OggS' ? '' : 'Ogg signature is invalid.';
      case 'wav': return ascii(0, 4) === 'RIFF' && ascii(8, 4) === 'WAVE' ? '' : 'WAV signature is invalid.';
      case 'mp3': return ascii(0, 3) === 'ID3' || (b[0] === 0xff && (b[1] & 0xe0) === 0xe0) ? '' : 'MP3 signature is invalid.';
      case 'flac': return ascii(0, 4) === 'fLaC' ? '' : 'FLAC signature is invalid.';
      case 'm4a': case 'aac': return ascii(4, 4) === 'ftyp' || (b[0] === 0xff && (b[1] & 0xf6) === 0xf0) ? '' : 'AAC/M4A signature is invalid.';
      case 'glb': return ascii(0, 4) === 'glTF' && new DataView(b.buffer, b.byteOffset, b.byteLength).getUint32(4, true) === 2 ? '' : 'GLB header or glTF version is invalid.';
      case 'svg': case 'gltf': return '';
      default: return 'Unsupported file extension.';
    }
  }

  function validateSvgText(text) {
    if (typeof DOMParser === 'undefined') {
      if (/<\s*script\b|<\s*foreignObject\b|\bon[a-z]+\s*=|(?:href|src)\s*=\s*["']\s*(?:https?:|javascript:|data:)/i.test(text)) {
        throw new Error('SVG contains active or external content and was rejected.');
      }
      return;
    }
    const doc = new DOMParser().parseFromString(text, 'image/svg+xml');
    if (doc.querySelector('parsererror') || !doc.documentElement || doc.documentElement.localName.toLowerCase() !== 'svg') {
      throw new Error('SVG markup is malformed.');
    }
    if (doc.querySelector('script,foreignObject,iframe,object,embed')) {
      throw new Error('SVG contains active content and was rejected.');
    }
    for (const element of Array.from(doc.querySelectorAll('*'))) {
      for (const attr of Array.from(element.attributes)) {
        const name = attr.name.toLowerCase();
        const value = attr.value.trim();
        if (name.startsWith('on')) throw new Error('SVG event handlers are not allowed.');
        if ((name === 'href' || name.endsWith(':href')) && value && !value.startsWith('#')) {
          throw new Error('SVG external references are not allowed. Embed local vector shapes instead.');
        }
        if (name === 'style' && /url\s*\(\s*['"]?(?:https?:|javascript:|data:)/i.test(value)) {
          throw new Error('SVG external styles/resources are not allowed.');
        }
      }
    }
  }

  function createDefaultProject(name, now) {
    const stamp = now || new Date().toISOString();
    const projectId = makeId('project');
    const tracks = [
      ['track-video', 'Video', 'video'],
      ['track-graphics', 'Graphics', 'graphic'],
      ['track-titles', 'Titles', 'title'],
      ['track-voiceover', 'Voiceover', 'voiceover'],
      ['track-music', 'Music', 'music'],
      ['track-sfx', 'Sound effects', 'sfx']
    ].map(([id, label, type], order) => ({
      id, name: label, type, order, enabled: true, muted: false, locked: false, clips: []
    }));
    return {
      format: FORMAT,
      schema_version: SCHEMA_VERSION,
      project: {
        id: projectId,
        name: String(name || 'Untitled V2 Project').slice(0, 200),
        description: 'FrameForge V2 editable multi-track project',
        author: '',
        created_at: stamp,
        updated_at: stamp
      },
      settings: {
        width: 1280, height: 720, fps: 30, color_space: 'srgb',
        pixel_aspect_ratio: 1, sample_rate: 48000, audio_channels: 2
      },
      assets: [],
      sequences: [{
        id: makeId('sequence'), name: 'Main', width: 1280, height: 720,
        fps: 30, duration_frames: 900, tracks
      }],
      creative_brief: {
        topic: 'Untitled video project', niche: 'unclassified', audience: '', platform: 'youtube_longform',
        target_duration_seconds: 30, tone: '', visual_direction: '', constraints: []
      },
      research: { sources: [], claims: [], visual_style_observations: [], researched_at: stamp },
      extensions: { editor_version: '2.0-foundation' }
    };
  }

  function getMainSequence(project) {
    if (!project || !Array.isArray(project.sequences) || !project.sequences.length) {
      throw new Error('Project has no editable sequence.');
    }
    return project.sequences[0];
  }

  function addTrack(project, type, name) {
    if (!TRACK_TYPES.includes(type)) throw new Error('Unsupported track type: ' + type);
    const sequence = getMainSequence(project);
    const track = {
      id: makeId('track'), name: String(name || type).slice(0, 200),
      type, order: sequence.tracks.length, enabled: true, muted: false, locked: false, clips: []
    };
    sequence.tracks.push(track);
    return track;
  }

  function trackForAssetType(type) {
    return ({ image: 'image', video: 'video', graphic: 'graphic', model3d: 'scene3d', audio: 'sfx' })[type] || 'graphic';
  }

  function findTrack(project, trackId) {
    const track = getMainSequence(project).tracks.find(item => item.id === trackId);
    if (!track) throw new Error('Timeline track was not found.');
    if (track.locked) throw new Error('This track is locked.');
    return track;
  }

  function assetToProjectRecord(asset) {
    return {
      id: asset.id,
      uri: 'indexeddb://assets/' + encodeURIComponent(asset.id),
      media_type: asset.media_type,
      label: asset.label || asset.file_name || asset.id,
      metadata: clone(asset.metadata || {}),
      provenance: clone(asset.provenance || { source_type: 'unknown' }),
      rights: clone(asset.rights || { status: 'pending', attribution_required: false }),
      tags: Array.isArray(asset.tags) ? [...asset.tags] : []
    };
  }

  function addAsset(project, asset) {
    if (!asset || !asset.id) throw new Error('Asset record needs a stable id.');
    const index = project.assets.findIndex(item => item.id === asset.id);
    const record = assetToProjectRecord(asset);
    if (index >= 0) project.assets[index] = record;
    else project.assets.push(record);
    return record;
  }

  function addAssetClip(project, assetId, trackId, startFrame, durationFrames) {
    const asset = project.assets.find(item => item.id === assetId);
    if (!asset) throw new Error('The asset is not part of this project.');
    const track = findTrack(project, trackId);
    const sequence = getMainSequence(project);
    const start = Math.max(0, Math.round(Number(startFrame) || 0));
    const length = Math.max(1, Math.round(Number(durationFrames) || sequence.fps * 5));
    const clip = {
      id: makeId('clip'), kind: 'asset', asset_id: assetId,
      start_frame: start, duration_frames: length, source_in_frame: 0,
      playback_rate: 1, enabled: true,
      transform: { position: [0, 0], scale: [1, 1], rotation_degrees: 0, opacity: 1, anchor: [0.5, 0.5] },
      keyframes: [], effects: []
    };
    track.clips.push(clip);
    sequence.duration_frames = Math.max(sequence.duration_frames, start + length);
    return clip;
  }

  function findClip(project, clipId) {
    for (const track of getMainSequence(project).tracks) {
      const clip = track.clips.find(item => item.id === clipId);
      if (clip) return { track, clip };
    }
    throw new Error('Timeline clip was not found.');
  }

  function moveClip(project, clipId, nextStart, snapFrames) {
    const { track, clip } = findClip(project, clipId);
    if (track.locked) throw new Error('This track is locked.');
    const snap = Math.max(1, Math.round(Number(snapFrames) || 1));
    const raw = Math.max(0, Math.round(Number(nextStart) || 0));
    clip.start_frame = Math.max(0, Math.round(raw / snap) * snap);
    const sequence = getMainSequence(project);
    sequence.duration_frames = Math.max(sequence.duration_frames, clip.start_frame + clip.duration_frames);
    return clip;
  }

  function trimClip(project, clipId, nextStart, nextDuration) {
    const { track, clip } = findClip(project, clipId);
    if (track.locked) throw new Error('This track is locked.');
    const start = Math.max(0, Math.round(Number(nextStart) || 0));
    const duration = Math.max(1, Math.round(Number(nextDuration) || 1));
    clip.start_frame = start;
    clip.duration_frames = duration;
    const sequence = getMainSequence(project);
    sequence.duration_frames = Math.max(sequence.duration_frames, start + duration);
    return clip;
  }

  function splitClip(project, clipId, atFrame) {
    const { track, clip } = findClip(project, clipId);
    if (track.locked) throw new Error('This track is locked.');
    const offset = Math.round(Number(atFrame) || 0) - clip.start_frame;
    if (offset < 1 || offset >= clip.duration_frames) throw new Error('Playhead must be inside the clip to split it.');
    const second = clone(clip);
    second.id = makeId('clip');
    second.start_frame = clip.start_frame + offset;
    second.duration_frames = clip.duration_frames - offset;
    second.source_in_frame = (clip.source_in_frame || 0) + offset;
    clip.duration_frames = offset;
    const index = track.clips.indexOf(clip);
    track.clips.splice(index + 1, 0, second);
    return second;
  }

  function duplicateClip(project, clipId) {
    const { track, clip } = findClip(project, clipId);
    if (track.locked) throw new Error('This track is locked.');
    const copyOfClip = clone(clip);
    copyOfClip.id = makeId('clip');
    copyOfClip.start_frame = clip.start_frame + clip.duration_frames;
    track.clips.push(copyOfClip);
    const sequence = getMainSequence(project);
    sequence.duration_frames = Math.max(sequence.duration_frames, copyOfClip.start_frame + copyOfClip.duration_frames);
    return copyOfClip;
  }

  function deleteClip(project, clipId) {
    const { track, clip } = findClip(project, clipId);
    if (track.locked) throw new Error('This track is locked.');
    track.clips = track.clips.filter(item => item.id !== clip.id);
  }

  function validateProject(project) {
    const errors = [];
    if (!project || project.format !== FORMAT || project.schema_version !== SCHEMA_VERSION) {
      return ['Unsupported FrameForge project format or schema version.'];
    }
    if (!project.project || !project.settings || !Array.isArray(project.assets) || !Array.isArray(project.sequences) || !project.sequences.length) {
      return ['Project is missing required metadata, settings, assets or sequences.'];
    }
    const sequence = project.sequences[0];
    if (!Array.isArray(sequence.tracks)) return ['Sequence tracks must be an array.'];
    const assetIds = new Set();
    for (const asset of project.assets) {
      if (assetIds.has(asset.id)) errors.push('Duplicate asset id: ' + asset.id);
      assetIds.add(asset.id);
    }
    const trackIds = new Set();
    const clipIds = new Set();
    for (const track of sequence.tracks) {
      if (trackIds.has(track.id)) errors.push('Duplicate track id: ' + track.id);
      trackIds.add(track.id);
      for (const clip of track.clips || []) {
        if (clipIds.has(clip.id)) errors.push('Duplicate clip id: ' + clip.id);
        clipIds.add(clip.id);
        if (clip.kind === 'asset' && !assetIds.has(clip.asset_id)) errors.push('Clip references missing asset: ' + clip.asset_id);
        if (!Number.isInteger(clip.start_frame) || clip.start_frame < 0) errors.push('Clip has an invalid start frame: ' + clip.id);
        if (!Number.isInteger(clip.duration_frames) || clip.duration_frames < 1) errors.push('Clip has an invalid duration: ' + clip.id);
        if (Number.isInteger(clip.start_frame) && Number.isInteger(clip.duration_frames) &&
            clip.start_frame + clip.duration_frames > sequence.duration_frames) {
          errors.push('Clip exceeds sequence duration: ' + clip.id);
        }
      }
    }
    return errors;
  }

  const api = {
    FORMAT, SCHEMA_VERSION, MAX_FILE_BYTES, HASH_LIMIT_BYTES, FORMATS, TRACK_TYPES,
    makeId, clone, extensionOf, classifyFile, verifySignature, validateSvgText,
    createDefaultProject, getMainSequence, addTrack, trackForAssetType,
    assetToProjectRecord, addAsset, addAssetClip, findClip, moveClip, trimClip,
    splitClip, duplicateClip, deleteClip, validateProject
  };
  root.FFV2Core = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
