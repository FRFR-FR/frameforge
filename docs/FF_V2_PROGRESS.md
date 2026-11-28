# FrameForge V2 — Upgrade Progress

**Canonical roadmap:** [FF_V2_50_STEP_ROADMAP.md](FF_V2_50_STEP_ROADMAP.md)  
**Current completed batch:** Steps 1–10  
**Last updated:** 2026-11-28

## Batch 1–5 status

| Step | Deliverable | Status | Verification |
|---:|---|---|---|
| 1 | Baseline repository/application/workflow audit | Complete | Reviewed source entry points and all 25 workflow YAML files; audit report committed |
| 2 | V2 architecture and zero-cost/media-rights policy | Complete | Architecture, cost and rights policy documents committed |
| 3 | Automated foundation validation | Complete | GitHub Actions run 46107773272 succeeded; all 14 unit tests passed, plus JavaScript/Python syntax checks |
| 4 | Versioned project format | Complete | Draft 2020-12 project schema validated; example project passes schema and semantic checks |
| 5 | Media provenance/rights manifest | Complete | Draft 2020-12 manifest schema validated; sample manifest passes; duplicate IDs and incomplete approvals are rejected |

## Step 1 — Audit

Created [FF_V2_BASELINE_AUDIT.md](FF_V2_BASELINE_AUDIT.md). It documents current application entry points, the existing Canvas and FF3D limits, Blender and FFmpeg production paths, the 25 workflow inventory, operational risks and baseline verification commands.

## Step 2 — Architecture and cost policy

Created:
- [FF_V2_ARCHITECTURE.md](FF_V2_ARCHITECTURE.md)
- [FF_V2_COST_AND_RIGHTS_POLICY.md](FF_V2_COST_AND_RIGHTS_POLICY.md)

The core production path has no mandatory paid API, AI-generation, stock-media, editing subscription or cloud-render service. Free compute, storage and artifact quotas remain finite; workflows must stop safely rather than silently incur charges.

## Step 3 — Test foundation

Created:
- [requirements-dev.txt](../requirements-dev.txt)
- [tests/test_ff_v2_foundations.py](../tests/test_ff_v2_foundations.py)
- [ff-v2-foundation-tests.yml](../.github/workflows/ff-v2-foundation-tests.yml)

