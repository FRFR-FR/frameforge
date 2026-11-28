#!/usr/bin/env node
import fs from "node:fs";
import fsp from "node:fs/promises";
import path from "node:path";
import http from "node:http";
import { fileURLToPath } from "node:url";
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

const server = http.createServer((req, res) => {
  try {
    const pathname = decodeURIComponent(new URL(req.url, "http://127.0.0.1").pathname);
    const relative = pathname === "/" ? "youtube-channel/episodes/EP002/threejs/render_frame.html" : pathname.replace(/^\/+/, "");
    const target = path.resolve(ROOT, relative);
    if (target !== ROOT && !target.startsWith(ROOT + path.sep)) {
      res.writeHead(403); res.end("Forbidden"); return;
    }
    if (!fs.existsSync(target) || !fs.statSync(target).isFile()) {
      res.writeHead(404); res.end("Not found"); return;
    }
    res.writeHead(200, {"content-type": MIME[path.extname(target)] || "application/octet-stream",
      "cache-control":"no-store"});
    fs.createReadStream(target).pipe(res);
  } catch (error) {
    res.writeHead(500); res.end(String(error));
  }
});

await fsp.mkdir(OUTPUT, {recursive:true});
await new Promise(resolve => server.listen(0, "127.0.0.1", resolve));
const baseURL = "http://127.0.0.1:" + server.address().port;
let browser;
try {
  browser = await chromium.launch({
    headless:true,
    args:["--no-sandbox","--disable-dev-shm-usage","--use-gl=swiftshader",
      "--enable-unsafe-swiftshader","--ignore-gpu-blocklist"]
  });
  const page = await browser.newPage({viewport:{width:WIDTH,height:HEIGHT},deviceScaleFactor:1});
  page.setDefaultTimeout(60000);
  page.on("pageerror", error => { console.error("THREEJS_PAGE_ERROR", error.message); });
  page.on("console", message => { if (message.type() === "error") console.error("THREEJS_CONSOLE_ERROR", message.text()); });
  await page.goto(baseURL + "/youtube-channel/episodes/EP002/threejs/render_frame.html", {waitUntil:"load"});
  await page.waitForFunction("window.__READY === true && window.__PLAYER", null, {timeout:90000});
  const canvasSize = await page.locator("#stage canvas").evaluate(canvas => [canvas.width,canvas.height]);
  if (canvasSize[0] !== WIDTH || canvasSize[1] !== HEIGHT) {
    throw new Error("Three.js scene canvas is not 1280x720: " + canvasSize.join("x"));
  }
  const collisionBefore = await page.evaluate(() => window.__PLAYER.collisionReport ? window.__PLAYER.collisionReport() : null);
  if (!collisionBefore || collisionBefore.length !== 10) {
    throw new Error("The ten-section collision/rig report is missing.");
  }

  console.log("Three.js renderer ready: 1280x720, 24fps, ten scenes, swept SAT checks active where assemblies move.");
  for (let sceneIndex=0; sceneIndex<SCENES.length; sceneIndex++) {
    const sceneName = SCENES[sceneIndex];
    const folder = path.join(OUTPUT, sceneName);
    await fsp.mkdir(folder,{recursive:true});
    for (let frame=0; frame<FRAMES_PER_SCENE; frame++) {
      const timelineTime = sceneIndex * SECONDS_PER_SCENE + frame / FPS;
      await page.evaluate(t => window.__PLAYER.seek(t), timelineTime);
      const png = await page.screenshot({type:"png",animations:"disabled"});
      const filename = path.join(folder, "frame_" + String(frame+1).padStart(4,"0") + ".png");
      await fsp.writeFile(filename,png);
      if (frame === 0 || (frame+1) % 72 === 0 || frame === FRAMES_PER_SCENE-1) {
        console.log("THREEJS_PROGRESS",sceneName,(frame+1)+"/"+FRAMES_PER_SCENE);
      }
    }
  }
  const collisionAfter = await page.evaluate(() => window.__PLAYER.collisionReport());
  await fsp.writeFile(path.join(OUTPUT,"collision_report.json"),JSON.stringify({
    renderer:"Three.js r175 via Playwright Chromium/SwiftShader",
    resolution:"1280x720",fps:FPS,secondsPerScene:SECONDS_PER_SCENE,
    framesPerScene:FRAMES_PER_SCENE,scenes:SCENES.map((name,index)=>({name,startSeconds:index*SECONDS_PER_SCENE,endSeconds:(index+1)*SECONDS_PER_SCENE})),
    collision:collisionAfter
  },null,2));
  for (const name of SCENES) {
    const count = fs.readdirSync(path.join(OUTPUT,name)).filter(file => /^frame_\d{4}\.png$/.test(file)).length;
    if (count !== FRAMES_PER_SCENE) throw new Error(name+" produced "+count+" frames; expected "+FRAMES_PER_SCENE);
  }
  console.log("THREEJS_CUTAWAYS_COMPLETE",SCENES.length,"scenes",SCENES.length*FRAMES_PER_SCENE,"frames");
} finally {
  if (browser) await browser.close();
  await new Promise(resolve => server.close(resolve));
}
