# FrameForge V2 — Upgrade Progress

**Canonical roadmap:** [FF_V2_50_STEP_ROADMAP.md](FF_V2_50_STEP_ROADMAP.md)  
**Current completed batch:** Steps 1–35  
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

## Batch 11–15 status

| Step | Deliverable | Status | Verification |
|---:|---|---|---|
| 11 | Canvas 2D layer compositor and alpha pipeline | Complete | Chromium smoke verifies a 1280 × 720 frame, semi-transparent PNG alpha retention (sampled alpha 126–130), and untouched transparent pixels (alpha 0); layers render in track order |
| 12 | Transform, crop, anchor, fit and opacity controls | Complete | Studio controls are connected to the clip model and compositor; Node tests validate normalized crop bounds, fit modes and opacity range |
| 13 | Transform keyframes, easing and layer parenting | Complete | Node tests cover linear/eased/Bezier interpolation, parent transform inheritance and cycle rejection; browser smoke adds a keyframe through the UI |
| 14 | Shape masks, alpha/luma mattes, feathering and blend modes | Complete | Node tests validate mask model constraints; Chromium smoke exercises a feathered ellipse mask and its inverted form; alpha/luma matte rendering is implemented but not separately pixel-tested in Chromium |
| 15 | Typography, lower thirds, SVG and vector shapes | Complete | Generated title/lower-third, shape and SVG clips are connected to the compositor; browser smoke composites generated vector artwork; SVG validation rejects active/external content |

## Step 11 — Layer compositor and alpha pipeline

Created [ff-v2-renderer.js](../ff-v2-renderer.js), a dependency-free Canvas 2D compositor. It resolves imported local image/SVG/video assets, orders visual layers by track order, renders each layer to an isolated transparent surface, and composites into an output canvas matching the sequence dimensions. The output is cleared to transparent for each render; untouched pixels stay transparent, and browser Canvas 2D performs the premultiplied-alpha compositing.

The V2 editor now displays the compositor canvas beneath the multi-track timeline. **Render frame** rerenders the current playhead frame and **Download PNG** exports that one frame. Rendering is queued to avoid stale asynchronous preview frames replacing newer ones.

## Step 12 — Transform, crop and anchor controls

Selected clips expose position X/Y, scale X/Y, rotation, opacity, anchor X/Y, fit mode and optional normalized source crop. Supported fit modes are contain, cover and stretch. These are non-destructive clip-level properties and are evaluated by the same compositor transform path.

## Step 13 — Keyframes, easing and parenting

Transform keyframes use clip-local frame positions and support position, scale, rotation, opacity and anchor properties. Interpolation supports step, linear, ease-in, ease-out, ease-in/out and cubic Bezier. Parent-child relationships propagate transforms and opacity; audio clips cannot be visual parents. Self-parenting and cycles are rejected by the project model.

## Step 14 — Masks, mattes and blend modes

The renderer supports rectangle/ellipse shape masks, inversion, feathering, alpha mattes and luma mattes. Matte sources are imported local image/graphic assets. The editor includes a curated list of Canvas blend modes, with normal compositing as the fallback for unsupported modes. Mask bounds are normalized against the sequence canvas. The Chromium smoke test pixel-checks a feathered ellipse mask and inverted result; alpha/luma matte modes are implemented but do not yet have a dedicated pixel-level browser fixture.

## Step 15 — Typography, SVG and shape graphics

Added generated title, lower-third, shape and inline-SVG clips on the Graphics/Titles tracks. Text supports font family, size, weight, colour, alignment, multiline content, optional background, outline and shadow parameters in the rendering layer. Shapes support rectangle, ellipse, line and polygon primitives. Generated graphics use the same transform, keyframe, parent, mask and blend pipeline as imported visual media. SVG input is validated before it is drawn.

## Verification for batch 11–15

