# GAMEFORGE Cutscene Studio

The supported production route is **GitHub Actions**. The browser editor creates a project manifest; GitHub-hosted runners install Blender, FFmpeg, Pocket TTS, WhisperX and the required Python dependencies, then generate the assets and render the cutscene. You do not need those programs installed on your own computer.

## GitHub cloud workflow

1. Open `editor/index.html` from this directory (or the deployed GitHub Pages copy, when enabled).
2. Create the characters and dialogue, using only the approved voice IDs.
3. Export the JSON project manifest.
4. Add that JSON file to this repository, for example under `gameforge/cutscenes/projects/`.
5. Open the [GAMEFORGE GitHub Cloud Pipeline](https://github.com/FRFR-FR/frameforge/actions/workflows/gameforge-cloud.yml), select the `gameforge-cutscene-integration` branch, and press **Run workflow**.
6. Enable **run_cutscene**, enter the manifest's repository-relative path, and select the render profile.
7. Before generating speech, review `VOICE_LICENSES.md` for the selected assets and confirm the workflow input. Download the cutscene artifact when the job finishes.

The artifact contains the MP4, editable Blender scene, rigged animated GLB, SRT/ASS subtitles, scene audit, alignment manifest and render report.

## Output policy

- 16:9 cutscene output only.
- Default: 1280x720 (720p), up to 30 FPS.
- Maximum: 1920x1080 (1080p), 30 FPS and 600 seconds per cutscene.
- Characters are generated procedurally in Blender; no image-generation service is used.
- The hosted workflow renders on CPU. Standard public GitHub runners do not provide a GPU.
- Long renders may exceed GitHub's six-hour per-job ceiling; the maximum duration is a format cap, not a promise that a maximum-length render will complete on a standard runner.

## Voice policy and lip-sync

Pocket TTS IDs are `eponine`, `george`, `azelma` (UI label Ezelma), `bill_boerst`, `jean`, `michael`, `peter_yearsley`, `stuart_bell` and `charles`. Review the source terms for each selected voice before any commercial release; the presets do not all necessarily share the same licence. The workflow requires an acknowledgement before it downloads or generates dialogue audio.

Pocket TTS does not emit native phoneme/viseme timestamps. WhisperX provides forced character alignment, and GAMEFORGE maps those timestamps to approximate mouth shapes. Review facial sync in the output before shipping; perfect lip movement is not guaranteed.

## Original FrameForge isolation

The standalone FrameForge editor at the repository root remains independent. This directory contains the GAMEFORGE-only editor copy and its cutscene pipeline.
