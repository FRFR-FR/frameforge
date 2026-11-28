/* FrameForge V2 resumable frame queue and chunk ZIP export. */
(function (root) {
  'use strict';

  const $ = id => root.document && root.document.getElementById(id);
  const MB = 1024 * 1024;
  let currentJob = null;
  let pauseRequested = false;
  let running = false;
  let uiBound = false;

  function setStatus(message, kind) {
    const node = $('ffv2RenderQueueStatus');
    if (node) {
      node.textContent = message;
      node.dataset.kind = kind || 'info';
    }
  }

  function stamp() { return new Date().toISOString(); }

  async function signature(project) {
    const bytes = new TextEncoder().encode(JSON.stringify(project));
    if (root.crypto?.subtle) {
      const digest = await root.crypto.subtle.digest('SHA-256', bytes);
      return Array.from(new Uint8Array(digest), value => value.toString(16).padStart(2, '0')).join('');
    }
    let hash = 2166136261;
    for (const byte of bytes) hash = Math.imul(hash ^ byte, 16777619);
    return 'fnv1a-' + (hash >>> 0).toString(16);
  }

  function updateProgress(job, text) {
    const done = Math.max(0, Math.min(job.total_frames, job.completed_frames || 0));
    const percent = job.total_frames ? Math.round(done / job.total_frames * 100) : 0;
    const bar = $('ffv2RenderQueueProgress');
    const label = $('ffv2RenderQueueProgressText');
    if (bar) bar.value = percent;
    if (label) label.textContent = text || (done + ' / ' + job.total_frames + ' frames · ' + percent + '%');
    const summary = $('ffv2RenderQueueJobSummary');
    if (summary) summary.textContent = job.project_name + ' · ' + job.width + '×' + job.height +
      ' · ' + job.fps + ' fps · ' + job.chunk_size + '-frame chunks · ' + (job.status || 'queued');
  }

  function chunkBounds(job, chunkIndex) {
    const start = chunkIndex * job.chunk_size;
    return { start, end: Math.min(job.total_frames, start + job.chunk_size) };
  }

  function chunkCount(job) {
    return Math.ceil(job.total_frames / job.chunk_size);
  }

  async function renderFrame(job, frame) {
    const project = root.FFV2Studio?.getProject?.();
    if (!project) throw new Error('Open a V2 project before rendering.');
    const sequence = root.FFV2Core.getMainSequence(project);
    const canvas = root.document.createElement('canvas');
    canvas.width = sequence.width;
    canvas.height = sequence.height;
    const studio = root.FFV2Studio;
    const result = await root.FFV2Renderer.composeFrame({
      project,
      frame,
      canvas,
      resolveAsset: studio.resolveRenderAsset,
      resolveModelAsset: studio.resolve3DAsset,
      modelAssets: studio.getAssetRecords(),
      resolveModelDependency: studio.resolve3DDependency
    });
    if (result.warnings.length) {
      throw new Error('Frame ' + frame + ' has a render warning: ' + result.warnings[0].message);
    }
    const blob = await new Promise((resolve, reject) => {
      canvas.toBlob(value => value ? resolve(value) : reject(new Error('PNG encoding failed at frame ' + frame + '.')), 'image/png');
    });
    if (!blob.size) throw new Error('PNG encoder returned an empty frame at ' + frame + '.');
    await studio.renderStorage.saveFrame(job.id, frame, blob, {
      width: result.width, height: result.height, drawn_layers: result.drawn, backend: result.backend
    });
    return { blob, result };
  }

  async function createJob(chunkSize) {
    const project = root.FFV2Studio?.getProject?.();
    if (!project) throw new Error('Open a V2 project before creating a render job.');
    const sequence = root.FFV2Core.getMainSequence(project);
    const total = Math.max(0, Math.round(Number(sequence.duration_frames) || 0));
    if (!total) throw new Error('The V2 sequence has no frames to render. Assemble or extend the timeline first.');
    const size = Math.round(Number(chunkSize) || 24);
    if (size < 1 || size > 240) throw new Error('Chunk size must be between 1 and 240 frames.');
    const job = {
      id: 'render-' + project.project.id + '-' + Date.now().toString(36),
      project_id: project.project.id,
      project_name: project.project.name || 'FrameForge project',
      project_signature: await signature(project),
      created_at: stamp(),
      updated_at: stamp(),
      status: 'queued',
      width: sequence.width,
      height: sequence.height,
      fps: sequence.fps,
      total_frames: total,
      chunk_size: size,
      completed_frames: 0,
      rendered_frames: 0,
      skipped_frames: 0,
      chunks: chunkCount({ total_frames: total, chunk_size: size }),
      error: '',
      warnings: []
    };
    await root.FFV2Studio.renderStorage.saveJob(job);
    currentJob = job;
    updateProgress(job);
    setStatus('Render job created. Press Start / resume to render its first chunk.', 'success');
    await refreshJobs();
    return job;
  }

  async function refreshJobs() {
    const select = $('ffv2RenderQueueJobs');
    const list = await root.FFV2Studio.renderStorage.listJobs();
    if (!select) return list;
    const previous = currentJob?.id || select.value;
    select.replaceChildren();
    list.forEach(job => {
      const option = root.document.createElement('option');
      option.value = job.id;
      option.textContent = job.project_name + ' · ' + job.status + ' · ' + job.completed_frames + '/' + job.total_frames;
      select.append(option);
    });
    if (previous && list.some(job => job.id === previous)) select.value = previous;
    if (!currentJob && list.length) {
      currentJob = list[0];
      select.value = currentJob.id;
      updateProgress(currentJob);
    }
    renderChunkChoices();
    return list;
  }

  function renderChunkChoices() {
    const select = $('ffv2RenderQueueChunk');
    if (!select || !currentJob) return;
    const old = Number(select.value) || 0;
    select.replaceChildren();
    for (let index = 0; index < currentJob.chunks; index++) {
      const bounds = chunkBounds(currentJob, index);
      const option = root.document.createElement('option');
      option.value = String(index);
      option.textContent = 'Chunk ' + (index + 1) + ' · frames ' + bounds.start + '–' + (bounds.end - 1);
      select.append(option);
    }
    if (old < currentJob.chunks) select.value = String(old);
  }

  async function selectJob(id) {
    const job = await root.FFV2Studio.renderStorage.getJob(id);
    if (!job) throw new Error('Render job record was not found.');
    if (job.status === 'running') {
      job.status = 'paused';
      job.updated_at = stamp();
      await root.FFV2Studio.renderStorage.saveJob(job);
    }
    currentJob = job;
    updateProgress(job);
    renderChunkChoices();
    setStatus(job.status === 'complete'
      ? 'This render job is complete. Export its chunks or review the result.'
      : 'Loaded saved job. Completed frame files will be skipped when resumed.', 'success');
  }

  async function resumeJob() {
    if (running) return;
    if (!currentJob) {
      const jobs = await refreshJobs();
      if (!jobs.length) throw new Error('Create a render job first.');
      currentJob = jobs[0];
    }
    const project = root.FFV2Studio.getProject();
    if (!project || project.project.id !== currentJob.project_id) {
      throw new Error('This render job belongs to a different V2 project. Open that project to resume it.');
    }
    const currentSignature = await signature(project);
    if (currentSignature !== currentJob.project_signature) {
      throw new Error('The project changed after this render job was created. Create a new render job so frames do not mix different edits.');
    }
    if (currentJob.status === 'complete') {
      setStatus('This render job is already complete.', 'success');
      return;
    }
    running = true;
    pauseRequested = false;
    currentJob.status = 'running';
    currentJob.error = '';
    currentJob.updated_at = stamp();
    await root.FFV2Studio.renderStorage.saveJob(currentJob);
    updateProgress(currentJob);
    setStatus('Rendering frame chunks locally. You can pause and resume safely.', 'info');
    try {
      for (let frame = 0; frame < currentJob.total_frames; frame++) {
        if (pauseRequested) break;
        const existing = await root.FFV2Studio.renderStorage.getFrame(currentJob.id, frame);
        if (existing?.blob?.size) {
          currentJob.skipped_frames = (currentJob.skipped_frames || 0) + 1;
          currentJob.completed_frames = await root.FFV2Studio.renderStorage.countFrames(currentJob.id);
          continue;
        }
        try {
          const rendered = await renderFrame(currentJob, frame);
          currentJob.rendered_frames = (currentJob.rendered_frames || 0) + 1;
          currentJob.completed_frames = await root.FFV2Studio.renderStorage.countFrames(currentJob.id);
          currentJob.updated_at = stamp();
          await root.FFV2Studio.renderStorage.saveJob(currentJob);
          updateProgress(currentJob, 'Rendered frame ' + frame + ' · ' +
            currentJob.completed_frames + '/' + currentJob.total_frames);
        } catch (error) {
          currentJob.status = 'failed';
          currentJob.error = error.message;
          currentJob.updated_at = stamp();
          await root.FFV2Studio.renderStorage.saveJob(currentJob);
          throw error;
        }
        if (frame % 2 === 1) await new Promise(resolve => root.setTimeout(resolve, 0));
      }
      currentJob.completed_frames = await root.FFV2Studio.renderStorage.countFrames(currentJob.id);
      currentJob.status = currentJob.completed_frames >= currentJob.total_frames ? 'complete' : 'paused';
      currentJob.updated_at = stamp();
      await root.FFV2Studio.renderStorage.saveJob(currentJob);
      updateProgress(currentJob);
      setStatus(currentJob.status === 'complete'
        ? 'Render complete. Export each completed chunk as a ZIP of numbered PNG frames.'
        : 'Render paused safely. Resume later; stored frames will not be rendered again.', 'success');
    } finally {
      running = false;
      await refreshJobs();
      if (currentJob) await selectJob(currentJob.id);
      updateButtons();
    }
  }

  function updateButtons() {
    const start = $('ffv2RenderQueueStart');
    const pause = $('ffv2RenderQueuePause');
    if (start) start.disabled = running || currentJob?.status === 'complete';
    if (pause) pause.disabled = !running;
  }

  function crc32(bytes) {
    let crc = 0xffffffff;
    for (let i = 0; i < bytes.length; i++) {
      crc ^= bytes[i];
      for (let bit = 0; bit < 8; bit++) crc = (crc >>> 1) ^ (0xedb88320 & -(crc & 1));
    }
    return (crc ^ 0xffffffff) >>> 0;
  }

  function dosStamp(date) {
    const year = Math.max(1980, date.getFullYear());
    return {
      time: (date.getHours() << 11) | (date.getMinutes() << 5) | Math.floor(date.getSeconds() / 2),
      date: ((year - 1980) << 9) | ((date.getMonth() + 1) << 5) | date.getDate()
    };
  }

  function createZip(files) {
    const encoder = new TextEncoder();
    const localParts = [];
    const centralParts = [];
    let offset = 0;
    const stampValue = dosStamp(new Date());
    for (const file of files) {
      const name = encoder.encode(file.name);
      const data = file.data instanceof Uint8Array ? file.data : new Uint8Array(file.data);
      const checksum = crc32(data);
      const local = new Uint8Array(30 + name.length);
      const lv = new DataView(local.buffer);
      lv.setUint32(0, 0x04034b50, true);
      lv.setUint16(4, 20, true);
      lv.setUint16(6, 0, true);
      lv.setUint16(8, 0, true);
      lv.setUint16(10, stampValue.time, true);
      lv.setUint16(12, stampValue.date, true);
      lv.setUint32(14, checksum, true);
      lv.setUint32(18, data.length, true);
      lv.setUint32(22, data.length, true);
      lv.setUint16(26, name.length, true);
      lv.setUint16(28, 0, true);
      local.set(name, 30);
      localParts.push(local, data);
      const central = new Uint8Array(46 + name.length);
      const cv = new DataView(central.buffer);
      cv.setUint32(0, 0x02014b50, true);
      cv.setUint16(4, 20, true);
      cv.setUint16(6, 20, true);
      cv.setUint16(8, 0, true);
      cv.setUint16(10, 0, true);
      cv.setUint16(12, stampValue.time, true);
      cv.setUint16(14, stampValue.date, true);
      cv.setUint32(16, checksum, true);
      cv.setUint32(20, data.length, true);
      cv.setUint32(24, data.length, true);
      cv.setUint16(28, name.length, true);
      cv.setUint16(30, 0, true);
      cv.setUint16(32, 0, true);
      cv.setUint16(34, 0, true);
      cv.setUint16(36, 0, true);
      cv.setUint32(38, 0, true);
      cv.setUint32(42, offset, true);
      central.set(name, 46);
      centralParts.push(central);
      offset += local.length + data.length;
    }
    const centralSize = centralParts.reduce((sum, part) => sum + part.length, 0);
    const end = new Uint8Array(22);
    const ev = new DataView(end.buffer);
    ev.setUint32(0, 0x06054b50, true);
    ev.setUint16(4, 0, true);
    ev.setUint16(6, 0, true);
    ev.setUint16(8, files.length, true);
    ev.setUint16(10, files.length, true);
    ev.setUint32(12, centralSize, true);
    ev.setUint32(16, offset, true);
    ev.setUint16(20, 0, true);
    return new Blob([...localParts, ...centralParts, end], { type: 'application/zip' });
  }

  async function exportChunk() {
    if (!currentJob) throw new Error('Select a render job first.');
    const index = Number($('ffv2RenderQueueChunk')?.value) || 0;
    const bounds = chunkBounds(currentJob, index);
    const frames = await root.FFV2Studio.renderStorage.getFrames(currentJob.id, bounds.start, bounds.end);
    if (frames.length !== bounds.end - bounds.start) {
      throw new Error('This chunk is incomplete. Render/resume the job before exporting it.');
    }
    const files = [];
    for (const record of frames) {
      files.push({
        name: 'frames/frame_' + String(record.frame).padStart(6, '0') + '.png',
        data: new Uint8Array(await record.blob.arrayBuffer())
      });
    }
    const manifest = {
      format: 'frameforge-render-chunk',
      version: 1,
      job_id: currentJob.id,
      project_id: currentJob.project_id,
      project_signature: currentJob.project_signature,
      chunk_index: index,
      start_frame: bounds.start,
      end_frame_exclusive: bounds.end,
      width: currentJob.width,
      height: currentJob.height,
      fps: currentJob.fps,
      frame_count: frames.length,
      created_at: stamp()
    };
    files.push({ name: 'chunk-manifest.json', data: encoderBytes(JSON.stringify(manifest, null, 2)) });
    const archive = createZip(files);
    const url = URL.createObjectURL(archive);
    const anchor = root.document.createElement('a');
    anchor.href = url;
    anchor.download = currentJob.id + '-chunk-' + String(index + 1).padStart(4, '0') + '.zip';
    root.document.body.append(anchor);
    anchor.click();
    anchor.remove();
    root.setTimeout(() => URL.revokeObjectURL(url), 60000);
    setStatus('Exported chunk ' + (index + 1) + ' (' + frames.length + ' PNG frames, ' +
      (archive.size / MB).toFixed(2) + ' MB).', 'success');
  }

  function encoderBytes(value) { return new TextEncoder().encode(value); }

  function bind() {
    if (uiBound || !root.FFV2Studio || !root.FFV2Renderer || !$('ffv2RenderQueuePanel')) return;
    uiBound = true;
    $('ffv2RenderQueueCreate').addEventListener('click', async () => {
      try { await createJob(Number($('ffv2RenderQueueChunkSize').value)); updateButtons(); }
      catch (error) { setStatus(error.message, 'error'); }
    });
    $('ffv2RenderQueueStart').addEventListener('click', async () => {
      try { await resumeJob(); } catch (error) { setStatus(error.message, 'error'); }
    });
    $('ffv2RenderQueuePause').addEventListener('click', () => {
      pauseRequested = true;
      setStatus('Pause requested. The current frame will finish and be saved before pausing.', 'info');
    });
    $('ffv2RenderQueueExport').addEventListener('click', async () => {
      try { await exportChunk(); } catch (error) { setStatus(error.message, 'error'); }
    });
    $('ffv2RenderQueueJobs').addEventListener('change', async event => {
      try { await selectJob(event.target.value); updateButtons(); } catch (error) { setStatus(error.message, 'error'); }
    });
    $('ffv2RenderQueueChunk').addEventListener('change', updateButtons);
    root.document.addEventListener('ffv2:ready', async () => {
      try {
        const jobs = await root.FFV2Studio.renderStorage.listJobs();
        for (const job of jobs) {
          if (job.status === 'running') {
            job.status = 'paused';
            job.updated_at = stamp();
            await root.FFV2Studio.renderStorage.saveJob(job);
          }
        }
        await refreshJobs();
        updateButtons();
      } catch (error) { setStatus('Render queue storage unavailable: ' + error.message, 'error'); }
    }, { once: true });
  }

  root.FFV2RenderQueue = {
    createJob,
    resumeJob,
    pause: () => { pauseRequested = true; },
    exportChunk,
    refreshJobs,
    getCurrentJob: () => currentJob,
    createZip,
    signature
  };
  if (root.document) {
    if (root.document.readyState === 'loading') root.document.addEventListener('DOMContentLoaded', bind);
    else bind();
    root.document.addEventListener('ffv2:ready', bind, { once: true });
  }
})(typeof globalThis !== 'undefined' ? globalThis : this);
