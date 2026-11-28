import * as THREE from 'three';

/*
  Underneath Everything — EP002 Three.js visual master
  Original conceptual reconstructions. No stock footage or stock stills.
  Not an exact model or recording of a proprietary ASML / ZEISS / Intel machine.
  Compatible with the supplied Offline Three.js MP4 Studio:
  exports mountScene(container, options) and returns seek(t), resize(w,h), pause(), dispose().
*/

const PALETTE = {
  red: 0xD62839, white: 0xFFFFFF, blue: 0x1746A2, navy: 0x102B52,
  dark: 0x061326, steel: 0x52677F, silver: 0xB8C8D9, cyan: 0x53CFFF,
  gold: 0xD5A74D, tin: 0xBAC8D6, orange: 0xFF7A35
};
const SECTION_WEIGHTS = [0.92, 0.98, 1.00, 0.98, 1.04, 1.02, 0.94, 0.96, 1.18, 0.98];
const SECTION_NAMES = [
  "THE FLASH", "A CHIP IN LAYERS", "WHY EUV", "TIN PLASMA",
  "MIRRORS & VACUUM", "PATTERN TO SILICON", "THE WAFER STAGE",
  "REPEATING THE PROCESS", "HIGH-NA EUV", "THE FACTORY ECOSYSTEM"
];

