# FrameForge V2 — VFX, post-processing and transitions (steps 16–20)

This phase adds procedural visual effects, an optional shader backend, atmosphere and lighting treatments, distortion effects and clip-edge transitions to the existing V2 Canvas compositor. It extends the current V2 project model; it does not replace V1 or change the project schema version.

## Open the VFX workspace

Open FrameForge, select **V2 Assets**, scroll below the V2 multi-track timeline to **V2 Layer Compositor**. Add a generated particle layer or select an existing clip to access clip effects and transitions. The post-processing panel applies global passes after all enabled visual layers have been composited.

## 16. Procedural particles

Use the particle preset selector and **＋ Particles** to add a generated particle clip on the Graphics track. Presets:
- Sparks
- Dust
- Embers
- Magic
- Confetti

A particle clip stores its preset, count, seed, speed, size, colour, spread, gravity, lifetime and emission origin in the project. Random values are generated from a deterministic seeded PRNG. A fixed project, seed, frame and renderer therefore produce repeatable particle positions. Particle count is clamped to 500 to avoid unbounded work in the browser.

The particle effect is procedural Canvas 2D artwork. It does not use downloaded stock, AI-generated images or paid services.

## 17. GPU post-processing and shader framework

The global post-processing panel stores an ordered pass stack in `settings.post_processing.passes`. Passes can be enabled/disabled, moved up/down, and have their intensity adjusted. The renderer selector offers:
- **Automatic:** try the local WebGL 1 pipeline, then fall back to Canvas 2D
- **Prefer WebGL:** try WebGL, but retain Canvas 2D fallback if the device or shader cannot run
- **Canvas 2D only:** skip the GPU path

The new `ff-v2-shaders.js` module uses browser-native WebGL 1 and locally compiled GLSL passes. It has no CDN dependency or external shader libraries. A custom GLSL fragment shader editor is included; its source is saved in the project and compiled when the render is attempted. The interface exposes texture, UV, resolution, time and intensity inputs. Invalid/custom shader passes report a warning and are skipped by the Canvas 2D fallback.

**Implementation choice:** this stage uses native WebGL rather than bringing in Three.js EffectComposer. The existing FrameForge 3D runtime is a dependency-free in-house renderer, not a managed Three.js application. Native WebGL avoids adding a remote or version-sensitive dependency to the core editor, while preserving the same optional GPU/fallback behaviour.

The GPU pipeline is WebGL 1, not WebGPU. GPU availability, shader precision, maximum texture size and browser drivers vary by device. A browser may support WebGL but reject a particular shader or lose its context; the Canvas fallback remains the recovery path for built-in effects.

## 18. Lighting, glow and atmosphere

Global pass presets can be appended to the stack:
- **Cinematic:** contrast, saturation and vignette
- **Soft glow:** glow and light rays
- **Noir:** monochrome, contrast and vignette
- **Documentary:** restrained contrast and saturation
- **Dream haze:** soft blur, glow and vignette

Individual passes include brightness/contrast, saturation, vignette, blur, glow/bloom, light rays and depth of field. Clip effects can use glow, blur, vignette, light rays and depth of field on a single selected layer. All built-in effects preserve sampled source alpha as much as the selected browser path allows. CPU-based depth-of-field reads image pixels and can be expensive at large resolutions.

## 19. Distortion, stylisation and speed ramps

The clip-effects panel adds:
- Glitch with a saved seed
- Chromatic aberration
- Ripple / warp
- Camera shake
- Motion blur
- Brightness/contrast and saturation
- Glow, blur, vignette, light rays and depth of field

Effect intensity can be keyframed on the selected clip in local clip-frame coordinates. Speed ramps use the existing playback-rate property, also keyframable at the playhead. For each preview frame the renderer integrates the rate of prior clip frames to calculate the source time, rather than multiplying one constant speed by the current frame.

Distortions are applied after layer drawing and before final layer compositing; the global effect stack runs after the visual layers have been assembled. A few complex effects, such as custom GLSL, require WebGL. When unavailable in Canvas 2D fallback they are explicitly skipped rather than silently approximated.

## 20. Clip transition library

Transitions attach to the selected clip's **incoming** or **outgoing** edge. The UI stores type, duration in frames, direction and intensity. Implemented transitions:
- Fade and crossfade
- Directional wipe
- Zoom
- Whip pan
- Radial
- Hypnosis wheel
- Swirl / warp
- Glitch

The transition is evaluated from the clip's edge-relative frame position, so a fixed clip and playhead always produce the same transition state. A crossfade is built from clip opacity; to visibly blend from one shot to another, place the two clips on overlapping visual tracks. Wipe/radial/hypnosis transitions reveal or hide the selected layer with a generated mask. Swirl/glitch use deterministic Canvas distortion fallbacks.

## Verification

The Foundation Validation workflow checks source syntax, the core and renderer regression suites, Python validators and the V2 schema. The expanded Node suite covers deterministic particle seeds, pass ordering and presets, clip-effect keyframes, transition timing and directions, playback-rate ramps and WebGL-unavailable fallback.

The Chromium browser smoke test exercises the actual controls for a particle layer, repeated-frame determinism, animated clip effects, incoming/outgoing transitions, speed keyframes, the ordered post-processing stack and custom GLSL fallback. The current successful run links are recorded in [FF_V2_PROGRESS.md](FF_V2_PROGRESS.md).

## Boundaries and later work

This stage extends the **single-frame** compositor. It does not render the whole V2 timeline to MP4 and does not provide a continuous real-time preview player. Full-sequence rendering, resumable render chunks and final FFmpeg export remain later roadmap steps.

Other limits:
- The built-in shader pipeline is WebGL 1, not a full Three.js EffectComposer or WebGPU stack.
- Custom GLSL works only when WebGL is available and the shader compiles. Canvas 2D fallback reports custom passes as skipped.
- GPU drivers, high-precision fragment support, texture limits, browser codecs and Canvas filter support vary by device.
- Pixel-based depth-of-field, luma operations and some distortions can use substantial memory/CPU at 720p or above, especially on phones.
- The compositor remains 2D. 3D scene tracks are not yet composited here, and the existing Blender/FF3D workflows are unchanged.
- Audio tracks are not yet processed by V2. Speed ramps alter visual source-time selection only; pitch-preserving audio retiming belongs to the later audio pipeline.
- Project JSON still does not package imported media blobs; keep source media backed up separately.

No paid render service, paid API, stock-media purchase, CDN shader library or image-generation service is required.
