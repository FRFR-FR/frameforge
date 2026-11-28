import * as THREE from 'three';

/*
  Underneath Everything — EP002 Three.js visual master
  Original conceptual reconstructions. No stock footage or stock stills.
  Rigged assemblies: pivots, bounded hinges/sliders, OBB SAT collision tests and travel-stop response.
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
  return new T.MeshPhysicalMaterial({
    color: color,
    metalness: metalness === undefined ? 0.42 : metalness,
    roughness: roughness === undefined ? 0.28 : roughness,
    clearcoat: metalness > 0.65 ? 0.42 : 0.16,
    clearcoatRoughness: 0.2,
    reflectivity: 0.72,
    emissive: emissive || 0x000000,
    emissiveIntensity: emissive ? 1.45 : 0,
    transparent: !!transparent,
    opacity: opacity === undefined ? 1 : opacity,
    side: transparent ? T.DoubleSide : T.FrontSide
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

function makePivot(T,parent,name,position){
  var rig=new T.Group(); rig.name=name;
  if(position)rig.position.set(position[0],position[1],position[2]);
  parent.add(rig); return rig;
}
function makeHinge(T,parent,name,position,axis,minAngle,maxAngle){
  var rig=makePivot(T,parent,name,position), key=axis||"z";
  var low=minAngle===undefined?-0.35:minAngle, high=maxAngle===undefined?0.35:maxAngle;
  return {rig:rig,set:function(v){rig.rotation[key]=T.MathUtils.clamp(v,low,high);},limits:[low,high]};
}
function makeSlider(T,parent,name,position,axis,minTravel,maxTravel){
  var rig=makePivot(T,parent,name,position), key=axis||"x", home=rig.position[key];
  var low=minTravel===undefined?-0.5:minTravel, high=maxTravel===undefined?0.5:maxTravel;
  return {rig:rig,set:function(v){rig.position[key]=home+T.MathUtils.clamp(v,low,high);},limits:[low,high],axis:key};
}
/* Oriented-box SAT collision checks; blocked motion is clamped to the last safe pose. */
function createCollisionWorld(T){
  var tests=0,blocked=0;
  function register(name,object,size){return {name:name,object:object,half:[size[0]/2,size[1]/2,size[2]/2]};}
  function box(body){
    var o=body.object, c=new T.Vector3(),q=new T.Quaternion(),sc=new T.Vector3();
    o.updateWorldMatrix(true,false);o.getWorldPosition(c);o.getWorldQuaternion(q);o.getWorldScale(sc);
    return {center:c,axes:[new T.Vector3(1,0,0).applyQuaternion(q),new T.Vector3(0,1,0).applyQuaternion(q),new T.Vector3(0,0,1).applyQuaternion(q)],
      half:[body.half[0]*Math.abs(sc.x),body.half[1]*Math.abs(sc.y),body.half[2]*Math.abs(sc.z)]};
  }
  function overlaps(A,B){
    tests++;var a=box(A),b=box(B),R=[[],[],[]],AR=[[],[],[]];
    for(var i=0;i<3;i++)for(var j=0;j<3;j++){R[i][j]=a.axes[i].dot(b.axes[j]);AR[i][j]=Math.abs(R[i][j])+1e-7;}
    var d=new T.Vector3().subVectors(b.center,a.center),t=[d.dot(a.axes[0]),d.dot(a.axes[1]),d.dot(a.axes[2])],ra,rb,v;
    for(var i=0;i<3;i++){ra=a.half[i];rb=b.half[0]*AR[i][0]+b.half[1]*AR[i][1]+b.half[2]*AR[i][2];if(Math.abs(t[i])>ra+rb)return false;}
    for(var j=0;j<3;j++){ra=a.half[0]*AR[0][j]+a.half[1]*AR[1][j]+a.half[2]*AR[2][j];rb=b.half[j];if(Math.abs(d.dot(b.axes[j]))>ra+rb)return false;}
    for(var i=0;i<3;i++)for(var j=0;j<3;j++){
      ra=a.half[(i+1)%3]*AR[(i+2)%3][j]+a.half[(i+2)%3]*AR[(i+1)%3][j];
      rb=b.half[(j+1)%3]*AR[i][(j+2)%3]+b.half[(j+2)%3]*AR[i][(j+1)%3];
      v=Math.abs(t[(i+2)%3]*R[(i+1)%3][j]-t[(i+1)%3]*R[(i+2)%3][j]);
      if(v>ra+rb)return false;
    }
    return true;
  }
  function move(body,target,obstacles,iterations){
    var obj=body.object,from=obj.position.clone(),to=target.clone(),n=iterations||18;
    obj.position.copy(to);obj.updateWorldMatrix(true,false);
    var hit=(obstacles||[]).some(function(o){return overlaps(body,o);});
    if(!hit)return {blocked:false,fraction:1,position:obj.position.clone()};
    blocked++;var lo=0,hi=1;
    for(var k=0;k<n;k++){
      var mid=(lo+hi)/2;obj.position.copy(from).lerp(to,mid);obj.updateWorldMatrix(true,false);
      var collision=(obstacles||[]).some(function(o){return overlaps(body,o);});
      if(collision)hi=mid;else lo=mid;
    }
    obj.position.copy(from).lerp(to,Math.max(0,lo-0.0005));obj.updateWorldMatrix(true,false);
    return {blocked:true,fraction:lo,position:obj.position.clone()};
  }
  return {register:register,overlaps:overlaps,move:move,report:function(){return {solver:"oriented-box SAT",overlapTests:tests,blockedMoves:blocked,status:"active"};}};
}
function addBoltCircle(T,parent,name,center,radius,count,boltRadius,material){
  var group=new T.Group();group.name=name;group.position.set(center[0],center[1],center[2]);parent.add(group);
  for(var i=0;i<count;i++){
    var a=i/count*Math.PI*2;
    var bolt=addCylinder(T,group,name+" fastener "+i,[Math.cos(a)*radius,0,Math.sin(a)*radius],boltRadius,boltRadius,0.055,material,12);
    bolt.rotation.x=Math.PI/2;
  }
  return group;
}
function addPulseBeam(T,parent,name,start,end,radius,material){
  var a=new T.Vector3(start[0],start[1],start[2]),b=new T.Vector3(end[0],end[1],end[2]);
  var d=new T.Vector3().subVectors(b,a),length=d.length(),rig=makePivot(T,parent,name,start);
  rig.quaternion.setFromUnitVectors(new T.Vector3(0,1,0),d.normalize());
  var beam=new T.Mesh(new T.CylinderGeometry(radius,radius,length,24,1,false),material);
  beam.position.y=length*0.5;beam.scale.y=0.001;rig.add(beam);
  return {rig:rig,beam:beam,length:length,setProgress:function(p){
    var q=T.MathUtils.clamp(p,0,1);beam.scale.y=Math.max(0.001,q);beam.position.y=length*q*0.5;beam.visible=q>0.005;
  }};
}
function addParabolicReflector(T,parent,name,radius,depth,material){
  var positions=[],indices=[],radial=40,around=96;
  for(var i=0;i<=radial;i++){
    var r=radius*i/radial,x=depth*(r/radius)*(r/radius);
    for(var j=0;j<=around;j++){var a=j/around*Math.PI*2;positions.push(x,r*Math.cos(a),r*Math.sin(a));}
  }
  for(var i=0;i<radial;i++)for(var j=0;j<around;j++){
    var n=i*(around+1)+j,m=n+around+1;indices.push(n,m,n+1,n+1,m,m+1);
  }
  var geo=new T.BufferGeometry();geo.setAttribute("position",new T.Float32BufferAttribute(positions,3));geo.setIndex(indices);geo.computeVertexNormals();
  var mesh=new T.Mesh(geo,material);mesh.name=name;mesh.castShadow=true;mesh.receiveShadow=true;parent.add(mesh);return mesh;
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
/* 01 and 04 — articulated two-pulse tin-droplet source, a conceptual engineering reconstruction. */
function makeTinScene(T,detailed){
  var g=new T.Group();g.name=detailed?"EUV SOURCE ASSEMBLY — MACRO":"EUV SOURCE ASSEMBLY — OVERVIEW";
  var steel=mat(T,0x78899A,0.92,0.22),brushed=mat(T,0xB4C0CA,0.86,0.20),titanium=mat(T,0x596B7C,0.88,0.25);
  var ceramic=mat(T,0xD9E0E5,0.2,0.28),black=mat(T,0x101923,0.48,0.42);
  var glass=mat(T,0x6C99BA,0.22,0.12,0x071B30,true,0.2);
  var gold=mat(T,0xC3A16A,0.9,0.19),tin=mat(T,0xD2DCE5,0.94,0.13);
  var hot=mat(T,0xFFB35C,0.08,0.16,0xFF6A28),cyan=mat(T,PALETTE.cyan,0.12,0.15,0x53CFFF);
  // Machined vacuum vessel, flanges, seals, service skid and inspection window.
  var vessel=addCylinder(T,g,"vacuum vessel",[0,0,0],1.62,1.62,6.9,black,72);vessel.rotation.z=Math.PI/2;
  [-3.46,3.46].forEach(function(x){
    var flange=addCylinder(T,g,"vacuum vessel end flange",[x,0,0],1.78,1.78,0.22,brushed,72);flange.rotation.z=Math.PI/2;
    addRing(T,g,"flange seal",[x+(x<0?-0.12:0.12),0,0],1.7,0.045,black,[0,Math.PI/2,0]);
    addBoltCircle(T,g,"flange bolt circle",[x,0,0],1.55,20,0.055,steel);
  });
  addBox(T,g,"lower vacuum skid",[0,-1.96,0],[8.2,0.26,4.1],black,true);
  addBox(T,g,"upper equipment bridge",[0,2.0,-1.55],[7.8,0.18,1.15],steel,true);
  [-3.7,3.7].forEach(function(x){
    addBox(T,g,"vessel pedestal",[x,-1.42,0],[0.32,1.0,0.58],titanium,true);
    addBox(T,g,"pedestal foot",[x,-1.91,0],[0.78,0.12,0.95],brushed,true);
  });
  addRing(T,g,"inspection viewport bezel",[0,0,1.54],1.08,0.12,brushed,[Math.PI/2,0,0]);
  var viewport=addCylinder(T,g,"inspection viewport glass",[0,0,1.52],0.94,0.94,0.045,glass,64);viewport.rotation.x=Math.PI/2;
  addBoltCircle(T,g,"viewport fasteners",[0,0,1.61],1.04,12,0.035,steel);

  // Droplet generator with a piezoelectric sleeve and replaceable ceramic orifice.
  var nozzleRig=makePivot(T,g,"DROPLET GENERATOR RIG",[0,1.52,0]);
  addCylinder(T,nozzleRig,"tin feed tube",[0,0.35,0],0.18,0.18,0.82,steel,40);
  addCylinder(T,nozzleRig,"piezoelectric actuator sleeve",[0,-0.05,0],0.29,0.29,0.40,gold,48);
  addCylinder(T,nozzleRig,"ceramic droplet nozzle",[0,-0.43,0],0.14,0.055,0.46,ceramic,48);
  addRing(T,nozzleRig,"nozzle orifice rim",[0,-0.67,0],0.085,0.022,brushed);
  addRing(T,nozzleRig,"piezo clamp",[0,0.10,0],0.31,0.035,steel);
  addBox(T,g,"generator service bracket",[0,0.75,-0.62],[0.76,0.48,0.38],titanium,true);
  addBoltCircle(T,g,"generator bracket fasteners",[0,0.74,-0.40],0.27,8,0.035,brushed);

  // Two separately articulated laser heads with yaw and pitch pivots.
  function laserHead(name,position,tilt){
    var base=makePivot(T,g,name+" BASE",position);
    addBox(T,base,name+" isolation foot",[0,-0.46,0],[1.35,0.22,1.1],titanium,true);
    var yaw=makeHinge(T,base,name+" YAW BEARING",[0,0,0],"y",-0.08,0.08);
    var pitch=makeHinge(T,yaw.rig,name+" PITCH BEARING",[0,0.18,0],"z",-0.12,0.12);
    var barrel=makePivot(T,pitch.rig,name+" LASER BARREL",[0.35,0,0]);
    var body=addCylinder(T,barrel,name+" machined optical barrel",[0,0,0],0.34,0.34,1.12,steel,48);body.rotation.z=Math.PI/2;
    addRing(T,barrel,name+" focusing collar",[0.56,0,0],0.30,0.055,gold,[0,Math.PI/2,0]);
    var optic=addCylinder(T,barrel,name+" fused silica window",[0.62,0,0],0.23,0.23,0.055,glass,40);optic.rotation.z=Math.PI/2;
    addRing(T,barrel,name+" beam aperture",[0.69,0,0],0.24,0.035,brushed,[0,Math.PI/2,0]);
    addBox(T,base,name+" gimbal saddle",[0.22,0.06,0],[0.98,0.22,0.82],black,true);
    addBoltCircle(T,base,name+" saddle fasteners",[0.22,-0.08,0],0.40,8,0.028,brushed);
    yaw.set(tilt*0.22);pitch.set(tilt);
    return {base:base,yaw:yaw,pitch:pitch,barrel:barrel};
  }
  var preHead=laserHead("PRE-PULSE LASER",[-2.9,-0.48,0.63],-0.025);
  var mainHead=laserHead("MAIN PULSE LASER",[-2.9,0.20,-0.62],-0.025);
  preHead.base.scale.setScalar(0.76);mainHead.base.scale.setScalar(0.92);
  addBox(T,g,"laser head alignment rail",[-2.92,-1.20,0],[1.1,0.18,2.2],titanium,true);
  addBox(T,g,"laser service manifold",[-3.42,-0.20,0],[0.18,1.55,2.1],steel,true);
  for(var h=0;h<5;h++)addBeam(T,g,"laser coolant line",[-3.38,-0.65+h*0.18,-0.92],[-2.85,-0.65+h*0.18,-0.92],0.035,h%2?gold:titanium);

  var dropletRig=makePivot(T,g,"TIN DROPLET CARRIER",[0,0.46,0]);
  var droplet=addSphere(T,dropletRig,"molten tin droplet",[0,0,0],0.125,tin,48);
  var dropProxy=makePivot(T,g,"TIN DROPLET COLLISION PROXY",[0,0.46,0]);
  var collision=createCollisionWorld(T);
  var dropletBody=collision.register("tin droplet",dropProxy,[0.25,0.25,0.25]);
  var nozzleBody=collision.register("nozzle envelope",nozzleRig,[0.34,0.34,0.34]);

  // Concave parabolic collector mounted on a bounded tip/tilt joint.
  var collectorBase=makePivot(T,g,"COLLECTOR MIRROR MOUNT",[1.82,-0.10,0]);
  addCylinder(T,collectorBase,"collector mount pedestal",[0,-0.94,0],0.32,0.40,0.58,titanium,40);
  addRing(T,collectorBase,"collector alignment ring",[0,0,0],1.22,0.085,gold,[0,Math.PI/2,0]);
  var collectorTilt=makeHinge(T,collectorBase,"COLLECTOR TIP/TILT JOINT",[0,0,0],"y",-0.035,0.035);
  addParabolicReflector(T,collectorTilt.rig,"parabolic collector mirror — conceptual",[0.99][0]||1.05,0.62,mat(T,0xD7C5A4,0.96,0.09));
  addRing(T,collectorTilt.rig,"collector mirror retaining rim",[0,0,0],1.07,0.045,brushed,[0,Math.PI/2,0]);
  [-0.7,0,0.7].forEach(function(z){addBeam(T,collectorTilt.rig,"collector kinematic support",[0.14,-0.05,z],[0.40,-0.78,z],0.055,titanium);});
  for(var bolt=0;bolt<16;bolt++){
    var a=bolt/16*Math.PI*2;
    addSphere(T,collectorTilt.rig,"collector retaining screw",[0.02,1.12*Math.cos(a),1.12*Math.sin(a)],0.035,steel,12);
  }
  var plasmaRig=makePivot(T,g,"PLASMA EXPANSION RIG",[0,-0.34,0]);
  var plasma=addSphere(T,plasmaRig,"ionized tin plasma",[0,0,0],0.28,hot,48);
  var halo=addRing(T,plasmaRig,"plasma emission shell",[0,0,0],0.55,0.025,hot,[Math.PI/2,0,0]);
  var spark=pulsePoints(T,plasmaRig,150,0xFF9A4A,1.35);
  var rays=[];
  for(var k=0;k<13;k++){
    var a=k/12*Math.PI*0.56-Math.PI*0.28;
    rays.push(addPulseBeam(T,g,"EUV collector output ray "+k,[0.10,0,0.05],[3.45,Math.sin(a)*0.95,Math.cos(a)*0.95],0.012,cyan));
  }
  addRing(T,g,"EUV output aperture",[3.35,0.02,0],0.58,0.07,brushed,[0,Math.PI/2,0]);
  addBox(T,g,"source support chassis",[0,-2.22,0],[8.1,0.16,4.4],black,true);
  addLabel(T,g,detailed?"TWO-PULSE LASER-PRODUCED TIN PLASMA":"EUV SOURCE · CONCEPTUAL RECONSTRUCTION",[-3.5,2.28,0.2],4.3);

  return {
    group:g,collisionSystem:collision,
    tick:function(p){
      var fall=T.MathUtils.smoothstep(p,0.03,0.35),dropY=0.46-1.12*fall;
      dropletRig.position.y=dropY;dropProxy.position.y=dropY;
      droplet.rotation.z=0.24*Math.sin(p*8);
      var pre=T.MathUtils.smoothstep(p,0.15,0.24)*(1-T.MathUtils.smoothstep(p,0.27,0.34));
      var main=T.MathUtils.smoothstep(p,0.40,0.50)*(1-T.MathUtils.smoothstep(p,0.52,0.60));
      var post=T.MathUtils.smoothstep(p,0.51,0.78);
      preHead.pitch.set(-0.025+0.012*Math.sin(p*4));mainHead.pitch.set(-0.025+0.012*Math.sin(p*4+0.7));
      if(pre>0.02)droplet.scale.set(1+0.55*pre,1-0.68*pre,1+0.28*pre);
      else if(main>0.02)droplet.scale.set(1+0.75*main,1-0.55*main,1+0.45*main);
      else if(post>0.01)droplet.scale.setScalar(Math.max(0.015,1-post));
      else droplet.scale.setScalar(1);
      plasma.scale.setScalar(0.001+post*(0.55+1.55*Math.sin(Math.PI*T.MathUtils.clamp((p-0.50)/0.29,0,1))));
      plasma.material.emissiveIntensity=0.5+post*4.2;
      halo.scale.setScalar(0.001+post*2.0);halo.rotation.x=p*2.7;halo.rotation.z=-p*3.2;
      spark.visible=post>0.015;spark.scale.setScalar(0.001+post*1.25);
      rays.forEach(function(ray,i){ray.setProgress(T.MathUtils.clamp((p-0.66-i*0.004)*7,0,1));});
      collectorTilt.set(0.012*Math.sin(p*Math.PI*2));
      // If an animated target ever enters the nozzle envelope, clamp it before penetration.
      if(collision.overlaps(dropletBody,nozzleBody)){
        dropletRig.position.y=Math.min(dropletRig.position.y,nozzleRig.position.y-0.40);
        dropProxy.position.y=dropletRig.position.y;
      }
    }
  };
}

/* 02 — layered wafer and interconnect stack. */
/* 02 — precision wafer stack with rigid layer carriers and metrology alignment hardware. */
function makeWaferScene(T){
  var g=new T.Group();
  var silicon=mat(T,0x425C72,0.84,0.19),dielectric=mat(T,0xD7DFE6,0.18,0.23);
  var copper=mat(T,0xB87945,0.91,0.18),interposer=mat(T,0x274A69,0.78,0.22),frame=mat(T,0x66798A,0.88,0.24);
  var waferRig=makePivot(T,g,"SILICON WAFER CARRIER",[0,-0.95,0]);
  addCylinder(T,waferRig,"300 mm silicon substrate",[0,0,0],1.7,1.7,0.13,silicon,96);
  addRing(T,waferRig,"wafer bevel edge",[0,0.075,0],1.67,0.035,mat(T,0xAFC0CE,0.88,0.15));
  var layers=[];
  for(var i=0;i<9;i++){
    var carrier=makePivot(T,g,"INTERCONNECT LAYER RIG "+i,[0,-0.68+i*0.19,0]);
    var layerMat=i%3===0?dielectric:(i%3===1?copper:interposer);
    addCylinder(T,carrier,"fabricated interconnect layer "+i,[0,0,0],1.53,1.53,0.065,layerMat,80);
    for(var j=-6;j<=6;j++){
      var trace=addBox(T,carrier,"copper interconnect trace",[j*0.22,0.046,0],[0.018,0.012,2.56],i%2?copper:frame);
      trace.rotation.y=(i%2?1:-1)*0.12;
      addBox(T,carrier,"cross-layer via trace",[0,0.047,j*0.20],[2.45,0.012,0.016],copper);
    }
    var proxy=makePivot(T,carrier,"LAYER COLLISION ENVELOPE",[0,0.07,0]);
    layers.push({carrier:carrier,proxy:proxy,base:-0.68+i*0.19});
  }
  var alignFrame=makePivot(T,g,"WAFER ALIGNMENT FRAME",[0,-0.05,0]);
  var posts=[];
  for(var k=0;k<4;k++){
    var a=k*Math.PI/2+Math.PI/4,x=Math.cos(a)*1.88,z=Math.sin(a)*1.88;
    posts.push(addCylinder(T,alignFrame,"ceramic alignment post",[x,0,z],0.055,0.055,1.8,dielectric,24));
    addRing(T,alignFrame,"alignment post collar",[x,0.48,z],0.09,0.025,copper);
  }
  var metrology=makePivot(T,g,"THREE-POINT METROLOGY FRAME",[0,1.25,0]);
  for(var m=0;m<3;m++){
    var angle=m/3*Math.PI*2;
    addBeam(T,metrology,"metrology probe arm",[0,0.16,0],[Math.cos(angle)*1.8,0.05,Math.sin(angle)*1.8],0.04,frame);
    addSphere(T,metrology,"laser displacement sensor",[Math.cos(angle)*1.8,0.05,Math.sin(angle)*1.8],0.105,mat(T,0x344C63,0.82,0.18),24);
  }
  addLabel(T,g,"SILICON · DIELECTRIC · COPPER · VIA",[-3.3,2.35,0],3.9);
  var collision=createCollisionWorld(T);
  var bodies=layers.map(function(layer,index){return collision.register("interconnect layer "+index,layer.proxy,[3.08,0.12,3.08]);});
  return {group:g,collisionSystem:collision,tick:function(p){
    layers.forEach(function(layer,index){
      var pulse=Math.sin(p*Math.PI*2+index*0.31)*0.008;
      layer.carrier.position.y=layer.base+(p>0.28&&p<0.78?(index-4)*0.01:0)+pulse;
    });
    waferRig.rotation.y=0.04*Math.sin(p*Math.PI*2);metrology.rotation.y=0.03*Math.sin(p*Math.PI*2);
    posts.forEach(function(post,index){post.rotation.z=0.004*Math.sin(p*5+index);});
    for(var q=0;q<bodies.length-1;q++){
      if(collision.overlaps(bodies[q],bodies[q+1])){
        layers[q+1].carrier.position.y=layers[q].carrier.position.y+0.20;
      }
    }
  }};
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