function mat(T, color, metalness, roughness, emissive, transparent, opacity) {
  return new T.MeshStandardMaterial({
    color: color,
    metalness: metalness === undefined ? 0.35 : metalness,
    roughness: roughness === undefined ? 0.32 : roughness,
    emissive: emissive || 0x000000,
    emissiveIntensity: emissive ? 1.8 : 0,
    transparent: !!transparent,
    opacity: opacity === undefined ? 1 : opacity
  });
}
function addBox(T, parent, name, pos, size, material, outlined) {
  var mesh = new T.Mesh(new T.BoxGeometry(size[0], size[1], size[2]), material);
  mesh.name = name;
  mesh.position.set(pos[0], pos[1], pos[2]);
  if (outlined) {
    var edges = new T.EdgesGeometry(mesh.geometry);
    mesh.add(new T.LineSegments(edges, new T.LineBasicMaterial({ color: 0x52749D, transparent: true, opacity: 0.72 })));
  }
  parent.add(mesh);
  return mesh;
}
function addSphere(T, parent, name, pos, radius, material, segments) {
  var mesh = new T.Mesh(new T.SphereGeometry(radius, segments || 32, segments || 24), material);
  mesh.name = name;
  mesh.position.set(pos[0], pos[1], pos[2]);
  parent.add(mesh);
  return mesh;
}
function addCylinder(T, parent, name, pos, radiusTop, radiusBottom, height, material, segments) {
  var mesh = new T.Mesh(new T.CylinderGeometry(radiusTop, radiusBottom, height, segments || 32), material);
  mesh.name = name;
  mesh.position.set(pos[0], pos[1], pos[2]);
  parent.add(mesh);
  return mesh;
}
function addBeam(T, parent, name, start, end, radius, material) {
  var a = new T.Vector3(start[0], start[1], start[2]);
  var b = new T.Vector3(end[0], end[1], end[2]);
  var direction = new T.Vector3().subVectors(b, a);
  var mesh = new T.Mesh(new T.CylinderGeometry(radius, radius, direction.length(), 16), material);
  mesh.name = name;
  mesh.position.copy(a).add(b).multiplyScalar(0.5);
  mesh.quaternion.setFromUnitVectors(new T.Vector3(0, 1, 0), direction.normalize());
  parent.add(mesh);
  return mesh;
}
function addLine(T, parent, name, points, color, opacity) {
  var geometry = new T.BufferGeometry().setFromPoints(points.map(function(p) {
    return new T.Vector3(p[0], p[1], p[2]);
  }));
  var line = new T.Line(geometry, new T.LineBasicMaterial({
    color: color, transparent: true, opacity: opacity === undefined ? 1 : opacity
  }));
  line.name = name;
  parent.add(line);
  return line;
}
function addRing(T, parent, name, pos, radius, tube, material, rotation) {
  var mesh = new T.Mesh(new T.TorusGeometry(radius, tube, 16, 96), material);
  mesh.name = name;
  mesh.position.set(pos[0], pos[1], pos[2]);
  if (rotation) mesh.rotation.set(rotation[0], rotation[1], rotation[2]);
  parent.add(mesh);
  return mesh;
}
function addLabel(T, parent, text, pos, scale) {
  var canvas = document.createElement("canvas");
  canvas.width = 1024;
  canvas.height = 220;
  var ctx = canvas.getContext("2d");
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = "rgba(16,43,82,0.92)";
  ctx.fillRect(0, 16, canvas.width, 188);
  ctx.fillStyle = "#D62839";
  ctx.fillRect(0, 16, 12, 188);
  ctx.fillStyle = "#FFFFFF";
  ctx.font = "700 58px Arial, sans-serif";
  ctx.textBaseline = "middle";
  ctx.fillText(text, 42, 110, 940);
  var texture = new T.CanvasTexture(canvas);
  texture.colorSpace = T.SRGBColorSpace;
  var material = new T.MeshBasicMaterial({ map: texture, transparent: true, side: T.DoubleSide, depthWrite: false });
  var mesh = new T.Mesh(new T.PlaneGeometry(scale || 3.8, (scale || 3.8) * 0.215), material);
  mesh.position.set(pos[0], pos[1], pos[2]);
  mesh.userData.texture = texture;
  parent.add(mesh);
  return mesh;
}
function pulsePoints(T, parent, count, color, radius) {
  var values = new Float32Array(count * 3);
  for (var i = 0; i < count; i++) {
    var a = i * 2.399963;
    var r = radius * (0.25 + ((i * 37) % 100) / 120);
    values[i * 3] = Math.cos(a) * r;
    values[i * 3 + 1] = Math.sin(a) * r;
    values[i * 3 + 2] = (((i * 19) % 100) / 100 - 0.5) * radius;
  }
  var geometry = new T.BufferGeometry();
  geometry.setAttribute("position", new T.BufferAttribute(values, 3));
  var material = new T.PointsMaterial({ color: color, size: 0.035, sizeAttenuation: true, transparent: true, opacity: 0.9 });
  var points = new T.Points(geometry, material);
  parent.add(points);
  return points;
}
function addStars(T, scene) {
  var values = new Float32Array(420 * 3);
  for (var i = 0; i < 420; i++) {
    values[i * 3] = (((i * 73) % 997) / 997 - 0.5) * 26;
    values[i * 3 + 1] = (((i * 127) % 991) / 991 - 0.5) * 15;
    values[i * 3 + 2] = -7 - ((i * 41) % 100) / 12;
  }
  var geometry = new T.BufferGeometry();
  geometry.setAttribute("position", new T.BufferAttribute(values, 3));
  scene.add(new T.Points(geometry, new T.PointsMaterial({ color: 0x7294C6, size: 0.018, transparent: true, opacity: 0.55 })));
}
function addChamber(T, group, width, depth) {
  var frameMat = mat(T, PALETTE.steel, 0.82, 0.28);
  var darkMat = mat(T, PALETTE.dark, 0.45, 0.42);
  addBox(T, group, "chamber floor", [0, -1.5, 0], [width, 0.12, depth], darkMat, true);
  addBox(T, group, "rear chamber wall", [0, 0.7, -depth / 2], [width, 4.5, 0.14], frameMat, true);
  [-width / 2, width / 2].forEach(function(x) {
    addBox(T, group, "chamber support", [x, 0, 0], [0.13, 3.2, depth], frameMat, true);
  });
  addRing(T, group, "inspection ring", [0, 0.15, 0], 1.6, 0.025,
    mat(T, PALETTE.blue, 0.3, 0.25, PALETTE.blue), [Math.PI / 2, 0, 0]);
}

