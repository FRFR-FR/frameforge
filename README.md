# FrameForge — Draw, Code, Animate

FrameForge is a lightweight, browser-based, frame-by-frame animation studio. It is built with plain HTML, CSS, and JavaScript. It has **no dependencies, server, API key, paid AI credits, image-generation service, WebGL, or WebGPU**.

It is designed to run as a static website on GitHub Pages, including from a phone browser.

## What it does

- A transparent drawing canvas with brush, pencil, ink, airbrush, texture brush, and eraser tools.
- Color, brush-size, and opacity controls; pointer-pressure support where the device/browser provides it.
- Undo and redo for hand-drawn strokes.
- A frame strip and timeline with blank frames, add-10-frames, duplicate, delete, frame scrubbing, and playback.
- Onion-skin previews of adjacent frames to help draw movement consistently.
- A per-frame JavaScript drawing layer. Write Canvas 2D code using `ctx`, `frame`, `width`, `height`, and `time`, then render it onto the current frame or across the entire timeline. The `time` value changes per frame, so code can create animated motion.
- A sample procedural city scene that demonstrates gradients, Bézier curves, building facades, individual windows, rain, atmospheric haze, reflections, and film grain.
- Import an image into the current frame as a tracing or compositing starting point.
- 30 FPS default, adjustable from 1 to 60 FPS.
- Export a silent WebM video in real time from the timeline, and export/import editable project JSON files.
- Automatic local save in the browser using IndexedDB.

## Run locally

1. Download or clone this repository.
2. Open `index.html` in a modern browser.
3. Start drawing, or open **Frame code** and choose **Load detailed city example**, then press **Run on frame**.

No Python installation or package installation is required. The application is a static website.

## Publish on GitHub Pages

1. Create a new GitHub repository, for example `frameforge`.
2. Upload `index.html`, `styles.css`, `app.js`, and this `README.md` to the repository root.
3. Open the repository's **Settings → Pages**.
4. Under **Build and deployment**, choose **Deploy from a branch**.
5. Select the `main` branch and `/ (root)` folder, then save.
6. After GitHub Pages publishes it, open the URL shown in the Pages settings. The app can be used directly in the mobile browser.

The site does not need GitHub Actions or a build step. GitHub is only hosting the static files; the animation itself runs locally in the visitor's browser.

## How code-drawn frames work

In the **Frame code** panel, the editor runs JavaScript with these values already available:

```js
ctx     // CanvasRenderingContext2D for a transparent frame layer
frame   // current frame number, starting at 1
width   // canvas width in pixels
height  // canvas height in pixels
time    // current frame time in seconds
```

For example:

```js
const gradient = ctx.createLinearGradient(0, 0, width, height);
gradient.addColorStop(0, "#0b1930");
gradient.addColorStop(1, "#b34d53");
ctx.fillStyle = gradient;
ctx.fillRect(0, 0, width, height);

ctx.strokeStyle = "#f3d7a2";
ctx.lineWidth = 5;
ctx.beginPath();
ctx.moveTo(70, 500);
ctx.bezierCurveTo(240, 260, 480, 790, 650, 410);
ctx.stroke();
```

Each frame stores its rendered code layer independently. Code layers sit above the hand-drawn layer. Use **Bake code layer into drawing** to merge the code artwork with the paint layer. The timeline plays the rendered images at the chosen frame rate; scripts are not re-executed during playback.

## Performance and limits

