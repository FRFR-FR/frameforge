// 30-second FrameForge mechanical-watch explainer. No captions or labels.
export const meta = { wps: 2.7 };

export function setup(E) {
  const {PAL, box, cyl, sph, tor, grp, add, spin, anim} = E;
  const S = E.state;

  // Minimal studio bench: one clean blue surface, timber lip and empty sage backdrop.
  add(box(34,.35,22,PAL.tile,{y:-.68,outline:false}));
  add(box(34,.34,.45,PAL.wood,{y:-.71,z:11.1,outline:false}));
  add(box(80,.18,70,PAL.floor,{y:-1.25,z:-8,outline:false}));

  S.watch = grp(); add(S.watch);
  const W = S.watch;
  W.add(cyl(3.16,.62,PAL.grey,{y:.22}));
  W.add(tor(3.08,.14,PAL.gold,{y:.54,rx:Math.PI/2}));
  W.add(tor(2.91,.08,PAL.white,{y:.59,rx:Math.PI/2}));
  W.add(cyl(2.78,.12,PAL.dark,{y:.56}));

  // Grooved winding crown on the right side.
  S.crown = grp(); S.crown.position.set(3.12,.23,0); W.add(S.crown);
  S.crown.add(cyl(.30,.72,PAL.white,{rz:Math.PI/2}));
  for(let i=0;i<7;i++) S.crown.add(cyl(.325,.045,PAL.gold,{z:(i-3)*.085,rz:Math.PI/2,outline:false}));

  // Articulated strap, aligned as a single clear silhouette.
  S.strap = grp(); W.add(S.strap);
  for(const side of [-1,1]) {
    for(let i=0;i<8;i++) {
      const z=side*(3.25+i*.48);
      S.strap.add(box(1.52,.23,.43,PAL.blue,{y:-.06,z,outline:false}));
      S.strap.add(box(1.30,.035,.025,PAL.wood,{y:.065,z:z+side*.145,outline:false}));
      S.strap.add(box(1.30,.035,.025,PAL.wood,{y:.065,z:z-side*.145,outline:false}));
      for(const x of [-.55,.55]) S.strap.add(sph(.045,PAL.gold,{x,y:.08,z,outline:false}));
    }
  }
  S.strap.add(box(1.32,.18,.52,PAL.gold,{y:-.015,z:7.05,outline:false}));

  // Movement plate, mainspring barrel and visible nested coils.
  S.movement=grp(); S.movement.position.y=.63; W.add(S.movement);
  S.movement.add(cyl(2.76,.10,PAL.grey,{outline:false}));
  S.movement.add(tor(2.53,.035,PAL.gold,{y:.065,rx:Math.PI/2,outline:false}));
  S.barrel=grp(); S.barrel.position.set(-1.25,.14,-.55); S.movement.add(S.barrel);
  S.barrel.add(cyl(.99,.18,PAL.dark));
  S.barrel.add(tor(.92,.085,PAL.gold,{y:.11,rx:Math.PI/2}));
  S.barrel.add(cyl(.16,.23,PAL.gold,{y:.02}));
  S.spring=grp(); S.barrel.add(S.spring);
  for(let i=0;i<5;i++) S.spring.add(tor(.34+i*.105,.028,PAL.copper,{y:.145+i*.002,rx:Math.PI/2,outline:false}));

  function gear(r,teeth,color,x,z,y,rim=PAL.gold) {
    const g=grp(); g.position.set(x,y,z);
    g.add(cyl(r*.72,.13,color,{outline:false}));
    g.add(tor(r*.61,.055,rim,{y:.08,rx:Math.PI/2,outline:false}));
    g.add(cyl(r*.23,.19,PAL.white,{outline:false}));
    for(let k=0;k<4;k++) {
      const a=k*Math.PI/2;
      g.add(box(.10,.065,r*1.13,color,{x:Math.sin(a)*r*.38,y:.075,z:Math.cos(a)*r*.38,ry:a,outline:false}));
    }
    for(let i=0;i<teeth;i++) {
      const a=i*Math.PI*2/teeth;
      g.add(box(r*.28,.12,r*.28,color,{x:Math.sin(a)*r*.85,y:.005,z:Math.cos(a)*r*.85,ry:a,outline:false}));
    }
    add(g); return g;
  }
  S.center=gear(.70,18,PAL.gold,.10,-.76,.81,PAL.white);
  S.third=gear(.48,16,PAL.white,1.25,-.65,.83,PAL.gold);
  S.fourth=gear(.42,14,PAL.gold,1.40,.62,.84,PAL.white);
  S.escape=gear(.34,12,PAL.copper,.53,1.56,.86,PAL.ruby);

  // Regulating escapement: fork with two ruby pallet stones.
  S.anchor=grp(); S.anchor.position.set(.67,.98,1.18); S.movement.add(S.anchor);
  S.anchor.add(box(.13,.09,.92,PAL.white,{rz:.42,outline:false}));
  S.anchor.add(box(.48,.08,.13,PAL.grey,{x:.27,z:-.32,ry:-.18,outline:false}));
  S.anchor.add(box(.48,.08,.13,PAL.grey,{x:-.27,z:.32,ry:.18,outline:false}));
  S.anchor.add(box(.25,.09,.13,PAL.ruby,{x:.50,z:-.53,ry:-.15,outline:false}));
  S.anchor.add(box(.25,.09,.13,PAL.ruby,{x:-.50,z:.53,ry:.15,outline:false}));
  S.anchor.add(cyl(.16,.13,PAL.gold,{y:.05,outline:false}));

  // Balance wheel and fine hairspring.
  S.balance=grp(); S.balance.position.set(-1.23,1.0,1.48); S.movement.add(S.balance);
  S.balance.add(tor(.72,.095,PAL.white,{rx:Math.PI/2}));
  S.balance.add(tor(.56,.045,PAL.gold,{y:.03,rx:Math.PI/2,outline:false}));
  S.balance.add(cyl(.14,.20,PAL.gold,{outline:false}));
  for(let i=0;i<4;i++) {
    const a=i*Math.PI/2;
    S.balance.add(box(.10,.075,1.27,PAL.white,{x:Math.sin(a)*.05,y:.04,z:Math.cos(a)*.05,ry:a,outline:false}));
    S.balance.add(box(.26,.12,.18,PAL.gold,{x:Math.sin(a)*.62,y:.04,z:Math.cos(a)*.62,ry:a,outline:false}));
  }
  const hairPts=[];
  for(let i=0;i<=120;i++){const p=i/120,a=p*Math.PI*7.3,r=.09+p*.49;hairPts.push([Math.cos(a)*r,.08,Math.sin(a)*r]);}
  // A fine stylised coil built from short linked metal segments (no text or callouts).
  for(let i=0;i<hairPts.length-1;i++){
    const a=hairPts[i],b=hairPts[i+1],dx=b[0]-a[0],dz=b[2]-a[2],len=Math.hypot(dx,dz);
    S.balance.add(box(.027,.023,len,PAL.copper,{x:(a[0]+b[0])/2,y:.08,z:(a[2]+b[2])/2,ry:Math.atan2(dx,dz),outline:false}));
  }

  // Dial assembly, hands and crystal lift together to reveal the mechanism.
  S.face=grp(); W.add(S.face);
  S.face.add(cyl(2.75,.13,PAL.white,{y:.77}));
  S.face.add(tor(2.69,.035,PAL.gold,{y:.86,rx:Math.PI/2,outline:false}));
  for(let i=0;i<60;i++){
    const a=i*Math.PI/30,r=2.43,major=i%5===0;
    S.face.add(box(major?.105:.045,.045,major?.31:.16,major?PAL.dark:PAL.grey,{x:Math.sin(a)*r,y:.88,z:Math.cos(a)*r,ry:a,outline:false}));
  }
  for(let i=0;i<12;i++){
    const a=i*Math.PI/6,r=2.12;
    S.face.add(box(.15,.075,.38,PAL.gold,{x:Math.sin(a)*r,y:.90,z:Math.cos(a)*r,ry:a,outline:false}));
  }
  S.hands=grp(); S.hands.position.set(0,.97,0); S.face.add(S.hands);
  S.hour=grp(); S.hands.add(S.hour);
  S.hour.add(box(.17,.055,1.20,PAL.dark,{z:-.55,outline:false}));
  S.hour.add(sph(.09,PAL.gold,{y:.035,z:-1.05,outline:false}));
  S.minute=grp(); S.hands.add(S.minute);
  S.minute.add(box(.11,.045,1.85,PAL.blue,{y:.015,z:-.86,outline:false}));
  S.minute.add(sph(.06,PAL.gold,{y:.045,z:-1.73,outline:false}));
  S.second=grp(); S.hands.add(S.second);
  S.second.add(box(.038,.034,2.28,PAL.red,{y:.045,z:-1.08,outline:false}));
  S.second.add(box(.13,.035,.26,PAL.red,{y:.045,z:.17,outline:false}));
  S.second.add(sph(.07,PAL.gold,{y:.055,outline:false}));
  const glass = new E.THREE.Mesh(new E.THREE.CylinderGeometry(2.80,2.80,.035,64),new E.THREE.MeshPhysicalMaterial({color:0xffffff,transparent:true,opacity:.12,roughness:.08,metalness:.04,clearcoat:1,depthWrite:false}));
  glass.position.y=1.10; S.face.add(glass);
  S.face.add(tor(2.82,.026,PAL.white,{y:1.115,rx:Math.PI/2,outline:false}));

  // Deterministic, one-owner animation curves: no competing transforms.
  anim(0,30,(p,t)=>{
    const up=p=>{p=Math.max(0,Math.min(1,p));return p*p*(3-2*p);};
    const lift=up((t-3.1)/2.35)*(1-up((t-24.1)/2.55));
    S.face.position.y=lift*2.85;
    S.face.rotation.x=lift*.035;
    W.rotation.y=.045*Math.sin(t*.5)+.10*up((t-26)/3.6);
    W.rotation.x=.025*Math.sin(t*.45);
    S.crown.rotation.x=t<4.5?t*1.75:7.875+Math.sin(t*.8)*.035;
    S.spring.rotation.y=-t*.42;
    S.barrel.rotation.y=t*.07;
    S.escape.rotation.y=-(Math.floor(t*4)+up((t*4)%1))*Math.PI*2/12;
    S.anchor.rotation.y=Math.sin(t*Math.PI*2*4)*.23;
    S.balance.rotation.y=Math.sin(t*Math.PI*2*4+.28)*.29;
    S.balance.rotation.z=Math.sin(t*Math.PI*2*4+.28)*.055;
    S.hour.rotation.y=-t*.0105;
    S.minute.rotation.y=-t*.085;
    S.second.rotation.y=-t*Math.PI*2/9.8;
    S.strap.rotation.x=.006*Math.sin(t*.65);
  },'lin');
  E.spin(S.center,'y',-.20);
  E.spin(S.third,'y',.29);
  E.spin(S.fourth,'y',-.34);
}