/* 01 and 04 — two-pulse tin droplet / plasma source. */
function makeTinScene(T, detailed) {
  var g = new T.Group();
  addChamber(T, g, 9.5, 4.0);
  var silver = mat(T, PALETTE.tin, 0.92, 0.16);
  var redGlow = mat(T, PALETTE.red, 0.15, 0.2, PALETTE.red);
  var hot = mat(T, PALETTE.orange, 0.08, 0.18, PALETTE.orange);
  var cyan = mat(T, PALETTE.cyan, 0.25, 0.18, PALETTE.cyan);
  addLabel(T, g, detailed ? "TWO LASER PULSES · TIN PLASMA" : "A LASER STRIKES A TIN DROPLET", [-3.6, 2.0, 0.05], 4.2);
  var droplet = addSphere(T, g, "molten tin droplet", [-2.4, 0, 0.3], detailed ? 0.14 : 0.20, silver, 40);
  var prePulse = addBeam(T, g, "pre-pulse beam", [-2.8, -1.1, 1.1], [-1.9, 0, 0.3], 0.035, redGlow);
  var mainPulse = addBeam(T, g, "main laser pulse", [-1.1, -1.7, 1.15], [-0.25, 0, 0.35], 0.06, redGlow);
  var plasma = addSphere(T, g, "glowing tin plasma", [-0.1, 0, 0.35], 0.35, hot, 40);
  var halo = addRing(T, g, "plasma shock ring", [-0.1, 0, 0.35], 0.55, 0.025, hot, [0, Math.PI / 2, 0]);
  var collector = addRing(T, g, "collector mirror", [1.7, 0, 0.35], 1.1, 0.12,
    mat(T, PALETTE.gold, 0.9, 0.12), [0, Math.PI / 2, 0]);
  var euv = addBeam(T, g, "EUV radiation path", [0.1, 0, 0.35], [3.55, 0, 0.35], 0.025, cyan);
  var spark = pulsePoints(T, g, 65, PALETTE.orange, 1.15);
  addLabel(T, g, detailed ? "25 µm DROPLET · ~70 m/s · UP TO 50,000 Hz" : "CONCEPTUAL RECONSTRUCTION", [-2.7, -2.3, 0], 3.7);
  return {
    group: g,
    tick: function(p) {
      droplet.position.x = -2.45 + Math.min(1, p * 2.0) * 1.85;
      droplet.scale.setScalar(1 - 0.12 * Math.max(0, Math.min(1, (p - 0.16) * 3)));
      var strike = Math.max(0, 1 - Math.abs(p - 0.22) * 8);
      prePulse.visible = p < 0.34;
      mainPulse.visible = p > 0.18 && p < 0.48;
      plasma.scale.setScalar(0.15 + strike * (detailed ? 2.1 : 1.7) + Math.max(0, p - 0.3) * 0.7);
      plasma.material.emissiveIntensity = 0.5 + strike * 4;
      halo.scale.setScalar(0.2 + strike * 1.9 + p * 0.2);
      halo.rotation.z = p * Math.PI * 2;
      spark.visible = p > 0.18 && p < 0.86;
      spark.scale.setScalar(0.2 + strike * 2.0 + p * 0.35);
      euv.scale.x = Math.max(0.05, Math.min(1, (p - 0.27) * 5));
      collector.rotation.y = 0.18 * Math.sin(p * Math.PI * 2);
    }
  };
}

/* 02 — layered wafer and interconnect stack. */
function makeWaferScene(T) {
  var g = new T.Group();
  var waferMat = mat(T, 0x2A5C91, 0.88, 0.18);
  var silver = mat(T, PALETTE.silver, 0.8, 0.22);
  var copper = mat(T, PALETTE.gold, 0.82, 0.21);
  var dark = mat(T, PALETTE.navy, 0.68, 0.25);
  var stack = new T.Group();
  g.add(stack);
  var layers = [];
  for (var i = 0; i < 8; i++) {
    var z = -0.8 + i * 0.24;
    var disk = addCylinder(T, stack, "wafer layer " + i, [0, 0, z], 1.65, 1.65, 0.13, i % 2 ? silver : waferMat, 64);
    layers.push(disk);
    for (var j = -3; j <= 3; j++) {
      var trace = addBox(T, stack, "interconnect", [j * 0.36, 0, z + 0.09], [0.025, 2.65, 0.028], i % 2 ? copper : dark);
      trace.rotation.z = i * 0.09;
    }
  }
  for (var row = -3; row <= 3; row++) {
    for (var col = -3; col <= 3; col++) {
      var die = addBox(T, stack, "die pattern", [col * 0.42, row * 0.42, 1.15], [0.35, 0.35, 0.035], mat(T, 0x244B78, 0.65, 0.22));
      die.add(new T.LineSegments(new T.EdgesGeometry(die.geometry), new T.LineBasicMaterial({ color: PALETTE.cyan })));
    }
  }
  addLabel(T, g, "A PROCESSOR IS BUILT LAYER BY LAYER", [-3.1, 2.4, 0], 4.0);
  var rings = [];
  for (var r = 0; r < 3; r++) rings.push(addRing(T, g, "layer alignment reference", [0, 0, -0.55 + r * 0.5],
    1.83 + r * 0.11, 0.018, mat(T, PALETTE.cyan, 0.2, 0.2, PALETTE.cyan)));
  return {
    group: g,
    tick: function(p) {
      layers.forEach(function(layer, index) {
        var target = -0.8 + index * 0.24;
        layer.position.z = target + Math.sin(p * Math.PI * 2 + index * 0.23) * 0.09;
      });
      stack.rotation.z = p * Math.PI * 0.3;
      stack.rotation.x = 0.1 * Math.sin(p * Math.PI * 2);
      rings.forEach(function(ring, index) { ring.rotation.z = p * (index % 2 ? -1 : 1) * 0.8; });
    }
  };
}

