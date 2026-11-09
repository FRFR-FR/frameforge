// BROWN | BOOK ONE — Minecraft-inspired 3D cinematic sequence
// FrameForge project script | 720x1280 | 15 FPS | 90 seconds
// The story sequence adapts the 21:39 industrial-corridor ambush from chapters 5–6.
// Run this script across all 1,350 frames. All motion is evaluated from time,
// so scrubbing any frame produces the same pose. No generated character images.
// Available FrameForge variables: ctx, frame, width, height, time, FF3D.

const T = Math.max(0, Math.min(90, Number(time) || 0));
const W = width, H = height;
const clamp = (v, a=0, b=1) => Math.max(a, Math.min(b, v));
const mix = (a,b,u) => a+(b-a)*u;
const smooth = (a,b,x) => { const u=clamp((x-a)/(b-a)); return u*u*(3-2*u); };
const V = (x,y,z) => [x,y,z];
const scene = new FF3D.Scene({background: T >= 75.5 ? '#17372f' : '#101927', depthMode:'zbuffer'});
scene.lights.length = 0;
scene.addLight(FF3D.ambientLight(T >= 75.5 ? 0.48 : 0.38));
scene.addLight(FF3D.directionalLight(T >= 75.5 ? [-0.42,0.88,0.27] : [-0.42,0.78,0.50], T >= 75.5 ? 0.92 : 0.83));

const cube = (p,s,c,r=[0,0,0],name='block') => scene.add(FF3D.cube({
  size:1, position:p, scale:s, rotation:r, name,
  material:FF3D.solidMaterial(c,{side:'double',roughness:0.92})
}));
const plane = (p,w,d,c) => scene.add(FF3D.plane({width:w,depth:d,position:p,material:FF3D.solidMaterial(c,{side:'double'})}));
const sphere = (p,r,c,segs=8) => scene.add(FF3D.sphere({radius:r,segments:segs,rings:Math.max(4,segs>>1),position:p,material:FF3D.solidMaterial(c,{side:'double'})}));
const light = (p,c,intensity) => scene.addLight({type:'point',position:p,color:c,intensity});
const local = (root,yaw,p) => [root[0]+p[0]*Math.cos(yaw)+p[2]*Math.sin(yaw),root[1]+p[1],root[2]-p[0]*Math.sin(yaw)+p[2]*Math.cos(yaw)];

// Character skins were authored as separate, consistent palettes before animation.
// The novel does not specify every character's appearance; hair and accent choices
// below are visual adaptations, not claims about textual descriptions.
const SKINS = {
 Kaylen:{skin:'#80513f',shade:'#5e392f',hair:'#15191d',jacket:'#242d38',shirt:'#c3c1b8',pants:'#20262f',boots:'#11191e',accent:'#9d5f4e',style:'short',lip:true},
 Kesh:{skin:'#895a45',shade:'#634030',hair:'#1d1715',jacket:'#4c5142',shirt:'#b0a58a',pants:'#292b27',boots:'#151a18',accent:'#b06a43',style:'cap'},
 Juno:{skin:'#704535',shade:'#4d302a',hair:'#191416',jacket:'#334756',shirt:'#d8d3c7',pants:'#28323a',boots:'#202328',accent:'#a8453e',style:'braids',pouch:true},
 Biko:{skin:'#986349',shade:'#6a4336',hair:'#2a1b16',jacket:'#9b754c',shirt:'#d7c6a1',pants:'#34343b',boots:'#201a18',accent:'#c44e36',style:'curl'},
 Tovin:{skin:'#87513d',shade:'#5d382f',hair:'#171c20',jacket:'#a8793e',shirt:'#e2d4bc',pants:'#354e63',boots:'#1b242c',accent:'#c2a05f',style:'short',paper:true},
 Lark:{skin:'#784b3a',shade:'#51342c',hair:'#171719',jacket:'#343640',shirt:'#b9b4a6',pants:'#292d38',boots:'#171a21',accent:'#657785',style:'long'},
 Amel:{skin:'#80543f',shade:'#583a30',hair:'#181b24',jacket:'#49374f',shirt:'#c6b8bd',pants:'#2c2935',boots:'#181923',accent:'#6c94a2',style:'bun',glasses:true},
 Rasha:{skin:'#98624a',shade:'#674437',hair:'#1c1818',jacket:'#6a5743',shirt:'#d0c2ae',pants:'#393337',boots:'#1a1c1e',accent:'#bd9b42',style:'wrap'},
 Sefu:{skin:'#704632',shade:'#4b3029',hair:'#161b19',jacket:'#465b47',shirt:'#c3b9a0',pants:'#303735',boots:'#171e1a',accent:'#b98b4b',style:'short'},
 Yara:{skin:'#895541',shade:'#604034',hair:'#24191c',jacket:'#2d4a59',shirt:'#d3c9b5',pants:'#29343e',boots:'#151d22',accent:'#57a0a1',style:'braids'},
 Kade:{skin:'#8d5a45',shade:'#603e32',hair:'#171719',jacket:'#272b31',shirt:'#b2b1a8',pants:'#25282d',boots:'#16181b',accent:'#aab5ba',style:'short',scar:true},
 'Rescuer A':{skin:'#78513e',shade:'#56392f',hair:'#202326',jacket:'#d08a32',shirt:'#f0c34d',pants:'#293943',boots:'#171d22',accent:'#f1d16a',style:'short',helmet:true},
 'Rescuer B':{skin:'#9a6b51',shade:'#704c3a',hair:'#242326',jacket:'#d3a33d',shirt:'#f0cb58',pants:'#333b40',boots:'#171c20',accent:'#e9d37b',style:'cap',helmet:true}
};