- There is no dedicated-GPU requirement and the application does not use a 3D graphics API. It uses the browser's Canvas 2D implementation, which can run on CPU-capable devices. Some browsers may internally accelerate Canvas 2D; the app cannot force every browser to use CPU-only rendering.
- The default canvas is 720 × 1280. Larger canvases and many detailed frames use more memory and may run slowly on phones.
- 30 FPS is the playback/export target. Actual drawing and playback smoothness depends on the phone/browser, number of frames, and complexity of the artwork.
- Hand-drawn artwork is raster per frame. The code layer can draw detailed paths, gradients, textures, and effects, but the user still authors the artwork; this is not an automatic film generator.
- WebM export depends on browser `MediaRecorder` support and runs in real time. Some mobile browsers may not support canvas recording. Project JSON export/import is the portable backup and editing format.
- Autosave is local to the browser/device. It is not synchronized to GitHub or another device. Export your project JSON regularly.
- A project file can become large because it stores the artwork for every frame. Keep a backup before changing canvas dimensions or clearing browser data.

## Security note for frame scripts

The frame-code feature executes JavaScript written into the editor. Only run code you wrote or trust. Do not paste unknown scripts into it. The app makes no network requests and loads no third-party libraries.

## License

MIT. See [LICENSE](LICENSE).


## Code-driven 3D animation (FrameForge 3D)

FrameForge includes a dependency-free, CPU-based 3D scene renderer in `frameforge-3d.js`. It constructs meshes from geometry in JavaScript, applies object transforms, projects them through a camera, shades faces with ambient and directional lights, then draws the projected triangles into FrameForge's existing frame canvas. It does not generate or import pictures and does not require WebGL, a GPU, npm packages, or a remote rendering service.

The frame-code editor receives an additional `FF3D` argument. Select **Load 3D penguin example** to load a working scene, choose a view from the Camera selector, then press **Run on frame** or **Run all frames**. The `time` value is the current frame time in seconds, so object and camera transforms can be animated across the timeline.

### Camera views

The Camera selector provides **Front, Back, Left, Right, Top, Bottom, 3/4, Isometric, and Free** views. A camera uses the editor view by default. To make a script keep its own camera position instead, create it with `useEditorView: false`, or call `camera.setView("front")`. Free mode uses the camera's own position and target.

### Minimal 3D scene

```js
const scene = new FF3D.Scene({ background: "#101b2b" });
scene.addLight(FF3D.ambientLight(0.45));
scene.addLight(FF3D.directionalLight([-0.5, 0.8, 0.4], 0.9));

const floor = FF3D.plane({
  width: 12,
  depth: 12,
  position: [0, -1, 0],
  material: { color: "#b7cbd6" }
});
scene.add(floor);

const cube = FF3D.cube({
  size: 2,
  position: [0, 0, 0],
  material: { color: "#d58d50", wireframe: false }
});
cube.rotation[1] = time * 0.7;
scene.add(cube);

const camera = new FF3D.Camera({
  position: [5, 3, 7],
  target: [0, 0, 0],
  projection: "perspective",
  fov: 48
});
FF3D.render(ctx, scene, camera, { width, height });
```

### Available building blocks

- `new FF3D.Scene({ background })`, `scene.add(mesh)`, and `scene.addLight(light)`
- `FF3D.cube(options)`, `sphere(options)`, `plane(options)`, `cylinder(options)`, and `cone(options)`
- `FF3D.custom(vertices, triangles, material, options)` for user-authored meshes
- `new FF3D.Camera({ position, target, projection, fov, orthoHeight })`
- `camera.orbit(yaw, pitch, distance)`, `camera.dolly(amount)`, `camera.pan(x, y, z)`, and `camera.lookAt(target)`
- `FF3D.ambientLight(intensity)`, `FF3D.directionalLight(direction, intensity)`, and `FF3D.render(ctx, scene, camera, options)`

### Renderer scope

This is a lightweight software renderer intended for coded motion graphics, low-poly scenes, educational animations, and camera-angle control on mobile devices. It uses perspective or orthographic projection, face-based lighting, and painter-order triangle sorting. It is not a full replacement for Blender or a GPU engine: advanced physically based materials, texture maps, skeletal character rigs, shadows, and a per-pixel depth buffer are not included. Complex intersecting or transparent meshes may therefore need simpler geometry or careful draw ordering. The final output is still raster video on FrameForge's existing canvas timeline.