/* 03 — compare the 193 nm DUV and 13.5 nm EUV wavelengths. */
function makeWavelengthScene(T) {
  var g = new T.Group();
  addBox(T, g, "optics table", [0, -1.35, 0], [9.2, 0.12, 3.0], mat(T, PALETTE.navy, 0.65, 0.3));
  var waves = [];
  [
    { y: 0.65, color: PALETTE.red, amp: 0.28, cycles: 5.0, label: "DUV · 193 nm" },
    { y: -0.55, color: PALETTE.cyan, amp: 0.16, cycles: 14.3, label: "EUV · 13.5 nm" }
  ].forEach(function(cfg) {
    var points = [];
    for (var i = 0; i <= 240; i++) {
      var x = -4.1 + i * 8.2 / 240;
      points.push([x, cfg.y + Math.sin(i / 240 * Math.PI * 2 * cfg.cycles) * cfg.amp, 0.2]);
    }
    var line = addLine(T, g, "wavelength waveform", points, cfg.color, 1);
    var pulse = addSphere(T, g, "travelling photon pulse", points[0], 0.10, mat(T, cfg.color, 0.15, 0.2, cfg.color), 24);
    addLabel(T, g, cfg.label, [-3.8, cfg.y + 0.5, 0], 2.6);
    waves.push({ points: points, pulse: pulse, line: line });
  });
  addLabel(T, g, "EUV WAVELENGTH IS ABOUT 14× SHORTER", [-2.5, 2.1, 0], 3.7);
  return {
    group: g,
    tick: function(p) {
      waves.forEach(function(w, index) {
        var at = Math.min(w.points.length - 1, Math.floor((p * 2.5 + index * 0.27) % 1 * (w.points.length - 1)));
        w.pulse.position.set(w.points[at][0], w.points[at][1], w.points[at][2] + 0.07);
        w.line.material.opacity = 0.72 + 0.25 * Math.sin(p * Math.PI * 2 + index);
      });
    }
  };
}

