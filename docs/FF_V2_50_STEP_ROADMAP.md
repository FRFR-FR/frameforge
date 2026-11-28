# FrameForge V2 — Canonical 50-Step Upgrade Roadmap

**Repository:** FRFR-FR/frameforge  
**Canonical roadmap:** `docs/FF_V2_50_STEP_ROADMAP.md`  
**Purpose:** Upgrade FrameForge from a basic frame/animation application into a full, code-controlled video production, compositing, VFX, audio and rendering system, with niche-aware research and visual direction.

## Non-negotiable project rules

1. **Zero mandatory software/service spend.** Prefer free and open-source tools. Do not add paid subscriptions, paid rendering, paid AI APIs, paid image-generation services, or paid stock libraries. If a free-tier quota is exhausted, pause that job or offer a local alternative; never silently incur a charge.
2. **No Runway.** Do not add or depend on Runway.
3. **No paid AI image generation.** Visuals must come from procedural drawing, code, Blender/Three.js, user-supplied assets, or appropriately licensed/public-domain sources.
4. **FrameForge and the user's GitHub repository remain the control plane.** Preserve existing work and workflows; do not replace the project with an unrelated hosted editor.
5. **Real editing, not merely trimming/reordering.** Support layers, compositing, keyframes, masks, effects, transitions, graphics, audio tracks, mixing and final rendering.
6. **Niche-specific creative direction.** Each video must be researched and visually directed for its particular subject and audience. Do not impose one generic visual template on every niche.
7. **Evidence and rights matter.** Record source, licence/permission, attribution requirements and intended use for imported media. Never label an asset "free" without evidence. Copyrighted clips may be used only where the user has permission or a defensible legal basis; no blanket fair-use guarantee.
8. **Do not promise unlimited free compute.** GitHub Actions, storage, bandwidth, local hardware and mobile-browser performance have quotas/limits. Design for resumable jobs, small artifacts and local rendering options. Never silently move work to paid runners.
9. **Backwards compatibility.** Audit existing projects before changing schemas or renderers. Migrate safely, preserve original files and provide rollback paths.
10. **A step is complete only after its acceptance checks pass.** Do not report a step as installed merely because code was written. Include the commit, changed files, tests, known limits and any manual action still required.

## How numbered-step requests work

When the user sends a number from **1 to 50**, interpret it as the corresponding step below. Work on that step only, using the repository's current state and this roadmap as the source of truth. Inspect dependencies and existing code before modifying anything. Implement the change, test it, commit it where repository access permits, and verify the result. Then report what was completed, test results, files changed, and remaining manual blockers. Do not start later steps without being asked.

If a step requires a user-only action (for example, approving a GitHub permission, uploading a private asset, or enabling a setting), complete all preparatory work possible and clearly identify the exact action required. Do not claim that the step is fully complete until the acceptance condition is met.

If a future conversation contains only a number, resolve it against this document. If this file cannot be accessed, ask the user to provide the number's roadmap context rather than guessing.

## Architecture and cost reality

- **Browser/editor layer:** existing HTML/CSS/JavaScript app, expanded into a project/timeline/compositing UI.
- **2D/graphics:** Canvas 2D and SVG for vector graphics, typography and portable effects.
- **3D:** Three.js/WebGL for interactive GPU previews and compositing; Blender for demanding 3D scene creation and CPU rendering. GPU features must have a fallback or clearly report when unsupported.
- **Compositing/render:** FFmpeg for deterministic offline assembly, filters, audio mixing and encoding; custom code for project data and effect orchestration.
- **Audio:** FFmpeg plus free local/open-source tools/libraries where appropriate.
- **Automation:** GitHub Actions only within available free quotas; public-repository hosted runner allowances and artifact retention/storage limits must be checked at implementation time.
- **Research/creative direction:** assistant-led live public-web research and analysis with no paid LLM/API dependency. FrameForge stores/consumes research dossiers and structured shot plans. Do not misrepresent a local rules engine as a fully autonomous general-purpose AI.
- **Media acquisition:** use public-domain, openly licensed, user-provided or permissioned sources. Some providers require free API keys or impose limits; adapters must be optional, and no key may be assumed to exist.

