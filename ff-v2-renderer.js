/* FrameForge V2 renderer — deterministic Canvas 2D layer compositor.
 * Uses browser-native Canvas APIs only; no remote services or paid dependencies.
 */
(function (root) {
  'use strict';
  const Core = root.FFV2Core;
  const BLENDS = new Set(['source-over','multiply','screen','overlay','darken','lighten','color-dodge','color-burn','hard-light','soft-light','difference','exclusion','hue','saturation','color','luminosity','lighter','destination-over']);
  const svgCache = new Map();

  function makeCanvas(width, height, reference) {
    if (typeof OffscreenCanvas !== 'undefined') return new OffscreenCanvas(width, height);
    const canvas = (reference && reference.ownerDocument ? reference.ownerDocument : document).createElement('canvas');
    canvas.width = width; canvas.height = height;
    return canvas;
  }

  function sourceSize(source) {
    return {
      width: Number(source && (source.naturalWidth || source.videoWidth || source.width)) || 0,
      height: Number(source && (source.naturalHeight || source.videoHeight || source.height)) || 0
    };
  }

  function allClips(project) {
    return Core.getMainSequence(project).tracks.flatMap(track => track.clips || []);
  }

  function resolveGlobalTransform(clip, frame, byId, visited) {
    const own = Core.evaluateClipTransform(clip, frame);
    if (!clip.parent_clip_id) return own;
    visited = visited || new Set();
    if (visited.has(clip.id)) throw new Error('Parenting cycle detected while rendering.');
    visited.add(clip.id);
    const parentClip = byId.get(clip.parent_clip_id);
    if (!parentClip) return own;
    const parent = resolveGlobalTransform(parentClip, frame, byId, visited);
    const radians = parent.rotation_degrees * Math.PI / 180;
    const localX = own.position[0] * parent.scale[0];
    const localY = own.position[1] * parent.scale[1];
    const rotatedX = localX * Math.cos(radians) - localY * Math.sin(radians);
    const rotatedY = localX * Math.sin(radians) + localY * Math.cos(radians);
    return {
      position: [parent.position[0] + rotatedX, parent.position[1] + rotatedY],
      scale: [own.scale[0] * parent.scale[0], own.scale[1] * parent.scale[1]],
      rotation_degrees: own.rotation_degrees + parent.rotation_degrees,
      opacity: own.opacity * parent.opacity,
      anchor: own.anchor,
      fit: own.fit,
      crop: own.crop
    };
  }

  function loadSvg(svgText) {
    if (svgCache.has(svgText)) return svgCache.get(svgText);
    const promise = new Promise((resolve, reject) => {
      try {
        Core.validateSvgText(svgText);
        const blob = new Blob([svgText], { type: 'image/svg+xml' });
        const url = URL.createObjectURL(blob);
        const image = new Image();
        image.onload = () => { URL.revokeObjectURL(url); resolve(image); };
        image.onerror = () => { URL.revokeObjectURL(url); reject(new Error('Could not decode generated SVG graphic.')); };
        image.src = url;
      } catch (error) { reject(error); }
    });
    svgCache.set(svgText, promise);
    return promise;
  }

  function drawText(ctx, params, width, height) {
    const fontSize = Math.max(1, Number(params.font_size) || 64);
    const family = String(params.font_family || 'Arial, sans-serif');
    const weight = String(params.font_weight || 700);
    const style = String(params.font_style || 'normal');
    const align = ['left','center','right'].includes(params.align) ? params.align : 'center';
    const text = String(params.text || '');
    const lines = text.split(/\r?\n/);
    const lineHeight = Math.max(fontSize, Number(params.line_height) || fontSize * 1.16);
    const maxWidth = Math.max(1, width - 40);
    ctx.textAlign = align;
    ctx.textBaseline = 'middle';
    ctx.font = style + ' ' + weight + ' ' + fontSize + 'px ' + family;
    const x = align === 'left' ? 0 : align === 'right' ? width : width / 2;
    const startY = height / 2 - ((lines.length - 1) * lineHeight) / 2;
    if (params.background) {
      ctx.fillStyle = params.background;
      const radius = Math.max(0, Number(params.background_radius) || 0);
      roundedRect(ctx, 0, 0, width, height, radius);
      ctx.fill();
    }
    ctx.fillStyle = String(params.color || '#ffffff');
    ctx.strokeStyle = String(params.outline_color || '#000000');
    ctx.lineWidth = Math.max(0, Number(params.outline_width) || 0);
    ctx.lineJoin = 'round';
    if (params.shadow_color) {
      ctx.shadowColor = String(params.shadow_color);
      ctx.shadowBlur = Math.max(0, Number(params.shadow_blur) || 0);
      ctx.shadowOffsetX = Number(params.shadow_x) || 0;
      ctx.shadowOffsetY = Number(params.shadow_y) || 0;
    }
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      if (ctx.measureText(line).width > maxWidth && maxWidth > 0) {
        // Canvas handles clipping deterministically; callers can add explicit line breaks for precise wrapping.
      }
      if (ctx.lineWidth > 0) ctx.strokeText(line, x, startY + i * lineHeight, maxWidth);
      ctx.fillText(line, x, startY + i * lineHeight, maxWidth);
    }
    ctx.shadowColor = 'transparent';
  }

  function roundedRect(ctx, x, y, width, height, radius) {
    const r = Math.min(radius, width / 2, height / 2);
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.arcTo(x + width, y, x + width, y + height, r);
    ctx.arcTo(x + width, y + height, x, y + height, r);
    ctx.arcTo(x, y + height, x, y, r);
    ctx.arcTo(x, y, x + width, y, r);
    ctx.closePath();
  }

  function drawShape(ctx, params, width, height) {
    const shape = String(params.shape || 'rect');
    ctx.fillStyle = String(params.fill || '#287fbd');
    ctx.strokeStyle = String(params.stroke || '#ffffff');
    ctx.lineWidth = Math.max(0, Number(params.stroke_width) || 0);
    ctx.beginPath();
    if (shape === 'ellipse') ctx.ellipse(width / 2, height / 2, width / 2, height / 2, 0, 0, Math.PI * 2);
    else if (shape === 'line') {
      ctx.moveTo(0, height / 2); ctx.lineTo(width, height / 2);
    } else if (shape === 'polygon' && Array.isArray(params.points) && params.points.length >= 3) {
      params.points.forEach((point, index) => {
        const x = Number(point[0]) * width, y = Number(point[1]) * height;
        if (index === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
      });
      ctx.closePath();
    } else roundedRect(ctx, 0, 0, width, height, Math.max(0, Number(params.radius) || 0));
    if (shape !== 'line') ctx.fill();
    if (ctx.lineWidth > 0) ctx.stroke();
  }

  function fitAsset(source, sequence, transform, params) {
    const size = sourceSize(source);
    if (!size.width || !size.height) throw new Error('Visual asset has no readable dimensions.');
    const crop = transform.crop || { x: 0, y: 0, width: 1, height: 1 };
    const sx = Math.max(0, Math.min(size.width - 1, crop.x * size.width));
    const sy = Math.max(0, Math.min(size.height - 1, crop.y * size.height));
    const sw = Math.max(1, Math.min(size.width - sx, crop.width * size.width));
    const sh = Math.max(1, Math.min(size.height - sy, crop.height * size.height));
    let width = sw, height = sh;
    if (transform.fit === 'stretch') { width = sequence.width; height = sequence.height; }
    else if (transform.fit === 'cover') {
      const factor = Math.max(sequence.width / sw, sequence.height / sh);
      width = sw * factor; height = sh * factor;
    } else {
      const factor = Math.min(sequence.width / sw, sequence.height / sh);
      width = sw * factor; height = sh * factor;
    }
    return { sx, sy, sw, sh, width, height };
  }

  async function drawClipContent(ctx, clip, source, sequence, transform, frame) {
    const generator = clip.generator || {};
    const params = generator.parameters || {};
    let width, height, draw;
    if (clip.kind === 'generated' && generator.type === 'text') {
      width = Math.max(40, Number(params.box_width) || Math.min(900, sequence.width * 0.78));
      height = Math.max(40, Number(params.box_height) || 180);
      draw = () => drawText(ctx, params, width, height);
    } else if (clip.kind === 'generated' && generator.type === 'shape') {
      width = Math.max(1, Number(params.width) || 300);
      height = Math.max(1, Number(params.height) || 180);
      draw = () => drawShape(ctx, params, width, height);
    } else if (clip.kind === 'generated' && generator.type === 'svg') {
      source = await loadSvg(String(params.svg || '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1"/>'));
      const size = sourceSize(source);
      width = size.width; height = size.height;
      draw = () => ctx.drawImage(source, 0, 0, width, height);
    } else {
      if (!source) return false;
      const fit = fitAsset(source, sequence, transform, params);
      width = fit.width; height = fit.height;
      draw = () => ctx.drawImage(source, fit.sx, fit.sy, fit.sw, fit.sh, 0, 0, width, height);
    }
    ctx.save();
    ctx.translate(sequence.width / 2 + transform.position[0], sequence.height / 2 + transform.position[1]);
    ctx.rotate(transform.rotation_degrees * Math.PI / 180);
    ctx.scale(transform.scale[0], transform.scale[1]);
    ctx.translate(-transform.anchor[0] * width, -transform.anchor[1] * height);
    draw();
    ctx.restore();
    return true;
  }

  async function applyMask(layerCanvas, mask, sequence, resolveAsset, clip, frame) {
    if (!mask || mask.type === 'none') return;
    const maskCanvas = makeCanvas(sequence.width, sequence.height, layerCanvas);
    const maskCtx = maskCanvas.getContext('2d', { willReadFrequently: mask.type === 'luma' });
    if (!maskCtx) throw new Error('Canvas 2D mask context is unavailable.');
    if (mask.type === 'shape') {
      const b = mask.bounds || { x: 0, y: 0, width: 1, height: 1 };
      const x = b.x * sequence.width, y = b.y * sequence.height;
      const w = b.width * sequence.width, h = b.height * sequence.height;
      if (mask.invert) { maskCtx.fillStyle = '#fff'; maskCtx.fillRect(0, 0, sequence.width, sequence.height); }
      maskCtx.save();
      maskCtx.filter = mask.feather > 0 ? 'blur(' + mask.feather + 'px)' : 'none';
      maskCtx.fillStyle = mask.invert ? '#000' : '#fff';
      maskCtx.beginPath();
      if (mask.shape === 'ellipse') maskCtx.ellipse(x + w / 2, y + h / 2, w / 2, h / 2, 0, 0, Math.PI * 2);
      else maskCtx.rect(x, y, w, h);
      maskCtx.fill();
      maskCtx.restore();
    } else {
      const matteAsset = (clip._projectAssets || []).find(item => item.id === mask.asset_id);
      if (!matteAsset) throw new Error('Matte asset is missing from the project.');
      const matteSource = await resolveAsset(matteAsset, clip, 0);
      if (!matteSource) throw new Error('Matte asset could not be decoded.');
      maskCtx.drawImage(matteSource, 0, 0, sequence.width, sequence.height);
      if (mask.type === 'luma') {
        try {
          const pixels = maskCtx.getImageData(0, 0, sequence.width, sequence.height);
          for (let i = 0; i < pixels.data.length; i += 4) {
            const luminance = (0.2126 * pixels.data[i] + 0.7152 * pixels.data[i + 1] + 0.0722 * pixels.data[i + 2]) / 255;
            const alpha = luminance * (pixels.data[i + 3] / 255);
            pixels.data[i + 3] = Math.round((mask.invert ? 1 - alpha : alpha) * 255);
          }
          maskCtx.putImageData(pixels, 0, 0);
        } catch (_) {
          throw new Error('Luma matte pixel access is unavailable in this browser; use an alpha matte or shape mask.');
        }
      } else if (mask.invert) {
        const pixels = maskCtx.getImageData(0, 0, sequence.width, sequence.height);
        for (let i = 3; i < pixels.data.length; i += 4) pixels.data[i] = 255 - pixels.data[i];
        maskCtx.putImageData(pixels, 0, 0);
      }
      if (mask.feather > 0) {
        const softened = makeCanvas(sequence.width, sequence.height, layerCanvas);
        const softCtx = softened.getContext('2d');
        softCtx.filter = 'blur(' + mask.feather + 'px)';
        softCtx.drawImage(maskCanvas, 0, 0);
        maskCtx.clearRect(0, 0, sequence.width, sequence.height);
        maskCtx.filter = 'none';
        maskCtx.drawImage(softened, 0, 0);
      }
    }
    const layerCtx = layerCanvas.getContext('2d');
    layerCtx.save();
    layerCtx.globalCompositeOperation = 'destination-in';
    layerCtx.drawImage(maskCanvas, 0, 0);
    layerCtx.restore();
  }

  async function composeFrame(options) {
    const project = options.project;
    const sequence = Core.getMainSequence(project);
    const frame = Math.max(0, Math.round(Number(options.frame) || 0));
    const canvas = options.canvas;
    const resolveAsset = options.resolveAsset;
    if (!canvas || typeof canvas.getContext !== 'function') throw new Error('A target canvas is required.');
    if (typeof resolveAsset !== 'function') throw new Error('An asset resolver function is required.');
    if (canvas.width !== sequence.width) canvas.width = sequence.width;
    if (canvas.height !== sequence.height) canvas.height = sequence.height;
    const output = canvas.getContext('2d', { alpha: true });
    if (!output) throw new Error('Canvas 2D output context is unavailable.');
    output.clearRect(0, 0, sequence.width, sequence.height);
    if (options.background) {
      output.fillStyle = options.background;
      output.fillRect(0, 0, sequence.width, sequence.height);
    }
    const all = allClips(project);
    const byId = new Map(all.map(clip => [clip.id, clip]));
    const projectAssets = project.assets || [];
    let drawn = 0;
    const warnings = [];
    for (const item of Core.getActiveVisualClips(project, frame)) {
      const clip = item.clip;
      try {
        const transform = resolveGlobalTransform(clip, frame, byId);
        const localFrame = Math.max(0, frame - clip.start_frame);
        const mediaTime = ((Number(clip.source_in_frame) || 0) + localFrame * (Number(clip.playback_rate) || 1)) / sequence.fps;
        const asset = clip.asset_id ? projectAssets.find(ref => ref.id === clip.asset_id) : null;
        clip._projectAssets = projectAssets;
        const source = asset ? await resolveAsset(asset, clip, mediaTime) : null;
        const layer = makeCanvas(sequence.width, sequence.height, canvas);
        const layerCtx = layer.getContext('2d');
        if (!layerCtx) throw new Error('Canvas 2D layer context is unavailable.');
        await drawClipContent(layerCtx, clip, source, sequence, transform, frame);
        await applyMask(layer, clip.mask, sequence, resolveAsset, clip, frame);
        output.save();
        const requestedBlend = clip.blend_mode === 'normal' || !clip.blend_mode ? 'source-over' : clip.blend_mode;
        output.globalCompositeOperation = BLENDS.has(requestedBlend) ? requestedBlend : 'source-over';
        output.globalAlpha = transform.opacity;
        output.drawImage(layer, 0, 0);
        output.restore();
        delete clip._projectAssets;
        drawn++;
      } catch (error) {
        delete clip._projectAssets;
        warnings.push({ clip_id: clip.id, message: error.message });
      }
    }
    return { frame, drawn, warnings, width: sequence.width, height: sequence.height };
  }

  const api = { composeFrame, resolveGlobalTransform, drawText, drawShape, fitAsset };
  root.FFV2Renderer = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