/* 05 — vacuum chamber and multilayer reflection path. */
function makeMirrorScene(T) {
  var g = new T.Group();
  addChamber(T, g, 9.5, 3.8);
  var mirrorMat = mat(T, PALETTE.silver, 0.98, 0.12);
  var gold = mat(T, PALETTE.gold, 0.95, 0.15);
  var cyan = mat(T, PALETTE.cyan, 0.15, 0.16, PALETTE.cyan);
  var mirrors = [];
  [-2.6, 0, 2.6].forEach(function(x, i) {
    var mirror = addBox(T, g, "multilayer mirror", [x, 0, 0.4], [1.55, 0.16, 1.05], mirrorMat, true);
    mirror.rotation.y = i === 1 ? -0.45 : 0.43;
    mirrors.push(mirror);
    for (var j = 0; j < 9; j++) {
      var layer = addBox(T, g, "thin reflective coating layer", [x, -0.095 - j * 0.018, 0.4],
        [1.48, 0.014, 0.98], j % 2 ? mirrorMat : gold);
      layer.rotation.y = mirror.rotation.y;
    }
  });
  var pts = [[-4.2, 0.3, 0.1], [-2.6, 0.4, 0.6], [0, 0.4, -0.25], [2.6, 0.4, 0.6], [4.25, 0.4, 0.05]];
  addLine(T, g, "conceptual reflected EUV path", pts, PALETTE.cyan, 0.38);
  var photon = addSphere(T, g, "EUV pulse", pts[0], 0.12, cyan, 24);
  pts.forEach(function(p) { addSphere(T, g, "path marker", p, 0.07, cyan, 16); });
  addLabel(T, g, "EUV IS ABSORBED BY AIR AND GLASS", [-3.2, 2.2, 0], 3.7);
  addLabel(T, g, "MULTILAYER MIRRORS · HIGH VACUUM", [-2.5, -2.3, 0], 3.4);
  return {
    group: g,
    tick: function(p) {
      var total = p * (pts.length - 1);
      var index = Math.min(pts.length - 2, Math.floor(total));
      var local = total - index;
      photon.position.set(
        T.MathUtils.lerp(pts[index][0], pts[index + 1][0], local),
        T.MathUtils.lerp(pts[index][1], pts[index + 1][1], local),
        T.MathUtils.lerp(pts[index][2], pts[index + 1][2], local)
      );
      mirrors.forEach(function(m, i) { m.rotation.y = (i === 1 ? -0.45 : 0.43) + Math.sin(p * Math.PI * 2 + i) * 0.025; });
    }
  };
}

/* 06 — reflective reticle, reduction optics and photoresist-coated wafer. */
function makeReticleScene(T) {
  var g = new T.Group();
  var gold = mat(T, PALETTE.gold, 0.88, 0.18);
  var dark = mat(T, PALETTE.navy, 0.58, 0.28);
  var cyan = mat(T, PALETTE.cyan, 0.1, 0.2, PALETTE.cyan);
  var wafer = mat(T, 0x2D6599, 0.88, 0.19);
  addBox(T, g, "reflective reticle", [-2.3, 0.8, 0], [2.1, 0.12, 1.7], gold, true);
  for (var i = -4; i <= 4; i++) {
    addBox(T, g, "reticle circuit pattern", [-2.3 + i * 0.2, 0.88, 0], [0.035, 0.018, 1.45], dark);
    addBox(T, g, "reticle horizontal pattern", [-2.3, 0.89, i * 0.16], [1.9, 0.02, 0.035], dark);
  }
  var lens = addRing(T, g, "reduction optics", [0.3, 0, 0], 0.72, 0.1, mat(T, PALETTE.silver, 0.92, 0.12), [Math.PI / 2, 0, 0]);
  var waferDisc = addCylinder(T, g, "photoresist-coated wafer", [2.8, -0.95, 0], 1.13, 1.13, 0.12, wafer, 64);
  var rays = [];
  for (var r = -4; r <= 4; r++) rays.push(addBeam(T, g, "projected pattern ray",
    [-2.2, 0.7, r * 0.13], [2.7, -0.88, r * 0.0325], 0.012, cyan));
  addLabel(T, g, "REFLECTIVE RETICLE → 4× REDUCTION → WAFER", [-3.9, 2.2, 0], 4.4);
  var pattern = new T.Group();
  g.add(pattern);
  for (var k = -5; k <= 5; k++) {
    addBox(T, pattern, "exposed resist line", [2.8 + k * 0.17, -0.875, k * 0.08], [0.025, 0.02, 0.95], cyan);
  }
  return {
    group: g,
    tick: function(p) {
      lens.rotation.z = p * Math.PI * 2;
      waferDisc.rotation.y = p * Math.PI * 1.4;
      pattern.position.z = 0.05 * Math.sin(p * Math.PI * 2);
      rays.forEach(function(ray, i) { ray.material.emissiveIntensity = 0.6 + 1.5 * (0.5 + 0.5 * Math.sin(p * 8 + i)); });
    }
  };
}