function actor(name, root, yaw, phase=0, pose={}) {
 const sk=SKINS[name], gait=pose.gait||0, crouch=pose.crouch||0;
 const swing=Math.sin(T*7.2+phase)*gait, bounce=Math.max(0,Math.sin(T*14.4+phase))*.08*gait;
 const part=(p,s,c,r=[0,0,0],tag='actor')=>cube(local(root,yaw,p),s,c,[r[0],yaw+r[1],r[2]],tag);
 if (pose.seated) {
  for (const side of [-1,1]) {
   part([side*.22,1.12,.72],[.40,.40,.90],sk.pants,[0,0,side*.015],'seated-thigh');
   part([side*.22,.54,1.25],[.34,.70,.34],sk.pants,[0,0,0],'seated-shin');
   part([side*.22,.20,1.32],[.38,.19,.52],sk.boots,[0,0,0],'seated-boot');
   part([side*.22,.10,1.33],[.38,.04,.50],'#0b1015',[0,0,0],'sole');
  }
 } else if (pose.crawl) {
  for (const side of [-1,1]) {
   part([side*.23,.30,-.12],[.38,.40,.62],sk.pants,[0,0,side*.04],'crawl-thigh');
   part([side*.23,.12,-.65],[.36,.20,.44],sk.boots,[0,0,0],'crawl-boot');
   part([side*.23,.035,-.65],[.36,.035,.43],'#0b1015',[0,0,0],'crawl-sole');
  }
 } else {
  for (const side of [-1,1]) {
   const step=Math.sin(T*7.2+phase+(side<0?0:Math.PI))*gait;
   const lift=Math.max(0,Math.sin(T*7.2+phase+(side<0?0:Math.PI)))*.20*gait;
   part([side*.22,.52-crouch*.18+lift,step*.20],[.32,.92,.34],sk.pants,[step*.20,0,side*.02],'leg');
   const foot=Math.max(.12,.12+lift);
   part([side*.22,foot,step*.20+.10],[.36,.20,.49],sk.boots,[0,0,0],'boot');
   part([side*.22,foot-.085,step*.20+.11],[.36,.045,.48],'#0b1015',[0,0,0],'sole');
  }
 }
 const torsoY=pose.crawl ? .53 : 1.46-crouch*.25+bounce;
 const torsoSize=pose.crawl ? [.92,.55,1.05] : [.88,1.05,.42];
 part([0,torsoY,pose.crawl?-.02:0],torsoSize,sk.jacket,[pose.crawl?.08:0,0,(pose.lean||0)*.16],'torso');
 part([0,torsoY,pose.crawl?.49:.222],pose.crawl?[.34,.38,.05]:[.30,.80,.045],sk.shirt,[0,0,0],'shirt');
 if (sk.helmet) part([0,2.94,0],[.88,.30,.85],'#e9b94d',[0,0,0],'rescue-helmet');
 else part([0,pose.crawl?.98:2.86-crouch*.12+bounce*.35],[.76,.18,.74],sk.hair,[0,0,0],'hair-cap');
 for (const side of [-1,1]) {
  if (pose.crawl) {
   const reach=.18+.18*(Math.sin(T*6.2+(side<0?0:Math.PI))+1)*.5;
   part([side*.59,.38,.62+reach*.4],[.31,.46,.70],sk.jacket,[-.17,0,side*.08],'crawl-arm');
   part([side*.60,.11,.94+reach*.6],[.31,.18,.30],sk.skin,[0,0,0],'crawl-hand');
  } else {
   const armAng=side*(.07+(pose.arm||0)*.25)+swing*(side===1?1:-1)*.55+(pose.fall||0)*.7;
   const sy=1.78-crouch*.20;
   part([side*.56,sy-.46*Math.cos(armAng),.46*Math.sin(armAng)],[.31,.88,.34],sk.jacket,[armAng,0,side*.05],'arm');
   part([side*.56,sy-.88*Math.cos(armAng),.88*Math.sin(armAng)],[.29,.22,.30],sk.skin,[armAng,0,0],'hand');
  }
 }
 const hy=pose.crawl?.99:2.50-crouch*.12+bounce*.35;
 const hz=pose.crawl?.58:0;
 part([0,hy,hz],[.74,.73,.70],sk.skin,[0,pose.head||0,0],'head');
 if (sk.style==='short') {
  part([-.31,hy+.16,hz-.02],[.12,.38,.46],sk.hair,[0,0,0],'side-hair');
  part([.31,hy+.17,hz-.02],[.12,.34,.44],sk.hair,[0,0,0],'side-hair');
 } else if (sk.style==='cap') {
  part([0,hy+.41,hz],[.82,.20,.80],sk.hair,[0,0,0],'cap');
 } else if (sk.style==='braids') {
  for (const side of [-1,1]) for (let j=0;j<3;j++) part([side*.36,hy-.08-j*.16,hz-.02],[.14,.16,.16],sk.hair,[0,0,side*.06],'braid');
 } else if (sk.style==='long') {
  for (const side of [-1,1]) part([side*.34,hy-.19,hz-.02],[.18,.75,.54],sk.hair,[0,0,side*.03],'long-hair');
 } else if (sk.style==='bun') part([0,hy+.48,hz-.20],[.32,.28,.32],sk.hair,[0,0,0],'bun');
 else if (sk.style==='wrap') part([0,hy+.34,hz],[.84,.28,.79],sk.accent,[0,0,0],'headwrap');
 else if (sk.style==='curl') for (const x of [-.22,0,.22]) part([x,hy+.41,hz+.02],[.25,.20,.34],sk.hair,[0,0,0],'curl');
 for (const side of [-1,1]) {
  part([side*.16,hy-.02,hz+.36],[.085,.11,.045],'#e4d2b8',[0,0,0],'eye');
  part([side*.16,hy-.02,hz+.392],[.042,.08,.025],'#171b20',[0,0,0],'pupil');
  part([side*.16,hy+.10,hz+.365],[.12,.045,.06],sk.hair,[0,0,0],'brow');
 }
 const mouth=clamp(pose.mouth||0);
 part([0,hy-.17,hz+.365],[.13,.025+mouth*.09,.05],mouth>.18?'#1b1111':sk.shade,[0,0,0],'mouth');
 if (sk.lip) part([.23,hy-.12,hz+.398],[.07,.025,.02],'#b94e46',[0,0,-.32],'split-lip');
 if (pose.bandage) part([-.56,1.12,.05],[.34,.17,.37],'#dedbd2',[0,0,.06],'bandage');
 if (sk.pouch) part([-.42,1.23,.29],[.34,.44,.20],'#9d433d',[0,0,0],'medical-pouch');
 if (sk.paper && !pose.crawl) part([.40,1.18,.40],[.30,.42,.05],'#e8dfc6',[0,0,.05],'school-application');
 if (pose.paper && !pose.crawl) part([.30,1.0,.47],[.42,.54,.035],'#e8dfc6',[0,0,-.12],'creased-application');
 if (pose.crawl) part([.42,.24,1.00],[.34,.44,.045],'#e8dfc6',[0,0,-.10],'school-application');
 if (sk.glasses) for (const side of [-1,1]) part([side*.16,hy-.02,hz+.414],[.17,.13,.025],'#aeb8c0',[0,0,0],'glasses');
}

