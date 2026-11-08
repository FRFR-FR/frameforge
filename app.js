(() => {
  'use strict';

  const $ = (id) => document.getElementById(id);
  const paintCanvas = $('paintCanvas');
  const scriptCanvas = $('scriptCanvas');
  const onionCanvas = $('onionCanvas');
  const paintCtx = paintCanvas.getContext('2d', { willReadFrequently: true });
  const scriptCtx = scriptCanvas.getContext('2d');
  const onionCtx = onionCanvas.getContext('2d');
  const outputCanvas = document.createElement('canvas');
  const outputCtx = outputCanvas.getContext('2d');

  const PRESETS = {
    portrait: { width: 720, height: 1280 },
    landscape: { width: 1280, height: 720 },
    square: { width: 1080, height: 1080 }
  };
  const state = {
    width: 720,
    height: 1280,
    fps: 30,
    frames: [makeFrame()],
    current: 0,
    tool: 'brush',
    color: '#e7edf7',
    brushSize: 8,
    opacity: 0.9,
    onion: false,
    playing: false,
    loop: true,
    zoom: 'fit',
    pointerDown: false,
    lastPoint: null,
    strokeHistoryPushed: false,
    playbackRaf: 0,
    playbackLast: 0,
    playbackAccumulator: 0,
    recorder: null,
    recorderChunks: [],
    recording: false,
    previousLoopSetting: true,
    autosaveTimer: 0,
    dbPromise: null,
    toastTimer: 0
  };

  function makeFrame(data = {}) {
    return {
      id: crypto.randomUUID ? crypto.randomUUID() : `f-${Date.now()}-${Math.random().toString(16).slice(2)}`,
      paintData: data.paintData || '',
      scriptData: data.scriptData || '',
      script: data.script || '',
      undoStack: [],
      redoStack: []
    };
  }

  function currentFrame() { return state.frames[state.current]; }
  function clamp(value, min, max) { return Math.min(max, Math.max(min, value)); }
  function waitImage(src) {
    return new Promise((resolve, reject) => {
      if (!src) return resolve(null);
      const img = new Image();
      img.onload = () => resolve(img);
      img.onerror = reject;
      img.src = src;
    });
  }

  function showToast(message, duration = 2300) {
    const toast = $('toast');
    toast.textContent = message;
    toast.classList.add('show');
    clearTimeout(state.toastTimer);
    state.toastTimer = setTimeout(() => toast.classList.remove('show'), duration);
  }

  function setSaveStatus(text) { $('saveStatus').textContent = text; }

  function db() {
    if (state.dbPromise) return state.dbPromise;
    state.dbPromise = new Promise((resolve) => {
      if (!('indexedDB' in window)) return resolve(null);
      const request = indexedDB.open('FrameForgeDB', 1);
      request.onupgradeneeded = () => {
        const database = request.result;
        if (!database.objectStoreNames.contains('projects')) database.createObjectStore('projects', { keyPath: 'id' });
      };
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => resolve(null);
    });
    return state.dbPromise;
  }

  function serializableProject() {
    saveCurrentFrame();
    return {
      format: 'frameforge-project',
      version: 1,
      name: $('projectName').value.trim() || 'Untitled Film',
      width: state.width,
      height: state.height,
      fps: state.fps,
      frames: state.frames.map((frame) => ({
        paintData: frame.paintData,
        scriptData: frame.scriptData,
        script: frame.script
      }))
    };
  }

  function scheduleAutosave() {
    setSaveStatus('Saving…');
    clearTimeout(state.autosaveTimer);
    state.autosaveTimer = setTimeout(async () => {
      const database = await db();
      if (!database) {
        setSaveStatus('Export JSON to save');
        return;
      }
      try {
        const project = serializableProject();
        const transaction = database.transaction('projects', 'readwrite');
        transaction.objectStore('projects').put({ id: 'autosave', project, savedAt: Date.now() });
        transaction.oncomplete = () => setSaveStatus('Saved locally');
        transaction.onerror = () => setSaveStatus('Save failed');
      } catch (error) {
        console.warn('FrameForge autosave failed:', error);
        setSaveStatus('Export JSON to save');
      }
    }, 550);
  }

  async function restoreAutosave() {
    const database = await db();
    if (!database) return false;
    return new Promise((resolve) => {
      const request = database.transaction('projects', 'readonly').objectStore('projects').get('autosave');
      request.onsuccess = () => {
        const record = request.result;
        if (!record?.project) return resolve(false);
        try {
          loadProjectObject(record.project, false);
          resolve(true);
        } catch (error) {
          console.warn('Could not restore autosave:', error);
          resolve(false);
        }
      };
      request.onerror = () => resolve(false);
    });
  }

  function setCanvasSize(width, height) {
    state.width = width;
    state.height = height;
    for (const canvas of [paintCanvas, scriptCanvas, onionCanvas, outputCanvas]) {
      canvas.width = width;
      canvas.height = height;
    }
    $('canvasDimensions').textContent = `${width} × ${height} · Transparent`;
    $('exportSizeLabel').textContent = `${width} × ${height}`;
    renderStageSize();
  }

  function renderStageSize() {
    const canvases = [paintCanvas, scriptCanvas, onionCanvas];
    if (state.zoom === '100%') {
      for (const canvas of canvases) {
        canvas.style.width = `${state.width}px`;
        canvas.style.height = `${state.height}px`;
      }
      $('zoomLabel').textContent = '100%';
    } else {
      for (const canvas of canvases) {
        canvas.style.width = 'auto';
        canvas.style.height = 'auto';
      }
      $('zoomLabel').textContent = 'Fit';
    }
  }

  async function drawDataOnCanvas(canvasCtx, src) {
    canvasCtx.clearRect(0, 0, state.width, state.height);
    if (!src) return;
    try {
      const image = await waitImage(src);
      if (image) canvasCtx.drawImage(image, 0, 0, state.width, state.height);
    } catch (error) {
      console.warn('Frame image could not be loaded:', error);
    }
  }

  function saveCurrentFrame() {
    const frame = currentFrame();
    if (!frame) return;
    try {
      frame.paintData = paintCanvas.toDataURL('image/png');
      frame.scriptData = scriptCanvas.toDataURL('image/png');
      frame.script = $('frameScript').value;
    } catch (error) {
      console.warn('Could not save frame pixels:', error);
    }
  }

  async function activateFrame(index, options = {}) {
    if (!state.frames.length) state.frames.push(makeFrame());
    if (options.save !== false) saveCurrentFrame();
    state.current = clamp(index, 0, state.frames.length - 1);
    const frame = currentFrame();
    $('frameScript').value = frame.script || '';
    await Promise.all([
      drawDataOnCanvas(paintCtx, frame.paintData),
      drawDataOnCanvas(scriptCtx, frame.scriptData)
    ]);
    renderOnion();
    renderOutput();
    updateTimelineUi();
    updateUndoButtons();
    if (options.autosave !== false) scheduleAutosave();
  }

  async function renderOnion() {
    onionCtx.clearRect(0, 0, state.width, state.height);
    if (!state.onion || state.playing) return;
    const previous = state.frames[state.current - 1];
    const next = state.frames[state.current + 1];
    const ghostCanvas = document.createElement('canvas');
    ghostCanvas.width = state.width;
    ghostCanvas.height = state.height;
    const ghostCtx = ghostCanvas.getContext('2d');
    if (previous) {
      try {
        const [paint, code] = await Promise.all([waitImage(previous.paintData), waitImage(previous.scriptData)]);
        ghostCtx.clearRect(0, 0, state.width, state.height);
        if (paint) ghostCtx.drawImage(paint, 0, 0);
        if (code) ghostCtx.drawImage(code, 0, 0);
        onionCtx.globalAlpha = 0.19;
        onionCtx.drawImage(ghostCanvas, 0, 0);
      } catch (_) { /* corrupted ghost frame: ignore */ }
    }
    if (next) {
      try {
        const [paint, code] = await Promise.all([waitImage(next.paintData), waitImage(next.scriptData)]);
        ghostCtx.clearRect(0, 0, state.width, state.height);
        if (paint) ghostCtx.drawImage(paint, 0, 0);
        if (code) ghostCtx.drawImage(code, 0, 0);
        onionCtx.globalAlpha = 0.10;
        onionCtx.drawImage(ghostCanvas, 0, 0);
      } catch (_) { /* corrupted ghost frame: ignore */ }
    }
    onionCtx.globalAlpha = 1;
  }

  function renderOutput() {
    outputCtx.clearRect(0, 0, state.width, state.height);
    outputCtx.drawImage(paintCanvas, 0, 0);
    outputCtx.drawImage(scriptCanvas, 0, 0);
  }

  function updateTimelineUi() {
    $('frameCounter').textContent = `Frame ${state.current + 1} / ${state.frames.length}`;
    $('timelineScrubber').max = String(Math.max(0, state.frames.length - 1));
    $('timelineScrubber').value = String(state.current);
    $('timeReadout').textContent = formatTime(state.current / state.fps);
    $('projectFrameCount').textContent = String(state.frames.length);
    $('projectDuration').textContent = `${(state.frames.length / state.fps).toFixed(2)} sec`;
    $('fpsInput').value = String(state.fps);
    $('exportFpsLabel').textContent = `${state.fps} FPS`;
    $('playBtn').textContent = state.playing ? 'Ⅱ' : '▶';
    $('playBtn').title = state.playing ? 'Pause' : 'Play';
    renderFrameStrip();
  }

  function formatTime(seconds) {
    const totalFrames = Math.max(0, Math.floor(seconds * state.fps));
    const sec = Math.floor(totalFrames / state.fps);
    const frame = totalFrames % state.fps;
    const mins = Math.floor(sec / 60);
    const remain = sec % 60;
    return `${String(mins).padStart(2, '0')}:${String(remain).padStart(2, '0')}:${String(frame).padStart(2, '0')}`;
  }

  function renderFrameStrip() {
    const strip = $('frameStrip');
    strip.innerHTML = '';
    state.frames.forEach((frame, index) => {
      const card = document.createElement('button');
      card.type = 'button';
      card.className = `frame-card${index === state.current ? ' active' : ''}`;
      card.setAttribute('aria-label', `Go to frame ${index + 1}`);
      const thumbnail = document.createElement('canvas');
      thumbnail.width = 72;
      thumbnail.height = 96;
      const thumbCtx = thumbnail.getContext('2d');
      thumbCtx.fillStyle = '#182433';
      thumbCtx.fillRect(0, 0, 72, 96);
      const complete = (image) => {
        if (image) {
          const scale = Math.min(66 / image.width, 88 / image.height);
          const w = image.width * scale;
          const h = image.height * scale;
          thumbCtx.drawImage(image, (72 - w) / 2, (96 - h) / 2, w, h);
        }
      };
      if (frame.paintData) {
        const image = new Image();
        image.onload = () => complete(image);
        image.src = frame.paintData;
      }
      if (frame.scriptData) {
        const image = new Image();
        image.onload = () => complete(image);
        image.src = frame.scriptData;
      }
      const label = document.createElement('span');
      label.textContent = String(index + 1).padStart(2, '0');
      card.append(thumbnail, label);
      if (frame.script) {
        const dot = document.createElement('i');
        dot.className = 'script-dot';
        card.append(dot);
      }
      card.addEventListener('click', () => {
        if (state.playing) stopPlayback();
        activateFrame(index);
      });
      strip.append(card);
    });
    const active = strip.children[state.current];
    if (active && state.playing) active.scrollIntoView({ block: 'nearest', inline: 'nearest' });
  }

  function updateUndoButtons() {
    const frame = currentFrame();
    $('undoBtn').disabled = !frame?.undoStack.length;
    $('redoBtn').disabled = !frame?.redoStack.length;
    $('undoBtn').style.opacity = $('undoBtn').disabled ? '.4' : '1';
    $('redoBtn').style.opacity = $('redoBtn').disabled ? '.4' : '1';
  }

  function pushHistory() {
    const frame = currentFrame();
    frame.undoStack.push(paintCanvas.toDataURL('image/png'));
    if (frame.undoStack.length > 25) frame.undoStack.shift();
    frame.redoStack.length = 0;
    updateUndoButtons();
  }

  async function undo() {
    const frame = currentFrame();
    if (!frame.undoStack.length) return;
    frame.redoStack.push(paintCanvas.toDataURL('image/png'));
    const previous = frame.undoStack.pop();
    await drawDataOnCanvas(paintCtx, previous);
    saveCurrentFrame();
    renderOutput();
    renderFrameStrip();
    updateUndoButtons();
    scheduleAutosave();
  }

  async function redo() {
    const frame = currentFrame();
    if (!frame.redoStack.length) return;
    frame.undoStack.push(paintCanvas.toDataURL('image/png'));
    const next = frame.redoStack.pop();
    await drawDataOnCanvas(paintCtx, next);
    saveCurrentFrame();
    renderOutput();
    renderFrameStrip();
    updateUndoButtons();
    scheduleAutosave();
  }

  function setTool(tool) {
    state.tool = tool;
    document.querySelectorAll('.tool[data-tool]').forEach((button) => button.classList.toggle('active', button.dataset.tool === tool));
    paintCanvas.style.cursor = tool === 'eraser' ? 'cell' : 'crosshair';
  }

  function pointFromEvent(event) {
    const rect = paintCanvas.getBoundingClientRect();
    return {
      x: (event.clientX - rect.left) * (state.width / rect.width),
      y: (event.clientY - rect.top) * (state.height / rect.height),
      pressure: event.pressure && event.pressure > 0 ? event.pressure : 0.5
    };
  }

  function beginStroke(event) {
    if (state.playing || event.button > 0) return;
    event.preventDefault();
    paintCanvas.setPointerCapture?.(event.pointerId);
    state.pointerDown = true;
    state.lastPoint = pointFromEvent(event);
    state.strokeHistoryPushed = false;
    pushHistory();
    state.strokeHistoryPushed = true;
    paintCtx.save();
    paintCtx.lineCap = 'round';
    paintCtx.lineJoin = 'round';
    applyBrushDefaults(state.lastPoint.pressure);
    if (state.tool === 'airbrush' || state.tool === 'texture') stampBrush(state.lastPoint, state.lastPoint);
    else {
      paintCtx.beginPath();
      paintCtx.moveTo(state.lastPoint.x, state.lastPoint.y);
      paintCtx.lineTo(state.lastPoint.x + 0.01, state.lastPoint.y + 0.01);
      paintCtx.stroke();
    }
  }

  function applyBrushDefaults(pressure) {
    const pressureScale = clamp(pressure || 0.5, 0.25, 1.2);
    const width = Math.max(0.6, state.brushSize * pressureScale);
    paintCtx.globalCompositeOperation = state.tool === 'eraser' ? 'destination-out' : 'source-over';
    paintCtx.globalAlpha = state.tool === 'pencil' ? state.opacity * 0.42 : state.opacity;
    paintCtx.strokeStyle = state.color;
    paintCtx.fillStyle = state.color;
    paintCtx.lineWidth = state.tool === 'ink' ? Math.max(1, width * 0.72) : width;
    paintCtx.shadowBlur = state.tool === 'brush' ? Math.max(0, width * 0.11) : 0;
    paintCtx.shadowColor = state.color;
  }

  function stampBrush(point, previous) {
    const dx = point.x - previous.x;
    const dy = point.y - previous.y;
    const distance = Math.max(1, Math.hypot(dx, dy));
    const steps = Math.ceil(distance / Math.max(2, state.brushSize * 0.22));
    for (let i = 0; i <= steps; i++) {
      const x = previous.x + dx * (i / steps);
      const y = previous.y + dy * (i / steps);
      if (state.tool === 'airbrush') {
        const radius = Math.max(2, state.brushSize * 1.55);
        const gradient = paintCtx.createRadialGradient(x, y, 0, x, y, radius);
        gradient.addColorStop(0, hexToRgba(state.color, state.opacity * 0.18));
        gradient.addColorStop(0.55, hexToRgba(state.color, state.opacity * 0.07));
        gradient.addColorStop(1, hexToRgba(state.color, 0));
        paintCtx.globalAlpha = 1;
        paintCtx.fillStyle = gradient;
        paintCtx.beginPath();
        paintCtx.arc(x, y, radius, 0, Math.PI * 2);
        paintCtx.fill();
      } else {
        const specks = Math.ceil(state.brushSize / 3.5);
        paintCtx.globalAlpha = state.opacity * 0.52;
        paintCtx.fillStyle = state.color;
        for (let j = 0; j < specks; j++) {
          const angle = Math.random() * Math.PI * 2;
          const radius = Math.random() * state.brushSize * 0.55;
          const dot = Math.random() * Math.max(0.6, state.brushSize * 0.085) + 0.45;
          paintCtx.beginPath();
          paintCtx.arc(x + Math.cos(angle) * radius, y + Math.sin(angle) * radius, dot, 0, Math.PI * 2);
          paintCtx.fill();
        }
      }
    }
  }

  function hexToRgba(hex, alpha) {
    const value = hex.replace('#', '');
    const bigint = parseInt(value.length === 3 ? value.split('').map((c) => c + c).join('') : value, 16);
    const r = (bigint >> 16) & 255;
    const g = (bigint >> 8) & 255;
    const b = bigint & 255;
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
  }

  function moveStroke(event) {
    if (!state.pointerDown || !state.lastPoint) return;
    event.preventDefault();
    const next = pointFromEvent(event);
    const previous = state.lastPoint;
    $('cursorPosition').textContent = `${Math.round(next.x)}, ${Math.round(next.y)}`;
    applyBrushDefaults(next.pressure);
    if (state.tool === 'airbrush' || state.tool === 'texture') {
      stampBrush(next, previous);
    } else {
      const midX = (previous.x + next.x) / 2;
      const midY = (previous.y + next.y) / 2;
      paintCtx.beginPath();
      paintCtx.moveTo(previous.x, previous.y);
      paintCtx.quadraticCurveTo(previous.x, previous.y, midX, midY);
      paintCtx.stroke();
      paintCtx.beginPath();
      paintCtx.moveTo(midX, midY);
      paintCtx.lineTo(next.x, next.y);
      paintCtx.stroke();
    }
    state.lastPoint = next;
  }

  function endStroke(event) {
    if (!state.pointerDown) return;
    state.pointerDown = false;
    state.lastPoint = null;
    paintCtx.restore();
    saveCurrentFrame();
    renderOutput();
    renderFrameStrip();
    scheduleAutosave();
    if (event?.pointerId !== undefined) {
      try { paintCanvas.releasePointerCapture(event.pointerId); } catch (_) { /* already released */ }
    }
  }

  async function runFrameScript() {
    const source = $('frameScript').value;
    const scratch = document.createElement('canvas');
    scratch.width = state.width;
    scratch.height = state.height;
    const context = scratch.getContext('2d');
    try {
      // The script is authored by the project owner and executes locally. Do not run untrusted code.
      const execute = new Function('ctx', 'frame', 'width', 'height', 'time', `"use strict";\n${source}`);
      execute(context, state.current + 1, state.width, state.height, state.current / state.fps);
      const frame = currentFrame();
      frame.script = source;
      frame.scriptData = scratch.toDataURL('image/png');
      await drawDataOnCanvas(scriptCtx, frame.scriptData);
      renderOutput();
      renderFrameStrip();
      scheduleAutosave();
      showToast('Code rendered onto this frame.');
    } catch (error) {
      console.error(error);
      showToast(`Script error: ${error.message}`, 4200);
    }
  }

  async function runScriptOnAllFrames() {
    const source = $('frameScript').value;
    if (!source.trim()) { showToast('Write some JavaScript drawing code first.'); return; }
    if (state.frames.length > 120 && !confirm(`Render this script across ${state.frames.length} frames? This may take a while on a phone.`)) return;
    saveCurrentFrame();
    const originalIndex = state.current;
    const runButton = $('runAllScriptsBtn');
    runButton.disabled = true;
    runButton.textContent = 'Rendering…';
    try {
      for (let index = 0; index < state.frames.length; index++) {
        const scratch = document.createElement('canvas');
        scratch.width = state.width;
        scratch.height = state.height;
        const context = scratch.getContext('2d');
        const execute = new Function('ctx', 'frame', 'width', 'height', 'time', `"use strict";\n${source}`);
        execute(context, index + 1, state.width, state.height, index / state.fps);
        state.frames[index].script = source;
        state.frames[index].scriptData = scratch.toDataURL('image/png');
        if (index % 2 === 1) await new Promise((resolve) => setTimeout(resolve, 0));
      }
      await activateFrame(originalIndex, { save: false });
      renderFrameStrip();
      scheduleAutosave();
      showToast(`Drawing code rendered across all ${state.frames.length} frames.`);
    } catch (error) {
      console.error(error);
      showToast(`Script stopped at a frame error: ${error.message}`, 4500);
    } finally {
      runButton.disabled = false;
      runButton.textContent = 'Run all frames';
    }
  }

  async function clearScriptLayer() {
    const frame = currentFrame();
    frame.script = $('frameScript').value;
    frame.scriptData = '';
    scriptCtx.clearRect(0, 0, state.width, state.height);
    saveCurrentFrame();
    renderOutput();
    renderFrameStrip();
    scheduleAutosave();
    showToast('Code layer cleared. Your drawing layer is untouched.');
  }

  function bakeScriptLayer() {
    pushHistory();
    paintCtx.drawImage(scriptCanvas, 0, 0);
    scriptCtx.clearRect(0, 0, state.width, state.height);
    const frame = currentFrame();
    frame.scriptData = '';
    frame.script = '';
    $('frameScript').value = '';
    saveCurrentFrame();
    renderOutput();
    renderFrameStrip();
    scheduleAutosave();
    showToast('Code layer merged into the drawing layer.');
  }

  function starterCityScript() {
    return `// DETAILED NIGHT CITY — procedural Canvas 2D example
// Available values: ctx, frame, width, height, time
// Edit the curves, palette, and details to make the scene your own.
const W = width, H = height;
const horizon = H * 0.70;
const seed = 9341;
let seedState = seed;
const rand = () => { seedState = (seedState * 1664525 + 1013904223) >>> 0; return seedState / 4294967296; };

// Deep atmospheric sky with a soft urban glow
const sky = ctx.createLinearGradient(0, 0, 0, H);
sky.addColorStop(0, '#070d1b');
sky.addColorStop(0.54, '#17243b');
sky.addColorStop(1, '#50354b');
ctx.fillStyle = sky; ctx.fillRect(0, 0, W, H);
const haze = ctx.createRadialGradient(W*.52, H*.68, 5, W*.52, H*.68, W*.67);
haze.addColorStop(0, 'rgba(231,116,103,.25)'); haze.addColorStop(1, 'rgba(231,116,103,0)');
ctx.fillStyle = haze; ctx.fillRect(0, 0, W, H);

// Stars and distant aircraft lights
for (let i=0; i<175; i++) {
  const x = rand()*W, y = rand()*H*.49, r = rand()*1.15+.25;
  ctx.globalAlpha = (rand()*.65+.2) * (0.72 + 0.28*Math.sin(time*2.1+i)); ctx.fillStyle = i%8===0 ? '#f5c9b5' : '#c8dbf4';
  ctx.beginPath(); ctx.arc(x,y,r,0,Math.PI*2); ctx.fill();
}
ctx.globalAlpha = 1;

// Far skyline: irregular silhouettes and individually lit windows
for (let i=0, x=-8; x<W+10; i++) {
  const bw = 24 + rand()*57, bh = H*(.10 + rand()*.22), top = horizon - bh;
  ctx.fillStyle = i%3===0 ? '#101c2d' : '#0c1727';
  ctx.fillRect(x, top, bw, bh+12);
  ctx.fillStyle = 'rgba(144,178,205,.15)'; ctx.fillRect(x+3,top+5,1,bh-8);
  for (let wy=top+10; wy<horizon-6; wy+=9) for (let wx=x+5; wx<x+bw-4; wx+=8) {
    if (rand()>.58) { ctx.globalAlpha = .18+rand()*.5; ctx.fillStyle = rand()>.75 ? '#ffcb87' : '#9ac5e7'; ctx.fillRect(wx,wy,2.1,3.4); }
  }
  ctx.globalAlpha = 1; x += bw-1;
}

// Main architecture with ledges, roof equipment and a water tower
const buildings = [
  {x:W*.04,w:W*.19,h:H*.40,c:'#111d2c'},
  {x:W*.25,w:W*.16,h:H*.56,c:'#101b2c'},
  {x:W*.44,w:W*.20,h:H*.47,c:'#142237'},
  {x:W*.67,w:W*.15,h:H*.61,c:'#101b2c'},
  {x:W*.84,w:W*.13,h:H*.39,c:'#152238'}
];
for (const b of buildings) {
  const top=horizon-b.h;
  const wall=ctx.createLinearGradient(b.x,top,b.x+b.w,top+b.h);
  wall.addColorStop(0,b.c); wall.addColorStop(.52,'#1a2a40'); wall.addColorStop(1,'#091321');
  ctx.fillStyle=wall; ctx.fillRect(b.x,top,b.w,b.h+25);
  ctx.fillStyle='#25384d'; ctx.fillRect(b.x-3,top,b.w+6,4);
  ctx.fillStyle='rgba(95,132,164,.22)'; ctx.fillRect(b.x+7,top+7,2,b.h-10);
  // Recessed windows with warm interiors and subtle frames
  for (let row=0; row<Math.floor(b.h/18); row++) for (let col=0; col<Math.floor(b.w/15); col++) {
    const wx=b.x+8+col*15, wy=top+12+row*18;
    ctx.fillStyle='#07111c'; ctx.fillRect(wx,wy,8,10);
    if (rand()>.32) {
      ctx.fillStyle=rand()>.28 ? 'rgba(255,194,116,.78)' : 'rgba(107,177,223,.72)';
      ctx.fillRect(wx+1,wy+1,6,7);
      ctx.fillStyle='rgba(255,245,220,.27)'; ctx.fillRect(wx+1,wy+1,1,7);
    }
  }
  // Fine vertical facade seams
  ctx.strokeStyle='rgba(129,167,196,.18)'; ctx.lineWidth=1;
  for(let k=1;k<4;k++){ctx.beginPath();ctx.moveTo(b.x+b.w*k/4,top+4);ctx.lineTo(b.x+b.w*k/4,horizon);ctx.stroke();}
}

// Roofline antennas, cables and small lit signs
ctx.strokeStyle='rgba(119,160,194,.62)'; ctx.lineWidth=2;
for (const x of [W*.12,W*.31,W*.51,W*.74,W*.91]) {
  const y=horizon-H*(.40+rand()*.2);
  ctx.beginPath(); ctx.moveTo(x,y); ctx.lineTo(x,y-28-rand()*26); ctx.stroke();
  ctx.fillStyle='#ffb577'; ctx.beginPath(); ctx.arc(x,y-30,2.2,0,Math.PI*2); ctx.fill();
}
ctx.strokeStyle='rgba(87,127,163,.45)'; ctx.lineWidth=1.5;
ctx.beginPath(); ctx.moveTo(0,H*.40); ctx.bezierCurveTo(W*.3,H*.35,W*.58,H*.46,W,H*.37); ctx.stroke();

// Rain-soaked foreground street and perspective reflections
const road = ctx.createLinearGradient(0,horizon,0,H);
road.addColorStop(0,'#152137'); road.addColorStop(.25,'#111b2d'); road.addColorStop(1,'#050a12');
ctx.fillStyle=road; ctx.fillRect(0,horizon,W,H-horizon);
ctx.save(); ctx.beginPath(); ctx.rect(0,horizon,W,H-horizon); ctx.clip();
for(let i=0;i<90;i++){
  const x=(rand()*W + time*26)%W, y=horizon+((rand()*(H-horizon) + time*145)%(H-horizon)), len=7+rand()*85;
  ctx.globalAlpha=.035+rand()*.10; ctx.strokeStyle=rand()>.55?'#f3a66d':'#78b7ea'; ctx.lineWidth=.5+rand()*2;
  ctx.beginPath(); ctx.moveTo(x,y); ctx.lineTo(x+(rand()-.5)*12,y+len); ctx.stroke();
}
// Broken elongated reflections
for(let i=0;i<24;i++){
  const x=rand()*W, y=horizon+rand()*(H-horizon), width=3+rand()*15, height=20+rand()*130;
  const reflection=ctx.createLinearGradient(x,y,x,y+height);
  reflection.addColorStop(0,rand()>.5?'rgba(255,177,114,.32)':'rgba(107,180,235,.28)');
  reflection.addColorStop(1,'rgba(50,90,130,0)');
  ctx.fillStyle=reflection; ctx.fillRect(x-width/2,y,width,height);
}
ctx.restore(); ctx.globalAlpha=1;

// Atmospheric foreground silhouettes and fine rain lines
ctx.fillStyle='#070d17';
ctx.beginPath(); ctx.moveTo(0,H*.86); ctx.quadraticCurveTo(W*.12,H*.81,W*.24,H*.87); ctx.lineTo(W*.32,H); ctx.lineTo(0,H); ctx.closePath(); ctx.fill();
ctx.strokeStyle='rgba(183,207,229,.18)'; ctx.lineWidth=1;
for(let i=0;i<120;i++){const x=rand()*W,y=rand()*H;ctx.beginPath();ctx.moveTo(x,y);ctx.lineTo(x-3,y+10+rand()*18);ctx.stroke();}
// Film-like fine grain
for(let i=0;i<2300;i++){const x=rand()*W,y=rand()*H;ctx.globalAlpha=rand()*.055;ctx.fillStyle=rand()>.5?'#fff':'#02050a';ctx.fillRect(x,y,1.1,1.1);}
ctx.globalAlpha=1;
`;
  }

  function setActivePanel(panelId) {
    document.querySelectorAll('.panel-tab').forEach((tab) => tab.classList.toggle('active', tab.dataset.panel === panelId));
    document.querySelectorAll('.panel-content').forEach((panel) => panel.classList.toggle('active', panel.id === panelId));
  }

  function addFrames(count = 1) {
    saveCurrentFrame();
    const newFrames = Array.from({ length: count }, () => makeFrame());
    state.frames.splice(state.current + 1, 0, ...newFrames);
    activateFrame(state.current + 1, { save: false });
    showToast(count === 1 ? 'Blank frame added.' : `${count} blank frames added.`);
  }

  function addFrame() { addFrames(1); }

  function duplicateFrame() {
    saveCurrentFrame();
    const source = currentFrame();
    const duplicate = makeFrame({ paintData: source.paintData, scriptData: source.scriptData, script: source.script });
    state.frames.splice(state.current + 1, 0, duplicate);
    activateFrame(state.current + 1, { save: false });
    showToast('Frame duplicated. Make small changes to create motion.');
  }

  function deleteFrame() {
    if (state.frames.length <= 1) {
      showToast('A project must keep at least one frame.');
      return;
    }
    state.frames.splice(state.current, 1);
    state.current = Math.min(state.current, state.frames.length - 1);
    activateFrame(state.current, { save: false });
    showToast('Frame deleted.');
  }

  async function importImageFile(file) {
    if (!file || !file.type.startsWith('image/')) return;
    const url = URL.createObjectURL(file);
    try {
      const image = await waitImage(url);
      pushHistory();
      const scale = Math.min(state.width / image.width, state.height / image.height);
      const w = image.width * scale;
      const h = image.height * scale;
      paintCtx.drawImage(image, (state.width - w) / 2, (state.height - h) / 2, w, h);
      saveCurrentFrame();
      renderOutput();
      renderFrameStrip();
      scheduleAutosave();
      showToast('Image imported into the current drawing layer.');
    } catch (error) {
      showToast('Could not open that image file.');
    } finally {
      URL.revokeObjectURL(url);
    }
  }

  function exportProject() {
    const project = serializableProject();
    const blob = new Blob([JSON.stringify(project)], { type: 'application/json' });
    downloadBlob(blob, `${safeFilename(project.name)}.frameforge.json`);
    showToast('Project file exported. Keep it as your editable backup.');
    scheduleAutosave();
  }

  function safeFilename(name) {
    return (name || 'frameforge-project').replace(/[^a-z0-9-_]+/gi, '-').replace(/^-+|-+$/g, '').toLowerCase() || 'frameforge-project';
  }

  function downloadBlob(blob, filename) {
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = filename;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    setTimeout(() => URL.revokeObjectURL(url), 5000);
  }

  function loadProjectObject(project, showMessage = true) {
    if (!project || project.format !== 'frameforge-project' || !Array.isArray(project.frames) || !project.frames.length) {
      throw new Error('This is not a valid FrameForge project file.');
    }
    const width = Number(project.width);
    const height = Number(project.height);
    if (!Number.isInteger(width) || !Number.isInteger(height) || width < 64 || height < 64 || width > 4096 || height > 4096) {
      throw new Error('The project canvas dimensions are invalid.');
    }
    state.frames = project.frames.map((frame) => makeFrame(frame));
    state.current = 0;
    state.fps = clamp(Number(project.fps) || 30, 1, 60);
    $('projectName').value = String(project.name || 'Imported Film').slice(0, 48);
    setCanvasSize(width, height);
    $('fpsInput').value = String(state.fps);
    const match = Object.entries(PRESETS).find(([, size]) => size.width === width && size.height === height);
    $('canvasPreset').value = match ? match[0] : 'portrait';
    activateFrame(0, { save: false, autosave: false });
    if (showMessage) showToast('Project opened.');
    scheduleAutosave();
  }

  async function openProjectFile(file) {
    if (!file) return;
    try {
      const text = await file.text();
      loadProjectObject(JSON.parse(text));
    } catch (error) {
      showToast(`Could not open project: ${error.message}`, 4500);
    }
  }

  function newProject() {
    const hasWork = state.frames.some((frame) => frame.paintData || frame.scriptData || frame.script);
    if (hasWork && !confirm('Start a new project? Save your current project first if you need it.')) return;
    stopPlayback();
    state.frames = [makeFrame()];
    state.current = 0;
    $('projectName').value = 'Untitled Film';
    $('frameScript').value = '';
    paintCtx.clearRect(0, 0, state.width, state.height);
    scriptCtx.clearRect(0, 0, state.width, state.height);
    onionCtx.clearRect(0, 0, state.width, state.height);
    renderOutput();
    updateTimelineUi();
    updateUndoButtons();
    scheduleAutosave();
    showToast('New blank project created.');
  }

  function startPlayback() {
    if (state.playing || !state.frames.length) return;
    state.playing = true;
    state.playbackLast = 0;
    state.playbackAccumulator = 0;
    onionCtx.clearRect(0, 0, state.width, state.height);
    $('playBtn').textContent = 'Ⅱ';
    $('playBtn').title = 'Pause';
    const tick = (timestamp) => {
      if (!state.playing) return;
      if (!state.playbackLast) state.playbackLast = timestamp;
      const elapsed = Math.min(100, timestamp - state.playbackLast);
      state.playbackLast = timestamp;
      state.playbackAccumulator += elapsed;
      const frameMs = 1000 / state.fps;
      let changed = false;
      while (state.playbackAccumulator >= frameMs) {
        state.playbackAccumulator -= frameMs;
        if (state.current >= state.frames.length - 1) {
          if (state.loop && !state.recording) {
            state.current = 0;
            changed = true;
          } else {
            stopPlayback();
            if (state.recording && state.recorder?.state === 'recording') state.recorder.stop();
            return;
          }
        } else {
          state.current += 1;
          changed = true;
        }
      }
      if (changed) {
        const frame = state.frames[state.current];
        drawDataOnCanvas(paintCtx, frame.paintData);
        drawDataOnCanvas(scriptCtx, frame.scriptData);
        renderOutput();
        updateTimelineUi();
      }
      state.playbackRaf = requestAnimationFrame(tick);
    };
    state.playbackRaf = requestAnimationFrame(tick);
    updateTimelineUi();
  }

  function stopPlayback() {
    state.playing = false;
    cancelAnimationFrame(state.playbackRaf);
    $('playBtn').textContent = '▶';
    $('playBtn').title = 'Play';
    const frame = currentFrame();
    if (frame) {
      drawDataOnCanvas(paintCtx, frame.paintData);
      drawDataOnCanvas(scriptCtx, frame.scriptData);
    }
    renderOnion();
    renderOutput();
    updateTimelineUi();
  }

  function togglePlayback() {
    if (state.playing) stopPlayback(); else startPlayback();
  }

  function showExportModal() {
    $('exportFpsLabel').textContent = `${state.fps} FPS`;
    $('exportSizeLabel').textContent = `${state.width} × ${state.height}`;
    $('exportModal').classList.remove('hidden');
  }

  function closeExportModal() { $('exportModal').classList.add('hidden'); }

  async function beginVideoExport() {
    if (!('MediaRecorder' in window) || !outputCanvas.captureStream) {
      showToast('This browser cannot record canvas video. Save the project JSON and use a desktop browser for WebM export.', 5000);
      return;
    }
    saveCurrentFrame();
    renderOutput();
    let mimeType = '';
    const candidates = ['video/webm;codecs=vp9', 'video/webm;codecs=vp8', 'video/webm'];
    for (const candidate of candidates) {
      if (MediaRecorder.isTypeSupported(candidate)) { mimeType = candidate; break; }
    }
    if (!mimeType) {
      showToast('This browser does not report a supported WebM encoder.', 4500);
      return;
    }
    $('exportTitle').textContent = 'Recording your film…';
    $('startExportBtn').disabled = true;
    $('startExportBtn').textContent = 'Recording…';
    $('cancelExportBtn').textContent = 'Stop export';
    $('exportProgress').classList.remove('hidden');
    $('exportProgressFill').style.width = '0%';
    state.recorderChunks = [];
    state.recording = true;
    state.previousLoopSetting = state.loop;
    state.loop = false;
    $('loopPlayback').checked = false;
    state.current = 0;
    await activateFrame(0, { save: false });
    const stream = outputCanvas.captureStream(state.fps);
    const recorder = new MediaRecorder(stream, { mimeType, videoBitsPerSecond: Math.min(12_000_000, Math.max(2_000_000, state.width * state.height * state.fps * 0.035)) });
    state.recorder = recorder;
    recorder.ondataavailable = (event) => { if (event.data && event.data.size) state.recorderChunks.push(event.data); };
    recorder.onerror = (event) => {
      console.error('Recording error:', event);
      state.recording = false;
      stream.getTracks().forEach((track) => track.stop());
      showToast('Video export failed in this browser.', 4000);
    };
    recorder.onstop = () => {
      state.recording = false;
      stream.getTracks().forEach((track) => track.stop());
      state.loop = state.previousLoopSetting;
      $('loopPlayback').checked = state.loop;
      $('exportTitle').textContent = 'Export your film';
      $('startExportBtn').disabled = false;
      $('startExportBtn').textContent = 'Start export';
      $('cancelExportBtn').textContent = 'Cancel';
      closeExportModal();
      const blob = new Blob(state.recorderChunks, { type: mimeType });
      if (blob.size) {
        downloadBlob(blob, `${safeFilename($('projectName').value)}.webm`);
        showToast(`Video exported: ${(blob.size / (1024 * 1024)).toFixed(1)} MB`);
      } else {
        showToast('The browser returned an empty video file. Try a shorter animation.');
      }
      $('exportProgress').classList.add('hidden');
      $('exportProgressFill').style.width = '0%';
      state.recorder = null;
    };
    recorder.start(250);
    startPlayback();
    const durationMs = state.frames.length / state.fps * 1000;
    const startedAt = performance.now();
    const progress = () => {
      if (!state.recording) return;
      const percent = Math.min(99, ((performance.now() - startedAt) / durationMs) * 100);
      $('exportProgressFill').style.width = `${percent}%`;
      if (state.recording) requestAnimationFrame(progress);
    };
    requestAnimationFrame(progress);
    // A defensive stop in case the browser misses the final playback tick.
    setTimeout(() => {
      if (state.recording && state.recorder?.state === 'recording') {
        stopPlayback();
        state.recorder.stop();
      }
    }, durationMs + 1200);
    showToast('Recording timeline at real-time playback speed. Keep this tab open.', 4000);
  }

  function applyCanvasPreset() {
    const preset = PRESETS[$('canvasPreset').value] || PRESETS.portrait;
    if (preset.width === state.width && preset.height === state.height) return;
    const hasWork = state.frames.some((frame) => frame.paintData || frame.scriptData || frame.script);
    if (hasWork && !confirm('Changing canvas size clears the artwork in this project. Save a project copy first. Continue?')) return;
    stopPlayback();
    setCanvasSize(preset.width, preset.height);
    state.frames = [makeFrame()];
    state.current = 0;
    $('frameScript').value = '';
    paintCtx.clearRect(0, 0, state.width, state.height);
    scriptCtx.clearRect(0, 0, state.width, state.height);
    onionCtx.clearRect(0, 0, state.width, state.height);
    renderOutput();
    updateTimelineUi();
    scheduleAutosave();
    showToast(`Canvas set to ${preset.width} × ${preset.height}.`);
  }

  function setFps(value) {
    state.fps = clamp(Math.round(Number(value) || 30), 1, 60);
    $('fpsInput').value = String(state.fps);
    updateTimelineUi();
    scheduleAutosave();
  }

  function bindEvents() {
    document.querySelectorAll('.tool[data-tool]').forEach((button) => button.addEventListener('click', () => setTool(button.dataset.tool)));
    $('brushColor').addEventListener('input', (event) => { state.color = event.target.value; });
    $('brushSize').addEventListener('input', (event) => {
      state.brushSize = Number(event.target.value);
      $('brushSizeValue').textContent = `${state.brushSize} px`;
    });
    $('brushOpacity').addEventListener('input', (event) => {
      state.opacity = Number(event.target.value) / 100;
      $('brushOpacityValue').textContent = `${event.target.value}%`;
    });
    paintCanvas.addEventListener('pointerdown', beginStroke);
    paintCanvas.addEventListener('pointermove', moveStroke);
    paintCanvas.addEventListener('pointerup', endStroke);
    paintCanvas.addEventListener('pointercancel', endStroke);
    paintCanvas.addEventListener('lostpointercapture', endStroke);
    $('undoBtn').addEventListener('click', undo);
    $('redoBtn').addEventListener('click', redo);
    $('runScriptBtn').addEventListener('click', runFrameScript);
    $('runAllScriptsBtn').addEventListener('click', runScriptOnAllFrames);
    $('clearScriptBtn').addEventListener('click', clearScriptLayer);
    $('bakeScriptBtn').addEventListener('click', bakeScriptLayer);
    $('frameScript').addEventListener('input', () => {
      currentFrame().script = $('frameScript').value;
      renderFrameStrip();
      scheduleAutosave();
    });
    $('loadStarterBtn').addEventListener('click', () => {
      $('frameScript').value = starterCityScript();
      currentFrame().script = $('frameScript').value;
      scheduleAutosave();
      showToast('Detailed city scene code loaded. Press Run on frame.');
    });
    $('onionBtn').addEventListener('click', () => {
      state.onion = !state.onion;
      $('onionBtn').setAttribute('aria-pressed', String(state.onion));
      $('onionBtn').classList.toggle('toggle', state.onion);
      renderOnion();
    });
    $('fitBtn').addEventListener('click', () => { state.zoom = 'fit'; renderStageSize(); });
    $('actualBtn').addEventListener('click', () => { state.zoom = '100%'; renderStageSize(); });
    $('zoomOutBtn').addEventListener('click', () => { state.zoom = 'fit'; renderStageSize(); });
    $('zoomInBtn').addEventListener('click', () => { state.zoom = '100%'; renderStageSize(); });
    $('addFrameBtn').addEventListener('click', addFrame);
    $('addTenFramesBtn').addEventListener('click', () => addFrames(10));
    $('duplicateFrameBtn').addEventListener('click', duplicateFrame);
    $('deleteFrameBtn').addEventListener('click', deleteFrame);
    $('firstFrameBtn').addEventListener('click', () => { stopPlayback(); activateFrame(0); });
    $('prevFrameBtn').addEventListener('click', () => { stopPlayback(); activateFrame(state.current - 1); });
    $('nextFrameBtn').addEventListener('click', () => { stopPlayback(); activateFrame(state.current + 1); });
    $('lastFrameBtn').addEventListener('click', () => { stopPlayback(); activateFrame(state.frames.length - 1); });
    $('playBtn').addEventListener('click', togglePlayback);
    $('timelineScrubber').addEventListener('input', (event) => { stopPlayback(); activateFrame(Number(event.target.value)); });
    $('loopPlayback').addEventListener('change', (event) => { state.loop = event.target.checked; });
    $('fpsInput').addEventListener('change', (event) => setFps(event.target.value));
    $('applyCanvasBtn').addEventListener('click', applyCanvasPreset);
    $('projectName').addEventListener('input', scheduleAutosave);
    $('newProjectBtn').addEventListener('click', newProject);
    $('saveProjectBtn').addEventListener('click', exportProject);
    $('openProjectBtn').addEventListener('click', () => $('projectFileInput').click());
    $('projectFileInput').addEventListener('change', (event) => openProjectFile(event.target.files[0]));
    $('importImageBtn').addEventListener('click', () => $('imageFileInput').click());
    $('imageFileInput').addEventListener('change', (event) => {
      const file = event.target.files[0];
      importImageFile(file);
      event.target.value = '';
    });
    document.querySelectorAll('.panel-tab').forEach((tab) => tab.addEventListener('click', () => setActivePanel(tab.dataset.panel)));
    $('exportVideoBtn').addEventListener('click', showExportModal);
    $('closeExportModal').addEventListener('click', closeExportModal);
    $('cancelExportBtn').addEventListener('click', () => {
      if (state.recording && state.recorder?.state === 'recording') {
        stopPlayback();
        state.recorder.stop();
      } else closeExportModal();
    });
    $('startExportBtn').addEventListener('click', beginVideoExport);
    $('exportModal').addEventListener('click', (event) => { if (event.target === $('exportModal')) closeExportModal(); });

    document.addEventListener('keydown', (event) => {
      const target = event.target;
      const typing = target && (target.tagName === 'TEXTAREA' || target.tagName === 'INPUT' || target.tagName === 'SELECT' || target.isContentEditable);
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'z' && !typing) { event.preventDefault(); undo(); }
      else if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'y' && !typing) { event.preventDefault(); redo(); }
      else if (!typing && event.code === 'Space') { event.preventDefault(); togglePlayback(); }
      else if (!typing && event.key.toLowerCase() === 'b') setTool('brush');
      else if (!typing && event.key.toLowerCase() === 'e') setTool('eraser');
      else if (!typing && event.key === 'ArrowRight') { stopPlayback(); activateFrame(state.current + 1); }
      else if (!typing && event.key === 'ArrowLeft') { stopPlayback(); activateFrame(state.current - 1); }
    });
  }

  async function init() {
    setCanvasSize(state.width, state.height);
    bindEvents();
    const restored = await restoreAutosave();
    if (!restored) {
      await activateFrame(0, { save: false, autosave: false });
      setSaveStatus('Local project');
    }
    renderOutput();
    updateTimelineUi();
    updateUndoButtons();
    renderStageSize();
  }

  init().catch((error) => {
    console.error('FrameForge failed to initialize:', error);
    showToast('The editor could not initialize. Refresh the page to try again.', 5000);
  });
})();