/* 07 — precision wafer stage and metrology feedback. */
function makeStageScene(T) {
  var g = new T.Group();
  var steel = mat(T, PALETTE.steel, 0.9, 0.2);
  var gold = mat(T, PALETTE.gold, 0.88, 0.18);
  var waferMat = mat(T, 0x2C679C, 0.9, 0.14);
  var cyan = mat(T, PALETTE.cyan, 0.15, 0.22, PALETTE.cyan);
  addCylinder(T, g, "precision stage base", [0, -0.55, 0], 2.2, 2.2, 0.52, steel, 64);
  addRing(T, g, "magnetic drive ring", [0, -0.18, 0], 1.78, 0.12, gold);
  var actuators = [];
  for (var i = 0; i < 8; i++) {
    var a = i / 8 * Math.PI * 2;
    var x = Math.cos(a) * 1.82;
    var z = Math.sin(a) * 1.82;
    actuators.push(addCylinder(T, g, "linear actuator", [x, 0.14, z], 0.12, 0.12, 0.82, steel, 24));
    addBeam(T, g, "metrology sensor beam", [x * 1.12, 0.65, z * 1.12], [x * 0.42, 1.12, z * 0.42], 0.012, cyan);
  }
  var platform = addCylinder(T, g, "moving wafer platform", [0, 0.46, 0], 1.55, 1.55, 0.22, steel, 64);
  var wafer = addCylinder(T, g, "silicon wafer", [0, 0.62, 0], 1.42, 1.42, 0.09, waferMat, 64);
  addLabel(T, g, "MEASURE · CORRECT · EXPOSE", [-2.8, 2.0, 0], 3.4);
  addLabel(T, g, "ILLUSTRATIVE PRECISION-STAGE MOTION", [-3.2, -1.8, 0], 3.6);
  return {
    group: g,
    tick: function(p) {
      platform.position.x = Math.sin(p * Math.PI * 4) * 0.22;
      platform.position.z = Math.cos(p * Math.PI * 4) * 0.18;
      platform.rotation.y = p * Math.PI * 2;
      wafer.position.x = platform.position.x;
      wafer.position.z = platform.position.z;
      wafer.rotation.y = -platform.rotation.y * 0.35;
      actuators.forEach(function(a, i) { a.scale.y = 0.84 + 0.18 * Math.sin(p * 8 + i); });
    }
  };
}

/* 08 — process sequence. */
function makeProcessScene(T) {
  var g = new T.Group();
  var steel = mat(T, PALETTE.steel, 0.78, 0.25);
  var gold = mat(T, PALETTE.gold, 0.75, 0.24);
  var cyan = mat(T, PALETTE.cyan, 0.1, 0.2, PALETTE.cyan);
  var names = ["DEPOSITION", "LITHOGRAPHY", "ETCH", "INSPECTION"];
  var machines = [];
  for (var i = 0; i < 4; i++) {
    var x = -3.3 + i * 2.2;
    var machine = addBox(T, g, "process tool", [x, 0.2, 0], [1.45, 2.05, 1.35], i % 2 ? gold : steel, true);
    addBox(T, g, "machine window", [x, 0.35, 0.69], [0.72, 0.7, 0.06],
      mat(T, PALETTE.navy, 0.25, 0.2, PALETTE.blue), true);
    addLabel(T, g, names[i], [x - 0.72, 1.6, 0.2], 1.5);
    addRing(T, g, "tool port", [x, -0.88, 0.7], 0.24, 0.035, cyan);
    machines.push(machine);
  }
  var wafer = addCylinder(T, g, "wafer travelling through process tools", [-4.45, -1.0, 0.6],
    0.43, 0.43, 0.08, mat(T, 0x2C679C, 0.9, 0.18), 48);
  var track = addLine(T, g, "process flow route", [[-4.4, -0.88, 0.6], [4.4, -0.88, 0.6]], PALETTE.cyan, 0.45);
  addLabel(T, g, "ONE WAFER · MANY DISTINCT PROCESS STEPS", [-3.5, 2.4, 0], 4.1);
  return {
    group: g,
    tick: function(p) {
      wafer.position.x = -4.4 + p * 8.8;
      wafer.rotation.z = p * Math.PI * 4;
      machines.forEach(function(m, i) { m.scale.y = 1 + 0.025 * Math.sin(p * 12 + i); });
      track.material.opacity = 0.35 + 0.25 * Math.sin(p * Math.PI * 2);
    }
  };
}