function building(x,z,h,w,col,lit=true,seed=0) {
 cube([x,h/2,z],[w,h,5],col,[0,0,0],'tower');
 cube([x,h,z],[w+.25,.22,5.2],'#354454',[0,0,0],'roof-cap');
 if(lit){
  for(let r=0;r<Math.min(7,Math.floor(h/2));r++) for(let c=0;c<Math.max(2,Math.floor(w/1.5));c++){
   const v=Math.sin(seed*3.17+r*8.1+c*6.3)*43758.5453;
   if((v-Math.floor(v))>.48) cube([x-w*.42+c*(w*.84/Math.max(1,Math.floor(w/1.5)-1)),2+r*(h-3)/Math.max(1,Math.floor(h/2)-1),z-2.57],[.22,.32,.045],['#e5b978','#547a8b','#8d9ba0','#6d6c62'][(r+c)%4],[0,0,0],'window');
  }
 }
}
function addCity() {
 cube([0,-.28,8],[18,.45,65],'#242d34',[0,0,0],'asphalt');
 cube([-8.8,-.18,8],[.6,.55,65],'#7b7468'); cube([8.8,-.18,8],[.6,.55,65],'#7b7468');
 for(let z=-20;z<45;z+=5) cube([0,-.02,z],[.18,.025,2.2],'#b4a889');
 [[-15,-7,18,5,'#263746'],[-12,8,24,6,'#283948'],[14,-2,25,6,'#263341'],[16,16,19,5,'#283746'],[-18,24,17,5,'#303c47'],[18,34,27,7,'#2a3946']].forEach((b,i)=>building(b[0],b[1],b[2],b[3],b[4],true,i+11));
 cube([-10,8,10],[4,2,.35],'#263849'); cube([-10,8,9.78],[3.6,1.3,.07],'#d5d1c4');
 cube([8,5.8,2],[.28,.28,.28],'#131a21'); cube([8,5.8,1.78],[.12,.12,.1],'#56a7bd');
 cube([0,4.5,31],[24,9,1.4],'#454950'); cube([0,9.1,31],[25,.4,2],'#303840');
 cube([0,3.5,30.2],[7,5.6,.15],'#111820');
 for(let x=-3.1;x<3.2;x+=.55) cube([x,3.5,30.0],[.06,5.4,.09],'#6f7477');
 for(const x of [-9,-6,6,9]) cube([x,5.2,30.1],[.6,7.6,.7],'#343b42');
 for(const x of [-8,-4,4,8]) {cube([x,7.2,30.15],[1.15,.8,.12],'#82939a');cube([x,2.2,29.9],[.35,.35,.18],'#ad4c3d');}
 for(const side of [-1,1]) for(let z=-12;z<42;z+=12) {
  cube([side*11,4.2,z],[.24,8.4,.24],'#303944'); cube([side*10.1,8.1,z],[2,.18,.24],'#303944'); cube([side*9.2,7.95,z],[.48,.18,.42],'#f3cc8a');
 }
 for(const x of [-7,7]) {cube([x,.55,18],[.7,1.1,.55],'#383d41');cube([x,.95,18],[.75,.18,.60],'#b39869');}
 light([0,8,28],'#ff9f58',.55);
}
function car(x,z,kind,names,drive) {
 const y=.02, body=kind===0?'#1d2630':'#33383c';
 cube([x,y+.70,z],[4,.95,6],body); cube([x,y+1.08,z-1.88],[3.85,.62,2.15],kind===0?'#303943':'#474b4c'); cube([x,y+1.10,z+2.25],[3.55,.55,1.45],body);
 for(const side of [-1,1]) {
  cube([x+side*1.72,y+2.05,z-.95],[.16,1.55,.18],'#171e25'); cube([x+side*1.72,y+2.0,z+1.18],[.16,1.45,.18],'#171e25');
  cube([x+side*1.70,y+1.32,z],[.18,.42,3.2],'#2d353e');
  for(const wz of [-1.7,1.6]) {cube([x+side*1.70,y+.42,z+wz],[.58,.68,.30],'#0b0d10',[drive*2.7,0,0],'tyre');cube([x+side*1.72,y+.42,z+wz],[.19,.36,.27],'#70777a');}
 }
 cube([x,y+.62,z-3.08],[1.25,.35,.12],'#10171d');
 for(const side of [-1,1]) {cube([x+side*1.42,y+1.05,z-3.04],[.62,.27,.13],'#e6d5a5');cube([x+side*1.42,y+1.05,z-3.13],[.36,.16,.08],'#fff1c4');}
 cube([x,y+1.38,z-.55],[3.2,.40,.70],'#1a222a'); cube([x-.70,y+1.55,z-.82],[.6,.75,.64],'#3b4349');cube([x+.70,y+1.55,z-.82],[.6,.75,.64],'#3b4349');
 cube([x,y+1.30,z+1.18],[3,.55,.82],'#39424a');
 names.forEach((name,i)=>{
  const xx=x+(i<2?(i===0?-.70:.70):(-1+(i-2)*.66));
  const zz=z+(i<2?-.78:1.2), yy=.92+Math.sin(T*2.1+i*1.31)*.12;
  const reaction=smooth(42.7,44,T);
  let pose={gait:.08,head:Math.sin(T*1.5+i)*.16,lean:Math.sin(T*2.1+i)*.08,arm:Math.sin(T*2+i)*.15};
  if(name==='Kaylen' && T>18.8 && T<26) pose.arm=.65;
  if(name==='Tovin' && T>19 && T<25) pose.arm=.35;
  if(T>43.4 && T<49.5) {pose={gait:.15,fall:reaction*.6,lean:.15,crouch:.35,arm:.7,head:Math.sin(T*2+i)*.22};}
  actor(name,[xx,yy,zz],Math.PI,i*1.7,pose);
 });
 for(const side of [-1,1]) {cube([x+side*1.93,y+2.70,z-.95],[.10,.14,.20],'#141a20');}
 cube([x,y+2.08,z-1.95],[3.45,.12,.10],'#7d9ba2');
}
function cityAnimation() {
 addCity();
 const drive=smooth(6,42,T)*6.4;
 if(T<50) {car(-1.65,10-drive,0,['Kesh','Kaylen','Juno','Biko','Tovin','Lark'],T);car(2.8,16-drive*.95,1,['Amel','Rasha','Sefu','Yara','Kade'],T);}
 for(let i=0;i<96;i++) {
  const x=((i*83+T*17)%26)-13, y=((i*47+T*31)%19)+1, z=((i*29+T*24)%48)-13;
  cube([x,y,z],[.025,.24,.025],'#718ea2',[.18,0,.10],'rain');
 }
 if(T>43 && T<58) {
  const q=clamp((T-43)/6), fade=1-smooth(46.2,49,T);
  for(let i=0;i<65;i++) {
   const a=i*2.399, r=(.4+(i%9)*.28)*q, x=Math.cos(a)*r, y=2.2+((i*7)%12)*.28*q, z=20+Math.sin(a)*r;
   cube([x,y,z],[.12+(i%4)*.07,.12+(i%4)*.07,.12+(i%4)*.07],['#8b5840','#bb6a38','#df9c4f','#565d60','#7a7770'][i%5],[a*2,a,a*.4],'debris');
  }
  for(let i=0;i<22;i++) sphere([Math.sin(i*3.3+T*.48)*(1.2+i*.13),3.5+i*.34+Math.sin(T*1.7+i)*.15,29+i*.12],.7+i*.04,'#42484d',8);
  if(fade>.01) light([0,4,29],'#ff833e',2.2*fade);
 }
 if(T>=49) {
  for(let i=0;i<30;i++) {const a=i*13.73; const x=Math.sin(a)*9,z=14+(i*7%16),y=.05+(i%4)*.09;cube([x,y,z],[.35+(i%3)*.22,.2+(i%3)*.1,.35+(i%4)*.16],['#565b5b','#6e6b64','#4b5052','#766d62'][i%4],[0,a,0],'rubble');}
  for(let i=0;i<12;i++) sphere([Math.sin(T+i)*2,2+i*.27,26+i*.3],.5+i*.035,'#454b50',8);
  light([-3,.8,24],'#ff7f40',.32);
 }
 if(T>=57.5 && T<75) {
  if(T<64.8) actor('Kaylen',[-.45,.06,2.0+clamp((T-57.5)/5)*1.0],Math.PI,0,{crawl:true,head:Math.sin(T*1.3)*.07});
  else actor('Kaylen',[-.45,.05,3.0],Math.PI,0,{crouch:.60,lean:.4,arm:.55,head:.1,bandage:true,paper:true});
 }
 if(T>66 && T<75) {
  actor('Rescuer A',[-2,.02,1.9],.3,1,{crouch:.3,lean:-.4,arm:.8,head:.2});
  actor('Rescuer B',[1.8,.02,1.0],-.3,2,{crouch:.45,lean:-.45,arm:Math.sin(T*3)*.65,head:-.2});
 }
}
function jungleAnimation() {
 cube([0,-.25,0],[22,.5,22],'#263a2c');
 for(const x of [-8,-6,6,8]) for(const z of [-4,1,6]) {
  cube([x,3.2,z],[.8,6.4,.9],'#503e2b');
  for(let j=0;j<9;j++) cube([x+Math.sin(j*1.7+x)*1.1+Math.sin(T*1.2+j+x)*.16,6.5+(j%3)*.42,z+Math.cos(j*1.4+z)*1.1],[2.2,1.2,2.0],['#234c39','#2c6040','#367149','#1b4938'][j%4]);
 }
 for(let i=0;i<12;i++) {const x=-9+(i%6)*3.5,z=-3+(i>>1)*8,s=Math.sin(T*1.3+i*.8)*.35;cube([x+s,3.8,z],[.10,3.8,.10],'#4f7850');cube([x+s+.06,2.05,z],[.27,.25,.20],'#76a36a');}
 cube([0,.56,1.1],[3.4,1.12,2.1],'#575e57');cube([0,1.16,1.1],[3.45,.16,2.15],'#6c7964');
 for(const [x,z] of [[-1.5,.4],[1.5,1.6],[-1.2,1.9],[1,.25]]) cube([x,.72,z],[.48,.25,.28],'#454f49');
 cube([8,3.4,5],[.22,6.2,3.2],'#276b73');cube([8,6.6,5],[.45,.3,3.4],'#8bb0a7');cube([7.4,.10,5.3],[3.8,.18,3.5],'#1e5960');
 for(let i=0;i<10;i++) {const x=-6+i*1.3,z=4+Math.sin(i*1.5)*1.8;cube([x,.18,z],[.65,.3,.55],'#42534a');cube([x,.55,z],[.15,.65,.15],'#477e4e',[0,0,Math.sin(T+i)*.2]);for(const side of [-1,1]) cube([x+side*.24,.72,z],[.45,.16,.2],'#6d9c5e',[0,0,side*.18+Math.sin(T*1.4+i)*.15]);}
 light([1,8,-3],'#ccc383',.75);light([8,4,5],'#5cb5ca',.45);
 for(let i=0;i<32;i++) sphere([((i*97+Math.sin(T*1.4+i)*26)%20)-10,((i*59+Math.cos(T+i)*20+T*1.3)%16)+.2,((i*37)%17)-7],.035+(i%3)*.012,'#9ec886',6);
 const mouth=ctaMouth(T);
 actor('Kaylen',[0,.30,1.05],0,.6,{seated:true,head:Math.sin(T*.75)*.03,mouth,bandage:true,arm:T>81?-.2:0});
}
function ctaMouth(t) {
 const start=77.5, rel=t-start;
 if(rel<0 || rel>11.67) return 0;
 const beats=[.25,.48,.76,1.05,1.42,1.78,2.18,2.54,2.93,3.28,3.62,4.02,4.38,4.74,5.10,5.49,5.88,6.22,6.58,6.98,7.35,7.74,8.10,8.48,8.84,9.20,9.58,9.96,10.34,10.73,11.12,11.48];
 let v=0; for(let i=0;i<beats.length;i++) {const d=Math.abs(rel-beats[i]); v=Math.max(v,Math.max(0,1-d/.13));} return v*.9;
}
function cameraPose(t) {
 const key=(a,b,u)=>mix(a,b,clamp(u));
 if(t<7) return [[key(15,8,t/7),key(10,7,t/7),key(-22,-12,t/7)],[0,3,9],45];
 if(t<15) return [[key(8,4,(t-7)/8),key(3.6,2.8,(t-7)/8),key(-10,-4,(t-7)/8)],[0,1.8,8],53];
 if(t<22) return [[key(4.5,2.8,(t-15)/7),key(5.5,4.8,(t-15)/7),-6.5],[0,2,8.5],62];
 if(t<30) return [[key(2.8,.8,(t-22)/8),key(4.8,4,(t-22)/8),key(-6,-4,(t-22)/8)],[0,2,9.5],65];
 if(t<37) return [[key(4,1.2,(t-30)/7),key(4.2,3.3,(t-30)/7),key(1,6,(t-30)/7)],[0,3,28],58];
 if(t<43.5) return [[key(1.8,-.8,(t-37)/6.5),2.7,key(8,4,(t-37)/6.5)],[0,2.4,13],44];
 if(t<49) {const u=(t-43.5)/5.5, shake=(1-u)*.42;return [[key(2,-1,u)+Math.sin(t*39)*shake,key(3,2.5,u)+Math.cos(t*33)*shake,key(-8,5,u)],[0,2,12],50];}
 if(t<59) {const u=(t-49)/10;return [[key(10,8,u),key(13,10,u),key(-1,-3,u)],[0,2.2,28],56];}
 if(t<66) return [[.1,3.2,-5.5],[-.45,1,2.6],58];
 if(t<75) {const u=(t-66)/9;return [[key(.2,.8,u),key(4.1,4.6,u),-9],[-.1,1.25,2.5],66];}
 const u=clamp((t-76)/14); return [[key(5.2,3.2,u),key(3.5,3.2,u),key(8,6.4,u)],[0,2,0],42];
}