## The 50 steps

### Phase 1 — Baseline, safety and project foundations

**1. Repository and workflow audit**  
Map the current application, Blender pipeline, Three.js runtime workflow, project files, active GitHub Actions, artifacts and known failures. Record the baseline without deleting or rewriting existing production workflows.  
**Acceptance:** an audit report lists key entry points, dependencies, workflows, current capabilities, risks and test commands.

**2. V2 architecture and zero-cost policy**  
Define module boundaries, data flow, free-tool choices, compute/storage budgets, licensing rules and fallback behaviour. Identify anything that could incur a charge and make it opt-in or exclude it.  
**Acceptance:** architecture and cost-policy documents are committed; no paid service is required to run the core path.

**3. Automated test and validation foundation**  
Add appropriate linting, unit tests, schema validation and workflow checks using free tooling. Establish a test command that can run locally and in GitHub Actions.  
**Acceptance:** baseline tests pass and a deliberate test failure is detected by CI.

**4. Versioned project format**  
Define a versioned project schema for sequences, scenes, tracks, layers, assets, keyframes, effects, transitions, audio and render settings.  
**Acceptance:** valid sample projects parse; malformed projects fail with understandable errors; schema version is recorded.

**5. Media provenance and rights manifest**  
Define a media manifest that records local path, source URL/provider, creator, licence/permission evidence, attribution text, date obtained, usage restrictions and whether the material is user-supplied.  
**Acceptance:** every imported asset can be traced; unknown rights are marked unknown rather than assumed free.

### Phase 2 — Media management and timeline

**6. Import and validation pipeline**  
Support practical import of PNG, JPEG, SVG, WebP, GIF, MP4/WebM, WAV/MP3/OGG and suitable 3D interchange formats such as glTF/GLB. Validate dimensions, codecs, transparency and errors.  
**Acceptance:** representative files import with correct metadata; unsupported or corrupt files produce useful errors.

**7. Asset library and search**  
Create a searchable local project asset library with tags, thumbnails, media type, duration, dimensions, transparency and provenance.  
**Acceptance:** assets can be searched, previewed, relinked and reused without duplicating files unnecessarily.

**8. Multi-track timeline data model**  
Implement tracks and clips for video, image, graphics, titles, effects, 3D scenes, narration, music and SFX, with start/end times, offsets and ordering.  
**Acceptance:** a saved project can represent overlapping independent tracks and round-trip through load/save.

**9. Timeline editing UI and controls**  
Add track visibility/lock/mute, selection, move, trim, split, duplicate, snapping, zoom, scrubbing and time/frame display. This is a foundation, not the final definition of editing.  
**Acceptance:** user can edit multiple overlapping clips and preserve exact timing after save/reload.

**10. Project persistence, autosave and cache management**  
Implement safe autosave, explicit save/open/export, recovery after interruption, cache invalidation and project migration.  
**Acceptance:** restart/reload restores a valid project; interrupted writes do not corrupt the last good save.

### Phase 3 — 2D compositing and motion graphics

**11. Layer compositor and alpha pipeline**  
Composite multiple visual layers with correct alpha handling, ordering, premultiplied-alpha discipline where needed and deterministic frame output.  
**Acceptance:** transparent PNGs and overlapping layers composite without black/white fringes or incorrect transparency.

**12. Transform, crop and anchor controls**  
Support position, scale, rotation, anchor point, crop, fit/fill, opacity and aspect-ratio handling for every visual layer.  
**Acceptance:** transforms animate and render consistently at preview and export resolutions.