/* 09 — 0.33 vs 0.55 numerical-aperture cone comparison. */
function makeHighNAScene(T) {
  var g = new T.Group();
  var steel = mat(T, PALETTE.steel, 0.9, 0.18);
  var waferMat = mat(T, 0x286093, 0.86, 0.18);
  var red = mat(T, PALETTE.red, 0.1, 0.18, PALETTE.red);
  var cyan = mat(T, PALETTE.cyan, 0.1, 0.18, PALETTE.cyan);
  var sides = [-2.2, 2.2];
  var apertures = [0.72, 1.12];
  var raysBySide = [];
  for (var i = 0; i < 2; i++) {
    var x = sides[i], aperture = apertures[i], color = i ? cyan : red;
    addCylinder(T, g, "objective aperture", [x, 1.15, 0], aperture, aperture, 0.18, steel, 48);
    addRing(T, g, "numerical aperture ring", [x, 1.0, 0], aperture, 0.07, color);
    var rays = [];
    for (var j = 0; j < 20; j++) {
      var a = j / 20 * Math.PI * 2;
      var end = [x * 0.12 + Math.cos(a) * 0.38, -1.0, Math.sin(a) * 0.38];
      rays.push(addBeam(T, g, "optical ray",
        [x + Math.cos(a) * aperture, 1.0, Math.sin(a) * aperture], end, 0.012, color));
    }
    addCylinder(T, g, "exposure plane", [x * 0.12, -1.12, 0], 0.62, 0.62, 0.11, waferMat, 48);
    addLabel(T, g, i ? "HIGH-NA · 0.55" : "EUV · 0.33 NA", [x - 1.0, 2.0, 0], 2.4);
    raysBySide.push(rays);
  }
  addLabel(T, g, "A LARGER APERTURE GATHERS A WIDER CONE OF LIGHT", [-4.0, -2.25, 0], 4.7);
  return {
    group: g,
    tick: function(p) {
      raysBySide.forEach(function(rays, i) {
        rays.forEach(function(ray, j) {
          ray.material.opacity = 0.35 + 0.55 * (0.5 + 0.5 * Math.sin(p * 7 + j * 0.4 + i));
        });
      });
    }
  };
}

/* 10 — system ecosystem around the wafer. */
function makeEcosystemScene(T) {
  var g = new T.Group();
  var steel = mat(T, PALETTE.steel, 0.82, 0.22);
  var cyan = mat(T, PALETTE.cyan, 0.1, 0.2, PALETTE.cyan);
  var gold = mat(T, PALETTE.gold, 0.85, 0.2);
  var centre = addCylinder(T, g, "silicon wafer", [0, 0, 0], 1.05, 1.05, 0.12, mat(T, 0x2B6398, 0.9, 0.16), 64);
  var nodes = [];
  var labels = ["LASER SOURCE", "PRECISION OPTICS", "MOTION CONTROL", "SENSORS", "RESIST & MASK", "PROCESS TOOLS"];
  for (var i = 0; i < 6; i++) {
    var a = i / 6 * Math.PI * 2;
    var x = Math.cos(a) * 3.0;
    var z = Math.sin(a) * 2.2;
    var node = addBox(T, g, "ecosystem component", [x, 0.15, z], [1.05, 1.0, 0.75], i % 2 ? gold : steel, true);
    addBeam(T, g, "system interconnection", [x * 0.7, 0.05, z * 0.7],
      [Math.cos(a) * 0.9, 0, Math.sin(a) * 0.7], 0.026, cyan);
    addLabel(T, g, labels[i], [x - 0.9, 1.0, z], 1.8);
    nodes.push(node);
  }
  addRing(T, g, "integrated system orbit", [0, -0.05, 0], 2.05, 0.025, cyan, [Math.PI / 2, 0, 0]);
  addLabel(T, g, "ONE BREAKTHROUGH · AN ENTIRE ENGINEERING ECOSYSTEM", [-4.0, 2.5, 0], 4.8);
  return {
    group: g,
    tick: function(p) {
      g.rotation.y = p * Math.PI * 0.75;
      centre.rotation.y = -p * Math.PI * 3;
      nodes.forEach(function(node, i) {
        node.position.y = 0.12 + Math.sin(p * 8 + i) * 0.14;
        node.rotation.y = Math.sin(p * 5 + i) * 0.08;
      });
    }
  };
}

