# FrameForge V2 on Android and mobile browsers

FrameForge is a static browser application. The editor, local project controls and V2 asset/timeline tools run on the device. The five-button mobile dock is available at phone widths: **Assets**, **Timeline**, **Director**, **Produce** and **Render**.

## Start a project on Android

1. Open the FrameForge GitHub Pages site in current Chrome or another Chromium-based browser.
2. Use the top-bar **New** or **Open** controls for the legacy drawing project, or open **V2 Assets** and use **Save V2**, **Open V2 JSON** or **Export JSON** for a V2 project.
3. In **Assets**, import local images, audio, video, SVG or GLB/glTF files. Imported media begins with rights status **pending**; importing is not a licence check.
4. Use the mobile dock to jump between the asset library, timeline, research director, production panel and render queue.
5. Select the playhead position and use the compositor preview to inspect the visual layers. Open a section from the dock before editing its controls.

## Backups and storage limits

- V2 projects and imported media are stored in the browser's IndexedDB on that device. It is not cloud storage and does not automatically sync to another phone or computer.
- Browser storage is quota-limited and may be evicted by the browser or operating system. Use **Export JSON** and keep original source files in a separate backup.
- Export completed render-queue chunk ZIPs regularly. A paused job can resume from saved frames while its IndexedDB data remains available. The tab/device must remain open while rendering; it is not a background cloud worker.
- The 250 MB per-file import ceiling is a validation limit, not a promise that the phone has enough free storage or memory for that file.
- Some video/audio formats depend on the device's browser codecs. Rendering imported GLB/glTF model pixels requires WebGL; the 2D editor remains usable where WebGL is unavailable.
- Avoid keeping very large projects open alongside other memory-heavy apps. Lower output resolution, use smaller chunks and close unused tabs when a phone struggles.

## Final MP4 export: use a local computer for heavier jobs

The mobile browser creates and downloads PNG chunk ZIPs. It does **not** run native FFmpeg, launch Blender or encode a long MP4 through GitHub Pages. For final assembly, use a computer or another environment you control with Python 3.12, FFmpeg and ffprobe:

```bash
python -m pip install -r requirements-dev.txt
python tools/merge_render_chunks.py --chunks-dir ./render-input/chunks --output-dir ./render-output
python tools/export_ffmpeg.py --frames-dir ./render-output/frames --output ./render-output/final.mp4 --profile 720p-horizontal --fps 30
python tools/qa_render.py --input ./render-output/final.mp4 --expected-manifest ./render-output/render-frames.json --json-out ./render-output/qa-report.json
python tools/create_review.py --input ./render-output/final.mp4 --output-dir ./render-output/review
python tools/package_delivery.py --video ./render-output/final.mp4 --project ./project.json --qa-report ./render-output/qa-report.json --review-dir ./render-output/review --output ./render-output/delivery.zip
```

Use the **720p-vertical** profile for Shorts. Add separate copies of imported source assets to the delivery package when the recipient needs to reopen the editable project: the V2 JSON does not embed the binary files held in IndexedDB.

GitHub Actions offers a manual, capped validation/export path for small inputs, but it is not unlimited free compute. Larger/longer renders should be encoded locally.
