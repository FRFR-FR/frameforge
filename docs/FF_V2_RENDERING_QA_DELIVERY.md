# FrameForge V2 — Rendering, QA, review and delivery (steps 41–45)

This batch adds a resumable browser frame queue and a local FFmpeg finishing toolchain. It deliberately does not claim that GitHub Pages can launch FFmpeg or run a native renderer. The browser compositor produces PNG frame chunks; FFmpeg encoding, media QA, review-sheet generation and delivery ZIP creation run locally where FFmpeg/ffprobe are installed.

## Step 41 — Resumable V2 frame render queue

The **Resumable V2 render queue** panel sits below the V2 timeline.

1. Finish and save the V2 sequence. Confirm the timeline duration and all linked media are correct.
2. Choose a chunk size (12, 24, 48 or 96 frames) and create a render job.
3. Press **Start / resume**. Each frame is composed by the V2 Canvas/Three.js compositor and saved as a PNG Blob in the dedicated IndexedDB `renderFrames` store. The job record is stored in `renderJobs`.
4. Press **Pause safely** to finish and persist the current frame before pausing. Close/reopen FrameForge to resume an interrupted job. Frames already present in IndexedDB are skipped; the queue records newly rendered and skipped frame counts.
5. Select a completed chunk and choose **Download completed chunk ZIP**. Each ZIP contains numbered PNG frames and `chunk-manifest.json` (job/project signature, chunk index, frame range, total frame count, resolution and FPS).

A job is tied to a project signature. If the project is edited after the job is created, resume is blocked; create a new job instead of mixing frames from different edit versions. The queue is local to the browser/device and subject to IndexedDB storage quotas. Export chunk ZIPs as backups before clearing browser data.

## Step 42 — FFmpeg export profiles

The local merge and encode path uses Python 3.10+ and FFmpeg/ffprobe. No paid API or hosted renderer is required.

Install FFmpeg/ffprobe and ensure both commands are on PATH. Merge downloaded chunks into a numbered PNG sequence:

```bash
python tools/merge_render_chunks.py --chunks-dir ./render-chunks --output-dir ./render-output
```

The merger is idempotent. Re-importing an identical chunk skips existing frames; an overlapping frame with different contents, an inconsistent project signature or a missing frame is rejected. It writes `render-output/render-frames.json` and returns a non-zero/incomplete status until all expected frames are present.

Encode a 720p horizontal MP4 with an optional stereo WAV master:

```bash
python tools/export_ffmpeg.py \
  --frames-dir ./render-output/frames \
  --output ./final-720p-horizontal.mp4 \
  --profile 720p-horizontal \
  --audio ./audio-master.wav
```

Available profiles:

| Profile | Output |
|---|---:|
| `720p-horizontal` | 1280 × 720 |
| `720p-vertical` | 720 × 1280 |
| `1080p-horizontal` | 1920 × 1080 |
| `1080p-vertical` | 1080 × 1920 |

Supported frame rates are 24, 25, 30, 50 and 60 FPS. Defaults are H.264/libx264, CRF 18, medium preset and AAC 192k at 48 kHz stereo when a WAV master is supplied. The exporter checks that the image sequence is complete, validates the PNG dimensions, then probes the finished MP4 and checks output dimensions, FPS, frame count and audio-stream presence. 1080p is optional and may be slow or exceed available memory/storage on phones and low-power devices.

## Step 43 — Automated technical QA

Run QA on the encoded video:

```bash
python tools/qa_render.py \
  --input ./final-720p-horizontal.mp4 \
  --expect-audio \
  --expected-width 1280 \
  --expected-height 720 \
  --expected-fps 30 \
  --expected-frames 900 \
  --json-out ./final-qa.json
```

Alternatively, pass `--expected-manifest ./render-output/render-frames.json` when the output has the same dimensions/FPS as the source frames. For a profile that resizes or changes orientation, use the explicit expected width/height/FPS arguments.

The QA pass checks:
- FFprobe video/audio streams, dimensions, frame rate, frame count and duration.
- Full FFmpeg decode (corrupt packets/frames).
- Black intervals lasting at least 0.5 seconds (failure by default).
- Possible frozen holds lasting at least 2 seconds (warning by default; `--strict-freeze` makes them failures).
- Audio-stream presence when `--expect-audio` is supplied, and sample peak/mean levels when audio exists.
- Optional declared sync markers (JSON entries with `label`, `video_frame` and `audio_seconds`).

