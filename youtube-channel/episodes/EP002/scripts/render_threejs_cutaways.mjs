#!/usr/bin/env node
import fs from "node:fs";
import fsp from "node:fs/promises";
import path from "node:path";
import http from "node:http";
import { chromium } from "playwright";

const args = process.argv.slice(2);
function arg(name, fallback) {
  const i = args.indexOf(name);
  return i >= 0 && args[i + 1] ? args[i + 1] : fallback;
}
const ROOT = path.resolve(process.cwd());
const OUTPUT = path.resolve(arg("--output-dir", "youtube-channel/episodes/EP002/output/3d_frames"));
const WIDTH = 1280, HEIGHT = 720, FPS = 24, SECONDS_PER_SCENE = 12, FRAMES_PER_SCENE = FPS * SECONDS_PER_SCENE;
const SCENES = [
  "scene_01_tin_plasma",
  "scene_02_layer_stack",
  "scene_03_wavelength",
  "scene_04_tin_plasma_detail",
  "scene_05_mirror_optics",
  "scene_06_reticle_projection",
  "scene_07_wafer_stage",
  "scene_08_process_cycle",
  "scene_09_high_na",
  "scene_10_supply_chain"
];
const MIME = {
  ".html":"text/html; charset=utf-8", ".mjs":"text/javascript; charset=utf-8",
  ".js":"text/javascript; charset=utf-8", ".json":"application/json",
  ".css":"text/css", ".png":"image/png"
};

const server = http.createServer((req,res) => {
  try {
    const url = new URL(req.url,"http://127.0.0.1");
    const pathname = decodeURIComponent(url.pathname);
    if(req.method==="POST" && pathname==="/upload"){
      const filename=url.searchParams.get("name")||"";
      if(!/^[a-z0-9_]+\.mp4$/.test(filename)){
        res.writeHead(400);res.end("Invalid output filename");return;
      }
      const destination=path.resolve(OUTPUT,filename);
      if(!destination.startsWith(OUTPUT+path.sep)){
        res.writeHead(403);res.end("Forbidden");return;
      }
      const output=fs.createWriteStream(destination);
      req.pipe(output);
      output.on("finish",()=>{res.writeHead(201,{"content-type":"text/plain"});res.end("saved");});
      output.on("error",error=>{res.writeHead(500);res.end(error.message);});
      return;
    }
    const relative=pathname==="/"?"youtube-channel/episodes/EP002/threejs/render_frame.html":pathname.replace(/^\/+/, "");
    const target=path.resolve(ROOT,relative);
    if(target!==ROOT&&!target.startsWith(ROOT+path.sep)){
      res.writeHead(403);res.end("Forbidden");return;
    }
    if(!fs.existsSync(target)||!fs.statSync(target).isFile()){
      res.writeHead(404);res.end("Not found");return;
    }
    res.writeHead(200,{"content-type":MIME[path.extname(target)]||"application/octet-stream","cache-control":"no-store"});
    fs.createReadStream(target).pipe(res);
  } catch(error) {
    res.writeHead(500);res.end(String(error));
  }
});