if(T<75.5) cityAnimation(); else jungleAnimation();
let [cp,ct,fov]=cameraPose(T);
if(T>=75.5) ct=[0,1.9,1.1];
const camera=new FF3D.Camera({position:cp,target:ct,fov,near:.1,far:500,useEditorView:false});
FF3D.render(ctx,scene,camera,{width:W,height:H,depthMode:'zbuffer'});

if(T<43.5 || (T>49 && T<75.5)) {
 for(let i=0;i<70;i++) {const x=(i*83+T*17)%W,y=(i*47+T*31)%H;ctx.fillStyle='rgba(135,164,180,.24)';ctx.fillRect(x,y,1.5,10+(i%6)*2);}
}
if(T>43 && T<49.5) {
 const e=Math.sin(clamp((T-43)/6)*Math.PI),g=ctx.createRadialGradient(W*.5,H*.42,5,W*.5,H*.42,Math.max(W,H)*.55);
 g.addColorStop(0,'rgba(255,232,190,'+(.42*e)+')');g.addColorStop(.3,'rgba(255,145,68,'+(.20*e)+')');g.addColorStop(1,'rgba(255,120,50,0)');ctx.fillStyle=g;ctx.fillRect(0,0,W,H);
}
if(T>20 && T<27) {ctx.font='700 22px sans-serif';ctx.textAlign='center';ctx.fillStyle='#e4e3de';ctx.strokeStyle='#202830';ctx.lineWidth=3;ctx.strokeText('YOU CAN STILL LEAVE',W/2,H*.81);ctx.fillText('YOU CAN STILL LEAVE',W/2,H*.81);}
if(T>31 && T<40 || T>40 && T<44) {ctx.font='700 24px sans-serif';ctx.textAlign='right';ctx.fillStyle='#e2c995';ctx.fillText(T<40?'21:39':'21:40',W-42,76);}
const fadeOut=1-smooth(73.8,75.5,T), fadeIn=smooth(75.5,77,T);
if(T<75.5) {ctx.fillStyle='rgba(0,0,0,'+(1-fadeOut)+')';ctx.fillRect(0,0,W,H);} else {ctx.fillStyle='rgba(0,0,0,'+(1-fadeIn)+')';ctx.fillRect(0,0,W,H);}
const vignette=ctx.createRadialGradient(W/2,H/2,Math.min(W,H)*.22,W/2,H/2,Math.max(W,H)*.72);
vignette.addColorStop(0,'rgba(0,0,0,0)');vignette.addColorStop(1,'rgba(0,0,0,.22)');ctx.fillStyle=vignette;ctx.fillRect(0,0,W,H);