A declared sync marker compares user-supplied video-frame and audio-time values; it does not detect a sync beep or estimate audio/video offset from the waveform. Human judgement is still required for intentional black shots, creative holds, pacing, intelligibility and subjective quality.

## Step 44 — Visual/audio review tools

Generate a review folder without opening every source frame:

```bash
python tools/create_review.py \
  --input ./final-720p-horizontal.mp4 \
  --output-dir ./review \
  --sample-interval 2.5
```

The tool creates:
- `contact-sheet.jpg`: sampled overview frames, laid out in a grid.
- `scene-previews/`: selected high-confidence scene-change stills (when FFmpeg detects them).
- `audio-waveform.png`: waveform preview when the MP4 has an audio stream.
- `review.json` and `review.html`: media facts, file links and a browser-readable review page.

The HTML review page is an inspection aid, not an automated creative approval.

## Step 45 — Delivery package and attribution notes

After QA and review, create a final delivery ZIP:

```bash
python tools/package_delivery.py \
  --video ./final-720p-horizontal.mp4 \
  --project ./frameforge-project.json \
  --qa-report ./final-qa.json \
  --review-dir ./review \
  --output ./final-delivery.zip
```

The package contains the MP4, editable project JSON, a generated asset provenance/rights manifest, attribution notes, a render report, the optional QA report and review folder. The command prints the MP4 and ZIP sizes in MB, format, dimensions, FPS, duration and codec information.

The attribution notes list approved credits, usage restrictions and any assets still pending/unresolved. Pending, restricted, rejected and unknown assets are not cleared by packaging. This is a user-metadata report, not independent licence verification or legal advice.

**Binary-media limitation:** V2 project JSON stores asset references and metadata, not imported binary media held in browser IndexedDB. The delivery package cannot retrieve those browser-only Blobs. Include separately exported media with repeatable `--extra PATH` arguments when the recipient needs the source files to reopen the edit.

## Local pipeline summary

```bash
# 1. Merge the ZIP chunks exported from the V2 browser queue.
python tools/merge_render_chunks.py --chunks-dir ./render-chunks --output-dir ./render-output

# 2. Encode H.264 MP4 (add --audio ./audio-master.wav when available).
python tools/export_ffmpeg.py --frames-dir ./render-output/frames --output ./final.mp4 --profile 720p-vertical

# 3. Run technical checks. Set expected output dimensions for the selected profile.
python tools/qa_render.py --input ./final.mp4 --expected-width 720 --expected-height 1280 --expected-fps 30 --expect-audio --json-out ./qa.json

# 4. Build visual/audio review artefacts.
python tools/create_review.py --input ./final.mp4 --output-dir ./review

# 5. Package the final MP4, project, rights notes, QA and review.
python tools/package_delivery.py --video ./final.mp4 --project ./project.json --qa-report ./qa.json --review-dir ./review --output ./delivery.zip
```

The browser frame queue can render and save chunks on-device, but final FFmpeg encoding and Python packaging require a local or otherwise authorised free environment with FFmpeg installed. GitHub-hosted compute is not started automatically, no paid runner is selected, and no continuous render job is created.

## Verification

Verified on code commit `5fcca0a0109654eead76edc1c2d871df4cbb5a30`:

- [Foundation Validation run 46141969613 — success](https://github.com/FRFR-FR/frameforge/actions/runs/46141969613): **74 JavaScript tests passed** and **42 Python tests passed**, including real FFmpeg export, output probing, black-frame/audio QA, review artefacts and delivery packaging.
- [Browser Smoke run 46141969605 — success](https://github.com/FRFR-FR/frameforge/actions/runs/46141969605): all five V2, audio, director, production and render-queue Chromium smoke tests passed. The queue fixture persisted two PNG frames, paused, resumed without rendering those frames again, exported a ZIP chunk and survived a page reload.
- [Latest GitHub Pages deployment — success](https://github.com/FRFR-FR/frameforge/actions/runs/46142236482): the updated 1–45 progress documentation was deployed.


