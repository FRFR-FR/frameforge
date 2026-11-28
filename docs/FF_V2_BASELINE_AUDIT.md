# FrameForge V2 — Baseline Audit

**Audit date:** 2026-11-28  
**Repository:** `FRFR-FR/frameforge`  
**Branch reviewed:** `main`  
**Roadmap batch:** Steps 1–5

## Executive finding

FrameForge is a working, static browser-based drawing and frame-animation application with a lightweight software 3D preview and a separate set of native Blender production pipelines. It is not yet a full nonlinear editor or compositing suite. The repository contains substantial production-specific automation, but no shared V2 project model, no repository-wide test suite, and no central asset-rights manifest format.

The V2 upgrade should be additive. Preserve current project workflows and the existing editor while introducing separate, versioned schemas, validators, tests and documentation.

## Existing application entry points

| Path | Observed role | Current boundary |
|---|---|---|
| `index.html` | Static browser UI and script loading | No native render process can be launched by a GitHub Pages page |
| `styles.css` | Browser editor styling | UI is built around the existing drawing/frame workflow |
| `app.js` | Canvas drawing, frame timeline, IndexedDB autosave, image import, project JSON and browser recording | Project format is version 1; visual output is two canvas layers; browser export is silent WebM and real-time |
| `frameforge-3d.js` | Dependency-free CPU-side projected-mesh renderer | Preview renderer, not a full real-time 3D compositor; no PBR pipeline or skeletal rig system |
| `blender_pipeline/` | Native Blender scene construction, audits and CPU rendering | Separate production scripts rather than a unified timeline/compositor |
| `brown_film/` and `minecraft_pipeline/` | Dedicated long-form scene/render scripts | Project-specific pipelines |
| `projects/` | Per-video narration, timing, assets and production metadata | Formats are currently project-specific rather than one common V2 model |
| `tools/` | Utility scripts including authorised media download workflow | Not yet a general FF V2 tool suite |

### Current editor behaviour verified from source

- Canvas presets are portrait 720×1280, landscape 1280×720 and square 1080×1080.
- The frame model stores paint PNG data, code-layer PNG data and the frame script separately.
- Project export uses `format: "frameforge-project"` and `version: 1`, plus project name, canvas dimensions, FPS and frames.
- Autosave uses browser IndexedDB; it is local to that browser/device.
- Browser video recording uses the canvas output and MediaRecorder; there is no audio-track timeline in this editor path.
- The 3D preview projects mesh triangles into the 2D canvas. The Blender path is used for rigged production scenes.

## Existing workflow inventory

**25 workflow YAML files** were present in `.github/workflows/` at the audit commit.

| Workflow file | Observed purpose | Operational notes |
|---|---|---|
| `ambient-dual-video.yml` | Two ambient Blender productions, chunked by project | Push and manual triggers; matrix render jobs |
| `ambient-extracts.yml` | Short extracts from existing ambient render artifacts | Uses a hard-coded source run ID |
| `assemble-existing-minecraft.yml` | Assemble previously rendered Minecraft clips | Uses a default hard-coded source run ID |
| `ballpoint-pen-kokoro-echo.yml` | Kokoro Echo narration generation | Push/manual triggers; write permission to repository contents |
| `brown-blender-cpu.yml` | BROWN scene audit or full Blender CPU render | Relevant Blender-pipeline pushes invoke audit; manual render mode |
| `brown-film-render.yml` | Render an individual five-minute BROWN part | Branch push/manual trigger; six-hour job timeout |
| `brown-final-assembly.yml` | Assemble 24 BROWN render parts after a successful part workflow | Depends on branch runs and stored artifacts |
| `brown-render-controller.yml` | Benchmark and dispatch parallel BROWN part renders | Manual controller; matrix fan-out up to 20 parallel jobs |
| `brown-render-watchdog.yml` | Inspect/recover BROWN part renders | Scheduled every two hours; has Actions write permission |
| `build-embedded-three-runtime.yml` | Bundle Three.js and GLTFLoader | Manual or workflow-file push; installs pinned npm packages |
| `build-photoreal-suburban-assets.yml` | Fetch/build a photoreal asset collection | Manual or workflow-file push; downloads third-party models |
| `build-photoreal-three-runtime.yml` | Bundle Three.js, loaders and post-processing | Manual or workflow-file push; installs pinned npm packages |
| `download-youtube-shorts.yml` | Download videos after explicit rights confirmation | Manual only; requires confirmation; media remains subject to rights/terms |
| `fetch-suburban-assets.yml` | Download character and city-kit assets | Manual or workflow-file push; source/rights records need asset-level review |
| `gameforge-offline-pvp-watchdog.yml` | Daily GameForge prototype health check | Scheduled daily; calls a reusable workflow on a feature branch |
| `great-emu-war-kokoro-echo.yml` | Kokoro Echo narration generation | Push/manual triggers; write permission to repository contents |
| `konigsberg-educational-video.yml` | Blender educational scene audit/render | Scene and workflow push triggers; manual audit/render modes |
| `mechanical-watch-tts.yml` | Kokoro and eSpeak narration/sample generation | Push/manual triggers; write permission; cancels in-progress run in its group |
| `minecraft-blender-cpu.yml` | Legacy Minecraft scene generation and preview | Manual only; explicitly avoids render-on-push |
| `ocean-nightmares-download-audit.yml` | Download and audit NOAA candidates | Manual/workflow-file push; Actions write permission; generates review material |
| `ocean-nightmares-noaa-render.yml` | Gate and assemble the NOAA-only documentary | Project-path push/manual trigger; six-hour timeout; rights/species approval validator |
| `padlock-kokoro-echo.yml` | Kokoro Echo narration generation | Push/manual triggers; write permission to repository contents |
| `photoreal-suburban-dialogue.yml` | Generate and verify two-speaker dialogue | Push/manual triggers; installs CPU PyTorch/Kokoro |
| `rooftop-continuation-10min.yml` | Build and render a ten-minute Blender continuation | Push/manual triggers; chunked long render |
| `windows-ip-explainer.yml` | Build/audit/render Windows IP explainer | Push/manual triggers; lengthy Blender scene jobs |