await fsp.mkdir(OUTPUT,{recursive:true});
await new Promise(resolve=>server.listen(0,"127.0.0.1",resolve));
const baseURL="http://127.0.0.1:"+server.address().port;
let browser;
try{
  browser=await chromium.launch({headless:true,args:["--no-sandbox","--disable-dev-shm-usage","--use-gl=swiftshader","--enable-unsafe-swiftshader","--ignore-gpu-blocklist"]});
  const page=await browser.newPage({viewport:{width:WIDTH,height:HEIGHT},deviceScaleFactor:1});
  page.setDefaultTimeout(90000);
  const pageErrors=[];
  page.on("pageerror",error=>{pageErrors.push(error.message);console.error("THREEJS_PAGE_ERROR",error.message);});
  page.on("console",message=>{if(message.type()==="error")console.error("THREEJS_CONSOLE_ERROR",message.text());});
  await page.goto(baseURL+"/youtube-channel/episodes/EP002/threejs/render_frame.html",{waitUntil:"load"});
  await page.waitForFunction("window.__READY === true && window.__PLAYER",null,{timeout:90000});
  const canvasSize=await page.locator("#stage canvas").evaluate(canvas=>[canvas.width,canvas.height]);
  if(canvasSize[0]!==WIDTH||canvasSize[1]!==HEIGHT)throw new Error("Three.js canvas is not 1280x720: "+canvasSize.join("x"));
  const collisionBefore=await page.evaluate(()=>window.__PLAYER.collisionReport?window.__PLAYER.collisionReport():null);
  if(!collisionBefore||collisionBefore.length!==10)throw new Error("The ten-section rig/collision report is missing.");

  // Verify the WebGL drawing buffer contains actual scene pixels before encoding.
  // Chromium may otherwise clear the WebGL canvas before VideoFrame captures it.
  const visualPreflight=await page.evaluate(async()=>{
    const canvas=document.querySelector("#stage canvas");
    const gl=canvas&&(canvas.getContext("webgl2")||canvas.getContext("webgl"));
    if(!canvas||!gl)return {ok:false,reason:"WebGL canvas/context unavailable"};
    window.__PLAYER.seek(6);
    await new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)));
    const pixels=new Uint8Array(canvas.width*canvas.height*4);
    gl.readPixels(0,0,canvas.width,canvas.height,gl.RGBA,gl.UNSIGNED_BYTE,pixels);
    let visible=0,bright=0,alpha=0;
    for(let i=0;i<pixels.length;i+=4){
      const y=0.2126*pixels[i]+0.7152*pixels[i+1]+0.0722*pixels[i+2];
      if(y>28)visible++;
      if(y>56)bright++;
      if(pixels[i+3]>0)alpha++;
    }
    const total=canvas.width*canvas.height;
    return {
      ok:visible/total>0.025&&bright/total>0.004,
      visible_fraction:visible/total,
      bright_fraction:bright/total,
      alpha_fraction:alpha/total,
      preserve_drawing_buffer:gl.getContextAttributes()?.preserveDrawingBuffer===true
    };
  });
  console.log("THREEJS_VISUAL_PREFLIGHT",JSON.stringify(visualPreflight));
  if(!visualPreflight.ok)throw new Error("Three.js visual preflight failed: canvas is empty or black; refusing to encode.");
  const h264Supported=await page.evaluate(async()=>{
    if(!window.VideoEncoder||!window.VideoFrame)return false;
    try{
      const result=await VideoEncoder.isConfigSupported({
        codec:"avc1.42001f",width:1280,height:720,bitrate:12000000,
        framerate:24,latencyMode:"quality",avc:{format:"avc"}
      });
      return !!result.supported;
    }catch(_){return false;}
  });
  let encodingMode=h264Supported?"WebCodecs H.264 MP4":"PNG frames + FFmpeg fallback";
  console.log("Three.js renderer ready: 1280x720, 24fps, ten scenes. Encoding mode: "+encodingMode);
  if(h264Supported){
    try{
      for(let sceneIndex=0;sceneIndex<SCENES.length;sceneIndex++){
        const sceneName=SCENES[sceneIndex];
        const result=await page.evaluate(async({sceneName,startSeconds,durationSeconds,width,height,fps})=>{
          const canvas=document.querySelector("#stage canvas");
          if(!canvas)throw new Error("Three.js canvas missing during H.264 encoding.");
          const count=Math.round(durationSeconds*fps);
          const config={codec:"avc1.42001f",width:width,height:height,bitrate:12000000,framerate:fps,latencyMode:"quality",avc:{format:"avc"}};
          const supported=await VideoEncoder.isConfigSupported(config);
          if(!supported.supported)throw new Error("H.264 WebCodecs encoder became unavailable.");
          const samples=[];let avcC=null,error=null;
          const encoder=new VideoEncoder({
            output:function(chunk,metadata){
              try{
                if(!avcC&&metadata&&metadata.decoderConfig&&metadata.decoderConfig.description){
                  const desc=metadata.decoderConfig.description;
                  if(desc instanceof ArrayBuffer)avcC=new Uint8Array(desc).slice();
                  else if(ArrayBuffer.isView(desc))avcC=new Uint8Array(desc.buffer,desc.byteOffset,desc.byteLength).slice();
                }
                const data=new Uint8Array(chunk.byteLength);chunk.copyTo(data);
                samples.push({data:data,key:chunk.type==="key",timestamp:chunk.timestamp});
              }catch(e){error=e;}
            },
            error:function(e){error=e;}
          });
          function cat(){const parts=[...arguments],length=parts.reduce((n,p)=>n+p.length,0),out=new Uint8Array(length);let offset=0;for(const p of parts){out.set(p,offset);offset+=p.length;}return out;}
          const u8=n=>new Uint8Array([n&255]);
          const u16=n=>new Uint8Array([(n>>8)&255,n&255]);
          const u32=n=>new Uint8Array([(n>>>24)&255,(n>>>16)&255,(n>>>8)&255,n&255]);
          const txt=s=>new TextEncoder().encode(s);
          const zero=n=>new Uint8Array(n);
          function box(type){const parts=[].slice.call(arguments,1),body=cat.apply(null,parts);return cat(u32(body.length+8),txt(type),body);}
          function full(type,version,flags){const p=[].slice.call(arguments,3);return box.apply(null,[type,u8(version),new Uint8Array([(flags>>16)&255,(flags>>8)&255,flags&255])].concat(p));}
          function makeMP4(avcConfig){
            if(!samples.length||!avcConfig)throw new Error("H.264 AVC configuration missing.");
            const total=samples.reduce((n,x)=>n+x.data.length,0);
            if(total+200000>0xffffffff)throw new Error("MP4 segment exceeds 4GB.");
            const ftyp=box("ftyp",txt("isom"),u32(0x200),txt("isomiso2avc1mp41"));
            const n=samples.length;
            const identity=cat(u32(0x10000),u32(0),u32(0),u32(0),u32(0x10000),u32(0),u32(0),u32(0),u32(0x40000000));
            const mvhd=full("mvhd",0,0,u32(0),u32(0),u32(fps),u32(n),u32(0x10000),u16(0x100),u16(0),zero(8),identity,zero(24),u32(2));
            const tkhd=full("tkhd",0,7,u32(0),u32(0),u32(1),u32(0),u32(n),zero(8),u16(0),u16(0),u16(0),u16(0),identity,u32(width*65536),u32(height*65536));
            const mdhd=full("mdhd",0,0,u32(0),u32(0),u32(fps),u32(n),u16(0x55c4),u16(0));
            const hdlr=full("hdlr",0,0,u32(0),txt("vide"),zero(12),txt("VideoHandler\0"));
            const vmhd=full("vmhd",0,1,u16(0),u16(0),u16(0),u16(0));
            const url=full("url ",0,1),dref=full("dref",0,0,u32(1),url),dinf=box("dinf",dref);
            const avc1=box("avc1",zero(6),u16(1),u16(0),u16(0),zero(12),u16(width),u16(height),u32(0x480000),u32(0x480000),u32(0),u16(1),zero(32),u16(0x18),u16(0xffff),box("avcC",avcConfig));
            const stsd=full("stsd",0,0,u32(1),avc1),stts=full("stts",0,0,u32(1),u32(n),u32(1));
            const stsc=full("stsc",0,0,u32(1),u32(1),u32(n),u32(1));
            const stsz=full("stsz",0,0,u32(0),u32(n),...samples.map(x=>u32(x.data.length)));
            const keys=samples.map((x,i)=>x.key?u32(i+1):null).filter(Boolean);
            const stss=full("stss",0,0,u32(keys.length),...keys);
            const moovAt=offset=>box("moov",mvhd,box("trak",tkhd,box("mdia",mdhd,hdlr,box("minf",vmhd,dinf,box("stbl",stsd,stts,stsc,stsz,full("stco",0,0,u32(1),u32(offset)),stss)))));
            let moov=moovAt(0);moov=moovAt(ftyp.length+moov.length+8);
            return new Blob([ftyp,moov,u32(total+8),txt("mdat")].concat(samples.map(x=>x.data)),{type:"video/mp4"});
          }
          encoder.configure(supported.config||config);
          try{
            for(let frameIndex=0;frameIndex<count;frameIndex++){
              window.__PLAYER.seek(startSeconds+frameIndex/fps);
              await new Promise(resolve=>requestAnimationFrame(resolve));
              const frame=new VideoFrame(canvas,{timestamp:Math.round(frameIndex*1000000/fps),duration:Math.round(1000000/fps)});
              encoder.encode(frame,{keyFrame:frameIndex===0||frameIndex%(fps*2)===0});
              frame.close();
              if(encoder.encodeQueueSize>6){
                await new Promise((resolve,reject)=>{
                  const timeout=setTimeout(()=>reject(new Error("H.264 encoder stalled.")),15000);
                  encoder.addEventListener("dequeue",()=>{clearTimeout(timeout);resolve();},{once:true});
                });
              }
              if(error)throw error;
            }
            await encoder.flush();
            if(error)throw error;
            samples.sort((a,b)=>a.timestamp-b.timestamp);
            if(samples.length!==count)throw new Error("Frame-count mismatch: "+samples.length+" / "+count);
            const blob=makeMP4(avcC);
            const response=await fetch("/upload?name="+encodeURIComponent(sceneName+".mp4"),{method:"POST",body:blob});
            if(!response.ok)throw new Error("Could not save H.264 MP4: HTTP "+response.status);
            return {frames:samples.length,bytes:blob.size,codec:config.codec};
          }finally{
            try{encoder.close();}catch(_){}
          }
        },{sceneName,startSeconds:sceneIndex*SECONDS_PER_SCENE,durationSeconds:SECONDS_PER_SCENE,width:WIDTH,height:HEIGHT,fps:FPS});
        if(result.frames!==FRAMES_PER_SCENE)throw new Error(sceneName+" H.264 encoder returned the wrong frame count.");
        console.log("WEB_CODECS_PROGRESS",sceneName,result.frames,result.bytes);
      }
    }catch(error){
      console.error("WEB_CODECS_FAILED; falling back to lossless PNG frame extraction:",error.message);
      encodingMode="PNG frames + FFmpeg fallback";
      for(const name of SCENES)await fsp.rm(path.join(OUTPUT,name+".mp4"),{force:true});
    }
  }
  if(!h264Supported||encodingMode==="PNG frames + FFmpeg fallback"){
    for(let sceneIndex=0;sceneIndex<SCENES.length;sceneIndex++){
      const sceneName=SCENES[sceneIndex],folder=path.join(OUTPUT,sceneName);
      await fsp.mkdir(folder,{recursive:true});
      for(let frame=0;frame<FRAMES_PER_SCENE;frame++){
        const timelineTime=sceneIndex*SECONDS_PER_SCENE+frame/FPS;
        await page.evaluate(t=>window.__PLAYER.seek(t),timelineTime);
        const png=await page.screenshot({type:"png",animations:"disabled"});
        await fsp.writeFile(path.join(folder,"frame_"+String(frame+1).padStart(4,"0")+".png"),png);
        if(frame===0||(frame+1)%72===0||frame===FRAMES_PER_SCENE-1)
          console.log("THREEJS_PROGRESS",sceneName,(frame+1)+"/"+FRAMES_PER_SCENE);
      }
    }
  }
  const collisionAfter=await page.evaluate(()=>window.__PLAYER.collisionReport());
  await fsp.writeFile(path.join(OUTPUT,"collision_report.json"),JSON.stringify({
    renderer:"Three.js r175 via Playwright Chromium/SwiftShader",
    encoding:encodingMode,
    resolution:"1280x720",fps:FPS,secondsPerScene:SECONDS_PER_SCENE,
    framesPerScene:FRAMES_PER_SCENE,
    scenes:SCENES.map((name,index)=>({name,startSeconds:index*SECONDS_PER_SCENE,endSeconds:(index+1)*SECONDS_PER_SCENE})),
    collision:collisionAfter
  },null,2));
  for(const name of SCENES){
    const direct=path.join(OUTPUT,name+".mp4");
    const frames=path.join(OUTPUT,name);
    if(fs.existsSync(direct)&&fs.statSync(direct).size>1000)continue;
    const count=fs.existsSync(frames)?fs.readdirSync(frames).filter(file=>/^frame_\d{4}\.png$/.test(file)).length:0;
    if(count!==FRAMES_PER_SCENE)throw new Error(name+" produced "+count+" PNG frames or no direct MP4.");
  }
  await fsp.writeFile(path.join(OUTPUT,"render_mode.json"),JSON.stringify({encoding:encodingMode,resolution:"1280x720",fps:FPS,sceneCount:SCENES.length},null,2));
  console.log("THREEJS_CUTAWAYS_COMPLETE",SCENES.length,"scenes",SCENES.length*FRAMES_PER_SCENE,"frames",encodingMode);
}finally{
  if(browser)await browser.close();
  await new Promise(resolve=>server.close(resolve));
}
