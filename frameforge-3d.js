/* FrameForge 3D — dependency-free, code-first 3D renderer for FrameForge.
 * It transforms real 3D meshes through a camera and rasterizes the projected
 * triangles onto FrameForge's Canvas 2D frame layer. No generated images or
 * external libraries are used.
 */
(function (root) {
  'use strict';

  const VERSION = '1.0.0';
  const V = {
    add: (a, b) => [a[0] + b[0], a[1] + b[1], a[2] + b[2]],
    sub: (a, b) => [a[0] - b[0], a[1] - b[1], a[2] - b[2]],
    mul: (a, s) => [a[0] * s, a[1] * s, a[2] * s],
    dot: (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2],
    cross: (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]],
    length: (a) => Math.hypot(a[0], a[1], a[2]),
    norm: (a) => { const n = Math.hypot(a[0], a[1], a[2]) || 1; return [a[0] / n, a[1] / n, a[2] / n]; }
  };

  function vec3(value, fallback) {
    if (Array.isArray(value) && value.length >= 3) return [Number(value[0]) || 0, Number(value[1]) || 0, Number(value[2]) || 0];
    return fallback.slice();
  }

  function colorRGB(color) {
    if (Array.isArray(color)) return [color[0] || 0, color[1] || 0, color[2] || 0];
    const text = String(color || '#b7c7dc').trim();
    const short = /^#([0-9a-f]{3})$/i.exec(text);
    const full = /^#([0-9a-f]{6})$/i.exec(text);
    if (short) return short[1].split('').map((c) => parseInt(c + c, 16));
    if (full) return [parseInt(full[1].slice(0, 2), 16), parseInt(full[1].slice(2, 4), 16), parseInt(full[1].slice(4, 6), 16)];
    const rgb = /^rgba?\(([^)]+)\)/i.exec(text);
    if (rgb) return rgb[1].split(',').slice(0, 3).map((n) => Math.max(0, Math.min(255, Number(n.trim()) || 0)));
    return [183, 199, 220];
  }

  function cssColor(rgb, light, material) {
    const factor = Math.max(0, Math.min(1.5, light));
    const c = rgb.map((v) => Math.max(0, Math.min(255, Math.round(v * factor))));
    return `rgb(${c[0]},${c[1]},${c[2]})`;
  }

  function rotateXYZ(point, rotation) {
    let [x, y, z] = point;
    const [rx, ry, rz] = rotation;
    let c = Math.cos(rx), s = Math.sin(rx); [y, z] = [y * c - z * s, y * s + z * c];
    c = Math.cos(ry); s = Math.sin(ry); [x, z] = [x * c + z * s, -x * s + z * c];
    c = Math.cos(rz); s = Math.sin(rz); [x, y] = [x * c - y * s, x * s + y * c];
    return [x, y, z];
  }

  class Geometry {
    constructor(vertices, triangles) {
      this.vertices = vertices.map((p) => vec3(p, [0, 0, 0]));
      this.triangles = triangles.map((t) => [t[0] | 0, t[1] | 0, t[2] | 0]);
    }
  }

  class Mesh {
    constructor(geometry, material, options) {
      if (!(geometry instanceof Geometry)) throw new Error('FF3D.Mesh expects a Geometry.');
      const opts = options || {};
      this.geometry = geometry;
      this.material = Object.assign({ color: '#8ea8c8', roughness: 0.82, opacity: 1, solid: true, depthTest: true, depthWrite: true, wireframe: false, wireColor: '#172336' }, material || {});
      this.position = vec3(opts.position, [0, 0, 0]);
      this.rotation = vec3(opts.rotation, [0, 0, 0]);
      this.scale = Array.isArray(opts.scale) ? vec3(opts.scale, [1, 1, 1]) : [1, 1, 1];
      this.name = opts.name || 'Mesh';
      this.visible = opts.visible !== false;
    }
  }

  class Scene {
    constructor(options) {
      const opts = options || {};
      this.objects = [];
      this.lights = [{ type: 'ambient', color: '#ffffff', intensity: 0.38 }, { type: 'directional', direction: [-0.55, 0.78, 0.48], color: '#ffffff', intensity: 0.9 }];
      this.background = opts.background === undefined ? null : opts.background;
      this.fog = opts.fog || null;
      this.depthMode = opts.depthMode === 'zbuffer' ? 'zbuffer' : 'painter';
    }
    add(object) {
      if (!(object instanceof Mesh)) throw new Error('Scene.add expects an FF3D.Mesh.');
      this.objects.push(object);
      return object;
    }
    addLight(light) { this.lights.push(Object.assign({}, light)); return this; }
    remove(object) { this.objects = this.objects.filter((item) => item !== object); }
    clear() { this.objects.length = 0; }
  }

  class Camera {
    constructor(options) {
      const opts = options || {};
      this.position = vec3(opts.position, [5, 4, 7]);
      this.target = vec3(opts.target, [0, 0, 0]);
      this.up = vec3(opts.up, [0, 1, 0]);
      this.projection = opts.projection === 'orthographic' ? 'orthographic' : 'perspective';
      this.fov = Math.max(10, Math.min(120, Number(opts.fov) || 48));
      this.orthoHeight = Math.max(0.1, Number(opts.orthoHeight) || 8);
      this.near = Math.max(0.01, Number(opts.near) || 0.1);
      this.far = Math.max(this.near + 1, Number(opts.far) || 1000);
      this.useEditorView = opts.useEditorView !== false;
      this.viewName = opts.view || 'three-quarter';
    }
    lookAt(target) { this.target = vec3(target, this.target); return this; }
    setView(name) { this.viewName = String(name || 'three-quarter'); this.useEditorView = false; return this; }
    orbit(yaw, pitch, distance) {
      const y = Number(yaw) || 0, p = Math.max(-1.48, Math.min(1.48, Number(pitch) || 0));
      const d = Math.max(0.25, Number(distance) || V.length(V.sub(this.position, this.target)) || 8);
      this.position = [this.target[0] + Math.sin(y) * Math.cos(p) * d, this.target[1] + Math.sin(p) * d, this.target[2] + Math.cos(y) * Math.cos(p) * d];
      this.up = [0, 1, 0];
      return this;
    }
    dolly(amount) {
      const direction = V.norm(V.sub(this.position, this.target));
      this.position = V.add(this.position, V.mul(direction, Number(amount) || 0));
      return this;
    }
    pan(x, y, z) { const delta = [Number(x) || 0, Number(y) || 0, Number(z) || 0]; this.position = V.add(this.position, delta); this.target = V.add(this.target, delta); return this; }
  }

  function cubeGeometry(size) {
    const h = (Number(size) || 1) / 2;
    const v = [[-h,-h,-h],[h,-h,-h],[h,h,-h],[-h,h,-h],[-h,-h,h],[h,-h,h],[h,h,h],[-h,h,h]];
    const f = [[0,2,1],[0,3,2],[4,5,6],[4,6,7],[0,1,5],[0,5,4],[3,7,6],[3,6,2],[0,4,7],[0,7,3],[1,2,6],[1,6,5]];
    return new Geometry(v, f);
  }

  function sphereGeometry(radius, segments, rings) {
    const r = Number(radius) || 1, s = Math.max(6, Math.min(48, segments | 0 || 16)), n = Math.max(4, Math.min(32, rings | 0 || 10));
    const v = [], f = [];
    for (let y = 0; y <= n; y++) {
      const theta = y / n * Math.PI;
      for (let x = 0; x <= s; x++) {
        const phi = x / s * Math.PI * 2;
        v.push([r * Math.sin(theta) * Math.cos(phi), r * Math.cos(theta), r * Math.sin(theta) * Math.sin(phi)]);
      }
    }
    for (let y = 0; y < n; y++) for (let x = 0; x < s; x++) {
      const a = y * (s + 1) + x, b = a + s + 1;
      f.push([a, a + 1, b], [a + 1, b + 1, b]);
    }
    return new Geometry(v, f);
  }

  function planeGeometry(width, depth) {
    const x = (Number(width) || 1) / 2, z = (Number(depth) || width || 1) / 2;
    return new Geometry([[-x,0,-z],[x,0,-z],[x,0,z],[-x,0,z]], [[0,2,1],[0,3,2]]);
  }

  function cylinderGeometry(radiusTop, radiusBottom, height, segments) {
    const top = Math.max(0, Number.isFinite(Number(radiusTop)) ? Number(radiusTop) : 0.5), bottom = Math.max(0, Number.isFinite(Number(radiusBottom)) ? Number(radiusBottom) : 0.5);
    const h = (Number(height) || 1) / 2, s = Math.max(6, Math.min(48, segments | 0 || 16));
    const v = [], f = [];
    for (let i = 0; i < s; i++) { const a = i / s * Math.PI * 2; v.push([Math.cos(a) * bottom, -h, Math.sin(a) * bottom]); }
    for (let i = 0; i < s; i++) { const a = i / s * Math.PI * 2; v.push([Math.cos(a) * top, h, Math.sin(a) * top]); }
    const bottomCenter = v.length; v.push([0, -h, 0]);
    const topCenter = v.length; v.push([0, h, 0]);
    for (let i = 0; i < s; i++) { const j = (i + 1) % s; f.push([i, s + j, j], [i, s + i, s + j], [bottomCenter, i, j], [topCenter, s + j, s + i]); }
    return new Geometry(v, f);
  }

  function makeMesh(geometry, material, options) { return new Mesh(geometry, material, options); }
  const primitives = {
    cube: (options) => { const o = options || {}; return makeMesh(cubeGeometry(o.size || 1), o.material || o, o); },
    sphere: (options) => { const o = options || {}; return makeMesh(sphereGeometry(o.radius || 1, o.segments, o.rings), o.material || o, o); },
    plane: (options) => { const o = options || {}; return makeMesh(planeGeometry(o.width || 1, o.depth || o.width || 1), o.material || o, o); },
    cylinder: (options) => { const o = options || {}; return makeMesh(cylinderGeometry(o.radiusTop === undefined ? (o.radius || 0.5) : o.radiusTop, o.radiusBottom === undefined ? (o.radius || 0.5) : o.radiusBottom, o.height || 1, o.segments), o.material || o, o); },
    cone: (options) => { const o = options || {}; return makeMesh(cylinderGeometry(0, o.radius || 0.5, o.height || 1, o.segments), o.material || o, o); },
    custom: (vertices, triangles, material, options) => makeMesh(new Geometry(vertices, triangles), material, options)
  };

  function viewPose(camera, viewName) {
    const target = camera.target.slice();
    const base = V.sub(camera.position, target);
    const distance = Math.max(0.5, V.length(base));
    let direction;
    let up = [0, 1, 0];
    switch (viewName) {
      case 'front': direction = [0, 0, 1]; break;
      case 'back': direction = [0, 0, -1]; break;
      case 'left': direction = [1, 0, 0]; break;
      case 'right': direction = [-1, 0, 0]; break;
      case 'top': direction = [0, 1, 0]; up = [0, 0, -1]; break;
      case 'bottom': direction = [0, -1, 0]; up = [0, 0, 1]; break;
      case 'isometric': direction = [1, 0.85, 1]; up = [0, 1, 0]; break;
      case 'three-quarter': direction = [0.75, 0.48, 1]; break;
      default: return { position: camera.position, target, up: camera.up };
    }
    return { position: V.add(target, V.mul(V.norm(direction), distance)), target, up };
  }

  function transformVertex(vertex, mesh) {
    const scaled = [vertex[0] * mesh.scale[0], vertex[1] * mesh.scale[1], vertex[2] * mesh.scale[2]];
    return V.add(rotateXYZ(scaled, mesh.rotation), mesh.position);
  }

  function makeCameraBasis(pose) {
    const forward = V.norm(V.sub(pose.target, pose.position));
    let right = V.cross(forward, pose.up);
    if (V.length(right) < 1e-5) right = V.cross(forward, [0, 0, 1]);
    right = V.norm(right);
    const up = V.norm(V.cross(right, forward));
    return { forward, right, up };
  }

  function render(ctx, scene, camera, options) {
    if (!ctx || !scene || !camera) throw new Error('FF3D.render(ctx, scene, camera) needs all three arguments.');
    const opts = options || {};
    const width = Math.max(1, Number(opts.width) || ctx.canvas?.width || 720);
    const height = Math.max(1, Number(opts.height) || ctx.canvas?.height || 1280);
    ctx.save();
    ctx.clearRect(0, 0, width, height);
    const background = opts.background === undefined ? scene.background : opts.background;
    if (background) { ctx.fillStyle = background; ctx.fillRect(0, 0, width, height); }

    const selectedView = camera.useEditorView ? editorView : camera.viewName;
    const pose = viewPose(camera, selectedView);
    const basis = makeCameraBasis(pose);
    const f = (height * 0.5) / Math.tan(camera.fov * Math.PI / 360);
    const centerX = width * 0.5, centerY = height * 0.5;
    const project = (world) => {
      const rel = V.sub(world, pose.position);
      const x = V.dot(rel, basis.right), y = V.dot(rel, basis.up), z = V.dot(rel, basis.forward);
      if (z <= camera.near || z >= camera.far) return null;
      if (camera.projection === 'orthographic') {
        const scale = height / camera.orthoHeight;
        return { x: centerX + x * scale, y: centerY - y * scale, z };
      }
      return { x: centerX + x * f / z, y: centerY - y * f / z, z };
    };

    const ambient = scene.lights.filter((l) => l.type === 'ambient').reduce((sum, l) => sum + (Number(l.intensity) || 0), 0);
    const directions = scene.lights.filter((l) => l.type === 'directional').map((l) => ({ direction: V.norm(vec3(l.direction, [-0.5, 1, 0.5])), intensity: Number(l.intensity) || 0.7 }));
    const triangles = [];
    for (const mesh of scene.objects) {
      if (!mesh.visible) continue;
      const world = mesh.geometry.vertices.map((point) => transformVertex(point, mesh));
      for (const indices of mesh.geometry.triangles) {
        const a = world[indices[0]], b = world[indices[1]], c = world[indices[2]];
        if (!a || !b || !c) continue;
        const pa = project(a), pb = project(b), pc = project(c);
        if (!pa || !pb || !pc) continue;
        const normal = V.norm(V.cross(V.sub(b, a), V.sub(c, a)));
        const center = V.mul(V.add(V.add(a, b), c), 1 / 3);
        const toCamera = V.norm(V.sub(pose.position, center));
        const facing = V.dot(normal, toCamera);
        if (mesh.material.side !== 'double' && facing <= -0.035) continue;
        let light = ambient;
        for (const lamp of directions) light += Math.max(0, V.dot(normal, lamp.direction)) * lamp.intensity;
        light = Math.max(0.16, Math.min(1.32, light));
        const base = colorRGB(mesh.material.color);
        const pixelColor = base.map((value) => Math.max(0, Math.min(255, Math.round(value * light))));
        const rgb = `rgb(${pixelColor[0]},${pixelColor[1]},${pixelColor[2]})`;
        const opacity = mesh.material.opacity === undefined ? 1 : Math.max(0, Math.min(1, Number(mesh.material.opacity)));
        triangles.push({ points: [pa, pb, pc], depth: (pa.z + pb.z + pc.z) / 3, color: rgb, pixelColor, opacity, solid: mesh.material.solid !== false, depthTest: mesh.material.depthTest !== false, depthWrite: mesh.material.depthWrite !== false, wireframe: mesh.material.wireframe, wireColor: mesh.material.wireColor || '#172336' });
      }
    }
    const depthMode = opts.depthMode || scene.depthMode || 'painter';
    triangles.sort((a, b) => b.depth - a.depth);
    let solidCount = 0;
    if (depthMode === 'zbuffer') {
      // Opaque solid meshes get per-pixel depth testing and depth writes.
      // This prevents intersecting geometry and feet/ground surfaces from drawing through each other.
      const image = ctx.getImageData(0, 0, width, height);
      const pixels = image.data;
      const depthBuffer = new Float32Array(width * height);
      depthBuffer.fill(Infinity);
      const overlays = [];
      for (const tri of triangles) {
        if (!tri.solid || tri.opacity < 0.999 || !tri.depthTest) { overlays.push(tri); continue; }
        solidCount += 1;
        const [a, b, c] = tri.points;
        const denom = (b.y - c.y) * (a.x - c.x) + (c.x - b.x) * (a.y - c.y);
        if (Math.abs(denom) < 1e-8) continue;
        const minX = Math.max(0, Math.floor(Math.min(a.x, b.x, c.x)));
        const maxX = Math.min(width - 1, Math.ceil(Math.max(a.x, b.x, c.x)));
        const minY = Math.max(0, Math.floor(Math.min(a.y, b.y, c.y)));
        const maxY = Math.min(height - 1, Math.ceil(Math.max(a.y, b.y, c.y)));
        const color = tri.pixelColor;
        for (let y = minY; y <= maxY; y += 1) {
          const py = y + 0.5;
          for (let x = minX; x <= maxX; x += 1) {
            const px = x + 0.5;
            const w0 = ((b.y - c.y) * (px - c.x) + (c.x - b.x) * (py - c.y)) / denom;
            const w1 = ((c.y - a.y) * (px - c.x) + (a.x - c.x) * (py - c.y)) / denom;
            const w2 = 1 - w0 - w1;
            if (w0 < -1e-5 || w1 < -1e-5 || w2 < -1e-5) continue;
            const invZ = w0 / a.z + w1 / b.z + w2 / c.z;
            if (invZ <= 0) continue;
            const z = 1 / invZ;
            const index = y * width + x;
            if (z >= depthBuffer[index]) continue;
            if (tri.depthWrite) depthBuffer[index] = z;
            const offset = index * 4;
            pixels[offset] = color[0];
            pixels[offset + 1] = color[1];
            pixels[offset + 2] = color[2];
            pixels[offset + 3] = 255;
          }
        }
      }
      ctx.putImageData(image, 0, 0);
      // Transparent, non-solid, and overlay meshes are drawn after opaque geometry.
      for (const tri of overlays) {
        const [a, b, c] = tri.points;
        ctx.globalAlpha = tri.opacity;
        ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.lineTo(c.x, c.y); ctx.closePath();
        ctx.fillStyle = tri.color; ctx.fill();
        if (tri.wireframe) { ctx.strokeStyle = tri.wireColor; ctx.lineWidth = 1; ctx.stroke(); }
      }
      // Optional solid-object wireframes remain a visible authoring aid.
      for (const tri of triangles) {
        if (!tri.wireframe || !tri.solid) continue;
        const [a, b, c] = tri.points;
        ctx.globalAlpha = 1;
        ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.lineTo(c.x, c.y); ctx.closePath();
        ctx.strokeStyle = tri.wireColor; ctx.lineWidth = 1; ctx.stroke();
      }
    } else {
      for (const tri of triangles) {
        const [a, b, c] = tri.points;
        ctx.globalAlpha = tri.opacity;
        ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.lineTo(c.x, c.y); ctx.closePath();
        ctx.fillStyle = tri.color; ctx.fill();
        // Slight same-color edge coverage prevents antialias gaps between adjacent triangles.
        ctx.strokeStyle = tri.color; ctx.lineWidth = 1.05; ctx.lineJoin = 'round'; ctx.stroke();
        if (tri.wireframe) { ctx.strokeStyle = tri.wireColor; ctx.lineWidth = 1; ctx.stroke(); }
      }
    }
    ctx.globalAlpha = 1;
    ctx.restore();
    return { triangles: triangles.length, solidTriangles: solidCount, view: selectedView, projection: camera.projection, depthMode };
  }

  let editorView = 'three-quarter';
  const api = {
    version: VERSION,
    Scene, Camera, Geometry, Mesh, primitives,
    cube: primitives.cube, sphere: primitives.sphere, plane: primitives.plane,
    cylinder: primitives.cylinder, cone: primitives.cone, custom: primitives.custom,
    render,
    solidMaterial(color, extras) { return Object.assign({ color: color || '#8ea8c8', opacity: 1, solid: true, depthTest: true, depthWrite: true }, extras || {}); },
    clampFeetToGround(rootY, minFootOffset, groundY, clearance) { const gap = clearance === undefined ? 0.02 : Math.max(0, Number(clearance) || 0); return Math.max(Number(rootY) || 0, (Number(groundY) || 0) + gap - (Number(minFootOffset) || 0)); },
    setEditorView(name) { editorView = String(name || 'three-quarter'); },
    getEditorView() { return editorView; },
    views: ['front', 'back', 'left', 'right', 'top', 'bottom', 'three-quarter', 'isometric', 'free'],
    vec3: (x, y, z) => [Number(x) || 0, Number(y) || 0, Number(z) || 0],
    directionalLight: (direction, intensity, color) => ({ type: 'directional', direction: vec3(direction, [-0.5, 1, 0.5]), intensity: intensity === undefined ? 0.8 : Number(intensity), color: color || '#ffffff' }),
    ambientLight: (intensity, color) => ({ type: 'ambient', intensity: intensity === undefined ? 0.35 : Number(intensity), color: color || '#ffffff' })
  };
  root.FF3D = api;
})(typeof window !== 'undefined' ? window : globalThis);
