# GAMEFORGE Cutscene Studio

This is a GAMEFORGE-only derivative of FrameForge. The original standalone FrameForge editor remains at the repository root and is not modified by this subsystem. The copied FrameForge canvas/3D source is kept under `editor/core/`; the GAMEFORGE editor adds a character/dialogue director and exports a cutscene project manifest for the native Blender pipeline.

## Scope and output limits

- 16:9 cutscene output only.
- Default: 1280x720 (720p), up to 30 FPS.
- Maximum: 1920x1080 (1080p). The renderer rejects larger dimensions and frame rates above 30.
- Character geometry and rigs are generated procedurally in Blender; no image-generation service is used.
- Blender renders on CPU in bounded quality profiles. This avoids GPU dependency but is slower.
- Final MP4 includes synced dialogue audio and outline-only subtitles with no subtitle box/background.

## Voice policy

The voice selector is a strict allowlist. Canonical Pocket TTS IDs:
`eponine`, `george`, `azelma` (UI label: Ezelma), `bill_boerst`, `jean`, `michael`, `peter_yearsley`, `stuart_bell`, `charles`.
No other TTS voices are accepted by the project validator.

## First prototype

Install Blender, FFmpeg, Python 3.11 or 3.12, and Pocket TTS. For accurate dialogue timing, install the optional WhisperX forced aligner and its CPU PyTorch dependencies. See [INSTALL.md](INSTALL.md).

1. Open `editor/index.html` from the GAMEFORGE copy (not the root FrameForge site).
2. Create characters and assign only an allowlisted voice.
3. Add dialogue with intended start times, then export `cutscene_project.json`.
4. Run `python gameforge/cutscenes/run_cutscene.py --project cutscene_project.json --out build/cutscene`.
5. Review the rendered MP4 and the alignment report before using it in a game.

The browser editor only authors the manifest. A static GitHub Pages page cannot start Blender or run the TTS model by itself.

## Synchronisation quality

Pocket TTS produces audio, not phoneme timestamps. This pipeline therefore measures the actual generated WAV duration and uses WhisperX forced character alignment to obtain audio-grounded cue positions. The Blender rig consumes the resulting viseme cue data and exports a skinned GLB for Godot import. The in-game runtime has a jaw-bone cue component that listens to the same audio playback clock. Lip shape mapping is an approximation from aligned characters (not a native phoneme stream), so the final face animation must receive visual review. No software can guarantee perfect lip-sync for every line without correction; the pipeline fails on an unavailable aligner rather than silently pretending estimated timings are exact.

## Original FrameForge isolation

The original `/index.html`, `/app.js`, `/styles.css` and `/frameforge-3d.js` stay in place for independent film projects. This branch places copies inside `gameforge/cutscenes/editor/core/`; GAMEFORGE's cutscene page links to its own manifest editor and uses the copied FrameForge 3D software renderer for a lightweight preview.

## In-game character lip-sync

Import the generated `GAMEFORGE_Cutscene_Characters.glb` into Godot. Attach `gameforge/runtime/godot_template/scripts/cutscene_character_lip_sync.gd` to each character root, set the `skeleton_path` to the imported `Skeleton3D`, and add the root node to `gameforge_character_<character_id>`. GAMEFORGE's audio director emits the audio-aligned jaw cues, returns the jaw to neutral at each cue end, and drives subtitles from the same playback clock.
