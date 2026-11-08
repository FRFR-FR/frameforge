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
