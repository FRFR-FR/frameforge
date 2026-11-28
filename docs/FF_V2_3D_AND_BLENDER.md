# FrameForge V2 — 3D scenes, glTF models and Blender bridge (steps 21–25)

This phase adds an offline, version-pinned Three.js runtime to the V2 browser editor, real GLB/glTF model loading, 3D scene controls, imported animation playback, model transforms/constraints and a portable Blender handoff.

## 21. Offline Three.js runtime

FrameForge vendors **Three.js r164.1** locally at `vendor/three/0.164.1/frameforge-three-runtime.min.js`. The bundle exposes Three.js, GLTFLoader and SkeletonUtils.clone. It is built by [build-embedded-three-runtime.yml](../.github/workflows/build-embedded-three-runtime.yml) using pinned package versions.

The vendor directory contains:
- the minified browser bundle,
- the upstream Three.js MIT licence,
- a runtime manifest with the package versions, entrypoints and SHA-256 checksum.

The editor loads this bundle from the repository itself. It does not fetch Three.js from a CDN at runtime. WebGL availability and maximum texture size are feature-detected. If WebGL is unavailable, 2D editing/compositing still works, while 3D model clips show a render warning instead of crashing the V2 editor. The older dependency-free `frameforge-3d.js` runtime remains in place.

## 22. GLB/glTF model and material import

The V2 asset importer now decodes:
- **GLB** (binary glTF 2.0),
- **glTF JSON 2.0**.

Three.js GLTFLoader loads meshes, PBR materials, embedded textures, nodes, skins/skeletons and animation clips. The asset library records the number of meshes, model nodes, dimensions, bounds and available animation clips. These values remain metadata in the project; the original source Blob remains in the browser's IndexedDB.

For a glTF JSON file that references external `.bin` or image files, import those dependency files into the V2 asset library first, then import the `.gltf` file. The local LoadingManager resolves those referenced files from the library; the Blender ZIP export packages them beside the glTF source using the same relative paths. Embedded GLB resources do not need separate files.

## 23. Scene, camera and lighting

Each V2 sequence carries a serializable `scene3d` section. The scene editor exposes:
- perspective or orthographic camera,
- camera position, target and FOV,
- scene background and transparency,
- ambient and directional light intensity,
- tone mapping.

The stored schema also supports point and spot lights, light colours/positions/directions, orthographic camera height, near/far clipping, exposure and shadow settings. The Three.js render surface is transparent when requested and is composited into the V2 frame at sequence resolution.

## 24. Model animation, rigging and constraints

Imported glTF animation clips play through Three.js AnimationMixer. The selected clip, enabled state, loop behaviour and playback speed are stored on the model clip. Imported skins and skeleton animation are supported by the GLTFLoader runtime; SkeletonUtils.clone keeps independent model instances safe.

Model clips have editable position, rotation and scale on X/Y/Z. These transform channels can be keyframed in the existing clip-local keyframe editor. The project model also supports:
- ground contact,
- parent-to-model relationships,
- look-at targets,
- approximate axis-aligned bounding-box contact.

Ground and AABB contacts are deliberately **approximations**. They are not rigid-body physics, cloth, soft-body, ragdoll, collision meshes or a general constraint solver. The Three.js path uses Y-up coordinates; the Blender bridge converts camera, light and imported model transforms into Blender's Z-up coordinate system. Per-axis Euler keyframes are mapped to the corresponding Blender axes; complex multi-axis Euler combinations may not be numerically identical after conversion.

For advanced rig authoring, retargeting, custom constraints and physically simulated motion, use the Blender handoff.

## 25. Blender interchange and render bridge

The 3D scene panel has **Export Blender bridge ZIP**. It creates a portable package containing:
- a versioned scene manifest with sequence dimensions/FPS, camera, lights, environment, render settings and model clips,
- every referenced GLB/glTF source model stored in the browser library,
- external glTF buffers/textures when referenced,
- the Python bridge script,
- usage instructions.

No IndexedDB object URLs or browser-only paths are written to the package. If an external glTF dependency is missing, packaging stops with a specific error rather than silently producing an incomplete scene.

After extracting the ZIP and installing Blender 4.x or later, run from the extracted directory:

```bash
blender --background --python tools/frameforge_blender_bridge.py -- \
  --project frameforge_blender_scene.json \
  --output-dir output --mode build

blender --background --python tools/frameforge_blender_bridge.py -- \
  --project frameforge_blender_scene.json \
  --output-dir output --mode render --frame 1
```

Build mode creates an editable `.blend` project and exports a GLB interchange scene. Render mode creates an RGBA PNG for the requested frame. Import that PNG into the V2 asset library to composite it back into the FrameForge timeline. This is a **frame-based bridge**, not an automatic round-trip of a full Blender video sequence.

The bridge supports glTF model import, scene camera, lights, material settings, NLA animation clip selection, object transform keyframes, ground contact, parent/look-at and approximate AABB contact. Blender runs headless using CPU Cycles in the CI verification workflow. The build/render output is retained as a 14-day GitHub Actions artifact in that workflow.

## Tests and verification

- Foundation CI syntax-checks the local 3D runtime, core and renderer; unit tests exercise camera/light configuration, GLB clip creation, 3D transform animation and contact/parent validation.
- Browser CI loads the repository-vendored Three.js bundle, imports a generated animated GLB containing a triangle mesh and a translation animation, verifies the model metadata/clip controls, applies a 3D transform keyframe, adjusts scene camera/lighting, and checks that the Blender bridge download is a valid ZIP containing the project model and animation/keyframe data.
- Blender CI installs Blender and EGL/Mesa support, validates the bridge manifest, imports a separate embedded glTF model, builds the editable scene/GLB, renders a PNG on CPU Cycles and uploads the outputs.

Current run links are recorded in [FF_V2_PROGRESS.md](FF_V2_PROGRESS.md).

## Boundaries and later work

The V2 3D renderer is WebGL-based. If WebGL is unavailable, GLB/glTF assets can still be imported/inspected, but the V2 compositor cannot render their 3D model pixels on that device. The editor reports this explicitly; the dependency-free procedural 3D renderer remains available for code-authored geometry.

This phase does not provide a general-purpose Blender scene graph editor, full rigid-body physics, automatic mocap retargeting, arbitrary constraints, a material-node editor, 3D sculpting, or a full-sequence Blender video pipeline. The Blender bridge currently creates/reconstructs the scene from a portable manifest and returns individual PNG frames. Audio mixing and final V2 MP4 rendering remain later roadmap steps. V2 project JSON still stores imported media as local browser Blobs rather than embedding the binary files; keep separate source-media backups.
