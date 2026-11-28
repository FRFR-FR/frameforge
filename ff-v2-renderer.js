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
    } else if (clip.kind === 'generated' && generator.type === 'particles') {
      width = sequence.width; height = sequence.height;
      const localFrame = Math.max(0, frame - clip.start_frame);
      draw = () => drawParticles(ctx, params, width, height, localFrame, sequence.fps);
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

  async function applyMask(layerCanvas, mask, sequence, resolveAsset, clip, frame, projectAssets) {
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
      maskCtx.globalCompositeOperation = mask.invert ? 'destination-out' : 'source-over';
      maskCtx.fillStyle = '#fff';
      maskCtx.beginPath();
      if (mask.shape === 'ellipse') maskCtx.ellipse(x + w / 2, y + h / 2, w / 2, h / 2, 0, 0, Math.PI * 2);
      else maskCtx.rect(x, y, w, h);
      maskCtx.fill();
      maskCtx.restore();
    } else {
      const matteAsset = (projectAssets || []).find(item => item.id === mask.asset_id);
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


  function seededRandom(seed) {
    let value = (Number(seed) >>> 0) || 1;
    return function () {
      value += 0x6D2B79F5;
      let t = value;
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14) >>> 0) >>> 0) / 4294967296;
    };
  }

  function drawParticles(ctx, params, width, height, localFrame, fps) {
    const preset = ['sparks','dust','embers','magic','confetti'].includes(params.preset) ? params.preset : 'sparks';
    const count = Math.max(1, Math.min(500, Math.round(Number(params.count) || 72)));
    const rng = seededRandom(Number(params.seed) || 1337);
    const speed = Math.max(0, Math.min(8, Number(params.speed) || 1));
    const spread = Math.max(0.05, Math.min(3, Number(params.spread) || 1));
    const gravity = Number(params.gravity ?? 72);
    const size = Math.max(0.5, Math.min(40, Number(params.size) || 3));
    const lifeFrames = Math.max(1, (Number(params.life_seconds) || 1.8) * fps);
    const originX = (Number(params.origin_x ?? 0.5)) * width;
    const originY = (Number(params.origin_y ?? 0.55)) * height;
    const color = String(params.color || '#ffc46b');
    const time = Math.max(0, localFrame);
    ctx.save();
    ctx.fillStyle = color;
    ctx.strokeStyle = color;
    for (let i = 0; i < count; i++) {
      const r = seededRandom((Number(params.seed) || 1337) + i * 7919);
      const spawn = r() * Math.max(1, lifeFrames * 0.7);
      const ageFrames = time - spawn;
      if (ageFrames < 0 || ageFrames > lifeFrames) continue;
      const age = ageFrames / Math.max(1, fps);
      const angle = (r() * Math.PI * 2) + (preset === 'sparks' || preset === 'embers' ? -Math.PI / 2 : 0);
      const baseVelocity = (0.15 + r() * 0.9) * speed * spread;
      let vx = Math.cos(angle) * baseVelocity * width * 0.36;
      let vy = Math.sin(angle) * baseVelocity * height * (preset === 'dust' ? 0.12 : 0.35);
      if (preset === 'sparks' || preset === 'embers') vy -= (0.15 + r() * 0.7) * speed * height * 0.2;
      if (preset === 'magic') { vx *= 0.28; vy *= 0.28; }
      const x = originX + vx * age;
      const y = originY + vy * age + 0.5 * gravity * age * age;
      const fade = Math.max(0, 1 - ageFrames / lifeFrames);
      const radius = size * (preset === 'dust' ? 0.55 + r() * 1.6 : 0.55 + fade * 0.65);
      ctx.globalAlpha = fade * (preset === 'magic' ? 0.85 : 0.95);
      if (preset === 'sparks' || preset === 'embers') {
        ctx.lineWidth = Math.max(1, radius * (preset === 'sparks' ? 0.7 : 1.2));
        ctx.beginPath();
        ctx.moveTo(x - vx * 0.025, y - vy * 0.025);
        ctx.lineTo(x, y);
        ctx.stroke();
      } else if (preset === 'confetti') {
        ctx.save();
        ctx.translate(x, y);
        ctx.rotate(age * (r() > 0.5 ? 5 : -5));
        ctx.fillRect(-radius, -radius * 1.8, radius * 2, radius * 3.6);
        ctx.restore();
      } else if (preset === 'magic') {
        ctx.beginPath();
        ctx.arc(x, y, radius * 1.6, 0, Math.PI * 2);
        ctx.fill();
        ctx.globalAlpha = fade * 0.2;
        ctx.beginPath(); ctx.arc(x, y, radius * 3.4, 0, Math.PI * 2); ctx.fill();
      } else {
        ctx.beginPath();
        ctx.arc(x, y, radius, 0, Math.PI * 2);
        ctx.fill();
      }
    }
    ctx.restore();
  }

  function copyCanvas(source, target) {
    const ctx = target.getContext('2d');
    ctx.clearRect(0, 0, target.width, target.height);
    ctx.drawImage(source, 0, 0);
    return ctx;
  }


  function smoothStep(edge0, edge1, value) {
    const t = Math.max(0, Math.min(1, (value - edge0) / Math.max(0.000001, edge1 - edge0)));
    return t * t * (3 - 2 * t);
  }

  function angerTintPixel(red, green, blue, yNorm, intensity, tintStrength) {
    const level = Math.max(0, Math.min(1, Number(intensity) || 0));
    const tint = Math.max(0, Math.min(0.9, Number(tintStrength ?? 0.58)));
    if (level <= 0 || tint <= 0) return [red, green, blue];
    const position = Math.max(0, Math.min(1, Number(yNorm) || 0));
    const edge = 0.075;
    const coverage = level >= 0.985 ? 1 : smoothStep(1 - level - edge, 1 - level + edge, position);
    const amount = tint * coverage;
    return [
      Math.round(red + (255 - red) * amount),
      Math.round(green + (42 - green) * amount),
      Math.round(blue + (30 - blue) * amount)
    ];
  }

  function alphaBounds(data, width, height) {
    let left = width, top = height, right = -1, bottom = -1;
    for (let y = 0; y < height; y++) {
      for (let x = 0; x < width; x++) {
        if (data[(y * width + x) * 4 + 3] < 12) continue;
        if (x < left) left = x;
        if (x > right) right = x;
        if (y < top) top = y;
        if (y > bottom) bottom = y;
      }
    }
    if (right < left || bottom < top) return null;
    return { left, top, right, bottom, cx: (left + right) / 2, cy: (top + bottom) / 2,
      width: right - left + 1, height: bottom - top + 1 };
  }

  function drawAngerExplosion(ctx, width, height, bounds, frame, fps, elapsed, duration, seed, scale) {
    const progress = Math.max(0, Math.min(1, elapsed / Math.max(1, duration)));
    const fade = 1 - progress;
    const center = bounds || { cx: width / 2, cy: height * 0.46, width: width * 0.36, height: height * 0.5 };
    const baseRadius = Math.max(46, Math.max(center.width, center.height) * 0.34);
    const radius = baseRadius * (0.48 + progress * 1.45) * scale;
    ctx.save();
    ctx.globalCompositeOperation = 'screen';
    ctx.globalAlpha = Math.min(0.9, fade * (elapsed < fps * 0.12 ? 0.82 : 0.42));
    if (elapsed < fps * 0.18) {
      const flash = ctx.createRadialGradient(center.cx, center.cy, 0, center.cx, center.cy, baseRadius * 1.45);
      flash.addColorStop(0, 'rgba(255,244,194,0.78)');
      flash.addColorStop(0.25, 'rgba(255,163,61,0.44)');
      flash.addColorStop(1, 'rgba(255,47,26,0)');
      ctx.fillStyle = flash;
      ctx.beginPath();
      ctx.arc(center.cx, center.cy, baseRadius * 1.45, 0, Math.PI * 2);
      ctx.fill();
    }
    for (let ring = 0; ring < 2; ring++) {
      ctx.globalAlpha = fade * (ring === 0 ? 0.82 : 0.42);
      ctx.lineWidth = (ring === 0 ? 7 : 3) * (1 - progress * 0.35);
      ctx.strokeStyle = ring === 0 ? '#ffe29b' : '#ff5938';
      ctx.beginPath();
      ctx.arc(center.cx, center.cy, radius * (ring === 0 ? 1 : 1.22), 0, Math.PI * 2);
      ctx.stroke();
    }
    const random = seededRandom((Number(seed) || 901) + 1777);
    const rays = 26;
    for (let i = 0; i < rays; i++) {
      const angle = (i / rays) * Math.PI * 2 + (random() - 0.5) * 0.09;
      const inner = radius * (0.82 + random() * 0.12);
      const outer = radius * (1.12 + random() * 0.9) * scale;
      ctx.globalAlpha = fade * (0.35 + random() * 0.48);
      ctx.strokeStyle = i % 3 === 0 ? '#fff0c2' : i % 2 === 0 ? '#ffad51' : '#ff5137';
      ctx.lineWidth = 1.5 + random() * 3.5;
      ctx.beginPath();
      ctx.moveTo(center.cx + Math.cos(angle) * inner, center.cy + Math.sin(angle) * inner);
      ctx.lineTo(center.cx + Math.cos(angle) * outer, center.cy + Math.sin(angle) * outer);
      ctx.stroke();
    }
    ctx.restore();
  }

  function drawAngerFlames(ctx, width, height, frame, fps, intensity, parameters) {
    const strengthValue = Math.max(0, Math.min(1, (intensity - 0.12) / 0.88));
    if (strengthValue <= 0) return;
    const requestedHeight = Math.max(0.08, Math.min(0.42, Number(parameters.flame_height) || 0.22));
    const maxHeight = height * requestedHeight * strengthValue;
    const count = Math.max(12, Math.min(44, Math.round(width / 58)));
    const baseWidth = width / count;
    const time = frame / Math.max(1, fps);
    const seed = Number(parameters.seed) || 901;
    ctx.save();
    ctx.globalCompositeOperation = 'screen';
    ctx.globalAlpha = Math.min(0.94, strengthValue * 0.92);
    const baseGlow = ctx.createLinearGradient(0, height - maxHeight * 0.65, 0, height);
    baseGlow.addColorStop(0, 'rgba(255,67,24,0)');
    baseGlow.addColorStop(0.45, 'rgba(255,86,25,0.22)');
    baseGlow.addColorStop(1, 'rgba(255,151,48,0.52)');
    ctx.fillStyle = baseGlow;
    ctx.fillRect(0, height - maxHeight * 0.65, width, maxHeight * 0.65);
    for (let i = 0; i < count; i++) {
      const random = seededRandom(seed + i * 7919);
      const x = (i + 0.5) * baseWidth + (random() - 0.5) * baseWidth * 0.22;
      const phase = time * (3.1 + random() * 1.2) + i * 1.31 + random() * 6;
      const heightFactor = 0.46 + 0.54 * (0.5 + 0.5 * Math.sin(phase));
      const flameHeight = maxHeight * heightFactor * (0.82 + random() * 0.28);
      const half = baseWidth * (0.31 + random() * 0.15);
      const lean = Math.sin(phase * 0.72) * half * 0.62;
      const gradient = ctx.createLinearGradient(x, height - flameHeight, x, height);
      gradient.addColorStop(0, 'rgba(255,231,135,0.18)');
      gradient.addColorStop(0.16, 'rgba(255,191,69,0.94)');
      gradient.addColorStop(0.55, 'rgba(255,94,29,0.96)');
      gradient.addColorStop(1, 'rgba(178,26,16,0.98)');
      ctx.fillStyle = gradient;
      ctx.beginPath();
      ctx.moveTo(x - half, height);
      ctx.bezierCurveTo(x - half * 0.84, height - flameHeight * 0.3,
        x - half * 0.12 + lean * 0.15, height - flameHeight * 0.64,
        x + lean, height - flameHeight);
      ctx.bezierCurveTo(x + half * 0.1 + lean, height - flameHeight * 0.65,
        x + half * 0.94, height - flameHeight * 0.38,
        x + half, height);
      ctx.closePath();
      ctx.fill();

      const innerHeight = flameHeight * (0.42 + 0.18 * (0.5 + 0.5 * Math.sin(phase + 1.7)));
      const inner = ctx.createLinearGradient(x, height - innerHeight, x, height);
      inner.addColorStop(0, 'rgba(255,245,174,0)');
      inner.addColorStop(0.28, 'rgba(255,219,105,0.78)');
      inner.addColorStop(1, 'rgba(255,134,31,0)');
      ctx.fillStyle = inner;
      ctx.beginPath();
      ctx.moveTo(x - half * 0.38, height);
      ctx.quadraticCurveTo(x - half * 0.26, height - innerHeight * 0.62, x + lean * 0.52, height - innerHeight);
      ctx.quadraticCurveTo(x + half * 0.34, height - innerHeight * 0.47, x + half * 0.38, height);
      ctx.closePath();
      ctx.fill();
    }
    ctx.restore();
    drawParticles(ctx, {
      preset: 'embers', count: Math.round(18 + 24 * strengthValue), seed: seed + 49,
      speed: 1.25, spread: 1.1, gravity: -30, size: 2.4,
      life_seconds: 1.1, origin_x: 0.5, origin_y: 0.96, color: '#ffb24d'
    }, width, height, frame, fps);
  }

  function applyAngerRisePass(canvas, sourceCtx, outputCtx, parameters, frame, fps, intensity) {
    let pixels;
    try { pixels = sourceCtx.getImageData(0, 0, canvas.width, canvas.height); }
    catch (_) { return { applied:false, warning:'Anger-rise needs a readable local PNG/Canvas layer; pixel access was blocked.' }; }
    const width = canvas.width, height = canvas.height;
    const bounds = alphaBounds(pixels.data, width, height);
    const tintStrength = Math.max(0.1, Math.min(0.9, Number(parameters.tint_strength ?? 0.58)));
    for (let y = 0; y < height; y++) {
      const yNorm = y / Math.max(1, height - 1);
      for (let x = 0; x < width; x++) {
        const index = (y * width + x) * 4;
        if (pixels.data[index + 3] < 1) continue;
        const tinted = angerTintPixel(pixels.data[index], pixels.data[index + 1], pixels.data[index + 2],
          yNorm, intensity, tintStrength);
        pixels.data[index] = tinted[0];
        pixels.data[index + 1] = tinted[1];
        pixels.data[index + 2] = tinted[2];
      }
    }
    outputCtx.putImageData(pixels, 0, 0);
    const burstElapsed = Number(parameters.burst_elapsed ?? -1);
    const burstDuration = Math.max(8, Math.min(60, Number(parameters.burst_duration_frames) || 28));
    if (burstElapsed >= 0 && burstElapsed < burstDuration) {
      drawAngerExplosion(outputCtx, width, height, bounds, frame, fps, burstElapsed, burstDuration,
        parameters.seed, Math.max(0.5, Math.min(2, Number(parameters.explosion_scale) || 1)));
    }
    drawAngerFlames(outputCtx, width, height, frame, fps, intensity, parameters);
    return { applied:true };
  }

  function angerBurstElapsed(effect, localFrame, threshold, duration) {
    const firstFrame = Math.max(0, localFrame - duration + 1);
    for (let cursor = localFrame; cursor >= firstFrame; cursor--) {
      const current = Core.evaluateEffectParameters(effect, cursor).intensity;
      const previous = cursor === 0 ? 0 : Core.evaluateEffectParameters(effect, cursor - 1).intensity;
      if (current >= threshold && previous < threshold) return localFrame - cursor;
    }
    return -1;
  }

  function applyCanvasPass(canvas, type, parameters, frame, fps) {
    const p = parameters || {};
    const intensity = Math.max(0, Math.min(2, Number(p.intensity ?? 1)));
    if (intensity === 0 || type === 'custom') return { applied:false, warning:type === 'custom' ? 'Custom GLSL pass requires WebGL; skipped in Canvas 2D fallback.' : '' };
    const w = canvas.width, h = canvas.height;
    const source = makeCanvas(w, h, canvas);
    const sourceCtx = copyCanvas(canvas, source);
    const out = canvas.getContext('2d');
    const time = frame / Math.max(1, fps);
    const strength = (value, fallback) => Number.isFinite(Number(value)) ? Number(value) * intensity : fallback;

    if (type === 'anger-rise') {
      return applyAngerRisePass(canvas, sourceCtx, out, p, frame, fps, Math.max(0, Math.min(1, intensity)));
    }
    if (type === 'depth-of-field') {
      const blurred = makeCanvas(w,h,canvas);
      const bctx = blurred.getContext('2d');
      bctx.filter = 'blur(' + Math.max(0,Math.min(40,(Number(p.blur_radius)||7)*intensity)) + 'px)';
      bctx.drawImage(source,0,0);
      const basePixels = sourceCtx.getImageData(0,0,w,h);
      const blurPixels = bctx.getImageData(0,0,w,h);
      const outputPixels = basePixels;
      const fx = Math.max(0,Math.min(1,Number(p.focus_x ?? 0.5)))*w;
      const fy = Math.max(0,Math.min(1,Number(p.focus_y ?? 0.5)))*h;
      const radius = Math.max(0.01,Math.min(1,Number(p.focus_radius)||0.24))*Math.min(w,h);
      const edge = Math.max(radius+1,radius+Math.min(w,h)*0.18);
      for(let y=0;y<h;y++) for(let x=0;x<w;x++){
        const i=(y*w+x)*4;
        const distance=Math.hypot(x-fx,y-fy);
        const mix=Math.max(0,Math.min(1,(distance-radius)/(edge-radius)))*intensity;
        outputPixels.data[i]=Math.round(basePixels.data[i]*(1-mix)+blurPixels.data[i]*mix);
        outputPixels.data[i+1]=Math.round(basePixels.data[i+1]*(1-mix)+blurPixels.data[i+1]*mix);
        outputPixels.data[i+2]=Math.round(basePixels.data[i+2]*(1-mix)+blurPixels.data[i+2]*mix);
      }
      out.putImageData(outputPixels,0,0);
      return {applied:true};
    }
    if (type === 'swirl-warp') {
      let image;
      try { image = sourceCtx.getImageData(0,0,w,h); }
      catch (_) { return {applied:false,warning:'Pixel access is unavailable for the swirl transition.'}; }
      const original=new Uint8ClampedArray(image.data);
      const amount=Math.max(0,Math.min(3,Number(p.amount)||0))*intensity;
      const cx=w/2, cy=h/2, maxRadius=Math.hypot(cx,cy);
      for(let y=0;y<h;y++) for(let x=0;x<w;x++){
        const dx=x-cx, dy=y-cy, radius=Math.hypot(dx,dy);
        const angle=amount*(1-radius/maxRadius)*Math.PI*2;
        const sx=Math.max(0,Math.min(w-1,Math.round(cx+dx*Math.cos(angle)+dy*Math.sin(angle))));
        const sy=Math.max(0,Math.min(h-1,Math.round(cy-dx*Math.sin(angle)+dy*Math.cos(angle))));
        const from=(sy*w+sx)*4, to=(y*w+x)*4;
        image.data[to]=original[from];image.data[to+1]=original[from+1];
        image.data[to+2]=original[from+2];image.data[to+3]=original[from+3];
      }
      out.putImageData(image,0,0);
      return {applied:true};
    }

    if (type === 'blur') {
      const radius = Math.max(0, Math.min(40, strength(p.radius, 2)));
      out.clearRect(0,0,w,h);
      out.save(); out.filter = 'blur(' + radius + 'px)'; out.drawImage(source,0,0); out.restore();
      return { applied:true };
    }
    if (type === 'glow') {
      const radius = Math.max(0, Math.min(80, Number(p.radius)||12));
      out.clearRect(0,0,w,h);
      out.drawImage(source,0,0);
      const glow = makeCanvas(w,h,canvas);
      const gctx = glow.getContext('2d');
      gctx.filter = 'blur(' + radius + 'px)';
      gctx.drawImage(source,0,0);
      out.save(); out.globalCompositeOperation = 'screen'; out.globalAlpha = Math.min(1, Number(p.strength ?? 0.45) * intensity); out.drawImage(glow,0,0); out.restore();
      return { applied:true };
    }
    if (type === 'light-rays') {
      out.clearRect(0,0,w,h); out.drawImage(source,0,0);
      const rays = makeCanvas(w,h,canvas);
      const rctx = rays.getContext('2d');
      const cx = w * Number(p.origin_x ?? 0.5), cy = h * Number(p.origin_y ?? 0.15);
      const gradient = rctx.createRadialGradient(cx,cy,0,cx,cy,Math.max(w,h)*0.9);
      gradient.addColorStop(0,'rgba(255,238,190,'+Math.min(0.55,0.12*intensity)+')');
      gradient.addColorStop(0.55,'rgba(255,218,150,'+Math.min(0.16,0.05*intensity)+')');
      gradient.addColorStop(1,'rgba(255,220,170,0)');
      rctx.fillStyle=gradient; rctx.fillRect(0,0,w,h);
      rctx.globalCompositeOperation='destination-out';
      for(let i=0;i<18;i++){
        const angle=(i/18)*Math.PI*2+Number(p.angle||0);
        rctx.beginPath(); rctx.moveTo(cx,cy);
        rctx.lineTo(cx+Math.cos(angle-0.018)*w*1.4,cy+Math.sin(angle-0.018)*h*1.4);
        rctx.lineTo(cx+Math.cos(angle+0.018)*w*1.4,cy+Math.sin(angle+0.018)*h*1.4);
        rctx.closePath(); rctx.fill();
      }
      out.save(); out.globalCompositeOperation='screen'; out.drawImage(rays,0,0); out.restore();
      return { applied:true };
    }
    let image;
    try { image = sourceCtx.getImageData(0,0,w,h); }
    catch (_) { return { applied:false, warning:'Pixel access is unavailable for this Canvas 2D effect.' }; }
    const src = image.data;
    if (type === 'brightness-contrast' || type === 'saturation' || type === 'vignette') {
      const brightness = strength(p.brightness,0);
      const contrast = 1 + (Number(p.contrast ?? 1)-1)*intensity;
      const saturation = 1 + (Number(p.saturation ?? 1)-1)*intensity;
      const radius = Math.max(0.05,Math.min(1,Number(p.radius)||0.72));
      const edge = Math.max(0,Math.min(1,strength(p.strength,0.35)));
      for(let y=0;y<h;y++) for(let x=0;x<w;x++){
        const i=(y*w+x)*4;
        if(src[i+3]===0) continue;
        let red=src[i]/255, green=src[i+1]/255, blue=src[i+2]/255;
        if(type==='brightness-contrast'){
          red=(red-0.5)*contrast+0.5+brightness;
          green=(green-0.5)*contrast+0.5+brightness;
          blue=(blue-0.5)*contrast+0.5+brightness;
        } else if(type==='saturation'){
          const l=0.2126*red+0.7152*green+0.0722*blue;
          red=l+(red-l)*saturation; green=l+(green-l)*saturation; blue=l+(blue-l)*saturation;
        } else {
          const dx=(x/w)-0.5, dy=(y/h)-0.5;
          const distance=Math.sqrt(dx*dx+dy*dy);
          const v=Math.max(0,Math.min(1,(distance-radius)/(0.78-radius)))*edge;
          red*=1-v; green*=1-v; blue*=1-v;
        }
        src[i]=Math.round(Math.max(0,Math.min(1,red))*255);
        src[i+1]=Math.round(Math.max(0,Math.min(1,green))*255);
        src[i+2]=Math.round(Math.max(0,Math.min(1,blue))*255);
      }
    } else if(type==='chromatic-aberration'){
      const shift=Math.min(30,Math.round(strength(p.amount,2)));
      const original=new Uint8ClampedArray(src);
      for(let y=0;y<h;y++) for(let x=0;x<w;x++){
        const i=(y*w+x)*4;
        const rx=(y*w+Math.max(0,Math.min(w-1,x+shift)))*4;
        const bx=(y*w+Math.max(0,Math.min(w-1,x-shift)))*4;
        src[i]=original[rx]; src[i+2]=original[bx];
      }
    } else if(type==='ripple'){
      const original=new Uint8ClampedArray(src);
      const amp=Math.min(24,Math.abs(strength(p.amount,0.25))*16);
      const freq=Math.max(1,Number(p.frequency)||8);
      for(let y=0;y<h;y++) for(let x=0;x<w;x++){
        const shift=Math.round(Math.sin(y/h*freq*Math.PI*2-time*5)*amp);
        const sx=Math.max(0,Math.min(w-1,x+shift));
        const from=(y*w+sx)*4,to=(y*w+x)*4;
        src[to]=original[from];src[to+1]=original[from+1];src[to+2]=original[from+2];src[to+3]=original[from+3];
      }
    } else if(type==='glitch'){
      const original=new Uint8ClampedArray(src);
      const rng=seededRandom((Number(p.seed)||7)+frame*17);
      const bands=Math.max(2,Math.min(80,Math.round(Number(p.bands)||24)));
      const bandH=Math.max(1,Math.floor(h/bands));
      const maxShift=Math.min(90,Math.round(Math.abs(strength(p.amount,0.35))*70));
      for(let y=0;y<h;y++){
        const offset=Math.round((rng()-0.5)*maxShift);
        for(let x=0;x<w;x++){
          const sx=Math.max(0,Math.min(w-1,x+offset));
          const from=(y*w+sx)*4,to=(y*w+x)*4;
          src[to]=original[from];src[to+1]=original[from+1];src[to+2]=original[from+2];src[to+3]=original[from+3];
        }
      }
      for(let y=0;y<h;y+=bandH*3) for(let x=0;x<w;x++) if(rng()<0.018){
        const i=(y*w+x)*4; src[i]=255;src[i+1]=255;src[i+2]=255;
      }
    } else if(type==='shake' || type==='motion-blur'){
      out.clearRect(0,0,w,h);
      const amount=Math.min(50,Math.abs(strength(p.amount,type==='shake'?5:4)));
      if(type==='shake'){
        const rng=seededRandom((Number(p.seed)||13)+frame);
        out.drawImage(source,Math.round((rng()-0.5)*amount*2),Math.round((rng()-0.5)*amount*2));
        return { applied:true };
      }
      out.drawImage(source,0,0);
      out.save(); out.globalCompositeOperation='source-over';
      for(let n=1;n<=3;n++){out.globalAlpha=0.16;out.drawImage(source,-amount*n/3,0);out.drawImage(source,amount*n/3,0);}
      out.restore(); return { applied:true };
    } else {
      return { applied:false, warning:'Unsupported Canvas 2D pass: '+type };
    }
    out.putImageData(image,0,0);
    return { applied:true };
  }

  function applyTransitionMask(layer, transition, progress, edge, sequence) {
    if (!transition || !['wipe','radial','hypnosis_wheel'].includes(transition.type)) return;
    const width=sequence.width,height=sequence.height;
    const mask=makeCanvas(width,height,layer);
    const ctx=mask.getContext('2d');
    const p=Math.max(0,Math.min(1,progress));
    ctx.fillStyle='#fff';
    const direction=transition.direction||'right';
    if(transition.type==='wipe'){
      const fraction=p;
      if(direction==='left') ctx.fillRect(width*(1-fraction),0,width*fraction,height);
      else if(direction==='up') ctx.fillRect(0,height*(1-fraction),width,height*fraction);
      else if(direction==='down') ctx.fillRect(0,0,width,height*fraction);
      else ctx.fillRect(0,0,width*fraction,height);
    } else if(transition.type==='radial'){
      ctx.beginPath();ctx.arc(width/2,height/2,Math.hypot(width,height)*p,0,Math.PI*2);ctx.fill();
    } else {
      const count=Math.max(3,Math.min(64,Number(transition.parameters?.segments)||12));
      const angle=(Math.PI*2/count)*p;
      for(let i=0;i<count;i++){
        const start=(i/count)*Math.PI*2+(direction==='counterclockwise'?-Math.PI:0);
        ctx.beginPath();ctx.moveTo(width/2,height/2);
        ctx.arc(width/2,height/2,Math.hypot(width,height),start,start+angle);
        ctx.closePath();ctx.fill();
      }
    }
    if(edge==='out'){
      ctx.globalCompositeOperation='source-out';
      // Preserve the inverse of the revealed area as the outgoing content.
      const inverse=makeCanvas(width,height,layer);
      const inverseCtx=inverse.getContext('2d');
      inverseCtx.fillStyle='#fff';inverseCtx.fillRect(0,0,width,height);
      inverseCtx.globalCompositeOperation='destination-out';
      inverseCtx.drawImage(mask,0,0);
      ctx.clearRect(0,0,width,height);
      ctx.drawImage(inverse,0,0);
    }
    const layerCtx=layer.getContext('2d');
    layerCtx.save();layerCtx.globalCompositeOperation='destination-in';layerCtx.drawImage(mask,0,0);layerCtx.restore();
  }

  function transitionValues(clip, frame, sequence, baseTransform) {
    const local=frame-clip.start_frame;
    const remaining=clip.start_frame+clip.duration_frames-1-frame;
    const result={opacity:1,transform:Object.assign({},baseTransform,{position:[...baseTransform.position],scale:[...baseTransform.scale]}),masks:[],distortions:[]};
    const entries=[['in',clip.transition_in,local],['out',clip.transition_out,remaining]];
    for(const [edge,transition,elapsed] of entries){
      if(!transition || elapsed<0 || elapsed>=transition.duration_frames) continue;
      const raw=Math.max(0,Math.min(1,elapsed/Math.max(1,transition.duration_frames)));
      const progress=edge==='in'?raw:1-raw;
      const intensity=Math.max(0,Math.min(2,Number(transition.parameters?.intensity)||1));
      switch(transition.type){
        case 'fade': case 'crossfade':
          result.opacity*=edge==='in'?progress:raw;
          break;
        case 'wipe': case 'radial': case 'hypnosis_wheel':
          result.masks.push({transition,progress,edge});
          break;
        case 'zoom': {
          const scale=edge==='in'?0.72+0.28*progress:1+0.18*(1-progress);
          result.transform.scale=[result.transform.scale[0]*scale,result.transform.scale[1]*scale];
          result.opacity*=edge==='in'?Math.min(1,progress*1.8):1;
          break;
        }
        case 'whip_pan': {
          const amount=(edge==='in'?(1-progress):progress)*Math.max(sequence.width,sequence.height)*0.85*intensity;
          if(transition.direction==='up') result.transform.position[1]+=edge==='in'?-amount:amount;
          else if(transition.direction==='down') result.transform.position[1]+=edge==='in'?amount:-amount;
          else result.transform.position[0]+=edge==='in'?(transition.direction==='left'?-amount:amount):(transition.direction==='left'?amount:-amount);
          result.opacity*=edge==='in'?Math.min(1,0.35+progress*0.65):Math.max(0,1-progress);
          break;
        }
        case 'swirl_warp':
          result.distortions.push({type:'swirl-warp',parameters:{amount:0.6*intensity*progress,intensity:1}});
          break;
        case 'glitch':
          result.distortions.push({type:'glitch',parameters:{amount:0.65*intensity*progress,seed:clip.start_frame+17,intensity:1}});
          break;
      }
    }
    return result;
  }


  function sourceFramesAtClipFrame(clip, globalFrame) {
    const localFrame = Math.max(0,Math.min(clip.duration_frames,Math.round(Number(globalFrame)||0)-clip.start_frame));
    let sourceFrames = Math.max(0,Number(clip.source_in_frame)||0);
    for(let frame=0;frame<localFrame;frame++){
      sourceFrames += Core.evaluateClipPlaybackRate(clip,clip.start_frame+frame);
    }
    return sourceFrames;
  }

  function evaluatePass(pass, frame) {
    const params=Object.assign({},pass.parameters||{});
    for(const property of ['intensity','amount','radius','strength','saturation','brightness','contrast','frequency']){
      if(Number.isFinite(Number(params[property]))){
        params[property]=Core.evaluateKeyframes({keyframes:pass.keyframes||[]},property,frame,Number(params[property]));
      }
    }
    return Object.assign({},pass,{parameters:params});
  }

  function applyPostProcessing(canvas, project, frame, fps, warnings) {
    const settings=project.settings.post_processing||{renderer:'auto',passes:[]};
    const passes=(settings.passes||[]).filter(pass=>pass.enabled!==false).map(pass=>evaluatePass(pass,frame));
    if(!passes.length) return {backend:'canvas2d'};
    const shader=root.FFV2Shaders;
    if(shader && settings.renderer!=='canvas2d'){
      const result=shader.apply(canvas,passes,frame,settings.renderer||'auto');
      if(result.used) {
        (result.warnings||[]).forEach(message=>warnings.push({clip_id:'post-processing',message}));
        return {backend:'webgl'};
      }
      if(settings.renderer==='webgl'||settings.renderer==='auto'){
        warnings.push({clip_id:'post-processing',message:'WebGL pass pipeline fell back to Canvas 2D: '+(result.reason||'unavailable')});
      }
    } else if(settings.renderer==='webgl') {
      warnings.push({clip_id:'post-processing',message:'WebGL shader framework is not loaded; using Canvas 2D fallback.'});
    }
    for(const pass of passes){
      const result=applyCanvasPass(canvas,pass.type,pass.parameters,frame,fps);
      if(result.warning) warnings.push({clip_id:'post-processing',message:result.warning});
    }
    return {backend:'canvas2d'};
  }

  function applyClipEffects(layer, clip, localFrame, frame, fps) {
    for(const effect of clip.effects||[]){
      if(effect.enabled===false) continue;
      const parameters=Core.evaluateEffectParameters(effect,localFrame);
      if (effect.type === 'anger-rise') {
        const threshold = Math.max(0.5, Math.min(1, Number(parameters.burst_threshold) || 0.985));
        const burstDuration = Math.max(8, Math.min(60, Number(parameters.burst_duration_frames) || 28));
        parameters.burst_elapsed = angerBurstElapsed(effect, localFrame, threshold, burstDuration);
      }
      const result=applyCanvasPass(layer,effect.type,parameters,frame,fps);
      if(result.warning) return result.warning;
    }
    return '';
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
    const activeVisual = Core.getActiveVisualClips(project, frame);
    const processed3DTracks = new Set();
    for (const item of activeVisual) {
      const clip = item.clip;
      const referencedAsset = clip.asset_id ? projectAssets.find(ref => ref.id === clip.asset_id) : null;
      const is3DModel = item.track.type === 'scene3d' || referencedAsset?.media_type === 'model3d';
      if (is3DModel) {
        const trackKey = item.track.id;
        if (processed3DTracks.has(trackKey)) continue;
        processed3DTracks.add(trackKey);
        const modelItems = activeVisual.filter(candidate => candidate.track.id === trackKey && candidate.clip.asset_id &&
          projectAssets.find(asset => asset.id === candidate.clip.asset_id)?.media_type === 'model3d');
        try {
          if (!root.FFV2ThreeStudio || typeof options.resolveModelAsset !== 'function') {
            throw new Error('The local Three.js runtime or 3D asset resolver is unavailable.');
          }
          const models = [];
          for (const candidate of modelItems) {
            const ref = projectAssets.find(asset => asset.id === candidate.clip.asset_id);
            const asset = await options.resolveModelAsset(ref);
            models.push({ asset, clip:candidate.clip });
          }
          const settings = Core.getMainSequence(project).scene3d || Core.default3DSceneSettings();
          const result = await root.FFV2ThreeStudio.renderTrack({
            models, allAssets:options.modelAssets || [], resolveDependency:options.resolveModelDependency,
            settings, width:sequence.width, height:sequence.height, frame, fps:sequence.fps
          });
          output.save();
          output.globalAlpha = 1;
          output.globalCompositeOperation = 'source-over';
          output.drawImage(result.canvas,0,0);
          output.restore();
          drawn += result.drawn;
          if (result.collisions.length) warnings.push({clip_id:modelItems[0]?.clip.id || trackKey,message:result.collisions.length+' approximate AABB contact(s) detected in the 3D scene.'});
        } catch (error) {
          warnings.push({clip_id:clip.id,message:'3D layer not rendered: '+error.message});
        }
        continue;
      }
      try {
        const baseTransform = resolveGlobalTransform(clip, frame, byId);
        const transition = transitionValues(clip, frame, sequence, baseTransform);
        const transform = transition.transform;
        const localFrame = Math.max(0, frame - clip.start_frame);
        const mediaTime = sourceFramesAtClipFrame(clip,frame) / sequence.fps;
        const asset = clip.asset_id ? projectAssets.find(ref => ref.id === clip.asset_id) : null;
        const source = asset ? await resolveAsset(asset, clip, mediaTime) : null;
        const layer = makeCanvas(sequence.width, sequence.height, canvas);
        const layerCtx = layer.getContext('2d');
        if (!layerCtx) throw new Error('Canvas 2D layer context is unavailable.');
        await drawClipContent(layerCtx, clip, source, sequence, transform, frame);
        const effectWarning = applyClipEffects(layer, clip, localFrame, frame, sequence.fps);
        if (effectWarning) warnings.push({clip_id:clip.id,message:effectWarning});
        await applyMask(layer, clip.mask, sequence, resolveAsset, clip, frame, projectAssets);
        for(const transitionMask of transition.masks) applyTransitionMask(layer,transitionMask.transition,transitionMask.progress,transitionMask.edge,sequence);
        for(const distortion of transition.distortions) {
          applyCanvasPass(layer,distortion.type,distortion.parameters,frame,sequence.fps);
        }
        output.save();
        const requestedBlend = clip.blend_mode === 'normal' || !clip.blend_mode ? 'source-over' : clip.blend_mode;
        output.globalCompositeOperation = BLENDS.has(requestedBlend) ? requestedBlend : 'source-over';
        output.globalAlpha = Math.max(0,Math.min(1,transform.opacity*transition.opacity));
        output.drawImage(layer, 0, 0);
        output.restore();
        drawn++;
      } catch (error) {
        warnings.push({ clip_id: clip.id, message: error.message });
      }
    }
    const post = applyPostProcessing(canvas,project,frame,sequence.fps,warnings);
    return { frame, drawn, warnings, width: sequence.width, height: sequence.height, backend:post.backend };
  }

  const api = { composeFrame, resolveGlobalTransform, drawText, drawShape, fitAsset, drawParticles, seededRandom, applyCanvasPass, angerTintPixel, angerBurstElapsed, transitionValues, applyTransitionMask, applyPostProcessing, sourceFramesAtClipFrame };
  root.FFV2Renderer = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
