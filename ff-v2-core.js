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
      case 'glb': return b.length >= 12 && ascii(0, 4) === 'glTF' && new DataView(b.buffer, b.byteOffset, b.byteLength).getUint32(4, true) === 2 ? '' : 'GLB header or glTF version is invalid.';
      case 'svg': case 'gltf': return '';
      default: return 'Unsupported file extension.';
    }
  }

  function validateSvgText(text) {
    if (typeof DOMParser === 'undefined') {
      if (/<\s*script\b|<\s*foreignObject\b|\bon[a-z]+\s*=|@import|url\s*\(\s*['"]?(?!#)|(?:href|src)\s*=\s*["']\s*(?:https?:|javascript:|data:)/i.test(text)) {
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
    for (const styleElement of Array.from(doc.querySelectorAll('style'))) {
      if (/@import|url\s*\(\s*['"]?(?!#)/i.test(styleElement.textContent || '')) {
        throw new Error('SVG external style imports/resources are not allowed.');
      }
    }
    for (const element of Array.from(doc.querySelectorAll('*'))) {
      for (const attr of Array.from(element.attributes)) {
        const name = attr.name.toLowerCase();
        const value = attr.value.trim();
        if (name.startsWith('on')) throw new Error('SVG event handlers are not allowed.');
        if ((name === 'href' || name.endsWith(':href')) && value && !value.startsWith('#')) {
          throw new Error('SVG external references are not allowed. Embed local vector shapes instead.');
        }
        if (name === 'style' && /url\s*\(\s*['"]?(?!#)/i.test(value)) {
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
      ['track-images', 'Images / cut-outs', 'image'],
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
        pixel_aspect_ratio: 1, sample_rate: 48000, audio_channels: 2,
        post_processing: { renderer: 'auto', fallback: 'canvas2d', passes: [] }
      },
      assets: [],
      sequences: [{
        id: makeId('sequence'), name: 'Main', width: 1280, height: 720,
        fps: 30, duration_frames: 900, tracks,
        scene3d: {
          camera: { projection:'perspective', position:[6,4,7], target:[0,0,0], up:[0,1,0], fov:45, orthographic_height:8, near:0.1, far:1000 },
          lights: [
            { id:'light-ambient', type:'ambient', color:'#ffffff', intensity:0.45 },
            { id:'light-key', type:'directional', color:'#ffffff', intensity:1.1, direction:[-0.55,0.78,0.48] }
          ],
          environment: { background:'#101c2b', transparent:false },
          render: { tone_mapping:'aces', exposure:1, shadows:true }
        }
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
      transform: { position: [0, 0], scale: [1, 1], rotation_degrees: 0, opacity: 1, anchor: [0.5, 0.5], fit: 'contain' },
      blend_mode: 'normal',
      keyframes: [], effects: [],
      ...(track.type === 'scene3d' || asset.media_type === 'model3d' ? {
        transform3d: { position:[0,0,0], rotation:[0,0,0], scale:[1,1,1] },
        animation: { enabled:true, clip_name:'', time_scale:1, loop:true, start_frame:start },
        constraints: []
      } : {})
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
    const isObject = value => value !== null && typeof value === 'object' && !Array.isArray(value);
    if (!isObject(project) || project.format !== FORMAT || project.schema_version !== SCHEMA_VERSION) {
      return ['Unsupported FrameForge project format or schema version.'];
    }
    if (!isObject(project.project) || !isObject(project.settings) ||
        !Array.isArray(project.assets) || !Array.isArray(project.sequences) || !project.sequences.length) {
      return ['Project is missing required metadata, settings, assets or sequences.'];
    }
    const settings = project.settings;
    if (!Number.isInteger(settings.width) || settings.width < 1 ||
        !Number.isInteger(settings.height) || settings.height < 1 ||
        !Number.isFinite(settings.fps) || settings.fps <= 0) {
      errors.push('Project output settings contain invalid dimensions or frame rate.');
    }

    const assetIds = new Set();
    for (const asset of project.assets) {
      if (!isObject(asset) || typeof asset.id !== 'string' || !asset.id) {
        errors.push('Every project asset must be an object with a stable id.');
        continue;
      }
      if (assetIds.has(asset.id)) errors.push('Duplicate asset id: ' + asset.id);
      assetIds.add(asset.id);
    }

    const sequenceIds = new Set();
    const trackIds = new Set();
    const clipIds = new Set();
    for (const sequence of project.sequences) {
      if (!isObject(sequence)) {
        errors.push('Every sequence must be an object.');
        continue;
      }
      if (typeof sequence.id !== 'string' || !sequence.id) errors.push('Sequence is missing a stable id.');
      else if (sequenceIds.has(sequence.id)) errors.push('Duplicate sequence id: ' + sequence.id);
      sequenceIds.add(sequence.id);
      if (!Number.isInteger(sequence.duration_frames) || sequence.duration_frames < 1) {
        errors.push('Sequence ' + sequence.id + ' has an invalid duration.');
      }
      if (!Array.isArray(sequence.tracks)) {
        errors.push('Sequence ' + sequence.id + ' tracks must be an array.');
        continue;
      }
      for (const track of sequence.tracks) {
        if (!isObject(track)) {
          errors.push('Every track must be an object.');
          continue;
        }
        if (typeof track.id !== 'string' || !track.id) errors.push('Track is missing a stable id.');
        else if (trackIds.has(track.id)) errors.push('Duplicate track id: ' + track.id);
        trackIds.add(track.id);
        if (!Array.isArray(track.clips)) {
          errors.push('Track ' + track.id + ' clips must be an array.');
          continue;
        }
        for (const clip of track.clips) {
          if (!isObject(clip)) {
            errors.push('Every clip must be an object.');
            continue;
          }
          if (typeof clip.id !== 'string' || !clip.id) errors.push('Clip is missing a stable id.');
          else if (clipIds.has(clip.id)) errors.push('Duplicate clip id: ' + clip.id);
          clipIds.add(clip.id);
          if (clip.kind === 'asset' && !assetIds.has(clip.asset_id)) {
            errors.push('Clip references missing asset: ' + clip.asset_id);
          }
          if (!Number.isInteger(clip.start_frame) || clip.start_frame < 0) {
            errors.push('Clip has an invalid start frame: ' + clip.id);
          }
          if (!Number.isInteger(clip.duration_frames) || clip.duration_frames < 1) {
            errors.push('Clip has an invalid duration: ' + clip.id);
          }
          if (Number.isInteger(clip.start_frame) && Number.isInteger(clip.duration_frames) &&
              Number.isInteger(sequence.duration_frames) &&
              clip.start_frame + clip.duration_frames > sequence.duration_frames) {
            errors.push('Clip exceeds sequence duration: ' + clip.id);
          }
        }
      }
    }
    const clipsById = new Map();
    for (const sequence of project.sequences) {
      for (const track of sequence.tracks || []) {
        for (const clip of track.clips || []) {
          clipsById.set(clip.id, clip);
          if (clip.blend_mode && !BLEND_MODES.includes(clip.blend_mode)) errors.push('Clip has an unsupported blend mode: ' + clip.id);
          if (clip.parent_clip_id && !project.sequences.some(other => (other.tracks || []).some(t => (t.clips || []).some(c => c.id === clip.parent_clip_id)))) {
            errors.push('Clip references a missing parent layer: ' + clip.id);
          }
          if (clip.mask && ['alpha','luma'].includes(clip.mask.type) && !assetIds.has(clip.mask.asset_id)) {
            errors.push('Clip mask references a missing matte asset: ' + clip.id);
          }
        }
      }
    }
    for (const clip of clipsById.values()) {
      const visited = new Set([clip.id]);
      let parentId = clip.parent_clip_id;
      while (parentId) {
        if (visited.has(parentId)) { errors.push('Clip parenting contains a cycle: ' + clip.id); break; }
        visited.add(parentId);
        parentId = clipsById.get(parentId)?.parent_clip_id;
      }
    }

    return errors;
  }


  const BLEND_MODES = ['normal','multiply','screen','overlay','darken','lighten','color-dodge','color-burn','hard-light','soft-light','difference','exclusion','hue','saturation','color','luminosity','lighter','destination-over'];
  const KEYFRAME_PROPERTIES = ['position.x','position.y','scale.x','scale.y','rotation_degrees','opacity','anchor.x','anchor.y'];
  const ANIMATABLE_PROPERTIES = KEYFRAME_PROPERTIES.concat(['playback_rate','position3d.x','position3d.y','position3d.z','rotation3d.x','rotation3d.y','rotation3d.z','scale3d.x','scale3d.y','scale3d.z']);

  function addGraphicClip(project, trackId, generatorType, parameters, startFrame, durationFrames) {
    if (!['text','shape','svg','particles'].includes(generatorType)) throw new Error('Unsupported generated graphic type.');
    const track = findTrack(project, trackId);
    if (!['graphic','title'].includes(track.type)) throw new Error('Generated graphics require a Graphics or Titles track.');
    const sequence = getMainSequence(project);
    const defaults = generatorType === 'text'
      ? { text: 'Your title', font_family: 'Arial, sans-serif', font_size: 72, font_weight: 700, color: '#ffffff', align: 'center', box_width: 900, box_height: 180 }
      : generatorType === 'shape'
        ? { shape: 'rect', width: 420, height: 220, fill: '#287fbd', stroke: '#ffffff', stroke_width: 0, radius: 18 }
        : generatorType === 'svg'
        ? { svg: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><circle cx="50" cy="50" r="42" fill="#287fbd"/></svg>' }
        : { preset: 'sparks', count: 72, seed: 1337, speed: 1, size: 3.5, color: '#ffc46b', spread: 1, gravity: 72, life_seconds: 1.8 };
    const next = Object.assign({}, defaults, clone(parameters || {}));
    if (generatorType === 'svg') validateSvgText(next.svg);
    const start = Math.max(0, Math.round(Number(startFrame) || 0));
    const duration = Math.max(1, Math.round(Number(durationFrames) || sequence.fps * 3));
    const clip = {
      id: makeId('clip'), kind: 'generated', generator: { type: generatorType, parameters: next },
      start_frame: start, duration_frames: duration, source_in_frame: 0,
      playback_rate: 1, enabled: true,
      transform: { position: [0, 0], scale: [1, 1], rotation_degrees: 0, opacity: 1, anchor: [0.5, 0.5], fit: 'contain' },
      blend_mode: 'normal', keyframes: [], effects: []
    };
    track.clips.push(clip);
    sequence.duration_frames = Math.max(sequence.duration_frames, start + duration);
    return clip;
  }

  function setClipTransform(project, clipId, updates) {
    const found = findClip(project, clipId);
    if (found.track.locked) throw new Error('This track is locked.');
    const current = Object.assign({ position: [0, 0], scale: [1, 1], rotation_degrees: 0, opacity: 1, anchor: [0.5, 0.5], fit: 'contain' }, clone(found.clip.transform || {}));
    const next = clone(current);
    for (const [key, value] of Object.entries(updates || {})) {
      if (key === 'position' || key === 'scale' || key === 'anchor') {
        if (!Array.isArray(value) || value.length !== 2 || value.some(item => !Number.isFinite(Number(item)))) {
          throw new Error('Transform ' + key + ' must contain two finite numbers.');
        }
        next[key] = value.map(Number);
      } else if (key === 'rotation_degrees') {
        next[key] = Number(value);
        if (!Number.isFinite(next[key])) throw new Error('Rotation must be a finite number.');
      } else if (key === 'opacity') {
        next[key] = Number(value);
        if (!Number.isFinite(next[key]) || next[key] < 0 || next[key] > 1) throw new Error('Opacity must be between 0 and 1.');
      } else if (key === 'fit') {
        if (!['contain','cover','stretch'].includes(value)) throw new Error('Fit must be contain, cover or stretch.');
        next.fit = value;
      } else if (key === 'crop') {
        if (value !== null && (!value || !['x','y','width','height'].every(k => Number.isFinite(Number(value[k]))) ||
            Number(value.x) < 0 || Number(value.y) < 0 || Number(value.width) <= 0 || Number(value.height) <= 0 ||
            Number(value.x) + Number(value.width) > 1 || Number(value.y) + Number(value.height) > 1)) {
          throw new Error('Crop must be a normalized rectangle inside the source image.');
        }
        if (value === null) delete next.crop;
        else next.crop = { x: Number(value.x), y: Number(value.y), width: Number(value.width), height: Number(value.height) };
      } else {
        throw new Error('Unsupported transform property: ' + key);
      }
    }
    found.clip.transform = next;
    return found.clip;
  }

  function setClipParent(project, clipId, parentClipId) {
    const found = findClip(project, clipId);
    if (found.track.locked) throw new Error('This track is locked.');
    if (!parentClipId) {
      delete found.clip.parent_clip_id;
      return found.clip;
    }
    if (parentClipId === clipId) throw new Error('A clip cannot parent itself.');
    const parent = findClip(project, parentClipId);
    if (['audio','music','sfx','voiceover'].includes(parent.track.type)) throw new Error('An audio clip cannot be a visual parent.');
    let cursor = parent.clip;
    const seen = new Set([clipId]);
    while (cursor) {
      if (seen.has(cursor.id)) throw new Error('Parenting would create a cycle.');
      seen.add(cursor.id);
      if (!cursor.parent_clip_id) break;
      cursor = findClip(project, cursor.parent_clip_id).clip;
    }
    found.clip.parent_clip_id = parentClipId;
    return found.clip;
  }

  function setClipMask(project, clipId, mask) {
    const found = findClip(project, clipId);
    if (found.track.locked) throw new Error('This track is locked.');
    if (!mask || mask.type === 'none') {
      delete found.clip.mask;
      return found.clip;
    }
    const next = clone(mask);
    if (!['shape','alpha','luma'].includes(next.type)) throw new Error('Mask type must be shape, alpha or luma.');
    next.feather = Math.max(0, Math.min(100, Number(next.feather) || 0));
    next.invert = Boolean(next.invert);
    if (next.type === 'shape') {
      if (!['rect','ellipse'].includes(next.shape)) throw new Error('Shape masks currently support rectangles and ellipses.');
      const bounds = next.bounds || { x: 0, y: 0, width: 1, height: 1 };
      if (!['x','y','width','height'].every(k => Number.isFinite(Number(bounds[k]))) ||
          Number(bounds.x) < 0 || Number(bounds.y) < 0 || Number(bounds.width) <= 0 || Number(bounds.height) <= 0 ||
          Number(bounds.x) + Number(bounds.width) > 1 || Number(bounds.y) + Number(bounds.height) > 1) {
        throw new Error('Mask bounds must be a normalized rectangle inside the output frame.');
      }
      next.bounds = { x: Number(bounds.x), y: Number(bounds.y), width: Number(bounds.width), height: Number(bounds.height) };
    } else {
      if (!next.asset_id || !project.assets.some(asset => asset.id === next.asset_id)) throw new Error('Choose a matte asset that belongs to this project.');
      next.channel = next.type === 'luma' ? 'luma' : 'alpha';
    }
    found.clip.mask = next;
    return found.clip;
  }

  function applyKeyframeValue(target, property, value) {
    const parts = property.split('.');
    if (parts.length === 2 && ['position','scale','anchor'].includes(parts[0]) && ['x','y'].includes(parts[1])) {
      const index = parts[1] === 'x' ? 0 : 1;
      if (!Array.isArray(target[parts[0]])) target[parts[0]] = [0, 0];
      target[parts[0]][index] = Number(value);
    } else if (property === 'rotation_degrees' || property === 'opacity') {
      target[property] = Number(value);
    }
  }

  function setKeyframe(project, clipId, property, globalFrame, value, interpolation, bezier) {
    const found = findClip(project, clipId);
    if (found.track.locked) throw new Error('This track is locked.');
    if (!ANIMATABLE_PROPERTIES.includes(property)) throw new Error('Unsupported keyframe property.');
    const localFrame = Math.round(Number(globalFrame) || 0) - found.clip.start_frame;
    if (localFrame < 0 || localFrame > found.clip.duration_frames) throw new Error('Move the playhead inside the selected clip to add a keyframe.');
    if (typeof value === 'number' && !Number.isFinite(value)) throw new Error('Keyframe value must be finite.');
    const mode = interpolation || 'ease_in_out';
    if (!['step','linear','ease_in','ease_out','ease_in_out','bezier'].includes(mode)) throw new Error('Unsupported keyframe interpolation.');
    const key = { property, frame: localFrame, value: clone(value), interpolation: mode };
    if (mode === 'bezier') {
      const curve = Array.isArray(bezier) && bezier.length === 4 ? bezier.map(Number) : [0.25, 0.1, 0.25, 1];
      if (curve.some(n => !Number.isFinite(n)) || curve.some(n => n < 0 || n > 1)) throw new Error('Bezier controls must be in the 0–1 range.');
      key.bezier = curve;
    }
    found.clip.keyframes = Array.isArray(found.clip.keyframes) ? found.clip.keyframes : [];
    const existing = found.clip.keyframes.findIndex(item => item.property === property && item.frame === localFrame);
    if (existing >= 0) found.clip.keyframes[existing] = key;
    else found.clip.keyframes.push(key);
    found.clip.keyframes.sort((a, b) => a.frame - b.frame || a.property.localeCompare(b.property));
    return key;
  }


  function setClipPlaybackRate(project, clipId, rate) {
    const found = findClip(project, clipId);
    if (found.track.locked) throw new Error('This track is locked.');
    const next = Number(rate);
    if (!Number.isFinite(next) || next < 0.05 || next > 8) throw new Error('Playback rate must be between 0.05× and 8×.');
    found.clip.playback_rate = next;
    return found.clip;
  }

  function evaluateClipPlaybackRate(clip, globalFrame) {
    const base = Number(clip.playback_rate) > 0 ? Number(clip.playback_rate) : 1;
    const localFrame = Math.max(0,Math.round(Number(globalFrame)||0)-clip.start_frame);
    return Math.max(0.05,Math.min(8,Number(evaluateKeyframes({keyframes:clip.keyframes||[]},'playback_rate',localFrame,base))));
  }

  function cubicAt(t, p1, p2) {
    const inv = 1 - t;
    return 3 * inv * inv * t * p1 + 3 * inv * t * t * p2 + t * t * t;
  }

  function cubicBezierEase(progress, curve) {
    const p = Math.max(0, Math.min(1, progress));
    const [x1,y1,x2,y2] = curve || [0.25,0.1,0.25,1];
    let t = p;
    for (let i = 0; i < 8; i++) {
      const estimate = cubicAt(t, x1, x2) - p;
      const derivative = 3 * (1 - t) * (1 - t) * x1 +
        6 * (1 - t) * t * (x2 - x1) + 3 * t * t * (1 - x2);
      if (Math.abs(derivative) < 1e-6) break;
      t = Math.max(0, Math.min(1, t - estimate / derivative));
    }
    return cubicAt(t, y1, y2);
  }

  function interpolateValue(a, b, progress) {
    if (typeof a === 'number' && typeof b === 'number') return a + (b - a) * progress;
    if (Array.isArray(a) && Array.isArray(b) && a.length === b.length) return a.map((v, i) => interpolateValue(v, b[i], progress));
    return progress < 1 ? clone(a) : clone(b);
  }

  function evaluateKeyframes(clip, property, localFrame, fallback) {
    const keys = (clip.keyframes || []).filter(item => item.property === property).sort((a, b) => a.frame - b.frame);
    if (!keys.length) return clone(fallback);
    if (localFrame <= keys[0].frame) return clone(keys[0].value);
    if (localFrame >= keys[keys.length - 1].frame) return clone(keys[keys.length - 1].value);
    let left = keys[0], right = keys[keys.length - 1];
    for (let i = 0; i < keys.length - 1; i++) {
      if (localFrame >= keys[i].frame && localFrame <= keys[i + 1].frame) {
        left = keys[i]; right = keys[i + 1]; break;
      }
    }
    if (left.interpolation === 'step') return clone(left.value);
    const raw = (localFrame - left.frame) / Math.max(1, right.frame - left.frame);
    let eased = raw;
    if (left.interpolation === 'ease_in') eased = raw * raw;
    else if (left.interpolation === 'ease_out') eased = 1 - (1 - raw) * (1 - raw);
    else if (left.interpolation === 'ease_in_out') eased = raw * raw * (3 - 2 * raw);
    else if (left.interpolation === 'bezier') eased = cubicBezierEase(raw, left.bezier);
    return interpolateValue(left.value, right.value, eased);
  }

  function evaluateClipTransform(clip, globalFrame) {
    const transform = Object.assign({ position: [0,0], scale: [1,1], rotation_degrees: 0, opacity: 1, anchor: [0.5,0.5], fit: 'contain' }, clone(clip.transform || {}));
    const localFrame = Math.max(0, Math.round(Number(globalFrame) || 0) - clip.start_frame);
    for (const property of KEYFRAME_PROPERTIES) {
      const fallback = property === 'rotation_degrees' || property === 'opacity'
        ? transform[property]
        : transform[property.split('.')[0]][property.endsWith('.x') ? 0 : 1];
      applyKeyframeValue(transform, property, evaluateKeyframes(clip, property, localFrame, fallback));
    }
    transform.opacity = Math.max(0, Math.min(1, Number(transform.opacity)));
    return transform;
  }

  function getActiveVisualClips(project, frame) {
    const sequence = getMainSequence(project);
    const visualTypes = new Set(['video','image','graphic','title','scene3d','effect','adjustment']);
    return sequence.tracks
      .filter(track => track.enabled !== false && visualTypes.has(track.type))
      .flatMap(track => (track.clips || []).filter(clip =>
        clip.enabled !== false && frame >= clip.start_frame && frame < clip.start_frame + clip.duration_frames
      ).map(clip => ({ track, clip })))
      .sort((a, b) => (a.track.order - b.track.order) || a.clip.start_frame - b.clip.start_frame);
  }


  const PARTICLE_PRESETS = ['sparks','dust','embers','magic','confetti'];
  const CLIP_EFFECT_TYPES = ['blur','glow','vignette','brightness-contrast','saturation','light-rays','depth-of-field','chromatic-aberration','glitch','ripple','shake','motion-blur'];
  const POST_PROCESS_TYPES = ['brightness-contrast','saturation','vignette','blur','glow','light-rays','depth-of-field','chromatic-aberration','glitch','ripple','shake','motion-blur','custom'];
  const TRANSITION_TYPES = ['crossfade','fade','wipe','zoom','whip_pan','radial','hypnosis_wheel','swirl_warp','glitch'];


  const POST_PROCESS_PRESETS = {
    cinematic: [
      ['brightness-contrast',{brightness:0,contrast:1.12,intensity:0.55}],
      ['saturation',{saturation:0.88,intensity:0.55}],
      ['vignette',{radius:0.68,strength:0.28,intensity:0.85}]
    ],
    soft_glow: [
      ['glow',{radius:14,strength:0.42,intensity:0.8}],
      ['light-rays',{strength:0.2,rays:14,intensity:0.45}]
    ],
    noir: [
      ['saturation',{saturation:0,intensity:1}],
      ['brightness-contrast',{brightness:-0.02,contrast:1.24,intensity:0.7}],
      ['vignette',{radius:0.65,strength:0.4,intensity:0.9}]
    ],
    documentary: [
      ['brightness-contrast',{brightness:0.015,contrast:1.06,intensity:0.5}],
      ['saturation',{saturation:0.94,intensity:0.45}]
    ],
    dream_haze: [
      ['blur',{radius:1.2,intensity:0.4}],
      ['glow',{radius:18,strength:0.25,intensity:0.9}],
      ['vignette',{radius:0.76,strength:0.15,intensity:0.45}]
    ]
  };

  function applyPostProcessPreset(project, presetName) {
    const preset = POST_PROCESS_PRESETS[presetName];
    if (!preset) throw new Error('Unknown post-processing preset.');
    return preset.map(([type,parameters])=>addPostProcessPass(project,type,parameters));
  }

  function addPostProcessPass(project, type, parameters) {
    if (!POST_PROCESS_TYPES.includes(type)) throw new Error('Unsupported post-processing pass: ' + type);
    const settings = project.settings.post_processing || (project.settings.post_processing = { renderer: 'auto', fallback: 'canvas2d', passes: [] });
    if (!Array.isArray(settings.passes)) settings.passes = [];
    const defaults = {
      'brightness-contrast': { brightness: 0, contrast: 1, intensity: 1 },
      saturation: { saturation: 1, intensity: 1 },
      vignette: { strength: 0.35, radius: 0.72, intensity: 1 },
      blur: { radius: 2, intensity: 1 },
      glow: { strength: 0.45, radius: 12, intensity: 1 },
      'light-rays': { strength: 0.3, angle: 0, intensity: 1 },
      'depth-of-field': { blur_radius: 7, focus_radius: 0.24, intensity: 0.8 },
      'chromatic-aberration': { amount: 2, intensity: 1 },
      glitch: { amount: 0.35, seed: 7, intensity: 1 },
      ripple: { amount: 0.25, frequency: 8, intensity: 1 },
      shake: { amount: 5, seed: 13, intensity: 1 },
      'motion-blur': { amount: 4, intensity: 1 },
      custom: { fragment: '', intensity: 1 }
    };
    const pass = {
      id: makeId('pass'), type, enabled: true,
      parameters: Object.assign({}, defaults[type], clone(parameters || {})),
      keyframes: []
    };
    settings.passes.push(pass);
    return pass;
  }

  function removePostProcessPass(project, passId) {
    const passes = project.settings.post_processing?.passes || [];
    project.settings.post_processing.passes = passes.filter(pass => pass.id !== passId);
  }

  function setPostProcessRenderer(project, renderer) {
    if (!['auto','webgl','canvas2d'].includes(renderer)) throw new Error('Renderer must be auto, webgl or canvas2d.');
    const settings = project.settings.post_processing || (project.settings.post_processing = { renderer: 'auto', fallback: 'canvas2d', passes: [] });
    settings.renderer = renderer;
    settings.fallback = 'canvas2d';
    return settings;
  }

  function setClipEffect(project, clipId, type, parameters) {
    if (!CLIP_EFFECT_TYPES.includes(type)) throw new Error('Unsupported clip effect: ' + type);
    const found = findClip(project, clipId);
    if (found.track.locked) throw new Error('This track is locked.');
    found.clip.effects = Array.isArray(found.clip.effects) ? found.clip.effects : [];
    let effect = found.clip.effects.find(item => item.type === type);
    if (!effect) {
      effect = { id: makeId('effect'), type, enabled: true, parameters: {}, keyframes: [] };
      found.clip.effects.push(effect);
    }
    effect.enabled = true;
    effect.parameters = Object.assign({}, effect.parameters || {}, clone(parameters || {}));
    effect.keyframes = Array.isArray(effect.keyframes) ? effect.keyframes : [];
    return effect;
  }

  function setEffectParameterKeyframe(project, clipId, effectId, property, globalFrame, value, interpolation) {
    const found = findClip(project, clipId);
    if (found.track.locked) throw new Error('This track is locked.');
    const effect = (found.clip.effects || []).find(item => item.id === effectId);
    if (!effect) throw new Error('Effect was not found on this clip.');
    if (!['intensity','amount','radius','strength','saturation','brightness','contrast','frequency'].includes(property)) {
      throw new Error('Unsupported animated effect parameter.');
    }
    const local = Math.round(Number(globalFrame) || 0) - found.clip.start_frame;
    if (local < 0 || local > found.clip.duration_frames) throw new Error('Playhead must be inside the clip to keyframe an effect.');
    const interpolationMode = interpolation || 'ease_in_out';
    if (!['step','linear','ease_in','ease_out','ease_in_out','bezier'].includes(interpolationMode)) throw new Error('Unsupported keyframe interpolation.');
    effect.keyframes = Array.isArray(effect.keyframes) ? effect.keyframes : [];
    const record = { property, frame: local, value: Number(value), interpolation: interpolationMode };
    if (!Number.isFinite(record.value)) throw new Error('Effect keyframe value must be finite.');
    const existing = effect.keyframes.findIndex(key => key.property === property && key.frame === local);
    if (existing >= 0) effect.keyframes[existing] = record;
    else effect.keyframes.push(record);
    effect.keyframes.sort((a,b) => a.frame-b.frame);
    return record;
  }

  function evaluateEffectParameters(effect, localFrame) {
    const parameters = clone(effect.parameters || {});
    for (const property of ['intensity','amount','radius','strength','saturation','brightness','contrast','frequency']) {
      if (Number.isFinite(Number(parameters[property]))) {
        parameters[property] = evaluateKeyframes({ keyframes: effect.keyframes || [] }, property, localFrame, Number(parameters[property]));
      }
    }
    return parameters;
  }

  function setClipTransition(project, clipId, edge, transition) {
    const found = findClip(project, clipId);
    if (found.track.locked) throw new Error('This track is locked.');
    if (!['in','out'].includes(edge)) throw new Error('Transition edge must be in or out.');
    if (!transition || !TRANSITION_TYPES.includes(transition.type)) throw new Error('Choose a supported transition.');
    const duration = Math.max(1, Math.min(found.clip.duration_frames, Math.round(Number(transition.duration_frames) || 1)));
    const direction = transition.direction || 'right';
    if (!['in','out','left','right','up','down','clockwise','counterclockwise'].includes(direction)) {
      throw new Error('Unsupported transition direction.');
    }
    const record = {
      type: transition.type, duration_frames: duration, direction,
      parameters: Object.assign({ intensity: 1, segments: 12 }, clone(transition.parameters || {}))
    };
    found.clip[edge === 'in' ? 'transition_in' : 'transition_out'] = record;
    return record;
  }



  function default3DSceneSettings() {
    return {
      camera: { projection:'perspective', position:[6,4,7], target:[0,0,0], up:[0,1,0], fov:45, orthographic_height:8, near:0.1, far:1000 },
      lights: [
        { id:makeId('light'), type:'ambient', color:'#ffffff', intensity:0.45 },
        { id:makeId('light'), type:'directional', color:'#ffffff', intensity:1.1, direction:[-0.55,0.78,0.48] }
      ],
      environment: { background:'#101c2b', transparent:false },
      render: { tone_mapping:'aces', exposure:1, shadows:true }
    };
  }

  function set3DSceneSettings(project, updates) {
    const sequence=getMainSequence(project);
    sequence.scene3d=sequence.scene3d||default3DSceneSettings();
    const settings=sequence.scene3d;
    const next=clone(settings);
    if(updates.camera){
      const camera=Object.assign({},next.camera,clone(updates.camera));
      if(!['perspective','orthographic'].includes(camera.projection)) throw new Error('3D camera projection must be perspective or orthographic.');
      for(const key of ['position','target','up']){
        if(!Array.isArray(camera[key])||camera[key].length!==3||camera[key].some(n=>!Number.isFinite(Number(n)))) throw new Error('3D camera '+key+' must have three finite coordinates.');
        camera[key]=camera[key].map(Number);
      }
      if(!Number.isFinite(Number(camera.fov))||camera.fov<10||camera.fov>120) throw new Error('3D camera FOV must be between 10 and 120 degrees.');
      if(!Number.isFinite(Number(camera.orthographic_height))||camera.orthographic_height<=0) throw new Error('Orthographic camera height must be positive.');
      if(!Number.isFinite(Number(camera.near))||!Number.isFinite(Number(camera.far))||camera.near<=0||camera.far<=camera.near) throw new Error('3D camera clipping planes are invalid.');
      next.camera=camera;
    }
    if(updates.lights){
      if(!Array.isArray(updates.lights)||updates.lights.length>32) throw new Error('A 3D scene supports up to 32 lights.');
      next.lights=updates.lights.map(light=>{
        if(!['ambient','directional','point','spot'].includes(light.type)) throw new Error('Unsupported 3D light type.');
        const copy=Object.assign({id:makeId('light'),color:'#ffffff',intensity:1},clone(light));
        copy.intensity=Math.max(0,Math.min(100,Number(copy.intensity)||0));
        if(copy.position) copy.position=copy.position.map(Number);
        if(copy.direction) copy.direction=copy.direction.map(Number);
        return copy;
      });
    }
    if(updates.environment){
      const environment=Object.assign({},next.environment,clone(updates.environment));
      if(environment.background!==undefined && environment.background!==null && typeof environment.background!=='string') throw new Error('3D background must be a colour or null.');
      next.environment=environment;
    }
    if(updates.render){
      const render=Object.assign({},next.render,clone(updates.render));
      if(!['none','linear','aces'].includes(render.tone_mapping)) throw new Error('Unsupported 3D tone mapping.');
      render.exposure=Math.max(0,Math.min(10,Number(render.exposure)||1));
      next.render=render;
    }
    sequence.scene3d=next;
    return next;
  }

  function set3DClipTransform(project, clipId, transform) {
    const found=findClip(project,clipId);
    if(found.track.locked) throw new Error('This track is locked.');
    const current=Object.assign({position:[0,0,0],rotation:[0,0,0],scale:[1,1,1]},clone(found.clip.transform3d||{}));
    const next=Object.assign({},current);
    for(const key of ['position','rotation','scale']){
      if(transform[key]!==undefined){
        const value=transform[key];
        if(!Array.isArray(value)||value.length!==3||value.some(n=>!Number.isFinite(Number(n)))) throw new Error('3D '+key+' must contain three finite numbers.');
        next[key]=value.map(Number);
      }
    }
    if(next.scale.some(n=>Math.abs(n)<0.0001||Math.abs(n)>10000)) throw new Error('3D scale must be non-zero and below 10,000.');
    found.clip.transform3d=next;
    return next;
  }

  function set3DClipAnimation(project,clipId,animation) {
    const found=findClip(project,clipId);
    if(found.track.locked) throw new Error('This track is locked.');
    const next=Object.assign({enabled:true,clip_name:'',time_scale:1,loop:true,start_frame:found.clip.start_frame},clone(found.clip.animation||{}),clone(animation||{}));
    if(!Number.isFinite(Number(next.time_scale))||next.time_scale<0||next.time_scale>8) throw new Error('3D animation speed must be between 0 and 8.');
    if(!Number.isInteger(Number(next.start_frame))||Number(next.start_frame)<0) throw new Error('3D animation start frame must be a non-negative integer.');
    next.time_scale=Number(next.time_scale);next.start_frame=Number(next.start_frame);
    found.clip.animation=next;
    return next;
  }

  function set3DClipConstraints(project,clipId,constraints) {
    const found=findClip(project,clipId);
    if(found.track.locked) throw new Error('This track is locked.');
    if(!Array.isArray(constraints)||constraints.length>16) throw new Error('A model can have up to 16 scene constraints.');
    const accepted=new Set(['ground_contact','look_at','parent','aabb_collision']);
    for(const constraint of constraints){
      if(!accepted.has(constraint.type)) throw new Error('Unsupported 3D constraint.');
      if(constraint.type==='ground_contact'&&!Number.isFinite(Number(constraint.ground_y??0))) throw new Error('Ground contact needs a finite ground height.');
      if(constraint.type==='look_at'&&(!Array.isArray(constraint.target)||constraint.target.length!==3||constraint.target.some(n=>!Number.isFinite(Number(n))))) throw new Error('Look-at target needs three finite coordinates.');
      if(constraint.type==='parent'&&constraint.target_clip_id===clipId) throw new Error('A model cannot parent itself.');
      if(constraint.type==='parent') findClip(project,constraint.target_clip_id);
    }
    found.clip.constraints=clone(constraints);
    return found.clip.constraints;
  }

  function evaluate3DClipState(clip,globalFrame) {
    const base=Object.assign({position:[0,0,0],rotation:[0,0,0],scale:[1,1,1]},clone(clip.transform3d||{}));
    const frame=Math.max(0,Math.round(Number(globalFrame)||0));
    const local=Math.max(0,frame-clip.start_frame);
    const keys=(clip.keyframes||[]);
    for(const [property,index,field] of [
      ['position3d.x',0,'position'],['position3d.y',1,'position'],['position3d.z',2,'position'],
      ['rotation3d.x',0,'rotation'],['rotation3d.y',1,'rotation'],['rotation3d.z',2,'rotation'],
      ['scale3d.x',0,'scale'],['scale3d.y',1,'scale'],['scale3d.z',2,'scale']
    ]){
      const fallback=base[field][index];
      base[field][index]=evaluateKeyframes({keyframes:keys},property,local,fallback);
    }
    return base;
  }


  const api = {
    FORMAT, SCHEMA_VERSION, MAX_FILE_BYTES, HASH_LIMIT_BYTES, FORMATS, TRACK_TYPES,
    makeId, clone, extensionOf, classifyFile, verifySignature, validateSvgText,
    createDefaultProject, getMainSequence, addTrack, trackForAssetType,
    assetToProjectRecord, addAsset, addAssetClip, findClip, moveClip, trimClip,
    splitClip, duplicateClip, deleteClip, addGraphicClip, setClipTransform, setClipParent, setClipMask,
    BLEND_MODES, KEYFRAME_PROPERTIES, ANIMATABLE_PROPERTIES, PARTICLE_PRESETS, CLIP_EFFECT_TYPES, POST_PROCESS_TYPES, POST_PROCESS_PRESETS, TRANSITION_TYPES,
    setKeyframe, evaluateKeyframes, evaluateClipTransform, setClipPlaybackRate, evaluateClipPlaybackRate, getActiveVisualClips,
    default3DSceneSettings, set3DSceneSettings, set3DClipTransform, set3DClipAnimation, set3DClipConstraints, evaluate3DClipState,
    addPostProcessPass, applyPostProcessPreset, removePostProcessPass, setPostProcessRenderer, setClipEffect, setEffectParameterKeyframe, evaluateEffectParameters, setClipTransition, validateProject
  };
  root.FFV2Core = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
