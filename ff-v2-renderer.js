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
          result.opacity*=progress;
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
          result.opacity*=Math.min(1,0.55+progress*0.45);
          break;
        }
        case 'swirl_warp':
          result.distortions.push({type:'ripple',parameters:{amount:0.6*intensity*progress,frequency:10,intensity:1}});
          break;
        case 'glitch':
          result.distortions.push({type:'glitch',parameters:{amount:0.65*intensity*progress,seed:clip.start_frame+17,intensity:1}});
          break;
      }
    }
    return result;
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
    for (const item of Core.getActiveVisualClips(project, frame)) {
      const clip = item.clip;
      try {
        const baseTransform = resolveGlobalTransform(clip, frame, byId);
        const transition = transitionValues(clip, frame, sequence, baseTransform);
        const transform = transition.transform;
        const localFrame = Math.max(0, frame - clip.start_frame);
        const mediaTime = ((Number(clip.source_in_frame) || 0) + localFrame * (Number(clip.playback_rate) || 1)) / sequence.fps;
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

  const api = { composeFrame, resolveGlobalTransform, drawText, drawShape, fitAsset, drawParticles, seededRandom, applyCanvasPass, transitionValues, applyTransitionMask, applyPostProcessing };
  root.FFV2Renderer = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
