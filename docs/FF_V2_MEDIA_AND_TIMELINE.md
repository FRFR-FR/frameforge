# FrameForge V2 — Media Import, Asset Library and Timeline Guide

**Implemented roadmap range:** Steps 6–10  
**Editor entry point:** `index.html` → **V2 Assets** panel and **V2 Multi-track Timeline**

## 1. V2 is additive

The original frame-by-frame editor, frame strip, browser WebM export and version-1 project format remain present. V2 uses a separate project model with `schema_version: 2` and a separate asset/project store in the same IndexedDB database. A V2 project is not silently converted into a version-1 project.

## 2. Supported imports

| Category | Extensions |
|---|---|
| Raster image | PNG, JPEG/JPG, GIF, WebP, BMP, AVIF |
| Vector graphic | SVG |
| Video | MP4, M4V, MOV, WebM, OGV |
| Audio | MP3, WAV, OGG/OGA, FLAC, M4A, AAC |
| 3D interchange | GLB and glTF 2.0 JSON |

Each import is checked against an allowed extension/MIME family and a basic file/container signature where available. Images are decoded in the browser to read dimensions. Video/audio metadata is read through the browser's media element; if the current browser cannot read its container/codec or duration, the import is rejected. GLB headers and glTF 2.0 JSON are checked.

### File limits and format notes

- Maximum individual import: **250 MB**. A device/browser's available IndexedDB quota may be lower.
- SHA-256 is calculated for imports up to **32 MB**. Larger files are not fully read into memory just to hash them.
- The importer stores actual media bytes as Blob records in IndexedDB; project JSON stores references and metadata.
- For glTF JSON, external buffers/textures are recorded and flagged. Import those dependencies separately or use a self-contained GLB. External files are not silently downloaded.
- SVG rejects script/foreign-object content, event-handler attributes, external references and external CSS resource imports. Only embedded vector shapes and local fragment references are accepted.
- Alpha capability describes whether the file format can support alpha; it does not promise that every pixel in the file is transparent.
- The browser metadata probe is not a full-file codec audit. A format accepted on one device may be unsupported on another, and an imported media file can still contain later decode errors.

## 3. Asset library

The **V2 Assets** tab shows the current V2 project's asset collection. It provides:
- Image previews; media-type markers for video/audio/3D items.
- Search by name, MIME type and tags.
- Filters for images, graphics/SVG, video, audio and 3D models.
- Editable comma-separated tags.
- File size, pixel dimensions, duration and MIME/format metadata where available.
- Rights state for each asset.

Imported assets are marked `user_supplied` with rights state `pending`. This deliberately does not infer that an imported file is owned by the user or cleared for publication. Review its rights and attribution before publishing.

Assets are stored in IndexedDB under stable asset IDs. The browser asset library is local to that browser profile; it does not sync to GitHub or another device.

## 4. Multi-track timeline

A new V2 project starts with separate tracks for video, images/cut-outs, graphics, titles, voiceover, music and sound effects. Additional tracks can be added for video, image, graphics, title, 3D scene, voiceover, music, SFX, effects and adjustment content.

A timeline clip references a project asset, has a start frame and duration, and stores its transform/keyframe/effect arrays for future compositor work. Current timeline controls include:

- Track enable/visibility, mute and lock.
- Automatic or manually selected destination track when adding an asset.
- Clip selection and drag-to-move.
- Optional snap-to-seconds and timeline zoom.
- Playhead/frame scrubbing.
- Numeric start-frame and duration editing.
- Split at playhead, duplicate and delete.

The timeline model allows clips on separate tracks to overlap. A track lock prevents clip movement, trimming and deletion on that track.

### Current rendering boundary

This step creates an editable V2 timeline model and controls; it does **not** yet composite those V2 tracks into the legacy canvas preview or export them to a final video. The renderer/compositor integration is scheduled for later roadmap phases. The original version-1 drawing timeline still controls the original browser preview/export.

## 5. Persistence and recovery

The shared IndexedDB database is version 2. It preserves the existing `projects` store used by the version-1 editor and adds:

| Store | Purpose |
|---|---|
| `assets` | Imported binary Blobs plus media metadata and provenance |
| `v2projects` | Saved V2 project documents |
| `recovery` | Previous V2 project snapshots |

The V2 editor autosaves after changes. It keeps up to **six previous snapshots per project**, avoids creating recovery copies for unchanged content, and exposes a **Restore previous** control when history exists. Browser storage estimate and persistent-storage request controls are provided where supported.

### Important backup limitation

**Export JSON exports the editable V2 project document, not the binary media files.** Imported Blob assets remain in that browser's IndexedDB. A V2 JSON opened on another device can display missing-asset entries until those files are imported there. Keep the original media files separately; an all-in-one ZIP media package is not part of steps 6–10.

IndexedDB is subject to browser/device quota and eviction policy. The V2 panel can estimate usage and request persistent storage where the browser supports it, but permission is not guaranteed. Export the project JSON and keep source files backed up.

## 6. Automated checks

- `tests/ff-v2-core.test.js`: media classification/signature checks and timeline model operations.
- `tests/ff-v2-browser-smoke.js`: Chromium import, asset library, track editing, recovery and reload smoke test.
- `.github/workflows/ff-v2-foundation-tests.yml`: JavaScript/Python syntax, Node core tests, Python regression tests and schema/example validation.
- `.github/workflows/ff-v2-browser-smoke.yml`: free headless Chromium smoke workflow.

All workflows use read-only repository permissions and do not start production renders.