**13. Keyframes, easing and parenting**  
Add keyframes for transforms, opacity and supported effect/audio parameters; provide easing curves and parent-child transforms.  
**Acceptance:** smooth, repeatable animation can be created without drawing every frame manually.

**14. Masks, mattes and blend modes**  
Add masks, alpha/luma mattes, feathering and a curated set of blend modes with clear fallbacks.  
**Acceptance:** masked overlays and composited PNG elements render correctly in test scenes.

**15. Typography, SVG and shape graphics**  
Build a reusable title/lower-third/label/diagram system with font handling, vector shapes, outlines, shadows and animation.  
**Acceptance:** text and vector graphics remain crisp at target output resolutions and can be keyframed.

### Phase 4 — VFX and transitions

**16. Particle and procedural effect system**  
Build reusable particles for sparks, dust, embers, magic/energy motifs, confetti and other non-photoreal effects, with seeded randomness for reproducible renders.  
**Acceptance:** effect parameters can be saved in a project and produce repeatable output.

**17. GPU post-processing and shader framework**  
Integrate a supported Three.js post-processing pipeline and custom shader interface, with feature detection and a non-GPU/offline fallback where feasible.  
**Acceptance:** ordered effect passes can be enabled/disabled and export settings are explicit; unsupported hardware fails gracefully.

**18. Lighting, glow and atmospheric effects**  
Add practical bloom/glow, light rays, vignette, blur, depth-of-field options, color adjustments and atmospheric overlays, while controlling performance.  
**Acceptance:** named presets render predictably and can be combined without corrupting alpha or timing.

**19. Distortion and stylised effects**  
Add controlled glitch, chromatic aberration, displacement, warp, ripple, shake and speed-ramp/motion-blur options where supported.  
**Acceptance:** effects are adjustable, keyframable and tested for visual artifacts at export resolution.

**20. Transition library**  
Create editable transitions including cuts, fades, wipes, zooms, whip-pan, radial/hypnosis-wheel, swirl/warp and glitch transitions.  
**Acceptance:** transitions have duration, direction and intensity controls, work between arbitrary compatible layers/scenes and render deterministically.

### Phase 5 — 3D production integration

**21. Three.js runtime integration**  
Integrate and version the existing offline Three.js runtime properly; establish WebGL capability checks, runtime loading, licence notices and a clear fallback.  
**Acceptance:** runtime loads from the project's controlled build artifact and does not depend on a remote CDN at render time.

**22. 3D model and material import**  
Support GLB/glTF import, materials, textures, animation clips and asset relinking, with explicit limits for unsupported formats/features.  
**Acceptance:** sample models load and render in a reproducible scene.

**23. 3D scene, camera and lighting controls**  
Create reusable scenes with cameras, lights, environments, object transforms, framing and scene-level render settings.  
**Acceptance:** camera/light changes are stored in the project and match rendered frames.

**24. 3D animation, rigging and interaction support**  
Support model animation clips, armatures/rigs through Blender, object constraints and tested collision/ground-contact solutions when the scene requires them.  
**Acceptance:** a sample character/prop scene demonstrates reliable motion and object contact; do not claim full physics if only approximated.

**25. Blender bridge and scene interchange**  
Build a documented handoff between FrameForge project data and Blender scripts/scenes, including asset paths, cameras, timing, render settings and returned image/video sequences.  
**Acceptance:** a test scene can be generated or updated, rendered in Blender and composited back into FrameForge.

### Phase 6 — Audio production

**26. Multi-track audio engine**  
Add independent narration, dialogue, music, ambience and SFX tracks with placement, trim, fades, gain and mute/solo.  
**Acceptance:** multiple overlapping tracks mix to a synchronized test output.

**27. Waveforms and audio synchronization**  
Display waveforms, seek by audio time, support frame-accurate placement within the output timebase and preserve sync through edits.  
**Acceptance:** known sync markers remain within the defined tolerance after preview and export.