function createSceneForSection(T, index) {
  if (index === 0) return makeTinScene(T, false);
  if (index === 1) return makeWaferScene(T);
  if (index === 2) return makeWavelengthScene(T);
  if (index === 3) return makeTinScene(T, true);
  if (index === 4) return makeMirrorScene(T);
  if (index === 5) return makeReticleScene(T);
  if (index === 6) return makeStageScene(T);
  if (index === 7) return makeProcessScene(T);
  if (index === 8) return makeHighNAScene(T);
  return makeEcosystemScene(T);
}

export function mountScene(container, options) {
  var T = (options && options.THREE) || THREE;
  var width = (options && options.width) || 1280;
  var height = (options && options.height) || 720;
  var duration = (options && options.duration) || 699.25;
  var renderer = new T.WebGLRenderer({ antialias: true, alpha: false, powerPreference: "high-performance" });
  renderer.setPixelRatio(1);
  renderer.setSize(width, height, false);
  renderer.outputColorSpace = T.SRGBColorSpace;
  renderer.toneMapping = T.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.15;
  renderer.setClearColor(PALETTE.dark, 1);
  renderer.domElement.style.display = "block";
  container.innerHTML = "";
  container.appendChild(renderer.domElement);

  var scene = new T.Scene();
  scene.background = new T.Color(PALETTE.dark);
  scene.fog = new T.FogExp2(PALETTE.dark, 0.028);
  var camera = new T.PerspectiveCamera(38, width / height, 0.1, 100);
  camera.position.set(7.4, 4.7, 9.5);
  camera.lookAt(0, 0, 0);
  scene.add(new T.HemisphereLight(0xBCD8FF, 0x0A1426, 1.6));
  var key = new T.DirectionalLight(0xF4F8FF, 3.0);
  key.position.set(4, 7, 6);
  scene.add(key);
  var fill = new T.PointLight(PALETTE.blue, 28, 22);
  fill.position.set(-6, 1, -3);
  scene.add(fill);
  var rim = new T.PointLight(PALETTE.red, 13, 15);
  rim.position.set(5, 3, 1);
  scene.add(rim);
  addStars(T, scene);

  var sections = [];
  var totalWeight = SECTION_WEIGHTS.reduce(function(a, b) { return a + b; }, 0);
  var elapsed = 0;
  for (var i = 0; i < 10; i++) {
    var length = duration * SECTION_WEIGHTS[i] / totalWeight;
    var section = createSceneForSection(T, i);
    section.name = SECTION_NAMES[i];
    section.duration = length;
    section.start = elapsed;
    section.end = elapsed + length;
    section.group.visible = false;
    scene.add(section.group);
    sections.push(section);
    elapsed += length;
  }

  function resize(w, h) {
    width = w || width;
    height = h || height;
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
    renderer.setSize(width, height, false);
  }
  function seek(time) {
    var t = Math.max(0, Math.min(duration, Number(time) || 0));
    var currentIndex = 9;
    for (var i = 0; i < sections.length; i++) {
      if (t < sections[i].end || i === sections.length - 1) {
        currentIndex = i;
        break;
      }
    }
    sections.forEach(function(section, i) { section.group.visible = i === currentIndex; });
    var current = sections[currentIndex];
    var local = Math.max(0, Math.min(1, (t - current.start) / Math.max(0.001, current.duration)));
    current.tick(local, t);
    var orbit = local * Math.PI * 0.55;
    camera.position.set(7.8 + Math.sin(orbit) * 0.8, 4.6 + Math.sin(local * Math.PI) * 0.45, 9.6 + Math.cos(orbit) * 0.55);
    camera.lookAt(0, 0, 0);
    renderer.render(scene, camera);
  }
  seek(0);
  return {
    duration: duration,
    renderer: renderer,
    resize: resize,
    seek: seek,
    pause: function() {},
    dispose: function() {
      scene.traverse(function(object) {
        if (object.geometry && object.geometry.dispose) object.geometry.dispose();
        if (object.material) {
          var materials = Array.isArray(object.material) ? object.material : [object.material];
          materials.forEach(function(material) {
            if (material.map && material.map.dispose) material.map.dispose();
            if (material.dispose) material.dispose();
          });
        }
      });
      renderer.dispose();
      if (renderer.domElement.parentNode) renderer.domElement.parentNode.removeChild(renderer.domElement);
    }
  };
}