This inventory is a source-level review of the workflow files on `main`; it is not a claim that every workflow was executed or that its external downloads currently succeed.

## Existing strengths to reuse

1. Blender is already used for genuine 3D scene construction, rigging, cameras, materials, animation and CPU rendering.
2. FFmpeg/FFprobe are already used in production workflows for encoding and media verification.
3. The Three.js runtime workflows already pin versions and bundle assets for offline use.
4. The Ocean Nightmares project has an asset-level manifest gate that requires approval and checks distinct media URLs before rendering.
5. Several production workflows already use chunking, audits, concurrency groups and artifact verification.
6. Existing project examples separate narration, timing, source manifests and scene scripts.

## Gaps confirmed

- No repository-wide `tests/` suite or single standard test command was found.
- No Python development dependency file or Node package manifest for the browser editor was found at repository root.
- No shared versioned schema governs all video projects.
- No shared media provenance/rights manifest schema exists; Ocean Nightmares uses a project-specific structure.
- The browser editor does not yet provide an independent multi-track layer/audio timeline, general compositing graph, reusable VFX stack or final audio mix.
- The editor's local IndexedDB autosave does not synchronize projects between devices.
- Browser export depends on MediaRecorder support and is not the native Blender/FFmpeg production pipeline.
- The lightweight FF3D renderer is not the same thing as the separately bundled Three.js runtime and is not a complete GPU compositor.
- Research, shot planning and niche-specific visual direction are not yet represented by a reusable, validated project data model.

## Risks and controls

| Risk | Evidence/impact | V2 control |
|---|---|---|
| Push-triggered production jobs | Several workflows start Blender, media download or model-build work on matching pushes | Keep V2 validation narrowly path-filtered; avoid broad push triggers for rendering |
| Scheduled automation | BROWN watchdog runs every two hours; GameForge watchdog runs daily | Do not add new schedules by default; make future automation opt-in and cost-bounded |
| Parallel render fan-out | BROWN controller can dispatch up to 20 jobs and individual jobs can run for hours | Define explicit concurrency, timeouts, retry limits and free-quota safeguards |
| Artifact coupling | Ambient extracts and existing Minecraft assembly use fixed source run IDs | Future V2 manifests should reference explicit artifact/run IDs and fail clearly when expired |
| Broad write permissions | Some narration workflows require `contents: write`; watchdogs require `actions: write` | New validation workflow must use read-only permissions; request write scope only for a documented need |
| Third-party downloads | Model/media source availability and licensing can change | Record source, licence evidence, attribution and review state per asset |
| Rights assumptions | A URL or a public webpage alone does not establish reuse permission | Default rights state to unknown/pending; block automatic publication packaging until reviewed |
| Free compute assumptions | Long CPU renders and artifacts have platform quotas/limits | Never assume unlimited free compute or silently switch to paid services |

## Baseline verification commands

The current repository has no one-command test suite. The following source-level checks are suitable starting points:

- Browser editor: open `index.html` in a modern browser; exercise project import/export and a short Canvas 2D preview.
- JavaScript syntax: `node --check app.js` and `node --check frameforge-3d.js` where Node.js is available.
- Python syntax: `python -m py_compile` against applicable Python scripts (compressed scripts must be decompressed to a temporary path first).
- Blender scene audits: run the relevant scene script with Blender's documented `--mode audit` command. Native Blender is required.
- Media verification: use FFprobe for stream, frame-rate, dimensions, duration and size checks.

## Audit conclusion

The repository is a strong base for a staged upgrade, but the current application should not be described as a complete video editor. Steps 2–5 establish the architecture, automated validation foundation, versioned project schema and media-rights contract before more invasive editing-engine changes begin.