**28. SFX cue and event system**  
Allow visual events and timeline markers to trigger imported sound effects, including whooshes, impacts, clicks, transitions and atmosphere.  
**Acceptance:** cues can be attached to events, moved with clips and previewed without repeated accidental playback.

**29. Mixing and automation**  
Add volume automation, fades, narration ducking, panning where supported, peak monitoring and configurable loudness targets.  
**Acceptance:** a sample mix demonstrates controlled narration/music balance without clipping.

**30. Audio render and final muxing**  
Render a clean audio master and mux it with picture through FFmpeg, preserving sample rate, channel layout and sync.  
**Acceptance:** exported file passes duration, stream and audio-playback checks.

### Phase 7 — Niche research and visual direction

**31. Research intake and brief builder**  
Accept topic, niche, audience, platform, duration, narration/script, desired tone and restrictions. Resolve ambiguous claims and identify what must be verified.  
**Acceptance:** a structured research brief is created before visual production begins.

**32. Niche and reference-video research**  
Use assistant-led public-web research to discover relevant niche examples, recurring formats, visual conventions and reference creators/videos. Accept user-provided URLs. Do not scrape private/login-only content, bypass access controls or assume that a reference video's assets are reusable.  
**Acceptance:** research dossier records sources, dates, observations and confidence; factual claims are separately sourced.

**33. Niche-specific visual style profiles**  
Define editable profiles for entertainment/power-scaling, gaming, cybersecurity, history, science, mysteries, finance and other detected niches. Profiles guide, but do not rigidly dictate, the visual treatment.  
**Acceptance:** different test topics produce meaningfully different visual plans and the user can override any style choice.

**34. Narration-to-shot visual director**  
Break narration into timed beats and decide for each beat whether to use character PNG cut-outs, source footage, procedural 2D graphics, 3D animation, diagrams, typography or a combination. Specify camera movement, VFX, transitions and pacing.  
**Acceptance:** every narration beat has a visual purpose, shot duration, asset requirements and effect/audio cues.

**35. Evidence, visual proof and rights review**  
Attach evidence to factual/comparative claims; identify when actual footage is needed to substantiate a point; track timestamps and sources when supplied/accessible. Flag copyrighted material and require permission or a defensible user-reviewed legal basis; never guarantee fair use or reuse rights.  
**Acceptance:** the plan distinguishes illustration from evidence and includes a rights/provenance review before rendering.

### Phase 8 — Asset acquisition and production automation

**36. Reusable shot recipes and templates**  
Create configurable shot recipes for character reveals, comparisons, explainers, diagrams, maps, timelines, evidence callouts, gameplay overlays and documentary-style scenes.  
**Acceptance:** recipes are reusable but allow topic-specific composition and timing.

**37. Free/open media source adapters**  
Add optional adapters/workflows for public-domain and openly licensed image/video/audio/model repositories. Respect provider terms, API-key requirements, rate limits and attribution. Include manual import as a universal fallback.  
**Acceptance:** each downloaded asset is validated and added to the rights manifest; no paid provider is required.

**38. Procedural asset and motion-graphics builder**  
Generate original backgrounds, diagrams, icon treatments, charts, particles and stylised graphical elements from code and structured descriptions, without paid image-generation services.  
**Acceptance:** a test video can contain original assets created entirely by the local/procedural system.

**39. Free and licensed audio asset workflow**  
Provide a catalogue/import workflow for user-created, public-domain or appropriately licensed music and SFX; record required credit text and usage limits.  
**Acceptance:** every external audio asset has rights metadata or is marked unverified and excluded from automatic publication packaging.

**40. Shot assembly and production orchestrator**  
Convert the approved shot plan into scene/timeline data, allocate assets, place effects and audio cues, and generate a reviewable draft project.  
**Acceptance:** an end-to-end test script produces an editable project, not only a flattened MP4.

### Phase 9 — Rendering, quality assurance and delivery

