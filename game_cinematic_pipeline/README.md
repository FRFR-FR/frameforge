# FrameForge AI Game-Cinematic Pipeline

This folder adds a genuine Blender 3D production path to FrameForge. It is deliberately separate from the browser Canvas 2D preview renderer and from the existing BROWN/Königsberg productions.

## What it does

- Builds a real editable Blender scene from `scene_spec.json` using native meshes, materials, lights, cameras and keyframed animation.
- Uses Blender Cycles on CPU; no GPU, AI image generation, Runway, paid image API or generated stills are required.
- Produces an editable `.blend`, an optional glTF `.glb`, a structural audit report, PNG frame sequences and an H.264 MP4.
- Splits frame ranges across four independent GitHub Actions jobs, then assembles the frames with FFmpeg.
- Automatically starts a render when the scene spec or pipeline code is pushed to the configured feature branch.

## Current starter scene

The included spec builds a short sci-fi outpost game-cinematic proof of pipeline: modular structures, a procedural armored hero, PBR-style materials, practical emissive lights, a tracked camera move and animated character motion. All visible objects are genuine 3D geometry. This is a procedural starter scene, not a claim to AAA character art; higher-end character and environment assets can be imported as licensed GLB/FBX assets in a later extension.

## Change a scene with ChatGPT

Ask ChatGPT to change the scene, camera, animation, environment, palette, duration, resolution or quality. ChatGPT can update `scene_spec.json` and/or the Blender builder in this repository. A push to `feature/ai-game-cinematic-engine` automatically launches the audit and render workflow.

The JSON is a structured scene brief, not executable Python. Keep it valid JSON. Do not add secrets or API keys.

## Run locally

Install Blender and FFmpeg, then from the repository root:

```bash
blender --background --python game_cinematic_pipeline/build_scene.py -- --mode audit
blender --background --python game_cinematic_pipeline/build_scene.py -- --mode render
```

For a frame shard (used by CI):

```bash
blender --background --python game_cinematic_pipeline/build_scene.py -- --mode render --shard-index 0 --shard-count 4
```

Outputs are written to `output/game_cinematic/`.

## Render settings and limits

The starter is 1280×720, 24 FPS, 8 seconds, Cycles CPU, 32 samples with denoising. Increase samples, resolution or duration in `scene_spec.json` for slower/higher-quality productions. GitHub-hosted standard runners have a six-hour maximum per job; each shard runs independently. Public-repository standard GitHub-hosted runner use is free, but artifact storage, runner capacity, job limits and queueing still apply. A CPU render is not instantaneous and free compute is not unlimited.

## ChatGPT automation boundary

ChatGPT can author scene specifications and code, commit revisions to the connected GitHub repository, inspect workflow results and retrieve finished artifacts when the connected GitHub integration exposes those actions. This repository workflow reacts to pushes. The currently connected GitHub action interface does not expose a workflow-dispatch operation, so a manual re-render without a new commit can be started from GitHub Actions in the browser.

## Quality gate

The audit verifies the scene was built, has the requested timeline, camera and expected objects, and saves the editable project. It does not certify visual quality. Review the MP4 and representative frames before publishing. The initial scene uses procedural geometry; realistic character rigs and bespoke game assets require imported, properly licensed 3D models and animation clips.