- [Foundation validation run 46109813955 — success](https://github.com/FRFR-FR/frameforge/actions/runs/46109813955): JavaScript syntax checks passed; **23 Node tests passed**; **14 Python regression tests passed**; the V2 schema and both example validators passed.
- [Chromium browser smoke run 46109813917 — success](https://github.com/FRFR-FR/frameforge/actions/runs/46109813917): verified local asset import and timeline persistence, 1280 × 720 compositing, semitransparent PNG alpha retention, untouched transparent canvas pixels, generated vector artwork, transform controls, keyframe creation, feathered shape mask and inverted-mask pixel output.


## Batch 16–20 status

| Step | Deliverable | Status | Verification |
|---:|---|---|---|
| 16 | Seeded particle and procedural effect system | Complete | Node tests verify stable seeded random sequences and saved particle presets; Chromium smoke renders the same particle frame twice and compares pixel hashes |
| 17 | Optional GPU post-processing and shader framework | Complete with implementation adaptation | Local WebGL 1 shader pipeline with capability detection, ordered passes, custom GLSL and Canvas 2D fallback; browser smoke exercises the custom-shader path without a page error |
| 18 | Lighting, glow and atmospheric effects | Complete | Five named looks and built-in glow, light rays, vignette, blur, colour adjustment and depth-of-field passes; Canvas fallback path is browser-tested |
| 19 | Distortion, stylised effects and speed ramps | Complete | Node tests cover effect parameter keyframes and per-frame source-time integration; browser smoke adds and keyframes a glitch effect and playback rate |
| 20 | Editable clip-edge transition library | Complete | Node tests validate transition setup, direction and timing; Chromium smoke sets incoming wipe and outgoing fade and checks the saved clip controls |

**Step 17 design note:** the roadmap named Three.js EffectComposer. This implementation uses a browser-native WebGL 1 shader pipeline instead, with a Canvas 2D fallback. That keeps the 2D post-processing stack independent of Three.js EffectComposer. The separately vendored Three.js r164.1 runtime in step 21 is used for 3D scene/model rendering, not as the post-processing framework.

## Step 16 — Particle and procedural effects

Generated particle clips are stored as editable timeline clips. Presets are sparks, dust, embers, magic and confetti. The renderer uses seeded procedural randomness and stores the seed and particle parameters in the project so a fixed project/frame renders repeatably. Particle count is clamped to 500 to protect browser memory and processing time.

## Step 17 — GPU post-processing and shader framework

Created [ff-v2-shaders.js](../ff-v2-shaders.js). It probes WebGL availability and precision, compiles local GLSL programs, runs enabled post-processing passes in their saved order, and preserves source alpha in built-in fragment passes. The user can select automatic, WebGL-preferred or Canvas 2D-only mode. A custom GLSL editor stores the shader source in project settings; compilation failures and unavailable WebGL are reported and built-in effects fall back to Canvas 2D. Custom GLSL is skipped explicitly when only Canvas 2D is available.

## Step 18 — Lighting, glow and atmosphere

Added ordered passes for brightness/contrast, saturation, vignette, blur, glow/bloom, light rays and depth of field. Named presets are Cinematic, Soft glow, Noir, Documentary and Dream haze. Clip-level versions of the lighting/atmosphere effects can be placed on individual visual layers. The compositor status reports which backend was used for the frame.

## Step 19 — Distortion and stylised effects

Clip effects include glitch, chromatic aberration, ripple/warp, camera shake, motion blur, blur, glow, vignette, brightness/contrast, saturation, light rays and depth of field. Effect intensity is keyframable in local clip time. The existing playback-rate property now supports keyframes for speed ramps; the renderer integrates the prior frame rates to calculate the media source time for the current frame.

## Step 20 — Transition library

Transitions are attached to clip-in or clip-out edges with duration in frames, direction and intensity. Types are fade, crossfade, directional wipe, zoom, whip pan, radial, hypnosis wheel, swirl/warp and glitch. Transitions are computed deterministically from the current clip edge and frame. A crossfade is opacity-based, so it requires overlapping clips/layers to show the second shot underneath the first.

## Verification for batch 16–20

- [Foundation validation run 46117366648 — success](https://github.com/FRFR-FR/frameforge/actions/runs/46117366648): JavaScript syntax checks passed; **31 Node tests passed**; **14 Python regression tests passed**; project/media schema and example validation passed.
- [Chromium browser smoke run 46117366641 — success](https://github.com/FRFR-FR/frameforge/actions/runs/46117366641): the expanded browser test passed with no page errors. It verifies multi-track project persistence, 720p compositor alpha, deterministic repeated particle frames, clip-effect keyframes, incoming/outgoing transitions, playback-rate keyframes, ordered Canvas 2D atmosphere passes and the optional WebGL/custom-shader fallback control path.

## Batch 21–25 status

| Step | Deliverable | Status | Verification |
|---:|---|---|---|
| 21 | Offline, pinned Three.js runtime | Complete | Three.js r164.1 + GLTFLoader + SkeletonUtils bundle is committed in `vendor/three/0.164.1/`; MIT licence and SHA-256 manifest are included; no CDN runtime dependency |
| 22 | GLB/glTF model/material import | Complete | Chromium smoke imports an actual animated GLB, decodes mesh/bounds/animation metadata and adds it to a Scene 3D track; external glTF dependencies can be resolved from local assets |
| 23 | Scene camera, lighting and environment | Complete | Serializable perspective/orthographic camera, lights, background/alpha and render settings are controlled from the V2 scene panel; browser smoke updates camera and lighting |
| 24 | Model transform, animation and contacts | Complete with documented approximations | AnimationMixer playback, transform keyframes, parent/look-at and ground/AABB constraints; Node and Chromium tests exercise 3D transforms and animation selection |
| 25 | Blender scene interchange and render bridge | Complete | Portable ZIP exporter includes model files and dependencies, manifest and Python bridge; Blender CI imports an embedded animated glTF, builds `.blend`/`.glb`, renders PNG using CPU Cycles and uploads output |

## Step 21 — Controlled offline Three.js runtime

The previous temporary Three.js build workflow was replaced with a versioned vendor build. Three.js **r164.1** is bundled locally with GLTFLoader and SkeletonUtils.clone. The committed minified runtime is 712,826 bytes (about 696 KiB), with its MIT licence and `runtime-manifest.json` SHA-256 checksum beside it. The browser loads it from `vendor/three/0.164.1/`; no runtime CDN request is required.

Build workflow: [offline Three.js bundle build 46119591590 — success](https://github.com/FRFR-FR/frameforge/actions/runs/46119591590).

The older dependency-free `frameforge-3d.js` remains available. V2 feature-detects WebGL for the imported glTF scene renderer. If WebGL cannot be created, 2D editing/compositing remains available and 3D model frames report a warning.

## Step 22 — GLB/glTF models and materials

The V2 asset inspector uses the local GLTFLoader to decode GLB and glTF 2.0. The asset library records model/mesh count, bounds, dimensions and animation clip names/durations. Embedded GLB buffers/textures are handled by the file loader. A `.gltf` document with external `.bin` or image resources resolves those resources against already imported local asset records; import the referenced dependency files before importing the `.gltf`. Dependency paths are saved as metadata and reproduced in the Blender ZIP.

## Step 23 — 3D scene, cameras and lighting

Every default V2 sequence now has a serializable `scene3d` settings block. The editor exposes perspective/orthographic camera, position/target/FOV, scene colour/transparency, ambient/key light intensity and tone mapping. The schema also permits additional point/spot lights, light colour/positions/directions, orthographic size, clipping planes, exposure and shadow settings.

The Three renderer draws the GLTF scene to its own WebGL canvas; the V2 compositor places that scene output into the selected sequence-resolution frame.

## Step 24 — 3D animation and contact constraints

GLTF animation clips play through Three.js AnimationMixer. The V2 clip inspector exposes clip selection, playback rate, enabled state and looping, plus XYZ position/rotation/scale. Those transform axes are supported by the V2 keyframe editor. SkeletonUtils.clone is used for independent model instances.

Model constraints are stored in the project and include parent-to-model, look-at, ground contact and approximate AABB contact. Ground/AABB are deterministic convenience approximations, not a complete physics solver. The Three.js path uses Y-up coordinates; the Blender bridge converts camera, light and imported model transforms into Blender's Z-up coordinate system. Per-axis Euler keyframes are mapped to the corresponding Blender axes; complex multi-axis Euler combinations may not be numerically identical after conversion. Advanced rig authoring, retargeting and simulation remain Blender tasks.

## Step 25 — Blender bridge and interchange

The **Export Blender bridge ZIP** action packages the current sequence settings, camera/lights/environment, model clip timing/transform/animation/keyframes/constraints, local GLB/glTF source files and referenced external resources, plus `tools/frameforge_blender_bridge.py` and a usage README. It rejects missing dependencies instead of exporting a broken package.

The bridge has `build` mode (save editable `.blend` and export `.glb`) and `render` mode (render an RGBA PNG at a specified frame). The PNG is imported back into V2 through the normal local asset import workflow; a whole Blender video sequence is not automatically merged into the V2 timeline.

- [Browser smoke run 46120638371 — success](https://github.com/FRFR-FR/frameforge/actions/runs/46120638371): imports the bundled runtime's animated GLB, verifies mesh/animation metadata and UI controls, stores a 3D transform keyframe, edits scene camera/lighting and validates the downloaded Blender ZIP header/content.
- [Blender bridge run 46120638375 — success](https://github.com/FRFR-FR/frameforge/actions/runs/46120638375): bridge Python tests passed; Blender 4.0.2 built an editable scene and GLB, rendered a PNG frame with CPU Cycles and uploaded the outputs as an Actions artifact.
- [Foundation validation run 46120530579 — success](https://github.com/FRFR-FR/frameforge/actions/runs/46120530579): **36 JavaScript tests passed** and **18 Python tests passed**, including the new 3D scene/model/constraint tests and Blender bridge helper tests.
- The browser and Blender runs above include the final Y-up-to-Z-up conversion and model clip identity changes; both completed successfully. Blender uploaded the editable `.blend`, exported `.glb`, rendered PNG and related scene outputs as the `FrameForge-V2-Blender-Bridge-Test` artifact.
## Batch 26–30 status

| Step | Deliverable | Status | Verification |
|---:|---|---|---|
| 26 | Multi-track audio engine | Complete | Voiceover, music, SFX and general audio tracks have independent clip/track gain, pan, mute/solo, placement and fades; Node render tests and Chromium import/export test pass |
| 27 | Waveforms and audio sync | Complete | Web Audio decodes imported audio, the selected clip displays a peak waveform, waveform seeking is frame-based, and audio-player preview synchronizes the shared playhead |
| 28 | Event-triggered SFX | Complete | SFX cues can trigger at the playhead or at visual clip start/end; Node tests verify cue resolution follows the referenced clip |
| 29 | Mixing and automation | Complete | Clip-local gain keyframes, interpolation, track/clip gain, pan, fades, mute/solo, music ducking and peak normalization are implemented and regression-tested |
| 30 | WAV master and FFmpeg mux | Partial | 48 kHz stereo PCM16 WAV mastering and an end-to-end FFmpeg mux utility are tested; automatic V2 full-sequence picture render/mux remains blocked on the later full-sequence video renderer |

## Step 26 — Multi-track audio engine

Created [ff-v2-audio.js](../ff-v2-audio.js) and connected it to the V2 workspace. Voiceover, Music and SFX remain separate default tracks; additional Audio tracks can be used for dialogue or ambience. Clips keep their independent timeline position and duration with gain, pan, mute, fade-in and fade-out settings. Track gain, pan, solo, mute and enabled state affect the rendered mix. Audio data is stored in the V2 project model, not baked into the video compositor.

## Step 27 — Waveforms and audio sync

Audio assets are decoded through the browser Web Audio API. Selecting an audio clip displays its peak waveform; clicking/tapping the waveform seeks the shared playhead in frame units. During preview of the rendered audio master, the playhead follows the audio player's current time. Standard WAV duration is also read from its RIFF container metadata when the browser does not provide duration metadata.

## Step 28 — SFX event cues

SFX cues reference imported audio assets and can be placed at the current playhead or attached to a visual clip's start/end. Clip-linked cues resolve their timeline frame from the referenced clip ID, so moving or trimming that visual clip also changes the cue's resolved position. Cue data is serialized in the `extensions.ffv2_audio` project extension.

## Step 29 — Mixing and automation

Clip gain automation is stored as clip-local frame/gain keyframes with linear interpolation. The mix renderer evaluates track and clip gain, stereo pan, fades, mute/solo, and optional voiceover-triggered music ducking. It performs a peak scan and normalizes the exported PCM master toward -1 dBFS. Preview is an offline render followed by local audio playback, not a live low-latency mixer.

## Step 30 — Audio master and FFmpeg mux

The audio engine renders a 48 kHz stereo PCM16 WAV master. Added [tools/mux_ffmpeg.py](../tools/mux_ffmpeg.py) to map an already-rendered silent picture with the WAV master, pad/trim the audio to the measured picture duration, target -16 LUFS integrated loudness and -1.5 dBTP, encode AAC and verify the resulting MP4 streams/duration.

**Important boundary:** the V2 compositor currently exports the selected frame as PNG, not a full sequence MP4. The mux utility therefore accepts a silent video rendered by an existing renderer; automatic V2 timeline-to-MP4 export is not yet complete.

## Verification for batch 26–30

- [Foundation validation run 46126529805 — success](https://github.com/FRFR-FR/frameforge/actions/runs/46126529805): **45 JavaScript tests passed**, **22 Python tests passed**, including an end-to-end FFmpeg mux test that verifies 48 kHz stereo AAC output and duration; schema/example validation and JavaScript/Python syntax checks passed.
- [Chromium browser smoke run 46126529789 — success](https://github.com/FRFR-FR/frameforge/actions/runs/46126529789): existing V2 visual smoke and new audio browser smoke passed. The audio test imported/decoded WAV, drew and sought the waveform, synchronized the frame playhead, exercised track solo/gain and clip fades/automation, created an SFX marker and downloaded a valid 48 kHz stereo PCM16 WAV master.
- Audio implementation notes and the manual mux command are in [FF_V2_AUDIO.md](FF_V2_AUDIO.md).

## Batch 31–35 status

| Step | Deliverable | Status | Verification |
|---:|---|---|---|
| 31 | Structured production brief and research intake | Complete | Brief stores topic, niche, audience, platform, duration, script, restrictions, research questions and ambiguities; Node and Chromium tests cover save and reload |
| 32 | Research dossier and reference-video records | Complete with transparent manual/assistant-led intake | Sources store URL/title/publisher/publication and retrieval dates, type, access state and confidence; reference videos are permanently marked reference-only; no private-page scraping or access bypass |
| 33 | Editable niche visual style profiles | Complete | Distinct cybersecurity, history, science, mysteries, finance, gaming, entertainment/power-scaling and general profiles; browser smoke customises and saves one |
| 34 | Narration-to-shot visual director | Complete as a deterministic first-pass planner | Script is split into paragraph/sentence beats and allocated frame ranges; each beat includes visual purpose, media mix, camera, actions, VFX, transitions, assets and audio cues; the user can edit each field |
| 35 | Evidence and rights review gate | Complete as a workflow safeguard, not legal advice | Verified factual/comparative shots must link to source-backed claims; restricted sources are blocked; actual footage/screenshots require linked media assets; imported assets need documented user-reviewed rights decisions |

## Step 31 — Production brief

Added the Research & Visual Director panel to the V2 workspace. The structured brief records topic, niche, target audience, platform, target duration, tone, desired style, visual direction, narration/script, research questions, ambiguities/assumptions and production/legal/platform restrictions. Research questions are also copied into the dossier. The brief remains optional for older V2 projects and is saved in schema version 2.

## Step 32 — Research and reference-video dossier

Added source records for public URLs, titles, publishers, publication/retrieval dates, source type, access status, confidence and notes. Claims are stored separately and reference source IDs. Reference-video records capture title, creator, platform, dates, access status and format observations, and are always marked `reference_only: true`. The editor does not scrape pages, bypass login restrictions or independently verify a claim. Research is assistant-led or user-supplied; exact sources and confidence must be recorded. A reference video's style is not permission to reuse its protected footage, audio, branding or edit.

## Step 33 — Niche-specific style profiles

Created editable starting profiles for cybersecurity, history, science, mysteries/investigations, finance, gaming, entertainment/power-scaling and general/unclassified work. Profiles store visual language, preferred media, pacing, camera language, sound language and avoid/no-go rules. The user can load a profile, edit it and save the result to the V2 project.

## Step 34 — Narration-to-shot visual director

The first-pass planner divides the narration into timed beats, allocates each beat a start/end frame based on word-count weighting and the sequence frame rate, and suggests a topic-relevant media mix. Shot records include narration, visual purpose, visual role, evidence requirement, camera movement, visual actions, VFX/motion treatment, asset requirements and linked asset IDs, transitions, audio cues and linked claim IDs. It is deterministic and rule-assisted, not a claim of autonomous AI directing or verified fact research. It rejects durations too short to allocate a frame to every beat. Every shot remains editable.

## Step 35 — Evidence, visual proof and rights review

Factual/comparative evidence shots must link to a verified factual/comparative claim with at least one source marked publicly accessible. Blocked/login-only sources cannot clear the evidence gate. Illustrations, reconstructions, opinions and demonstrations remain distinct visual roles. If a shot requires actual footage, it must include source-footage media and link an imported video asset; an official-screenshot requirement must link an imported image. The rights review records the asset decision, basis, intended use, permission reference, attribution, restrictions, reviewer and review date. Approval requires a documented basis and reviewer/date; rejected, restricted and unreviewed assets block readiness.

This is a production workflow safeguard, not legal advice or a determination that a use is lawful. The rights reviewer must confirm ownership, licence terms, permission or another defensible basis. Reference-video records are not reuse licences.

## Verification for batch 31–35

- [Foundation validation run 46128278996 — success](https://github.com/FRFR-FR/frameforge/actions/runs/46128278996): **58 JavaScript tests passed**, **27 Python tests passed**, schema syntax and semantic tests passed, and the research/director example project passed the validator in the Python regression suite.
- [Chromium browser smoke run 46128278936 — success](https://github.com/FRFR-FR/frameforge/actions/runs/46128278936): visual, audio and director smoke tests all passed. The director test verified brief/ambiguity intake, source and reference records, niche profile editing, timed shot generation, verified claim linking, asset rights approval and persistence after reload.
- Detailed workflow and limitations: [FF_V2_RESEARCH_AND_DIRECTOR.md](FF_V2_RESEARCH_AND_DIRECTOR.md).

## Current V2 boundary after steps 1–35

The V2 timeline now feeds a single-frame Canvas 2D layer compositor with optional WebGL 1 post-processing, procedural VFX, clip effects, transitions, and a WebGL Three.js r164.1 scene renderer for imported GLB/glTF models. It exports transparent PNG frames and packages 3D scenes for Blender. The audio engine provides editable multi-track mixing, waveforms, event-linked SFX, automation, ducking and WAV mastering; an FFmpeg utility muxes a WAV master with an already-rendered silent video. The Research & Visual Director stores a production brief, source/reference dossier, editable niche profile, timed narration shot plan and evidence/rights review. V2 still does **not** render an entire timeline to MP4 automatically. Full-sequence rendering, resumable chunks, integrated FFmpeg export and technical QA remain later roadmap steps. The legacy V1 editor and existing Blender production workflows remain available.


## Remaining limits / not yet done

- The V2 compositor still renders the selected playhead frame and exports PNG; it does not yet render a full sequence or create the V2 timeline MP4. The FFmpeg mux utility only combines a silent video made by an existing renderer with the WAV master. Full-sequence rendering, resumable chunks and integrated V2 FFmpeg export remain future steps (41–43).
- The optional shader backend is native WebGL 1, not Three.js EffectComposer or WebGPU. Custom GLSL requires WebGL and is explicitly skipped under Canvas 2D fallback; built-in effects use Canvas 2D fallbacks where supported.
- Browser GPU drivers, shader precision, texture limits, Canvas filters, codecs, storage and memory vary by device. Pixel-heavy depth-of-field and distortion work can be slow on phones, especially at higher resolutions. The optional Three.js GLB/glTF scene renderer specifically needs WebGL.
- Imported 3D model pixels in V2 require WebGL; a device without WebGL can still inspect/import model metadata and use 2D editing, but cannot render those 3D tracks in the V2 compositor. The existing CPU-side `frameforge-3d.js` renderer remains available for code-authored geometry.
- The Blender bridge is a scene/frame handoff, not a full-sequence MP4 round trip. Ground and AABB contact are approximations rather than a full physics simulation; complex multi-axis Euler conversions may differ slightly.
- Audio preview uses an offline rendered WAV master, not a live low-latency mixer. Advanced insert effects such as EQ, reverb and compression, pitch-preserving audio speed ramps and automatic mux into a V2-rendered full sequence are not included yet. Browser audio decoding depends on device codec support.
- Alpha/luma matte modes are implemented but do not yet have dedicated pixel-level Chromium fixtures. Shape masks and their inversion are pixel-tested.
- Imported media metadata validation relies partly on browser codecs; it is not a full decode of every video frame or audio sample.
- Project JSON does not package imported binary files. Blobs remain in the originating browser's IndexedDB; keep source media separately backed up.
- Local browser storage is quota-limited and can be evicted. Persistent-storage requests are best-effort, not guaranteed.
- The asset rights gate checks user-recorded metadata and project references; it does not independently verify a licence, determine legal rights or provide legal advice. Research and reference-video intake is manual/assistant-led, not autonomous browsing or private-page scraping. Reference-video records are style observations only and do not authorise reuse.
- The 250 MB per-file import ceiling may exceed the available browser storage quota on some devices.
- The legacy V1 drawing editor and existing Blender/FF3D production workflows remain available and were not replaced by this batch.

## Next batch

The next five-step batch is **36–40** (reusable shot recipes, free/open media adapters, procedural asset generation, free/licensed audio workflow and shot assembly/orchestration). Do not start it until the user requests it.
