# Copied FrameForge engine components

This directory contains the source components copied from the original root FrameForge application on the main branch of this repository. The original files at the repository root remain untouched and continue to support independent video/animation projects.

The GAMEFORGE-only editor is the sibling `../index.html` and `../editor.js`. It loads `frameforge-3d.js` for its lightweight 3D preview. The original drawing app JavaScript and visual theme are retained here as the code base that was copied; the GAMEFORGE cutscene workflow replaces its drawing-first controls with character, dialogue, audio, subtitle and render-manifest controls.

No external image generation is used. Production 3D geometry, armatures, animation and cutscene rendering are authored by the Blender Python pipeline under `../../blender/`.