GitHub Actions run: [46107773272 — success](https://github.com/FRFR-FR/frameforge/actions/runs/46107773272).

Result from the final workflow log: **14 tests passed**. Both example validators also passed. The workflow also completed `node --check app.js`, `node --check frameforge-3d.js` and Python `compileall` for the existing source folders. It uses read-only repository permissions, is path-scoped and does not invoke any video-render workflow.

The run emitted an upstream maintenance warning that checkout/setup-python actions currently target a deprecated Node 20 runtime and were forced to Node 24 by the runner. The test job itself completed successfully; action-version maintenance should be reviewed as part of a later maintenance step.

## Step 4 — Versioned project schema

Created:
- [frameforge-project-v2.schema.json](../schemas/frameforge-project-v2.schema.json)
- [frameforge-project-v2.example.json](../examples/frameforge-project-v2.example.json)
- [opening-grid.svg](../examples/assets/opening-grid.svg)
- [validate_project.py](../tools/validate_project.py)

The schema defines project metadata, output settings, assets, source/rights metadata, sequences, tracks, clips, transforms, keyframes, effects, transitions and optional research/creative-brief fields. The validator checks schema rules, duplicate identifiers, missing asset/sequence references, sequence frame bounds and evidence-source/claim references.

The existing browser editor's version-1 project format has **not** been migrated or replaced. Migration is a later implementation task and must be explicit.

## Step 5 — Media rights manifest

Created:
- [media-asset-manifest-v1.schema.json](../schemas/media-asset-manifest-v1.schema.json)
- [media-asset-manifest.example.json](../examples/media-asset-manifest.example.json)
- [validate_media_manifest.py](../tools/validate_media_manifest.py)

The format records source classification, source URL, creator/provider, acquisition time, technical metadata, licence/permission basis, attribution and reviewer state. Approved assets require a review basis, reviewer and review timestamp; attribution-required assets must include attribution text. The sample includes a deliberately pending placeholder to demonstrate that unknown rights are not silently approved.

## Batch 6–10 status

| Step | Deliverable | Status | Verification |
|---:|---|---|---|
| 6 | Media import and validation | Complete | Browser smoke imported and decoded a generated PNG; importer includes MIME/extension checks, signature checks, metadata reads and SVG safety checks |
| 7 | Asset library and search | Complete | Browser smoke confirmed the asset library stores, previews and reloads the imported image; search, type filtering and tags are wired |
| 8 | Multi-track timeline data model | Complete | 17 Node tests pass for project creation, tracks, asset clips, references and timing |
| 9 | Timeline editing UI and controls | Complete | Chromium smoke exercised two tracks, playhead, drag-compatible clip selection, numeric timing, split, duplicate, delete, mute and lock/visibility controls |
| 10 | Persistence, autosave and recovery | Complete | Chromium smoke saved, restored a previous project version, reloaded the page and recovered the project plus imported asset from IndexedDB |

## Step 6 — Media import and validation

Created:
- [ff-v2-core.js](../ff-v2-core.js)
- [ff-v2-studio.js](../ff-v2-studio.js)
- V2 import controls in [index.html](../index.html)

Supports raster images (PNG, JPEG/JPG, GIF, WebP, BMP, AVIF), SVG, video (MP4/M4V, MOV, WebM, OGV), audio (MP3, WAV, OGG/OGA, FLAC, M4A, AAC), and glTF 2.0/GLB model assets. The importer validates extension/MIME family and container signatures where practical, decodes images for dimensions, reads browser-accessible audio/video metadata, validates GLB/glTF headers, records external glTF dependencies, and rejects active/external SVG content. Each file is limited to 250 MB; SHA-256 is computed for files up to 32 MB.

Browser codec support is device-dependent. If the browser cannot read a media container/duration, it rejects the import rather than claiming successful validation.

## Step 7 — Asset library and search

The V2 Assets panel includes thumbnail previews or media-type glyphs, search across names/MIME/tags, type filters, editable tags, file size/dimension/duration metadata, rights state, and Add to timeline. Actual imported file bytes are stored as Blob records in IndexedDB. Imported assets default to `user_supplied` provenance and rights status `pending`; import does not grant or infer publication rights.

## Step 8 — Multi-track project data model

The V2 project starts with seven separate tracks: video, images/cut-outs, graphics, titles, voiceover, music and SFX. The core supports track creation; asset/clip references; independent clip start/duration; snap-based moves; trim; split; duplicate; delete; lock enforcement; clip bounds and missing-asset validation. The project schema stores transforms, keyframe/effect arrays and sequence settings for future compositor integration.

## Step 9 — Multi-track editing UI

Integrated a dedicated V2 multi-track timeline below the existing frame-based animation strip. It provides:
- Add-track control and automatic/manual destination track selection.
- Track visibility/enable, mute and lock toggles.
- Time ruler, playhead, zoom and optional snap-to-second behaviour.
- Clip selection and drag-to-move.
- Numeric start/duration editing, split at playhead, duplicate and delete.

The original version-1 frame strip and drawing editor remain available and unchanged as a separate workflow.

## Step 10 — Persistence and recovery

The shared IndexedDB database was upgraded from version 1 to version 2. The existing `projects` store is preserved; V2 adds `assets`, `v2projects` and `recovery` stores. V2 autosaves its structured project, keeps up to six previous snapshots per project, offers Restore previous, reports local storage usage and requests persistent storage where supported by the browser.

**Backup limitation:** V2 project JSON exports the editable project structure, not the imported binary assets. Asset blobs remain in the originating browser's IndexedDB. Opening that JSON on another device can therefore display missing-asset references until those files are imported locally. This is documented in [FF_V2_MEDIA_AND_TIMELINE.md](FF_V2_MEDIA_AND_TIMELINE.md).

## Verification for batch 6–10

- [Foundation validation run 46109013911 — success](https://github.com/FRFR-FR/frameforge/actions/runs/46109013911): 17 Node core tests passed, 14 Python regression tests passed, JS syntax checks passed, Python source compile checks passed, and both project/rights manifest example validators passed.
- [Chromium browser smoke run 46109013937 — success](https://github.com/FRFR-FR/frameforge/actions/runs/46109013937): real browser imported/decode-tested an image, managed assets, edited independent timeline tracks and clips, saved/restored recovery, and verified persistence after reload.
- Both workflows use read-only repository permissions and do not launch Blender/video-production renders.

## Important limits / not yet done

- The V2 multi-track editor and project model now exist, but the V2 timeline is **not yet connected to a final compositor or video export renderer**. The current V2 UI edits project data; it does not yet composite its tracks into the legacy canvas preview or final MP4. That is planned for later rendering/compositing stages.
- Audio tracks are currently timeline data/clip types only; a playable audio mixer, SFX event engine and final audio mux are later steps 26–30.
- Imported media metadata validation relies partly on browser codecs; unsupported media is rejected, and a metadata check is not a full decode of every frame/sample.
- Project JSON does not package the actual imported files. Blob assets remain local to the original browser's IndexedDB; keep separate copies of source media.
- Local browser storage is quota-limited and can be evicted. The persistent-storage request is best-effort, not guaranteed.
- The rights validator checks metadata completeness; it does not determine legal rights or provide legal advice.
- The 250 MB per-file import ceiling may exceed the browser's available storage quota on some devices.
- Steps 6–10 did not change or invoke any existing Blender render production workflows.

## Next batch

Wait for the user to request the next batch. Do not start steps 11–15 automatically.
