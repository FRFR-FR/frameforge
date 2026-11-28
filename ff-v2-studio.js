/* FrameForge V2 studio — media library, multi-track editor model and local persistence. */
(() => {
  'use strict';

  const Core = window.FFV2Core;
  if (!Core) {
    console.error('FrameForge V2 core is missing.');
    return;
  }

  const DB_NAME = 'FrameForgeDB';
  const DB_VERSION = 2;
  const MAX_RECOVERY_VERSIONS = 6;
  const state = {
    db: null,
    project: null,
    assetRecords: [],
    objectUrls: new Map(),
    selectedAssetId: null,
    selectedClipId: null,
    playhead: 0,
    zoom: 1.15,
    snap: true,
    saveTimer: null,
    saveInFlight: false,
    pendingSave: false,
    ready: false,
    dragging: null
  };

  const $ = id => document.getElementById(id);
  const safeText = value => String(value == null ? '' : value);
  const bytesMB = bytes => (bytes / (1024 * 1024)).toFixed(2) + ' MB';

  function setStatus(message, kind) {
    const el = $('ffv2SaveStatus');
    if (!el) return;
    el.textContent = message;
    el.dataset.kind = kind || 'info';
  }

  function openDatabase() {
    return new Promise((resolve, reject) => {
      if (!('indexedDB' in window)) {
        reject(new Error('This browser does not support IndexedDB. V2 local saving is unavailable.'));
        return;
      }
      const request = indexedDB.open(DB_NAME, DB_VERSION);
      request.onupgradeneeded = () => {
        const database = request.result;
        if (!database.objectStoreNames.contains('projects')) database.createObjectStore('projects', { keyPath: 'id' });
        if (!database.objectStoreNames.contains('assets')) database.createObjectStore('assets', { keyPath: 'id' });
        if (!database.objectStoreNames.contains('v2projects')) database.createObjectStore('v2projects', { keyPath: 'id' });
        if (!database.objectStoreNames.contains('recovery')) database.createObjectStore('recovery', { keyPath: 'id' });
      };
      request.onsuccess = () => {
        const database = request.result;
        database.onversionchange = () => database.close();
        resolve(database);
      };
      request.onerror = () => reject(request.error || new Error('Could not open local project storage.'));
      request.onblocked = () => setStatus('Close older FrameForge tabs to finish the storage upgrade.', 'warning');
    });
  }

  function requestResult(request) {
    return new Promise((resolve, reject) => {
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error || new Error('Local storage request failed.'));
    });
  }

  function txDone(transaction) {
    return new Promise((resolve, reject) => {
      transaction.oncomplete = () => resolve();
      transaction.onerror = () => reject(transaction.error || new Error('Local storage transaction failed.'));
      transaction.onabort = () => reject(transaction.error || new Error('Local storage transaction was aborted.'));
    });
  }

  function makeSafeName(fileName) {
    return safeText(fileName).replace(/[\\/<>:"|?*\x00-\x1f]/g, '_').slice(0, 180) || 'untitled';
  }

  async function hashFile(file) {
    if (!window.crypto || !crypto.subtle || file.size > Core.HASH_LIMIT_BYTES) return null;
    try {
      const bytes = await file.arrayBuffer();
      const digest = await crypto.subtle.digest('SHA-256', bytes);
      return Array.from(new Uint8Array(digest), byte => byte.toString(16).padStart(2, '0')).join('');
    } catch (_) {
      return null;
    }
  }

  function mediaTypeFor(category, extension) {
    if (category === 'image' && extension === 'svg') return 'graphic';
    return category;
  }

  function createMetadataElement(label, value) {
    const row = document.createElement('div');
    row.className = 'ffv2-meta-row';
    const key = document.createElement('span');
    key.textContent = label;
    const val = document.createElement('strong');
    val.textContent = value;
    row.append(key, val);
    return row;
  }

  async function loadImageMetadata(file, url, extension) {
    let image;
    try {
      if (typeof createImageBitmap === 'function') {
        image = await createImageBitmap(file);
        const result = { width: image.width, height: image.height, alpha_capable: ['png', 'gif', 'webp', 'avif', 'svg'].includes(extension), decode_status: 'decoded' };
        image.close();
        return result;
      }
      image = new Image();
      await new Promise((resolve, reject) => {
        image.onload = resolve;
        image.onerror = () => reject(new Error('The browser could not decode this image.'));
        image.src = url;
      });
      return { width: image.naturalWidth, height: image.naturalHeight, alpha_capable: ['png', 'gif', 'webp', 'avif', 'svg'].includes(extension), decode_status: 'decoded' };
    } catch (error) {
      throw new Error('Image decode failed: ' + error.message);
    }
  }

  function loadMediaMetadata(tagName, url) {
    return new Promise((resolve, reject) => {
      const media = document.createElement(tagName);
      let finished = false;
      const timer = setTimeout(() => finish(new Error('Timed out reading media metadata.')), 12000);
      function finish(error) {
        if (finished) return;
        finished = true;
        clearTimeout(timer);
        media.removeAttribute('src');
        media.load?.();
        if (error) reject(error);
        else resolve({
          width: tagName === 'video' ? (media.videoWidth || 0) : undefined,
          height: tagName === 'video' ? (media.videoHeight || 0) : undefined,
          duration_seconds: Number.isFinite(media.duration) ? media.duration : null,
          decode_status: 'metadata-loaded'
        });
      }
      media.preload = 'metadata';
      media.muted = true;
      media.onloadedmetadata = () => {
        if (tagName === 'video' && (!media.videoWidth || !media.videoHeight)) {
          finish(new Error('Video has no readable picture dimensions.'));
          return;
        }
        if (!Number.isFinite(media.duration) || media.duration <= 0) {
          finish(new Error('Media duration is invalid or unavailable.'));
          return;
        }
        finish();
      };
      media.onerror = () => finish(new Error('The browser cannot read this media container or codec.'));
      media.src = url;
      media.load();
    });
  }

  async function inspectModel(file, extension, firstBytes) {
    if (extension === 'glb') {
      const header = new DataView(firstBytes.buffer, firstBytes.byteOffset, firstBytes.byteLength);
      if (firstBytes.length < 12 || header.getUint32(8, true) !== file.size) {
        throw new Error('GLB declared file length does not match the uploaded file.');
      }
      return { codec: 'glTF Binary 2.0', decode_status: 'header-validated' };
    }
    const text = await file.text();
    let documentData;
    try { documentData = JSON.parse(text); }
    catch (_) { throw new Error('glTF JSON is malformed.'); }
    if (!documentData.asset || !String(documentData.asset.version || '').startsWith('2.0')) {
      throw new Error('Only glTF 2.0 JSON files are supported.');
    }
    const dependencies = [];
    for (const item of [...(documentData.buffers || []), ...(documentData.images || [])]) {
      if (item.uri && !item.uri.startsWith('data:')) dependencies.push(item.uri);
    }
    return {
      codec: 'glTF JSON 2.0',
      decode_status: 'json-validated',
      external_dependencies: dependencies,
      dependency_warning: dependencies.length ? 'This glTF references external files. Import each referenced buffer/texture as a separate asset or use a self-contained GLB.' : ''
    };
  }

  async function inspectFile(file, classification, url, firstBytes) {
    const { category, extension } = classification;
    if (category === 'image') {
      if (extension === 'svg') {
        const svgText = await file.text();
        Core.validateSvgText(svgText);
      }
      return await loadImageMetadata(file, url, extension);
    }
    if (category === 'video') return await loadMediaMetadata('video', url);
    if (category === 'audio') return await loadMediaMetadata('audio', url);
    if (category === 'model3d') return await inspectModel(file, extension, firstBytes);
    throw new Error('This media category is not supported.');
  }

  async function importOneFile(file) {
    const classification = Core.classifyFile(file);
    const firstBytes = new Uint8Array(await file.slice(0, 64).arrayBuffer());
    const signatureError = Core.verifySignature(classification.extension, firstBytes);
    if (signatureError) throw new Error(signatureError);
    const url = URL.createObjectURL(file);
    try {
      const metadata = await inspectFile(file, classification, url, firstBytes);
      if ((classification.category === 'image' || classification.category === 'video') &&
          (!metadata.width || !metadata.height)) {
        throw new Error('Media dimensions could not be read.');
      }
      const sha256 = await hashFile(file);
      if (sha256 && state.assetRecords.some(asset => asset.metadata && asset.metadata.sha256 === sha256)) {
        throw new Error('This exact file is already in the current V2 project.');
      }
      const mediaType = mediaTypeFor(classification.category, classification.extension);
      const id = Core.makeId('asset');
      const asset = {
        id,
        file_name: makeSafeName(file.name),
        label: makeSafeName(file.name).replace(/\.[^.]+$/, ''),
        media_type: mediaType,
        mime_type: file.type || classification.mime,
        blob: file.slice(0, file.size, file.type || classification.mime),
        metadata: {
          size_bytes: file.size,
          sha256: sha256 || undefined,
          width: metadata.width || undefined,
          height: metadata.height || undefined,
          duration_seconds: metadata.duration_seconds || undefined,
          codec: metadata.codec || classification.mime,
          alpha_capable: metadata.alpha_capable,
          decode_status: metadata.decode_status,
          external_dependencies: metadata.external_dependencies || []
        },
        provenance: {
          source_type: 'user_supplied',
          creator: '',
          acquired_at: new Date().toISOString(),
          notes: "Imported from the user's device. This does not establish ownership or permission to publish."
        },
        rights: {
          status: 'pending',
          attribution_required: false,
          restrictions: ['Review ownership, permission and reuse rights before publication.']
        },
        tags: [],
        created_at: new Date().toISOString()
      };

      const transaction = state.db.transaction('assets', 'readwrite');
      transaction.objectStore('assets').put(asset);
      await txDone(transaction);
      state.assetRecords.unshift(asset);
      Core.addAsset(state.project, asset);
      state.selectedAssetId = id;
      scheduleSave();
      renderAssets();
      renderTracks();
      return asset;
    } finally {
      URL.revokeObjectURL(url);
    }
  }

  async function importFiles(fileList) {
    const files = Array.from(fileList || []);
    if (!files.length) return;
    let imported = 0;
    const failures = [];
    setStatus('Checking and importing ' + files.length + ' file(s)…');
    for (const file of files) {
      try {
        await importOneFile(file);
        imported += 1;
      } catch (error) {
        failures.push(file.name + ': ' + error.message);
      }
    }
    renderAssets();
    if (failures.length) {
      setStatus(imported + ' imported; ' + failures.length + ' rejected. See details.', 'warning');
      const message = failures.slice(0, 5).join('\n');
      window.alert('Some files were not imported:\n' + message + (failures.length > 5 ? '\n…and ' + (failures.length - 5) + ' more.' : ''));
    } else {
      setStatus(imported + ' asset(s) validated and saved locally.', 'success');
    }
  }

  function getObjectUrl(asset) {
    if (state.objectUrls.has(asset.id)) return state.objectUrls.get(asset.id);
    if (!asset.blob) return '';
    const url = URL.createObjectURL(asset.blob);
    state.objectUrls.set(asset.id, url);
    return url;
  }

  function formatAssetSummary(asset) {
    const meta = asset.metadata || {};
    const parts = [bytesMB(meta.size_bytes || (asset.blob && asset.blob.size) || 0)];
    if (meta.width && meta.height) parts.push(meta.width + ' × ' + meta.height);
    if (meta.duration_seconds) parts.push(meta.duration_seconds.toFixed(2) + ' s');
    if (meta.codec) parts.push(meta.codec);
    return parts.join(' · ');
  }

  function renderAssets() {
    const container = $('ffv2AssetList');
    if (!container || !state.project) return;
    const query = safeText($('ffv2AssetSearch').value).trim().toLowerCase();
    const filter = $('ffv2AssetFilter').value;
    const records = state.assetRecords.filter(asset => {
      const text = [asset.label, asset.file_name, asset.mime_type, ...(asset.tags || [])].join(' ').toLowerCase();
      const projectMatch = !query || text.includes(query);
      const typeMatch = filter === 'all' || asset.media_type === filter;
      return projectMatch && typeMatch;
    });
    container.replaceChildren();
    if (!records.length) {
      const empty = document.createElement('p');
      empty.className = 'ffv2-empty';
      empty.textContent = state.assetRecords.length ? 'No assets match this search.' : 'No V2 assets yet. Import PNGs, video, audio, SVG or 3D files to begin.';
      container.append(empty);
    }
    for (const asset of records) {
      const card = document.createElement('article');
      card.className = 'ffv2-asset-card' + (asset.id === state.selectedAssetId ? ' selected' : '');
      const preview = document.createElement('div');
      preview.className = 'ffv2-asset-preview';
      const url = getObjectUrl(asset);
      if (url && (asset.media_type === 'image' || asset.media_type === 'graphic')) {
        const image = document.createElement('img');
        image.src = url;
        image.alt = '';
        preview.append(image);
      } else {
        const mark = document.createElement('span');
        mark.textContent = ({ video: '▶', audio: '♫', model3d: '◇', image: '▧', graphic: '⌗' })[asset.media_type] || '•';
        preview.append(mark);
      }
      const details = document.createElement('div');
      details.className = 'ffv2-asset-details';
      const title = document.createElement('strong');
      title.textContent = asset.label;
      const metadata = document.createElement('small');
      metadata.textContent = formatAssetSummary(asset);
      const status = document.createElement('small');
      status.className = 'ffv2-rights-state';
      status.textContent = 'Rights: ' + (asset.rights?.status || 'pending');
      const tagInput = document.createElement('input');
      tagInput.className = 'ffv2-tag-input';
      tagInput.value = (asset.tags || []).join(', ');
      tagInput.placeholder = 'Tags, separated by commas';
      tagInput.setAttribute('aria-label', 'Tags for ' + asset.label);
      tagInput.addEventListener('change', () => updateAssetTags(asset.id, tagInput.value));
      const buttons = document.createElement('div');
      buttons.className = 'ffv2-asset-actions';
      const selectBtn = document.createElement('button');
      selectBtn.type = 'button';
      selectBtn.className = 'button small';
      selectBtn.textContent = 'Select';
      selectBtn.addEventListener('click', () => {
        state.selectedAssetId = asset.id;
        renderAssets();
      });
      const addBtn = document.createElement('button');
      addBtn.type = 'button';
      addBtn.className = 'button small primary';
      addBtn.textContent = 'Add to timeline';
      addBtn.addEventListener('click', () => addAssetToTimeline(asset));
      buttons.append(selectBtn, addBtn);
      details.append(title, metadata, status, tagInput, buttons);
      card.append(preview, details);
      card.addEventListener('click', () => {
        state.selectedAssetId = asset.id;
        container.querySelectorAll('.ffv2-asset-card').forEach(node => node.classList.remove('selected'));
        card.classList.add('selected');
      });
      container.append(card);
    }
    $('ffv2AssetCount').textContent = records.length + ' shown / ' + state.assetRecords.length + ' total';
  }

  async function updateAssetTags(assetId, text) {
    const asset = state.assetRecords.find(item => item.id === assetId);
    if (!asset) return;
    asset.tags = Array.from(new Set(text.split(',').map(tag => tag.trim()).filter(Boolean))).slice(0, 30);
    const transaction = state.db.transaction('assets', 'readwrite');
    transaction.objectStore('assets').put(asset);
    await txDone(transaction);
    Core.addAsset(state.project, asset);
    scheduleSave();
    renderAssets();
  }

  function currentSequence() { return Core.getMainSequence(state.project); }

  function populateTargetTracks() {
    const select = $('ffv2TargetTrack');
    if (!select) return;
    const current = select.value;
    select.replaceChildren();
    const automatic = document.createElement('option');
    automatic.value = '';
    automatic.textContent = 'Auto-match track';
    select.append(automatic);
    for (const track of currentSequence().tracks) {
      const option = document.createElement('option');
      option.value = track.id;
      option.textContent = track.name + ' (' + track.type + ')';
      select.append(option);
    }
    select.value = currentSequence().tracks.some(track => track.id === current) ? current : '';
  }

  function addAssetToTimeline(asset) {
    try {
      const seq = currentSequence();
      const requestedTrackId = $('ffv2TargetTrack').value;
      let track = requestedTrackId
        ? seq.tracks.find(item => item.id === requestedTrackId)
        : seq.tracks.find(item => item.type === Core.trackForAssetType(asset.media_type));
      if (!track) {
        track = Core.addTrack(state.project, Core.trackForAssetType(asset.media_type), asset.media_type + ' assets');
      }
      const durationSeconds = asset.metadata?.duration_seconds;
      const durationFrames = durationSeconds
        ? Math.max(1, Math.round(durationSeconds * seq.fps))
        : Math.round(seq.fps * 5);
      const clip = Core.addAssetClip(state.project, asset.id, track.id, state.playhead, durationFrames);
      state.selectedClipId = clip.id;
      scheduleSave();
      renderTracks();
      renderClipInspector();
      setStatus('Added ' + asset.label + ' to the timeline.', 'success');
    } catch (error) {
      setStatus(error.message, 'warning');
    }
  }

  function addTrack() {
    const type = $('ffv2NewTrackType').value;
    const defaultName = type.replace(/\b\w/g, value => value.toUpperCase());
    const name = window.prompt('Name this track:', defaultName);
    if (name === null) return;
    try {
      Core.addTrack(state.project, type, name.trim() || defaultName);
      scheduleSave();
      renderTracks();
      setStatus('Track added.', 'success');
    } catch (error) {
      setStatus(error.message, 'warning');
    }
  }

  function timelineScale() { return Math.max(0.35, Math.min(4, state.zoom)); }

  function setPlayhead(frame) {
    const seq = currentSequence();
    state.playhead = Math.max(0, Math.min(seq.duration_frames, Math.round(Number(frame) || 0)));
    $('ffv2Playhead').value = String(state.playhead);
    $('ffv2PlayheadLabel').textContent = 'Frame ' + state.playhead + ' · ' + (state.playhead / seq.fps).toFixed(2) + ' s';
    if (state.selectedClipId) renderClipInspector();
    renderPlayheadLine();
  }

  function timelinePixelWidth() {
    return Math.max(520, currentSequence().duration_frames * timelineScale());
  }

  function renderRuler() {
    const ruler = $('ffv2TimelineRuler');
    ruler.replaceChildren();
    ruler.style.width = timelinePixelWidth() + 'px';
    const sequence = currentSequence();
    const every = Math.max(sequence.fps, Math.round((100 / timelineScale()) / sequence.fps) * sequence.fps);
    const step = Math.max(sequence.fps, Math.ceil(every / sequence.fps) * sequence.fps);
    for (let frame = 0; frame <= sequence.duration_frames; frame += step) {
      const tick = document.createElement('button');
      tick.type = 'button';
      tick.className = 'ffv2-ruler-tick';
      tick.style.left = (frame * timelineScale()) + 'px';
      tick.textContent = (frame / sequence.fps).toFixed(0) + 's';
      tick.addEventListener('click', () => setPlayhead(frame));
      ruler.append(tick);
    }
  }

  function renderTracks() {
    if (!state.project) return;
    const host = $('ffv2TrackRows');
    const width = timelinePixelWidth();
    host.replaceChildren();
    $('ffv2TrackCount').textContent = currentSequence().tracks.length + ' tracks';
    for (const track of [...currentSequence().tracks].sort((a, b) => a.order - b.order)) {
      const row = document.createElement('div');
      row.className = 'ffv2-track-row';
      const heading = document.createElement('div');
      heading.className = 'ffv2-track-heading';
      const name = document.createElement('strong');
      name.textContent = track.name;
      const type = document.createElement('small');
      type.textContent = track.type;
      const controls = document.createElement('div');
      controls.className = 'ffv2-track-buttons';
      const enabled = document.createElement('button');
      enabled.type = 'button';
      enabled.className = 'icon-button';
      enabled.title = track.enabled ? 'Hide/disable track' : 'Show/enable track';
      enabled.textContent = track.enabled ? '◉' : '○';
      enabled.addEventListener('click', () => { track.enabled = !track.enabled; scheduleSave(); renderTracks(); });
      const mute = document.createElement('button');
      mute.type = 'button';
      mute.className = 'icon-button';
      mute.title = track.muted ? 'Unmute track' : 'Mute track';
      mute.textContent = track.muted ? 'M' : 'm';
      mute.addEventListener('click', () => { track.muted = !track.muted; scheduleSave(); renderTracks(); });
      const lock = document.createElement('button');
      lock.type = 'button';
      lock.className = 'icon-button';
      lock.title = track.locked ? 'Unlock track' : 'Lock track';
      lock.textContent = track.locked ? '🔒' : '🔓';
      lock.addEventListener('click', () => { track.locked = !track.locked; scheduleSave(); renderTracks(); });
      controls.append(enabled, mute, lock);
      heading.append(name, type, controls);

      const lane = document.createElement('div');
      lane.className = 'ffv2-track-lane' + (!track.enabled ? ' disabled' : '');
      lane.style.width = width + 'px';
      lane.addEventListener('click', event => {
        const rect = lane.getBoundingClientRect();
        setPlayhead((event.clientX - rect.left) / timelineScale());
      });
      for (const clip of track.clips) {
        const asset = state.project.assets.find(item => item.id === clip.asset_id);
        const chip = document.createElement('button');
        chip.type = 'button';
        chip.className = 'ffv2-clip' + (clip.id === state.selectedClipId ? ' selected' : '');
        chip.style.left = (clip.start_frame * timelineScale()) + 'px';
        chip.style.width = Math.max(28, clip.duration_frames * timelineScale()) + 'px';
        chip.title = (asset?.label || clip.id) + ' · frame ' + clip.start_frame + ' · ' + clip.duration_frames + ' frames';
        chip.textContent = asset?.label || 'Missing asset';
        chip.disabled = !track.enabled;
        chip.addEventListener('click', event => {
          event.stopPropagation();
          state.selectedClipId = clip.id;
          renderTracks();
          renderClipInspector();
        });
        chip.addEventListener('pointerdown', event => beginClipDrag(event, clip, track, chip));
        lane.append(chip);
      }
      row.append(heading, lane);
      host.append(row);
    }
    populateTargetTracks();
    renderRuler();
    renderPlayheadLine();
  }

  function renderPlayheadLine() {
    const line = $('ffv2PlayheadLine');
    if (line) line.style.left = (170 + state.playhead * timelineScale()) + 'px';
  }

  function beginClipDrag(event, clip, track, element) {
    if (event.button !== 0 || track.locked || !track.enabled) return;
    event.preventDefault();
    event.stopPropagation();
    state.dragging = {
      clipId: clip.id, trackId: track.id, initialX: event.clientX,
      startFrame: clip.start_frame, element
    };
    element.setPointerCapture?.(event.pointerId);
    element.classList.add('dragging');
    const move = moveEvent => {
      if (!state.dragging || state.dragging.clipId !== clip.id) return;
      const deltaFrames = (moveEvent.clientX - state.dragging.initialX) / timelineScale();
      let nextFrame = Math.max(0, Math.round(state.dragging.startFrame + deltaFrames));
      const snap = state.snap ? currentSequence().fps : 1;
      nextFrame = Math.max(0, Math.round(nextFrame / snap) * snap);
      element.style.left = (nextFrame * timelineScale()) + 'px';
    };
    const end = endEvent => {
      if (!state.dragging || state.dragging.clipId !== clip.id) return;
      const deltaFrames = (endEvent.clientX - state.dragging.initialX) / timelineScale();
      const snap = state.snap ? currentSequence().fps : 1;
      const nextFrame = Math.max(0, Math.round((state.dragging.startFrame + deltaFrames) / snap) * snap);
      state.dragging = null;
      element.classList.remove('dragging');
      try {
        Core.moveClip(state.project, clip.id, nextFrame, snap);
        state.selectedClipId = clip.id;
        scheduleSave();
        renderTracks();
        renderClipInspector();
      } catch (error) {
        setStatus(error.message, 'warning');
        renderTracks();
      }
      element.removeEventListener('pointermove', move);
      element.removeEventListener('pointerup', end);
      element.removeEventListener('pointercancel', end);
    };
    element.addEventListener('pointermove', move);
    element.addEventListener('pointerup', end);
    element.addEventListener('pointercancel', end);
  }

  function selectedClipInfo() {
    if (!state.selectedClipId) return null;
    try { return Core.findClip(state.project, state.selectedClipId); }
    catch (_) { state.selectedClipId = null; return null; }
  }

  function renderClipInspector() {
    const panel = $('ffv2ClipEditor');
    const found = selectedClipInfo();
    if (!found) {
      panel.classList.add('hidden');
      return;
    }
    panel.classList.remove('hidden');
    const asset = state.project.assets.find(item => item.id === found.clip.asset_id);
    $('ffv2SelectedClipName').textContent = asset?.label || found.clip.id;
    $('ffv2ClipStart').value = String(found.clip.start_frame);
    $('ffv2ClipDuration').value = String(found.clip.duration_frames);
    $('ffv2ClipTrack').textContent = found.track.name + (found.track.locked ? ' · locked' : '');
    const splitEnabled = !found.track.locked &&
      state.playhead > found.clip.start_frame &&
      state.playhead < found.clip.start_frame + found.clip.duration_frames;
    $('ffv2SplitClip').disabled = !splitEnabled;
    $('ffv2DuplicateClip').disabled = found.track.locked;
    $('ffv2DeleteClip').disabled = found.track.locked;
    $('ffv2ApplyClipTiming').disabled = found.track.locked;
  }

  function applyClipTiming() {
    const found = selectedClipInfo();
    if (!found) return;
    try {
      Core.trimClip(state.project, found.clip.id, $('ffv2ClipStart').value, $('ffv2ClipDuration').value);
      scheduleSave();
      renderTracks();
      renderClipInspector();
      setStatus('Clip timing updated.', 'success');
    } catch (error) {
      setStatus(error.message, 'warning');
    }
  }

  function splitSelectedClip() {
    if (!state.selectedClipId) return;
    try {
      const clip = Core.splitClip(state.project, state.selectedClipId, state.playhead);
      state.selectedClipId = clip.id;
      scheduleSave();
      renderTracks();
      renderClipInspector();
      setStatus('Clip split at the playhead.', 'success');
    } catch (error) {
      setStatus(error.message, 'warning');
    }
  }

  function duplicateSelectedClip() {
    if (!state.selectedClipId) return;
    try {
      const clip = Core.duplicateClip(state.project, state.selectedClipId);
      state.selectedClipId = clip.id;
      scheduleSave();
      renderTracks();
      renderClipInspector();
    } catch (error) { setStatus(error.message, 'warning'); }
  }

  function deleteSelectedClip() {
    if (!state.selectedClipId) return;
    try {
      Core.deleteClip(state.project, state.selectedClipId);
      state.selectedClipId = null;
      scheduleSave();
      renderTracks();
      renderClipInspector();
    } catch (error) { setStatus(error.message, 'warning'); }
  }

  function scheduleSave() {
    if (!state.project || !state.ready) return;
    clearTimeout(state.saveTimer);
    setStatus('Unsaved changes…');
    state.saveTimer = setTimeout(() => saveProject(false), 650);
  }

  async function saveProject(showMessage = true) {
    if (!state.project || !state.db) return;
    if (state.saveInFlight) { state.pendingSave = true; return; }
    const errors = Core.validateProject(state.project);
    if (errors.length) {
      setStatus('Save blocked: ' + errors[0], 'error');
      return;
    }
    state.saveInFlight = true;
    state.project.project.updated_at = new Date().toISOString();
    const snapshot = Core.clone(state.project);
    try {
      const transaction = state.db.transaction(['v2projects', 'projects', 'recovery'], 'readwrite');
      const projects = transaction.objectStore('v2projects');
      const pointer = transaction.objectStore('projects');
      const recovery = transaction.objectStore('recovery');
      const previousRequest = projects.get(snapshot.project.id);
      previousRequest.onsuccess = () => {
        const previous = previousRequest.result;
        const previousJSON = previous?.project ? JSON.stringify(previous.project) : '';
        const nextJSON = JSON.stringify(snapshot);
        if (previousJSON && previousJSON !== nextJSON) {
          const savedAt = Date.now();
          recovery.put({
            id: snapshot.project.id + ':' + savedAt,
            project_id: snapshot.project.id,
            saved_at: savedAt,
            project: previous.project
          });
          const listRequest = recovery.getAll();
          listRequest.onsuccess = () => {
            const versions = listRequest.result
              .filter(item => item.project_id === snapshot.project.id)
              .sort((a, b) => b.saved_at - a.saved_at);
            versions.slice(MAX_RECOVERY_VERSIONS).forEach(item => recovery.delete(item.id));
          };
        }
        projects.put({ id: snapshot.project.id, project: snapshot, updated_at: Date.now() });
        pointer.put({ id: 'ffv2-active', project_id: snapshot.project.id, updated_at: Date.now() });
      };
      await txDone(transaction);
      setStatus('Saved locally · recovery enabled', 'success');
      if (showMessage) window.alert('FrameForge V2 project saved in this browser.');
    } catch (error) {
      console.error('FrameForge V2 save failed:', error);
      setStatus('Save failed: storage may be full. Export the project JSON and back up imported assets.', 'error');
    } finally {
      state.saveInFlight = false;
      if (state.pendingSave) {
        state.pendingSave = false;
        scheduleSave();
      }
    }
  }

  async function loadActiveProject() {
    const pointerTransaction = state.db.transaction('projects', 'readonly');
    const pointerRecord = await requestResult(pointerTransaction.objectStore('projects').get('ffv2-active'));
    if (pointerRecord?.project_id) {
      const projectTransaction = state.db.transaction('v2projects', 'readonly');
      const record = await requestResult(projectTransaction.objectStore('v2projects').get(pointerRecord.project_id));
      if (record?.project && Core.validateProject(record.project).length === 0) {
        state.project = record.project;
        return true;
      }
    }
    state.project = Core.createDefaultProject('Untitled V2 Project');
    return false;
  }

  async function loadProjectAssets() {
    const transaction = state.db.transaction('assets', 'readonly');
    const allRecords = await requestResult(transaction.objectStore('assets').getAll());
    const byId = new Map(allRecords.map(asset => [asset.id, asset]));
    state.assetRecords = state.project.assets.map(ref => byId.get(ref.id) || ({
      id: ref.id, label: ref.label || 'Missing local asset', file_name: ref.label || '',
      media_type: ref.media_type, metadata: ref.metadata || {}, tags: ref.tags || [],
      rights: ref.rights || { status: 'pending' }, missing: true
    }));
  }

  async function showRecoveryCount() {
    const transaction = state.db.transaction('recovery', 'readonly');
    const all = await requestResult(transaction.objectStore('recovery').getAll());
    const versions = all.filter(item => item.project_id === state.project.project.id).sort((a, b) => b.saved_at - a.saved_at);
    $('ffv2RecoveryButton').disabled = versions.length === 0;
    $('ffv2RecoveryButton').textContent = versions.length ? 'Restore previous (' + versions.length + ')' : 'No recovery copy';
    $('ffv2RecoveryButton').dataset.latest = versions[0]?.id || '';
  }

  async function restorePreviousVersion() {
    const id = $('ffv2RecoveryButton').dataset.latest;
    if (!id) return;
    const transaction = state.db.transaction('recovery', 'readonly');
    const record = await requestResult(transaction.objectStore('recovery').get(id));
    if (!record?.project || Core.validateProject(record.project).length) {
      setStatus('Recovery copy is invalid.', 'error');
      return;
    }
    if (!window.confirm('Restore the previous saved version? The current version will remain in recovery history.')) return;
    state.project = record.project;
    state.selectedClipId = null;
    state.playhead = 0;
    await saveProject(false);
    await loadProjectAssets();
    renderAll();
    await showRecoveryCount();
    setStatus('Previous version restored.', 'success');
  }

  async function exportProject() {
    const errors = Core.validateProject(state.project);
    if (errors.length) {
      setStatus('Export blocked: ' + errors[0], 'error');
      return;
    }
    const blob = new Blob([JSON.stringify(state.project, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = makeSafeName(state.project.project.name) + '.frameforge-v2.json';
    document.body.append(anchor);
    anchor.click();
    anchor.remove();
    setTimeout(() => URL.revokeObjectURL(url), 5000);
    setStatus('V2 project JSON exported. Imported media remains in this browser unless separately backed up.', 'warning');
  }

  async function importProject(file) {
    if (!file) return;
    try {
      if (file.size > 25 * 1024 * 1024) throw new Error('Project JSON is larger than the 25 MB import limit.');
      const project = JSON.parse(await file.text());
      const errors = Core.validateProject(project);
      if (errors.length) throw new Error(errors[0]);
      if (!window.confirm('Open this V2 project? The current V2 workspace is saved before switching.')) return;
      await saveProject(false);
      state.project = project;
      state.selectedClipId = null;
      state.playhead = 0;
      await saveProject(false);
      await loadProjectAssets();
      renderAll();
      await showRecoveryCount();
      setStatus('V2 project opened. Any asset not stored on this device will show as missing.', 'warning');
    } catch (error) {
      setStatus('Could not open V2 project: ' + error.message, 'error');
    } finally {
      $('ffv2ProjectFile').value = '';
    }
  }

  function renderAll() {
    $('ffv2ProjectName').value = state.project.project.name;
    $('ffv2Playhead').max = String(currentSequence().duration_frames);
    $('ffv2Playhead').step = '1';
    $('ffv2Playhead').value = String(state.playhead);
    $('ffv2SnapToggle').checked = state.snap;
    renderAssets();
    renderTracks();
    renderClipInspector();
    setPlayhead(state.playhead);
  }

  function setZoom(delta) {
    state.zoom = Math.max(0.35, Math.min(4, state.zoom + delta));
    $('ffv2ZoomLabel').textContent = Math.round(state.zoom * 100) + '%';
    renderTracks();
  }

  function bindDropZone() {
    const zone = $('ffv2DropZone');
    ['dragenter', 'dragover'].forEach(type => zone.addEventListener(type, event => {
      event.preventDefault();
      zone.classList.add('dragging');
    }));
    ['dragleave', 'drop'].forEach(type => zone.addEventListener(type, event => {
      event.preventDefault();
      zone.classList.remove('dragging');
    }));
    zone.addEventListener('drop', event => importFiles(event.dataTransfer?.files));
  }

  function bindEvents() {
    $('ffv2ImportButton').addEventListener('click', () => $('ffv2FileInput').click());
    $('ffv2FileInput').addEventListener('change', event => {
      importFiles(event.target.files);
      event.target.value = '';
    });
    bindDropZone();
    $('ffv2AssetSearch').addEventListener('input', renderAssets);
    $('ffv2AssetFilter').addEventListener('change', renderAssets);
    $('ffv2ProjectName').addEventListener('change', () => {
      state.project.project.name = $('ffv2ProjectName').value.trim() || 'Untitled V2 Project';
      scheduleSave();
    });
    $('ffv2AddTrack').addEventListener('click', addTrack);
    $('ffv2SnapToggle').addEventListener('change', event => { state.snap = event.target.checked; });
    $('ffv2Playhead').addEventListener('input', event => setPlayhead(event.target.value));
    $('ffv2ZoomIn').addEventListener('click', () => setZoom(0.2));
    $('ffv2ZoomOut').addEventListener('click', () => setZoom(-0.2));
    $('ffv2ApplyClipTiming').addEventListener('click', applyClipTiming);
    $('ffv2SplitClip').addEventListener('click', splitSelectedClip);
    $('ffv2DuplicateClip').addEventListener('click', duplicateSelectedClip);
    $('ffv2DeleteClip').addEventListener('click', deleteSelectedClip);
    $('ffv2SaveProject').addEventListener('click', () => saveProject(true));
    $('ffv2ExportProject').addEventListener('click', exportProject);
    $('ffv2OpenProject').addEventListener('click', () => $('ffv2ProjectFile').click());
    $('ffv2ProjectFile').addEventListener('change', event => importProject(event.target.files[0]));
    $('ffv2RecoveryButton').addEventListener('click', restorePreviousVersion);
  }

  async function init() {
    try {
      state.db = await openDatabase();
      const restored = await loadActiveProject();
      await loadProjectAssets();
      bindEvents();
      state.ready = true;
      renderAll();
      await showRecoveryCount();
      if (restored) setStatus('V2 project restored from this browser.', 'success');
      else {
        setStatus('New V2 project created. Assets and edits save locally.', 'info');
        await saveProject(false);
      }
    } catch (error) {
      console.error('FrameForge V2 startup failed:', error);
      setStatus(error.message, 'error');
    }
  }

  document.addEventListener('DOMContentLoaded', init);
})();
