# FrameForge V2 — operation and handover

## 1. Open the editor

FrameForge is hosted as a static GitHub Pages application. Open the Pages URL for this repository in a current Chromium browser. The legacy V1 editor remains available; select **V2 Assets** for the V2 project and asset workspace. On a phone, use the bottom dock to jump to Assets, Timeline, Director, Produce and Render.

Android-specific storage and operation notes are in [FF_V2_MOBILE.md](FF_V2_MOBILE.md).

## 2. Back up an editable project

- Use the V2 project controls to export the project JSON regularly.
- Imported binary media is stored in the originating browser's IndexedDB and is not embedded in the project JSON. Keep the original files in a separate folder/cloud drive of your own and include those files in a delivery package when handing the project over.
- Export browser render-queue chunk ZIPs as they complete. Keep a second copy outside the browser.
- Do not clear site data or change browser/device before exporting the project and source media.

## 3. Clean local setup

Use Python 3.12 and install the pinned development requirements:

```bash
git clone https://github.com/FRFR-FR/frameforge.git
cd frameforge
python -m pip install -r requirements-dev.txt
```

Install FFmpeg and ffprobe from a trusted package source for your operating system. Run the validation and tests:

```bash
python -m unittest discover -s tests -p "test_*.py" -v
node --test tests/ff-v2-core.test.js tests/ff-v2-renderer.test.js tests/ff-v2-audio.test.js tests/ff-v2-director.test.js tests/ff-v2-production.test.js
python tools/validate_project.py examples/frameforge-project-v2.example.json
python tools/validate_project.py examples/frameforge-research-director.example.json
python tools/validate_media_manifest.py examples/media-asset-manifest.example.json
```

The project has no mandatory remote rendering service or paid image-generation dependency. The Pillow dependency is used by the two procedural pilot renderers and is pinned in `requirements-dev.txt`.

## 4. Render the demonstration pilots

The two original, editable pilots live in:
- `projects/v2-pilots/entertainment-power-scale/`
- `projects/v2-pilots/cybersecurity-phishing-check/`

Render locally with FFmpeg installed:

```bash
python tools/render_v2_pilots.py --pilot entertainment --output-dir artifacts/pilots/entertainment
python tools/render_v2_pilots.py --pilot cybersecurity --output-dir artifacts/pilots/cybersecurity
```

Each render is 12 seconds at 1280×720 and 24 FPS. It contains original procedural visuals and synthesized SFX; the separate `narration.txt` is a draft for recording, not a voice track embedded in the MP4. Run `tools/qa_render.py`, `tools/create_review.py` and `tools/package_delivery.py` before considering a revised render publication-ready. Inspect the review page and listen to the MP4.

## 5. Render a V2 project from the browser

1. Open the **Render Queue** panel and choose the chunk size.
2. Start a render and allow the queue to save PNG frames to IndexedDB.
3. Export each completed chunk ZIP. A job can resume from stored frames while the IndexedDB records remain.
4. Move those ZIPs to a computer with Python, FFmpeg and ffprobe.
5. Follow the exact merge/export/QA/review/package commands in [FF_V2_RENDERING_QA_DELIVERY.md](FF_V2_RENDERING_QA_DELIVERY.md).

For Shorts, use the `720p-vertical` profile; for landscape video, use `720p-horizontal`. The local render pipeline is CPU-only by default and can take time for longer sequences.

## 6. GitHub Actions operations and limits

- **Foundation Validation** runs tests and schema checks.
- **Browser Smoke** exercises the real Chromium editor and V2 queue/mobile journeys.
- **Pilot Builds and QA** renders the two small demo videos and uploads an artifact.
- **Manual Operations (Cost-Capped)** must be started explicitly from the Actions page. It only accepts small paths under `render-input/`, caps frame count, input size, resolution, duration, output size and runner time, and retains output artifacts for three days.
- **Publish Release** is also manual. From the `main` branch, enter a semantic tag such as `v2.0.0`. It checks successful prerequisite CI results and reruns the core validation suites before tagging.

These jobs use standard GitHub-hosted CPU runners, but GitHub account/repository quotas are finite and depend on repository/account settings. No workflow automatically starts paid or larger infrastructure. Do not place private media or secrets in this public repository.

## 7. Rollback and recovery

- To roll back a code release, use GitHub's **Revert** action on the offending commit or revert the release commit with Git. Do not force-push shared history.
- A Git revert does not restore a browser's IndexedDB contents or reverse local project edits. Preserve exported project JSON, source media and render ZIPs before changing code.
- If a local export fails, retain the original chunk ZIPs and rerun the idempotent merger; do not discard the source chunks.
- If a render job signature no longer matches the current project, create a new job rather than trying to combine chunks from different edits.
- A QA warning is not automatically a fault. Inspect the contact sheet and the named timestamp range; adjust the scene or document intentional holds before release.

## 8. Human acceptance checklist

- [ ] Project JSON opens and the original source assets are present.
- [ ] All media rights records are reviewed, with attribution included where needed.
- [ ] Correct frame size, FPS, duration and audio streams are confirmed.
- [ ] Contact sheet, scene previews and waveform are inspected.
- [ ] MP4 is watched end-to-end and the audio is listened to.
- [ ] Narration is recorded, mixed and checked for sync when a narrated episode is required.
- [ ] Final project JSON, binary source assets, render report, QA report and delivery ZIP are backed up.