export const beats = [
  {say:"A mechanical watch turns one wound spring into every second.",pause:-.12,cam:{p:[8.5,11.5,15],l:[0,.75,0],fov:49}},
  {say:"Inside, a steel mainspring stores energy, not electricity.",pause:-.12,cam:{p:[5.6,8.4,11.5],l:[0,.82,0],fov:47}},
  {say:"Tiny gears carry that power forward without a battery.",pause:.24,cam:{p:[1.1,7.2,8.2],l:[0,.85,0],fov:45}},
  {say:"Like and subscribe for more tiny engineering.",pause:-.12,cam:{p:[-1,4.7,5.7],l:[-1.1,.82,-.5],fov:41}},
  {say:"At the center, an escapement releases one tooth at a time.",pause:-.12,cam:{p:[1.8,4.25,5.2],l:[.95,.82,-.55],fov:39}},
  {say:"A balance wheel and hairspring swing back and forth, setting the rhythm.",pause:-.12,cam:{p:[1.2,3.7,4.15],l:[.62,.9,1.2],fov:36}},
  {say:"The gear train turns that steady beat into the minute and hour hands.",pause:-.12,cam:{p:[-1.25,3.55,4.05],l:[-1.23,.95,1.45],fov:36}},
  {say:"No battery, no screen, just stored energy, carefully metered into motion.",pause:.48,cam:{p:[3.6,6.5,9.2],l:[0,.8,0],fov:45}},
];