**41. Resumable render queue**  
Split long renders into resumable scene/frame chunks, track job status, retry failed chunks and avoid duplicate work.  
**Acceptance:** deliberately interrupted test render resumes without re-rendering valid chunks unnecessarily.

**42. FFmpeg export profiles**  
Create export presets for 720p horizontal (1280x720), 720p vertical (720x1280), and optional higher resolutions only when compute allows; configure frame rate, codec, bitrate and audio.  
**Acceptance:** exported files match the selected dimensions, frame rate, duration and stream settings.

**43. Automated technical QA**  
Check missing media, black/frozen frames, bad dimensions, frame count, audio stream, audio peaks, duration and sync markers.  
**Acceptance:** known-bad test exports are detected; known-good test exports pass.

**44. Visual/audio review tools**  
Generate contact sheets, scene previews and audio review data so important frames and transitions can be inspected before release. Keep human approval for subjective quality.  
**Acceptance:** a user can review a render without downloading every intermediate frame individually.

**45. Delivery package and attribution notes**  
Package final MP4, project file, asset manifest, source/licence records, attribution text and render report. Avoid committing huge binaries to Git when a workflow artifact or local export is more appropriate.  
**Acceptance:** the delivery report lists file sizes in MB, format, resolution, duration and any attribution/copyright notes.

### Phase 10 — Integration, demonstrations and release

**46. Mobile-friendly control and documentation**  
Make core project controls usable on Android browsers, document storage/export limitations and offer a local/desktop route for heavier jobs.  
**Acceptance:** a mobile user can create/open a project, manage assets, inspect previews and initiate supported workflows without hidden desktop-only controls.

**47. GitHub Actions integration and cost guardrails**  
Add manual workflows for tests, asset validation, render chunks and packaging. Set timeouts, concurrency limits, artifact retention and no-paid-runner safeguards. Do not create continuous background rendering/watchdogs unless explicitly requested and within free quotas.  
**Acceptance:** workflows run on permitted free infrastructure, fail clearly at limits and never switch to paid execution.

**48. End-to-end entertainment/power-scaling pilot**  
Build a sample in the style of a fictional-character comparison (for example, a Butterfly Miraculous versus Avengers threat analysis) using cut-outs, original effects, comparison graphics and only suitably permissioned/licensed or user-reviewed evidence footage.  
**Acceptance:** the pilot demonstrates niche-specific visuals, character animation, particles, SFX, proof callouts and a coherent finished edit. The example must not imply that copyrighted franchise assets are automatically free to reuse.

**49. End-to-end second-niche pilot**  
Build a separate cybersecurity or science/history pilot to prove that the system changes its visual direction rather than reusing the entertainment template.  
**Acceptance:** both pilots pass technical QA and have clearly different visual treatments.

**50. Stabilization, release and handover**  
Fix priority bugs, verify migration and rollback, review licences/dependencies, document setup and operation, publish the V2 release notes and final acceptance report.  
**Acceptance:** clean installation instructions work, core test suite passes, both pilots render, known limitations are documented and the V2 release is tagged.

## Definition of done for FrameForge V2

V2 is not complete just because the editor opens or a video exports. It must demonstrate:

- Multiple independently editable visual and audio tracks.
- Real compositing with transparent graphics and layered assets.
- Keyframed animation, masks and blend modes.
- Reusable VFX, transitions and motion-graphics tools.
- Integrated 2D and 3D scene workflows.
- Synchronized narration, music, ambience and SFX with mixing controls.
- A niche-specific research dossier and narration-to-shot plan for each production.
- Evidence/provenance/attribution tracking for external media.
- Resumable rendering and automated technical QA.
- Editable project delivery plus final MP4.
- No required paid API, AI generation, subscription or rendering service.

## Operational note

The user may begin a future conversation by sending only a step number. Treat this file as the canonical roadmap, inspect the current repository state, and execute that one step. Be honest about any action that requires the user's device, credentials, permission or manual approval. Never claim work continued in the background between conversations.
