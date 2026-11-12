# GAMEFORGE

GAMEFORGE is a code-first game production system built around Godot, procedural Blender assets, adaptive low-end device profiles and GitHub-based validation/export workflows.

## Core foundation

The existing Godot template contains a third-person controller, camera, seeded blockout world, quests, dialogue, inventory, combat health, NPC state machine, save/load, accessibility, FrameForge cue dispatch and Android/Windows export presets. The offline generator produces structured design artifacts, not a complete playable game by itself.

## GAMEFORGE-only FrameForge Cutscene Studio

A dedicated copy/adaptation of the FrameForge 3D core now lives in `gameforge/cutscenes/`. The standalone FrameForge at the repository root remains unchanged and continues to be the independent video/animation editor.

Open `gameforge/cutscenes/editor/index.html` to author characters, dialogue, voice choices, timing and render profile. The new interface uses the copied FrameForge CPU 3D preview renderer and exports a JSON cutscene project. The native pipeline builds original, procedural, armature-rigged Blender characters and outputs MP4, editable BLEND, SRT and ASS subtitles.

### Cutscene limits

- Default output: **1280×720 (720p)**.
- Maximum output: **1920×1080 (1080p)**.
- Maximum frame rate: **30 FPS**.
- Maximum single-cutscene duration: **10 minutes**.
- CPU profiles: Low (8 samples / at most 2 CPU threads), Balanced (16 / 4), High (32 / 8).
- No 2K or 4K export paths are provided.

### Dialogue and lip-sync

The only allowed Pocket TTS voices are Eponine, George, Ezelma (provider ID `azelma`), Bill Boerst, Jean, Michael, Peter Yearsley, Stuart Bell and Charles. The validator blocks other voices. Each line is rendered to WAV, measured, forced-aligned against its exact text with WhisperX, and mapped to Blender jaw/viseme keys. Subtitles use an outline-only ASS style with a fully transparent background (no black subtitle box).

Pocket TTS does not emit native phoneme/viseme timestamps. WhisperX provides acoustic character alignment; the current character-to-viseme mapping is an approximation and requires visual review/refinement. It is not honest to guarantee perfectly accurate lip movement automatically at this stage.

### Run a local cutscene

See [cutscene installation](cutscenes/INSTALL.md). Install Python, Blender, FFmpeg/FFprobe, Pocket TTS and WhisperX first. Then run:

```bash
python gameforge/cutscenes/run_cutscene.py \
  --project gameforge/cutscenes/config/default_project.json \
  --out build/cutscene
```

The browser editor only writes the project manifest; it cannot launch Blender or TTS directly.

## Validation and export

- `.github/workflows/gameforge-validate.yml` runs project, Python and Godot checks.
- `.github/workflows/gameforge-export.yml` exports an Android debug APK and Windows executable for testing.
- `.github/workflows/gameforge-cutscene-prototype.yml` is a manual, opt-in sample render; it can validate the code without consuming render minutes, and only runs a full TTS/Blender render when explicitly requested.

GitHub Actions has finite minutes, storage and runner limits. The 1080p ceiling helps control file size but does not make long CPU renders free or instantaneous. The full game still needs an authored vertical slice, original content, physical-device performance testing and release-signing checks.

## Current completion boundary

This branch adds a structured cutscene editor, a procedural Blender rig/scene builder, Kyutai voice generation, forced alignment, transparent-background subtitle output and CPU render profiles. It has not yet been run end-to-end on a real Blender/Pocket TTS/WhisperX installation in this workspace. The generated character design, facial motion quality, final audio levels and output video must be reviewed in the first local prototype before the subsystem can be considered production-ready.
